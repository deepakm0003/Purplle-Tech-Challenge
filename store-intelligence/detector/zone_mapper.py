"""
Zone Mapping Module.

Maps bounding boxes to store zones using point-in-polygon tests
on pre-defined zone polygons from configuration.
"""

import logging
import json
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


class ZoneMapper:
    """
    Zone mapping using polygon regions.
    
    Attributes:
        zones: Dict of zone_id -> list of (x, y) polygon vertices
        current_zones: Dict of track_id -> current zone_id
        previous_zones: Dict of track_id -> previous zone_id
    """
    
    def __init__(self, config_path: str = "configs/zones.json"):
        """
        Initialize zone mapper from configuration.
        
        Args:
            config_path: Path to zones.json configuration file
            
        Raises:
            FileNotFoundError: If config file not found
            ValueError: If config is invalid
        """
        self.zones: Dict[str, List[Tuple[float, float]]] = {}
        self.current_zones: Dict[int, str] = {}  # track_id -> zone_id
        self.previous_zones: Dict[int, str] = {}  # track_id -> zone_id
        self.zone_entry_time: Dict[Tuple[int, str], float] = {}  # (track_id, zone_id) -> timestamp
        
        self._load_zones(config_path)
        logger.info(f"Zone mapper initialized with {len(self.zones)} zones")
    
    def _add_zone_polygon(self, zone_id: str, polygon: list) -> None:
        """Parse polygon vertices into internal zone map."""
        vertices = []
        for vertex in polygon:
            if isinstance(vertex, list) and len(vertex) == 2:
                vertices.append((float(vertex[0]), float(vertex[1])))
            else:
                raise ValueError(f"Invalid vertex format in zone {zone_id}")
        self.zones[zone_id] = vertices

    def _load_zones(self, config_path: str) -> None:
        """
        Load zones from JSON configuration.
        
        Args:
            config_path: Path to zones.json
            
        Raises:
            FileNotFoundError: If file not found
            ValueError: If format is invalid
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            raise FileNotFoundError(f"Zone config not found: {config_path}")
        
        try:
            with open(config_file, encoding="utf-8") as f:
                raw = f.read()
            # Strip leading block comments / docstrings (legacy config files)
            start = raw.find("{")
            if start > 0:
                raw = raw[start:]
            config = json.loads(raw)

            # Format A: { "zones": [ { "zone_id", "polygon": [...] }, ... ] }
            if isinstance(config.get("zones"), list):
                for zone in config["zones"]:
                    zone_id = zone.get("zone_id") or zone.get("id")
                    polygon = zone.get("polygon")
                    if not zone_id or not polygon:
                        continue
                    self._add_zone_polygon(str(zone_id), polygon)
            else:
                # Format B: { "ZONE_ID": [[x,y], ...], ... }
                for zone_id, polygon in config.items():
                    if zone_id in ("store_id", "store_name", "camera_id", "zones"):
                        continue
                    if isinstance(polygon, list):
                        self._add_zone_polygon(str(zone_id), polygon)

            logger.info(f"Loaded {len(self.zones)} zones: {list(self.zones.keys())}")
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in zones config: {e}") from e
        except Exception as e:
            raise ValueError(f"Failed to load zone config: {e}") from e
    
    def point_in_polygon(
        self,
        point: Tuple[float, float],
        polygon: List[Tuple[float, float]]
    ) -> bool:
        """
        Ray-casting algorithm for point-in-polygon test.
        
        Args:
            point: (x, y) coordinates
            polygon: List of (x, y) vertices
            
        Returns:
            True if point is inside polygon
        """
        x, y = point
        n = len(polygon)
        inside = False
        
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            
            j = i
        
        return inside
    
    def get_zone(self, bbox: List[float]) -> Optional[str]:
        """
        Get zone for bounding box using centroid.
        
        Args:
            bbox: [x1, y1, x2, y2] bounding box coordinates
            
        Returns:
            zone_id if point in zone, else None
        """
        if not bbox or len(bbox) != 4:
            return None
        
        # Calculate centroid
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        
        # Check against all zones
        for zone_id, polygon in self.zones.items():
            if self.point_in_polygon((cx, cy), polygon):
                return zone_id
        
        return None
    
    def update_track_zone(
        self,
        track_id: int,
        bbox: List[float]
    ) -> Tuple[Optional[str], bool]:
        """
        Update track location and detect zone transitions.
        
        Args:
            track_id: Detector track ID
            bbox: [x1, y1, x2, y2] bounding box
            
        Returns:
            (current_zone, is_transition) tuple
        """
        current_zone = self.get_zone(bbox)
        
        previous_zone = self.current_zones.get(track_id)
        self.current_zones[track_id] = current_zone
        
        is_transition = current_zone != previous_zone
        
        if is_transition and previous_zone is not None:
            self.previous_zones[track_id] = previous_zone
            logger.debug(f"Track {track_id}: {previous_zone} -> {current_zone}")
        
        return current_zone, is_transition
    
    def get_zone_transition(
        self,
        track_id: int
    ) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """
        Get previous and current zones for track.
        
        Args:
            track_id: Detector track ID
            
        Returns:
            (previous_zone, current_zone) or None if no transition
        """
        current = self.current_zones.get(track_id)
        previous = self.previous_zones.get(track_id)
        
        if current is None:
            return None
        
        return (previous, current)
    
    def detect_entry(self, track_id: int, zone_id: str = "ENTRY") -> bool:
        """
        Check if track entered the store (entry zone).
        
        Args:
            track_id: Detector track ID
            zone_id: Entry zone identifier
            
        Returns:
            True if track just entered entry zone
        """
        current = self.current_zones.get(track_id)
        previous = self.previous_zones.get(track_id)
        
        return current == zone_id and previous is None
    
    def detect_exit(self, track_id: int, zone_id: str = "ENTRY") -> bool:
        """
        Check if track exited the store (left entry zone).
        
        Args:
            track_id: Detector track ID
            zone_id: Entry zone identifier
            
        Returns:
            True if track just left entry zone
        """
        current = self.current_zones.get(track_id)
        previous = self.previous_zones.get(track_id)
        
        return current is None and previous == zone_id
    
    def get_current_zone(self, track_id: int) -> Optional[str]:
        """Get current zone for track."""
        return self.current_zones.get(track_id)
    
    def get_previous_zone(self, track_id: int) -> Optional[str]:
        """Get previous zone for track."""
        return self.previous_zones.get(track_id)
    
    def reset_track(self, track_id: int) -> None:
        """Reset tracking state for track ID."""
        self.current_zones.pop(track_id, None)
        self.previous_zones.pop(track_id, None)
        
        # Clean up entry time records
        keys_to_remove = [k for k in self.zone_entry_time.keys() if k[0] == track_id]
        for key in keys_to_remove:
            del self.zone_entry_time[key]
    
    def get_zones(self) -> Dict[str, List[Tuple[float, float]]]:
        """Get all zone definitions."""
        return self.zones.copy()
    
    def get_all_zones_for_bbox(
        self,
        bbox: List[float]
    ) -> List[str]:
        """
        Get all zones that contain the bbox centroid.
        
        Args:
            bbox: Bounding box [x1, y1, x2, y2]
            
        Returns:
            List of zone IDs containing the point
        """
        if not bbox or len(bbox) != 4:
            return []
        
        cx = (bbox[0] + bbox[2]) / 2.0
        cy = (bbox[1] + bbox[3]) / 2.0
        
        zones = []
        for zone_id, polygon in self.zones.items():
            if self.point_in_polygon((cx, cy), polygon):
                zones.append(zone_id)
        
        return zones
    
    def get_stats(self) -> Dict[str, Any]:
        """Get zone mapper statistics."""
        return {
            'total_zones': len(self.zones),
            'zone_ids': list(self.zones.keys()),
            'tracked_objects': len(self.current_zones),
            'zone_definitions': {
                zone_id: len(verts) for zone_id, verts in self.zones.items()
            }
        }
    
    def reset(self) -> None:
        """Reset all tracking state."""
        self.current_zones.clear()
        self.previous_zones.clear()
        self.zone_entry_time.clear()
        logger.info("Zone mapper reset")

