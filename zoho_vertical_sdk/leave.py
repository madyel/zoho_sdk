"""
PeopleLeaveAPI  –  Zoho People Leave REST API v3
=================================================

Gestisce l'intero ciclo delle assenze: richiesta, approvazione, rifiuto
e consultazione dei saldi. Le politiche ferie (weekend, festivi) sono
rispettate automaticamente in base alla configurazione dell'account Zoho.

Endpoint v3:
    GET  /people/api/v3/leave/getLeaveRequests         – lista richieste
    POST /people/api/v3/leave/addLeaveRequest           – nuova richiesta
    GET  /people/api/v3/leave/getLeaveRecord            – saldo residuo
    POST /people/api/v3/leave/updateLeaveRequestStatus  – approva/rifiuta

Formato date: dd-MMM-yyyy (es. 01-Mar-2026)
Scope OAuth:  ZohoPeople.leave.ALL

Riferimento: guida/zoho_people_api_v3_guida.pdf — sezione 7
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient

from .attendance import _to_zoho_date


class PeopleLeaveAPI:
    """
    Wrapper per le API Zoho People Leave v3.

    Usato tramite:
        client.leave.get_requests(user_id, status="Pending")
        client.leave.add_request(user_id, "Annual Leave", "24/03/2026", "27/03/2026")
        client.leave.get_balance(user_id)
        client.leave.update_status(request_id, status=1)  # 1=approva

    Parameters
    ----------
    client : ZohoVerticalClient
        Istanza del client autenticato con OAuth.
    """

    # Costanti di stato per update_status()
    STATUS_APPROVE = 1
    STATUS_REJECT  = 2
    STATUS_CANCEL  = 3

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

        Endpoint: GET /people/api/v3/leave/getLeaveRequests

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

        Endpoint: POST /people/api/v3/leave/addLeaveRequest

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

        Raises
        ------
        ZohoAPIError
            Se esiste già una richiesta approvata o pendente nelle stesse date
            (Zoho restituisce status 1).
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

    # ------------------------------------------------------------------
    # Saldo residuo
    # ------------------------------------------------------------------

    def get_balance(self, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recupera il saldo residuo ferie per ogni tipo.

        Endpoint: GET /people/api/v3/leave/getLeaveRecord

        Parameters
        ----------
        user_id : str, optional
            Email o ID dipendente. Se omesso usa l'utente corrente.

        Returns
        -------
        list[dict]
            Lista con per ogni tipo ferie:
            ``{"leaveType": "...", "balance": "5", "used": "3"}``
        """
        params: Dict[str, Any] = {}
        if user_id:
            params["userId"] = user_id

        data     = self._client.get("v3/leave/getLeaveRecord", params=params or None)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Approvazione / Rifiuto
    # ------------------------------------------------------------------

    def update_status(
        self,
        request_id: str,
        status: int,
        comments: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Approva, rifiuta o cancella una richiesta di ferie.

        Endpoint: POST /people/api/v3/leave/updateLeaveRequestStatus

        Richiede permessi di manager o amministratore.

        Parameters
        ----------
        request_id : str
            ID della richiesta ferie (ottenuto da get_requests()).
        status : int
            1 = Approva (STATUS_APPROVE)
            2 = Rifiuta  (STATUS_REJECT)
            3 = Cancella (STATUS_CANCEL)
        comments : str, optional
            Note del manager (visibili al dipendente).

        Returns
        -------
        dict
            Risposta API con esito dell'operazione.
        """
        payload: Dict[str, Any] = {
            "requestId": request_id,
            "status":    status,
        }
        if comments:
            payload["comments"] = comments

        return self._client.form_post(
            "v3/leave/updateLeaveRequestStatus", data=payload
        )

    def approve(self, request_id: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Approva una richiesta di ferie (shortcut per update_status con status=1)."""
        return self.update_status(request_id, self.STATUS_APPROVE, comments)

    def reject(self, request_id: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Rifiuta una richiesta di ferie (shortcut per update_status con status=2)."""
        return self.update_status(request_id, self.STATUS_REJECT, comments)

    def cancel(self, request_id: str, comments: Optional[str] = None) -> Dict[str, Any]:
        """Cancella una richiesta di ferie (shortcut per update_status con status=3)."""
        return self.update_status(request_id, self.STATUS_CANCEL, comments)
