from pydantic import BaseModel


class AirlineComparisonRow(BaseModel):
    name: str
    avgFare: float
    change30d: float
    marketShare: float


class AirlineRouteMatrix(BaseModel):
    routes: list[str]
    matrix: dict[str, list[float]]   # airline name -> fare per route, same order as `routes`


class AirlineIndexTrend(BaseModel):
    labels: list[str]                # "D1".."D30"
    series: dict[str, list[float]]   # airline name -> index values (base 100)
