# -*- coding: utf-8 -*-

"""
***************************************************************************
    test_relation_selector.py
    ---------------------
    Unit tests for the QgsRelationSelector engine (no GUI).

    Run inside the QGIS Python environment, e.g.:
        python-qgis-ltr.bat -m pytest tests            (OSGeo4W / Windows)
        python3 -m pytest tests                        (Linux QGIS)
    or directly:
        python3 -m unittest tests.test_relation_selector
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

import os
import sys

from qgis.core import (
    QgsFeature,
    QgsProject,
    QgsRelation,
    QgsVectorLayer,
)
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.testing import start_app, unittest
from qgis.testing.mocked import get_iface

# Make the plugin package importable when tests are run from the repo root.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from select_by_relationship_handler import QgsRelationSelector  # noqa: E402

QGISAPP = start_app()


class FakeParent(QObject):
    """Minimal stand-in for the SelectByRelationship plugin/controller.

    QgsRelationSelector only needs ``iface`` and a ``buttonToggled`` signal
    from its parent.
    """

    buttonToggled = pyqtSignal(bool)

    def __init__(self, iface):
        super().__init__()
        self.iface = iface


def _make_layer(definition, name):
    layer = QgsVectorLayer(definition, name, "memory")
    assert layer.isValid(), "invalid memory layer: {}".format(name)
    return layer


def _add_feature(layer, attributes):
    feat = QgsFeature(layer.fields())
    feat.setAttributes(attributes)
    ok, _ = layer.dataProvider().addFeatures([feat])
    assert ok
    layer.updateExtents()


class TestQgsRelationSelector(unittest.TestCase):
    def setUp(self):
        self.iface = get_iface()
        self.project = QgsProject.instance()
        self.project.clear()

        # Parent (referenced) layer: pk
        self.parent_layer = _make_layer(
            "Point?crs=EPSG:4326&field=pk:integer", "parent")
        _add_feature(self.parent_layer, [10])
        _add_feature(self.parent_layer, [20])

        # Child (referencing) layer: cid, fk -> parent.pk
        self.child_layer = _make_layer(
            "Point?crs=EPSG:4326&field=cid:integer&field=fk:integer", "child")
        _add_feature(self.child_layer, [1, 10])
        _add_feature(self.child_layer, [2, 10])
        _add_feature(self.child_layer, [3, 20])

        self.project.addMapLayers([self.parent_layer, self.child_layer])

        rel = QgsRelation()
        rel.setId("rel1")
        rel.setName("rel1")
        rel.setReferencingLayer(self.child_layer.id())
        rel.setReferencedLayer(self.parent_layer.id())
        rel.addFieldPair("fk", "pk")
        self.assertTrue(rel.isValid())
        self.project.relationManager().addRelation(rel)

        self.fake_parent = FakeParent(self.iface)
        self.selector = QgsRelationSelector(self.fake_parent)

    def tearDown(self):
        self.selector.disable()
        self.project.clear()

    # ---- property mapping (friendly name -> QGIS term) --------------------

    def test_property_mappings(self):
        self.selector.zoomParentFeature = True
        self.selector.activeParentLayer = True
        self.selector.selectChildFromParent = True
        self.assertTrue(self.selector.zoomToReferencedLayerSelection)
        self.assertTrue(self.selector.activeReferencedLayerOnSelection)
        self.assertTrue(self.selector.childFromParentSelection)

        self.selector.zoomParentFeature = False
        self.assertFalse(self.selector.zoomToReferencedLayerSelection)

    # ---- enable / disable -------------------------------------------------

    def test_enable_with_relations(self):
        self.assertTrue(self.selector.enable())
        self.assertFalse(self.selector.disabled)

    def test_enable_without_relations_returns_false(self):
        self.project.relationManager().setRelations([])
        self.assertFalse(self.selector.enable())

    def test_disable_emits_button_toggled_false(self):
        received = []
        self.fake_parent.buttonToggled.connect(received.append)
        self.selector.disable()
        self.assertTrue(self.selector.disabled)
        self.assertEqual(received, [False])

    # ---- child -> parent propagation --------------------------------------

    def _pk_of_selected_parents(self):
        return sorted(f["pk"] for f in self.parent_layer.selectedFeatures())

    def _fk_of_selected_children(self):
        return sorted(f["fk"] for f in self.child_layer.selectedFeatures())

    def test_select_parent_from_childs(self):
        self.selector.enable()
        self.selector.setRelations(["rel1"])

        # Select the two children whose fk == 10
        child_ids = [f.id() for f in self.child_layer.getFeatures()
                     if f["fk"] == 10]
        self.child_layer.selectByIds(child_ids)

        self.assertEqual(self._pk_of_selected_parents(), [10])

    def test_select_parent_from_childs_multiple_parents(self):
        self.selector.enable()
        self.selector.setRelations(["rel1"])

        all_child_ids = [f.id() for f in self.child_layer.getFeatures()]
        self.child_layer.selectByIds(all_child_ids)

        self.assertEqual(self._pk_of_selected_parents(), [10, 20])

    # ---- parent -> child propagation (only when enabled) ------------------

    def test_select_childs_from_parent(self):
        self.selector.selectChildFromParent = True
        self.selector.enable()
        self.selector.setRelations(["rel1"])

        parent_id = [f.id() for f in self.parent_layer.getFeatures()
                     if f["pk"] == 20][0]
        self.parent_layer.selectByIds([parent_id])

        self.assertEqual(self._fk_of_selected_children(), [20])

    def test_parent_selection_ignored_when_disabled(self):
        # selectChildFromParent stays False -> selecting a parent must NOT
        # cascade to children.
        self.selector.selectChildFromParent = False
        self.selector.enable()
        self.selector.setRelations(["rel1"])

        parent_id = [f.id() for f in self.parent_layer.getFeatures()
                     if f["pk"] == 20][0]
        self.parent_layer.selectByIds([parent_id])

        self.assertEqual(self._fk_of_selected_children(), [])


if __name__ == "__main__":
    unittest.main()
