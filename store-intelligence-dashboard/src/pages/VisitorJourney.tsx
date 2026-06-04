import React, { useState, useMemo } from 'react';
import { useEvents } from '../hooks/useAPI.ts';
import { ChartContainer, LoadingState, ErrorState, Badge } from '../components/common/UIElements';
import { formatTime, formatSeconds } from '../utils/formatters';

export const VisitorJourney: React.FC = () => {
  const { data: events, isLoading, error } = useEvents(100, 0);
  const [selectedVisitor, setSelectedVisitor] = useState<string | null>(null);

  if (error) {
    return (
      <ErrorState
        title="Failed to load visitor data"
        message="Unable to fetch visitor journey data"
      />
    );
  }

  const visitors = useMemo(() => {
    if (!events?.events) return [];
    const visitorMap: Record<string, any[]> = {};
    events.events.forEach((event) => {
      if (!visitorMap[event.visitor_id]) {
        visitorMap[event.visitor_id] = [];
      }
      visitorMap[event.visitor_id].push(event);
    });
    return Object.entries(visitorMap)
      .map(([id, events]) => ({
        visitor_id: id,
        events: events.sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()),
        entry_time: events[0].timestamp,
        exit_time: events[events.length - 1].timestamp,
        zones: [...new Set(events.map((e) => e.zone_name))],
        cameras: [...new Set(events.map((e) => e.camera_id))],
        event_count: events.length,
      }))
      .sort((a, b) => new Date(b.entry_time).getTime() - new Date(a.entry_time).getTime());
  }, [events]);

  const selectedVisitorData = selectedVisitor ? visitors.find((v) => v.visitor_id === selectedVisitor) : null;

  const calculateDwellTime = (entry: string, exit: string): number => {
    return Math.floor((new Date(exit).getTime() - new Date(entry).getTime()) / 1000);
  };

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Visitor Journey</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Visitor List */}
        <div className="lg:col-span-2">
          <ChartContainer title="Recent Visitors">
            <LoadingState isLoading={isLoading}>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {visitors.map((visitor) => (
                  <div
                    key={visitor.visitor_id}
                    onClick={() => setSelectedVisitor(visitor.visitor_id)}
                    className={`p-3 rounded-lg cursor-pointer transition-colors border-2 ${
                      selectedVisitor === visitor.visitor_id
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800/50'
                    }`}
                  >
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <p className="font-mono text-sm font-medium text-slate-900 dark:text-white">
                          {visitor.visitor_id}
                        </p>
                        <p className="text-xs text-slate-600 dark:text-slate-400">
                          {formatTime(visitor.entry_time)}
                        </p>
                      </div>
                      <Badge
                        label={`${visitor.event_count} events`}
                        variant="info"
                        size="sm"
                      />
                    </div>
                    <div className="flex gap-2 flex-wrap">
                      {visitor.zones.slice(0, 3).map((zone) => (
                        <Badge key={zone} label={zone} variant="info" size="sm" />
                      ))}
                      {visitor.zones.length > 3 && (
                        <Badge label={`+${visitor.zones.length - 3}`} variant="info" size="sm" />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </LoadingState>
          </ChartContainer>
        </div>

        {/* Visitor Details */}
        <div className="card p-6 h-fit">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Journey Details
          </h3>
          {selectedVisitorData ? (
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-1">Visitor ID</p>
                <p className="font-mono text-slate-900 dark:text-white break-all">
                  {selectedVisitorData.visitor_id}
                </p>
              </div>

              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-1">Entry Time</p>
                <p className="text-slate-900 dark:text-white">
                  {formatTime(selectedVisitorData.entry_time)}
                </p>
              </div>

              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-1">Dwell Time</p>
                <p className="text-slate-900 dark:text-white">
                  {formatSeconds(calculateDwellTime(selectedVisitorData.entry_time, selectedVisitorData.exit_time))}
                </p>
              </div>

              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-2">Zones Visited</p>
                <div className="flex flex-wrap gap-2">
                  {selectedVisitorData.zones.map((zone) => (
                    <Badge key={zone} label={zone} variant="info" size="sm" />
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-2">Cameras</p>
                <div className="flex flex-wrap gap-2">
                  {selectedVisitorData.cameras.map((cam) => (
                    <Badge key={cam} label={cam} variant="success" size="sm" />
                  ))}
                </div>
              </div>

              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-1">Events Count</p>
                <p className="text-2xl font-bold text-primary-500">
                  {selectedVisitorData.event_count}
                </p>
              </div>
            </div>
          ) : (
            <div className="text-center text-slate-600 dark:text-slate-400">
              <p className="text-sm">Select a visitor to view their journey</p>
            </div>
          )}
        </div>
      </div>

      {/* Events Timeline */}
      {selectedVisitorData && (
        <ChartContainer title="Journey Timeline">
          <div className="space-y-3">
            {selectedVisitorData.events.map((event, index) => (
              <div key={event.id} className="flex gap-4">
                <div className="flex flex-col items-center">
                  <div className="w-3 h-3 rounded-full bg-primary-500" />
                  {index < selectedVisitorData.events.length - 1 && (
                    <div className="w-0.5 h-12 bg-slate-200 dark:bg-slate-700" />
                  )}
                </div>
                <div className="p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 flex-1">
                  <div className="flex justify-between items-start">
                    <div>
                      <p className="font-medium text-slate-900 dark:text-white">
                        {event.event_type}
                      </p>
                      <p className="text-sm text-slate-600 dark:text-slate-400">
                        {event.zone_name} • {event.camera_id}
                      </p>
                    </div>
                    <div className="text-right">
                      <Badge
                        label={`${(event.confidence * 100).toFixed(0)}%`}
                        variant="success"
                        size="sm"
                      />
                      <p className="text-xs text-slate-600 dark:text-slate-400 mt-1">
                        {formatTime(event.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ChartContainer>
      )}
    </div>
  );
};
