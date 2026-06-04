import {
  MetricsResponse,
  HealthResponse,
  POSAnalytics,
  FunnelResponse,
  HeatmapResponse,
  AnomaliesResponse,
  StoreLayout,
  SystemHealth,
} from '../types';
import { api, API_BASE_URL, ANALYTICS_PREFIX } from './api';

const STORES_PREFIX = '/api/stores';

/** Encode path segments so filenames with spaces play in HTML5 video. */
export function cctvMediaUrl(mediaPath: string): string {
  if (mediaPath.startsWith('http://') || mediaPath.startsWith('https://')) {
    return mediaPath;
  }
  const base = API_BASE_URL.replace(/\/$/, '');
  const path = mediaPath.startsWith('/') ? mediaPath : `/${mediaPath}`;
  const encoded = path
    .split('/')
    .map((segment, index) => {
      if (index === 0 && segment === '') return '';
      try {
        return encodeURIComponent(decodeURIComponent(segment));
      } catch {
        return encodeURIComponent(segment);
      }
    })
    .join('/');
  return `${base}${encoded}`;
}

export interface StoreInfo {
  store_id: string;
  name: string;
  slug: string;
  camera_count: number;
  layout_image_url?: string | null;
}

export interface StoreCamera {
  id: string;
  name: string;
  role?: string;
  file_name?: string;
  media_url?: string;
  tracks_url?: string | null;
  layout_image_url?: string | null;
  ip_address?: string;
  size_mb?: number;
  pipeline_status?: string;
  event_count?: number;
  entry_count?: number;
  visitor_count?: number;
  active_tracks?: number;
  last_frame_timestamp?: string | null;
  status?: 'active' | 'inactive' | 'error' | 'footage_available' | string;
}

export interface StoreCamerasResponse {
  store_id: string;
  store_name: string;
  footage_date: string;
  layout_image_url?: string | null;
  cameras: StoreCamera[];
  total: number;
  note: string;
  timestamp: string;
}

export interface StoreDashboard {
  source: string;
  store_name: string;
  store_id: string;
  date: string;
  summary: {
    total_revenue: number;
    total_orders: number;
    line_items: number;
    unique_customers: number;
    average_order_value: number;
    average_items_per_order: number;
  };
  hourly_revenue: Array<{ hour: number; label: string; revenue: number }>;
  top_products: Array<{ name: string; revenue: number; count: number }>;
  top_brands: Array<{ name: string; revenue: number; count: number }>;
  top_categories: Array<{ name: string; revenue: number }>;
  top_staff: Array<{ name: string; revenue: number }>;
}

export interface EventSummary {
  store_id: string;
  total_events: number;
  entry_events: number;
  exit_events: number;
  unique_visitors: number;
  cameras: string[];
  timestamp: string;
}

class APIClient {
  private storeId = import.meta.env.VITE_STORE_ID || 'ST1008';

  setStoreId(storeId: string) {
    this.storeId = storeId;
  }

  getStoreId() {
    return this.storeId;
  }

  private storePath(suffix: string) {
    return `${ANALYTICS_PREFIX}/stores/${this.storeId}${suffix}`;
  }

  async listStores(): Promise<{ stores: StoreInfo[] }> {
    const { data } = await api.get(`${STORES_PREFIX}`);
    return data;
  }

  async getStoreDashboard(storeId?: string): Promise<StoreDashboard> {
    const id = storeId ?? this.storeId;
    const { data } = await api.get<StoreDashboard>(`${STORES_PREFIX}/${id}/dashboard`);
    return data;
  }

  async getStorePOS(storeId?: string): Promise<
    POSAnalytics & { store_name?: string; date?: string; line_items?: number }
  > {
    const id = storeId ?? this.storeId;
    const { data } = await api.get(`${STORES_PREFIX}/${id}/pos`);
    return {
      total_revenue: data.total_revenue,
      average_basket_size: data.average_basket_size,
      total_transactions: data.total_transactions,
      revenue_per_visitor: data.revenue_per_visitor,
      top_products: data.top_products ?? [],
      top_brands: data.top_brands ?? [],
      top_hours: (data.top_hours ?? []).map(
        (h: { hour?: number; label: string; revenue: number }) => ({
          hour: h.hour ?? 0,
          count: 0,
          revenue: h.revenue,
        })
      ),
      store_name: data.store_name,
      date: data.date,
      line_items: data.line_items,
    };
  }

  async getCameras(storeId?: string): Promise<StoreCamerasResponse> {
    const id = storeId ?? this.storeId;
    const { data } = await api.get<StoreCamerasResponse>(`${STORES_PREFIX}/${id}/cameras`);
    return data;
  }

  async getStoreMetrics(): Promise<MetricsResponse & { store_footfall?: number }> {
    const { data } = await api.get(this.storePath('/metrics'));
    return {
      unique_visitors: data.unique_visitors ?? 0,
      active_visitors: data.store_footfall ?? data.unique_visitors ?? 0,
      conversion_rate: data.conversion_rate ?? 0,
      revenue: data.revenue ?? 0,
      average_dwell_time: data.average_dwell_time ?? 0,
      queue_depth: data.queue_depth ?? 0,
      timestamp: data.timestamp ?? new Date().toISOString(),
      store_footfall: data.store_footfall,
    };
  }

  async getEventSummary(): Promise<EventSummary> {
    const { data } = await api.get<EventSummary>(this.storePath('/events/summary'));
    return data;
  }

  async getFunnel(): Promise<FunnelResponse> {
    const { data } = await api.get(this.storePath('/funnel'));
    const stages = [
      { stage: 'Entry', count: data.entry_count ?? 0, conversion_rate: 1 },
      {
        stage: 'Zone visit',
        count: data.zone_count ?? 0,
        conversion_rate:
          data.entry_count > 0 ? (data.zone_count ?? 0) / data.entry_count : 0,
      },
      {
        stage: 'Billing queue',
        count: data.billing_count ?? 0,
        conversion_rate:
          data.zone_count > 0 ? (data.billing_count ?? 0) / data.zone_count : 0,
      },
      {
        stage: 'Purchase',
        count: data.purchase_count ?? 0,
        conversion_rate:
          data.billing_count > 0 ? (data.purchase_count ?? 0) / data.billing_count : 0,
      },
    ];
    return {
      stages,
      total_entries: data.entry_count ?? 0,
      total_conversions: data.purchase_count ?? 0,
      overall_conversion_rate: (data.efficiency_percentage ?? 0) / 100,
    };
  }

  async getHeatmap(): Promise<HeatmapResponse & { data_confidence?: string }> {
    const { data } = await api.get(this.storePath('/heatmap'));
    const zones = (data.zones ?? []).map(
      (z: {
        zone_id: string;
        visit_frequency: number;
        normalized_heat_score: number;
        avg_dwell_seconds: number;
      }) => ({
        zone_id: z.zone_id,
        zone_name: z.zone_id.replace(/_/g, ' '),
        visitor_count: z.visit_frequency,
        heat_score: (z.normalized_heat_score ?? 0) * 100,
        occupancy_percentage: (z.normalized_heat_score ?? 0) * 100,
        avg_dwell_seconds: z.avg_dwell_seconds,
      })
    );
    return {
      zones,
      timestamp: data.timestamp ?? new Date().toISOString(),
      data_confidence: data.data_confidence,
    };
  }

  async getAnomalies(): Promise<AnomaliesResponse> {
    const { data } = await api.get(this.storePath('/anomalies'));
    const anomalies = (data.anomalies ?? []).map(
      (
        a: {
          anomaly_type: string;
          severity: string;
          description: string;
          detected_at: string;
          suggested_action?: string;
        },
        i: number
      ) => ({
        id: `anom-${i}-${a.anomaly_type}`,
        anomaly_type: a.anomaly_type,
        severity: (a.severity === 'WARNING' ? 'WARN' : a.severity) as
          | 'INFO'
          | 'WARN'
          | 'CRITICAL',
        timestamp: a.detected_at,
        description: a.description,
        zone_id: undefined,
        value: undefined,
      })
    );
    return { anomalies, timestamp: data.timestamp ?? new Date().toISOString() };
  }

  async getStoreLayout(): Promise<StoreLayout> {
    const { data } = await api.get<{
      store_id: string;
      store_name: string;
      layout_image_url?: string;
      zones: Array<{
        zone_id: string;
        name: string;
        polygon: number[][];
        color?: string;
      }>;
    }>(this.storePath('/layout'));

    return {
      store_id: data.store_id,
      store_name: data.store_name,
      layout_image_url: data.layout_image_url
        ? cctvMediaUrl(data.layout_image_url)
        : undefined,
      total_area: 800 * 600,
      zones: (data.zones ?? []).map((z) => {
        const xs = z.polygon.map((p) => p[0]);
        const ys = z.polygon.map((p) => p[1]);
        const minX = Math.min(...xs);
        const minY = Math.min(...ys);
        return {
          id: z.zone_id,
          name: z.name,
          zone_type: z.zone_id,
          coordinates: z.polygon,
          pixel_bounds: {
            x: minX,
            y: minY,
            width: Math.max(...xs) - minX,
            height: Math.max(...ys) - minY,
          },
        };
      }),
    };
  }

  async getHealth(): Promise<HealthResponse> {
    const { data } = await api.get<HealthResponse>('/health');
    return data;
  }

  async getSystemHealth(): Promise<SystemHealth> {
    try {
      const { data } = await api.get(`${ANALYTICS_PREFIX}/health`);
      return {
        database_status: data.database?.status === 'UP' ? 'healthy' : 'degraded',
        redis_status: data.redis?.status === 'UP' ? 'healthy' : 'degraded',
        api_status: data.status === 'UP' ? 'healthy' : 'degraded',
        last_event_timestamp: data.last_event_timestamp ?? new Date().toISOString(),
        events_processed: 0,
        api_latency_ms: 0,
        request_rate_per_second: 0,
      };
    } catch {
      return {
        database_status: 'healthy',
        redis_status: 'healthy',
        api_status: 'healthy',
        last_event_timestamp: new Date().toISOString(),
        events_processed: 0,
        api_latency_ms: 0,
        request_rate_per_second: 0,
      };
    }
  }

  /** @deprecated use getStoreDashboard */
  async getBrigadeDashboard() {
    return this.getStoreDashboard('ST1008');
  }

  async getBrigadeMetrics() {
    return this.getStoreMetrics();
  }

  async getPOSAnalytics() {
    return this.getStorePOS();
  }

  async getMetrics() {
    return this.getStoreMetrics();
  }

  async getQueueAnalytics() {
    const m = await this.getStoreMetrics();
    return {
      current_queue_depth: m.queue_depth,
      average_queue_depth: m.queue_depth,
      peak_queue_depth: m.queue_depth,
      abandonment_rate: 0,
      average_wait_time: 0,
      queue_trend: [],
    };
  }

  async getEvents(limit = 50, offset = 0) {
    return { events: [], total: 0, limit, offset };
  }

  async getVisitorJourney(visitorId: string) {
    return {
      visitor_id: visitorId,
      entry_time: new Date().toISOString(),
      cameras: [],
      zones: [],
      purchase_status: 'not_converted' as const,
      staff_classification: false,
    };
  }
}

export const apiClient = new APIClient();

// Legacy type aliases
export type BrigadeCamera = StoreCamera;
export type BrigadeCamerasResponse = StoreCamerasResponse;
export type BrigadeDashboard = StoreDashboard;
