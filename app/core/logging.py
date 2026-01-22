import os
import logging
import sys
import uuid
from logging.handlers import RotatingFileHandler
from contextvars import ContextVar

# This variable holds the correlation ID for the current async task
correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")

# Ensure the logs directory exists
LOG_DIR = "logs"
if not os.path.exists(LOG_DIR):
    os.makedirs(LOG_DIR)


class CorrelationFilter(logging.Filter):
    """Filters and injects correlation_id into every log record."""

    def filter(self, record):
        record.correlation_id = correlation_id.get() or "no-trace"
        return True


def setup_logging():
    log_format = (
        "%(asctime)s | %(levelname)s | [%(correlation_id)s] | %(name)s | %(message)s"
    )
    formatter = logging.Formatter(log_format)
    corr_filter = CorrelationFilter()

    # 1. Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.addFilter(corr_filter)

    # 2. File Handler (Rotating: 10MB per file, max 5 files)
    file_handler = RotatingFileHandler(
        os.path.join(LOG_DIR, "payment_gateway.log"),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
    )
    file_handler.setFormatter(formatter)
    file_handler.addFilter(corr_filter)

    # Root Logger Configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid double logging
    root_logger.handlers = []

    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Quiet down some chatty libraries
    logging.getLogger("uvicorn.access").addFilter(corr_filter)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


# Export this logger for use in other files
logger = logging.getLogger("payment_gateway")
