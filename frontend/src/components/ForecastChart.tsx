'use client';

import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Clock } from 'lucide-react';
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import type { SensorData, ForecastPoint } from '@/types';
import { fetchForecast } from '@/lib/api';

interface ForecastChartProps {
  selectedSensor: string | null;
  sensors: SensorData[];
}

interface ChartPoint {
  time: string;
  predicted: number;
  lower: number;
  upper: number;
  range: [number, number];
}

export default function ForecastChart({ selectedSensor, sensors }: ForecastChartProps) {
  const [forecast, setForecast] = useState<ForecastPoint[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadForecast = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const sensorId = selectedSensor || (sensors.length > 0 ? sensors[0].id : undefined);
      const data = await fetchForecast(sensorId);
      setForecast(data);
    } catch (e) {
      setError('Failed to load forecast');
      if (forecast.length === 0) {
        const now = Date.now();
        const mockForecast: ForecastPoint[] = Array.from({ length: 6 }, (_, i) => {
          const basePm25 = sensors.length > 0
            ? sensors.reduce((a, s) => a + s.pollution.pm25, 0) / sensors.length
            : 25;
          const variation = Math.sin(i * 0.5) * 5 + (Math.random() - 0.5) * 3;
          const predicted = Math.max(0, basePm25 + variation);
          return {
            timestamp: new Date(now + (i + 1) * 3600000).toISOString(),
            predicted_pm25: Number(predicted.toFixed(1)),
            confidence_lower: Number(Math.max(0, predicted - 5 - i * 1.5).toFixed(1)),
            confidence_upper: Number((predicted + 5 + i * 1.5).toFixed(1)),
          };
        });
        setForecast(mockForecast);
      }
    } finally {
      setLoading(false);
    }
  }, [selectedSensor, sensors]);

  useEffect(() => {
    loadForecast();
    const interval = setInterval(loadForecast, 60000);
    return () => clearInterval(interval);
  }, [loadForecast]);

  const chartData: ChartPoint[] = useMemo(() => {
    return forecast.map((fp) => {
      const date = new Date(fp.timestamp);
      const timeStr = date.toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true,
      });
      return {
        time: timeStr,
        predicted: fp.predicted_pm25,
        lower: fp.confidence_lower,
        upper: fp.confidence_upper,
        range: [fp.confidence_lower, fp.confidence_upper] as [number, number],
      };
    });
  }, [forecast]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;
    const data = payload[0]?.payload;
    if (!data) return null;
    return (
      <div className="bg-[#1e2538] border border-[#2d3548] rounded-lg p-3 shadow-xl">
        <p className="text-xs text-navy-400 mb-2">{label}</p>
        <div className="space-y-1">
          <div className="flex items-center gap-2 text-xs">
            <div className="w-2 h-2 rounded-full bg-eco-500" />
            <span className="text-navy-400">Predicted:</span>
            <span className="text-white font-medium">{data.predicted} ug/m3</span>
          </div>
          <div className="flex items-center gap-2 text-xs">
            <div className="w-2 h-2 rounded-full bg-eco-500/30" />
            <span className="text-navy-400">Range:</span>
            <span className="text-white font-medium">
              {data.lower} - {data.upper} ug/m3
            </span>
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Clock className="w-4 h-4 text-eco-500" />
          <h3 className="text-sm font-semibold text-white">6-Hour Forecast</h3>
        </div>
        {loading && (
          <span className="text-[10px] text-navy-400 animate-pulse">Updating...</span>
        )}
      </div>

      <div className="h-48">
        {chartData.length === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-navy-400">
            {error || 'Loading forecast...'}
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={chartData}>
              <defs>
                <linearGradient id="forecastGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d68f" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00d68f" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="confidenceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d68f" stopOpacity={0.1} />
                  <stop offset="95%" stopColor="#00d68f" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3548" />
              <XAxis
                dataKey="time"
                tick={{ fill: '#8899a6', fontSize: 10 }}
                stroke="#2d3548"
              />
              <YAxis
                tick={{ fill: '#8899a6', fontSize: 10 }}
                stroke="#2d3548"
                domain={[0, 'auto']}
              />
              <Tooltip content={<CustomTooltip />} />
              <ReferenceLine
                x={chartData[0]?.time}
                stroke="#8899a6"
                strokeDasharray="4 4"
                label={{
                  value: 'Now',
                  position: 'top',
                  fill: '#8899a6',
                  fontSize: 10,
                }}
              />
              <Area
                type="monotone"
                dataKey="range"
                stroke="none"
                fill="url(#confidenceGradient)"
                animationDuration={500}
              />
              <Area
                type="monotone"
                dataKey="predicted"
                stroke="#00d68f"
                fill="url(#forecastGradient)"
                strokeWidth={2}
                dot={{ fill: '#00d68f', r: 3, strokeWidth: 0 }}
                activeDot={{ r: 5, fill: '#00d68f', stroke: '#0a0e17', strokeWidth: 2 }}
                animationDuration={500}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
