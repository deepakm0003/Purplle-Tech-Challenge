// Dashboard Constants

export const DASHBOARD_CONFIG = {
  // Refresh intervals (ms)
  METRICS_REFRESH: 5000,
  HEATMAP_REFRESH: 8000,
  CAMERA_REFRESH: 5000,
  QUEUE_REFRESH: 5000,
  ANOMALY_REFRESH: 5000,
  POS_REFRESH: 30000,
  HEALTH_REFRESH: 10000,

  // API Configuration
  API_TIMEOUT: 10000,
  MAX_RETRIES: 3,
  RETRY_DELAY: 1000,

  // Pagination
  DEFAULT_PAGE_SIZE: 50,
  MAX_PAGE_SIZE: 100,

  // Time windows
  CHART_HOURS: 24,
  TREND_POINTS: 100,
};

export const SEVERITY_LEVELS = {
  CRITICAL: 'CRITICAL',
  WARN: 'WARN',
  INFO: 'INFO',
} as const;

export const CAMERA_STATUS = {
  ACTIVE: 'active',
  INACTIVE: 'inactive',
  ERROR: 'error',
} as const;

export const VISITOR_STATUS = {
  CONVERTED: 'converted',
  NOT_CONVERTED: 'not_converted',
} as const;

export const ANOMALY_TYPES = {
  QUEUE_SPIKE: 'Queue Spike',
  CONVERSION_DROP: 'Conversion Drop',
  DEAD_ZONE: 'Dead Zone',
  UNUSUAL_BEHAVIOR: 'Unusual Behavior',
} as const;

export const EVENT_TYPES = {
  ENTRY: 'entry',
  EXIT: 'exit',
  ZONE_VISIT: 'zone_visit',
  DWELL: 'dwell',
  QUEUE_JOIN: 'queue_join',
  QUEUE_ABANDON: 'queue_abandon',
  REENTRY: 'reentry',
} as const;

export const ZONE_TYPES = {
  ENTRY: 'entry',
  FLOOR: 'floor',
  SECTION: 'section',
  BILLING: 'billing',
  QUEUE: 'queue',
} as const;

// Color mapping
export const COLOR_MAP = {
  primary: '#a855f7',
  secondary: '#8b5cf6',
  success: '#10b981',
  warning: '#f59e0b',
  danger: '#ef4444',
  info: '#3b82f6',
  slate: {
    50: '#f8fafc',
    100: '#f1f5f9',
    200: '#e2e8f0',
    500: '#64748b',
    600: '#475569',
    900: '#0f172a',
  },
};

// Chart colors
export const CHART_COLORS = ['#a855f7', '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6'];

// Thresholds
export const THRESHOLDS = {
  HIGH_QUEUE_DEPTH: 15,
  MODERATE_QUEUE_DEPTH: 5,
  HIGH_HEAT_SCORE: 80,
  MODERATE_HEAT_SCORE: 60,
  LOW_CONVERSION_RATE: 0.1,
  GOOD_CONVERSION_RATE: 0.25,
  API_LATENCY_GOOD: 100,
  API_LATENCY_WARN: 500,
};

// Messages
export const MESSAGES = {
  LOADING: 'Loading data...',
  ERROR: 'Failed to load data',
  NO_DATA: 'No data available',
  RETRY: 'Try Again',
  CONNECTION_ERROR: 'Failed to connect to API',
};

// Date/Time Formats
export const DATE_FORMATS = {
  SHORT: 'MMM dd',
  LONG: 'MMMM dd, yyyy',
  TIME: 'HH:mm:ss',
  DATETIME: 'MMM dd, yyyy HH:mm',
};

// Feature Flags
export const FEATURES = {
  REAL_TIME_UPDATES: true,
  EXPORT_DATA: true,
  CUSTOM_ALERTS: false,
  PREDICTIVE_ANALYTICS: false,
  INVENTORY_SYNC: false,
};

// API Endpoints (backend: /api/analytics/stores/{storeId}/...)
export const API_ENDPOINTS = {
  HEALTH: '/health',
  ANALYTICS_HEALTH: '/api/analytics/health',
  METRICS: '/api/analytics/stores/{storeId}/metrics',
  FUNNEL: '/api/analytics/stores/{storeId}/funnel',
  HEATMAP: '/api/analytics/stores/{storeId}/heatmap',
  ANOMALIES: '/api/analytics/stores/{storeId}/anomalies',
  EVENTS_INGEST: '/api/analytics/events/ingest',
} as const;
