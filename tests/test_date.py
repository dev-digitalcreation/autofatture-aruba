# -*- coding: utf-8 -*-
"""Test conversione date UI (GG-MM-AAAA) <-> motore/XML (ISO), senza rompere l'XML."""
import os
import sys
import copy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import main  # noqa: E402  (iso_to_it, it_to_iso)
import config_io  # noqa: E402
import motore  # noqa: E402
import validazione  # noqa: E402


def test_iso_to_it():
    assert main.iso_to_it("2026-03-15") == "15-03-2026"
    assert main.iso_to_it("") == ""
    assert main.iso_to_it("28-02-2026") == "28-02-2026"      # non ISO: lasciata


def test_it_to_iso():
    assert main.it_to_iso("15-03-2026") == "2026-03-15"
    assert main.it_to_iso("15/03/2026") == "2026-03-15"
    assert main.it_to_iso("5-3-2026") == "2026-03-05"        # zero-pad
    assert main.it_to_iso("2026-03-15") == "2026-03-15"      # gia' ISO -> passthrough
    assert main.it_to_iso("") == ""


def test_roundtrip():
    for iso in ("2026-01-01", "2026-12-31", "2025-06-09"):
        assert main.it_to_iso(main.iso_to_it(iso)) == iso


def test_xml_valido_da_data_italiana():
    cfg = copy.deepcopy(config_io.DEFAULT_CONFIG)
    cfg["azienda"] = {"denominazione": "Esempio Srl", "id_paese": "IT", "piva": "01234567890",
                      "codice_fiscale": "01234567890", "indirizzo": "Via A", "numero_civico": "1",
                      "cap": "00100", "comune": "Roma", "provincia": "RM", "nazione": "IT"}
    cfg["trasmittente"] = {"id_paese": "IT", "id_codice": "01234567890"}
    inv = {"tipo_documento": "TD17",
           "data": main.it_to_iso("15-03-2026"),                      # da UI italiana
           "aliquota_iva": "22.00", "imponibile": 100.0,
           "num_fattura_originaria": "T-1",
           "data_fattura_originaria": main.it_to_iso("28-02-2026"),   # da UI italiana
           "fornitore": {"denominazione": "Foreign Ltd", "id_paese": "IE", "id_codice": "IE1234567AB",
                         "indirizzo": "1 St", "cap": "00000", "comune": "Dublin", "nazione": "IE"},
           "righe": [{"descrizione": "Servizio", "quantita": 1, "prezzo": 100.0}]}
    assert inv["data"] == "2026-03-15" and inv["data_fattura_originaria"] == "2026-02-28"
    _fn, xml, _w = motore.genera_xml_bytes(inv, cfg, 1)
    ok, errs = validazione.valida_xml(xml)
    assert ok, "XML da date italiane deve restare valido:\n" + "\n".join(errs)


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
