# -*- coding: utf-8 -*-

"""
***************************************************************************
    relation_selector_handler.py
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

from PyQt4.QtCore import QObject
from qgis.core import QgsFeatureRequest, QgsProject


class QgsRelationSelector(QObject):
    def __init__(self, iface, activeReferencedLayer=False, zoomReferencedFeature=False):
        """
        Class to handle selection between layer relationships

        Usage:
        >>> RS = QgsRelationSelector(iface)
        # switching to parent layer by selecting a row on child layer
        >>> RS.activeParentLayer = True
        # zoom to parent feature by selecting a row on child layer
        >>> RS.zoomParentFeature = True
        # select childs from parent layer
        >>> RS.selectChildFromParent = True
        # to enable selection for relationships
        >>> RS.active()
        # to disable selection for relationships
        >>> RS.deactive()

        You can initializing properties directly from constructor as well
        >>> RS = QgsRelationSelector(iface, activeReferencedLayer=True, zoomReferencedFeature=False)

        :param iface: QgisInterface object
        :param activeReferencedLayer: whether or not activing layer on selection
        :type activeReferencedLayer: bool
        :param zoomReferencedFeature: whether or not zooming layer on selection
        :type zoomReferencedFeature: bool
        """
        super(QgsRelationSelector, self).__init__(iface)
        self.iface = iface

        self.manager = QgsProject.instance().relationManager()
        self.manager.changed.connect(self.relationsChanged)

        self.relations = self.manager.relations()
        self.relationsBuffer = self.relationsBackup = self.relations

        self.activeParentLayer = activeReferencedLayer
        self.zoomParentFeature = zoomReferencedFeature
        self.selectChildFromParent = False

        self.mc = self.iface.mapCanvas()

    def active(self):
        if len(self.relations) == 0:
            self.iface.messageBar().pushMessage("No relationship set in Project properties", 1)
            return False
        self.connectChildRelations()
        return True

    def deactive(self):
        self.disconnectRelations()
        if self.manager:
            self.manager.changed.disconnect(self.relationsChanged)
        self.deleteLater()

    def clear(self):
        self.manager.clear()

    @property
    def selectChildFromParent(self):
        return self.childFromParentSelection

    @selectChildFromParent.setter
    def selectChildFromParent(self, value):
        self.childFromParentSelection = value
        if len(self.relations) != 0:
            self.connectParentRelations()

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

    def relationsChanged(self):
        self.iface.messageBar().pushMessage('changed', 0)
        if len(self.relationsBuffer) >= len(self.relations):
            self.disconnectRelations()
            self.relations = self.manager.relations()
            self.relationsBuffer = self.relations
        self.connectChildRelations()
        if self.childFromParentSelection:
            self.connectParentRelations()

    def connectParentRelations(self):
        for _, rl in self.relations.iteritems():
            referencedLayer = rl.referencedLayer()
            if self.childFromParentSelection:
                referencedLayer.selectionChanged.connect(self.selectChildsFromParent)
            else:
                try:
                    referencedLayer.selectionChanged.disconnect(self.selectChildsFromParent)
                except:
                    pass

    def connectChildRelations(self):
        for _, rl in self.relations.iteritems():
            referencingLayer = rl.referencingLayer()
            referencingLayer.selectionChanged.connect(self.selectParentFromChilds)

    def disconnectRelations(self):
        for _, rl in self.relations.iteritems():
            referencedLayer = rl.referencedLayer()
            referencingLayer = rl.referencingLayer()
            try:
                if self.childFromParentSelection:
                    referencedLayer.selectionChanged.disconnect(self.selectChildsFromParent)
                referencingLayer.selectionChanged.disconnect(self.selectParentFromChilds)
            except:
                pass

    def selectParentFromChilds(self, fids):
        rl = self.manager.referencingRelations(self.sender())[0]

        referencingLayer = rl.referencingLayer()
        referencedLayer = rl.referencedLayer()

        request = QgsFeatureRequest().setFilterFids(fids)
        it = referencingLayer.getFeatures(request)
        parentIds = [rl.getReferencedFeature(i).id() for i in it]

        referencingLayer.blockSignals(True)
        referencedLayer.setSelectedFeatures(parentIds)
        referencingLayer.blockSignals(False)

        if self.activeReferencedLayerOnSelection:
            iface.setActiveLayer(referencedLayer)

        if self.zoomToReferencedLayerSelection:
            self.mc.zoomToSelected(referencedLayer)

        referencedLayer.triggerRepaint()
        referencingLayer.triggerRepaint()

    def selectChildsFromParent(self, fids):
        rls = self.manager.referencedRelations(self.sender())
        for rl in rls:
            referencingLayer = rl.referencingLayer()
            referencedLayer = rl.referencedLayer()

            request = QgsFeatureRequest().setFilterFids(fids)
            f = next(referencedLayer.getFeatures(request))
            it = rl.getRelatedFeatures(f)
            childIds = [i.id() for i in it]

            referencedLayer.blockSignals(True)
            referencingLayer.setSelectedFeatures(childIds)
            referencedLayer.blockSignals(False)

            referencedLayer.triggerRepaint()
            referencingLayer.triggerRepaint()
