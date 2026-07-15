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
    # chiave = denominazione completa (tipico import Aruba): raramente compare nel PDF.
    # Anagrafica COMPLETA di indirizzo: è ciò che deve finire nell'XML.
    "beta cloud ltd.": {"denominazione": "Beta Cloud Ltd.", "id_paese": "IE",
                        "id_codice": "IE1234567AA", "indirizzo": "1 Example Quay",
                        "numero_civico": "33", "cap": "00000", "comune": "Dublin",
                        "nazione": "IE", "tipo_documento": "TD17"},
    "alfa s.r.l.": {"denominazione": "Alfa S.r.l.", "id_paese": "IT",
                    "id_codice": "01234567890", "tipo_documento": "TD19"},
    # fornitore USA senza VAT: placeholder condiviso, chiave breve e distintiva
    "gamma": {"denominazione": "Gamma LLC", "id_paese": "US",
              "id_codice": "OO99999999999", "tipo_documento": "TD17"},
}


def test_match_per_piva_estera():
    """Riconosciuto per P.IVA anche se la chiave (denominazione) non compare nel testo,
    e l'anagrafica restituita include l'INDIRIZZO salvato."""
    testo = "INVOICE\nSupplier VAT: IE 1234567AA\nAmount due 100.00 EUR"
    ch, ana = estrazione._fornitore_noto(testo, FORN)
    assert ch == "beta cloud ltd." and ana["id_codice"] == "IE1234567AA"
    assert ana["indirizzo"] == "1 Example Quay" and ana["comune"] == "Dublin"


def test_indirizzo_riconosciuto_finisce_nell_xml():
    """End-to-end: l'indirizzo dell'anagrafica del fornitore riconosciuto deve
    comparire nella Sede del CedentePrestatore dell'XML generato."""
    import copy
    from lxml import etree
    import config_io
    import motore

    ana = FORN["beta cloud ltd."]                       # come se riconosciuto per P.IVA
    cfg = copy.deepcopy(config_io.DEFAULT_CONFIG)
    cfg["azienda"] = {"denominazione": "Esempio S.r.l.", "id_paese": "IT",
                      "piva": "01234567890", "codice_fiscale": "01234567890",
                      "indirizzo": "Via Azienda", "numero_civico": "10", "cap": "00100",
                      "comune": "Roma", "provincia": "RM", "nazione": "IT"}
    cfg["trasmittente"] = {"id_paese": "IT", "id_codice": "01234567890"}
    cfg["codice_destinatario"] = "0000000"
    cfg["numerazione"] = {"pattern": "AUTO {n}/{yy}"}

    inv = {
        "tipo_documento": "TD17", "data": "2026-03-15", "aliquota_iva": "22.00",
        "imponibile": 100.00, "num_fattura_originaria": "T-1",
        "data_fattura_originaria": "2026-02-28",
        "fornitore": dict(ana),                          # anagrafica salvata (con indirizzo)
        "righe": [{"descrizione": "Servizio", "quantita": 1, "prezzo": 100.00}],
    }
    _fname, xml, _warn = motore.genera_xml_bytes(inv, cfg, 1)
    root = etree.fromstring(xml)

    # individua la Sede del CedentePrestatore e verifica l'indirizzo salvato
    ced = [e for e in root.iter() if etree.QName(e).localname == "CedentePrestatore"]
    assert ced, "CedentePrestatore assente"
    sede = [e for e in ced[0].iter() if etree.QName(e).localname == "Sede"][0]
    campi = {etree.QName(x).localname: (x.text or "").strip() for x in sede}
    assert campi.get("Indirizzo") == "1 Example Quay", campi
    assert campi.get("Comune") == "Dublin", campi
    assert campi.get("Nazione") == "IE", campi


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
