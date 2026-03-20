#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
  examples_test.py  –  Zoho Vertical Studio SDK  –  Esempi & Test completi
═══════════════════════════════════════════════════════════════════════════════

Copre:
  1.  Login con Access Token statico
  2.  Login con Refresh Token (auto-refresh)
  3.  Login da variabili d'ambiente
  4.  Refresh manuale del token
  5.  Verifica connessione (lista moduli)
  6.  Metadata – lettura campi, layout, custom views
  7.  Records – list, get, create, update, upsert, delete
  8.  Records – search (criteria / email / keyword)
  9.  Records – related records, note, allegati
  10. COQL Query – raw string
  11. COQL Query – builder fluente
  12. COQL Query – aggregate / GROUP BY
  13. COQL Query – JOIN tra moduli via lookup
  14. Bulk Read  – crea job, poll, scarica CSV
  15. Notifications – abilita / lista / aggiorna / disabilita
  16. Gestione errori completa

Utilizzo:
    # Configura almeno una delle seguenti variabili prima di eseguire:
    export ZOHO_ACCESS_TOKEN="100xx.il_tuo_token"
    export ZOHO_API_DOMAIN="https://zohoverticalapis.com"   # opzionale, default US

    # Esegui tutti gli esempi:
    python examples_test.py

    # Esegui solo una sezione specifica:
    python examples_test.py --section 7
    python examples_test.py --section records
═══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import os
import sys
import json
import argparse
from datetime import datetime, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Aggiungi la cartella del progetto al path (funziona anche senza installare)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

# ---------------------------------------------------------------------------
# Carica variabili d'ambiente dal file .env (se presente)
# ---------------------------------------------------------------------------
try:
    from dotenv import load_dotenv
    _env_file = os.path.join(BASE_DIR, ".env")
    if os.path.exists(_env_file):
        load_dotenv(_env_file)
except ImportError:
    pass  # python-dotenv non installato, si usano le env var di sistema

try:
    from zoho_vertical_sdk import (
        ZohoVerticalClient,
        ZohoOAuthToken,
    )
    from zoho_vertical_sdk.exceptions import (
        ZohoAPIError,
        ZohoAuthError,
        ZohoNotFoundError,
        ZohoRateLimitError,
        ZohoValidationError,
    )
    from auth_manager import ZohoAuthManager
except ImportError as e:
    print(f"❌  Impossibile importare zoho_vertical_sdk: {e}")
    print("    Assicurati che la cartella 'zoho_vertical_sdk/' e 'auth_manager.py' siano nella stessa directory.")
    sys.exit(1)


# ═══════════════════════════════════════════════════════════════════════════ #
#  Utilità di stampa                                                         #
# ═══════════════════════════════════════════════════════════════════════════ #

def title(text: str) -> None:
    w = 70
    print("\n" + "═" * w)
    print(f"  {text}")
    print("═" * w)

def section(num, text: str) -> None:
    num_str = f"{num:02d}" if isinstance(num, int) else str(num)
    print(f"\n{'─'*60}")
    print(f"  [{num_str}]  {text}")
    print("─" * 60)

def ok(msg: str)   -> None: print(f"  ✅  {msg}")
def err(msg: str)  -> None: print(f"  ❌  {msg}")
def info(msg: str) -> None: print(f"  ℹ️   {msg}")
def skip(msg: str) -> None: print(f"  ⏭️   SALTATO – {msg}")

def dump(label: str, data) -> None:
    """Stampa un dict/lista in modo leggibile (troncato a 500 chars)."""
    raw = json.dumps(data, ensure_ascii=False, default=str, indent=2)
    if len(raw) > 500:
        raw = raw[:500] + "\n  … (troncato)"
    print(f"  📦  {label}:\n{raw}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  Configurazione globale                                                    #
# ═══════════════════════════════════════════════════════════════════════════ #

# Leggi da env vars (oppure imposta direttamente qui per test rapidi)
ACCESS_TOKEN   = os.getenv("ZOHO_ACCESS_TOKEN",   "")
CLIENT_ID      = os.getenv("ZOHO_CLIENT_ID",      "")
CLIENT_SECRET  = os.getenv("ZOHO_CLIENT_SECRET",  "")
REFRESH_TOKEN  = os.getenv("ZOHO_REFRESH_TOKEN",  "")
ACCOUNTS_URL   = os.getenv("ZOHO_ACCOUNTS_URL",   "https://accounts.zoho.com")
API_DOMAIN     = os.getenv("ZOHO_API_DOMAIN",     "https://people.zoho.com")

# Moduli di esempio su cui eseguire le operazioni CRUD
# → Cambia con i nomi reali del tuo account
TEST_MODULE    = os.getenv("ZOHO_TEST_MODULE",    "Employee")
TEST_RECORD_ID = os.getenv("ZOHO_TEST_RECORD_ID", "")   # ID record esistente per get/update

# Variabile globale del client (inizializzata alla sezione 1/2/3)
client: Optional[ZohoVerticalClient] = None


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 1 – Login con Access Token statico                                #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_01_login_static_token():
    section(1, "Login con Access Token statico")

    if not ACCESS_TOKEN:
        skip("ZOHO_ACCESS_TOKEN non impostato")
        return None

    auth = ZohoOAuthToken(access_token=ACCESS_TOKEN)
    token = auth.get_access_token()
    ok(f"Token ottenuto: {token[:20]}…")
    hdr = auth.auth_header()
    ok(f"Header: {hdr}")
    c = ZohoVerticalClient(
        auth=auth,
        api_domain=API_DOMAIN,
        version="v6",
        timeout=30,
        max_retries=3,
        retry_backoff=1.0,
    )
    ok("Client creato con token statico")
    return c


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 1b – Login AUTOMATICO via ZohoAuthManager (RACCOMANDATO)          #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_01b_login_auth_manager():
    """
    Metodo raccomandato per applicazioni reali.

    ZohoAuthManager gestisce automaticamente:
      - Primo login (guida l'utente a generare e incollare l'Authorization Code)
      - Salvataggio cifrato delle credenziali su ~/.zoho_credentials.json
      - Rinnovo automatico dell'access token prima della scadenza
      - Rilevamento token scaduto e re-login trasparente

    Dopo il primo avvio, i successivi non chiedono NULLA all'utente.
    """
    section("1b", "Login automatico via ZohoAuthManager (raccomandato)")

    if not all([CLIENT_ID, CLIENT_SECRET]):
        skip("ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET non impostati")
        return None

    # ── Creazione manager ─────────────────────────────────────────────────
    # Opzione A: passando le credenziali direttamente
    manager = ZohoAuthManager(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        data_centre=os.getenv("ZOHO_DATA_CENTRE", "US"),
    )

    # Opzione B: da variabili d'ambiente
    # manager = ZohoAuthManager.from_env()

    # ── Ottieni il client ─────────────────────────────────────────────────
    # Al primo avvio: chiede all'utente di incollare il code dalla Dev Console
    # Avvii successivi: carica e rinnova in silenzio
    try:
        c = manager.get_client()
    except Exception as e:
        err(f"AuthManager: {e}")
        return None

    # ── Stato ─────────────────────────────────────────────────────────────
    manager.print_status()
    ok("Client pronto — token gestito automaticamente")

    # ── Reset (per forzare un nuovo login) ────────────────────────────────
    # manager.reset()   # decommenta per cancellare le credenziali salvate

    return c


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 2 – Login con Refresh Token (auto-refresh)                        #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_02_login_refresh_token():
    section(2, "Login con Refresh Token (auto-refresh)")

    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        skip("ZOHO_CLIENT_ID / ZOHO_CLIENT_SECRET / ZOHO_REFRESH_TOKEN non impostati")
        return None

    # -----------------------------------------------------------------------
    # Con client_id + client_secret + refresh_token l'SDK rinnova
    # automaticamente l'access token 60 secondi prima della scadenza.
    # Ideale per processi long-running o script schedulati.
    # -----------------------------------------------------------------------
    auth = ZohoOAuthToken(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        refresh_token=REFRESH_TOKEN,
        accounts_url=ACCOUNTS_URL,   # cambia per EU: https://accounts.zoho.eu
    )

    try:
        token = auth.get_access_token()   # esegue il primo refresh
        ok(f"Access token ottenuto via refresh: {token[:20]}…")
    except ZohoAuthError as e:
        err(f"Refresh fallito: {e.message}")
        return None

    c = ZohoVerticalClient(auth=auth, api_domain=API_DOMAIN)
    ok("Client creato con auto-refresh")
    return c


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 3 – Login da variabili d'ambiente                                 #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_03_login_from_env():
    section(3, "Login da variabili d'ambiente")

    # -----------------------------------------------------------------------
    # ZohoOAuthToken.from_env() legge automaticamente:
    #   ZOHO_ACCESS_TOKEN
    #   ZOHO_CLIENT_ID, ZOHO_CLIENT_SECRET, ZOHO_REFRESH_TOKEN
    #   ZOHO_ACCOUNTS_URL
    # -----------------------------------------------------------------------
    auth = ZohoOAuthToken.from_env()

    try:
        token = auth.get_access_token()
        ok(f"Token da env: {token[:20]}…")
    except ZohoAuthError as e:
        err(f"Nessuna credenziale trovata nelle env vars: {e.message}")
        return None

    c = ZohoVerticalClient(auth=auth, api_domain=API_DOMAIN)
    ok("Client creato da variabili d'ambiente")
    return c


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 4 – Refresh manuale del token                                     #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_04_manual_token_refresh():
    section(4, "Refresh manuale del token")

    if not all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
        skip("Credenziali refresh non disponibili")
        return

    auth = ZohoOAuthToken(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        refresh_token=REFRESH_TOKEN,
        accounts_url=ACCOUNTS_URL,
    )

    # Forza il refresh azzerando la scadenza
    info("Forzo refresh del token…")
    auth._token_expiry = 0   # scaduto → al prossimo get_access_token() refresha

    try:
        new_token = auth.get_access_token()
        ok(f"Nuovo token: {new_token[:20]}…")
        info(f"Scade tra ~{int(auth._token_expiry - __import__('time').time())} secondi")
    except ZohoAuthError as e:
        err(f"Refresh fallito: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 5 – Verifica connessione                                          #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_05_verify_connection():
    section(5, "Verifica connessione – lista moduli")

    if client is None:
        skip("Client non inizializzato")
        return

    try:
        modules = client.modules.list_modules()
        api_modules = [m for m in modules if m.get("api_supported")]
        ok(f"Connessione OK – trovati {len(modules)} moduli totali, {len(api_modules)} con supporto API")
        info("Primi 5 moduli API:")
        for m in api_modules[:5]:
            print(f"    • {m['api_name']:35} {m['plural_label']}")
    except ZohoAuthError as e:
        err(f"Autenticazione fallita: {e.message}")
    except ZohoAPIError as e:
        err(f"Errore API: {e.message} (HTTP {e.status_code})")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 6 – Metadata                                                      #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_06_metadata():
    section(6, "Metadata – campi, layout, custom views, related lists")

    if client is None:
        skip("Client non inizializzato")
        return

    # --- Campi del modulo ---
    info(f"Campi di '{TEST_MODULE}':")
    try:
        fields = client.metadata.get_fields(TEST_MODULE)
        ok(f"Trovati {len(fields)} campi")
        for f in fields[:6]:
            req = "✱" if f.get("system_mandatory") else " "
            print(f"    {req} {f['api_name']:35} {f.get('data_type',''):20}")
    except ZohoAPIError as e:
        err(f"Campi: {e.message}")

    # --- Solo campi di tipo lookup ---
    info("Campi lookup:")
    try:
        lookups = client.metadata.get_fields(TEST_MODULE, field_type="lookup")
        for f in lookups[:3]:
            print(f"    • {f['api_name']}")
    except ZohoAPIError as e:
        err(f"Lookup: {e.message}")

    # --- Layout ---
    info("Layout disponibili:")
    try:
        layouts = client.metadata.get_layouts(TEST_MODULE)
        for lay in layouts[:3]:
            print(f"    • {lay.get('name','?')}  (id: {lay.get('id','')})")
    except ZohoAPIError as e:
        err(f"Layout: {e.message}")

    # --- Custom Views ---
    info("Custom views:")
    try:
        views = client.metadata.get_custom_views(TEST_MODULE)
        ok(f"Trovate {len(views)} custom views")
        for v in views[:3]:
            print(f"    • {v.get('name','?')}")
    except ZohoAPIError as e:
        err(f"Custom views: {e.message}")

    # --- Related Lists ---
    info("Related lists:")
    try:
        related = client.metadata.get_related_lists(TEST_MODULE)
        for r in related[:4]:
            print(f"    • {r.get('api_name','?'):30} → {r.get('module',{}).get('api_name','?')}")
    except ZohoAPIError as e:
        err(f"Related lists: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 7 – Records CRUD                                                  #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_07_records_crud():
    section(7, f"Records CRUD su '{TEST_MODULE}'")

    if client is None:
        skip("Client non inizializzato")
        return

    created_id: Optional[str] = None

    # ── LIST ──────────────────────────────────────────────────────────────
    info("LIST – primi 3 record:")
    try:
        resp = client.records.list(
            TEST_MODULE,
            fields=["Last_Name", "Email", "Phone"],
            page=1,
            per_page=3,
            sort_by="Created_Time",
            sort_order="desc",
        )
        records = resp.get("data", [])
        ok(f"Trovati {len(records)} record (pagina 1)")
        for r in records:
            print(f"    • [{r.get('id','')}]  {r.get('Last_Name','?')}")
    except ZohoAPIError as e:
        err(f"List: {e.message}")

    # ── GET BY ID ─────────────────────────────────────────────────────────
    if TEST_RECORD_ID:
        info(f"GET – record {TEST_RECORD_ID}:")
        try:
            rec = client.records.get(TEST_MODULE, TEST_RECORD_ID)
            ok(f"Record: {rec.get('Last_Name','?')}  email={rec.get('Email','?')}")
        except ZohoNotFoundError:
            err("Record non trovato")
        except ZohoAPIError as e:
            err(f"Get: {e.message}")
    else:
        skip("ZOHO_TEST_RECORD_ID non impostato – salto get singolo")

    # ── CREATE ────────────────────────────────────────────────────────────
    info("CREATE – nuovo Lead di test:")
    try:
        results = client.records.create(TEST_MODULE, [
            {
                "Last_Name": "SDK_Test",
                "First_Name": "Zoho",
                "Email": f"sdk.test.{int(datetime.now().timestamp())}@example.com",
                "Phone": "+39 02 12345678",
                "Company": "SDK Test Srl",
                "Lead_Source": "Web Site",
            }
        ])
        for r in results:
            if r.get("code") == "SUCCESS":
                created_id = r["details"]["id"]
                ok(f"Creato – ID: {created_id}")
            else:
                err(f"Create fallito: {r.get('message')} – {r.get('details')}")
    except ZohoAPIError as e:
        err(f"Create: {e.message}")

    # ── UPDATE ────────────────────────────────────────────────────────────
    if created_id:
        info(f"UPDATE – aggiorno il record {created_id}:")
        try:
            results = client.records.update(TEST_MODULE, [
                {"id": created_id, "Lead_Status": "Contacted", "Description": "Aggiornato via SDK"}
            ])
            for r in results:
                if r.get("code") == "SUCCESS":
                    ok("Update OK")
                else:
                    err(f"Update fallito: {r.get('message')}")
        except ZohoAPIError as e:
            err(f"Update: {e.message}")

    # ── UPSERT ────────────────────────────────────────────────────────────
    info("UPSERT – crea o aggiorna per email:")
    try:
        results = client.records.upsert(
            TEST_MODULE,
            records=[{"Last_Name": "UpsertTest", "Email": "upsert@example.com"}],
            duplicate_check_fields=["Email"],
        )
        for r in results:
            action = r.get("action", "?")
            code   = r.get("code", "?")
            ok(f"Upsert: {code}  action={action}  id={r.get('details',{}).get('id','?')}")
    except ZohoAPIError as e:
        err(f"Upsert: {e.message}")

    # ── DELETE ────────────────────────────────────────────────────────────
    if created_id:
        info(f"DELETE – cancello il record di test {created_id}:")
        try:
            results = client.records.delete(TEST_MODULE, ids=[created_id])
            for r in results:
                if r.get("code") == "SUCCESS":
                    ok("Eliminato")
                else:
                    err(f"Delete fallito: {r.get('message')}")
        except ZohoAPIError as e:
            err(f"Delete: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 8 – Search                                                        #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_08_search():
    section(8, f"Search su '{TEST_MODULE}'")

    if client is None:
        skip("Client non inizializzato")
        return

    # --- Criteria ---
    info("Ricerca per criteria:")
    try:
        resp = client.records.search(
            TEST_MODULE,
            criteria="(Last_Name:starts_with:S)",
            fields=["Last_Name", "Email"],
            per_page=3,
        )
        results = resp.get("data", [])
        ok(f"Trovati {len(results)} record con Last_Name che inizia per 'S'")
        for r in results[:3]:
            print(f"    • {r.get('Last_Name','?')}  {r.get('Email','')}")
    except ZohoAPIError as e:
        err(f"Search criteria: {e.message}")

    # --- Email ---
    info("Ricerca per email esatta:")
    try:
        resp = client.records.search("Contacts", email="test@example.com")
        ok(f"Risultati email: {len(resp.get('data', []))}")
    except ZohoAPIError as e:
        err(f"Search email: {e.message}")

    # --- Keyword full-text ---
    info("Ricerca full-text (word):")
    try:
        resp = client.records.search(TEST_MODULE, word="Acme", per_page=3)
        ok(f"Risultati keyword 'Acme': {len(resp.get('data', []))}")
    except ZohoAPIError as e:
        err(f"Search word: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 9 – Related records, Note, Allegati                               #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_09_related_notes_attachments():
    section(9, "Related records, Note, Allegati")

    if client is None or not TEST_RECORD_ID:
        skip("Client non inizializzato o ZOHO_TEST_RECORD_ID non impostato")
        return

    # --- Related Contacts di un Account ---
    info(f"Related Contacts dell'Account {TEST_RECORD_ID}:")
    try:
        resp = client.records.get_related("Accounts", TEST_RECORD_ID, "Contacts")
        ok(f"Related contacts: {len(resp.get('data', []))}")
    except ZohoAPIError as e:
        err(f"Related: {e.message}")

    # --- Note ---
    info(f"Note sul record {TEST_RECORD_ID}:")
    try:
        resp = client.records.get_notes(TEST_MODULE, TEST_RECORD_ID)
        ok(f"Note trovate: {len(resp.get('data', []))}")
    except ZohoAPIError as e:
        err(f"Notes: {e.message}")

    # --- Crea nota ---
    info("Creo una nota di test:")
    try:
        result = client.records.create_note(
            TEST_MODULE,
            TEST_RECORD_ID,
            note_title="Nota SDK",
            note_content="Creata automaticamente dall'SDK Python v6.",
        )
        if result.get("code") == "SUCCESS":
            ok(f"Nota creata – ID: {result.get('details',{}).get('id','?')}")
        else:
            err(f"Nota: {result.get('message')}")
    except ZohoAPIError as e:
        err(f"Create note: {e.message}")

    # --- Allegati ---
    info(f"Allegati del record {TEST_RECORD_ID}:")
    try:
        resp = client.records.get_attachments(TEST_MODULE, TEST_RECORD_ID)
        ok(f"Allegati trovati: {len(resp.get('data', []))}")
    except ZohoAPIError as e:
        err(f"Attachments: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 10 – COQL Query raw                                               #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_10_coql_raw():
    section(10, "COQL Query – stringa raw")

    if client is None:
        skip("Client non inizializzato")
        return

    info("Query semplice:")
    try:
        result = client.query.execute(
            f"SELECT Last_Name, Email, Created_Time "
            f"FROM {TEST_MODULE} "
            f"WHERE (Last_Name is not null) "
            f"ORDER BY Created_Time DESC "
            f"LIMIT 0, 5"
        )
        rows = result.get("data", [])
        ok(f"Righe restituite: {len(rows)}")
        for r in rows:
            print(f"    • {r.get('Last_Name','?'):25} {r.get('Email','')}")
        info(f"more_records: {result.get('info',{}).get('more_records')}")
    except ZohoAPIError as e:
        err(f"COQL: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 11 – COQL Builder fluente                                         #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_11_coql_builder():
    section(11, "COQL Query – builder fluente")

    if client is None:
        skip("Client non inizializzato")
        return

    # --- Builder base ---
    info("Builder base:")
    try:
        result = (
            client.query
            .select("Last_Name", "Email", "Lead_Status")
            .from_module(TEST_MODULE)
            .where("(Last_Name is not null)")
            .order_by("Last_Name", "ASC")
            .limit(offset=0, count=5)
            .run()
        )
        ok(f"Righe: {len(result.get('data', []))}")
    except ZohoAPIError as e:
        err(f"Builder: {e.message}")

    # --- Mostra la query generata senza eseguire ---
    info("Query generata dal builder (senza eseguire):")
    q = (
        client.query
        .select("Last_Name", "Email")
        .from_module(TEST_MODULE)
        .where("(Email like '%example%')")
        .order_by("Created_Time", "DESC")
        .limit(0, 10)
        .build()
    )
    print(f"    {q}")
    client.query._reset()   # reset manuale dopo build() senza run()

    # --- Auto-paginazione ---
    info("Auto-paginazione (execute_all):")
    try:
        all_rows = client.query.execute_all(
            f"SELECT Last_Name FROM {TEST_MODULE} WHERE (Last_Name is not null)",
            max_per_page=200,
        )
        ok(f"Totale record recuperati: {len(all_rows)}")
    except ZohoAPIError as e:
        err(f"execute_all: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 12 – COQL Aggregate / GROUP BY                                    #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_12_coql_aggregate():
    section(12, "COQL – Aggregate functions e GROUP BY")

    if client is None:
        skip("Client non inizializzato")
        return

    # --- COUNT per Lead_Status ---
    info("COUNT per Lead_Status:")
    try:
        result = client.query.execute(
            f"SELECT Lead_Status, COUNT(id) AS totale "
            f"FROM {TEST_MODULE} "
            f"GROUP BY Lead_Status "
            f"LIMIT 0, 50"
        )
        for row in result.get("data", [])[:6]:
            print(f"    {row.get('Lead_Status','?'):25} → {row.get('totale','?')}")
        ok(f"Righe raggruppate: {len(result.get('data',[]))}")
    except ZohoAPIError as e:
        err(f"Aggregate: {e.message}")

    # --- SUM / AVG su campo numerico (se disponibile) ---
    info("SUM e AVG (esempio su campo numerico):")
    try:
        result = client.query.execute(
            f"SELECT COUNT(id) AS totale_lead "
            f"FROM {TEST_MODULE} "
            f"WHERE (Last_Name is not null) "
            f"LIMIT 0, 1"
        )
        row = result.get("data", [{}])[0]
        ok(f"Totale Lead nel sistema: {row.get('totale_lead','?')}")
    except ZohoAPIError as e:
        err(f"SUM/AVG: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 13 – COQL JOIN tra moduli                                         #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_13_coql_join():
    section(13, "COQL – JOIN tra moduli via lookup (dot notation)")

    if client is None:
        skip("Client non inizializzato")
        return

    # In Zoho COQL i JOIN si fanno con il punto: Account_Name.Account_Name
    # Contacts → Accounts (tramite lookup Account_Name)
    info("Contacts + Account (JOIN via Account_Name):")
    try:
        result = client.query.execute(
            "SELECT Last_Name, 'Account_Name.Account_Name' AS account, "
            "'Account_Name.Phone' AS account_phone "
            "FROM Contacts "
            "WHERE (Last_Name is not null) "
            "LIMIT 0, 5"
        )
        rows = result.get("data", [])
        ok(f"Righe con JOIN: {len(rows)}")
        for r in rows:
            print(f"    Contact: {r.get('Last_Name','?'):20}  "
                  f"Account: {r.get('account','?')}")
    except ZohoAPIError as e:
        err(f"JOIN: {e.message}")

    # Alias personalizzati
    info("JOIN con alias personalizzati:")
    try:
        result = client.query.execute(
            "SELECT Last_Name AS nome, "
            "'Account_Name.Account_Name' AS azienda, "
            "'Account_Name.Parent_Account.Account_Name' AS gruppo "
            "FROM Contacts "
            "WHERE (Last_Name is not null) "
            "LIMIT 0, 3"
        )
        for r in result.get("data", []):
            print(f"    {r.get('nome','?'):20} | {r.get('azienda','?'):20} | {r.get('gruppo','?')}")
    except ZohoAPIError as e:
        err(f"JOIN alias: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 14 – Bulk Read                                                    #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_14_bulk_read():
    section(14, "Bulk Read – crea job, poll, scarica CSV")

    if client is None:
        skip("Client non inizializzato")
        return

    info("Creo job di bulk read…")
    try:
        job_resp = client.bulk.create_read_job(
            module=TEST_MODULE,
            fields=["Last_Name", "Email", "Phone", "Created_Time"],
            criteria="(Last_Name is not null)",
            page=1,
            file_type="csv",
        )
        job_data = job_resp.get("data", [{}])[0]
        job_id = job_data.get("details", {}).get("id")
        ok(f"Job creato – ID: {job_id}  stato: {job_data.get('state','?')}")

        if not job_id:
            err("ID job non ricevuto")
            return

        # Poll con timeout di 120 secondi
        info("Attendo completamento job (max 120s)…")
        try:
            final = client.bulk.wait_for_read_job(
                job_id,
                poll_interval=5.0,
                timeout=120.0,
            )
            ok(f"Job completato: {final.get('data',[{}])[0].get('state','?')}")

            # Scarica CSV
            info("Scarico il CSV risultante…")
            csv_bytes = client.bulk.download_read_result(job_id)
            lines = csv_bytes.decode("utf-8").splitlines()
            ok(f"CSV scaricato: {len(lines)} righe (inclusa intestazione)")
            info(f"Prima riga (header): {lines[0][:100] if lines else 'vuoto'}")

            # Pulizia
            client.bulk.delete_read_job(job_id)
            ok(f"Job {job_id} eliminato")

        except TimeoutError:
            err("Job non completato entro 120s – considera di aumentare il timeout")
        except RuntimeError as e:
            err(f"Job fallito: {e}")

    except ZohoAPIError as e:
        err(f"Bulk read: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 15 – Notifications                                                #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_15_notifications():
    section(15, "Notifications – abilita / lista / aggiorna / disabilita")

    if client is None:
        skip("Client non inizializzato")
        return

    CHANNEL_ID  = "100000006800999"
    NOTIFY_URL  = "https://myapp.example.com/webhooks/zoho"
    EXPIRY      = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%S+00:00")

    # Abilita
    info("Abilito notifiche per Leads…")
    try:
        resp = client.notifications.enable(
            channel_id=CHANNEL_ID,
            events=[f"{TEST_MODULE}.create", f"{TEST_MODULE}.edit", f"{TEST_MODULE}.delete"],
            channel_expiry=EXPIRY,
            notify_url=NOTIFY_URL,
            token="my_secret_validation_token",
        )
        ok(f"Notifiche abilitate: {resp}")
    except ZohoAPIError as e:
        err(f"Enable: {e.message}")

    # Lista
    info("Lista canali attivi:")
    try:
        channels = client.notifications.list_channels()
        ok(f"Canali trovati: {len(channels)}")
        for ch in channels[:3]:
            print(f"    • channel_id={ch.get('channel_id','?')}  "
                  f"events={ch.get('events',[])} ")
    except ZohoAPIError as e:
        err(f"List: {e.message}")

    # Rinnova scadenza
    info("Rinnovo scadenza canale…")
    try:
        new_expiry = (datetime.now() + timedelta(days=60)).strftime("%Y-%m-%dT%H:%M:%S+00:00")
        resp = client.notifications.update(
            channel_id=CHANNEL_ID,
            channel_expiry=new_expiry,
        )
        ok(f"Rinnovato fino a {new_expiry}")
    except ZohoAPIError as e:
        err(f"Update: {e.message}")

    # Disabilita
    info("Disabilito canale…")
    try:
        resp = client.notifications.disable_raw([CHANNEL_ID])
        ok("Canale disabilitato")
    except ZohoAPIError as e:
        err(f"Disable: {e.message}")


# ═══════════════════════════════════════════════════════════════════════════ #
#  SEZIONE 16 – Gestione errori completa                                     #
# ═══════════════════════════════════════════════════════════════════════════ #

def example_16_error_handling():
    section(16, "Gestione errori – tutti i tipi di eccezione")

    if client is None:
        skip("Client non inizializzato")
        return

    # ── ZohoNotFoundError ──────────────────────────────────────────────────
    info("Test ZohoNotFoundError (ID inesistente):")
    try:
        client.records.get(TEST_MODULE, "0000000000000000001")
    except ZohoNotFoundError as e:
        ok(f"ZohoNotFoundError catturata: status={e.status_code}  code={e.error_code}")
    except ZohoAPIError as e:
        info(f"Altra eccezione API: {type(e).__name__} – {e.message}")

    # ── ZohoValidationError ────────────────────────────────────────────────
    info("Test ZohoValidationError (payload vuoto):")
    try:
        client.records.create(TEST_MODULE, [{}])
    except ZohoValidationError as e:
        ok(f"ZohoValidationError: status={e.status_code}  code={e.error_code}")
    except ZohoAPIError as e:
        info(f"Altra: {type(e).__name__} – {e.message}")

    # ── ZohoAuthError ──────────────────────────────────────────────────────
    info("Test ZohoAuthError (token non valido):")
    try:
        bad_auth   = ZohoOAuthToken(access_token="INVALID_TOKEN_123")
        bad_client = ZohoVerticalClient(auth=bad_auth, api_domain=API_DOMAIN, max_retries=0)
        bad_client.modules.list_modules()
    except ZohoAuthError as e:
        ok(f"ZohoAuthError catturata: status={e.status_code}")
    except ZohoAPIError as e:
        info(f"Altra: {type(e).__name__} – {e.message}")

    # ── Cattura generica ───────────────────────────────────────────────────
    info("Cattura generica ZohoAPIError:")
    try:
        client.records.list("ModuloNonEsistente_XYZ")
    except ZohoNotFoundError as e:
        ok(f"NotFound: {e.message}")
    except ZohoAuthError as e:
        ok(f"Auth: {e.message}")
    except ZohoAPIError as e:
        ok(f"APIError generico: HTTP {e.status_code} – {e.message}")

    # ── Struttura completa dell'eccezione ──────────────────────────────────
    info("Struttura completa di un'eccezione:")
    try:
        raise ZohoAPIError(
            "Esempio di errore",
            status_code=400,
            error_code="INVALID_DATA",
            details={"field": "Email", "reason": "formato non valido"},
        )
    except ZohoAPIError as e:
        print(f"    message    : {e.message}")
        print(f"    status_code: {e.status_code}")
        print(f"    error_code : {e.error_code}")
        print(f"    details    : {e.details}")
        ok("Eccezione ispezionata correttamente")


# ═══════════════════════════════════════════════════════════════════════════ #
#  Runner principale                                                         #
# ═══════════════════════════════════════════════════════════════════════════ #

ALL_EXAMPLES = {
    1:  ("Login – Access Token statico",       example_01_login_static_token),
    2:  ("Login – Refresh Token",              example_02_login_refresh_token),
    3:  ("Login – da variabili d'ambiente",    example_03_login_from_env),
    4:  ("Refresh manuale del token",          example_04_manual_token_refresh),
    5:  ("Verifica connessione",               example_05_verify_connection),
    6:  ("Metadata",                           example_06_metadata),
    7:  ("Records CRUD",                       example_07_records_crud),
    8:  ("Search",                             example_08_search),
    9:  ("Related / Note / Allegati",          example_09_related_notes_attachments),
    10: ("COQL Query raw",                     example_10_coql_raw),
    11: ("COQL Builder fluente",               example_11_coql_builder),
    12: ("COQL Aggregate / GROUP BY",          example_12_coql_aggregate),
    13: ("COQL JOIN tra moduli",               example_13_coql_join),
    14: ("Bulk Read",                          example_14_bulk_read),
    15: ("Notifications",                      example_15_notifications),
    16: ("Gestione errori",                    example_16_error_handling),
}

# Sezioni che richiedono keyword speciali per --section
SECTION_ALIASES = {
    "login":   [1, 2, 3, 4],
    "auth":    [1, 2, 3, 4],
    "records": [7, 8, 9],
    "query":   [10, 11, 12, 13],
    "coql":    [10, 11, 12, 13],
    "bulk":    [14],
    "notif":   [15],
    "errors":  [16],
}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Zoho Vertical Studio SDK – Examples & Tests",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Esempi di utilizzo:
  python examples_test.py                   # esegui tutto
  python examples_test.py --section 7       # solo Records CRUD
  python examples_test.py --section login   # sezioni 1-4
  python examples_test.py --section records # sezioni 7-9
  python examples_test.py --section query   # sezioni 10-13
  python examples_test.py --list            # mostra tutte le sezioni
        """,
    )
    parser.add_argument(
        "--section", "-s",
        help="Numero o alias della sezione da eseguire",
        default=None,
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        help="Mostra la lista delle sezioni disponibili",
    )
    return parser.parse_args()


def resolve_sections(section_arg: Optional[str]) -> list[int]:
    if section_arg is None:
        return sorted(ALL_EXAMPLES.keys())

    # Alias testuale (es. "login", "records")
    alias = section_arg.lower()
    if alias in SECTION_ALIASES:
        return SECTION_ALIASES[alias]

    # Numero singolo
    if section_arg.isdigit():
        num = int(section_arg)
        if num in ALL_EXAMPLES:
            return [num]
        print(f"❌  Sezione {num} non trovata. Usa --list per vedere le disponibili.")
        sys.exit(1)

    print(f"❌  '{section_arg}' non riconosciuto. Usa --list per vedere le opzioni.")
    sys.exit(1)


def main():
    global client

    args = parse_args()

    if args.list:
        title("📋  Sezioni disponibili")
        for num, (desc, _) in ALL_EXAMPLES.items():
            print(f"  {num:2d}.  {desc}")
        print()
        print("  Alias: login, records, query/coql, bulk, notif, errors")
        return

    title("🧪  Zoho Vertical Studio SDK – Examples & Tests")
    print(f"  API Domain : {API_DOMAIN}")
    print(f"  Test Module: {TEST_MODULE}")
    print(f"  Record ID  : {TEST_RECORD_ID or '(non impostato)'}")

    sections_to_run = resolve_sections(args.section)

    # ── Inizializzazione client ────────────────────────────────────────────
    if any(s in sections_to_run for s in range(1, 17)):
        # Priorità 1: ZohoAuthManager (raccomandato – gestisce tutto automaticamente)
        if all([CLIENT_ID, CLIENT_SECRET]):
            client = example_01b_login_auth_manager()
        # Priorità 2: token statico
        if client is None and ACCESS_TOKEN:
            client = example_01_login_static_token()
        # Priorità 3: refresh token diretto
        if client is None and all([CLIENT_ID, CLIENT_SECRET, REFRESH_TOKEN]):
            client = example_02_login_refresh_token()
        # Priorità 4: tutto da env vars
        if client is None:
            client = example_03_login_from_env()

        if client is None:
            err("Impossibile inizializzare il client.")
            err("Imposta almeno ZOHO_CLIENT_ID e ZOHO_CLIENT_SECRET.")
            sys.exit(1)

    # ── Esegui le sezioni richieste ────────────────────────────────────────
    for num in sections_to_run:
        if num in (1, 2, 3):
            continue  # già gestiti sopra
        desc, fn = ALL_EXAMPLES[num]
        fn()

    title("✅  Completato")
    passed = sum(1 for n in sections_to_run if n not in (1, 2, 3))
    print(f"  Sezioni eseguite: {passed}")
    print()


if __name__ == "__main__":
    main()
