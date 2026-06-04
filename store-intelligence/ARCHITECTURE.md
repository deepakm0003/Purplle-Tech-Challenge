# Store Intelligence System - Architecture

## System Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    STORE INTELLIGENCE SYSTEM                     │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  LAYER 1: Ingestion                                             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ CCTV Footage → Frame Sampler → Raw Frame Queue          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ↓                                     │
│  LAYER 2: Detection & Tracking                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ YOLOv8 Detection → DeepSORT Tracking → Event Bus        │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ↓                                     │
│  LAYER 3: Event Streaming                                       │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ Kafka Topics: detections, tracking, zones, anomalies   │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ↓                                     │
│  LAYER 4: Analytics & Storage                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ PostgreSQL (events, tracks) | Redis (cache, pub/sub)   │    │
│  │ Metrics, Funnels, Heatmaps, Anomaly Detection          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ↓                                     │
│  LAYER 5: REST API                                              │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ FastAPI: /metrics, /events, /anomalies, /health        │    │
│  │ WebSocket: /live (real-time dashboard feed)            │    │
│  └─────────────────────────────────────────────────────────┘    │
│                            ↓                                     │
│  LAYER 6: Consumption                                           │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ React Dashboard | Third-party Integrations             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Detection Pipeline (`detector/`)

**YOLOv8 Person Detection**
- Detects people in video frames
- Filters to class 0 (person) only
- Confidence threshold: 0.4 (configurable)
- Model sizes: nano (CPU), small, medium, large

**DeepSORT Multi-Object Tracking**
- Maintains stable track IDs across frames
- Uses Kalman filter + appearance embeddings
- Handles occlusion and re-detection
- Track lifecycle: confirm → active → inactive → deleted

**Zone Mapping**
- Polygon-based zone definitions (JSON config)
- Point-in-polygon test for zone assignment
- Semantic zones: Entry, Skincare, Makeup, Haircare, Checkout

**Event Generation**
- Converts tracking data to structured events
- Event types: ENTRY, EXIT, ZONE_ENTER, ZONE_EXIT, ZONE_DWELL, etc.
- Self-describing JSON with versioning
- Idempotent for replay capability

### 2. Storage Layer (`storage/`)

**Database Models (SQLAlchemy)**

```
Store ──┬── Camera
        ├── Zone
        ├── Track ──┬── Event
        │           └── Visitor
        ├── Visitor
        ├── Event
        └── Anomaly
```

**Key Entities:**
- `Store`: Physical retail location
- `Camera`: CCTV camera with zone coverage
- `Zone`: Semantic region (aisle, checkout)
- `Track`: Person tracked during visit
- `Visitor`: Unique customer (re-ID token)
- `Event`: Behavioral event (entry, dwell, etc.)
- `Anomaly`: Detected operational anomaly

**Repository Pattern**
- `BaseRepository`: Generic CRUD operations
- Specific repositories: EventRepository, StoreRepository, etc.
- Async/await throughout for non-blocking I/O

### 3. Analytics Engine (`analytics/`)

**Real-time Metrics**
- Unique visitor count
- Average dwell time per zone
- Conversion rate (visitors → purchases)
- Queue depth tracking

**Funnel Analysis**
- Entry → Zone Visit → Billing Queue → Purchase
- Drop-off percentages at each stage
- Session-level deduplication

**Heatmap Generation**
- Zone visit frequency (0-100 normalized)
- Color-coded for visualization
- Updates every 10 seconds

**Anomaly Detection**
- Sigma-rules for statistical anomalies (low latency)
- Isolation Forest for pattern anomalies (batch mode)
- Types: Queue Spike, Conversion Drop, Dead Zone, Long Dwell, Crowd Spike

### 4. REST API Layer (`api/`)

**FastAPI Application**
- Type-safe Pydantic models
- Auto-generated OpenAPI documentation
- Structured error responses
- Request tracing (X-Request-ID header)

**Middleware**
- CORS support
- Request/response logging
- Latency tracking

**Endpoints** (Phase 2 & 3)
- GET `/v1/metrics/footfall` - Visitor counts
- GET `/v1/metrics/dwell` - Zone dwell times
- GET `/v1/metrics/heatmap` - Zone visit frequency
- GET `/v1/metrics/queue` - Queue depth
- GET `/v1/events` - Event log (paginated)
- GET `/v1/anomalies` - Anomaly list
- POST `/v1/anomalies/{id}/ack` - Acknowledge anomaly
- GET `/v1/tracks/{id}/path` - Visitor journey
- GET `/v1/health` - Liveness check
- WS `/v1/live` - WebSocket feed

### 5. Dashboard (Phase 5)

React frontend with:
- Real-time metrics (via WebSocket)
- Zone heatmap visualization
- Dwell time tables
- Anomaly alert feed
- Responsive design

## Data Flow

### Detection Flow

```
Video Frame
    ↓
YOLOv8 Detection
    ↓
DeepSORT Tracking
    ↓
Zone Mapper
    ↓
Event Generator
    ↓
Structured Event (JSON)
    ↓
Database + Kafka
```

### Analytics Flow

```
Events in Database
    ↓
Metrics Computation (footfall, dwell, conversion)
    ↓
Funnel Analysis (stage-based drop-off)
    ↓
Heatmap Generation (zone frequency)
    ↓
Anomaly Detection (sigma-rules, Isolation Forest)
    ↓
Redis Cache (for API responses)
    ↓
REST API / WebSocket
```

## Deployment Architecture

### Development (Docker Compose)

```
Host Machine
│
├─ postgres:5432 (PostgreSQL)
├─ redis:6379 (Redis)
├─ api:8000 (FastAPI)
└─ detector (Video processor)
```

### Production (Kubernetes)

```
Kubernetes Cluster
│
├─ PostgreSQL StatefulSet
├─ Redis StatefulSet
├─ FastAPI Deployment (replicas: 3)
├─ Detector DaemonSet (1 per node)
└─ Ingress (nginx-ingress-controller)
```

## Performance Characteristics

| Component | Metric | Target |
|-----------|--------|--------|
| Detection | FPS | 10-20 (CPU) |
| Tracking | Latency | <50ms/frame |
| Event Gen | Latency | <5ms/event |
| API Metrics | Latency p99 | <100ms |
| API Events | Latency p99 | <200ms |
| WebSocket | Latency | <500ms |
| DB Queries | Latency p99 | <50ms |

## Scalability Considerations

### Horizontal Scaling

- **Detection**: Frame sampler distributes work; GPU cluster for large deployments
- **API**: Load balance FastAPI instances; state in Redis
- **Database**: PostgreSQL replication (read replicas for analytics)
- **Redis**: Redis Cluster for high availability

### Data Retention

- **Events**: 7 days (archive older data)
- **Tracks**: 7 days
- **Anomalies**: 30 days
- **Metrics**: 2 years (aggregated hourly)

## Monitoring & Observability

### Prometheus Metrics

- `detector_frames_processed_total`
- `detector_inference_latency_seconds`
- `api_request_duration_seconds`
- `db_query_duration_seconds`

### Structured Logging

JSON logs with fields:
- `timestamp`, `level`, `logger`, `message`
- `trace_id` (request ID)
- `latency_ms` (for requests)
- Custom fields per service

### Health Checks

- Liveness: `/health` - service running?
- Readiness: `/ready` - dependencies available?

## Security

### Authentication (Phase TBD)

- JWT tokens for API
- API key fallback
- Rate limiting (100 req/min per key)

### Data Privacy

- Face blur in CCTV (anonymization)
- No PII in events
- No customer data beyond visit patterns

### Database Security

- Connection pooling (no connection leak)
- SQL injection protection (parameterized queries)
- Row-level security (store isolation)

## Error Handling & Resilience

### Failure Scenarios

| Scenario | Mitigation |
|----------|-----------|
| Detection timeout | Skip frame, count in metrics |
| DB connection loss | Retry with exponential backoff |
| Kafka producer failure | Dead-letter queue (SQLite) |
| WebSocket disconnect | Graceful cleanup, reconnect handling |

### Circuit Breaker Pattern

- Trip after 5 consecutive failures
- Half-open state: test single request
- Recovery: exponential backoff

## Future Enhancements

- [ ] Kafka streaming (replace direct DB writes)
- [ ] Distributed tracing (Jaeger)
- [ ] GraphQL API (in addition to REST)
- [ ] Multi-camera tracking (person re-ID across cameras)
- [ ] Staff detection (uniform recognition)
- [ ] Re-entry detection (same customer, new visit)
- [ ] Product recognition (what are they picking up?)
- [ ] Staff-customer interaction tracking
- [ ] Mobile app for store managers
- [ ] Advanced anomaly detection (fraud, theft patterns)
