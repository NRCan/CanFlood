# -*- coding: utf-8 -*-
"""
ui class for the dike mapper
"""
#==============================================================================
# imports-----------
#==============================================================================
#python
import sys, os, datetime, time, configparser

from shutil import copyfile

"""see __init__.py for dependency check"""
import pandas as pd
import numpy as np #assuming if pandas is fine, numpy will be fine

#PyQt
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QFileSystemModel, QListView, QHeaderView
from PyQt5.QtCore import QStringListModel, QAbstractTableModel
from PyQt5 import QtGui

#qgis

from qgis.core import QgsMapLayer


#==============================================================================
# custom imports
#==============================================================================

import hlpr.plug
from hlpr.basic import get_valid_filename, view
from hlpr.exceptions import QError as Error
from hlpr.plug import MyFeedBackQ, QprojPlug, pandasModel, bind_layersListWidget


#===============================================================================
# logger
#===============================================================================


#===============================================================================
# load UI file
#===============================================================================
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'dikes.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)


#===============================================================================
# class objects-------
#===============================================================================

class DikesDialog(QtWidgets.QDialog, FORM_CLASS, QprojPlug):



    def __init__(self, 
                 iface, 
                 parent=None,
                 plogger=None):
        """these will only ini tthe first baseclass (QtWidgets.QDialog)
        
        required"""
        super(DikesDialog, self).__init__(parent) #only calls QtWidgets.QDialog
        

        #=======================================================================
        # attachments
        #=======================================================================
        self.iface = iface
        
        #=======================================================================
        # setup funcs
        #=======================================================================

        self.setupUi(self)
        
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect


        #=======================================================================
        # qproj_setup 
        #=======================================================================
        """setup to run outside qgis
        self.qproj_setup() #basic dialog worker setup"""
        
        if plogger is None: plogger = hlpr.plug.logger(self) 
        self.logger=plogger
        

        self.setup_feedback(progressBar = self.progressBar,
                            feedback = MyFeedBackQ())
        
        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars')
        

        #=======================================================================
        # connect the slots
        #=======================================================================        
        #self.connect_slots()
        
        
        
        self.logger.debug('rDialog initilized')
        
    def _setup(self, **kwargs):

        self.connect_slots(**kwargs)
        return self

    def connect_slots(self,
                      rlays=None, #set of rasters to populate list w/ 
                      ):
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
        
        self.logger.statusQlab=self.progressText #connect to the progress text
        
        #=======================================================================
        # Exposurte--------
        #=======================================================================
        #=======================================================================
        # wsl raster layers
        #=======================================================================
        #list widget
        bind_layersListWidget(self.listWidget_expo_rlays, iface=self.iface, 
                              layerType=QgsMapLayer.RasterLayer) #add custom bindigns
        
        self.listWidget_expo_rlays.populate_layers(layers=rlays) #populate
        
        #connect buttons
        self.pushButton_expo_sAll.clicked.connect(self.listWidget_expo_rlays.selectAll)
        self.pushButton_expo_clear.clicked.connect(self.listWidget_expo_rlays.clearSelection)
        self.pushButton_expo_sVis.clicked.connect(self.listWidget_expo_rlays.select_visible)
        self.pushButton_expo_refr.clicked.connect(self.listWidget_expo_rlays.populate_layers)
       
        self.listWidget_expo_rlays._set_selection_byName([r.name() for r in rlays])
            
        
if __name__=='__main__':
    print('???')

    

        
        
        
                
  
 

           
            
                    
            