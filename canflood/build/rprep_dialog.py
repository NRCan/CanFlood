'''
Created on Oct. 20, 2021

@author: cefect
'''


#==============================================================================
# imports-----------
#==============================================================================
#python
import sys, os, datetime, time, configparser

#PyQt
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QFileSystemModel, QListView, QHeaderView
from PyQt5.QtCore import QStringListModel, QAbstractTableModel
from PyQt5 import QtGui

import hlpr.plug

#===============================================================================
# load UI file
#===============================================================================
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'rasterPrep.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)


class RPrepDialog(QtWidgets.QDialog, FORM_CLASS, hlpr.plug.QprojPlug):
    inherit_atts =  [] #for passing from the main
    def __init__(self, iface, parent=None, **kwargs):
        super(RPrepDialog, self).__init__(parent) #only calls QtWidgets.QDialog
        
        self.iface = iface
        
        self.setupUi(self)
        
    def _setup(self):
        """
        called on launch
        """

        self.connect_slots()
        
        
    def connect_slots(self):
        """leaving this on the main
        self.pushButton_HS_rprep.clicked.connect(self.run_rPrep)
        """
        pass