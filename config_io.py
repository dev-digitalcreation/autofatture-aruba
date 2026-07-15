# -*- coding: utf-8 -*-
"""
Lettura/scrittura della configurazione (azienda + fornitori).

In esecuzione da sorgente: i file stanno nella cartella dell'app (config/).
In esecuzione da .exe (frozen): i file stanno in una cartella scrivibile
dell'utente (%APPDATA%\\AutofattureAruba), perche' dentro il pacchetto sono
in sola lettura. Se mancano vengono creati dai default incorporati.
"""
import os
import sys
import json

# --------------------------------------------------------------------------- #
# Default incorporati (usati alla prima esecuzione / installazione)
# --------------------------------------------------------------------------- #
# NB: default GENERICI (nessun dato personale, il repo e' pubblico).
# Ogni utente inserisce i propri dati azienda/IBAN in Impostazioni alla prima apertura.
# I valori di trasmittente/codice destinatario sono quelli pubblici di Aruba,
# uguali per tutti gli utenti che trasmettono tramite Aruba.
DEFAULT_CONFIG = {
    "azienda": {
        "denominazione": "", "id_paese": "IT", "piva": "", "codice_fiscale": "",
        "indirizzo": "", "numero_civico": "", "cap": "", "comune": "", "provincia": "", "nazione": "IT",
    },
    "trasmittente": {"id_paese": "IT", "id_codice": "01879020517"},   # Aruba S.p.A.
    "codice_destinatario": "KRRH6B9",                                 # canale Aruba
    "soggetto_emittente": "CC",
    "regime_fiscale_cedente": "RF18",
    "importo_totale_documento": True,
    "numerazione": {"pattern": "AF {n}/{yy}"},
    "progressivo_start": 1,
    "filename_prefix": None,
    "ricorda_ultimo_numero": True,
    "aliquota_default": "22.00",
    "pagamento": None,          # opzionale; l'IBAN lo inserisce l'utente
    "github_token": "",
}

DEFAULT_FORNITORI = {
    "anthropic": {"denominazione": "Anthropic, PBC", "id_paese": "US", "id_codice": "OO99999999999",
                  "indirizzo": "548 Market Street PMB 90375", "cap": "00000", "comune": "San Francisco",
                  "nazione": "US", "tipo_documento": "TD17"},
    "siteground": {"denominazione": "SiteGround Spain S.L.", "id_paese": "ES", "id_codice": "B87194171",
                   "indirizzo": "28004 Calle Prim", "numero_civico": "19", "cap": "00000",
                   "comune": "Madrid", "nazione": "ES", "tipo_documento": "TD17"},
    "vercel": {"denominazione": "Vercel Inc.", "id_paese": "US", "id_codice": "OO99999999999",
               "indirizzo": "440 N Barranca Ave #4133", "cap": "00000", "comune": "Covina",
               "nazione": "US", "tipo_documento": "TD17"},
    "openai": {"denominazione": "OpenAI, LLC", "id_paese": "US", "id_codice": "OO99999999999",
               "indirizzo": "3180 18th Street", "cap": "00000", "comune": "San Francisco",
               "nazione": "US", "tipo_documento": "TD17"},
    "google": {"denominazione": "Google Cloud EMEA Limited", "id_paese": "IE", "id_codice": "IE3668997OH",
               "indirizzo": "70 Sir John Rogerson's Quay", "cap": "00000", "comune": "Dublin",
               "nazione": "IE", "tipo_documento": "TD17"},
    "microsoft": {"denominazione": "Microsoft Ireland Operations Ltd", "id_paese": "IE",
                  "id_codice": "IE8256796U", "indirizzo": "One Microsoft Place", "cap": "00000",
                  "comune": "Dublin", "nazione": "IE", "tipo_documento": "TD17"},
    "amazon web services": {"denominazione": "Amazon Web Services EMEA SARL", "id_paese": "LU",
                            "id_codice": "LU26888617", "indirizzo": "38 avenue John F. Kennedy",
                            "cap": "00000", "comune": "Luxembourg", "nazione": "LU",
                            "tipo_documento": "TD17"},
}


# --------------------------------------------------------------------------- #
# Percorsi (scrivibili anche quando l'app e' un .exe)
# --------------------------------------------------------------------------- #
def _base_dir() -> str:
    if getattr(sys, "frozen", False):          # in esecuzione come .exe
        base = os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "AutofattureAruba")
    else:                                       # in esecuzione da sorgente
        base = os.path.dirname(os.path.abspath(__file__))
    os.makedirs(os.path.join(base, "config"), exist_ok=True)
    os.makedirs(os.path.join(base, "output_xml"), exist_ok=True)
    return base


BASE = _base_dir()
CONFIG_PATH = os.path.join(BASE, "config", "azienda.json")
FORNITORI_PATH = os.path.join(BASE, "config", "fornitori.json")
OUTPUT_DIR = os.path.join(BASE, "output_xml")


def carica_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        salva_config(DEFAULT_CONFIG)
        return dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return dict(DEFAULT_CONFIG)


def salva_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def carica_fornitori() -> dict:
    if not os.path.exists(FORNITORI_PATH):
        salva_fornitori(DEFAULT_FORNITORI)
        return dict(DEFAULT_FORNITORI)
    try:
        with open(FORNITORI_PATH, encoding="utf-8") as f:
            return json.load(f).get("fornitori", DEFAULT_FORNITORI)
    except Exception:
        return dict(DEFAULT_FORNITORI)


def salva_fornitori(forn: dict):
    with open(FORNITORI_PATH, "w", encoding="utf-8") as f:
        json.dump({"_nota": "Fornitori riconosciuti automaticamente dal testo del PDF.",
                   "fornitori": forn}, f, ensure_ascii=False, indent=2)
