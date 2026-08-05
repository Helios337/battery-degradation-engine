from pydantic import BaseModel
from typing import List, Optional


class CycleDataPoint(BaseModel):
    cycle_number: int
    depth_of_discharge: float
    avg_temperature: float
    charge_rate_c: float
    internal_resistance: float
    capacity_ah: float
    voltage_sag: float
    ambient_temp: float


class PredictRequest(BaseModel):
    cycle_data: List[CycleDataPoint]


class PredictResponse(BaseModel):
    rul_cycles: int
    capacity_fade_pct: float
    confidence: str
    estimated_total_cycles: int


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool