'use client';

import React, { useMemo, useRef, useEffect, useState } from 'react';
import { Volume2 } from 'lucide-react';
import clsx from 'clsx';
import type { SensorData } from '@/types';
import { getNoiseColor, getNoiseCategory } from '@/lib/constants';

interface AcousticPanelProps {
  sensors: SensorData[];
  selectedSensor: string | null;
}

const MAX_SPARKLINE_POINTS = 30;

export default function AcousticPanel({ sensors, selectedSensor }: AcousticPanelProps) {
  const [history, setHistory] = useState<number[]>([]);
  const prevNoiseRef = useRef<number>(0);

  const currentNoise = useMemo(() => {
    if (sensors.length === 0) return 0;
    if (selectedSensor) {
      const sensor = sensors.find((s) => s.id === selectedSensor);
      return sensor?.noise.db_level ?? 0;
    }
    const sum = sensors.reduce((acc, s) => acc + s.noise.db_level, 0);
    return sum / sensors.length;
  }, [sensors, selectedSensor]);

  useEffect(() => {
    if (currentNoise !== prevNoiseRef.current && currentNoise > 0) {
      prevNoiseRef.current = currentNoise;
      setHistory((prev) => {
        const next = [...prev, currentNoise];
        if (next.length > MAX_SPARKLINE_POINTS) {
          return next.slice(next.length - MAX_SPARKLINE_POINTS);
        }
        return next;
      });
    }
  }, [currentNoise]);

  const noiseColor = getNoiseColor(currentNoise);
  const noiseCategory = getNoiseCategory(currentNoise);
  const fillPercent = Math.min(100, Math.max(0, (currentNoise / 120) * 100));

  const sparklinePath = useMemo(() => {
    if (history.length < 2) return '';
    const w = 200;
    const h = 30;
    const minVal = Math.min(...history) - 5;
    const maxVal = Math.max(...history) + 5;
    const range = maxVal - minVal || 1;
    const points = history.map((val, i) => {
      const x = (i / (history.length - 1)) * w;
      const y = h - ((val - minVal) / range) * h;
      return `${x},${y}`;
    });
    return `M${points.join(' L')}`;
  }, [history]);

  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] p-4">
      <div className="flex items-center gap-2 mb-4">
        <Volume2 className="w-4 h-4 text-eco-500" />
        <h3 className="text-sm font-semibold text-white">Acoustic Pollution</h3>
      </div>

      <div className="mb-4">
        <div className="flex items-end gap-2 mb-2">
          <span
            className="text-3xl font-bold transition-colors duration-300"
            style={{ color: noiseColor }}
          >
            {currentNoise.toFixed(1)}
          </span>
          <span className="text-sm text-navy-400 mb-1">dB</span>
        </div>

        <div
          className={clsx(
            'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium mb-3'
          )}
          style={{
            backgroundColor: `${noiseColor}20`,
            color: noiseColor,
            border: `1px solid ${noiseColor}40`,
          }}
        >
          {noiseCategory}
        </div>
      </div>

      <div className="mb-3">
        <div className="flex justify-between text-[10px] text-navy-400 mb-1">
          <span>0 dB</span>
          <span>60</span>
          <span>120 dB</span>
        </div>
        <div className="h-3 bg-[#0a0e17] rounded-full overflow-hidden relative">
          <div
            className="h-full rounded-full transition-all duration-500 ease-out"
            style={{
              width: `${fillPercent}%`,
              background: `linear-gradient(90deg, #00d68f 0%, #f59e0b 40%, #ff8c00 60%, #ef4444 100%)`,
            }}
          />
          <div
            className="absolute top-0 h-full w-0.5 bg-white/60"
            style={{ left: `${(55 / 120) * 100}%` }}
            title="WHO recommended limit: 55 dB"
          />
        </div>
      </div>

      <p className="text-[10px] text-navy-400 mb-3">
        WHO recommended: <span className="text-eco-500 font-medium">&lt; 55 dB</span>
      </p>

      {history.length >= 2 && (
        <div className="mt-2">
          <p className="text-[10px] text-navy-400 mb-1">Recent readings</p>
          <svg viewBox="0 0 200 30" className="w-full h-8" preserveAspectRatio="none">
            <path
              d={sparklinePath}
              fill="none"
              stroke={noiseColor}
              strokeWidth="1.5"
              strokeLinejoin="round"
              strokeLinecap="round"
              opacity={0.8}
            />
          </svg>
        </div>
      )}
    </div>
  );
}
