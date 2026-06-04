"""
Unit Tests for ConversionEngine.

Test coverage:
- Transaction-to-visitor matching
- Confidence scoring
- Deduplication (no double-counting)
- Conversion metrics (rate, revenue, basket size)
- Edge cases (zero visitors, no matches)
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4

from api.schemas import Event, EventType, EventMetadata
from analytics.pos_processor import POSTransaction
from analytics.conversion_engine import ConversionEngine, ConversionMatch, create_conversion_engine


class TestConversionMatch:
    """Test ConversionMatch result object."""
    
    def test_conversion_match_creation(self):
        """Test creating a ConversionMatch."""
        match = ConversionMatch(
            visitor_id="VIS_001",
            transaction_id="TXN_001",
            event_timestamp=datetime(2026, 3, 1, 10, 0, 0),
            transaction_timestamp=datetime(2026, 3, 1, 10, 2, 0),
            basket_value=5000.0,
            confidence=0.95
        )
        
        assert match.visitor_id == "VIS_001"
        assert match.basket_value == 5000.0
        assert match.confidence == 0.95


class TestConversionEngineMatching:
    """Test transaction-to-visitor matching."""
    
    @pytest.fixture
    def engine(self):
        """Create conversion engine."""
        return ConversionEngine()
    
    @pytest.fixture
    def sample_events(self):
        """Create sample events."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        return [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.ENTRY,
                timestamp=base_time,
                zone_id=None,
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_002",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time + timedelta(seconds=30),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95,
                metadata=EventMetadata(queue_depth=2)
            ),
        ]
    
    @pytest.fixture
    def sample_transactions(self):
        """Create sample POS transactions."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        return [
            POSTransaction(
                store_id="STORE_001",
                transaction_id="TXN_001",
                timestamp=base_time + timedelta(seconds=90),
                basket_value_inr=5000.0
            ),
            POSTransaction(
                store_id="STORE_001",
                transaction_id="TXN_002",
                timestamp=base_time + timedelta(minutes=6),  # Outside window
                basket_value_inr=3000.0
            ),
        ]
    
    def test_match_transaction_to_visitor(self, engine, sample_events, sample_transactions):
        """Test matching transactions to visitors."""
        matches = engine.match_transaction_to_visitor(
            sample_events,
            sample_transactions,
            "STORE_001"
        )
        
        assert len(engine.conversions) >= 1
        assert engine.conversions[0].visitor_id == "VIS_001"
        assert engine.conversions[0].transaction_id == "TXN_001"
    
    def test_confidence_scoring(self, engine, sample_events, sample_transactions):
        """Test confidence scoring based on time delta."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time,
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        transactions = [
            POSTransaction(
                store_id="STORE_001",
                transaction_id="TXN_001",
                timestamp=base_time + timedelta(seconds=30),  # 30 seconds later
                basket_value_inr=5000.0
            ),
        ]
        
        engine.match_transaction_to_visitor(events, transactions, "STORE_001")
        
        if engine.conversions:
            # Confidence should be high for close time delta
            assert engine.conversions[0].confidence > 0.5
    
    def test_no_duplicate_matching(self, engine):
        """Test that transactions are not double-counted."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time,
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_002",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time + timedelta(seconds=60),
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        transactions = [
            POSTransaction(
                store_id="STORE_001",
                transaction_id="TXN_001",
                timestamp=base_time + timedelta(seconds=90),
                basket_value_inr=5000.0
            ),
        ]
        
        engine.match_transaction_to_visitor(events, transactions, "STORE_001")
        
        # Only one transaction should match
        assert len(engine.conversions) == 1
    
    def test_match_outside_window(self, engine):
        """Test that matches outside time window are not made."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time,
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        transactions = [
            POSTransaction(
                store_id="STORE_001",
                transaction_id="TXN_001",
                timestamp=base_time + timedelta(seconds=310),  # 5 min 10 sec later (outside window)
                basket_value_inr=5000.0
            ),
        ]
        
        engine.match_transaction_to_visitor(events, transactions, "STORE_001")
        
        # Should not match (outside 5-minute window)
        assert len(engine.conversions) == 0
    
    def test_different_stores_no_match(self, engine):
        """Test that different stores don't match."""
        base_time = datetime(2026, 3, 1, 10, 0, 0)
        
        events = [
            Event(
                event_id=str(uuid4()),
                store_id="STORE_001",
                camera_id="CAM_001",
                visitor_id="VIS_001",
                event_type=EventType.BILLING_QUEUE_JOIN,
                timestamp=base_time,
                zone_id="BILLING",
                dwell_ms=0,
                is_staff=False,
                confidence=0.95
            ),
        ]
        
        transactions = [
            POSTransaction(
                store_id="STORE_002",
                transaction_id="TXN_001",
                timestamp=base_time + timedelta(seconds=60),
                basket_value_inr=5000.0
            ),
        ]
        
        # Match for STORE_001 with transactions from STORE_002
        engine.match_transaction_to_visitor(events, transactions, "STORE_001")
        
        # Should not match
        assert len(engine.conversions) == 0


class TestConversionEngineMetrics:
    """Test conversion metric computations."""
    
    @pytest.fixture
    def populated_engine(self):
        """Create engine with populated conversions."""
        engine = ConversionEngine()
        
        # Manually add conversions
        engine.conversions = [
            ConversionMatch(
                visitor_id="VIS_001",
                transaction_id="TXN_001",
                event_timestamp=datetime(2026, 3, 1, 10, 0, 0),
                transaction_timestamp=datetime(2026, 3, 1, 10, 2, 0),
                time_delta=120,
                basket_value=5000.0,
                confidence=0.95
            ),
            ConversionMatch(
                visitor_id="VIS_002",
                transaction_id="TXN_002",
                event_timestamp=datetime(2026, 3, 1, 10, 30, 0),
                transaction_timestamp=datetime(2026, 3, 1, 10, 32, 0),
                time_delta=120,
                basket_value=3000.0,
                confidence=0.85
            ),
            ConversionMatch(
                visitor_id="VIS_003",
                transaction_id="TXN_003",
                event_timestamp=datetime(2026, 3, 1, 11, 0, 0),
                transaction_timestamp=datetime(2026, 3, 1, 11, 1, 0),
                time_delta=60,
                basket_value=4500.0,
                confidence=0.98
            ),
        ]
        
        return engine
    
    def test_compute_conversion_rate(self, populated_engine):
        """Test conversion rate calculation."""
        rate = populated_engine.compute_conversion_rate(total_sessions=10)
        assert rate == 0.3  # 3 conversions / 10 sessions
    
    def test_compute_conversion_rate_zero_sessions(self, populated_engine):
        """Test conversion rate with zero sessions."""
        rate = populated_engine.compute_conversion_rate(total_sessions=0)
        assert rate == 0.0
    
    def test_compute_purchase_count(self, populated_engine):
        """Test purchase count."""
        count = populated_engine.compute_purchase_count()
        assert count == 3
    
    def test_compute_revenue(self, populated_engine):
        """Test revenue calculation."""
        revenue = populated_engine.compute_revenue()
        assert revenue == 12500.0  # 5000 + 3000 + 4500
    
    def test_compute_average_basket(self, populated_engine):
        """Test average basket size."""
        avg = populated_engine.compute_average_basket()
        assert avg == pytest.approx(4166.67, rel=0.01)
    
    def test_compute_confidence_average(self, populated_engine):
        """Test average confidence score."""
        conf = populated_engine.get_conversion_confidence()
        assert conf == pytest.approx(0.927, rel=0.01)
    
    def test_get_conversions(self, populated_engine):
        """Test getting all conversions."""
        conversions = populated_engine.get_conversions()
        assert len(conversions) == 3
    
    def test_get_stats(self, populated_engine):
        """Test getting statistics."""
        stats = populated_engine.get_stats()
        
        assert stats['total_conversions'] == 3
        assert stats['total_revenue'] == 12500.0
        assert stats['average_basket_size'] == pytest.approx(4166.67, rel=0.01)


class TestConversionEngineEdgeCases:
    """Test edge cases."""
    
    def test_no_conversions(self):
        """Test engine with no conversions."""
        engine = ConversionEngine()
        
        assert engine.compute_purchase_count() == 0
        assert engine.compute_revenue() == 0.0
        assert engine.compute_average_basket() == 0.0
        assert engine.get_conversion_confidence() == 0.0
    
    def test_factory_function(self):
        """Test factory function."""
        engine = create_conversion_engine()
        assert engine is not None
        assert len(engine.conversions) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
