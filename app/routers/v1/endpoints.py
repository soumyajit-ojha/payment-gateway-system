from fastapi import APIRouter
from app.routers.v1 import payments, webhooks, admin

api_router = APIRouter()

api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
