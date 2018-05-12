# -*- coding: utf-8 -*-

"""
***************************************************************************
    select_by_relationship_settings.py
    ---------------------
    Date                 : May 2018
    Copyright            : (C) 2018 by Salvatore Larosa
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
__date__ = 'May 2018'
__copyright__ = '(C) 2018 by Salvatore Larosa'

# This will get replaced with a git SHA1 when you do a git archive

__revision__ = '$Format:%H$'

import os

from qgis.PyQt.QtWidgets import QDialog
from qgis.PyQt.uic import loadUiType
from qgis.core import QgsSettings

from .select_by_relationship_handler import QgsRelationSelector

MAIN_DIALOG_CLASS, _ = loadUiType(os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'settings.ui')))


class SettingsDialog(QDialog, MAIN_DIALOG_CLASS):
    def __init__(self, dlg, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)
        self.parent = parent
        self.dlg = dlg
        self.s = QgsSettings()

        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.chkActiveParent.setChecked(self.s.value('relate/activeParentLayer', False, type=bool))
        self.chkZoomParent.setChecked(self.s.value('relate/zoomParentFeature', False, type=bool))
        self.chkSelectParent.setChecked(self.s.value('relate/selectChildFromParent', False, type=bool))

    def setZoomToParent(self, checkstate):
        if checkstate:
            enable = True
        else:
            enable = False

        print(enable)
        self.sFr.zoomParentFeature = enable

    def accept(self):
        self.s.setValue('relate/activeParentLayer', self.chkActiveParent.isChecked())
        self.s.setValue('relate/zoomParentFeature', self.chkZoomParent.isChecked())
        self.s.setValue('relate/selectChildFromParent', self.chkSelectParent.isChecked())

        self.dlg.updateSettings()

        super(SettingsDialog, self).accept()

