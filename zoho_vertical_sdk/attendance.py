"""
PeopleAttendanceAPI  –  Zoho People Attendance REST API
========================================================

Endpoint ufficiali Zoho People Attendance (OAuth 2.0):

  GET  /people/api/attendance/getUserReport
       → report mensile presenze con TotalHours, Status, ecc.
       Params: sdate, edate, empId (o emailId o mapId), dateFormat

  GET  /people/api/attendance/getAttendanceEntries
       → singole timbrature per un giorno
       Params: date, erecno (o mapId o emailId o empId), dateFormat

  POST /people/api/attendance
       → registra check-in / check-out
       Params: empId (o emailId o mapId), checkIn, checkOut, dateFormat
               (formato checkIn/checkOut: dd/MM/yyyy HH:mm:ss)

Scope OAuth richiesti: ZohoPeople.attendance.ALL

Riferimento API:
    https://www.zoho.com/people/api/userreport.html
    https://www.zoho.com/people/api/attendance-entries.html
    https://www.zoho.com/people/api/attendance-checkin-checkout.html
"""

from __future__ import annotations

import calendar
import json
from datetime import date, datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


# ---------------------------------------------------------------------------
# Helpers orario
# ---------------------------------------------------------------------------

def time_to_seconds(t: str) -> int:
    """
    Converte un orario HH:MM (o HH:MM:SS) in secondi dalla mezzanotte.

    Examples
    --------
    >>> time_to_seconds("9:00")   # → 32400
    >>> time_to_seconds("17:30")  # → 63000
    """
    parts = t.split(":")
    h = int(parts[0])
    m = int(parts[1]) if len(parts) > 1 else 0
    s = int(parts[2]) if len(parts) > 2 else 0
    return h * 3600 + m * 60 + s


def seconds_to_time(seconds: int) -> str:
    """Converte secondi dalla mezzanotte in stringa HH:MM."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    return f"{h:02d}:{m:02d}"


# ---------------------------------------------------------------------------
# Normalizzazione risposta getUserReport → formato dayList
# ---------------------------------------------------------------------------

def _normalize_user_report(raw: Any) -> Dict[str, Any]:
    """
    Converte la risposta di ``attendance/getUserReport`` nel formato
    interno ``{"dayList": {...}, "userDetails": {"eNo": "..."}}``
    usato dal resto dell'SDK.

    getUserReport risponde con::

        {
          "result": [
            {
              "attendanceDetails": {
                "2026-03-01": {
                  "Status": "Present",
                  "TotalHours": "08:30",
                  ...
                }
              },
              "employeeDetails": {
                "erecno": "439215000007867001",
                ...
              }
            }
          ]
        }
    """
    if isinstance(raw, dict) and "result" in raw:
        records = raw["result"]
        if not records:
            return {"dayList": {}, "userDetails": {}}
        first = records[0]
        employee = first.get("employeeDetails", {})
        attendance = first.get("attendanceDetails", {})

        day_list: Dict[str, Any] = {}
        for date_key, day in attendance.items():
            # Converti yyyy-MM-dd → dd/MM/yyyy se necessario
            try:
                d = datetime.strptime(date_key, "%Y-%m-%d")
                fmt_key = d.strftime("%d/%m/%Y")
            except ValueError:
                fmt_key = date_key

            day_list[fmt_key] = {
                "status": day.get("Status", ""),
                "tHrs":   day.get("TotalHours", "00:00"),
                "ldate":  fmt_key,
                # conserva tutti i campi originali
                **{k: v for k, v in day.items()},
            }

        return {
            "dayList":     day_list,
            "userDetails": {"eNo": employee.get("erecno", ""), **employee},
            "_raw":        raw,
        }

    # Risposta non riconosciuta → restituisci com'è
    return {"dayList": {}, "userDetails": {}, "_raw": raw}


# ---------------------------------------------------------------------------
# API class
# ---------------------------------------------------------------------------

class PeopleAttendanceAPI:
    """
    Wrapper per le API Zoho People Attendance.

    Usato tramite:
        client.attendance.get_monthly(employee_id, month, year)
        client.attendance.add(employee_id, date_str, "09:00", "18:00")
        client.attendance.add_bulk(employee_id, records)

    Parameters
    ----------
    client : ZohoVerticalClient
        Istanza del client autenticato con OAuth.
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Lettura presenze
    # ------------------------------------------------------------------

    def get_monthly(
        self,
        employee_id: str,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Recupera il riepilogo presenze mensile via ``getUserReport``.

        Endpoint: GET /people/api/attendance/getUserReport

        Returns
        -------
        dict
            ``{"dayList": {"01/03/2026": {"status": "Present", "tHrs": "08:30", ...}, ...},
               "userDetails": {"eNo": "...", ...}}``
        """
        first_day = date(year, month, 1)
        last_day  = date(year, month, calendar.monthrange(year, month)[1])

        params = self._client.people_params({
            "empId":      employee_id,
            "sdate":      first_day.strftime("%d/%m/%Y"),
            "edate":      last_day.strftime("%d/%m/%Y"),
            "dateFormat": "dd/MM/yyyy",
        })
        raw = self._client.get("attendance/getUserReport", params=params)
        return _normalize_user_report(raw)

    def get_range(
        self,
        employee_id: str,
        from_date: str,
        to_date: str,
        date_format: str = "dd/MM/yyyy",
    ) -> Dict[str, Any]:
        """
        Recupera le presenze per un intervallo di date.

        Endpoint: GET /people/api/attendance/getUserReport

        Parameters
        ----------
        from_date, to_date : str
            Date nel formato specificato da date_format (default dd/MM/yyyy).
        """
        params = self._client.people_params({
            "empId":      employee_id,
            "sdate":      from_date,
            "edate":      to_date,
            "dateFormat": date_format,
        })
        raw = self._client.get("attendance/getUserReport", params=params)
        return _normalize_user_report(raw)

    def get_entries(
        self,
        employee_id: str,
        day: str,
        date_format: str = "dd/MM/yyyy",
    ) -> Any:
        """
        Recupera le singole timbrature per un giorno specifico.

        Endpoint: GET /people/api/attendance/getAttendanceEntries

        Parameters
        ----------
        day : str
            Data nel formato date_format (default dd/MM/yyyy).
        """
        params = self._client.people_params({
            "empId":      employee_id,
            "date":       day,
            "dateFormat": date_format,
        })
        return self._client.get("attendance/getAttendanceEntries", params=params)

    # ------------------------------------------------------------------
    # Invio presenze
    # ------------------------------------------------------------------

    def add(
        self,
        employee_id: str,
        date_str: str,
        check_in: str = "09:00",
        check_out: str = "18:00",
        date_format: str = "dd/MM/yyyy",
    ) -> Dict[str, Any]:
        """
        Registra la presenza per un singolo giorno (check-in / check-out).

        Endpoint: POST /people/api/attendance

        Parameters
        ----------
        employee_id : str
            ID dipendente Zoho People (empId).
        date_str : str
            Data nel formato dd/MM/yyyy — es. "15/03/2026".
        check_in : str
            Orario entrata HH:MM — es. "09:00".
        check_out : str
            Orario uscita HH:MM — es. "18:00".

        Returns
        -------
        dict  con chiave "message" e "status".
        """
        # L'API vuole checkIn/checkOut in formato: dd/MM/yyyy HH:mm:ss
        check_in_dt  = f"{date_str} {check_in}:00"
        check_out_dt = f"{date_str} {check_out}:00"

        payload = self._client.people_params({
            "empId":      employee_id,
            "checkIn":    check_in_dt,
            "checkOut":   check_out_dt,
            "dateFormat": date_format,
        })

        return self._client.form_post("attendance", data=payload)

    def add_bulk(
        self,
        employee_id: str,
        records: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Registra le presenze per più giorni in sequenza.

        Parameters
        ----------
        employee_id : str
            ID dipendente Zoho People (empId).
        records : list[dict]
            Lista di dict con chiavi: date, check_in, check_out.
            Esempio::

                [
                    {"date": "03/03/2026", "check_in": "09:00", "check_out": "18:00"},
                    {"date": "04/03/2026", "check_in": "09:00", "check_out": "18:00"},
                ]

        Returns
        -------
        list[dict]  Un risultato per ogni record inviato.
        """
        results = []
        for rec in records:
            result = self.add(
                employee_id=employee_id,
                date_str=rec["date"],
                check_in=rec.get("check_in", "09:00"),
                check_out=rec.get("check_out", "18:00"),
            )
            results.append({
                "date":   rec["date"],
                "result": result,
            })
        return results

    # ------------------------------------------------------------------
    # Helper: costruisce la lista giorni assenti dal dayList
    # ------------------------------------------------------------------

    @staticmethod
    def absent_days_from_daylist(day_list: Dict[str, Any]) -> List[str]:
        """
        Restituisce le date assenti/vuote dal dayList restituito da get_monthly().

        Returns
        -------
        list[str]  Lista di date in formato dd/MM/yyyy.
        """
        absent = []
        for date_key, day in day_list.items():
            status = day.get("status", day.get("Status", ""))
            t_hrs  = day.get("tHrs", day.get("TotalHours", "00:00"))
            if (status in ("Absent", "")) and t_hrs == "00:00":
                ldate = day.get("ldate", date_key)
                absent.append(ldate)
        return absent
