# -*- coding: utf-8 -*-

"""
***************************************************************************
    settings.py
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

MAIN_DIALOG_CLASS, _ = loadUiType(os.path.abspath(
    os.path.join(os.path.dirname(__file__), 'settings.ui')))


class SettingsDialog(QDialog, MAIN_DIALOG_CLASS):
    def __init__(self, parent=None):
        super(SettingsDialog, self).__init__(parent)
        self.setupUi(self)
