# -*- coding: utf-8 -*-
"""Test _trova_importo: l'imponibile deve essere SEMPRE il totale finale della fattura,
non il subtotale/netto (bug: 'total' faceva match dentro 'subtotal')."""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

import estrazione  # noqa: E402


def test_subtotale_sconto_totale():
    """Caso dell'utente: subtotale 120, sconto -20, Total 100 -> 100."""
    testo = "Subtotal        120,00\nDiscount        -20,00\nTotal           100,00"
    val, incerto = estrazione._trova_importo(testo)
    assert val == 100.00, (val, incerto)
    assert incerto is False


def test_subtotal_non_confonde_total():
    """'total' dentro 'subtotal' non deve piu' vincere: si prende il Total finale."""
    val, _ = estrazione._trova_importo("Subtotal 120,00\nTotal 100,00")
    assert val == 100.00


def test_priorita_total_due():
    """Total Due vince sul Grand Total (ordine di priorita')."""
    val, _ = estrazione._trova_importo("Grand Total 130,00\nTotal Due 100,00")
    assert val == 100.00


def test_esclude_iva_e_netto():
    """Righe VAT/netto non devono essere prese come totale."""
    testo = "Net amount 100,00\nVAT 22,00\nTotal amount 122,00"
    val, _ = estrazione._trova_importo(testo)
    assert val == 122.00


def test_ripiego_imponibile_italiano():
    """Se c'e' solo 'Imponibile' (nessun totale), lo si usa come ripiego."""
    val, incerto = estrazione._trova_importo("Imponibile 100,00")
    assert val == 100.00 and incerto is False


def test_nessun_importo():
    val, incerto = estrazione._trova_importo("Nessun numero qui.")
    assert val is None and incerto is True


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
