# -*- coding: utf-8 -*-
"""Test del modulo anteprima (Fase 2): render PNG della prima pagina + fallback."""
import os
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import anteprima  # noqa: E402

PDF = os.path.join(tempfile.gettempdir(), "test_anteprima_probe.pdf")


def _crea_pdf():
    import pypdfium2 as pdfium
    pdf = pdfium.PdfDocument.new()
    pdf.new_page(200, 200)
    pdf.save(PDF)


def test_render_png():
    _crea_pdf()
    png = anteprima.render_png(PDF)
    assert png is not None and len(png) > 100, "atteso PNG non vuoto"
    assert png[:8] == b"\x89PNG\r\n\x1a\n", "header PNG non valido"


def test_render_path_invalido():
    assert anteprima.render_png(os.path.join(tempfile.gettempdir(), "non_esiste_xyz.pdf")) is None


def test_estrai_testo_path_invalido():
    assert anteprima.estrai_testo("non_esiste_xyz.pdf") == ""


def _main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    fail = 0
    for t in tests:
        try:
            t(); print(f"  PASS  {t.__name__}")
        except Exception as ex:
            fail += 1; print(f"  FAIL  {t.__name__}: {ex}")
    try:
        os.remove(PDF)
    except OSError:
        pass
    print(f"\n{'TUTTI VERDI' if not fail else str(fail) + ' FALLITI'} ({len(tests) - fail}/{len(tests)})")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(_main())
