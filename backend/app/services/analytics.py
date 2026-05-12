from __future__ import annotations

import pandas as pd

from backend.app.models.schemas import Alert, BatteryAnalytics


class BatteryAnalyticsService:
    def summarize(self, frame: pd.DataFrame) -> BatteryAnalytics:
        latest = frame.sort_values("timestamp").iloc[-1]
        power = abs(float(latest["battery_power_mw"]))
        temp = float(latest["battery_temperature_c"])
        thermal_stress = min(1.0, max(0.0, (temp - 32) / 28 + power / 600))
        soh = float(latest["soh_percent"])
        return BatteryAnalytics(
            soc_percent=float(latest["soc_percent"]),
            soh_percent=soh,
            remaining_useful_life_cycles=max(0.0, (soh - 70) / 0.018),
            charge_cycle_efficiency_percent=max(82.0, 94.0 - thermal_stress * 8.5),
            thermal_stress_index=thermal_stress,
            degradation_rate_percent_per_100_cycles=max(0.8, (100 - soh) * 0.18),
        )


class AnomalyDetectionService:
    def detect(self, frame: pd.DataFrame) -> list[Alert]:
        alerts: list[Alert] = []
        for row in frame.tail(96).itertuples(index=False):
            ts = pd.Timestamp(row.timestamp).to_pydatetime()
            if row.battery_temperature_c > 42:
                alerts.append(Alert(timestamp=ts, severity="critical", category="battery_temperature", message="Battery thermal stress exceeds safe operating band", value=float(row.battery_temperature_c), threshold=42.0))
            if row.soc_percent > 92:
                alerts.append(Alert(timestamp=ts, severity="warning", category="overcharge_risk", message="SOC approaching upper operating reserve", value=float(row.soc_percent), threshold=92.0))
            if row.demand_mw > frame["demand_mw"].quantile(0.96):
                alerts.append(Alert(timestamp=ts, severity="warning", category="grid_overload", message="Demand is in the top stress percentile", value=float(row.demand_mw), threshold=float(frame["demand_mw"].quantile(0.96))))
            if abs(row.frequency_hz - 60.0) > 0.12:
                alerts.append(Alert(timestamp=ts, severity="critical", category="frequency_instability", message="Grid frequency excursion requires fast BESS response", value=float(row.frequency_hz), threshold=0.12))
            if abs(row.voltage_kv - 13.8) > 0.55:
                alerts.append(Alert(timestamp=ts, severity="critical", category="voltage_instability", message="Voltage fluctuation exceeds feeder tolerance", value=float(row.voltage_kv), threshold=0.55))
        return alerts[-20:]
