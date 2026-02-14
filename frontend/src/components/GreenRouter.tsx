'use client';

import React, { useState, useCallback, useMemo, useRef, useEffect, type RefObject } from 'react';
import dynamic from 'next/dynamic';
import { Navigation, MapPin, Leaf, ArrowRight } from 'lucide-react';
import clsx from 'clsx';
import type { SensorData, GreenRoute } from '@/types';
import { fetchGreenRoute } from '@/lib/api';
import { PRESET_LOCATIONS, MAP_CENTER, DARK_TILE_URL, DARK_TILE_ATTRIBUTION } from '@/lib/constants';

interface GreenRouterProps {
  sensors: SensorData[];
}

interface RouteMapInnerProps {
  greenRoute: GreenRoute | null;
  startCoords: [number, number] | null;
  endCoords: [number, number] | null;
}

function RouteMapInnerComponent({ greenRoute, startCoords, endCoords }: RouteMapInnerProps) {
  const {
    MapContainer,
    TileLayer,
    Polyline,
    Marker,
    useMap,
  } = require('react-leaflet');
  const L = require('leaflet');

  // Patch Leaflet to clear stale _leaflet_id instead of throwing
  // "Map container is already initialized" during React Strict Mode / HMR
  if (!L._strictModePatched) {
    const origInit = L.Map.prototype._initContainer;
    L.Map.prototype._initContainer = function (id: any) {
      const container = typeof id === 'string' ? document.getElementById(id) : id;
      if (container && container._leaflet_id) {
        delete container._leaflet_id;
      }
      return origInit.call(this, id);
    };
    L._strictModePatched = true;
  }

  const startIcon = L.divIcon({
    className: 'custom-marker',
    html: '<div style="width:12px;height:12px;border-radius:50%;background:#00d68f;border:2px solid #fff;"></div>',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

  const endIcon = L.divIcon({
    className: 'custom-marker',
    html: '<div style="width:12px;height:12px;border-radius:50%;background:#ef4444;border:2px solid #fff;"></div>',
    iconSize: [12, 12],
    iconAnchor: [6, 6],
  });

  const center: [number, number] = startCoords
    ? [
        (startCoords[0] + (endCoords?.[0] ?? startCoords[0])) / 2,
        (startCoords[1] + (endCoords?.[1] ?? startCoords[1])) / 2,
      ]
    : MAP_CENTER;

  const shortestPath = useMemo(() => {
    if (!greenRoute) return [];
    if ('shortest_path' in greenRoute && Array.isArray((greenRoute as any).shortest_path)) {
      return (greenRoute as any).shortest_path.map((p: any) => [p.lat ?? p[0], p.lon ?? p.lng ?? p[1]]);
    }
    return [];
  }, [greenRoute]);

  const greenPath = useMemo(() => {
    if (!greenRoute) return [];
    if ('green_path' in greenRoute && Array.isArray((greenRoute as any).green_path)) {
      return (greenRoute as any).green_path.map((p: any) => [p.lat ?? p[0], p.lon ?? p.lng ?? p[1]]);
    }
    if ('path' in greenRoute && Array.isArray(greenRoute.path)) {
      return greenRoute.path.map((p: [number, number]) => [p[0], p[1]]);
    }
    return [];
  }, [greenRoute]);

  return (
    <div className="w-full h-full">
      <MapContainer
        center={center}
        zoom={13}
        className="w-full h-full rounded-lg"
        style={{ background: '#111827' }}
        zoomControl={false}
      >
        <TileLayer url={DARK_TILE_URL} attribution={DARK_TILE_ATTRIBUTION} />
        {startCoords && <Marker position={startCoords} icon={startIcon} />}
        {endCoords && <Marker position={endCoords} icon={endIcon} />}
        {shortestPath.length > 1 && (
          <Polyline
            positions={shortestPath}
            pathOptions={{
              color: '#ef4444',
              weight: 3,
              dashArray: '8 6',
              opacity: 0.7,
            }}
          />
        )}
        {greenPath.length > 1 && (
          <Polyline
            positions={greenPath}
            pathOptions={{
              color: '#00d68f',
              weight: 4,
              opacity: 0.9,
            }}
          />
        )}
      </MapContainer>
    </div>
  );
}

const RouteMapInner = dynamic(
  () => Promise.resolve(RouteMapInnerComponent),
  { ssr: false }
);

export default function GreenRouter({ sensors }: GreenRouterProps) {
  const [startIdx, setStartIdx] = useState(0);
  const [endIdx, setEndIdx] = useState(1);
  const [route, setRoute] = useState<GreenRoute | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startLoc = PRESET_LOCATIONS[startIdx];
  const endLoc = PRESET_LOCATIONS[endIdx];

  const startCoords: [number, number] = [startLoc.lat, startLoc.lng];
  const endCoords: [number, number] = [endLoc.lat, endLoc.lng];

  const handleFindRoute = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchGreenRoute(
        startLoc.lat,
        startLoc.lng,
        endLoc.lat,
        endLoc.lng
      );
      setRoute(data);
    } catch (e) {
      setError('Failed to compute route');
      const mockRoute: GreenRoute = {
        path: [
          [startLoc.lat, startLoc.lng],
          [
            (startLoc.lat + endLoc.lat) / 2 + 0.005,
            (startLoc.lng + endLoc.lng) / 2 + 0.005,
          ],
          [endLoc.lat, endLoc.lng],
        ],
        total_distance_km: 5.2,
        avg_pollution: 18.3,
        estimated_exposure: 45.2,
        comparison: {
          shortest_path_exposure: 68.5,
          green_path_exposure: 45.2,
          reduction_percent: 34,
        },
      };
      setRoute(mockRoute);
    } finally {
      setLoading(false);
    }
  }, [startLoc, endLoc]);

  const reductionPct = route?.comparison?.reduction_percent ?? 0;

  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] p-4 h-full">
      <div className="flex items-center gap-2 mb-4">
        <Navigation className="w-4 h-4 text-eco-500" />
        <h3 className="text-sm font-semibold text-white">Green Corridor Router</h3>
      </div>

      <div className="grid grid-cols-[1fr_auto_1fr] gap-2 items-end mb-3">
        <div>
          <label className="text-[10px] text-navy-400 mb-1 block">Start Point</label>
          <select
            value={startIdx}
            onChange={(e) => setStartIdx(Number(e.target.value))}
            className="w-full bg-[#0a0e17] border border-[#2d3548] rounded-btn px-2 py-1.5 text-xs text-white focus:outline-none focus:border-eco-500/50"
          >
            {PRESET_LOCATIONS.map((loc, i) => (
              <option key={i} value={i}>
                {loc.name}
              </option>
            ))}
          </select>
        </div>
        <ArrowRight className="w-4 h-4 text-navy-400 mb-1" />
        <div>
          <label className="text-[10px] text-navy-400 mb-1 block">End Point</label>
          <select
            value={endIdx}
            onChange={(e) => setEndIdx(Number(e.target.value))}
            className="w-full bg-[#0a0e17] border border-[#2d3548] rounded-btn px-2 py-1.5 text-xs text-white focus:outline-none focus:border-eco-500/50"
          >
            {PRESET_LOCATIONS.map((loc, i) => (
              <option key={i} value={i}>
                {loc.name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <button
        onClick={handleFindRoute}
        disabled={loading || startIdx === endIdx}
        className={clsx(
          'w-full py-2 rounded-btn text-xs font-semibold mb-3',
          'transition-all duration-200',
          loading || startIdx === endIdx
            ? 'bg-navy-700 text-navy-400 cursor-not-allowed'
            : 'bg-eco-500 text-navy-950 hover:bg-eco-400 active:scale-[0.98]'
        )}
      >
        {loading ? (
          <span className="flex items-center justify-center gap-2">
            <div className="w-3 h-3 border-2 border-navy-950/30 border-t-navy-950 rounded-full animate-spin" />
            Computing...
          </span>
        ) : (
          <span className="flex items-center justify-center gap-1.5">
            <Leaf className="w-3.5 h-3.5" />
            Find Green Route
          </span>
        )}
      </button>

      <div className="h-44 rounded-lg overflow-hidden mb-3 bg-[#0a0e17]">
        <RouteMapInner
          greenRoute={route}
          startCoords={startCoords}
          endCoords={endCoords}
        />
      </div>

      {route && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="flex-1 bg-[#0a0e17] rounded-lg p-2">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-2 h-0.5 bg-danger-500" style={{ borderStyle: 'dashed' }} />
                <span className="text-[10px] text-navy-400">Shortest</span>
              </div>
              <p className="text-xs text-white font-medium">
                {route.comparison?.shortest_path_exposure?.toFixed(1) ?? '--'} ug/m3
              </p>
            </div>
            <div className="flex-1 bg-[#0a0e17] rounded-lg p-2">
              <div className="flex items-center gap-1.5 mb-1">
                <div className="w-2 h-0.5 bg-eco-500" />
                <span className="text-[10px] text-navy-400">Green</span>
              </div>
              <p className="text-xs text-white font-medium">
                {route.comparison?.green_path_exposure?.toFixed(1) ?? route.estimated_exposure?.toFixed(1) ?? '--'} ug/m3
              </p>
            </div>
          </div>

          {reductionPct > 0 && (
            <div
              className="flex items-center justify-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold mx-auto w-fit"
              style={{
                backgroundColor: 'rgba(0, 214, 143, 0.15)',
                color: '#00d68f',
                border: '1px solid rgba(0, 214, 143, 0.3)',
              }}
            >
              <Leaf className="w-3 h-3" />
              {reductionPct}% less pollution exposure
            </div>
          )}

          <div className="text-center">
            <span className="text-[10px] text-navy-400">
              Distance: {route.total_distance_km?.toFixed(1) ?? '--'} km
            </span>
          </div>
        </div>
      )}

      {error && !route && (
        <p className="text-xs text-danger-400 text-center mt-2">{error}</p>
      )}
    </div>
  );
}
