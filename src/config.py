"""Pydantic-settings configuration; validated and loaded from .env or
INCONNU_CONFIG_FILE at startup."""

import os

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

CONFIG_FILE = os.getenv("INCONNU_CONFIG_FILE", ".env")


class Settings(BaseSettings):
    """Inconnu configuration settings. Loaded from INCONNU_CONFIG_FILE or from
    .env if that variable is not set.

    Should not be instantiated directly. Use the config.settings singleton
    instead."""

    model_config = SettingsConfigDict(env_file=CONFIG_FILE, extra="ignore")

    inconnu_token: str
    inconnu_api_token: str = ""
    admin_server: int
    supporter_guild: int
    supporter_role: int
    profile_site: str = "http://localhost:5173/"
    app_site: str = "http://localhost:5173"
    guild_cache_loc: str = "file::memory:?cache=shared"
    show_test_routes: bool = False
    debug: str | None = None

    # Database
    mongo_url: str

    # Channels
    report_channel: int | None = None
    db_error_channel: int | None = None

    # External APIs
    fc_api: str = "http://127.0.0.1:8080/"
    github_token: str = ""

    @field_validator("profile_site")
    @classmethod
    def ensure_trailing_slash(cls, v: str) -> str:
        return v if v.endswith("/") else v + "/"

    @field_validator("fc_api")
    @classmethod
    def validate_fc_api_url(cls, v: str) -> str:
        AnyHttpUrl(v)
        return v

    @property
    def debug_guilds(self) -> list[int] | None:
        if self.debug is None:
            return None
        return [int(g) for g in self.debug.split(",")]

    @property
    def prod(self) -> bool:
        return self.debug_guilds is None


settings = Settings()  # type: ignore[call-arg]
