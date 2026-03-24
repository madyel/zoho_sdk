"""
tests/test_people_api.py – Unit tests per le Zoho People API v3
================================================================
Copre:
  - time_to_seconds / seconds_to_time / _to_zoho_date
  - PeopleAttendanceAPI  (add, check_in/check_out, get_monthly, absent_days_from_daylist)
  - PeopleTimesheetAPI   (build_log_params, get, add, add_monthly, get_jobs)
  - PeopleEmployeeAPI    (_normalize_list, find, list, get, get_tree, add_record, update_record)
  - PeopleLeaveAPI       (get_requests, add_request, get_balance, update_status, shortcuts)

Run with:  pytest tests/
"""

from __future__ import annotations

import json
import pytest
import requests

from zoho_vertical_sdk import (
    ZohoOAuthToken,
    ZohoVerticalClient,
    time_to_seconds,
    seconds_to_time,
    PeopleAttendanceAPI,
    PeopleTimesheetAPI,
    PeopleEmployeeAPI,
    PeopleLeaveAPI,
)
from zoho_vertical_sdk.attendance import _to_zoho_date
from zoho_vertical_sdk.exceptions import ZohoAPIError, ZohoValidationError


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures condivise
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    auth = ZohoOAuthToken(access_token="test_token_123")
    return ZohoVerticalClient(
        auth=auth,
        api_domain="https://people.zoho.eu",
        max_retries=0,
    )


def fake_response(status_code: int, body: dict) -> requests.Response:
    """Crea una requests.Response minimale con corpo JSON."""
    r = requests.Response()
    r.status_code = status_code
    r._content = json.dumps(body).encode()
    r.headers["Content-Type"] = "application/json"
    return r


# ─────────────────────────────────────────────────────────────────────────────
# Helpers orario e data
# ─────────────────────────────────────────────────────────────────────────────

class TestTimeHelpers:

    def test_time_to_seconds_hhmm(self):
        assert time_to_seconds("9:00")  == 32400
        assert time_to_seconds("09:00") == 32400
        assert time_to_seconds("17:00") == 61200
        assert time_to_seconds("18:00") == 64800
        assert time_to_seconds("17:30") == 63000

    def test_time_to_seconds_hhmmss(self):
        assert time_to_seconds("09:00:00") == 32400
        assert time_to_seconds("17:00:30") == 61230

    def test_time_to_seconds_midnight(self):
        assert time_to_seconds("0:00") == 0
        assert time_to_seconds("00:00") == 0

    def test_seconds_to_time(self):
        assert seconds_to_time(32400) == "09:00"
        assert seconds_to_time(61200) == "17:00"
        assert seconds_to_time(63000) == "17:30"
        assert seconds_to_time(0)     == "00:00"

    def test_roundtrip(self):
        for t in ("09:00", "17:30", "08:45"):
            assert seconds_to_time(time_to_seconds(t)) == t

    def test_to_zoho_date(self):
        assert _to_zoho_date("15/03/2026") == "15-Mar-2026"
        assert _to_zoho_date("01/01/2026") == "01-Jan-2026"
        assert _to_zoho_date("31/12/2025") == "31-Dec-2025"


# ─────────────────────────────────────────────────────────────────────────────
# PeopleAttendanceAPI – unit puri (no HTTP)
# ─────────────────────────────────────────────────────────────────────────────

class TestAbsentDaysFromDaylist:

    def _daylist(self):
        return {
            "1": {"ldate": "01/03/2025", "status": "Present", "tHrs": "08:00"},
            "2": {"ldate": "02/03/2025", "status": "Absent",  "tHrs": "00:00"},
            "3": {"ldate": "03/03/2025", "status": "",        "tHrs": "00:00"},
            "4": {"ldate": "04/03/2025", "status": "Present", "tHrs": "04:00"},
            "5": {"ldate": "05/03/2025", "status": "Absent",  "tHrs": "04:00"},  # ha ore → non assente
        }

    def test_returns_absent_days(self):
        absent = PeopleAttendanceAPI.absent_days_from_daylist(self._daylist())
        assert "02/03/2025" in absent
        assert "03/03/2025" in absent

    def test_excludes_present_days(self):
        absent = PeopleAttendanceAPI.absent_days_from_daylist(self._daylist())
        assert "01/03/2025" not in absent
        assert "04/03/2025" not in absent

    def test_excludes_absent_with_hours(self):
        # status=Absent ma tHrs != "00:00" → non incluso
        absent = PeopleAttendanceAPI.absent_days_from_daylist(self._daylist())
        assert "05/03/2025" not in absent

    def test_empty_daylist(self):
        assert PeopleAttendanceAPI.absent_days_from_daylist({}) == []


# ─────────────────────────────────────────────────────────────────────────────
# PeopleAttendanceAPI – HTTP (mock)
# ─────────────────────────────────────────────────────────────────────────────

class TestAttendanceHTTP:

    def test_add_uses_rest_endpoint(self, client, monkeypatch):
        """add() senza service_url usa attendance/addEntries."""
        captured = {}

        def mock_form_post(path, data, params=None):
            captured["path"] = path
            captured["data"] = data
            return {"message": "Data added successfully", "status": 0}

        monkeypatch.setattr(client, "form_post", mock_form_post)

        client.attendance.add(
            employee_id="P-000042",
            date_str="15/03/2025",
            check_in="09:00",
            check_out="18:00",
        )

        assert captured["path"] == "attendance/addEntries"
        assert captured["data"]["empId"]    == "P-000042"
        assert captured["data"]["checkIn"]  == "09:00"
        assert captured["data"]["checkOut"] == "18:00"
        assert captured["data"]["date"]     == "15/03/2025"

    def test_check_in_calls_v3_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_form_post(path, data, params=None):
            captured["path"] = path
            captured["data"] = data
            return {"status": 0}

        monkeypatch.setattr(client, "form_post", mock_form_post)
        client.attendance.check_in("P-001", "20/03/2026", "09:00")

        assert captured["path"] == "attendance/checkIn"
        assert captured["data"]["empId"]       == "P-001"
        assert captured["data"]["checkInTime"] == "09:00"
        assert captured["data"]["date"]        == "20/03/2026"

    def test_check_out_calls_v3_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_form_post(path, data, params=None):
            captured["path"] = path
            captured["data"] = data
            return {"status": 0}

        monkeypatch.setattr(client, "form_post", mock_form_post)
        client.attendance.check_out("P-001", "20/03/2026", "18:00")

        assert captured["path"] == "attendance/checkOut"
        assert captured["data"]["checkOutTime"] == "18:00"
        assert captured["data"]["date"]         == "20/03/2026"

    def test_add_bulk_returns_one_result_per_record(self, client, monkeypatch):
        monkeypatch.setattr(
            client, "form_post",
            lambda path, data, params=None: {"message": "ok", "status": 0}
        )

        records = [
            {"date": "03/03/2025", "check_in": "09:00", "check_out": "18:00"},
            {"date": "04/03/2025", "check_in": "09:00", "check_out": "18:00"},
            {"date": "05/03/2025"},  # usa default check_in/out
        ]
        results = client.attendance.add_bulk("P-000042", records)

        assert len(results) == 3
        assert results[0]["date"] == "03/03/2025"
        assert results[2]["date"] == "05/03/2025"

    def test_get_monthly_calls_v3_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {}

        monkeypatch.setattr(client, "get", mock_get)
        client.attendance.get_monthly("P-000042", month=3, year=2025)

        assert captured["path"] == "attendance/getUserReport"
        # Date in formato dd/MM/yyyy
        assert captured["params"]["sdate"] == "01/03/2025"
        assert captured["params"]["edate"] == "31/03/2025"

    def test_get_monthly_february_last_day(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["params"] = params
            return {}

        monkeypatch.setattr(client, "get", mock_get)
        client.attendance.get_monthly("P-001", month=2, year=2025)

        assert captured["params"]["edate"] == "28/02/2025"

    def test_get_monthly_leap_year(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["params"] = params
            return {}

        monkeypatch.setattr(client, "get", mock_get)
        client.attendance.get_monthly("P-001", month=2, year=2024)  # 2024 = bisestile

        assert captured["params"]["edate"] == "29/02/2024"

    def test_get_entries_calls_v3_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {}

        monkeypatch.setattr(client, "get", mock_get)
        client.attendance.get_entries("P-001", "20/03/2026")

        assert captured["path"] == "attendance/getEntries"
        assert captured["params"]["date"]  == "20/03/2026"
        assert captured["params"]["empId"] == "P-001"


# ─────────────────────────────────────────────────────────────────────────────
# PeopleTimesheetAPI – build_log_params (puro, no HTTP)
# ─────────────────────────────────────────────────────────────────────────────

class TestBuildLogParams:

    def test_returns_correct_structure(self):
        result = PeopleTimesheetAPI.build_log_params(
            year=2025, month=3, job_id="JOB001", hours_per_day="8"
        )
        assert "logParams" in result
        assert isinstance(result["logParams"], list)

    def test_march_has_31_entries(self):
        # skip_weekends=False (default) → tutti i 31 giorni
        params = PeopleTimesheetAPI.build_log_params(
            year=2025, month=3, job_id="JOB001"
        )
        assert len(params["logParams"]) == 31

    def test_each_entry_has_required_keys(self):
        params = PeopleTimesheetAPI.build_log_params(
            year=2025, month=3, job_id="JOB001", hours_per_day="8", bill_status="0"
        )
        first = params["logParams"][0]
        assert "day1"        in first
        assert "jobId"       in first
        assert "billStatus"  in first
        assert first["day1"]       == "8"
        assert first["jobId"]      == "JOB001"
        assert first["billStatus"] == "0"

    def test_day_keys_are_sequential(self):
        params = PeopleTimesheetAPI.build_log_params(
            year=2025, month=1, job_id="J1"
        )
        # Tutti i 31 giorni di gennaio
        for i, entry in enumerate(params["logParams"], start=1):
            assert f"day{i}" in entry

    def test_skip_dates_excluded(self):
        # Salta i primi 3 giorni di marzo
        skip = {"2025-03-01", "2025-03-02", "2025-03-03"}
        params = PeopleTimesheetAPI.build_log_params(
            year=2025, month=3, job_id="J1", skip_dates=skip
        )
        entries = params["logParams"]
        assert len(entries) == 28            # 31 - 3 = 28
        assert "day1" not in entries[0]      # day1 saltato → primo entry è day4
        assert "day4" in entries[0]

    def test_february_2025_has_28_entries(self):
        params = PeopleTimesheetAPI.build_log_params(
            year=2025, month=2, job_id="J1"
        )
        assert len(params["logParams"]) == 28

    def test_february_2024_leap_has_29_entries(self):
        params = PeopleTimesheetAPI.build_log_params(
            year=2024, month=2, job_id="J1"
        )
        assert len(params["logParams"]) == 29

    def test_skip_weekends_true_reduces_entries(self):
        # Con skip_weekends=True, marzo 2025 ha 10 weekend days → 21 entries
        params = PeopleTimesheetAPI.build_log_params(
            year=2025, month=3, job_id="J1", skip_weekends=True
        )
        assert len(params["logParams"]) == 21


# ─────────────────────────────────────────────────────────────────────────────
# PeopleTimesheetAPI – HTTP (mock)
# ─────────────────────────────────────────────────────────────────────────────

class TestTimesheetHTTP:

    def test_get_calls_correct_endpoint_with_user_id(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {"tsArr": [], "leaveData": {"leaveJson": {}}}

        monkeypatch.setattr(client, "get", mock_get)
        client.timesheet.get("P-001", "01/03/2025", "31/03/2025")

        assert captured["path"] == "timetracker/getTimesheetLog"
        assert captured["params"]["userId"]   == "P-001"
        assert captured["params"]["fromDate"] == "01/03/2025"
        assert captured["params"]["toDate"]   == "31/03/2025"

    def test_add_sends_json_encoded_log_params(self, client, monkeypatch):
        captured = {}

        def mock_form_post(path, data, params=None):
            captured["path"] = path
            captured["data"] = data
            return {"message": "ok", "status": 0}

        monkeypatch.setattr(client, "form_post", mock_form_post)

        log_params = {"logParams": [{"day1": "8", "jobId": "J1", "billStatus": "0"}]}
        client.timesheet.add("P-001", "01/03/2025", "31/03/2025", log_params)

        assert captured["path"] == "timetracker/addtimesheet"
        assert captured["data"]["userErecNo"] == "P-001"
        assert json.loads(captured["data"]["logParams"]) == log_params

    def test_add_monthly_raises_if_already_sent(self, client, monkeypatch):
        def mock_get(path, params=None):
            return {"tsArr": [{"id": "1"}], "leaveData": {"leaveJson": {}}}

        monkeypatch.setattr(client, "get", mock_get)

        with pytest.raises(ValueError, match="già inviato"):
            client.timesheet.add_monthly("P-001", month=3, year=2025, job_id="J1")

    def test_add_monthly_skips_leave_days(self, client, monkeypatch):
        captured_params = {}

        def mock_get(path, params=None):
            return {
                "tsArr": [],
                "leaveData": {
                    "leaveJson": {
                        "2025-03-10": {"type": "Annual Leave"},
                        "2025-03-11": {"type": "Annual Leave"},
                    }
                },
            }

        def mock_form_post(path, data, params=None):
            captured_params["logParams"] = json.loads(data["logParams"])
            return {"message": "ok", "status": 0}

        monkeypatch.setattr(client, "get", mock_get)
        monkeypatch.setattr(client, "form_post", mock_form_post)

        client.timesheet.add_monthly("P-001", month=3, year=2025, job_id="J1")

        entries = captured_params["logParams"]["logParams"]
        # 31 giorni di marzo - 2 giorni di ferie = 29 voci (skip_weekends=False)
        assert len(entries) == 29
        # day10 e day11 non devono essere presenti
        all_keys = {k for e in entries for k in e}
        assert "day10" not in all_keys
        assert "day11" not in all_keys

    def test_get_jobs_calls_correct_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"] = path
            return {"response": {"result": [
                {"jobId": "J001", "jobName": "Sviluppo"},
                {"jobId": "J002", "jobName": "Supporto"},
            ]}}

        monkeypatch.setattr(client, "get", mock_get)
        jobs = client.timesheet.get_jobs()

        assert captured["path"] == "timetracker/getjobs"
        assert len(jobs) == 2
        assert jobs[0]["jobId"] == "J001"

    def test_get_jobs_handles_flat_data_key(self, client, monkeypatch):
        monkeypatch.setattr(
            client, "get",
            lambda path, params=None: {"data": [{"jobId": "J1", "jobName": "Dev"}]}
        )
        jobs = client.timesheet.get_jobs()
        assert len(jobs) == 1
        assert jobs[0]["jobName"] == "Dev"

    def test_get_jobs_empty_response(self, client, monkeypatch):
        monkeypatch.setattr(client, "get", lambda path, params=None: {})
        jobs = client.timesheet.get_jobs()
        assert jobs == []

    def test_get_jobs_filters_by_employee(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["params"] = params
            return {"data": []}

        monkeypatch.setattr(client, "get", mock_get)
        client.timesheet.get_jobs(employee_id="P-001")

        assert captured["params"]["userId"] == "P-001"


# ─────────────────────────────────────────────────────────────────────────────
# PeopleEmployeeAPI – _normalize_list (puro, no HTTP)
# ─────────────────────────────────────────────────────────────────────────────

class TestNormalizeList:

    def test_normalizes_list_format(self):
        raw = [["P-001", None, None, "Mario Rossi", "EMP001", "API001", "mario@example.com"]]
        result = PeopleEmployeeAPI._normalize_list(raw)

        assert len(result) == 1
        assert result[0]["EmployeeRecordNumber"] == "P-001"
        assert result[0]["SurnameName"]          == "Mario Rossi"
        assert result[0]["Email"]                == "mario@example.com"
        assert result[0]["EmployID"]             == "EMP001"
        assert result[0]["ApiID"]                == "API001"

    def test_normalizes_dict_format(self):
        raw = [{"eNo": "P-002", "fullName": "Luca Bianchi", "emailId": "luca@example.com",
                "empId": "EMP002", "id": "API002"}]
        result = PeopleEmployeeAPI._normalize_list(raw)

        assert result[0]["EmployeeRecordNumber"] == "P-002"
        assert result[0]["SurnameName"]          == "Luca Bianchi"
        assert result[0]["Email"]                == "luca@example.com"

    def test_handles_html_entities_in_email(self):
        raw = [["P-003", None, None, "Test User", "E1", "A1", "test&#64;example.com"]]
        result = PeopleEmployeeAPI._normalize_list(raw)
        assert result[0]["Email"] == "test@example.com"

    def test_handles_empty_list(self):
        assert PeopleEmployeeAPI._normalize_list([]) == []

    def test_handles_short_list_entries(self):
        raw = [["P-004", None, None, "Solo Nome"]]
        result = PeopleEmployeeAPI._normalize_list(raw)
        assert result[0]["EmployeeRecordNumber"] == "P-004"
        assert result[0]["SurnameName"]          == "Solo Nome"
        assert result[0]["Email"]                == ""


# ─────────────────────────────────────────────────────────────────────────────
# PeopleEmployeeAPI – HTTP (mock)
# ─────────────────────────────────────────────────────────────────────────────

class TestEmployeeHTTP:

    def test_list_calls_correct_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {}

        monkeypatch.setattr(client, "get", mock_get)
        client.employee.list()

        assert captured["path"] == "forms/json/P_EmployeeView/getRecords"
        assert captured["params"]["page"]     == 1
        assert captured["params"]["per_page"] == 200

    def test_list_with_search_value(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["params"] = params
            return {}

        monkeypatch.setattr(client, "get", mock_get)
        client.employee.list(search_value="Mario")

        assert captured["params"]["searchValue"] == "Mario"

    def test_list_returns_result_array(self, client, monkeypatch):
        employees = [
            {"eNo": "P-001", "fullName": "Mario Rossi",  "emailId": "mario@ex.com", "empId": "E1", "id": "A1"},
            {"eNo": "P-002", "fullName": "Luca Bianchi", "emailId": "luca@ex.com",  "empId": "E2", "id": "A2"},
        ]
        monkeypatch.setattr(
            client, "get",
            lambda path, params=None: {"data": employees}
        )
        result = client.employee.list()
        assert len(result) == 2

    def test_search_filters_by_name(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["params"] = params
            return {}

        monkeypatch.setattr(client, "get", mock_get)
        client.employee.search("Rossi")

        assert captured["params"]["searchValue"] == "Rossi"

    def test_find_returns_json_string(self, client, monkeypatch):
        monkeypatch.setattr(
            client, "get",
            lambda path, params=None: {"data": [
                {"eNo": "P-001", "fullName": "Mario Rossi", "emailId": "mario@ex.com",
                 "empId": "E1", "id": "A1"}
            ]}
        )
        result = client.employee.find("Rossi")

        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]["SurnameName"] == "Mario Rossi"

    def test_get_calls_v3_getrecordbyid(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {"response": {"result": [
                {"eNo": "P-001", "fullName": "Mario Rossi", "emailId": "mario@ex.com",
                 "empId": "P-001", "id": "A1"}
            ]}}

        monkeypatch.setattr(client, "get", mock_get)
        emp = client.employee.get("P-001")

        assert captured["path"] == "employee/getRecordByID"
        assert captured["params"]["empId"] == "P-001"
        assert emp["SurnameName"] == "Mario Rossi"

    def test_get_tree_calls_v3_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {"response": {"result": []}}

        monkeypatch.setattr(client, "get", mock_get)
        client.employee.get_tree("P-001")

        assert captured["path"] == "employee/getEmployeeTree"
        assert captured["params"]["erecno"] == "P-001"

    def test_add_record_calls_post(self, client, monkeypatch):
        captured = {}

        def mock_post(path, json=None, params=None):
            captured["path"] = path
            captured["json"] = json
            return {"response": {"result": {"recordId": "NEW-001"}}}

        monkeypatch.setattr(client, "post", mock_post)
        client.employee.add_record({"firstName": "Nuovo", "lastName": "Dipendente"})

        assert captured["path"] == "employee/addRecord"
        assert captured["json"]["firstName"] == "Nuovo"

    def test_update_record_calls_put(self, client, monkeypatch):
        captured = {}

        def mock_put(path, json=None, params=None):
            captured["path"] = path
            captured["json"] = json
            return {"response": {"status": 0}}

        monkeypatch.setattr(client, "put", mock_put)
        client.employee.update_record("P-001", {"department": "HR"})

        assert captured["path"] == "employee/updateRecord"
        assert captured["json"]["empId"]      == "P-001"
        assert captured["json"]["department"] == "HR"

    def test_list_handles_users_key(self, client, monkeypatch):
        monkeypatch.setattr(
            client, "get",
            lambda path, params=None: {"users": {"userList": [["P-010"]]}}
        )
        result = client.employee.list()
        assert isinstance(result, list)


# ─────────────────────────────────────────────────────────────────────────────
# PeopleLeaveAPI – HTTP (mock)
# ─────────────────────────────────────────────────────────────────────────────

class TestLeaveHTTP:

    def test_get_requests_calls_v3_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {"response": {"result": []}}

        monkeypatch.setattr(client, "get", mock_get)
        client.leave.get_requests(user_id="mario@azienda.it", status="Pending")

        assert captured["path"] == "leave/getLeaveRequests"
        assert captured["params"]["userId"]        == "mario@azienda.it"
        assert captured["params"]["allowedStatus"] == "Pending"

    def test_get_requests_date_conversion(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["params"] = params
            return {"response": {"result": []}}

        monkeypatch.setattr(client, "get", mock_get)
        client.leave.get_requests(from_date="01/03/2026", to_date="31/03/2026")

        assert captured["params"]["fromDate"] == "01-Mar-2026"
        assert captured["params"]["toDate"]   == "31-Mar-2026"

    def test_add_request_calls_v3_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_form_post(path, data, params=None):
            captured["path"] = path
            captured["data"] = data
            return {"response": {"result": {"requestId": "REQ-001"}}}

        monkeypatch.setattr(client, "form_post", mock_form_post)

        client.leave.add_request(
            user_id="mario@azienda.it",
            leave_type="Annual Leave",
            from_date="24/03/2026",
            to_date="27/03/2026",
            reason="Vacanza",
        )

        assert captured["path"] == "leave/addLeaveRequest"
        assert captured["data"]["userId"]    == "mario@azienda.it"
        assert captured["data"]["leavetype"] == "Annual Leave"
        assert captured["data"]["fromDate"]  == "24-Mar-2026"
        assert captured["data"]["toDate"]    == "27-Mar-2026"
        assert captured["data"]["reason"]    == "Vacanza"

    def test_get_balance_calls_v3_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {"response": {"result": [
                {"leaveType": "Annual Leave", "balance": "10", "used": "5"},
            ]}}

        monkeypatch.setattr(client, "get", mock_get)
        balance = client.leave.get_balance("mario@azienda.it")

        assert captured["path"] == "leave/getLeaveRecord"
        assert captured["params"]["userId"] == "mario@azienda.it"
        assert len(balance) == 1
        assert balance[0]["leaveType"] == "Annual Leave"

    def test_update_status_approve(self, client, monkeypatch):
        captured = {}

        def mock_form_post(path, data, params=None):
            captured["path"] = path
            captured["data"] = data
            return {"response": {"status": 0}}

        monkeypatch.setattr(client, "form_post", mock_form_post)
        client.leave.update_status("REQ-789", status=1, comments="Approvato")

        assert captured["path"] == "leave/updateLeaveRequestStatus"
        assert captured["data"]["requestId"] == "REQ-789"
        assert captured["data"]["status"]    == 1
        assert captured["data"]["comments"]  == "Approvato"

    def test_approve_shortcut(self, client, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            client, "form_post",
            lambda path, data, params=None: captured.update({"path": path, "data": data}) or {}
        )
        client.leave.approve("REQ-001")
        assert captured["data"]["status"] == PeopleLeaveAPI.STATUS_APPROVE

    def test_reject_shortcut(self, client, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            client, "form_post",
            lambda path, data, params=None: captured.update({"path": path, "data": data}) or {}
        )
        client.leave.reject("REQ-001", "Non approvato")
        assert captured["data"]["status"] == PeopleLeaveAPI.STATUS_REJECT

    def test_cancel_shortcut(self, client, monkeypatch):
        captured = {}
        monkeypatch.setattr(
            client, "form_post",
            lambda path, data, params=None: captured.update({"path": path, "data": data}) or {}
        )
        client.leave.cancel("REQ-001")
        assert captured["data"]["status"] == PeopleLeaveAPI.STATUS_CANCEL

    def test_get_requests_returns_list(self, client, monkeypatch):
        monkeypatch.setattr(
            client, "get",
            lambda path, params=None: {"response": {"result": [
                {"requestId": "R1", "status": "Pending"},
                {"requestId": "R2", "status": "Approved"},
            ]}}
        )
        result = client.leave.get_requests()
        assert len(result) == 2
        assert result[0]["requestId"] == "R1"

    def test_get_balance_without_user(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["params"] = params
            return {"response": {"result": []}}

        monkeypatch.setattr(client, "get", mock_get)
        client.leave.get_balance()

        # Senza userId non deve essere incluso nel params
        assert captured["params"] is None or "userId" not in (captured["params"] or {})


# ─────────────────────────────────────────────────────────────────────────────
# Integrazione: client espone le proprietà
# ─────────────────────────────────────────────────────────────────────────────

class TestClientProperties:

    def test_attendance_property(self, client):
        assert isinstance(client.attendance, PeopleAttendanceAPI)

    def test_timesheet_property(self, client):
        assert isinstance(client.timesheet, PeopleTimesheetAPI)

    def test_employee_property(self, client):
        assert isinstance(client.employee, PeopleEmployeeAPI)

    def test_leave_property(self, client):
        assert isinstance(client.leave, PeopleLeaveAPI)

    def test_properties_are_cached(self, client):
        assert client.attendance is client.attendance
        assert client.timesheet  is client.timesheet
        assert client.employee   is client.employee
        assert client.leave      is client.leave


# ─────────────────────────────────────────────────────────────────────────────
# PeopleAttendanceAPI – new REST endpoints
# ─────────────────────────────────────────────────────────────────────────────

class TestAttendanceNewEndpoints:

    def test_get_specific_entry(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {"response": {"result": {"attendanceId": "ATT-001"}}}

        monkeypatch.setattr(client, "get", mock_get)
        client.attendance.get_specific_entry("ATT-001")

        assert captured["path"]              == "attendance/getSpecificEntry"
        assert captured["params"]["attendanceId"] == "ATT-001"

    def test_update_entry(self, client, monkeypatch):
        captured = {}

        def mock_put(path, json=None, params=None):
            captured["path"] = path
            captured["json"] = json
            return {"response": {"result": {}}}

        monkeypatch.setattr(client, "put", mock_put)
        client.attendance.update_entry("ATT-001", "09:00", "18:00", reason="correction")

        assert captured["path"]              == "attendance/updateEntry"
        assert captured["json"]["attendanceId"] == "ATT-001"
        assert captured["json"]["checkIn"]      == "09:00"
        assert captured["json"]["checkOut"]     == "18:00"
        assert captured["json"]["reason"]       == "correction"

    def test_update_entry_no_reason(self, client, monkeypatch):
        captured = {}
        monkeypatch.setattr(client, "put",
                            lambda path, json=None, params=None: captured.update({"json": json}) or {})
        client.attendance.update_entry("ATT-002", "08:30", "17:30")
        assert "reason" not in captured["json"]

    def test_delete_specific_entry(self, client, monkeypatch):
        captured = {}

        def mock_delete(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {"response": {"result": {}}}

        monkeypatch.setattr(client, "delete", mock_delete)
        client.attendance.delete_specific_entry("ATT-001")

        assert captured["path"]                  == "attendance/deleteSpecificEntry"
        assert captured["params"]["attendanceId"] == "ATT-001"

    def test_delete_entries(self, client, monkeypatch):
        captured = {}

        def mock_delete(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return {"response": {"result": {}}}

        monkeypatch.setattr(client, "delete", mock_delete)
        client.attendance.delete_entries("user@example.com", "01/03/2026", "31/03/2026")

        assert captured["path"]              == "attendance/deleteEntries"
        assert captured["params"]["userId"]  == "user@example.com"

    def test_punch_in(self, client, monkeypatch):
        captured = {}

        def mock_form_post(path, data, params=None):
            captured["path"] = path
            captured["data"] = data
            return {"status": 0}

        monkeypatch.setattr(client, "form_post", mock_form_post)
        client.attendance.punch_in("P-001", "09:00", location="HQ",
                                   latitude="45.0", longitude="9.0")

        assert captured["path"]                  == "attendance/punchIn"
        assert captured["data"]["employeeId"]    == "P-001"
        assert captured["data"]["checkInTime"]   == "09:00"
        assert captured["data"]["location"]      == "HQ"
        assert captured["data"]["latitude"]      == "45.0"
        assert captured["data"]["longitude"]     == "9.0"

    def test_punch_in_minimal(self, client, monkeypatch):
        captured = {}
        monkeypatch.setattr(client, "form_post",
                            lambda path, data, params=None: captured.update({"data": data}) or {})
        client.attendance.punch_in("P-002", "08:30")
        assert "location" not in captured["data"]
        assert "latitude" not in captured["data"]


# ─────────────────────────────────────────────────────────────────────────────
# CompensatoryAPI – file_upload
# ─────────────────────────────────────────────────────────────────────────────

class TestCompensatoryFileUpload:

    def test_file_upload_calls_correct_endpoint(self, client, monkeypatch, tmp_path):
        captured = {}
        dummy = tmp_path / "doc.pdf"
        dummy.write_bytes(b"PDF")

        def mock_upload(path, files, data=None):
            captured["path"] = path
            captured["data"] = data
            return {"status": 0}

        monkeypatch.setattr(client, "upload", mock_upload)
        from zoho_vertical_sdk.compensatory import CompensatoryAPI
        api = CompensatoryAPI(client)
        api.file_upload("REQ-001", str(dummy))

        assert captured["path"]              == "compensatory/fileUpload"
        assert captured["data"]["requestId"] == "REQ-001"


# ─────────────────────────────────────────────────────────────────────────────
# FilesAPI – add_file / download_file
# ─────────────────────────────────────────────────────────────────────────────

class TestFilesAPINew:

    def test_add_file_calls_correct_endpoint(self, client, monkeypatch, tmp_path):
        captured = {}
        dummy = tmp_path / "report.pdf"
        dummy.write_bytes(b"PDF content")

        def mock_upload(path, files, data=None):
            captured["path"] = path
            captured["data"] = data
            return {"status": 0}

        monkeypatch.setattr(client, "upload", mock_upload)
        from zoho_vertical_sdk.files_api import FilesAPI
        api = FilesAPI(client)
        api.add_file(str(dummy), folder_id="FOLD-1", employee_id="EMP-1")

        assert captured["path"]                == "files/addFile"
        assert captured["data"]["folderId"]    == "FOLD-1"
        assert captured["data"]["employeeId"]  == "EMP-1"

    def test_add_file_without_employee(self, client, monkeypatch, tmp_path):
        captured = {}
        dummy = tmp_path / "file.txt"
        dummy.write_bytes(b"text")

        monkeypatch.setattr(client, "upload",
                            lambda path, files, data=None: captured.update({"data": data}) or {})
        from zoho_vertical_sdk.files_api import FilesAPI
        api = FilesAPI(client)
        api.add_file(str(dummy), folder_id="FOLD-2")

        assert "employeeId" not in (captured["data"] or {})

    def test_download_file_calls_correct_endpoint(self, client, monkeypatch):
        captured = {}

        def mock_get(path, params=None):
            captured["path"]   = path
            captured["params"] = params
            return b"binary content"

        monkeypatch.setattr(client, "get", mock_get)
        from zoho_vertical_sdk.files_api import FilesAPI
        api = FilesAPI(client)
        result = api.download_file("FILE-001")

        assert captured["path"]               == "files/downloadFile"
        assert captured["params"]["fileId"]   == "FILE-001"
        assert result == b"binary content"
