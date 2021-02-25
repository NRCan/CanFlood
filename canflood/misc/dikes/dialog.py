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

from qgis.core import QgsMapLayer, QgsMapLayerProxyModel


#==============================================================================
# custom imports
#==============================================================================

import hlpr.plug
from hlpr.basic import get_valid_filename, view
from hlpr.exceptions import QError as Error
from hlpr.plug import MyFeedBackQ, QprojPlug, pandasModel, bind_layersListWidget


#===============================================================================
# workers
#===============================================================================
from misc.dikes.expo import Dexpo


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
        # setup--------
        #=======================================================================
        #working directory
        self._connect_wdir(self.pushButton_wd_brwse, self.pushButton_wd_open, self.lineEdit_wdir,
                           default_wdir = os.path.join(os.path.expanduser('~'), 'CanFlood', 'dikes'))
        
        #aoi
        self.comboBox_aoi.setFilters(QgsMapLayerProxyModel.PolygonLayer) #SS. Project AOI
        self.comboBox_aoi.setCurrentIndex(-1) #by default, lets have this be blan

        #=======================================================================
        # #dikes
        #=======================================================================
        self.comboBox_dikesVlay.setFilters(QgsMapLayerProxyModel.LineLayer)
        
        #connect field boxes
        self.comboBox_dikesVlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_dikeID, 
                           self.comboBox_ivlay.currentLayer(), fn_str='id'))

        
 
        #=======================================================================
        # Exposure--------
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
       
        
        
        #=======================================================================
        # dtm
        #=======================================================================
        self.mMapLayerComboBox_dtm.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.mMapLayerComboBox_dtm.setAllowEmptyLayer(True)
        self.mMapLayerComboBox_dtm.setCurrentIndex(-1) #set selection to none
        
        #=======================================================================
        # run
        #=======================================================================
        self.pushButton_expo_run.clicked.connect(self.run_expo)
        
        
    def _set_setup(self): #attach parameters from setup tab
        
        #secssion controls
        self.tag = self.linEdit_ScenTag.text()
        self.out_dir = self.lineEdit_wdir.text()
        assert os.path.exists(self.out_dir), 'working directory does not exist!'
        
        #project aoi
        self.aoi_vlay = self.comboBox_aoi.currentLayer()
        
        #file behavior
        self.loadRes = self.checkBox_loadres.isChecked()
        self.overwrite=self.checkBox_SSoverwrite.isChecked()
        self.absolute_fp = self.radioButton_SS_fpAbs.isChecked()
        
        #dikes layer
        self.dike_vlay = self.comboBox_dikesVlay.currentLayer()
        self.dikeID = self.mFieldComboBox_dikeID.currentField()
        self.segID = self.mFieldComboBox_segID.currentField()
        
    def run_expo(self): #execute dike exposure routeines
        log = self.logger.getChild('run_expo')
        self.feedback.setProgress(1)
        log.debug('start')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in ['logger', 'out_dir', 'segID', 'dikeID', 'tag']}
        
        rlays_d = self.listWidget_expo_rlays.get_selected_layers()
        
        #tside
        if self.radioButton_v_tside_left.isChecked():
            tside = 'Left'
        else:
            tside = 'Right'

        #=======================================================================
        # init
        #=======================================================================
        
        wrkr = Dexpo(**kwargs)
        self.feedback.setProgress(10)
        
        #=======================================================================
        # execute
        #=======================================================================
        
        kwargs = {attn:getattr(self, attn) for attn in ['dike_vlay']} 
        
        dxcol, vlay_d = wrkr.get_dike_expo(rlays_d, 
                           dtm_rlay = self.mMapLayerComboBox_dtm.currentLayer(),
                           
                           #transect pars
                           tside=tside,
                           
                           write_tr=self.checkBox_expo_write_tr.isChecked(),
                           dist_dike=float(self.doubleSpinBox_dist_dike.value()), 
                           dist_trans=float(self.doubleSpinBox_dist_trans.value()),
                           **kwargs)
        
        self.feedback.setProgress(60)
        
        
        expo_df = wrkr.get_fb_smry()
        self.feedback.setProgress(80)
        #=======================================================================
        # write
        #=======================================================================
        wrkr.output_expo_dxcol()
        dexpo_fp = wrkr.output_expo_df(as_vlay=self.checkBox_expo_write_vlay.isChecked())
        
        if self.checkBox_expo_breach_pts.isChecked():
            breach_vlay_d = wrkr.get_breach_vlays()
            wrkr.output_breaches()
            
        if self.checkBox_expo_plot.isChecked():
            wrkr._init_plt()
            for sidVal in wrkr.sid_vals:
                fig = wrkr.plot_seg_prof(sidVal)
                wrkr.output_fig(fig)
                
        self.feedback.setProgress(95)
        #=======================================================================
        # update gui
        #=======================================================================
        self.lineEdit_v_dexpo_fp.setText(dexpo_fp)
        
        log.info('finished w/ %s'%str(expo_df.shape))
            
        
if __name__=='__main__':
    print('???')

    

        
        
        
                
  
 

           
            
                    
            