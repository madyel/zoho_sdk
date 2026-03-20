"""
tests/test_sdk.py – Unit tests for the Zoho Vertical Studio SDK.
Run with: pytest tests/
"""

import json
import pytest

try:
    import responses as resp_mock
    HAS_RESPONSES = True
except ImportError:
    HAS_RESPONSES = False

from zoho_vertical_sdk import ZohoOAuthToken, ZohoVerticalClient
from zoho_vertical_sdk.exceptions import (
    ZohoAPIError,
    ZohoAuthError,
    ZohoNotFoundError,
    ZohoRateLimitError,
    ZohoValidationError,
)
from zoho_vertical_sdk.query import QueryAPI


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class TestZohoOAuthToken:
    def test_static_token(self):
        auth = ZohoOAuthToken(access_token="abc123")
        assert auth.get_access_token() == "abc123"
        assert auth.auth_header() == {"Authorization": "Zoho-oauthtoken abc123"}

    def test_no_token_raises(self):
        auth = ZohoOAuthToken()
        with pytest.raises(ZohoAuthError):
            auth.get_access_token()

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("ZOHO_ACCESS_TOKEN", "env_token")
        auth = ZohoOAuthToken.from_env()
        assert auth.access_token == "env_token"


# ---------------------------------------------------------------------------
# URL builder test
# ---------------------------------------------------------------------------

class TestClientURLBuilder:
    def setup_method(self):
        auth = ZohoOAuthToken(access_token="tok")
        self.client = ZohoVerticalClient(auth=auth, api_domain="https://zohoverticalapis.com")

    def test_build_url(self):
        url = self.client.build_url("Leads")
        assert url == "https://zohoverticalapis.com/crm/v6/Leads"

    def test_build_url_with_leading_slash(self):
        url = self.client.build_url("/settings/modules")
        assert url == "https://zohoverticalapis.com/crm/v6/settings/modules"


# ---------------------------------------------------------------------------
# Query builder tests (no HTTP)
# ---------------------------------------------------------------------------

class TestQueryBuilder:
    def setup_method(self):
        auth = ZohoOAuthToken(access_token="tok")
        self.client = ZohoVerticalClient(auth=auth, api_domain="https://example.com")

    def test_build_simple(self):
        q = (
            self.client.query
            .select("Last_Name", "Email")
            .from_module("Leads")
            .limit(0, 10)
            .build()
        )
        assert "SELECT Last_Name, Email FROM Leads" in q
        assert "LIMIT 0, 10" in q

    def test_build_with_where(self):
        q = (
            self.client.query
            .select("Last_Name")
            .from_module("Leads")
            .where("Last_Name is not null")
            .build()
        )
        assert "WHERE (Last_Name is not null)" in q

    def test_build_with_order(self):
        q = (
            self.client.query
            .select("id")
            .from_module("Contacts")
            .order_by("Created_Time", "DESC")
            .build()
        )
        assert "ORDER BY Created_Time DESC" in q

    def test_build_missing_fields_raises(self):
        with pytest.raises(ValueError, match="No fields"):
            self.client.query.from_module("Leads").build()

    def test_build_missing_module_raises(self):
        with pytest.raises(ValueError, match="No module"):
            self.client.query.select("id").build()

    def test_limit_cap(self):
        q = (
            self.client.query
            .select("id")
            .from_module("Leads")
            .limit(0, 9999)
            .build()
        )
        assert "LIMIT 0, 2000" in q


# ---------------------------------------------------------------------------
# Response handling tests (no HTTP mock needed)
# ---------------------------------------------------------------------------

class TestResponseHandling:
    def setup_method(self):
        auth = ZohoOAuthToken(access_token="tok")
        self.client = ZohoVerticalClient(auth=auth, api_domain="https://example.com")

    def _fake_response(self, status_code, body):
        """Create a minimal fake requests.Response."""
        import requests
        r = requests.Response()
        r.status_code = status_code
        r._content = json.dumps(body).encode()
        r.headers["Content-Type"] = "application/json"
        return r

    def test_200_returns_data(self):
        r = self._fake_response(200, {"modules": [{"api_name": "Leads"}]})
        data = self.client._handle_response(r)
        assert data["modules"][0]["api_name"] == "Leads"

    def test_401_raises_auth_error(self):
        r = self._fake_response(401, {"code": "OAUTH_SCOPE_MISMATCH", "message": "no scope"})
        with pytest.raises(ZohoAuthError) as exc_info:
            self.client._handle_response(r)
        assert exc_info.value.status_code == 401

    def test_404_raises_not_found(self):
        r = self._fake_response(404, {"code": "RECORD_NOT_FOUND", "message": "not found"})
        with pytest.raises(ZohoNotFoundError):
            self.client._handle_response(r)

    def test_429_raises_rate_limit(self):
        r = self._fake_response(429, {"code": "RATE_LIMIT", "message": "limit"})
        with pytest.raises(ZohoRateLimitError):
            self.client._handle_response(r)

    def test_400_raises_validation(self):
        r = self._fake_response(400, {"code": "INVALID_DATA", "message": "bad"})
        with pytest.raises(ZohoValidationError):
            self.client._handle_response(r)

    def test_204_returns_empty_dict(self):
        import requests
        r = requests.Response()
        r.status_code = 204
        r._content = b""
        data = self.client._handle_response(r)
        assert data == {}
