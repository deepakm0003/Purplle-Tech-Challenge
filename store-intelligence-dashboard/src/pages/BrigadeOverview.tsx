import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  AreaChart,
  Area,
} from 'recharts';
import { Link } from 'react-router-dom';
import { Store, ShoppingCart, Users, Receipt, RefreshCw, Video } from 'lucide-react';
import { useQueryClient } from '@tanstack/react-query';
import { useStore } from '../context/StoreContext';
import { useEventSummary, useStoreDashboard } from '../hooks/useAPI.ts';
import { MetricCard, ChartContainer, LoadingState, ErrorState } from '../components/common/UIElements';
import { formatCurrency, formatNumber } from '../utils/formatters';

export const BrigadeOverview: React.FC = () => {
  const queryClient = useQueryClient();
  const { storeName } = useStore();
  const { data, isLoading, error } = useStoreDashboard();
  const { data: cctvSummary } = useEventSummary();

  if (error) {
    return (
      <ErrorState
        title="Could not load store data"
        message="Ensure the backend is running and POS - sample transactions CSV is present."
        onRetry={() => queryClient.invalidateQueries()}
      />
    );
  }

  const s = data?.summary;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap justify-between items-start gap-4">
        <div>
          <p className="text-sm text-primary-600 dark:text-primary-400 font-medium">
            Purplle take-home · {storeName}
          </p>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
            {data?.store_name ?? storeName}
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mt-1">
            POS: {data?.date} · {data?.source ?? 'sample POS CSV'}
            {cctvSummary && (
              <> · CCTV: {cctvSummary.unique_visitors} unique visitors</>
            )}
          </p>
        </div>
        <button
          type="button"
          onClick={() => queryClient.invalidateQueries()}
          className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg"
          aria-label="Refresh"
        >
          <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {cctvSummary && cctvSummary.total_events > 0 && (
        <div className="card p-4 flex flex-wrap items-center justify-between gap-4 border-primary-200 dark:border-primary-800 bg-primary-50/50 dark:bg-primary-900/10">
          <div className="flex items-center gap-3">
            <Video className="w-8 h-8 text-primary-600" />
            <div>
              <p className="font-semibold text-slate-900 dark:text-white">CCTV pipeline active</p>
              <p className="text-sm text-slate-600 dark:text-slate-400">
                {cctvSummary.total_events} events · {cctvSummary.unique_visitors} visitors ·{' '}
                {cctvSummary.entry_events} entries
              </p>
            </div>
          </div>
          <Link
            to="/sales"
            className="text-sm font-medium text-primary-600 hover:text-primary-700 dark:text-primary-400"
          >
            View sales & intelligence →
          </Link>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total Revenue"
          value={isLoading ? '-' : formatCurrency(s?.total_revenue ?? 0)}
          unit="NMV"
          icon={<Store className="w-5 h-5" />}
          color="primary"
          isLoading={isLoading}
        />
        <MetricCard
          title="Orders"
          value={isLoading ? '-' : formatNumber(s?.total_orders ?? 0)}
          unit="invoices"
          icon={<Receipt className="w-5 h-5" />}
          color="success"
          isLoading={isLoading}
        />
        <MetricCard
          title="Customers"
          value={isLoading ? '-' : formatNumber(s?.unique_customers ?? 0)}
          unit="unique"
          icon={<Users className="w-5 h-5" />}
          color="warning"
          isLoading={isLoading}
        />
        <MetricCard
          title="Avg Order Value"
          value={isLoading ? '-' : formatCurrency(s?.average_order_value ?? 0)}
          icon={<ShoppingCart className="w-5 h-5" />}
          color="primary"
          isLoading={isLoading}
        />
      </div>

      <ChartContainer title="Revenue by Hour (10 April 2026)">
        <LoadingState isLoading={isLoading}>
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={data?.hourly_revenue ?? []}>
              <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
              <XAxis dataKey="label" stroke="#94a3b8" />
              <YAxis stroke="#94a3b8" />
              <Tooltip
                formatter={(value: number) => formatCurrency(value)}
                contentStyle={{
                  backgroundColor: '#1e293b',
                  border: '1px solid #475569',
                  borderRadius: '8px',
                  color: '#f1f5f9',
                }}
              />
              <Area type="monotone" dataKey="revenue" stroke="#a855f7" fill="#a855f7" fillOpacity={0.2} />
            </AreaChart>
          </ResponsiveContainer>
        </LoadingState>
      </ChartContainer>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartContainer title="Top Products">
          <LoadingState isLoading={isLoading}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={(data?.top_products ?? []).slice(0, 6)} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(v) => `₹${v}`} />
                <YAxis dataKey="name" type="category" width={120} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Bar dataKey="revenue" fill="#a855f7" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </LoadingState>
        </ChartContainer>

        <ChartContainer title="Top Categories">
          <LoadingState isLoading={isLoading}>
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={data?.top_categories ?? []}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="name" />
                <YAxis tickFormatter={(v) => `₹${v}`} />
                <Tooltip formatter={(v: number) => formatCurrency(v)} />
                <Bar dataKey="revenue" fill="#8b5cf6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </LoadingState>
        </ChartContainer>
      </div>
    </div>
  );
};
