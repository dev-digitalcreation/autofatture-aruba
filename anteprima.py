# -*- coding: utf-8 -*-
"""
Anteprima di un PDF per l'interfaccia: rende la prima pagina come PNG
(pypdfium2 + Pillow, gia' dipendenze) oppure, in fallback, ne estrae il testo.
Nessuna nuova dipendenza; pypdfium2 e' gia' incluso nell'exe.
"""
import io


def render_png(path, scale: float = 1.6):
    """Ritorna i bytes PNG della prima pagina del PDF, o None se non renderizzabile."""
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(path)
        try:
            if len(pdf) == 0:
                return None
            bmp = pdf[0].render(scale=scale)
            pil = bmp.to_pil()
            buf = io.BytesIO()
            pil.save(buf, format="PNG")
            return buf.getvalue()
        finally:
            pdf.close()
    except Exception:
        return None


def estrai_testo(path, max_char: int = 4000) -> str:
    """Fallback: testo della prima pagina (pdfplumber). '' se non disponibile."""
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            if not pdf.pages:
                return ""
            return (pdf.pages[0].extract_text() or "")[:max_char]
    except Exception:
        return ""
