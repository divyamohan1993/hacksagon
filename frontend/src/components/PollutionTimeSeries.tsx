'use client';

import React, { useMemo, useRef, useEffect, useState } from 'react';
import { Activity } from 'lucide-react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Area,
  AreaChart,
  Legend,
} from 'recharts';
import type { SensorData } from '@/types';
import { PM25_THRESHOLDS, SENSOR_COLORS } from '@/lib/constants';

interface PollutionTimeSeriesProps {
  sensors: SensorData[];
  selectedSensor: string | null;
}

interface HistoryEntry {
  time: string;
  timestamp: number;
  [key: string]: string | number;
}

const MAX_HISTORY_POINTS = 120;

export default function PollutionTimeSeries({
  sensors,
  selectedSensor,
}: PollutionTimeSeriesProps) {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const lastUpdateRef = useRef<number>(0);

  useEffect(() => {
    if (sensors.length === 0) return;
    const now = Date.now();
    if (now - lastUpdateRef.current < 2000) return;
    lastUpdateRef.current = now;

    const timeStr = new Date().toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });

    const entry: HistoryEntry = {
      time: timeStr,
      timestamp: now,
    };

    sensors.forEach((s) => {
      entry[s.id] = Number(s.pollution.pm25.toFixed(1));
    });

    const avgPm25 =
      sensors.reduce((acc, s) => acc + s.pollution.pm25, 0) / sensors.length;
    entry['avg'] = Number(avgPm25.toFixed(1));

    setHistory((prev) => {
      const next = [...prev, entry];
      if (next.length > MAX_HISTORY_POINTS) {
        return next.slice(next.length - MAX_HISTORY_POINTS);
      }
      return next;
    });
  }, [sensors]);

  const currentAvgPm25 = useMemo(() => {
    if (sensors.length === 0) return 0;
    if (selectedSensor) {
      const sensor = sensors.find((s) => s.id === selectedSensor);
      return sensor?.pollution.pm25 ?? 0;
    }
    return sensors.reduce((a, s) => a + s.pollution.pm25, 0) / sensors.length;
  }, [sensors, selectedSensor]);

  const sensorNames = useMemo(() => {
    const map: Record<string, string> = {};
    sensors.forEach((s) => {
      map[s.id] = s.name;
    });
    return map;
  }, [sensors]);

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload || payload.length === 0) return null;
    return (
      <div className="bg-[#1e2538] border border-[#2d3548] rounded-lg p-3 shadow-xl">
        <p className="text-xs text-navy-400 mb-2">{label}</p>
        {payload.map((entry: any, idx: number) => (
          <div key={idx} className="flex items-center gap-2 text-xs">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: entry.color }}
            />
            <span className="text-navy-400">
              {sensorNames[entry.dataKey] || entry.dataKey}:
            </span>
            <span className="text-white font-medium">
              {entry.value} ug/m3
            </span>
          </div>
        ))}
      </div>
    );
  };

  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-eco-500" />
          <h3 className="text-sm font-semibold text-white">PM2.5 Concentration</h3>
        </div>
        <span className="text-xs text-navy-400">
          Current avg:{' '}
          <span className="text-white font-medium">
            {currentAvgPm25.toFixed(1)} ug/m3
          </span>
        </span>
      </div>

      <div className="h-48">
        {history.length < 2 ? (
          <div className="flex items-center justify-center h-full text-sm text-navy-400">
            Collecting data...
          </div>
        ) : selectedSensor ? (
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={history}>
              <defs>
                <linearGradient id="pmGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00d68f" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#00d68f" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3548" />
              <XAxis
                dataKey="time"
                tick={{ fill: '#8899a6', fontSize: 10 }}
                stroke="#2d3548"
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: '#8899a6', fontSize: 10 }}
                stroke="#2d3548"
                domain={[0, 'auto']}
              />
              <Tooltip content={<CustomTooltip />} />
              {PM25_THRESHOLDS.map((t) => (
                <ReferenceLine
                  key={t.value}
                  y={t.value}
                  stroke={t.color}
                  strokeDasharray="4 4"
                  strokeOpacity={0.4}
                />
              ))}
              <Area
                type="monotone"
                dataKey={selectedSensor}
                stroke="#00d68f"
                fill="url(#pmGradient)"
                strokeWidth={2}
                dot={false}
                animationDuration={300}
              />
            </AreaChart>
          </ResponsiveContainer>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={history}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3548" />
              <XAxis
                dataKey="time"
                tick={{ fill: '#8899a6', fontSize: 10 }}
                stroke="#2d3548"
                interval="preserveStartEnd"
              />
              <YAxis
                tick={{ fill: '#8899a6', fontSize: 10 }}
                stroke="#2d3548"
                domain={[0, 'auto']}
              />
              <Tooltip content={<CustomTooltip />} />
              <Legend
                wrapperStyle={{ fontSize: 10, color: '#8899a6' }}
                formatter={(value: string) => sensorNames[value] || value}
              />
              {PM25_THRESHOLDS.map((t) => (
                <ReferenceLine
                  key={t.value}
                  y={t.value}
                  stroke={t.color}
                  strokeDasharray="4 4"
                  strokeOpacity={0.4}
                />
              ))}
              {sensors.map((sensor, i) => (
                <Line
                  key={sensor.id}
                  type="monotone"
                  dataKey={sensor.id}
                  stroke={SENSOR_COLORS[i % SENSOR_COLORS.length]}
                  strokeWidth={1.5}
                  dot={false}
                  animationDuration={300}
                />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>
    </div>
  );
}
