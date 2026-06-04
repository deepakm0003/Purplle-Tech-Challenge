# Phase 2: Detection and Tracking Layer

Complete production-grade implementation of person detection, multi-object tracking, and visitor state management for retail CCTV analytics.

## Overview

Phase 2 delivers a fully integrated detection and tracking pipeline featuring:
- **YOLOv8-based person detection** with support for multiple model sizes (nano to xlarge)
- **ByteTrack multi-object tracking** with IoU-based matching and occlusion handling
- **Thread-safe visitor session management** with zone tracking and dwell time calculation
- **Complete video processing pipeline** with JSONL event generation
- **Comprehensive test coverage** (60+ test cases, 70%+ code coverage)

## Architecture

### Component Diagram

```
Video Input
    ↓
[VideoProcessor]
    ↓
┌─────────────────────────────────┐
│  Frame Processing Pipeline      │
├─────────────────────────────────┤
│  PersonDetector (YOLOv8)        │ → Bounding boxes
├─────────────────────────────────┤
│  MultiObjectTracker (ByteTrack) │ → Track IDs
├─────────────────────────────────┤
│  VisitorStateManager            │ → Visitor Sessions
├─────────────────────────────────┤
│  Event Generator                │ → ENTRY/EXIT Events
└─────────────────────────────────┘
    ↓
JSONL Output (Events)
```

## Core Modules

### 1. PersonDetector (detector/detector.py)

**Purpose**: Real-time person detection using YOLOv8

**Key Features**:
- Model sizes: nano, small, medium, large, xlarge
- Device support: CPU, GPU (CUDA/MPS), auto-detection
- Half-precision inference for memory efficiency
- Configurable confidence threshold
- Batch processing support

**Usage**:
```python
from detector import PersonDetector, create_detector

# Initialize detector
detector = create_detector(model_size="small", device="auto", confidence_threshold=0.5)

# Detect persons in frame
detections = detector.detect(frame)  # Returns List[Detection]

# Batch processing
batch_detections = detector.batch_detect(frames)
```

**Detection Format**:
```python
@dataclass
class Detection:
    bbox: List[float]  # [x1, y1, x2, y2] - pixel coordinates
    confidence: float  # 0.0 - 1.0
    class_id: int      # Always 0 for person (YOLOv8)
```

### 2. MultiObjectTracker (detector/tracker.py)

**Purpose**: Multi-object tracking with IoU-based matching

**Key Features**:
- ByteTrack algorithm implementation
- IoU (Intersection-over-Union) based detection-track association
- Track lifecycle management: Tentative → Confirmed → Deleted
- Occlusion handling with track recovery
- Configurable age and hit thresholds

**Usage**:
```python
from detector import MultiObjectTracker, create_tracker

# Initialize tracker
tracker = create_tracker(max_age=30, min_hits=3, iou_threshold=0.3)

# Update with detections
tracks = tracker.update(detections)  # Returns confirmed tracks only

# Get all tracks (including tentative)
all_tracks = tracker.get_all_tracks()

# Get statistics
stats = tracker.get_stats()
```

**Track Format**:
```python
@dataclass
class Track:
    track_id: int           # Unique identifier
    bbox: List[float]       # Current bounding box
    confidence: float       # Detection confidence
    age: int                # Frames since creation
    hits: int               # Confirmed detections
    state: str              # "tentative", "confirmed", "deleted"
    trajectory: List        # Historical bboxes
```

### 3. VisitorStateManager (detector/visitor_state.py)

**Purpose**: Thread-safe visitor session management with zone tracking

**Key Features**:
- Session creation/update/end lifecycle
- Zone entry/exit tracking
- Dwell time accumulation per zone
- Automatic session timeout cleanup
- Thread-safe with RLock protection
- Visitor ID generation and session tracking

**Usage**:
```python
from detector import VisitorStateManager, create_visitor_manager

# Initialize manager
manager = create_visitor_manager(session_timeout=300)

# Create session when track is detected
session = manager.create_session(track_id=1, current_frame=0)

# Update with zone information
manager.update_session(track_id=1, current_frame=100, zone_id=5)

# End session when track disappears
manager.end_session(track_id=1, current_frame=200)

# Get statistics
stats = manager.get_stats()
```

**Session Format**:
```python
@dataclass
class VisitorSession:
    visitor_id: str              # Unique visitor identifier
    session_id: str              # Unique session identifier
    track_id: int                # Associated track ID
    first_seen_frame: int        # Frame where detected first
    last_seen_frame: int         # Frame where detected last
    zones_visited: Set[int]      # Set of zone IDs visited
    zone_entry_frames: Dict      # Frame numbers of zone entries
    dwell_times: Dict[int, int]  # Zone ID → dwell frames
    current_zone: Optional[int]  # Current zone ID
    entry_count: int             # Number of zone entries
    active: bool                 # Session active status
```

### 4. VideoProcessor (detector/process_video.py)

**Purpose**: End-to-end video processing pipeline

**Key Features**:
- Complete frame-by-frame pipeline orchestration
- Configurable frame sampling (process every N frames)
- Optional zone mapping for spatial analysis
- JSONL event output with comprehensive metadata
- Progress tracking with tqdm
- Structured logging

**Usage**:
```python
from detector import VideoProcessor, create_processor

# Initialize components
detector = create_detector()
tracker = create_tracker()
visitor_manager = create_visitor_manager()

# Create processor
def zone_mapper(center_x, center_y):
    """Map pixel coordinates to store zone ID"""
    if center_x < 320:
        return 1  # Zone 1: Left side
    else:
        return 2  # Zone 2: Right side

processor = create_processor(
    detector=detector,
    tracker=tracker,
    visitor_manager=visitor_manager,
    fps_sample_rate=5,
    zone_mapper=zone_mapper,
    store_id="STORE-001",
    camera_id="CAM-001"
)

# Process video
event_count, events = processor.process_video(
    video_path="input.mp4",
    output_path="events.jsonl",
    show_progress=True
)

# Get statistics
stats = processor.get_stats()
```

**Event Format** (JSONL):
```json
{
  "event_id": "550e8400-e29b-41d4-a716-446655440000",
  "event_type": "ENTRY",
  "visitor_id": "v_1234567890",
  "session_id": "s_0987654321",
  "track_id": 1,
  "store_id": "STORE-001",
  "camera_id": "CAM-001",
  "timestamp": "2024-01-15T10:30:45.123456",
  "frame_number": 150,
  "zone_id": 1
}
```

## Test Suite

### Test Organization

```
tests/
├── unit/
│   ├── test_detector.py           (15 test cases)
│   ├── test_tracker.py            (20 test cases)
│   └── test_visitor_state.py      (16 test cases)
└── integration/
    └── test_video_processor.py    (11 test cases)
```

### Test Coverage

- **Detection Module**: Initialization, validation, batch processing, device handling
- **Tracking Module**: IoU computation, track matching, lifecycle management, statistics
- **Visitor State**: Session management, zone transitions, cleanup, thread-safety
- **Video Processing**: End-to-end pipeline, event generation, JSONL output

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_detector.py -v

# Run with coverage report
pytest tests/ --cov=detector --cov-report=html

# Run specific test class
pytest tests/unit/test_tracker.py::TestMultiObjectTracker -v

# Run with specific markers
pytest tests/ -m "not slow" -v
```

## Dependencies

### Core Dependencies
- **ultralytics==8.1.15**: YOLOv8 detection
- **torch==2.2.1, torchvision==0.17.1**: PyTorch deep learning framework
- **boxmot==10.8.27**: Tracker utilities
- **filterpy==1.4.2**: Filtering algorithms
- **opencv-python==4.8.1**: Video processing
- **numpy==1.24.3**: Numerical computing
- **Pillow==10.2.0**: Image processing

### Development Dependencies
- **pytest==7.4.3**: Testing framework
- **pytest-cov==4.1.0**: Coverage reporting
- **tqdm==4.66.2**: Progress bars

## Configuration

### Model Sizes

| Size    | Parameters | Inference Speed (CPU) |
|---------|------------|----------------------|
| nano    | 2.6M       | ~5ms                |
| small   | 11.2M      | ~15ms               |
| medium  | 40.2M      | ~40ms               |
| large   | 108.2M     | ~100ms              |
| xlarge  | 161.0M     | ~150ms              |

### Tracker Parameters

- **max_age**: Frames to keep track without detection (default: 30)
- **min_hits**: Detections required to confirm track (default: 3)
- **iou_threshold**: IoU threshold for matching (default: 0.3)
- **high_det_thresh**: High confidence detection threshold (default: 0.5)
- **low_det_thresh**: Low confidence recovery threshold (default: 0.1)

### Session Timeout

- **session_timeout**: Frames before session marked inactive (default: 300)

## Performance Considerations

### Memory Usage

- **Model Selection**: Nano (~50MB) vs Large (~400MB)
- **Batch Size**: Process multiple frames simultaneously for efficiency
- **Device**: GPU VRAM vs CPU RAM (GPU typically 2-4x faster)

### Processing Speed

```
Example on RTX 3070:
- YOLOv8 Small: ~150 FPS (640x480 frames)
- Tracking: ~1000 FPS (negligible overhead)
- Full pipeline: ~120 FPS per sampled frame
```

## Error Handling

### Common Issues and Solutions

1. **CUDA out of memory**
   - Reduce model size: `create_detector(model_size="nano")`
   - Use CPU: `create_detector(device="cpu")`
   - Reduce batch size

2. **Video file not found**
   - Verify file path exists
   - Check file permissions
   - Ensure valid video format (mp4, avi, mov)

3. **No detections**
   - Lower confidence threshold: `create_detector(confidence_threshold=0.3)`
   - Check video quality and lighting
   - Verify frame resolution is adequate

## Examples

### Basic Detection Only

```python
from detector import create_detector

detector = create_detector(model_size="small", device="auto")

detections = detector.detect(frame)
for det in detections:
    x1, y1, x2, y2 = det.bbox
    print(f"Person detected: ({x1},{y1}) - ({x2},{y2}), confidence: {det.confidence:.2f}")
```

### Complete Pipeline with Zone Mapping

```python
from detector import create_detector, create_tracker, create_visitor_manager, create_processor

def store_zone_mapper(x, y):
    """Map detection center to store zone"""
    if y < 240:  # Top half
        return 1 if x < 320 else 2
    else:  # Bottom half
        return 3 if x < 320 else 4

detector = create_detector(model_size="small", device="auto")
tracker = create_tracker()
visitor_manager = create_visitor_manager()

processor = create_processor(
    detector=detector,
    tracker=tracker,
    visitor_manager=visitor_manager,
    fps_sample_rate=5,
    zone_mapper=store_zone_mapper,
    store_id="STORE-001",
    camera_id="CAM-A1"
)

event_count, events = processor.process_video(
    video_path="store_footage.mp4",
    output_path="events.jsonl"
)

print(f"Generated {event_count} events")
```

## Logging

All modules use Python's standard logging with structured fields:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("detector")

# Log includes extra fields for debugging:
# frame_id, detections, tracks, zones_visited, duration_frames, etc.
```

## Production Deployment

### Recommended Configuration

```python
# High accuracy, moderate speed
detector = create_detector(model_size="medium", device="cuda")
tracker = create_tracker(max_age=30, min_hits=3)
visitor_manager = create_visitor_manager(session_timeout=600)

# Process at reasonable frame rate
processor = create_processor(
    detector=detector,
    tracker=tracker,
    visitor_manager=visitor_manager,
    fps_sample_rate=5,  # Process every 5th frame at 30fps = 6 FPS effective
    store_id="PRODUCTION_STORE",
    camera_id="MAIN_CAM"
)
```

### Database Integration (Phase 3)

Events can be persisted to PostgreSQL via SQLAlchemy models (see Phase 1 foundation).

## Future Enhancements

- **Phase 3**: Database persistence and REST API
- **Phase 4**: Real-time streaming and WebSocket events
- **Phase 5**: Advanced analytics (heatmaps, dwell patterns, crowd detection)
- **Phase 6**: Multi-camera synchronization and cross-zone tracking
