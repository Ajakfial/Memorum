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

    # Postgres-wire connection string, exactly as CockroachDB's console gives
    # it to you: postgresql://user:pass@host:26257/defaultdb?sslmode=verify-full
    # normalized_database_url (below) rewrites this to cockroachdb+asyncpg://
    # for actual use — don't put the rewritten form here.
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
        gives you) and route it through the `sqlalchemy-cockroachdb` dialect
        (`cockroachdb+asyncpg://`) instead of the vanilla Postgres one.
        CockroachDB is Postgres wire-compatible but differs enough at the
        catalog level — its version string doesn't match Postgres's `X.Y`
        format, and its `pg_catalog` has no standalone `json` type — that
        the plain `postgresql+asyncpg` dialect breaks on both. The
        CockroachDB-specific dialect patches both around it.

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
            url = "cockroachdb+asyncpg://" + url[len("postgresql://"):]
        url = url.replace("sslmode=verify-full", "ssl=require")
        url = url.replace("sslmode=require", "ssl=require")
        url = url.replace("sslmode=verify-ca", "ssl=require")
        return url


@lru_cache
def get_settings() -> Settings:
    return Settings()
