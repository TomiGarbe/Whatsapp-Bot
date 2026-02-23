"""Application settings management."""

try:
    # Pydantic v2-style settings package.
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    try:
        # Pydantic v2 compatibility namespace for v1 API.
        from pydantic.v1 import BaseSettings  # type: ignore
    except ImportError:
        # Pydantic v1 direct import fallback.
        from pydantic import BaseSettings  # type: ignore

    SettingsConfigDict = None  # type: ignore


class Settings(BaseSettings):
    """Global settings loaded from environment variables."""

    app_name: str = "WhatsApp Bot AI"
    app_version: str = "0.1.0"
    environment: str = "development"

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False


settings = Settings()
