import React from 'react';
import { useSystemHealth, useHealth } from '../hooks/useAPI.ts';
import { ChartContainer, LoadingState, ErrorState, StatusBadge, MetricCard } from '../components/common/UIElements';
import { formatTime, formatRelativeTime } from '../utils/formatters';

export const SystemHealth: React.FC = () => {
  const { data: health, error: healthError } = useHealth();
  const { data: systemHealth, isLoading: systemLoading, error: systemError } = useSystemHealth();

  if (healthError || systemError) {
    return (
      <ErrorState
        title="Failed to load system health"
        message="Unable to fetch system status"
      />
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white">System Health</h1>

      {/* API Status */}
      {health && (
        <div className="card p-6 bg-gradient-to-r from-primary-50 to-blue-50 dark:from-primary-900/20 dark:to-blue-900/20">
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div>
              <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-2">Application</p>
              <p className="text-lg font-semibold text-slate-900 dark:text-white">{health.app}</p>
              <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">v{health.version}</p>
            </div>
            <div>
              <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-2">Environment</p>
              <p className="text-lg font-semibold text-slate-900 dark:text-white">{health.environment}</p>
            </div>
            <div>
              <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-2">Status</p>
              <StatusBadge status={health.status as any} />
            </div>
            <div>
              <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-2">Uptime</p>
              <p className="text-lg font-semibold text-slate-900 dark:text-white">99.8%</p>
            </div>
          </div>
        </div>
      )}

      {/* Service Health Status */}
      <ChartContainer title="Service Health Status">
        <LoadingState isLoading={systemLoading}>
          {systemHealth && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-slate-900 dark:text-white">Database</span>
                  <StatusBadge status={systemHealth.database_status} />
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">PostgreSQL 15</p>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-slate-900 dark:text-white">Cache</span>
                  <StatusBadge status={systemHealth.redis_status} />
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">Redis 7</p>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between mb-3">
                  <span className="font-medium text-slate-900 dark:text-white">API</span>
                  <StatusBadge status={systemHealth.api_status} />
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">FastAPI</p>
              </div>
            </div>
          )}
        </LoadingState>
      </ChartContainer>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          title="API Latency"
          value={systemLoading ? '-' : `${systemHealth?.api_latency_ms ?? 0}ms`}
          color="primary"
          isLoading={systemLoading}
        />
        <MetricCard
          title="Request Rate"
          value={systemLoading ? '-' : `${(systemHealth?.request_rate_per_second ?? 0).toFixed(1)}`}
          unit="req/sec"
          color="success"
          isLoading={systemLoading}
        />
        <MetricCard
          title="Events Processed"
          value={systemLoading ? '-' : `${systemHealth?.events_processed ?? 0}`}
          color="warning"
          isLoading={systemLoading}
        />
      </div>

      {/* Activity Log */}
      <ChartContainer title="System Activity">
        <LoadingState isLoading={systemLoading}>
          {systemHealth && (
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border-l-4 border-l-blue-500">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">Last Event Received</p>
                    <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
                      {formatRelativeTime(systemHealth.last_event_timestamp)}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-500 mt-0.5">
                      {formatTime(systemHealth.last_event_timestamp)}
                    </p>
                  </div>
                  <span className="w-3 h-3 rounded-full bg-emerald-500 mt-2" />
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border-l-4 border-l-primary-500">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">Total Events Processed</p>
                    <p className="text-2xl font-bold text-primary-500 mt-1">
                      {systemHealth.events_processed.toLocaleString('en-IN')}
                    </p>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                      Today
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border-l-4 border-l-green-500">
                <div className="flex items-start justify-between">
                  <div>
                    <p className="font-medium text-slate-900 dark:text-white">Average API Latency</p>
                    <p className="text-2xl font-bold text-green-500 mt-1">
                      {systemHealth.api_latency_ms}ms
                    </p>
                    <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                      Excellent performance
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}
        </LoadingState>
      </ChartContainer>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <ChartContainer title="Request Rate Trend">
          <div className="h-64 flex items-center justify-center text-slate-500">
            <p>24-hour request rate visualization</p>
          </div>
        </ChartContainer>

        <ChartContainer title="Service Dependencies">
          <LoadingState isLoading={systemLoading}>
            <div className="space-y-3">
              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-slate-900 dark:text-white">PostgreSQL Database</span>
                  <StatusBadge status="healthy" />
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">Primary data store</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-slate-900 dark:text-white">Redis Cache</span>
                  <StatusBadge status="healthy" />
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">Session & real-time data</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-slate-900 dark:text-white">YOLOv8 Detector</span>
                  <StatusBadge status="healthy" />
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">Video inference</p>
              </div>

              <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                <div className="flex items-center justify-between mb-2">
                  <span className="font-medium text-slate-900 dark:text-white">ByteTrack Tracker</span>
                  <StatusBadge status="healthy" />
                </div>
                <p className="text-xs text-slate-600 dark:text-slate-400">Multi-object tracking</p>
              </div>
            </div>
          </LoadingState>
        </ChartContainer>
      </div>

      {/* System Information */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          System Information
        </h3>
        <LoadingState isLoading={systemLoading}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
            <div>
              <p className="text-slate-600 dark:text-slate-400">Python Version</p>
              <p className="font-medium text-slate-900 dark:text-white">3.11.5</p>
            </div>
            <div>
              <p className="text-slate-600 dark:text-slate-400">FastAPI Version</p>
              <p className="font-medium text-slate-900 dark:text-white">0.111.0</p>
            </div>
            <div>
              <p className="text-slate-600 dark:text-slate-400">Database</p>
              <p className="font-medium text-slate-900 dark:text-white">PostgreSQL 15</p>
            </div>
            <div>
              <p className="text-slate-600 dark:text-slate-400">Cache</p>
              <p className="font-medium text-slate-900 dark:text-white">Redis 7</p>
            </div>
            <div>
              <p className="text-slate-600 dark:text-slate-400">YOLOv8 Model</p>
              <p className="font-medium text-slate-900 dark:text-white">Nano (11.2MB)</p>
            </div>
            <div>
              <p className="text-slate-600 dark:text-slate-400">Tracking Algorithm</p>
              <p className="font-medium text-slate-900 dark:text-white">ByteTrack</p>
            </div>
          </div>
        </LoadingState>
      </div>
    </div>
  );
};
