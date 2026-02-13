'use client';

import React, { useMemo } from 'react';
import { Truck } from 'lucide-react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  Cell,
} from 'recharts';
import type { SensorData } from '@/types';

interface VehicleBreakdownProps {
  sensors: SensorData[];
  selectedSensor: string | null;
}

const VEHICLE_COLORS = {
  trucks: '#ef4444',
  cars: '#3b82f6',
  buses: '#f59e0b',
  motorcycles: '#00d68f',
};

const VEHICLE_LABELS: Record<string, string> = {
  trucks: 'Trucks',
  cars: 'Cars',
  buses: 'Buses',
  motorcycles: 'Motorcycles',
};

export default function VehicleBreakdown({
  sensors,
  selectedSensor,
}: VehicleBreakdownProps) {
  const chartData = useMemo(() => {
    if (sensors.length === 0) {
      return [
        { type: 'Trucks', count: 0, fill: VEHICLE_COLORS.trucks },
        { type: 'Cars', count: 0, fill: VEHICLE_COLORS.cars },
        { type: 'Buses', count: 0, fill: VEHICLE_COLORS.buses },
        { type: 'Motorcycles', count: 0, fill: VEHICLE_COLORS.motorcycles },
      ];
    }

    if (selectedSensor) {
      const sensor = sensors.find((s) => s.id === selectedSensor);
      if (!sensor) {
        return [
          { type: 'Trucks', count: 0, fill: VEHICLE_COLORS.trucks },
          { type: 'Cars', count: 0, fill: VEHICLE_COLORS.cars },
          { type: 'Buses', count: 0, fill: VEHICLE_COLORS.buses },
          { type: 'Motorcycles', count: 0, fill: VEHICLE_COLORS.motorcycles },
        ];
      }
      return [
        { type: 'Trucks', count: sensor.vehicles.trucks, fill: VEHICLE_COLORS.trucks },
        { type: 'Cars', count: sensor.vehicles.cars, fill: VEHICLE_COLORS.cars },
        { type: 'Buses', count: sensor.vehicles.buses, fill: VEHICLE_COLORS.buses },
        { type: 'Motorcycles', count: sensor.vehicles.motorcycles, fill: VEHICLE_COLORS.motorcycles },
      ];
    }

    const totals = sensors.reduce(
      (acc, s) => ({
        trucks: acc.trucks + s.vehicles.trucks,
        cars: acc.cars + s.vehicles.cars,
        buses: acc.buses + s.vehicles.buses,
        motorcycles: acc.motorcycles + s.vehicles.motorcycles,
      }),
      { trucks: 0, cars: 0, buses: 0, motorcycles: 0 }
    );

    return [
      { type: 'Trucks', count: totals.trucks, fill: VEHICLE_COLORS.trucks },
      { type: 'Cars', count: totals.cars, fill: VEHICLE_COLORS.cars },
      { type: 'Buses', count: totals.buses, fill: VEHICLE_COLORS.buses },
      { type: 'Motorcycles', count: totals.motorcycles, fill: VEHICLE_COLORS.motorcycles },
    ];
  }, [sensors, selectedSensor]);

  const totalCount = chartData.reduce((a, b) => a + b.count, 0);

  const CustomTooltip = ({ active, payload }: any) => {
    if (!active || !payload || payload.length === 0) return null;
    const data = payload[0].payload;
    const pct = totalCount > 0 ? ((data.count / totalCount) * 100).toFixed(1) : '0';
    return (
      <div className="bg-[#1e2538] border border-[#2d3548] rounded-lg p-3 shadow-xl">
        <p className="text-xs text-navy-400 mb-1">{data.type}</p>
        <p className="text-sm text-white font-semibold">{data.count.toLocaleString()}</p>
        <p className="text-xs text-navy-400">{pct}% of total</p>
      </div>
    );
  };

  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Truck className="w-4 h-4 text-eco-500" />
          <h3 className="text-sm font-semibold text-white">Vehicle Classification</h3>
        </div>
        <span className="text-xs text-navy-400">
          Total: <span className="text-white font-medium">{totalCount.toLocaleString()}</span>
        </span>
      </div>

      <div className="h-48">
        {totalCount === 0 ? (
          <div className="flex items-center justify-center h-full text-sm text-navy-400">
            No vehicle data
          </div>
        ) : (
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} barSize={32}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2d3548" vertical={false} />
              <XAxis
                dataKey="type"
                tick={{ fill: '#8899a6', fontSize: 10 }}
                stroke="#2d3548"
              />
              <YAxis
                tick={{ fill: '#8899a6', fontSize: 10 }}
                stroke="#2d3548"
              />
              <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(45, 53, 72, 0.3)' }} />
              <Bar dataKey="count" radius={[4, 4, 0, 0]} animationDuration={500}>
                {chartData.map((entry, index) => (
                  <Cell key={index} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="flex justify-center gap-4 mt-2">
        {Object.entries(VEHICLE_COLORS).map(([key, color]) => (
          <div key={key} className="flex items-center gap-1.5">
            <div className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-[10px] text-navy-400">{VEHICLE_LABELS[key]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
