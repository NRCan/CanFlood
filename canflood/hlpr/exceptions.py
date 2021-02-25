'''
Created on May 18, 2019

@author: cef

custom exceptions and errors
'''



class QError(Exception): #errors for qgis plugins

    def __init__(self, msg):

        from qgis.utils import iface
        
        try:
            from qgis.core import QgsMessageLog, Qgis, QgsLogger
            iface.messageBar().pushMessage("Error", msg, level=Qgis.Critical)
            QgsMessageLog.logMessage(msg,'CanFlood', level=Qgis.Critical)
            QgsLogger.debug('ERROR_%s'%msg) #also send to file
        except:
            Error(msg)

class Error(Exception):

    def __init__(self, msg):
        import logging
        mod_logger = logging.getLogger('exceptions') #creates a child logger of the root

        mod_logger.error(msg)
