# Test — rete di sicurezza (Fase 0)

Test di **regressione del motore**: garantisce che la generazione dell'XML non
regredisca tra una fase e l'altra. Deve restare **verde al termine di ogni fase**.

## Cosa verifica
Partendo da dati **fittizi** (azienda e fornitore inventati, definiti dentro il
test — nessun dato reale), genera un'autofattura **TD17** con il motore e controlla:

1. **XML ben formato** — parsing senza errori.
2. **Valido contro lo schema ufficiale SDI** — XSD FatturaPA v1.2.2 (in `xsd/`).
3. **Importi coerenti** — imponibile 100,00 · IVA 22% = 22,00 · totale 122,00.
4. **Confronto campo-per-campo col "golden"** — l'XML atteso è in `golden/TD17_atteso.xml`.

## Come si esegue
Non servono dipendenze extra: usa solo `lxml` (già in `requirements.txt`).

```
python tests/test_regressione.py
```
Esce con codice `0` se tutto è verde, `1` se qualcosa fallisce.

Se hai `pytest` installato (facoltativo), funziona anche:
```
pytest tests/
```

## Aggiornare il golden
Solo quando una modifica **voluta** cambia l'XML (es. una nuova funzione del
motore): rigenera il file atteso e verifica a mano che il nuovo XML sia corretto.
```
python tests/test_regressione.py --update-golden
```

## Contenuto della cartella
- `test_regressione.py` — il test (dati di esempio inclusi).
- `golden/TD17_atteso.xml` — XML atteso per il confronto campo-per-campo.
- `xsd/Schema_FatturaPA_1.2.2.xsd` — schema ufficiale FatturaPA v1.2.2
  (fonte: <https://www.fatturapa.gov.it>), usato per la validazione.
- `xsd/xmldsig-core-schema.xsd` — schema W3C XML-DSig importato dal precedente
  (fonte: <https://www.w3.org/TR/xmldsig-core/>). Il test lo risolve in locale
  senza accessi di rete.
