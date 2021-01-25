# -*- coding: utf-8 -*-
"""
ui class for the vfunction selection dialog
"""
#==============================================================================
# imports-----------
#==============================================================================
#python
import sys, os, datetime, time

from shutil import copyfile

"""see __init__.py for dependency check"""
import pandas as pd
import numpy as np #assuming if pandas is fine, numpy will be fine

#PyQt
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

#qgis

#from qgis.core import *


#==============================================================================
# custom imports
#==============================================================================




import hlpr.plug
#from hlpr.Q import vlay_get_fdf

from hlpr.basic import get_valid_filename, force_open_dir 
from hlpr.exceptions import QError as Error


#===============================================================================
# load UI file
#===============================================================================
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'vfunc_select.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)


#===============================================================================
# class objects-------
#===============================================================================

class vDialog(QtWidgets.QDialog, FORM_CLASS, hlpr.plug.QprojPlug):
    
    def __init__(self, iface, parent=None):
        """these will only ini tthe first baseclass (QtWidgets.QDialog)
        
        required"""
        super(vDialog, self).__init__(parent) #only calls QtWidgets.QDialog

        self.setupUi(self)
        
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect


        self.iface = iface
        
        self.qproj_setup() #basic dialog worker setup
        
        self.connect_slots()
        
        
        self.logger.debug('rDialog initilized')
        

    def connect_slots(self):
        log = self.logger.getChild('connect_slots')

        #======================================================================
        # pull project data
        #======================================================================

                
        #=======================================================================
        # general----------------
        #=======================================================================

        #ok/cancel buttons
        self.buttonBox.accepted.connect(self.reject) #back out of the dialog
        self.buttonBox.rejected.connect(self.reject)
        
        self.logger.statusQlab=self.progressText #connect to the progress text above the bar
        """
        where does the progressBar get connected?
        """
        
        
                    
                
            
        

            
            
             
        
        
        
                
  
 

           
            
                    
            