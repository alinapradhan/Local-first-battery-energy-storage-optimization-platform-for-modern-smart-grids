# API Examples

Start the backend locally:

```bash
uvicorn backend.app.main:app --reload
```

Fetch live grid status:

```bash
curl http://localhost:8000/grid/live
```

Run a 24-hour balanced battery optimization:

```bash
curl -X POST http://localhost:8000/battery/optimize \
  -H 'Content-Type: application/json' \
  -d '{"horizon_hours":24,"initial_soc_percent":62,"objective":"balanced"}'
```

Train the local LSTM forecaster:

```bash
curl -X POST http://localhost:8000/model/train
```
