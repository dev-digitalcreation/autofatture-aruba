# -*- coding: utf-8 -*-
"""Test riconoscimento fornitore noto (_fornitore_noto): match per P.IVA e per chiave.
Dati fittizi."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import estrazione  # noqa: E402

FORN = {
    # chiave = denominazione completa (tipico import Aruba): raramente compare nel PDF
    "beta cloud ltd.": {"denominazione": "Beta Cloud Ltd.", "id_paese": "IE",
                        "id_codice": "IE1234567AA", "tipo_documento": "TD17"},
    "alfa s.r.l.": {"denominazione": "Alfa S.r.l.", "id_paese": "IT",
                    "id_codice": "01234567890", "tipo_documento": "TD19"},
    # fornitore USA senza VAT: placeholder condiviso, chiave breve e distintiva
    "gamma": {"denominazione": "Gamma LLC", "id_paese": "US",
              "id_codice": "OO99999999999", "tipo_documento": "TD17"},
}


def test_match_per_piva_estera():
    """Riconosciuto per P.IVA anche se la chiave (denominazione) non compare nel testo."""
    testo = "INVOICE\nSupplier VAT: IE 1234567AA\nAmount due 100.00 EUR"
    ch, ana = estrazione._fornitore_noto(testo, FORN)
    assert ch == "beta cloud ltd." and ana["id_codice"] == "IE1234567AA"


def test_match_per_piva_italiana_con_prefisso():
    """P.IVA italiana con prefisso IT nel testo, salvata senza prefisso."""
    testo = "Fattura n. 5\nPartita IVA: IT01234567890\nTotale 100"
    ch, _ = estrazione._fornitore_noto(testo, FORN)
    assert ch == "alfa s.r.l."


def test_fallback_per_chiave():
    """Nessuna P.IVA nota nel testo -> match per chiave testuale (fornitore USA)."""
    testo = "Receipt from Gamma, thank you. No VAT number."
    ch, _ = estrazione._fornitore_noto(testo, FORN)
    assert ch == "gamma"


def test_placeholder_oo_non_matcha():
    """Il placeholder OO99999999999 non deve MAI fare match (condiviso tra fornitori)."""
    testo = "Sconosciuto srl - codice OO99999999999 - importo 50"
    ch, _ = estrazione._fornitore_noto(testo, FORN)
    assert ch is None


def test_nessun_match():
    ch, ana = estrazione._fornitore_noto("Fornitore mai visto, VAT ZZ000, 10 EUR", FORN)
    assert ch is None and ana is None


def _main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    fail = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}")
        except Exception as ex:
            fail += 1; print(f"  FAIL  {t.__name__}: {ex}")
    print(f"\n{'TUTTI VERDI' if not fail else str(fail) + ' FALLITI'} ({len(tests) - fail}/{len(tests)})")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(_main())
