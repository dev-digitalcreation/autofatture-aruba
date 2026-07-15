# Prompt da dare a Claude Code

Incolla il testo qui sotto come primo messaggio a Claude Code, dopo aver aperto
la cartella del progetto. Sostituisci `TUO_USERNAME` con il tuo username GitHub.

---

Contesto: in questa cartella c'è "Reversa", un'app desktop in Python +
Flet che genera autofatture/integrazioni reverse charge (TD16–TD19) in XML per il
portale Aruba. Voglio trasformarla in un'applicazione Windows con installer,
pubblicarla su un repository GitHub PRIVATO e abilitare gli aggiornamenti
automatici. Usa il file `BUILD.md` presente nella cartella come guida autorevole:
leggilo prima di iniziare, insieme a `version.py`.

Procedi in ordine, mostrandomi eventuali errori e proponendo i fix, iterando
finché exe e aggiornamenti funzionano:

1. Installa le dipendenze: `pip install -r requirements.txt -r requirements-build.txt`.
   Avvia `python main.py` e verifica che l'app parta e funzioni (aggiungi un PDF,
   controlla la tabella, apri Impostazioni con le schede, genera un XML).

2. Compila l'exe con Flet: è un'app Flet, quindi usa `flet pack` (NON PyInstaller
   grezzo). Comando base:
   `flet pack main.py --name Reversa --product-name "Reversa"`.
   Se l'exe all'avvio segnala moduli mancanti, riprova aggiungendo gli
   hidden-import: `a38`, `pdfplumber`, `dateutil`, `lxml`.
   Prova `dist\Reversa.exe`: alla prima apertura deve creare la config in
   `%APPDATA%\Reversa` e funzionare. Testa: aggiunta PDF, generazione XML,
   e (serve internet) la conversione valuta per una fattura in USD.

3. Crea l'installer con Inno Setup da `build\installer.iss` (verifica che
   `MyAppVersion` combaci con `version.py`). Output atteso:
   `dist_installer\Reversa_Setup.exe`. Installalo e verifica collegamento
   nel menu Start e disinstallazione.

4. Crea il repository GitHub PUBBLICO e fai il push:
   `gh repo create reversa --public --source=. --push`.
   PRIMA verifica che NON finisca online alcun dato personale: `config/azienda.json`,
   `config/fornitori.json` e i token sono già in `.gitignore`, e i default in
   `config_io.py` sono generici (campi azienda e IBAN vuoti). Se trovi dati
   personali residui nel codice, segnalameli e rimuovili prima del push.

5. Imposta in `version.py`: `GITHUB_OWNER = "TUO_USERNAME"` e
   `GITHUB_REPO = "reversa"`. Committa.

6. Pubblica la prima release allegando l'installer:
   `gh release create v1.0.0-beta.1 dist_installer\Reversa_Setup.exe --prerelease --title "v1.0.0-beta.1" --notes "Prima beta"`.

7. Verifica gli aggiornamenti (repo pubblico, NESSUN token): avvia l'app, apri
   Impostazioni → Info e premi "Controlla aggiornamenti": deve dire che sei
   aggiornato. Poi, come test del flusso: porta la versione a `1.0.0-beta.2` (in
   `version.py` E in `build\installer.iss`), ricompila exe+installer, pubblica
   `v1.0.0-beta.2`, e verifica che l'app installata proponga l'aggiornamento e lo
   scarichi/avvii correttamente.

Vincoli:
- Non modificare il "motore" (`motore.py`, `estrazione.py`, `cambio.py`) se non
  strettamente necessario; se lo tocchi, verifica che l'XML generato resti identico.
- Il `tag` di ogni release deve combaciare con `__version__` di `version.py`.
- A ogni nuova versione aggiorna sempre SIA `version.py` SIA `build\installer.iss`.

Il mio username GitHub è: ________
