"""
PeopleEmployeeAPI  –  Zoho People Employee REST API
====================================================

Sostituisce il vecchio approccio cookie/CSRF con OAuth 2.0.

Mapping vecchio → nuovo
-----------------------
peopleAction()      →  client.employee.list() / client.employee.get_tree()
findEmploy(user)    →  client.employee.search(user)
userDetails(key)    →  client.employee.get_details()  (usa attendance.get_monthly)

Vecchi endpoint web (richiedono cookie + CSRF):
    POST /peopleAction.zp   mode=EMPLOYEE_TREE

Nuovi endpoint REST (richiedono solo OAuth token):
    GET  /people/api/forms/json/P_EmployeeView/getRecords
    GET  /people/api/employee/getEmployeeBasicInfo

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

        Equivale a peopleAction() con mode=EMPLOYEE_TREE del vecchio script,
        ma restituisce la lista strutturata invece del raw JSON.

        Parameters
        ----------
        search_value : str, optional
            Filtro per valore (es. nome, email).
        search_field : str, optional
            Campo su cui filtrare (es. "First_Name", "EmailID").

        Returns
        -------
        list[dict]
            Lista di dipendenti, ognuno con chiavi standardizzate:
            eNo, empId, name, email, department, ...
        """
        params: Dict[str, Any] = {
            "page":     page,
            "per_page": per_page,
        }
        if search_value:
            params["searchValue"] = search_value
        if search_field:
            params["searchField"] = search_field

        data = self._client.get(
            "forms/json/P_EmployeeView/getRecords",
            params=params,
        )
        # La risposta di Zoho People è {"response": {"result": [...]}}
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def search(self, query: str) -> List[Dict[str, Any]]:
        """
        Cerca dipendenti per nome (o email) tramite ricerca full-text.

        Equivale a findEmploy(user) del vecchio script che filtrava
        su employeeTree['users']['userList'] con `if user in e[3]`.

        Parameters
        ----------
        query : str
            Stringa da cercare nel nome del dipendente.

        Returns
        -------
        list[dict]
            Lista con chiavi: eNo, name, email, empId, apiId.

        Example
        -------
        >>> results = client.employee.search("Mario Rossi")
        >>> for r in results:
        ...     print(r["name"], r["email"])
        """
        employees = self.list(search_value=query)
        return self._normalize_list(employees)

    def get(self, employee_id: str) -> Dict[str, Any]:
        """
        Recupera i dettagli di un singolo dipendente.

        Parameters
        ----------
        employee_id : str
            ID del dipendente (eNo o empId).
        """
        params = {"empId": employee_id}
        data   = self._client.get("employee/getEmployeeBasicInfo", params=params)
        return data

    # ------------------------------------------------------------------
    # Albero dipendenti
    # ------------------------------------------------------------------

    def get_tree(self, employee_id: str) -> Dict[str, Any]:
        """
        Recupera l'albero organizzativo del dipendente (manager + riporti).

        Equivale a peopleAction() con mode=EMPLOYEE_TREE del vecchio script.

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (eNo).
        """
        params = {
            "erecno": employee_id,
            "type":   "EMPLOYEE_TREE",
        }
        return self._client.get("employee/getEmployeeTree", params=params)

    # ------------------------------------------------------------------
    # Helper: normalizza la lista per compatibilità con findEmploy()
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_list(raw_list: List[Any]) -> List[Dict[str, Any]]:
        """
        Converte la risposta grezza dell'API nella struttura restituita
        dal vecchio findEmploy()::

            {
                "EmployeeRecordNumber": e[0],
                "SurnameName":         e[3],
                "Email":               html.unescape(e[6]),
                "EmployID":            e[4],
                "ApiID":               e[5],
            }

        Funziona sia con la risposta flat-list (vecchio formato)
        che con la risposta dict (nuovo formato REST).
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
                # Formato REST: dizionario con campi nominali
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

        Returns
        -------
        str  JSON indentato con la lista dei dipendenti trovati.
        """
        results = self.search(query)
        return json.dumps(results, indent=4, sort_keys=True, ensure_ascii=False)
