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


def _make_relation(rel_id, referencing_layer, referenced_layer,
                   referencing_field, referenced_field):
    rel = QgsRelation()
    rel.setId(rel_id)
    rel.setName(rel_id)
    rel.setReferencingLayer(referencing_layer.id())
    rel.setReferencedLayer(referenced_layer.id())
    rel.addFieldPair(referencing_field, referenced_field)
    assert rel.isValid(), "invalid relation: {}".format(rel_id)
    return rel


class TestMultiLevelCascade(unittest.TestCase):
    """Three-level chain  GP <- P <- C  cascading in both directions."""

    def setUp(self):
        self.iface = get_iface()
        self.project = QgsProject.instance()
        self.project.clear()

        self.gp = _make_layer("None?field=pk:integer", "grandparent")
        for pk in (100, 200):
            _add_feature(self.gp, [pk])

        self.p = _make_layer(
            "None?field=pk:integer&field=gp_fk:integer", "parent")
        for pk, gp_fk in ((10, 100), (20, 100), (30, 200)):
            _add_feature(self.p, [pk, gp_fk])

        self.c = _make_layer(
            "None?field=cid:integer&field=p_fk:integer", "child")
        for cid, p_fk in ((1, 10), (2, 20), (3, 30)):
            _add_feature(self.c, [cid, p_fk])

        self.project.addMapLayers([self.gp, self.p, self.c])
        self.project.relationManager().addRelation(
            _make_relation("rel_pc", self.c, self.p, "p_fk", "pk"))
        self.project.relationManager().addRelation(
            _make_relation("rel_gp", self.p, self.gp, "gp_fk", "pk"))

        self.selector = QgsRelationSelector(FakeParent(self.iface))

    def tearDown(self):
        self.selector.disable()
        self.project.clear()

    def _fids(self, layer, field, value):
        return [f.id() for f in layer.getFeatures() if f[field] == value]

    def _vals(self, layer, field):
        return sorted(f[field] for f in layer.selectedFeatures())

    def test_child_cascades_up_two_levels(self):
        self.selector.enable()
        self.selector.setRelations(["rel_pc", "rel_gp"])

        self.c.selectByIds(self._fids(self.c, "cid", 1))  # p_fk=10

        self.assertEqual(self._vals(self.p, "pk"), [10])
        self.assertEqual(self._vals(self.gp, "pk"), [100])

    def test_parent_cascades_down_two_levels(self):
        self.selector.selectChildFromParent = True
        self.selector.enable()
        self.selector.setRelations(["rel_pc", "rel_gp"])

        self.gp.selectByIds(self._fids(self.gp, "pk", 100))

        self.assertEqual(self._vals(self.p, "pk"), [10, 20])
        self.assertEqual(self._vals(self.c, "cid"), [1, 2])

    def test_leaf_selection_does_not_explode_with_bidirectional(self):
        # Regression: with parent->child ON, selecting a single leaf feature
        # must NOT drag in its siblings/cousins via the up-then-down path.
        # That over-selection (here: context pk=20, sibling of pk=10 under
        # the same site) is what froze the UI on real data.
        self.selector.selectChildFromParent = True
        self.selector.enable()
        self.selector.setRelations(["rel_pc", "rel_gp"])

        self.c.selectByIds(self._fids(self.c, "cid", 1))  # ctx pk=10, site 100

        self.assertEqual(self._vals(self.c, "cid"), [1])    # origin untouched
        self.assertEqual(self._vals(self.p, "pk"), [10])    # only its context
        self.assertEqual(self._vals(self.gp, "pk"), [100])  # only its site


class TestManyToMany(unittest.TestCase):
    """Many-to-many  A <- L -> B  through a link/pivot table."""

    def setUp(self):
        self.iface = get_iface()
        self.project = QgsProject.instance()
        self.project.clear()

        self.a = _make_layer("None?field=pk:integer", "a")
        for pk in (1, 2):
            _add_feature(self.a, [pk])

        self.b = _make_layer("None?field=pk:integer", "b")
        for pk in (10, 20):
            _add_feature(self.b, [pk])

        self.link = _make_layer(
            "None?field=a_fk:integer&field=b_fk:integer", "link")
        for a_fk, b_fk in ((1, 10), (1, 20), (2, 20)):
            _add_feature(self.link, [a_fk, b_fk])

        self.project.addMapLayers([self.a, self.b, self.link])
        self.project.relationManager().addRelation(
            _make_relation("rel_la", self.link, self.a, "a_fk", "pk"))
        self.project.relationManager().addRelation(
            _make_relation("rel_lb", self.link, self.b, "b_fk", "pk"))

        self.selector = QgsRelationSelector(FakeParent(self.iface))

    def tearDown(self):
        self.selector.disable()
        self.project.clear()

    def _fids(self, layer, field, value):
        return [f.id() for f in layer.getFeatures() if f[field] == value]

    def _vals(self, layer, field):
        return sorted(f[field] for f in layer.selectedFeatures())

    def test_select_b_from_a_via_link_table(self):
        self.selector.selectChildFromParent = True
        self.selector.enable()
        self.selector.setRelations(["rel_la", "rel_lb"])

        # A pk=1 is linked (via L) to B pk=10 and pk=20
        self.a.selectByIds(self._fids(self.a, "pk", 1))

        self.assertEqual(self._vals(self.b, "pk"), [10, 20])
        # the origin keeps exactly the user selection
        self.assertEqual(self._vals(self.a, "pk"), [1])

    def test_select_b_from_a_single_link(self):
        self.selector.selectChildFromParent = True
        self.selector.enable()
        self.selector.setRelations(["rel_la", "rel_lb"])

        # A pk=2 is linked only to B pk=20
        self.a.selectByIds(self._fids(self.a, "pk", 2))

        self.assertEqual(self._vals(self.b, "pk"), [20])


if __name__ == "__main__":
    unittest.main()
