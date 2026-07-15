# -*- coding: utf-8 -*-
"""
Estrazione dati da PDF di fatture passive estere/reverse charge.

Strategia:
  1) riconoscimento fornitori ricorrenti (Anthropic, SiteGround, Google, ...);
  2) euristiche generiche robuste (nome fornitore, P.IVA/VAT, paese, importi, numero, data).
Restituisce un dict con i campi + una lista di 'note' sui punti incerti,
che la GUI evidenzia (bordo giallo) per la revisione manuale.
"""
import os
import re
import json
import pdfplumber
from dateutil import parser as dateparser


# --------------------------------------------------------------------------- #
# Anagrafiche fornitori ricorrenti (caricate da config/fornitori.json)
# --------------------------------------------------------------------------- #
_DEFAULT_FORNITORI = {
    "anthropic": {
        "denominazione": "Anthropic, PBC", "id_paese": "US", "id_codice": "OO99999999999",
        "indirizzo": "548 Market Street PMB 90375", "cap": "00000", "comune": "San Francisco",
        "nazione": "US", "tipo_documento": "TD17",
    },
    "siteground": {
        "denominazione": "SiteGround Spain S.L.", "id_paese": "ES", "id_codice": "B87194171",
        "indirizzo": "28004 Calle Prim", "numero_civico": "19", "cap": "00000", "comune": "Madrid",
        "nazione": "ES", "tipo_documento": "TD17",
    },
    "vercel": {
        "denominazione": "Vercel Inc.", "id_paese": "US", "id_codice": "OO99999999999",
        "indirizzo": "440 N Barranca Ave #4133", "cap": "00000", "comune": "Covina",
        "nazione": "US", "tipo_documento": "TD17",
    },
}

_FORNITORI_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "fornitori.json")


def carica_fornitori() -> dict:
    try:
        import config_io
        return config_io.carica_fornitori()
    except Exception:
        pass
    try:
        with open(_FORNITORI_PATH, encoding="utf-8") as f:
            return json.load(f).get("fornitori", _DEFAULT_FORNITORI)
    except Exception:
        return dict(_DEFAULT_FORNITORI)


# Paesi UE (per stimare UE vs extra-UE)
UE = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "FR", "DE", "GR", "HU", "IE",
      "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}

# Prefisso VAT -> codice ISO paese (per lo piu' coincidono; eccezione: EL=Grecia)
VAT_PREFIX_ISO = {"EL": "GR"}
VAT_PREFIXES = {c for c in UE} | {"EL"} | {"GB", "CH", "NO"}

# Nomi paese (varie lingue) -> ISO
PAESI_TESTO = {
    "united states": "US", "stati uniti": "US", " usa": "US", "u.s.a": "US", "america": "US",
    "united kingdom": "GB", "regno unito": "GB", "england": "GB", "great britain": "GB",
    "ireland": "IE", "irlanda": "IE", "eire": "IE",
    "spain": "ES", "spagna": "ES", "españa": "ES", "espana": "ES",
    "germany": "DE", "germania": "DE", "deutschland": "DE",
    "france": "FR", "francia": "FR",
    "netherlands": "NL", "paesi bassi": "NL", "nederland": "NL", "holland": "NL",
    "luxembourg": "LU", "lussemburgo": "LU",
    "belgium": "BE", "belgio": "BE", "belgique": "BE",
    "portugal": "PT", "portogallo": "PT",
    "austria": "AT", "österreich": "AT",
    "poland": "PL", "polonia": "PL", "polska": "PL",
    "sweden": "SE", "svezia": "SE", "sverige": "SE",
    "denmark": "DK", "danimarca": "DK",
    "finland": "FI", "finlandia": "FI",
    "greece": "GR", "grecia": "GR",
    "czech": "CZ", "repubblica ceca": "CZ",
    "romania": "RO", "hungary": "HU", "ungheria": "HU",
    "switzerland": "CH", "svizzera": "CH", "schweiz": "CH", "suisse": "CH",
    "norway": "NO", "norvegia": "NO",
    "canada": "CA", "australia": "AU", "india": "IN", "japan": "JP", "giappone": "JP",
    "singapore": "SG", "israel": "IL", "israele": "IL",
}

# suffissi societari per riconoscere il nome del fornitore
SUFFISSI = (r"S\.?R\.?L\.?S?|S\.?P\.?A\.?|S\.?A\.?S\.?|S\.?A\.?|S\.?L\.?U?|L\.?L\.?C|LLC|"
            r"L\.?T\.?D|LIMITED|INC\.?|CORP\.?|CO\.?|COMPANY|PBC|PLC|GMBH|UG|KG|OHG|MBH|"
            r"S\.?A\.?R\.?L|SARL|SAS|B\.?V\.?|N\.?V\.?|OY|OYJ|AB|A/S|AS|LDA|UAB|SP\.?\s?Z\.?O\.?O")

# marker che introducono il blocco del CLIENTE (per separarlo dal fornitore).
# usati anche a meta' riga: le fatture a due colonne fondono fornitore + cliente.
MARKER_CLIENTE = ["indirizzo di fatturazione", "indirizzo di spedizione",
                  "billing address", "shipping address", "bill to", "billed to",
                  "invoice to", "sold to", "ship to", "fatturato a", "fattura a",
                  "intestatario", "destinatario", "cessionario", "cliente",
                  "customer", "buyer"]

# mesi italiani/inglesi -> numero (per date tipo "15 febbraio 2026")
MESI = {"gennaio": 1, "febbraio": 2, "marzo": 3, "aprile": 4, "maggio": 5, "giugno": 6,
        "luglio": 7, "agosto": 8, "settembre": 9, "ottobre": 10, "novembre": 11, "dicembre": 12,
        "gen": 1, "feb": 2, "mar": 3, "apr": 4, "mag": 5, "giu": 6, "lug": 7, "ago": 8,
        "set": 9, "ott": 10, "nov": 11, "dic": 12,
        "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7,
        "august": 8, "september": 9, "october": 10, "november": 11, "december": 12}

# Totale finale della fattura, in ordine di priorità (vince il primo trovato)
TOTALE = [
    ["total due", "amount due", "importo dovuto", "balance due", "total a pagar", "total à payer"],
    ["total invoice", "invoice total", "totale fattura", "totale documento"],
    ["grand total", "importo totale", "total amount", "gesamtbetrag", "montant total", "importe total"],
    ["totale", "total"],
]
# righe da NON confondere col totale finale (subtotali, netti, IVA, imponibili parziali)
_ESCLUDI_TOT = ("subtotal", "sub-total", "sub total", "subtotale", "parziale",
                "imponibil", "imponibl", "netto", "net", "excl", " ht", "iva", "vat")


def _estrai_testo(path: str) -> str:
    parti = []
    with pdfplumber.open(path) as pdf:
        for pag in pdf.pages:
            parti.append(pag.extract_text() or "")
    return "\n".join(parti).replace("\x00", "-")   # ripristina trattini mappati a NUL


# --------------------------------------------------------------------------- #
# Importi
# --------------------------------------------------------------------------- #
def _parse_importo(s: str):
    s = re.sub(r"[^\d.,]", "", s)
    if not s:
        return None
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".") if s.rfind(",") > s.rfind(".") else s.replace(",", "")
    elif "," in s:
        # virgola: decimale se seguono 1-2 cifre, altrimenti migliaia
        s = s.replace(",", ".") if re.search(r",\d{1,2}$", s) else s.replace(",", "")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


_AMT = re.compile(r"(?:€|\$|£|EUR|USD|GBP|CHF)?\s?(\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{1,2})?|\d+(?:[.,]\d{1,2})?)\s*(?:€|\$|£|EUR|USD|GBP|CHF)?", re.I)


def _importi_riga(riga: str):
    out = []
    for m in _AMT.finditer(riga):
        v = _parse_importo(m.group(1))
        if v is not None:
            out.append(v)
    return out


def _trova_importo(testo: str):
    """Imponibile = TOTALE finale della fattura (Total Due / Amount due / Totale).
    Ignora subtotali/netti/imponibili parziali. Ritorna (valore, incerto)."""
    righe = testo.splitlines()
    for gruppo in TOTALE:
        for r in righe:
            rl = r.lower()
            if any(et in rl for et in gruppo) and not any(x in rl for x in _ESCLUDI_TOT):
                vals = _importi_riga(r)
                if vals:
                    return vals[-1], False
    # ripiego: fatture italiane che riportano solo "Imponibile"
    for r in righe:
        if "imponibil" in r.lower():
            vals = _importi_riga(r)
            if vals:
                return vals[-1], False
    # ultimo ripiego: importo piu' grande del documento (da verificare)
    tutti = [x for r in righe for x in _importi_riga(r)]
    if tutti:
        return max(tutti), True
    return None, True


# --------------------------------------------------------------------------- #
# P.IVA / VAT / paese
# --------------------------------------------------------------------------- #
def _norm(s):
    return re.sub(r"[\s\.]", "", s or "").upper()


def _trova_vat(testo: str, piva_cess: str):
    """Ritorna (id_paese, id_codice) del fornitore. Esclude la P.IVA del cessionario."""
    escl = {_norm("IT" + piva_cess), _norm(piva_cess)}
    trovate = []
    # 1) VAT con prefisso paese (UE + GB/CH/NO)
    for m in re.finditer(r"\b([A-Z]{2})\s?-?\s?([A-Z0-9]{7,12})\b", testo):
        pref, code = m.group(1).upper(), m.group(2).upper()
        if pref in VAT_PREFIXES and _norm(pref + code) not in escl:
            iso = VAT_PREFIX_ISO.get(pref, pref)
            trovate.append((iso, code))
    # preferisci un fornitore NON italiano
    for iso, code in trovate:
        if iso != "IT":
            return iso, code
    if trovate:
        return trovate[0]
    # 2) VAT/P.IVA senza prefisso, guidata da etichetta
    for m in re.finditer(r"(?:vat|p\.?\s?iva|partita iva|tax id|cif|nif|ust-?idnr|tva|btw)"
                         r"[^\dA-Z]{0,8}([A-Z]{0,2}\s?-?\d[\dA-Z\-]{5,13})", testo, re.I):
        raw = _norm(m.group(1))
        if raw in escl:
            continue
        mpref = re.match(r"^([A-Z]{2})(.+)$", raw)
        if mpref and mpref.group(1) in VAT_PREFIXES:
            return VAT_PREFIX_ISO.get(mpref.group(1), mpref.group(1)), mpref.group(2)
        return None, raw   # numero senza paese: paese verra' dedotto altrove
    return None, None


def _trova_paese(testo: str):
    tl = " " + testo.lower() + " "
    # ordina per lunghezza del nome per evitare match parziali
    for nome in sorted(PAESI_TESTO, key=len, reverse=True):
        if nome in tl:
            return PAESI_TESTO[nome]
    return None


# --------------------------------------------------------------------------- #
# Nome fornitore
# --------------------------------------------------------------------------- #
def _blocco_fornitore(testo: str) -> str:
    """Ritorna la parte di testo che precede il blocco cliente (intestazione fornitore)."""
    tl = testo.lower()
    pos = [tl.find(m) for m in MARKER_CLIENTE if tl.find(m) > 0]
    cut = min(pos) if pos else None
    head = testo[:cut] if cut else "\n".join(testo.splitlines()[:15])
    return head


def _taglia_marker_cliente(s: str) -> str:
    """Rimuove dalla riga eventuale testo del blocco cliente (fatture a 2 colonne)."""
    low = s.lower()
    tagli = [low.find(mk) for mk in MARKER_CLIENTE if low.find(mk) > 0]
    if tagli:
        s = s[:min(tagli)]
    return re.sub(r"\s{2,}", " ", s).strip(" ,;•|")


def _trova_denominazione(testo: str, piva_cess: str) -> str:
    head = _blocco_fornitore(testo)
    righe = [r.strip() for r in head.splitlines() if r.strip()]
    suff = re.compile(rf"\b({SUFFISSI})\b", re.I)
    esclusi = ("invoice", "fattura", "receipt", "ricevuta", "page", "pagina",
               "date", "data", "numero", "vat", "p.iva", "partita")
    # 1) prima riga con forma societaria -> tronca ALLA FINE del suffisso
    #    (gestisce le righe che fondono fornitore + blocco cliente)
    for r in righe:
        if piva_cess and piva_cess in _norm(r):
            continue
        m = suff.search(r)
        if m and m.end() <= 60:
            end = m.end()
            nome = r[:end] + ("." if r[end:end + 1] == "." else "")  # reintegra il punto finale
            return _taglia_marker_cliente(nome)[:80]
    # 2) prima riga "plausibile" (non solo numeri/indirizzo)
    for r in righe:
        if piva_cess and piva_cess in _norm(r):
            continue
        if len(r) < 3 or re.fullmatch(r"[\d\W]+", r):
            continue
        if any(k in r.lower() for k in esclusi):
            continue
        return _taglia_marker_cliente(r)[:80]
    return ""


def _trova_data(testo: str):
    # solo nomi di mese ESTESI (le abbreviazioni a 3 lettere darebbero falsi match)
    mese_alt = "|".join(sorted({m for m in MESI if len(m) >= 4} | {"may"}, key=len, reverse=True))
    # 1) data con mese testuale (it/en), preferendo l'etichetta 'emissione'
    for pref in (r"emissione[^\n\d]{0,15}", r"issue[^\n\d]{0,15}", r""):
        m = re.search(rf"{pref}\b(\d{{1,2}})\s+({mese_alt})\.?\s+(\d{{4}})\b", testo, re.I)
        if m:
            try:
                return f"{int(m.group(3)):04d}-{MESI[m.group(2).lower()]:02d}-{int(m.group(1)):02d}"
            except Exception:
                pass
    # 2) date numeriche / ISO
    for pat in [r"emissione[:\s]*([0-3]?\d[\/\-\.][01]?\d[\/\-\.]\d{2,4})",
                r"date of issue[:\s]*([A-Za-z]+ \d{1,2},? \d{4})",
                r"invoice date[:\s]*([0-3]?\d[\/\-\.][01]?\d[\/\-\.]\d{2,4})",
                r"data[:\s]*([0-3]?\d[\/\-\.][01]?\d[\/\-\.]\d{2,4})",
                r"([0-3]?\d[\/\-\.][01]?\d[\/\-\.]\d{4})",
                r"(\d{4}-\d{2}-\d{2})"]:
        m = re.search(pat, testo, re.I)
        if m:
            try:
                return dateparser.parse(m.group(1), dayfirst=True).strftime("%Y-%m-%d")
            except Exception:
                pass
    return None


def _valuta(testo: str) -> str:
    for r in testo.splitlines():
        if any(et in r.lower() for et in ["importo dovuto", "amount due", "totale", "total"]):
            if "USD" in r or "$" in r:
                return "USD"
            if "GBP" in r or "£" in r:
                return "GBP"
            if "CHF" in r:
                return "CHF"
            if "EUR" in r or "€" in r:
                return "EUR"
    if "USD" in testo or "$" in testo:
        return "USD"
    if "GBP" in testo or "£" in testo:
        return "GBP"
    if "CHF" in testo:
        return "CHF"
    return "EUR"


def _trova_numero_data(testo: str):
    num, data = None, None
    DASH = r"\-‐-―−"
    # valore: token alfanumerico che DEVE contenere almeno una cifra (lookahead)
    VAL = rf"((?=[A-Za-z0-9{DASH}\/]*\d)[A-Za-z0-9{DASH}\/]{{3,}})"
    # etichette possibili per il numero fattura
    LAB = (r"numero fattura|invoice number|fattura numero|fattura n[.r]?|"
           r"invoice no\.?|invoice #|invoice|n[.\s]*fattura|nr\.? fattura|"
           r"documento n[.r]?|n[.\s]*documento")
    def _valido(c):
        c = re.sub(rf"[{DASH}]", "-", (c or "").strip().strip("."))
        if not re.search(r"\d", c):                                   # un numero fattura ha cifre
            return None
        if re.fullmatch(r"[0-3]?\d[\/\-.][01]?\d[\/\-.]\d{2,4}", c):   # non e' una data
            return None
        return c

    # 1) valore sullo stesso rigo, 2) valore sul rigo successivo (colonne separate)
    for pat in (rf"(?:{LAB})[\s:#]*{VAL}",
                rf"(?:{LAB})[\s:#]*[\r\n]+\s*{VAL}"):
        for m in re.finditer(pat, testo, re.I):
            c = _valido(m.group(1))
            if c:
                num = c
                break
        if num:
            break
    data = _trova_data(testo)
    return num, data


def _numero_da_nomefile(path: str):
    """Fallback: ricava il numero fattura dal nome del file (es. 'invoice_444961')."""
    name = os.path.splitext(os.path.basename(path or ""))[0]
    m = re.search(r"(?:invoice|fattura|inv|fatt|receipt|nr|no)[ _\-#.]*"
                  r"([A-Za-z0-9][A-Za-z0-9\-]*\d[A-Za-z0-9\-]*)", name, re.I)
    if m:
        return m.group(1).strip("_-")
    runs = re.findall(r"\d{4,}", name)          # altrimenti la sequenza di cifre piu' lunga
    if runs:
        return max(runs, key=len)
    return None


def _trova_descrizione(testo: str) -> str:
    for r in testo.splitlines():
        rl = r.lower()
        if any(k in rl for k in ["renewal", "subscription", "abbonamento", "servizio",
                                 "service", "claude", "workspace", "hosting", "licen",
                                 "plan", "piano", "canone", "fee"]):
            r = re.sub(r"\s{2,}", " ", r).strip()
            r = re.sub(r"(\s+\d+)?(\s*(?:€|\$|£)\s?[\d.,]+)+\s*$", "", r).strip()
            return r[:120]
    return ""


# --------------------------------------------------------------------------- #
# API principale
# --------------------------------------------------------------------------- #
def _cod_norm(s):
    """Normalizza un codice/P.IVA per il confronto: solo lettere/cifre minuscole."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def _fornitore_noto(testo: str, forn: dict):
    """Riconosce un fornitore salvato (importato o compilato) dal testo della fattura.
    Ritorna (chiave, anagrafica) oppure (None, None).

    Priorità:
      1) P.IVA / id_codice — molto affidabile: il numero compare in fattura, quindi
         riconosce anche i fornitori la cui 'chiave' è la denominazione completa
         (es. importati da Aruba) che raramente compare identica nel testo;
      2) 'chiave' — testo cercato nel PDF (per i fornitori senza P.IVA utile).
    """
    tl = (testo or "").lower()
    tnorm = _cod_norm(tl)
    # 1) per P.IVA / id_codice (esclude il placeholder condiviso OO99999999999)
    for chiave, ana in forn.items():
        cod = _cod_norm(ana.get("id_codice"))
        if len(cod) >= 6 and cod != "oo99999999999" and cod in tnorm:
            return chiave, ana
    # 2) per chiave testuale
    for chiave, ana in forn.items():
        if chiave and chiave in tl:
            return chiave, ana
    return None, None


def estrai_da_pdf(path: str, piva_cessionario: str = "") -> dict:
    testo = _estrai_testo(path)
    tl = testo.lower()
    note = []

    dati = {
        "file": path, "tipo_documento": None, "aliquota_iva": "22.00",
        "num_fattura_originaria": None, "data_fattura_originaria": None,
        "data": None, "imponibile": None, "descrizione": "", "fornitore": {},
    }

    # 1) fornitore noto? (prima per P.IVA presente in fattura, poi per chiave testuale)
    _chiave_noto, noto = _fornitore_noto(testo, carica_fornitori())

    if noto:
        dati["fornitore"] = {k: v for k, v in noto.items() if k != "tipo_documento"}
        dati["tipo_documento"] = noto.get("tipo_documento", "TD17")
    else:
        paese, codice = _trova_vat(testo, piva_cessionario)
        paese_txt = _trova_paese(testo)
        if not paese:
            paese = paese_txt
        denom = _trova_denominazione(testo, piva_cessionario)
        # extra-UE senza VAT -> codifica convenzionale
        if paese and paese not in UE and not (codice and len(codice) > 6):
            codice = "OO99999999999"
        if not codice:
            codice = "OO99999999999"
        dati["fornitore"] = {
            "denominazione": denom or "DA VERIFICARE",
            "id_paese": paese or "??",
            "id_codice": codice,
            "indirizzo": "DA VERIFICARE", "cap": "00000", "comune": "DA VERIFICARE",
            "nazione": paese or "??", "regime_fiscale": "RF18",
        }
        # TD stimato: UE beni? non deducibile senza contesto -> default TD17 (servizi)
        dati["tipo_documento"] = "TD17"
        if not denom:
            note.append("Fornitore non riconosciuto.")
        if not paese:
            note.append("Paese non rilevato.")
        note.append("Verifica anagrafica fornitore e codice TD.")

    # 2) importo + valuta
    imp, incerto = _trova_importo(testo)
    dati["imponibile"] = imp
    val = _valuta(testo)
    dati["valuta"] = val
    if imp is None:
        note.append("Imponibile non trovato: inseriscilo a mano.")
    elif incerto:
        note.append("Imponibile stimato (importo piu' grande): verificalo.")
    if val != "EUR":
        note.append(f"Importo in {val}: converti l'imponibile in EUR (cambio del giorno).")

    # 3) numero e data
    num, data = _trova_numero_data(testo)
    if not num:
        num = _numero_da_nomefile(path)
        if num:
            note.append("Numero ricavato dal nome del file — verifica.")
    dati["num_fattura_originaria"] = num
    dati["data_fattura_originaria"] = data
    dati["data"] = data
    if not num:
        note.append("Numero fattura non trovato.")
    if not data:
        note.append("Data non trovata.")

    # 4) descrizione
    dati["descrizione"] = _trova_descrizione(testo) or "Servizio"

    dati["note"] = note
    return dati


if __name__ == "__main__":
    import sys
    print(json.dumps(estrai_da_pdf(sys.argv[1]), indent=2, ensure_ascii=False))
