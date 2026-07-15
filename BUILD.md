# Build & Release — Autofatture Aruba

Guida per creare l'`.exe` con installer, pubblicare su GitHub e abilitare gli
aggiornamenti automatici. Pensata per essere eseguita **su Windows** (Claude Code
in locale oppure a mano). Versione attuale: vedi `version.py` (`1.0.0-beta.1`).

Il codice è già predisposto per l'exe: la configurazione viene salvata in
`%APPDATA%\AutofattureAruba\config` (scrivibile) e i default vengono creati alla
prima esecuzione. Non serve includere `config/` nel pacchetto.

---

## 1. Prerequisiti (una volta)
- Windows 10/11, **Python 3.11+** (con "Add to PATH").
- **Inno Setup** 6: https://jrsoftware.org/isdl.php
- **git** e un account **GitHub** (repo privato per la beta).
- Dipendenze:
  ```
  pip install -r requirements.txt -r requirements-build.txt
  ```

## 2. Provare in sviluppo
```
python main.py
```
Verificare: aggiunta PDF, tabella, impostazioni a schede, Genera XML, e in
Impostazioni → Info il pulsante "Controlla aggiornamenti".

Test di regressione del motore (deve restare verde a ogni modifica):
```
python tests/test_regressione.py
```
Dettagli in `tests/README.md` (genera un TD17, valida contro l'XSD ufficiale
FatturaPA 1.2.2 e confronta col golden).

## 3. Creare l'exe (Flet)
Metodo consigliato (PyInstaller tramite Flet). Comando completo (hidden-import +
schema XSD per la validazione della Fase 1):
```
flet pack main.py --name AutofattureAruba --product-name "Autofatture Aruba" ^
  --copyright "Digital Creation" --company-name "Digital Creation" ^
  --hidden-import a38 --hidden-import pdfplumber --hidden-import dateutil --hidden-import lxml ^
  --add-data "schema:schema" -y
```
Output: `dist\AutofattureAruba.exe` (onefile).

- `--hidden-import a38 pdfplumber dateutil lxml`: moduli con import dinamici che
  PyInstaller non rileva da solo.
- `--add-data "schema:schema"`: **necessario** — include la cartella `schema/`
  (XSD FatturaPA) usata da `validazione.py` per validare l'XML nell'app.
  Senza, la validazione nell'exe non funziona.

(In alternativa `flet build windows` produce un'app Flutter nativa ma richiede
Flutter SDK + Visual Studio: più pesante, non necessario per la beta.)

Provare `dist\AutofattureAruba.exe`: alla prima apertura crea la config in
`%APPDATA%\AutofattureAruba`. I campi azienda sono vuoti: inserisci i tuoi dati
(denominazione, P.IVA, indirizzo e, se vuoi, l'IBAN) in Impostazioni →
Azienda/Pagamento prima di generare. Testare anche la conversione valuta (internet).

## 4. Creare l'installer (Inno Setup)
- Aprire `build\installer.iss` con Inno Setup.
- Controllare che `MyAppVersion` combaci con `version.py`.
- Compile (F9). Output: `dist_installer\AutofattureAruba_Setup.exe`.
- Se hai usato una build ONEDIR invece che onefile, nel `.iss` usa la riga
  "Variante ONEDIR" al posto di quella onefile.

## 5. Repository GitHub (pubblico)
Il repo è **pubblico**: gli aggiornamenti si scaricano senza alcun token.
IMPORTANTE prima di pubblicare: NON deve finire online alcun dato personale.
`config/azienda.json`, `config/fornitori.json` e i token sono già in `.gitignore`,
e i default in `config_io.py` sono generici (campi azienda/IBAN vuoti). Ogni
utente inserirà i propri dati in Impostazioni alla prima apertura.
```
git init            # se non già fatto
git add -A && git commit -m "beta 1"
gh repo create autofatture-aruba --public --source=. --push
```
Poi in `version.py` impostare:
```python
GITHUB_OWNER = "TUO_USERNAME"
GITHUB_REPO  = "autofatture-aruba"
```
Committare la modifica.

## 6. Aggiornamenti — come funziona
- L'app legge la sua versione da `version.py` e interroga
  `GET /repos/OWNER/REPO/releases` (elenco), scegliendo la versione SemVer più
  alta tra le release pubblicate. NB: si usa l'elenco e non `/releases/latest`
  perché quest'ultimo esclude le **prerelease** (le beta): con sole prerelease
  darebbe 404. Le bozze (draft) vengono ignorate.
- Se il `tag_name` della release è più recente, mostra "Nuova versione
  disponibile" e scarica l'asset `.exe` (l'installer) allegato alla release.
- **Repo pubblico (nostra scelta)**: nessun token necessario. Le release si
  scaricano in modo anonimo e l'updater funziona per tutti. Il campo "Token
  GitHub" in Impostazioni → Info resta vuoto e va ignorato (serve solo se un
  domani il repo tornasse privato — cosa che per un'app distribuita non va fatta,
  perché non si deve MAI incorporare un token in un pacchetto distribuito).

## 7. Pubblicare una nuova versione
1. Aggiorna la versione in **`version.py`** (`__version__`) e in
   **`build\installer.iss`** (`MyAppVersion`). Usa SemVer: `1.0.0-beta.2`, poi
   `1.0.0-beta.3`, … fino a `1.0.0` per la finale.
2. Ricompila exe (passo 3) e installer (passo 4).
3. Commit + tag + release con l'installer allegato:
   ```
   git commit -am "v1.0.0-beta.2"
   git tag v1.0.0-beta.2
   git push --tags
   gh release create v1.0.0-beta.2 dist_installer\AutofattureAruba_Setup.exe ^
     --title "v1.0.0-beta.2" --notes "Novità: ..." --prerelease
   ```
4. Le app installate troveranno l'aggiornamento con "Controlla aggiornamenti".

> Suggerimento: il `tag` della release DEVE combaciare con `__version__`
> (con o senza la `v` iniziale è indifferente, il confronto la ignora).

## 8. (Facoltativo, per dopo) Build automatica su GitHub Actions
Quando vorrai, si può aggiungere un workflow che compila exe+installer su un
runner Windows a ogni tag e pubblica la release da solo — così non compili più a
mano. Chiedi e lo predispongo.
