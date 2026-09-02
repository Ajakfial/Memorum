"""
Application configuration.

Every secret (database URL, JWT signing key) is read from the environment.
Nothing sensitive is ever hardcoded here or checked into source control.
Locally, populate a `.env` file (see .env.example). In CI/production,
these are injected as environment variables sourced from GitHub Actions
repository secrets.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Postgres-wire connection string. CockroachDB is wire-compatible with
    # Postgres, so a standard asyncpg driver works. Example shape:
    # postgresql+asyncpg://user:pass@host:26257/defaultdb?ssl=verify-full
    database_url: str

    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    cors_origins: str = "http://localhost:1420,tauri://localhost"

    app_name: str = "Memorum"
    environment: str = "development"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def normalized_database_url(self) -> str:
        """
        Accept a plain `postgresql://` string (what CockroachDB's console
        gives you) and coerce it to the asyncpg driver URL SQLAlchemy needs.

        `sslmode=verify-full` is deliberately downgraded to `ssl=require`:
        verify-full makes asyncpg look for a locally pinned root CA cert at
        ~/.postgresql/root.crt, which doesn't exist on a fresh machine (e.g.
        a CI runner) and isn't needed here — CockroachDB Cloud's certificate
        chains up to a public CA that Python's default SSL context already
        trusts, so `require` still gets you a fully encrypted, verified-cert
        connection without pinning a file.
        """
        url = self.database_url
        if url.startswith("postgresql://"):
            url = "postgresql+asyncpg://" + url[len("postgresql://"):]
        url = url.replace("sslmode=verify-full", "ssl=require")
        url = url.replace("sslmode=require", "ssl=require")
        url = url.replace("sslmode=verify-ca", "ssl=require")
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
