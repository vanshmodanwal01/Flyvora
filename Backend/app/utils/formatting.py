"""
Small formatting helpers so the API returns strings in exactly the shape the
existing frontend already renders (e.g. "₹4,325", "+18%"), instead of raw
numbers the frontend would have to reformat differently than it does today.
"""


def format_inr(amount: float) -> str:
    return f"₹{amount:,.0f}"


def format_signed_percent(pct: float, decimals: int = 0) -> str:
    sign = "+" if pct >= 0 else ""
    return f"{sign}{pct:.{decimals}f}%"


def trend_direction(pct: float) -> str:
    return "up" if pct >= 0 else "down"
