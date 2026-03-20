"""
PeopleAttendanceAPI  –  Zoho People Attendance
===============================================

Supporta due modalità di accesso:

1. **Endpoint interno** (preferito, stessa API usata dal vecchio script):
   GET  https://people.zoho.com/{org}/AttendanceViewAction.zp
        ?userId=...&dateRange=dd/MM/yyyy,dd/MM/yyyy&dateFormat=dd/MM/yyyy
   POST https://people.zoho.com/{org}/AttendanceAction.zp
        mode=bulkAttendReg&erecno=...&fdate=...&ftime=...&ttime=...&dataObj=...

   Richiede: ZOHO_SERVICE_URL=/relewanthrm/zp (per estrarre l'org name)

2. **REST API ufficiale** (fallback):
   GET  /people/api/attendance/getUserReport  (sdate, edate, empId)
   POST /people/api/attendance  (empId, checkIn, checkOut)

   Scope OAuth: ZohoPeople.attendance.ALL

Formato risposta endpoint interno (dayList con chiavi numeriche 0-based):
    {
      "dayList": {
        "0": {"ldate": "01/07/2024", "status": "Absent", "tHrs": "00:00",
               "shift": {"fTime": 540, "tTime": 1080}, ...},
        "1": {"ldate": "02/07/2024", "status": "", ...},
        "5": {"ldate": "06/07/2024", "status": "Weekend", ...}
      },
      "userDetails": {"eNo": "439215000007867001", "eId": "IMP085", "fName": "..."}
    }
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
# Helpers URL endpoint interno
# ---------------------------------------------------------------------------

def _org_from_service_url(service_url: str) -> str:
    """
    Estrae il nome organizzazione da ZOHO_SERVICE_URL.

    Esempi:
        "/relewanthrm/zp" → "relewanthrm"
        "relewanthrm"      → "relewanthrm"
    """
    return service_url.strip("/").split("/")[0]


# ---------------------------------------------------------------------------
# Normalizzazione risposte
# ---------------------------------------------------------------------------

def _normalize_web_response(raw: Any) -> Dict[str, Any]:
    """
    Normalizza la risposta dell'endpoint interno AttendanceViewAction.zp.

    La risposta ha ``dayList`` con chiavi numeriche stringa ("0", "1", ...).
    Ogni entry ha ``ldate`` (dd/MM/yyyy), ``status``, ``tHrs``, ``shift``.

    Restituisce il formato interno canonico:
        {
          "dayList": {"01/07/2024": {"status": "Absent", "tHrs": "00:00", ...}},
          "userDetails": {"eNo": "...", "eId": "...", "fName": "..."},
          "_source": "web",
          "_raw": <risposta originale>
        }
    """
    if not isinstance(raw, dict):
        return {"dayList": {}, "userDetails": {}, "_source": "web", "_raw": raw}

    user_raw  = raw.get("userDetails", {})
    day_raw   = raw.get("dayList", {})

    # Ri-indicizza dayList da chiavi numeriche a ldate (dd/MM/yyyy)
    day_list: Dict[str, Any] = {}
    for _idx, day in day_raw.items():
        key = day.get("ldate") or day.get("attDate") or str(_idx)
        if key:
            day_list[key] = day

    return {
        "dayList":     day_list,
        "userDetails": user_raw,
        "_source":     "web",
        "_raw":        raw,
    }


def _normalize_user_report(raw: Any) -> Dict[str, Any]:
    """
    Normalizza la risposta di ``attendance/getUserReport`` (REST API).

    Risposta getUserReport::

        {
          "result": [
            {
              "attendanceDetails": {"2026-03-01": {"Status": "Present", "TotalHours": "08:30"}},
              "employeeDetails": {"erecno": "439215000007867001"}
            }
          ]
        }

    Restituisce il formato interno canonico con dayList keyed by dd/MM/yyyy.
    """
    if isinstance(raw, dict) and "result" in raw:
        records = raw["result"]
        if not records:
            return {"dayList": {}, "userDetails": {}, "_source": "rest", "_raw": raw}
        first    = records[0]
        employee = first.get("employeeDetails", {})
        attend   = first.get("attendanceDetails", {})

        day_list: Dict[str, Any] = {}
        for date_key, day in attend.items():
            try:
                d = datetime.strptime(date_key, "%Y-%m-%d")
                fmt_key = d.strftime("%d/%m/%Y")
            except ValueError:
                fmt_key = date_key

            day_list[fmt_key] = {
                "status": day.get("Status", ""),
                "tHrs":   day.get("TotalHours", "00:00"),
                "ldate":  fmt_key,
                **day,
            }

        return {
            "dayList":     day_list,
            "userDetails": {"eNo": employee.get("erecno", ""), **employee},
            "_source":     "rest",
            "_raw":        raw,
        }

    return {"dayList": {}, "userDetails": {}, "_source": "rest", "_raw": raw}


# ---------------------------------------------------------------------------
# API class
# ---------------------------------------------------------------------------

class PeopleAttendanceAPI:
    """
    Wrapper per le API Zoho People Attendance.

    Prova prima l'endpoint interno (se ZOHO_SERVICE_URL è configurato),
    poi cade back sulla REST API pubblica.

    Usato tramite:
        client.attendance.get_monthly(employee_id, month, year)
        client.attendance.add(employee_id, date_str, "09:00", "18:00")
        client.attendance.add_bulk(employee_id, records)
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # URL helpers endpoint interno
    # ------------------------------------------------------------------

    def _web_base_url(self) -> Optional[str]:
        """
        Restituisce l'URL base dell'endpoint interno se SERVICE_URL è configurato.
        Es: https://people.zoho.com/relewanthrm
        """
        if not self._client.service_url:
            return None
        org = _org_from_service_url(self._client.service_url)
        return f"{self._client.api_domain}/{org}"

    # ------------------------------------------------------------------
    # Lettura presenze – endpoint interno (attendanceViewAction)
    # ------------------------------------------------------------------

    def _get_monthly_web(
        self,
        employee_id: str,
        month: int,
        year: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Recupera presenze via endpoint interno AttendanceViewAction.zp.
        Restituisce None se SERVICE_URL non è configurato.
        """
        base = self._web_base_url()
        if not base:
            return None

        first_day = date(year, month, 1)
        last_day  = date(year, month, calendar.monthrange(year, month)[1])
        url = f"{base}/AttendanceViewAction.zp"
        params = {
            "userId":     employee_id,
            "dateRange":  f"{first_day.strftime('%d/%m/%Y')},{last_day.strftime('%d/%m/%Y')}",
            "dateFormat": "dd/MM/yyyy",
        }
        raw = self._client.get_absolute(url, params=params)
        return _normalize_web_response(raw)

    # ------------------------------------------------------------------
    # Lettura presenze – REST API (getUserReport)
    # ------------------------------------------------------------------

    def _get_monthly_rest(
        self,
        employee_id: str,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """Recupera presenze via REST API attendance/getUserReport."""
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

    # ------------------------------------------------------------------
    # Interfaccia pubblica – lettura
    # ------------------------------------------------------------------

    def get_monthly(
        self,
        employee_id: str,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Recupera il riepilogo presenze mensile.

        Prova prima l'endpoint interno (se ZOHO_SERVICE_URL è configurato),
        poi la REST API pubblica getUserReport.

        Returns
        -------
        dict
            ``{"dayList": {"01/03/2026": {"status": "Absent", "tHrs": "00:00",
               "ldate": "01/03/2026", "shift": {...}, ...}, ...},
               "userDetails": {"eNo": "...", ...},
               "_source": "web"|"rest"}``
        """
        # 1. Prova endpoint interno
        result = self._get_monthly_web(employee_id, month, year)
        if result is not None:
            day_list = result.get("dayList", {})
            raw      = result.get("_raw", {})
            # Controlla se è una risposta di errore
            if isinstance(raw, dict) and raw.get("response") == "failure":
                pass  # lascia cadere sulla REST API
            elif day_list or isinstance(raw, dict):
                return result

        # 2. Fallback REST API
        return self._get_monthly_rest(employee_id, month, year)

    def get_range(
        self,
        employee_id: str,
        from_date: str,
        to_date: str,
        date_format: str = "dd/MM/yyyy",
    ) -> Dict[str, Any]:
        """
        Recupera le presenze per un intervallo di date via REST API.

        Parameters
        ----------
        from_date, to_date : str
            Date nel formato dd/MM/yyyy.
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
        Recupera le singole timbrature per un giorno.

        Endpoint: GET /people/api/attendance/getAttendanceEntries
        """
        params = self._client.people_params({
            "empId":      employee_id,
            "date":       day,
            "dateFormat": date_format,
        })
        return self._client.get("attendance/getAttendanceEntries", params=params)

    # ------------------------------------------------------------------
    # Invio presenze – endpoint interno (AttendanceAction.zp)
    # ------------------------------------------------------------------

    def _add_web(
        self,
        employee_no: str,
        date_str: str,
        check_in: str,
        check_out: str,
    ) -> Optional[Dict[str, Any]]:
        """
        Registra presenza via endpoint interno AttendanceAction.zp.

        Parameters
        ----------
        employee_no : str
            Numero record dipendente (eNo) — es. "439215000007867001".
        date_str : str
            Data in formato dd/MM/yyyy.
        check_in, check_out : str
            Orari HH:MM.
        """
        base = self._web_base_url()
        if not base:
            return None

        ftime = time_to_seconds(check_in)
        ttime = time_to_seconds(check_out)

        data_obj = {
            date_str: {
                "fromDate": date_str,
                "toDate":   date_str,
                "ftime":    ftime,
                "ttime":    ttime,
            }
        }

        url     = f"{base}/AttendanceAction.zp"
        payload = {
            "mode":            "bulkAttendReg",
            "erecno":          employee_no,
            "fdate":           date_str,
            "ftime":           str(ftime),
            "ttime":           str(ttime),
            "isFromEntryPage": "true",
            "dataObj":         json.dumps({"dataObj": data_obj}),
        }

        return self._client.form_post_absolute(url, data=payload)

    # ------------------------------------------------------------------
    # Interfaccia pubblica – invio
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
        Registra la presenza per un singolo giorno.

        Prova prima l'endpoint interno (se ZOHO_SERVICE_URL è configurato)
        con il formato erecno/ftime/ttime del vecchio script, poi la REST API.

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (eNo) o empId Zoho People.
        date_str : str
            Data in formato dd/MM/yyyy — es. "15/03/2026".
        check_in, check_out : str
            Orari HH:MM.
        """
        # 1. Prova endpoint interno
        result = self._add_web(employee_id, date_str, check_in, check_out)
        if result is not None:
            return result

        # 2. Fallback REST API (empId + checkIn/checkOut in datetime format)
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
            Numero record dipendente (eNo).
        records : list[dict]
            Lista di dict con chiavi: date, check_in, check_out.
            Esempio::

                [
                    {"date": "03/03/2026", "check_in": "09:00", "check_out": "18:00"},
                    {"date": "04/03/2026", "check_in": "09:00", "check_out": "18:00"},
                ]
        """
        results = []
        for rec in records:
            result = self.add(
                employee_id=employee_id,
                date_str=rec["date"],
                check_in=rec.get("check_in", "09:00"),
                check_out=rec.get("check_out", "18:00"),
            )
            results.append({"date": rec["date"], "result": result})
        return results

    # ------------------------------------------------------------------
    # Helper: giorni assenti dal dayList
    # ------------------------------------------------------------------

    @staticmethod
    def absent_days_from_daylist(day_list: Dict[str, Any]) -> List[str]:
        """
        Restituisce le date assenti/vuote dal dayList di get_monthly().

        Un giorno è "assente" se:
        - status == "Absent" (esplicitamente segnato assente), oppure
        - status == "" (non ancora registrato, non weekend, non festivo)
          E tHrs == "00:00"

        Vengono esclusi automaticamente i giorni con status "Weekend" o "Holiday".

        Returns
        -------
        list[str]  Date in formato dd/MM/yyyy (dal campo ldate).
        """
        absent = []
        for date_key, day in day_list.items():
            status = day.get("status", "")
            t_hrs  = day.get("tHrs", "00:00")
            ldate  = day.get("ldate", date_key)

            if status in ("Weekend", "Holiday", "Leave"):
                continue
            if status == "Absent" or (status == "" and t_hrs == "00:00"):
                absent.append(ldate)
        return absent
