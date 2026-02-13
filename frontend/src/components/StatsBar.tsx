'use client';

import React from 'react';
import { Car, Activity, Satellite, Volume2 } from 'lucide-react';
import clsx from 'clsx';
import type { GlobalStats } from '@/types';
import { getAqiColor, getNoiseColor } from '@/lib/constants';

interface StatsBarProps {
  stats: GlobalStats | null;
}

interface StatCardProps {
  icon: React.ReactNode;
  value: string | number;
  label: string;
  valueColor: string;
}

function StatCard({ icon, value, label, valueColor }: StatCardProps) {
  return (
    <div
      className={clsx(
        'bg-[#1e2538] rounded-card p-4 border border-[#2d3548]',
        'transition-all duration-300',
        'hover:border-eco-500/30 hover:shadow-lg hover:shadow-eco-500/5',
        'hover:-translate-y-0.5'
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="p-2 rounded-lg bg-[#0a0e17]/60">{icon}</div>
      </div>
      <div
        className="text-2xl font-bold mb-1 transition-colors duration-500"
        style={{ color: valueColor }}
      >
        {value}
      </div>
      <div className="text-xs text-navy-400 uppercase tracking-wider">{label}</div>
    </div>
  );
}

export default function StatsBar({ stats }: StatsBarProps) {
  const totalVehicles = stats?.total_vehicles_detected ?? 0;
  const avgAqi = stats?.avg_aqi ?? 0;
  const activeSensors = stats?.active_sensors ?? 0;
  const avgNoise = stats?.avg_noise_db ?? 0;

  const vehicleColor = totalVehicles > 500 ? '#ef4444' : totalVehicles > 200 ? '#f59e0b' : '#00d68f';
  const aqiColor = getAqiColor(avgAqi);
  const sensorColor = '#00d68f';
  const noiseColor = getNoiseColor(avgNoise);

  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        icon={<Car className="w-4 h-4 text-accent-400" />}
        value={totalVehicles.toLocaleString()}
        label="Vehicles Detected"
        valueColor={vehicleColor}
      />
      <StatCard
        icon={<Activity className="w-4 h-4 text-eco-500" />}
        value={Math.round(avgAqi)}
        label="Average AQI"
        valueColor={aqiColor}
      />
      <StatCard
        icon={<Satellite className="w-4 h-4 text-accent-400" />}
        value={activeSensors}
        label="Active Sensors"
        valueColor={sensorColor}
      />
      <StatCard
        icon={<Volume2 className="w-4 h-4 text-warning-400" />}
        value={`${avgNoise.toFixed(1)} dB`}
        label="Avg Noise Level"
        valueColor={noiseColor}
      />
    </div>
  );
}
