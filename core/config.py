from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str

    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30
    REFRESH_TOKEN_COOKIE_SECURE: bool = True
    BOOKING_PAYMENT_TIMEOUT_MINUTES: int = 10
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    OTP_IP_RATE_LIMIT: int = 3
    OTP_IP_RATE_WINDOW_SECONDS: int = 60
    OTP_PHONE_RATE_LIMIT: int = 3
    OTP_PHONE_RATE_WINDOW_SECONDS: int = 60
    OTP_VERIFY_RATE_LIMIT: int = 5
    OTP_VERIFY_RATE_WINDOW_SECONDS: int = 60
    REFRESH_RATE_LIMIT: int = 10
    REFRESH_RATE_WINDOW_SECONDS: int = 60
    BOOKING_RATE_LIMIT: int = 10
    BOOKING_RATE_WINDOW_SECONDS: int = 60
    PAYMENT_RATE_LIMIT: int = 5
    PAYMENT_RATE_WINDOW_SECONDS: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
