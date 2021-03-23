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
from PyQt5.QtWidgets import QFileSystemModel, QListView, QHeaderView, QComboBox, QGroupBox
from PyQt5.QtCore import QStringListModel, QAbstractTableModel
from PyQt5 import QtGui

#qgis

from qgis.core import QgsMapLayer, QgsMapLayerProxyModel, QgsProject


#==============================================================================
# custom imports
#==============================================================================


from hlpr.basic import get_valid_filename, view
from hlpr.exceptions import QError as Error
#import hlpr.plug
from hlpr.plug import MyFeedBackQ, QprojPlug, pandasModel, bind_layersListWidget, bind_MapLayerComboBox
from hlpr.plug import bind_link_boxes
import hlpr.logr

#===============================================================================
# workers
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

    groupName = 'CanFlood.Dikes'

    def __init__(self, 
                 iface, 
                 parent=None,
                 plogger=None,
                 **kwargs):
        """
        called during startup by CanFlood.__init__
        """
        
        """these will only ini tthe first baseclass (QtWidgets.QDialog)
        required"""
        super(DikesDialog, self).__init__(parent) #only calls QtWidgets.QDialog
        
        #=======================================================================
        # attachments
        #=======================================================================

        #=======================================================================
        # setup funcs
        #=======================================================================
        self.setupUi(self)
        
        self.qproj_setup(iface=iface, plogger=plogger) #basic dialog worker setup
        self.connect_slots(**kwargs)


    
    def launch(self): #launch the gui from a plugin (and do some setup)
        """called by CanFlood.py menu click
        should improve load time by moving the connections to after the menu click"""
        log = self.logger.getChild('launch')
        for fName, f in self.launch_actions.items():
            log.debug('%s: %s'%(fName, f))
            try:
                f()
            except Exception as e:
                log.warning('failed to execute \'%s\' w/ \n    %s'%(fName, e))
        
 

        self.show()

    def connect_slots(self,
                      rlays=None, #set of rasters to populate list w/ (for standalone)
                      ):
        log = self.logger.getChild('connect_slots')
        #assert not self.iface is None

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
        """not implemented
        self.comboBox_aoi.setFilters(QgsMapLayerProxyModel.PolygonLayer) #SS. Project AOI
        self.comboBox_aoi.setCurrentIndex(-1) #by default, lets have this be blan"""

        #=======================================================================
        # #dikes
        #=======================================================================
        bind_MapLayerComboBox(self.comboBox_dikesVlay, 
                      layerType=QgsMapLayerProxyModel.LineLayer, iface=self.iface)
         

        self.launch_actions['dikes layer selection'] = lambda: self.comboBox_dikesVlay.attempt_selection('dikes')
        
        #connect field boxes
        self.comboBox_dikesVlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_dikeID, 
                           self.comboBox_dikesVlay.currentLayer(), fn_str='id', fn_no_str='fid'))

        self.comboBox_dikesVlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_segID, 
                           self.comboBox_dikesVlay.currentLayer(), fn_str='seg'))
        
        self.comboBox_dikesVlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_cbfn, 
                           self.comboBox_dikesVlay.currentLayer(), fn_str='crest'))
        
        self.comboBox_dikesVlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_ifidN, 
                           self.comboBox_dikesVlay.currentLayer(), fn_str='ifz'))
                
                
                

        #=======================================================================
        # Exposure--------
        #=======================================================================
        #=======================================================================
        # wsl raster layers
        #=======================================================================
        #list widget
        bind_layersListWidget(self.listView_expo_rlays, log, iface=self.iface, 
                              layerType=QgsMapLayer.RasterLayer) #add custom bindigns
        
        
        
        #connect buttons
        self.pushButton_expo_sAll.clicked.connect(self.listView_expo_rlays.check_all)
        self.pushButton_expo_clear.clicked.connect(self.listView_expo_rlays.clear_checks)
        self.pushButton_expo_sVis.clicked.connect(self.listView_expo_rlays.select_visible)
        self.pushButton_expo_canvas.clicked.connect(self.listView_expo_rlays.select_canvas)
        
        """not sure if this fix is needed... but possibleissue with kwarg passing"""
        self.pushButton_expo_refr.clicked.connect(lambda x: self.listView_expo_rlays.populate_layers())
       
        #populate the widget
        if not rlays is None: #for debug runs
            self.listView_expo_rlays.populate_layers(layers=rlays) 
        self.launch_actions['hazlay selection'] = lambda: self.listView_expo_rlays.populate_layers()
        
        #=======================================================================
        # dtm
        #=======================================================================
        bind_MapLayerComboBox(self.mMapLayerComboBox_dtm, 
                              layerType=QgsMapLayerProxyModel.RasterLayer, iface=self.iface)
 
        self.launch_actions['dtm layer selection'] = lambda: self.mMapLayerComboBox_dtm.attempt_selection('dtm')

        #=======================================================================
        # run
        #=======================================================================
        self.pushButton_expo_run.clicked.connect(self.run_expo)
        
        #=======================================================================
        # Vuln-------
        #=======================================================================
        #filepath browse buttons
        self.pushButton_v_dexpo_brwse.clicked.connect(
            lambda: self.fileSelect_button(self.lineEdit_v_dexpo_fp, 
                                       caption='Select Exposure Results',
                                       filters="Data Files (*.csv)",
                                       path=self.lineEdit_wdir.text())
                                       )
        
        self.pushButton_v_dcurves_brwse.clicked.connect(
            lambda: self.fileSelect_button(self.lineEdit_v_dcurves_fp, 
                                       caption='Select Fragility Curves',
                                       filters="Spreadsheets (*.xls)",
                                       path=self.lineEdit_wdir.text())
                                       )
        
        self.pushButton_vuln_run.clicked.connect(self.run_vuln)
        
        #=======================================================================
        # Join Areas------------
        #=======================================================================
        #datafilepaths
        self.pushButton_ja_brwse.clicked.connect(
            lambda: self.fileSelect_button(self.lineEdit_ja_pfail_fp, 
                                       caption='Select Failure P Results',
                                       filters="Data Files (*.csv)",
                                       path=self.lineEdit_wdir.text())
                                       )
        #setup the layer linker
        bind_link_boxes(self.scrollAreaWidgetContents_ja, 
                 {'event':QgsMapLayerProxyModel.RasterLayer, 'lpol':QgsMapLayerProxyModel.PolygonLayer},
                 iface=self.iface)

        self.pushButton_ja_clearAll.clicked.connect(self.scrollAreaWidgetContents_ja.clear_all)
        self.pushButton_ja_fill.clicked.connect(
            lambda x: self.scrollAreaWidgetContents_ja.fill_down('lpol', name_str2='event'))
        
        
        
        #runner
        self.pushButton_ja_run.clicked.connect(self.run_rjoin)
        #=======================================================================
        # wrap-------
        #=======================================================================
        log.info("finished")
        
        
    def set_setup(self): #attach parameters from setup tab

        self._set_setup(set_cf_fp=False)

        
        #project aoi
        #self.aoi_vlay = self.comboBox_aoi.currentLayer()
        
        #file behavior
        self.loadRes = self.checkBox_loadres.isChecked()

        #dikes layer
        self.dike_vlay = self.comboBox_dikesVlay.currentLayer()
        
        #dikes layer fields
        self.dikeID = self.mFieldComboBox_dikeID.currentField()
        self.segID = self.mFieldComboBox_segID.currentField()
        self.cbfn = self.mFieldComboBox_cbfn.currentField()
        self.ifidN = self.mFieldComboBox_ifidN.currentField()
        
        """just put this here for easy upedating"""
        self.inherit_fieldNames = set(
            self.inherit_fieldNames + ['segID', 'dikeID',
                                    'cbfn', 'ifidN'])
        #=======================================================================
        # prechecks
        #=======================================================================
        for attn in ['dikeID', 'segID', 'cbfn', 'ifidN']:
            assert hasattr(self, attn)
            attv = getattr(self, attn)
            assert isinstance(attv, str)
            assert not attv == '', 'got empty string for \"%s\'. did you select a field?'%attn
        
    def run_expo(self): #execute dike exposure routeines
        log = self.logger.getChild('run_expo')
        log.debug('start')
        self.set_setup() #attach all the commons
        self.inherit_fieldNames.add('init_q_d')
        self.feedback.setProgress(5)
        from misc.dikes.expo import Dexpo
        #=======================================================================
        # collect inputs
        #=======================================================================
        rlays_d = self.listView_expo_rlays.get_selected_layers()
        
        #tside
        if self.radioButton_v_tside_left.isChecked():
            tside = 'Left'
        else:
            tside = 'Right'

        #=======================================================================
        # init
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Dexpo(**kwargs)
        self.feedback.setProgress(10)
        
        #=======================================================================
        # execute------
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
        #wrkr.output_expo_dxcol()
        dexpo_fp = wrkr.output_expo_df()
        
        #=======================================================================
        # dike layer
        #=======================================================================
        if self.checkBox_expo_wDikes.isChecked():
            dike_vlay = wrkr.get_dikes_vlay() #get the dikes layer for writintg (fixed index)
            self._load_toCanvas(dike_vlay, logger=log.getChild('dike_vlay'))

        #=======================================================================
        # breach points
        #=======================================================================
        if self.checkBox_expo_breach_pts.isChecked():
            breach_vlay_d = wrkr.get_breach_vlays()
            self._load_toCanvas(list(breach_vlay_d.values()), logger=log.getChild('breachPts'))
            
        #=======================================================================
        # transects
        #=======================================================================
        if self.checkBox_expo_write_tr.isChecked():
            self._load_toCanvas(wrkr.tr_vlay, logger=log.getChild('tr_vlay'))
            log.info('loaded transect layer \'%s\' to canvas'%wrkr.tr_vlay.name())
            
        #=======================================================================
        # exposure crest points
        #=======================================================================
        if self.checkBox_expo_crestPts.isChecked():
            self._load_toCanvas(list(wrkr.expo_vlay_d.values()), logger=log.getChild('expo_crestPts'))

        #=======================================================================
        # plots
        #=======================================================================
        if self.checkBox_expo_plot.isChecked():
            wrkr._init_plt()
            #check for exessive plot windows
            if len(wrkr.sid_vals)>5:
                plt_window = False
                log.warning('got %i plots... setting plt_window=False'%len(wrkr.sid_vals))
            elif len(wrkr.sid_vals)>100:
                raise Error('too many plots!')
            else:
                plt_window = self.plt_window
                
            for sidVal in wrkr.sid_vals:
                fig = wrkr.plot_seg_prof(sidVal)
                self.output_fig(fig, plt_window=plt_window)
                
        self.feedback.setProgress(95)
        #=======================================================================
        # update gui
        #=======================================================================
        self.lineEdit_v_dexpo_fp.setText(dexpo_fp) #fill joinareaas filepath
        
        #populate the Join Areas widget
        self.scrollAreaWidgetContents_ja.clear_all() #clear for repeat runs
        self.scrollAreaWidgetContents_ja.set_selections('event', list(rlays_d.values()))
        
        log.info('finished Dike Expo w/ %s'%str(expo_df.shape))
        self.feedback.upd_prog(None)
        
    def run_vuln(self):
        log = self.logger.getChild('run_vuln')
        log.debug('start')
        self.set_setup() #attach all the commons
        self.feedback.setProgress(5)
        from misc.dikes.vuln import Dvuln
        #=======================================================================
        # collect inputs
        #=======================================================================
        
        #=======================================================================
        # init
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Dvuln(**kwargs)
        self.feedback.setProgress(10)
        
        #=======================================================================
        # load
        #=======================================================================
        wrkr._setup(
            dexpo_fp=self.lineEdit_v_dexpo_fp.text(),
             dcurves_fp = self.lineEdit_v_dcurves_fp.text())
        self.feedback.setProgress(20)
        #==========================================================================
        # execute
        #==========================================================================
        pf_df = wrkr.get_failP()
        self.feedback.setProgress(60)
        #=======================================================================
        # length effect
        #=======================================================================
        #collect method from user
        if self.radioButton_v_lfx_none.isChecked():
            method = None
        elif self.radioButton_v_lfx_urs.isChecked():
            method='URS2007'
        else:
            raise Error('unrecognized lfx method')

        if not method is None:
            wrkr.set_lenfx(method=method) #apply length effects
        self.feedback.setProgress(80)
        #=======================================================================
        # outputs
        #=======================================================================
        pfail_fp = wrkr.output_vdfs()
        self.feedback.setProgress(95)
        #=======================================================================
        # update gui
        #=======================================================================
        self.lineEdit_ja_pfail_fp.setText(pfail_fp)
        
        log.info('finished Dike Vuln w/ %s'%str(pf_df.shape))
        self.feedback.upd_prog(None)
        
    def run_rjoin(self): #join failure probabilities onto influence polygons
        #=======================================================================
        # setup
        #=======================================================================
        log = self.logger.getChild('run_rjoin')
        log.debug('start')
        self.set_setup() #attach all the commons
        self.inherit_fieldNames.add('init_q_d')
        self.feedback.setProgress(5)
        from misc.dikes.rjoin import DikeJoiner
        
        """no reason to build the layers if they won't be loaded"""
        assert self.loadRes, 'ensure \'Load Results to Canvas..\' is selected'
        #=======================================================================
        # init
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = DikeJoiner(**kwargs)
        self.feedback.setProgress(10)
        
        #==========================================================================
        # load the data
        #==========================================================================
        wrkr.load_pfail_df(fp=self.lineEdit_ja_pfail_fp.text())
        
        #get influence polygons {rasterLayerName:polygonLayer}   
        eifz_d = self.scrollAreaWidgetContents_ja.get_linked_layers(keyByFirst=True) 
        
        self.feedback.setProgress(40)
        #==========================================================================
        # execute
        #==========================================================================
        vlay_d = wrkr.join_pfails(eifz_d=eifz_d)
        self.feedback.setProgress(80)
        #=======================================================================
        # outputs
        #=======================================================================
        self._load_toCanvas(list(vlay_d.values()), logger=log, style_fn = 'failPoly_graduated_reds.qml')
        self.feedback.setProgress(95)
        #=======================================================================
        # wrapo
        #=======================================================================
        log.info('finisehd Join Areas w/ %i'%len(vlay_d))
        self.feedback.upd_prog(None)
        
if __name__=='__main__':
    print('???')

    

        
        
        
                
  
 

           
            
                    
            