"""
PeopleAttendanceAPI  –  Zoho People Attendance v3 REST API
===========================================================

Supporta due modalità di accesso:

1. **Endpoint interno** (preferito, stessa API usata dal vecchio script):
   GET  https://people.zoho.com/{org}/AttendanceViewAction.zp
        ?userId=...&dateRange=dd/MM/yyyy,dd/MM/yyyy&dateFormat=dd/MM/yyyy
   POST https://people.zoho.com/{org}/AttendanceAction.zp
        mode=bulkAttendReg&erecno=...&fdate=...&ftime=...&ttime=...&dataObj=...

   Richiede: ZOHO_SERVICE_URL=/relewanthrm/zp (per estrarre l'org name)

2. **REST API v3** (fallback):
   GET  /people/api/v3/attendance/getUserReport  (empId, sdate, edate in dd-MMM-yyyy)
   GET  /people/api/v3/attendance/getAttendanceEntries  (empId, date in dd-MMM-yyyy)
   POST /people/api/v3/attendance/checkIn  (empId, checkInTime HH:mm, date dd-MMM-yyyy)
   POST /people/api/v3/attendance/checkOut (empId, checkOutTime HH:mm, date dd-MMM-yyyy)
   POST /people/api/v3/attendance/addEntries  (bulk)

   Scope OAuth: ZohoPeople.attendance.ALL

Formato data v3: dd-MMM-yyyy (es. 20-Mar-2026)
Formato orario:  HH:mm (24h)

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


def _to_zoho_date(date_str: str) -> str:
    """
    Converte una data dal formato dd/MM/yyyy al formato v3 dd-MMM-yyyy.

    Examples
    --------
    >>> _to_zoho_date("15/03/2026")  # → "15-Mar-2026"
    """
    d = datetime.strptime(date_str, "%d/%m/%Y")
    return d.strftime("%d-%b-%Y")


def _date_to_zoho(d: date) -> str:
    """Converte un oggetto date nel formato v3 dd-MMM-yyyy."""
    return d.strftime("%d-%b-%Y")


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
    Normalizza la risposta di ``v3/attendance/getUserReport`` (REST API v3).

    La risposta reale è un **flat dict** keyed by date (yyyy-MM-dd)::

        {
          "2026-03-21": {
            "Status": "Fine settimana",
            "TotalHours": "00:00",
            "ShiftStartTime": "09:00",
            "ShiftEndTime": "18:00",
            ...
          },
          "2026-03-20": { ... }
        }

    Restituisce il formato interno canonico con dayList keyed by dd/MM/yyyy.
    """
    if not isinstance(raw, dict):
        return {"dayList": {}, "userDetails": {}, "_source": "rest", "_raw": raw}

    # Errore esplicito
    if "response" in raw and raw.get("response") == "failure":
        return {"dayList": {}, "userDetails": {}, "_source": "rest", "_raw": raw}

    # Formato flat dict (chiavi yyyy-MM-dd → entry giorno)
    day_list: Dict[str, Any] = {}
    for date_key, day in raw.items():
        if not isinstance(day, dict):
            continue
        # Riconosce solo entry con almeno "Status" o "TotalHours"
        if "Status" not in day and "TotalHours" not in day:
            continue
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
        "userDetails": {},   # getUserReport non include eNo
        "_source":     "rest",
        "_raw":        raw,
    }


# ---------------------------------------------------------------------------
# API class
# ---------------------------------------------------------------------------

class PeopleAttendanceAPI:
    """
    Wrapper per le API Zoho People Attendance v3.

    Prova prima l'endpoint interno (se ZOHO_SERVICE_URL è configurato),
    poi cade back sulla REST API v3 pubblica.

    Usato tramite:
        client.attendance.get_monthly(employee_id, month, year)
        client.attendance.get_range(employee_id, from_date, to_date)
        client.attendance.get_entries(employee_id, day)
        client.attendance.check_in(employee_id, date_str, check_in_time)
        client.attendance.check_out(employee_id, date_str, check_out_time)
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
        url       = f"{base}/AttendanceViewAction.zp"
        dr        = f"{first_day.strftime('%d/%m/%Y')},{last_day.strftime('%d/%m/%Y')}"

        for params in [
            {"dateRange": dr, "dateFormat": "dd/MM/yyyy"},
            {"userId": employee_id, "dateRange": dr, "dateFormat": "dd/MM/yyyy"},
        ]:
            try:
                raw = self._client.get_absolute(url, params=params)
            except Exception:
                continue

            if isinstance(raw, dict):
                if raw.get("error") or raw.get("response") == "failure":
                    continue
                if "dayList" in raw:
                    return _normalize_web_response(raw)

        return None

    # ------------------------------------------------------------------
    # Lettura presenze – REST API v3 (getUserReport)
    # ------------------------------------------------------------------

    def _get_monthly_rest(
        self,
        employee_id: str,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Recupera presenze via REST API v3 attendance/getUserReport.

        Prova prima senza empId (utente corrente del token OAuth),
        poi con empId=employee_id se la prima chiamata non restituisce dati.
        """
        first_day = date(year, month, 1)
        last_day  = date(year, month, calendar.monthrange(year, month)[1])
        sdate     = _date_to_zoho(first_day)
        edate     = _date_to_zoho(last_day)

        sdate = first_day.strftime("%d/%m/%Y")
        edate = last_day.strftime("%d/%m/%Y")

        base_params = self._client.people_params({
            "sdate":      sdate,
            "edate":      edate,
            "dateFormat": "dd/MM/yyyy",
        })

        # 1. Senza empId → restituisce dati dell'utente autenticato
        raw = self._client.get("attendance/getUserReport", params=base_params)
        result = _normalize_user_report(raw)
        if result.get("dayList"):
            return result

        # 2. Con empId esplicito
        params_with_id = {**base_params, "empId": employee_id}
        raw2   = self._client.get("attendance/getUserReport", params=params_with_id)
        return _normalize_user_report(raw2)

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
        poi la REST API v3 pubblica getUserReport.

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
            if isinstance(raw, dict) and raw.get("response") == "failure":
                pass
            elif day_list or isinstance(raw, dict):
                return result

        # 2. Fallback REST API v3
        return self._get_monthly_rest(employee_id, month, year)

    def get_range(
        self,
        employee_id: str,
        from_date: str,
        to_date: str,
    ) -> Dict[str, Any]:
        """
        Recupera le presenze per un intervallo di date via REST API v3.

        Parameters
        ----------
        from_date, to_date : str
            Date nel formato dd/MM/yyyy (vengono convertite in dd-MMM-yyyy per v3).
        """
        params = self._client.people_params({
            "empId":      employee_id,
            "sdate":      from_date,
            "edate":      to_date,
            "dateFormat": "dd/MM/yyyy",
        })
        raw = self._client.get("attendance/getUserReport", params=params)
        return _normalize_user_report(raw)

    def get_entries(
        self,
        employee_id: str,
        day: str,
    ) -> Any:
        """
        Recupera le singole timbrature per un giorno.

        Endpoint: GET /people/api/v3/attendance/getAttendanceEntries

        Parameters
        ----------
        day : str
            Data in formato dd/MM/yyyy.
        """
        params = self._client.people_params({
            "empId": employee_id,
            "date":  day,
        })
        return self._client.get("attendance/getEntries", params=params)

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
            Numero record dipendente (eNo).
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
    # Interfaccia pubblica – invio singolo
    # ------------------------------------------------------------------

    def check_in(
        self,
        employee_id: str,
        date_str: str,
        check_in_time: str = "09:00",
    ) -> Dict[str, Any]:
        """
        Registra la timbratura di ingresso via REST API v3.

        Endpoint: POST /people/api/v3/attendance/checkIn

        Parameters
        ----------
        employee_id : str
            ID dipendente (empId).
        date_str : str
            Data in formato dd/MM/yyyy.
        check_in_time : str
            Orario HH:MM (es. "09:00").
        """
        payload = self._client.people_params({
            "empId":        employee_id,
            "checkInTime":  check_in_time,
            "date":         date_str,
        })
        return self._client.form_post("attendance/checkIn", data=payload)

    def check_out(
        self,
        employee_id: str,
        date_str: str,
        check_out_time: str = "18:00",
    ) -> Dict[str, Any]:
        """
        Registra la timbratura di uscita via REST API v3.

        Endpoint: POST /people/api/v3/attendance/checkOut

        Parameters
        ----------
        employee_id : str
            ID dipendente (empId).
        date_str : str
            Data in formato dd/MM/yyyy.
        check_out_time : str
            Orario HH:MM (es. "18:00").
        """
        payload = self._client.people_params({
            "empId":         employee_id,
            "checkOutTime":  check_out_time,
            "date":          date_str,
        })
        return self._client.form_post("attendance/checkOut", data=payload)

    def add(
        self,
        employee_id: str,
        date_str: str,
        check_in: str = "09:00",
        check_out: str = "18:00",
    ) -> Dict[str, Any]:
        """
        Registra la presenza per un singolo giorno.

        Prova prima l'endpoint interno (se ZOHO_SERVICE_URL è configurato),
        poi la REST API v3 (addEntries).

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

        # 2. Fallback REST API
        payload = self._client.people_params({
            "empId":    employee_id,
            "checkIn":  check_in,
            "checkOut": check_out,
            "date":     date_str,
        })
        return self._client.form_post("attendance/addEntries", data=payload)

    def get_specific_entry(self, attendance_id: str) -> Dict[str, Any]:
        """
        Recupera una specifica timbratura.

        Endpoint: GET /attendance/getSpecificEntry

        Parameters
        ----------
        attendance_id : str
            ID univoco della timbratura.
        """
        return self._client.get("attendance/getSpecificEntry",
                                params={"attendanceId": attendance_id})

    def update_entry(
        self,
        attendance_id: str,
        check_in: str,
        check_out: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Modifica una timbratura esistente.

        Endpoint: PUT /attendance/updateEntry

        Parameters
        ----------
        attendance_id : str
            ID univoco della timbratura.
        check_in : str
            Nuovo orario di ingresso HH:MM.
        check_out : str
            Nuovo orario di uscita HH:MM.
        reason : str, optional
            Motivo della modifica.
        """
        payload: Dict[str, Any] = {
            "attendanceId": attendance_id,
            "checkIn":      check_in,
            "checkOut":     check_out,
        }
        if reason:
            payload["reason"] = reason
        return self._client.put("attendance/updateEntry", json=payload)

    def delete_specific_entry(self, attendance_id: str) -> Dict[str, Any]:
        """
        Elimina una specifica timbratura.

        Endpoint: DELETE /attendance/deleteSpecificEntry

        Parameters
        ----------
        attendance_id : str
            ID univoco della timbratura.
        """
        return self._client.delete("attendance/deleteSpecificEntry",
                                   params={"attendanceId": attendance_id})

    def delete_entries(
        self,
        user_id: str,
        from_date: str,
        to_date: str,
    ) -> Dict[str, Any]:
        """
        Elimina tutte le timbrature di un dipendente in un intervallo di date.

        Endpoint: DELETE /attendance/deleteEntries

        Parameters
        ----------
        user_id : str
            Email o ID dipendente.
        from_date : str
            Data inizio nel formato dd-MMM-yyyy (es. "01-Mar-2026").
        to_date : str
            Data fine nel formato dd-MMM-yyyy (es. "31-Mar-2026").
        """
        params: Dict[str, Any] = {
            "userId":   user_id,
            "fromDate": _to_zoho_date(from_date),
            "toDate":   _to_zoho_date(to_date),
        }
        return self._client.delete("attendance/deleteEntries", params=params)

    def punch_in(
        self,
        employee_id: str,
        check_in_time: str,
        location: Optional[str] = None,
        latitude: Optional[str] = None,
        longitude: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registra una timbratura di ingresso (punch-in).

        Endpoint: POST /attendance/punchIn

        Parameters
        ----------
        employee_id : str
            ID dipendente.
        check_in_time : str
            Orario di ingresso HH:mm.
        location : str, optional
            Nome della posizione.
        latitude : str, optional
            Latitudine GPS.
        longitude : str, optional
            Longitudine GPS.
        """
        payload: Dict[str, Any] = {
            "employeeId":   employee_id,
            "checkInTime":  check_in_time,
        }
        if location:
            payload["location"] = location
        if latitude:
            payload["latitude"] = latitude
        if longitude:
            payload["longitude"] = longitude
        return self._client.form_post("attendance/punchIn", data=payload)

    def file_upload(
        self,
        file_path: str,
        employee_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Carica un file CSV/XLS con le presenze.

        Endpoint: POST /attendance/fileUpload

        Parameters
        ----------
        file_path : str
            Percorso del file CSV o XLS da caricare.
        employee_id : str, optional
            ID dipendente (se il file riguarda un singolo dipendente).
        """
        data: Dict[str, Any] = {}
        if employee_id:
            data["employeeId"] = employee_id
        with open(file_path, "rb") as f:
            return self._client.upload("attendance/fileUpload",
                                       files={"file": f},
                                       data=data or None)

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

    # Status che indicano "giorno non lavorativo" — da saltare
    _SKIP_STATUSES = frozenset({
        # Inglese
        "Weekend", "Holiday", "Leave", "Present",
        # Italiano
        "Fine settimana", "Festività", "Ferie", "Presente",
        "Permesso retribuito", "Malattia",
    })

    # Suffissi che indicano una festività (es. "San Giuseppe(Vacanza)")
    _HOLIDAY_SUFFIXES = ("(Vacanza)", "(Holiday)", "(Festività)")

    # Status che indicano "assente" (da registrare)
    _ABSENT_STATUSES = frozenset({
        "Absent", "Assente",
    })

    @staticmethod
    def _is_holiday(status: str) -> bool:
        """True se lo status indica una festività (es. 'San Giuseppe(Vacanza)')."""
        return any(status.endswith(suf) for suf in PeopleAttendanceAPI._HOLIDAY_SUFFIXES)

    @staticmethod
    def absent_days_from_daylist(day_list: Dict[str, Any]) -> List[str]:
        """
        Restituisce le date assenti/vuote dal dayList di get_monthly().

        Un giorno è "assente" se:
        - status è "Absent" / "Assente" E tHrs == "00:00", oppure
        - status è "" (non ancora registrato) e tHrs == "00:00"

        Vengono esclusi i giorni Weekend, Holiday, festività (pattern
        ``NomeFestività(Vacanza)``), Leave (anche in italiano).

        Returns
        -------
        list[str]  Date in formato dd/MM/yyyy (dal campo ldate).
        """
        skip   = PeopleAttendanceAPI._SKIP_STATUSES
        absent = PeopleAttendanceAPI._ABSENT_STATUSES
        result = []

        for date_key, day in day_list.items():
            status = day.get("status", day.get("Status", ""))
            t_hrs  = day.get("tHrs",   day.get("TotalHours", "00:00"))
            ldate  = day.get("ldate",  date_key)

            if status in skip:
                continue
            if PeopleAttendanceAPI._is_holiday(status):
                continue
            # Assente solo se non ha ore registrate
            if (status in absent or status == "") and t_hrs == "00:00":
                result.append(ldate)

        return result
