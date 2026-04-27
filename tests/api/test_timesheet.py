"""
tests/api/test_timesheet.py — Unit tests for TimesheetAPI.
Run with: pytest tests/
"""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_client():
    """Return a ZohoPeopleClient with a mocked auth and HTTP layer."""
    from zoho_people import ZohoPeopleAuth, ZohoPeopleClient

    auth = ZohoPeopleAuth(
        client_id="test_id",
        client_secret="test_secret",
        refresh_token="test_refresh",
        data_centre="US",
    )
    auth.access_token = "test_token"
    auth._token_expiry = float("inf")

    client = ZohoPeopleClient(auth=auth)
    return client


class TestTimesheetAddTimelog:
    def test_add_timelog_calls_post(self, mock_client):
        with patch.object(mock_client, "post", return_value={"result": "ok"}) as mock_post:
            mock_client.timesheet.add_timelog(
                user="mario@company.com",
                work_date="2026-04-25",
                hours="08:00",
                job_name="My Project",
            )
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args
            assert "timetracker/addtimelog" in str(call_kwargs)

    def test_add_timelog_requires_user(self, mock_client):
        with pytest.raises(TypeError):
            mock_client.timesheet.add_timelog(
                work_date="2026-04-25",
                hours="08:00",
            )


class TestTimesheetCreate:
    def test_create_returns_dict(self, mock_client):
        expected = {"timesheetId": ["12345"]}
        with patch.object(mock_client, "post", return_value=expected):
            result = mock_client.timesheet.create(
                user="mario@company.com",
                name="April 2026",
                from_date="01-04-2026",
                to_date="30-04-2026",
            )
        assert result == expected

    def test_create_list_response_normalised(self, mock_client):
        """If the API returns a list, create() should return a dict."""
        with patch.object(mock_client, "post", return_value=[{"timesheetId": ["99"]}]):
            result = mock_client.timesheet.create(
                user="mario@company.com",
                name="April 2026",
                from_date="01-04-2026",
                to_date="30-04-2026",
            )
        assert isinstance(result, dict)


class TestTimesheetList:
    def test_list_returns_list(self, mock_client):
        with patch.object(mock_client, "get", return_value={"result": [{"id": "1"}]}):
            result = mock_client.timesheet.list(
                user="mario@company.com",
                from_date="01-Apr-2026",
                to_date="30-Apr-2026",
            )
        assert isinstance(result, list)

    def test_list_empty_on_no_data(self, mock_client):
        with patch.object(mock_client, "get", return_value={}):
            result = mock_client.timesheet.list(
                user="mario@company.com",
                from_date="01-Apr-2026",
                to_date="30-Apr-2026",
            )
        assert result == []
