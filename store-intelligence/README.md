# Store Intelligence System - Production README

## Quick start (Purplle take-home)

```bash
git clone <repo> && cd store-intelligence
pip install -r requirements.txt
docker compose up -d --build    # API + Postgres + Redis (uses data/bootstrap events)
cd ../store-intelligence-dashboard && npm ci && npm run dev
```

**With local videos** (parent folder — not in git):

```bash
python scripts/process_stores.py --export-tracks
python scripts/backfill_entry_events.py
python scripts/sync_bootstrap_events.py
python -m uvicorn api.main:app --reload --port 8000
```

**Dataset paths (local):** `../Store 1/`, `../Store 2/`, `../POS - sample transactionsb1e826f.csv`, `../sample_eventsbe42122.jsonl`

**Store 2:** CCTV visitors/heatmap work from bootstrap events; POS revenue is 0 because the sample CSV has no `ST2002` rows.

**Submission event logs (after pipeline):**
- `output/submission_events.jsonl` — challenge/API schema
- `output/sample_format_events.jsonl` — matches `sample_eventsbe42122.jsonl` shape

**Dashboard:** `cd ../store-intelligence-dashboard && npm install && npm run dev` → http://localhost:5173

---

## Problem Statement

Retail chains need **real-time understanding of store operations** to optimize customer experience and maximize conversion. Current solutions rely on manual staff observations or expensive consultants. This system provides **AI-powered computer vision analytics** that automatically:

### Key Capabilities

- **Person Detection**: YOLOv8-based person detection with high accuracy
- **Multi-Object Tracking**: DeepSORT tracking for stable customer identity
- **Behavioral Events**: Structured events (entry, zone visits, dwell, queue join/abandon)
- **Real-Time Analytics**: Metrics, conversion funnels, zone heatmaps
- **Anomaly Detection**: Queue spikes, conversion drops, unusual behavior
- **REST APIs**: Production-grade FastAPI with full documentation
- **Containerized**: Docker Compose for easy deployment

---

## Architecture

### System Layers

```
CCTV Footage
    ↓
Frame Sampling (adaptive motion-based)
    ↓
YOLOv8 Detection (person detection)
    ↓
DeepSORT Tracking (stable track IDs)
    ↓
Zone Mapping (pixel → semantic zones)
    ↓
Event Generation (structured events)
    ↓
PostgreSQL (event storage + analytics)
    ↓
Redis (cache + pub/sub)
    ↓
FastAPI REST API
    ↓
React Dashboard / Third-party Integrations
```

### Technology Stack

- **Backend**: Python 3.11, FastAPI, SQLAlchemy
- **Database**: PostgreSQL 15 with asyncpg
- **Cache**: Redis 7
- **Detection**: YOLOv8 (Ultralytics)
- **Tracking**: DeepSORT
- **Containerization**: Docker, Docker Compose
- **Testing**: Pytest, pytest-asyncio
- **Logging**: Structured JSON logging

---

## Project Structure

```
store-intelligence/
├── configs/                    # Configuration & settings
│   ├── settings.py            # Pydantic Settings
│   └── logging_config.py      # Logging setup
├── storage/                   # Database layer
│   ├── database.py            # SQLAlchemy setup
│   ├── models.py              # ORM models
│   └── repositories/          # Repository pattern
├── api/                       # REST API
│   ├── main.py               # FastAPI app factory
│   ├── dependencies.py       # DI functions
│   ├── middleware.py         # Custom middleware
│   ├── routes/               # API routes (TBD)
│   ├── services/             # Business logic (TBD)
│   ├── schemas/              # Pydantic models
│   └── core/                 # Core utilities
├── detector/                 # Detection pipeline
│   ├── detector.py           # YOLOv8 detection
│   ├── tracker.py            # DeepSORT tracking
│   ├── reid.py               # Re-identification
│   ├── zone_mapper.py        # Zone mapping
│   ├── event_generator.py    # Event generation
│   └── process_video.py      # Video processing entry point
├── analytics/                # Analytics computation
│   ├── metrics.py            # Footfall, dwell metrics
│   ├── funnel.py             # Conversion funnel
│   ├── heatmap.py            # Zone heatmaps
│   └── anomalies.py          # Anomaly detection
├── tests/                    # Test suite
│   ├── unit/                 # Unit tests
│   ├── integration/          # Integration tests
│   └── fixtures/             # Test data
├── scripts/                  # Utility scripts
├── alembic/                  # Database migrations
├── docker-compose.yml        # Docker Compose config
├── Dockerfile                # API container
├── requirements.txt          # Python dependencies
├── .env.example             # Environment template
└── README.md                # This file
```

---

## Getting Started

### Prerequisites

- Docker & Docker Compose (recommended)
- OR: Python 3.11+, PostgreSQL 15, Redis 7

### Quick Start (Docker)

```bash
# Clone repository
git clone <repo_url>
cd store-intelligence

# Create environment file
cp .env.example .env

# Start services
docker-compose up --build

# Verify
curl http://localhost:8000/health
# Expected response: {"status": "healthy", ...}
```

### Manual Setup (Local)

```bash
# Create Python virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env

# Start PostgreSQL and Redis (ensure they're running)
# Then:
export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/store_intelligence
export REDIS_URL=redis://localhost:6379/0

# Initialize database
python -c "import asyncio; from storage import init_db; asyncio.run(init_db())"

# Start API
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Configuration

### Environment Variables

See `.env.example` for all available configuration options. Key variables:

```env
# Application
APP_ENV=development
LOG_LEVEL=INFO
DEBUG=true

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/store_intelligence
DATABASE_POOL_SIZE=20

# Redis
REDIS_URL=redis://localhost:6379/0

# API
API_PORT=8000
API_WORKERS=4

# Detection Pipeline
DETECTOR_MODEL_SIZE=nano
DETECTOR_CONFIDENCE_THRESHOLD=0.4

# Tracking
TRACKER_MAX_AGE=30
TRACKER_MIN_HITS=3

# Analytics
ANOMALY_DETECTION_ENABLED=true
ISOLATION_FOREST_CONTAMINATION=0.05
```

---

## Running Detection

The CCTV detection service processes video frames and generates events.

### Start Detector

```bash
# Development
python -m detector.process_video \
  --video-path /path/to/store_footage.mp4 \
  --store-id STORE_BLR_002 \
  --layout-path config/store_layout.json

# With Docker
docker run -v /data:/data store-intelligence:detector \
  --video-path /data/footage.mp4 \
  --store-id STORE_BLR_002
```

### Configuration

Edit `config/zones.json` to define store zones:

```json
{
  "zones": [
    {
      "id": "ENTRY",
      "polygon": [[0, 0], [100, 0], [100, 50], [0, 50]],
      "category": "ENTRY"
    },
    {
      "id": "SKINCARE",
      "polygon": [[100, 50], [200, 50], [200, 150], [100, 150]],
      "category": "DISPLAY"
    }
  ]
}
```

---

## Running Analytics

The FastAPI server provides REST endpoints for analytics.

### Start API Server

```bash
# Development (with hot reload)
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Production
gunicorn api.main:app -w 4 --bind 0.0.0.0:8000

# Docker
docker run -p 8000:8000 store-intelligence:api
```

### API Endpoints

**Event Ingestion:**
```bash
curl -X POST http://localhost:8000/api/analytics/events/ingest \
  -H "Content-Type: application/json" \
  -d '{
    "events": [
      {
        "event_id": "550e8400-e29b-41d4-a716-446655440000",
        "store_id": "STORE_BLR_002",
        "camera_id": "CAM_ENTRY_01",
        "visitor_id": "VIS_abc123",
        "event_type": "ENTRY",
        "timestamp": "2026-03-03T14:22:10Z",
        "zone_id": null,
        "dwell_ms": 0,
        "is_staff": false,
        "confidence": 0.95
      }
    ]
  }'
```

**Get Metrics:**
```bash
curl http://localhost:8000/api/analytics/stores/STORE_BLR_002/metrics
```

Response:
```json
{
  "success": true,
  "message": "Metrics computed",
  "unique_visitors": 150,
  "conversion_rate": 0.28,
  "average_dwell_time": 420,
  "queue_depth": 8,
  "revenue": 125000
}
```

**Get Funnel:**
```bash
curl http://localhost:8000/api/analytics/stores/STORE_BLR_002/funnel
```

**Get Heatmap:**
```bash
curl http://localhost:8000/api/analytics/stores/STORE_BLR_002/heatmap
```

**Get Anomalies:**
```bash
curl http://localhost:8000/api/analytics/stores/STORE_BLR_002/anomalies
```

**Health Check:**
```bash
curl http://localhost:8000/health
```

---

## Development Workflow

### Phase 1: Foundation (Complete)
- [x] Project structure
- [x] Configuration management (Pydantic Settings)
- [x] Database models (SQLAlchemy)
- [x] Repository pattern
- [x] FastAPI application setup
- [x] Docker containerization
- [x] Logging configuration

### Phase 2: Detection Pipeline (Next)
- [ ] YOLOv8 person detection
- [ ] DeepSORT multi-object tracking
- [ ] Zone polygon mapping
- [ ] Behavioral event generation
- [ ] Video processing entry point

### Phase 3: Analytics Engine (Next)
- [ ] Metrics computation (footfall, dwell)
- [ ] Funnel analysis
- [ ] Heatmap generation
- [ ] Anomaly detection (sigma-rules + Isolation Forest)

### Phase 4: REST API (Next)
- [ ] Metrics endpoints
- [ ] Events endpoints
- [ ] Anomalies endpoints
- [ ] WebSocket live feed

### Phase 5: Dashboard (Future)
- [ ] React frontend
- [ ] Real-time updates
- [ ] Zone heatmap visualization

---

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run specific test file
pytest tests/unit/test_models.py -v

# Run async tests
pytest tests/integration/ -v
```

---

## API Documentation

Once the API is running, visit:

- **Swagger UI**: http://localhost:8000/api/docs
- **ReDoc**: http://localhost:8000/api/redoc
- **OpenAPI JSON**: http://localhost:8000/api/openapi.json

### Health Endpoints

```bash
# Liveness probe (service is running)
curl http://localhost:8000/health

# Readiness probe (dependencies ready)
curl http://localhost:8000/ready
```

---

## Database

### Schema

The system uses PostgreSQL with the following core tables:

- **stores**: Physical retail locations
- **cameras**: CCTV cameras within stores
- **zones**: Semantic regions (aisles, checkout, etc.)
- **tracks**: Tracked persons during visits
- **visitors**: Unique customers with re-ID
- **events**: Behavioral events (entry, zone visit, dwell, etc.)
- **anomalies**: Detected operational anomalies

### Migrations

Generate migration after schema changes:

```bash
alembic revision --autogenerate -m "Add new field"
alembic upgrade head
```

---

## Logging

Logs are written to:
- **Console**: JSON or text format (configurable)
- **File**: `logs/app.log` with rotation

Structured logging includes:
- Timestamp (UTC)
- Log level
- Module and function name
- Request trace ID (for debugging)
- Custom fields (latency_ms, endpoint, etc.)

---

## Deployment

### Docker Compose (Development/Testing)

```bash
docker-compose up -d
docker-compose logs -f api
docker-compose down
```

### Kubernetes (Production - TBD)

Kubernetes manifests will be provided for production deployment with:
- Auto-scaling
- Resource limits
- Health checks
- Persistent volumes
- Network policies

---

## Monitoring

### Prometheus Metrics (TBD)

The system exposes Prometheus metrics at `/metrics`:

- `detector_frames_processed_total`
- `detector_inference_latency_seconds`
- `api_request_duration_seconds`
- `database_query_duration_seconds`
- `anomaly_alerts_total`

### Grafana Dashboards (TBD)

Pre-built dashboards for:
- System health
- Detection pipeline performance
- API latency
- Business metrics

---

## Troubleshooting

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose logs postgres

# Verify connection
psql postgresql://postgres:postgres@localhost:5432/store_intelligence

# Reset database (development only)
python -c "import asyncio; from storage import drop_db; asyncio.run(drop_db())"
```

### Redis Connection Issues

```bash
# Check Redis is running
docker-compose logs redis

# Test connection
redis-cli ping
# Expected: PONG
```

### API Not Responding

```bash
# Check API container
docker-compose logs api

# Verify port is not in use
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows
```

---

## Contributing

### Code Style

- Use `black` for formatting: `black .`
- Use `isort` for import sorting: `isort .`
- Use `flake8` for linting: `flake8 .`
- Use `mypy` for type checking: `mypy .`

### Testing

- Write tests for new features
- Maintain >70% code coverage
- Use pytest for unit and integration tests

---

## Performance

### Expected Metrics

- **Detection**: 10-20 fps (YOLOv8 nano on CPU)
- **API Response**: <100ms p99 for metrics endpoints
- **WebSocket Latency**: <500ms for live updates
- **Database Queries**: <50ms p99 for analytics

### Optimization Tips

- Batch events before writing to database
- Use Redis caching for frequently accessed metrics
- Implement connection pooling (done via SQLAlchemy)
- Monitor and tune database query performance

---

## License

Confidential - Purplle Tech Challenge 2026

---

## Support & Questions

For questions about this system, refer to:

1. **Inline Code Comments**: All modules have detailed docstrings
2. **Configuration Examples**: See `.env.example`
3. **Phase Documentation**: Check phase-specific READMEs in subdirectories

---

## Changelog

### v1.0.0 (Phase 1) - 2026-05-30
- Project initialization
- Configuration framework
- Database models and repositories
- FastAPI application scaffold
- Docker containerization
