import React, { useMemo } from 'react';
import {
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  LineChart,
  Line,
} from 'recharts';
import { RefreshCw } from 'lucide-react';
import { usePOSAnalytics, useRefreshData } from '../hooks/useAPI.ts';
import { useStore } from '../context/StoreContext';
import { IntelligenceSection } from './ExecutiveOverview';
import { ChartContainer, LoadingState, ErrorState, MetricCard } from '../components/common/UIElements';
import { formatCurrency, formatNumber } from '../utils/formatters';

export const POSAnalytics: React.FC = () => {
  const { storeName } = useStore();
  const { data: pos, isLoading, error } = usePOSAnalytics();
  const { refetchAll } = useRefreshData();

  if (error) {
    return (
      <ErrorState
        title="Failed to load sales data"
        message="Unable to fetch POS and intelligence analytics"
        onRetry={() => refetchAll()}
      />
    );
  }

  const topProductsData = useMemo(() => {
    return (pos?.top_products || []).slice(0, 5);
  }, [pos]);

  const topBrandsData = useMemo(() => {
    return (pos?.top_brands || []).slice(0, 5);
  }, [pos]);

  const topHoursData = useMemo(() => {
    return (pos?.top_hours || []).map((h) => ({
      ...h,
      hour:
        'label' in h && typeof (h as { label?: string }).label === 'string'
          ? (h as { label: string }).label
          : `${String(h.hour).padStart(2, '0')}:00`,
    }));
  }, [pos]);

  const COLORS = ['#a855f7', '#8b5cf6', '#7c3aed', '#6d28d9', '#5b21b6'];

  return (
    <div className="space-y-10">
      <div className="flex flex-wrap justify-between items-start gap-4">
        <div>
          <p className="text-sm text-primary-600 dark:text-primary-400 font-medium">
            {pos?.store_name ?? storeName} · {pos?.date ?? '—'}
          </p>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Sales & Intelligence</h1>
          <p className="text-slate-600 dark:text-slate-400 text-sm mt-1">
            Store metrics from CCTV pipeline + POS transactions
          </p>
        </div>
        <button
          type="button"
          onClick={() => refetchAll()}
          className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
          aria-label="Refresh"
        >
          <RefreshCw className="w-5 h-5" />
        </button>
      </div>

      <section>
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          Store intelligence
        </h2>
        <IntelligenceSection />
      </section>

      <section className="space-y-6 pt-4 border-t border-slate-200 dark:border-slate-800">
        <h2 className="text-lg font-semibold text-slate-900 dark:text-white">POS sales</h2>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          <MetricCard
            title="Total Revenue"
            value={isLoading ? '-' : formatCurrency(pos?.total_revenue ?? 0)}
            color="primary"
            isLoading={isLoading}
          />
          <MetricCard
            title="Total Transactions"
            value={isLoading ? '-' : formatNumber(pos?.total_transactions ?? 0)}
            color="success"
            isLoading={isLoading}
          />
          <MetricCard
            title="Avg Basket Size"
            value={isLoading ? '-' : formatCurrency(pos?.average_basket_size ?? 0)}
            color="warning"
            isLoading={isLoading}
          />
          <MetricCard
            title="Revenue per Visitor"
            value={isLoading ? '-' : formatCurrency(pos?.revenue_per_visitor ?? 0)}
            color="danger"
            isLoading={isLoading}
          />
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <ChartContainer title="Top 5 Products by Revenue">
            <LoadingState isLoading={isLoading}>
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={topProductsData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" stroke="#94a3b8" angle={-45} textAnchor="end" height={80} />
                  <YAxis stroke="#94a3b8" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #475569',
                      borderRadius: '8px',
                      color: '#f1f5f9',
                    }}
                  />
                  <Bar dataKey="revenue" fill="#a855f7" radius={[8, 8, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </LoadingState>
          </ChartContainer>

          <ChartContainer title="Top 5 Brands by Revenue">
            <LoadingState isLoading={isLoading}>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={topBrandsData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) =>
                      `${name}: ${(percent * 100).toFixed(0)}%`
                    }
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="revenue"
                  >
                    {topBrandsData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#1e293b',
                      border: '1px solid #475569',
                      borderRadius: '8px',
                      color: '#f1f5f9',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </LoadingState>
          </ChartContainer>
        </div>

        <ChartContainer title="Revenue Trend by Hour">
          <LoadingState isLoading={isLoading}>
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={topHoursData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                <XAxis dataKey="hour" stroke="#94a3b8" />
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
                  dataKey="revenue"
                  stroke="#a855f7"
                  dot={false}
                  strokeWidth={2}
                  isAnimationActive={false}
                />
              </LineChart>
            </ResponsiveContainer>
          </LoadingState>
        </ChartContainer>

        <ChartContainer title="Top 10 Products">
          <LoadingState isLoading={isLoading}>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-700">
                    <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">
                      Product
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                      Units Sold
                    </th>
                    <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                      Revenue
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                  {(pos?.top_products || []).slice(0, 10).map((product) => (
                    <tr key={product.name} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                      <td className="px-4 py-3 text-slate-900 dark:text-white">{product.name}</td>
                      <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-400">
                        {formatNumber(product.count)}
                      </td>
                      <td className="px-4 py-3 text-right font-medium text-slate-900 dark:text-white">
                        {formatCurrency(product.revenue)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </LoadingState>
        </ChartContainer>
      </section>
    </div>
  );
};
