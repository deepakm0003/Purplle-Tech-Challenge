import React from 'react';
import { Loader, AlertCircle } from 'lucide-react';

// Loading skeleton
export const Skeleton: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`animate-pulse bg-slate-200 dark:bg-slate-700 rounded ${className}`} />
);

// Loading spinner
export const LoadingSpinner: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({ size = 'md' }) => {
  const sizeClass = {
    sm: 'w-4 h-4',
    md: 'w-8 h-8',
    lg: 'w-12 h-12',
  }[size];

  return (
    <div className={`${sizeClass} animate-spin text-primary-500`}>
      <Loader className="w-full h-full" />
    </div>
  );
};

// Loading state container
export const LoadingState: React.FC<{ isLoading: boolean; children: React.ReactNode }> = ({
  isLoading,
  children,
}) => {
  if (!isLoading) return <>{children}</>;
  return (
    <div className="flex items-center justify-center h-64">
      <LoadingSpinner size="lg" />
    </div>
  );
};

// Error state
export const ErrorState: React.FC<{
  title?: string;
  message?: string;
  onRetry?: () => void;
}> = ({ title = 'Error', message = 'Something went wrong', onRetry }) => (
  <div className="card p-6 text-center border-red-200 dark:border-red-900">
    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
    <h3 className="font-semibold text-red-900 dark:text-red-100 mb-1">{title}</h3>
    <p className="text-red-700 dark:text-red-300 text-sm mb-4">{message}</p>
    {onRetry && (
      <button
        onClick={onRetry}
        className="px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 rounded hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
      >
        Try Again
      </button>
    )}
  </div>
);

// Empty state
export const EmptyState: React.FC<{
  icon?: React.ReactNode;
  title?: string;
  message?: string;
}> = ({ title = 'No data', message = 'No data available' }) => (
  <div className="card p-12 text-center border-slate-200 dark:border-slate-800">
    <div className="w-12 h-12 bg-slate-100 dark:bg-slate-800 rounded-lg mx-auto mb-4" />
    <h3 className="font-semibold text-slate-700 dark:text-slate-300 mb-1">{title}</h3>
    <p className="text-slate-600 dark:text-slate-400 text-sm">{message}</p>
  </div>
);

// Metric card component
export interface MetricCardProps {
  title: string;
  value: string | number;
  unit?: string;
  icon?: React.ReactNode;
  trend?: number;
  trendLabel?: string;
  color?: 'primary' | 'success' | 'warning' | 'danger';
  isLoading?: boolean;
}

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  unit,
  icon,
  trend,
  trendLabel,
  color = 'primary',
  isLoading = false,
}) => {
  const colorClasses = {
    primary: 'bg-primary-50 dark:bg-primary-900/20 border-primary-200 dark:border-primary-800',
    success: 'bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800',
    warning: 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800',
    danger: 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800',
  };

  const iconColorClasses = {
    primary: 'text-primary-600 dark:text-primary-400',
    success: 'text-emerald-600 dark:text-emerald-400',
    warning: 'text-yellow-600 dark:text-yellow-400',
    danger: 'text-red-600 dark:text-red-400',
  };

  return (
    <div className={`card p-6 ${colorClasses[color]}`}>
      <div className="flex items-start justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-600 dark:text-slate-400">{title}</h3>
        {icon && <div className={`w-5 h-5 ${iconColorClasses[color]}`}>{icon}</div>}
      </div>

      {isLoading ? (
        <Skeleton className="h-8 w-24 mb-2" />
      ) : (
        <div className="flex items-baseline gap-2">
          <span className="text-2xl font-bold text-slate-900 dark:text-slate-50">{value}</span>
          {unit && <span className="text-sm text-slate-600 dark:text-slate-400">{unit}</span>}
        </div>
      )}

      {trend !== undefined && (
        <div className={`mt-3 text-xs font-medium ${trend >= 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-red-600 dark:text-red-400'}`}>
          {trend >= 0 ? '↑' : '↓'} {Math.abs(trend).toFixed(1)}% {trendLabel ? `${trendLabel}` : ''}
        </div>
      )}
    </div>
  );
};

// Chart container
export const ChartContainer: React.FC<{
  title: string;
  children: React.ReactNode;
  isLoading?: boolean;
  className?: string;
}> = ({ title, children, isLoading = false, className = '' }) => (
  <div className={`card p-6 ${className}`}>
    <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-50 mb-4">{title}</h3>
    {isLoading ? (
      <div className="h-80 flex items-center justify-center">
        <LoadingSpinner />
      </div>
    ) : (
      children
    )}
  </div>
);

// Badge component
export const Badge: React.FC<{
  label: string;
  variant?: 'success' | 'warning' | 'danger' | 'info';
  size?: 'sm' | 'md';
}> = ({ label, variant = 'info', size = 'md' }) => {
  const variantClasses = {
    success: 'badge-success',
    warning: 'badge-warning',
    danger: 'badge-danger',
    info: 'badge-info',
  };

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-sm px-3 py-1',
  };

  return <span className={`${variantClasses[variant]} ${sizeClasses[size]}`}>{label}</span>;
};

// Status badge
export const StatusBadge: React.FC<{
  status: 'active' | 'inactive' | 'error' | 'healthy' | 'degraded' | 'unhealthy';
}> = ({ status }) => {
  const statusMap = {
    active: { label: 'Active', variant: 'success' as const },
    inactive: { label: 'Inactive', variant: 'warning' as const },
    error: { label: 'Error', variant: 'danger' as const },
    healthy: { label: 'Healthy', variant: 'success' as const },
    degraded: { label: 'Degraded', variant: 'warning' as const },
    unhealthy: { label: 'Unhealthy', variant: 'danger' as const },
  };

  const config = statusMap[status];
  return <Badge label={config.label} variant={config.variant} />;
};

// Progress bar
export const ProgressBar: React.FC<{
  value: number;
  max?: number;
  showLabel?: boolean;
  color?: 'primary' | 'success' | 'warning' | 'danger';
}> = ({ value, max = 100, showLabel = true, color = 'primary' }) => {
  const percentage = (value / max) * 100;

  const colorClasses = {
    primary: 'bg-primary-500',
    success: 'bg-emerald-500',
    warning: 'bg-yellow-500',
    danger: 'bg-red-500',
  };

  return (
    <div>
      <div className="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
        <div
          className={`${colorClasses[color]} h-full rounded-full transition-all duration-300`}
          style={{ width: `${Math.min(percentage, 100)}%` }}
        />
      </div>
      {showLabel && (
        <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
          {Math.round(percentage)}%
        </p>
      )}
    </div>
  );
};

// Divider
export const Divider: React.FC<{ className?: string }> = ({ className = '' }) => (
  <div className={`border-t border-slate-200 dark:border-slate-800 ${className}`} />
);

// Spacer
export const Spacer: React.FC<{ size?: 'sm' | 'md' | 'lg' }> = ({ size = 'md' }) => {
  const sizeClass = {
    sm: 'h-2',
    md: 'h-4',
    lg: 'h-8',
  }[size];
  return <div className={sizeClass} />;
};
