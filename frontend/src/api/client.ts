import type { Alert, BatteryStatus, ForecastPoint, GridCondition } from '../types/energy';

const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

async function get<T>(path: string): Promise<T> {
  const response = await fetch(`${API_URL}${path}`);
  if (!response.ok) throw new Error(`API request failed: ${path}`);
  return response.json() as Promise<T>;
}

export const energyApi = {
  grid: () => get<GridCondition>('/grid/live'),
  battery: () => get<BatteryStatus>('/battery/status'),
  forecasts: () => get<ForecastPoint[]>('/battery/forecast?steps=48'),
  alerts: () => get<Alert[]>('/alerts')
};
