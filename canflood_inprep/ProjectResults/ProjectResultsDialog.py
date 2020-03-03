# -*- coding: utf-8 -*-
"""


"""

import os

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

#==============================================================================
# custom imports
#==============================================================================

#import canflood_inprep.prep.wsamp
from prep.wsamp import WSLSampler
from prep.lisamp import LikeSampler
#from canFlood_model import CanFlood_Model
import hp
import hlpr.plug
from hp import Error



# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ProjectResultsDialog_Base.ui'))


class Results_Dialog(QtWidgets.QDialog, FORM_CLASS, hlpr.plug.QprojPlug):
    def __init__(self, parent=None):
        """Constructor."""
        super(Results_Dialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
