# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SelectByRelationship

 The plugin allows to select records through tables based on relationships
 one-to-one or one-to-many specified inside a Qgis project.
                             -------------------
        begin                : 2017-04-20
        copyright            : (C) 2017 by Luca Mandolesi
        email                : pyarchinit@gmail.com
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load SelectByRelationship class from file SelectByRelationship.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .select_by_relationship_plugin import SelectByRelationship
    return SelectByRelationship(iface)
