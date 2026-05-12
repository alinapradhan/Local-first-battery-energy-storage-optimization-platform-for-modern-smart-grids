from __future__ import annotations

import pandas as pd

from backend.app.ml.forecasting import ForecastingService
from backend.app.models.schemas import BatteryStatus, ForecastPoint, GridCondition
from backend.app.simulators.grid_simulator import ensure_dataset


class GridDataService:
    def __init__(self) -> None:
        self.frame = ensure_dataset()
        self.forecaster = ForecastingService()

    def refresh(self) -> pd.DataFrame:
        self.frame = ensure_dataset()
        return self.frame

    def live_grid(self) -> GridCondition:
        row = self.frame.iloc[-1]
        instability_score = min(1.0, abs(float(row.frequency_hz) - 60) / 0.22 + abs(float(row.voltage_kv) - 13.8) / 1.4)
        return GridCondition(timestamp=pd.Timestamp(row.timestamp).to_pydatetime(), demand_mw=float(row.demand_mw), renewable_generation_mw=float(row.renewable_generation_mw), net_load_mw=float(row.net_load_mw), frequency_hz=float(row.frequency_hz), voltage_kv=float(row.voltage_kv), price_usd_mwh=float(row.price_usd_mwh), peak_period=bool(row.peak_period), instability_score=instability_score)

    def battery_status(self) -> BatteryStatus:
        row = self.frame.iloc[-1]
        power = float(row.battery_power_mw)
        mode = "charging" if power < -1 else "discharging" if power > 1 else "idle"
        return BatteryStatus(timestamp=pd.Timestamp(row.timestamp).to_pydatetime(), soc_percent=float(row.soc_percent), soh_percent=float(row.soh_percent), power_mw=power, capacity_mwh=420.0, temperature_c=float(row.battery_temperature_c), cycle_count=float(row.cycle_count), mode=mode, efficiency_percent=max(84.0, 94.0 - abs(power) / 35))

    def forecasts(self, steps: int = 24) -> list[ForecastPoint]:
        forecast = self.forecaster.forecast(self.frame, steps=steps)
        spread = max(12.0, float(self.frame["demand_mw"].tail(96).std()) * 0.45)
        return [ForecastPoint(timestamp=pd.Timestamp(row.timestamp).to_pydatetime(), predicted_demand_mw=float(row.predicted_demand_mw), predicted_renewable_mw=float(row.predicted_renewable_mw), confidence_low_mw=float(row.predicted_demand_mw - spread), confidence_high_mw=float(row.predicted_demand_mw + spread)) for row in forecast.itertuples(index=False)]
