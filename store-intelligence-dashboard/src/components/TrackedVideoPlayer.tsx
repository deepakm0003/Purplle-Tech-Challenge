import React, { useCallback, useEffect, useRef, useState } from 'react';
import { cctvMediaUrl } from '../services/apiClient';

export interface TrackObject {
  id: number;
  b: [number, number, number, number];
  c: number;
  z?: string | null;
}

export interface TrackFrame {
  i: number;
  o: TrackObject[];
}

export interface TrackData {
  version: number;
  video: string;
  fps: number;
  width: number;
  height: number;
  inference_sample_rate?: number;
  frame_count?: number;
  frames: TrackFrame[];
}

const PALETTE = [
  '#22c55e',
  '#3b82f6',
  '#f97316',
  '#a855f7',
  '#ec4899',
  '#14b8a6',
  '#eab308',
  '#ef4444',
];

function colorForId(id: number): string {
  return PALETTE[id % PALETTE.length];
}

function findObjectsAtFrame(frames: TrackFrame[], frameIdx: number): TrackObject[] {
  if (!frames.length) return [];
  let lo = 0;
  let hi = frames.length - 1;
  if (frameIdx <= frames[0].i) return frames[0].o;
  if (frameIdx >= frames[hi].i) return frames[hi].o;

  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].i === frameIdx) return frames[mid].o;
    if (frames[mid].i < frameIdx) lo = mid + 1;
    else hi = mid - 1;
  }
  const before = frames[Math.max(0, hi)];
  const after = frames[Math.min(frames.length - 1, lo)];
  if (frameIdx - before.i <= after.i - frameIdx) return before.o;
  return after.o;
}

interface TrackedVideoPlayerProps {
  videoUrl: string;
  tracksUrl?: string | null;
  title?: string;
}

export const TrackedVideoPlayer: React.FC<TrackedVideoPlayerProps> = ({
  videoUrl,
  tracksUrl,
  title,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number>(0);

  const [tracks, setTracks] = useState<TrackData | null>(null);
  const [tracksError, setTracksError] = useState<string | null>(null);
  const [loadingTracks, setLoadingTracks] = useState(false);

  useEffect(() => {
    if (!tracksUrl) {
      setTracks(null);
      return;
    }
    let cancelled = false;
    setLoadingTracks(true);
    setTracksError(null);
    fetch(cctvMediaUrl(tracksUrl))
      .then((r) => {
        if (!r.ok) throw new Error(`Tracks not found (${r.status})`);
        return r.json();
      })
      .then((data: TrackData) => {
        if (!cancelled) setTracks(data);
      })
      .catch((e: Error) => {
        if (!cancelled) {
          setTracks(null);
          setTracksError(e.message);
        }
      })
      .finally(() => {
        if (!cancelled) setLoadingTracks(false);
      });
    return () => {
      cancelled = true;
    };
  }, [tracksUrl]);

  const drawOverlay = useCallback(() => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    const container = containerRef.current;
    if (!video || !canvas || !container) return;

    const rect = container.getBoundingClientRect();
    const cw = Math.floor(rect.width);
    const ch = Math.floor(rect.height);
    if (canvas.width !== cw || canvas.height !== ch) {
      canvas.width = cw;
      canvas.height = ch;
    }

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    ctx.clearRect(0, 0, cw, ch);

    if (!tracks?.frames?.length || !tracks.width || !tracks.height) return;

    const scaleX = cw / tracks.width;
    const scaleY = ch / tracks.height;
    const frameIdx = Math.max(0, Math.round(video.currentTime * tracks.fps));
    const objects = findObjectsAtFrame(tracks.frames, frameIdx);

    for (const obj of objects) {
      const [x1, y1, x2, y2] = obj.b;
      const sx1 = x1 * scaleX;
      const sy1 = y1 * scaleY;
      const sw = (x2 - x1) * scaleX;
      const sh = (y2 - y1) * scaleY;
      const color = colorForId(obj.id);

      ctx.strokeStyle = color;
      ctx.lineWidth = Math.max(2, Math.min(sw, sh) * 0.02);
      ctx.strokeRect(sx1, sy1, sw, sh);

      const label = `#${obj.id}`;
      ctx.font = `bold ${Math.max(11, 13 * scaleX)}px system-ui, sans-serif`;
      const tw = ctx.measureText(label).width + 8;
      const th = 18;
      ctx.fillStyle = color;
      ctx.fillRect(sx1, Math.max(0, sy1 - th), tw, th);
      ctx.fillStyle = '#fff';
      ctx.fillText(label, sx1 + 4, Math.max(12, sy1 - 5));
    }
  }, [tracks]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;

    const loop = () => {
      drawOverlay();
      if (!video.paused && !video.ended) {
        rafRef.current = requestAnimationFrame(loop);
      }
    };

    const onPlay = () => {
      cancelAnimationFrame(rafRef.current);
      rafRef.current = requestAnimationFrame(loop);
    };
    const onPause = () => {
      cancelAnimationFrame(rafRef.current);
      drawOverlay();
    };
    const onSeeked = () => drawOverlay();
    const onTimeUpdate = () => {
      if (video.paused) drawOverlay();
    };
    const onResize = () => drawOverlay();

    video.addEventListener('play', onPlay);
    video.addEventListener('pause', onPause);
    video.addEventListener('seeked', onSeeked);
    video.addEventListener('timeupdate', onTimeUpdate);
    window.addEventListener('resize', onResize);

    if (!video.paused) onPlay();
    else drawOverlay();

    return () => {
      cancelAnimationFrame(rafRef.current);
      video.removeEventListener('play', onPlay);
      video.removeEventListener('pause', onPause);
      video.removeEventListener('seeked', onSeeked);
      video.removeEventListener('timeupdate', onTimeUpdate);
      window.removeEventListener('resize', onResize);
    };
  }, [drawOverlay, tracks]);

  return (
    <div className="relative w-full aspect-video bg-black rounded-b-lg overflow-hidden" ref={containerRef}>
      <video
        ref={videoRef}
        className="w-full h-full object-contain"
        controls
        preload="metadata"
        src={cctvMediaUrl(videoUrl)}
        crossOrigin="anonymous"
      >
        {title ?? 'CCTV playback'}
      </video>
      <canvas
        ref={canvasRef}
        className="absolute inset-0 w-full h-full pointer-events-none"
        aria-hidden
      />
      {loadingTracks && (
        <div className="absolute top-2 left-2 px-2 py-1 text-xs bg-black/70 text-white rounded">
          Loading tracks…
        </div>
      )}
      {tracks && !loadingTracks && (
        <div className="absolute top-2 right-2 px-2 py-1 text-xs bg-emerald-600/90 text-white rounded flex items-center gap-1">
          <span className="w-2 h-2 rounded-full bg-white animate-pulse" />
          Live tracking
        </div>
      )}
      {!tracksUrl && !loadingTracks && (
        <div className="absolute bottom-12 left-2 right-2 px-2 py-1 text-xs bg-amber-600/90 text-white rounded">
          Run track export: python scripts/export_store_tracks.py
        </div>
      )}
      {tracksError && (
        <div className="absolute bottom-12 left-2 right-2 px-2 py-1 text-xs bg-red-600/90 text-white rounded">
          {tracksError}
        </div>
      )}
    </div>
  );
};
