from fastapi import APIRouter

from backend.app.ml.forecasting import ForecastingService
from backend.app.models.schemas import Alert, BatteryAnalytics, BatteryStatus, ForecastPoint, GridCondition, OptimizationRequest, OptimizationResponse, TrainResponse
from backend.app.optimization.engine import BatteryOptimizationEngine
from backend.app.services.analytics import AnomalyDetectionService, BatteryAnalyticsService
from backend.app.services.grid_service import GridDataService
from backend.app.simulators.grid_simulator import GridSimulator

router = APIRouter()
grid_service = GridDataService()
analytics_service = BatteryAnalyticsService()
anomaly_service = AnomalyDetectionService()
optimizer = BatteryOptimizationEngine()
forecaster = ForecastingService()


@router.get("/grid/live", response_model=GridCondition)
def grid_live() -> GridCondition:
    return grid_service.live_grid()


@router.get("/battery/status", response_model=BatteryStatus)
def battery_status() -> BatteryStatus:
    return grid_service.battery_status()


@router.get("/battery/forecast", response_model=list[ForecastPoint])
def battery_forecast(steps: int = 24) -> list[ForecastPoint]:
    return grid_service.forecasts(steps=steps)


@router.post("/battery/optimize", response_model=OptimizationResponse)
def optimize_battery(request: OptimizationRequest) -> OptimizationResponse:
    forecast = forecaster.forecast(grid_service.frame, steps=request.horizon_hours * 4)
    return optimizer.optimize(forecast, grid_service.frame["price_usd_mwh"], request)


@router.get("/battery/analytics", response_model=BatteryAnalytics)
def battery_analytics() -> BatteryAnalytics:
    return analytics_service.summarize(grid_service.frame)


@router.get("/alerts", response_model=list[Alert])
def alerts() -> list[Alert]:
    return anomaly_service.detect(grid_service.frame)


@router.post("/model/train", response_model=TrainResponse)
def train_model() -> TrainResponse:
    result = forecaster.train(grid_service.frame)
    return TrainResponse(**result)


@router.post("/simulator/regenerate")
def regenerate(days: int = 45) -> dict[str, int | str]:
    frame = GridSimulator().generate_and_save(days=days)
    grid_service.frame = frame
    return {"rows": len(frame), "dataset": "data/synthetic_grid_telemetry.csv"}
