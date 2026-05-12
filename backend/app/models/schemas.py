from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GridCondition(BaseModel):
    timestamp: datetime
    demand_mw: float
    renewable_generation_mw: float
    net_load_mw: float
    frequency_hz: float
    voltage_kv: float
    price_usd_mwh: float
    peak_period: bool
    instability_score: float = Field(ge=0, le=1)


class BatteryStatus(BaseModel):
    timestamp: datetime
    soc_percent: float = Field(ge=0, le=100)
    soh_percent: float = Field(ge=0, le=100)
    power_mw: float
    capacity_mwh: float
    temperature_c: float
    cycle_count: float
    mode: Literal["charging", "discharging", "idle"]
    efficiency_percent: float


class ForecastPoint(BaseModel):
    timestamp: datetime
    predicted_demand_mw: float
    predicted_renewable_mw: float
    confidence_low_mw: float
    confidence_high_mw: float


class OptimizationRequest(BaseModel):
    horizon_hours: int = Field(default=24, ge=1, le=72)
    initial_soc_percent: float = Field(default=62.0, ge=5, le=95)
    objective: Literal["balanced", "peak_shaving", "arbitrage", "stabilization"] = "balanced"


class SchedulePoint(BaseModel):
    timestamp: datetime
    action: Literal["charge", "discharge", "hold"]
    power_mw: float
    expected_soc_percent: float
    reason: str
    estimated_value_usd: float


class OptimizationResponse(BaseModel):
    objective: str
    projected_savings_usd: float
    renewable_utilization_gain_percent: float
    degradation_cost_usd: float
    schedule: list[SchedulePoint]


class BatteryAnalytics(BaseModel):
    soc_percent: float
    soh_percent: float
    remaining_useful_life_cycles: float
    charge_cycle_efficiency_percent: float
    thermal_stress_index: float = Field(ge=0, le=1)
    degradation_rate_percent_per_100_cycles: float


class Alert(BaseModel):
    timestamp: datetime
    severity: Literal["info", "warning", "critical"]
    category: str
    message: str
    value: float
    threshold: float


class TrainResponse(BaseModel):
    model_path: str
    metrics: dict[str, float]
    training_rows: int
    test_rows: int
