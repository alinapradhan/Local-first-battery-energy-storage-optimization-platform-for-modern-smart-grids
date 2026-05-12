from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.preprocessing import MinMaxScaler
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

FEATURES = ["demand_mw", "renewable_generation_mw", "price_usd_mwh", "frequency_hz", "voltage_kv"]
TARGET = "demand_mw"
MODEL_PATH = Path("backend/saved_models/lstm_demand_forecaster.pt")


class LSTMDemandForecaster(nn.Module):
    def __init__(self, feature_count: int, hidden_size: int = 48, layers: int = 2) -> None:
        super().__init__()
        self.lstm = nn.LSTM(feature_count, hidden_size, layers, batch_first=True, dropout=0.12)
        self.head = nn.Sequential(nn.Linear(hidden_size, 32), nn.ReLU(), nn.Linear(32, 1))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        output, _ = self.lstm(x)
        return self.head(output[:, -1, :])


@dataclass
class ForecastArtifacts:
    model: LSTMDemandForecaster
    feature_scaler: MinMaxScaler
    target_scaler: MinMaxScaler
    window: int


class ForecastingService:
    def __init__(self, model_path: Path = MODEL_PATH, window: int = 24) -> None:
        self.model_path = model_path
        self.window = window

    def _sequences(self, data: np.ndarray, target: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        xs, ys = [], []
        for idx in range(self.window, len(data)):
            xs.append(data[idx - self.window: idx])
            ys.append(target[idx])
        return np.array(xs, dtype=np.float32), np.array(ys, dtype=np.float32)

    def train(self, frame: pd.DataFrame, epochs: int = 4, batch_size: int = 64) -> dict:
        clean = frame.sort_values("timestamp").dropna(subset=FEATURES).copy()
        feature_scaler = MinMaxScaler()
        target_scaler = MinMaxScaler()
        scaled_features = feature_scaler.fit_transform(clean[FEATURES])
        scaled_target = target_scaler.fit_transform(clean[[TARGET]])
        x, y = self._sequences(scaled_features, scaled_target)
        split = int(len(x) * 0.8)
        x_train, x_test = x[:split], x[split:]
        y_train, y_test = y[:split], y[split:]

        model = LSTMDemandForecaster(feature_count=len(FEATURES))
        optimizer = torch.optim.AdamW(model.parameters(), lr=0.003, weight_decay=0.0004)
        loss_fn = nn.SmoothL1Loss()
        loader = DataLoader(TensorDataset(torch.tensor(x_train), torch.tensor(y_train)), batch_size=batch_size, shuffle=True)
        model.train()
        for _ in range(epochs):
            for batch_x, batch_y in loader:
                optimizer.zero_grad()
                loss = loss_fn(model(batch_x), batch_y)
                loss.backward()
                optimizer.step()

        model.eval()
        with torch.no_grad():
            pred_scaled = model(torch.tensor(x_test)).numpy()
        pred = target_scaler.inverse_transform(pred_scaled).ravel()
        actual = target_scaler.inverse_transform(y_test).ravel()
        mae = float(mean_absolute_error(actual, pred))
        rmse = float(np.sqrt(mean_squared_error(actual, pred)))
        mape = float(np.mean(np.abs((actual - pred) / np.maximum(actual, 1))) * 100)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        torch.save(
            {
                "state_dict": model.state_dict(),
                "feature_min": feature_scaler.data_min_,
                "feature_max": feature_scaler.data_max_,
                "target_min": target_scaler.data_min_,
                "target_max": target_scaler.data_max_,
                "window": self.window,
                "features": FEATURES,
            },
            self.model_path,
        )
        return {"model_path": str(self.model_path), "metrics": {"mae": mae, "rmse": rmse, "mape": mape}, "training_rows": int(split), "test_rows": int(len(x_test))}

    def load(self) -> ForecastArtifacts | None:
        if not self.model_path.exists():
            return None
        payload = torch.load(self.model_path, map_location="cpu", weights_only=False)
        model = LSTMDemandForecaster(feature_count=len(payload["features"]))
        model.load_state_dict(payload["state_dict"])
        model.eval()
        feature_scaler = MinMaxScaler()
        target_scaler = MinMaxScaler()
        feature_scaler.fit(np.vstack([payload["feature_min"], payload["feature_max"]]))
        target_scaler.fit(np.vstack([payload["target_min"], payload["target_max"]]))
        return ForecastArtifacts(model, feature_scaler, target_scaler, int(payload["window"]))

    def forecast(self, frame: pd.DataFrame, steps: int = 24) -> pd.DataFrame:
        artifacts = self.load()
        recent = frame.sort_values("timestamp").tail(max(self.window, 96)).copy()
        if artifacts is None:
            baseline = recent.groupby(recent["timestamp"].dt.hour)[TARGET].mean()
            last_ts = recent["timestamp"].max()
            rows = []
            for step in range(1, steps + 1):
                ts = last_ts + pd.Timedelta(minutes=15 * step)
                value = float(baseline.get(ts.hour, recent[TARGET].mean()))
                rows.append({"timestamp": ts, "predicted_demand_mw": value, "predicted_renewable_mw": float(recent["renewable_generation_mw"].tail(24).mean())})
            return pd.DataFrame(rows)

        values = artifacts.feature_scaler.transform(recent[FEATURES])[-artifacts.window:]
        predictions = []
        last_ts = recent["timestamp"].max()
        renewable_mean = float(recent["renewable_generation_mw"].tail(24).mean())
        with torch.no_grad():
            for step in range(1, steps + 1):
                pred_scaled = artifacts.model(torch.tensor(values[None, :, :], dtype=torch.float32)).numpy()
                pred = float(artifacts.target_scaler.inverse_transform(pred_scaled)[0, 0])
                ts = last_ts + pd.Timedelta(minutes=15 * step)
                predictions.append({"timestamp": ts, "predicted_demand_mw": pred, "predicted_renewable_mw": renewable_mean})
                next_row = values[-1].copy()
                next_row[0] = pred_scaled[0, 0]
                values = np.vstack([values[1:], next_row])
        return pd.DataFrame(predictions)
