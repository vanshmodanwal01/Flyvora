"""
IndexValue: stores computed "Flyvora Airfare Price Index - Prototype"
values over time, so the frontend can plot real history instead of the
backend recomputing the whole series on every request. Explicitly NOT an
official CPI series - see app/services/index_service.py for the disclosed
methodology.
"""
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class IndexValue(Base):
    __tablename__ = "index_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(20), index=True)   # "national" | a route code | an airline code
    period: Mapped[date] = mapped_column(Date, index=True)       # the period this value represents (e.g. week start)
    base_period: Mapped[date] = mapped_column(Date)
    index_value: Mapped[float] = mapped_column(Numeric(8, 2))
    sample_size: Mapped[int] = mapped_column(Integer)       # observation count backing this period - the data-quality signal
    methodology_version: Mapped[str] = mapped_column(String(20), default="v1-route-weighted")
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    def __repr__(self) -> str:
        return f"<IndexValue {self.scope} {self.period} = {self.index_value}>"
