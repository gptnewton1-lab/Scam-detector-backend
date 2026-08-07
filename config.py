"""
Application settings loaded from environment variables / .env file.

Production-ready configuration: every sensitive or environment-specific
value comes from the environment instead of being hardcoded in the code.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",  # local overrides (git-ignored)
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- API identity ---------------------------------------------------
    app_name: str = "Scam Detector API"

    # --- Security --------------------------------------------------------
    # REQUIRED in production. Must point to a long random string.
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    # bcrypt cost factor. Default 12 is a good balance of security & speed.
    bcrypt_rounds: int = 12

    # --- Database --------------------------------------------------------
    # SQLite by default for local dev. In production point at a real DB,
    # e.g. postgresql+psycopg://user:pass@host:5432/dbname
    database_url: str = "sqlite:///./database.db"

    # --- CORS / hosts ----------------------------------------------------
    # Comma-separated list of browser origins allowed to call this API.
    # Put your deployed Lovable frontend URL here.
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    # Comma-separated hostnames that may hit this server (Host header check).
    allowed_hosts: str = "127.0.0.1,localhost"

    # --- Rate limiting ---------------------------------------------------
    # Protect auth + public endpoints from brute force / abuse.
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60
    public_analyze_rate_limit: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def allowed_host_list(self) -> list[str]:
        return [h.strip() for h in self.allowed_hosts.split(",") if h.strip()]

    def validate(self) -> None:
        """Fail fast at startup if the config is not safe for production."""
        if not self.secret_key:
            raise RuntimeError(
                "SECRET_KEY is not set. Set it in a .env file or as an "
                "environment variable before starting the server."
            )
        if self.secret_key in ("dev-secret-key", "change-me", "secret"):
            raise RuntimeError(
                "SECRET_KEY is set to a known-insecure value. Generate a "
                "strong random value, e.g. `python -c "
                "\"import secrets; print(secrets.token_hex(32))\"`."
            )


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (loaded once per process)."""
    settings = Settings()
    settings.validate()
    return settings
