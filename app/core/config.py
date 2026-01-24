from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field


class Settings(BaseSettings):
    SECRET_KEY: str

    # DB Configuration
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: str = "5432"
    DB_NAME: str

    @computed_field
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # Redis/Celery
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Provider Keys
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    # RAZORPAY_KEY_ID: str
    # RAZORPAY_KEY_SECRET: str
    # PAYPAL_CLIENT_ID: str
    # PAYPAL_CLIENT_SECRET: str

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
