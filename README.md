<div align="center">

<img src="assets/reversa_logo.svg" alt="Reversa" width="360">

**Autofatture e integrazioni reverse charge (TD16–TD19) in FatturaPA XML, pronte per il portale Aruba.**

[![Ultima release](https://img.shields.io/github/v/release/dev-digitalcreation/reversa?label=release)](https://github.com/dev-digitalcreation/reversa/releases/latest)
![Piattaforma](https://img.shields.io/badge/piattaforma-Windows-0078D6)
![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB)
![UI](https://img.shields.io/badge/UI-Flet-02569B)

</div>

---

## Cos'è

**Reversa** trasforma i PDF delle **fatture passive estere** (servizi/beni in reverse charge)
nelle **autofatture / integrazioni elettroniche** (TD16, TD17, TD18, TD19) in formato
**FatturaPA XML**, pronte per il caricamento massivo sul portale
**Aruba Fatturazione Elettronica**.

Il motore di estrazione e generazione è quello validato su fatture reali; l'interfaccia
(realizzata in [Flet](https://flet.dev)) lo richiama soltanto.

> ⚠️ **Nota fiscale** — Lo strumento *prepara* i documenti, non sostituisce il commercialista.
> Prima dell'invio verifica sempre: codice TD, aliquota/natura IVA, data di registrazione e
> numerazione del sezionale.

## Funzionalità

- 📄 **Estrazione automatica** dai PDF: fornitore, numero, data, imponibile, valuta.
- 🧾 **Generazione FatturaPA 1.2.2** con **validazione contro l'XSD ufficiale**.
- 💱 **Valuta estera** → conversione dell'imponibile in EUR al **cambio Banca d'Italia** del giorno fattura.
- 🗂️ **Archivio** delle autofatture con **controllo duplicati** e numerazione del sezionale.
- 🏷️ **Fornitori noti**: i fornitori ricorrenti vengono riconosciuti e precompilati.
- 👁️ **Anteprima PDF** affiancata (con zoom) e **cartella sorvegliata** (import automatico).
- 📊 **Dashboard** (n. fatture, imponibile, IVA, da verificare) e righe a stato colorato.
- 💾 **Backup/ripristino** di configurazione e fornitori.
- 🔄 **Aggiornamenti automatici** dall'app (Impostazioni → Info → *Controlla aggiornamenti*).
- 🌗 Tema chiaro/scuro.

## Installazione

### Opzione A — Installer (consigliata)
1. Scarica **`Reversa_Setup.exe`** dall'ultima release:
   👉 [**Releases**](https://github.com/dev-digitalcreation/reversa/releases/latest)
2. Eseguilo e segui la procedura guidata.

> L'eseguibile non è firmato digitalmente: Windows SmartScreen potrebbe mostrare un avviso →
> *Ulteriori informazioni → Esegui comunque*.

### Opzione B — Da sorgente (Windows)
1. Doppio-click su **`Avvia.bat`**.
2. Solo la **prima volta**: se manca Python si apre la pagina di download (installa Python 3 e
   spunta *"Add python.exe to PATH"*), poi rilancia `Avvia.bat`. Lo script crea l'ambiente e
   installa le dipendenze da solo.
3. Le volte successive parte in pochi secondi.

Avvio manuale (per sviluppatori):
```bash
pip install -r requirements.txt
python main.py
```

## Come si usa

1. **Aggiungi PDF** → seleziona una o più fatture. L'app estrae i dati nella tabella:
   **controlla** e correggi dove serve (i campi incerti hanno il bordo giallo; gli errori diventano rossi).
2. Imposta **Primo n.** (numero di partenza del sezionale) e **Data autofattura** (data di registrazione).
3. *(Facoltativo)* scegli la **cartella output**.
4. **Genera XML** → trovi i file e un `riepilogo.csv` nella cartella di output.
5. Carica gli XML su **Aruba** → *Carica fattura* → invio a SdI.

Revisione più rapida: icona 👁 per l'anteprima del PDF, menu ⋮ per *Salva come fornitore noto* / *Rimuovi*.
Maggiori dettagli in [`LEGGIMI.txt`](LEGGIMI.txt).

## Impostazioni

Tutto gestibile dall'interfaccia (pulsante **Impostazioni**), senza toccare i file:
**Azienda** (cessionario, trasmittente Aruba, destinatario) · **Numerazione** (pattern, memoria del numero) ·
**Pagamento e IVA** (IBAN, aliquota, regime) · **Fornitori** (riconoscimento automatico).
I dati restano in locale in `%APPDATA%\Reversa` — nessun dato personale è incluso nel repository.

## Sviluppo

Stack: **Python 3.10+**, **Flet** (UI), `a38` (FatturaPA), `lxml`, `pdfplumber`, `pypdfium2` + `Pillow`, `python-dateutil`.

```bash
pip install -r requirements.txt          # dipendenze runtime
python main.py                           # avvia l'app
python tests/test_regressione.py         # test di regressione del motore (deve restare verde)
```

- **Test**: la cartella [`tests/`](tests/) genera un TD17, lo valida contro l'XSD ufficiale FatturaPA 1.2.2
  e lo confronta con un golden file; coperti anche archivio, validazione, anteprima, date e importo.
- **Build exe + installer + release**: guida completa in [`BUILD.md`](BUILD.md).

### Struttura del progetto
| File | Ruolo |
|------|-------|
| `main.py` | interfaccia Flet |
| `motore.py`, `estrazione.py`, `cambio.py`, `config_io.py` | motore (generazione XML, estrazione PDF, cambio valuta, config) |
| `archivio.py`, `validazione.py`, `anteprima.py`, `aggiornamenti.py` | archivio SQLite, validazione XSD, anteprima PDF, updater |
| `settings_flet.py`, `version.py` | impostazioni UI, versione/repo |
| `schema/` | XSD FatturaPA 1.2.2 (validazione runtime) |
| `build/installer.iss` | script Inno Setup per l'installer |

## Aggiornamenti

L'app legge la propria versione da `version.py` e interroga le **GitHub Releases** del repository:
se è disponibile una versione più recente, propone il download dell'installer. Repository pubblico →
nessun token necessario.

---

<div align="center">

© Digital Creation — Tutti i diritti riservati.

</div>
