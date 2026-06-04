import React, { useMemo } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import { AlertCircle, TrendingUp } from 'lucide-react';
import { useQueueAnalytics } from '../hooks/useAPI.ts';
import { ChartContainer, LoadingState, ErrorState, Skeleton } from '../components/common/UIElements';
import { formatNumber } from '../utils/formatters';

export const QueueManagement: React.FC = () => {
  const { data: queue, isLoading, error } = useQueueAnalytics();

  if (error) {
    return (
      <ErrorState
        title="Failed to load queue data"
        message="Unable to fetch queue analytics"
      />
    );
  }

  const queueTrendData = useMemo(() => {
    if (!queue?.queue_trend) return [];
    return queue.queue_trend.slice(-24).map((item) => ({
      time: new Date(item.timestamp).toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
      }),
      depth: item.depth,
    }));
  }, [queue]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Queue Management</h1>

      {/* Warning Alert */}
      {queue && queue.current_queue_depth > queue.average_queue_depth * 1.5 && (
        <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-4 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400 flex-shrink-0 mt-0.5" />
          <div>
            <h3 className="font-semibold text-yellow-900 dark:text-yellow-100">
              Queue Alert
            </h3>
            <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
              Current queue depth ({queue.current_queue_depth}) is significantly higher than average
              ({queue.average_queue_depth.toFixed(1)}). Consider opening additional checkout counters.
            </p>
          </div>
        </div>
      )}

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="card p-6 bg-primary-50 dark:bg-primary-900/20">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">Current Queue Depth</p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-slate-900 dark:text-white">
              {isLoading ? <Skeleton className="w-16 h-8" /> : formatNumber(queue?.current_queue_depth ?? 0)}
            </p>
            <span className="text-sm text-slate-600 dark:text-slate-400">people</span>
          </div>
        </div>

        <div className="card p-6 bg-blue-50 dark:bg-blue-900/20">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">Average Queue Depth</p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-slate-900 dark:text-white">
              {isLoading ? <Skeleton className="w-16 h-8" /> : (queue?.average_queue_depth ?? 0).toFixed(1)}
            </p>
            <span className="text-sm text-slate-600 dark:text-slate-400">people</span>
          </div>
        </div>

        <div className="card p-6 bg-red-50 dark:bg-red-900/20">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">Peak Queue Depth</p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-slate-900 dark:text-white">
              {isLoading ? <Skeleton className="w-16 h-8" /> : formatNumber(queue?.peak_queue_depth ?? 0)}
            </p>
            <span className="text-sm text-slate-600 dark:text-slate-400">people</span>
          </div>
        </div>

        <div className="card p-6 bg-orange-50 dark:bg-orange-900/20">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">Abandonment Rate</p>
          <div className="flex items-baseline gap-2">
            <p className="text-3xl font-bold text-slate-900 dark:text-white">
              {isLoading ? <Skeleton className="w-16 h-8" /> : ((queue?.abandonment_rate ?? 0) * 100).toFixed(1)}
            </p>
            <span className="text-sm text-slate-600 dark:text-slate-400">%</span>
          </div>
        </div>
      </div>

      {/* Queue Trend Chart */}
      <ChartContainer title="Queue Depth Trend (Last 24 Hours)">
        <LoadingState isLoading={isLoading}>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={queueTrendData}>
              <defs>
                <linearGradient id="colorQueue" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#f59e0b" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#f59e0b" stopOpacity={0} />
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
              <Line
                type="monotone"
                dataKey="depth"
                stroke="#f59e0b"
                dot={false}
                strokeWidth={2}
                isAnimationActive={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </LoadingState>
      </ChartContainer>

      {/* Queue Statistics */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">Queue Statistics</h3>
        <LoadingState isLoading={isLoading}>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Average Wait Time</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {queue?.average_wait_time ? `${queue.average_wait_time.toFixed(1)}m` : '—'}
                </p>
              </div>
              <TrendingUp className="w-8 h-8 text-primary-500" />
            </div>

            <div className="flex items-center justify-between p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
              <div>
                <p className="text-sm text-slate-600 dark:text-slate-400">Queue Efficiency</p>
                <p className="text-2xl font-bold text-slate-900 dark:text-white">
                  {((1 - (queue?.abandonment_rate ?? 0)) * 100).toFixed(1)}%
                </p>
              </div>
              <div
                className="w-12 h-12 rounded-full flex items-center justify-center"
                style={{
                  background: `conic-gradient(#10b981 0deg ${((1 - (queue?.abandonment_rate ?? 0)) * 100) * 3.6}deg, #e5e7eb ${((1 - (queue?.abandonment_rate ?? 0)) * 100) * 3.6}deg)`,
                }}
              >
                <div className="w-10 h-10 rounded-full bg-white dark:bg-slate-900" />
              </div>
            </div>

            <div className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50">
              <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">Queue Status</p>
              <div className="flex items-center gap-2">
                <div
                  className={`w-3 h-3 rounded-full ${
                    queue && queue.current_queue_depth < 5
                      ? 'bg-emerald-500'
                      : queue && queue.current_queue_depth < 15
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                  }`}
                />
                <span className="text-sm text-slate-600 dark:text-slate-400">
                  {queue && queue.current_queue_depth < 5
                    ? 'Low - Store is operating smoothly'
                    : queue && queue.current_queue_depth < 15
                      ? 'Moderate - Consider opening more counters'
                      : 'High - Immediate action recommended'}
                </span>
              </div>
            </div>
          </div>
        </LoadingState>
      </div>

      {/* Recommendations */}
      <div className="card p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <h3 className="text-lg font-semibold text-blue-900 dark:text-blue-100 mb-3">Recommendations</h3>
        <ul className="space-y-2 text-sm text-blue-800 dark:text-blue-200">
          <li>• Monitor queue depth during peak hours (11 AM - 2 PM, 6 PM - 8 PM)</li>
          <li>• Consider implementing self-checkout to reduce wait times</li>
          <li>• Train staff on express lane procedures for customers with few items</li>
          <li>• Current abandonment rate suggests customer satisfaction concerns</li>
        </ul>
      </div>
    </div>
  );
};
