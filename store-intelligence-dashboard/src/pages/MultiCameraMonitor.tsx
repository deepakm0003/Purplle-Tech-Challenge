import React, { useState } from 'react';
import { Camera, AlertCircle, CheckCircle } from 'lucide-react';
import { useCameras } from '../hooks/useAPI.ts';
import { LoadingState, ErrorState, StatusBadge } from '../components/common/UIElements';
import { formatRelativeTime } from '../utils/formatters';

export const MultiCameraMonitor: React.FC = () => {
  const { data: cameras, isLoading, error } = useCameras();
  const [selectedCamera, setSelectedCamera] = useState<string | null>(null);

  if (error) {
    return (
      <ErrorState
        title="Failed to load cameras"
        message="Unable to fetch camera status"
      />
    );
  }

  const selectedCameraData = cameras?.cameras.find((c) => c.id === selectedCamera);

  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Multi-Camera Monitor</h1>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
        {/* Camera Grid */}
        <div className="lg:col-span-3">
          <div className="card p-6">
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
              Camera Feeds
            </h3>
            <LoadingState isLoading={isLoading}>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {cameras?.cameras.map((cam) => (
                  <div
                    key={cam.id}
                    onClick={() => setSelectedCamera(cam.id)}
                    className={`cursor-pointer rounded-lg overflow-hidden transition-all border-2 ${
                      selectedCamera === cam.id
                        ? 'border-primary-500 shadow-lg'
                        : 'border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600'
                    }`}
                  >
                    {/* Camera Feed Placeholder */}
                    <div className="bg-gradient-to-br from-slate-800 to-slate-900 aspect-video flex items-center justify-center relative">
                      <div className="text-center">
                        <Camera className="w-8 h-8 text-slate-600 mx-auto mb-2" />
                        <p className="text-slate-400 text-sm font-medium">{cam.name}</p>
                        <p className="text-slate-500 text-xs mt-1">{cam.ip_address}</p>
                      </div>

                      {/* Status Indicator */}
                      <div className="absolute top-2 right-2 flex items-center gap-1">
                        {cam.status === 'active' ? (
                          <CheckCircle className="w-5 h-5 text-emerald-500" />
                        ) : cam.status === 'error' ? (
                          <AlertCircle className="w-5 h-5 text-red-500" />
                        ) : (
                          <AlertCircle className="w-5 h-5 text-yellow-500" />
                        )}
                      </div>
                    </div>

                    {/* Camera Stats */}
                    <div className="p-3 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-200 dark:border-slate-700">
                      <div className="flex justify-between items-center mb-2">
                        <p className="font-medium text-slate-900 dark:text-white text-sm">
                          {cam.name}
                        </p>
                        <StatusBadge
                          status={
                            (cam.status === 'footage_available'
                              ? 'active'
                              : cam.status === 'inactive' || cam.status === 'error'
                                ? cam.status
                                : 'active') as 'active' | 'inactive' | 'error'
                          }
                        />
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div>
                          <p className="text-slate-600 dark:text-slate-400">Visitors</p>
                          <p className="font-medium text-slate-900 dark:text-white">
                            {cam.visitor_count}
                          </p>
                        </div>
                        <div>
                          <p className="text-slate-600 dark:text-slate-400">Active Tracks</p>
                          <p className="font-medium text-slate-900 dark:text-white">
                            {cam.active_tracks}
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </LoadingState>
          </div>
        </div>

        {/* Camera Details Panel */}
        <div className="card p-6 h-fit sticky top-20">
          <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
            Camera Details
          </h3>
          {selectedCameraData ? (
            <div className="space-y-4">
              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase">Name</p>
                <p className="font-medium text-slate-900 dark:text-white">
                  {selectedCameraData.name}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase">IP Address</p>
                <p className="font-mono text-sm text-slate-900 dark:text-white">
                  {selectedCameraData.ip_address}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase mb-2">
                  Status
                </p>
                <StatusBadge
                  status={
                    (selectedCameraData.status === 'footage_available'
                      ? 'active'
                      : selectedCameraData.status === 'inactive' ||
                          selectedCameraData.status === 'error'
                        ? selectedCameraData.status
                        : 'active') as 'active' | 'inactive' | 'error'
                  }
                />
              </div>
              <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                <p className="text-xs text-slate-600 dark:text-slate-400 uppercase">Metrics</p>
                <div className="mt-3 space-y-2">
                  <div className="flex justify-between">
                    <span className="text-slate-600 dark:text-slate-400">Visitor Count</span>
                    <span className="font-medium text-slate-900 dark:text-white">
                      {selectedCameraData.visitor_count}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600 dark:text-slate-400">Active Tracks</span>
                    <span className="font-medium text-slate-900 dark:text-white">
                      {selectedCameraData.active_tracks}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-600 dark:text-slate-400">Last Frame</span>
                    <span className="font-medium text-slate-900 dark:text-white">
                      {formatRelativeTime(selectedCameraData.last_frame_timestamp ?? new Date().toISOString())}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-center text-slate-600 dark:text-slate-400">
              <p className="text-sm">Select a camera to view details</p>
            </div>
          )}
        </div>
      </div>

      {/* Camera Health Summary */}
      <div className="card p-6">
        <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4">
          System Health
        </h3>
        <LoadingState isLoading={isLoading}>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <p className="text-3xl font-bold text-emerald-500">
                {cameras?.cameras.filter((c) => c.status === 'active').length}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400">Active Cameras</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-slate-900 dark:text-white">
                {cameras?.cameras.reduce((sum, c) => sum + (c.visitor_count ?? 0), 0)}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400">Total Visitors</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-slate-900 dark:text-white">
                {cameras?.cameras.reduce((sum, c) => sum + (c.active_tracks ?? 0), 0)}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400">Active Tracks</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-yellow-500">
                {cameras?.cameras.filter((c) => c.status !== 'active').length}
              </p>
              <p className="text-sm text-slate-600 dark:text-slate-400">Inactive Cameras</p>
            </div>
          </div>
        </LoadingState>
      </div>
    </div>
  );
};
