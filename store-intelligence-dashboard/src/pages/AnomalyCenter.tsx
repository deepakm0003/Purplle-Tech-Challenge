import React, { useMemo } from 'react';
import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { useAnomalies } from '../hooks/useAPI.ts';
import { ChartContainer, LoadingState, ErrorState, Badge } from '../components/common/UIElements';
import { formatRelativeTime, getSeverityColor } from '../utils/formatters';

export const AnomalyCenter: React.FC = () => {
  const { data: anomalies, isLoading, error } = useAnomalies();

  if (error) {
    return (
      <ErrorState
        title="Failed to load anomalies"
        message="Unable to fetch anomaly data"
      />
    );
  }

  const anomalyStats = useMemo(() => {
    if (!anomalies?.anomalies) return { critical: 0, warning: 0, info: 0 };
    return {
      critical: anomalies.anomalies.filter((a) => a.severity === 'CRITICAL').length,
      warning: anomalies.anomalies.filter((a) => a.severity === 'WARN').length,
      info: anomalies.anomalies.filter((a) => a.severity === 'INFO').length,
    };
  }, [anomalies]);

  const anomalyTypes = useMemo(() => {
    if (!anomalies?.anomalies) return {};
    const types: Record<string, number> = {};
    anomalies.anomalies.forEach((a) => {
      types[a.anomaly_type] = (types[a.anomaly_type] || 0) + 1;
    });
    return types;
  }, [anomalies]);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Anomaly Center</h1>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-6 bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800">
          <div className="flex items-center gap-3 mb-2">
            <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
            <p className="text-sm text-slate-600 dark:text-slate-400">Critical</p>
          </div>
          <p className="text-3xl font-bold text-red-600 dark:text-red-400">{anomalyStats.critical}</p>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-2">Require immediate action</p>
        </div>

        <div className="card p-6 bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800">
          <div className="flex items-center gap-3 mb-2">
            <AlertCircle className="w-5 h-5 text-yellow-600 dark:text-yellow-400" />
            <p className="text-sm text-slate-600 dark:text-slate-400">Warnings</p>
          </div>
          <p className="text-3xl font-bold text-yellow-600 dark:text-yellow-400">{anomalyStats.warning}</p>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-2">Monitor closely</p>
        </div>

        <div className="card p-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
          <div className="flex items-center gap-3 mb-2">
            <Info className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            <p className="text-sm text-slate-600 dark:text-slate-400">Informational</p>
          </div>
          <p className="text-3xl font-bold text-blue-600 dark:text-blue-400">{anomalyStats.info}</p>
          <p className="text-xs text-slate-600 dark:text-slate-400 mt-2">General information</p>
        </div>
      </div>

      {/* Anomaly Types Distribution */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          Anomaly Types Distribution
        </h3>
        <LoadingState isLoading={isLoading}>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(anomalyTypes).map(([type, count]) => (
              <div key={type} className="p-4 rounded-lg bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                <p className="font-medium text-slate-900 dark:text-white">{type}</p>
                <p className="text-2xl font-bold text-primary-500 mt-2">{count}</p>
                <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">occurrences</p>
              </div>
            ))}
          </div>
        </LoadingState>
      </div>

      {/* Anomalies List */}
      <ChartContainer title="Active Anomalies">
        <LoadingState isLoading={isLoading}>
          {anomalies && anomalies.anomalies.length > 0 ? (
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {anomalies.anomalies.map((anomaly) => (
                <div
                  key={anomaly.id}
                  className={`p-4 rounded-lg border-l-4 ${getSeverityColor(anomaly.severity)} border-l-current`}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <h4 className="font-semibold text-slate-900 dark:text-white mb-1">
                        {anomaly.anomaly_type}
                      </h4>
                      <p className="text-sm text-slate-600 dark:text-slate-400 mb-2">
                        {anomaly.description}
                      </p>
                      <div className="flex gap-2 text-xs">
                        {anomaly.zone_id && (
                          <Badge
                            label={`Zone: ${anomaly.zone_id}`}
                            variant="info"
                            size="sm"
                          />
                        )}
                        {anomaly.value && (
                          <Badge
                            label={`Value: ${anomaly.value.toFixed(2)}`}
                            variant="info"
                            size="sm"
                          />
                        )}
                      </div>
                    </div>
                    <div className="flex flex-col items-end gap-2">
                      <Badge
                        label={anomaly.severity}
                        variant={
                          anomaly.severity === 'CRITICAL'
                            ? 'danger'
                            : anomaly.severity === 'WARN'
                              ? 'warning'
                              : 'info'
                        }
                        size="sm"
                      />
                      <p className="text-xs text-slate-500 dark:text-slate-500">
                        {formatRelativeTime(anomaly.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <p className="text-slate-600 dark:text-slate-400">✓ No anomalies detected</p>
            </div>
          )}
        </LoadingState>
      </ChartContainer>

      {/* Anomaly Guidelines */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="card p-6 bg-red-50 dark:bg-red-900/20">
          <h4 className="font-semibold text-red-900 dark:text-red-100 mb-2">Critical</h4>
          <p className="text-sm text-red-700 dark:text-red-300">
            Requires immediate intervention. System performance or customer experience is severely impacted.
          </p>
        </div>

        <div className="card p-6 bg-yellow-50 dark:bg-yellow-900/20">
          <h4 className="font-semibold text-yellow-900 dark:text-yellow-100 mb-2">Warning</h4>
          <p className="text-sm text-yellow-700 dark:text-yellow-300">
            Monitor closely and take preventive action. System may degrade if not addressed.
          </p>
        </div>

        <div className="card p-6 bg-blue-50 dark:bg-blue-900/20">
          <h4 className="font-semibold text-blue-900 dark:text-blue-100 mb-2">Info</h4>
          <p className="text-sm text-blue-700 dark:text-blue-300">
            Informational alerts about system state and operations. For awareness only.
          </p>
        </div>
      </div>
    </div>
  );
};
