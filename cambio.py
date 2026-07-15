# -*- coding: utf-8 -*-
"""
Conversione valuta -> EUR usando i cambi ufficiali della Banca d'Italia.

API: https://tassidicambio.bancaditalia.it/terzevalute-wf-web/rest/v1.0/dailyRates
avgRate = quantita' di valuta estera per 1 EUR  =>  EUR = importo_valuta / avgRate.
Se la data non e' quotata (weekend/festivi) si ripiega sui giorni precedenti.
"""
import json
import urllib.parse
import urllib.request
from datetime import date, timedelta

BASE = "https://tassidicambio.bancaditalia.it/terzevalute-wf-web/rest/v1.0/dailyRates"


def _query(data_iso: str, valuta: str) -> dict:
    q = urllib.parse.urlencode({
        "referenceDate": data_iso,
        "currencyIsoCode": "EUR",
        "baseCurrencyIsoCode": valuta,
        "lang": "en",
    })
    req = urllib.request.Request(
        f"{BASE}?{q}",
        headers={"Accept": "application/json", "User-Agent": "AutofattureAruba/1.0"},
    )
    with urllib.request.urlopen(req, timeout=8) as r:
        return json.loads(r.read().decode("utf-8"))


def tasso_eur(valuta: str, data_iso: str, giorni_indietro: int = 7):
    """Ritorna (avgRate, data_usata) o (None, None)."""
    valuta = (valuta or "").upper()
    if valuta in ("", "EUR"):
        return None, None
    try:
        d0 = date.fromisoformat(data_iso)
    except Exception:
        return None, None
    for i in range(giorni_indietro + 1):
        giorno = (d0 - timedelta(days=i)).isoformat()
        try:
            js = _query(giorno, valuta)
            rates = js.get("rates") or []
            if rates:
                avg = rates[0].get("avgRate")
                if avg not in (None, "", "N.A.", "NA"):
                    return float(avg), giorno
        except Exception:
            continue
    return None, None


def converti_in_eur(importo, valuta: str, data_iso: str):
    """Ritorna dict con eur, tasso, data_cambio, valuta — oppure None se non disponibile."""
    tasso, giorno = tasso_eur(valuta, data_iso)
    if not tasso:
        return None
    try:
        eur = round(float(importo) / tasso, 2)
    except Exception:
        return None
    return {"eur": eur, "tasso": tasso, "data_cambio": giorno, "valuta": (valuta or "").upper()}


if __name__ == "__main__":
    import sys
    print(converti_in_eur(float(sys.argv[1]), sys.argv[2], sys.argv[3]))
