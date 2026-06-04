"""
Conversion Engine Module.

Correlates visitor events with POS transactions to compute conversion metrics.

Business Rule:
A visitor is converted if:
1. Visitor entered BILLING zone
2. POS transaction occurs within 5 minutes
3. Same store
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event, EventType
from analytics.pos_processor import POSTransaction


class ConversionMatch:
    """Result of visitor-transaction correlation."""
    
    def __init__(
        self,
        visitor_id: str,
        transaction_id: str,
        event_timestamp: datetime,
        transaction_timestamp: datetime,
        basket_value: float,
        confidence: float
    ):
        """Initialize match."""
        self.visitor_id = visitor_id
        self.transaction_id = transaction_id
        self.event_timestamp = event_timestamp
        self.transaction_timestamp = transaction_timestamp
        self.time_delta = (transaction_timestamp - event_timestamp).total_seconds()
        self.basket_value = basket_value
        self.confidence = confidence
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'visitor_id': self.visitor_id,
            'transaction_id': self.transaction_id,
            'event_timestamp': self.event_timestamp.isoformat(),
            'transaction_timestamp': self.transaction_timestamp.isoformat(),
            'time_delta_seconds': self.time_delta,
            'basket_value': self.basket_value,
            'confidence': self.confidence
        }


class ConversionEngine:
    """
    Conversion Engine.
    
    Correlates visitor events with POS transactions.
    Computes conversion rates, purchase counts, revenue, etc.
    
    Attributes:
        billing_zone: Name of billing/checkout zone (default "BILLING")
        match_window_seconds: Time window for transaction matching (default 300 = 5 min)
        conversions: List of ConversionMatch objects
    """
    
    def __init__(
        self,
        billing_zone: str = "CHECKOUT",
        match_window_seconds: int = 300
    ):
        """
        Initialize conversion engine.
        
        Args:
            billing_zone: Billing zone identifier
            match_window_seconds: Time window in seconds (default 5 min)
        """
        self.billing_zone = billing_zone
        self.match_window_seconds = match_window_seconds
        self.conversions: List[ConversionMatch] = []
        
        logger.info(
            f"ConversionEngine init: billing_zone={billing_zone}, "
            f"match_window={match_window_seconds}s"
        )
    
    def match_transaction_to_visitor(
        self,
        events: List[Event],
        transactions: List[POSTransaction],
        store_id: str
    ) -> List[ConversionMatch]:
        """
        Match transactions to visitors based on BILLING zone entry.
        
        Business Rule:
        - Visitor entered BILLING zone
        - POS transaction within 5 minutes
        - Same store
        
        Args:
            events: List of events
            transactions: List of POS transactions
            store_id: Store identifier
            
        Returns:
            List of ConversionMatch objects
        """
        # Filter for store
        store_events = [e for e in events if e.store_id == store_id]
        store_txns = [t for t in transactions if t.store_id == store_id]
        
        if not store_events or not store_txns:
            logger.debug(f"No events or transactions for store {store_id}")
            return []
        
        matches = []
        matched_txns = set()  # Avoid double-counting
        
        # Find BILLING zone entry events per visitor
        visitor_billing_times: Dict[str, datetime] = {}
        for event in store_events:
            if (event.event_type == EventType.BILLING_QUEUE_JOIN and
                event.zone_id == self.billing_zone):
                # Use first billing entry time for each visitor
                if event.visitor_id not in visitor_billing_times:
                    visitor_billing_times[event.visitor_id] = event.timestamp
        
        if not visitor_billing_times:
            logger.debug(f"No BILLING zone entries in {store_id}")
            return []
        
        # Try to match transactions to billing entries
        for visitor_id, billing_time in visitor_billing_times.items():
            window_start = billing_time
            window_end = billing_time + timedelta(seconds=self.match_window_seconds)
            
            # Find transaction in window (earliest one)
            best_match = None
            best_txn = None
            
            for txn in store_txns:
                if txn.transaction_id in matched_txns:
                    continue
                
                if window_start <= txn.timestamp <= window_end:
                    # Calculate confidence based on time proximity
                    time_delta = (txn.timestamp - billing_time).total_seconds()
                    # Higher confidence if closer to entry
                    confidence = max(0.5, 1.0 - (time_delta / self.match_window_seconds) * 0.4)
                    
                    if best_match is None or confidence > best_match.confidence:
                        best_match = confidence
                        best_txn = txn
            
            if best_txn:
                match = ConversionMatch(
                    visitor_id=visitor_id,
                    transaction_id=best_txn.transaction_id,
                    event_timestamp=billing_time,
                    transaction_timestamp=best_txn.timestamp,
                    basket_value=best_txn.basket_value_inr,
                    confidence=best_match
                )
                matches.append(match)
                matched_txns.add(best_txn.transaction_id)
        
        self.conversions = matches
        logger.info(f"Found {len(matches)} conversion matches in {store_id}")
        return matches
    
    def compute_conversion_rate(self, total_sessions: int) -> float:
        """
        Compute conversion rate.
        
        Args:
            total_sessions: Total number of sessions
            
        Returns:
            Conversion rate (0-1)
        """
        if total_sessions == 0:
            return 0.0
        
        return len(self.conversions) / total_sessions
    
    def compute_purchase_count(self) -> int:
        """
        Get total purchase count.
        
        Returns:
            Number of conversions
        """
        return len(self.conversions)
    
    def compute_revenue(self) -> float:
        """
        Compute total revenue from conversions.
        
        Returns:
            Total revenue in INR
        """
        return sum(m.basket_value for m in self.conversions)
    
    def compute_average_basket(self) -> float:
        """
        Compute average basket size.
        
        Returns:
            Average basket value in INR
        """
        if not self.conversions:
            return 0.0
        
        return self.compute_revenue() / len(self.conversions)
    
    def get_conversion_confidence(self) -> float:
        """
        Get average confidence score of conversions.
        
        Returns:
            Average confidence (0-1)
        """
        if not self.conversions:
            return 0.0
        
        return sum(m.confidence for m in self.conversions) / len(self.conversions)
    
    def get_conversions(self) -> List[ConversionMatch]:
        """Get all conversion matches."""
        return self.conversions.copy()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get conversion statistics."""
        return {
            'total_conversions': len(self.conversions),
            'total_revenue': self.compute_revenue(),
            'average_basket': self.compute_average_basket(),
            'average_confidence': self.get_conversion_confidence(),
            'conversions': [m.to_dict() for m in self.conversions]
        }


def create_conversion_engine(
    billing_zone: str = "CHECKOUT",
    match_window_seconds: int = 300
) -> ConversionEngine:
    """
    Factory function to create ConversionEngine.
    
    Args:
        billing_zone: Billing zone identifier
        match_window_seconds: Time window in seconds
        
    Returns:
        Configured ConversionEngine
    """
    return ConversionEngine(billing_zone, match_window_seconds)
