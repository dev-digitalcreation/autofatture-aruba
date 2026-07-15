# -*- coding: utf-8 -*-
"""
Reversa — autofatture reverse charge -> Aruba  ·  interfaccia moderna (Flet)

- Aggiungi i PDF con il pulsante (o cliccando la zona in alto).
- Colonne che si adattano al testo, con scorrimento orizzontale/verticale.
- Impostazioni a schede (Azienda, Pagamento, Fornitori, Numerazione).
- Conversione valuta -> EUR con cambio Banca d'Italia.
- "Genera XML" -> file pronti per il caricamento massivo su Aruba.
Riusa il motore (motore.py, estrazione.py, cambio.py, config_io.py) senza modificarlo.
"""
import os
import sys
import csv
import re

import flet as ft

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)
import estrazione
import motore
import config_io
import cambio
import version
import archivio
import validazione
import anteprima

OUTPUT_DEF = config_io.OUTPUT_DIR
ACCENT = ft.Colors.GREEN
WARN = ft.Colors.AMBER

# (chiave, etichetta, larghezza minima px)
COLS = [
    ("file", "PDF", 110),
    ("denominazione", "Fornitore", 150),
    ("id_paese", "Paese", 60),
    ("id_codice", "P.IVA/ID", 110),
    ("tipo_documento", "TD", 92),
    ("imponibile", "Imponibile", 92),
    ("aliquota_iva", "Aliq%", 62),
    ("num_fattura_originaria", "N. fatt.", 100),
    ("data_fattura_originaria", "Data fatt.", 100),
    ("data", "Data reg.", 100),
    ("descrizione", "Descrizione", 150),
]
CHAR_PX = 8.2
PAD_PX = 30
MAX_W = 440


class UI:
    def __init__(self, page: ft.Page):
        self.page = page
        self.cfg = config_io.carica_config()
        self.data = []          # righe: dict con valori stringa + _extra/_note/_ctrl
        self.output_dir = OUTPUT_DEF
        self.col_w = {}         # larghezze correnti delle colonne
        self.manual = set()     # colonne ridimensionate a mano (non piu' auto)
        self.head_cells = {}    # riferimenti alle celle di intestazione

        page.title = "Reversa"
        page.theme_mode = ft.ThemeMode.SYSTEM
        page.theme = ft.Theme(
            color_scheme_seed=ft.Colors.GREEN,
            # scrollbar sempre visibile quando c'e' da scorrere: niente animazione di
            # fade che rimane appesa (la barra orizzontale spariva troppo lentamente).
            scrollbar_theme=ft.ScrollbarTheme(thumb_visibility=True, thickness=8,
                                              radius=6, interactive=True))
        page.window.width = 1200
        page.window.height = 760
        page.window.min_width = 1000      # sotto questa soglia il layout resta usabile
        page.window.min_height = 620
        page.padding = 0
        page.on_resize = self._adatta     # colonne + anteprima si adattano alla finestra

        self.preview_container = None
        self._preview_on = True
        self.fp = ft.FilePicker()
        page.services.append(self.fp)
        self._build()

    # ------------------------------------------------------------------ build
    def _build(self):
        self.info = ft.Text(self._info_text(), size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.status = ft.Text("Pronto. Aggiungi i PDF delle fatture passive.",
                              size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.start_field = ft.TextField(value=str(self._numero_suggerito()),
                                        width=90, height=46, text_size=13, dense=True, label="Primo n.")
        self.data_field = ft.TextField(value="", width=150, height=46, text_size=13, dense=True,
                                       label="Data autofattura", hint_text="AAAA-MM-GG")

        header = ft.Container(
            content=ft.Row([
                ft.Row([ft.Icon(ft.Icons.RECEIPT_LONG, color=ACCENT),
                        ft.Text("Reversa", size=19, weight=ft.FontWeight.BOLD),
                        ft.Text("autofatture reverse charge → Aruba", size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Container(ft.Text(f"v{version.__version__}", size=11,
                                             color=ft.Colors.ON_SURFACE_VARIANT),
                                     bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                     padding=ft.Padding(left=8, top=2, right=8, bottom=2),
                                     border_radius=10)], spacing=8,
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Row([
                    ft.PopupMenuButton(icon=ft.Icons.BRIGHTNESS_6, items=[
                        ft.PopupMenuItem(content="Sistema", on_click=lambda e: self._tema("system")),
                        ft.PopupMenuItem(content="Chiaro", on_click=lambda e: self._tema("light")),
                        ft.PopupMenuItem(content="Scuro", on_click=lambda e: self._tema("dark")),
                    ]),
                    ft.IconButton(ft.Icons.VIEW_SIDEBAR, tooltip="Mostra/nascondi anteprima PDF",
                                  on_click=self.toggle_anteprima),
                    ft.OutlinedButton("Impostazioni", icon=ft.Icons.SETTINGS, on_click=self.apri_impostazioni),
                    ft.FilledTonalButton("Aggiungi PDF", icon=ft.Icons.UPLOAD_FILE, on_click=self.aggiungi_pdf),
                    ft.OutlinedButton("Valida", icon=ft.Icons.FACT_CHECK, on_click=self.valida_righe),
                    ft.FilledButton("Genera XML", icon=ft.Icons.BOLT, on_click=self.genera),
                ], spacing=8),
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding(left=16, top=12, right=16, bottom=8),
        )

        self.drop = ft.Container(
            content=ft.Row([ft.Icon(ft.Icons.UPLOAD_FILE, color=ACCENT),
                            ft.Text("Clicca qui (o «Aggiungi PDF») per selezionare le fatture passive",
                                    size=14)],
                           alignment=ft.MainAxisAlignment.CENTER, spacing=10),
            height=60, border_radius=12, bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            margin=ft.Margin(left=16, top=0, right=16, bottom=10),
            alignment=ft.Alignment.CENTER, on_click=self.aggiungi_pdf, ink=True,
        )

        # tabella: doppio scorrimento. La Row (scroll orizzontale) contiene la Column
        # delle righe alla sua larghezza NATURALE, così le colonne scorrono invece di
        # essere tagliate; la Column esterna (scroll verticale) gestisce l'altezza.
        self.table_inner = ft.Column([], spacing=4)
        h_scroll = ft.Row([self.table_inner], scroll=ft.ScrollMode.AUTO,
                          vertical_alignment=ft.CrossAxisAlignment.START)
        table = ft.Container(
            ft.Column([h_scroll], scroll=ft.ScrollMode.AUTO, expand=True),
            expand=True, padding=ft.Padding(left=16, top=0, right=8, bottom=8))

        # pannello anteprima PDF (a destra)
        self.preview_titolo = ft.Text("Anteprima PDF", size=13, weight=ft.FontWeight.BOLD, expand=True)
        self.preview_zoom_btn = ft.IconButton(ft.Icons.ZOOM_IN, tooltip="Ingrandisci (popup)",
                                              on_click=self.apri_anteprima_popup, disabled=True)
        self.preview_img = ft.Image(src="", fit=ft.BoxFit.FIT_WIDTH, visible=False)
        self.preview_txt = ft.Text("Seleziona una riga (icona 👁) per vedere il PDF originale.",
                                   size=12, color=ft.Colors.ON_SURFACE_VARIANT, selectable=True)
        preview = ft.Container(
            content=ft.Column([
                ft.Row([self.preview_titolo, self.preview_zoom_btn],
                       vertical_alignment=ft.CrossAxisAlignment.CENTER),
                ft.Divider(height=1),
                ft.Column([self.preview_img, self.preview_txt],
                          scroll=ft.ScrollMode.AUTO, expand=True)],
                spacing=6, expand=True),
            width=self._preview_w(), padding=ft.Padding(left=8, top=0, right=16, bottom=8),
            border=ft.Border(left=ft.BorderSide(1, ft.Colors.OUTLINE_VARIANT)))
        self.preview_container = preview

        corpo = ft.Row([table, preview], expand=True, spacing=0,
                       vertical_alignment=ft.CrossAxisAlignment.STRETCH)

        self.watch_btn = ft.OutlinedButton("Cartella sorvegliata", icon=ft.Icons.FOLDER_SPECIAL,
                                           on_click=self.toggle_sorveglia)
        footer = ft.Container(
            content=ft.Row([
                ft.Row([self.start_field, self.data_field,
                        ft.OutlinedButton("Cartella output", icon=ft.Icons.FOLDER,
                                          on_click=self.scegli_output),
                        self.watch_btn], spacing=10),
                self.status,
            ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
            padding=ft.Padding(left=16, top=6, right=16, bottom=10),
        )

        self.page.add(ft.Column([
            header, ft.Container(self.info, padding=ft.Padding(left=16, top=0, right=16, bottom=6)),
            self.drop, corpo, footer,
        ], spacing=0, expand=True))
        self._render_table()

    def _info_text(self):
        az = self.cfg.get("azienda", {})
        tr = self.cfg.get("trasmittente", {})
        return (f"Cessionario: {az.get('denominazione','?')}  ·  P.IVA {az.get('piva','?')}  ·  "
                f"Trasmittente {tr.get('id_codice','?')}  ·  Dest. {self.cfg.get('codice_destinatario','?')}")

    def _tema(self, mode):
        self.page.theme_mode = {"system": ft.ThemeMode.SYSTEM, "light": ft.ThemeMode.LIGHT,
                                "dark": ft.ThemeMode.DARK}[mode]
        self.page.update()

    # ------------------------------------------------------------ tabella
    def _win_w(self):
        """Larghezza contenuto corrente (logical px), con fallback."""
        try:
            return int(self.page.width or self.page.window.width or 1200)
        except Exception:
            return 1200

    def _preview_w(self):
        """Larghezza responsive del pannello anteprima (0 se nascosto)."""
        if not self._preview_on:
            return 0
        return max(300, min(560, int(self._win_w() * 0.34)))

    def toggle_anteprima(self, e=None):
        """Mostra/nasconde il pannello anteprima per liberare spazio alle colonne."""
        self._preview_on = not self._preview_on
        if self.preview_container is not None:
            self.preview_container.visible = self._preview_on
        self._adatta()
        self._set_status("Anteprima mostrata." if self._preview_on
                         else "Anteprima nascosta: più spazio per le colonne.")

    def _larghezze(self):
        w = {}
        for key, label, minw in COLS:
            if key in self.manual:                      # colonna regolata a mano: mantieni
                w[key] = self.col_w.get(key, minw)
                continue
            longest = len(label)
            for d in self.data:
                longest = max(longest, len(str(d.get(key, "") or "")))
            w[key] = min(MAX_W, max(minw, int(longest * CHAR_PX + PAD_PX)))
        # Responsive: se c'e' spazio, allarga le colonne non manuali per riempire la
        # larghezza disponibile (altrimenti restano al naturale e la tabella scorre).
        avail = self._win_w() - self._preview_w() - 40
        fissi = 26 + 80 + 6 * (len(COLS) + 2)           # stato + azioni + spaziature
        flessibili = [k for k, _l, _m in COLS if k not in self.manual]
        tot = sum(w.values()) + fissi
        if avail > tot and flessibili:
            extra = avail - tot
            base = sum(w[k] for k in flessibili) or 1
            for k in flessibili:
                w[k] += int(extra * w[k] / base)
        self.col_w = dict(w)
        return w

    def _adatta(self, e=None):
        """Handler resize: adatta pannello anteprima e larghezze colonne alla finestra."""
        try:
            if self.preview_container is not None:
                self.preview_container.width = self._preview_w()
            w = self._larghezze()
            for key, _l, _m in COLS:
                if key in self.head_cells:
                    self.head_cells[key].width = w[key]
                for d in self.data:
                    c = (d.get("_ctrl") or {}).get(key)
                    if c is not None:
                        c.width = max(w[key], 92) if key == "tipo_documento" else w[key]
            self.page.update()
        except Exception:
            pass

    def _resize(self, key, dx):
        try:
            dx = float(dx or 0)
        except (TypeError, ValueError):
            dx = 0
        neww = max(46, int(self.col_w.get(key, 80) + dx))
        self.col_w[key] = neww
        self.manual.add(key)
        if key in self.head_cells:
            self.head_cells[key].width = neww
        for d in self.data:
            c = d.get("_ctrl")
            if c and key in c:
                c[key].width = max(neww, 92) if key == "tipo_documento" else neww
        self.page.update()

    def _cella_header(self, key, lab, width):
        cell = ft.Container(
            width=width,
            content=ft.Row([
                ft.Container(ft.Text(lab, size=12, weight=ft.FontWeight.BOLD), expand=True),
                ft.GestureDetector(
                    mouse_cursor=ft.MouseCursor.RESIZE_COLUMN,
                    on_pan_update=lambda e, k=key: self._resize(k, e.local_delta.x),
                    content=ft.Container(width=6, height=22, border_radius=3,
                                         bgcolor=ft.Colors.OUTLINE_VARIANT,
                                         tooltip="Trascina per allargare/stringere"),
                ),
            ], spacing=2, vertical_alignment=ft.CrossAxisAlignment.CENTER),
        )
        self.head_cells[key] = cell
        return cell

    def _sync(self):
        """Riporta i valori dei controlli nelle righe-dati (prima di ricostruire)."""
        for d in self.data:
            c = d.get("_ctrl")
            if c:
                for key, _l, _m in COLS:
                    d[key] = c[key].value

    def _render_table(self):
        w = self._larghezze()
        self.head_cells = {}
        header = ft.Row(
            [ft.Container(width=26)]
            + [self._cella_header(key, lab, w[key]) for key, lab, _m in COLS]
            + [ft.Container(width=80)], spacing=6)
        controls = [header]
        for d in self.data:
            controls.append(self._riga(d, w))
        self.table_inner.controls = controls
        self.page.update()

    def _riga(self, d, w):
        ctrls = {}
        cells = []
        warn = bool(d.get("_note"))
        for key, lab, _m in COLS:
            val = str(d.get(key, "") or "")
            if key == "file":
                c = ft.TextField(value=val, width=w[key], height=40, text_size=12, dense=True, read_only=True)
            elif key == "tipo_documento":
                c = ft.Dropdown(value=val or "TD17", width=max(w[key], 92), text_size=12, dense=True,
                                options=[ft.dropdown.Option(x) for x in ("TD16", "TD17", "TD18", "TD19")])
            else:
                c = ft.TextField(value=val, width=w[key], height=40, text_size=12, dense=True)
                if warn and key in ("denominazione", "id_paese", "id_codice", "imponibile") \
                        and (val in ("", "??") or "VERIFICA" in val.upper()):
                    c.border_color = WARN
                if key in ("data", "data_fattura_originaria", "imponibile", "aliquota_iva",
                           "id_paese", "id_codice"):
                    c.on_change = lambda e, k=key: self._on_campo_change(e, k)
            ctrls[key] = c
            cells.append(c)
        d["_ctrl"] = ctrls
        azioni = ft.Row([
            ft.IconButton(ft.Icons.VISIBILITY, icon_size=16, tooltip="Anteprima PDF",
                          on_click=lambda e, dd=d: self.mostra_anteprima(dd)),
            ft.PopupMenuButton(icon=ft.Icons.MORE_VERT, tooltip="Azioni", items=[
                ft.PopupMenuItem(content="Salva come fornitore noto",
                                 on_click=lambda e, dd=d: self.salva_fornitore_da_riga(dd)),
                ft.PopupMenuItem(content="Rimuovi",
                                 on_click=lambda e, dd=d: self._del_row(dd)),
            ]),
        ], spacing=0)
        cells.append(ft.Container(azioni, width=80))
        return ft.Row([self._icona_stato(d)] + cells, spacing=6)

    def _icona_stato(self, d):
        """Icona di validazione della riga: verde=valido, rosso=errore, giallo=duplicato."""
        stato = d.get("_valid")
        if stato is False:
            ic = ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED, size=18,
                         tooltip="XML non valido:\n" + "\n".join(d.get("_valid_err", []))[:600])
        elif d.get("_dup"):
            dup = d["_dup"]
            ic = ft.Icon(ft.Icons.WARNING_AMBER, color=WARN, size=18,
                         tooltip=f"Gia' in archivio: n. {dup.get('numero','?')} "
                                 f"({dup.get('data_registrazione','?')})")
        elif stato is True:
            ic = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN, size=18, tooltip="XML valido")
        else:
            ic = ft.Icon(ft.Icons.RADIO_BUTTON_UNCHECKED, color=ft.Colors.OUTLINE, size=16,
                         tooltip="Non ancora validato")
        return ft.Container(ic, width=26, alignment=ft.Alignment.CENTER)

    def _del_row(self, d):
        self._sync()
        if d in self.data:
            self.data.remove(d)
        self._render_table()
        self._set_status(f"{len(self.data)} fatture in tabella.")

    def _set_status(self, t):
        self.status.value = t
        self.page.update()

    # ---------------------------------------------------- Fase 2: revisione
    def _png_size(self, png):
        """Ritorna (w, h) in px del PNG, o (None, None)."""
        try:
            import io as _io
            from PIL import Image as _PILImage
            return _PILImage.open(_io.BytesIO(png)).size
        except Exception:
            return (None, None)

    def _scrivi_png_temp(self, png, prefisso, tieni_precedente_attr=None):
        import tempfile
        pdir = os.path.join(tempfile.gettempdir(), "reversa_preview")
        os.makedirs(pdir, exist_ok=True)
        if tieni_precedente_attr:
            prev = getattr(self, tieni_precedente_attr, None)
            if prev and os.path.exists(prev):
                try:
                    os.remove(prev)
                except OSError:
                    pass
        n = getattr(self, "_preview_n", 0) + 1
        self._preview_n = n
        outp = os.path.join(pdir, f"{prefisso}_{n}.png")
        with open(outp, "wb") as f:
            f.write(png)
        return outp

    def mostra_anteprima(self, d):
        path = d.get("_path")
        nome = d.get("file") or "PDF"
        self.preview_titolo.value = f"Anteprima — {nome}"
        self._preview_path = path if (path and os.path.exists(path)) else None
        self.preview_zoom_btn.disabled = self._preview_path is None
        if self._preview_path:
            png = anteprima.render_png(path, scale=2.0)
            if png:
                outp = self._scrivi_png_temp(png, "prev", tieni_precedente_attr="_preview_file")
                self._preview_file = outp
                w, h = self._png_size(png)
                larghezza = 440
                self.preview_img.src = outp
                self.preview_img.width = larghezza
                self.preview_img.height = int(larghezza * h / w) if (w and h) else None
                self.preview_img.visible = True
                self.preview_txt.visible = False
                self.page.update()
                return
            testo = anteprima.estrai_testo(path)
            self.preview_img.visible = False
            self.preview_txt.value = testo or "Impossibile mostrare il PDF."
            self.preview_txt.visible = True
        else:
            self.preview_img.visible = False
            note = d.get("_note") or []
            self.preview_txt.value = ("PDF non disponibile per questa riga."
                                      + (("\n\n" + "\n".join(note)) if note else ""))
            self.preview_txt.visible = True
        self.page.update()

    def apri_anteprima_popup(self, e=None):
        path = getattr(self, "_preview_path", None)
        if not path or not os.path.exists(path):
            self._set_status("Nessun PDF da ingrandire: seleziona prima una riga con 👁.")
            return
        png = anteprima.render_png(path, scale=3.0)
        if not png:
            self._dialogo("Anteprima", "Impossibile renderizzare il PDF.")
            return
        outp = self._scrivi_png_temp(png, "pop", tieni_precedente_attr="_popup_file")
        self._popup_file = outp
        w, h = self._png_size(png)
        disp_w = 900
        img = ft.Image(src=outp, width=disp_w, fit=ft.BoxFit.FIT_WIDTH,
                       height=int(disp_w * h / w) if (w and h) else None)
        dlg = ft.AlertDialog(
            title=ft.Text(f"Anteprima — {os.path.basename(path)}"),
            content=ft.Container(
                ft.Column([ft.Row([img], scroll=ft.ScrollMode.AUTO)], scroll=ft.ScrollMode.AUTO),
                width=980, height=700),
            actions=[ft.TextButton("Chiudi", on_click=lambda e: self.page.pop_dialog())])
        self.page.show_dialog(dlg)

    def salva_fornitore_da_riga(self, d):
        self._sync()
        forn = dict(d.get("_extra", {}).get("fornitore", {}))
        denom = (d.get("denominazione") or "").strip()
        prefill = {
            "chiave": denom.lower()[:24],
            "denominazione": denom,
            "id_paese": (d.get("id_paese") or "").strip(),
            "id_codice": (d.get("id_codice") or "").strip(),
            "indirizzo": forn.get("indirizzo", ""),
            "numero_civico": forn.get("numero_civico", ""),
            "cap": forn.get("cap", "") or "00000",
            "comune": forn.get("comune", ""),
            "nazione": forn.get("nazione", "") or (d.get("id_paese") or "").strip(),
            "tipo_documento": (d.get("tipo_documento") or "TD17").strip(),
        }
        from settings_flet import build_settings_dialog
        build_settings_dialog(self.page, self.cfg, on_save=self._dopo_impostazioni,
                              prefill_fornitore=prefill, tab_index=2)

    # ---- validazione inline dei campi ----
    def _valida_campo(self, key, val):
        v = (val or "").strip()
        if key in ("data", "data_fattura_originaria"):
            if v == "":
                return True, ""
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
                return False, "Data in formato AAAA-MM-GG."
            return True, ""
        if key in ("imponibile", "aliquota_iva"):
            if v == "":
                return (key != "imponibile", "Imponibile mancante." if key == "imponibile" else "")
            try:
                float(v.replace(",", "."))
                return True, ""
            except ValueError:
                return False, "Valore non numerico."
        if key == "id_paese":
            if len(v) == 2 and v.isalpha():
                return True, ""
            return False, "Paese: 2 lettere (es. IT, IE)."
        if key == "id_codice":
            return (bool(v), "" if v else "P.IVA/ID mancante.")
        return True, ""

    def _on_campo_change(self, e, key):
        ok, msg = self._valida_campo(key, e.control.value)
        e.control.border_color = None if ok else ft.Colors.RED
        e.control.tooltip = None if ok else msg
        try:
            e.control.update()
        except Exception:
            self.page.update()
        if not ok:
            self._set_status(f"⚠ {msg}")

    # ---- cartella sorvegliata ----
    async def toggle_sorveglia(self, e=None):
        if getattr(self, "_watch_active", False):
            self._watch_active = False
            self.watch_btn.text = "Cartella sorvegliata"
            self._set_status("Sorveglianza cartella disattivata.")
            return
        try:
            folder = await self.fp.get_directory_path(dialog_title="Cartella da sorvegliare")
        except Exception as ex:
            self._set_status(f"Selezione cartella non disponibile: {ex}")
            return
        if not folder:
            return
        self._watch_dir = folder
        try:
            self._watch_seen = set(os.listdir(folder))
        except Exception:
            self._watch_seen = set()
        self._watch_active = True
        self.watch_btn.text = "Sorveglianza ON"
        self._set_status(f"Sorveglio: {folder}")
        self.page.run_task(self._watch_loop)

    async def _watch_loop(self):
        import asyncio
        while getattr(self, "_watch_active", False):
            try:
                files = set(os.listdir(self._watch_dir))
                nuovi = [os.path.join(self._watch_dir, f)
                         for f in sorted(files - self._watch_seen) if f.lower().endswith(".pdf")]
                self._watch_seen = files
                if nuovi:
                    self._add_pdfs(nuovi)
                    self._set_status(f"Importati {len(nuovi)} PDF dalla cartella sorvegliata.")
            except Exception:
                pass
            await asyncio.sleep(3)

    # ---------------------------------------------------------------- azioni
    async def aggiungi_pdf(self, e=None):
        try:
            res = await self.fp.pick_files(dialog_title="Seleziona i PDF", allow_multiple=True,
                                           allowed_extensions=["pdf"])
        except Exception as ex:
            self._set_status(f"Selezione file non disponibile: {ex}")
            return
        self._add_pdfs([f.path for f in res] if res else [])

    def _add_pdfs(self, paths):
        self._sync()
        n_ok = n_note = 0
        conversioni = []
        for p in paths:
            try:
                d = estrazione.estrai_da_pdf(p, self.cfg.get("azienda", {}).get("piva", ""))
                forn = d.get("fornitore", {})
                imp = d.get("imponibile")
                valuta = (d.get("valuta") or "EUR").upper()
                note = list(d.get("note", []))
                data_rif = d.get("data_fattura_originaria") or d.get("data")
                if imp is not None and valuta != "EUR" and data_rif:
                    conv = None
                    try:
                        conv = cambio.converti_in_eur(imp, valuta, data_rif)
                    except Exception:
                        conv = None
                    note = [n for n in note if "converti l'imponibile" not in n.lower()]
                    if conv:
                        conversioni.append(f"{forn.get('denominazione','?')}: {imp:.2f} {valuta} → "
                                           f"{conv['eur']:.2f} EUR (cambio BdI {conv['tasso']} del {conv['data_cambio']})")
                        imp = conv["eur"]
                        note.append(f"Convertito da {valuta} in EUR (cambio Banca d'Italia "
                                    f"{conv['tasso']} del {conv['data_cambio']}) — verifica.")
                    else:
                        note.append(f"Cambio Banca d'Italia non disponibile: converti a mano da {valuta} in EUR.")
                self.data.append({
                    "_path": p,
                    "file": os.path.basename(d.get("file", "")),
                    "denominazione": forn.get("denominazione", ""),
                    "id_paese": forn.get("id_paese", ""),
                    "id_codice": forn.get("id_codice", ""),
                    "tipo_documento": d.get("tipo_documento", "TD17"),
                    "imponibile": "" if imp is None else f"{imp:.2f}",
                    "aliquota_iva": d.get("aliquota_iva", self.cfg.get("aliquota_default", "22.00")),
                    "num_fattura_originaria": d.get("num_fattura_originaria", "") or "",
                    "data_fattura_originaria": d.get("data_fattura_originaria", "") or "",
                    "data": d.get("data", "") or "",
                    "descrizione": d.get("descrizione", "") or "",
                    "_extra": {"fornitore": forn, "note": note}, "_note": note,
                })
                n_ok += 1
                n_note += 1 if note else 0
            except Exception as ex:
                self._set_status(f"Errore su {os.path.basename(p)}: {ex}")
        self._render_table()
        msg = f"Aggiunte {n_ok} fatture" + (f" · {n_note} da verificare" if n_note else " · nessun avviso")
        if conversioni:
            msg += "  ·  " + "  ·  ".join(conversioni)
        self._set_status(msg)

    async def scegli_output(self, e=None):
        try:
            res = await self.fp.get_directory_path(dialog_title="Cartella output")
        except Exception as ex:
            self._set_status(f"Selezione cartella non disponibile: {ex}")
            return
        if res:
            self.output_dir = res
            self._set_status(f"Output: {res}")

    def apri_impostazioni(self, e=None):
        from settings_flet import build_settings_dialog
        build_settings_dialog(self.page, self.cfg, on_save=self._dopo_impostazioni)

    def _dopo_impostazioni(self, nuova):
        self.cfg = nuova
        self.info.value = self._info_text()
        self.start_field.value = str(self._numero_suggerito())
        self.page.update()
        self._set_status("Impostazioni salvate.")

    # ----- numerazione sicura / costruzione invoice / archivio ----------
    def _start_int(self):
        try:
            return int(self.start_field.value)
        except (ValueError, TypeError):
            return None

    def _numero_suggerito(self):
        """Prossimo sezionale proposto in base all'archivio (fallback: config)."""
        fallback = self.cfg.get("progressivo_start", 1)
        try:
            return archivio.prossimo_progressivo(fallback=fallback)
        except Exception:
            return fallback

    def _riga_to_inv(self, d, data_glob):
        """Costruisce l'invoice dal record-riga. Ritorna (inv, errore_o_None)."""
        forn = dict(d.get("_extra", {}).get("fornitore", {}))
        forn.update({"denominazione": (d.get("denominazione") or "").strip(),
                     "id_paese": (d.get("id_paese") or "").strip(),
                     "id_codice": (d.get("id_codice") or "").strip(),
                     "nazione": forn.get("nazione") or (d.get("id_paese") or "").strip()})
        imp = _to_float(d.get("imponibile"))
        if imp is None:
            return None, "imponibile mancante/non valido."
        data_reg = data_glob or (d.get("data") or "").strip()
        if not data_reg:
            return None, "manca la data (compila «Data autofattura»)."
        inv = {
            "tipo_documento": (d.get("tipo_documento") or "TD17").strip(),
            "data": data_reg,
            "aliquota_iva": (d.get("aliquota_iva") or "22.00").strip(),
            "imponibile": imp,
            "num_fattura_originaria": (d.get("num_fattura_originaria") or "").strip(),
            "data_fattura_originaria": (d.get("data_fattura_originaria") or "").strip() or None,
            "fornitore": forn,
            "righe": [{"descrizione": (d.get("descrizione") or "Servizio").strip(),
                       "quantita": 1, "prezzo": imp}],
        }
        return inv, None

    def _trova_dup(self, inv):
        try:
            return archivio.esiste_duplicato(inv["fornitore"].get("denominazione", ""),
                                             inv.get("num_fattura_originaria", ""))
        except Exception:
            return None

    def _anomalie_txt(self):
        try:
            an = archivio.anomalie_numerazione()
        except Exception:
            an = []
        return ("  ⚠ " + " ".join(an)) if an else ""

    def _registra_in_archivio(self, inv, prog, fname, imp2, al, iva, tot):
        """Registra l'autofattura generata; non deve mai bloccare la generazione."""
        try:
            archivio.registra({
                "progressivo": prog,
                "numero": motore.numero_documento(self.cfg, inv, prog),
                "tipo_documento": inv["tipo_documento"],
                "fornitore": inv["fornitore"].get("denominazione", ""),
                "fornitore_id": inv["fornitore"].get("id_codice", ""),
                "num_fattura_originaria": inv.get("num_fattura_originaria", ""),
                "data_fattura_originaria": inv.get("data_fattura_originaria") or "",
                "data_registrazione": inv["data"],
                "imponibile": float(imp2), "aliquota": str(al),
                "imposta": float(iva), "totale": float(tot),
                "valuta": "EUR", "filename": fname, "stato": "generata",
            })
        except Exception as ex:
            self._set_status(f"Attenzione: archivio non aggiornato ({ex}).")

    # ----- validazione per riga (verde/rosso) ---------------------------
    def valida_righe(self, e=None):
        if not self.data:
            self._set_status("Nessuna riga da validare.")
            return
        self._sync()
        start = self._start_int()
        if start is None:
            self._dialogo("Numerazione", "Il primo numero sezionale deve essere un intero.")
            return
        data_glob = (self.data_field.value or "").strip()
        n_ok = n_ko = n_dup = 0
        for i, d in enumerate(self.data):
            inv, err = self._riga_to_inv(d, data_glob)
            if err:
                d["_valid"] = False; d["_valid_err"] = [err]; d["_dup"] = None
                n_ko += 1
                continue
            try:
                _fn, xml, _w = motore.genera_xml_bytes(inv, self.cfg, start + i)
                ok, errs = validazione.valida_xml(xml)
            except Exception as ex:
                ok, errs = False, [str(ex)]
            d["_valid"] = ok
            d["_valid_err"] = errs
            d["_dup"] = self._trova_dup(inv)
            n_ok += 1 if ok else 0
            n_ko += 0 if ok else 1
            n_dup += 1 if d["_dup"] else 0
        self._render_table()
        extra = f" · {n_dup} già in archivio" if n_dup else ""
        self._set_status(f"Validazione: {n_ok} valide, {n_ko} con errori{extra}.{self._anomalie_txt()}")

    def genera(self, e=None):
        if not self.data:
            self._dialogo("Genera XML", "Aggiungi almeno una fattura.")
            return
        self._sync()
        start = self._start_int()
        if start is None:
            self._dialogo("Numerazione", "Il primo numero sezionale deve essere un intero.")
            return
        os.makedirs(self.output_dir, exist_ok=True)
        data_glob = (self.data_field.value or "").strip()

        generati, errori, duplicati, riepilogo = 0, [], [], []
        for i, d in enumerate(self.data):
            prog = start + i
            inv, err = self._riga_to_inv(d, data_glob)
            if err:
                d["_valid"] = False; d["_valid_err"] = [err]; d["_dup"] = None
                errori.append(f"Riga {i+1}: {err}")
                continue
            forn = inv["fornitore"]
            try:
                fname, xml, _w = motore.genera_xml_bytes(inv, self.cfg, prog)
            except Exception as ex:
                d["_valid"] = False; d["_valid_err"] = [str(ex)]; d["_dup"] = None
                errori.append(f"Riga {i+1} ({forn.get('denominazione','?')}): {ex}")
                continue
            # Validazione XSD PRIMA di scrivere: un XML invalido non viene salvato.
            ok, verrs = validazione.valida_xml(xml)
            d["_valid"] = ok
            d["_valid_err"] = verrs
            if not ok:
                errori.append(f"Riga {i+1} ({forn.get('denominazione','?')}): XML non valido — "
                              + "; ".join(verrs[:3]))
                continue
            # Duplicato? avvisa ma genera comunque.
            dup = self._trova_dup(inv)
            d["_dup"] = dup
            if dup:
                duplicati.append(f"Riga {i+1} ({forn.get('denominazione','?')}, "
                                 f"fatt. {inv.get('num_fattura_originaria') or '—'}): già in "
                                 f"archivio come n. {dup.get('numero','?')}.")
            with open(os.path.join(self.output_dir, fname), "wb") as fh:
                fh.write(xml)
            imp2, al, iva, tot = motore.calcola_importi(inv)
            riepilogo.append([fname, inv["tipo_documento"],
                              motore.numero_documento(self.cfg, inv, prog), inv["data"],
                              forn["denominazione"], forn["id_paese"], f"{imp2}", f"{al}",
                              f"{iva}", f"{tot}", inv["num_fattura_originaria"]])
            self._registra_in_archivio(inv, prog, fname, imp2, al, iva, tot)
            generati += 1

        if riepilogo:
            with open(os.path.join(self.output_dir, "riepilogo.csv"), "w", newline="", encoding="utf-8") as fh:
                wcsv = csv.writer(fh, delimiter=";")
                wcsv.writerow(["file_xml", "tipo_doc", "numero", "data_reg", "fornitore", "paese",
                               "imponibile", "aliquota", "imposta", "totale", "rif_fattura"])
                wcsv.writerows(riepilogo)

        if generati:
            self.cfg["progressivo_start"] = start + generati
            if self.cfg.get("ricorda_ultimo_numero", True):
                config_io.salva_config(self.cfg)
            self.start_field.value = str(self._numero_suggerito())
        self._render_table()

        msg = f"Generati {generati} file XML in:\n{self.output_dir}"
        if duplicati:
            msg += "\n\n⚠ Possibili duplicati (già in archivio):\n• " + "\n• ".join(duplicati)
        if errori:
            msg += "\n\nDa correggere:\n• " + "\n• ".join(errori)
        self._dialogo("Genera XML", msg)
        self._set_status(f"Generati {generati} XML"
                         + (f" · {len(duplicati)} duplicati" if duplicati else "")
                         + (f" · {len(errori)} errori" if errori else " · nessun errore"))

    def _dialogo(self, titolo, testo):
        dlg = ft.AlertDialog(title=ft.Text(titolo), content=ft.Text(testo),
                             actions=[ft.TextButton("OK", on_click=lambda e: self.page.pop_dialog())])
        self.page.show_dialog(dlg)


def _to_float(s):
    s = (s or "").strip().replace(",", ".")
    try:
        return round(float(s), 2)
    except ValueError:
        return None


def main(page: ft.Page):
    ui = UI(page)
    auto = os.environ.get("AUTO_PDFS")
    if auto:
        ui._add_pdfs([p for p in auto.split("||") if p])
        if os.environ.get("AUTO_DATA"):
            ui.data[0]["data"] = os.environ["AUTO_DATA"]
        if os.environ.get("AUTO_DESC"):
            ui.data[0]["descrizione"] = os.environ["AUTO_DESC"]
        ui._render_table()
        if os.environ.get("AUTO_START"):
            ui.start_field.value = os.environ["AUTO_START"]
        if os.environ.get("AUTO_GEN"):
            ui.output_dir = os.environ["AUTO_GEN"]
            ui.cfg["ricorda_ultimo_numero"] = False
            ui.genera()
    if os.environ.get("AUTO_RESIZE"):
        k, dx = os.environ["AUTO_RESIZE"].split(":")
        ui._resize(k, float(dx))
    if os.environ.get("AUTO_SETTINGS"):
        ui.apri_impostazioni()
    if os.environ.get("AUTO_FAKEROW"):          # riga fittizia per test GUI (senza PDF)
        ui.data.append({
            "file": "esempio.pdf", "denominazione": "Foreign Supplier Ltd", "id_paese": "IE",
            "id_codice": "IE1234567AB", "tipo_documento": "TD17", "imponibile": "100.00",
            "aliquota_iva": "22.00", "num_fattura_originaria": "TEST-001",
            "data_fattura_originaria": "2026-02-28", "data": "2026-03-15",
            "descrizione": "Servizio di esempio",
            "_extra": {"fornitore": {"denominazione": "Foreign Supplier Ltd", "id_paese": "IE",
                                     "id_codice": "IE1234567AB", "indirizzo": "1 Test Street",
                                     "cap": "00000", "comune": "Dublin", "nazione": "IE"}},
            "_note": [],
        })
        ui._render_table()
        if os.environ.get("AUTO_GEN"):
            ui.output_dir = os.environ["AUTO_GEN"]
            ui.cfg["ricorda_ultimo_numero"] = False
            ui.genera()
    if os.environ.get("AUTO_VALIDA"):
        ui.valida_righe()
    if os.environ.get("AUTO_PREVIEW") and ui.data:
        ui.mostra_anteprima(ui.data[0])
    if os.environ.get("AUTO_POPUP") and ui.data:
        ui.mostra_anteprima(ui.data[0])
        ui.apri_anteprima_popup()
    if os.environ.get("AUTO_SAVEFORN") and ui.data:
        ui.salva_fornitore_da_riga(ui.data[0])
    if os.environ.get("AUTO_WATCH"):            # avvia la sorveglianza su una cartella (test)
        ui._watch_dir = os.environ["AUTO_WATCH"]
        ui._watch_seen = set()
        ui._watch_active = True
        ui.watch_btn.text = "Sorveglianza ON"
        page.run_task(ui._watch_loop)


if __name__ == "__main__":
    if os.environ.get("FLET_WEB_TEST"):
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=int(os.environ.get("PORT", "8560")), no_cdn=True)
    else:
        ft.run(main)
