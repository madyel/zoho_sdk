"""
PeopleLeaveAPI  –  Zoho People Leave Tracker API v3
=====================================================

Endpoint Leave Tracker:
    GET    v3/leave-tracker/leaves           (richieste ferie)
    POST   v3/leave-tracker/leaves           (nuova richiesta)
    GET    v3/leave-tracker/balances         (saldo residuo)
    GET    v3/leave-tracker/settings/leavetypes  (tipi di ferie)
    POST   v3/leave-tracker/grants           (nuova maturazione)

Scope OAuth:  ZOHOPEOPLE.leave.READ / ZOHOPEOPLE.leave.CREATE
Formato date: dd-MMM-yyyy (es. 01-Mar-2026)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient

from .attendance import _to_zoho_date


class PeopleLeaveAPI:
    """
    Wrapper per le API Zoho People Leave Tracker v3.

    Usato tramite:
        client.leave.get_requests(from_date="01/03/2026", to_date="31/03/2026")
        client.leave.add_request(employee_zoho_id, leave_type_id, from_date, to_date)
        client.leave.get_balance(employee_zoho_id)
        client.leave.get_leave_types()
        client.leave.add_grant(employee_zoho_id, leave_type_id, count)
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Richieste di ferie
    # ------------------------------------------------------------------

    def get_requests(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        employee_zoho_id: Optional[str] = None,
        approval_status: Optional[str] = None,
        limit: int = 200,
        offset: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Recupera le richieste di ferie.

        Endpoint: GET v3/leave-tracker/leaves

        Parameters
        ----------
        from_date, to_date : str, optional
            Intervallo di date in formato dd/MM/yyyy (vengono convertite in dd-MMM-yyyy).
        employee_zoho_id : str, optional
            ID Zoho del dipendente. Se omesso restituisce tutte.
        approval_status : str, optional
            Filtra per stato: "APPROVED", "PENDING", "REJECTED", "CANCELLED", "CANCEL_PENDING", "ALL".
        limit : int
            Numero massimo di record da restituire.
        offset : int
            Offset di paginazione.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        if from_date:
            params["from_date"] = _to_zoho_date(from_date)
        if to_date:
            params["to_date"] = _to_zoho_date(to_date)
        if employee_zoho_id:
            params["employee_zoho_ids"] = employee_zoho_id
        if approval_status:
            params["approval_status"] = approval_status

        data   = self._client.get("v3/leave-tracker/leaves", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    def add_request(
        self,
        employee_zoho_id: str,
        leave_type_id: str,
        from_date: str,
        to_date: str,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invia una nuova richiesta di ferie.

        Endpoint: POST v3/leave-tracker/leaves

        Parameters
        ----------
        employee_zoho_id : str
            ID Zoho del dipendente richiedente.
        leave_type_id : str
            ID del tipo di ferie.
        from_date, to_date : str
            Date in formato dd/MM/yyyy.
        reason : str, optional
            Motivazione della richiesta.
        """
        payload: Dict[str, Any] = {
            "employee_zoho_id": employee_zoho_id,
            "leave_type_id":    leave_type_id,
            "from_date":        _to_zoho_date(from_date),
            "to_date":          _to_zoho_date(to_date),
        }
        if reason:
            payload["reason"] = reason
        return self._client.form_post("v3/leave-tracker/leaves", data=payload)

    # ------------------------------------------------------------------
    # Saldo residuo
    # ------------------------------------------------------------------

    def get_balance(
        self,
        employee_zoho_id: str,
        leave_type_ids: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Recupera il saldo residuo ferie di un dipendente.

        Endpoint: GET v3/leave-tracker/balances

        Parameters
        ----------
        employee_zoho_id : str
            ID Zoho del dipendente.
        leave_type_ids : str, optional
            ID tipo ferie (per filtrare un tipo specifico).
        """
        params: Dict[str, Any] = {"employee_zoho_id": employee_zoho_id}
        if leave_type_ids:
            params["leave_type_ids"] = leave_type_ids
        data   = self._client.get("v3/leave-tracker/balances", params=params)
        result = data.get("data", data)
        return result if isinstance(result, dict) else data

    # ------------------------------------------------------------------
    # Tipi di ferie
    # ------------------------------------------------------------------

    def get_leave_types(
        self,
        employee_zoho_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recupera i tipi di ferie disponibili.

        Endpoint: GET v3/leave-tracker/settings/leavetypes

        Parameters
        ----------
        employee_zoho_id : str, optional
            ID Zoho del dipendente (per vedere i tipi a lui assegnati).
        """
        params: Dict[str, Any] = {}
        if employee_zoho_id:
            params["employee_zoho_id"] = employee_zoho_id
        data   = self._client.get("v3/leave-tracker/settings/leavetypes", params=params or None)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Grant (maturazione ferie)
    # ------------------------------------------------------------------

    def add_grant(
        self,
        employee_zoho_id: str,
        leave_type_id: str,
        count: float,
        reason: Optional[str] = None,
        date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crea una nuova maturazione ferie (grant).

        Endpoint: POST v3/leave-tracker/grants

        Parameters
        ----------
        employee_zoho_id : str
            ID Zoho del dipendente.
        leave_type_id : str
            ID del tipo di ferie.
        count : float
            Numero di giorni da maturare.
        reason : str, optional
            Motivazione.
        date : str, optional
            Data di riferimento in formato dd/MM/yyyy.
        """
        payload: Dict[str, Any] = {
            "employee_zoho_id": employee_zoho_id,
            "leave_type_id":    leave_type_id,
            "count":            count,
        }
        if reason:
            payload["reason"] = reason
        if date:
            payload["date"] = _to_zoho_date(date)
        return self._client.form_post("v3/leave-tracker/grants", data=payload)
