from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import settings
from app.core.scheduler import start_scheduler, stop_scheduler

app = FastAPI(
    title=settings.APP_NAME,
    description="Airfare Price Index (APIx) backend for SIH26056 — CSV historical data + live SerpApi collection + analytics.",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_PREFIX)


@app.on_event("startup")
def _on_startup():
    start_scheduler()


@app.on_event("shutdown")
def _on_shutdown():
    stop_scheduler()


@app.get("/")
def root():
    return {"name": settings.APP_NAME, "docs": "/docs"}
