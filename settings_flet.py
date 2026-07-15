# -*- coding: utf-8 -*-
"""Dialogo Impostazioni per l'interfaccia Flet — a schede (Azienda, Pagamento, Fornitori, Numerazione)."""
import os
import copy
import flet as ft

import config_io
import version
import aggiornamenti


def _campo(label, value, width=280):
    tf = ft.TextField(value="" if value is None else str(value), width=width, height=46,
                      dense=True, text_size=13, label=label)
    return tf


def _scheda(controls):
    return ft.Column(controls, scroll=ft.ScrollMode.AUTO, expand=True, spacing=8)


def _titolo(t):
    return ft.Text(t, weight=ft.FontWeight.BOLD, size=14)


def build_settings_dialog(page: ft.Page, cfg: dict, on_save=None):
    cfg = copy.deepcopy(cfg)
    forn = config_io.carica_fornitori()
    az = cfg.setdefault("azienda", {})
    tr = cfg.setdefault("trasmittente", {})
    num = cfg.setdefault("numerazione", {})
    pg = cfg.get("pagamento") or {}
    v = {}

    # ---------------- scheda AZIENDA ----------------
    az_campi = [("denominazione", "Denominazione"), ("piva", "P.IVA"),
                ("codice_fiscale", "Codice fiscale"), ("indirizzo", "Indirizzo"),
                ("numero_civico", "Numero civico"), ("cap", "CAP"), ("comune", "Comune"),
                ("provincia", "Provincia"), ("nazione", "Nazione")]
    az_rows = [_titolo("Dati azienda (cessionario)")]
    for k, lab in az_campi:
        v[f"az_{k}"] = _campo(lab, az.get(k)); az_rows.append(v[f"az_{k}"])
    az_rows.append(_titolo("Trasmittente / recapito SdI"))
    v["tr_paese"] = _campo("Trasmittente IdPaese", tr.get("id_paese", "IT"))
    v["tr_cod"] = _campo("Trasmittente IdCodice", tr.get("id_codice", ""))
    v["dest"] = _campo("Codice destinatario", cfg.get("codice_destinatario", "0000000"))

    def _applica_preset(e=None):
        p = config_io.ROUTING_PRESETS.get(v["preset"].value)
        if not p:
            return
        v["tr_paese"].value = p.get("trasmittente_id_paese", "IT")
        v["tr_cod"].value = p.get("trasmittente_id_codice", "")
        v["dest"].value = p.get("codice_destinatario", "0000000")
        page.update()

    v["preset"] = ft.Dropdown(label="Intermediario / preset routing", width=280,
                              options=[ft.dropdown.Option(k) for k in config_io.ROUTING_PRESETS])
    v["preset"].on_change = _applica_preset
    az_rows.append(ft.Text("Scegli un preset per compilare trasmittente e destinatario "
                           "(es. Aruba), oppure inseriscili a mano.", size=12,
                           color=ft.Colors.ON_SURFACE_VARIANT))
    az_rows.append(v["preset"])
    az_rows.append(v["tr_paese"]); az_rows.append(v["tr_cod"]); az_rows.append(v["dest"])
    v["pec"] = _campo("PEC destinatario", cfg.get("pec_destinatario")); az_rows.append(v["pec"])
    v["soggetto"] = _campo("SoggettoEmittente", cfg.get("soggetto_emittente", "CC")); az_rows.append(v["soggetto"])
    view_az = _scheda(az_rows)

    # ---------------- scheda PAGAMENTO ----------------
    v["pag_on"] = ft.Switch(label="Includi blocco DatiPagamento (IBAN)", value=bool(cfg.get("pagamento")))
    v["istituto"] = _campo("Istituto finanziario", pg.get("istituto", ""))
    v["iban"] = _campo("IBAN", pg.get("iban", ""))
    v["cond"] = _campo("Condizioni pagamento", pg.get("condizioni", "TP02"), 160)
    v["mod"] = _campo("Modalità pagamento", pg.get("modalita", "MP05"), 160)
    v["aliq"] = _campo("Aliquota IVA default (%)", cfg.get("aliquota_default", "22.00"), 160)
    v["regime"] = _campo("Regime fiscale cedente", cfg.get("regime_fiscale_cedente", "RF18"), 160)
    v["totale"] = ft.Switch(label="Includi ImportoTotaleDocumento",
                            value=bool(cfg.get("importo_totale_documento", True)))
    view_pag = _scheda([_titolo("Pagamento"), v["pag_on"], v["istituto"], v["iban"], v["cond"], v["mod"],
                        _titolo("IVA"), v["aliq"], v["regime"], v["totale"]])

    # ---------------- scheda FORNITORI ----------------
    forn_state = dict(forn)
    campi_f = [("chiave", "Chiave (testo nel PDF)"), ("denominazione", "Denominazione"),
               ("id_paese", "IdPaese"), ("id_codice", "IdCodice"), ("indirizzo", "Indirizzo"),
               ("numero_civico", "N. civico"), ("cap", "CAP"), ("comune", "Comune"),
               ("nazione", "Nazione"), ("tipo_documento", "Tipo doc")]
    vf = {}
    dd = ft.Dropdown(label="Fornitore esistente", width=300,
                     options=[ft.dropdown.Option(k) for k in sorted(forn_state)])
    for k, lab in campi_f:
        vf[k] = _campo(lab, "", 300)

    def load_forn(e=None):
        d = forn_state.get(dd.value, {})
        vf["chiave"].value = dd.value or ""
        for k, _l in campi_f:
            if k != "chiave":
                vf[k].value = str(d.get(k, "") or "")
        page.update()

    def forn_nuovo(e=None):
        for k, _l in campi_f:
            vf[k].value = ""
        vf["tipo_documento"].value = "TD17"
        vf["cap"].value = "00000"
        dd.value = None
        page.update()

    def forn_applica(e=None):
        key = (vf["chiave"].value or "").strip().lower()
        if not key:
            return
        forn_state[key] = {k: (vf[k].value or "").strip() for k, _l in campi_f
                           if k != "chiave" and (vf[k].value or "").strip()}
        dd.options = [ft.dropdown.Option(k) for k in sorted(forn_state)]
        dd.value = key
        page.update()

    def forn_elimina(e=None):
        key = (vf["chiave"].value or "").strip().lower()
        if key in forn_state:
            del forn_state[key]
            dd.options = [ft.dropdown.Option(k) for k in sorted(forn_state)]
            forn_nuovo()

    dd.on_change = load_forn
    view_forn = _scheda([
        _titolo("Fornitori riconosciuti automaticamente"),
        ft.Text("Seleziona un fornitore per modificarlo, o premi «Nuovo» per crearne uno.",
                size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        dd,
        *[vf[k] for k, _l in campi_f],
        ft.Row([ft.FilledTonalButton("Nuovo", icon=ft.Icons.ADD, on_click=forn_nuovo),
                ft.FilledButton("Salva fornitore", icon=ft.Icons.CHECK, on_click=forn_applica),
                ft.OutlinedButton("Elimina", icon=ft.Icons.DELETE, on_click=forn_elimina)], spacing=8),
    ])

    # ---------------- scheda NUMERAZIONE ----------------
    v["pattern"] = _campo("Pattern numero", num.get("pattern", "{n}/{yy}"))
    v["start"] = _campo("Numero di partenza", cfg.get("progressivo_start", 1), 160)
    v["prefix"] = _campo("Prefisso nome file", cfg.get("filename_prefix", ""))
    v["ricorda"] = ft.Switch(label="Ricorda l'ultimo numero usato (avanza da solo)",
                             value=bool(cfg.get("ricorda_ultimo_numero", True)))
    view_num = _scheda([_titolo("Numerazione sezionale"), v["pattern"],
                        ft.Text("Segnaposto: {n}=numero, {yy}=anno 2 cifre", size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT),
                        v["start"], v["prefix"], v["ricorda"]])

    # ---------------- scheda INFO / AGGIORNAMENTI ----------------
    v["token"] = _campo("Token GitHub (non necessario con repo pubblico)", cfg.get("github_token", ""))
    stato_upd = ft.Text("", size=13)
    _info = {}

    def scarica(e=None):
        stato_upd.value = "Scaricamento in corso…"
        page.update()
        try:
            p = aggiornamenti.scarica_installer(_info.get("info", {}), (v["token"].value or "").strip())
            aggiornamenti.avvia_installer(p)
            stato_upd.value = "Installer avviato. Chiudi l'app per completare l'aggiornamento."
        except Exception as ex:
            stato_upd.value = f"Errore nel download: {ex}"
        page.update()

    dl_btn = ft.FilledButton("Scarica e installa", icon=ft.Icons.DOWNLOAD, visible=False, on_click=scarica)

    def controlla_upd(e=None):
        stato_upd.value = "Controllo in corso…"
        dl_btn.visible = False
        page.update()
        try:
            info = aggiornamenti.controlla(version.GITHUB_OWNER, version.GITHUB_REPO,
                                           (v["token"].value or "").strip())
        except Exception as ex:
            stato_upd.value = f"Impossibile controllare: {ex}"
            page.update()
            return
        _info["info"] = info
        if info.get("nuova"):
            stato_upd.value = f"Nuova versione disponibile: {info['tag']} (attuale v{version.__version__})."
            dl_btn.visible = bool(info.get("asset_download") or info.get("asset_api"))
        else:
            stato_upd.value = f"Sei aggiornato (versione attuale v{version.__version__})."
        page.update()

    repo_txt = (f"{version.GITHUB_OWNER}/{version.GITHUB_REPO}"
                if version.GITHUB_OWNER and version.GITHUB_REPO
                else "(repository non ancora configurato in version.py)")
    view_info = _scheda([
        _titolo("Applicazione"),
        ft.Text(f"Versione installata: v{version.__version__}", size=13),
        ft.Text(f"Repository aggiornamenti: {repo_txt}", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        v["token"],
        ft.Row([ft.FilledTonalButton("Controlla aggiornamenti", icon=ft.Icons.SYSTEM_UPDATE,
                                     on_click=controlla_upd), dl_btn], spacing=8),
        stato_upd,
    ])

    # ---------------- Tabs ----------------
    tabs = ft.Tabs(
        length=5, expand=True, selected_index=int(os.environ.get('AUTO_TAB', '0') or 0),
        content=ft.Column(expand=True, controls=[
            ft.TabBar(tabs=[ft.Tab(label="Azienda", icon=ft.Icons.BUSINESS),
                            ft.Tab(label="Pagamento", icon=ft.Icons.PAYMENTS),
                            ft.Tab(label="Fornitori", icon=ft.Icons.STORE),
                            ft.Tab(label="Numerazione", icon=ft.Icons.NUMBERS),
                            ft.Tab(label="Info", icon=ft.Icons.INFO)]),
            ft.TabBarView(expand=True, controls=[view_az, view_pag, view_forn, view_num, view_info]),
        ]),
    )

    def salva(e=None):
        for k, _l in [("denominazione", 0), ("piva", 0), ("codice_fiscale", 0), ("indirizzo", 0),
                      ("numero_civico", 0), ("cap", 0), ("comune", 0), ("provincia", 0), ("nazione", 0)]:
            az[k] = (v[f"az_{k}"].value or "").strip()
        tr["id_paese"] = (v["tr_paese"].value or "IT").strip()
        tr["id_codice"] = (v["tr_cod"].value or "").strip()
        cfg["codice_destinatario"] = (v["dest"].value or "0000000").strip()
        cfg["pec_destinatario"] = (v["pec"].value or "").strip() or None
        cfg["soggetto_emittente"] = (v["soggetto"].value or "CC").strip()
        num["pattern"] = (v["pattern"].value or "{n}").strip()
        try:
            cfg["progressivo_start"] = int((v["start"].value or "1").strip())
        except ValueError:
            pass
        cfg["filename_prefix"] = (v["prefix"].value or "").strip() or None
        cfg["ricorda_ultimo_numero"] = bool(v["ricorda"].value)
        if v["pag_on"].value:
            cfg["pagamento"] = {"condizioni": (v["cond"].value or "TP02").strip(),
                                "modalita": (v["mod"].value or "MP05").strip(),
                                "istituto": (v["istituto"].value or "").strip(),
                                "iban": (v["iban"].value or "").strip()}
        else:
            cfg["pagamento"] = None
        cfg["aliquota_default"] = (v["aliq"].value or "22.00").strip()
        cfg["regime_fiscale_cedente"] = (v["regime"].value or "RF18").strip()
        cfg["importo_totale_documento"] = bool(v["totale"].value)
        cfg["github_token"] = (v["token"].value or "").strip()
        config_io.salva_config(cfg)
        config_io.salva_fornitori(forn_state)
        page.pop_dialog()
        if on_save:
            on_save(cfg)

    dlg = ft.AlertDialog(
        title=ft.Text("Impostazioni"),
        content=ft.Container(width=760, height=500, content=tabs),
        actions=[ft.TextButton("Annulla", on_click=lambda e: page.pop_dialog()),
                 ft.FilledButton("Salva tutto", icon=ft.Icons.SAVE, on_click=salva)],
    )
    page.show_dialog(dlg)
