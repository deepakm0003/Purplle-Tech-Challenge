// Metrics and Analytics
export interface MetricsResponse {
  unique_visitors: number;
  active_visitors: number;
  conversion_rate: number;
  revenue: number;
  average_dwell_time: number;
  queue_depth: number;
  timestamp: string;
}

export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  environment: string;
}

// Funnel
export interface FunnelStage {
  stage: string;
  count: number;
  conversion_rate: number;
}

export interface FunnelResponse {
  stages: FunnelStage[];
  total_entries: number;
  total_conversions: number;
  overall_conversion_rate: number;
}

// Heatmap
export interface ZoneHeatmap {
  zone_id: string;
  zone_name: string;
  visitor_count: number;
  heat_score: number;
  occupancy_percentage: number;
  avg_dwell_seconds?: number;
}

export interface HeatmapResponse {
  zones: ZoneHeatmap[];
  timestamp: string;
}

// Anomalies
export interface Anomaly {
  id: string;
  anomaly_type: string;
  severity: 'INFO' | 'WARN' | 'CRITICAL';
  timestamp: string;
  description: string;
  zone_id?: string;
  value?: number;
}

export interface AnomaliesResponse {
  anomalies: Anomaly[];
  timestamp: string;
}

// Events
export interface Event {
  id: string;
  event_type: string;
  timestamp: string;
  zone_id: string;
  zone_name: string;
  visitor_id: string;
  camera_id: string;
  confidence: number;
  metadata?: Record<string, unknown>;
}

export interface EventsResponse {
  events: Event[];
  total: number;
  limit: number;
  offset: number;
}

// Camera
export interface Camera {
  id: string;
  name: string;
  ip_address: string;
  status: 'active' | 'inactive' | 'error';
  visitor_count: number;
  active_tracks: number;
  last_frame_timestamp: string;
}

export interface CamerasResponse {
  cameras: Camera[];
  timestamp: string;
}

// Store Layout
export interface Zone {
  id: string;
  name: string;
  zone_type: string;
  pixel_bounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  coordinates?: number[][];
}

export interface StoreLayout {
  store_id: string;
  store_name: string;
  zones: Zone[];
  total_area: number;
  layout_image_url?: string;
  camera_positions?: Record<string, { x: number; y: number }>;
}

// POS Transaction
export interface POSTransaction {
  order_id: string;
  invoice_number: string;
  order_date: string;
  order_time: string;
  customer_number: string;
  product_name: string;
  brand_name: string;
  qty: number;
  total_amount: number;
  salesperson_name: string;
  store_name: string;
}

export interface POSAnalytics {
  total_revenue: number;
  average_basket_size: number;
  total_transactions: number;
  revenue_per_visitor: number;
  top_products: Array<{ name: string; count: number; revenue: number }>;
  top_hours: Array<{ hour: number; count: number; revenue: number }>;
  top_brands: Array<{ name: string; count: number; revenue: number }>;
  store_name?: string;
  date?: string;
  line_items?: number;
}

// Visitor Journey
export interface VisitorJourney {
  visitor_id: string;
  entry_time: string;
  exit_time?: string;
  cameras: string[];
  zones: Array<{
    zone_name: string;
    entry_time: string;
    exit_time: string;
    dwell_time: number;
  }>;
  purchase_status: 'converted' | 'not_converted';
  purchase_amount?: number;
  staff_classification: boolean;
}

// Dashboard Card Metrics
export interface MetricCard {
  title: string;
  value: number | string;
  unit?: string;
  trend?: number;
  trendDirection?: 'up' | 'down' | 'neutral';
  icon: React.ReactNode;
  color: string;
}

// API Error
export interface APIError {
  type: string;
  title: string;
  status: number;
  detail: string;
  trace_id: string;
  error_code: string;
  recovery_suggestions?: string[];
}

// Queue Analytics
export interface QueueAnalytics {
  current_queue_depth: number;
  average_queue_depth: number;
  peak_queue_depth: number;
  abandonment_rate: number;
  average_wait_time: number;
  queue_trend: Array<{ timestamp: string; depth: number }>;
}

// System Health
export interface SystemHealth {
  database_status: 'healthy' | 'degraded' | 'unhealthy';
  redis_status: 'healthy' | 'degraded' | 'unhealthy';
  api_status: 'healthy' | 'degraded' | 'unhealthy';
  last_event_timestamp: string;
  events_processed: number;
  api_latency_ms: number;
  request_rate_per_second: number;
}

// Trend Data
export interface TrendData {
  timestamp: string;
  value: number;
}

// Time Series Data
export interface TimeSeriesMetric {
  timestamp: string;
  visitors: number;
  conversions: number;
  revenue: number;
  dwell_time: number;
}
