# -*- coding: utf-8 -*-
"""
Rete di sicurezza (Fase 0) — test di regressione del motore.

Partendo da dati NON personali (azienda e fornitore fittizi definiti qui),
genera un'autofattura TD17 col motore e verifica:
  (a) l'XML e' ben formato;
  (b) e' valido contro lo schema ufficiale SDI (XSD FatturaPA v1.2.2, in tests/xsd/);
  (c) gli importi (imponibile, IVA 22%, totale) sono coerenti;
  (d) l'XML combacia campo-per-campo con il "golden" atteso (tests/golden/).

Esecuzione:
    python tests/test_regressione.py           # esegue tutti i controlli
    python tests/test_regressione.py --update-golden   # rigenera il golden
    pytest tests/                              # (se hai pytest installato)

Questo test deve restare VERDE al termine di ogni fase successiva.
"""
import os
import sys
import copy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from lxml import etree  # noqa: E402
import config_io  # noqa: E402
import motore  # noqa: E402

XSD_DIR = os.path.join(HERE, "xsd")
MAIN_XSD = os.path.join(XSD_DIR, "Schema_FatturaPA_1.2.2.xsd")
DSIG_XSD = os.path.join(XSD_DIR, "xmldsig-core-schema.xsd")
GOLDEN = os.path.join(HERE, "golden", "TD17_atteso.xml")

# --------------------------------------------------------------------------- #
# Dati di esempio FITTIZI (nessun dato reale). L'azienda si autotrasmette.
# --------------------------------------------------------------------------- #
CFG_ESEMPIO = copy.deepcopy(config_io.DEFAULT_CONFIG)
CFG_ESEMPIO["azienda"] = {
    "denominazione": "Esempio Servizi S.r.l.", "id_paese": "IT",
    "piva": "01234567890", "codice_fiscale": "01234567890",
    "indirizzo": "Via Esempio", "numero_civico": "10", "cap": "00100",
    "comune": "Roma", "provincia": "RM", "nazione": "IT",
}
CFG_ESEMPIO["trasmittente"] = {"id_paese": "IT", "id_codice": "01234567890"}
CFG_ESEMPIO["codice_destinatario"] = "0000000"
CFG_ESEMPIO["numerazione"] = {"pattern": "AUTO {n}/{yy}"}

INV_ESEMPIO = {
    "tipo_documento": "TD17",
    "data": "2026-03-15",
    "aliquota_iva": "22.00",
    "imponibile": 100.00,
    "num_fattura_originaria": "TEST-001",
    "data_fattura_originaria": "2026-02-28",
    "fornitore": {
        "denominazione": "Foreign Supplier Ltd", "id_paese": "IE",
        "id_codice": "IE1234567AB", "indirizzo": "1 Test Street",
        "cap": "00000", "comune": "Dublin", "nazione": "IE",
    },
    "righe": [{"descrizione": "Servizio di esempio", "quantita": 1, "prezzo": 100.00}],
}
PROG = 1


# --------------------------------------------------------------------------- #
# Helper
# --------------------------------------------------------------------------- #
def genera():
    """Ritorna (filename, xml_bytes) per l'autofattura di esempio."""
    fname, xml, _warn = motore.genera_xml_bytes(INV_ESEMPIO, CFG_ESEMPIO, PROG)
    return fname, xml


class _LocalXSDResolver(etree.Resolver):
    """Reindirizza l'import xmldsig (URL W3C) alla copia locale in tests/xsd/."""
    def resolve(self, system_url, public_id, context):
        if system_url and "xmldsig-core-schema" in system_url:
            return self.resolve_filename(DSIG_XSD, context)
        return None


def _carica_schema():
    parser = etree.XMLParser(no_network=True)
    parser.resolvers.add(_LocalXSDResolver())
    xsd_doc = etree.parse(MAIN_XSD, parser)
    return etree.XMLSchema(xsd_doc)


# --------------------------------------------------------------------------- #
# Test
# --------------------------------------------------------------------------- #
def test_xml_ben_formato():
    _fname, xml = genera()
    root = etree.fromstring(xml)                      # solleva se malformato
    assert etree.QName(root).localname == "FatturaElettronica"


def test_valido_xsd():
    _fname, xml = genera()
    schema = _carica_schema()
    doc = etree.fromstring(xml)
    if not schema.validate(doc):
        errori = "\n".join(f"  - riga {e.line}: {e.message}" for e in schema.error_log)
        raise AssertionError("XML NON valido contro l'XSD FatturaPA 1.2.2:\n" + errori)


def test_importi_coerenti():
    imponibile, aliquota, imposta, totale = motore.calcola_importi(INV_ESEMPIO)
    assert str(imponibile) == "100.00", imponibile
    assert str(aliquota) == "22.00", aliquota
    assert str(imposta) == "22.00", imposta
    assert str(totale) == "122.00", totale


def test_golden_campo_per_campo():
    _fname, xml = genera()
    if not os.path.exists(GOLDEN):
        raise AssertionError(f"Golden mancante: {GOLDEN}. Rigeneralo con --update-golden.")
    with open(GOLDEN, "rb") as f:
        atteso = f.read()
    gen_tree = etree.fromstring(xml)
    exp_tree = etree.fromstring(atteso)
    gen_els = list(gen_tree.iter())
    exp_els = list(exp_tree.iter())
    assert len(gen_els) == len(exp_els), (
        f"Numero elementi diverso: generato={len(gen_els)} atteso={len(exp_els)}")
    for i, (g, e) in enumerate(zip(gen_els, exp_els)):
        gt, et = etree.QName(g).localname, etree.QName(e).localname
        assert gt == et, f"Campo #{i}: tag '{gt}' != atteso '{et}'"
        gv = (g.text or "").strip()
        ev = (e.text or "").strip()
        assert gv == ev, f"Campo '{gt}' (#{i}): valore '{gv}' != atteso '{ev}'"


# --------------------------------------------------------------------------- #
# Runner standalone (senza pytest)
# --------------------------------------------------------------------------- #
def _aggiorna_golden():
    os.makedirs(os.path.dirname(GOLDEN), exist_ok=True)
    _fname, xml = genera()
    with open(GOLDEN, "wb") as f:
        f.write(xml)
    print(f"Golden aggiornato: {GOLDEN} ({len(xml)} bytes)")


def _main():
    if "--update-golden" in sys.argv:
        _aggiorna_golden()
        return 0
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    fail = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
        except Exception as ex:
            fail += 1
            print(f"  FAIL  {t.__name__}: {ex}")
    print(f"\n{'TUTTI VERDI' if not fail else str(fail) + ' TEST FALLITI'} "
          f"({len(tests) - fail}/{len(tests)})")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(_main())
