from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from backend.app.models.schemas import OptimizationRequest, OptimizationResponse, SchedulePoint


@dataclass(frozen=True)
class OptimizerConfig:
    capacity_mwh: float = 420.0
    max_power_mw: float = 120.0
    min_soc: float = 10.0
    max_soc: float = 92.0
    charge_efficiency: float = 0.93
    discharge_efficiency: float = 0.91


class BatteryOptimizationEngine:
    def __init__(self, config: OptimizerConfig | None = None) -> None:
        self.config = config or OptimizerConfig()

    def optimize(self, forecasts: pd.DataFrame, price_profile: pd.Series, request: OptimizationRequest) -> OptimizationResponse:
        horizon = min(request.horizon_hours * 4, len(forecasts))
        forecast = forecasts.head(horizon).copy()
        prices = price_profile.tail(horizon).reset_index(drop=True)
        if len(prices) < horizon:
            prices = pd.Series([float(price_profile.mean())] * horizon)
        high_demand = forecast["predicted_demand_mw"].quantile(0.72)
        low_price = prices.quantile(0.35)
        high_price = prices.quantile(0.72)
        soc = request.initial_soc_percent
        schedule: list[SchedulePoint] = []
        savings = 0.0
        degradation_cost = 0.0
        renewable_gain = 0.0

        for idx, row in forecast.reset_index(drop=True).iterrows():
            demand = float(row["predicted_demand_mw"])
            renewable = float(row["predicted_renewable_mw"])
            price = float(prices.iloc[idx])
            surplus_renewable = renewable > demand * 0.48
            action = "hold"
            power = 0.0
            reason = "Reserve energy while grid conditions remain nominal."
            if (price <= low_price or surplus_renewable) and soc < self.config.max_soc:
                action = "charge"
                power = min(self.config.max_power_mw, (self.config.max_soc - soc) / 100 * self.config.capacity_mwh * 4)
                soc += power * 0.25 * self.config.charge_efficiency / self.config.capacity_mwh * 100
                reason = "Absorb low-cost or renewable energy to increase grid flexibility."
                renewable_gain += 0.18 if surplus_renewable else 0.04
            elif (demand >= high_demand or price >= high_price or request.objective == "peak_shaving") and soc > self.config.min_soc:
                action = "discharge"
                power = min(self.config.max_power_mw, (soc - self.config.min_soc) / 100 * self.config.capacity_mwh * 4, demand * 0.2)
                soc -= power * 0.25 / (self.config.capacity_mwh * self.config.discharge_efficiency) * 100
                reason = "Discharge to shave peak demand, support frequency, and capture arbitrage value."
                savings += power * 0.25 * price
            degradation_cost += abs(power) * 0.25 * 1.8
            schedule.append(SchedulePoint(timestamp=pd.Timestamp(row["timestamp"]).to_pydatetime(), action=action, power_mw=round(power, 3), expected_soc_percent=round(soc, 3), reason=reason, estimated_value_usd=round(power * 0.25 * price if action == "discharge" else 0, 2)))
        return OptimizationResponse(objective=request.objective, projected_savings_usd=round(savings, 2), renewable_utilization_gain_percent=round(renewable_gain, 2), degradation_cost_usd=round(degradation_cost, 2), schedule=schedule)
