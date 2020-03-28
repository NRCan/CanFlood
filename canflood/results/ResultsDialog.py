# -*- coding: utf-8 -*-
"""


"""

import os

#===============================================================================
# PyQT
#===============================================================================

from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem


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
        
        #=======================================================================
        # general----------------
        #=======================================================================
        #ok/cancel buttons
        self.buttonBox.accepted.connect(self.reject)
        self.buttonBox.rejected.connect(self.reject)
        
        #status label
        self.logger.statusQlab=self.progressText
        self.logger.statusQlab.setText('BuildDialog initialized')
        
        
        #=======================================================================
        # setup------------
        #=======================================================================
        #Working Directory browse
        def browse_wd():
            return self.browse_button(self.lineEdit_wd, prompt='Select Working Directory',
                                      qfd = QFileDialog.getExistingDirectory)
            
        self.pushButton_wd.clicked.connect(browse_wd) # SS. Working Dir. Browse
        
        #=======================================================================
        # Join Geometry------------
        #=======================================================================
        """
        comboBox_JGfinv
        mFieldComboBox_JGfinv
        
        
        lineEdit_JG_resfp
        pushButton_JG_resfp_br
        
        pushButton_JG_join
        
        
        """
        #vector geometry layer
        self.comboBox_JGfinv.setFilters(QgsMapLayerProxyModel.VectorLayer) 
        
        def upd_cid(): #change the 'cid' display when the finv selection changes
            return self.mfcb_connect(
                self.mFieldComboBox_JGfinv, self.comboBox_JGfinv.currentLayer(),
                fn_str = 'xid' )
        
        self.comboBox_JGfinv.layerChanged.connect(upd_cid)
        
        
        #data file browse
        def browse_jg():
            return self.fileSelect_button(self.lineEdit_JG_resfp, caption='Select Data File',
                                      qfd = QFileDialog.getExistingDirectory)
            
        self.pushButton_JG_resfp_br.clicked.connect(browse_jg) # SS. Working Dir. Browse
        
        #execute
        self.pushButton_JG_join.clicked.connect(self.join_geo)
        
        
        
        
        log.info('finished')
        
    def join_geo(self):
        log = self.logger.getChild('join_geo')
        log.info('user pushed \'join_geo\'')
        pass
