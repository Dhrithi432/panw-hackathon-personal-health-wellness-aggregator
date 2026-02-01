from pydantic import BaseModel


class CorrelationOut(BaseModel):
    metric_a: str
    metric_b: str
    lag_days: int
    correlation: float
    p_value: float | None = None
    confidence: float


class AnomalyOut(BaseModel):
    metric_name: str
    start_ts: str  # ISO string
    end_ts: str
    severity: str
    score: float
    confidence: float
    summary: str


class CorrelationsResponse(BaseModel):
    items: list[CorrelationOut]


class AnomaliesResponse(BaseModel):
    items: list[AnomalyOut]
