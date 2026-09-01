from pydantic import BaseModel


class OverviewSummary(BaseModel):
    airfareIndex: float
    inflationRate: float
    anomaliesDetected: int
    trackedRoutes: int
