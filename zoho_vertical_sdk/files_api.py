"""
FilesAPI  –  Zoho People Files REST API
========================================

Gestisce documenti e cartelle nell'archivio Zoho People.

Endpoint:
    POST /files/addFile
    PUT  /files/editFile
    DELETE /files/deleteFile
    GET  /files/getFolders
    GET  /files/getAllFiles
    GET  /files/getFolderView
    GET  /files/getSubfolders
    GET  /files/viewFile
    GET  /files/downloadFile
    GET  /files/getAllowedFolders
    GET  /files/getShareOptions
    POST /files/addAcknowledgement
    GET  /files/getAckDetails
    POST /files/addFolder
    PUT  /files/editFolder
    GET  /files/getAckListByUser

Scope OAuth: ZohoPeople.files.ALL
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional

if TYPE_CHECKING:
    from .client import ZohoVerticalClient


class FilesAPI:
    """
    Wrapper per le API Zoho People Files.

    Usato tramite:
        client.files.get_folders()
        client.files.get_all_files(folder_id)
        client.files.get_allowed_folders()
    """

    def __init__(self, client: "ZohoVerticalClient"):
        self._client = client

    # ------------------------------------------------------------------
    # Cartelle
    # ------------------------------------------------------------------

    def get_folders(self) -> List[Dict[str, Any]]:
        """
        Recupera tutte le cartelle.

        Endpoint: GET /files/getFolders
        """
        data     = self._client.get("v3/files/getFolders")
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def get_allowed_folders(self) -> List[Dict[str, Any]]:
        """
        Recupera le cartelle accessibili all'utente corrente.

        Endpoint: GET /files/getAllowedFolders
        """
        data     = self._client.get("v3/files/getAllowedFolders")
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def get_folder_view(self, folder_id: str) -> Dict[str, Any]:
        """
        Recupera la vista di una cartella.

        Endpoint: GET /files/getFolderView
        """
        return self._client.get("v3/files/getFolderView", params={"folderId": folder_id})

    def get_subfolders(self, folder_id: str) -> List[Dict[str, Any]]:
        """
        Recupera le sottocartelle di una cartella.

        Endpoint: GET /files/getSubfolders
        """
        data     = self._client.get("v3/files/getSubfolders", params={"folderId": folder_id})
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def add_folder(
        self,
        folder_name: str,
        parent_folder_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Crea una nuova cartella.

        Endpoint: POST /files/addFolder
        """
        payload: Dict[str, Any] = {"folderName": folder_name}
        if parent_folder_id:
            payload["parentFolderId"] = parent_folder_id
        return self._client.form_post("v3/files/addFolder", data=payload)

    def edit_folder(self, folder_id: str, folder_name: str) -> Dict[str, Any]:
        """
        Rinomina una cartella.

        Endpoint: PUT /files/editFolder
        """
        payload: Dict[str, Any] = {"folderId": folder_id, "folderName": folder_name}
        return self._client.put("v3/files/editFolder", json=payload)

    # ------------------------------------------------------------------
    # File
    # ------------------------------------------------------------------

    def get_all_files(
        self,
        folder_id: str,
        page: int = 1,
    ) -> List[Dict[str, Any]]:
        """
        Recupera tutti i file di una cartella.

        Endpoint: GET /files/getAllFiles
        """
        params: Dict[str, Any] = {"folderId": folder_id, "sIndex": page}
        data     = self._client.get("v3/files/getAllFiles", params=params)
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []

    def view_file(self, file_id: str) -> Dict[str, Any]:
        """
        Visualizza i dettagli di un file.

        Endpoint: GET /files/viewFile
        """
        return self._client.get("v3/files/viewFile", params={"fileId": file_id})

    def download_file(self, file_id: str) -> bytes:
        """
        Scarica il contenuto binario di un file.

        Endpoint: GET /files/downloadFile

        Parameters
        ----------
        file_id : str
            ID univoco del file.

        Returns
        -------
        bytes
            Contenuto binario del file.
        """
        return self._client.get("v3/files/downloadFile", params={"fileId": file_id})

    def get_share_options(self, file_id: str) -> Dict[str, Any]:
        """
        Recupera le opzioni di condivisione di un file.

        Endpoint: GET /files/getShareOptions
        """
        return self._client.get("v3/files/getShareOptions", params={"fileId": file_id})

    def add_file(
        self,
        file_path: str,
        folder_id: str,
        employee_id: Optional[str] = None,
        file_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Carica un nuovo file nella cartella specificata.

        Endpoint: POST /files/addFile

        Parameters
        ----------
        file_path : str
            Percorso del file da caricare.
        folder_id : str
            ID della cartella di destinazione.
        employee_id : str, optional
            ID dipendente a cui associare il file.
        file_name : str, optional
            Nome del file (default: nome originale del file).
        """
        import os
        data: Dict[str, Any] = {"folderId": folder_id}
        if employee_id:
            data["employeeId"] = employee_id
        if file_name:
            data["fileName"] = file_name
        name = file_name or os.path.basename(file_path)
        with open(file_path, "rb") as f:
            return self._client.upload("v3/files/addFile",
                                       files={"file": (name, f)},
                                       data=data)

    def edit_file(self, file_id: str, file_name: str) -> Dict[str, Any]:
        """
        Rinomina un file.

        Endpoint: PUT /files/editFile
        """
        payload: Dict[str, Any] = {"fileId": file_id, "fileName": file_name}
        return self._client.put("v3/files/editFile", json=payload)

    def delete_file(self, file_id: str) -> Dict[str, Any]:
        """
        Elimina un file.

        Endpoint: DELETE /files/deleteFile
        """
        return self._client.delete("v3/files/deleteFile", params={"fileId": file_id})

    # ------------------------------------------------------------------
    # Acknowledgement
    # ------------------------------------------------------------------

    def add_acknowledgement(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Aggiunge una conferma di lettura per un file.

        Endpoint: POST /files/addAcknowledgement
        """
        payload: Dict[str, Any] = {"fileId": file_id, "userId": user_id}
        return self._client.form_post("v3/files/addAcknowledgement", data=payload)

    def get_ack_details(self, file_id: str) -> Dict[str, Any]:
        """
        Recupera i dettagli delle conferme di lettura di un file.

        Endpoint: GET /files/getAckDetails
        """
        return self._client.get("v3/files/getAckDetails", params={"fileId": file_id})

    def get_ack_list_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Recupera la lista delle conferme di lettura per un dipendente.

        Endpoint: GET /files/getAckListByUser
        """
        data     = self._client.get("v3/files/getAckListByUser", params={"userId": user_id})
        response = data.get("response", data)
        result   = response.get("result", [])
        return result if isinstance(result, list) else []
