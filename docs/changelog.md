# Changelog

## [0.1.0] - 2026-04-26

### Added
- `zoho_people` SDK: attendance, timesheet, leave, employee modules
- OAuth 2.0 authentication with automatic token refresh
- CLI (`main.py`) with interactive menu
- Attendance: read report, send via browser session (Playwright fallback)
- Timesheet: add time logs, create and submit timesheet for approval
- Leave: get approved and pending leave records
- Holidays: Italian and Swiss public holidays (including Easter calculation)
- Auto-exclusion of weekends, public holidays, approved and pending leaves
- Playwright-based browser automation for attendance when API permissions unavailable

### Known Limitations
- Attendance write API requires admin/data-admin role in Zoho People
- Browser fallback (Playwright) requires `ZOHO_PASSWORD` in `.env`
