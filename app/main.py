import time
import uuid
from fastapi import FastAPI, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.db.session import get_db
from app.core.config import settings
from app.core.logging import correlation_id, logger, setup_logging

setup_logging()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="Unified Payment Gateway Microservice for Internal Apps",
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # 1. Get correlation ID from header (sent by E-commerce app) or generate new one
    trace_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    token = correlation_id.set(trace_id)

    start_time = time.time()

    logger.info(f"Incoming request: {request.method} {request.url.path}")

    try:
        response = await call_next(request)
        process_time = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed in {process_time:.2f}ms | Status: {response.status_code}"
        )

        # Return the trace ID to the caller for their logs
        response.headers["X-Correlation-ID"] = trace_id
        return response
    finally:
        correlation_id.reset(token)


# Include our API routes
# app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        data = await db.execute(text("SELECT 1"))
        return {"status": "online", "database": "connected"}
    except Exception as e:
        print(e)
        return {"status": "degraded", "database": "disconnected"}
