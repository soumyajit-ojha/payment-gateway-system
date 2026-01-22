from fastapi import APIRouter
from app.routers.v1 import payments

api_router = APIRouter()
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
