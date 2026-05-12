import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.simulators.grid_simulator import GridSimulator

if __name__ == "__main__":
    frame = GridSimulator(seed=42).generate_and_save(Path("data/synthetic_grid_telemetry.csv"), days=45)
    print(f"Generated {len(frame)} telemetry rows at data/synthetic_grid_telemetry.csv")
