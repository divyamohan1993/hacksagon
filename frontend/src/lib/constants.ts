export const MAP_CENTER: [number, number] = [40.758, -73.9855];
export const MAP_ZOOM = 12;

export const DARK_TILE_URL =
  'https://basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png';

export const DARK_TILE_ATTRIBUTION =
  '&copy; <a href="https://carto.com/">CARTO</a> &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>';

export const AQI_COLORS: Record<string, string> = {
  good: '#00d68f',
  moderate: '#f59e0b',
  unhealthy_sensitive: '#ff8c00',
  unhealthy: '#ef4444',
  very_unhealthy: '#8b5cf6',
  hazardous: '#7f1d1d',
};

export function getAqiColor(aqi: number): string {
  if (aqi <= 50) return AQI_COLORS.good;
  if (aqi <= 100) return AQI_COLORS.moderate;
  if (aqi <= 150) return AQI_COLORS.unhealthy_sensitive;
  if (aqi <= 200) return AQI_COLORS.unhealthy;
  if (aqi <= 300) return AQI_COLORS.very_unhealthy;
  return AQI_COLORS.hazardous;
}

export function getAqiLabel(aqi: number): string {
  if (aqi <= 50) return 'Good';
  if (aqi <= 100) return 'Moderate';
  if (aqi <= 150) return 'Unhealthy (Sensitive)';
  if (aqi <= 200) return 'Unhealthy';
  if (aqi <= 300) return 'Very Unhealthy';
  return 'Hazardous';
}

export function getPm25Color(pm25: number): string {
  if (pm25 <= 12) return '#00d68f';
  if (pm25 <= 35.4) return '#f59e0b';
  if (pm25 <= 55.4) return '#ff8c00';
  if (pm25 <= 150.4) return '#ef4444';
  if (pm25 <= 250.4) return '#8b5cf6';
  return '#7f1d1d';
}

export function getNoiseColor(db: number): string {
  if (db < 55) return '#00d68f';
  if (db < 70) return '#f59e0b';
  if (db < 85) return '#ff8c00';
  return '#ef4444';
}

export function getNoiseCategory(db: number): string {
  if (db < 55) return 'Quiet';
  if (db < 70) return 'Moderate';
  if (db < 85) return 'Loud';
  return 'Very Loud';
}

export const PRESET_LOCATIONS: { name: string; lat: number; lng: number }[] = [
  { name: 'Times Square', lat: 40.758, lng: -73.9855 },
  { name: 'Brooklyn Bridge', lat: 40.7061, lng: -73.9969 },
  { name: 'Central Park', lat: 40.7829, lng: -73.9654 },
  { name: 'Wall Street', lat: 40.7074, lng: -74.0113 },
  { name: 'Harlem', lat: 40.8116, lng: -73.9465 },
  { name: 'Queens', lat: 40.7282, lng: -73.7949 },
];

export const PM25_THRESHOLDS = [
  { value: 12, label: 'Good', color: '#00d68f' },
  { value: 35.4, label: 'Moderate', color: '#f59e0b' },
  { value: 55.4, label: 'USG', color: '#ff8c00' },
  { value: 150.4, label: 'Unhealthy', color: '#ef4444' },
];

export const SENSOR_COLORS = [
  '#00d68f',
  '#3b82f6',
  '#f59e0b',
  '#ef4444',
  '#8b5cf6',
  '#ec4899',
  '#14b8a6',
  '#f97316',
];

export const AQI_THRESHOLDS = [
  { min: 0, max: 50, label: 'Good', color: '#00d68f' },
  { min: 51, max: 100, label: 'Moderate', color: '#f59e0b' },
  { min: 101, max: 150, label: 'Unhealthy (Sensitive)', color: '#ff8c00' },
  { min: 151, max: 200, label: 'Unhealthy', color: '#ef4444' },
  { min: 201, max: 300, label: 'Very Unhealthy', color: '#8b5cf6' },
  { min: 301, max: 500, label: 'Hazardous', color: '#7f1d1d' },
];

export const CHART_COLORS = {
  pm25: '#00d68f',
  pm10: '#3b82f6',
  no2: '#f59e0b',
  co: '#8b5cf6',
  aqi: '#ef4444',
  forecast: '#3b82f6',
  confidence: 'rgba(59, 130, 246, 0.15)',
  grid: '#2d3548',
  axis: '#8899a6',
};

export const NOISE_COLORS: Record<string, string> = {
  quiet: '#00d68f',
  moderate: '#f59e0b',
  loud: '#ff8c00',
  dangerous: '#ef4444',
};
