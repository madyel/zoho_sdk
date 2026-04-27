"""
OAuth 2.0 authentication for Zoho People.

Supports:
  - Static access token (short-lived, ~1h)
  - Auto-refresh via client_id + client_secret + refresh_token (recommended)
  - Construction from environment variables via ``ZohoPeopleAuth.from_env()``

Example::

    auth = ZohoPeopleAuth(
        client_id="1000.xxx",
        client_secret="yyy",
        refresh_token="1000.zzz",
        data_centre="EU",
    )
    # or
    auth = ZohoPeopleAuth.from_env()
"""
from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from typing import Optional

import requests

from .exceptions import ZohoPeopleAuthError

DEFAULT_SCOPES: list[str] = [
    "ZOHOPEOPLE.forms.ALL",
    "ZOHOPEOPLE.attendance.ALL",
    "ZOHOPEOPLE.timetracker.ALL",
    "ZOHOPEOPLE.leave.ALL",
]

ACCOUNTS_URLS: dict[str, str] = {
    "US": "https://accounts.zoho.com",
    "EU": "https://accounts.zoho.eu",
    "IN": "https://accounts.zoho.in",
    "AU": "https://accounts.zoho.com.au",
    "JP": "https://accounts.zoho.jp",
}

PEOPLE_BASE_URLS: dict[str, str] = {
    "US": "https://people.zoho.com",
    "EU": "https://people.zoho.eu",
    "IN": "https://people.zoho.in",
    "AU": "https://people.zoho.com.au",
    "JP": "https://people.zoho.jp",
}

_EXPIRY_MARGIN: int = 60  # seconds before actual expiry to trigger refresh


@dataclass
class ZohoPeopleAuth:
    """
    Manages OAuth 2.0 tokens for Zoho People API.

    Parameters
    ----------
    client_id : str, optional
        OAuth client ID (``1000.xxx``).
    client_secret : str, optional
        OAuth client secret.
    refresh_token : str, optional
        Long-lived refresh token.
    access_token : str, optional
        Short-lived access token. Automatically refreshed when expired.
    data_centre : str
        Zoho data centre: ``US`` | ``EU`` | ``IN`` | ``AU`` | ``JP``.
        Defaults to ``US``.
    """

    client_id:     Optional[str] = None
    client_secret: Optional[str] = None
    refresh_token: Optional[str] = None
    access_token:  Optional[str] = None
    data_centre:   str           = "US"

    _token_expiry: float = field(default=0.0, init=False, repr=False)

    @property
    def accounts_url(self) -> str:
        """OAuth accounts base URL for the configured data centre."""
        return ACCOUNTS_URLS.get(self.data_centre.upper(), ACCOUNTS_URLS["US"])

    @property
    def base_url(self) -> str:
        """Zoho People API base URL for the configured data centre."""
        return PEOPLE_BASE_URLS.get(self.data_centre.upper(), PEOPLE_BASE_URLS["US"])

    @property
    def can_refresh(self) -> bool:
        """``True`` when refresh credentials are present."""
        return bool(self.client_id and self.client_secret and self.refresh_token)

    def get_access_token(self) -> str:
        """
        Return a valid access token, refreshing it automatically when needed.

        Raises
        ------
        ZohoPeopleAuthError
            If no token is available and refresh credentials are missing.
        """
        if self._is_valid() and self.access_token:
            return self.access_token
        if self.can_refresh:
            self._refresh()
        if not self.access_token:
            raise ZohoPeopleAuthError(
                "No access token available. Provide access_token or "
                "client_id / client_secret / refresh_token."
            )
        return self.access_token

    def auth_header(self) -> dict[str, str]:
        """Return the ``Authorization`` header dict."""
        return {"Authorization": f"Zoho-oauthtoken {self.get_access_token()}"}

    def invalidate(self) -> None:
        """Force the next :meth:`get_access_token` call to refresh the token."""
        self._token_expiry = 0.0

    @classmethod
    def from_env(cls) -> "ZohoPeopleAuth":
        """
        Build :class:`ZohoPeopleAuth` from environment variables.

        Reads: ``ZOHO_CLIENT_ID``, ``ZOHO_CLIENT_SECRET``,
        ``ZOHO_REFRESH_TOKEN``, ``ZOHO_PEOPLE_ACCESS_TOKEN``,
        ``ZOHO_DATA_CENTRE``.

        Raises
        ------
        ZohoPeopleAuthError
            If neither an access token nor full refresh credentials are set.
        """
        kwargs: dict = {"data_centre": os.getenv("ZOHO_DATA_CENTRE", "US").upper()}
        mapping = {
            "ZOHO_CLIENT_ID":           "client_id",
            "ZOHO_CLIENT_SECRET":       "client_secret",
            "ZOHO_REFRESH_TOKEN":       "refresh_token",
            "ZOHO_PEOPLE_ACCESS_TOKEN": "access_token",
        }
        for env, kw in mapping.items():
            if val := os.getenv(env):
                kwargs[kw] = val

        obj = cls(**kwargs)
        if not obj.access_token and not obj.can_refresh:
            raise ZohoPeopleAuthError(
                "Missing credentials. Set ZOHO_PEOPLE_ACCESS_TOKEN or "
                "ZOHO_CLIENT_ID + ZOHO_CLIENT_SECRET + ZOHO_REFRESH_TOKEN."
            )
        return obj

    def _is_valid(self) -> bool:
        return bool(self.access_token) and time.time() < (self._token_expiry - _EXPIRY_MARGIN)

    def _refresh(self) -> None:
        try:
            resp = requests.post(
                f"{self.accounts_url}/oauth/v2/token",
                params={
                    "grant_type":    "refresh_token",
                    "client_id":     self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                },
                timeout=30,
            )
            data = resp.json()
        except Exception as exc:
            raise ZohoPeopleAuthError(f"Network error during token refresh: {exc}") from exc

        if "access_token" not in data:
            raise ZohoPeopleAuthError(f"Token refresh failed: {data.get('error', data)}")

        self.access_token  = data["access_token"]
        self._token_expiry = time.time() + int(data.get("expires_in", 3600))
