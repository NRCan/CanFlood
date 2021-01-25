# -*- coding: utf-8 -*-
"""
ui class for the BUILD toolset
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

from qgis.core import *


#==============================================================================
# custom imports
#==============================================================================




import hlpr.plug
#from hlpr.Q import vlay_get_fdf

from hlpr.basic import get_valid_filename, force_open_dir 
from hlpr.exceptions import QError as Error

from .convert import RFDAconv

#===============================================================================
# load UI file
#===============================================================================
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'rfda.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)


#===============================================================================
# class objects-------
#===============================================================================

class rDialog(QtWidgets.QDialog, FORM_CLASS, hlpr.plug.QprojPlug):
    
    def __init__(self, iface, parent=None):
        """these will only ini tthe first baseclass (QtWidgets.QDialog)
        
        required"""
        super(rDialog, self).__init__(parent) #only calls QtWidgets.QDialog

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
        
        #=======================================================================
        # session controls
        #=======================================================================
        #Working Directory 
        """default is set below.
        doesn't seem to open the displayed directory on first click"""
        def browse_wd():
            return self.browse_button(self.lineEdit_wd, prompt='Select Working Directory',
                                      qfd = QFileDialog.getExistingDirectory)
            
        self.pushButton_wd.clicked.connect(browse_wd) # SS. Working Dir. Browse
        
        #WD force open
        def open_wd():
            force_open_dir(self.lineEdit_wd.text())
        
        self.pushButton_wd_open.clicked.connect(open_wd)
        
        #======================================================================
        # RFDA
        #======================================================================
        #Vulnerability Curve Set
        def browse_rfda_crv():
            return self.browse_button(self.lineEdit_wd_OthRf_cv, prompt='Select RFDA curve .xls',
                                      qfd = QFileDialog.getOpenFileName)
            
        self.pushButton_wd_OthRf_cv.clicked.connect(browse_rfda_crv)
            
        self.mMapLayerComboBox_OthR_rinv.setFilters(QgsMapLayerProxyModel.PointLayer)
        self.mMapLayerComboBox_OthR_rinv.setCurrentIndex(-1) #clear the selection
        
        self.pushButton_OthRfda.clicked.connect(self.convert_rfda)
                
        
            
        #=======================================================================
        # wrap
        #=======================================================================
        return
            




    def convert_rfda(self): #Other.Rfda tab

        log = self.logger.getChild('convert_rfda')
        tag = 'rfda'
        log.debug('start')
        #======================================================================
        # collect from  ui
        #======================================================================
        rinv_vlay = self.mMapLayerComboBox_OthR_rinv.currentLayer()
        crv_fp = self.lineEdit_wd_OthRf_cv.text()
        bsmt_ht = self.lineEdit_OthRf_bht.text()
        #cid = self.mFieldComboBox_cid.currentField() #user selected field
        
        #crs = self.qproj.crs()
        out_dir = self.lineEdit_wd.text()
        
        try:
            bsmt_ht = float(bsmt_ht)
        except Exception as e:
            raise Error('failed to convert bsmt_ht to float w/ \n    %s'%e)
        
        self.feedback.setProgress(10)
        
        #======================================================================
        # input checks
        #======================================================================
        
        wrkr = RFDAconv(logger=self.logger, out_dir=out_dir, tag=tag, bsmt_ht = bsmt_ht)
        self.feedback.setProgress(20)
        #======================================================================
        # invnentory convert
        #======================================================================
        if isinstance(rinv_vlay, QgsVectorLayer):
            
            
            finv_vlay = wrkr.to_finv(rinv_vlay)
            
            self.qproj.addMapLayer(finv_vlay)
            log.info('added \'%s\' to canvas'%finv_vlay.name())
            self.feedback.setProgress(40)
        #======================================================================
        # curve convert
        #======================================================================
        if os.path.exists(crv_fp):
            df_raw = pd.read_excel(crv_fp, header=None)
            
            df_d = wrkr.to_curveset(df_raw, logger=log)
            
            basefn = os.path.splitext(os.path.split(crv_fp)[1])[0]
            
            ofp = wrkr.output(df_d, basefn=basefn)
            
        else:
            log.info('no valid crv_fp provided')
        self.feedback.setProgress(99)
        #======================================================================
        # wrap
        #======================================================================
        log.push('finished rfda')
        self.feedback.upd_prog(None) #set the progress bar back down to zero
            

    
    
     
            
                    
                
            
        

            
            
             
        
        
        
                
  
 

           
            
                    
            