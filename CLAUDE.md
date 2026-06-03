# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A QGIS desktop plugin ("Select by relationship", category Database, `qgisMinimumVersion=3.16`). On a single button click it cascades feature selections across vector layers that are tied together by **relations defined in the QGIS project** (one-to-one or one-to-many). Selecting child rows selects the parent feature(s); optionally selecting parent features selects the related children.

There is no build or lint tooling — the repo *is* the deployable plugin. QGIS loads it directly. Unit tests for the GUI-free engine live in [tests/](tests/) and run inside the QGIS Python environment (see [tests/README.md](tests/README.md)).

## Running / developing

- Deploy by symlinking or copying the repo into the QGIS plugins directory, then enable it in Plugin Manager. The folder name must match the package import (`select_by_relationship_plugin`, etc.):
  - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
  - The plugin appears in the QGIS **Database** menu and adds a 3-widget toolbar.
- After editing code, reload via the *Plugin Reloader* plugin or restart QGIS. There is no hot reload.
- Manual testing inside QGIS: load layers, define relations in **Project ▸ Properties ▸ Relations**, then toggle the plugin and pick relations from the combo box. Automated engine tests: `python3 -m unittest tests.test_relation_selector -v` (run with the QGIS Python; on WSL+OSGeo4W use `python-qgis-ltr.bat`, see [tests/README.md](tests/README.md)).
- Bump `version=` in [metadata.txt](metadata.txt) for releases; `experimental=True` is currently set there.

## Architecture

Three modules, loaded via [`__init__.py`](__init__.py)'s `classFactory` (QGIS entry point):

- [select_by_relationship_plugin.py](select_by_relationship_plugin.py) — `SelectByRelationship`, the GUI/controller. Builds the toolbar (toggle action, a custom `CheckableComboBox` of relation IDs, settings action), wires QGIS signals, and owns the lifecycle (`initGui`/`unload`/`run`). Toggling the main action constructs a fresh `QgsRelationSelector` each time. `CheckableComboBox` + `CheckBoxDelegate` are custom Qt widgets enabling multi-select of relations with a "N relationship(s) selected" label.
- [select_by_relationship_handler.py](select_by_relationship_handler.py) — `QgsRelationSelector`, the engine. Holds **no GUI**. It connects to `selectionChanged` on the relation's referencing (child) and referenced (parent) layers and propagates selections:
  - `selectParentFromChilds` — child selection → select referenced parent features (always active when enabled).
  - `selectChildsFromParent` — parent selection → select referencing child features (only when `selectChildFromParent` setting is on).
  - Uses `blockSignals` to prevent feedback loops between the two directions.
- [select_by_relationship_settings.py](select_by_relationship_settings.py) — `SettingsDialog`, a `QDialog` loaded from [settings.ui](settings.ui) via `loadUiType`. Three checkboxes persisted in `QgsSettings` under the `relate/` prefix: `zoomParentFeature`, `selectChildFromParent`, `activeParentLayer`.

### Key flow & state

- Settings live in `QgsSettings` (`relate/...`). The dialog writes them on `accept()`, then calls `plugin.updateSettings()`, which copies them onto the live `QgsRelationSelector` and re-applies relations.
- The selector tracks which relations are active in `relations` / `relationsChecked`, keyed by QGIS relation ID. `setRelations()` (driven by the combo box checkboxes) disconnects everything, then reconnects only the chosen relations.
- `relationManager().changed` (relations added/removed in the project) repopulates the combo box; `newProjectCreated` and `layersWillBeRemoved` reset/disable to avoid dangling connections.
- The plugin↔selector boundary uses the `buttonToggled(bool)` Qt signal so the engine can force the UI button off (e.g. when no relations exist).

## Conventions

- Qt is imported through the `qgis.PyQt` shim (`qgis.PyQt.QtWidgets`, etc.), not PyQt5 directly — keep this for QGIS compatibility.
- "Parent" in this codebase = the *referenced* layer; "child" = the *referencing* layer. Properties expose friendly names (`zoomParentFeature`, `activeParentLayer`) that map to QGIS terms (`zoomToReferencedLayerSelection`, `activeReferencedLayerOnSelection`).
- GPL v2-or-later; preserve the license header blocks on existing files.
