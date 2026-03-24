"""
ShiftAPI  –  Zoho People Shifts REST API
=========================================

Gestisce i turni di lavoro (schedule e mapping).

Endpoint Shift Schedule:
    GET /shift/getSchedule

Endpoint Shift Mapping:
    GET    /shift/getMapping
    GET    /shift/getSpecificMapping
    POST   /shift/mapShift
    DELETE /shift/deleteMapping

Scope OAuth: ZohoPeople.shift.READ / ZohoPeople.shift.CREATE / ZohoPeople.shift.DELETE
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient

from .attendance import _to_zoho_date


class ShiftAPI:
    """
    Wrapper per le API Zoho People Shifts.

    Usato tramite:
        client.shift.get_schedule(user_id, from_date, to_date)
        client.shift.get_mapping(shift_id, user_id)
        client.shift.map_shift(user_id, shift_id, from_date)
        client.shift.delete_mapping(map_id)
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    def get_schedule(
        self,
        user_id: str,
        from_date: str,
        to_date: str,
    ) -> Dict[str, Any]:
        """
        Recupera il calendario turni di un dipendente.

        Endpoint: GET /shift/getSchedule

        Parameters
        ----------
        user_id : str
            Email o ID dipendente.
        from_date, to_date : str
            Intervallo date in formato dd/MM/yyyy.
        """
        params: Dict[str, Any] = {
            "userId":   user_id,
            "fromDate": _to_zoho_date(from_date),
            "toDate":   _to_zoho_date(to_date),
        }
        return self._client.get("v3/shift/getSchedule", params=params)

    def get_mapping(
        self,
        shift_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Recupera i mapping turni.

        Endpoint: GET /shift/getMapping

        Parameters
        ----------
        shift_id : str, optional
            ID del turno.
        user_id : str, optional
            Email o ID dipendente.
        """
        params: Dict[str, Any] = {}
        if shift_id:
            params["shiftId"] = shift_id
        if user_id:
            params["userId"] = user_id

        data     = self._client.get("v3/shift/getMapping", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def get_specific_mapping(self, map_id: str) -> Dict[str, Any]:
        """
        Recupera un singolo mapping turno.

        Endpoint: GET /shift/getSpecificMapping
        """
        data     = self._client.get("v3/shift/getSpecificMapping", params={"mapId": map_id})
        response = data.get("response", data)
        result   = response.get("result", {})
        return result if isinstance(result, dict) else {}

    def map_shift(
        self,
        user_id: str,
        shift_id: str,
        from_date: str,
    ) -> Dict[str, Any]:
        """
        Assegna un turno a un dipendente.

        Endpoint: POST /shift/mapShift

        Parameters
        ----------
        user_id : str
            Email o ID dipendente.
        shift_id : str
            ID del turno da assegnare.
        from_date : str
            Data di inizio dell'assegnazione (dd/MM/yyyy).
        """
        payload: Dict[str, Any] = {
            "userId":   user_id,
            "shiftId":  shift_id,
            "fromDate": _to_zoho_date(from_date),
        }
        return self._client.form_post("v3/shift/mapShift", data=payload)

    def delete_mapping(self, map_id: str) -> Dict[str, Any]:
        """
        Elimina un mapping turno.

        Endpoint: DELETE /shift/deleteMapping
        """
        return self._client.delete("v3/shift/deleteMapping", params={"mapId": map_id})
