"""Routers de la API v1."""

from fastapi import APIRouter

from app.api.v1.health_logs import router as health_router
from app.api.v1.health_tdee import router as health_tdee_router
from app.api.v1.ingredients import router as ingredients_router
from app.api.v1.market import router as market_router
from app.api.v1.recipes import router as recipes_router
from app.api.v1.users import router as users_router
from app.api.v1.webhooks import router as webhooks_router

router = APIRouter(prefix="/api/v1")

router.include_router(users_router)
router.include_router(health_router)
router.include_router(health_tdee_router)
router.include_router(recipes_router)
router.include_router(ingredients_router)
router.include_router(market_router)
router.include_router(webhooks_router)
