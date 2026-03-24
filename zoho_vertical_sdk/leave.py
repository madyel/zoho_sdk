"""
PeopleLeaveAPI  –  Zoho People Leave REST API
==============================================

Gestisce l'intero ciclo delle assenze e delle maturazioni (grant).

Endpoint Leave (richieste):
    GET    /leave/getLeaveRequests
    GET    /leave/getSpecificLeaveRequest
    POST   /leave/addLeaveRequest
    PUT    /leave/updateLeaveRequest
    PATCH  /leave/cancelLeaveRequest
    DELETE /leave/deleteLeaveRequests
    POST   /leave/fileUploadLeave

Endpoint Grant (maturazione):
    GET    /leave/getLeaveGrantRequests
    GET    /leave/getSpecificLeaveGrantRequests
    POST   /leave/addLeaveGrantRequests
    PUT    /leave/updateLeaveGrantRequests
    PATCH  /leave/cancelLeaveGrantRequest
    DELETE /leave/deleteLeaveGrantRequests
    POST   /leave/fileUploadGrant

Scope OAuth:  ZohoPeople.leave.ALL
Formato date: dd-MMM-yyyy (es. 01-Mar-2026)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient

from .attendance import _to_zoho_date


class PeopleLeaveAPI:
    """
    Wrapper per le API Zoho People Leave.

    Usato tramite:
        client.leave.get_requests(user_id, status="Pending")
        client.leave.get_specific_request(request_id)
        client.leave.add_request(user_id, "Annual Leave", "24/03/2026", "27/03/2026")
        client.leave.update_request(request_id, "24/03/2026", "28/03/2026")
        client.leave.cancel_request(request_id)
        client.leave.delete_requests(request_id)
        client.leave.get_balance(user_id)
        client.leave.update_status(request_id, status=1)  # 1=approva
        client.leave.get_grant_requests(user_id)
        client.leave.add_grant_request(user_id, leave_type_id, count, reason)

    Parameters
    ----------
    client : ZohoVerticalClient
        Istanza del client autenticato con OAuth.
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Lettura richieste
    # ------------------------------------------------------------------

    def get_requests(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        page: int = 1,
        per_page: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Recupera le richieste di ferie.

        Endpoint: GET /leave/getLeaveRequests

        Parameters
        ----------
        user_id : str, optional
            Email o ID dipendente. Se omesso restituisce richieste dell'utente corrente.
        status : str, optional
            Filtra per stato: "Approved", "Pending", "Rejected", "Cancelled".
        from_date, to_date : str, optional
            Intervallo di date in formato dd/MM/yyyy.
        page : int
            Indice di partenza per la paginazione (sIndex), default 1.
        per_page : int
            Numero di record per pagina (resLen), max 200.

        Returns
        -------
        list[dict]
            Lista di richieste ferie.
        """
        params: Dict[str, Any] = {
            "sIndex": page,
            "resLen": per_page,
        }
        if user_id:
            params["userId"] = user_id
        if status:
            params["allowedStatus"] = status
        if from_date:
            params["fromDate"] = _to_zoho_date(from_date)
        if to_date:
            params["toDate"] = _to_zoho_date(to_date)

        data     = self._client.get("v3/leave/getLeaveRequests", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def get_specific_request(self, request_id: str) -> Dict[str, Any]:
        """
        Recupera una specifica richiesta di ferie.

        Endpoint: GET /leave/getSpecificLeaveRequest

        Parameters
        ----------
        request_id : str
            ID della richiesta ferie.
        """
        data     = self._client.get("v3/leave/getSpecificLeaveRequest", params={"requestId": request_id})
        response = data.get("response", data)
        result   = response.get("result", {})
        return result if isinstance(result, dict) else {}

    # ------------------------------------------------------------------
    # Invio richiesta
    # ------------------------------------------------------------------

    def add_request(
        self,
        user_id: str,
        leave_type: str,
        from_date: str,
        to_date: str,
        is_half_day: bool = False,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Invia una nuova richiesta di ferie.

        Endpoint: POST /leave/addLeaveRequest

        Parameters
        ----------
        user_id : str
            Email o ID del dipendente richiedente.
        leave_type : str
            Nome del tipo ferie (es. "Annual Leave", "Sick Leave").
        from_date, to_date : str
            Date in formato dd/MM/yyyy.
        is_half_day : bool
            True per richiedere mezza giornata.
        reason : str, optional
            Motivazione della richiesta.

        Returns
        -------
        dict
            Risposta API con ``response.result.requestId``.
        """
        payload: Dict[str, Any] = {
            "userId":    user_id,
            "leavetype": leave_type,
            "fromDate":  _to_zoho_date(from_date),
            "toDate":    _to_zoho_date(to_date),
            "isHalfDay": is_half_day,
        }
        if reason:
            payload["reason"] = reason

        return self._client.form_post("v3/leave/addLeaveRequest", data=payload)

    def update_request(
        self,
        request_id: str,
        from_date: str,
        to_date: str,
    ) -> Dict[str, Any]:
        """
        Modifica una richiesta di ferie esistente.

        Endpoint: PUT /leave/updateLeaveRequest

        Parameters
        ----------
        request_id : str
            ID della richiesta ferie da modificare.
        from_date, to_date : str
            Nuove date in formato dd/MM/yyyy.
        """
        payload: Dict[str, Any] = {
            "requestId": request_id,
            "fromDate":  _to_zoho_date(from_date),
            "toDate":    _to_zoho_date(to_date),
        }
        return self._client.put("v3/leave/updateLeaveRequest", json=payload)

    def cancel_request(self, request_id: str) -> Dict[str, Any]:
        """
        Cancella una richiesta di ferie.

        Endpoint: PATCH /leave/cancelLeaveRequest

        Parameters
        ----------
        request_id : str
            ID della richiesta ferie da cancellare.
        """
        return self._client.patch("v3/leave/cancelLeaveRequest", json={"requestId": request_id})

    def delete_requests(self, request_id: str) -> Dict[str, Any]:
        """
        Elimina una richiesta di ferie.

        Endpoint: DELETE /leave/deleteLeaveRequests

        Parameters
        ----------
        request_id : str
            ID della richiesta ferie da eliminare.
        """
        return self._client.delete("v3/leave/deleteLeaveRequests", params={"requestId": request_id})

    def file_upload_leave(self, request_id: str, file_path: str) -> Dict[str, Any]:
        """
        Carica un allegato per una richiesta di ferie.

        Endpoint: POST /leave/fileUploadLeave

        Parameters
        ----------
        request_id : str
            ID della richiesta ferie.
        file_path : str
            Percorso del file da caricare.
        """
        with open(file_path, "rb") as f:
            return self._client.upload("v3/leave/fileUploadLeave",
                                       files={"file": f},
                                       data={"requestId": request_id})

    # ------------------------------------------------------------------
    # Saldo residuo
    # ------------------------------------------------------------------
    # Grant API (Maturazione ferie)
    # ------------------------------------------------------------------

    def get_grant_requests(
        self,
        user_id: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        per_page: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Recupera le richieste di maturazione ferie (grant).

        Endpoint: GET /leave/getLeaveGrantRequests

        Parameters
        ----------
        user_id : str, optional
            Email o ID dipendente.
        status : str, optional
            Filtra per stato.
        """
        params: Dict[str, Any] = {"sIndex": page, "resLen": per_page}
        if user_id:
            params["userId"] = user_id
        if status:
            params["status"] = status

        data     = self._client.get("v3/leave/getLeaveGrantRequests", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def get_specific_grant_request(self, request_id: str) -> Dict[str, Any]:
        """
        Recupera una specifica richiesta di maturazione.

        Endpoint: GET /leave/getSpecificLeaveGrantRequests
        """
        data     = self._client.get("v3/leave/getSpecificLeaveGrantRequests",
                                    params={"requestId": request_id})
        response = data.get("response", data)
        result   = response.get("result", {})
        return result if isinstance(result, dict) else {}

    def add_grant_request(
        self,
        user_id: str,
        leave_type_id: str,
        count: float,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crea una nuova richiesta di maturazione ferie.

        Endpoint: POST /leave/addLeaveGrantRequests

        Parameters
        ----------
        user_id : str
            Email o ID dipendente.
        leave_type_id : str
            ID del tipo di ferie.
        count : float
            Numero di giorni da maturare.
        reason : str, optional
            Motivazione.
        """
        payload: Dict[str, Any] = {
            "userId":      user_id,
            "leaveTypeId": leave_type_id,
            "count":       count,
        }
        if reason:
            payload["reason"] = reason
        return self._client.form_post("v3/leave/addLeaveGrantRequests", data=payload)

    def update_grant_request(
        self,
        request_id: str,
        count: float,
        reason: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Aggiorna una richiesta di maturazione esistente.

        Endpoint: PUT /leave/updateLeaveGrantRequests
        """
        payload: Dict[str, Any] = {"requestId": request_id, "count": count}
        if reason:
            payload["reason"] = reason
        return self._client.put("v3/leave/updateLeaveGrantRequests", json=payload)

    def cancel_grant_request(self, request_id: str) -> Dict[str, Any]:
        """
        Cancella una richiesta di maturazione.

        Endpoint: PATCH /leave/cancelLeaveGrantRequest
        """
        return self._client.patch("v3/leave/cancelLeaveGrantRequest",
                                  json={"requestId": request_id})

    def delete_grant_request(self, request_id: str) -> Dict[str, Any]:
        """
        Elimina una richiesta di maturazione.

        Endpoint: DELETE /leave/deleteLeaveGrantRequests
        """
        return self._client.delete("v3/leave/deleteLeaveGrantRequests",
                                   params={"requestId": request_id})

    def file_upload_grant(self, request_id: str, file_path: str) -> Dict[str, Any]:
        """
        Carica un allegato per una richiesta di maturazione.

        Endpoint: POST /leave/fileUploadGrant
        """
        with open(file_path, "rb") as f:
            return self._client.upload("v3/leave/fileUploadGrant",
                                       files={"file": f},
                                       data={"requestId": request_id})
