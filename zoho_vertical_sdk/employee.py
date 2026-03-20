"""
PeopleEmployeeAPI  –  Zoho People Employee REST API
====================================================

Sostituisce il vecchio approccio cookie/CSRF con OAuth 2.0.

Mapping vecchio → nuovo
-----------------------
peopleAction()      →  client.employee.get_tree(eNo)
findEmploy(user)    →  client.employee.search(user)
userDetails(key)    →  client.employee.get_details()  (usa attendance.get_monthly)

Vecchi endpoint web (richiedono cookie + CSRF, ma funzionano anche con OAuth):
    POST /{org}/peopleAction.zp   mode=EMPLOYEE_TREE

Endpoint REST ufficiali (fallback):
    GET  /people/api/forms/json/P_EmployeeView/getRecords

Scope OAuth richiesti: ZohoPeople.forms.ALL

Riferimento API:
    https://www.zoho.com/people/api-integration/employee.html
"""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient

# Importa helper già usato in attendance
from .attendance import _org_from_service_url


class PeopleEmployeeAPI:
    """
    Wrapper per le API Zoho People Employee.

    Usato tramite:
        client.employee.list()
        client.employee.search("Mario Rossi")
        client.employee.get(employee_id)
        client.employee.get_tree(employee_id)

    Parameters
    ----------
    client : ZohoVerticalClient
        Istanza del client autenticato con OAuth.
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # URL helper endpoint interno (stesso pattern di PeopleAttendanceAPI)
    # ------------------------------------------------------------------

    def _web_base_url(self) -> Optional[str]:
        """
        Restituisce l'URL base dell'endpoint interno se SERVICE_URL è configurato.
        Es: https://people.zoho.com/relewanthrm
        """
        if not self._client.service_url:
            return None
        org = _org_from_service_url(self._client.service_url)
        return f"{self._client.api_domain}/{org}"

    # ------------------------------------------------------------------
    # Endpoint interno: peopleAction.zp  mode=EMPLOYEE_TREE
    # Equivalente esatto del vecchio peopleAction()
    # ------------------------------------------------------------------

    def _get_tree_web(self, employee_id: str = "") -> Optional[Dict[str, Any]]:
        """
        Recupera l'albero dipendenti via endpoint interno ``peopleAction.zp``.

        Equivale a::

            POST /{org}/peopleAction.zp
                 mode=EMPLOYEE_TREE  isint=true  erecno=<eNo>

        Restituisce None se SERVICE_URL non è configurato.
        Risposta attesa::

            {
              "users": {
                "userList": [
                  [eNo, ?, ?, "Cognome Nome", empId, apiId, "email@...", ...],
                  ...
                ]
              }
            }
        """
        base = self._web_base_url()
        if not base:
            return None

        url = f"{base}/peopleAction.zp"

        candidates = [
            # 1. Senza erecno → utente corrente del token OAuth
            {"mode": "EMPLOYEE_TREE", "isint": "true"},
        ]
        if employee_id:
            candidates.append(
                {"mode": "EMPLOYEE_TREE", "isint": "true", "erecno": employee_id}
            )

        for data in candidates:
            try:
                raw = self._client.form_post_absolute(url, data=data)
            except Exception:
                continue
            if isinstance(raw, dict) and "users" in raw:
                return raw

        return None

    # ------------------------------------------------------------------
    # Lista dipendenti
    # ------------------------------------------------------------------

    def list(
        self,
        search_value: Optional[str] = None,
        search_field: Optional[str] = None,
        page: int = 1,
        per_page: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Recupera la lista di tutti i dipendenti.

        Prova prima la REST API pubblica, poi l'endpoint interno
        (``peopleAction.zp`` mode=EMPLOYEE_TREE) come fallback.

        Returns
        -------
        list[dict]
            Lista di dipendenti normalizzata con chiavi:
            EmployeeRecordNumber, SurnameName, Email, EmployID, ApiID.
        """
        # 1. REST API: GET /people/api/forms/json/P_EmployeeView/getRecords
        params: Dict[str, Any] = {"page": page, "per_page": per_page}
        if search_value:
            params["searchValue"] = search_value
        if search_field:
            params["searchField"] = search_field

        try:
            data     = self._client.get("forms/json/P_EmployeeView/getRecords", params=params)
            response = data.get("response", data)
            result   = response.get("result", [])
            if result and isinstance(result, list):
                return self._normalize_list(result)
        except Exception:
            pass

        # 2. Fallback: endpoint interno peopleAction.zp
        tree = self._get_tree_web()
        if tree is None:
            return []

        user_list = tree.get("users", {}).get("userList", [])
        normalized = self._normalize_list(user_list)

        # Filtra per search_value se richiesto (match case-insensitive su nome)
        if search_value:
            q = search_value.lower()
            normalized = [
                e for e in normalized
                if q in e.get("SurnameName", "").lower()
                or q in e.get("Email", "").lower()
            ]
        return normalized

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Cerca dipendenti per nome o email.

        Equivale a findEmploy(user) del vecchio script::

            for e in employeeTree['users']['userList']:
                if user in e[3]:   # e[3] = SurnameName
                    ...

        Parameters
        ----------
        query : str
            Stringa da cercare nel nome o nell'email.
        """
        return self.list(search_value=query)

    def get(self, employee_id: str) -> Dict[str, Any]:
        """
        Recupera i dettagli di un singolo dipendente dall'albero organizzativo.

        Cerca nell'albero restituito da ``peopleAction.zp`` il dipendente
        con EmployeeRecordNumber == employee_id.

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (eNo).
        """
        # Prima prova direttamente con l'erecno dell'utente specifico
        tree = self._get_tree_web(employee_id)
        if tree:
            user_list = tree.get("users", {}).get("userList", [])
            normalized = self._normalize_list(user_list)
            for emp in normalized:
                if emp.get("EmployeeRecordNumber") == employee_id:
                    return emp
            if normalized:
                return normalized[0]

        # Fallback: cerca nella lista completa
        all_employees = self.list()
        for emp in all_employees:
            if emp.get("EmployeeRecordNumber") == employee_id:
                return emp

        return {}

    # ------------------------------------------------------------------
    # Albero dipendenti
    # ------------------------------------------------------------------

    def get_tree(self, employee_id: str) -> Dict[str, Any]:
        """
        Recupera l'albero organizzativo del dipendente.

        Equivale a peopleAction() con mode=EMPLOYEE_TREE del vecchio script.

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (eNo).

        Returns
        -------
        dict
            Struttura originale ``{"users": {"userList": [[...], ...]}}``
            con in aggiunta ``"_normalized"`` — lista dizionari normalizzata.
        """
        raw = self._get_tree_web(employee_id)
        if raw is None:
            return {}
        user_list = raw.get("users", {}).get("userList", [])
        return {
            **raw,
            "_normalized": self._normalize_list(user_list),
        }

    # ------------------------------------------------------------------
    # Helper: normalizza la lista per compatibilità con findEmploy()
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_list(raw_list: List[Any]) -> List[Dict[str, Any]]:
        """
        Converte la risposta grezza nella struttura del vecchio findEmploy()::

            {
                "EmployeeRecordNumber": e[0],
                "SurnameName":         e[3],
                "Email":               html.unescape(e[6]),
                "EmployID":            e[4],
                "ApiID":               e[5],
            }

        Funziona sia con la risposta flat-list (vecchio formato / internal endpoint)
        che con la risposta dict (REST API).
        """
        result = []
        for emp in raw_list:
            if isinstance(emp, list):
                # Formato vecchio: [eNo, ?, ?, nome, empId, apiId, email, ...]
                result.append({
                    "EmployeeRecordNumber": emp[0] if len(emp) > 0 else "",
                    "SurnameName":         emp[3] if len(emp) > 3 else "",
                    "Email":               html.unescape(emp[6]) if len(emp) > 6 else "",
                    "EmployID":            emp[4] if len(emp) > 4 else "",
                    "ApiID":               emp[5] if len(emp) > 5 else "",
                })
            elif isinstance(emp, dict):
                result.append({
                    "EmployeeRecordNumber": emp.get("eNo", emp.get("recordNo", "")),
                    "SurnameName":         emp.get("fullName", emp.get("name", "")),
                    "Email":               emp.get("emailId", emp.get("email", "")),
                    "EmployID":            emp.get("empId", ""),
                    "ApiID":               emp.get("id", ""),
                })
        return result

    def find(self, query: str) -> str:
        """
        Equivalente diretto di findEmploy(user) del vecchio script.

        Restituisce il risultato come stringa JSON indentata, identica
        all'output originale.

        Parameters
        ----------
        query : str
            Stringa da cercare nel nome del dipendente.
        """
        results = self.search(query)
        return json.dumps(results, indent=4, sort_keys=True, ensure_ascii=False)
