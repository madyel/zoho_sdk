"""
tests/test_auth.py — Unit tests for ZohoPeopleAuth.
"""
from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from zoho_people import ZohoPeopleAuth
from zoho_people.exceptions import ZohoPeopleAuthError


class TestZohoPeopleAuth:
    def test_base_url_us(self):
        auth = ZohoPeopleAuth("id", "secret", "refresh", data_centre="US")
        assert "zoho.com" in auth.base_url

    def test_base_url_eu(self):
        auth = ZohoPeopleAuth("id", "secret", "refresh", data_centre="EU")
        assert "zoho.eu" in auth.base_url

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("ZOHO_CLIENT_ID",     "env_id")
        monkeypatch.setenv("ZOHO_CLIENT_SECRET",  "env_secret")
        monkeypatch.setenv("ZOHO_REFRESH_TOKEN",  "env_refresh")
        monkeypatch.setenv("ZOHO_DATA_CENTRE",    "EU")
        auth = ZohoPeopleAuth.from_env()
        assert auth.client_id    == "env_id"
        assert auth.data_centre  == "EU"

    def test_from_env_missing_raises(self, monkeypatch):
        monkeypatch.delenv("ZOHO_CLIENT_ID",    raising=False)
        monkeypatch.delenv("ZOHO_CLIENT_SECRET", raising=False)
        monkeypatch.delenv("ZOHO_REFRESH_TOKEN", raising=False)
        with pytest.raises((ZohoPeopleAuthError, ValueError, KeyError)):
            ZohoPeopleAuth.from_env()

    def test_token_refresh(self):
        auth = ZohoPeopleAuth("id", "secret", "refresh", data_centre="US")
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"access_token": "new_token", "expires_in": 3600}
        mock_resp.status_code = 200
        with patch("requests.post", return_value=mock_resp):
            token = auth.get_access_token()
        assert token == "new_token"
