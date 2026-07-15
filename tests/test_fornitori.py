# -*- coding: utf-8 -*-
"""Test import/export fornitori (CSV / Excel .xlsx) di config_io."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import config_io  # noqa: E402

FORN = {
    "anthropic": {"denominazione": "Anthropic, PBC", "id_paese": "US", "id_codice": "OO99999999999",
                  "cap": "00000", "comune": "San Francisco", "nazione": "US", "tipo_documento": "TD17"},
    "acme srl": {"denominazione": "ACME S.r.l.", "id_paese": "IT", "id_codice": "IT01234567890",
                 "indirizzo": "Via Roma", "numero_civico": "1", "cap": "20100", "comune": "Milano",
                 "nazione": "IT", "tipo_documento": "TD19"},
}


def _tmp(nome):
    return os.path.join(tempfile.mkdtemp(prefix="reversa_test_"), nome)


def test_csv_roundtrip():
    p = _tmp("forn.csv")
    config_io.esporta_fornitori(FORN, p)
    back = config_io.importa_fornitori(p)
    assert set(back) == set(FORN), (set(back), set(FORN))
    assert back["acme srl"]["id_codice"] == "IT01234567890"
    assert back["acme srl"]["tipo_documento"] == "TD19"
    assert back["anthropic"]["comune"] == "San Francisco"


def test_xlsx_roundtrip():
    p = _tmp("forn.xlsx")
    config_io.esporta_fornitori(FORN, p)
    back = config_io.importa_fornitori(p)
    assert set(back) == set(FORN)
    assert back["acme srl"]["numero_civico"] == "1"
    assert back["anthropic"]["id_paese"] == "US"


def test_import_tollerante():
    """Intestazioni con maiuscole/spazi, chiave assente -> ricavata dalla denominazione; TD di default."""
    p = _tmp("tol.csv")
    with open(p, "w", encoding="utf-8-sig", newline="") as f:
        f.write("Denominazione;Id Paese;IdCodice\n")
        f.write("Pippo SRL;IT;IT99999999999\n")
    back = config_io.importa_fornitori(p)
    assert "pippo srl" in back, back
    assert back["pippo srl"]["tipo_documento"] == "TD17"   # default
    assert back["pippo srl"]["cap"] == "00000"             # default
    assert back["pippo srl"]["id_codice"] == "IT99999999999"


def test_import_virgola():
    """CSV con delimitatore virgola: lo sniffer lo riconosce."""
    p = _tmp("comma.csv")
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write("chiave,denominazione,id_paese\n")
        f.write("beta,Beta Inc,US\n")
    back = config_io.importa_fornitori(p)
    assert back.get("beta", {}).get("denominazione") == "Beta Inc"


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
