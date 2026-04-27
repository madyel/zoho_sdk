"""
Employee API – anagrafica dipendenti Zoho People.

Endpoint coperti:
  GET  /api/forms/P_EmployeeView/records        – lista / ricerca dipendenti
  GET  /api/forms/json/P_Employee/getDataByID   – singolo dipendente per ID
  POST /api/forms/json/P_Employee/insertRecord  – crea dipendente
  POST /api/forms/json/P_Employee/updateRecord  – aggiorna dipendente

Scope richiesto: ZOHOPEOPLE.forms.ALL  (o READ per sola lettura)
"""

from __future__ import annotations

import json

from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from ..client import ZohoPeopleClient


class EmployeeAPI:
    """
    Accesso all'anagrafica dipendenti di Zoho People.

    Example
    -------
    >>> # Lista tutti i dipendenti attivi (paginata)
    >>> employees = client.employee.list(view_name="P_EmployeeView")

    >>> # Ricerca per email
    >>> emp = client.employee.get_by_email("mario.rossi@azienda.it")

    >>> # Crea nuovo dipendente
    >>> result = client.employee.create({
    ...     "First Name": "Mario",
    ...     "Last Name":  "Rossi",
    ...     "Email":      "mario.rossi@azienda.it",
    ...     "Employee ID": "EMP001",
    ... })
    """

    def __init__(self, client: "ZohoPeopleClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Lettura
    # ------------------------------------------------------------------

    def list(
        self,
        view_name: str = "P_EmployeeView",
        s_index: int = 1,
        rec_limit: int = 200,
        search_column: Optional[str] = None,
        search_value: Optional[str] = None,
        modified_time: Optional[int] = None,
    ) -> list[dict]:
        """
        Recupera i dipendenti da una vista.

        Parameters
        ----------
        view_name : str
            Nome della vista (default ``P_EmployeeView``).
        s_index : int
            Indice di partenza per la paginazione (default 1).
        rec_limit : int
            Numero di record per pagina (max 200, default 200).
        search_column : str, optional
            ``EMPLOYEEID`` o ``EMPLOYEEMAILALIAS``.
        search_value : str, optional
            Valore da cercare nel campo ``search_column``.
        modified_time : int, optional
            Timestamp in ms: restituisce solo i record modificati dopo.

        Returns
        -------
        list[dict]
            Lista di record dipendente.
        """
        params: dict[str, Any] = {
            "sIndex":   s_index,
            "rec_limit": min(rec_limit, 200),
        }
        if search_column:
            params["searchColumn"] = search_column
        if search_value:
            params["searchValue"] = search_value
        if modified_time is not None:
            params["modifiedtime"] = modified_time

        result = self._client.get(f"forms/{view_name}/records", params=params)
        # L'endpoint restituisce direttamente una lista
        if isinstance(result, list):
            return result
        return result.get("result", result) if isinstance(result, dict) else []

    def get_all(
        self,
        view_name: str = "P_EmployeeView",
        **kwargs,
    ) -> list[dict]:
        """
        Auto-paginazione: recupera TUTTI i dipendenti dalla vista.

        Attenzione: può generare molte chiamate API per organizzazioni grandi.
        """
        all_records: list[dict] = []
        index = 1
        limit = 200

        while True:
            batch = self.list(view_name=view_name, s_index=index, rec_limit=limit, **kwargs)
            if not batch:
                break
            all_records.extend(batch)
            if len(batch) < limit:
                break
            index += limit

        return all_records

    def get_by_email(self, email: str) -> Optional[dict]:
        """
        Recupera un dipendente tramite indirizzo email.

        Returns
        -------
        dict or None
        """
        records = self.list(
            search_column="EMPLOYEEMAILALIAS",
            search_value=email,
            rec_limit=1,
        )
        return records[0] if records else None

    def get_by_id(self, employee_id: str) -> Optional[dict]:
        """
        Recupera un dipendente tramite Employee ID (non erecno).

        Returns
        -------
        dict or None
        """
        records = self.list(
            search_column="EMPLOYEEID",
            search_value=employee_id,
            rec_limit=1,
        )
        return records[0] if records else None

    def get_by_record_id(self, record_id: str) -> dict:
        """
        Recupera un dipendente tramite il suo record ID (erecno / Zoho.ID).

        Parameters
        ----------
        record_id : str
            Il valore di ``recordId`` / ``erecno`` restituito nelle liste.
        """
        params = {"recordId": record_id}
        result = self._client.get("forms/json/P_Employee/getDataByID", params=params)
        if isinstance(result, dict):
            return result.get("result", result)
        return {}

    # ------------------------------------------------------------------
    # Scrittura
    # ------------------------------------------------------------------

    def create(
        self,
        data: dict,
        input_type: str = "json",
        form_link_name: str = "P_Employee",
    ) -> dict:
        """
        Crea un nuovo dipendente.

        Parameters
        ----------
        data : dict
            Campi del dipendente nel formato ``{"First Name": "Mario", ...}``.
        input_type : str
            ``json`` (default) oppure ``xml``.
        form_link_name : str
            Nome del form (default ``P_Employee``).

        Returns
        -------
        dict
            Risposta con ``pkId`` (ID del record creato) e ``message``.
        """
        params = {"inputData": json.dumps(data)}
        result = self._client.post(
            f"forms/{input_type}/{form_link_name}/insertRecord",
            params=params,
        )
        return result if isinstance(result, dict) else {}

    def update(
        self,
        record_id: str,
        data: dict,
        input_type: str = "json",
        form_link_name: str = "P_Employee",
    ) -> dict:
        """
        Aggiorna un dipendente esistente.

        Parameters
        ----------
        record_id : str
            ``recordId`` / erecno del dipendente.
        data : dict
            Campi da aggiornare.

        Returns
        -------
        dict
            Risposta con ``pkId`` e ``message``.
        """
        params = {
            "inputData": json.dumps(data),
            "recordId":  record_id,
        }
        result = self._client.post(
            f"forms/{input_type}/{form_link_name}/updateRecord",
            params=params,
        )
        return result if isinstance(result, dict) else {}
