'use client';

import React, { useRef, useEffect, useMemo, useCallback } from 'react';
import { Wind } from 'lucide-react';
import type { SensorData, WeatherData } from '@/types';

interface ParticleSimulationProps {
  sensors: SensorData[];
  weather: WeatherData | null;
}

interface Particle {
  x: number;
  y: number;
  vx: number;
  vy: number;
  age: number;
  maxAge: number;
  concentration: number;
  size: number;
}

function gaussianRandom(): number {
  let u = 0;
  let v = 0;
  while (u === 0) u = Math.random();
  while (v === 0) v = Math.random();
  return Math.sqrt(-2.0 * Math.log(u)) * Math.cos(2.0 * Math.PI * v);
}

function concentrationToColor(c: number, alpha: number): string {
  const clamped = Math.min(1, Math.max(0, c));
  let r: number, g: number, b: number;

  if (clamped < 0.25) {
    const t = clamped / 0.25;
    r = 0;
    g = Math.round(214 + (255 - 214) * t);
    b = Math.round(143 * (1 - t));
  } else if (clamped < 0.5) {
    const t = (clamped - 0.25) / 0.25;
    r = Math.round(245 * t);
    g = Math.round(255 - (255 - 158) * t);
    b = 0;
  } else if (clamped < 0.75) {
    const t = (clamped - 0.5) / 0.25;
    r = Math.round(245 + (239 - 245) * t);
    g = Math.round(158 - 158 * t);
    b = 0;
  } else {
    const t = (clamped - 0.75) / 0.25;
    r = Math.round(239 - (239 - 127) * t);
    g = 0;
    b = Math.round(29 * t);
  }

  return `rgba(${r},${g},${b},${alpha.toFixed(3)})`;
}

export default function ParticleSimulation({
  sensors,
  weather,
}: ParticleSimulationProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const particlesRef = useRef<Particle[]>([]);
  const animFrameRef = useRef<number>(0);

  const windDir = weather?.wind_direction ?? 180;
  const windSpeed = weather?.wind_speed ?? 2;
  const windRad = useMemo(() => ((windDir - 90) * Math.PI) / 180, [windDir]);

  const sources = useMemo(() => {
    if (sensors.length === 0) {
      return [{ x: 0.5, y: 0.5, emission: 0.5 }];
    }
    const lats = sensors.map((s) => s.lat);
    const lngs = sensors.map((s) => s.lng);
    const minLat = Math.min(...lats);
    const maxLat = Math.max(...lats);
    const minLng = Math.min(...lngs);
    const maxLng = Math.max(...lngs);
    const latRange = maxLat - minLat || 0.01;
    const lngRange = maxLng - minLng || 0.01;

    return sensors.map((s) => ({
      x: 0.1 + ((s.lng - minLng) / lngRange) * 0.8,
      y: 0.1 + (1 - (s.lat - minLat) / latRange) * 0.8,
      emission: Math.min(1, s.pollution.pm25 / 100),
    }));
  }, [sensors]);

  const animate = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const w = canvas.width;
    const h = canvas.height;

    ctx.fillStyle = 'rgba(10, 14, 23, 0.15)';
    ctx.fillRect(0, 0, w, h);

    const dt = 1 / 60;
    const baseVx = Math.cos(windRad) * windSpeed * 8;
    const baseVy = Math.sin(windRad) * windSpeed * 8;
    const spread = 2.0 + windSpeed * 0.5;

    sources.forEach((source) => {
      const spawnCount = Math.max(1, Math.round(source.emission * 3));
      for (let i = 0; i < spawnCount; i++) {
        particlesRef.current.push({
          x: source.x * w + gaussianRandom() * 3,
          y: source.y * h + gaussianRandom() * 3,
          vx: baseVx + gaussianRandom() * spread,
          vy: baseVy + gaussianRandom() * spread,
          age: 0,
          maxAge: 120 + Math.random() * 80,
          concentration: source.emission * (0.7 + Math.random() * 0.3),
          size: 1 + source.emission * 2 + Math.random(),
        });
      }
    });

    const alive: Particle[] = [];
    for (const p of particlesRef.current) {
      p.x += p.vx * dt + gaussianRandom() * spread * dt;
      p.y += p.vy * dt + gaussianRandom() * spread * dt;
      p.age += 1;

      const lifeRatio = p.age / p.maxAge;
      const fadedConcentration = p.concentration * (1 - lifeRatio);
      const alpha = Math.max(0, (1 - lifeRatio) * 0.7);

      if (p.age < p.maxAge && p.x > -20 && p.x < w + 20 && p.y > -20 && p.y < h + 20) {
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.size * (1 - lifeRatio * 0.5), 0, Math.PI * 2);
        ctx.fillStyle = concentrationToColor(fadedConcentration, alpha);
        ctx.fill();
        alive.push(p);
      }
    }
    particlesRef.current = alive;

    if (particlesRef.current.length > 2000) {
      particlesRef.current = particlesRef.current.slice(-1500);
    }

    const arrowCx = w - 35;
    const arrowCy = 35;
    const arrowLen = 15;

    ctx.save();
    ctx.beginPath();
    ctx.arc(arrowCx, arrowCy, 22, 0, Math.PI * 2);
    ctx.fillStyle = 'rgba(30, 37, 56, 0.8)';
    ctx.fill();
    ctx.strokeStyle = '#2d3548';
    ctx.lineWidth = 1;
    ctx.stroke();

    ctx.fillStyle = '#8899a6';
    ctx.font = '8px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.fillText('N', arrowCx, arrowCy - 16);

    ctx.translate(arrowCx, arrowCy);
    ctx.rotate(windRad + Math.PI / 2);

    ctx.beginPath();
    ctx.moveTo(0, -arrowLen);
    ctx.lineTo(-4, arrowLen * 0.4);
    ctx.lineTo(0, arrowLen * 0.2);
    ctx.lineTo(4, arrowLen * 0.4);
    ctx.closePath();
    ctx.fillStyle = '#00d68f';
    ctx.fill();

    ctx.restore();

    animFrameRef.current = requestAnimationFrame(animate);
  }, [windRad, windSpeed, sources]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const resizeCanvas = () => {
      const rect = canvas.parentElement?.getBoundingClientRect();
      if (rect) {
        canvas.width = rect.width;
        canvas.height = rect.height;
      }
    };

    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    animFrameRef.current = requestAnimationFrame(animate);

    return () => {
      window.removeEventListener('resize', resizeCanvas);
      cancelAnimationFrame(animFrameRef.current);
      particlesRef.current = [];
    };
  }, [animate]);

  return (
    <div className="bg-[#1e2538] rounded-card border border-[#2d3548] p-4 h-full">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <Wind className="w-4 h-4 text-eco-500" />
          <h3 className="text-sm font-semibold text-white">Dispersion Simulation</h3>
        </div>
        <span className="text-xs text-navy-400">
          {windSpeed.toFixed(1)} m/s @ {Math.round(windDir)}deg
        </span>
      </div>
      <div className="relative h-48 bg-[#0a0e17] rounded-lg overflow-hidden">
        <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
      </div>
    </div>
  );
}
