"""
PeopleEmployeeAPI  –  Zoho People Employee REST API v3
=======================================================

Endpoint v3 ufficiali:
    GET  /people/api/v3/employee/getRecords       – lista dipendenti
    GET  /people/api/v3/employee/getRecordByID    – singolo dipendente
    GET  /people/api/v3/employee/getEmployeeTree  – albero organizzativo
    POST /people/api/v3/employee/addRecord        – aggiunge dipendente
    PUT  /people/api/v3/employee/updateRecord     – aggiorna dipendente

Endpoint interno legacy (fallback, richiede ZOHO_SERVICE_URL):
    POST /{org}/peopleAction.zp   mode=EMPLOYEE_TREE

Scope OAuth richiesti: ZohoPeople.employee.ALL

Formato risposta v3:
    {
      "response": {
        "status": 0,
        "message": "Data retrieved successfully",
        "result": [...]
      }
    }
"""

from __future__ import annotations

import html
import json
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient

from .attendance import _org_from_service_url
from .exceptions import ZohoAPIError


def _extract_user_list(raw: Dict[str, Any]) -> List[Any]:
    """
    Estrae la lista dipendenti da una risposta grezza, indipendentemente
    dal formato (legacy peopleAction.zp oppure v3).

    Formati gestiti:
      Legacy:  {"users": {"userList": [[...], ...]}}
      v3 dict: {"data": [...]}
      v3 list: {"response": {"result": [...]}}
      Fallback: primo valore che sia una lista nell'intera struttura
    """
    # Legacy
    if "users" in raw:
        return raw["users"].get("userList", [])
    # v3 candidati
    for key in ("data", "employees", "result", "records"):
        val = raw.get(key)
        if isinstance(val, list):
            return val
    # Annidato un livello (es. {"response": {"data": [...]}})
    for val in raw.values():
        if isinstance(val, dict):
            for key in ("data", "employees", "result", "records", "userList"):
                inner = val.get(key)
                if isinstance(inner, list):
                    return inner
    return []


class PeopleEmployeeAPI:
    """
    Wrapper per le API Zoho People Employee v3.

    Usato tramite:
        client.employee.list()
        client.employee.search("Mario Rossi")
        client.employee.get(employee_id)
        client.employee.get_tree(employee_id)
        client.employee.add_record(data)
        client.employee.update_record(employee_id, data)

    Parameters
    ----------
    client : ZohoVerticalClient
        Istanza del client autenticato con OAuth.
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # URL helper endpoint interno (legacy)
    # ------------------------------------------------------------------

    def _web_base_url(self) -> Optional[str]:
        if not self._client.service_url:
            return None
        org = _org_from_service_url(self._client.service_url)
        return f"{self._client.api_domain}/{org}"

    # ------------------------------------------------------------------
    # Endpoint interno legacy: peopleAction.zp  mode=EMPLOYEE_TREE
    # ------------------------------------------------------------------

    def _get_tree_web(self, employee_id: str = "") -> Optional[Dict[str, Any]]:
        """
        Recupera l'albero dipendenti via endpoint interno legacy.
        Restituisce None se SERVICE_URL non è configurato.
        """
        base = self._web_base_url()
        if not base:
            return None

        last_exc: Optional[Exception] = None

        # Nuovo endpoint REST v5
        v5_paths = [
            f"{base}/v5/tree/employee",
            f"{base}/zp/v5/tree/employee",
        ]
        v5_params_base: Dict[str, str] = {"mode": "EMPLOYEE_TREE"}
        v5_params_with_id = {**v5_params_base, "erecno": employee_id} if employee_id else v5_params_base

        for v5_url in v5_paths:
            for params in ([v5_params_with_id, v5_params_base] if employee_id else [v5_params_base]):
                try:
                    raw = self._client.get_absolute(v5_url, params=params)
                    if isinstance(raw, dict):
                        return raw
                except ZohoAPIError as exc:
                    last_exc = exc
                except Exception as exc:
                    last_exc = exc
                try:
                    raw = self._client.form_post_absolute(v5_url, data=params)
                    if isinstance(raw, dict):
                        return raw
                except ZohoAPIError as exc:
                    last_exc = exc
                except Exception as exc:
                    last_exc = exc

        # Endpoint legacy peopleAction.zp
        legacy_urls = [
            f"{base}/zp/peopleAction.zp",
            f"{base}/peopleAction.zp",
        ]
        body_base = {"mode": "EMPLOYEE_TREE", "isint": "true"}
        body_variants = [body_base]
        if employee_id:
            body_variants.append({**body_base, "erecno": employee_id})

        for url in legacy_urls:
            for data in body_variants:
                try:
                    raw = self._client.form_post_absolute(url, data=data)
                except ZohoAPIError as exc:
                    last_exc = exc
                    continue
                except Exception as exc:
                    last_exc = exc
                    continue
                if isinstance(raw, dict) and "users" in raw:
                    return raw

        if last_exc is not None:
            raise ZohoAPIError(
                f"endpoint albero non raggiungibile: {last_exc}"
            ) from last_exc
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
        view_name: str = "Active_Employees",
    ) -> List[Dict[str, Any]]:
        """
        Recupera la lista di tutti i dipendenti via REST API v3.

        Endpoint: GET /people/api/v3/employee/getRecords

        Parameters
        ----------
        search_value : str, optional
            Valore da cercare (es. "Mario").
        search_field : str, optional
            Campo su cui filtrare (es. "FirstName", "Department").
        page : int
            Indice di partenza (sIndex), default 1.
        per_page : int
            Numero di record per pagina (resLen), max 200.
        view_name : str
            "Active_Employees" (default) oppure "Terminated".

        Returns
        -------
        list[dict]
            Lista di dipendenti normalizzata.
        """
        params: Dict[str, Any] = {
            "sIndex":   page,
            "resLen":   per_page,
            "viewName": view_name,
        }
        if search_value:
            params["searchVal"] = search_value
        if search_field:
            params["searchField"] = search_field

        try:
            data     = self._client.get("v3/employee/getRecords", params=params)
            response = data.get("response", data)
            result   = response.get("result", [])
            if result and isinstance(result, list):
                return self._normalize_list(result)
        except Exception:
            pass

        # Fallback: endpoint interno legacy
        tree = self._get_tree_web()
        if tree is None:
            return []

        user_list  = _extract_user_list(tree)
        normalized = self._normalize_list(user_list)

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

        Parameters
        ----------
        query : str
            Stringa da cercare nel nome o nell'email.
        """
        return self.list(search_value=query)

    def get(self, employee_id: str) -> Dict[str, Any]:
        """
        Recupera i dettagli di un singolo dipendente.

        Endpoint: GET /people/api/v3/employee/getRecordByID

        Parameters
        ----------
        employee_id : str
            ID dipendente (empId o eNo).
        """
        try:
            data     = self._client.get("v3/employee/getRecordByID", params={"empId": employee_id})
            response = data.get("response", data)
            result   = response.get("result", [])
            if result:
                records = result if isinstance(result, list) else [result]
                normalized = self._normalize_list(records)
                if normalized:
                    return normalized[0]
        except Exception:
            pass

        # Fallback: cerca nella lista completa
        all_employees = self.list()
        for emp in all_employees:
            if emp.get("EmployeeRecordNumber") == employee_id:
                return emp

        return {}

    def get_tree(self, employee_id: str) -> Dict[str, Any]:
        """
        Recupera l'albero organizzativo del dipendente.

        Prova prima la REST API v3, poi l'endpoint interno legacy.

        Endpoint: GET /people/api/v3/employee/getEmployeeTree

        Parameters
        ----------
        employee_id : str
            Numero record dipendente (erecno).

        Returns
        -------
        dict
            Con chiave ``"_normalized"`` — lista dizionari normalizzata.
        """
        # 1. REST API v3
        try:
            data     = self._client.get("v3/employee/getEmployeeTree", params={"erecno": employee_id})
            response = data.get("response", data)
            result   = response.get("result", _extract_user_list(data))
            if result and isinstance(result, list):
                return {**data, "_normalized": self._normalize_list(result)}
            return {**data, "_normalized": []}
        except ZohoAPIError:
            pass

        # 2. Endpoint interno legacy
        try:
            raw = self._get_tree_web(employee_id)
            if raw is not None:
                user_list = _extract_user_list(raw)
                return {**raw, "_normalized": self._normalize_list(user_list)}
        except ZohoAPIError:
            pass

        # 3. Fallback: lista completa
        employees = self.list()
        return {"_normalized": employees}

    # ------------------------------------------------------------------
    # Scrittura dipendenti
    # ------------------------------------------------------------------

    def add_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggiunge un nuovo dipendente.

        Endpoint: POST /people/api/v3/employee/addRecord

        Parameters
        ----------
        record_data : dict
            Dati del dipendente. Campi comuni:
            ``{"firstName": "Mario", "lastName": "Rossi",
               "email": "mario.rossi@azienda.it", "department": "IT"}``

        Returns
        -------
        dict
            Risposta API con ``response.result.recordId`` del nuovo dipendente.
        """
        return self._client.post("v3/employee/addRecord", json=record_data)

    def update_record(
        self,
        employee_id: str,
        record_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Aggiorna i dati di un dipendente esistente.

        Endpoint: PUT /people/api/v3/employee/updateRecord

        Parameters
        ----------
        employee_id : str
            ID dipendente (empId).
        record_data : dict
            Campi da aggiornare.

        Returns
        -------
        dict
            Risposta API con esito dell'aggiornamento.
        """
        payload = {"empId": employee_id, **record_data}
        return self._client.put("v3/employee/updateRecord", json=payload)

    # ------------------------------------------------------------------
    # Helper: normalizza la lista per compatibilità
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_list(raw_list: List[Any]) -> List[Dict[str, Any]]:
        """
        Converte la risposta grezza nella struttura normalizzata::

            {
                "EmployeeRecordNumber": ...,
                "SurnameName":         ...,
                "Email":               ...,
                "EmployID":            ...,
                "ApiID":               ...,
            }

        Funziona sia con la risposta flat-list (vecchio formato / internal endpoint)
        che con la risposta dict (REST API v3).
        """
        result = []
        for emp in raw_list:
            if isinstance(emp, list):
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
        Cerca dipendenti e restituisce il risultato come stringa JSON.

        Parameters
        ----------
        query : str
            Stringa da cercare nel nome del dipendente.
        """
        results = self.search(query)
        return json.dumps(results, indent=4, sort_keys=True, ensure_ascii=False)
