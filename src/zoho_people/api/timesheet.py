"""
Timesheet API – gestione timesheet e time log in Zoho People.

Endpoint coperti:
  GET  /api/timetracker/gettimesheet           – lista timesheet
  GET  /api/timetracker/gettimesheetdetails    – dettaglio timesheet
  POST /api/timetracker/createtimesheet        – crea timesheet
  POST /api/timetracker/modifytimesheet        – modifica / invia per approvazione
  POST /api/timetracker/deletetimesheet        – elimina timesheet
  POST /api/timetracker/approvetimesheet       – approva / rifiuta timesheet
  GET  /api/timetracker/gettimelogdetails      – dettaglio time log
  POST /api/timetracker/addtimelog             – aggiungi time log
  POST /api/timetracker/edittimelog            – modifica time log
  POST /api/timetracker/deletetimelog          – elimina time log
  GET  /api/timetracker/getpayrollreport       – report payroll
  GET  /api/timetracker/gettimetrackersettings – impostazioni generali

Scope richiesto: ZOHOPEOPLE.timetracker.ALL
Rate limit: 20–50 req/min a seconda dell'endpoint.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..client import ZohoPeopleClient


class TimesheetAPI:
    """
    Gestione completa di timesheet e time log Zoho People.

    Example
    -------
    >>> # Lista timesheet approvati di aprile
    >>> sheets = client.timesheet.list(
    ...     user="mario.rossi@azienda.it",
    ...     from_date="01-Apr-2026",
    ...     to_date="30-Apr-2026",
    ...     approval_status="approved",
    ... )

    >>> # Crea un timesheet settimanale
    >>> result = client.timesheet.create(
    ...     user="mario.rossi@azienda.it",
    ...     name="Settimana 17/2026",
    ...     from_date="20-04-2026",
    ...     to_date="26-04-2026",
    ...     send_for_approval=True,
    ... )

    >>> # Aggiungi ore a un timesheet
    >>> client.timesheet.add_timelog(
    ...     user="mario.rossi@azienda.it",
    ...     work_date="2026-04-25",
    ...     hours="08:00",
    ...     job_name="Sviluppo SDK",
    ...     billing_status="Billable",
    ... )
    """

    def __init__(self, client: "ZohoPeopleClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Timesheet – lettura
    # ------------------------------------------------------------------

    def list(
        self,
        user: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        approval_status: str = "all",
        employee_status: str = "users",
        date_format: Optional[str] = None,
        s_index: int = 0,
        limit: int = 200,
    ) -> list[dict]:
        """
        Recupera la lista dei timesheet.

        Parameters
        ----------
        user : str
            Email, Employee ID, erecno o ``"all"`` per tutti.
        from_date : str, optional
            Data inizio (nel formato aziendale o in ``date_format``).
        to_date : str, optional
            Data fine.
        approval_status : str
            ``all`` | ``draft`` | ``pending`` | ``approved`` | ``rejected``
        employee_status : str
            ``users`` | ``nonusers`` | ``usersandnonusers`` | ``logindisabled``
        s_index : int
            Indice di inizio per la paginazione (default 0).
        limit : int
            Numero di record per pagina (max 200).

        Returns
        -------
        list[dict]
            Lista di timesheet con campi: recordId, timesheetName, status,
            totalHours, billableHours, fromDate, toDate, …
        """
        params: dict[str, Any] = {
            "user":           user,
            "approvalStatus": approval_status,
            "employeeStatus": employee_status,
            "sIndex":         s_index,
            "limit":          min(limit, 200),
        }
        if from_date:
            params["fromDate"] = from_date
        if to_date:
            params["toDate"] = to_date
        if date_format:
            params["dateFormat"] = date_format

        result = self._client.get("timetracker/gettimesheet", params=params)
        return result.get("result", []) if isinstance(result, dict) else []

    def get_all(self, user: str, **kwargs) -> list[dict]:
        """
        Auto-paginazione: recupera TUTTI i timesheet dell'utente.
        """
        all_sheets: list[dict] = []
        index = 0
        limit = 200

        while True:
            batch = self.list(user=user, s_index=index, limit=limit, **kwargs)
            if not batch:
                break
            all_sheets.extend(batch)
            if len(batch) < limit:
                break
            index += limit

        return all_sheets

    def get_detail(self, timesheet_id: str) -> dict:
        """
        Recupera il dettaglio di un timesheet (time log inclusi).

        Parameters
        ----------
        timesheet_id : str
            ID del timesheet (``recordId`` dalla lista).

        Returns
        -------
        dict
            Dettaglio completo con time log, progetti, clienti.
        """
        params = {"timesheetId": timesheet_id}
        result = self._client.get("timetracker/gettimesheetdetails", params=params)
        return result.get("result", result) if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Timesheet – scrittura
    # ------------------------------------------------------------------

    def create(
        self,
        user: str,
        name: str,
        from_date: str,
        to_date: str,
        description: Optional[str] = None,
        billable_status: str = "all",
        job_id: str = "all",
        project_id: str = "all",
        client_id: str = "all",
        send_for_approval: bool = False,
        date_format: Optional[str] = None,
    ) -> dict:
        """
        Crea un nuovo timesheet.

        Parameters
        ----------
        user : str
            Email o Employee ID del dipendente.
        name : str
            Nome del timesheet (es. ``"Settimana 17/2026"``).
        from_date : str
            Data inizio.
        to_date : str
            Data fine.
        description : str, optional
            Descrizione del timesheet.
        billable_status : str
            ``all`` | ``Billable`` | ``Non Billable``
        send_for_approval : bool
            Se True, invia subito per approvazione.

        Returns
        -------
        dict
            ``{"timesheetId": [...], "message": "..."}``
        """
        params: dict[str, Any] = {
            "user":              user,
            "timesheetName":     name,
            "fromDate":          from_date,
            "toDate":            to_date,
            "billableStatus":    billable_status,
            "jobId":             job_id,
            "projectId":         project_id,
            "clientId":          client_id,
            "sendforApproval":   str(send_for_approval).lower(),
        }
        if description:
            params["description"] = description
        if date_format:
            params["dateFormat"] = date_format

        result = self._client.post("timetracker/createtimesheet", data=params)
        return result.get("result", result) if isinstance(result, dict) else {}

    def modify(
        self,
        timesheet_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        send_for_approval: Optional[bool] = None,
    ) -> dict:
        """
        Modifica un timesheet esistente o lo invia per approvazione.

        Per ri-sottomettere un timesheet rifiutato usare ``send_for_approval=True``.

        Returns
        -------
        dict
            ``{"timesheetId": "...", "message": "..."}``
        """
        params: dict[str, Any] = {"timesheetId": timesheet_id}
        if name:
            params["timesheetName"] = name
        if description is not None:
            params["description"] = description
        if send_for_approval is not None:
            params["sendforApproval"] = str(send_for_approval).lower()

        result = self._client.post("timetracker/modifytimesheet", data=params)
        return result.get("result", result) if isinstance(result, dict) else {}

    def delete(self, timesheet_id: str) -> dict:
        """
        Elimina un timesheet.

        Returns
        -------
        dict
            Risposta di conferma.
        """
        params = {"timesheetId": timesheet_id}
        result = self._client.post("timetracker/deletetimesheet", data=params)
        return result.get("result", result) if isinstance(result, dict) else {}

    def approve(
        self,
        timesheet_id: str,
        approval_status: str = "approved",
        time_logs: Optional[dict] = None,
        comments: Optional[str] = None,
        all_levels: bool = False,
    ) -> dict:
        """
        Approva o rifiuta un timesheet (e opzionalmente i suoi time log).

        Parameters
        ----------
        timesheet_id : str
            ID del timesheet.
        approval_status : str
            ``"approved"`` | ``"rejected"``
        time_logs : dict, optional
            Dict ``{timelog_id: "approved"|"rejected"}`` per approvazione parziale.
            Es: ``{"469505000000272225": "approved", "469505000000272083": "rejected"}``
        comments : str, optional
            Commento per l'approvazione/rifiuto.
        all_levels : bool
            Se True, approva a tutti i livelli gerarchici.

        Returns
        -------
        dict
            ``{"timesheetId": "...", "message": "..."}``
        """
        import json as _json

        params: dict[str, Any] = {
            "timesheetId":    timesheet_id,
            "approvalStatus": approval_status,
            "isAllLevelApprove": str(all_levels).lower(),
        }
        if time_logs:
            params["timeLogs"] = _json.dumps(time_logs)
        if comments:
            params["comments"] = comments

        result = self._client.post("timetracker/approvetimesheet", data=params)
        return result.get("result", result) if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Time Log – lettura
    # ------------------------------------------------------------------

    def get_timelog(self, timelog_id: str) -> dict:
        """
        Recupera il dettaglio di un singolo time log.

        Returns
        -------
        dict
            Dettaglio con: workDate, hours, jobName, billingStatus, …
        """
        params = {"timeLogId": timelog_id}
        result = self._client.get("timetracker/gettimelogdetails", params=params)
        items = result.get("result", []) if isinstance(result, dict) else []
        return items[0] if items else {}

    # ------------------------------------------------------------------
    # Time Log – scrittura
    # ------------------------------------------------------------------

    def add_timelog(
        self,
        user: str,
        work_date: str,
        hours: str,
        job_id: Optional[str] = None,
        job_name: Optional[str] = None,
        billing_status: str = "Billable",
        work_item: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Aggiunge un time log a un timesheet.

        Almeno uno tra ``job_id`` e ``job_name`` è obbligatorio.

        Parameters
        ----------
        user : str
            Email o Employee ID del dipendente.
        work_date : str
            Data di lavoro nel formato ``YYYY-MM-DD``.
        hours : str
            Ore lavorate nel formato ``HH:MM`` (es. ``"08:00"``).
        job_id : str, optional
            ID del job/attività.
        job_name : str, optional
            Nome del job/attività (alternativa a job_id).
        billing_status : str
            ``"Billable"`` | ``"Non Billable"``
        work_item : str, optional
            Sottoattività / work item.
        description : str, optional
            Descrizione delle ore lavorate.

        Returns
        -------
        dict
            ``{"timeLogId": "...", "message": "..."}``
        """
        params: dict[str, Any] = {
            "user":          user,
            "workDate":      work_date,
            "hours":         hours,
            "billingStatus": billing_status,
        }
        if job_id:
            params["jobId"] = job_id
        if job_name:
            params["jobName"] = job_name
        if work_item:
            params["workItem"] = work_item
        if description:
            params["description"] = description

        result = self._client.post("timetracker/addtimelog", data=params)
        items = result.get("result", []) if isinstance(result, dict) else []
        return items[0] if items else {}

    def edit_timelog(
        self,
        timelog_id: str,
        hours: Optional[str] = None,
        work_date: Optional[str] = None,
        billing_status: Optional[str] = None,
        description: Optional[str] = None,
    ) -> dict:
        """
        Modifica un time log esistente.

        Returns
        -------
        dict
            Risposta di conferma.
        """
        params: dict[str, Any] = {"timeLogId": timelog_id}
        if hours:
            params["hours"] = hours
        if work_date:
            params["workDate"] = work_date
        if billing_status:
            params["billingStatus"] = billing_status
        if description is not None:
            params["description"] = description

        result = self._client.post("timetracker/edittimelog", data=params)
        return result.get("result", result) if isinstance(result, dict) else {}

    def delete_timelog(self, timelog_id: str) -> dict:
        """
        Elimina un time log.

        Returns
        -------
        dict
            Risposta di conferma.
        """
        params = {"timeLogId": timelog_id}
        result = self._client.post("timetracker/deletetimelog", data=params)
        return result.get("result", result) if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Report e impostazioni
    # ------------------------------------------------------------------

    def get_payroll_report(
        self,
        user: str,
        from_date: str,
        to_date: str,
        date_format: Optional[str] = None,
    ) -> list[dict]:
        """
        Recupera il report payroll (ore ordinarie, straordinari, ferie retribuite).

        Parameters
        ----------
        user : str
            Email, Employee ID, erecno o ``"all"``.
        from_date : str
            Data inizio.
        to_date : str
            Data fine.

        Returns
        -------
        list[dict]
            Lista di record con: regularHour, OtHours, paidLeaveHours, totalAmount, …
        """
        params: dict[str, Any] = {
            "user":     user,
            "fromDate": from_date,
            "toDate":   to_date,
        }
        if date_format:
            params["dateFormat"] = date_format

        result = self._client.get("timetracker/getpayrollreport", params=params)
        return result.get("result", []) if isinstance(result, dict) else []

    def get_settings(self) -> dict:
        """
        Recupera le impostazioni generali del time tracker.

        Returns
        -------
        dict
            Impostazioni: tipo log (ore/inizio-fine/timer), max ore/giorno, …
        """
        result = self._client.get("timetracker/gettimetrackersettings")
        return result.get("result", result) if isinstance(result, dict) else {}

    def get_jobs(
        self,
        assigned_to: Optional[str] = None,
        job_status: str = "in-progress",
        s_index: int = 0,
        limit: int = 200,
    ) -> list[dict]:
        """
        Recupera la lista dei job disponibili.

        Parameters
        ----------
        assigned_to : str, optional
            Email o Employee ID del dipendente. Se omesso → tutti i job.
        job_status : str
            ``"in-progress"`` (default) | ``"completed"`` | ``"all"``
        s_index : int
            Indice di partenza per paginazione.
        limit : int
            Max record (default 200).

        Returns
        -------
        list[dict]
            Lista di job con: jobId, jobName, projectName, clientName,
            jobStatus, jobBillableStatus, fromDate, toDate.
        """
        params: dict[str, Any] = {
            "jobStatus": job_status,
            "sIndex":    s_index,
            "limit":     min(limit, 200),
        }
        if assigned_to:
            params["assignedTo"] = assigned_to

        result = self._client.get("timetracker/getjobs", params=params)
        return result.get("result", []) if isinstance(result, dict) else []
