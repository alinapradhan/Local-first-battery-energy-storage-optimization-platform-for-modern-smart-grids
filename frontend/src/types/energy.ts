export interface GridCondition {
  timestamp: string;
  demand_mw: number;
  renewable_generation_mw: number;
  net_load_mw: number;
  frequency_hz: number;
  voltage_kv: number;
  price_usd_mwh: number;
  peak_period: boolean;
  instability_score: number;
}

export interface BatteryStatus {
  timestamp: string;
  soc_percent: number;
  soh_percent: number;
  power_mw: number;
  capacity_mwh: number;
  temperature_c: number;
  cycle_count: number;
  mode: 'charging' | 'discharging' | 'idle';
  efficiency_percent: number;
}

export interface ForecastPoint {
  timestamp: string;
  predicted_demand_mw: number;
  predicted_renewable_mw: number;
  confidence_low_mw: number;
  confidence_high_mw: number;
}

export interface Alert {
  timestamp: string;
  severity: 'info' | 'warning' | 'critical';
  category: string;
  message: string;
}
