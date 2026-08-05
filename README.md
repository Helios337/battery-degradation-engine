# Battery Degradation Prediction Engine

An LSTM-based model that predicts the remaining useful life (RUL) of EV batteries from charge cycle data, served via FastAPI with a web dashboard.

## Architecture

```
+-----------------+       +-----------------+       +------------------+
|   Dashboard     | ----> |     FastAPI     | ----> |  LSTM Model      |
|   (Next.js)     | <----- |   (Inference)   | <----- |  (PyTorch)       |
|   Port 3000     |       |   Port 8000     |       |  Port (in-memory)|
+-----------------+       +-----------------+       +------------------+
        |                         |
        v                         v
  Upload CSV / Paste Data    POST /predict
  View Degradation Curve     GET /health
```

## Quick Start

```bash
# 1. Generate synthetic battery data
cd data && python generate_synthetic.py

# 2. Train the LSTM model
cd ../model && python train.py

# 3. Start both services
cd ..
docker compose up
```

## API Example

```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{
    "cycle_data": [
      {"cycle_number": 1, "depth_of_discharge": 0.75, "avg_temperature": 25.0, "charge_rate_c": 1.5, "internal_resistance": 1.52, "capacity_ah": 99.8, "voltage_sag": 0.12, "ambient_temp": 22.0}
    ]
  }'
```

## Project Structure

```
battery-degradation-engine/
├── data/
│   ├── generate_synthetic.py
│   └── dataset.csv
├── model/
│   ├── train.py
│   ├── model.py
│   └── battery_lstm.pt
├── api/
│   ├── main.py
│   ├── schemas.py
│   ├── requirements.txt
│   └── Dockerfile
├── dashboard/
│   ├── package.json
│   ├── next.config.js
│   ├── Dockerfile
│   ├── pages/
│   │   └── index.tsx
│   └── components/
│       └── BatteryChart.tsx
├── docker-compose.yml
└── README.md
```

## Acceptance Criteria

1. `python data/generate_synthetic.py` produces dataset.csv with 500 batteries
2. `python model/train.py` achieves MAPE < 5% and R2 > 0.9
3. `docker compose up` starts both services
4. POST /predict with valid input returns correct RUL
5. Dashboard shows degradation curve + RUL prediction on data paste