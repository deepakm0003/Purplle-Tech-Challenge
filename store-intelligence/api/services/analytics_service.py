"""
Analytics Service Module.

Orchestrates all analytics engines for store intelligence computation.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger

# Configure loguru
logger.remove()
logger.add(lambda msg: logging.getLogger(__name__).info(msg.strip()), format="{message}")

from api.schemas import Event
from analytics.pos_processor import POSProcessor
from analytics.conversion_engine import ConversionEngine
from analytics.metrics import MetricsEngine
from analytics.funnel import FunnelEngine
from analytics.heatmap import HeatmapEngine
from analytics.anomalies import AnomalyDetector


class AnalyticsService:
    """
    Analytics Service.
    
    Orchestrates all analytics computations for a store.
    Manages dependencies between engines.
    
    Attributes:
        store_id: Store identifier
        events: List of events
        pos_processor: POS transaction processor
        conversion_engine: Conversion computation engine
        metrics_engine: Metrics computation engine
        funnel_engine: Funnel computation engine
        heatmap_engine: Heatmap computation engine
        anomaly_detector: Anomaly detection engine
    """
    
    def __init__(self, store_id: str):
        """
        Initialize analytics service.
        
        Args:
            store_id: Store identifier
        """
        self.store_id = store_id
        self.events: List[Event] = []
        
        self.pos_processor = POSProcessor()
        self.conversion_engine = ConversionEngine()
        self.metrics_engine = MetricsEngine()
        self.funnel_engine = FunnelEngine()
        self.heatmap_engine = HeatmapEngine()
        self.anomaly_detector = AnomalyDetector()
        
        logger.info(f"AnalyticsService initialized for {store_id}")
    
    def load_pos_data(self, csv_path: str) -> bool:
        """
        Load POS transaction data.
        
        Args:
            csv_path: Path to CSV file
            
        Returns:
            True if successful
        """
        return self.pos_processor.load_csv(csv_path)
    
    def ingest_events(self, events: List[Event], replace: bool = False) -> None:
        """
        Ingest events for analysis (merge by default, dedupe by event_id).
        
        Args:
            events: List of Event objects
            replace: If True, replace in-memory list instead of merging
        """
        if replace:
            self.events = [e for e in events if e.store_id == self.store_id]
        else:
            seen = {e.event_id for e in self.events}
            for e in events:
                if e.store_id == self.store_id and e.event_id not in seen:
                    self.events.append(e)
                    seen.add(e.event_id)
        logger.info(f"Ingested {len(self.events)} events for {self.store_id}")
    
    def compute_all_analytics(self) -> Dict[str, Any]:
        """
        Compute all analytics.
        
        Runs dependency order:
        1. Conversions (events + POS transactions)
        2. Metrics (events + conversions)
        3. Funnel (events + conversions)
        4. Heatmap (events)
        5. Anomalies (events + metrics)
        
        Returns:
            Complete analytics dict
        """
        # Step 1: Match transactions to events (conversions)
        transactions = self.pos_processor.get_transactions_by_store(self.store_id)
        self.conversion_engine.match_transaction_to_visitor(
            self.events,
            transactions,
            self.store_id
        )
        logger.info(f"Conversion engine: {self.conversion_engine.compute_purchase_count()} matches")
        
        # Step 2: Compute metrics
        metrics = self.metrics_engine.compute_metrics(
            self.events,
            self.conversion_engine
        )
        logger.info(f"Metrics computed: {metrics['unique_visitors']} visitors")
        
        # Step 3: Compute funnel
        funnel = self.funnel_engine.compute_funnel(
            self.events,
            self.conversion_engine
        )
        logger.info(f"Funnel computed: {funnel['purchase_count']} purchases")
        
        # Step 4: Compute heatmap
        heatmap = self.heatmap_engine.compute_heatmap(self.events)
        logger.info(f"Heatmap computed: {heatmap['zone_count']} zones")
        
        # Step 5: Detect anomalies
        historical_conversion = metrics['conversion_rate']
        anomalies = self.anomaly_detector.detect_anomalies(
            self.events,
            historical_conversion_rate=historical_conversion
        )
        logger.info(f"Anomalies detected: {len(anomalies)} total")
        
        return {
            'store_id': self.store_id,
            'metrics': metrics,
            'funnel': funnel,
            'heatmap': heatmap,
            'anomalies': [a.to_dict() for a in anomalies],
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        if not self.conversion_engine.conversions:
            # Re-compute conversions first
            transactions = self.pos_processor.get_transactions_by_store(self.store_id)
            self.conversion_engine.match_transaction_to_visitor(
                self.events,
                transactions,
                self.store_id
            )
        
        return self.metrics_engine.compute_metrics(self.events, self.conversion_engine)
    
    def get_funnel(self) -> Dict[str, Any]:
        """Get current funnel."""
        if not self.conversion_engine.conversions:
            transactions = self.pos_processor.get_transactions_by_store(self.store_id)
            self.conversion_engine.match_transaction_to_visitor(
                self.events,
                transactions,
                self.store_id
            )
        
        return self.funnel_engine.compute_funnel(self.events, self.conversion_engine)
    
    def get_heatmap(self) -> Dict[str, Any]:
        """Get current heatmap."""
        return self.heatmap_engine.compute_heatmap(self.events)
    
    def get_anomalies(self) -> Dict[str, Any]:
        """Get current anomalies."""
        if not self.conversion_engine.conversions:
            transactions = self.pos_processor.get_transactions_by_store(self.store_id)
            self.conversion_engine.match_transaction_to_visitor(
                self.events,
                transactions,
                self.store_id
            )
        
        metrics = self.metrics_engine.compute_metrics(self.events, self.conversion_engine)
        self.anomaly_detector.detect_anomalies(
            self.events,
            historical_conversion_rate=metrics['conversion_rate'],
        )

        return self.anomaly_detector.get_stats()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get service statistics."""
        return {
            'store_id': self.store_id,
            'events_count': len(self.events),
            'transactions_count': len(self.pos_processor.get_transactions()),
            'conversions': self.conversion_engine.compute_purchase_count()
        }


def create_analytics_service(store_id: str) -> AnalyticsService:
    """
    Factory function to create AnalyticsService.
    
    Args:
        store_id: Store identifier
        
    Returns:
        Configured AnalyticsService
    """
    return AnalyticsService(store_id)
