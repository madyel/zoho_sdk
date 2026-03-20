# Setup dopo clone del repository

## Prerequisiti

```bash
pip install requests
```

## Primo avvio

Il software gestisce l'autenticazione **completamente da solo**.

### Opzione A – avvio diretto (consigliata)

```bash
python zoho_timesheet_cli.py
```

Al primo avvio chiederà:
1. **Client ID** → lo trovi su `accounts.zoho.com/developerconsole` → Self Client → Client Secret
2. **Client Secret** → stessa pagina

Poi aprirà il browser sulla Developer Console e chiederà di incollare
l'Authorization Code (operazione una-tantum, ~30 secondi).

Da quel momento in poi il software si avvia senza chiedere nulla.

### Opzione B – variabili d'ambiente

```bash
export ZOHO_CLIENT_ID="1000.C29G99K98..."
export ZOHO_CLIENT_SECRET="6d12797e3d2d..."
export ZOHO_DATA_CENTRE="EU"          # US / EU / IN / AU / JP

python zoho_timesheet_cli.py
```

---

## File generati automaticamente (NON nel repo)

| File | Dove | Contenuto |
|---|---|---|
| `~/.zoho_credentials.json` | Home utente | Refresh token + access token (cifrati) |
| `zoho_config.json` | Cartella progetto | Solo client_id e data centre (non sensibile) |

> ⚠️  Non committare mai `~/.zoho_credentials.json`.
> È già escluso dal `.gitignore` ma per sicurezza verifica sempre con `git status`.

---

## Reset credenziali

Se devi ricominciare da capo (es. nuovo account Zoho):

```bash
# Elimina le credenziali salvate
rm ~/.zoho_credentials.json
rm zoho_config.json

# Al prossimo avvio verrà chiesto tutto da capo
python zoho_timesheet_cli.py
```

---

## Struttura del progetto

```
zoho_vertical_sdk/
├── zoho_vertical_sdk/      ← SDK Python (moduli, records, query, bulk…)
├── auth_manager.py         ← gestione OAuth automatica (login, refresh, salvataggio)
├── zoho_timesheet_cli.py   ← CLI per timesheet e attendance
├── zoho_config.json        ← configurazione locale (client_id, data centre)
├── examples_test.py        ← esempi e test di tutte le funzionalità
└── README.md               ← documentazione completa dell'SDK
```
