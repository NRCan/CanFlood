'''
Created on May 18, 2019

@author: cef

custom exceptions and errors
'''

from qgis.core import QgsMessageLog, Qgis

class QError(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, msg):
        from qgis.utils import iface
        
        try:
            iface.messageBar().pushMessage("Error", msg, level=Qgis.Critical)
            QgsMessageLog.logMessage(msg,'CanFlood', level=Qgis.Critical)
        except:
            Error(msg)

class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, msg):
        import logging
        mod_logger = logging.getLogger('exceptions') #creates a child logger of the root

        mod_logger.error(msg)
