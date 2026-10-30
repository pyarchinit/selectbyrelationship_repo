# Test

Test unitari per l'engine `QgsRelationSelector`
([select_by_relationship_handler.py](../select_by_relationship_handler.py)),
la parte di logica del plugin che non dipende dalla GUI.

I test usano solo `qgis.testing` (incluso in QGIS) — nessuna dipendenza
esterna. Costruiscono due layer in memoria (parent/child), definiscono una
relazione QGIS reale e verificano la propagazione delle selezioni in entrambe
le direzioni, oltre al mapping delle proprietà e al ciclo enable/disable.

Vanno eseguiti **dentro l'ambiente Python di QGIS** (PyQGIS), non con il
`python3` di sistema.

## Linux (QGIS installato dai pacchetti)

```bash
cd /percorso/del/repo
python3 -m unittest tests.test_relation_selector -v
# oppure, se è installato pytest:
python3 -m pytest tests -v
```

## Windows / OSGeo4W

Usare il launcher che configura l'ambiente PyQGIS:

```bat
cd C:\percorso\del\repo
C:\OSGeo4W\bin\python-qgis-ltr.bat -m unittest tests.test_relation_selector -v
```

## WSL con QGIS Windows (OSGeo4W)

Il `python3` di WSL non vede il modulo `qgis`. Copiare `tests/` e
`select_by_relationship_handler.py` in una cartella sul disco Windows
(es. `C:\temp\sbr_test`) ed eseguire:

```bash
cd /mnt/c/temp/sbr_test
cmd.exe /C 'C:\OSGeo4W\bin\python-qgis-ltr.bat -u C:\temp\sbr_test\tests\test_relation_selector.py -v'
```
