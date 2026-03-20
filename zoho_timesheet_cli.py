#!/usr/bin/env python3
"""
zoho_timesheet_cli.py
=====================
CLI interattivo per inviare Timesheet e Attendance a Zoho Vertical Studio.

Funzionalità:
  1. Autenticazione OAuth completamente automatica (primo login guidato,
     poi rinnovo silenzioso del token ad ogni avvio)
  2. Esplora i moduli disponibili e individua automaticamente quelli di
     timesheet / attendance / presenze
  3. Legge i campi del modulo selezionato per sapere cosa compilare
  4. Modalità SINGOLA   – inserisci manualmente un record
  5. Modalità SETTIMANA – genera automaticamente i record per 5 giorni lavorativi
  6. Modalità MESE      – genera automaticamente i record per tutti i giorni lavorativi del mese

Prerequisiti:
    pip install requests

Utilizzo al primo avvio (ti chiede Client ID e Secret una volta sola):
    python zoho_timesheet_cli.py

Utilizzo con variabili d'ambiente (opzionale):
    export ZOHO_CLIENT_ID="1000.xxx"
    export ZOHO_CLIENT_SECRET="yyy"
    python zoho_timesheet_cli.py

Le credenziali vengono salvate automaticamente in ~/.zoho_credentials.json
e riutilizzate ad ogni avvio successivo senza chiedere nulla.
"""

from __future__ import annotations

import os
import sys
import json
from datetime import date, timedelta, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Assicurati che la cartella del progetto sia nel path
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from zoho_vertical_sdk import ZohoVerticalClient, ZohoOAuthToken
    from zoho_vertical_sdk.exceptions import ZohoAPIError, ZohoNotFoundError
    from auth_manager import ZohoAuthManager
except ImportError as _e:
    print(f"❌  Impossibile importare i moduli necessari: {_e}")
    print("   Assicurati che 'zoho_vertical_sdk/' e 'auth_manager.py' siano nella stessa directory.")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════ #
#  Costanti / parole chiave per rilevamento automatico dei moduli            #
# ═══════════════════════════════════════════════════════════════════════════ #

TIMESHEET_KEYWORDS = [
    "timesheet", "time_sheet", "timelog", "time_log",
    "ore", "hours", "workhour", "work_hour", "horas",
    "timeentry", "time_entry", "timereport",
]

ATTENDANCE_KEYWORDS = [
    "attendance", "presenz", "timbratur", "check_in", "checkin",
    "check_out", "checkout", "presence", "leave", "ferie",
    "permesso", "assenz", "shift",
]


# ═══════════════════════════════════════════════════════════════════════════ #
#  Helpers di formattazione                                                  #
# ═══════════════════════════════════════════════════════════════════════════ #

def hr(char: str = "─", width: int = 60) -> None:
    print(char * width)

def header(title: str) -> None:
    print()
    hr("═")
    print(f"  {title}")
    hr("═")

def section(title: str) -> None:
    print()
    hr()
    print(f"  {title}")
    hr()

def ok(msg: str) -> None:
    print(f"  ✅  {msg}")

def err(msg: str) -> None:
    print(f"  ❌  {msg}")

def warn(msg: str) -> None:
    print(f"  ⚠️   {msg}")

def info(msg: str) -> None:
    print(f"  ℹ️   {msg}")

def ask(prompt: str, default: str = "") -> str:
    """Legge input dall'utente con valore di default opzionale."""
    suffix = f" [{default}]" if default else ""
    value = input(f"  → {prompt}{suffix}: ").strip()
    return value if value else default

def choose(prompt: str, options: List[str], allow_skip: bool = False) -> int:
    """Mostra un menu numerato e restituisce l'indice (0-based) scelto."""
    print(f"\n  {prompt}")
    for i, opt in enumerate(options, 1):
        print(f"    {i}. {opt}")
    if allow_skip:
        print(f"    0. Salta / Torna indietro")
    while True:
        raw = input("  → Scelta: ").strip()
        if allow_skip and raw == "0":
            return -1
        if raw.isdigit():
            idx = int(raw) - 1
            if 0 <= idx < len(options):
                return idx
        print("  ⚠️  Scelta non valida, riprova.")

def confirm(prompt: str, default: bool = True) -> bool:
    suffix = "[S/n]" if default else "[s/N]"
    raw = input(f"  → {prompt} {suffix}: ").strip().lower()
    if not raw:
        return default
    return raw in ("s", "si", "sì", "y", "yes")


# ═══════════════════════════════════════════════════════════════════════════ #
#  Connessione – completamente automatica via ZohoAuthManager                #
# ═══════════════════════════════════════════════════════════════════════════ #

CONFIG_FILE = Path(__file__).parent / "zoho_config.json"
CREDS_FILE  = Path.home() / ".zoho_credentials.json"


def _load_config() -> dict:
    """Legge zoho_config.json (solo client_id e data_centre, NON segreti)."""
    if CONFIG_FILE.exists():
        try:
            return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _save_config(client_id: str, dc: str) -> None:
    """Salva client_id e data_centre in zoho_config.json."""
    data = {
        "_comment": "Contiene solo client_id e data_centre (NON segreti). "
                    "Le credenziali sensibili sono in ~/.zoho_credentials.json",
        "client_id":   client_id,
        "data_centre": dc,
    }
    try:
        CONFIG_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        warn(f"Impossibile salvare la configurazione: {e}")


def setup_client() -> ZohoVerticalClient:
    """
    Gestisce l'autenticazione in modo completamente automatico.

    Strategia (in ordine di priorità):
      1. Variabili d'ambiente ZOHO_CLIENT_ID + ZOHO_CLIENT_SECRET
      2. zoho_config.json  (client_id) + ~/.zoho_credentials.json (segreti cifrati)
      3. Input interattivo da terminale (solo al primo avvio)

    Dal secondo avvio in poi non viene chiesto nulla:
    client_id  →  zoho_config.json       (testo in chiaro, non sensibile)
    segreti    →  ~/.zoho_credentials.json (cifrati con XOR + base64)
    """
    header("🔐  Autenticazione Zoho Vertical Studio")

    cfg = _load_config()

    # ── 1. Prova env vars ─────────────────────────────────────────────────
    client_id     = os.getenv("ZOHO_CLIENT_ID",     cfg.get("client_id", ""))
    client_secret = os.getenv("ZOHO_CLIENT_SECRET", "")
    dc            = os.getenv("ZOHO_DATA_CENTRE",   cfg.get("data_centre", "EU")).upper()

    if client_id:
        info(f"Client ID caricato: {client_id[:20]}…")
    if client_secret:
        info("Client Secret caricato da variabile d'ambiente")

    # ── 2. Se non abbiamo client_id chiediamolo (prima volta) ─────────────
    if not client_id:
        print()
        print("  ╔══════════════════════════════════════════════════════╗")
        print("  ║        Prima configurazione – un'operazione sola     ║")
        print("  ╚══════════════════════════════════════════════════════╝")
        print()
        print("  Trovi le credenziali su:")
        print("  accounts.zoho.com/developerconsole → Self Client → Client Secret")
        print()
        client_id = ask("Client ID  (es. 1000.C29G99K98...)").strip()
        if not client_id:
            err("Client ID obbligatorio.")
            sys.exit(1)

    # ── 3. Se non abbiamo client_secret chiediamolo ────────────────────────
    #       (serve solo se le credenziali NON sono ancora salvate su disco)
    creds_exist = CREDS_FILE.exists()
    if not client_secret and not creds_exist:
        client_secret = ask("Client Secret").strip()
        if not client_secret:
            err("Client Secret obbligatorio.")
            sys.exit(1)
    elif not client_secret and creds_exist:
        # Le credenziali sono già salvate: ZohoAuthManager le caricherà
        # senza bisogno del client_secret in chiaro.
        # Usiamo una stringa segnaposto che il manager ignorerà.
        client_secret = "__loaded_from_file__"

    # ── 4. Data centre ────────────────────────────────────────────────────
    if dc not in ("US", "EU", "IN", "AU", "JP"):
        dc = "EU"

    # ── 5. Salva config (client_id + dc, NON il secret) ──────────────────
    _save_config(client_id, dc)

    # ── 6. Crea manager e ottieni client ──────────────────────────────────
    try:
        # Se il secret è il segnaposto, il manager userà quello salvato su disco
        actual_secret = (
            client_secret
            if client_secret != "__loaded_from_file__"
            else _get_secret_from_creds_file(client_id)
        )

        manager = ZohoAuthManager(
            client_id=client_id,
            client_secret=actual_secret,
            data_centre=dc,
        )
        c = manager.get_client()
        manager.print_status()
        return c

    except Exception as e:
        err(f"Autenticazione fallita: {e}")
        info("Suggerimento: verifica Client ID e Client Secret e riprova.")
        info(f"Per ricominciare da capo elimina: {CREDS_FILE}")
        sys.exit(1)


def _get_secret_from_creds_file(client_id: str) -> str:
    """
    Estrae il client_secret dal file di credenziali cifrato.
    Usato quando le credenziali sono già salvate e non serve ri-chiederlo.
    """
    import base64, hashlib

    def _derive_key(cid: str) -> bytes:
        return hashlib.sha256(f"zoho-sdk-{cid}".encode()).digest()

    def _xor_bytes(data: bytes, key: bytes) -> bytes:
        return bytes(b ^ key[i % len(key)] for i, b in enumerate(data))

    try:
        raw = json.loads(CREDS_FILE.read_text(encoding="utf-8"))
        if raw.get("v") != 1 or "data" not in raw:
            return ""
        obfuscated = base64.b64decode(raw["data"].encode("ascii"))
        key = _derive_key(client_id)
        decoded = _xor_bytes(obfuscated, key)
        creds = json.loads(decoded.decode("utf-8"))
        return creds.get("client_secret", "")
    except Exception:
        return ""


# ═══════════════════════════════════════════════════════════════════════════ #
#  Esplorazione moduli                                                       #
# ═══════════════════════════════════════════════════════════════════════════ #

def detect_modules(client: ZohoVerticalClient) -> Tuple[List[dict], List[dict], List[dict]]:
    """
    Recupera tutti i moduli e li classifica in:
      - timesheet_modules
      - attendance_modules
      - all_api_modules (per selezione manuale)
    """
    section("🔍  Esplorazione moduli disponibili")
    info("Recupero lista moduli da Zoho...")

    try:
        all_modules = client.modules.list_modules()
    except ZohoAPIError as e:
        err(f"Impossibile recuperare i moduli: {e.message}")
        sys.exit(1)

    api_modules = [m for m in all_modules if m.get("api_supported", False)]

    timesheet_modules: List[dict] = []
    attendance_modules: List[dict] = []

    for m in api_modules:
        name_lower = (
            m.get("api_name", "").lower() + " " +
            m.get("plural_label", "").lower() + " " +
            m.get("singular_label", "").lower()
        )
        if any(kw in name_lower for kw in TIMESHEET_KEYWORDS):
            timesheet_modules.append(m)
        elif any(kw in name_lower for kw in ATTENDANCE_KEYWORDS):
            attendance_modules.append(m)

    ok(f"Trovati {len(api_modules)} moduli con supporto API")

    if timesheet_modules:
        print(f"\n  📋  Moduli Timesheet rilevati automaticamente:")
        for m in timesheet_modules:
            print(f"       • {m['api_name']:30}  ({m['plural_label']})")
    else:
        warn("Nessun modulo timesheet rilevato automaticamente.")

    if attendance_modules:
        print(f"\n  📋  Moduli Attendance rilevati automaticamente:")
        for m in attendance_modules:
            print(f"       • {m['api_name']:30}  ({m['plural_label']})")
    else:
        warn("Nessun modulo attendance rilevato automaticamente.")

    return timesheet_modules, attendance_modules, api_modules


def select_module(
    label: str,
    auto_candidates: List[dict],
    all_modules: List[dict],
) -> Optional[dict]:
    """Chiede all'utente di scegliere un modulo per timesheet o attendance."""
    section(f"📌  Selezione modulo {label}")

    options = []
    module_list = []

    if auto_candidates:
        for m in auto_candidates:
            options.append(f"[AUTO] {m['api_name']}  –  {m['plural_label']}")
            module_list.append(m)

    options.append("Scegli manualmente da tutti i moduli disponibili")
    options.append("Salta (non inviare dati di questo tipo)")

    idx = choose(f"Quale modulo usi per {label}?", options)

    if idx == len(options) - 1:
        return None  # salta

    if idx == len(options) - 2:
        # selezione manuale
        all_options = [f"{m['api_name']:35}  {m['plural_label']}" for m in all_modules]
        all_options.append("← Torna indietro")
        manual_idx = choose("Seleziona il modulo:", all_options, allow_skip=True)
        if manual_idx < 0 or manual_idx >= len(all_modules):
            return None
        return all_modules[manual_idx]

    return module_list[idx]


# ═══════════════════════════════════════════════════════════════════════════ #
#  Lettura campi del modulo                                                  #
# ═══════════════════════════════════════════════════════════════════════════ #

# Tipi di campo che escludiamo dal form interattivo (sistema / auto)
SKIP_FIELD_TYPES = {
    "autonumber", "formula", "profileimage",
    "ownerlookup", "userlookup",
}

# Campi di sistema da ignorare sempre
SKIP_FIELD_NAMES = {
    "id", "created_time", "modified_time", "created_by", "modified_by",
    "tag", "record_approval_state__s",
}


def get_module_fields(client: ZohoVerticalClient, module_api_name: str) -> List[dict]:
    """Recupera i campi di un modulo filtrando quelli non editabili."""
    try:
        fields = client.metadata.get_fields(module_api_name)
    except ZohoAPIError as e:
        warn(f"Impossibile leggere i campi di {module_api_name}: {e.message}")
        return []

    editable = []
    for f in fields:
        if not f.get("editable", True):
            continue
        if f.get("read_only", False):
            continue
        api_name = f.get("api_name", "").lower()
        dtype = f.get("data_type", "").lower()
        if api_name in SKIP_FIELD_NAMES:
            continue
        if dtype in SKIP_FIELD_TYPES:
            continue
        editable.append(f)

    return editable


def print_fields_table(fields: List[dict]) -> None:
    print()
    print(f"  {'Campo API':35} {'Tipo':20} {'Obbligatorio'}")
    hr("-", 70)
    for f in fields:
        required = "✱ RICHIESTO" if f.get("system_mandatory") or f.get("required") else ""
        print(f"  {f['api_name']:35} {f.get('data_type',''):20} {required}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  Input interattivo di un singolo record                                    #
# ═══════════════════════════════════════════════════════════════════════════ #

DATE_FORMATS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y"]
DATETIME_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d %H:%M", "%d/%m/%Y %H:%M",
]

def parse_date(s: str) -> Optional[str]:
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    return None

def parse_datetime(s: str) -> Optional[str]:
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        except ValueError:
            pass
    return None

def input_field(field: dict, prefill: Dict[str, Any] = {}) -> Tuple[str, Any]:
    """
    Chiede all'utente il valore per un campo.
    Restituisce (api_name, value) o (api_name, None) se saltato.
    """
    api_name = field["api_name"]
    dtype = field.get("data_type", "text").lower()
    label = field.get("display_label") or field.get("field_label") or api_name
    required = field.get("system_mandatory") or field.get("required", False)
    req_str = " [RICHIESTO]" if required else " [opzionale, invio=salta]"

    default = prefill.get(api_name, "")

    print(f"\n  {label}  ({dtype}){req_str}")

    while True:
        if dtype in ("date",):
            raw = ask(f"{api_name}  [YYYY-MM-DD o GG/MM/YYYY]", str(default))
            if not raw and not required:
                return api_name, None
            parsed = parse_date(raw)
            if parsed:
                return api_name, parsed
            warn("Formato data non valido. Esempi: 2025-03-20 oppure 20/03/2025")

        elif dtype in ("datetime",):
            raw = ask(f"{api_name}  [YYYY-MM-DD HH:MM]", str(default))
            if not raw and not required:
                return api_name, None
            parsed = parse_datetime(raw)
            if parsed:
                return api_name, parsed
            warn("Formato datetime non valido. Esempio: 2025-03-20 09:00")

        elif dtype in ("integer", "biginteger"):
            raw = ask(api_name, str(default))
            if not raw and not required:
                return api_name, None
            if raw.lstrip("-").isdigit():
                return api_name, int(raw)
            warn("Inserisci un numero intero.")

        elif dtype in ("decimal", "double", "currency", "number"):
            raw = ask(api_name, str(default))
            if not raw and not required:
                return api_name, None
            try:
                return api_name, float(raw.replace(",", "."))
            except ValueError:
                warn("Inserisci un numero (es. 8.5)")

        elif dtype == "boolean":
            raw = ask(f"{api_name} [true/false]", str(default).lower())
            if not raw and not required:
                return api_name, None
            return api_name, raw.lower() in ("true", "1", "si", "sì", "yes", "s")

        elif dtype == "picklist":
            values = [v.get("actual_value") or v.get("display_value", "")
                      for v in field.get("pick_list_values", [])]
            if values:
                options = values + ["[salta]"]
                idx = choose(f"Scegli valore per {api_name}:", options)
                if idx == len(values):
                    if required:
                        warn("Questo campo è obbligatorio.")
                        continue
                    return api_name, None
                return api_name, values[idx]
            else:
                raw = ask(api_name, str(default))
                return api_name, raw if raw else None

        elif dtype == "multiselectpicklist":
            values = [v.get("actual_value") or v.get("display_value", "")
                      for v in field.get("pick_list_values", [])]
            if values:
                print(f"  Opzioni: {', '.join(values)}")
            raw = ask(f"{api_name} (valori separati da ;)", str(default))
            if not raw and not required:
                return api_name, None
            return api_name, raw

        elif dtype == "lookup":
            raw = ask(f"{api_name} (ID del record collegato)", str(default))
            if not raw and not required:
                return api_name, None
            if raw:
                return api_name, {"id": raw}
            return api_name, None

        else:
            # text, textarea, email, phone, url, …
            raw = ask(api_name, str(default))
            if not raw and not required:
                return api_name, None
            return api_name, raw if raw else None


def build_record_interactive(
    fields: List[dict],
    prefill: Dict[str, Any] = {},
    title: str = "Inserimento record",
) -> Dict[str, Any]:
    """Guida l'utente campo per campo e restituisce il dict del record."""
    print(f"\n  📝  {title}")
    hr("-")
    record: Dict[str, Any] = {}

    for field in fields:
        api_name, value = input_field(field, prefill)
        if value is not None:
            record[api_name] = value

    return record


# ═══════════════════════════════════════════════════════════════════════════ #
#  Generazione range di date                                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

def workdays_in_week(ref_date: date) -> List[date]:
    """Restituisce i giorni lavorativi (lun-ven) della settimana di ref_date."""
    monday = ref_date - timedelta(days=ref_date.weekday())
    return [monday + timedelta(days=i) for i in range(5)]


def workdays_in_month(year: int, month: int) -> List[date]:
    """Restituisce tutti i giorni lun-ven del mese dato."""
    days = []
    d = date(year, month, 1)
    while d.month == month:
        if d.weekday() < 5:  # 0=lun … 4=ven
            days.append(d)
        d += timedelta(days=1)
    return days


def ask_period_week() -> List[date]:
    """Chiede all'utente una settimana e restituisce i giorni lavorativi."""
    section("📅  Settimana di riferimento")
    today_str = date.today().strftime("%d/%m/%Y")
    raw = ask("Inserisci una data nella settimana desiderata", today_str)
    parsed = parse_date(raw)
    if not parsed:
        warn("Data non valida, uso la settimana corrente.")
        ref = date.today()
    else:
        ref = date.fromisoformat(parsed)

    days = workdays_in_week(ref)
    print(f"\n  Settimana selezionata:")
    for d in days:
        print(f"    • {d.strftime('%A %d/%m/%Y')}")
    return days


def ask_period_month() -> List[date]:
    """Chiede all'utente mese/anno e restituisce i giorni lavorativi."""
    section("📅  Mese di riferimento")
    now = date.today()
    raw_month = ask("Mese (1-12)", str(now.month))
    raw_year  = ask("Anno",        str(now.year))

    try:
        month = int(raw_month)
        year  = int(raw_year)
        if not (1 <= month <= 12):
            raise ValueError
    except ValueError:
        warn("Valori non validi, uso il mese corrente.")
        month, year = now.month, now.year

    days = workdays_in_month(year, month)
    print(f"\n  Giorni lavorativi in {month:02d}/{year}: {len(days)}")
    return days


# ═══════════════════════════════════════════════════════════════════════════ #
#  Rilevamento automatico campi data/ora nel modulo                          #
# ═══════════════════════════════════════════════════════════════════════════ #

DATE_FIELD_HINTS   = ["date", "data", "day", "giorno", "work_date", "attendance_date"]
CHECKIN_HINTS      = ["check_in", "checkin", "in_time",  "start", "inizio", "ora_inizio", "from"]
CHECKOUT_HINTS     = ["check_out","checkout","out_time", "end",   "fine",   "ora_fine",   "to"]
HOURS_HINTS        = ["hours", "ore", "duration", "durata", "worked", "lavorate", "total"]

def find_field_by_hints(fields: List[dict], hints: List[str]) -> Optional[dict]:
    for f in fields:
        name = f["api_name"].lower()
        label = (f.get("display_label") or f.get("field_label") or "").lower()
        if any(h in name or h in label for h in hints):
            return f
    return None


# ═══════════════════════════════════════════════════════════════════════════ #
#  Invio batch                                                               #
# ═══════════════════════════════════════════════════════════════════════════ #

def send_records(
    client: ZohoVerticalClient,
    module_api_name: str,
    records: List[Dict[str, Any]],
    dry_run: bool = False,
) -> None:
    """Invia i record in batch da max 100 e stampa i risultati."""
    if dry_run:
        section("🧪  DRY RUN – I record NON vengono inviati")
        for i, r in enumerate(records, 1):
            print(f"  Record {i:>3}: {json.dumps(r, ensure_ascii=False, default=str)}")
        return

    section(f"📤  Invio {len(records)} record a '{module_api_name}'")
    BATCH = 100
    success_count = 0
    error_count = 0

    for batch_start in range(0, len(records), BATCH):
        batch = records[batch_start:batch_start + BATCH]
        print(f"  Invio batch {batch_start + 1}–{batch_start + len(batch)}…", end=" ", flush=True)
        try:
            results = client.records.create(module_api_name, batch)
            for r in results:
                if r.get("code") == "SUCCESS":
                    success_count += 1
                else:
                    error_count += 1
                    warn(f"Errore record: {r.get('message')} – {r.get('details', {})}")
            print("✅")
        except ZohoAPIError as e:
            print("❌")
            err(f"Batch fallito: {e.message}")
            error_count += len(batch)

    print()
    ok(f"Completato: {success_count} record creati, {error_count} errori.")


# ═══════════════════════════════════════════════════════════════════════════ #
#  Flusso TIMESHEET                                                          #
# ═══════════════════════════════════════════════════════════════════════════ #

def flow_timesheet(client: ZohoVerticalClient, module: dict) -> None:
    module_name = module["api_name"]
    header(f"⏱  Timesheet  →  {module['plural_label']}  ({module_name})")

    # Campi del modulo
    info("Recupero campi del modulo…")
    fields = get_module_fields(client, module_name)
    if not fields:
        warn("Nessun campo trovato o non accessibile.")
        return

    print_fields_table(fields)

    # Rileva automaticamente campo data e ore
    date_field   = find_field_by_hints(fields, DATE_FIELD_HINTS)
    hours_field  = find_field_by_hints(fields, HOURS_HINTS)

    if date_field:
        info(f"Campo data rilevato automaticamente: {date_field['api_name']}")
    if hours_field:
        info(f"Campo ore rilevato automaticamente:  {hours_field['api_name']}")

    # Modalità
    mode_options = [
        "Singolo record (inserimento manuale completo)",
        "Settimana  – stesse ore per ogni giorno lavorativo",
        "Mese       – stesse ore per ogni giorno lavorativo",
    ]
    mode_idx = choose("Modalità di inserimento:", mode_options)

    # ------------------------------------------------------------------
    if mode_idx == 0:  # SINGOLO
        record = build_record_interactive(fields, title="Nuovo record Timesheet")
        if not record:
            warn("Nessun dato inserito.")
            return
        dry = confirm("Vuoi fare un DRY RUN (non invia realmente)?", default=False)
        send_records(client, module_name, [record], dry_run=dry)

    # ------------------------------------------------------------------
    elif mode_idx in (1, 2):  # SETTIMANA o MESE
        days = ask_period_week() if mode_idx == 1 else ask_period_month()

        # Chiedi un "record template" (senza il campo data)
        fields_no_date = [f for f in fields if f != date_field] if date_field else fields

        print(f"\n  Inserisci i valori comuni per TUTTI i {len(days)} giorni.")
        print("  (il campo data verrà impostato automaticamente per ogni giorno)")
        template = build_record_interactive(fields_no_date, title="Template giornaliero")

        # Chiedi le ore se non già inserite nel template
        daily_hours: Optional[float] = None
        if hours_field and hours_field["api_name"] not in template:
            raw_h = ask(f"Ore giornaliere ({hours_field['api_name']})", "8")
            try:
                daily_hours = float(raw_h.replace(",", "."))
            except ValueError:
                daily_hours = 8.0

        # Anteprima giorni
        print(f"\n  Preview giorni:")
        for d in days[:5]:
            print(f"    {d.strftime('%A %d/%m/%Y')}")
        if len(days) > 5:
            print(f"    … e altri {len(days)-5} giorni")

        if not confirm(f"\n  Creare {len(days)} record?"):
            info("Operazione annullata.")
            return

        # Genera records
        records = []
        for d in days:
            rec = dict(template)
            date_str = d.strftime("%Y-%m-%d")

            if date_field:
                rec[date_field["api_name"]] = date_str
            if hours_field and daily_hours is not None:
                rec[hours_field["api_name"]] = daily_hours

            records.append(rec)

        dry = confirm("Vuoi fare un DRY RUN (non invia realmente)?", default=False)
        send_records(client, module_name, records, dry_run=dry)


# ═══════════════════════════════════════════════════════════════════════════ #
#  Flusso ATTENDANCE                                                         #
# ═══════════════════════════════════════════════════════════════════════════ #

def flow_attendance(client: ZohoVerticalClient, module: dict) -> None:
    module_name = module["api_name"]
    header(f"📋  Attendance  →  {module['plural_label']}  ({module_name})")

    info("Recupero campi del modulo…")
    fields = get_module_fields(client, module_name)
    if not fields:
        warn("Nessun campo trovato o non accessibile.")
        return

    print_fields_table(fields)

    # Rileva campi automaticamente
    date_field    = find_field_by_hints(fields, DATE_FIELD_HINTS)
    checkin_field = find_field_by_hints(fields, CHECKIN_HINTS)
    checkout_field= find_field_by_hints(fields, CHECKOUT_HINTS)

    if date_field:
        info(f"Campo data rilevato:     {date_field['api_name']}")
    if checkin_field:
        info(f"Campo check-in rilevato: {checkin_field['api_name']}")
    if checkout_field:
        info(f"Campo check-out rilevato:{checkout_field['api_name']}")

    # Modalità
    mode_options = [
        "Singolo giorno (inserimento manuale completo)",
        "Settimana  – stesso orario per ogni giorno lavorativo",
        "Mese       – stesso orario per ogni giorno lavorativo",
    ]
    mode_idx = choose("Modalità di inserimento:", mode_options)

    # ------------------------------------------------------------------
    if mode_idx == 0:  # SINGOLO
        record = build_record_interactive(fields, title="Nuovo record Attendance")
        if not record:
            warn("Nessun dato inserito.")
            return
        dry = confirm("Vuoi fare un DRY RUN (non invia realmente)?", default=False)
        send_records(client, module_name, [record], dry_run=dry)

    # ------------------------------------------------------------------
    elif mode_idx in (1, 2):  # SETTIMANA o MESE
        days = ask_period_week() if mode_idx == 1 else ask_period_month()

        auto_fields = {f["api_name"] for f in [date_field, checkin_field, checkout_field] if f}
        fields_manual = [f for f in fields if f["api_name"] not in auto_fields]

        # Orario comune
        checkin_time  = "09:00"
        checkout_time = "18:00"
        if checkin_field:
            checkin_time  = ask(f"Orario CHECK-IN  ({checkin_field['api_name']})",  "09:00")
        if checkout_field:
            checkout_time = ask(f"Orario CHECK-OUT ({checkout_field['api_name']})", "18:00")

        # Altri campi comuni
        template: Dict[str, Any] = {}
        if fields_manual:
            print(f"\n  Inserisci gli altri valori comuni per tutti i giorni:")
            template = build_record_interactive(fields_manual, title="Valori comuni")

        # Anteprima
        print(f"\n  Preview:")
        for d in days[:3]:
            print(f"    {d.strftime('%A %d/%m/%Y')}  check-in={checkin_time}  check-out={checkout_time}")
        if len(days) > 3:
            print(f"    … e altri {len(days)-3} giorni")

        if not confirm(f"\n  Creare {len(days)} record?"):
            info("Operazione annullata.")
            return

        # Genera records
        records = []
        for d in days:
            rec = dict(template)
            date_str = d.strftime("%Y-%m-%d")

            if date_field:
                rec[date_field["api_name"]] = date_str
            if checkin_field:
                dt_in = f"{date_str}T{checkin_time}:00+00:00"
                rec[checkin_field["api_name"]] = dt_in
            if checkout_field:
                dt_out = f"{date_str}T{checkout_time}:00+00:00"
                rec[checkout_field["api_name"]] = dt_out

            records.append(rec)

        dry = confirm("Vuoi fare un DRY RUN (non invia realmente)?", default=False)
        send_records(client, module_name, records, dry_run=dry)


# ═══════════════════════════════════════════════════════════════════════════ #
#  Menu principale                                                           #
# ═══════════════════════════════════════════════════════════════════════════ #

def main_menu(
    client: ZohoVerticalClient,
    ts_module: Optional[dict],
    att_module: Optional[dict],
    all_modules: List[dict],
) -> None:
    while True:
        header("🗂  Menu principale")

        ts_label  = ts_module["plural_label"]  if ts_module  else "non configurato"
        att_label = att_module["plural_label"] if att_module else "non configurato"

        options = []
        if ts_module:
            options.append(f"Invia Timesheet         → {ts_label}")
        if att_module:
            options.append(f"Invia Attendance        → {att_label}")
        options += [
            "Cambia modulo Timesheet",
            "Cambia modulo Attendance",
            "Esplora un modulo (visualizza campi)",
            "Esci",
        ]

        idx = choose("Cosa vuoi fare?", options)
        chosen = options[idx]

        if "Timesheet" in chosen and "Invia" in chosen:
            flow_timesheet(client, ts_module)

        elif "Attendance" in chosen and "Invia" in chosen:
            flow_attendance(client, att_module)

        elif "Cambia modulo Timesheet" in chosen:
            ts_candidates = [
                m for m in all_modules
                if any(kw in m.get("api_name","").lower() for kw in TIMESHEET_KEYWORDS)
            ]
            ts_module = select_module("Timesheet", ts_candidates, all_modules)
            if ts_module:
                ok(f"Modulo Timesheet → {ts_module['api_name']}")
            else:
                warn("Nessun modulo selezionato.")

        elif "Cambia modulo Attendance" in chosen:
            att_candidates = [
                m for m in all_modules
                if any(kw in m.get("api_name","").lower() for kw in ATTENDANCE_KEYWORDS)
            ]
            att_module = select_module("Attendance", att_candidates, all_modules)
            if att_module:
                ok(f"Modulo Attendance → {att_module['api_name']}")
            else:
                warn("Nessun modulo selezionato.")

        elif "Esplora" in chosen:
            all_opts = [f"{m['api_name']:35} {m['plural_label']}" for m in all_modules]
            midx = choose("Seleziona un modulo da esplorare:", all_opts)
            m = all_modules[midx]
            section(f"📂  Campi di {m['api_name']}")
            fields = get_module_fields(client, m["api_name"])
            if fields:
                print_fields_table(fields)
            else:
                warn("Nessun campo trovato.")

        elif "Esci" in chosen:
            print()
            ok("Arrivederci!")
            break


# ═══════════════════════════════════════════════════════════════════════════ #
#  Entry point                                                               #
# ═══════════════════════════════════════════════════════════════════════════ #

def main() -> None:
    header("🚀  Zoho Vertical Studio – Timesheet & Attendance CLI")
    print("  Versione 1.0  |  Usa Ctrl+C per uscire in qualsiasi momento")

    # 1. Connessione
    client = setup_client()

    # 2. Esplora moduli
    ts_candidates, att_candidates, all_api_modules = detect_modules(client)

    # 3. Selezione moduli
    ts_module  = select_module("Timesheet",  ts_candidates,  all_api_modules)
    att_module = select_module("Attendance", att_candidates, all_api_modules)

    if not ts_module and not att_module:
        warn("Nessun modulo selezionato. Puoi sceglierli dal menu principale.")

    # 4. Menu principale
    main_menu(client, ts_module, att_module, all_api_modules)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  👋  Uscita forzata.")
        sys.exit(0)
    except Exception as exc:
        err(f"Errore imprevisto: {exc}")
        raise
