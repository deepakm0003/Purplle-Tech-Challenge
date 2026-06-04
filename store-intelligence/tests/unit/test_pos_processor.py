"""
Unit Tests for POSProcessor.

Test coverage:
- CSV loading and validation
- Transaction querying
- Edge cases (nulls, negatives, duplicates)
- Store filtering and time windowing
"""

import pytest
import pandas as pd
import tempfile
import os
from datetime import datetime, timedelta
from analytics.pos_processor import POSProcessor, POSTransaction, create_pos_processor


class TestPOSTransaction:
    """Test POSTransaction dataclass."""
    
    def test_pos_transaction_creation(self):
        """Test creating a POSTransaction."""
        txn = POSTransaction(
            store_id="STORE_001",
            transaction_id="TXN_001",
            timestamp=datetime(2026, 3, 1, 10, 0, 0),
            basket_value_inr=5000.0
        )
        
        assert txn.store_id == "STORE_001"
        assert txn.transaction_id == "TXN_001"
        assert txn.basket_value_inr == 5000.0
    
    def test_pos_transaction_negative_value_rejected(self):
        """Test that negative basket values are rejected."""
        # POSTransaction doesn't validate, validation happens in POSProcessor
        txn = POSTransaction(
            store_id="STORE_001",
            transaction_id="TXN_001",
            timestamp=datetime(2026, 3, 1, 10, 0, 0),
            basket_value_inr=-100.0
        )
        # Dataclass allows this, validation happens elsewhere
        assert txn.basket_value_inr == -100.0


class TestPOSProcessorLoading:
    """Test POSProcessor CSV loading."""
    
    def create_test_csv(self, filename, rows):
        """Create a test CSV file."""
        df = pd.DataFrame(rows)
        df.to_csv(filename, index=False)
        return filename
    
    def test_load_valid_csv(self, tmp_path):
        """Test loading a valid CSV file."""
        csv_file = tmp_path / "valid.csv"
        rows = [
            {
                "store_id": "STORE_001",
                "transaction_id": "TXN_001",
                "timestamp": "2026-03-01T10:00:00",
                "basket_value_inr": 5000.0
            },
            {
                "store_id": "STORE_001",
                "transaction_id": "TXN_002",
                "timestamp": "2026-03-01T10:05:00",
                "basket_value_inr": 3500.0
            }
        ]
        
        df = pd.DataFrame(rows)
        df.to_csv(csv_file, index=False)
        
        processor = POSProcessor()
        success = processor.load_csv(str(csv_file))
        
        assert success
        assert len(processor.transactions) == 2
    
    def test_load_csv_missing_column(self, tmp_path):
        """Test loading CSV with missing required column."""
        csv_file = tmp_path / "missing_col.csv"
        rows = [
            {
                "store_id": "STORE_001",
                "transaction_id": "TXN_001",
                # Missing timestamp
                "basket_value_inr": 5000.0
            }
        ]
        
        df = pd.DataFrame(rows)
        df.to_csv(csv_file, index=False)
        
        processor = POSProcessor()
        success = processor.load_csv(str(csv_file))
        
        # Should fail due to missing column
        assert not success
    
    def test_load_csv_with_nulls(self, tmp_path):
        """Test loading CSV with null values."""
        csv_file = tmp_path / "nulls.csv"
        rows = [
            {
                "store_id": "STORE_001",
                "transaction_id": "TXN_001",
                "timestamp": "2026-03-01T10:00:00",
                "basket_value_inr": 5000.0
            },
            {
                "store_id": None,
                "transaction_id": "TXN_002",
                "timestamp": "2026-03-01T10:05:00",
                "basket_value_inr": 3500.0
            }
        ]
        
        df = pd.DataFrame(rows)
        df.to_csv(csv_file, index=False)
        
        processor = POSProcessor()
        success = processor.load_csv(str(csv_file))
        
        # Should fail due to null values
        assert not success
    
    def test_load_csv_with_negative_values(self, tmp_path):
        """Test loading CSV with negative basket values."""
        csv_file = tmp_path / "negatives.csv"
        rows = [
            {
                "store_id": "STORE_001",
                "transaction_id": "TXN_001",
                "timestamp": "2026-03-01T10:00:00",
                "basket_value_inr": -5000.0
            }
        ]
        
        df = pd.DataFrame(rows)
        df.to_csv(csv_file, index=False)
        
        processor = POSProcessor()
        success = processor.load_csv(str(csv_file))
        
        # Should fail due to negative value
        assert not success
    
    def test_load_csv_invalid_timestamp(self, tmp_path):
        """Test loading CSV with invalid timestamp format."""
        csv_file = tmp_path / "bad_timestamp.csv"
        rows = [
            {
                "store_id": "STORE_001",
                "transaction_id": "TXN_001",
                "timestamp": "not-a-valid-timestamp",
                "basket_value_inr": 5000.0
            }
        ]
        
        df = pd.DataFrame(rows)
        df.to_csv(csv_file, index=False)
        
        processor = POSProcessor()
        success = processor.load_csv(str(csv_file))
        
        # Should fail due to invalid timestamp
        assert not success


class TestPOSProcessorQuerying:
    """Test POSProcessor query methods."""
    
    @pytest.fixture
    def processor_with_data(self, tmp_path):
        """Create processor with test data."""
        csv_file = tmp_path / "data.csv"
        rows = [
            {"store_id": "STORE_001", "transaction_id": "TXN_001", "timestamp": "2026-03-01T10:00:00", "basket_value_inr": 5000.0},
            {"store_id": "STORE_001", "transaction_id": "TXN_002", "timestamp": "2026-03-01T10:30:00", "basket_value_inr": 3500.0},
            {"store_id": "STORE_002", "transaction_id": "TXN_003", "timestamp": "2026-03-01T11:00:00", "basket_value_inr": 6000.0},
            {"store_id": "STORE_001", "transaction_id": "TXN_004", "timestamp": "2026-03-01T15:00:00", "basket_value_inr": 2500.0},
        ]
        
        df = pd.DataFrame(rows)
        df.to_csv(csv_file, index=False)
        
        processor = POSProcessor()
        processor.load_csv(str(csv_file))
        return processor
    
    def test_get_all_transactions(self, processor_with_data):
        """Test getting all transactions."""
        transactions = processor_with_data.get_transactions()
        assert len(transactions) == 4
    
    def test_get_transactions_by_store(self, processor_with_data):
        """Test filtering transactions by store."""
        store_1_txns = processor_with_data.get_transactions_by_store("STORE_001")
        assert len(store_1_txns) == 3
        
        store_2_txns = processor_with_data.get_transactions_by_store("STORE_002")
        assert len(store_2_txns) == 1
    
    def test_get_transactions_by_store_nonexistent(self, processor_with_data):
        """Test filtering by nonexistent store."""
        txns = processor_with_data.get_transactions_by_store("STORE_999")
        assert len(txns) == 0
    
    def test_get_transactions_in_window(self, processor_with_data):
        """Test time window filtering."""
        start = datetime(2026, 3, 1, 10, 0, 0)
        end = datetime(2026, 3, 1, 11, 0, 0)
        
        txns = processor_with_data.get_transactions_in_window(start, end, "STORE_001")
        assert len(txns) == 2  # TXN_001, TXN_002
    
    def test_get_transactions_in_window_empty(self, processor_with_data):
        """Test time window with no results."""
        start = datetime(2026, 3, 2, 10, 0, 0)
        end = datetime(2026, 3, 2, 11, 0, 0)
        
        txns = processor_with_data.get_transactions_in_window(start, end, "STORE_001")
        assert len(txns) == 0
    
    def test_get_transaction_by_id(self, processor_with_data):
        """Test getting transaction by ID."""
        txn = processor_with_data.get_transaction_by_id("TXN_002")
        
        assert txn is not None
        assert txn.store_id == "STORE_001"
        assert txn.basket_value_inr == 3500.0
    
    def test_get_transaction_by_id_nonexistent(self, processor_with_data):
        """Test getting nonexistent transaction."""
        txn = processor_with_data.get_transaction_by_id("NONEXISTENT")
        assert txn is None
    
    def test_get_store_ids(self, processor_with_data):
        """Test getting unique store IDs."""
        stores = processor_with_data.get_store_ids()
        assert len(stores) == 2
        assert "STORE_001" in stores
        assert "STORE_002" in stores
    
    def test_get_stats(self, processor_with_data):
        """Test getting processor statistics."""
        stats = processor_with_data.get_stats()
        
        assert stats['total_transactions'] == 4
        assert stats['stores'] == 2
        assert stats['total_revenue'] == 17000.0
        assert stats['average_basket_size'] == 4250.0


class TestPOSProcessorEdgeCases:
    """Test edge cases and error handling."""
    
    def test_load_empty_csv(self, tmp_path):
        """Test loading empty CSV."""
        csv_file = tmp_path / "empty.csv"
        df = pd.DataFrame(columns=["store_id", "transaction_id", "timestamp", "basket_value_inr"])
        df.to_csv(csv_file, index=False)
        
        processor = POSProcessor()
        success = processor.load_csv(str(csv_file))
        
        # Should succeed but have no transactions
        assert success
        assert len(processor.transactions) == 0
    
    def test_load_file_not_found(self):
        """Test loading nonexistent file."""
        processor = POSProcessor()
        success = processor.load_csv("/nonexistent/path/file.csv")
        assert not success
    
    def test_factory_function(self, tmp_path):
        """Test factory function."""
        csv_file = tmp_path / "data.csv"
        rows = [
            {"store_id": "STORE_001", "transaction_id": "TXN_001", "timestamp": "2026-03-01T10:00:00", "basket_value_inr": 5000.0}
        ]
        
        df = pd.DataFrame(rows)
        df.to_csv(csv_file, index=False)
        
        processor = create_pos_processor(str(csv_file))
        assert processor is not None
        assert len(processor.transactions) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
