import { describe, it, expect } from 'vitest';
import {
  getAqiColor,
  getAqiLabel,
  getPm25Color,
  getNoiseColor,
  getNoiseCategory,
  MAP_CENTER,
  PRESET_LOCATIONS,
} from '@/lib/constants';

// ---------------------------------------------------------------------------
// getAqiColor
// ---------------------------------------------------------------------------
describe('getAqiColor', () => {
  it('returns green for AQI 0-50 (Good)', () => {
    expect(getAqiColor(0)).toBe('#00d68f');
    expect(getAqiColor(25)).toBe('#00d68f');
    expect(getAqiColor(50)).toBe('#00d68f');
  });

  it('returns amber for AQI 51-100 (Moderate)', () => {
    expect(getAqiColor(51)).toBe('#f59e0b');
    expect(getAqiColor(75)).toBe('#f59e0b');
    expect(getAqiColor(100)).toBe('#f59e0b');
  });

  it('returns orange for AQI 101-150 (Unhealthy for Sensitive Groups)', () => {
    expect(getAqiColor(101)).toBe('#ff8c00');
    expect(getAqiColor(150)).toBe('#ff8c00');
  });

  it('returns red for AQI 151-200 (Unhealthy)', () => {
    expect(getAqiColor(151)).toBe('#ef4444');
    expect(getAqiColor(200)).toBe('#ef4444');
  });

  it('returns purple for AQI 201-300 (Very Unhealthy)', () => {
    expect(getAqiColor(201)).toBe('#8b5cf6');
    expect(getAqiColor(300)).toBe('#8b5cf6');
  });

  it('returns dark red for AQI > 300 (Hazardous)', () => {
    expect(getAqiColor(301)).toBe('#7f1d1d');
    expect(getAqiColor(500)).toBe('#7f1d1d');
  });
});

// ---------------------------------------------------------------------------
// getAqiLabel
// ---------------------------------------------------------------------------
describe('getAqiLabel', () => {
  it('returns "Good" for AQI 0-50', () => {
    expect(getAqiLabel(0)).toBe('Good');
    expect(getAqiLabel(50)).toBe('Good');
  });

  it('returns "Moderate" for AQI 51-100', () => {
    expect(getAqiLabel(51)).toBe('Moderate');
    expect(getAqiLabel(100)).toBe('Moderate');
  });

  it('returns "Unhealthy (Sensitive)" for AQI 101-150', () => {
    expect(getAqiLabel(101)).toBe('Unhealthy (Sensitive)');
    expect(getAqiLabel(150)).toBe('Unhealthy (Sensitive)');
  });

  it('returns "Unhealthy" for AQI 151-200', () => {
    expect(getAqiLabel(151)).toBe('Unhealthy');
    expect(getAqiLabel(200)).toBe('Unhealthy');
  });

  it('returns "Very Unhealthy" for AQI 201-300', () => {
    expect(getAqiLabel(201)).toBe('Very Unhealthy');
    expect(getAqiLabel(300)).toBe('Very Unhealthy');
  });

  it('returns "Hazardous" for AQI > 300', () => {
    expect(getAqiLabel(301)).toBe('Hazardous');
    expect(getAqiLabel(500)).toBe('Hazardous');
  });
});

// ---------------------------------------------------------------------------
// getPm25Color
// ---------------------------------------------------------------------------
describe('getPm25Color', () => {
  it('returns green for PM2.5 <= 12 (Good)', () => {
    expect(getPm25Color(0)).toBe('#00d68f');
    expect(getPm25Color(12)).toBe('#00d68f');
  });

  it('returns amber for PM2.5 12.1-35.4 (Moderate)', () => {
    expect(getPm25Color(13)).toBe('#f59e0b');
    expect(getPm25Color(35.4)).toBe('#f59e0b');
  });

  it('returns orange for PM2.5 35.5-55.4 (Unhealthy for Sensitive)', () => {
    expect(getPm25Color(36)).toBe('#ff8c00');
    expect(getPm25Color(55.4)).toBe('#ff8c00');
  });

  it('returns red for PM2.5 55.5-150.4 (Unhealthy)', () => {
    expect(getPm25Color(56)).toBe('#ef4444');
    expect(getPm25Color(150.4)).toBe('#ef4444');
  });

  it('returns purple for PM2.5 150.5-250.4 (Very Unhealthy)', () => {
    expect(getPm25Color(151)).toBe('#8b5cf6');
    expect(getPm25Color(250.4)).toBe('#8b5cf6');
  });

  it('returns dark red for PM2.5 > 250.4 (Hazardous)', () => {
    expect(getPm25Color(251)).toBe('#7f1d1d');
    expect(getPm25Color(500)).toBe('#7f1d1d');
  });
});

// ---------------------------------------------------------------------------
// getNoiseColor
// ---------------------------------------------------------------------------
describe('getNoiseColor', () => {
  it('returns green for noise < 55 dB (Quiet)', () => {
    expect(getNoiseColor(0)).toBe('#00d68f');
    expect(getNoiseColor(54)).toBe('#00d68f');
  });

  it('returns amber for noise 55-69 dB (Moderate)', () => {
    expect(getNoiseColor(55)).toBe('#f59e0b');
    expect(getNoiseColor(69)).toBe('#f59e0b');
  });

  it('returns orange for noise 70-84 dB (Loud)', () => {
    expect(getNoiseColor(70)).toBe('#ff8c00');
    expect(getNoiseColor(84)).toBe('#ff8c00');
  });

  it('returns red for noise >= 85 dB (Very Loud)', () => {
    expect(getNoiseColor(85)).toBe('#ef4444');
    expect(getNoiseColor(120)).toBe('#ef4444');
  });
});

// ---------------------------------------------------------------------------
// getNoiseCategory
// ---------------------------------------------------------------------------
describe('getNoiseCategory', () => {
  it('returns "Quiet" for noise < 55 dB', () => {
    expect(getNoiseCategory(0)).toBe('Quiet');
    expect(getNoiseCategory(54)).toBe('Quiet');
  });

  it('returns "Moderate" for noise 55-69 dB', () => {
    expect(getNoiseCategory(55)).toBe('Moderate');
    expect(getNoiseCategory(69)).toBe('Moderate');
  });

  it('returns "Loud" for noise 70-84 dB', () => {
    expect(getNoiseCategory(70)).toBe('Loud');
    expect(getNoiseCategory(84)).toBe('Loud');
  });

  it('returns "Very Loud" for noise >= 85 dB', () => {
    expect(getNoiseCategory(85)).toBe('Very Loud');
    expect(getNoiseCategory(120)).toBe('Very Loud');
  });
});

// ---------------------------------------------------------------------------
// MAP_CENTER
// ---------------------------------------------------------------------------
describe('MAP_CENTER', () => {
  it('is set to Delhi coordinates [28.6139, 77.2090]', () => {
    expect(MAP_CENTER).toEqual([28.6139, 77.2090]);
  });

  it('is a tuple with exactly two elements', () => {
    expect(MAP_CENTER).toHaveLength(2);
  });
});

// ---------------------------------------------------------------------------
// PRESET_LOCATIONS
// ---------------------------------------------------------------------------
describe('PRESET_LOCATIONS', () => {
  it('contains exactly 6 Delhi locations', () => {
    expect(PRESET_LOCATIONS).toHaveLength(6);
  });

  it('each location has name, lat, and lng properties', () => {
    for (const loc of PRESET_LOCATIONS) {
      expect(loc).toHaveProperty('name');
      expect(loc).toHaveProperty('lat');
      expect(loc).toHaveProperty('lng');
      expect(typeof loc.name).toBe('string');
      expect(typeof loc.lat).toBe('number');
      expect(typeof loc.lng).toBe('number');
    }
  });

  it('includes India Gate as the first location', () => {
    expect(PRESET_LOCATIONS[0].name).toBe('India Gate');
  });

  it('includes all expected location names', () => {
    const names = PRESET_LOCATIONS.map((l) => l.name);
    expect(names).toContain('India Gate');
    expect(names).toContain('Connaught Place');
    expect(names).toContain('ITO Junction');
    expect(names).toContain('Anand Vihar');
    expect(names).toContain('Dwarka Sec-8');
    expect(names).toContain('Chandni Chowk');
  });
});
