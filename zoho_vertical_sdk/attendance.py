"""
PeopleAttendanceAPI  –  Zoho People Attendance REST API
========================================================

Sostituisce il vecchio approccio cookie/CSRF con OAuth 2.0.

Vecchio codice (web scraping):
    POST https://people.zoho.com/{service_url}/AttendanceAction.zp
    data = 'mode=bulkAttendReg&conreqcsr={CSRF_TOKEN}&erecno={eNo}&...'

Nuovo approccio (REST API ufficiale):
    POST https://people.zoho.com/people/api/attendance
    Authorization: Zoho-oauthtoken {access_token}
    Content-Type: application/x-www-form-urlencoded
    erecno={eNo}&fdate={date}&ftime={sec_from}&ttime={sec_to}

Scope OAuth richiesti: ZohoPeople.attendance.ALL

Riferimento API:
    https://www.zoho.com/people/api-integration/attendance.html
"""

from __future__ import annotations

import calendar
import json
import urllib.parse
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

    Equivale alla funzione get_sec() del vecchio script.

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
# API class
# ---------------------------------------------------------------------------

class PeopleAttendanceAPI:
    """
    Wrapper per le API Zoho People Attendance.

    Usato tramite:
        client.attendance.get_monthly(employee_id, month, year)
        client.attendance.add(employee_id, date_str, "09:00", "18:00")
        client.attendance.add_bulk(employee_id, records)
        client.attendance.get_employee_details()

    Parameters
    ----------
    client : ZohoVerticalClient
        Istanza del client autenticato con OAuth.
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Dettagli dipendente
    # ------------------------------------------------------------------

    def get_employee_details(self, employee_id: str = "self") -> Dict[str, Any]:
        """
        Recupera i dettagli del dipendente, incluso il numero record (eNo).

        Equivale alla chiamata attendanceViewAction() del vecchio script
        per ottenere eNo = dl['userDetails']['eNo'].

        Parameters
        ----------
        employee_id : str
            ID dipendente Zoho People o "self" per l'utente corrente.

        Returns
        -------
        dict  con chiavi: eNo, empId, name, department, ...
        """
        params = {"userId": employee_id}
        return self._client.get("forms/json/P_EmployeeView/getRecord", params=params)

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
        Recupera il riepilogo presenze mensile (dayList + userDetails).

        Equivale alla chiamata attendanceViewAction() del vecchio script
        per ottenere dl['dayList'].

        Returns
        -------
        dict
            ``{"dayList": {"01/03/2025": {"status": "Present", "tHrs": "08:00", ...}, ...},
               "userDetails": {"eNo": "...", ...}}``
        """
        first_day = date(year, month, 1)
        last_day  = date(year, month, calendar.monthrange(year, month)[1])

        params = {
            "userId":    employee_id,
            "dateRange": f"{first_day.strftime('%d/%m/%Y')},{last_day.strftime('%d/%m/%Y')}",
            "dateFormat": "dd/MM/yyyy",
        }
        return self._client.get("attendance", params=params)

    def get_range(
        self,
        employee_id: str,
        from_date: str,
        to_date: str,
        date_format: str = "dd/MM/yyyy",
    ) -> Dict[str, Any]:
        """
        Recupera le presenze per un intervallo di date.

        Parameters
        ----------
        from_date, to_date : str
            Date nel formato specificato da date_format (default dd/MM/yyyy).
        """
        params = {
            "userId":    employee_id,
            "dateRange": f"{from_date},{to_date}",
            "dateFormat": date_format,
        }
        return self._client.get("attendance", params=params)

    # ------------------------------------------------------------------
    # Invio presenze
    # ------------------------------------------------------------------

    def add(
        self,
        employee_record_no: str,
        date_str: str,
        check_in: str = "09:00",
        check_out: str = "18:00",
        date_format: str = "dd/MM/yyyy",
    ) -> Dict[str, Any]:
        """
        Registra la presenza per un singolo giorno.

        Sostituisce la chiamata POST ad AttendanceAction.zp del vecchio script.

        Parameters
        ----------
        employee_record_no : str
            Numero record dipendente (eNo) — es. "P-000042".
        date_str : str
            Data nel formato dd/MM/yyyy — es. "15/03/2025".
        check_in : str
            Orario entrata HH:MM — es. "09:00".
        check_out : str
            Orario uscita HH:MM — es. "18:00".

        Returns
        -------
        dict  con chiave "message" e "status".
        """
        # La Zoho People Attendance API accetta secondi dalla mezzanotte
        # come nel vecchio get_sec() — mantenuta compatibilità
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

        payload = {
            "erecno":          employee_record_no,
            "fdate":           date_str,
            "ftime":           str(ftime),
            "ttime":           str(ttime),
            "isFromEntryPage": "true",
            "dataObj":         json.dumps({"dataObj": data_obj}),
        }

        return self._client.form_post("attendance", data=payload)

    def add_bulk(
        self,
        employee_record_no: str,
        records: List[Dict[str, str]],
    ) -> List[Dict[str, Any]]:
        """
        Registra le presenze per più giorni in sequenza.

        Sostituisce il ciclo for di sendAttendance() del vecchio script.

        Parameters
        ----------
        employee_record_no : str
            Numero record dipendente (eNo).
        records : list[dict]
            Lista di dict con chiavi: date, check_in, check_out.
            Esempio::

                [
                    {"date": "03/03/2025", "check_in": "09:00", "check_out": "18:00"},
                    {"date": "04/03/2025", "check_in": "09:00", "check_out": "18:00"},
                ]

        Returns
        -------
        list[dict]  Un risultato per ogni record inviato.
        """
        results = []
        for rec in records:
            result = self.add(
                employee_record_no=employee_record_no,
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

        Equivale al filtro del vecchio sendAttendance():
            if status == 'Absent' or status == '' and tHrs == "00:00"

        Returns
        -------
        list[str]  Lista di date in formato dd/MM/yyyy.
        """
        absent = []
        for date_key, day in day_list.items():
            status = day.get("status", "")
            t_hrs  = day.get("tHrs", "00:00")
            if (status in ("Absent", "")) and t_hrs == "00:00":
                # Normalizza la data in dd/MM/yyyy (il vecchio usava ldate)
                ldate = day.get("ldate", date_key)
                absent.append(ldate)
        return absent
