export interface VehicleCounts {
  trucks: number;
  cars: number;
  buses: number;
  motorcycles: number;
  total: number;
}

export interface PollutionData {
  pm25: number;
  pm10: number;
  no2: number;
  co: number;
  aqi: number;
  category: string;
}

export interface WeatherData {
  wind_speed: number;
  wind_direction: number;
  temperature: number;
  humidity: number;
}

export interface NoiseData {
  db_level: number;
  category: string;
}

export interface HealthData {
  score: number;
  risk_level: string;
  equivalent_cigarettes: number;
  vulnerable_advisory: string;
}

export interface SensorData {
  id: string;
  name: string;
  lat: number;
  lng: number;
  status: string;
  vehicles: VehicleCounts;
  pollution: PollutionData;
  weather: WeatherData;
  noise: NoiseData;
  health: HealthData;
  timestamp: string;
}

export interface GridData {
  bounds: { north: number; south: number; east: number; west: number };
  resolution: number;
  values: number[][];
}

export interface ForecastPoint {
  timestamp: string;
  predicted_pm25: number;
  confidence_lower: number;
  confidence_upper: number;
}

export interface GreenRoute {
  path: [number, number][];
  total_distance_km: number;
  avg_pollution: number;
  estimated_exposure: number;
  comparison: {
    shortest_path_exposure: number;
    green_path_exposure: number;
    reduction_percent: number;
  };
}

export interface ParticleData {
  x: number;
  y: number;
  vx: number;
  vy: number;
  concentration: number;
  age: number;
  source_id: string;
}

export interface GlobalStats {
  active_sensors: number;
  avg_aqi: number;
  avg_pm25: number;
  avg_noise_db: number;
  total_vehicles_detected: number;
  healthiest_zone: string;
  most_polluted_zone: string;
}

export interface WebSocketMessage {
  type: string;
  timestamp: string;
  sensors: SensorData[];
  grid: GridData | null;
  particles: ParticleData[];
  stats: GlobalStats;
  forecast: ForecastPoint[];
}

export interface HealthImpactData {
  score: number;
  risk_level: string;
  equivalent_cigarettes: number;
  vulnerable_advisory: string;
  pm25_avg: number;
  dominant_pollutant: string;
}
