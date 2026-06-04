"""
Store Layout Parser Module.

Parses store_layout.json for:
- Store metadata
- Camera definitions and positioning
- Zone definitions and polygons
- Operating hours

Validates layout integrity and provides query interfaces.
"""

import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
from loguru import logger
from pydantic import BaseModel, Field

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


class CameraDefinition(BaseModel):
    """Camera configuration."""
    camera_id: str
    location: str  # "ENTRY", "FLOOR", "BILLING"
    position: Tuple[float, float, float]  # x, y, z coordinates
    resolution: Tuple[int, int]  # width, height
    fov_degrees: float  # Field of view in degrees
    enabled: bool = True

    class Config:
        from_attributes = True


class ZonePolygon(BaseModel):
    """Zone boundary polygon."""
    zone_id: str
    zone_name: str
    polygon_points: List[Tuple[float, float]]  # List of (x, y) coordinates
    category: str  # "ENTRY", "DISPLAY", "BILLING", "CHECKOUT", "OTHER"
    priority: int = 1  # 1=high (billing), 10=low (display)

    class Config:
        from_attributes = True


class StoreLayout(BaseModel):
    """Complete store layout."""
    store_id: str
    store_name: str
    city: str
    country: str
    timezone: str
    operating_hours: Dict[str, Tuple[str, str]]  # day -> (open_time, close_time)
    cameras: List[CameraDefinition]
    zones: List[ZonePolygon]
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        from_attributes = True


class LayoutParser:
    """
    Store Layout Parser.
    
    Loads and validates store_layout.json.
    Provides query interfaces for cameras and zones.
    
    Attributes:
        layout: Parsed StoreLayout
        store_id: Store identifier
        camera_map: Map of camera_id -> CameraDefinition
        zone_map: Map of zone_id -> ZonePolygon
    """
    
    def __init__(self):
        """Initialize parser."""
        self.layout: Optional[StoreLayout] = None
        self.store_id: Optional[str] = None
        self.camera_map: Dict[str, CameraDefinition] = {}
        self.zone_map: Dict[str, ZonePolygon] = {}
        logger.info("LayoutParser initialized")
    
    def load_layout(self, file_path: str) -> bool:
        """
        Load and validate store layout from JSON.
        
        Args:
            file_path: Path to store_layout.json
            
        Returns:
            True if successful
        """
        try:
            file_path = Path(file_path)
            
            if not file_path.exists():
                logger.error(f"Layout file not found: {file_path}")
                return False
            
            with open(file_path, 'r') as f:
                layout_dict = json.load(f)
            
            # Parse and validate
            self.layout = StoreLayout(**layout_dict)
            self.store_id = self.layout.store_id
            
            # Build maps
            self.camera_map = {cam.camera_id: cam for cam in self.layout.cameras}
            self.zone_map = {zone.zone_id: zone for zone in self.layout.zones}
            
            logger.info(
                f"Layout loaded: {self.layout.store_name} "
                f"({len(self.layout.cameras)} cameras, {len(self.layout.zones)} zones)"
            )
            
            # Validate
            if not self.validate_layout():
                logger.error("Layout validation failed")
                return False
            
            return True
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error in layout file: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error loading layout: {str(e)}")
            return False
    
    def validate_layout(self) -> bool:
        """
        Validate layout integrity.
        
        Checks:
        - All cameras have valid IDs
        - All zones have valid IDs and polygons
        - Operating hours are valid
        - No duplicate IDs
        
        Returns:
            True if valid
        """
        if not self.layout:
            logger.error("No layout loaded")
            return False
        
        # Check cameras
        camera_ids = set()
        for cam in self.layout.cameras:
            if not cam.camera_id or cam.camera_id in camera_ids:
                logger.error(f"Invalid or duplicate camera ID: {cam.camera_id}")
                return False
            camera_ids.add(cam.camera_id)
            
            # Validate position
            if len(cam.position) != 3:
                logger.error(f"Camera {cam.camera_id} has invalid position")
                return False
            
            # Validate resolution
            if cam.resolution[0] <= 0 or cam.resolution[1] <= 0:
                logger.error(f"Camera {cam.camera_id} has invalid resolution")
                return False
            
            # Validate FOV
            if cam.fov_degrees <= 0 or cam.fov_degrees > 180:
                logger.error(f"Camera {cam.camera_id} has invalid FOV")
                return False
        
        # Check zones
        zone_ids = set()
        for zone in self.layout.zones:
            if not zone.zone_id or zone.zone_id in zone_ids:
                logger.error(f"Invalid or duplicate zone ID: {zone.zone_id}")
                return False
            zone_ids.add(zone.zone_id)
            
            # Validate polygon
            if len(zone.polygon_points) < 3:
                logger.error(f"Zone {zone.zone_id} has fewer than 3 points")
                return False
        
        # Check operating hours
        valid_days = {'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'}
        for day in self.layout.operating_hours.keys():
            if day not in valid_days:
                logger.error(f"Invalid day: {day}")
                return False
        
        logger.info("Layout validation passed")
        return True
    
    def get_store_zones(self) -> List[ZonePolygon]:
        """
        Get all zones.
        
        Returns:
            List of ZonePolygon
        """
        if not self.layout:
            return []
        
        # Sort by priority (higher = more important)
        return sorted(self.layout.zones, key=lambda z: z.priority)
    
    def get_zone_by_id(self, zone_id: str) -> Optional[ZonePolygon]:
        """
        Get zone by ID.
        
        Args:
            zone_id: Zone identifier
            
        Returns:
            ZonePolygon or None
        """
        return self.zone_map.get(zone_id)
    
    def get_zones_by_category(self, category: str) -> List[ZonePolygon]:
        """
        Get zones by category.
        
        Args:
            category: Zone category (ENTRY, BILLING, etc.)
            
        Returns:
            List of matching ZonePolygon
        """
        return [z for z in self.layout.zones if z.category == category] if self.layout else []
    
    def get_camera_mapping(self) -> Dict[str, CameraDefinition]:
        """
        Get all cameras.
        
        Returns:
            Dict of camera_id -> CameraDefinition
        """
        return self.camera_map
    
    def get_camera_by_id(self, camera_id: str) -> Optional[CameraDefinition]:
        """
        Get camera by ID.
        
        Args:
            camera_id: Camera identifier
            
        Returns:
            CameraDefinition or None
        """
        return self.camera_map.get(camera_id)
    
    def get_cameras_by_location(self, location: str) -> List[CameraDefinition]:
        """
        Get cameras by location.
        
        Args:
            location: Location name (ENTRY, FLOOR, BILLING)
            
        Returns:
            List of CameraDefinition
        """
        return [
            c for c in self.layout.cameras if c.location == location
        ] if self.layout else []
    
    def get_store_info(self) -> Dict[str, Any]:
        """
        Get store information.
        
        Returns:
            Store metadata dict
        """
        if not self.layout:
            return {}
        
        return {
            'store_id': self.layout.store_id,
            'store_name': self.layout.store_name,
            'city': self.layout.city,
            'country': self.layout.country,
            'timezone': self.layout.timezone,
            'camera_count': len(self.layout.cameras),
            'zone_count': len(self.layout.zones),
            'operating_hours': self.layout.operating_hours
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get parser statistics."""
        return {
            'store_id': self.store_id,
            'cameras_loaded': len(self.camera_map),
            'zones_loaded': len(self.zone_map),
            'is_valid': self.validate_layout() if self.layout else False
        }


def create_layout_parser(file_path: str) -> Optional[LayoutParser]:
    """
    Factory function to create and load LayoutParser.
    
    Args:
        file_path: Path to store_layout.json
        
    Returns:
        Loaded LayoutParser or None if failed
    """
    parser = LayoutParser()
    if parser.load_layout(file_path):
        return parser
    return None
