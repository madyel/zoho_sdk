"""
tests/test_zoho_people.py – Unit test per Zoho People SDK.
Esegui con: pytest tests/test_zoho_people.py -v
"""

import json
import pytest
import requests

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from zoho_people import ZohoPeopleClient, ZohoPeopleAuth
from zoho_people.exceptions import (
    ZohoPeopleError,
    ZohoPeopleAuthError,
    ZohoPeopleRateLimitError,
    ZohoPeopleValidationError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_client(token: str = "test_token", dc: str = "US") -> ZohoPeopleClient:
    auth = ZohoPeopleAuth(access_token=token, data_centre=dc)
    return ZohoPeopleClient(auth=auth, max_retries=0)


def fake_response(status_code: int, body) -> requests.Response:
    r = requests.Response()
    r.status_code = status_code
    r._content = json.dumps(body).encode()
    r.headers["Content-Type"] = "application/json"
    return r


# ---------------------------------------------------------------------------
# Auth tests
# ---------------------------------------------------------------------------

class TestZohoPeopleAuth:

    def test_static_token(self):
        auth = ZohoPeopleAuth(access_token="tok123")
        assert auth.get_access_token() == "tok123"
        assert auth.auth_header() == {"Authorization": "Zoho-oauthtoken tok123"}

    def test_no_token_raises(self):
        auth = ZohoPeopleAuth()
        with pytest.raises(ZohoPeopleAuthError):
            auth.get_access_token()

    def test_base_url_us(self):
        auth = ZohoPeopleAuth(access_token="x", data_centre="US")
        assert auth.base_url == "https://people.zoho.com"

    def test_base_url_eu(self):
        auth = ZohoPeopleAuth(access_token="x", data_centre="EU")
        assert auth.base_url == "https://people.zoho.eu"

    def test_accounts_url_eu(self):
        auth = ZohoPeopleAuth(access_token="x", data_centre="EU")
        assert auth.accounts_url == "https://accounts.zoho.eu"

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("ZOHO_PEOPLE_ACCESS_TOKEN", "env_tok")
        monkeypatch.setenv("ZOHO_DATA_CENTRE", "EU")
        auth = ZohoPeopleAuth.from_env()
        assert auth.access_token == "env_tok"
        assert auth.data_centre == "EU"

    def test_can_refresh_false_without_creds(self):
        auth = ZohoPeopleAuth(access_token="tok")
        assert auth._can_refresh() is False

    def test_can_refresh_true_with_creds(self):
        auth = ZohoPeopleAuth(
            client_id="cid",
            client_secret="cs",
            refresh_token="rt",
        )
        assert auth._can_refresh() is True


# ---------------------------------------------------------------------------
# Client URL builder
# ---------------------------------------------------------------------------

class TestZohoPeopleClientURL:

    def setup_method(self):
        self.client = make_client()

    def test_build_url_us(self):
        url = self.client.build_url("attendance")
        assert url == "https://people.zoho.com/people/api/attendance"

    def test_build_url_strips_leading_slash(self):
        url = self.client.build_url("/timetracker/gettimesheet")
        assert url == "https://people.zoho.com/people/api/timetracker/gettimesheet"

    def test_build_url_eu(self):
        client = make_client(dc="EU")
        url = client.build_url("attendance")
        assert url == "https://people.zoho.eu/people/api/attendance"


# ---------------------------------------------------------------------------
# Response handler
# ---------------------------------------------------------------------------

class TestResponseHandler:

    def setup_method(self):
        self.client = make_client()

    def test_200_standard_response_ok(self):
        r = fake_response(200, {"response": {"status": 0, "result": [{"id": "1"}]}})
        data = self.client._handle_response(r)
        assert data["result"][0]["id"] == "1"

    def test_200_application_error_raises(self):
        r = fake_response(200, {
            "response": {
                "status": 1,
                "message": "Errore",
                "errors": [{"code": 9002, "message": "Param mancante"}],
            }
        })
        with pytest.raises(ZohoPeopleValidationError) as exc:
            self.client._handle_response(r)
        assert exc.value.error_code == 9002

    def test_200_list_response(self):
        r = fake_response(200, [{"recordId": "1"}, {"recordId": "2"}])
        data = self.client._handle_response(r)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_401_raises_auth_error(self):
        r = fake_response(401, {"message": "Unauthorized"})
        with pytest.raises(ZohoPeopleAuthError) as exc:
            self.client._handle_response(r)
        assert exc.value.status_code == 401

    def test_429_raises_rate_limit(self):
        r = fake_response(429, {})
        with pytest.raises(ZohoPeopleRateLimitError):
            self.client._handle_response(r)

    def test_400_raises_validation(self):
        r = fake_response(400, {"message": "Bad request"})
        with pytest.raises(ZohoPeopleValidationError):
            self.client._handle_response(r)

    def test_500_raises_generic(self):
        r = fake_response(500, {"message": "Server error"})
        with pytest.raises(ZohoPeopleError):
            self.client._handle_response(r)

    def test_204_returns_empty(self):
        r = requests.Response()
        r.status_code = 204
        r._content = b""
        data = self.client._handle_response(r)
        assert data == {}

    def test_9000_raises_auth_error(self):
        r = fake_response(200, {
            "response": {
                "status": 1,
                "message": "Permission denied",
                "errors": [{"code": 9000, "message": "Permission denied"}],
            }
        })
        with pytest.raises(ZohoPeopleAuthError):
            self.client._handle_response(r)


# ---------------------------------------------------------------------------
# Attendance API logic (no HTTP)
# ---------------------------------------------------------------------------

class TestAttendanceAPI:

    def setup_method(self):
        self.client = make_client()

    def test_checkin_requires_identifier(self):
        with pytest.raises(ValueError, match="obbligatorio"):
            self.client.attendance.checkin(checkin="25/04/2026 09:00:00")

    def test_checkout_requires_identifier(self):
        with pytest.raises(ValueError, match="obbligatorio"):
            self.client.attendance.checkout(checkout="25/04/2026 18:00:00")

    def test_checkin_params_built_correctly(self):
        """Verifica che i parametri vengano costruiti correttamente (senza fare HTTP)."""
        calls = []

        def fake_post(path, params=None, data=None):
            calls.append({"path": path, "params": params})
            return {"response": {"status": 0, "message": "OK"}}

        self.client.post = fake_post
        self.client.attendance.checkin(
            checkin="25/04/2026 09:00:00",
            checkout="25/04/2026 18:00:00",
            emp_id="EMP001",
        )
        assert len(calls) == 1
        assert calls[0]["path"] == "attendance"
        p = calls[0]["params"]
        assert p["checkIn"] == "25/04/2026 09:00:00"
        assert p["checkOut"] == "25/04/2026 18:00:00"
        assert p["empId"] == "EMP001"


# ---------------------------------------------------------------------------
# Timesheet API logic (no HTTP)
# ---------------------------------------------------------------------------

class TestTimesheetAPI:

    def setup_method(self):
        self.client = make_client()

    def test_list_params(self):
        calls = []

        def fake_get(path, params=None):
            calls.append({"path": path, "params": params})
            return {"result": [], "status": 0}

        self.client.get = fake_get
        self.client.timesheet.list(
            user="mario@test.it",
            from_date="01-Apr-2026",
            to_date="30-Apr-2026",
            approval_status="approved",
        )
        assert calls[0]["path"] == "timetracker/gettimesheet"
        p = calls[0]["params"]
        assert p["user"] == "mario@test.it"
        assert p["approvalStatus"] == "approved"
        assert p["fromDate"] == "01-Apr-2026"

    def test_add_timelog_params(self):
        calls = []

        def fake_post(path, params=None, data=None):
            calls.append({"path": path, "params": params})
            return {"result": [{"timeLogId": "123"}], "status": 0}

        self.client.post = fake_post
        result = self.client.timesheet.add_timelog(
            user="mario@test.it",
            work_date="2026-04-25",
            hours="08:00",
            job_name="SDK Dev",
            billing_status="Billable",
        )
        assert calls[0]["path"] == "timetracker/addtimelog"
        assert result["timeLogId"] == "123"

    def test_approve_params(self):
        calls = []

        def fake_post(path, params=None, data=None):
            calls.append({"path": path, "params": params})
            return {"result": {"timesheetId": "456"}, "status": 0}

        self.client.post = fake_post
        self.client.timesheet.approve("456", approval_status="approved", comments="OK")
        p = calls[0]["params"]
        assert p["timesheetId"] == "456"
        assert p["approvalStatus"] == "approved"
        assert p["comments"] == "OK"

    def test_limit_capped_at_200(self):
        calls = []

        def fake_get(path, params=None):
            calls.append(params)
            return {"result": []}

        self.client.get = fake_get
        self.client.timesheet.list(user="all", limit=999)
        assert calls[0]["limit"] == 200


# ---------------------------------------------------------------------------
# Leave API logic (no HTTP)
# ---------------------------------------------------------------------------

class TestLeaveAPI:

    def setup_method(self):
        self.client = make_client()

    def test_apply_builds_json_payload(self):
        calls = []

        def fake_post(path, params=None, data=None):
            calls.append({"path": path, "params": params})
            return {}

        self.client.post = fake_post
        self.client.leave.apply(
            leave_type_id="LT001",
            from_date="04-May-2026",
            to_date="05-May-2026",
            reason="Vacanza",
        )
        assert calls[0]["path"] == "forms/leave/addLeave"
        payload = json.loads(calls[0]["params"]["inputData"])
        assert payload["leaveTypeId"] == "LT001"
        assert payload["reason"] == "Vacanza"

    def test_approve_status(self):
        calls = []

        def fake_post(path, params=None, data=None):
            calls.append(params)
            return {}

        self.client.post = fake_post
        self.client.leave.approve("REC001", status="Rejected", comments="Non autorizzato")
        assert calls[0]["status"] == "Rejected"
        assert calls[0]["comments"] == "Non autorizzato"

    def test_get_balance_multi_emp(self):
        calls = []

        def fake_get(path, params=None):
            calls.append(params)
            return {}

        self.client.get = fake_get
        self.client.leave.get_balance(emp_ids=["EMP001", "EMP002"])
        assert calls[0]["empId"] == "EMP001,EMP002"


# ---------------------------------------------------------------------------
# Employee API logic (no HTTP)
# ---------------------------------------------------------------------------

class TestEmployeeAPI:

    def setup_method(self):
        self.client = make_client()

    def test_list_default_view(self):
        calls = []

        def fake_get(path, params=None):
            calls.append(path)
            return []

        self.client.get = fake_get
        self.client.employee.list()
        assert "P_EmployeeView" in calls[0]

    def test_get_by_email(self):
        calls = []

        def fake_get(path, params=None):
            calls.append(params)
            return [{"recordId": "1", "Email address": "mario@test.it"}]

        self.client.get = fake_get
        emp = self.client.employee.get_by_email("mario@test.it")
        assert emp["recordId"] == "1"
        assert calls[0]["searchColumn"] == "EMPLOYEEMAILALIAS"
        assert calls[0]["searchValue"] == "mario@test.it"

    def test_create_serializes_json(self):
        calls = []

        def fake_post(path, params=None, data=None):
            calls.append(params)
            return {}

        self.client.post = fake_post
        self.client.employee.create({"First Name": "Mario", "Last Name": "Rossi"})
        payload = json.loads(calls[0]["inputData"])
        assert payload["First Name"] == "Mario"
