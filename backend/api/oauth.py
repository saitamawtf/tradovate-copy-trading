"""Tradovate OAuth 2.0 flow.

Register your app at https://partner.tradovate.com to obtain
TRADOVATE_OAUTH_CLIENT_ID and TRADOVATE_OAUTH_CLIENT_SECRET, then set
TRADOVATE_OAUTH_REDIRECT_URI to wherever this callback runs.
"""
import base64
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import get_settings
from ..models import BrokerAccount
from ..security import encrypt
from .deps import SessionDep, UserDep

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/oauth", tags=["oauth"])

# In-memory state store (nonce → {env, label, env})
# In production use Redis/DB; fine for single-user v1
_states: dict[str, dict] = {}


def _cfg_ready() -> bool:
    s = get_settings()
    return bool(s.tradovate_oauth_client_id and s.tradovate_oauth_client_secret)


@router.get("/tradovate/start")
async def oauth_start(
    env: str = Query("live", pattern="^(live|demo)$"),
    label: str = Query(..., min_length=1, max_length=80),
):
    """Redirect browser to Tradovate authorisation page."""
    if not _cfg_ready():
        raise HTTPException(
            400,
            "Tradovate OAuth not configured. Set TRADOVATE_OAUTH_CLIENT_ID and "
            "TRADOVATE_OAUTH_CLIENT_SECRET in .env",
        )
    s = get_settings()
    state = secrets.token_urlsafe(24)
    _states[state] = {"env": env, "label": label}

    params = urlencode(
        {
            "response_type": "code",
            "client_id": s.tradovate_oauth_client_id,
            "redirect_uri": s.tradovate_oauth_redirect_uri,
            "state": state,
        }
    )
    auth_url = s.tradovate_oauth_auth_url
    return RedirectResponse(f"{auth_url}?{params}", status_code=302)


@router.get("/tradovate/callback", response_class=HTMLResponse)
async def oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    error_description: str | None = None,
    session: AsyncSession = SessionDep,
    user_id: int = UserDep,
):
    """Receive auth code, exchange for token, save account."""
    if error:
        return _html_result(
            ok=False,
            message=f"Tradovate denied access: {error_description or error}",
        )

    if not code or not state or state not in _states:
        return _html_result(ok=False, message="Invalid callback — missing code or state.")

    meta = _states.pop(state)
    env: str = meta["env"]
    label: str = meta["label"]
    s = get_settings()

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(
            s.tradovate_oauth_token_url,
            data={
                "grant_type": "authorization_code",
                "client_id": s.tradovate_oauth_client_id,
                "client_secret": s.tradovate_oauth_client_secret,
                "redirect_uri": s.tradovate_oauth_redirect_uri,
                "code": code,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

    if resp.status_code != 200:
        log.error("Tradovate token exchange failed %s: %s", resp.status_code, resp.text)
        return _html_result(
            ok=False,
            message=f"Token exchange failed ({resp.status_code}). Check credentials.",
        )

    data = resp.json()
    access_token = data.get("access_token") or data.get("accessToken")
    refresh_token = data.get("refresh_token") or data.get("refreshToken")
    expires_in = int(data.get("expires_in", 5400))

    if not access_token:
        return _html_result(ok=False, message=f"No access_token in response: {data}")

    expires_at = (
        datetime.now(timezone.utc) + timedelta(seconds=expires_in)
    ).isoformat()

    credentials = {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "expires_at": expires_at,
        # mark as oauth so factory knows which path to use
        "_auth_type": "oauth",
    }

    acc = BrokerAccount(
        user_id=user_id,
        broker="tradovate",
        label=label,
        env=env,
        credentials_encrypted=encrypt(credentials),
        status="ok",
        last_seen_at=datetime.utcnow(),
    )
    session.add(acc)
    await session.commit()
    await session.refresh(acc)
    log.info("Tradovate OAuth account created: id=%s label=%s env=%s", acc.id, label, env)

    return _html_result(
        ok=True,
        message=f'Account "{label}" connected. You can close this tab.',
    )


@router.get("/tradovate/status")
async def oauth_status():
    """Check if OAuth is configured (for the frontend toggle)."""
    s = get_settings()
    return {
        "configured": _cfg_ready(),
        "client_id_set": bool(s.tradovate_oauth_client_id),
    }


def _html_result(*, ok: bool, message: str) -> HTMLResponse:
    color = "#2dd4bf" if ok else "#ef4444"
    icon = "✓" if ok else "✗"
    return HTMLResponse(
        f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Tradovate OAuth</title>
  <style>
    body {{
      font-family: 'JetBrains Mono', monospace;
      background: #0a0d10; color: #e6ecef;
      display: flex; align-items: center; justify-content: center;
      height: 100vh; margin: 0;
    }}
    .box {{
      text-align: center; padding: 40px;
      border: 1px solid {color}; border-radius: 4px;
      background: #0e1216;
      box-shadow: 0 0 32px rgba(0,0,0,0.5);
    }}
    .icon {{ font-size: 48px; color: {color}; margin-bottom: 16px; }}
    .msg {{ font-size: 14px; color: #8b97a3; margin-top: 12px; }}
    .close {{
      margin-top: 24px; padding: 10px 20px;
      background: {color}; color: #0a0d10;
      border: none; border-radius: 2px;
      font-family: inherit; font-size: 12px;
      letter-spacing: 0.12em; cursor: pointer;
    }}
  </style>
</head>
<body>
  <div class="box">
    <div class="icon">{icon}</div>
    <div style="font-size:16px; font-weight:700">{message}</div>
    <div class="msg">{'Reload the Accounts page to see your new account.' if ok else ''}</div>
    <button class="close" onclick="window.close()">CLOSE TAB</button>
  </div>
  <script>
    // Auto-close and notify opener after success
    {'if(window.opener){window.opener.postMessage({type:"tradovate_oauth_done"},"*");setTimeout(()=>window.close(),1500);}' if ok else ''}
  </script>
</body>
</html>""",
        status_code=200,
    )
