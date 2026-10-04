"""Application Settings and Configuration Management.

This module defines the type-safe configuration schema using Pydantic Settings
and Pydantic v2. It manages environment variables, `.env` file overrides,
local embedded DuckDB connection strings, and runtime directories.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Self

from pydantic import (
    EmailStr,
    Field,
    HttpUrl,
    Secret,
    model_validator,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_project_root(current_path: Path) -> Path:
    """Locate the project root by searching for known anchor files.

    Starting from ``current_path``, recursively walks up the directory tree
    until a directory containing the project's anchor files is found.

    Parameters
    ----------
    current_path : pathlib.Path
        Starting path from which the parent directories are searched.

    Returns
    -------
    pathlib.Path
        Path to the detected project root directory.
    """
    for parent in [current_path, *list(current_path.parents)]:
        if (
            (parent / "pyproject.toml").exists()
            or (parent / "alembic.ini").exists()
            or (parent / ".git").exists()
        ):
            return parent

    return current_path.resolve().parents[2]


# Get the base directory for the project
BASE_DIR = _find_project_root(Path(__file__).resolve())


class Environment(StrEnum):
    """Enumeration of supported runtime environments."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


class LogLevel(StrEnum):
    """Enumeration of standard logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """Define validated application-wide runtime configuration.

    Configuration values are loaded from environment variables and the
    project-level ``.env`` file, with environment variables taking
    precedence.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application & Logging
    ENVIRONMENT: Environment = Field(default=Environment.DEVELOPMENT)
    LOG_LEVEL: LogLevel = Field(default=LogLevel.INFO)
    LOG_BACKUP_COUNT: int = Field(default=14, ge=1)
    LOG_ROTATION_WHEN: str = Field(default="midnight", pattern=r"^(midnight|[Hh]|[Dd]|[Ww])$")
    LOGGER_NAME: str = Field(default="agent_logger", min_length=1)
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000, ge=1, le=65535)

    # API Endpoints
    API_BASE_URL: str | None = None
    HEALTH_API_URL: str = ""
    TRIGGER_AGENT_API_URL: str = ""

    # Embedded Database
    DATABASE_URL: str = Field(default="duckdb:///./data/agent.duckdb")
    MEMORY_LIMIT: str = Field(default="1GB")

    # Ollama Engine
    OLLAMA_BASE_URL: HttpUrl = Field(default_factory=lambda: HttpUrl("http://localhost:11434"))
    OLLAMA_DECISION_MODEL: str = Field(default="tev1:4b")
    OLLAMA_GENERATIVE_MODEL: str = Field(default="gemma4:e4b")
    MATCH_THRESHOLD_PROBABILITY: float = Field(default=0.65, ge=0.0, le=1.0)

    # Browser Automation & Playwright
    BROWSER_USER_DATA_DIR: Path = Field(default=BASE_DIR / "browser_user_data")
    HEADLESS_BROWSER: bool = Field(default=False)
    BROWSER_TIMEOUT_MS: int = Field(default=30000, ge=1000)

    # Temporal Workflow Orchestration
    TEMPORAL_HOST: str = Field(default="localhost")
    TEMPORAL_NAMESPACE: str = Field(default="default")
    TEMPORAL_TASK_QUEUE: str = Field(default="agent-queue")

    # Sentry Error Tracking
    SENTRY_DSN: HttpUrl | None = Field(default=None)
    SENTRY_TRACES_SAMPLE_RATE: float = Field(default=1.0, ge=0.0, le=1.0)

    # User Credentials for Wellfound Website
    USER_EMAIL: EmailStr | None = Field(default=None)
    USER_PASSWORD: Secret | None = Field(default=None, min_length=1)

    # Workspace Directory Paths
    DATA_DIR: Path = Field(default_factory=lambda: BASE_DIR / "data")
    LOGS_DIR: Path = Field(default_factory=lambda: BASE_DIR / "logs")

    @model_validator(mode="after")
    def assemble_api_urls(self) -> "Settings":
        """Construct API endpoint URLs from the configured host and port."""
        base_url = self.API_BASE_URL or f"http://{self.APP_HOST}:{self.APP_PORT}"
        self.API_BASE_URL = base_url.rstrip("/")
        self.HEALTH_API_URL = f"{self.API_BASE_URL}/health"
        self.TRIGGER_AGENT_API_URL = f"{self.API_BASE_URL}/api/v1/agent/run"

        return self

    @model_validator(mode="after")
    def _validate_environment_credentials(self) -> Self:
        """Validate credentials required outside development and testing."""
        if self.ENVIRONMENT not in {
            Environment.PRODUCTION,
            Environment.STAGING,
        }:
            return self

        missing_secrets: list[str] = []

        if self.SENTRY_DSN is None:
            missing_secrets.append("SENTRY_DSN")

        if self.USER_EMAIL is None:
            missing_secrets.append("USER_EMAIL")

        if self.USER_PASSWORD is None:
            missing_secrets.append("USER_PASSWORD")

        if missing_secrets:
            raise ValueError(
                f"Missing required secrets for "
                f"{self.ENVIRONMENT.value} environment: "
                f"{', '.join(missing_secrets)}"
            )

        return self

    def ensure_directories(self) -> None:
        """Create required application workspace directories."""
        directories = [
            self.LOGS_DIR,
            self.DATA_DIR,
        ]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    """Return the cached application settings.

    Local development may use a project-level environment file, while
    deployment environments such as Render provide configuration directly
    through environment variables.
    """
    settings = Settings()
    settings.ensure_directories()

    return settings
