# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SelectByRelationship

 The plugin allows to select records through tables based on relationships
 one-to-one or one-to-many specified inside a Qgis project.
                              -------------------
        begin                : 2017-04-20
        git sha              : $Format:%H$
        copyright            : (C) 2017 by Luca Mandolesi
        email                : pyarchinit@gmail.com
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import os.path

from qgis.PyQt.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, pyqtSlot, pyqtSignal, QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction

from .select_by_relationship_handler import QgsRelationSelector
from .select_by_relationship_settings import SettingsDialog


class SelectByRelationship(QObject):
    """QGIS Plugin Implementation."""
    buttonToggled = pyqtSignal(bool)

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        super(SelectByRelationship, self).__init__(iface)
        self.iface = iface

        self.actions = []
        self.menu = self.tr(u'&Select by relationship')
        self.toolbar = self.iface.addToolBar(u'SelectByRelationship')
        self.toolbar.setObjectName(u'SelectByRelationship')

        self.sFr = None
        self.buttonToggled.connect(self.toggleButton)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            checkable=False,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        # Create the dialog (after translation) and keep reference
        # self.dlg = SelectByRelationshipDialog()

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        if checkable:
            action.toggled.connect(callback)
        else:
            action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_plugin = '{}{}'.format(os.path.dirname(__file__), os.path.join(os.sep, 'images', 'icon.svg'))
        self.actionRelations = self.add_action(
            icon_plugin,
            text=self.tr(u'Allows selections by relationship'),
            checkable=True,
            callback=self.run,
            parent=self.iface.mainWindow())

        icon_settings = '{}{}'.format(os.path.dirname(__file__), os.path.join(os.sep, 'images', 'settings.svg'))
        self.actionSettings = self.add_action(
            icon_settings,
            text=self.tr(u'Settings relationship'),
            checkable=False,
            callback=self.showSettings,
            parent=self.iface.mainWindow())

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginDatabaseMenu(
                self.tr(u'&Select by relationship'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    @pyqtSlot(bool)
    def toggleButton(self, toggled):
        self.actionRelations.setChecked(toggled)

    def run(self, toggle):
        """Run method that performs all the real work"""
        # self.debug_trace()
        if toggle:
            self.sFr = QgsRelationSelector(self)
            ok = self.sFr.enable()
            if not ok:
                self.buttonToggled.emit(False)
        else:
            if self.sFr:
                self.sFr.disable()

    def showSettings(self):
        rsettings = SettingsDialog(self, self.iface.mainWindow())
        rsettings.show()
        rsettings.raise_()

    def debug_trace(self):
        """Set a tracepoint in the Python debugger that works with Qt"""

        from PyQt5.QtCore import pyqtRemoveInputHook
        from pdb import set_trace
        pyqtRemoveInputHook()
        set_trace()
