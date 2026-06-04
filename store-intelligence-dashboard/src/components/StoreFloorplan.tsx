import React, { useMemo } from 'react';
import type { StoreLayout, ZoneHeatmap } from '../types';

interface StoreFloorplanProps {
  layout?: StoreLayout;
  heatmap?: ZoneHeatmap[];
  width?: number;
  height?: number;
}

const REF_W = 800;
const REF_H = 600;

function heatColor(score: number): string {
  if (score >= 80) return '#ef4444';
  if (score >= 60) return '#f97316';
  if (score >= 40) return '#eab308';
  if (score >= 20) return '#22d3ee';
  return '#3b82f6';
}

export const StoreFloorplan: React.FC<StoreFloorplanProps> = ({
  layout,
  heatmap = [],
  width = 640,
  height = 480,
}) => {
  const heatByZone = useMemo(() => {
    const m = new Map<string, ZoneHeatmap>();
    heatmap.forEach((z) => m.set(z.zone_id, z));
    return m;
  }, [heatmap]);

  const zones = layout?.zones ?? [];
  const sx = width / REF_W;
  const sy = height / REF_H;

  if (layout?.layout_image_url && zones.length === 0) {
    return (
      <div className="w-full h-full flex flex-col items-center justify-center bg-slate-900 rounded-lg p-2">
        <img
          src={layout.layout_image_url}
          alt={`${layout.store_name} floor plan`}
          className="max-w-full max-h-full object-contain rounded"
        />
        <p className="text-slate-500 text-xs mt-2">{layout.store_name} — layout</p>
      </div>
    );
  }

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-full rounded-lg bg-slate-900"
      role="img"
      aria-label="Store floor plan heatmap"
    >
      <rect x={0} y={0} width={width} height={height} fill="#0f172a" />
      <text x={width / 2} y={20} textAnchor="middle" fill="#94a3b8" fontSize={12}>
        {layout?.store_name ?? 'Store'} — zone heatmap
      </text>

      {zones.map((zone) => {
        const coords = zone.coordinates ?? [];
        if (coords.length < 3) return null;
        const points = coords
          .map(([x, y]) => `${x * sx},${y * sy}`)
          .join(' ');
        const heat = heatByZone.get(zone.id);
        const score = heat?.heat_score ?? 10;
        const fill = heatColor(score);
        return (
          <g key={zone.id}>
            <polygon
              points={points}
              fill={fill}
              fillOpacity={0.55}
              stroke="#e2e8f0"
              strokeWidth={1.5}
            />
            <text
              x={
                (Math.min(...coords.map((c) => c[0])) +
                  Math.max(...coords.map((c) => c[0]))) /
                  2 *
                sx
              }
              y={
                (Math.min(...coords.map((c) => c[1])) +
                  Math.max(...coords.map((c) => c[1]))) /
                  2 *
                sy
              }
              textAnchor="middle"
              fill="#f8fafc"
              fontSize={11}
              fontWeight={600}
            >
              {zone.name}
            </text>
          </g>
        );
      })}

      {/* Entrance label */}
      <text x={40 * sx} y={580 * sy} fill="#fca5a5" fontSize={10}>
        Entry
      </text>
      <text x={650 * sx} y={580 * sy} fill="#93c5fd" fontSize={10}>
        Cash Counter
      </text>
    </svg>
  );
};
