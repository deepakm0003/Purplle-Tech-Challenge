import React from 'react';
import { Video, Info, CheckCircle2, Users } from 'lucide-react';
import { useCameras, useEventSummary } from '../hooks/useAPI.ts';
import { useStore } from '../context/StoreContext';
import type { StoreCamera } from '../services/apiClient';
import { TrackedVideoPlayer } from '../components/TrackedVideoPlayer';
import { LoadingState, ErrorState, Badge } from '../components/common/UIElements';
import { formatNumber } from '../utils/formatters';

function pipelineBadge(cam: StoreCamera) {
  const visitors = cam.visitor_count ?? 0;
  const entries = cam.entry_count ?? 0;
  if (visitors > 0 || entries > 0) {
    return (
      <Badge
        label={`${formatNumber(visitors)} visitors · ${formatNumber(entries)} entries`}
        variant="success"
        size="sm"
      />
    );
  }
  if ((cam.event_count ?? 0) > 0) {
    return (
      <Badge label={`${formatNumber(cam.event_count ?? 0)} events`} variant="success" size="sm" />
    );
  }
  return <Badge label="Pipeline pending" variant="warning" size="sm" />;
}

export const StoreCCTV: React.FC = () => {
  const { storeName } = useStore();
  const { data, isLoading, error } = useCameras();
  const { data: summary } = useEventSummary();

  if (error) {
    return (
      <ErrorState
        title="Could not load CCTV"
        message="Check that the backend is running and Store 1 / Store 2 video folders exist."
      />
    );
  }

  const processedCount =
    data?.cameras.filter(
      (c) =>
        c.pipeline_status === 'processed' ||
        (c.visitor_count ?? 0) > 0 ||
        (c.entry_count ?? 0) > 0
    ).length ?? 0;

  const tracksReady = data?.cameras.filter((c) => c.tracks_url).length ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-primary-600 dark:text-primary-400 font-medium">
          Purplle take-home · {data?.store_name ?? storeName}
        </p>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">CCTV playback</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1 max-w-2xl">
          Person boxes only — no store outline on video. Counts use unique ENTRY visitors (staff
          excluded).
        </p>
        {summary && (
          <p className="text-sm text-slate-500 mt-2 flex items-center gap-2">
            <Users className="w-4 h-4" />
            Store total: {formatNumber(summary.unique_visitors)} unique visitors ·{' '}
            {formatNumber(summary.entry_events)} entries
          </p>
        )}
      </div>

      {processedCount > 0 && (
        <div className="card p-4 flex gap-3 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-emerald-900 dark:text-emerald-100">
            Pipeline data for {processedCount}/{data?.total ?? 0} cameras.
            {tracksReady > 0
              ? ` Live tracking on ${tracksReady} camera(s).`
              : ' Run track export to enable live boxes.'}
          </p>
        </div>
      )}

      <div className="card p-4 flex gap-3 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-900 dark:text-blue-100 space-y-1">
          <p>
            <strong>Track export</strong> (one-time per store):
          </p>
          <p>
            <code className="text-xs">
              python scripts/export_store_tracks.py --store {data?.store_id ?? 'ST1008'}
            </code>
          </p>
          <p className="text-blue-800/80 dark:text-blue-200/80">
            Then restart the API and refresh this page.
          </p>
        </div>
      </div>

      <LoadingState isLoading={isLoading}>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {(data?.cameras ?? []).map((cam) => (
            <div key={cam.id} className="card overflow-hidden">
              <div className="p-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
                <div className="flex items-center gap-2">
                  <Video className="w-5 h-5 text-primary-500" />
                  <span className="font-semibold text-slate-900 dark:text-white">{cam.name}</span>
                </div>
                <div className="flex items-center gap-2">
                  {cam.tracks_url && <Badge label="Tracking on" variant="success" size="sm" />}
                  {pipelineBadge(cam)}
                </div>
              </div>

              {cam.media_url ? (
                <TrackedVideoPlayer
                  videoUrl={cam.media_url}
                  tracksUrl={cam.tracks_url}
                  title={cam.name}
                />
              ) : (
                <div className="aspect-video bg-slate-900 flex items-center justify-center text-slate-500">
                  No file
                </div>
              )}

              <div className="p-3 text-xs text-slate-600 dark:text-slate-400 flex justify-between items-center">
                <span>{cam.file_name}</span>
                <span className="flex items-center gap-3">
                  {(cam.visitor_count ?? 0) > 0 && (
                    <span className="flex items-center gap-1 text-emerald-600">
                      <Users className="w-3 h-3" />
                      {formatNumber(cam.visitor_count ?? 0)} visitors
                    </span>
                  )}
                  <span>{cam.size_mb != null ? `${cam.size_mb} MB` : ''}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      </LoadingState>
    </div>
  );
};
