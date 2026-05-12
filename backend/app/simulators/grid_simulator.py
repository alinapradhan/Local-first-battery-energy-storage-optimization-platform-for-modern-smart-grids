from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

from backend.app.storage.database import persist_telemetry


@dataclass(frozen=True)
class BatterySpec:
    capacity_mwh: float = 420.0
    max_power_mw: float = 120.0
    min_soc: float = 8.0
    max_soc: float = 94.0
    initial_soc: float = 58.0
    base_efficiency: float = 0.925


class GridSimulator:
    """Synthetic digital twin for a utility-scale grid-connected BESS site."""

    def __init__(self, seed: int = 42, battery: BatterySpec | None = None) -> None:
        self.rng = np.random.default_rng(seed)
        self.battery = battery or BatterySpec()

    def generate(self, days: int = 45, freq: str = "15min") -> pd.DataFrame:
        periods = int(days * 24 * (60 / pd.Timedelta(freq).seconds * 60)) if freq != "15min" else days * 96
        start = datetime(2026, 1, 1)
        timestamps = pd.date_range(start=start, periods=periods, freq=freq)
        hour = timestamps.hour + timestamps.minute / 60
        day_index = np.arange(periods) / 96

        daily_cycle = 78 * np.sin((hour - 7) / 24 * 2 * np.pi) + 44 * np.sin((hour - 18) / 24 * 2 * np.pi)
        evening_peak = 130 * np.exp(-0.5 * ((hour - 18.5) / 2.2) ** 2)
        morning_peak = 62 * np.exp(-0.5 * ((hour - 8.0) / 1.8) ** 2)
        weekly = 28 * np.sin(day_index / 7 * 2 * np.pi)
        demand = 510 + daily_cycle + evening_peak + morning_peak + weekly + self.rng.normal(0, 16, periods)

        spike_mask = self.rng.random(periods) < 0.018
        demand += spike_mask * self.rng.uniform(55, 170, periods)

        solar_shape = np.maximum(0, np.sin((hour - 6) / 12 * np.pi)) ** 1.7
        cloud_events = np.clip(1 - self.rng.beta(1.4, 8, periods), 0.28, 1.0)
        solar = 210 * solar_shape * cloud_events
        wind = 92 + 36 * np.sin((hour + 3) / 24 * 2 * np.pi) + self.rng.normal(0, 20, periods)
        wind += self.rng.choice([0, 35, -30], size=periods, p=[0.88, 0.06, 0.06])
        renewable = np.clip(solar + wind, 0, None)

        net_load = demand - renewable
        peak_period = (hour >= 17) & (hour <= 21) | (net_load > np.quantile(net_load, 0.88))
        price = 42 + 0.18 * net_load + 36 * peak_period + self.rng.normal(0, 4, periods)
        price = np.clip(price, 12, None)

        soc = np.zeros(periods)
        soh = np.zeros(periods)
        battery_power = np.zeros(periods)
        temp = np.zeros(periods)
        cycle_count = np.zeros(periods)
        soc[0] = self.battery.initial_soc
        soh[0] = 99.2
        cumulative_cycles = 22.0

        for idx in range(1, periods):
            overproduction = renewable[idx] - demand[idx]
            high_price = price[idx] > np.quantile(price[max(0, idx - 96): idx + 1], 0.72)
            if overproduction > 25 and soc[idx - 1] < self.battery.max_soc:
                power = -min(self.battery.max_power_mw, overproduction, (self.battery.max_soc - soc[idx - 1]) / 100 * self.battery.capacity_mwh * 4)
            elif (peak_period[idx] or high_price) and soc[idx - 1] > self.battery.min_soc:
                power = min(self.battery.max_power_mw, net_load[idx] * 0.22, (soc[idx - 1] - self.battery.min_soc) / 100 * self.battery.capacity_mwh * 4)
            else:
                power = 0.0
            battery_power[idx] = power
            delta_mwh = -power * 0.25 if power < 0 else -power * 0.25 / self.battery.base_efficiency
            soc[idx] = np.clip(soc[idx - 1] + delta_mwh / self.battery.capacity_mwh * 100, self.battery.min_soc, self.battery.max_soc)
            throughput = abs(power) * 0.25
            cumulative_cycles += throughput / (2 * self.battery.capacity_mwh)
            cycle_count[idx] = cumulative_cycles
            degradation = 0.0022 * cumulative_cycles + 0.0009 * max(0, soc[idx] - 82) + 0.0007 * abs(power) / self.battery.max_power_mw
            soh[idx] = np.clip(99.2 - degradation, 72, 100)
            temp[idx] = 27 + 0.055 * abs(power) + 5.2 * np.maximum(0, solar_shape[idx] - 0.45) + self.rng.normal(0, 1.1)

        adjusted_net_load = demand - renewable - battery_power
        frequency = 60 - 0.00085 * (adjusted_net_load - np.mean(adjusted_net_load)) + self.rng.normal(0, 0.018, periods)
        voltage = 13.8 - 0.0015 * (adjusted_net_load - np.mean(adjusted_net_load)) + self.rng.normal(0, 0.045, periods)
        instability = spike_mask | (self.rng.random(periods) < 0.012)
        frequency[instability] += self.rng.choice([-0.16, 0.14], instability.sum())
        voltage[instability] += self.rng.choice([-0.75, 0.62], instability.sum())

        frame = pd.DataFrame(
            {
                "timestamp": timestamps,
                "demand_mw": demand.round(3),
                "renewable_generation_mw": renewable.round(3),
                "solar_mw": solar.round(3),
                "wind_mw": wind.round(3),
                "battery_power_mw": battery_power.round(3),
                "soc_percent": soc.round(3),
                "soh_percent": soh.round(3),
                "cycle_count": cycle_count.round(3),
                "frequency_hz": frequency.round(4),
                "voltage_kv": voltage.round(4),
                "price_usd_mwh": price.round(3),
                "battery_temperature_c": temp.round(3),
                "peak_period": peak_period.astype(int),
                "load_spike": spike_mask.astype(int),
                "instability_event": instability.astype(int),
                "net_load_mw": adjusted_net_load.round(3),
            }
        )
        return frame

    def generate_and_save(self, output: Path = Path("data/synthetic_grid_telemetry.csv"), days: int = 45) -> pd.DataFrame:
        output.parent.mkdir(parents=True, exist_ok=True)
        frame = self.generate(days=days)
        frame.to_csv(output, index=False)
        persist_telemetry(frame.to_dict(orient="records"))
        return frame


def ensure_dataset(path: Path = Path("data/synthetic_grid_telemetry.csv")) -> pd.DataFrame:
    if path.exists():
        return pd.read_csv(path, parse_dates=["timestamp"])
    return GridSimulator().generate_and_save(path)
