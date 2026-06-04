import React from 'react';
import { Video, Info, CheckCircle2, Users } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { apiClient, type BrigadeCamera } from '../services/apiClient';
import { TrackedVideoPlayer } from '../components/TrackedVideoPlayer';
import { LoadingState, ErrorState, Badge } from '../components/common/UIElements';
import { formatNumber } from '../utils/formatters';

function pipelineBadge(cam: BrigadeCamera) {
  const done = cam.pipeline_status === 'processed' || (cam.event_count ?? 0) > 0;
  if (done) {
    return (
      <Badge
        label={`${formatNumber(cam.event_count ?? cam.visitor_count ?? 0)} events`}
        variant="success"
        size="sm"
      />
    );
  }
  return <Badge label="Pipeline pending" variant="warning" size="sm" />;
}

export const BrigadeCCTV: React.FC = () => {
  const { data, isLoading, error } = useQuery({
    queryKey: ['brigade-cameras'],
    queryFn: () => apiClient.getCameras(),
    staleTime: 30_000,
    refetchInterval: 15_000,
  });

  if (error) {
    return (
      <ErrorState
        title="Could not load CCTV list"
        message="Check that the backend is running and the CCTV Footage folder exists."
      />
    );
  }

  const processedCount =
    data?.cameras.filter(
      (c) => c.pipeline_status === 'processed' || (c.event_count ?? 0) > 0
    ).length ?? 0;

  const tracksReady = data?.cameras.filter((c) => c.tracks_url).length ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <p className="text-sm text-primary-600 dark:text-primary-400 font-medium">
          Purplle submission · {data?.footage_date}
        </p>
        <h1 className="text-3xl font-bold text-slate-900 dark:text-white">CCTV Footage</h1>
        <p className="text-slate-600 dark:text-slate-400 mt-1 max-w-2xl">
          Play any camera — person boxes track movement in real time on the original video
          (YOLO + ByteTrack per frame).
        </p>
      </div>

      {processedCount > 0 && (
        <div className="card p-4 flex gap-3 bg-emerald-50 dark:bg-emerald-900/20 border-emerald-200 dark:border-emerald-800">
          <CheckCircle2 className="w-5 h-5 text-emerald-600 flex-shrink-0 mt-0.5" />
          <p className="text-sm text-emerald-900 dark:text-emerald-100">
            Events ready for {processedCount}/{data?.total ?? 5} cameras.
            {tracksReady > 0
              ? ` Live tracking enabled on ${tracksReady} camera(s).`
              : ' Run track export below to enable live boxes.'}
          </p>
        </div>
      )}

      <div className="card p-4 flex gap-3 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
        <Info className="w-5 h-5 text-blue-600 flex-shrink-0 mt-0.5" />
        <div className="text-sm text-blue-900 dark:text-blue-100 space-y-1">
          <p>
            <strong>One-time export</strong> (boxes follow people when you press play):
          </p>
          <p>
            <code className="text-xs">python scripts/export_brigade_tracks.py</code>
          </p>
          <p className="text-blue-800/80 dark:text-blue-200/80">
            Uses sample-rate 3 and min-hits 1 for smooth, tight boxes. Restart API after export.
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
                  {cam.tracks_url && (
                    <Badge label="Tracking on" variant="success" size="sm" />
                  )}
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
                  {(cam.event_count ?? 0) > 0 && (
                    <span className="flex items-center gap-1 text-emerald-600">
                      <Users className="w-3 h-3" />
                      {formatNumber(cam.event_count ?? 0)} events
                    </span>
                  )}
                  {cam.size_mb != null && <span>{cam.size_mb} MB</span>}
                </span>
              </div>
            </div>
          ))}
        </div>
      </LoadingState>

      {!isLoading && (data?.cameras?.length ?? 0) === 0 && (
        <p className="text-center text-slate-500 py-12">
          No MP4 files found in store-intelligence/CCTV Footage
        </p>
      )}
    </div>
  );
};
