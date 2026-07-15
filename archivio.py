# -*- coding: utf-8 -*-
"""
Archivio locale (SQLite) delle autofatture generate.

Sta in %APPDATA%\\AutofattureAruba\\archivio.db (stessa cartella scrivibile della
config). Serve per: storico, rilevamento duplicati e numerazione sicura.
Nessun dato personale nel repo: il DB e' solo sul PC dell'utente.
"""
import os
import sqlite3
from datetime import datetime

import config_io

DB_PATH = os.path.join(config_io.BASE, "archivio.db")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS autofatture (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    progressivo            INTEGER,
    numero                 TEXT,
    tipo_documento         TEXT,
    fornitore              TEXT,
    fornitore_id           TEXT,
    num_fattura_originaria TEXT,
    data_fattura_originaria TEXT,
    data_registrazione     TEXT,
    imponibile             REAL,
    aliquota               TEXT,
    imposta                REAL,
    totale                 REAL,
    valuta                 TEXT,
    filename               TEXT,
    stato                  TEXT,
    creato_il              TEXT
);
"""


def _norm(s) -> str:
    return (s or "").strip().lower()


def _conn(db_path: str = None):
    con = sqlite3.connect(db_path or DB_PATH)
    con.row_factory = sqlite3.Row
    con.execute(_SCHEMA)
    con.commit()
    return con


def registra(rec: dict, db_path: str = None) -> int:
    """Inserisce un'autofattura generata. Ritorna l'id."""
    campi = ["progressivo", "numero", "tipo_documento", "fornitore", "fornitore_id",
             "num_fattura_originaria", "data_fattura_originaria", "data_registrazione",
             "imponibile", "aliquota", "imposta", "totale", "valuta", "filename", "stato"]
    vals = [rec.get(c) for c in campi]
    con = _conn(db_path)
    try:
        cur = con.execute(
            f"INSERT INTO autofatture ({','.join(campi)}, creato_il) "
            f"VALUES ({','.join(['?'] * len(campi))}, ?)",
            vals + [datetime.now().isoformat(timespec="seconds")])
        con.commit()
        return cur.lastrowid
    finally:
        con.close()


def esiste_duplicato(fornitore: str, num_fattura: str, db_path: str = None):
    """
    Ritorna il record (dict) se esiste gia' un'autofattura con lo stesso
    (fornitore + numero fattura originaria), altrimenti None.
    """
    if not _norm(num_fattura):
        return None
    con = _conn(db_path)
    try:
        row = con.execute(
            "SELECT * FROM autofatture "
            "WHERE lower(trim(fornitore))=? AND lower(trim(num_fattura_originaria))=? "
            "ORDER BY id LIMIT 1",
            (_norm(fornitore), _norm(num_fattura))).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def max_progressivo(db_path: str = None) -> int:
    con = _conn(db_path)
    try:
        row = con.execute("SELECT MAX(progressivo) AS m FROM autofatture").fetchone()
        return int(row["m"]) if row and row["m"] is not None else 0
    finally:
        con.close()


def prossimo_progressivo(fallback: int = 1, db_path: str = None) -> int:
    """Prossimo numero sezionale proposto (max in archivio + 1), o `fallback` se vuoto."""
    m = max_progressivo(db_path)
    return m + 1 if m > 0 else fallback


def anomalie_numerazione(db_path: str = None) -> list:
    """Segnala doppioni e salti nella sequenza dei progressivi (lista di messaggi)."""
    con = _conn(db_path)
    try:
        rows = con.execute(
            "SELECT progressivo, COUNT(*) AS n FROM autofatture "
            "WHERE progressivo IS NOT NULL GROUP BY progressivo ORDER BY progressivo").fetchall()
    finally:
        con.close()
    msg = []
    nums = [r["progressivo"] for r in rows]
    for r in rows:
        if r["n"] > 1:
            msg.append(f"Numero {r['progressivo']} usato {r['n']} volte (doppione).")
    if nums:
        attesi = set(range(nums[0], nums[-1] + 1))
        mancanti = sorted(attesi - set(nums))
        if mancanti:
            msg.append("Salti nella numerazione: " + ", ".join(map(str, mancanti)) + ".")
    return msg


def elenco(limit: int = 500, db_path: str = None) -> list:
    con = _conn(db_path)
    try:
        rows = con.execute(
            "SELECT * FROM autofatture ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
