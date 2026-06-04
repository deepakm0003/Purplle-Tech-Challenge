import { useQuery, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../services/apiClient';
import { useStore } from '../context/StoreContext';
import {
  MetricsResponse,
  HealthResponse,
  FunnelResponse,
  HeatmapResponse,
  AnomaliesResponse,
  EventsResponse,
  StoreLayout,
  QueueAnalytics,
  SystemHealth,
  POSAnalytics,
  VisitorJourney,
} from '../types';
import type { StoreCamerasResponse } from '../services/apiClient';

export const queryKeys = {
  metrics: (storeId: string) => ['metrics', storeId] as const,
  storeMetrics: (storeId: string) => ['storeMetrics', storeId] as const,
  eventSummary: (storeId: string) => ['eventSummary', storeId] as const,
  funnel: (storeId: string) => ['funnel', storeId] as const,
  heatmap: (storeId: string) => ['heatmap', storeId] as const,
  anomalies: (storeId: string) => ['anomalies', storeId] as const,
  events: (storeId: string, limit: number, offset: number) =>
    ['events', storeId, limit, offset] as const,
  cameras: (storeId: string) => ['cameras', storeId] as const,
  dashboard: (storeId: string) => ['dashboard', storeId] as const,
  health: ['health'] as const,
  storeLayout: (storeId: string) => ['storeLayout', storeId] as const,
  queueAnalytics: (storeId: string) => ['queueAnalytics', storeId] as const,
  systemHealth: ['systemHealth'] as const,
  posAnalytics: (storeId: string) => ['posAnalytics', storeId] as const,
  visitorJourney: (id: string) => ['visitorJourney', id] as const,
};

export const useStoreMetrics = () => {
  const { storeId } = useStore();
  return useQuery<MetricsResponse>({
    queryKey: queryKeys.storeMetrics(storeId),
    queryFn: () => apiClient.getStoreMetrics(),
    refetchInterval: 5000,
    staleTime: 2000,
    retry: 2,
  });
};

export const useEventSummary = () => {
  const { storeId } = useStore();
  return useQuery({
    queryKey: queryKeys.eventSummary(storeId),
    queryFn: () => apiClient.getEventSummary(),
    refetchInterval: 8000,
    retry: 1,
  });
};

export const useStoreDashboard = () => {
  const { storeId } = useStore();
  return useQuery({
    queryKey: queryKeys.dashboard(storeId),
    queryFn: () => apiClient.getStoreDashboard(),
    staleTime: 60_000,
  });
};

export const useMetrics = () => useStoreMetrics();

export const useFunnel = () => {
  const { storeId } = useStore();
  return useQuery<FunnelResponse>({
    queryKey: queryKeys.funnel(storeId),
    queryFn: () => apiClient.getFunnel(),
    refetchInterval: 10000,
    staleTime: 5000,
    retry: 2,
  });
};

export const useHeatmap = () => {
  const { storeId } = useStore();
  return useQuery<HeatmapResponse>({
    queryKey: queryKeys.heatmap(storeId),
    queryFn: () => apiClient.getHeatmap(),
    refetchInterval: 8000,
    staleTime: 4000,
    retry: 2,
  });
};

export const useAnomalies = () => {
  const { storeId } = useStore();
  return useQuery<AnomaliesResponse>({
    queryKey: queryKeys.anomalies(storeId),
    queryFn: () => apiClient.getAnomalies(),
    refetchInterval: 5000,
    staleTime: 2000,
    retry: 2,
  });
};

export const useEvents = (limit: number = 50, offset: number = 0) => {
  const { storeId } = useStore();
  return useQuery<EventsResponse>({
    queryKey: queryKeys.events(storeId, limit, offset),
    queryFn: () => apiClient.getEvents(limit, offset),
    refetchInterval: 3000,
    staleTime: 1000,
    retry: 2,
  });
};

export const useCameras = () => {
  const { storeId } = useStore();
  return useQuery<StoreCamerasResponse>({
    queryKey: queryKeys.cameras(storeId),
    queryFn: () => apiClient.getCameras(),
    staleTime: 30_000,
    refetchInterval: 15_000,
    retry: 2,
  });
};

export const useHealth = () => {
  return useQuery<HealthResponse>({
    queryKey: queryKeys.health,
    queryFn: () => apiClient.getHealth(),
    refetchInterval: 10000,
    staleTime: 5000,
    retry: 1,
  });
};

export const useStoreLayout = () => {
  const { storeId } = useStore();
  return useQuery<StoreLayout>({
    queryKey: queryKeys.storeLayout(storeId),
    queryFn: () => apiClient.getStoreLayout(),
    staleTime: Infinity,
    retry: 2,
  });
};

export const useQueueAnalytics = () => {
  const { storeId } = useStore();
  return useQuery<QueueAnalytics>({
    queryKey: queryKeys.queueAnalytics(storeId),
    queryFn: () => apiClient.getQueueAnalytics(),
    refetchInterval: 5000,
    staleTime: 2000,
    retry: 2,
  });
};

export const useSystemHealth = () => {
  return useQuery<SystemHealth>({
    queryKey: queryKeys.systemHealth,
    queryFn: () => apiClient.getSystemHealth(),
    refetchInterval: 10000,
    staleTime: 5000,
    retry: 2,
  });
};

export const usePOSAnalytics = () => {
  const { storeId } = useStore();
  return useQuery<POSAnalytics>({
    queryKey: queryKeys.posAnalytics(storeId),
    queryFn: () => apiClient.getPOSAnalytics(),
    refetchInterval: 30000,
    staleTime: 10000,
    retry: 2,
  });
};

export const useVisitorJourney = (visitorId: string) => {
  return useQuery<VisitorJourney>({
    queryKey: queryKeys.visitorJourney(visitorId),
    queryFn: () => apiClient.getVisitorJourney(visitorId),
    enabled: !!visitorId,
    retry: 2,
  });
};

export const useRefreshData = () => {
  const queryClient = useQueryClient();
  const { storeId } = useStore();

  return {
    refetchMetrics: () =>
      queryClient.refetchQueries({ queryKey: queryKeys.storeMetrics(storeId) }),
    refetchFunnel: () =>
      queryClient.refetchQueries({ queryKey: queryKeys.funnel(storeId) }),
    refetchHeatmap: () =>
      queryClient.refetchQueries({ queryKey: queryKeys.heatmap(storeId) }),
    refetchAnomalies: () =>
      queryClient.refetchQueries({ queryKey: queryKeys.anomalies(storeId) }),
    refetchAll: () => queryClient.refetchQueries(),
  };
};
