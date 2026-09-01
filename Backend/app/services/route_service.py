from sqlalchemy.orm import Session

from app.repositories import route_repo
from app.schemas.routes import AirlineBreakdown, RouteListItem, RouteRankingRow, RouteSummary
from app.utils.formatting import format_inr, format_signed_percent, trend_direction


def list_routes(db: Session) -> list[RouteListItem]:
    routes = route_repo.list_routes(db)
    return [RouteListItem(code=r.display_code, label=r.display_code) for r in routes]


def get_route_ranking(db: Session, days: int = 30) -> list[RouteRankingRow]:
    rows = route_repo.get_route_ranking(db, days=days)
    return [
        RouteRankingRow(route=r["route"], weight=f"{r['weight']:.0f}%", change=r["change"])
        for r in rows
    ]


def get_route_summary(db: Session, code: str, days: int = 30) -> RouteSummary | None:
    route = route_repo.get_route_by_code(db, code)
    if route is None:
        return None
    data = route_repo.get_route_summary(db, route, days=days)
    if data is None:
        return None

    return RouteSummary(
        name=route.display_code,
        avgFare=format_inr(data["avg_fare"]),
        change30D=format_signed_percent(data["pct_change"]),
        changeTrend=trend_direction(data["pct_change"]),
        weight=f"{float(route.index_weight):.0f}%" if route.index_weight is not None else "—",
        observations=f"{data['observations']:,}",
        airlines=AirlineBreakdown(
            indigo=format_inr(data["airline_breakdown"]["6E"]) if "6E" in data["airline_breakdown"] else None,
            airIndia=format_inr(data["airline_breakdown"]["AI"]) if "AI" in data["airline_breakdown"] else None,
            spicejet=format_inr(data["airline_breakdown"]["SG"]) if "SG" in data["airline_breakdown"] else None,
            akasa=format_inr(data["airline_breakdown"]["QP"]) if "QP" in data["airline_breakdown"] else None,
        ),
        labels=data["labels"],
        routePrices=data["route_prices"],
        nationalAvgPrices=data["national_avg_prices"],
    )
