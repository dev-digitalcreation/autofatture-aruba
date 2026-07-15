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


def build_settings_dialog(page: ft.Page, cfg: dict, on_save=None,
                          prefill_fornitore=None, tab_index=None, fp=None):
    cfg = copy.deepcopy(cfg)
    forn = config_io.carica_fornitori()
    # FilePicker per import/export fornitori: riusa quello della UI o ne crea uno.
    _fp = fp
    if _fp is None:
        _fp = ft.FilePicker()
        page.services.append(_fp)
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
    TD_OPTS = ["TD16", "TD17", "TD18", "TD19"]
    COLS_F = config_io.FORNITORI_COLS          # chiave + anagrafica

    def _campi_forn():
        """Crea i controlli di una scheda fornitore. Ritorna (dict_controlli, layout)."""
        c = {
            "chiave": _campo("Chiave (testo nel PDF)", "", 330),
            "denominazione": _campo("Denominazione", "", 330),
            "id_paese": _campo("IdPaese", "", 120),
            "id_codice": _campo("IdCodice (P.IVA estera)", "", 200),
            "indirizzo": _campo("Indirizzo", "", 330),
            "numero_civico": _campo("N. civico", "", 120),
            "cap": _campo("CAP", "", 120),
            "comune": _campo("Comune", "", 200),
            "nazione": _campo("Nazione", "", 120),
            "tipo_documento": ft.Dropdown(label="Tipo doc", width=120, value="TD17",
                                          options=[ft.dropdown.Option(x) for x in TD_OPTS]),
        }
        layout = ft.Column([
            ft.Row([c["chiave"], c["tipo_documento"]], spacing=8, wrap=True),
            ft.Row([c["denominazione"]], spacing=8, wrap=True),
            ft.Row([c["id_paese"], c["id_codice"]], spacing=8, wrap=True),
            ft.Row([c["indirizzo"], c["numero_civico"]], spacing=8, wrap=True),
            ft.Row([c["cap"], c["comune"], c["nazione"]], spacing=8, wrap=True),
        ], spacing=8, tight=True)
        return c, layout

    def _leggi(c):
        """(chiave, anagrafica) dai controlli; l'anagrafica esclude i campi vuoti."""
        chiave = (c["chiave"].value or "").strip().lower()
        ana = {}
        for k in COLS_F[1:]:
            val = (c[k].value or "").strip()
            if val:
                ana[k] = val
        ana.setdefault("tipo_documento", "TD17")
        ana.setdefault("cap", "00000")
        return chiave, ana

    def _svuota(c):
        for k in COLS_F:
            c[k].value = ""
        c["tipo_documento"].value = "TD17"
        c["cap"].value = "00000"

    def _riempi(c, chiave, ana):
        c["chiave"].value = chiave
        for k in COLS_F[1:]:
            c[k].value = str(ana.get(k, "") or "")
        c["tipo_documento"].value = ana.get("tipo_documento") or "TD17"

    titolo_esist = _titolo(f"Fornitori esistenti ({len(forn_state)})")
    msg_ie = ft.Text("", size=12, color=ft.Colors.PRIMARY)
    msg_new = ft.Text("", size=12, color=ft.Colors.PRIMARY)
    msg_edit = ft.Text("", size=12, color=ft.Colors.PRIMARY)

    def _refresh_dd():
        dd.options = [ft.dropdown.Option(k) for k in sorted(forn_state)]
        titolo_esist.value = f"Fornitori esistenti ({len(forn_state)})"

    # === Sezione 1: NUOVO fornitore ===
    cn, layout_new = _campi_forn()

    def forn_crea(e=None):
        chiave, ana = _leggi(cn)
        if not chiave:
            msg_new.value = "Inserisci almeno la «Chiave» del nuovo fornitore."
            page.update(); return
        if chiave in forn_state:
            msg_new.value = f"Esiste già un fornitore «{chiave}»: modificalo nella sezione sotto."
            page.update(); return
        forn_state[chiave] = ana
        config_io.salva_fornitori(forn_state)
        _svuota(cn)
        _refresh_dd()
        msg_new.value = f"Fornitore «{chiave}» creato e salvato."
        page.update()

    # === Sezione 2: fornitori ESISTENTI ===
    ce, layout_edit = _campi_forn()
    dd = ft.Dropdown(label="Seleziona un fornitore", width=330,
                     options=[ft.dropdown.Option(k) for k in sorted(forn_state)])
    sel = {"chiave": None}                      # chiave originale selezionata

    def load_forn(e=None):
        k = dd.value
        sel["chiave"] = k
        if k and k in forn_state:
            _riempi(ce, k, forn_state[k])
        msg_edit.value = ""
        page.update()

    dd.on_change = load_forn

    def forn_salva_mod(e=None):
        orig = sel["chiave"]
        if not orig:
            msg_edit.value = "Seleziona prima un fornitore dall'elenco."
            page.update(); return
        nuova, ana = _leggi(ce)
        if not nuova:
            msg_edit.value = "La «Chiave» non può essere vuota."
            page.update(); return
        if nuova != orig:
            forn_state.pop(orig, None)          # chiave rinominata
        forn_state[nuova] = ana
        sel["chiave"] = nuova
        config_io.salva_fornitori(forn_state)
        _refresh_dd()
        dd.value = nuova
        msg_edit.value = f"Modifiche a «{nuova}» salvate." + (" (chiave rinominata)" if nuova != orig else "")
        page.update()

    def forn_elimina(e=None):
        orig = sel["chiave"]
        if not orig or orig not in forn_state:
            msg_edit.value = "Seleziona prima un fornitore dall'elenco."
            page.update(); return
        del forn_state[orig]
        sel["chiave"] = None
        dd.value = None
        _svuota(ce)
        config_io.salva_fornitori(forn_state)
        _refresh_dd()
        msg_edit.value = f"Fornitore «{orig}» eliminato."
        page.update()

    # === Import / Export (.csv / .xlsx) ===
    async def forn_esporta(e=None):
        fmt = e.control.data                    # 'csv' | 'xlsx'
        try:
            dest = await _fp.save_file(dialog_title=f"Esporta fornitori ({fmt.upper()})",
                                       file_name=f"fornitori.{fmt}",
                                       file_type=ft.FilePickerFileType.CUSTOM, allowed_extensions=[fmt])
        except Exception as ex:
            msg_ie.value = f"Esportazione non disponibile: {ex}"; page.update(); return
        if not dest:
            return
        if not dest.lower().endswith("." + fmt):
            dest += "." + fmt
        try:
            config_io.esporta_fornitori(forn_state, dest)
            msg_ie.value = f"{len(forn_state)} fornitori esportati in: {dest}"
        except Exception as ex:
            msg_ie.value = f"Errore esportazione: {ex}"
        page.update()

    async def forn_importa(e=None):
        try:
            res = await _fp.pick_files(dialog_title="Importa fornitori (CSV o Excel)",
                                       allowed_extensions=["csv", "xlsx", "xlsm"])
        except Exception as ex:
            msg_ie.value = f"Selezione non disponibile: {ex}"; page.update(); return
        if not res:
            return
        try:
            nuovi = config_io.importa_fornitori(res[0].path)
        except Exception as ex:
            msg_ie.value = f"File non valido: {ex}"; page.update(); return
        if not nuovi:
            msg_ie.value = "Nessun fornitore trovato nel file."; page.update(); return
        agg = sum(1 for k in nuovi if k in forn_state)
        forn_state.update(nuovi)
        config_io.salva_fornitori(forn_state)
        _refresh_dd()
        msg_ie.value = f"Importati {len(nuovi)} fornitori: {len(nuovi) - agg} nuovi, {agg} aggiornati (salvati)."
        page.update()

    # Precompilazione da "Salva come fornitore noto": va nella sezione «Nuovo»
    if prefill_fornitore:
        _riempi(cn, "", prefill_fornitore)
        cn["chiave"].value = str(prefill_fornitore.get("denominazione", "") or "").strip().lower()
        cn["tipo_documento"].value = prefill_fornitore.get("tipo_documento") or "TD17"
        cn["cap"].value = str(prefill_fornitore.get("cap", "") or "") or "00000"

    view_forn = _scheda([
        _titolo("Import / Export"),
        ft.Text("Salva o carica l'elenco fornitori come CSV o Excel (.xlsx). "
                "L'import aggiorna i fornitori con la stessa chiave e aggiunge i nuovi.",
                size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        ft.Row([ft.OutlinedButton("Importa da file", icon=ft.Icons.UPLOAD_FILE, on_click=forn_importa),
                ft.OutlinedButton("Esporta CSV", icon=ft.Icons.DOWNLOAD, data="csv", on_click=forn_esporta),
                ft.OutlinedButton("Esporta Excel", icon=ft.Icons.GRID_ON, data="xlsx", on_click=forn_esporta)],
               spacing=8, wrap=True),
        msg_ie,
        ft.Divider(),
        _titolo("➕  Nuovo fornitore"),
        ft.Text("La «Chiave» è il testo cercato nel PDF per riconoscere il fornitore (es. il nome).",
                size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        layout_new,
        ft.Row([ft.FilledButton("Crea fornitore", icon=ft.Icons.ADD, on_click=forn_crea)]),
        msg_new,
        ft.Divider(),
        titolo_esist,
        ft.Text("Seleziona un fornitore per vederne i dati, modificarli e salvarli.",
                size=12, color=ft.Colors.ON_SURFACE_VARIANT),
        dd,
        layout_edit,
        ft.Row([ft.FilledButton("Salva modifiche", icon=ft.Icons.SAVE, on_click=forn_salva_mod),
                ft.OutlinedButton("Elimina", icon=ft.Icons.DELETE, on_click=forn_elimina)], spacing=8),
        msg_edit,
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
    stato_upd = ft.Text("", size=13)
    _info = {}

    def scarica(e=None):
        stato_upd.value = "Scaricamento in corso…"
        page.update()
        try:
            p = aggiornamenti.scarica_installer(_info.get("info", {}))
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
            info = aggiornamenti.controlla(version.GITHUB_OWNER, version.GITHUB_REPO)
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
        ft.Row([ft.FilledTonalButton("Controlla aggiornamenti", icon=ft.Icons.SYSTEM_UPDATE,
                                     on_click=controlla_upd), dl_btn], spacing=8),
        stato_upd,
    ])

    # ---------------- Tabs ----------------
    _sel = tab_index if tab_index is not None else int(os.environ.get('AUTO_TAB', '0') or 0)
    tabs = ft.Tabs(
        length=5, expand=True, selected_index=_sel,
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
        cfg["github_token"] = ""      # repo pubblico: nessun token
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
