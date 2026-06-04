/**
 * Format large numbers with K, M, B suffixes
 */
export const formatNumber = (value: number, decimals = 1): string => {
  if (value === 0) return '0';
  if (value >= 1e9) return `${(value / 1e9).toFixed(decimals)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(decimals)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(decimals)}K`;
  return value.toFixed(decimals);
};

/**
 * Format currency
 */
export const formatCurrency = (value: number, currency = '₹'): string => {
  return `${currency}${value.toLocaleString('en-IN', {
    maximumFractionDigits: 0,
  })}`;
};

/**
 * Format percentage
 */
export const formatPercentage = (value: number, decimals = 1): string => {
  return `${(value * 100).toFixed(decimals)}%`;
};

/**
 * Format time difference
 */
export const formatTimeDifference = (seconds: number): string => {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)}h`;
  return `${Math.round(seconds / 86400)}d`;
};

/**
 * Format timestamp
 */
export const formatTimestamp = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/**
 * Format time for display (HH:MM)
 */
export const formatTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleTimeString('en-IN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
};

/**
 * Format date (MMM DD, YYYY)
 */
export const formatDate = (timestamp: string): string => {
  const date = new Date(timestamp);
  return date.toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
};

/**
 * Get relative time (e.g., "2 hours ago")
 */
export const formatRelativeTime = (timestamp: string): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const secondsDiff = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (secondsDiff < 60) return 'just now';
  if (secondsDiff < 3600) return `${Math.floor(secondsDiff / 60)}m ago`;
  if (secondsDiff < 86400) return `${Math.floor(secondsDiff / 3600)}h ago`;
  return `${Math.floor(secondsDiff / 86400)}d ago`;
};

/**
 * Calculate trend
 */
export const calculateTrend = (current: number, previous: number): { value: number; direction: 'up' | 'down' | 'neutral' } => {
  if (previous === 0) return { value: 0, direction: 'neutral' };
  const trend = ((current - previous) / previous) * 100;
  return {
    value: Math.abs(trend),
    direction: trend > 0 ? 'up' : trend < 0 ? 'down' : 'neutral',
  };
};

/**
 * Get status color
 */
export const getStatusColor = (status: string): string => {
  switch (status.toLowerCase()) {
    case 'active':
    case 'healthy':
    case 'success':
      return 'text-emerald-500';
    case 'inactive':
    case 'degraded':
    case 'warning':
      return 'text-yellow-500';
    case 'error':
    case 'unhealthy':
    case 'critical':
      return 'text-red-500';
    default:
      return 'text-slate-500';
  }
};

/**
 * Get severity color
 */
export const getSeverityColor = (severity: string): string => {
  switch (severity.toUpperCase()) {
    case 'INFO':
      return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300';
    case 'WARN':
      return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-300';
    case 'CRITICAL':
      return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300';
    default:
      return 'bg-slate-100 dark:bg-slate-900/30 text-slate-800 dark:text-slate-300';
  }
};

/**
 * Truncate text
 */
export const truncate = (text: string, length: number): string => {
  return text.length > length ? `${text.substring(0, length)}...` : text;
};

/**
 * Get initials from name
 */
export const getInitials = (name: string): string => {
  return name
    .split(' ')
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
};

/**
 * Convert seconds to HH:MM:SS
 */
export const formatSeconds = (seconds: number): string => {
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
};

/**
 * Get color based on percentage/score
 */
export const getScoreColor = (score: number): string => {
  if (score >= 80) return 'text-emerald-500';
  if (score >= 60) return 'text-yellow-500';
  if (score >= 40) return 'text-orange-500';
  return 'text-red-500';
};

/**
 * Calculate average
 */
export const calculateAverage = (values: number[]): number => {
  if (values.length === 0) return 0;
  return values.reduce((a, b) => a + b, 0) / values.length;
};

/**
 * Calculate max value
 */
export const calculateMax = (values: number[]): number => {
  return Math.max(...values);
};

/**
 * Calculate min value
 */
export const calculateMin = (values: number[]): number => {
  return Math.min(...values);
};
