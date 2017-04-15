# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SelectFromRelation
                                 A QGIS plugin
 tihisi a test
                             -------------------
        begin                : 2017-04-15
        copyright            : (C) 2017 by larosa, fiandaca, borruso
        email                : test@gmail.com
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
    """Load SelectFromRelation class from file SelectFromRelation.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .select_manager import SelectFromRelation
    return SelectFromRelation(iface)
