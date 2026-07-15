# -*- coding: utf-8 -*-
"""
Motore di generazione autofatture/integrazioni reverse charge (TD16-19).
Modulo importabile: costruisce l'XML SDI (FatturaPA FPR12) a partire da un dict
con i dati della fattura e da una configurazione aziendale.

Riproduce lo stile dello studio (validato: XML identico all'autofattura reale).
"""
from decimal import Decimal, ROUND_HALF_UP

from a38 import fattura as a38f
from a38.validation import Validation
import lxml.etree as ET


TIPI_VALIDI = {
    "TD16": "Integrazione reverse charge interno",
    "TD17": "Autofattura servizi dall'estero",
    "TD18": "Integrazione acquisto beni intra-UE",
    "TD19": "Autofattura acquisto beni ex art.17 c.2",
}


def d2(x) -> Decimal:
    return Decimal(str(x)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def costruisci_fattura(inv: dict, cfg: dict, prog_num: int) -> a38f.FatturaPrivati12:
    tipo = str(inv["tipo_documento"]).upper()
    if tipo not in TIPI_VALIDI:
        raise ValueError(f"tipo_documento non valido: {tipo}")

    az = cfg["azienda"]
    tr = cfg["trasmittente"]
    forn = inv["fornitore"]

    dati_trasmissione = a38f.DatiTrasmissione(
        id_trasmittente=a38f.IdTrasmittente(id_paese=tr["id_paese"], id_codice=tr["id_codice"]),
        progressivo_invio=str(prog_num),
        codice_destinatario=cfg.get("codice_destinatario", "0000000"),
    )
    if cfg.get("codice_destinatario", "0000000") == "0000000" and cfg.get("pec_destinatario"):
        dati_trasmissione.pec_destinatario = cfg["pec_destinatario"]

    cedente = a38f.CedentePrestatore(
        dati_anagrafici=a38f.DatiAnagraficiCedentePrestatore(
            id_fiscale_iva=a38f.IdFiscaleIVA(id_paese=forn["id_paese"], id_codice=forn["id_codice"]),
            anagrafica=a38f.Anagrafica(denominazione=forn["denominazione"]),
            regime_fiscale=forn.get("regime_fiscale", cfg.get("regime_fiscale_cedente", "RF18")),
        ),
        sede=a38f.Sede(
            indirizzo=forn.get("indirizzo") or "-",
            numero_civico=forn.get("numero_civico"),
            cap=forn.get("cap", "00000"),
            comune=forn.get("comune") or "-",
            provincia=forn.get("provincia"),
            nazione=forn["nazione"],
        ),
    )

    cessionario = a38f.CessionarioCommittente(
        dati_anagrafici=a38f.DatiAnagraficiCessionarioCommittente(
            id_fiscale_iva=a38f.IdFiscaleIVA(id_paese=az["id_paese"], id_codice=az["piva"]),
            codice_fiscale=az.get("codice_fiscale"),
            anagrafica=a38f.Anagrafica(denominazione=az["denominazione"]),
        ),
        sede=a38f.Sede(
            indirizzo=az["indirizzo"],
            numero_civico=az.get("numero_civico"),
            cap=az["cap"],
            comune=az["comune"],
            provincia=az.get("provincia"),
            nazione=az["nazione"],
        ),
    )

    header = a38f.FatturaElettronicaHeader(
        dati_trasmissione=dati_trasmissione,
        cedente_prestatore=cedente,
        cessionario_committente=cessionario,
        soggetto_emittente=cfg.get("soggetto_emittente", "CC"),
    )

    imponibile = d2(inv["imponibile"])
    aliquota = Decimal(str(inv.get("aliquota_iva", "22.00")))
    natura = inv.get("natura")
    imposta = d2(0) if natura else d2(imponibile * aliquota / Decimal("100"))
    totale = d2(imponibile + imposta)

    dgd = a38f.DatiGeneraliDocumento(
        tipo_documento=tipo,
        divisa=inv.get("divisa", "EUR"),
        data=inv["data"],
        numero=inv["numero"],
    )
    if cfg.get("importo_totale_documento", True):
        dgd.importo_totale_documento = totale
    if inv.get("causale"):
        dgd.causale = [inv["causale"]]

    dati_generali = a38f.DatiGenerali(dati_generali_documento=dgd)
    if inv.get("num_fattura_originaria"):
        dati_generali.dati_fatture_collegate = [
            a38f.DatiDocumentiCorrelati(
                riferimento_numero_linea=[1],
                id_documento=str(inv["num_fattura_originaria"])[:20],
                data=inv.get("data_fattura_originaria"),
            )
        ]

    righe = inv.get("righe") or [{"descrizione": inv.get("descrizione", "Integrazione reverse charge"),
                                  "prezzo": imponibile, "quantita": 1}]
    linee = []
    for i, riga in enumerate(righe, start=1):
        prezzo = d2(riga["prezzo"])
        linee.append(
            a38f.DettaglioLinee(
                numero_linea=i,
                descrizione=str(riga["descrizione"])[:1000],
                quantita=riga.get("quantita"),
                unita_misura=riga.get("unita_misura"),
                prezzo_unitario=prezzo,
                prezzo_totale=prezzo,
                aliquota_iva=aliquota,
                natura=natura,
            )
        )

    riepilogo = a38f.DatiRiepilogo(
        aliquota_iva=aliquota,
        natura=natura,
        imponibile_importo=imponibile,
        imposta=imposta,
        esigibilita_iva=inv.get("esigibilita_iva") or cfg.get("esigibilita_iva"),
    )

    body = a38f.FatturaElettronicaBody(
        dati_generali=dati_generali,
        dati_beni_servizi=a38f.DatiBeniServizi(dettaglio_linee=linee, dati_riepilogo=[riepilogo]),
    )

    pg = cfg.get("pagamento")
    if pg:
        body.dati_pagamento = [
            a38f.DatiPagamento(
                condizioni_pagamento=pg.get("condizioni", "TP02"),
                dettaglio_pagamento=[
                    a38f.DettaglioPagamento(
                        modalita_pagamento=pg.get("modalita", "MP05"),
                        data_scadenza_pagamento=inv["data"],
                        importo_pagamento=totale,
                        istituto_finanziario=pg.get("istituto"),
                        iban=pg.get("iban"),
                    )
                ],
            )
        ]

    return a38f.FatturaPrivati12(
        fattura_elettronica_header=header,
        fattura_elettronica_body=[body],
    )


def numero_documento(cfg: dict, inv: dict, prog_num: int) -> str:
    if inv.get("numero"):
        return inv["numero"]
    num = cfg.get("numerazione", {})
    pattern = num.get("pattern", "{n}")
    yy = str(inv["data"])[2:4]
    return pattern.format(n=prog_num, yy=yy)


def nome_file(cfg: dict, prog_num: int) -> str:
    prefix = cfg.get("filename_prefix")
    if not prefix:
        prefix = f"{cfg['trasmittente']['id_paese']}{cfg['trasmittente']['id_codice']}"
    return f"{prefix}_{prog_num:05d}.xml"


def calcola_importi(inv: dict):
    imponibile = d2(inv["imponibile"])
    aliquota = Decimal(str(inv.get("aliquota_iva", "22.00")))
    imposta = d2(0) if inv.get("natura") else d2(imponibile * aliquota / Decimal("100"))
    return imponibile, aliquota, imposta, d2(imponibile + imposta)


def genera_xml_bytes(inv: dict, cfg: dict, prog_num: int):
    """Ritorna (nome_file, xml_bytes, lista_warning)."""
    inv = dict(inv)
    inv["numero"] = numero_documento(cfg, inv, prog_num)
    f = costruisci_fattura(inv, cfg, prog_num)
    val = Validation()
    f.validate(val)
    warn = [str(e) for e in val.errors if "unita_misura" not in str(e)]
    tree = f.build_etree(lxml=True)
    xml_bytes = ET.tostring(tree, xml_declaration=True, encoding="UTF-8", pretty_print=True)
    return nome_file(cfg, prog_num), xml_bytes, warn
