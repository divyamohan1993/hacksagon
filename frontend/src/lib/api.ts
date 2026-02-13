import type {
  SensorData,
  ForecastPoint,
  GreenRoute,
  GridData,
  GlobalStats,
  HealthImpactData,
} from '@/types';

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

async function fetchJSON<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) {
    throw new Error(`API error: ${res.status} ${res.statusText}`);
  }
  return res.json();
}

export async function fetchSensors(): Promise<SensorData[]> {
  return fetchJSON<SensorData[]>('/sensors');
}

export async function fetchForecast(sensorId?: string): Promise<ForecastPoint[]> {
  const query = sensorId ? `?sensor_id=${sensorId}` : '';
  return fetchJSON<ForecastPoint[]>(`/forecast${query}`);
}

export async function fetchGreenRoute(
  startLat: number,
  startLng: number,
  endLat: number,
  endLng: number
): Promise<GreenRoute> {
  return fetchJSON<GreenRoute>(
    `/green-route?start_lat=${startLat}&start_lng=${startLng}&end_lat=${endLat}&end_lng=${endLng}`
  );
}

export async function fetchGrid(): Promise<GridData> {
  return fetchJSON<GridData>('/grid');
}

export async function fetchStats(): Promise<GlobalStats> {
  return fetchJSON<GlobalStats>('/stats');
}

export async function fetchSensorHistory(
  sensorId: string,
  hours?: number
): Promise<{ timestamp: string; pm25: number; aqi: number }[]> {
  const query = hours ? `?hours=${hours}` : '';
  return fetchJSON(`/sensors/${sensorId}/history${query}`);
}

export async function fetchHealthImpact(sensorId?: string): Promise<HealthImpactData> {
  const query = sensorId ? `?sensor_id=${sensorId}` : '';
  return fetchJSON<HealthImpactData>(`/health-impact${query}`);
}
