import redis
from app.core.config import settings

redis_client = redis.from_url(settings.CELERY_BROKER_URL)


def is_duplicate_request(key: str) -> bool:
    # Set a key in Redis that expires in 24 hours
    # Returns True if key already existed
    return not redis_client.set(f"idemp:{key}", "locked", nx=True, ex=86400)
