import React, { useMemo } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import {
  Users,
  TrendingUp,
  ShoppingCart,
  Clock,
  AlertCircle,
} from 'lucide-react';
import {
  useMetrics,
  useAnomalies,
  useRefreshData,
} from '../hooks/useAPI.ts';
import {
  MetricCard,
  LoadingState,
  ErrorState,
  ChartContainer,
} from '../components/common/UIElements';
import { formatNumber, formatCurrency, formatPercentage, formatRelativeTime } from '../utils/formatters';

// Mock time series data - would come from API in production
const generateTimeSeriesData = () => {
  const data = [];
  for (let i = 24; i >= 0; i--) {
    const now = new Date();
    now.setHours(now.getHours() - i);
    data.push({
      time: now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }),
      visitors: Math.floor(Math.random() * 500) + 100,
      conversions: Math.floor(Math.random() * 150) + 20,
      revenue: Math.floor(Math.random() * 50000) + 10000,
    });
  }
  return data;
};

export const IntelligenceSection: React.FC = () => {
  const { data: metrics, isLoading: metricsLoading, error: metricsError } = useMetrics();
  const { data: anomalies, isLoading: anomaliesLoading } = useAnomalies();
  const { refetchAll } = useRefreshData();
  const timeSeriesData = useMemo(() => generateTimeSeriesData(), []);

  const handleRefresh = () => {
    refetchAll();
  };

  if (metricsError) {
    return (
      <ErrorState
        title="Failed to load metrics"
        message="Unable to fetch store intelligence metrics. Please try again."
        onRetry={handleRefresh}
      />
    );
  }

  const criticalAnomalies = anomalies?.anomalies.filter((a) => a.severity === 'CRITICAL') || [];

  return (
    <div className="space-y-6">
      {/* Critical Alerts */}
      {criticalAnomalies.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-red-600 dark:text-red-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-red-900 dark:text-red-100">
              {criticalAnomalies.length} Critical Alert{criticalAnomalies.length > 1 ? 's' : ''}
            </h3>
            <p className="text-sm text-red-700 dark:text-red-300 mt-1">
              {criticalAnomalies[0]?.description}
            </p>
          </div>
        </div>
      )}

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          title="Total Visitors"
          value={metricsLoading ? '-' : formatNumber(metrics?.unique_visitors ?? 0)}
          unit="today"
          icon={<Users className="w-5 h-5" />}
          trend={12.5}
          trendLabel="vs yesterday"
          color="primary"
          isLoading={metricsLoading}
        />
        <MetricCard
          title="Active Visitors"
          value={metricsLoading ? '-' : formatNumber(metrics?.active_visitors ?? 0)}
          unit="right now"
          icon={<Users className="w-5 h-5" />}
          trend={8.2}
          trendLabel="vs 1h ago"
          color="success"
          isLoading={metricsLoading}
        />
        <MetricCard
          title="Conversion Rate"
          value={metricsLoading ? '-' : formatPercentage(metrics?.conversion_rate ?? 0)}
          trend={-2.3}
          trendLabel="vs yesterday"
          icon={<ShoppingCart className="w-5 h-5" />}
          color="warning"
          isLoading={metricsLoading}
        />
        <MetricCard
          title="Revenue"
          value={metricsLoading ? '-' : formatCurrency(metrics?.revenue ?? 0)}
          unit="today"
          icon={<TrendingUp className="w-5 h-5" />}
          trend={15.8}
          trendLabel="vs yesterday"
          color="success"
          isLoading={metricsLoading}
        />
        <MetricCard
          title="Avg Dwell Time"
          value={metricsLoading ? '-' : `${(metrics?.average_dwell_time ?? 0).toFixed(1)}m`}
          trend={-5.2}
          trendLabel="vs yesterday"
          icon={<Clock className="w-5 h-5" />}
          color="primary"
          isLoading={metricsLoading}
        />
        <MetricCard
          title="Queue Depth"
          value={metricsLoading ? '-' : formatNumber(metrics?.queue_depth ?? 0)}
          unit="at billing"
          trend={22.1}
          trendLabel="vs 1h ago"
          icon={<AlertCircle className="w-5 h-5" />}
          color="danger"
          isLoading={metricsLoading}
        />
      </div>

      {/* Time Series Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartContainer title="Visitor Trend" isLoading={metricsLoading}>
          <ResponsiveContainer width="100%" height={300}>
            <AreaChart data={timeSeriesData}>
              <defs>
                <linearGradient id="colorVisitors" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#a855f7" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#a855f7" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="time" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                }}
              />
              <Area
                type="monotone"
                dataKey="visitors"
                stroke="#a855f7"
                fillOpacity={1}
                fill="url(#colorVisitors)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </ChartContainer>

        <ChartContainer title="Revenue Trend" isLoading={metricsLoading}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={timeSeriesData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="time" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                }}
              />
              <Legend />
              <Line
                type="monotone"
                dataKey="revenue"
                stroke="#10b981"
                dot={false}
                strokeWidth={2}
              />
              <Line
                type="monotone"
                dataKey="conversions"
                stroke="#f59e0b"
                dot={false}
                strokeWidth={2}
              />
            </LineChart>
          </ResponsiveContainer>
        </ChartContainer>
      </div>

      {/* Recent Anomalies */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          Recent Anomalies
        </h3>
        <LoadingState isLoading={anomaliesLoading}>
          {anomalies && anomalies.anomalies.length > 0 ? (
            <div className="space-y-3">
              {anomalies.anomalies.slice(0, 5).map((anomaly) => (
                <div
                  key={anomaly.id}
                  className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50"
                >
                  <div
                    className={`w-2 h-2 rounded-full mt-1.5 flex-shrink-0 ${
                      anomaly.severity === 'CRITICAL'
                        ? 'bg-red-500'
                        : anomaly.severity === 'WARN'
                          ? 'bg-yellow-500'
                          : 'bg-blue-500'
                    }`}
                  />
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-slate-900 dark:text-white">
                      {anomaly.anomaly_type}
                    </p>
                    <p className="text-sm text-slate-600 dark:text-slate-400 truncate">
                      {anomaly.description}
                    </p>
                    <p className="text-xs text-slate-500 dark:text-slate-500 mt-1">
                      {formatRelativeTime(anomaly.timestamp)}
                    </p>
                  </div>
                  <span
                    className={`text-xs font-semibold px-2 py-1 rounded-full flex-shrink-0 ${
                      anomaly.severity === 'CRITICAL'
                        ? 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300'
                        : anomaly.severity === 'WARN'
                          ? 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300'
                          : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300'
                    }`}
                  >
                    {anomaly.severity}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-slate-600 dark:text-slate-400">No anomalies detected</p>
          )}
        </LoadingState>
      </div>

      {/* Last Updated */}
      <p className="text-xs text-slate-500 dark:text-slate-400 text-right">
        Last updated: {metrics?.timestamp ? formatRelativeTime(metrics.timestamp) : 'loading...'}
      </p>
    </div>
  );
};

/** @deprecated Use IntelligenceSection inside Sales page */
export const ExecutiveOverview: React.FC = () => (
  <div className="space-y-6">
    <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Executive Overview</h1>
    <IntelligenceSection />
  </div>
);
