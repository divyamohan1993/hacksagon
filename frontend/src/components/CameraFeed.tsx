'use client';

import React, { useMemo } from 'react';
import { Camera, Truck, Car, Bus } from 'lucide-react';
import clsx from 'clsx';
import type { SensorData } from '@/types';
import { getAqiColor } from '@/lib/constants';

interface CameraFeedProps {
  sensors: SensorData[];
  selectedSensor: string | null;
  onSelectSensor: (id: string | null) => void;
}

function timeSince(timestamp: string): string {
  const now = Date.now();
  const then = new Date(timestamp).getTime();
  const diffSec = Math.max(0, Math.round((now - then) / 1000));
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  return `${Math.floor(diffSec / 3600)}h ago`;
}

export default function CameraFeed({
  sensors,
  selectedSensor,
  onSelectSensor,
}: CameraFeedProps) {
  const displaySensors = useMemo(() => {
    return sensors.slice(0, 6);
  }, [sensors]);

  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] p-4 h-full">
      <div className="flex items-center gap-2 mb-4">
        <Camera className="w-4 h-4 text-eco-500" />
        <h3 className="text-sm font-semibold text-white">Virtual Sensor Network</h3>
        <span className="text-xs text-navy-400 ml-auto">
          {sensors.filter((s) => s.status === 'active').length}/{sensors.length} online
        </span>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {displaySensors.map((sensor) => {
          const isSelected = selectedSensor === sensor.id;
          const isActive = sensor.status === 'active';
          const aqiColor = getAqiColor(sensor.pollution.aqi);

          return (
            <button
              key={sensor.id}
              onClick={() => onSelectSensor(sensor.id)}
              className={clsx(
                'bg-[#0a0e17]/60 rounded-lg p-3 text-left',
                'border transition-all duration-200',
                isSelected
                  ? 'border-eco-500/50 shadow-lg shadow-eco-500/10'
                  : 'border-[#2d3548] hover:border-[#3d4760]',
                'hover:-translate-y-0.5'
              )}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-white truncate pr-1">
                  {sensor.name}
                </span>
                <div className="flex items-center gap-1">
                  <div
                    className={clsx(
                      'w-1.5 h-1.5 rounded-full',
                      isActive ? 'bg-eco-500 pulse-dot' : 'bg-danger-500'
                    )}
                  />
                  <span
                    className={clsx(
                      'text-[9px] font-medium',
                      isActive ? 'text-eco-500' : 'text-danger-500'
                    )}
                  >
                    {isActive ? 'Active' : 'Offline'}
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2 mb-2">
                <div className="flex items-center gap-1 text-[10px] text-navy-400">
                  <Truck className="w-3 h-3 text-danger-400" />
                  <span>{sensor.vehicles.trucks}</span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-navy-400">
                  <Car className="w-3 h-3 text-accent-400" />
                  <span>{sensor.vehicles.cars}</span>
                </div>
                <div className="flex items-center gap-1 text-[10px] text-navy-400">
                  <Bus className="w-3 h-3 text-warning-400" />
                  <span>{sensor.vehicles.buses}</span>
                </div>
              </div>

              <div className="flex items-center justify-between">
                <div
                  className="px-1.5 py-0.5 rounded text-[9px] font-semibold"
                  style={{
                    backgroundColor: `${aqiColor}20`,
                    color: aqiColor,
                    border: `1px solid ${aqiColor}40`,
                  }}
                >
                  AQI {sensor.pollution.aqi}
                </div>
                <span className="text-[9px] text-navy-400">
                  {timeSince(sensor.timestamp)}
                </span>
              </div>
            </button>
          );
        })}

        {displaySensors.length === 0 && (
          <div className="col-span-full flex items-center justify-center h-32 text-sm text-navy-400">
            No sensors available
          </div>
        )}
      </div>
    </div>
  );
}
