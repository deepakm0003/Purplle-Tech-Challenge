# DESIGN.md - Architecture & Design Decisions

## AI-Assisted Decisions (detection robustness update)

An LLM suggested lowering YOLO confidence to 0.25 for recall on anonymised CCTV. **We overrode this** after observing false positives on face-blur patches and mirror reflections. The shipped pipeline uses:

- **confidence 0.45**, **min_hits 5**, **motion gate 12px** before track confirmation
- **Geometric filters** (`detector/detection_filters.py`): aspect ratio, min height, NMS dedup for mirror doubles
- **ENTRY/EXIT only on entry-role cameras** — zone/billing cameras emit zone events only (fixes inflated footfall)
- **Staff heuristics** post-pass via `StaffClassifier` on completed sessions

This reduced ghost boxes and stabilised track IDs without switching models (YOLOv8n remains the latency/accuracy trade-off for batch processing).

---

### 1.1 High-Level Data Flow

```
┌──────────────────────────────────────────────────────────────────┐
│                        CCTV INPUT                                 │
│                   (Multi-camera feeds)                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
    ┌──────────┐  ┌──────────┐  ┌──────────┐
    │ Entry    │  │Main Floor│  │ Billing  │
    │ Camera   │  │ Camera   │  │ Camera   │
    └────┬─────┘  └────┬─────┘  └────┬─────┘
         │             │             │
         └─────────────┼─────────────┘
                       │
                ┌──────▼──────┐
                │Frame Buffer │ (motion detection)
                └──────┬──────┘
                       │
        ┌──────────────▼──────────────┐
        │   YOLOv8 Detection          │
        │  (Person bounding boxes)    │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   ByteTrack Tracking        │
        │  (Stable track IDs)         │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   OSNet Re-Identification   │
        │  (Embedding generation)     │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │ Zone Mapping & Overlap      │
        │ (pixel coords → zones)      │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │ Event Generation            │
        │ (Entry, Zone, Dwell, Exit)  │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │ Staff Classification        │
        │ (Visitor vs Staff heuristics)
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │ Camera Fusion               │
        │ (Deduplication across       │
        │  multi-camera tracking)     │
        └──────────────┬──────────────┘
                       │
        ┌──────────────▼──────────────┐
        │ Event Storage (PostgreSQL)  │
        └──────────┬──────────────────┘
                   │
    ┌──────────────┼──────────────┬─────────────────┐
    ▼              ▼              ▼                 ▼
┌─────────┐ ┌───────────┐ ┌─────────┐ ┌────────────────┐
│Metrics  │ │Funnel     │ │Heatmap  │ │Anomalies       │
│Engine   │ │Engine     │ │Engine   │ │Detector        │
└────┬────┘ └─────┬─────┘ └────┬────┘ └────────┬───────┘
     │           │            │               │
     └───────────┼────────────┼───────────────┘
                 │            │
    ┌────────────▼────────────▼──────┐
    │ POS Integration                │
    │ (Transaction matching)         │
    └────────────┬───────────────────┘
                 │
    ┌────────────▼───────────────────┐
    │ Conversion Engine              │
    │ (Event-to-transaction matches) │
    └────────────┬───────────────────┘
                 │
    ┌────────────▼───────────────────┐
    │ Final Analytics Computation    │
    └────────────┬───────────────────┘
                 │
    ┌────────────▼───────────────────┐
    │ FastAPI REST Endpoints         │
    │ (/metrics, /funnel, /heatmap)  │
    └────────────┬───────────────────┘
                 │
    ┌────────────▼───────────────────┐
    │ React Dashboard               │
    │ (Live visualization)          │
    └───────────────────────────────┘
```

### 1.2 Component Layers

**Layer 1: Detection Pipeline**
- YOLOv8 for person detection
- ByteTrack for temporal tracking
- OSNet for re-identification embeddings
- Zone mapping for semantic localization

**Layer 2: Event Generation**
- Event creation from detection pipeline
- Behavioral event types (ENTRY, ZONE_ENTER, ZONE_EXIT, EXIT, DWELL)
- Session management for visitor lifecycle
- Staff classification for filtering

**Layer 3: Multi-Camera Fusion**
- Deduplication across camera streams
- Camera-aware visitor tracking
- Temporal-spatial matching for same visitor

**Layer 4: Business Analytics**
- Event aggregation and processing
- POS data integration (CSV ingestion)
- Transaction matching with confidence scoring
- Metrics, funnel, heatmap, anomaly computation

**Layer 5: Observability**
- Structured logging (loguru)
- Request tracing with trace IDs
- Latency tracking
- Error handling with RFC 7807 responses

**Layer 6: API & Presentation**
- FastAPI REST endpoints
- React + Vite dashboard
- Real-time updates via polling

---

## 2. Detection Pipeline

### 2.1 Person Detection (YOLOv8)

**Why YOLOv8:** 
- Real-time inference (30+ fps on GPU)
- High accuracy (AP 53.9% on COCO)
- Small model size (11.2M params for nano)
- Handles multiple persons well
- Easy fine-tuning

**Process:**
1. Frame sampling: Every Nth frame (adaptive based on motion)
2. YOLOv8 inference: Produces bounding boxes + confidence
3. Filtering: Keep detections with confidence > 0.4
4. Box format: (x_min, y_min, x_max, y_max, conf, class_id)

**Code Location:** `detector/detector.py`

### 2.2 Multi-Object Tracking (ByteTrack)

**Why ByteTrack:**
- Handles occlusions well
- Stable track IDs across frames
- Lower computational cost than DeepSORT
- Better performance on crowded scenes

**Algorithm:**
1. Frame t: Get detections from YOLOv8
2. High-confidence matches: Greedy assignment (IoU > 0.5)
3. Low-confidence matches: Use embeddings (cosine similarity)
4. Track age management: MAX_AGE=30, MIN_HITS=3
5. Output: Stable track_id for each person

**Code Location:** `detector/tracker.py`

### 2.3 Re-Identification (OSNet)

**Why OSNet:**
- Light-weight architecture (2.2M params)
- Fast inference (40ms on CPU)
- Good performance on retail scenarios
- Embeddings suitable for similarity matching

**Process:**
1. Extract person region (bounding box)
2. Normalize: Resize to 256x128
3. Forward pass through OSNet
4. Output: 512-dimensional embedding
5. Similarity: Cosine distance to other embeddings

**Use Cases:**
- Long-term track association
- Multi-camera person matching
- Staff identification (known embeddings)

**Code Location:** `detector/reid.py`

### 2.4 Zone Mapping

**Polygon-Based Mapping:**
- Zones defined as polygon points: [(x1,y1), (x2,y2), ...]
- Point-in-polygon test using ray casting
- Frame coordinates (pixels) → semantic zone_id

**Data Format (store_layout.json):**
```json
{
  "zones": [
    {
      "zone_id": "ENTRY",
      "polygon_points": [[0, 0], [100, 0], [100, 50], [0, 50]],
      "category": "ENTRY",
      "priority": 1
    }
  ]
}
```

**Event Generation:**
- ENTRY zone: First zone entered after detection start
- ZONE_ENTER: Crossing zone boundary (entering)
- ZONE_EXIT: Crossing zone boundary (exiting)
- ZONE_DWELL: Time spent in zone (dwell_ms)

**Code Location:** `detector/zone_mapper.py`, `detector/event_generator.py`

---

## 3. Event Schema

### 3.1 Core Event Structure

```python
class Event(BaseModel):
    event_id: str              # UUID for deduplication
    store_id: str              # Which store
    camera_id: str             # Which camera
    visitor_id: str            # Tracked person ID
    event_type: EventType      # ENTRY, ZONE_ENTER, etc.
    timestamp: datetime        # When event occurred (ISO-8601)
    zone_id: Optional[str]     # Which zone
    dwell_ms: int             # Time spent (for ZONE_EXIT)
    is_staff: bool            # Staff vs visitor classification
    confidence: float         # Detection confidence (0-1)
```

### 3.2 Event Types

```python
class EventType(str, Enum):
    ENTRY = "ENTRY"           # Person enters store
    ZONE_ENTER = "ZONE_ENTER"   # Person enters zone
    ZONE_EXIT = "ZONE_EXIT"     # Person exits zone
    ZONE_DWELL = "ZONE_DWELL"   # Dwell time record
    EXIT = "EXIT"              # Person exits store
    BILLING_QUEUE_JOIN = "BILLING_QUEUE_JOIN"
    BILLING_QUEUE_LEAVE = "BILLING_QUEUE_LEAVE"
```

### 3.3 Event Lifecycle Example

**Visitor journey:**
```
Frame 100: Person detected → ENTRY event (visitor_id = VIS_123)
Frame 115: Enters SKINCARE zone → ZONE_ENTER event
Frame 200: Exits SKINCARE zone (100 frames = 3.3s dwell) → ZONE_EXIT event (dwell_ms=3333)
Frame 300: Enters BILLING zone → ZONE_ENTER event
Frame 305: BILLING_QUEUE_JOIN event
Frame 350: BILLING_QUEUE_LEAVE event (purchase detected)
Frame 400: Exits store → EXIT event
```

---

## 4. Analytics Engine

### 4.1 Metrics Computation

**10 Core Metrics:**

1. **unique_visitors**: Count of distinct visitor_ids (staff filtered)
2. **conversion_rate**: (purchase_count / entry_count) * 100
3. **average_dwell_time**: Sum of all zone dwell / zone visits
4. **average_dwell_by_zone**: Dwell time for each zone
5. **queue_depth**: Current people in BILLING zone
6. **abandonment_rate**: (entered_billing - exited_billing) / entered_billing * 100
7. **revenue**: Sum of all POS transactions (staff filtered)
8. **average_basket_size**: revenue / purchase_count
9. **store_footfall**: unique_visitors
10. **zone_visit_frequency**: Visits per zone

**Implementation:** `analytics/metrics.py`
- Staff filtering: `is_staff=false` at query start
- Zero-division guards: Explicit checks before division
- Edge cases: Empty stores, no conversions, no dwell data

### 4.2 Conversion Funnel

**4-Stage Funnel:**

```
        ENTRY               ZONE VISIT              BILLING              PURCHASE
        (100%)              (45%)                   (20%)                 (12%)
┌─────────────────┐  ┌─────────────────┐  ┌──────────────┐  ┌─────────────────┐
│ Visitor enters  │→ │ Visits any zone │→ │Enters billing│→ │Makes purchase   │
│    store        │  │   (e.g., aisle) │  │    queue     │  │  (POS match)    │
└─────────────────┘  └─────────────────┘  └──────────────┘  └─────────────────┘
      Dropoff              Dropoff                Dropoff
      55%                  55.5%                  40%
```

**Dropoff Calculation:**
```
dropoff_% = ((count[i] - count[i+1]) / count[i]) * 100
```

**Efficiency:**
```
efficiency_% = (purchase_count / entry_count) * 100
```

**Implementation:** `analytics/funnel.py`
- No double-counting: Uses set intersection
- Handles multiple visitors
- Filters staff events

### 4.3 Zone Heatmap

**Heatmap Data:**
- Zone ID
- Visit frequency (count)
- Average dwell time
- Normalized heat score (0-100)
- Confidence level (HIGH/LOW)

**Normalization:**
```
normalized_score = (zone_visits / max_zone_visits) * 100
```

**Confidence:**
```
confidence = "HIGH" if session_count >= 20 else "LOW"
```

**Sorting:** By normalized_heat_score descending

**Implementation:** `analytics/heatmap.py`
- ZONE_EXIT events with dwell_ms
- Handles staff filtering
- Graceful handling of empty zones

### 4.4 Anomaly Detection

**3 Detection Types:**

1. **Queue Spike**
   - Condition: `current_queue > rolling_avg * 1.5`
   - Severity: CRITICAL if > 2.0x, WARNING if > 1.5x
   - Use: Real-time queue monitoring

2. **Conversion Drop**
   - Condition: `current_conversion < historical_baseline * (1 - 0.25)`
   - Severity: CRITICAL if > 50% drop, WARNING if > 25% drop
   - Use: Sales performance degradation alerts

3. **Dead Zone**
   - Condition: No ZONE_ENTER event for 30 minutes
   - Severity: INFO (low priority)
   - Use: Zone accessibility issues

**Implementation:** `analytics/anomalies.py`
- Thresholds configurable
- Severity classification
- Recovery suggestions in response
- Filters staff to prevent false positives

---

## 5. Multi-Camera Fusion

### 5.1 Deduplication Strategy

**Priority-based matching:**

1. **Direct visitor_id match (Primary)**
   - If visitor_id already exists in active tracks, add event to that track
   - Highest confidence
   - Used for same-camera continuity

2. **Temporal-Spatial Matching (Secondary)**
   - If different cameras see someone at same time in same zone
   - Condition: `time_diff < 5 min AND same_zone AND different_camera`
   - Fuses tracks into unified visitor identity
   - Medium confidence

3. **Embedding Similarity (Tertiary, Future)**
   - Cosine similarity of ReID embeddings
   - Threshold: 0.85
   - For long-term cross-camera tracking
   - Lower confidence but handles occlusions

**Example:** 
```
Entry Camera: VIS_001 enters ENTRY zone at 10:00
Main Camera: Someone enters SKINCARE zone at 10:02 (same visitor)
Fusion: Both events mapped to single visitor_id = VIS_001
```

**Implementation:** `analytics/camera_fusion.py`
- Active track management
- Closed track archive (for history queries)
- Visitor ID remapping
- Camera transition tracking

---

## 6. POS Integration & Conversion

### 6.1 Transaction Matching

**Business Rule:**
```
Match when:
  - Visitor entered BILLING zone (event_type = ZONE_ENTER)
  - Within 5-minute window (configurable)
  - Same store_id
  - Not already matched
```

**Matching Process:**
```
visitor_id=VIS_001, BILLING_QUEUE_JOIN at 10:30:00
↓
Find POS transactions for STORE_ID between 10:25:00 and 10:35:00
↓
Match to first unmatched transaction → Conversion!
↓
Record confidence score (based on time proximity)
```

**Confidence Scoring:**
```
confidence = 1.0 - (time_delta_seconds / window_seconds) * 0.4
Range: [0.5, 1.0]

Example:
- 0 seconds delta: confidence = 1.0
- 150 seconds delta: confidence = 0.7
- 300 seconds delta: confidence = 0.5
```

**Deduplication:**
- Matched transaction_ids stored in set
- Prevents double-counting same transaction

**Implementation:** `analytics/conversion_engine.py`
- CSV transaction loading (pos_processor.py)
- Matching with confidence
- Revenue aggregation

---

## 7. Staff Detection

### 7.1 Classification Heuristics

**Confidence Scoring (cumulative):**

1. **Whitelist** (+1.0)
   - Manual list of known staff
   - Example: ["EMP_001", "EMP_002"]

2. **Multiple Entries** (+0.3)
   - Visitor has > 5 entries
   - Suggests regular employee/staff

3. **Long Duration** (+0.4)
   - Total dwell > 120 minutes
   - Staff working long shifts

4. **Many Zones** (+0.2)
   - Visits > 3 distinct zones
   - Staff move around more than shoppers

5. **Billing Zone Frequent** (+0.15)
   - Frequent visits to billing zone + multiple entries
   - Checkout staff behavior

**Decision Rule:**
```
confidence = sum of heuristic scores
is_staff = confidence >= 0.7 (CONFIDENCE_THRESHOLD)
```

**Implementation:** `detector/staff_classifier.py`
- Patterns tracked per visitor_id
- Recalculated per batch of events
- Confidence scores returned

---

## 8. Store Layout

### 8.1 Layout JSON Format

```json
{
  "store_id": "STORE_BLR_002",
  "store_name": "Purplle Premium - Bangalore",
  "city": "Bangalore",
  "country": "India",
  "timezone": "Asia/Kolkata",
  "operating_hours": {
    "Monday": {"open": "10:00", "close": "21:00"},
    "Tuesday": {"open": "10:00", "close": "21:00"}
  },
  "cameras": [
    {
      "camera_id": "CAM_ENTRY_01",
      "location": "ENTRY",
      "position": {"x": 0, "y": 0, "z": 0},
      "resolution": {"width": 1920, "height": 1080},
      "fov_degrees": 90,
      "enabled": true
    }
  ],
  "zones": [
    {
      "zone_id": "ENTRY",
      "zone_name": "Entrance",
      "polygon_points": [[0, 0], [100, 0], [100, 50], [0, 50]],
      "category": "ENTRY",
      "priority": 1
    }
  ]
}
```

**Validation:**
- Unique camera_ids and zone_ids
- Valid polygon (≥3 points)
- Resolution > 0
- FOV 0-180°
- Operating hours valid

**Implementation:** `analytics/layout_parser.py`

---

## 9. Data Persistence

### 9.1 Database Schema

**Events Table:**
```sql
CREATE TABLE events (
  id BIGSERIAL PRIMARY KEY,
  event_id UUID NOT NULL UNIQUE,
  store_id VARCHAR(50) NOT NULL,
  camera_id VARCHAR(50) NOT NULL,
  visitor_id VARCHAR(50) NOT NULL,
  event_type VARCHAR(30) NOT NULL,
  timestamp TIMESTAMPTZ NOT NULL,
  zone_id VARCHAR(50),
  dwell_ms INT,
  is_staff BOOLEAN,
  confidence FLOAT,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  INDEX idx_event_id (event_id),
  INDEX idx_store_timestamp (store_id, timestamp),
  INDEX idx_visitor (visitor_id)
);
```

**Query Patterns:**
- Event insertion: Bulk insert (500 events/batch)
- Time range queries: `timestamp BETWEEN ? AND ?`
- Visitor queries: `visitor_id = ?`
- Staff filtering: `is_staff = FALSE`

### 9.2 API Response Caching

**Cache Strategy:**
- Redis key: `metrics:{store_id}:{date}` (TTL: 5 min)
- Cache invalidation: On new events
- Async refresh: Background task computes new metrics

---

## 10. API Design

### 10.1 Endpoint Design

**POST /api/analytics/events/ingest**
- Accepts batch of up to 500 events
- Returns 202 Accepted (async processing)
- Deduplication by event_id
- Partial success allowed

**GET /api/analytics/stores/{store_id}/metrics**
- Returns 10 core metrics
- Time-range filtering (optional)
- Staff-filtered results
- Response time: < 200ms (cached)

**GET /api/analytics/stores/{store_id}/funnel**
- 4-stage funnel data
- Dropoff percentages
- Efficiency score
- Time-range filtering

**GET /api/analytics/stores/{store_id}/heatmap**
- Zone visit frequency
- Dwell time per zone
- Confidence levels
- Sorted by heat score

**GET /api/analytics/stores/{store_id}/anomalies**
- Active anomalies
- Severity classification
- Recovery suggestions
- Detected timestamp

**GET /health**
- Service status
- Database connectivity
- Redis connectivity
- Last event timestamp
- Stale feed warning (if > 30 min)

### 10.2 Error Handling (RFC 7807)

All errors return structured responses:

```json
{
  "type": "https://api.error.store-intelligence/DATABASE_UNAVAILABLE",
  "title": "Database Unavailable",
  "status": 503,
  "detail": "The database service is currently unavailable",
  "instance": "/api/analytics/stores/STORE_001/metrics",
  "timestamp": "2026-03-03T14:22:10Z",
  "error_code": "DATABASE_UNAVAILABLE",
  "trace_id": "trk_12345678",
  "recovery_suggestions": [
    "Check database connectivity",
    "Retry request in 30 seconds"
  ]
}
```

---

## 11. Observability

### 11.1 Structured Logging

All logs include:
- Timestamp (UTC)
- Log level (DEBUG, INFO, WARNING, ERROR)
- Module name
- Function name
- Trace ID (for request correlation)
- Custom fields (latency_ms, store_id, etc.)

**Example:**
```json
{
  "timestamp": "2026-03-03T14:22:10.123Z",
  "level": "INFO",
  "module": "analytics.metrics",
  "message": "Metrics computed",
  "trace_id": "trk_12345678",
  "store_id": "STORE_BLR_002",
  "unique_visitors": 150,
  "latency_ms": 45
}
```

### 11.2 Tracing

Request tracing with trace IDs:
- Unique 8-character trace ID per request
- Propagated through all components
- Spans recorded for sub-operations
- Total latency tracked

**Example Trace:**
```
[TRACE trk_12345678] Started: compute_metrics
  [TRACE trk_12345678] Span load_pos_data: 12.5ms
  [TRACE trk_12345678] Span compute_funnel: 8.3ms
  [TRACE trk_12345678] Span detect_anomalies: 15.2ms
[TRACE trk_12345678] Ended: SUCCESS (45.2ms)
```

---

## 12. Future Enhancements

### 12.1 Real-Time Streaming

- RTSP camera integration
- WebSocket live feed
- Event streaming via Kafka
- Real-time dashboard updates

### 12.2 Advanced ML

- Transformer-based ReID
- Crowd counting
- Behavior anomaly (unusual movement patterns)
- Customer demographic estimation

### 12.3 Multi-Store

- Cross-store visitor tracking
- Aggregate dashboards
- Store benchmarking
- Comparative analytics

### 12.4 Predictive Analytics

- Conversion forecasting
- Queue depth prediction
- Optimal staffing recommendations
- Customer lifetime value estimation

---

## 13. Performance Considerations

### 13.1 Scalability Targets

- **Detection:** 30 fps per camera (GPU-accelerated)
- **Event ingestion:** 1000 events/sec throughput
- **API latency:** p95 < 500ms
- **Storage:** ~10MB per 8-hour store day
- **Concurrent users:** 100+ dashboard viewers

### 13.2 Optimization Strategies

- Event batching (500 events/batch)
- Redis caching for frequent queries
- Database connection pooling
- Async event processing
- Lazy loading of analytics

---

## 14. Security Considerations

### 14.1 Data Privacy

- Events stored in encrypted database
- No PII in logs (only visitor_id hash)
- GDPR-compliant data retention (30-day default)
- Role-based access control (dashboard - future)

### 14.2 API Security

- Rate limiting per IP
- Input validation (Pydantic)
- SQL injection protection (SQLAlchemy ORM)
- CORS configured

---

## Document Version

**Version:** 1.0.0  
**Last Updated:** June 1, 2026  
**Status:** Production Ready

This design document reflects the complete architecture and design decisions for the Store Intelligence System Phase 3 (Business Intelligence Layer). For implementation details, see code comments and docstrings.
