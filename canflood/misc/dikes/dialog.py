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


from hlpr.basic import get_valid_filename, view
from hlpr.exceptions import QError as Error
import hlpr.plug
from hlpr.plug import MyFeedBackQ, QprojPlug, pandasModel, bind_layersListWidget, bind_MapLayerComboBox


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
        
        
        
        self.logger.info('rDialog initilized')
        

        
    def _setup(self, **kwargs):

        self.connect_slots(**kwargs)
        return self
    
    def launch(self): #connect + show
        """called by CanFlood.py menu click
        should improve load time by moving the connections to after the menu click"""
        self.connect_slots()
        self.show()

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
        bind_MapLayerComboBox(self.comboBox_dikesVlay, 
                      layerType=QgsMapLayerProxyModel.LineLayer, iface=self.iface)
        self.comboBox_dikesVlay.attempt_selection('dikes')
        
        #connect field boxes
        self.comboBox_dikesVlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_dikeID, 
                           self.comboBox_dikesVlay.currentLayer(), fn_str='id'))

        self.comboBox_dikesVlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_segID, 
                           self.comboBox_dikesVlay.currentLayer(), fn_str='seg'))
        
        self.comboBox_dikesVlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_cbfn, 
                           self.comboBox_dikesVlay.currentLayer(), fn_str='crest'))
                

        #=======================================================================
        # Exposure--------
        #=======================================================================
        #=======================================================================
        # wsl raster layers
        #=======================================================================
        #list widget
        bind_layersListWidget(self.listWidget_expo_rlays, log, iface=self.iface, 
                              layerType=QgsMapLayer.RasterLayer) #add custom bindigns
        
        self.listWidget_expo_rlays.populate_layers(layers=rlays) #populate
        
        #connect buttons
        self.pushButton_expo_sAll.clicked.connect(self.listWidget_expo_rlays.selectAll)
        self.pushButton_expo_clear.clicked.connect(self.listWidget_expo_rlays.clearSelection)
        self.pushButton_expo_sVis.clicked.connect(self.listWidget_expo_rlays.select_visible)
        self.pushButton_expo_canvas.clicked.connect(self.listWidget_expo_rlays.select_canvas)
        
        """not sure if this fix is needed... but possibleissue with kwarg passing"""
        self.pushButton_expo_refr.clicked.connect(lambda x: self.listWidget_expo_rlays.populate_layers())
       
        
        
        #=======================================================================
        # dtm
        #=======================================================================
        bind_MapLayerComboBox(self.mMapLayerComboBox_dtm, 
                              layerType=QgsMapLayerProxyModel.RasterLayer, iface=self.iface)

        self.mMapLayerComboBox_dtm.attempt_selection('dtm')
        #=======================================================================
        # run
        #=======================================================================
        self.pushButton_expo_run.clicked.connect(self.run_expo)
        
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info("finished")
        
        
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
        self.cbfn = self.mFieldComboBox_cbfn.currentField()
        
    def run_expo(self): #execute dike exposure routeines
        log = self.logger.getChild('run_expo')
        log.debug('start')
        self._set_setup() #attach all the commons
        self.feedback.setProgress(5)
        
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        
        
        rlays_d = self.listWidget_expo_rlays.get_selected_layers()
        
        #tside
        if self.radioButton_v_tside_left.isChecked():
            tside = 'Left'
        else:
            tside = 'Right'

        #=======================================================================
        # init
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in ['logger', 'out_dir', 'segID', 'dikeID', 'tag', 'cbfn']}
        wrkr = Dexpo(**kwargs)
        self.feedback.setProgress(10)
        
        #=======================================================================
        # execute
        #=======================================================================
        dike_vlay = wrkr.prep_dike(self.dike_vlay)
        
        kwargs = {attn:getattr(self, attn) for attn in []} 
        
        dxcol, vlay_d = wrkr.get_dike_expo(rlays_d, 
                           dtm_rlay = self.mMapLayerComboBox_dtm.currentLayer(),
                           dike_vlay = dike_vlay,
                           #transect pars
                           tside=tside,
                           
                           write_tr=False, #loaded below
                           dist_dike=float(self.doubleSpinBox_dist_dike.value()), 
                           dist_trans=float(self.doubleSpinBox_dist_trans.value()),
                           **kwargs)
        
        self.feedback.setProgress(60)
        
        
        expo_df = wrkr.get_fb_smry()
        self.feedback.setProgress(80)
        #=======================================================================
        # write/load to cannvas----------
        #=======================================================================
        """dont write any layers.. just load them and let the user write"""
        wrkr.output_expo_dxcol()
        dexpo_fp = wrkr.output_expo_df(as_vlay=self.checkBox_expo_write_vlay.isChecked())
        
        #=======================================================================
        # breach points
        #=======================================================================
        if self.checkBox_expo_breach_pts.isChecked():
            assert self.checkBox_loadres.isChecked(), 'to get ouput layers, check \'Load session results...\''
            breach_vlay_d = wrkr.get_breach_vlays()
            
            for k, layer in breach_vlay_d.items():
                self.qproj.addMapLayer(layer)
            log.info('loaded %i breach point layers'%len(breach_vlay_d))
            
        #=======================================================================
        # transects
        #=======================================================================
        if self.checkBox_expo_write_tr.isChecked():
            assert self.checkBox_loadres.isChecked(), 'to get ouput layers, check \'Load session results...\''
            self.qproj.addMapLayer(wrkr.tr_vlay)
            log.info('loaded transect layer \'%s\' to canvas'%wrkr.tr_vlay.name())
            
        #=======================================================================
        # exposure crest points
        #=======================================================================
        if self.checkBox_expo_crestPts.isChecked():
            assert self.checkBox_loadres.isChecked(), 'to get ouput layers, check \'Load session results...\''
            
            for k, layer in wrkr.expo_vlay_d.items():
                self.qproj.addMapLayer(layer)
            log.info('loaded %i expo_crest_pts layers'%len(wrkr.expo_vlay_d))
            
        #=======================================================================
        # dike layer
        #=======================================================================
        if self.checkBox_expo_wDikes.isChecked():
            assert self.checkBox_loadres.isChecked(), 'to get ouput layers, check \'Load session results...\''
            self.qproj.addMapLayer(dike_vlay)
            log.info('added \'%s\' to canvas'%(dike_vlay.name()))
            
            
        #=======================================================================
        # plots
        #=======================================================================
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

    

        
        
        
                
  
 

           
            
                    
            