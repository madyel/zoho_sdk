# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-04-27

### Added
- `ZohoPeopleAuth` — OAuth 2.0 with automatic token refresh and `from_env()` helper
- `ZohoPeopleClient` — core HTTP client with retry, rate-limit handling and context manager support
- `AttendanceAPI` — check-in / check-out, bulk import, user report, shift configuration
- `TimesheetAPI` — add time logs, create and submit timesheets for approval
- `LeaveAPI` — list, apply, approve, cancel leave requests; leave balance report
- `EmployeeAPI` — list, search by email / ID, create and update employee records
- Typed exceptions: `ZohoPeopleAuthError`, `ZohoPeoplePermissionError`, `ZohoPeopleRateLimitError`, `ZohoPeopleNotFoundError`, `ZohoPeopleValidationError`
- Multi data-centre support: US, EU, IN, AU, JP
- PEP 561 `py.typed` marker — full type hint support
- Sphinx documentation with English and Italian translations
- Read the Docs integration (`.readthedocs.yaml`)
- GitHub Actions CI — lint (ruff, mypy) + test matrix (Python 3.10 / 3.11 / 3.12)

### Known Limitations
- Attendance write API requires *"Check-in/Check-out"* or *"Regularize Attendance"* permission enabled in Zoho People → Settings → Attendance → Permissions
