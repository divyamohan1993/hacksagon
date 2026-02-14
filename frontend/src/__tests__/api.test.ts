import { describe, it, expect, vi, beforeEach } from 'vitest';
import {
  fetchSensors,
  fetchForecast,
  fetchGreenRoute,
  fetchGrid,
  fetchStats,
  fetchSensorHistory,
  fetchHealthImpact,
} from '@/lib/api';

// ---------------------------------------------------------------------------
// Mock global fetch
// ---------------------------------------------------------------------------
const mockFetch = vi.fn();
global.fetch = mockFetch;

function mockOkResponse(data: unknown) {
  return {
    ok: true,
    status: 200,
    statusText: 'OK',
    json: () => Promise.resolve(data),
  };
}

function mockErrorResponse(status: number, statusText: string) {
  return {
    ok: false,
    status,
    statusText,
    json: () => Promise.resolve({}),
  };
}

beforeEach(() => {
  mockFetch.mockReset();
});

// ---------------------------------------------------------------------------
// fetchSensors
// ---------------------------------------------------------------------------
describe('fetchSensors', () => {
  it('calls /api/sensors and returns sensor data', async () => {
    const fakeSensors = [{ id: 'cam-001', name: 'Sensor 1' }];
    mockFetch.mockResolvedValueOnce(mockOkResponse(fakeSensors));

    const result = await fetchSensors();

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url, options] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/sensors');
    expect(options.headers).toEqual({ Accept: 'application/json' });
    expect(result).toEqual(fakeSensors);
  });
});

// ---------------------------------------------------------------------------
// fetchForecast
// ---------------------------------------------------------------------------
describe('fetchForecast', () => {
  it('calls /api/forecast/{sensorId} with provided sensor ID', async () => {
    const fakeData = [{ timestamp: '2025-01-01', predicted_pm25: 42 }];
    mockFetch.mockResolvedValueOnce(mockOkResponse(fakeData));

    const result = await fetchForecast('cam-005');

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/forecast/cam-005');
    expect(result).toEqual(fakeData);
  });

  it('defaults to cam-001 when no sensor ID is provided', async () => {
    mockFetch.mockResolvedValueOnce(mockOkResponse([]));

    await fetchForecast();

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/forecast/cam-001');
  });
});

// ---------------------------------------------------------------------------
// fetchGreenRoute
// ---------------------------------------------------------------------------
describe('fetchGreenRoute', () => {
  it('calls /api/routing/green-path with correct query parameters', async () => {
    const fakeRoute = {
      path: [[28.6, 77.2]],
      total_distance_km: 3.5,
      avg_pollution: 60,
    };
    mockFetch.mockResolvedValueOnce(mockOkResponse(fakeRoute));

    const result = await fetchGreenRoute(28.61, 77.22, 28.63, 77.24);

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe(
      '/api/routing/green-path?from_lat=28.61&from_lng=77.22&to_lat=28.63&to_lng=77.24'
    );
    expect(result).toEqual(fakeRoute);
  });
});

// ---------------------------------------------------------------------------
// fetchGrid
// ---------------------------------------------------------------------------
describe('fetchGrid', () => {
  it('calls /api/grid and returns grid data', async () => {
    const fakeGrid = { bounds: {}, resolution: 0.01, values: [[1, 2]] };
    mockFetch.mockResolvedValueOnce(mockOkResponse(fakeGrid));

    const result = await fetchGrid();

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/grid');
    expect(result).toEqual(fakeGrid);
  });
});

// ---------------------------------------------------------------------------
// fetchStats
// ---------------------------------------------------------------------------
describe('fetchStats', () => {
  it('calls /api/stats and returns global stats', async () => {
    const fakeStats = { active_sensors: 6, avg_aqi: 120 };
    mockFetch.mockResolvedValueOnce(mockOkResponse(fakeStats));

    const result = await fetchStats();

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/stats');
    expect(result).toEqual(fakeStats);
  });
});

// ---------------------------------------------------------------------------
// fetchSensorHistory
// ---------------------------------------------------------------------------
describe('fetchSensorHistory', () => {
  it('calls /api/sensors/{id}/history with sensor ID', async () => {
    const fakeHistory = [{ timestamp: '2025-01-01', pm25: 30, aqi: 80 }];
    mockFetch.mockResolvedValueOnce(mockOkResponse(fakeHistory));

    const result = await fetchSensorHistory('cam-003');

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/sensors/cam-003/history');
    expect(result).toEqual(fakeHistory);
  });

  it('appends hours query parameter when provided', async () => {
    mockFetch.mockResolvedValueOnce(mockOkResponse([]));

    await fetchSensorHistory('cam-003', 24);

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/sensors/cam-003/history?hours=24');
  });

  it('omits hours query parameter when not provided', async () => {
    mockFetch.mockResolvedValueOnce(mockOkResponse([]));

    await fetchSensorHistory('cam-003');

    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain('?hours');
  });
});

// ---------------------------------------------------------------------------
// fetchHealthImpact
// ---------------------------------------------------------------------------
describe('fetchHealthImpact', () => {
  it('calls /api/health-impact and returns health data', async () => {
    const fakeHealth = { score: 65, risk_level: 'moderate' };
    mockFetch.mockResolvedValueOnce(mockOkResponse(fakeHealth));

    const result = await fetchHealthImpact();

    expect(mockFetch).toHaveBeenCalledOnce();
    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/health-impact');
    expect(result).toEqual(fakeHealth);
  });

  it('appends sensor_id query parameter when provided', async () => {
    mockFetch.mockResolvedValueOnce(mockOkResponse({}));

    await fetchHealthImpact('cam-002');

    const [url] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/health-impact?sensor_id=cam-002');
  });

  it('omits sensor_id query parameter when not provided', async () => {
    mockFetch.mockResolvedValueOnce(mockOkResponse({}));

    await fetchHealthImpact();

    const [url] = mockFetch.mock.calls[0];
    expect(url).not.toContain('?sensor_id');
  });
});

// ---------------------------------------------------------------------------
// Error handling
// ---------------------------------------------------------------------------
describe('error handling', () => {
  it('throws an error when the response is not ok', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse(500, 'Internal Server Error'));

    await expect(fetchSensors()).rejects.toThrow('API error: 500 Internal Server Error');
  });

  it('throws on 404 Not Found', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse(404, 'Not Found'));

    await expect(fetchGrid()).rejects.toThrow('API error: 404 Not Found');
  });

  it('throws on 401 Unauthorized', async () => {
    mockFetch.mockResolvedValueOnce(mockErrorResponse(401, 'Unauthorized'));

    await expect(fetchStats()).rejects.toThrow('API error: 401 Unauthorized');
  });
});
