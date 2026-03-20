"""
auth_manager.py
═══════════════════════════════════════════════════════════════════════════════
Gestione OAuth completamente automatica per Zoho Vertical Studio.

Funzionalità:
  - Primo avvio: guida l'utente a generare l'Authorization Code e lo scambia
    automaticamente con access_token + refresh_token
  - Salva le credenziali cifrate su file locale (.zoho_credentials.json)
  - Rinnova l'access_token automaticamente prima della scadenza
  - Ad ogni avvio successivo carica le credenziali salvate senza chiedere nulla
  - Supporta più data centre (US, EU, IN, AU, JP)

Utilizzo minimo:
    from auth_manager import ZohoAuthManager
    manager = ZohoAuthManager(client_id="...", client_secret="...")
    client  = manager.get_client()   # fa tutto da solo

Utilizzo da variabili d'ambiente:
    export ZOHO_CLIENT_ID="1000.xxx"
    export ZOHO_CLIENT_SECRET="yyy"
    from auth_manager import ZohoAuthManager
    manager = ZohoAuthManager.from_env()
    client  = manager.get_client()
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import sys
import time
import webbrowser
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlencode

import requests

# ---------------------------------------------------------------------------
# Aggiungi la directory corrente al path per importare l'SDK
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from zoho_vertical_sdk import ZohoVerticalClient, ZohoOAuthToken
    from zoho_vertical_sdk.exceptions import ZohoAuthError, ZohoAPIError
except ImportError:
    raise ImportError(
        "zoho_vertical_sdk non trovato. "
        "Assicurati che la cartella 'zoho_vertical_sdk/' sia nella stessa directory."
    )


# ═══════════════════════════════════════════════════════════════════════════ #
#  Costanti                                                                   #
# ═══════════════════════════════════════════════════════════════════════════ #

# Scope di default per timesheet + attendance + metadata
DEFAULT_SCOPES = [
    "ZohoPeople.attendance.ALL",
    "ZohoPeople.timetracker.ALL",
    "ZohoPeople.forms.ALL",
    "ZohoPeople.leave.ALL",
]

# Data centre → (api_domain, accounts_url)
DATA_CENTRES = {
    "US": ("https://people.zoho.com",    "https://accounts.zoho.com"),
    "EU": ("https://people.zoho.eu",     "https://accounts.zoho.eu"),
    "IN": ("https://people.zoho.in",     "https://accounts.zoho.in"),
    "AU": ("https://people.zoho.com.au", "https://accounts.zoho.com.au"),
    "JP": ("https://people.zoho.jp",     "https://accounts.zoho.jp"),
}

# File di credenziali di default
DEFAULT_CREDENTIALS_FILE = Path.home() / ".zoho_credentials.json"

# Margine di rinnovo: rinnova il token 5 minuti prima della scadenza
REFRESH_MARGIN_SECONDS = 300


# ═══════════════════════════════════════════════════════════════════════════ #
#  Struttura dati credenziali                                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

@dataclass
class ZohoCredentials:
    client_id:     str
    client_secret: str
    refresh_token: str
    access_token:  str       = ""
    token_expiry:  float     = 0.0   # timestamp UNIX
    data_centre:   str       = "US"
    scopes:        list      = field(default_factory=lambda: list(DEFAULT_SCOPES))

    @property
    def api_domain(self) -> str:
        return DATA_CENTRES[self.data_centre][0]

    @property
    def accounts_url(self) -> str:
        return DATA_CENTRES[self.data_centre][1]

    def is_access_token_valid(self) -> bool:
        if not self.access_token:
            return False
        return time.time() < (self.token_expiry - REFRESH_MARGIN_SECONDS)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ZohoCredentials":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ═══════════════════════════════════════════════════════════════════════════ #
#  Cifratura semplice (offuscamento, non crittografia forte)                  #
# ═══════════════════════════════════════════════════════════════════════════ #

def _derive_key(client_id: str) -> bytes:
    """Deriva una chiave da client_id per offuscare le credenziali salvate."""
    return hashlib.sha256(f"zoho-sdk-{client_id}".encode()).digest()

def _xor_bytes(data: bytes, key: bytes) -> bytes:
    return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

def _encode_credentials(creds: dict, client_id: str) -> str:
    """Serializza e offusca le credenziali per il salvataggio su disco."""
    raw = json.dumps(creds, ensure_ascii=False).encode("utf-8")
    key = _derive_key(client_id)
    obfuscated = _xor_bytes(raw, key)
    return base64.b64encode(obfuscated).decode("ascii")

def _decode_credentials(encoded: str, client_id: str) -> dict:
    """Decodifica le credenziali salvate su disco."""
    obfuscated = base64.b64decode(encoded.encode("ascii"))
    key = _derive_key(client_id)
    raw = _xor_bytes(obfuscated, key)
    return json.loads(raw.decode("utf-8"))


# ═══════════════════════════════════════════════════════════════════════════ #
#  Helpers di stampa                                                          #
# ═══════════════════════════════════════════════════════════════════════════ #

def _hr(w: int = 60) -> None:     print("─" * w)
def _ok(msg: str)   -> None:      print(f"  ✅  {msg}")
def _err(msg: str)  -> None:      print(f"  ❌  {msg}")
def _info(msg: str) -> None:      print(f"  ℹ️   {msg}")
def _ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    val = input(f"  → {prompt}{suffix}: ").strip()
    return val if val else default


# ═══════════════════════════════════════════════════════════════════════════ #
#  ZohoAuthManager                                                            #
# ═══════════════════════════════════════════════════════════════════════════ #

class ZohoAuthManager:
    """
    Gestisce l'intero ciclo di vita OAuth di Zoho Vertical Studio.

    Al primo avvio guida l'utente tramite CLI a:
      1. Scegliere il data centre
      2. Aprire il link di autorizzazione nel browser
      3. Incollare l'Authorization Code ricevuto
      4. Scambiarlo con access_token + refresh_token
      5. Salvare tutto su file cifrato

    Agli avvii successivi:
      - Carica le credenziali dal file
      - Rinnova l'access_token se scaduto o in scadenza
      - Restituisce un ZohoVerticalClient pronto all'uso

    Parameters
    ----------
    client_id : str
        Client ID del Self Client Zoho.
    client_secret : str
        Client Secret del Self Client Zoho.
    credentials_file : Path, optional
        Percorso del file di credenziali. Default: ~/.zoho_credentials.json
    scopes : list[str], optional
        Lista degli scope OAuth. Default: ALL modules + settings + bulk.
    data_centre : str, optional
        Data centre di default ('US','EU','IN','AU','JP'). Default 'US'.
        Viene ignorato se le credenziali sono già salvate.
    """

    def __init__(
        self,
        client_id: str,
        client_secret: str,
        credentials_file: Optional[Path] = None,
        scopes: Optional[list] = None,
        data_centre: str = "US",
        service_url: str = "",
    ):
        self.client_id     = client_id
        self.client_secret = client_secret
        self.credentials_file = credentials_file or DEFAULT_CREDENTIALS_FILE
        self.scopes        = scopes or list(DEFAULT_SCOPES)
        self.data_centre   = data_centre.upper()
        # Es: "/relewanthrm/zp" — path organizzativo Zoho People
        self.service_url   = service_url.strip()
        self._creds: Optional[ZohoCredentials] = None

    # ------------------------------------------------------------------
    # Costruttori alternativi
    # ------------------------------------------------------------------

    @classmethod
    def from_env(
        cls,
        credentials_file: Optional[Path] = None,
        scopes: Optional[list] = None,
    ) -> "ZohoAuthManager":
        """
        Costruisce il manager leggendo client_id e client_secret
        dalle variabili d'ambiente ZOHO_CLIENT_ID e ZOHO_CLIENT_SECRET.
        """
        client_id     = os.getenv("ZOHO_CLIENT_ID", "")
        client_secret = os.getenv("ZOHO_CLIENT_SECRET", "")
        data_centre   = os.getenv("ZOHO_DATA_CENTRE", "US").upper()
        service_url   = os.getenv("ZOHO_SERVICE_URL", "")

        if not client_id or not client_secret:
            raise ZohoAuthError(
                "ZOHO_CLIENT_ID e ZOHO_CLIENT_SECRET devono essere impostati "
                "come variabili d'ambiente."
            )
        return cls(
            client_id=client_id,
            client_secret=client_secret,
            credentials_file=credentials_file,
            scopes=scopes,
            data_centre=data_centre,
            service_url=service_url,
        )

    # ------------------------------------------------------------------
    # Entry point principale
    # ------------------------------------------------------------------

    def get_client(self) -> ZohoVerticalClient:
        """
        Restituisce un ZohoVerticalClient autenticato e pronto all'uso.

        - Se non ci sono credenziali salvate → avvia il flusso di primo login
        - Se le credenziali sono salvate     → carica e rinnova se necessario
        - Se l'access_token è valido         → lo usa direttamente

        Returns
        -------
        ZohoVerticalClient
        """
        self._ensure_credentials()
        self._ensure_valid_access_token()

        auth = ZohoOAuthToken(
            client_id=self.client_id,
            client_secret=self.client_secret,
            refresh_token=self._creds.refresh_token,
            access_token=self._creds.access_token,
            accounts_url=self._creds.accounts_url,
        )
        # Sovrascrivi il metodo di refresh dell'SDK con il nostro
        # (così salviamo automaticamente ogni nuovo token su disco)
        original_refresh = auth._do_refresh
        manager_self = self

        def _patched_refresh():
            original_refresh()
            # Salva il nuovo token su disco
            manager_self._creds.access_token = auth.access_token
            manager_self._creds.token_expiry = auth._token_expiry
            manager_self._save_credentials()

        auth._do_refresh = _patched_refresh

        return ZohoVerticalClient(
            auth=auth,
            api_domain=self._creds.api_domain,
            max_retries=3,
            retry_backoff=1.0,
            service_url=self.service_url,
        )

    # ------------------------------------------------------------------
    # Gestione credenziali
    # ------------------------------------------------------------------

    def _ensure_credentials(self) -> None:
        """Carica credenziali da file, oppure avvia il flusso di primo login."""
        if self._creds is not None:
            return

        loaded = self._load_credentials()
        if loaded:
            self._creds = loaded
            _ok(f"Credenziali caricate da {self.credentials_file}")
        else:
            _info("Nessuna credenziale trovata. Avvio il flusso di autenticazione...")
            self._creds = self._first_login_flow()
            self._save_credentials()
            _ok("Credenziali salvate. I prossimi avvii saranno automatici.")

    def _ensure_valid_access_token(self) -> None:
        """Rinnova l'access_token se scaduto o in scadenza."""
        if self._creds.is_access_token_valid():
            remaining = int(self._creds.token_expiry - time.time())
            _info(f"Access token valido (scade tra {remaining // 60}m {remaining % 60}s)")
            return

        _info("Access token scaduto o in scadenza. Rinnovo...")
        self._refresh_access_token()

    def _refresh_access_token(self) -> None:
        """Chiama l'endpoint token con grant_type=refresh_token."""
        url = f"{self._creds.accounts_url}/oauth/v2/token"
        params = {
            "grant_type":    "refresh_token",
            "client_id":     self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": self._creds.refresh_token,
        }
        try:
            resp = requests.post(url, params=params, timeout=30)
            data = resp.json()
        except Exception as e:
            raise ZohoAuthError(f"Errore durante il refresh del token: {e}")

        if "access_token" not in data:
            error = data.get("error", data)
            # Se il refresh token è scaduto/revocato → ri-login
            if "invalid_code" in str(error) or "expired" in str(error).lower():
                _err("Refresh token non valido. Avvio nuovo flusso di login...")
                self._creds = self._first_login_flow()
                self._save_credentials()
                return
            raise ZohoAuthError(f"Refresh fallito: {error}")

        self._creds.access_token = data["access_token"]
        expires_in = int(data.get("expires_in", 3600))
        self._creds.token_expiry = time.time() + expires_in
        self._save_credentials()
        _ok(f"Access token rinnovato (valido per {expires_in // 60} minuti)")

    # ------------------------------------------------------------------
    # Primo login
    # ------------------------------------------------------------------

    def _first_login_flow(self) -> ZohoCredentials:
        """
        Guida l'utente passo-passo a ottenere il refresh token.
        Tutto avviene nel terminale, nessun server browser necessario.
        """
        print()
        print("═" * 60)
        print("  🔐  Configurazione iniziale Zoho OAuth")
        print("═" * 60)

        # 1. Scegli data centre
        dc = self._ask_data_centre()
        api_domain, accounts_url = DATA_CENTRES[dc]

        # 2. Mostra link e istruzioni
        auth_code = self._guide_authorization_code(accounts_url, dc)

        # 3. Scambia code con token
        creds = self._exchange_code_for_tokens(
            auth_code, accounts_url, api_domain, dc
        )

        return creds

    def _ask_data_centre(self) -> str:
        """Chiede all'utente il data centre se non già configurato."""
        if self.data_centre in DATA_CENTRES:
            dc = self.data_centre
        else:
            dc = "US"

        print(f"\n  Data centre: {dc} ({DATA_CENTRES[dc][0]})")
        change = input("  → Vuoi cambiarlo? [s/N]: ").strip().lower()
        if change in ("s", "si", "sì", "y", "yes"):
            print()
            for i, (k, (api, _)) in enumerate(DATA_CENTRES.items(), 1):
                print(f"    {i}. {k}  –  {api}")
            raw = input("  → Scegli (1-5): ").strip()
            keys = list(DATA_CENTRES.keys())
            if raw.isdigit() and 1 <= int(raw) <= len(keys):
                dc = keys[int(raw) - 1]

        return dc

    def _guide_authorization_code(self, accounts_url: str, dc: str) -> str:
        """
        Genera il link di autorizzazione, lo apre nel browser,
        e aspetta che l'utente incolli il code.
        """
        scope_str = ",".join(self.scopes)

        # Per Self Client l'Authorization Code si genera direttamente
        # dalla Developer Console, non tramite redirect OAuth standard.
        # L'utente deve:
        #   1. Andare su accounts.zoho.*/developerconsole
        #   2. Aprire il Self Client
        #   3. Tab "Generate Code"
        #   4. Inserire gli scope
        #   5. Copiare il code generato

        dev_console_url = f"{accounts_url}/developerconsole"

        print()
        print("  Segui questi passi nel browser:")
        print()
        print(f"  1. Apri → {dev_console_url}")
        print("  2. Clicca su 'Self Client'")
        print("  3. Tab 'Generate Code'")
        print("  4. Nel campo 'Scope' incolla:")
        print()
        print(f"     {scope_str}")
        print()
        print("  5. Durata: scegli '10 minutes'")
        print("  6. Clicca 'Create'")
        print("  7. Copia il codice generato")
        print()

        # Prova ad aprire il browser automaticamente
        try:
            webbrowser.open(dev_console_url)
            _info("Browser aperto automaticamente")
        except Exception:
            _info("Apri manualmente l'URL sopra indicato")

        print()
        auth_code = ""
        while not auth_code:
            auth_code = _ask("Incolla qui l'Authorization Code").strip()
            if not auth_code:
                _err("Il codice non può essere vuoto. Riprova.")

        return auth_code

    def _exchange_code_for_tokens(
        self,
        auth_code: str,
        accounts_url: str,
        api_domain: str,
        dc: str,
    ) -> ZohoCredentials:
        """
        Chiama POST /oauth/v2/token per ottenere access_token e refresh_token.
        """
        _info("Scambio il codice con i token...")

        url = f"{accounts_url}/oauth/v2/token"
        params = {
            "grant_type":    "authorization_code",
            "client_id":     self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri":  "https://www.zoho.com/vertical-studio",
            "code":          auth_code,
        }

        try:
            resp = requests.post(url, params=params, timeout=30)
            data = resp.json()
        except Exception as e:
            raise ZohoAuthError(f"Errore di rete durante lo scambio del codice: {e}")

        if "refresh_token" not in data:
            error = data.get("error", str(data))
            msg = {
                "invalid_code":   "Il codice è scaduto o non valido. Riprova dal passo 1.",
                "invalid_client": "Client ID o Client Secret non corretti.",
                "access_denied":  "Accesso negato. Verifica gli scope richiesti.",
            }.get(error, f"Errore sconosciuto: {error}")
            raise ZohoAuthError(msg)

        access_token  = data["access_token"]
        refresh_token = data["refresh_token"]
        expires_in    = int(data.get("expires_in", 3600))
        token_expiry  = time.time() + expires_in

        _ok("Access token e Refresh token ottenuti con successo!")
        _info(f"Access token valido per {expires_in // 60} minuti")
        _info("Refresh token salvato – non scade (finché non lo revochi)")

        return ZohoCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret,
            refresh_token=refresh_token,
            access_token=access_token,
            token_expiry=token_expiry,
            data_centre=dc,
            scopes=list(self.scopes),
        )

    # ------------------------------------------------------------------
    # Persistenza
    # ------------------------------------------------------------------

    def _save_credentials(self) -> None:
        """Salva le credenziali offuscate su file."""
        if self._creds is None:
            return

        data = {
            "v":    1,
            "data": _encode_credentials(self._creds.to_dict(), self.client_id),
        }
        try:
            self.credentials_file.parent.mkdir(parents=True, exist_ok=True)
            self.credentials_file.write_text(
                json.dumps(data, indent=2), encoding="utf-8"
            )
            # Permessi restrittivi (solo owner su Unix)
            try:
                self.credentials_file.chmod(0o600)
            except Exception:
                pass
        except Exception as e:
            _err(f"Impossibile salvare le credenziali: {e}")

    def _load_credentials(self) -> Optional[ZohoCredentials]:
        """Carica e decodifica le credenziali dal file."""
        if not self.credentials_file.exists():
            return None

        try:
            raw = json.loads(self.credentials_file.read_text(encoding="utf-8"))
            if raw.get("v") != 1 or "data" not in raw:
                return None
            data = _decode_credentials(raw["data"], self.client_id)
            # Verifica che siano le credenziali del client_id corretto
            if data.get("client_id") != self.client_id:
                return None
            return ZohoCredentials.from_dict(data)
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Utilità pubbliche
    # ------------------------------------------------------------------

    def reset(self) -> None:
        """
        Cancella le credenziali salvate e forza un nuovo login
        al prossimo get_client().
        """
        self._creds = None
        if self.credentials_file.exists():
            self.credentials_file.unlink()
            _ok(f"Credenziali cancellate da {self.credentials_file}")

    def status(self) -> dict:
        """
        Restituisce lo stato attuale delle credenziali (senza esporre i secret).
        """
        if self._creds is None:
            self._ensure_credentials()

        valid = self._creds.is_access_token_valid()
        remaining = max(0, int(self._creds.token_expiry - time.time()))

        return {
            "client_id":      self._creds.client_id[:20] + "...",
            "data_centre":    self._creds.data_centre,
            "api_domain":     self._creds.api_domain,
            "scopes":         self._creds.scopes,
            "has_refresh_token": bool(self._creds.refresh_token),
            "access_token_valid": valid,
            "token_expires_in_seconds": remaining,
            "credentials_file": str(self.credentials_file),
        }

    def print_status(self) -> None:
        """Stampa lo stato delle credenziali in modo leggibile."""
        s = self.status()
        print()
        print("  📋  Stato autenticazione Zoho")
        _hr()
        print(f"  Client ID      : {s['client_id']}")
        print(f"  Data centre    : {s['data_centre']}  ({s['api_domain']})")
        print(f"  Scope          : {', '.join(s['scopes'])}")
        print(f"  Refresh token  : {'✅ presente' if s['has_refresh_token'] else '❌ assente'}")
        if s["access_token_valid"]:
            mins = s["token_expires_in_seconds"] // 60
            secs = s["token_expires_in_seconds"] % 60
            print(f"  Access token   : ✅ valido (scade tra {mins}m {secs}s)")
        else:
            print("  Access token   : ⚠️  scaduto (verrà rinnovato automaticamente)")
        print(f"  File credenziali: {s['credentials_file']}")
        print()
