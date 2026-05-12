import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from backend.app.ml.forecasting import ForecastingService
from backend.app.simulators.grid_simulator import ensure_dataset

if __name__ == "__main__":
    frame = ensure_dataset()
    result = ForecastingService().train(frame)
    print(result)
