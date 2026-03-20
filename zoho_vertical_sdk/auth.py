"""
Authentication helpers for Zoho Vertical Studio SDK.

Supports:
- Static OAuth token (access token string)
- Auto-refresh via client credentials / refresh token
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from .exceptions import ZohoAuthError


@dataclass
class ZohoOAuthToken:
    """
    Holds OAuth credentials and manages access-token refresh.

    Usage – static token (no auto-refresh):
        auth = ZohoOAuthToken(access_token="100xx.xxxxxxx")

    Usage – auto-refresh with a refresh token:
        auth = ZohoOAuthToken(
            client_id="...",
            client_secret="...",
            refresh_token="...",
        )
    """

    # Static token
    access_token: Optional[str] = None

    # Refresh-flow credentials
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None

    # OAuth endpoints vary by data centre
    accounts_url: str = "https://accounts.zoho.com"

    # Internal state
    _token_expiry: float = field(default=0.0, init=False, repr=False)

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def get_access_token(self) -> str:
        """Return a valid access token, refreshing if necessary."""
        if self.access_token and not self._can_refresh():
            return self.access_token

        if self._needs_refresh():
            self._do_refresh()

        if not self.access_token:
            raise ZohoAuthError(
                "No access token available. Provide access_token or "
                "client_id/client_secret/refresh_token."
            )
        return self.access_token

    def auth_header(self) -> dict:
        """Return the Authorization header dict."""
        return {"Authorization": f"Zoho-oauthtoken {self.get_access_token()}"}

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _can_refresh(self) -> bool:
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def _needs_refresh(self) -> bool:
        if not self._can_refresh():
            return False
        # Refresh 60 seconds before expiry
        return time.time() >= (self._token_expiry - 60)

    def _do_refresh(self) -> None:
        url = f"{self.accounts_url}/oauth/v2/token"
        params = {
            "grant_type": "refresh_token",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self.refresh_token,
        }
        resp = requests.post(url, params=params, timeout=30)
        data = resp.json()

        if "access_token" not in data:
            raise ZohoAuthError(
                f"Token refresh failed: {data.get('error', data)}"
            )

        self.access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        self._token_expiry = time.time() + expires_in

    @classmethod
    def from_env(cls) -> "ZohoOAuthToken":
        """
        Build from environment variables:
            ZOHO_ACCESS_TOKEN   – static token
            ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN – refresh flow
            ZOHO_ACCOUNTS_URL   – optional, defaults to https://accounts.zoho.com
        """
        import os

        kwargs: dict = {}
        if os.getenv("ZOHO_ACCOUNTS_URL"):
            kwargs["accounts_url"] = os.environ["ZOHO_ACCOUNTS_URL"]

        if os.getenv("ZOHO_ACCESS_TOKEN"):
            kwargs["access_token"] = os.environ["ZOHO_ACCESS_TOKEN"]

        for key in ("ZOHO_CLIENT_ID", "ZOHO_CLIENT_SECRET", "ZOHO_REFRESH_TOKEN"):
            if os.getenv(key):
                kwargs[key.lower().replace("zoho_", "")] = os.environ[key]

        return cls(**kwargs)
