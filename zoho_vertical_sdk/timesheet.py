"""
PeopleTimesheetAPI  –  Zoho People Timesheet REST API
======================================================

Sostituisce il vecchio approccio cookie/CSRF con OAuth 2.0.

Mapping vecchio → nuovo
-----------------------
timesheetDispAction()   →  client.timesheet.get(emp_id, from_date, to_date)
sendTimesheet()         →  client.timesheet.add(emp_id, from_date, to_date, log_params)
build_log_params()      →  PeopleTimesheetAPI.build_log_params()  (helper statico)

Vecchi endpoint web (richiedono cookie + CSRF):
    POST /timesheetDispAction.zp   mode=getTimesheet
    POST /timesheet.zp             mode=addWeekTimesheet

Nuovi endpoint REST (richiedono solo OAuth token):
    GET  /people/api/timetracker/getjobs
    GET  /people/api/timetracker/getTimesheetLog
    POST /people/api/timetracker/addtimesheet

Scope OAuth richiesti: ZohoPeople.timetracker.ALL

Riferimento API:
    https://www.zoho.com/people/api-integration/timetracker.html
"""

from __future__ import annotations

import calendar
import json
from datetime import date
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class PeopleTimesheetAPI:
    """
    Wrapper per le API Zoho People Timetracker.

    Usato tramite:
        client.timesheet.get(emp_id, from_date, to_date)
        client.timesheet.add(emp_id, from_date, to_date, log_params)
        client.timesheet.get_monthly(emp_id, month, year)
        client.timesheet.add_monthly(emp_id, month, year, job_id, hours)

    Parameters
    ----------
    client : ZohoVerticalClient
        Istanza del client autenticato con OAuth.
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Jobs
    # ------------------------------------------------------------------

    def get_jobs(
        self,
        employee_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recupera la lista dei job disponibili per il timetracker.

        Endpoint: GET /people/api/timetracker/getjobs

        Parameters
        ----------
        employee_id : str, optional
            Filtra i job assegnati a un dipendente specifico.
            Se omesso restituisce tutti i job attivi dell'account.

        Returns
        -------
        list[dict]
            Lista di job, ognuno con almeno:
            ``{"jobId": "...", "jobName": "...", "clientName": "..."}``

        Example
        -------
        >>> jobs = client.timesheet.get_jobs()
        >>> for j in jobs:
        ...     print(j["jobId"], j["jobName"])
        """
        params: Dict[str, Any] = {}
        if employee_id:
            params["userId"] = employee_id

        data = self._client.get("timetracker/getjobs", params=params or None)
        # La risposta può essere {"response": {"result": [...]}} oppure {"data": [...]}
        if "response" in data:
            result = data["response"].get("result", [])
        else:
            result = data.get("data", data.get("jobs", []))
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Lettura timesheet
    # ------------------------------------------------------------------

    def get(
        self,
        employee_id: str,
        from_date: str,
        to_date: str,
        date_format: str = "dd/MM/yyyy",
    ) -> Dict[str, Any]:
        """
        Recupera il log timesheet per un intervallo di date.

        Equivale a timesheetDispAction() del vecchio script
        (POST /timesheetDispAction.zp con mode=getTimesheet).

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (eNo) — es. "P-000042".
        from_date, to_date : str
            Date nel formato specificato da date_format (default dd/MM/yyyy).

        Returns
        -------
        dict
            Struttura con chiavi:
            ``{"tsArr": [...], "leaveData": {"leaveJson": {...}}, ...}``

            - tsArr vuoto   → timesheet non ancora inviato (OK per procedere)
            - tsArr non vuoto → già inviato (equivale al check del vecchio script)
        """
        # Prova prima senza userId (utente OAuth corrente),
        # poi con userId esplicito se la prima risposta è vuota/errore.
        base_params = {
            "fromDate":   from_date,
            "toDate":     to_date,
            "dateFormat": date_format,
        }
        for params in [base_params, {**base_params, "userId": employee_id}]:
            try:
                result = self._client.get("timetracker/getTimesheetLog", params=params)
            except Exception:
                continue
            if isinstance(result, dict) and result.get("response") != "failure":
                return result
        return result  # type: ignore[return-value]

    def get_monthly(
        self,
        employee_id: str,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        Recupera il timesheet per un intero mese.

        Equivale a timesheetDispAction() con le date calcolate automaticamente.

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (eNo).
        month : int
            Mese (1-12).
        year : int
            Anno a 4 cifre.
        """
        first_day = date(year, month, 1)
        last_day  = date(year, month, calendar.monthrange(year, month)[1])
        fmt       = "%d/%m/%Y"
        return self.get(
            employee_id=employee_id,
            from_date=first_day.strftime(fmt),
            to_date=last_day.strftime(fmt),
        )

    # ------------------------------------------------------------------
    # Invio timesheet
    # ------------------------------------------------------------------

    def add(
        self,
        employee_id: str,
        from_date: str,
        to_date: str,
        log_params: Dict[str, Any],
        date_format: str = "dd/MM/yyyy",
    ) -> Dict[str, Any]:
        """
        Invia il timesheet per un intervallo di date.

        Equivale a sendTimesheet() del vecchio script
        (POST /timesheet.zp con mode=addWeekTimesheet).

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (eNo).
        from_date, to_date : str
            Inizio e fine periodo nel formato dd/MM/yyyy.
        log_params : dict
            Struttura logParams costruita da build_log_params().
            Esempio::

                {
                    "logParams": [
                        {"day1": "8", "jobId": "123456", "billStatus": "0"},
                        {"day2": "8", "jobId": "123456", "billStatus": "0"},
                        ...
                    ]
                }

        Returns
        -------
        dict  con chiave "message" e "status".
        """
        payload = {
            "userErecNo": employee_id,
            "fromDate":   from_date,
            "toDate":     to_date,
            "dateFormat": date_format,
            "logParams":  json.dumps(log_params),
        }
        return self._client.form_post("timetracker/addtimesheet", data=payload)

    def add_monthly(
        self,
        employee_id: str,
        month: int,
        year: int,
        job_id: str,
        hours_per_day: str = "8",
        bill_status: str = "0",
    ) -> Dict[str, Any]:
        """
        Invia il timesheet per un intero mese (wrapper ad alto livello).

        Controlla automaticamente se il timesheet è già stato inviato.
        Salta i giorni in ferie/permesso (leaveData).

        Equivale al flusso completo:
            timesheetDispAction() → build logParams → sendTimesheet()

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (eNo).
        month : int
            Mese (1-12).
        year : int
            Anno.
        job_id : str
            ID del progetto/job Zoho People — es. "123456789".
        hours_per_day : str
            Ore da registrare per ogni giorno — es. "8".
        bill_status : str
            Stato di fatturazione — "0" = non fatturabile (default).

        Returns
        -------
        dict  Risposta dell'API add(), oppure {"already_sent": True} se già inviato.

        Raises
        ------
        ValueError
            Se il timesheet è già stato inviato per il mese indicato.
        """
        first_day = date(year, month, 1)
        last_day  = date(year, month, calendar.monthrange(year, month)[1])
        fmt       = "%d/%m/%Y"
        from_date = first_day.strftime(fmt)
        to_date   = last_day.strftime(fmt)

        # 1. Recupera log esistente (equivale a timesheetDispAction)
        ts_data = self.get(employee_id, from_date, to_date)

        # 2. Controlla se già inviato (equivale al check su tsArr del vecchio script)
        if ts_data.get("tsArr") and len(ts_data["tsArr"]) > 0:
            raise ValueError(
                f"Timesheet {month:02d}/{year} già inviato "
                f"({len(ts_data['tsArr'])} voci presenti)."
            )

        # 3. Costruisci logParams (equivale al for loop nel vecchio script)
        leave_dates = set(ts_data.get("leaveData", {}).get("leaveJson", {}).keys())
        log_params  = self.build_log_params(
            year=year,
            month=month,
            job_id=job_id,
            hours_per_day=hours_per_day,
            bill_status=bill_status,
            skip_dates=leave_dates,
        )

        # 4. Invia
        return self.add(employee_id, from_date, to_date, log_params)

    # ------------------------------------------------------------------
    # Helper: costruisce logParams
    # ------------------------------------------------------------------

    @staticmethod
    def build_log_params(
        year: int,
        month: int,
        job_id: str,
        hours_per_day: str = "8",
        bill_status: str = "0",
        skip_dates: Optional[set] = None,
        skip_weekends: bool = True,
    ) -> Dict[str, Any]:
        """
        Costruisce la struttura logParams richiesta dall'API addtimesheet.

        Equivale al loop for del vecchio timesheetDispAction()::

            logParams = {"logParams": []}
            for n in range(1, num_days + 1):
                if y in res['leaveData']['leaveJson'].keys():
                    continue
                params[f"day{n}"] = config['timesheet']
                params["jobId"]   = config['jobId']
                params["billStatus"] = '0'
                logParams["logParams"].append(params)

        Parameters
        ----------
        year, month : int
            Anno e mese di riferimento.
        job_id : str
            ID job/progetto Zoho.
        hours_per_day : str
            Ore da loggare per ogni giorno — es. "8".
        bill_status : str
            "0" = non fatturabile, "1" = fatturabile.
        skip_dates : set[str], optional
            Set di date in formato YYYY-MM-DD da saltare (giorni di ferie/permesso).
        skip_weekends : bool
            Se True (default) salta sabati e domeniche automaticamente.

        Returns
        -------
        dict
            ``{"logParams": [{"day1": "8", "jobId": "...", "billStatus": "0"}, ...]}``
        """
        if skip_dates is None:
            skip_dates = set()

        num_days   = calendar.monthrange(year, month)[1]
        log_params: List[Dict[str, str]] = []

        for n in range(1, num_days + 1):
            d       = date(year, month, n)
            day_iso = d.strftime("%Y-%m-%d")
            if skip_weekends and d.weekday() >= 5:  # 5=sabato, 6=domenica
                continue
            if day_iso in skip_dates:
                continue
            entry = {
                f"day{n}":    hours_per_day,
                "jobId":      job_id,
                "billStatus": bill_status,
            }
            log_params.append(entry)

        return {"logParams": log_params}
