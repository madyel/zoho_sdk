#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
  examples_test2.py  –  Zoho People SDK  –  Attendance / Timesheet / Employee
═══════════════════════════════════════════════════════════════════════════════

Copre le nuove API specifiche di Zoho People:

  1.  Helpers orario  – time_to_seconds / seconds_to_time
  2.  Employee – lista dipendenti
  3.  Employee – cerca dipendente (findEmploy)
  4.  Employee – dettaglio singolo dipendente
  5.  Employee – albero organizzativo
  6.  Attendance – presenze mensili (attendanceViewAction)
  7.  Attendance – giorni assenti del mese
  8.  Attendance – registra presenza singola (add)
  9.  Attendance – registra presenza bulk (sendAttendance)
  10. Timesheet  – lista job disponibili
  11. Timesheet  – log timesheet mese (timesheetDispAction)
  12. Timesheet  – costruisci logParams (build_log_params)
  13. Timesheet  – invia timesheet (sendTimesheet)
  14. Timesheet  – flusso completo mese (add_monthly)
  15. Gestione errori People API

Utilizzo:
    python examples_test2.py                    # esegui tutto
    python examples_test2.py --section 10       # solo lista job
    python examples_test2.py --section employee # sezioni 2-5
    python examples_test2.py --section attend   # sezioni 6-9
    python examples_test2.py --section time     # sezioni 10-14
    python examples_test2.py --list             # mostra tutte le sezioni

Variabili .env richieste (minimo):
    ZOHO_CLIENT_ID=...
    ZOHO_CLIENT_SECRET=...
    ZOHO_DATA_CENTRE=US

Variabili .env opzionali per i test:
    ZOHO_EMPLOYEE_ID=self          # ID dipendente (default: self)
    ZOHO_TEST_MONTH=3              # mese di test (default: mese corrente)
    ZOHO_TEST_YEAR=2025            # anno di test (default: anno corrente)
    ZOHO_JOB_ID=                   # job ID per il timesheet
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import date
from typing import Optional

# ---------------------------------------------------------------------------
# Path e .env
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from dotenv import load_dotenv
    _env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
except ImportError:
    pass

try:
    from zoho_vertical_sdk import (
        ZohoVerticalClient,
        ZohoOAuthToken,
        time_to_seconds,
        seconds_to_time,
    )
    from zoho_vertical_sdk.exceptions import ZohoAPIError, ZohoAuthError
    from zoho_vertical_sdk.timesheet import PeopleTimesheetAPI
    from auth_manager import ZohoAuthManager
except ImportError as e:
    print(f"❌  Impossibile importare: {e}")
    sys.exit(1)


# ─────────────────────────────────────────────────────────────────────────────
#  Stampa
# ─────────────────────────────────────────────────────────────────────────────

def title(text: str) -> None:
    w = 70
    print("\n" + "═" * w)
    print(f"  {text}")
    print("═" * w)

def section(num, text: str) -> None:
    num_str = f"{num:02d}" if isinstance(num, int) else str(num)
    print(f"\n{'─'*60}")
    print(f"  [{num_str}]  {text}")
    print("─" * 60)

def ok(msg: str)   -> None: print(f"  ✅  {msg}")
def err(msg: str)  -> None: print(f"  ❌  {msg}")
def info(msg: str) -> None: print(f"  ℹ️   {msg}")
def skip(msg: str) -> None: print(f"  ⏭️   SALTATO – {msg}")
def warn(msg: str) -> None: print(f"  ⚠️   {msg}")

def dump(label: str, data) -> None:
    raw = json.dumps(data, ensure_ascii=False, default=str, indent=2)
    if len(raw) > 600:
        raw = raw[:600] + "\n  … (troncato)"
    print(f"  📦  {label}:\n{raw}")


# ─────────────────────────────────────────────────────────────────────────────
#  Configurazione
# ─────────────────────────────────────────────────────────────────────────────

CLIENT_ID     = os.getenv("ZOHO_CLIENT_ID",     "")
CLIENT_SECRET = os.getenv("ZOHO_CLIENT_SECRET", "")
EMPLOYEE_ID   = os.getenv("ZOHO_EMPLOYEE_ID",   "self")
JOB_ID        = os.getenv("ZOHO_JOB_ID",        "")
# Es: ZOHO_SERVICE_URL=/relewanthrm/zp  (il path organizzativo Zoho People)
SERVICE_URL   = os.getenv("ZOHO_SERVICE_URL",   "")

_today = date.today()
TEST_MONTH = int(os.getenv("ZOHO_TEST_MONTH", str(_today.month)))
TEST_YEAR  = int(os.getenv("ZOHO_TEST_YEAR",  str(_today.year)))

client: Optional[ZohoVerticalClient] = None


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 1 – Helpers orario                                                #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_01_time_helpers():
    section(1, "Helpers orario – time_to_seconds / seconds_to_time")

    samples = [
        ("9:00",  32400),
        ("17:00", 61200),
        ("17:30", 63000),
        ("18:00", 64800),
        ("00:00", 0),
    ]

    info("Conversione HH:MM → secondi dalla mezzanotte:")
    all_ok = True
    for t, expected in samples:
        result = time_to_seconds(t)
        status = "✅" if result == expected else "❌"
        print(f"    {status}  time_to_seconds({t!r:8}) = {result:6}  (atteso {expected})")
        if result != expected:
            all_ok = False

    info("Conversione secondi → HH:MM:")
    for t, secs in samples:
        result = seconds_to_time(secs)
        h, m = t.split(":")
        expected_fmt = f"{int(h):02d}:{m}"
        status = "✅" if result == expected_fmt else "❌"
        print(f"    {status}  seconds_to_time({secs:6}) = {result!r:8}  (atteso {expected_fmt!r})")

    info("Roundtrip HH:MM → secondi → HH:MM:")
    for t, _ in [("09:00", None), ("17:30", None), ("08:45", None)]:
        rt = seconds_to_time(time_to_seconds(t))
        status = "✅" if rt == t else "❌"
        print(f"    {status}  {t!r} → {time_to_seconds(t)} → {rt!r}")

    if all_ok:
        ok("Tutti gli helper funzionano correttamente")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 2 – Employee – lista                                              #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_02_employee_list():
    section(2, "Employee – lista dipendenti")

    if client is None:
        skip("Client non inizializzato")
        return

    try:
        employees = client.employee.list(per_page=5)
        ok(f"Dipendenti ricevuti: {len(employees)}")
        for e in employees[:5]:
            if isinstance(e, dict):
                name   = e.get("fullName") or e.get("name", "?")
                emp_id = e.get("eNo") or e.get("empId", "?")
                email  = e.get("emailId") or e.get("email", "")
                print(f"    • [{emp_id}]  {name:30}  {email}")
            else:
                print(f"    • {e}")
    except ZohoAPIError as e:
        err(f"Lista dipendenti: {e}")
        info("Provo path alternativi per trovare l'endpoint corretto:")
        for alt_path in ["employee", "forms/P_Employee/getRecords", "forms/P_EmployeeView/getRecords", "v2/employee"]:
            try:
                raw = client.get(alt_path)
                ok(f"  ✅  Funziona: /people/api/{alt_path}")
                dump(f"  risposta", raw)
                break
            except ZohoAPIError as ex2:
                info(f"  ❌  /people/api/{alt_path} → {ex2}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 3 – Employee – cerca (findEmploy)                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_03_employee_search():
    section(3, "Employee – cerca dipendente (findEmploy)")

    if client is None:
        skip("Client non inizializzato")
        return

    query = "a"   # cerca tutti quelli con 'a' nel nome
    info(f"Ricerca dipendenti con '{query}':")
    try:
        # find() restituisce JSON stringa, identico al vecchio findEmploy()
        result_json = client.employee.find(query)
        results = json.loads(result_json)
        ok(f"Trovati {len(results)} dipendenti")
        for r in results[:3]:
            print(f"    • [{r.get('EmployeeRecordNumber','?')}]  "
                  f"{r.get('SurnameName','?'):30}  {r.get('Email','')}")
        if len(results) > 3:
            info(f"  … e altri {len(results) - 3}")
    except ZohoAPIError as e:
        err(f"Ricerca: {e}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 4 – Employee – dettaglio singolo                                  #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_04_employee_get():
    section(4, f"Employee – dettaglio '{EMPLOYEE_ID}'")

    if client is None:
        skip("Client non inizializzato")
        return

    try:
        data = client.employee.get(EMPLOYEE_ID)
        ok(f"Risposta ricevuta")
        dump("employee.get()", data)
    except ZohoAPIError as e:
        err(f"Get employee: {e}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 5 – Employee – albero organizzativo                               #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_05_employee_tree():
    section(5, f"Employee – albero organizzativo di '{EMPLOYEE_ID}'")

    if client is None:
        skip("Client non inizializzato")
        return

    if EMPLOYEE_ID == "self":
        skip("Imposta ZOHO_EMPLOYEE_ID con un eNo reale (es. P-000042)")
        return

    try:
        tree = client.employee.get_tree(EMPLOYEE_ID)
        ok("Albero ricevuto")
        dump("employee.get_tree()", tree)
    except ZohoAPIError as e:
        err(f"Albero: {e}")


def _attendance_diagnose(cl, month: int, year: int, employee_id: str) -> None:
    """Prova varianti di endpoint e parametri per l'attendance API."""
    import calendar as _cal
    first = date(year, month, 1).strftime("%d/%m/%Y")
    last  = date(year, month, _cal.monthrange(year, month)[1]).strftime("%d/%m/%Y")
    svc   = {"servicename": "zohopeople", "serviceurl": SERVICE_URL} if SERVICE_URL else {}

    # Endpoint getUserReport (corretto per report mensile)
    base_report = {"sdate": first, "edate": last, "dateFormat": "dd/MM/yyyy"}
    # Endpoint vecchio (check-in/out) — manteniamo per confronto
    base_old    = {"dateRange": f"{first},{last}", "dateFormat": "dd/MM/yyyy"}

    variants = [
        # --- endpoint corretto: getUserReport ---
        ("getUserReport – nessun empId",      "attendance/getUserReport", {**base_report}),
        ("getUserReport – empId=self",        "attendance/getUserReport", {**base_report, "empId": "self"}),
        ("getUserReport – empId=ID",          "attendance/getUserReport", {**base_report, "empId": employee_id}),
        # --- getAttendanceEntries (singolo giorno) ---
        ("getAttendanceEntries – empId=ID",   "attendance/getAttendanceEntries",
         {"date": first, "empId": employee_id, "dateFormat": "dd/MM/yyyy"}),
        ("getAttendanceEntries – erecno=ID",  "attendance/getAttendanceEntries",
         {"date": first, "erecno": employee_id, "dateFormat": "dd/MM/yyyy"}),
        # --- vecchio endpoint attendance (solo check-in/out) ---
        ("attendance – userId=ID (vecchio)",  "attendance", {**base_old, "userId": employee_id}),
    ]
    if SERVICE_URL:
        variants += [
            ("getUserReport+svc – empId=ID",  "attendance/getUserReport",
             {**base_report, **svc, "empId": employee_id}),
        ]
    else:
        info("  ℹ  ZOHO_SERVICE_URL non impostato – imposta es. ZOHO_SERVICE_URL=/relewanthrm/zp")

    for label, endpoint, params in variants:
        try:
            raw = cl.get(endpoint, params=params)
            if isinstance(raw, list) and raw and raw[0].get("response") == "failure":
                info(f"  ✗  [{label}] → {raw[0].get('msg','?')}")
            elif isinstance(raw, dict) and raw.get("response") == "failure":
                info(f"  ✗  [{label}] → {raw.get('message', raw.get('msg','?'))}")
            else:
                ok(f"  ✓  [{label}] → SUCCESSO")
                dump(f"  risposta [{label}]", raw)
                return
        except ZohoAPIError as ex:
            info(f"  ✗  [{label}] → {ex}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 6 – Attendance – presenze mensili                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_06_attendance_monthly():
    section(6, f"Attendance – presenze {TEST_MONTH:02d}/{TEST_YEAR}")

    if client is None:
        skip("Client non inizializzato")
        return

    try:
        result = client.attendance.get_monthly(EMPLOYEE_ID, TEST_MONTH, TEST_YEAR)
        ok("Risposta ricevuta")

        # Stampa struttura raw per capire il formato reale dell'API
        info("Struttura risposta (raw, troncata):")
        dump("get_monthly()", result)

        # Errore di permesso (può arrivare come dict o lista)
        raw_check = result.get("_raw", result)
        if isinstance(raw_check, list) and raw_check:
            raw_check = raw_check[0]
        if isinstance(raw_check, dict) and raw_check.get("response") == "failure":
            msg = raw_check.get("msg", raw_check.get("message", "?"))
            err(f"Zoho People ha rifiutato la richiesta: '{msg}'")
            info("Provo varianti di endpoint e parametri per diagnostica:")
            _attendance_diagnose(client, TEST_MONTH, TEST_YEAR, EMPLOYEE_ID)
            return

        user = result.get("userDetails", {})
        if user:
            info(f"Dipendente: {user.get('firstName', user.get('first name',''))} "
                 f"{user.get('lastName', user.get('last name',''))}  "
                 f"eNo={user.get('eNo','?')}")

        day_list = result.get("dayList", {})
        if day_list:
            present = sum(1 for d in day_list.values() if d.get("status") == "Present")
            absent  = sum(1 for d in day_list.values()
                          if d.get("status") in ("Absent", "") and d.get("tHrs") == "00:00")
            ok(f"Giorni nel mese: {len(day_list)}  |  Presenti: {present}  |  Assenti: {absent}")

            info("Primi 5 giorni:")
            for date_key, day in list(day_list.items())[:5]:
                ldate  = day.get("ldate", date_key)
                status = day.get("status", "")
                t_hrs  = day.get("tHrs", "00:00")
                print(f"    • {ldate}  status={status:10}  ore={t_hrs}")
        else:
            warn("dayList vuoto – risposta raw:")
            dump("_raw", result.get("_raw", result))
            info("Avvio diagnostica endpoint:")
            _attendance_diagnose(client, TEST_MONTH, TEST_YEAR, EMPLOYEE_ID)

    except ZohoAPIError as e:
        err(f"get_monthly: {e}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 7 – Attendance – giorni assenti                                   #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_07_attendance_absent_days():
    section(7, f"Attendance – giorni assenti {TEST_MONTH:02d}/{TEST_YEAR}")

    if client is None:
        skip("Client non inizializzato")
        return

    try:
        result   = client.attendance.get_monthly(EMPLOYEE_ID, TEST_MONTH, TEST_YEAR)

        # Errore di permesso
        raw_check = result.get("_raw", result)
        if isinstance(raw_check, list) and raw_check:
            raw_check = raw_check[0]
        if isinstance(raw_check, dict) and raw_check.get("response") == "failure":
            skip(f"Attendance API: '{raw_check.get('msg','?')}' — vedi sezione 6")
            return

        day_list = result.get("dayList", {})

        if not day_list:
            skip("dayList vuoto")
            return

        from zoho_vertical_sdk.attendance import PeopleAttendanceAPI
        absent = PeopleAttendanceAPI.absent_days_from_daylist(day_list)

        ok(f"Giorni assenti trovati: {len(absent)}")
        for d in absent[:10]:
            print(f"    • {d}")
        if len(absent) > 10:
            info(f"  … e altri {len(absent) - 10}")

    except ZohoAPIError as e:
        err(f"Giorni assenti: {e}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 8 – Attendance – registra presenza singola                        #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_08_attendance_add():
    section(8, "Attendance – registra presenza singola (DRY RUN)")

    if client is None:
        skip("Client non inizializzato")
        return

    if EMPLOYEE_ID == "self":
        skip("Imposta ZOHO_EMPLOYEE_ID con un eNo reale per testare add()")
        return

    # Usa il primo giorno del mese di test come data di esempio
    test_date = date(TEST_YEAR, TEST_MONTH, 1).strftime("%d/%m/%Y")

    info(f"Parametri che verrebbero inviati (DRY RUN):")
    print(f"    erecno    = {EMPLOYEE_ID}")
    print(f"    fdate     = {test_date}")
    print(f"    ftime     = {time_to_seconds('09:00')}  ({seconds_to_time(time_to_seconds('09:00'))})")
    print(f"    ttime     = {time_to_seconds('18:00')}  ({seconds_to_time(time_to_seconds('18:00'))})")
    print(f"    endpoint  = POST /people/api/attendance")

    info("Per eseguire realmente:")
    print(f"    client.attendance.add('{EMPLOYEE_ID}', '{test_date}', '09:00', '18:00')")

    ok("DRY RUN completato – nessuna modifica effettuata")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 9 – Attendance – registra presenze bulk                           #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_09_attendance_bulk():
    section(9, "Attendance – flusso bulk (sendAttendance) – DRY RUN")

    if client is None:
        skip("Client non inizializzato")
        return

    try:
        result = client.attendance.get_monthly(EMPLOYEE_ID, TEST_MONTH, TEST_YEAR)
    except ZohoAPIError as e:
        err(f"get_monthly: {e}")
        return

    raw_check = result.get("_raw", result)
    if isinstance(raw_check, list) and raw_check:
        raw_check = raw_check[0]
    if isinstance(raw_check, dict) and raw_check.get("response") == "failure":
        skip(f"Attendance API: '{raw_check.get('msg','?')}' — vedi sezione 6")
        return

    day_list = result.get("dayList", {})
    eNo      = result.get("userDetails", {}).get("eNo", EMPLOYEE_ID)

    if not day_list:
        skip("dayList vuoto")
        return

    from zoho_vertical_sdk.attendance import PeopleAttendanceAPI
    absent = PeopleAttendanceAPI.absent_days_from_daylist(day_list)

    if not absent:
        ok(f"Nessun giorno assente in {TEST_MONTH:02d}/{TEST_YEAR} – nulla da registrare")
        return

    records = [{"date": d, "check_in": "09:00", "check_out": "18:00"} for d in absent]

    ok(f"eNo rilevato: {eNo}")
    ok(f"Giorni da registrare: {len(records)}")
    info("Primi 3 record che verrebbero inviati:")
    for r in records[:3]:
        ftime = time_to_seconds(r["check_in"])
        ttime = time_to_seconds(r["check_out"])
        print(f"    • {r['date']}  ftime={ftime}  ttime={ttime}")

    info("Per eseguire realmente rimuovi il commento:")
    print(f"    # client.attendance.add_bulk('{eNo}', records)")
    ok("DRY RUN completato – nessuna modifica effettuata")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 10 – Timesheet – lista job                                        #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_10_timesheet_jobs():
    section(10, "Timesheet – lista job disponibili (get_jobs)")

    if client is None:
        skip("Client non inizializzato")
        return

    try:
        jobs = client.timesheet.get_jobs()
        ok(f"Job trovati: {len(jobs)}")
        for j in jobs[:10]:
            job_id   = j.get("jobId",   j.get("id",   "?"))
            job_name = j.get("jobName", j.get("name", "?"))
            client_n = j.get("clientName", "")
            print(f"    • [{job_id}]  {job_name:35}  {client_n}")
        if len(jobs) > 10:
            info(f"  … e altri {len(jobs) - 10} job")
        if jobs:
            info(f"Usa ZOHO_JOB_ID={jobs[0].get('jobId','?')} nel .env per i test successivi")
    except ZohoAPIError as e:
        err(f"get_jobs: {e}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 11 – Timesheet – log del mese (timesheetDispAction)               #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_11_timesheet_get():
    section(11, f"Timesheet – log {TEST_MONTH:02d}/{TEST_YEAR} (timesheetDispAction)")

    if client is None:
        skip("Client non inizializzato")
        return

    try:
        result = client.attendance.get_monthly(EMPLOYEE_ID, TEST_MONTH, TEST_YEAR)
        eNo    = result.get("userDetails", {}).get("eNo", EMPLOYEE_ID) \
                 if isinstance(result, dict) else EMPLOYEE_ID

        first = date(TEST_YEAR, TEST_MONTH, 1).strftime("%d/%m/%Y")
        import calendar
        last_day = calendar.monthrange(TEST_YEAR, TEST_MONTH)[1]
        last  = date(TEST_YEAR, TEST_MONTH, last_day).strftime("%d/%m/%Y")

        ts = client.timesheet.get(eNo, first, last)
        ok(f"Risposta ricevuta")

        ts_arr = ts.get("tsArr", [])
        if ts_arr:
            warn(f"Timesheet già inviato ({len(ts_arr)} voci) – non puoi reinviarlo")
        else:
            ok("Timesheet non ancora inviato per questo mese")

        leave_json = ts.get("leaveData", {}).get("leaveJson", {})
        if leave_json:
            info(f"Giorni di ferie/permesso: {len(leave_json)}")
            for d, v in list(leave_json.items())[:3]:
                print(f"    • {d}  tipo={v.get('type','?')}")
        else:
            info("Nessun giorno di ferie nel periodo")

    except ZohoAPIError as e:
        err(f"timesheet.get: {e}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 12 – Timesheet – build_log_params                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_12_timesheet_build_log_params():
    section(12, f"Timesheet – build_log_params {TEST_MONTH:02d}/{TEST_YEAR}")

    if not JOB_ID:
        skip("ZOHO_JOB_ID non impostato nel .env – imposta il job ID dalla sezione 10")
        return

    import calendar
    num_days = calendar.monthrange(TEST_YEAR, TEST_MONTH)[1]

    # Simula 2 giorni di ferie
    fake_leave = {
        date(TEST_YEAR, TEST_MONTH, 1).strftime("%Y-%m-%d"),
        date(TEST_YEAR, TEST_MONTH, 2).strftime("%Y-%m-%d"),
    }

    log_params = PeopleTimesheetAPI.build_log_params(
        year=TEST_YEAR,
        month=TEST_MONTH,
        job_id=JOB_ID,
        hours_per_day="8",
        bill_status="0",
        skip_dates=fake_leave,
    )

    entries = log_params["logParams"]
    ok(f"logParams costruiti: {len(entries)} voci  (su {num_days} giorni, 2 saltati)")

    info("Primi 3 entry:")
    for e in entries[:3]:
        print(f"    • {e}")

    info("Ultimo entry:")
    print(f"    • {entries[-1]}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 13 – Timesheet – invia (sendTimesheet) – DRY RUN                 #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_13_timesheet_add():
    section(13, "Timesheet – invia timesheet (sendTimesheet) – DRY RUN")

    if client is None:
        skip("Client non inizializzato")
        return

    if not JOB_ID:
        skip("ZOHO_JOB_ID non impostato – imposta il job ID dalla sezione 10")
        return

    import calendar
    first    = date(TEST_YEAR, TEST_MONTH, 1).strftime("%d/%m/%Y")
    last_day = calendar.monthrange(TEST_YEAR, TEST_MONTH)[1]
    last     = date(TEST_YEAR, TEST_MONTH, last_day).strftime("%d/%m/%Y")

    log_params = PeopleTimesheetAPI.build_log_params(
        year=TEST_YEAR, month=TEST_MONTH, job_id=JOB_ID
    )

    # Tenta di ottenere l'eNo dal profilo presenze; se l'API ritorna Permission
    # Denied usa direttamente EMPLOYEE_ID come fallback.
    eNo = EMPLOYEE_ID
    try:
        result = client.attendance.get_monthly(EMPLOYEE_ID, TEST_MONTH, TEST_YEAR)
        eNo = result.get("userDetails", {}).get("eNo") or EMPLOYEE_ID
        if eNo == EMPLOYEE_ID:
            warn("userDetails.eNo non disponibile – uso EMPLOYEE_ID come eNo")
    except ZohoAPIError as e:
        err(f"get_monthly: {e}")
        return

    ok(f"eNo: {eNo}")
    ok(f"Periodo: {first} → {last}")
    ok(f"Voci logParams: {len(log_params['logParams'])}")

    info("Payload che verrebbe inviato (DRY RUN):")
    print(f"    userErecNo = {eNo}")
    print(f"    fromDate   = {first}")
    print(f"    toDate     = {last}")
    print(f"    logParams  = {json.dumps(log_params)[:200]} …")
    print(f"    endpoint   = POST /people/api/timetracker/addtimesheet")

    info("Per eseguire realmente rimuovi il commento:")
    print(f"    # client.timesheet.add('{eNo}', '{first}', '{last}', log_params)")
    ok("DRY RUN completato – nessuna modifica effettuata")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 14 – Timesheet – flusso completo (add_monthly) – DRY RUN         #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_14_timesheet_add_monthly():
    section(14, "Timesheet – flusso completo add_monthly – DRY RUN")

    if client is None:
        skip("Client non inizializzato")
        return

    if not JOB_ID:
        skip("ZOHO_JOB_ID non impostato – imposta il job ID dalla sezione 10")
        return

    info("Il flusso add_monthly fa automaticamente:")
    print("    1. GET timetracker/getTimesheetLog  → verifica se già inviato")
    print("    2. Legge leaveData per saltare giorni di ferie")
    print("    3. Costruisce logParams per tutti i giorni lavorativi")
    print("    4. POST timetracker/addtimesheet  → invia")
    print()
    info("Equivale al vecchio flusso:")
    print("    timesheetDispAction() → build logParams → sendTimesheet()")
    print()

    eNo = EMPLOYEE_ID
    try:
        result = client.attendance.get_monthly(EMPLOYEE_ID, TEST_MONTH, TEST_YEAR)
        eNo = result.get("userDetails", {}).get("eNo") or EMPLOYEE_ID
        if eNo == EMPLOYEE_ID:
            warn("userDetails.eNo non disponibile – uso EMPLOYEE_ID come eNo")
    except ZohoAPIError as e:
        err(f"get_monthly: {e}")
        return

    info(f"Parametri che verrebbero usati:")
    print(f"    employee_id  = {eNo}")
    print(f"    month        = {TEST_MONTH}")
    print(f"    year         = {TEST_YEAR}")
    print(f"    job_id       = {JOB_ID}")
    print(f"    hours_per_day = 8")
    print()
    info("Per eseguire realmente rimuovi il commento:")
    print(f"    # client.timesheet.add_monthly('{eNo}', {TEST_MONTH}, {TEST_YEAR}, '{JOB_ID}')")
    ok("DRY RUN completato – nessuna modifica effettuata")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 15 – Gestione errori People API                                   #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_15_error_handling():
    section(15, "Gestione errori People API")

    if client is None:
        skip("Client non inizializzato")
        return

    # ── ValueError: timesheet già inviato ──────────────────────────────────
    info("Simulazione ValueError (timesheet già inviato):")
    try:
        raise ValueError("Timesheet 03/2025 già inviato (3 voci presenti).")
    except ValueError as e:
        ok(f"ValueError catturata: {e}")

    # ── ZohoAPIError su endpoint inesistente ───────────────────────────────
    info("Test ZohoAPIError su endpoint inesistente:")
    try:
        client.attendance.get_range("INVALID_EMP", "01/01/2025", "31/01/2025")
    except ZohoAPIError as e:
        ok(f"ZohoAPIError: HTTP {e.status_code} – {e.message}")
    except Exception as e:
        info(f"Eccezione generica: {type(e).__name__} – {e}")

    # ── Gestione risposta vuota dai job ───────────────────────────────────
    info("Gestione lista job vuota (response senza chiavi note):")
    from zoho_vertical_sdk.timesheet import PeopleTimesheetAPI as TS
    # Simula risposta sconosciuta
    fake_api = type("FakeAPI", (), {"get": lambda self, p, params=None: {"unknown_key": []}})()
    ts = PeopleTimesheetAPI.__new__(PeopleTimesheetAPI)
    ts._client = fake_api
    jobs = ts.get_jobs()
    assert jobs == [], f"Atteso [], ottenuto {jobs}"
    ok("Lista job vuota gestita correttamente (nessun crash)")

    # ── build_log_params con tutti i giorni saltati ────────────────────────
    info("build_log_params con tutti i giorni saltati:")
    import calendar
    all_days = {
        date(TEST_YEAR, TEST_MONTH, n).strftime("%Y-%m-%d")
        for n in range(1, calendar.monthrange(TEST_YEAR, TEST_MONTH)[1] + 1)
    }
    result = PeopleTimesheetAPI.build_log_params(
        TEST_YEAR, TEST_MONTH, job_id="J1", skip_dates=all_days
    )
    assert result["logParams"] == []
    ok("logParams vuoto quando tutti i giorni sono saltati")


# ═══════════════════════════════════════════════════════════════════════════ #
#  Runner                                                                    #
# ═══════════════════════════════════════════════════════════════════════════ #

ALL_EXAMPLES = {
    1:  ("Helpers orario",                    example_01_time_helpers),
    2:  ("Employee – lista",                  example_02_employee_list),
    3:  ("Employee – cerca (findEmploy)",     example_03_employee_search),
    4:  ("Employee – dettaglio",              example_04_employee_get),
    5:  ("Employee – albero organizzativo",   example_05_employee_tree),
    6:  ("Attendance – presenze mensili",     example_06_attendance_monthly),
    7:  ("Attendance – giorni assenti",       example_07_attendance_absent_days),
    8:  ("Attendance – add singolo (dry)",    example_08_attendance_add),
    9:  ("Attendance – bulk (dry)",           example_09_attendance_bulk),
    10: ("Timesheet – lista job",             example_10_timesheet_jobs),
    11: ("Timesheet – log mese",              example_11_timesheet_get),
    12: ("Timesheet – build_log_params",      example_12_timesheet_build_log_params),
    13: ("Timesheet – add (dry)",             example_13_timesheet_add),
    14: ("Timesheet – add_monthly (dry)",     example_14_timesheet_add_monthly),
    15: ("Gestione errori",                   example_15_error_handling),
}

SECTION_ALIASES = {
    "employee": [2, 3, 4, 5],
    "attend":   [6, 7, 8, 9],
    "time":     [10, 11, 12, 13, 14],
    "errors":   [15],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Zoho People SDK – Examples & Tests (attendance / timesheet / employee)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi:
  python examples_test2.py                    # tutto
  python examples_test2.py --section 1        # solo helpers orario
  python examples_test2.py --section employee # sezioni 2-5
  python examples_test2.py --section attend   # sezioni 6-9
  python examples_test2.py --section time     # sezioni 10-14
  python examples_test2.py --list             # mostra sezioni
        """,
    )
    parser.add_argument("--section", "-s", default=None)
    parser.add_argument("--list", "-l", action="store_true")
    return parser.parse_args()


def resolve_sections(section_arg):
    if section_arg is None:
        return sorted(ALL_EXAMPLES.keys())
    alias = section_arg.lower()
    if alias in SECTION_ALIASES:
        return SECTION_ALIASES[alias]
    if section_arg.isdigit():
        num = int(section_arg)
        if num in ALL_EXAMPLES:
            return [num]
        print(f"❌  Sezione {num} non trovata. Usa --list.")
        sys.exit(1)
    print(f"❌  '{section_arg}' non riconosciuto. Usa --list.")
    sys.exit(1)


def main():
    global client

    args = parse_args()

    if args.list:
        title("📋  Sezioni disponibili")
        for num, (desc, _) in ALL_EXAMPLES.items():
            print(f"  {num:2d}.  {desc}")
        print()
        print("  Alias: employee, attend, time, errors")
        return

    title("🧪  Zoho People SDK – Attendance / Timesheet / Employee")
    print(f"  Dipendente   : {EMPLOYEE_ID}")
    print(f"  Mese/Anno    : {TEST_MONTH:02d}/{TEST_YEAR}")
    print(f"  Job ID       : {JOB_ID or '(non impostato)'}")

    sections_to_run = resolve_sections(args.section)

    # Inizializza client (salta la sezione 1 che non richiede HTTP)
    if any(s > 1 for s in sections_to_run):
        if all([CLIENT_ID, CLIENT_SECRET]):
            try:
                manager = ZohoAuthManager(
                    client_id=CLIENT_ID,
                    client_secret=CLIENT_SECRET,
                    data_centre=os.getenv("ZOHO_DATA_CENTRE", "US"),
                )
                client = manager.get_client()
                ok("Client autenticato via ZohoAuthManager")
            except Exception as e:
                err(f"AuthManager: {e}")
                sys.exit(1)
        else:
            err("Imposta ZOHO_CLIENT_ID e ZOHO_CLIENT_SECRET nel .env")
            sys.exit(1)

    for num in sections_to_run:
        _, fn = ALL_EXAMPLES[num]
        fn()

    title("✅  Completato")
    print(f"  Sezioni eseguite: {len(sections_to_run)}")
    print()


if __name__ == "__main__":
    main()
