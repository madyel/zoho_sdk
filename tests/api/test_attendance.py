"""
tests/api/test_attendance.py — Unit tests for AttendanceAPI.
Run with: pytest tests/
"""
from __future__ import annotations

import pytest
from unittest.mock import patch


@pytest.fixture
def mock_client():
    from zoho_people import ZohoPeopleAuth, ZohoPeopleClient

    auth = ZohoPeopleAuth(
        client_id="test_id",
        client_secret="test_secret",
        refresh_token="test_refresh",
        data_centre="US",
    )
    auth.access_token = "test_token"
    auth._token_expiry = float("inf")
    return ZohoPeopleClient(auth=auth)


class TestCheckin:
    def test_checkin_requires_employee_identifier(self, mock_client):
        with pytest.raises(ValueError, match="emp_id"):
            mock_client.attendance.checkin(checkin="25/04/2026 09:00:00")

    def test_checkin_with_email(self, mock_client):
        with patch.object(mock_client, "post", return_value={}) as mock_post:
            mock_client.attendance.checkin(
                checkin="25/04/2026 09:00:00",
                checkout="25/04/2026 18:00:00",
                email_id="mario@company.com",
            )
            mock_post.assert_called_once()
            data = mock_post.call_args.kwargs.get("data", {})
            assert data["emailId"] == "mario@company.com"
            assert data["checkIn"] == "25/04/2026 09:00:00"
            assert data["checkOut"] == "25/04/2026 18:00:00"

    def test_checkin_without_checkout(self, mock_client):
        with patch.object(mock_client, "post", return_value={}) as mock_post:
            mock_client.attendance.checkin(
                checkin="25/04/2026 09:00:00",
                emp_id="IMP085",
            )
            data = mock_post.call_args.kwargs.get("data", {})
            assert "checkOut" not in data

    def test_checkout_requires_identifier(self, mock_client):
        with pytest.raises(ValueError):
            mock_client.attendance.checkout(checkout="25/04/2026 18:00:00")


class TestBulkImport:
    def test_bulk_import_sends_json(self, mock_client):
        with patch.object(mock_client, "post", return_value={}) as mock_post:
            mock_client.attendance.bulk_import([
                {"checkIn": "2026-04-01 09:00:00"},
                {"checkOut": "2026-04-01 18:00:00"},
            ])
            data = mock_post.call_args.kwargs.get("data", {})
            assert "data" in data
            assert "dateFormat" in data


class TestGetUserReport:
    def test_get_user_report_returns_list(self, mock_client):
        with patch.object(mock_client, "get", return_value=[{"date": "2026-04-01"}]):
            result = mock_client.attendance.get_user_report(
                start_date="01/04/2026",
                end_date="30/04/2026",
            )
        assert isinstance(result, list)

    def test_get_user_report_empty_on_no_data(self, mock_client):
        with patch.object(mock_client, "get", return_value={}):
            result = mock_client.attendance.get_user_report(
                start_date="01/04/2026",
                end_date="30/04/2026",
            )
        assert result == []
