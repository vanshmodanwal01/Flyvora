from fastapi import APIRouter

from app.api.endpoints import airlines, analytics, collection, dashboard, data_quality, forecast, health, index, routes

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(routes.router)
api_router.include_router(airlines.router)
api_router.include_router(analytics.router)
api_router.include_router(data_quality.router)
api_router.include_router(collection.router)
api_router.include_router(index.router)
api_router.include_router(forecast.router)
