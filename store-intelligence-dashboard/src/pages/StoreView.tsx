import React, { useMemo } from 'react';
import { useHeatmap, useStoreLayout } from '../hooks/useAPI.ts';
import { StoreFloorplan } from '../components/StoreFloorplan';
import {
  ChartContainer,
  LoadingState,
  ErrorState,
  Badge,
  Skeleton,
} from '../components/common/UIElements';
import { formatNumber } from '../utils/formatters';

export const StoreView: React.FC = () => {
  const { data: heatmap, isLoading: heatmapLoading, error: heatmapError } = useHeatmap();
  const { data: storeLayout, isLoading: layoutLoading } = useStoreLayout();

  const zoneStats = useMemo(() => {
    if (!heatmap) return [];
    return heatmap.zones.sort((a, b) => b.visitor_count - a.visitor_count);
  }, [heatmap]);

  if (heatmapError) {
    return (
      <ErrorState
        title="Failed to load store view"
        message="Unable to fetch zone heatmap data"
      />
    );
  }

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Live Store View</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Heatmap Canvas */}
        <div className="lg:col-span-2">
          <ChartContainer title="Zone Heatmap" isLoading={heatmapLoading}>
            <div className="bg-slate-900 rounded-lg p-4 aspect-video">
              {heatmapLoading || layoutLoading ? (
                <Skeleton className="w-full h-full min-h-[320px]" />
              ) : (
                <StoreFloorplan layout={storeLayout} heatmap={heatmap?.zones} />
              )}
              <p className="text-slate-500 text-xs mt-2 text-center">
                Zones: {zoneStats.length} · Visits:{' '}
                {formatNumber(zoneStats.reduce((sum, z) => sum + z.visitor_count, 0))}
                {heatmap && 'data_confidence' in heatmap && (
                  <> · Confidence: {(heatmap as { data_confidence?: string }).data_confidence}</>
                )}
              </p>
            </div>

            {/* Heatmap Legend */}
            <div className="mt-6 grid grid-cols-5 gap-2">
              {[
                { label: 'Cold', color: 'bg-blue-500' },
                { label: 'Cool', color: 'bg-cyan-500' },
                { label: 'Warm', color: 'bg-yellow-500' },
                { label: 'Hot', color: 'bg-orange-500' },
                { label: 'Critical', color: 'bg-red-500' },
              ].map((item) => (
                <div key={item.label} className="text-center">
                  <div className={`h-6 rounded mb-2 ${item.color}`} />
                  <p className="text-xs text-slate-600 dark:text-slate-400">{item.label}</p>
                </div>
              ))}
            </div>
          </ChartContainer>
        </div>

        {/* Zone Statistics */}
        <div className="card p-6">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Zone Metrics
          </h3>
          <LoadingState isLoading={heatmapLoading}>
            <div className="space-y-3">
              {zoneStats.length > 0 ? (
                zoneStats.map((zone) => (
                  <div key={zone.zone_id} className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50">
                    <div className="flex justify-between items-start mb-2">
                      <p className="font-medium text-slate-900 dark:text-white">
                        {zone.zone_name}
                      </p>
                      <Badge
                        label={`${zone.heat_score.toFixed(0)}`}
                        variant={
                          zone.heat_score >= 80
                            ? 'danger'
                            : zone.heat_score >= 60
                              ? 'warning'
                              : 'info'
                        }
                        size="sm"
                      />
                    </div>
                    <div className="space-y-1 text-sm">
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span>Visitors:</span>
                        <span className="font-medium">{formatNumber(zone.visitor_count)}</span>
                      </div>
                      <div className="flex justify-between text-slate-600 dark:text-slate-400">
                        <span>Occupancy:</span>
                        <span className="font-medium">
                          {zone.occupancy_percentage.toFixed(1)}%
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-slate-600 dark:text-slate-400 text-sm">No zone data</p>
              )}
            </div>
          </LoadingState>
        </div>
      </div>

      {/* Zone Details Table */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          Zone Details
        </h3>
        <LoadingState isLoading={heatmapLoading}>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-200 dark:border-slate-700">
                  <th className="px-4 py-3 text-left font-medium text-slate-700 dark:text-slate-300">
                    Zone Name
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                    Visitors
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                    Avg dwell (s)
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                    Occupancy
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                    Heat Score
                  </th>
                  <th className="px-4 py-3 text-right font-medium text-slate-700 dark:text-slate-300">
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                {zoneStats.map((zone) => (
                  <tr key={zone.zone_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                    <td className="px-4 py-3 font-medium text-slate-900 dark:text-white">
                      {zone.zone_name}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-400">
                      {formatNumber(zone.visitor_count)}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-400">
                      {zone.avg_dwell_seconds ?? 0}
                    </td>
                    <td className="px-4 py-3 text-right text-slate-600 dark:text-slate-400">
                      {zone.occupancy_percentage.toFixed(1)}%
                    </td>
                    <td className="px-4 py-3 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <div className="w-16 h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${
                              zone.heat_score >= 80
                                ? 'bg-red-500'
                                : zone.heat_score >= 60
                                  ? 'bg-yellow-500'
                                  : zone.heat_score >= 40
                                    ? 'bg-cyan-500'
                                    : 'bg-blue-500'
                            }`}
                            style={{ width: `${zone.heat_score}%` }}
                          />
                        </div>
                        <span className="text-slate-900 dark:text-white font-medium">
                          {zone.heat_score.toFixed(0)}
                        </span>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-right">
                      <Badge
                        label={
                          zone.heat_score >= 80
                            ? 'Critical'
                            : zone.heat_score >= 60
                              ? 'High'
                              : 'Normal'
                        }
                        variant={
                          zone.heat_score >= 80
                            ? 'danger'
                            : zone.heat_score >= 60
                              ? 'warning'
                              : 'success'
                        }
                        size="sm"
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </LoadingState>
      </div>
    </div>
  );
};
