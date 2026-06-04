"""
Video Processing Module

Processes video files to detect persons, track them, extract embeddings,
map zones, manage sessions, and generate structured events.

Integrates: YOLOv8 detection → ByteTrack tracking → ReID matching → 
ZoneMapper → SessionManager → EventGenerator
"""

import logging
import json
import cv2
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta
import uuid
from tqdm import tqdm
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from .detector import PersonDetector, Detection, create_detector
from .tracker import MultiObjectTracker, Track, create_tracker
from .reid import ReIDManager
from .zone_mapper import ZoneMapper
from .session_manager import SessionManager
from .event_generator import EventGenerator
from .visitor_state import VisitorStateManager
from .detection_filters import DetectionFilter, dedupe_confirmed_tracks
from .event_postprocess import postprocess_events
from api.schemas import Event


class VideoProcessor:
    """
    Complete Video Processing Pipeline.
    
    Processes video frames through full intelligence layer:
    detection → tracking → ReID → zone mapping → session management → event generation
    
    Attributes:
        detector: PersonDetector instance
        tracker: MultiObjectTracker instance
        reid_manager: ReIDManager for visitor re-identification
        zone_mapper: ZoneMapper for spatial zone assignment
        session_manager: SessionManager for visitor lifecycle
        event_generator: EventGenerator for event creation
        visitor_manager: Legacy VisitorStateManager (backward compat)
    """
    
    def __init__(
        self,
        detector: PersonDetector,
        tracker: MultiObjectTracker,
        reid_manager: Optional[ReIDManager] = None,
        zone_mapper: Optional[ZoneMapper] = None,
        session_manager: Optional[SessionManager] = None,
        event_generator: Optional[EventGenerator] = None,
        visitor_manager: Optional[VisitorStateManager] = None,
        fps_sample_rate: int = 5,
        store_id: str = "STORE-001",
        camera_id: str = "CAM-001",
        camera_role: str = "zone",
        entry_camera_ids: Optional[List[str]] = None,
    ):
        """
        Initialize VideoProcessor with full intelligence layer.
        
        Args:
            detector: PersonDetector instance
            tracker: MultiObjectTracker instance
            reid_manager: Optional ReIDManager for visitor matching
            zone_mapper: Optional ZoneMapper for zone assignment
            session_manager: Optional SessionManager for session tracking
            event_generator: Optional EventGenerator for event creation
            visitor_manager: Optional legacy VisitorStateManager (backward compat)
            fps_sample_rate: Sample rate (process every N frames)
            store_id: Store identifier
            camera_id: Camera identifier
        """
        self.detector = detector
        self.tracker = tracker
        self.reid_manager = reid_manager
        self.zone_mapper = zone_mapper
        self.session_manager = session_manager
        self.event_generator = event_generator
        self.visitor_manager = visitor_manager
        
        self.fps_sample_rate = fps_sample_rate
        self.store_id = store_id
        self.camera_id = camera_id
        self.camera_role = camera_role
        self.entry_camera_ids = set(entry_camera_ids or [])
        if camera_role == "entry":
            self.entry_camera_ids.add(camera_id)

        self.detection_filter: Optional[DetectionFilter] = None
        self._frame_width = 1920
        self._frame_height = 1080
        self._video_fps = 25.0
        self._video_start = datetime.utcnow()
        
        # Event tracking
        self.events: List[Event] = []
        self.frame_count = 0
        self.processed_count = 0
        
        # Track state
        self.track_to_visitor: Dict[int, str] = {}  # track_id -> visitor_id
        self.current_tracks: set = set()

        # Diagnostics
        self.total_detections = 0
        self.total_track_frames = 0
        self._zones_scaled = False

        # Per-frame track export (frontend video overlay)
        self.track_recorder = None
        
        logger.info(
            f"VideoProcessor init: fps_sample_rate={fps_sample_rate}, "
            f"store_id={store_id}, camera_id={camera_id}, "
            f"reid={reid_manager is not None}, zone_mapper={zone_mapper is not None}, "
            f"session_manager={session_manager is not None}, "
            f"event_generator={event_generator is not None}"
        )
    
    def process_video(
        self,
        video_path: str,
        output_path: Optional[str] = None,
        tracks_output: Optional[str] = None,
        show_progress: bool = True,
    ) -> Tuple[int, List[Event]]:
        """
        Process a video file end-to-end.
        
        Args:
            video_path: Path to video file
            output_path: Optional path to save events as JSONL
            tracks_output: Optional path to save per-frame bboxes JSON (video overlay)
            show_progress: Show progress bar
            
        Returns:
            (total_events_generated, events_list)
        """
        video_path = Path(video_path)
        video_path = Path(video_path)
        
        if not video_path.exists():
            raise FileNotFoundError(f"Video file not found: {video_path}")
        
        logger.info(f"Starting video processing: {video_path}")
        
        # Open video
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            raise RuntimeError(f"Failed to open video: {video_path}")
        
        try:
            # Get video properties
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self._frame_width = width
            self._frame_height = height
            self._video_fps = float(fps)
            self.detection_filter = DetectionFilter(
                width,
                height,
                camera_role=self.camera_role,
                min_confidence=self.detector.confidence_threshold,
            )
            self._video_start = datetime.utcnow()

            if tracks_output:
                from detector.track_export import FrameTrackRecorder

                self.track_recorder = FrameTrackRecorder(
                    video_name=video_path.name,
                    fps=self._video_fps,
                    width=width,
                    height=height,
                    sample_rate=self.fps_sample_rate,
                )
            
            logger.info(
                f"Processing video: {video_path.name} - "
                f"{total_frames} frames, {fps} FPS, {width}x{height}"
            )

            if self.zone_mapper and width > 0 and height > 0:
                self._scale_zone_mapper_to_frame(width, height)

            if not self.event_generator:
                logger.warning(
                    "EventGenerator not configured — no events will be written. "
                    "Pass session_manager and event_generator when creating VideoProcessor."
                )
            
            # Process frames
            pbar = tqdm(
                total=total_frames,
                desc="Processing video",
                disable=not show_progress
            )
            
            self.events = []
            self.frame_count = 0
            self.processed_count = 0
            self.track_to_visitor = {}
            self.current_tracks = set()
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                self.frame_count += 1
                
                # Sample frames — run detector + tracker
                if self.frame_count % self.fps_sample_rate == 0:
                    self.processed_count += 1
                    self._process_frame(frame)

                # Record track boxes on every frame so overlay follows motion smoothly
                if self.track_recorder is not None:
                    active = self.tracker.get_active_tracks()
                    tentative = [
                        t
                        for t in self.tracker.get_all_tracks()
                        if t.state == "tentative" and t.time_since_update == 0
                    ]
                    seen = {t.track_id for t in active}
                    combined = active + [t for t in tentative if t.track_id not in seen]
                    self.track_recorder.record(
                        self.frame_count - 1,
                        combined,
                        self.zone_mapper,
                    )
                
                pbar.update(1)
            
            pbar.close()
            
            # Finalize all sessions
            self._finalize_sessions()

            # Post-process: staff flags, entry-camera-only footfall, dedupe
            if self.events:
                self.events = postprocess_events(
                    self.events,
                    entry_camera_ids=self.entry_camera_ids or None,
                    mark_staff=True,
                )
            
            logger.info(
                f"Video processing complete: {self.processed_count} frames processed, "
                f"{len(self.events)} events generated"
            )
            
            # Save events if output path provided
            if output_path:
                self._save_events(output_path)

            if self.track_recorder and tracks_output:
                self.track_recorder.save(tracks_output)
            
            return len(self.events), self.events
            
        finally:
            cap.release()
    
    def _process_frame(self, frame: np.ndarray) -> None:
        """
        Process a single frame through complete pipeline.
        
        Pipeline: detect → track → extract bboxes → 
                  reid match → zone map → session update → generate events
        
        Args:
            frame: Video frame
        """
        try:
            # 1. DETECTION: YOLOv8 person detection
            detections = self.detector.detect(frame)
            
            det_list = [{"bbox": d.bbox, "confidence": d.confidence} for d in detections]
            if self.detection_filter:
                det_list = self.detection_filter.filter_detections(det_list)
            self.total_detections += len(det_list)
            
            # 2. TRACKING: ByteTrack update
            tracks = self.tracker.update(det_list)
            tracks = dedupe_confirmed_tracks(tracks)
            self.total_track_frames += len(tracks)
            
            # Store current track IDs
            self.current_tracks = {t.track_id for t in tracks}
            
            # 3. MAIN UPDATE LOOP: For each track
            for track in tracks:
                # Extract person crop for ReID if available
                embedding = None
                if self.reid_manager and track.bbox:
                    try:
                        x1, y1, x2, y2 = [int(c) for c in track.bbox]
                        person_crop = frame[max(0, y1):min(frame.shape[0], y2), 
                                            max(0, x1):min(frame.shape[1], x2)]
                        if person_crop.size > 0:
                            embedding = self.reid_manager.extract_embedding(person_crop)
                    except Exception as e:
                        logger.debug(f"ReID extraction failed: {e}")
                
                # 4. ZONE MAPPING: Get zone from bbox center
                zone_id = None
                if self.zone_mapper and track.bbox:
                    try:
                        zone_id = self.zone_mapper.get_zone(track.bbox)
                    except Exception as e:
                        logger.debug(f"Zone mapping failed: {e}")
                
                # 5. SESSION & EVENT MANAGEMENT
                if track.track_id not in self.track_to_visitor:
                    # New track - create session
                    self._handle_new_track(track, zone_id, embedding)
                else:
                    # Update existing session
                    self._handle_existing_track(track, zone_id, embedding)
            
            # 6. CLEANUP: Handle disappeared tracks
            self._handle_disappeared_tracks()
            
            # 7. CLEANUP: Expire sessions
            if self.session_manager:
                self.session_manager.cleanup_expired_sessions()
            
            logger.debug(
                f"Frame {self.frame_count}: {len(detections)} detections, {len(tracks)} tracks"
            )
            
        except Exception as e:
            logger.error(f"Frame processing failed at frame {self.frame_count}: {e}")
            raise
    
    def _handle_new_track(
        self,
        track: Track,
        zone_id: Optional[str],
        embedding: Optional[np.ndarray]
    ) -> None:
        """
        Handle new track detection (entry).
        
        Args:
            track: Track object
            zone_id: Zone ID
            embedding: Visitor embedding
        """
        # Check if visitor already exists (re-entry via ReID)
        visitor_id = None
        is_reentry = False
        
        if self.reid_manager and embedding is not None:
            # Try to match against existing embeddings
            match = self.reid_manager.match_existing_visitor(embedding)
            if match:
                visitor_id = match.visitor_id
                is_reentry = True
                logger.info(f"ReID match: track {track.track_id} -> visitor {visitor_id}")
        
        # Create new visitor ID if no match
        if visitor_id is None:
            visitor_id = f"VIS_{uuid.uuid4().hex[:8]}"
        
        # Store mapping
        self.track_to_visitor[track.track_id] = visitor_id
        
        # Create session if using SessionManager
        if self.session_manager:
            session = self.session_manager.start_session(track.track_id, visitor_id)
            
            # Update zone
            if zone_id:
                self.session_manager.update_session(visitor_id, zone_id)
            
            # Mark re-entry if applicable
            if is_reentry:
                self.session_manager.mark_reentry(visitor_id)
        
        # Generate ENTRY / REENTRY only on entry cameras
        if self.event_generator and self.camera_id in self.entry_camera_ids:
            ts = self._timestamp_for_current_frame()
            if is_reentry:
                event = self.event_generator.generate_reentry_event(
                    visitor_id=visitor_id,
                    timestamp=ts,
                    confidence=track.confidence,
                )
            else:
                event = self.event_generator.generate_entry_event(
                    visitor_id=visitor_id,
                    zone_id=zone_id or "ENTRY",
                    timestamp=ts,
                    confidence=track.confidence,
                )
            self.events.append(event)
        
        # Store embedding if ReID active
        if self.reid_manager and embedding is not None:
            self.reid_manager.create_new_visitor(embedding, visitor_id)
        
        logger.debug(
            f"New track {track.track_id}: visitor {visitor_id}, "
            f"is_reentry={is_reentry}, zone={zone_id}"
        )
    
    def _handle_existing_track(
        self,
        track: Track,
        zone_id: Optional[str],
        embedding: Optional[np.ndarray]
    ) -> None:
        """
        Handle existing track update.
        
        Args:
            track: Track object
            zone_id: Zone ID
            embedding: Visitor embedding
        """
        visitor_id = self.track_to_visitor.get(track.track_id)
        if not visitor_id:
            logger.warning(f"Track {track.track_id} not in mapping")
            return

        session = self.session_manager.get_session(visitor_id) if self.session_manager else None
        previous_zone = session.current_zone if session else None
        ts = self._timestamp_for_current_frame()

        if self.session_manager and zone_id:
            self.session_manager.update_session(visitor_id, zone_id)

        if session and zone_id and self.event_generator and previous_zone != zone_id:
            if previous_zone:
                dwell_ms = int(session.get_zone_dwell(previous_zone) * 1000)
                if dwell_ms > 0:
                    self.events.append(
                        self.event_generator.generate_zone_exit_event(
                            visitor_id=visitor_id,
                            zone_id=previous_zone,
                            dwell_ms=dwell_ms,
                            timestamp=ts,
                            confidence=track.confidence,
                        )
                    )
            self.events.append(
                self.event_generator.generate_zone_enter_event(
                    visitor_id=visitor_id,
                    zone_id=zone_id,
                    timestamp=ts,
                    confidence=track.confidence,
                )
            )
        elif session and zone_id and self.event_generator and previous_zone == zone_id:
            dwell_ms = int(session.get_zone_dwell(zone_id) * 1000)
            event = self.event_generator.generate_zone_dwell_event(
                visitor_id=visitor_id,
                zone_id=zone_id,
                dwell_ms=dwell_ms,
                timestamp=ts,
                confidence=track.confidence,
            )
            if event:
                self.events.append(event)
    
    def _timestamp_for_current_frame(self) -> datetime:
        offset_sec = max(0, self.frame_count - 1) / max(self._video_fps, 1.0)
        return self._video_start + timedelta(seconds=offset_sec)
    
    def _handle_disappeared_tracks(self) -> None:
        """Handle tracks that disappeared in this frame."""
        # Get previously active tracks
        previous_tracks = set(self.track_to_visitor.keys())
        
        # Find disappeared tracks
        disappeared = previous_tracks - self.current_tracks
        
        for track_id in disappeared:
            visitor_id = self.track_to_visitor.get(track_id)
            if visitor_id:
                # Close session and generate EXIT
                if self.session_manager:
                    session = self.session_manager.close_session(visitor_id)
                    
                    if session and self.event_generator and self.camera_id in self.entry_camera_ids:
                        self.events.append(
                            self.event_generator.generate_exit_event(
                                session=session,
                                timestamp=self._timestamp_for_current_frame(),
                                confidence=0.9,
                            )
                        )
                
                # Remove from mapping
                del self.track_to_visitor[track_id]
                logger.debug(f"Track {track_id} disappeared, closed session")
    
    def _finalize_sessions(self) -> None:
        """Finalize all active sessions at end of video."""
        if not self.session_manager:
            return
        
        # Get all active sessions and close them
        active = self.session_manager.get_active_sessions()
        for session in active:
            self.session_manager.close_session(session.visitor_id)
            
            # Generate EXIT event
            if self.event_generator and self.camera_id in self.entry_camera_ids:
                self.events.append(
                    self.event_generator.generate_exit_event(
                        session=session,
                        timestamp=self._timestamp_for_current_frame(),
                        confidence=0.9,
                    )
                )
        
        logger.info(f"Finalized {len(active)} active sessions")
    
    def _scale_zone_mapper_to_frame(
        self,
        frame_width: int,
        frame_height: int,
        ref_width: int = 800,
        ref_height: int = 600,
    ) -> None:
        """Scale zone polygons from config reference size to actual video resolution."""
        if self._zones_scaled or not self.zone_mapper:
            return
        sx = frame_width / ref_width
        sy = frame_height / ref_height
        scaled = {}
        for zone_id, polygon in self.zone_mapper.zones.items():
            scaled[zone_id] = [(x * sx, y * sy) for x, y in polygon]
        self.zone_mapper.zones = scaled
        self._zones_scaled = True
        logger.info(f"Scaled zones to {frame_width}x{frame_height} (sx={sx:.2f}, sy={sy:.2f})")

    def _save_events(self, output_path: str) -> None:
        """Save events to JSONL file."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w') as f:
                for event in self.events:
                    f.write(json.dumps(event.to_dict()) + '\n')
            
            logger.info(f"Saved {len(self.events)} events to {output_path}")
        except Exception as e:
            logger.error(f"Failed to save events: {e}")
            raise
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        stats = {
            "frame_count": self.frame_count,
            "processed_count": self.processed_count,
            "events_generated": len(self.events),
            "skip_rate": self.fps_sample_rate,
        }
        
        if self.detector:
            stats["detector"] = self.detector.get_device_info()
        
        if self.tracker:
            stats["tracker"] = self.tracker.get_stats()
        
        if self.session_manager:
            stats["sessions"] = self.session_manager.get_stats()
        
        return stats



def create_processor(
    detector: PersonDetector,
    tracker: MultiObjectTracker,
    reid_manager: Optional[ReIDManager] = None,
    zone_mapper: Optional[ZoneMapper] = None,
    session_manager: Optional[SessionManager] = None,
    event_generator: Optional[EventGenerator] = None,
    visitor_manager: Optional[VisitorStateManager] = None,
    **kwargs
) -> VideoProcessor:
    """
    Factory function to create VideoProcessor.
    
    Args:
        detector: PersonDetector instance
        tracker: MultiObjectTracker instance
        reid_manager: Optional ReIDManager
        zone_mapper: Optional ZoneMapper
        session_manager: Optional SessionManager
        event_generator: Optional EventGenerator
        visitor_manager: Optional legacy VisitorStateManager
        **kwargs: Additional arguments (fps_sample_rate, store_id, camera_id, etc.)
        
    Returns:
        Configured VideoProcessor instance
    """
    return VideoProcessor(
        detector=detector,
        tracker=tracker,
        reid_manager=reid_manager,
        zone_mapper=zone_mapper,
        session_manager=session_manager,
        event_generator=event_generator,
        visitor_manager=visitor_manager,
        **kwargs
    )


def run_cli() -> int:
    """Command-line entry: process one CCTV file into events JSONL."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Process Purplle CCTV footage (YOLO detect + track → events JSONL)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m detector.process_video --help
  python -m detector.process_video -v "CCTV Footage/CAM 1.mp4" -o output/cam1_events.jsonl
  python -m detector.process_video -v "CCTV Footage/CAM 1.mp4" -o output/cam1.jsonl \\
      --store-id ST1008 --camera-id CAM-1 --sample-rate 10

Process all Brigade cameras:
  python scripts/process_brigade_cctv.py
        """,
    )
    parser.add_argument(
        "-v", "--video",
        required=True,
        help="Path to input MP4 (e.g. CCTV Footage/CAM 1.mp4)",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="Output JSONL path (default: output/events/<video_stem>_events.jsonl)",
    )
    parser.add_argument("--store-id", default="ST1008", help="Store ID (Brigade Bangalore)")
    parser.add_argument("--camera-id", default="CAM-1", help="Camera ID label")
    parser.add_argument(
        "--camera-role",
        default="zone",
        choices=["entry", "zone", "billing"],
        help="Camera role — ENTRY/EXIT only emitted on entry cameras",
    )
    parser.add_argument(
        "--entry-camera-id",
        action="append",
        default=[],
        help="Additional entry camera IDs for footfall (repeatable)",
    )
    parser.add_argument(
        "--layout",
        default="config/zones.json",
        help="Zone layout JSON",
    )
    parser.add_argument(
        "--sample-rate",
        type=int,
        default=10,
        help="Process every Nth frame (higher = faster, less accurate)",
    )
    parser.add_argument(
        "--model",
        default="nano",
        choices=["nano", "small", "medium"],
        help="YOLOv8 model size",
    )
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="Disable progress bar",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.45,
        help="YOLO person detection confidence (default 0.45 — reduces blur false positives)",
    )
    parser.add_argument(
        "--min-hits",
        type=int,
        default=5,
        help="Tracker confirmations before emitting events (default 5)",
    )
    parser.add_argument(
        "--export-tracks",
        action="store_true",
        help="Export per-frame bbox JSON for live dashboard video overlay",
    )
    parser.add_argument(
        "--tracks-output",
        default=None,
        help="Track JSON path (default: output/tracks/<video>_tracks.json)",
    )

    args = parser.parse_args()

    video_path = Path(args.video)
    if not video_path.exists():
        print(f"Error: video not found: {video_path}")
        return 1

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = Path("output/events") / f"{video_path.stem}_events.jsonl"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    tracks_path = None
    if args.export_tracks:
        if args.tracks_output:
            tracks_path = Path(args.tracks_output)
        else:
            tracks_path = Path("output/tracks") / f"{video_path.stem.replace(' ', '_')}_tracks.json"
        tracks_path.parent.mkdir(parents=True, exist_ok=True)

    layout_path = Path(args.layout)
    if not layout_path.exists():
        print(f"Warning: layout not found at {layout_path}, continuing without zones")

    # Local imports for CLI (reliable when run as python -m detector.process_video)
    from detector.detector import create_detector as _create_detector
    from detector.tracker import create_tracker as _create_tracker
    from detector.zone_mapper import ZoneMapper as _ZoneMapper
    from detector.session_manager import SessionManager
    from detector.event_generator import EventGenerator

    print(f"Loading YOLO model ({args.model}) — first run may download weights...")
    detector = _create_detector(
        model_size=args.model,
        confidence_threshold=args.confidence,
    )
    tracker = _create_tracker(
        min_hits=args.min_hits,
        high_det_thresh=max(0.35, args.confidence),
        min_motion_pixels=12.0,
        max_age=20,
    )

    entry_ids = list(args.entry_camera_id)
    if args.camera_role == "entry" and args.camera_id not in entry_ids:
        entry_ids.append(args.camera_id)

    zone_mapper = None
    if layout_path.exists():
        try:
            zone_mapper = _ZoneMapper(str(layout_path))
            print(f"Loaded {len(zone_mapper.zones)} zones from {layout_path}")
        except Exception as exc:
            print(f"Warning: could not load zones ({exc}), continuing without zone mapping")

    session_manager = SessionManager(session_timeout_minutes=10)
    event_generator = EventGenerator(
        store_id=args.store_id,
        camera_id=args.camera_id,
    )

    processor = create_processor(
        detector=detector,
        tracker=tracker,
        zone_mapper=zone_mapper,
        session_manager=session_manager,
        event_generator=event_generator,
        fps_sample_rate=args.sample_rate,
        store_id=args.store_id,
        camera_id=args.camera_id,
        camera_role=args.camera_role,
        entry_camera_ids=entry_ids,
    )

    count, _events = processor.process_video(
        str(video_path),
        str(output_path),
        tracks_output=str(tracks_path) if tracks_path else None,
        show_progress=not args.no_progress,
    )
    print(
        f"Done: {count} events → {output_path}\n"
        f"  Detections (sampled frames): {processor.total_detections}\n"
        f"  Confirmed track frames: {processor.total_track_frames}"
    )
    if tracks_path:
        print(f"  Track overlay data → {tracks_path}")
    if count == 0 and processor.total_detections == 0:
        print(
            "  No people detected — try lower --confidence 0.2 or --sample-rate 5"
        )
    elif count == 0 and processor.total_track_frames == 0:
        print(
            "  People detected but no stable tracks — try --min-hits 1 or --sample-rate 5"
        )
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(run_cli())
