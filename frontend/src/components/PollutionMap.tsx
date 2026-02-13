'use client';

import React, { useCallback, useEffect, useRef, useMemo } from 'react';
import dynamic from 'next/dynamic';
import { MapPin } from 'lucide-react';
import type { SensorData, GridData } from '@/types';
import { MAP_CENTER, MAP_ZOOM, DARK_TILE_URL, DARK_TILE_ATTRIBUTION, getAqiColor, getPm25Color } from '@/lib/constants';

interface PollutionMapProps {
  sensors: SensorData[];
  grid: GridData | null;
  selectedSensor: string | null;
  onSelectSensor: (id: string | null) => void;
}

interface MapInnerProps {
  sensors: SensorData[];
  grid: GridData | null;
  selectedSensor: string | null;
  onSelectSensor: (id: string | null) => void;
}

function MapInnerComponent({ sensors, grid, selectedSensor, onSelectSensor }: MapInnerProps) {
  const {
    MapContainer,
    TileLayer,
    CircleMarker,
    Popup,
    Tooltip: LeafletTooltip,
    useMap,
  } = require('react-leaflet');

  function HeatmapOverlay({ grid }: { grid: GridData | null }) {
    const map = useMap();

    useEffect(() => {
      if (!grid || !grid.values || grid.values.length === 0) return;

      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return;

      const bounds = grid.bounds;
      const rows = grid.values.length;
      const cols = grid.values[0]?.length ?? 0;
      if (rows === 0 || cols === 0) return;

      canvas.width = cols * 4;
      canvas.height = rows * 4;

      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const val = grid.values[r][c];
          const color = getPm25Color(val);
          ctx.fillStyle = color;
          ctx.globalAlpha = Math.min(0.5, Math.max(0.05, val / 150));
          ctx.fillRect(c * 4, r * 4, 4, 4);
        }
      }

      const L = require('leaflet');
      const imageBounds = L.latLngBounds(
        [bounds.south, bounds.west],
        [bounds.north, bounds.east]
      );

      const overlay = L.imageOverlay(canvas.toDataURL(), imageBounds, {
        opacity: 0.6,
        interactive: false,
      });
      overlay.addTo(map);

      return () => {
        map.removeLayer(overlay);
      };
    }, [grid, map]);

    return null;
  }

  function WindArrow({ sensor }: { sensor: SensorData }) {
    const map = useMap();
    const arrowRef = useRef<any>(null);

    useEffect(() => {
      const L = require('leaflet');
      const windDir = sensor.weather.wind_direction;
      const windSpeed = sensor.weather.wind_speed;
      const rad = (windDir * Math.PI) / 180;
      const offset = 0.003;
      const endLat = sensor.lat + Math.cos(rad) * offset;
      const endLng = sensor.lng + Math.sin(rad) * offset;

      const arrow = L.polyline(
        [
          [sensor.lat, sensor.lng],
          [endLat, endLng],
        ],
        {
          color: '#8899a6',
          weight: 1.5,
          opacity: Math.min(1, windSpeed / 15),
          dashArray: '4 4',
        }
      );
      arrow.addTo(map);
      arrowRef.current = arrow;

      return () => {
        if (arrowRef.current) {
          map.removeLayer(arrowRef.current);
        }
      };
    }, [sensor, map]);

    return null;
  }

  return (
    <MapContainer
      center={MAP_CENTER}
      zoom={MAP_ZOOM}
      className="w-full h-full rounded-card"
      style={{ background: '#111827' }}
      zoomControl={true}
    >
      <TileLayer url={DARK_TILE_URL} attribution={DARK_TILE_ATTRIBUTION} />
      <HeatmapOverlay grid={grid} />
      {sensors.map((sensor) => {
        const isSelected = selectedSensor === sensor.id;
        const color = getAqiColor(sensor.pollution.aqi);
        return (
          <React.Fragment key={sensor.id}>
            <CircleMarker
              center={[sensor.lat, sensor.lng]}
              radius={isSelected ? 12 : 8}
              pathOptions={{
                fillColor: color,
                fillOpacity: isSelected ? 0.9 : 0.7,
                color: isSelected ? '#ffffff' : color,
                weight: isSelected ? 2 : 1,
              }}
              eventHandlers={{
                click: () => {
                  onSelectSensor(isSelected ? null : sensor.id);
                },
              }}
            >
              <LeafletTooltip
                direction="top"
                offset={[0, -10]}
                className="custom-tooltip"
              >
                <div className="text-xs">
                  <p className="font-semibold">{sensor.name}</p>
                  <p>AQI: {sensor.pollution.aqi}</p>
                </div>
              </LeafletTooltip>
              <Popup>
                <div className="min-w-[180px]">
                  <h4 className="font-semibold text-sm mb-2">{sensor.name}</h4>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-[#8899a6]">AQI</span>
                      <span className="font-medium" style={{ color }}>
                        {sensor.pollution.aqi} ({sensor.pollution.category})
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8899a6]">PM2.5</span>
                      <span>{sensor.pollution.pm25.toFixed(1)} ug/m3</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8899a6]">PM10</span>
                      <span>{sensor.pollution.pm10.toFixed(1)} ug/m3</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8899a6]">NO2</span>
                      <span>{sensor.pollution.no2.toFixed(1)} ppb</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8899a6]">Noise</span>
                      <span>{sensor.noise.db_level.toFixed(1)} dB</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8899a6]">Wind</span>
                      <span>
                        {sensor.weather.wind_speed.toFixed(1)} m/s @{' '}
                        {Math.round(sensor.weather.wind_direction)}deg
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8899a6]">Vehicles</span>
                      <span>{sensor.vehicles.total}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[#8899a6]">Status</span>
                      <span
                        className={
                          sensor.status === 'active' ? 'text-[#00d68f]' : 'text-[#ef4444]'
                        }
                      >
                        {sensor.status}
                      </span>
                    </div>
                  </div>
                </div>
              </Popup>
            </CircleMarker>
            <WindArrow sensor={sensor} />
          </React.Fragment>
        );
      })}
    </MapContainer>
  );
}

const MapInner = dynamic(
  () => Promise.resolve(MapInnerComponent),
  { ssr: false }
);

export default function PollutionMap({
  sensors,
  grid,
  selectedSensor,
  onSelectSensor,
}: PollutionMapProps) {
  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] overflow-hidden h-full">
      <div className="flex items-center gap-2 p-3 border-b border-[#2d3548]">
        <MapPin className="w-4 h-4 text-eco-500" />
        <h3 className="text-sm font-semibold text-white">Pollution Heatmap</h3>
        <span className="text-xs text-navy-400 ml-auto">
          {sensors.length} sensors | Click markers for details
        </span>
      </div>
      <div className="h-[400px] lg:h-[500px]">
        <MapInner
          sensors={sensors}
          grid={grid}
          selectedSensor={selectedSensor}
          onSelectSensor={onSelectSensor}
        />
      </div>
    </div>
  );
}
