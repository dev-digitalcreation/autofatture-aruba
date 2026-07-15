# -*- coding: utf-8 -*-
"""Test dell'archivio SQLite (Fase 1): duplicati, numerazione sicura, registro IVA."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import archivio  # noqa: E402

DB = os.path.join(tempfile.gettempdir(), "test_archivio_autofatture.db")


def _rec(prog, forn, numfatt, data_reg, imp, iva, tot, valuta="EUR"):
    return {
        "progressivo": prog, "numero": f"AUTO {prog}/26", "tipo_documento": "TD17",
        "fornitore": forn, "fornitore_id": "X", "num_fattura_originaria": numfatt,
        "data_fattura_originaria": "2026-01-01", "data_registrazione": data_reg,
        "imponibile": imp, "aliquota": "22.00", "imposta": iva, "totale": tot,
        "valuta": valuta, "filename": f"f{prog}.xml", "stato": "generata",
    }


def _reset():
    if os.path.exists(DB):
        os.remove(DB)


def test_registra_e_duplicato():
    _reset()
    archivio.registra(_rec(1, "Anthropic", "INV-1", "2026-01-15", 100, 22, 122), db_path=DB)
    # stesso fornitore + numero => duplicato (case/spazi insensibile)
    dup = archivio.esiste_duplicato(" anthropic ", "inv-1", db_path=DB)
    assert dup is not None and dup["num_fattura_originaria"] == "INV-1", dup
    # fornitore diverso o numero diverso => non duplicato
    assert archivio.esiste_duplicato("Google", "INV-1", db_path=DB) is None
    assert archivio.esiste_duplicato("Anthropic", "INV-2", db_path=DB) is None


def test_numerazione_sicura():
    _reset()
    for p in (1, 2, 3):
        archivio.registra(_rec(p, "F", f"N{p}", "2026-01-10", 10, 2.2, 12.2), db_path=DB)
    assert archivio.max_progressivo(db_path=DB) == 3
    assert archivio.prossimo_progressivo(db_path=DB) == 4
    # su archivio vuoto usa il fallback
    _reset()
    assert archivio.prossimo_progressivo(fallback=71, db_path=DB) == 71


def test_anomalie_numerazione():
    _reset()
    # progressivi: 1, 3, 3  -> manca il 2 (salto) e il 3 e' doppione
    archivio.registra(_rec(1, "F", "A", "2026-01-10", 10, 2.2, 12.2), db_path=DB)
    archivio.registra(_rec(3, "F", "B", "2026-01-11", 10, 2.2, 12.2), db_path=DB)
    archivio.registra(_rec(3, "F", "C", "2026-01-12", 10, 2.2, 12.2), db_path=DB)
    an = archivio.anomalie_numerazione(db_path=DB)
    testo = " ".join(an)
    assert "doppione" in testo.lower(), an
    assert "2" in testo, an  # il salto sul 2


def test_registro_iva():
    _reset()
    archivio.registra(_rec(1, "F", "A", "2026-01-15", 100, 22, 122), db_path=DB)
    archivio.registra(_rec(2, "F", "B", "2026-01-20", 200, 44, 244), db_path=DB)
    archivio.registra(_rec(3, "F", "C", "2026-02-05", 50, 11, 61), db_path=DB)
    reg = archivio.registro_iva(db_path=DB)
    per_mese = {r["mese"]: r for r in reg}
    assert round(per_mese["2026-01"]["imponibile"], 2) == 300.0, per_mese
    assert round(per_mese["2026-01"]["imposta"], 2) == 66.0, per_mese
    assert per_mese["2026-01"]["n"] == 2
    assert round(per_mese["2026-02"]["imponibile"], 2) == 50.0, per_mese
    # filtro anno
    assert len(archivio.registro_iva(anno=2026, db_path=DB)) == 2
    assert archivio.registro_iva(anno=2099, db_path=DB) == []


def _main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    fail = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as ex:
            fail += 1
            print(f"  FAIL  {t.__name__}: {ex}")
    _reset()
    print(f"\n{'TUTTI VERDI' if not fail else str(fail) + ' FALLITI'} ({len(tests) - fail}/{len(tests)})")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(_main())
