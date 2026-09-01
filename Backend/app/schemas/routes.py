"""
Response shapes for /api/routes/*. These are deliberately shaped to match
what Route Heatmap+Trends/script.js already expects from `mockData[routeKey]`
and the heatmap table, so the frontend swap is a data-source change only.
"""
from pydantic import BaseModel


class RouteListItem(BaseModel):
    code: str          # "DEL-BOM"
    label: str          # human label for a <select> option


class RouteRankingRow(BaseModel):
    route: str
    weight: str          # pre-formatted "30%" to match existing table rendering
    change: float        # signed percent, e.g. 18.0 — frontend applies its own +/- and color


class AirlineBreakdown(BaseModel):
    indigo: str | None = None
    airIndia: str | None = None
    spicejet: str | None = None
    akasa: str | None = None


class RouteSummary(BaseModel):
    name: str
    avgFare: str
    change30D: str
    changeTrend: str      # "up" | "down"
    weight: str
    observations: str
    airlines: AirlineBreakdown
    labels: list[str]
    routePrices: list[float]
    nationalAvgPrices: list[float]
