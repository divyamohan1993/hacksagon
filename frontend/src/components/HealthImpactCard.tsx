'use client';

import React, { useMemo, useEffect, useState } from 'react';
import { Heart, AlertTriangle, Cigarette, ShieldAlert } from 'lucide-react';
import clsx from 'clsx';
import type { SensorData } from '@/types';

interface HealthImpactCardProps {
  sensors: SensorData[];
  selectedSensor: string | null;
}

function computeHealthScore(pm25: number): number {
  if (pm25 <= 12) return Math.max(80, 100 - pm25 * 1.5);
  if (pm25 <= 35.4) return Math.max(55, 80 - (pm25 - 12) * 1.1);
  if (pm25 <= 55.4) return Math.max(35, 55 - (pm25 - 35.4) * 1.0);
  if (pm25 <= 150.4) return Math.max(10, 35 - (pm25 - 55.4) * 0.26);
  return Math.max(0, 10 - (pm25 - 150.4) * 0.1);
}

function getRiskLevel(score: number): { label: string; color: string } {
  if (score >= 80) return { label: 'Low', color: '#00d68f' };
  if (score >= 60) return { label: 'Moderate', color: '#f59e0b' };
  if (score >= 40) return { label: 'High', color: '#ff8c00' };
  if (score >= 20) return { label: 'Very High', color: '#ef4444' };
  return { label: 'Hazardous', color: '#7f1d1d' };
}

function getScoreColor(score: number): string {
  if (score >= 80) return '#00d68f';
  if (score >= 60) return '#f59e0b';
  if (score >= 40) return '#ff8c00';
  if (score >= 20) return '#ef4444';
  return '#7f1d1d';
}

function getAdvisory(score: number): string {
  if (score >= 80) return 'Air quality is satisfactory. Enjoy outdoor activities.';
  if (score >= 60) return 'Unusually sensitive individuals should consider limiting prolonged outdoor exertion.';
  if (score >= 40) return 'People with respiratory conditions should reduce prolonged outdoor exertion.';
  if (score >= 20) return 'Everyone should reduce prolonged outdoor exertion. Keep windows closed.';
  return 'Avoid all outdoor physical activity. Health emergency conditions.';
}

export default function HealthImpactCard({ sensors, selectedSensor }: HealthImpactCardProps) {
  const [animatedScore, setAnimatedScore] = useState(0);

  const avgPm25 = useMemo(() => {
    if (sensors.length === 0) return 0;
    if (selectedSensor) {
      const sensor = sensors.find((s) => s.id === selectedSensor);
      return sensor?.pollution.pm25 ?? 0;
    }
    const sum = sensors.reduce((acc, s) => acc + s.pollution.pm25, 0);
    return sum / sensors.length;
  }, [sensors, selectedSensor]);

  const score = useMemo(() => Math.round(computeHealthScore(avgPm25)), [avgPm25]);
  const risk = useMemo(() => getRiskLevel(score), [score]);
  const scoreColor = useMemo(() => getScoreColor(score), [score]);
  const advisory = useMemo(() => getAdvisory(score), [score]);

  const equivalentCigarettes = useMemo(() => {
    return Math.max(0, (avgPm25 / 22) * 1).toFixed(2);
  }, [avgPm25]);

  useEffect(() => {
    const duration = 800;
    const steps = 30;
    const stepDuration = duration / steps;
    const diff = score - animatedScore;
    if (Math.abs(diff) < 1) {
      setAnimatedScore(score);
      return;
    }
    let step = 0;
    const interval = setInterval(() => {
      step++;
      const progress = step / steps;
      const eased = 1 - Math.pow(1 - progress, 3);
      setAnimatedScore(Math.round(animatedScore + diff * eased));
      if (step >= steps) {
        clearInterval(interval);
        setAnimatedScore(score);
      }
    }, stepDuration);
    return () => clearInterval(interval);
  }, [score]);

  const circumference = 2 * Math.PI * 50;
  const offset = circumference - (animatedScore / 100) * circumference;

  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] p-4">
      <div className="flex items-center gap-2 mb-4">
        <Heart className="w-4 h-4 text-eco-500" />
        <h3 className="text-sm font-semibold text-white">Health Impact Score</h3>
      </div>

      <div className="flex items-center gap-4">
        <div className="flex-shrink-0">
          <svg viewBox="0 0 120 120" className="w-28 h-28">
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              stroke="#2d3548"
              strokeWidth="8"
            />
            <circle
              cx="60"
              cy="60"
              r="50"
              fill="none"
              stroke={scoreColor}
              strokeWidth="8"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              strokeLinecap="round"
              transform="rotate(-90 60 60)"
              className="transition-all duration-700 ease-out"
            />
            <text
              x="60"
              y="55"
              textAnchor="middle"
              dominantBaseline="middle"
              fill="white"
              fontSize="24"
              fontWeight="bold"
            >
              {animatedScore}
            </text>
            <text
              x="60"
              y="78"
              textAnchor="middle"
              fill="#8899a6"
              fontSize="10"
            >
              Health Score
            </text>
          </svg>
        </div>

        <div className="flex-1 space-y-3">
          <div
            className={clsx(
              'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold'
            )}
            style={{
              backgroundColor: `${risk.color}20`,
              color: risk.color,
              border: `1px solid ${risk.color}40`,
            }}
          >
            <ShieldAlert className="w-3 h-3" />
            {risk.label} Risk
          </div>

          <div className="flex items-center gap-2 text-sm">
            <Cigarette className="w-4 h-4 text-warning-400" />
            <span className="text-navy-400">
              <span className="text-white font-semibold">{equivalentCigarettes}</span>{' '}
              cigarettes/hour
            </span>
          </div>

          <div className="flex items-start gap-1.5">
            <AlertTriangle className="w-3 h-3 text-warning-400 mt-0.5 flex-shrink-0" />
            <p className="text-xs text-navy-400 leading-relaxed">{advisory}</p>
          </div>
        </div>
      </div>
    </div>
  );
}
