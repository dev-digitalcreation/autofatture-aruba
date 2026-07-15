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


def test_import_struttura_aruba():
    """Import di un export in stile Aruba: 18 colonne con Denominazione/Nome/
    Cognome distinte. La colonna 'Nome' (vuota o valorizzata) NON deve
    sovrascrivere la Denominazione. NB: dati completamente fittizi."""
    import openpyxl
    p = _tmp("aruba.xlsx")
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["Codice fornitore", "Email", "PEC", "ID Paese", "Partita Iva",
               "Codice Fiscale", "Denominazione", "Nome", "Cognome", "Regime Fiscale",
               "Nazione", "CAP", "Provincia", "Comune", "Indirizzo", "Numero civico",
               "Telefono", "Invio codice destinatario"])
    # azienda (Nome/Cognome vuoti)
    ws.append(["", "", "", "IT", "IT11111111111", "IT11111111111", "Alfa S.r.l.", "", "",
               "RF01", "IT", "20100", "MI", "Milano", "Via Esempio", "1", "", "Non inviato"])
    # estero reverse charge
    ws.append(["", "", "", "IE", "IE1234567AA", "", "Beta Cloud Ltd.", "", "",
               "RF18", "IE", "00000", "", "Dublin", "1 Example Street", "", "", "Non inviato"])
    # persona fisica: Denominazione piena, Nome/Cognome pure (non devono clobberare)
    ws.append(["", "", "", "IT", "IT22222222222", "", "Rossi Mario", "Mario", "Rossi",
               "RF01", "IT", "20100", "MI", "Milano", "Via Prova", "2", "", "Non inviato"])
    wb.save(p)

    back = config_io.importa_fornitori(p)
    assert len(back) == 3, back
    assert back["alfa s.r.l."]["id_codice"] == "IT11111111111"
    assert back["alfa s.r.l."]["comune"] == "Milano"
    assert back["beta cloud ltd."]["id_paese"] == "IE"
    assert back["beta cloud ltd."]["id_codice"] == "IE1234567AA"
    # la colonna "Nome" NON ha sovrascritto la denominazione
    assert "rossi mario" in back, list(back)
    assert back["rossi mario"]["denominazione"] == "Rossi Mario"


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
