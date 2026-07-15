# -*- coding: utf-8 -*-
"""
Validazione dell'XML generato contro lo schema ufficiale SDI (FatturaPA v1.2.2).

Gli XSD sono in `schema/` (inclusi nell'exe via `flet pack --add-data schema:schema`).
L'import xmldsig (URL W3C) viene risolto sulla copia locale, senza accessi di rete.
"""
import os
import sys
from lxml import etree


def _schema_dir() -> str:
    if getattr(sys, "frozen", False):                       # exe (PyInstaller onefile)
        base = getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    else:                                                   # da sorgente
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "schema")


SCHEMA_DIR = _schema_dir()
MAIN_XSD = os.path.join(SCHEMA_DIR, "Schema_FatturaPA_1.2.2.xsd")
DSIG_XSD = os.path.join(SCHEMA_DIR, "xmldsig-core-schema.xsd")


class _LocalResolver(etree.Resolver):
    """Reindirizza l'import xmldsig (URL W3C) alla copia locale in schema/."""
    def resolve(self, system_url, public_id, context):
        if system_url and "xmldsig-core-schema" in system_url:
            return self.resolve_filename(DSIG_XSD, context)
        return None


_schema_cache = None


def _schema():
    global _schema_cache
    if _schema_cache is None:
        parser = etree.XMLParser(no_network=True)
        parser.resolvers.add(_LocalResolver())
        xsd_doc = etree.parse(MAIN_XSD, parser)
        _schema_cache = etree.XMLSchema(xsd_doc)
    return _schema_cache


def disponibile() -> bool:
    """True se gli XSD sono presenti (utile per degradare senza crash)."""
    return os.path.exists(MAIN_XSD) and os.path.exists(DSIG_XSD)


def valida_xml(xml) -> tuple:
    """
    Valida `xml` (bytes o str) contro lo schema FatturaPA 1.2.2.
    Ritorna (ok: bool, errori: list[str]).
    """
    try:
        data = xml if isinstance(xml, (bytes, bytearray)) else xml.encode("utf-8")
        doc = etree.fromstring(data)
    except etree.XMLSyntaxError as ex:
        return False, [f"XML non ben formato: {ex}"]
    if not disponibile():
        return False, ["Schema XSD non disponibile."]
    schema = _schema()
    if schema.validate(doc):
        return True, []
    return False, [f"riga {e.line}: {e.message}" for e in schema.error_log]
