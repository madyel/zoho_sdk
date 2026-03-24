"""
FilesAPI  –  Zoho People Files REST API v3
===========================================

Endpoint:
    GET    v3/files/folders          (lista cartelle)
    GET    v3/files                  (lista file in una cartella)
    POST   v3/files                  (carica file)
    GET    v3/files/{file_id}/download  (scarica file)
    DELETE v3/files/{file_id}        (elimina file)

Scope OAuth: ZOHOPEOPLE.files.READ / ZOHOPEOPLE.files.CREATE
             ZOHOPEOPLE.files.DELETE
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class FilesAPI:
    """
    Wrapper per le API Zoho People Files v3.

    Usato tramite:
        client.files.get_folders()
        client.files.get_files(folder_id)
        client.files.upload_file(file_path, folder_id)
        client.files.download_file(file_id)
        client.files.delete_file(file_id)
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    def get_folders(
        self,
        parent_folder_id: Optional[str] = None,
        limit: int = 200,
    ) -> List[Dict[str, Any]]:
        """
        Recupera le cartelle.

        Endpoint: GET v3/files/folders

        Parameters
        ----------
        parent_folder_id : str, optional
            ID della cartella padre (per sottocartelle).
        limit : int
            Numero massimo di record.
        """
        params: Dict[str, Any] = {"limit": limit}
        if parent_folder_id:
            params["parent_folder_id"] = parent_folder_id
        data   = self._client.get("v3/files/folders", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    def get_files(
        self,
        folder_id: str,
        limit: int = 200,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Recupera i file di una cartella.

        Endpoint: GET v3/files

        Parameters
        ----------
        folder_id : str
            ID della cartella.
        limit : int
            Numero massimo di record.
        offset : int
            Offset di paginazione.
        """
        params: Dict[str, Any] = {"folder_id": folder_id, "limit": limit, "offset": offset}
        data   = self._client.get("v3/files", params=params)
        result = data.get("data", data.get("response", {}).get("result", []))
        return result if isinstance(result, list) else []

    def upload_file(
        self,
        file_path: str,
        folder_id: str,
        employee_zoho_id: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Carica un file nella cartella specificata.

        Endpoint: POST v3/files

        Parameters
        ----------
        file_path : str
            Percorso del file da caricare.
        folder_id : str
            ID della cartella di destinazione.
        employee_zoho_id : str, optional
            ID Zoho del dipendente a cui associare il file.
        file_name : str, optional
            Nome del file (default: nome originale).
        """
        data: Dict[str, Any] = {"folder_id": folder_id}
        if employee_zoho_id:
            data["employee_zoho_id"] = employee_zoho_id
        name = file_name or os.path.basename(file_path)
        if file_name:
            data["file_name"] = file_name
        with open(file_path, "rb") as f:
            return self._client.upload("v3/files", files={"file": (name, f)}, data=data)

    def download_file(self, file_id: str) -> bytes:
        """
        Scarica il contenuto binario di un file.

        Endpoint: GET v3/files/{file_id}/download

        Parameters
        ----------
        file_id : str
            ID univoco del file.

        Returns
        -------
        bytes
            Contenuto binario del file.
        """
        return self._client.get(f"v3/files/{file_id}/download")

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Elimina un file.

        Endpoint: DELETE v3/files/{file_id}
        """
        return self._client.delete(f"v3/files/{file_id}")
