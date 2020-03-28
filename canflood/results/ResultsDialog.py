# -*- coding: utf-8 -*-
"""


"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

#==============================================================================
# custom imports
#==============================================================================

import hlpr.plug


from hlpr.Q import *
from hlpr.basic import *




# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'results.ui')
assert os.path.exists(ui_fp)
FORM_CLASS, _ = uic.loadUiType(ui_fp)


class Results_Dialog(QtWidgets.QDialog, FORM_CLASS, hlpr.plug.QprojPlug):
    def __init__(self, iface, parent=None):

        super(Results_Dialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        #custom setup
        self.iface = iface
        self.qproj_setup()
        self.connect_slots()
        
        
    def connect_slots(self): #connect your slots
        log = self.logger.getChild('connect_slots')
        
        
        log.info('finished')
        
    def join_geo(self):
        pass
