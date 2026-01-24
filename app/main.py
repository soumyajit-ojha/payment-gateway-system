import time
import uuid
import tracemalloc
from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from contextlib import asynccontextmanager

from app.db.session import engine, get_db
from app.core.config import settings
from app.core.logging import correlation_id, logger, setup_logging
from app.routers.v1.endpoints import api_router

# Initialize tracemalloc to find unawaited coroutines (fixes your warning)
tracemalloc.start()

setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # STARTUP LOGIC
    logger.info("Application starting up...")
    try:
        # Check if DB is reachable on startup
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            logger.info("Database connection verified.")
    except Exception as e:
        logger.error(f"Database connection failed during startup: {e}")

    yield  # Application runs here

    # SHUTDOWN LOGIC
    logger.info("Application shutting down...")
    # BUG FIX: engine.dispose() is ASYNC for AsyncEngine.
    # Must be awaited to avoid RuntimeWarnings.
    await engine.dispose()
    logger.info("Database connection pool closed.")


app = FastAPI(
    title="Payment Gateway Service",
    version="1.0.0",
    description="Unified Payment Gateway Microservice for Internal Apps",
    lifespan=lifespan,
)

# ADDED: CORS Middleware
# Required for React-JS or any browser-based frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific domains
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Correlation-ID"],  # Let the frontend see the trace ID
)


@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    # Get correlation ID from header or generate new one
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
        response.headers["X-Correlation-ID"] = trace_id
        return response
    finally:
        correlation_id.reset(token)


# Include our API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Deep health check to verify both API and Database"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "online", "database": "connected", "version": "1.0.0"}
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return {"status": "degraded", "database": "disconnected"}
