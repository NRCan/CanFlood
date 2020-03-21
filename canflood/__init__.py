# -*- coding: utf-8 -*-
"""

This is th efirst call of the tool

"""
"""
TODO: better dependency check

"""
#==============================================================================
# dependency check
#==============================================================================
# Let users know if they're missing any of our hard dependencies
hard_dependencies = ("pandas",)
missing_dependencies = []

for dependency in hard_dependencies:
    try:
        __import__(dependency)
    except ImportError as e:
        missing_dependencies.append("{0}: {1}".format(dependency, str(e)))

if missing_dependencies:
    raise ImportError(
        "Unable to import required dependencies:\n" + "\n".join(missing_dependencies)
    )
    
del hard_dependencies, dependency, missing_dependencies


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

    from .CanFlood import CanFlood
    return CanFlood(iface)
