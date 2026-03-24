"""
ShiftAPI  –  Zoho People Shifts REST API v3
============================================

Endpoint:
    GET    v3/shifts/schedules   (calendario turni)
    POST   v3/shifts/mappings    (assegna turno)
    GET    v3/shifts             (lista turni disponibili)

Scope OAuth: ZOHOPEOPLE.shift.READ / ZOHOPEOPLE.shift.CREATE
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient

from .attendance import _to_zoho_date


class ShiftAPI:
    """
    Wrapper per le API Zoho People Shifts v3.

    Usato tramite:
        client.shift.get_schedule(from_date, to_date, employee_zoho_id)
        client.shift.map_shift(employee_zoho_id, shift_id, from_date, to_date)
        client.shift.get_shifts()
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    def get_schedule(
        self,
        from_date: str,
        to_date: str,
        employee_zoho_ids: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Recupera il calendario turni.

        Endpoint: GET v3/shifts/schedules

        Parameters
        ----------
        from_date, to_date : str
            Intervallo date in formato dd/MM/yyyy.
        employee_zoho_ids : str, optional
            ID Zoho del dipendente.
        """
        params: Dict[str, Any] = {
            "from_date": _to_zoho_date(from_date),
            "to_date":   _to_zoho_date(to_date),
        }
        if employee_zoho_ids:
            params["employee_zoho_ids"] = employee_zoho_ids
        return self._client.get("v3/shifts/schedules", params=params)

    def map_shift(
        self,
        employee_zoho_id: str,
        shift_id: str,
        from_date: str,
        to_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Assegna un turno a un dipendente.

        Endpoint: POST v3/shifts/mappings

        Parameters
        ----------
        employee_zoho_id : str
            ID Zoho del dipendente.
        shift_id : str
            ID del turno da assegnare.
        from_date : str
            Data di inizio dell'assegnazione (dd/MM/yyyy).
        to_date : str, optional
            Data di fine dell'assegnazione (dd/MM/yyyy).
        """
        payload: Dict[str, Any] = {
            "employee_zoho_id": employee_zoho_id,
            "shift_id":         shift_id,
            "from_date":        _to_zoho_date(from_date),
        }
        if to_date:
            payload["to_date"] = _to_zoho_date(to_date)
        return self._client.form_post("v3/shifts/mappings", data=payload)

    def get_shifts(self, limit: int = 200, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Recupera la lista dei turni disponibili.

        Endpoint: GET v3/shifts

        Parameters
        ----------
        limit : int
            Numero massimo di record.
        offset : int
            Offset di paginazione.
        """
        params: Dict[str, Any] = {"limit": limit, "offset": offset}
        data   = self._client.get("v3/shifts", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []
