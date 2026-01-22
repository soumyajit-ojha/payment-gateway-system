from fastapi import FastAPI
from app.core.config import settings

# from app.routers.v1.api import api_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Unified Payment Gateway Microservice for Internal Apps",
)

# Include our API routes
# app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "payment-gateway"}
