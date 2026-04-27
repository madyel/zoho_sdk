# zoho-people-sdk

[![CI](https://github.com/madyel83/zoho-people-sdk/actions/workflows/ci.yml/badge.svg)](https://github.com/madyel83/zoho-people-sdk/actions)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://pypi.org/project/zoho-people-sdk/)
[![Version](https://img.shields.io/badge/version-0.1.0-blue)](CHANGELOG.md)
[![Docs](https://readthedocs.org/projects/zoho-sdk-people/badge/?version=latest)](https://zoho-sdk-people.readthedocs.io/en/latest/)
<!-- Uncomment after publishing to PyPI:
[![PyPI](https://img.shields.io/pypi/v/zoho-people-sdk)](https://pypi.org/project/zoho-people-sdk/)
-->

Python SDK for the **Zoho People REST API**.

Covers attendance, timesheet, leave management, and employee records — with automatic OAuth token refresh, typed exceptions, and full type hints.

📚 **Full documentation:** [zoho-people-sdk.readthedocs.io](https://zoho-sdk-people.readthedocs.io)

---

## Features

- **Attendance** — check-in / check-out, bulk import, user reports, shift configuration
- **Timesheet** — create, submit, approve time logs and timesheet periods
- **Leave** — apply, approve, cancel leave requests; leave balance report
- **Employees** — list, search by email / ID, create and update records
- **OAuth 2.0** — automatic token refresh, `from_env()` helper, multi data-centre support
- **Typed exceptions** — `ZohoPeopleAuthError`, `ZohoPeoplePermissionError`, `ZohoPeopleRateLimitError`, …
- **PEP 561** — fully typed, `py.typed` marker included

---

## Installation

```bash
pip install zoho-people-sdk
```

With browser fallback for attendance (when API permissions are unavailable):

```bash
pip install "zoho-people-sdk[browser]"
playwright install chromium
```

---

## Quick Start

```python
from zoho_people import ZohoPeopleAuth, ZohoPeopleClient

# Load credentials from environment variables:
# ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN, ZOHO_DATA_CENTRE
auth   = ZohoPeopleAuth.from_env()
client = ZohoPeopleClient(auth=auth)

# Employees
employees = client.employee.list()

# Add a time log
client.timesheet.add_timelog(
    user="mario.rossi@company.com",
    work_date="2026-04-25",
    hours="08:00",
    job_name="My Project",
)

# Pending leave requests
pending = client.leave.get_pending(
    from_date="01-Apr-2026",
    to_date="30-Apr-2026",
)

# Monthly attendance report
report = client.attendance.get_user_report(
    start_date="01/04/2026",
    end_date="30/04/2026",
    date_format="dd/MM/yyyy",
)
```

---

## Environment Variables

Copy `.env.example` to `.env`:

```env
ZOHO_CLIENT_ID=1000.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ZOHO_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ZOHO_DATA_CENTRE=US          # US | EU | IN | AU | JP
ZOHO_REFRESH_TOKEN=1000.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
ZOHO_USER_EMAIL=you@company.com
```

Required OAuth scopes:

```
ZOHOPEOPLE.forms.ALL,ZOHOPEOPLE.attendance.ALL,ZOHOPEOPLE.timetracker.ALL,ZOHOPEOPLE.leave.ALL
```

---

## Error Handling

```python
from zoho_people.exceptions import (
    ZohoPeopleAuthError,
    ZohoPeoplePermissionError,
    ZohoPeopleRateLimitError,
    ZohoPeopleNotFoundError,
    ZohoPeopleValidationError,
    ZohoPeopleError,
)

try:
    client.timesheet.add_timelog(...)
except ZohoPeoplePermissionError:
    print("Missing role permission in Zoho People settings")
except ZohoPeopleAuthError:
    print("Invalid or expired OAuth token")
except ZohoPeopleRateLimitError:
    print("Rate limit hit — SDK will auto-retry")
except ZohoPeopleError as e:
    print(f"API error {e.status_code}: {e.message}")
```

---

## Data Centres

| Region    | Code | Accounts URL                  |
|-----------|------|-------------------------------|
| US        | `US` | `accounts.zoho.com`           |
| Europe    | `EU` | `accounts.zoho.eu`            |
| India     | `IN` | `accounts.zoho.in`            |
| Australia | `AU` | `accounts.zoho.com.au`        |
| Japan     | `JP` | `accounts.zoho.jp`            |

---

## Documentation

Full documentation is available at **[zoho-people-sdk.readthedocs.io](https://zoho-sdk-people.readthedocs.io)** in English and Italian:

- [Getting Started](https://zoho-sdk-people.readthedocs.io/en/latest/getting-started/installation.html)
- [User Guide](https://zoho-sdk-people.readthedocs.io/en/latest/guide/attendance.html)
- [API Reference](https://zoho-sdk-people.readthedocs.io/en/latest/api/client.html)

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Install dev dependencies: `pip install -e ".[dev]"`
4. Run tests: `pytest`
5. Lint: `ruff check src/`
6. Open a pull request

---

## License

[MIT](LICENSE) © 2026 madyel83
