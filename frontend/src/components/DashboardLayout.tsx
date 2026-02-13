'use client';

import React, { useState, useMemo, useCallback } from 'react';
import {
  Leaf,
  Wifi,
  WifiOff,
  Clock,
  MapPin,
  ChevronLeft,
  ChevronRight,
  Activity,
  Eye,
} from 'lucide-react';
import clsx from 'clsx';
import { useWebSocket } from '@/hooks/useWebSocket';
import { getAqiColor } from '@/lib/constants';
import type { SensorData } from '@/types';

import StatsBar from './StatsBar';
import PollutionMap from './PollutionMap';
import PollutionTimeSeries from './PollutionTimeSeries';
import ForecastChart from './ForecastChart';
import VehicleBreakdown from './VehicleBreakdown';
import HealthImpactCard from './HealthImpactCard';
import AcousticPanel from './AcousticPanel';
import ParticleSimulation from './ParticleSimulation';
import GreenRouter from './GreenRouter';
import CameraFeed from './CameraFeed';

function formatTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  } catch {
    return '--:--:--';
  }
}

function SensorListItem({
  sensor,
  isSelected,
  onClick,
}: {
  sensor: SensorData;
  isSelected: boolean;
  onClick: () => void;
}) {
  const color = getAqiColor(sensor.pollution.aqi);

  return (
    <button
      onClick={onClick}
      className={clsx(
        'w-full text-left p-3 rounded-btn transition-all duration-200',
        isSelected
          ? 'bg-navy-700 border border-eco-500/30 shadow-lg shadow-eco-500/5'
          : 'bg-navy-800/50 border border-transparent hover:bg-navy-700/50 hover:border-navy-600'
      )}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2 min-w-0">
          <span
            className={clsx(
              'w-2 h-2 rounded-full flex-shrink-0',
              sensor.status === 'online' ? 'status-online' : 'status-offline'
            )}
          />
          <span className="text-sm font-medium text-[#f0f4f8] truncate">
            {sensor.name}
          </span>
        </div>
        <span className="text-sm font-bold flex-shrink-0 ml-2" style={{ color }}>
          {Math.round(sensor.pollution.aqi)}
        </span>
      </div>
      <div className="flex items-center gap-3 mt-1.5 text-xs text-navy-400">
        <span>PM2.5: {sensor.pollution.pm25.toFixed(1)}</span>
        <span>{sensor.noise.db_level.toFixed(0)} dB</span>
        <span>{sensor.vehicles.total} veh</span>
      </div>
    </button>
  );
}

export default function DashboardLayout() {
  const { data, isConnected, error } = useWebSocket();
  const [selectedSensorId, setSelectedSensorId] = useState<string | null>(null);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const sensors = data?.sensors ?? [];
  const stats = data?.stats ?? null;
  const grid = data?.grid ?? null;

  const handleSensorSelect = useCallback((id: string | null) => {
    setSelectedSensorId(id);
  }, []);

  const selectedSensor = useMemo(() => {
    if (!selectedSensorId) return null;
    return sensors.find((s) => s.id === selectedSensorId) ?? null;
  }, [sensors, selectedSensorId]);

  const weather = useMemo(() => {
    if (selectedSensor) return selectedSensor.weather;
    if (sensors.length > 0) return sensors[0].weather;
    return null;
  }, [sensors, selectedSensor]);

  /* ===== Loading / connection screen ===== */
  if (!data) {
    return (
      <div className="h-full bg-navy-950 flex items-center justify-center">
        <div className="flex flex-col items-center gap-6 animate-fade-in">
          <div className="relative">
            <Leaf className="w-20 h-20 text-eco-500 animate-spin-slow" />
            <div className="absolute inset-0 blur-2xl bg-eco-500/20 rounded-full" />
          </div>
          <div className="text-center">
            <h1 className="text-3xl font-bold text-[#f0f4f8] mb-2">Eco-Lens</h1>
            <p className="text-sm text-navy-400 uppercase tracking-widest">
              Virtual Air Quality Matrix
            </p>
          </div>
          <div className="flex items-center gap-2 mt-4">
            <div className="w-2 h-2 bg-eco-500 rounded-full animate-pulse" />
            <p className="text-navy-400 text-sm">
              {error ? `Connection error: ${error}` : 'Connecting to sensor network...'}
            </p>
          </div>
          {error && (
            <p className="text-xs text-navy-400">Retrying with exponential backoff...</p>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-navy-950">
      {/* ===== Header ===== */}
      <header className="bg-navy-900/80 border-b border-navy-700 px-4 md:px-6 py-3 flex items-center justify-between backdrop-blur-md z-50 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="relative">
            <Leaf className="w-7 h-7 text-eco-500" />
            <div className="absolute inset-0 blur-md bg-eco-500/30 rounded-full" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-[#f0f4f8] tracking-tight">
              Eco-Lens
            </h1>
            <p className="text-[10px] text-navy-400 -mt-0.5 tracking-wider uppercase">
              Virtual Air Quality Matrix
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            {isConnected ? (
              <>
                <Wifi className="w-4 h-4 text-eco-500" />
                <span className="text-xs text-eco-500 font-medium hidden sm:inline">
                  Live
                </span>
                <span className="w-2 h-2 rounded-full bg-eco-500 animate-pulse" />
              </>
            ) : (
              <>
                <WifiOff className="w-4 h-4 text-danger-500" />
                <span className="text-xs text-danger-500 font-medium hidden sm:inline">
                  Offline
                </span>
              </>
            )}
          </div>

          {data?.timestamp && (
            <div className="hidden md:flex items-center gap-1.5 text-navy-400">
              <Clock className="w-3.5 h-3.5" />
              <span className="text-xs font-mono">{formatTime(data.timestamp)}</span>
            </div>
          )}

          {stats && (
            <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 bg-navy-800 rounded-btn border border-navy-700">
              <MapPin className="w-3.5 h-3.5 text-eco-500" />
              <span className="text-xs text-[#f0f4f8] font-medium">
                {stats.active_sensors} Sensors Active
              </span>
            </div>
          )}
        </div>
      </header>

      {/* ===== Body ===== */}
      <div className="flex flex-1 overflow-hidden">
        {/* ---- Left Sidebar: Sensor List ---- */}
        <aside
          className={clsx(
            'bg-navy-900 border-r border-navy-700 flex-shrink-0 flex flex-col transition-all duration-300',
            sidebarOpen ? 'w-64 xl:w-72' : 'w-0'
          )}
        >
          {sidebarOpen && (
            <>
              <div className="p-3 border-b border-navy-700 flex items-center justify-between">
                <span className="text-xs font-semibold text-navy-400 uppercase tracking-wider">
                  Sensor Network
                </span>
                <button
                  onClick={() => setSidebarOpen(false)}
                  className="p-1 hover:bg-navy-800 rounded transition-colors text-navy-400 hover:text-[#f0f4f8]"
                  aria-label="Close sidebar"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
              </div>

              {/* Selected sensor indicator */}
              {selectedSensor && (
                <div className="p-3 border-b border-navy-700 bg-navy-800/50">
                  <div className="flex items-center gap-2 text-xs text-navy-400">
                    <Eye className="w-3 h-3 text-eco-500" />
                    <span>Viewing:</span>
                    <span className="text-eco-500 font-medium truncate">
                      {selectedSensor.name}
                    </span>
                  </div>
                </div>
              )}

              <div className="flex-1 overflow-y-auto p-2 flex flex-col gap-1">
                {sensors.map((sensor) => (
                  <SensorListItem
                    key={sensor.id}
                    sensor={sensor}
                    isSelected={selectedSensorId === sensor.id}
                    onClick={() =>
                      handleSensorSelect(
                        selectedSensorId === sensor.id ? null : sensor.id
                      )
                    }
                  />
                ))}
                {sensors.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-12 text-navy-400">
                    <Activity className="w-8 h-8 mb-2 opacity-50" />
                    <p className="text-xs">No sensors detected</p>
                  </div>
                )}
              </div>
            </>
          )}
        </aside>

        {/* Sidebar toggle when collapsed */}
        {!sidebarOpen && (
          <button
            onClick={() => setSidebarOpen(true)}
            className="absolute left-0 top-1/2 -translate-y-1/2 z-40 bg-navy-800 border border-navy-700 border-l-0 rounded-r-btn p-2 hover:bg-navy-700 transition-colors text-navy-400 hover:text-[#f0f4f8]"
            aria-label="Open sidebar"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}

        {/* ---- Main Content ---- */}
        <main className="flex-1 overflow-y-auto p-3 md:p-4 xl:p-5">
          <div className="flex flex-col gap-4 max-w-[1800px] mx-auto">
            {/* Row 1: Stats Bar */}
            {stats && (
              <section className="animate-fade-in">
                <StatsBar stats={stats} />
              </section>
            )}

            {/* Row 2: Map + Side Panels */}
            <section className="grid grid-cols-1 lg:grid-cols-3 gap-4 animate-slide-up">
              {/* Map - takes 2 columns */}
              <div className="lg:col-span-2 h-[400px] xl:h-[480px]">
                <PollutionMap
                  sensors={sensors}
                  grid={grid}
                  selectedSensor={selectedSensorId}
                  onSelectSensor={handleSensorSelect}
                />
              </div>

              {/* Right column: Vehicle + Health */}
              <div className="flex flex-col gap-4">
                <VehicleBreakdown
                  sensors={sensors}
                  selectedSensor={selectedSensorId}
                />
                <HealthImpactCard
                  sensors={sensors}
                  selectedSensor={selectedSensorId}
                />
              </div>
            </section>

            {/* Row 3: Charts */}
            <section className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <PollutionTimeSeries
                sensors={sensors}
                selectedSensor={selectedSensorId}
              />
              <ForecastChart
                selectedSensor={selectedSensorId}
                sensors={sensors}
              />
            </section>

            {/* Row 4: Acoustic + Particle + Camera */}
            <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              <AcousticPanel
                sensors={sensors}
                selectedSensor={selectedSensorId}
              />
              <ParticleSimulation
                sensors={sensors}
                weather={weather}
              />
              <CameraFeed
                sensors={sensors}
                selectedSensor={selectedSensorId}
                onSelectSensor={handleSensorSelect}
              />
            </section>

            {/* Row 5: Green Router */}
            <section>
              <GreenRouter sensors={sensors} />
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
