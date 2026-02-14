import type {
  SensorData,
  ForecastPoint,
  GreenRoute,
  GridData,
  GlobalStats,
  HealthImpactData,
} from '@/types';

// Use relative paths through Next.js proxy rewrites by default.
// When NEXT_PUBLIC_API_URL is set (e.g. http://localhost:40881),
// requests go directly to the backend.
const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

async function fetchJSON<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    headers: { 'Accept': 'application/json' },
  });
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSensors(): Promise<SensorData[]> {
  return fetchJSON<SensorData[]>('/api/sensors');
}

export async function fetchForecast(sensorId?: string): Promise<ForecastPoint[]> {
  const id = sensorId || 'cam-001';
  return fetchJSON<ForecastPoint[]>(`/api/forecast/${id}`);
}

export async function fetchGreenRoute(
  startLat: number,
  startLng: number,
  endLat: number,
  endLng: number
): Promise<GreenRoute> {
  return fetchJSON<GreenRoute>(
    `/api/routing/green-path?from_lat=${startLat}&from_lng=${startLng}&to_lat=${endLat}&to_lng=${endLng}`
  );
}

export async function fetchGrid(): Promise<GridData> {
  return fetchJSON<GridData>('/api/grid');
}

export async function fetchStats(): Promise<GlobalStats> {
  return fetchJSON<GlobalStats>('/api/stats');
}

export async function fetchSensorHistory(
  sensorId: string,
  hours?: number
): Promise<{ timestamp: string; pm25: number; aqi: number }[]> {
  const query = hours ? `?hours=${hours}` : '';
  return fetchJSON(`/api/sensors/${sensorId}/history${query}`);
}

export async function fetchHealthImpact(sensorId?: string): Promise<HealthImpactData> {
  const query = sensorId ? `?sensor_id=${sensorId}` : '';
  return fetchJSON<HealthImpactData>(`/api/health-impact${query}`);
}
