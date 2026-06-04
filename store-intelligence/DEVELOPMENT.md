# Development Guide

## Local Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL 15 (or Docker)
- Redis 7 (or Docker)
- Git

### Step 1: Clone Repository

```bash
git clone <repo_url>
cd store-intelligence
```

### Step 2: Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Install production dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-asyncio pytest-cov black isort flake8 mypy
```

### Step 4: Environment Configuration

```bash
# Copy example to actual .env
cp .env.example .env

# Edit .env with your local database credentials
nano .env
```

### Step 5: Start Database Services

**Option A: Docker Compose**

```bash
docker-compose up -d postgres redis
```

**Option B: Homebrew (macOS)**

```bash
brew install postgresql redis
brew services start postgresql
brew services start redis
```

**Option C: Manual Installation**

Follow PostgreSQL and Redis official documentation.

### Step 6: Initialize Database

```bash
python -c "import asyncio; from storage import init_db; asyncio.run(init_db())"
```

### Step 7: Run Development Server

```bash
# With auto-reload
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Or use make command
make dev
```

Visit http://localhost:8000/health to verify.

---

## Project Conventions

### Code Style

**Formatting** (Black)
```bash
black .
```

**Import Sorting** (isort)
```bash
isort .
```

**Linting** (Flake8)
```bash
flake8 . --max-line-length=100
```

**Type Checking** (Mypy)
```bash
mypy . --ignore-missing-imports
```

**All-in-one:**
```bash
make format && make lint
```

### File Structure

Each module should have:
- `__init__.py` with `__all__` exports
- Docstrings for all public functions/classes
- Type hints throughout
- Inline comments for complex logic

Example:

```python
"""Module docstring explaining purpose."""

from typing import Optional, List
import logging

logger = logging.getLogger(__name__)

__all__ = ["MyClass", "my_function"]


class MyClass:
    """Class docstring."""
    
    def method(self, param: str) -> Optional[str]:
        """
        Method docstring.
        
        Args:
            param: Parameter description
            
        Returns:
            Return value description
        """
        return param


async def my_function(value: int) -> List[int]:
    """
    Function docstring.
    
    Args:
        value: Parameter description
        
    Returns:
        Return value description
    """
    return [value] * 3
```

### Logging

Use structured logging with context:

```python
import logging

logger = logging.getLogger(__name__)

# Info level
logger.info("Operation completed", extra={"user_id": "123", "duration_ms": 150})

# Warning level
logger.warning("Unusual behavior detected", extra={"anomaly_type": "queue_spike"})

# Error level with exception
try:
    risky_operation()
except Exception as e:
    logger.error("Operation failed", exc_info=True)
```

### Async/Await

All I/O operations must be async:

```python
async def get_user(user_id: str):
    """Get user from database."""
    async with get_db_session() as session:
        user = await session.get(User, user_id)
        return user

# Don't do this:
def get_user_sync(user_id: str):
    session = SessionLocal()
    user = session.query(User).get(user_id)
    return user
```

### Database Operations

Always use repository pattern:

```python
# Correct:
from storage import EventRepository

async def list_events(session):
    repo = EventRepository(session)
    events = await repo.get_by_store_id(store_id)
    return events

# Don't query directly:
result = await session.execute(select(Event))
```

### Error Handling

Use custom exceptions:

```python
from api.core import NotFoundError, ValidationError

async def get_store(store_id: str, session):
    from storage import StoreRepository
    
    repo = StoreRepository(session)
    store = await repo.get_by_store_id(store_id)
    
    if not store:
        raise NotFoundError(f"Store {store_id} not found")
    
    return store
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# With coverage report
pytest --cov=. --cov-report=html

# Specific file
pytest tests/unit/test_models.py -v

# Specific test
pytest tests/unit/test_models.py::test_store_creation -v

# Run only unit tests (skip integration)
pytest -m "not integration"
```

### Writing Unit Tests

```python
# tests/unit/test_detector.py

import pytest
from detector import PersonDetector

@pytest.fixture
def detector():
    return PersonDetector(model_size="nano")

def test_detector_initialization(detector):
    assert detector.model_size == "nano"

@pytest.mark.asyncio
async def test_detect_persons(detector):
    # Mock frame data
    frame = None  # Replace with actual test frame
    
    detections = await detector.detect_persons(frame)
    assert isinstance(detections, list)
```

### Writing Integration Tests

```python
# tests/integration/test_api.py

import pytest
from fastapi.testclient import TestClient
from api.main import app

@pytest.fixture
def client():
    return TestClient(app)

def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

@pytest.mark.asyncio
async def test_create_store(client, sample_store_data):
    response = client.post("/v1/stores", json=sample_store_data)
    assert response.status_code == 201
```

### Test Coverage

Aim for >70% coverage:

```bash
pytest --cov=. --cov-report=html --cov-fail-under=70
```

Review coverage in `htmlcov/index.html`.

---

## Debugging

### Print Debugging

```python
# Add logging statements
logger.debug(f"Variable value: {variable}")
```

### Interactive Debugging

```python
# Use pdb for breakpoints
import pdb; pdb.set_trace()

# Or pytest with pdb on failure
pytest --pdb
```

### Debugging Async Code

```python
import asyncio

async def main():
    # Your code here
    pass

# Run with asyncio debug enabled
asyncio.run(main(), debug=True)
```

---

## Common Tasks

### Add a New Endpoint

1. Create route in `api/routes/new_route.py`
2. Define Pydantic schemas in `api/schemas/`
3. Implement service logic in `api/services/`
4. Test with pytest
5. Document in README

### Add a Database Migration

1. Modify `storage/models.py`
2. Run migration generation:
   ```bash
   alembic revision --autogenerate -m "Add new field"
   ```
3. Review generated migration in `alembic/versions/`
4. Apply migration:
   ```bash
   alembic upgrade head
   ```

### Add a New Configuration Variable

1. Add to `configs/settings.py` with type hints
2. Add to `.env.example`
3. Add to `.env` for development
4. Use via `get_settings()`

```python
from configs import get_settings

settings = get_settings()
value = settings.new_config_variable
```

### Run a Custom Script

```bash
# Create script in scripts/
# scripts/seed_data.py

import asyncio
from storage import init_db, get_db_session

async def main():
    await init_db()
    async for session in get_db_session():
        # Your code here
        pass

if __name__ == "__main__":
    asyncio.run(main())

# Run it
python scripts/seed_data.py
```

---

## Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000  # macOS/Linux
netstat -ano | findstr :8000  # Windows

# Kill process
kill -9 <PID>
```

### Database Connection Error

```bash
# Verify PostgreSQL is running
psql -U postgres -d store_intelligence

# Check connection string in .env
echo $DATABASE_URL
```

### Redis Connection Error

```bash
# Test Redis connection
redis-cli ping
# Expected: PONG
```

### Import Errors

```bash
# Ensure virtual environment is activated
which python  # Should be in venv/

# Reinstall packages
pip install -r requirements.txt --force-reinstall
```

---

## IDE Setup

### VS Code

**Extensions:**
- Python
- Pylance
- Black Formatter
- Flake8
- isort
- Pytest Explorer

**Settings** (`.vscode/settings.json`):

```json
{
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.formatOnSave": true,
    "editor.defaultFormatter": "ms-python.python"
  },
  "python.testing.pytestEnabled": true,
  "python.testing.pytestArgs": ["tests"]
}
```

### PyCharm

- Mark `src/` as Sources Root
- Enable Black formatting
- Configure Pytest as test runner
- Enable type checking

---

## Useful Commands

```bash
# Format and lint all code
make format

# Run all tests
make test

# Run tests with coverage
make test-cov

# Start Docker services
make docker-up

# Stop Docker services
make docker-down

# Initialize database
make db-init

# Apply migrations
make db-migrate

# Clean cache and temp files
make clean

# Start development server
make dev
```

---

## Next Steps for Phase 2

- [ ] Implement YOLOv8 detection in `detector/detector.py`
- [ ] Implement DeepSORT tracking in `detector/tracker.py`
- [ ] Implement zone mapping in `detector/zone_mapper.py`
- [ ] Implement event generation in `detector/event_generator.py`
- [ ] Create test data/fixtures
- [ ] Write integration tests for detection pipeline
- [ ] Document detection performance metrics
