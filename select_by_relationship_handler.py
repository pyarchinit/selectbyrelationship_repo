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


from qgis.core import QgsFeatureRequest, QgsProject, QgsSettings
from qgis.PyQt.QtCore import pyqtSlot, pyqtSignal, QObject


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
        self.relationsBuffer = self.relationsBackup = {}
        self.relationsChecked = {}

        self.zoomParentFeature = self.s.value('relate/zoomParentFeature', type=bool)
        self.selectChildFromParent = self.s.value('relate/selectChildFromParent', type=bool)
        self.activeParentLayer = self.s.value('relate/activeParentLayer', type=bool)

        self.mc = self.iface.mapCanvas()
        self.disabled = False

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
            self.iface.messageBar().pushMessage("No relationship set in Project properties", 1)
            return False
        # self.connectChildRelations()
        # if self.childFromParentSelection:
        #     self.connectParentRelations()
        # self.manager.changed.connect(self.relationsChanged)
        self.disabled = False
        return True

    def disable(self):
        self.disconnectRelations()
        try:
            self.manager.changed.disconnect(self.relationsChanged)
        except:
            pass
        self.disabled = True
        self.parent.buttonToggled.emit(False)

    def clear(self):
        self.manager.clear()

    def setRelations(self, relations):
        self.disconnectRelations()
        if not relations:
            return

        self.relationsChecked = {rel: self.manager.relations()[rel] for rel in relations}

        self.relations = self.relationsBuffer = self.relationsChecked
        self.connectChildRelations()
        if self.childFromParentSelection:
            self.connectParentRelations()

    def relationsChanged(self):
        if len(self.relationsBuffer) != len(self.relations):
            self.disconnectRelations()
            self.relations = self.manager.relations()
            self.relationsBuffer = self.relations
        self.connectChildRelations()
        if self.childFromParentSelection:
            self.connectParentRelations()

    def connectParentRelations(self):
        for _, rl in self.relations.items():
            referencedLayer = rl.referencedLayer()
            if self.childFromParentSelection:
                referencedLayer.selectionChanged.connect(self.selectChildsFromParent)
            else:
                try:
                    referencedLayer.selectionChanged.disconnect(self.selectChildsFromParent)
                except:
                    pass

    def connectChildRelations(self):
        for _, rl in self.relations.items():
            referencingLayer = rl.referencingLayer()
            referencingLayer.selectionChanged.connect(self.selectParentFromChilds)

    def disconnectRelations(self):
        for _, rl in self.relations.items():
            referencedLayer = rl.referencedLayer()
            referencingLayer = rl.referencingLayer()
            try:
                referencingLayer.selectionChanged.disconnect(self.selectParentFromChilds)
                if self.childFromParentSelection:
                    referencedLayer.selectionChanged.disconnect(self.selectChildsFromParent)
            except:
                pass

    def selectParentFromChilds(self, fids):
        rls = self.manager.referencingRelations(self.sender())
        for rl in rls:
            if rl.name() in self.relations.keys():
                referencingLayer = rl.referencingLayer()
                referencedLayer = rl.referencedLayer()

                request = QgsFeatureRequest().setFilterFids(fids)
                it = referencingLayer.getFeatures(request)
                parentIds = [rl.getReferencedFeature(i).id() for i in it]

                referencingLayer.blockSignals(True)
                referencedLayer.selectByIds(parentIds)
                referencingLayer.blockSignals(False)

                if self.activeReferencedLayerOnSelection:
                    self.iface.setActiveLayer(referencedLayer)

                if self.zoomToReferencedLayerSelection:
                    self.mc.zoomToSelected(referencedLayer)

                # referencedLayer.triggerRepaint()
                # referencingLayer.triggerRepaint()

    def selectChildsFromParent(self, fids):
        rls = self.manager.referencedRelations(self.sender())
        for rl in rls:
            if rl.name() in self.relations.keys():
                referencingLayer = rl.referencingLayer()
                referencedLayer = rl.referencedLayer()

                request = QgsFeatureRequest().setFilterFids(fids)
                fit = referencedLayer.getFeatures(request)
                childIds = []
                for f in fit:
                    it = rl.getRelatedFeatures(f)
                    childIds.extend([i.id() for i in it])

                referencedLayer.blockSignals(True)
                referencingLayer.selectByIds(childIds)
                referencedLayer.blockSignals(False)

                # referencedLayer.triggerRepaint()
                # referencingLayer.triggerRepaint()
