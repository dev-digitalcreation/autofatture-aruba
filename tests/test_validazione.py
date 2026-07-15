# -*- coding: utf-8 -*-
"""Test del modulo di validazione XSD (Fase 1): accetta il valido, rifiuta il non conforme."""
import os
import sys
import copy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import config_io  # noqa: E402
import motore  # noqa: E402
import validazione  # noqa: E402

NS = "http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2"


def _xml_valido():
    cfg = copy.deepcopy(config_io.DEFAULT_CONFIG)
    cfg["azienda"] = {"denominazione": "Esempio Srl", "id_paese": "IT", "piva": "01234567890",
                      "codice_fiscale": "01234567890", "indirizzo": "Via A", "numero_civico": "1",
                      "cap": "00100", "comune": "Roma", "provincia": "RM", "nazione": "IT"}
    cfg["trasmittente"] = {"id_paese": "IT", "id_codice": "01234567890"}
    inv = {"tipo_documento": "TD17", "data": "2026-03-15", "aliquota_iva": "22.00",
           "imponibile": 100.0, "num_fattura_originaria": "T-1", "data_fattura_originaria": "2026-02-01",
           "fornitore": {"denominazione": "Foreign Ltd", "id_paese": "IE", "id_codice": "IE1234567AB",
                         "indirizzo": "1 St", "cap": "00000", "comune": "Dublin", "nazione": "IE"},
           "righe": [{"descrizione": "Servizio", "quantita": 1, "prezzo": 100.0}]}
    _fn, xml, _w = motore.genera_xml_bytes(inv, cfg, 1)
    return xml


def test_valida_ok():
    ok, errs = validazione.valida_xml(_xml_valido())
    assert ok and errs == [], errs


def test_valida_malformato():
    ok, errs = validazione.valida_xml(b"<non><chiuso>")
    assert not ok and errs


def test_valida_non_conforme():
    # root corretto ma contenuto non conforme allo schema -> deve fallire
    xml = (f'<?xml version="1.0" encoding="UTF-8"?>'
           f'<p:FatturaElettronica versione="FPR12" xmlns:p="{NS}"><Bogus/></p:FatturaElettronica>'
           ).encode("utf-8")
    ok, errs = validazione.valida_xml(xml)
    assert not ok and errs, "un XML non conforme deve essere rifiutato"


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
