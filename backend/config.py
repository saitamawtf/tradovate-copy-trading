from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Copy Trading"
    database_url: str = "sqlite+aiosqlite:///./copy_trading.db"
    fernet_key: str = "ZmFrZV9rZXlfcmVwbGFjZV93aXRoX3JlYWxfZmVybmV0X2tleQ=="
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    tradovate_api_base: str = "https://live.tradovateapi.com/v1"
    tradovate_ws_url: str = "wss://live.tradovateapi.com/v1/websocket"
    tradovate_demo_api_base: str = "https://demo.tradovateapi.com/v1"
    tradovate_demo_ws_url: str = "wss://demo.tradovateapi.com/v1/websocket"

    projectx_default_base: str = "https://api.topstepx.com"

    app_id: str = "CopyTradingApp"
    app_version: str = "0.1.0"

    # Tradovate OAuth 2.0 (register at partner.tradovate.com)
    tradovate_oauth_client_id: str = ""
    tradovate_oauth_client_secret: str = ""
    tradovate_oauth_redirect_uri: str = "http://localhost:8000/api/oauth/tradovate/callback"
    # Authorization page (live) — override if using demo/partner env
    tradovate_oauth_auth_url: str = "https://live.tradovateapi.com/auth/authorize"
    tradovate_oauth_token_url: str = "https://live.tradovateapi.com/auth/oauthtoken"

    @property
    def db_path(self) -> Path:
        return Path(self.database_url.split(":///")[-1]).resolve()


@lru_cache
def get_settings() -> Settings:
    return Settings()
