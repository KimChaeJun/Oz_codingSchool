from typing import Literal

from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DB_USER: str = "root"
    DB_PASSWORD: str = "password1234"
    DB_HOST: str = "localhost"
    
    DB_PORT: str = "3306"

    DB_NAME: str = "ai_health"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379


    JWT_SECRET_KEY: SecretStr = SecretStr(
        "development-only-secret-key-change-in-production"
    )
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    REFRESH_COOKIE_NAME: str = "refresh_token"
    COOKIE_SECURE: bool = False
    COOKIE_SAMESITE: Literal["lax", "strict", "none"] = "lax"

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
