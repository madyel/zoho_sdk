"""
CompensatoryAPI  –  Zoho People Compensatory Off REST API
=========================================================

Gestisce le richieste di recupero (compensatory off).

Endpoint:
    GET    /compensatory/getRequests
    GET    /compensatory/getSpecificRequest
    POST   /compensatory/addRequest
    PUT    /compensatory/updateRequest
    PATCH  /compensatory/cancelRequest
    DELETE /compensatory/deleteRequest
    POST   /compensatory/fileUpload

Scope OAuth: ZohoPeople.leave.ALL
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient

from .attendance import _to_zoho_date


class CompensatoryAPI:
    """
    Wrapper per le API Zoho People Compensatory Off.

    Usato tramite:
        client.compensatory.get_requests(user_id)
        client.compensatory.add_request(user_id, date, worked_date)
        client.compensatory.cancel_request(request_id)
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    def get_requests(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Recupera le richieste di recupero.

        Endpoint: GET /compensatory/getRequests

        Parameters
        ----------
        user_id : str, optional
            Email o ID dipendente.
        status : str, optional
            Filtra per stato: "Pending", "Approved", "Rejected".
        """
        params: Dict[str, Any] = {"sIndex": page, "resLen": per_page}
        if user_id:
            params["userId"] = user_id
        if status:
            params["status"] = status

        data     = self._client.get("v3/compensatory/getRequests", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def get_specific_request(self, request_id: str) -> Dict[str, Any]:
        """
        Recupera una specifica richiesta di recupero.

        Endpoint: GET /compensatory/getSpecificRequest
        """
        data     = self._client.get("v3/compensatory/getSpecificRequest",
                                    params={"requestId": request_id})
        response = data.get("response", data)
        result   = response.get("result", {})
        return result if isinstance(result, dict) else {}

    def add_request(
        self,
        user_id: str,
        date: str,
        worked_date: str,
    ) -> Dict[str, Any]:
        """
        Crea una nuova richiesta di recupero.

        Endpoint: POST /compensatory/addRequest

        Parameters
        ----------
        user_id : str
            Email o ID dipendente.
        date : str
            Data del riposo compensativo richiesto (dd/MM/yyyy).
        worked_date : str
            Data del giorno lavorato (dd/MM/yyyy).
        """
        payload: Dict[str, Any] = {
            "userId":     user_id,
            "date":       _to_zoho_date(date),
            "workedDate": _to_zoho_date(worked_date),
        }
        return self._client.form_post("v3/compensatory/addRequest", data=payload)

    def update_request(self, request_id: str, date: str) -> Dict[str, Any]:
        """
        Aggiorna una richiesta di recupero.

        Endpoint: PUT /compensatory/updateRequest

        Parameters
        ----------
        request_id : str
            ID della richiesta.
        date : str
            Nuova data del riposo compensativo (dd/MM/yyyy).
        """
        payload: Dict[str, Any] = {
            "requestId": request_id,
            "date":      _to_zoho_date(date),
        }
        return self._client.put("v3/compensatory/updateRequest", json=payload)

    def cancel_request(self, request_id: str) -> Dict[str, Any]:
        """
        Cancella una richiesta di recupero.

        Endpoint: PATCH /compensatory/cancelRequest
        """
        return self._client.patch("v3/compensatory/cancelRequest",
                                  json={"requestId": request_id})

    def delete_request(self, request_id: str) -> Dict[str, Any]:
        """
        Elimina una richiesta di recupero.

        Endpoint: DELETE /compensatory/deleteRequest
        """
        return self._client.delete("v3/compensatory/deleteRequest",
                                   params={"requestId": request_id})

    def file_upload(self, request_id: str, file_path: str) -> Dict[str, Any]:
        """
        Carica un allegato per una richiesta di recupero.

        Endpoint: POST /compensatory/fileUpload

        Parameters
        ----------
        request_id : str
            ID della richiesta di recupero.
        file_path : str
            Percorso del file da caricare.
        """
        with open(file_path, "rb") as f:
            return self._client.upload("v3/compensatory/fileUpload",
                                       files={"file": f},
                                       data={"requestId": request_id})
