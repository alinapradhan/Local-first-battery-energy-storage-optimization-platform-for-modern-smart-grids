import sqlite3
from pathlib import Path
from typing import Iterable

import pandas as pd

DB_PATH = Path("backend/local_energy_storage.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS telemetry (
    timestamp TEXT PRIMARY KEY,
    demand_mw REAL,
    renewable_generation_mw REAL,
    battery_power_mw REAL,
    soc_percent REAL,
    soh_percent REAL,
    frequency_hz REAL,
    voltage_kv REAL,
    price_usd_mwh REAL,
    battery_temperature_c REAL,
    peak_period INTEGER,
    instability_event INTEGER
);
"""


def connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(SCHEMA)
    return conn


def persist_telemetry(rows: Iterable[dict]) -> None:
    frame = pd.DataFrame(rows)
    if frame.empty:
        return
    with connect() as conn:
        frame.to_sql("telemetry", conn, if_exists="replace", index=False)


def latest_rows(limit: int = 288) -> pd.DataFrame:
    with connect() as conn:
        return pd.read_sql_query(
            "SELECT * FROM telemetry ORDER BY timestamp DESC LIMIT ?", conn, params=(limit,)
        ).sort_values("timestamp")
