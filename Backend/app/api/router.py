from fastapi import APIRouter

from app.api.endpoints import airlines, analytics, dashboard, data_quality, health, routes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(routes.router)
api_router.include_router(airlines.router)
api_router.include_router(analytics.router)
api_router.include_router(data_quality.router)
