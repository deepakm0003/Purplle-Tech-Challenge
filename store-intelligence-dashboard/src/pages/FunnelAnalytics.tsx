import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from 'recharts';
import { useFunnel } from '../hooks/useAPI.ts';
import { ChartContainer, LoadingState, ErrorState, ProgressBar, Skeleton } from '../components/common/UIElements';
import { formatNumber, formatPercentage } from '../utils/formatters';

export const FunnelAnalytics: React.FC = () => {
  const { data: funnel, isLoading, error } = useFunnel();

  if (error) {
    return (
      <ErrorState
        title="Failed to load funnel data"
        message="Unable to fetch conversion funnel analytics"
      />
    );
  }

  const stages = funnel?.stages || [];
  const colors = ['#a855f7', '#8b5cf6', '#7c3aed', '#6d28d9'];

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Funnel Analytics</h1>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-6 bg-primary-50 dark:bg-primary-900/20">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Total Entries</p>
          <p className="text-3xl font-bold text-slate-900 dark:text-white">
            {isLoading ? (
              <Skeleton className="w-24 h-8" />
            ) : (
              formatNumber(funnel?.total_entries ?? 0)
            )}
          </p>
        </div>
        <div className="card p-6 bg-emerald-50 dark:bg-emerald-900/20">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Total Conversions</p>
          <p className="text-3xl font-bold text-slate-900 dark:text-white">
            {isLoading ? (
              <Skeleton className="w-24 h-8" />
            ) : (
              formatNumber(funnel?.total_conversions ?? 0)
            )}
          </p>
        </div>
        <div className="card p-6 bg-blue-50 dark:bg-blue-900/20">
          <p className="text-sm text-slate-600 dark:text-slate-400 mb-1">Conversion Rate</p>
          <p className="text-3xl font-bold text-slate-900 dark:text-white">
            {isLoading ? (
              <Skeleton className="w-24 h-8" />
            ) : (
              formatPercentage(funnel?.overall_conversion_rate ?? 0)
            )}
          </p>
        </div>
      </div>

      {/* Funnel Chart */}
      <ChartContainer title="Conversion Funnel">
        <LoadingState isLoading={isLoading}>
          <ResponsiveContainer width="100%" height={400}>
            <BarChart
              data={stages}
              margin={{ top: 20, right: 30, left: 0, bottom: 60 }}
              layout="vertical"
            >
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis type="number" stroke="#94a3b8" />
              <YAxis dataKey="stage" type="category" stroke="#94a3b8" width={100} />
              <Tooltip
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                }}
              />
              <Bar dataKey="count" radius={[0, 8, 8, 0]}>
                {stages.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </LoadingState>
      </ChartContainer>

      {/* Stage Details */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-6">
          Stage Details
        </h3>
        <LoadingState isLoading={isLoading}>
          <div className="space-y-6">
            {stages.map((stage, index) => (
              <div key={stage.stage}>
                <div className="flex items-baseline justify-between mb-3">
                  <h4 className="font-medium text-slate-900 dark:text-white">
                    {index + 1}. {stage.stage}
                  </h4>
                  <span className="text-sm text-slate-600 dark:text-slate-400">
                    {formatNumber(stage.count)} visitors
                  </span>
                </div>

                <ProgressBar
                  value={stage.count}
                  max={stages[0].count}
                  color={index === 0 ? 'primary' : index === 1 ? 'success' : index === 2 ? 'warning' : 'danger'}
                />

                <div className="flex items-center justify-between mt-2 text-xs text-slate-600 dark:text-slate-400">
                  <span>Conversion Rate</span>
                  <span className="font-medium text-slate-900 dark:text-white">
                    {formatPercentage(stage.conversion_rate)}
                  </span>
                </div>

                {index < stages.length - 1 && (
                  <div className="mt-4 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                    <p className="text-xs font-medium text-slate-700 dark:text-slate-300">
                      Drop-off to next stage:{' '}
                      <span className="text-red-600 dark:text-red-400">
                        {formatNumber(stage.count - stages[index + 1].count)} visitors
                        ({formatPercentage(
                          1 - stages[index + 1].count / stage.count
                        )})
                      </span>
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </LoadingState>
      </div>

      {/* Insights */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="card p-6 bg-blue-50 dark:bg-blue-900/20">
          <h4 className="font-medium text-slate-900 dark:text-white mb-3">Key Insight</h4>
          <LoadingState isLoading={isLoading}>
            {stages.length >= 2 && (
              <p className="text-sm text-slate-600 dark:text-slate-400">
                Largest drop-off occurs between{' '}
                <span className="font-medium text-slate-900 dark:text-white">
                  {stages[0].stage}
                </span>{' '}
                and{' '}
                <span className="font-medium text-slate-900 dark:text-white">
                  {stages[1].stage}
                </span>{' '}
                with{' '}
                <span className="text-red-600 dark:text-red-400 font-medium">
                  {formatPercentage(1 - stages[1].count / stages[0].count)}
                </span>{' '}
                conversion loss.
              </p>
            )}
          </LoadingState>
        </div>

        <div className="card p-6 bg-emerald-50 dark:bg-emerald-900/20">
          <h4 className="font-medium text-slate-900 dark:text-white mb-3">Opportunity</h4>
          <p className="text-sm text-slate-600 dark:text-slate-400">
            Focus optimization efforts on the first stage where customer interest is highest.
            Even a 5% improvement here could yield significant gains downstream.
          </p>
        </div>
      </div>
    </div>
  );
};
