from pydantic import BaseModel


class IndexTrendResponse(BaseModel):
    labels: list[str]
    national: list[float]
    south: list[float]           # kept for Phase 1 parity with the mock; Phase 3 can generalize to N regions


class LeadTimeCurve(BaseModel):
    labels: list[str]            # "T-45".."T-1"
    prices: list[float]


class LeadTimeCompareResponse(BaseModel):
    labels: list[str]
    series: dict[str, list[float]]   # route code -> price series


class CheckpointRow(BaseModel):
    checkpoint: str               # "T-45"
    price: float
    pctChange: float


class AnomalyAlert(BaseModel):
    route: str
    detail: str
    severity: str                 # "High" | "Medium" | "Low"
