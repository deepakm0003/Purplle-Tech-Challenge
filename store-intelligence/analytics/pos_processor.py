"""
POS Transaction Processor Module.

Ingests and validates POS transaction data from CSV files.
Provides query interfaces for transaction analysis.
"""

import logging
import pandas as pd
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")


class POSTransaction:
    """POS transaction record."""
    
    def __init__(
        self,
        store_id: str,
        transaction_id: str,
        timestamp: datetime,
        basket_value_inr: float
    ):
        """Initialize transaction."""
        self.store_id = store_id
        self.transaction_id = transaction_id
        self.timestamp = timestamp
        self.basket_value_inr = basket_value_inr
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'store_id': self.store_id,
            'transaction_id': self.transaction_id,
            'timestamp': self.timestamp.isoformat(),
            'basket_value_inr': self.basket_value_inr
        }


class POSProcessor:
    """
    POS Transaction Processor.
    
    Loads, validates, and queries POS transaction data from CSV files.
    
    Expected CSV schema:
    - store_id: Store identifier
    - transaction_id: Unique transaction ID
    - timestamp: ISO-8601 datetime
    - basket_value_inr: Transaction amount in INR
    
    Attributes:
        transactions: List of POSTransaction objects
        df: Raw Pandas DataFrame
    """
    
    # Schema validation
    REQUIRED_COLUMNS = {'store_id', 'transaction_id', 'timestamp', 'basket_value_inr'}
    
    def __init__(self):
        """Initialize POS processor."""
        self.transactions: List[POSTransaction] = []
        self.df: Optional[pd.DataFrame] = None
        logger.info("POSProcessor initialized")
    
    def load_csv(self, file_path: str) -> bool:
        """
        Load transactions from CSV file.
        
        Args:
            file_path: Path to CSV file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                logger.error(f"File not found: {file_path}")
                return False
            
            # Read CSV
            self.df = pd.read_csv(file_path)
            logger.info(f"Loaded CSV: {len(self.df)} rows")

            self.df = self._normalize_dataframe(self.df)
            
            # Validate schema
            if not self.validate_schema():
                return False
            
            # Convert to POSTransaction objects
            self.transactions = []
            for _, row in self.df.iterrows():
                try:
                    # Parse timestamp
                    if isinstance(row['timestamp'], str):
                        ts = pd.to_datetime(row['timestamp'])
                    else:
                        ts = row['timestamp']
                    
                    # Create transaction object
                    txn = POSTransaction(
                        store_id=str(row['store_id']),
                        transaction_id=str(row['transaction_id']),
                        timestamp=ts.to_pydatetime(),
                        basket_value_inr=float(row['basket_value_inr'])
                    )
                    self.transactions.append(txn)
                    
                except Exception as e:
                    logger.warning(f"Skipping invalid row: {e}")
                    continue
            
            logger.info(f"Parsed {len(self.transactions)} valid transactions")
            return True
            
        except Exception as e:
            logger.error(f"Error loading CSV: {e}")
            return False
    
    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Accept Purplle sample POS (order_id, order_date, order_time, total_amount)
        and map to challenge schema columns.
        """
        if self.REQUIRED_COLUMNS.issubset(set(df.columns)):
            return df

        if {"order_id", "store_id", "total_amount"}.issubset(set(df.columns)):
            out = df.copy()
            out["transaction_id"] = out["order_id"].astype(str)
            if "order_date" in out.columns and "order_time" in out.columns:
                out["timestamp"] = pd.to_datetime(
                    out["order_date"].astype(str) + " " + out["order_time"].astype(str),
                    format="%d-%m-%Y %H:%M:%S",
                    errors="coerce",
                )
            else:
                out["timestamp"] = pd.Timestamp.utcnow()

            basket = (
                out.groupby(["store_id", "transaction_id", "timestamp"], dropna=False)[
                    "total_amount"
                ]
                .sum()
                .reset_index()
            )
            basket = basket.rename(columns={"total_amount": "basket_value_inr"})
            return basket

        return df

    def validate_schema(self) -> bool:
        """
        Validate CSV schema.
        
        Returns:
            True if valid, False otherwise
        """
        if self.df is None or self.df.empty:
            logger.error("No data to validate")
            return False
        
        # Check required columns
        missing = self.REQUIRED_COLUMNS - set(self.df.columns)
        if missing:
            logger.error(f"Missing required columns: {missing}")
            return False
        
        # Check data types
        try:
            # Validate numeric columns
            pd.to_numeric(self.df['basket_value_inr'])
            
            # Validate timestamp
            pd.to_datetime(self.df['timestamp'])
            
            # Check for nulls in required fields
            if self.df[list(self.REQUIRED_COLUMNS)].isnull().any().any():
                logger.error("Found null values in required columns")
                return False
            
            # Validate basket values are positive
            if (self.df['basket_value_inr'] < 0).any():
                logger.error("Found negative basket values")
                return False
            
            logger.info("Schema validation passed")
            return True
            
        except Exception as e:
            logger.error(f"Schema validation failed: {e}")
            return False
    
    def get_transactions(self) -> List[POSTransaction]:
        """
        Get all transactions.
        
        Returns:
            List of transactions
        """
        return self.transactions.copy()
    
    def get_transactions_by_store(self, store_id: str) -> List[POSTransaction]:
        """
        Get transactions for specific store.
        
        Args:
            store_id: Store identifier
            
        Returns:
            List of transactions for store
        """
        return [t for t in self.transactions if t.store_id == store_id]
    
    def get_transactions_in_window(
        self,
        start_time: datetime,
        end_time: datetime,
        store_id: Optional[str] = None
    ) -> List[POSTransaction]:
        """
        Get transactions within time window.
        
        Args:
            start_time: Start time (inclusive)
            end_time: End time (inclusive)
            store_id: Optional store filter
            
        Returns:
            Transactions in window
        """
        result = []
        for t in self.transactions:
            if start_time <= t.timestamp <= end_time:
                if store_id is None or t.store_id == store_id:
                    result.append(t)
        
        return sorted(result, key=lambda x: x.timestamp)
    
    def get_transaction_by_id(self, transaction_id: str) -> Optional[POSTransaction]:
        """
        Get transaction by ID.
        
        Args:
            transaction_id: Transaction identifier
            
        Returns:
            Transaction or None
        """
        for t in self.transactions:
            if t.transaction_id == transaction_id:
                return t
        return None
    
    def get_store_ids(self) -> List[str]:
        """Get unique store IDs."""
        return list(set(t.store_id for t in self.transactions))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processor statistics."""
        if not self.transactions:
            return {
                'total_transactions': 0,
                'stores': 0,
                'total_revenue': 0.0,
                'date_range': None
            }
        
        timestamps = [t.timestamp for t in self.transactions]
        
        return {
            'total_transactions': len(self.transactions),
            'stores': len(self.get_store_ids()),
            'total_revenue': sum(t.basket_value_inr for t in self.transactions),
            'average_basket': sum(t.basket_value_inr for t in self.transactions) / len(self.transactions),
            'date_range': {
                'start': min(timestamps).isoformat(),
                'end': max(timestamps).isoformat()
            }
        }


def create_pos_processor(file_path: str) -> Optional[POSProcessor]:
    """
    Factory function to create and load POSProcessor.
    
    Args:
        file_path: Path to CSV file
        
    Returns:
        Configured POSProcessor or None on error
    """
    processor = POSProcessor()
    if processor.load_csv(file_path):
        return processor
    return None
