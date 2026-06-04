"""Pytest Configuration"""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_store_data():
    """Sample store data for tests."""
    return {
        "store_id": "TEST-STORE-001",
        "name": "Test Store",
        "address": "123 Main St",
        "timezone": "Asia/Kolkata",
    }


@pytest.fixture
def sample_event_data():
    """Sample event data for tests."""
    return {
        "event_id": "evt_12345",
        "event_type": "ENTRY",
        "is_staff": False,
        "confidence": 0.95,
    }
