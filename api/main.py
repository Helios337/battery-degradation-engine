import json
import os
import sys
import numpy as np
import pandas as pd
import torch
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas import PredictRequest, PredictResponse, HealthResponse, CycleDataPoint

app = FastAPI(title="Battery Degradation Prediction API")

model = None
FEATURE_COLS = [
    "depth_of_discharge",
    "avg_temperature",
    "charge_rate_c",
    "internal_resistance",
    "capacity_ah",
    "voltage_sag",
    "ambient_temp",
    "cycle_number",
]
SEQ_LEN = 50


@app.on_event("startup")
def load_model():
    global model
    model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "model", "battery_lstm.pt")
    from model.model import BatteryLSTM
    model = BatteryLSTM()
    if os.path.exists(model_path):
        model.load_state_dict(torch.load(model_path, map_location="cpu", weights_only=True))
        model.eval()
    else:
        print(f"Warning: Model file not found at {model_path}")


@app.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(status="ok", model_loaded=model is not None)


@app.post("/predict", response_model=PredictResponse)
def predict(request: PredictRequest):
    if model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")

    if len(request.cycle_data) < 10:
        raise HTTPException(status_code=400, detail="need at least 10 cycles")

    data = request.cycle_data[-SEQ_LEN:]
    feature_matrix = np.array(
        [[getattr(dp, col) for col in FEATURE_COLS] for dp in data],
        dtype=np.float32,
    )

    if feature_matrix.shape[0] < SEQ_LEN:
        padding = np.zeros((SEQ_LEN - feature_matrix.shape[0], len(FEATURE_COLS)), dtype=np.float32)
        feature_matrix = np.vstack([padding, feature_matrix])

    tensor = torch.tensor(feature_matrix).unsqueeze(0)

    with torch.no_grad():
        prediction = model(tensor).squeeze().item()

    rul_cycles = max(0, int(round(prediction)))
    last_capacity = request.cycle_data[-1].capacity_ah
    initial_capacity = 100.0
    capacity_fade_pct = round((initial_capacity - last_capacity) / initial_capacity * 100, 2)

    if rul_cycles <= 50:
        confidence = "high"
    elif rul_cycles <= 200:
        confidence = "medium"
    else:
        confidence = "low"

    estimated_total_cycles = request.cycle_data[-1].cycle_number + rul_cycles

    return PredictResponse(
        rul_cycles=rul_cycles,
        capacity_fade_pct=capacity_fade_pct,
        confidence=confidence,
        estimated_total_cycles=estimated_total_cycles,
    )