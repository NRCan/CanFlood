# -*- coding: utf-8 -*-
"""

This is th efirst call of the tool

"""
"""
TODO: better dependency check

"""
#==============================================================================
# pandas depdendency check
#==============================================================================
msg = 'requires pandas version >=0.25.3 and < 1.0.0'
try:
    import pandas as pd
except:
    from qgis.core import *
    import qgis.utils
    qgis.utils.iface.messageBar().pushMessage('CanFlood', msg, level=Qgis.Critical)
    raise ImportError(msg)
    
if not pd.__version__ >= '0.25.3' and pd.__version__<='1.0.0':
    from qgis.core import *
    import qgis.utils
    qgis.utils.iface.messageBar().pushMessage('CanFlood', msg, level=Qgis.Critical)
    raise ImportError(msg)


#===============================================================================
# add module directory to environemnt
#===============================================================================
import os, sys
file_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(file_dir)



# noinspection PyPep8Naming
def classFactory(iface):  # pylint: disable=invalid-name
    """Load CanFlood_inPrep class from file CanFlood_inPrep.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .canFlood_inPrep import CanFlood
    return CanFlood(iface)
