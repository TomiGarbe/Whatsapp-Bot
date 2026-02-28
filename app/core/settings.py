"""Application settings management."""

from pydantic import Field

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
    database_url: str = Field(..., alias="DATABASE_URL")
    
    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_key: str | None = Field(default=None, alias="AZURE_OPENAI_API_KEY")
    azure_openai_deployment: str | None = Field(default=None, alias="AZURE_OPENAI_DEPLOYMENT")
    azure_openai_api_version: str | None = Field(default=None, alias="AZURE_OPENAI_API_VERSION")

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            env_file_encoding="utf-8",
            case_sensitive=False,
            extra="forbid",
        )
    else:
        class Config:
            env_file = ".env"
            env_file_encoding = "utf-8"
            case_sensitive = False
            extra = "forbid"


settings = Settings()
