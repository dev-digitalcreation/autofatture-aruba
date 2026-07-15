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
Non servono dipendenze extra: usa solo `lxml` (già in `requirements.txt`) e la
libreria standard.

```
python tests/test_regressione.py     # motore + XSD + golden (rete di sicurezza, Fase 0)
python tests/test_archivio.py         # archivio SQLite: duplicati, numerazione, registro IVA (Fase 1)
python tests/test_validazione.py      # validazione XSD: accetta valido, rifiuta non conforme (Fase 1)
```
Ognuno esce con codice `0` se verde, `1` se qualcosa fallisce.

Se hai `pytest` installato (facoltativo), li esegue tutti insieme:
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

Gli schemi XSD stanno in `../schema/` (a livello di progetto, così vengono
inclusi anche nell'exe) e la validazione usa il modulo runtime `validazione.py`
— quindi il test valida con lo **stesso** codice usato dall'app:
- `schema/Schema_FatturaPA_1.2.2.xsd` — schema ufficiale FatturaPA v1.2.2
  (fonte: <https://www.fatturapa.gov.it>).
- `schema/xmldsig-core-schema.xsd` — schema W3C XML-DSig importato dal precedente
  (fonte: <https://www.w3.org/TR/xmldsig-core/>), risolto in locale senza rete.
