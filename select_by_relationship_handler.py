# -*- coding: utf-8 -*-

"""
***************************************************************************
    select_by_relationship_handler.py
    ---------------------
    Date                 : April 2017
    Copyright            : (C) 2017 by Salvatore Larosa
    Email                : lrssvtml at gmail dot com
***************************************************************************
*                                                                         *
*   This program is free software; you can redistribute it and/or modify  *
*   it under the terms of the GNU General Public License as published by  *
*   the Free Software Foundation; either version 2 of the License, or     *
*   (at your option) any later version.                                   *
*                                                                         *
***************************************************************************
"""

__author__ = 'Salvatore Larosa'
__date__ = 'April 2017'
__copyright__ = '(C) 2017 by Salvatore Larosa'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'


from collections import deque

from qgis.core import Qgis, QgsFeatureRequest, QgsProject, QgsSettings
from qgis.PyQt.QtCore import QObject


class QgsRelationSelector(QObject):
    def __init__(self, parent):
        """
        Class to handle selection between layer relationships

        Usage:
        >>> RS = QgsRelationSelector(parent)
        # switching to parent layer by selecting a row on child layer
        >>> RS.activeParentLayer = True
        # zoom to parent feature by selecting a row on child layer
        >>> RS.zoomParentFeature = True
        # select childs from parent layer
        >>> RS.selectChildFromParent = True
        # to enable selection for relationships
        >>> RS.enable()
        # to disable selection for relationships
        >>> RS.disable()

        You can initializing properties directly from constructor as well
        >>> RS = QgsRelationSelector(parent, activeReferencedLayer=True, zoomReferencedFeature=False)

        :param iface: QgisInterface object
        :param activeReferencedLayer: whether or not activing layer on selection
        :type activeReferencedLayer: bool
        :param zoomReferencedFeature: whether or not zooming layer on selection
        :type zoomReferencedFeature: bool
        """
        super(QgsRelationSelector, self).__init__(parent)
        self.parent = parent
        self.iface = self.parent.iface
        self.s = QgsSettings()

        self.prj = QgsProject.instance()
        self.prj.layersWillBeRemoved.connect(self.disable)

        self.manager = self.prj.relationManager()
        self.manager.changed.connect(self.relationsChanged)

        self.relations = {}
        self.relationsBuffer = {}
        self.relationsChecked = {}

        self.zoomParentFeature = self.s.value('relate/zoomParentFeature', type=bool)
        self.selectChildFromParent = self.s.value('relate/selectChildFromParent', type=bool)
        self.activeParentLayer = self.s.value('relate/activeParentLayer', type=bool)

        self.mc = self.iface.mapCanvas()
        self.disabled = False
        # Guard against signal re-entrancy while we propagate a selection
        # across the relation graph (our own selectByIds calls re-emit
        # selectionChanged synchronously).
        self._propagating = False

    @property
    def selectChildFromParent(self):
        return self.childFromParentSelection

    @selectChildFromParent.setter
    def selectChildFromParent(self, value):
        self.childFromParentSelection = value

    @property
    def activeParentLayer(self):
        return self.activeReferencedLayerOnSelection

    @activeParentLayer.setter
    def activeParentLayer(self, value):
        self.activeReferencedLayerOnSelection = value

    @property
    def zoomParentFeature(self):
        return self.zoomToReferencedLayerSelection

    @zoomParentFeature.setter
    def zoomParentFeature(self, value):
        self.zoomToReferencedLayerSelection = value

    def enable(self):
        if len(self.manager.relations()) == 0:
            self.iface.messageBar().pushMessage(
                "No relationship set in Project properties", Qgis.MessageLevel.Warning)
            return False
        self.disabled = False
        return True

    def disable(self):
        self.disconnectRelations()
        try:
            self.manager.changed.disconnect(self.relationsChanged)
        except (TypeError, RuntimeError):
            pass
        try:
            self.prj.layersWillBeRemoved.disconnect(self.disable)
        except (TypeError, RuntimeError):
            pass
        self.disabled = True
        self.parent.buttonToggled.emit(False)

    def setRelations(self, relations):
        self.disconnectRelations()
        if not relations:
            self.relations = self.relationsBuffer = {}
            self.relationsChecked = {}
            return

        self.relationsChecked = {rel: self.manager.relations()[rel] for rel in relations}

        self.relations = self.relationsBuffer = self.relationsChecked
        self.connectRelations()

    def relationsChanged(self):
        if len(self.relationsBuffer) != len(self.relations):
            self.disconnectRelations()
            self.relations = self.manager.relations()
            self.relationsBuffer = self.relations
        else:
            self.disconnectRelations()
        self.connectRelations()

    def participatingLayers(self):
        """All distinct layers touched by the active relations, keyed by id."""
        layers = {}
        for rl in self.relations.values():
            for layer in (rl.referencingLayer(), rl.referencedLayer()):
                if layer is not None:
                    layers[layer.id()] = layer
        return layers

    def connectRelations(self):
        for layer in self.participatingLayers().values():
            # Disconnect first to avoid duplicate connections (which would
            # otherwise fire propagateSelection more than once per change).
            try:
                layer.selectionChanged.disconnect(self.propagateSelection)
            except (TypeError, RuntimeError):
                pass
            layer.selectionChanged.connect(self.propagateSelection)

    def disconnectRelations(self):
        for layer in self.participatingLayers().values():
            try:
                layer.selectionChanged.disconnect(self.propagateSelection)
            except (TypeError, RuntimeError):
                pass

    def propagateSelection(self, *args):
        """Cascade the selection of the sender layer across the whole graph
        of active relations (multi-level, and bidirectional when
        ``selectChildFromParent`` is on)."""
        if self._propagating:
            return
        origin = self.sender()
        if origin is None or not self.relations:
            return

        self._propagating = True
        try:
            layers = self.participatingLayers()
            selection = self._computeClosure(origin, layers)
            for lid, layer in layers.items():
                if layer is origin:
                    continue
                target = selection.get(lid, set())
                # Idempotent: only touch a layer whose selection actually
                # changes. This stops the cascade from re-emitting redundant
                # selectionChanged signals and makes it converge to a fixed
                # point, so it cannot loop or thrash even if something
                # re-triggers us (e.g. a stale selector still connected).
                if set(layer.selectedFeatureIds()) != target:
                    layer.selectByIds(list(target))
            self._applyZoomAndActivate(origin, selection)
        finally:
            self._propagating = False

    def _computeClosure(self, origin, layers):
        """Breadth-first traversal of the relation graph.

        Each layer is *expanded* (used to derive further selections) at most
        once, so the traversal always terminates even on cyclic relation
        graphs and many-to-many setups (parent ─ link table ─ parent). Ids
        are accumulated as a union, which keeps diamond topologies correct.
        """
        selection = {origin.id(): set(origin.selectedFeatureIds())}
        queue = deque([origin])
        expanded = set()

        while queue:
            layer = queue.popleft()
            lid = layer.id()
            if lid in expanded:
                continue
            expanded.add(lid)
            ids = selection.get(lid, set())
            if not ids:
                continue

            for rl in self.relations.values():
                child = rl.referencingLayer()
                parent = rl.referencedLayer()
                if child is None or parent is None:
                    continue
                # child -> parent (always)
                if child.id() == lid:
                    self._merge(selection, parent,
                                self._parentIds(rl, child, ids),
                                queue, expanded, layers)
                # parent -> child (opt-in)
                if self.childFromParentSelection and parent.id() == lid:
                    self._merge(selection, child,
                                self._childIds(rl, parent, ids),
                                queue, expanded, layers)
        return selection

    @staticmethod
    def _merge(selection, layer, derived, queue, expanded, layers):
        if not derived:
            return
        lid = layer.id()
        selection.setdefault(lid, set()).update(derived)
        layers.setdefault(lid, layer)
        if lid not in expanded:
            queue.append(layer)

    @staticmethod
    def _parentIds(relation, child_layer, ids):
        request = QgsFeatureRequest().setFilterFids(list(ids))
        result = set()
        for feature in child_layer.getFeatures(request):
            referenced = relation.getReferencedFeature(feature)
            if referenced.isValid():
                result.add(referenced.id())
        return result

    @staticmethod
    def _childIds(relation, parent_layer, ids):
        request = QgsFeatureRequest().setFilterFids(list(ids))
        result = set()
        for feature in parent_layer.getFeatures(request):
            for related in relation.getRelatedFeatures(feature):
                result.add(related.id())
        return result

    def _applyZoomAndActivate(self, origin, selection):
        """Preserve the original single-hop behaviour: when a child layer is
        the origin of the selection, optionally activate and/or zoom to its
        directly referenced (parent) layer."""
        if not (self.zoomToReferencedLayerSelection
                or self.activeReferencedLayerOnSelection):
            return
        for rl in self.relations.values():
            if rl.referencingLayer() is origin:
                referenced = rl.referencedLayer()
                if referenced is None or not selection.get(referenced.id()):
                    continue
                if self.activeReferencedLayerOnSelection:
                    self.iface.setActiveLayer(referenced)
                if self.zoomToReferencedLayerSelection:
                    self.mc.zoomToSelected(referenced)
