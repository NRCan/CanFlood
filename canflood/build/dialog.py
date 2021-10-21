# -*- coding: utf-8 -*-
"""
ui class for the BUILD toolset
"""
#==============================================================================
# imports-----------
#==============================================================================
#python
import sys, os, datetime, time



"""see __init__.py for dependency check"""
import pandas as pd
import numpy as np #assuming if pandas is fine, numpy will be fine

#PyQt
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

#qgis
#from qgis.core import *
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer, QgsMapLayerProxyModel, \
    QgsWkbTypes, QgsMapLayer

#==============================================================================
# custom imports
#==============================================================================
#get hlpr funcs
import hlpr.plug
from hlpr.plug import bind_layersListWidget
#from hlpr.basic import get_valid_filename, force_open_dir 
from hlpr.exceptions import QError as Error

#get sub-models
from build.rsamp import Rsamp
from build.lisamp import LikeSampler
from build.prepr import Preparor
from build.validator import Vali

#get sub-dialogs
from build.dialog_vfunc import vDialog
from build.dialog_rprep import RPrepDialog

#===============================================================================
# load UI file
#===============================================================================
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'build.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)


#===============================================================================
# class objects-------
#===============================================================================

class BuildDialog(QtWidgets.QDialog, FORM_CLASS, hlpr.plug.QprojPlug):
    
    event_name_set = [] #event names
    

    def __init__(self, iface, parent=None, **kwargs):
        #=======================================================================
        # #init baseclass
        #=======================================================================
        """these will only ini tthe first baseclass (QtWidgets.QDialog)
        
        required"""
        
        super(BuildDialog, self).__init__(parent) #only calls QtWidgets.QDialog

        #=======================================================================
        # attachments
        #=======================================================================
        #=======================================================================
        # setup funcs
        #=======================================================================
        
        self.setupUi(self)

        self.qproj_setup(iface=iface, **kwargs)

        self.vDialog = vDialog(iface) #init and attach vfunc library dialog(connected below)
        self.RPrepDialog=RPrepDialog(iface)
        

        self.connect_slots()
        
        self.logger.debug('BuildDialog initilized')
        

    def connect_slots(self,
                      rlays=None):
        """
        using the cointaier (dict) self.launch_actions to store functions
            that should be called once the dialog is launched
            see self.launch()
        """
        
        log = self.logger.getChild('connect_slots')

        #======================================================================
        # pull project data
        #======================================================================
        #pull layer info from project
        rlays_d = dict()
        vlays_d = dict()
        for layname, layer in QgsProject.instance().mapLayers().items():
            if isinstance(layer, QgsVectorLayer):
                vlays_d[layname] = layer
            elif isinstance(layer, QgsRasterLayer):
                rlays_d[layname] = layer
            else:
                self.logger.debug('%s not filtered'%layname)
                
        #=======================================================================
        # general----------------
        #=======================================================================

        #ok/cancel buttons
        self.buttonBox.accepted.connect(self.reject) #back out of the dialog
        self.buttonBox.rejected.connect(self.reject)
        
        
        #connect to status label
        """
        this could be moved onto the feedback object...
            but would be a lot of work to move it off the logger
            and not sure what the benefit would be
            
            see hlpr.plug.logger._loghlp()
        """
        self.logger.statusQlab=self.progressText #connect to the progress text
        #self.logger.statusQlab.setText('BuildDialog initialized')
                
        #======================================================================
        #TAB: SETUP----------
        #======================================================================
        #=======================================================================
        # session controls
        #=======================================================================
        #Working Directory 
        self._connect_wdir(self.pushButton_wd, self.pushButton_wd_open, self.lineEdit_wdir,
                           default_wdir = os.path.join(os.path.expanduser('~'), 'CanFlood', 'build'))
                

        
        #AOI
        hlpr.plug.bind_MapLayerComboBox(self.comboBox_aoi, 
                                        iface=self.iface, layerType=QgsMapLayerProxyModel.PolygonLayer)

        
        #CanFlood Control 
        self.pushButton_cf.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_cf_fp, 
                                          caption='Select Control File',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Text Files (*.txt)")
                )
        
        self.pushButton_s_cfOpen.clicked.connect(lambda: os.startfile(self.lineEdit_cf_fp.text()))

        
        
        #=======================================================================
        # Control File Assembly
        #=======================================================================
        #elevation t ype
        self.comboBox_SSelv.addItems(['datum', 'ground']) #ss elevation type
        
                
        #Vulnerability Curve Set
        def browse_curves():
            return self.browse_button(self.lineEdit_curve, prompt='Select Curve Set',
                                      qfd = QFileDialog.getOpenFileName)
            
        self.pushButton_SScurves.clicked.connect(browse_curves)# SS. Vuln Curve Set. Browse
        
        #generate new control file      
        self.pushButton_generate.clicked.connect(self.build_scenario) #SS. generate
        

        
        #=======================================================================
        # TAB: INVENTORY------------
        #=======================================================================
        #=======================================================================
        # vfunc
        #=======================================================================
        #give commmon widgets
        for wName in self.vDialog.inherit_atts:
            assert hasattr(self, wName), wName
            setattr(self.vDialog, wName, getattr(self, wName))

        #connect launcher button
        def vDia(): #helper to connect slots and 
            """only executing setup once called to simplify initial loading"""
            _ = self.vDialog._setup()
            self.vDialog.show()
            
        self.pushButton_inv_vfunc.clicked.connect(vDia)
        self.pushButton_Inv_curves.clicked.connect(self.store_curves)

        #=======================================================================
        # Store IVlayer
        #=======================================================================
        #inventory vector layer box
        hlpr.plug.bind_MapLayerComboBox(self.comboBox_ivlay, 
                      layerType=QgsMapLayerProxyModel.VectorLayer, iface=self.iface)
        
        #attempt to select the layer during launch
        self.launch_actions['attempt finv'] = lambda: self.comboBox_ivlay.attempt_selection('finv')
        
        #set it on the session for the other dialogs
        self.comboBox_ivlay.layerChanged.connect( 
            lambda: setattr(self.session, 'finv_vlay', self.comboBox_ivlay.currentLayer()))
        

        #index field name
        self.comboBox_ivlay.layerChanged.connect(
            lambda : self.mfcb_connect(self.mFieldComboBox_cid, 
                           self.comboBox_ivlay.currentLayer(), fn_str='xid'))
                

        
        #connect button
        self.pushButton_Inv_store.clicked.connect(self.store_finv)
        #=======================================================================
        # NRPI
        #=======================================================================
        #filter the vector layer
        self.mMapLayerComboBox_inv_finv.setFilters(QgsMapLayerProxyModel.VectorLayer) 
        self.mMapLayerComboBox_inv_finv.setCurrentIndex(-1) #clear the selection
        
        #connect the push button
        self.pushButton_inv_const.clicked.connect(self.construct_finv)
        
        
        #======================================================================
        # TAB: HAZARD SAMPLER---------
        #======================================================================
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
        # inundation
        #=======================================================================
        hlpr.plug.bind_MapLayerComboBox(self.comboBox_HS_DTM, 
                      layerType=QgsMapLayerProxyModel.RasterLayer, iface=self.iface)
        
        #attempt to select the layer during launch
        self.launch_actions['attempt dtm2'] = lambda: self.comboBox_HS_DTM.attempt_selection('dtm')
        
        #=======================================================================
        # #exposure type
        #=======================================================================

        #populate the exposure type
        self.hs_expoType_d = {'value':'Values', 'area':'Area-Threshold'}
        self.comboBox_HS_EC_type.addItems(list(self.hs_expoType_d.values()))
        

        
        #force logic ontofindChildren type controls
        def force_expoTypeControlLogic():
            self.logger.debug('force_expoTypeControlLogic called')
            vlay = self.comboBox_ivlay.currentLayer()
            if isinstance(vlay,QgsVectorLayer): 
                gtype = QgsWkbTypes().displayString(vlay.wkbType())
                if not 'Point' in gtype: #complex geometry

                    #value selected. freeze area controls
                    if self.comboBox_HS_EC_type.currentText() == self.hs_expoType_d['value']:
                        self.groupBox_HS_AT.setDisabled(True)
                        self.groupBox_HS_VS.setDisabled(False) 
        
                    #area threshold selected
                    elif self.comboBox_HS_EC_type.currentText() == self.hs_expoType_d['area']:
                        self.groupBox_HS_AT.setDisabled(False)
                        self.groupBox_HS_VS.setDisabled(True) #disable the Value Sampling box
                    else:
                        log.debug('bad selection on comboBox_HS_EC_type: \'%s\''%(
                            self.comboBox_HS_EC_type.currentText()))
        #type box
        self.HSvalueSamplingType_d = {'global':'Global', 'passet':'Per-Asset'}
        
        #force logic onto exposure type when the finv selection changes
        def force_expoTypeLogic():
            vlay = self.comboBox_ivlay.currentLayer()

            if isinstance(vlay,QgsVectorLayer):
                gtype = QgsWkbTypes().displayString(vlay.wkbType())
                self.label_HS_finvgtype.setText(gtype) #set the label
                self.comboBox_HS_EC_type.setCurrentIndex(0)
                
                if 'Point' in gtype: #simple geometry
                    self.comboBox_HS_EC_type.setDisabled(True)                    
                    #turn off complex controls
                    self.groupBox_HS_AT.setDisabled(True)
                    self.groupBox_HS_VS.setDisabled(True) 
                    self.comboBox_HS_VS_type.setCurrentIndex(-1)
                    
                else:
                    self.comboBox_HS_EC_type.setDisabled(False)
                    force_expoTypeControlLogic()
                    

                    
            else:
                #disable until a finv is selected
                self.label_HS_finvgtype.setText('select a finv on the \'Inventory\' tab')
                self.comboBox_HS_EC_type.setCurrentIndex(-1)
                self.comboBox_HS_EC_type.setDisabled(True)
                    
        #link to the finv
        self.comboBox_ivlay.layerChanged.connect(force_expoTypeLogic) 
       
        #link to the type combobox
        self.comboBox_HS_EC_type.currentTextChanged.connect(force_expoTypeControlLogic)
        
        
        #=======================================================================
        # value sampling
        #=======================================================================

        
        self.comboBox_HS_VS_type.addItems(list(self.HSvalueSamplingType_d.values()))
        self.comboBox_HS_VS_type.setCurrentIndex(-1)
        
        #statistic or field box
        def force_vsStatBox(): #populate the comboox according to the selected type
            self.comboBox_HS_VS_stat.clear()
            vlay = self.comboBox_ivlay.currentLayer()
            if isinstance(vlay,QgsVectorLayer):
                selection = self.comboBox_HS_VS_type.currentText()
                #user selected global
                if selection == self.HSvalueSamplingType_d['global']:
                    
                    self.comboBox_HS_VS_stat.addItems(['Mean','Median','Min','Max'])
                elif selection == self.HSvalueSamplingType_d['passet']:
                    self.comboBox_HS_VS_stat.addItems([f.name() for f in vlay.fields()])

                else:
                    log.debug('bad selection on comboBox_HS_VS_type: \'%s\''%selection)
            
        
        
        self.comboBox_HS_VS_type.currentTextChanged.connect(force_vsStatBox)
        
        
        
        #=======================================================================
        # #execute buttons
        #=======================================================================
        self.pushButton_HSgenerate.clicked.connect(self.run_rsamp)


        #=======================================================================
        # Raster Prep
        #=======================================================================
        #give commmon widgets
        for wName in self.RPrepDialog.inherit_atts:
            assert hasattr(self, wName), wName
            setattr(self.RPrepDialog, wName, getattr(self, wName))

        #connect launcher button
        def rpDia(): #helper to connect slots and 
            """only executing setup once called to simplify initial loading"""
            _ = self.RPrepDialog._setup()
            self.RPrepDialog.pushButton_HS_prep.clicked.connect(self.run_rPrep)
            
            self.RPrepDialog.show()
            
        self.pushButton_HS_rprep.clicked.connect(rpDia)

        #======================================================================
        # TAB: EVENT VARIABLES---------
        #======================================================================
        self.pushButton_ELstore.clicked.connect(self.set_event_vals)
        """not much here?
        
        table population is done by run_rsamp()
        """
        

        #======================================================================
        # TAB: CONDITIONAL P-----------
        #======================================================================
        """
        run_rsamp() attempts to populate this
        
        todo: rename the buttons so they align w/ the set labels
        
        todo: automatically populate the first column of boxes w/ those layers
        sampled w/ rsamp
        """
        #list of combo box names on the likelihood sampler tab
        self.ls_cb_d = { #set {hazard raster : lpol}
            1: (self.MLCB_LS1_event_3, self.MLCB_LS1_lpol_3),
            2: (self.MLCB_LS1_event_4, self.MLCB_LS1_lpol_4),
            3: (self.MLCB_LS1_event_5, self.MLCB_LS1_lpol_5),
            4: (self.MLCB_LS1_event,   self.MLCB_LS1_lpol),
            5: (self.MLCB_LS1_event_6, self.MLCB_LS1_lpol_6),
            6: (self.MLCB_LS1_event_7, self.MLCB_LS1_lpol_7),
            7: (self.MLCB_LS1_event_2, self.MLCB_LS1_lpol_2),
            8: (self.MLCB_LS1_event_8, self.MLCB_LS1_lpol_8)
            }
        
        #loop and set filteres
        first = True
        for sname, (mlcb_haz, mlcb_lpol) in self.ls_cb_d.items():
            
            #set drop down filters on hazard bars
            mlcb_haz.setFilters(QgsMapLayerProxyModel.RasterLayer)
            mlcb_haz.setAllowEmptyLayer(True)
            mlcb_haz.setCurrentIndex(-1) #set selection to none
            
            #on polygon bars
            mlcb_lpol.setFilters(QgsMapLayerProxyModel.PolygonLayer)
            mlcb_lpol.setAllowEmptyLayer(True)
            mlcb_lpol.setCurrentIndex(-1) #set selection to none
            
            #store the first lpol box for connecting the FieldName dropdown
            if first:
                mlcb_lpol_1 = mlcb_lpol
                first = False

            
        #connect to update the field name box (based on the first layer)
        def upd_lfield(): #updating the field box
            return self.mfcb_connect(
                self.mFieldComboBox_LSfn, mlcb_lpol_1.currentLayer(),
                fn_str = 'fail' )
    
        
        mlcb_lpol_1.layerChanged.connect(upd_lfield)
        
            
        #connect execute
        self.pushButton_LSsample.clicked.connect(self.run_lisamp)
        
        
        #=======================================================================
        # clear button
        #=======================================================================

                    
        self.pushButton_CP_clear.clicked.connect(self._CP_clear)
        #======================================================================
        # DTM sampler---------
        #======================================================================       
        hlpr.plug.bind_MapLayerComboBox(self.comboBox_dtm, 
                      layerType=QgsMapLayerProxyModel.RasterLayer, iface=self.iface)
        
        #attempt to select the layer during launch
        self.launch_actions['attempt dtm'] = lambda: self.comboBox_dtm.attempt_selection('dtm')
        
        
        self.pushButton_DTMsamp.clicked.connect(self.run_dsamp)
        
        #======================================================================
        # validator-----------
        #======================================================================
        self.pushButton_Validate.clicked.connect(self.run_validate)

            
        #=======================================================================
        # wrap
        #=======================================================================
        return
            


    #===========================================================================
    # HELPERS----------
    #===========================================================================
    def set_setup(self, set_cf_fp=True, set_finv=True, #attach parameters from setup tab
                  logger=None,): 
        if logger is None: logger=self.logger
        log = logger.getChild('set_setup')
        #=======================================================================
        # #call the common
        #=======================================================================
        self._set_setup(set_cf_fp=set_cf_fp)
        self.inherit_fieldNames.append('init_q_d')
        #=======================================================================
        # custom setups
        #=======================================================================
        #project aoi
        self.aoi_vlay = self.comboBox_aoi.currentLayer()
        
        #file behavior
        self.loadRes = self.checkBox_loadres.isChecked()
        
        
        #=======================================================================
        # #inventory vector layer---------
        #=======================================================================
        if set_finv:
            
            #===================================================================
            # get using sleection logic
            #===================================================================
            vlay_raw = self.comboBox_ivlay.currentLayer()
            assert not vlay_raw is None, 'must select a finv vlay'
            
            aoi_vlay = self.comboBox_aoi.currentLayer()
            
            #selected finv features
            if self.checkBox_sels.isChecked():
                assert aoi_vlay is None, 'specify \'Selected features only\' or an AOI layer'
                vlay = self.saveselectedfeatures(vlay_raw, logger=log)
                vlay.setName('%s_sels'%vlay_raw.name())
                self._set_finv(vlay)  

            #aoi slice
            elif not aoi_vlay is  None:
                self.check_aoi(aoi_vlay)
            
                vlay =  self.selectbylocation(vlay_raw, aoi_vlay, 
                                        result_type='layer', logger=log)
                
                vlay.setName('%s_aoi'%vlay_raw.name())
                self._set_finv(vlay)  
                
                
            #use the raw
            else:
                self.finv_vlay = vlay_raw
            
            vlay_raw.removeSelection()
            self.session.finv_vlay = self.finv_vlay #set for the next dialog
            #===================================================================
            # cid
            #===================================================================
            self.cid = self.mFieldComboBox_cid.currentField() #user selected fied
            self.inherit_fieldNames.append('cid')
            #===================================================================
            # checks
            #===================================================================
            self._check_finv()
            
    def _set_finv(self, vlay): #helper for finv slicing
        
        #cleaqr selection handles
        self.comboBox_aoi.setCurrentIndex(-1)
        self.checkBox_sels.setChecked(False) #uncheck
        
        
        #name check
        if len(vlay.name()) > 50:
            vlay.setName(vlay.name()[0:50])
            
        #load it
        self._load_toCanvas(vlay)
            
        #set as teh new layer
        self.comboBox_ivlay.setLayer(vlay)
        self.finv_vlay = vlay

    #===========================================================================
    # ACTIONS------
    #===========================================================================

    def build_scenario(self): #'Generate' on the setup tab
        """
        Generate a CanFlood project from scratch
        
        This tab facilitates the creation of a Control File from user specified parameters and inventory, 
            as well as providing general file control variables for the other tools in the toolset.
            
        
        
        """
        log = self.logger.getChild('build_scenario')
        log.info('build_scenario started')
        #tag = self.linEdit_ScenTag.text() #set the secnario tag from user provided name
        #wdir =  self.lineEdit_wdir.text() #pull the wd filepath from the user provided in 'Browse'
        
        #=======================================================================
        # collect inputs
        #=======================================================================

        self.set_setup(set_cf_fp=False, set_finv=False)
        prec = str(int(self.spinBox_s_prec.value())) #need a string for setting
        
        #=======================================================================
        # prechecks
        #======================================================================= 
        if self.radioButton_SS_fpRel.isChecked():
            raise Error('Relative filepaths not implemented')

        self.feedback.upd_prog(10)
            
        #=======================================================================
        # run the control file builder----
        #=======================================================================
        #initilize
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Preparor(**kwargs)
        self.feedback.upd_prog(20)
        
        #=======================================================================
        # #copy the template
        #=======================================================================
        cf_path = wrkr.copy_cf_template()
        self.feedback.upd_prog(75)
        
        #=======================================================================
        # #set some basics
        #=======================================================================
            
        wrkr.upd_cf_first(scenarioName=self.linEdit_ScenTag.text(), **{'prec':prec})
 
        log.info("default CanFlood model config file created :\n    %s"%cf_path)
        
        """NO. should only populate this automatically from ModelControlFile.Browse
        self.lineEdit_curve.setText(os.path.normpath(os.path.join(wdir, 'CanFlood - curve set 01.xls')))"""
        
        """TODO:
        write aoi filepath to scratch file
        """
        self.feedback.upd_prog(95)
        
        #=======================================================================
        # ui updates
        #=======================================================================
        
        #display the control file in the dialog
        self.lineEdit_cf_fp.setText(cf_path)
        
        #======================================================================
        # wrap
        #======================================================================

        log.push('control file created for "\'%s\''%self.tag)
        self.feedback.upd_prog(None) #set the progress bar back down to zero

    def store_curves(self): #write the curves_fp to the control file
        
        
        #=======================================================================
        # get values
        #=======================================================================
        self.set_setup(set_finv=False)
        curves_fp=self.lineEdit_curve.text()
 
        self.feedback.upd_prog(10)
        #=======================================================================
        # precheck
        #=======================================================================
        assert os.path.exists(curves_fp), 'bad curves_fp: %s'%curves_fp


        #=======================================================================
        # execute
        #=======================================================================
        #get a simple worker to handle the control file
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Preparor(**kwargs) 
        self.feedback.upd_prog(50)
        wrkr.set_cf_pars(
            {
            'dmg_fps':(
                {'curves':curves_fp}, 
                '#\'curves\' file path set from BuildDialog.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                ),
             },
            )
        
        self.feedback.upd_prog(95)
        self.feedback.upd_prog(None)
        
    def store_finv(self): #aoi slice and convert the finv vector to csv file
        log = self.logger.getChild('store_finv')
        log.debug('start')
        #=======================================================================
        # retrieve data
        #=======================================================================
        self.set_setup()
        self.feedback.upd_prog(10)
        
        #=======================================================================
        # extract, download, and update cf
        #=======================================================================
        """
        for k,v in kwargs.items():
            print(k,v)
        """
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Preparor(**kwargs) 
        
        _ = wrkr.finv_to_csv(self.finv_vlay, felv=self.comboBox_SSelv.currentText(),
                                   logger=self.logger)

        #try the curves
        """user may think this button stores the curves also"""
        try:
            self.store_curves()
        except: pass
        
        #=======================================================================
        # secondary flags
        #=======================================================================
        if self.checkBox_inv_apMiti.isChecked():
            wrkr.set_cf_pars(
                            {
                    'parameters':(
                        {'apply_miti':'True'},
                                )
                                },
                        )
        #=======================================================================
        # wrap
        #=======================================================================
        log.push('inventory vector layer stored "\'%s\''%self.finv_vlay.name())
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
        return 
    
    def construct_finv(self): #add some fields to a finv like vectoralyer

        log = self.logger.getChild('construct_finv')
        #tag = self.linEdit_ScenTag.text() #set the secnario tag from user provided name
        
        #=======================================================================
        # collect from UI----
        #=======================================================================
        """not applying aoi slices"""
        in_vlay = self.mMapLayerComboBox_inv_finv.currentLayer()
        #out_dir = self.lineEdit_wdir.text()
        self.set_setup(set_finv=False, set_cf_fp=False)
        nestID = int(self.spinBox_inv.value())
        
        def get_data(d): #helper to pull data off widgets
            new_d = dict()
            for dName, (lineEdit, reqType) in d.items():
            
                vRaw = lineEdit.text()
                if vRaw == '':continue #blank.. ksipit
                new_d[dName] = reqType(vRaw)
            
            log.debug('collected %i:  \n%s'%(len(new_d), new_d))
            return new_d
            
        #=======================================================================
        # nest data
        #=======================================================================
        nest_data = get_data({    
                'scale':(self.lineEdit_inv_scale, float),
                'elv':(self.lineEdit_inv_elv,float),
                'tag':(self.lineEdit_inv_tag, str),
                'cap':(self.lineEdit_inv_cap, float)}
                        )
        
        self.feedback.upd_prog(10)
        
        #=======================================================================
        # mitigation data
        #=======================================================================
        miti_data = get_data({    
                'mi_Lthresh':(self.lineEdit_inv_mi_Lthresh, float),
                'mi_Uthresh':(self.lineEdit_inv_mi_Uthresh,float),
                'mi_iScale':(self.lineEdit_inv_mi_iScale, str),
                'mi_iVal':(self.lineEdit_inv_mi_iVal, float)}
                        )
        
        
        #=======================================================================
        # input checks
        #=======================================================================
        assert isinstance(in_vlay, QgsVectorLayer), 'no VectorLayer selected!'

        
        #=======================================================================
        # init
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Preparor(**kwargs)
        

        #=======================================================================
        # run converter
        #=======================================================================
        nest_data2 = wrkr.build_nest_data(nestID=nestID, d_raw = nest_data)
        finv_vlay = wrkr.to_finv(in_vlay, newLayname = 'finv_%s'%in_vlay.name(),
                                new_data={**nest_data2, **miti_data})
        
        #=======================================================================
        # wrap
        #=======================================================================
        self._set_finv(finv_vlay)
        
        log.push('finished building finv from %s'%in_vlay.name())
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
    def run_rPrep(self):
        log = self.logger.getChild('run_rPrep')
        start = datetime.datetime.now()
        log.info('start \'run_rPrep\' at %s'%start)
 
        
        """the buttons have been moved onto the sub-dialog
        but we're keeping all the functions here for better integration
        treats the popout as more of an extension"""
        subDia = self.RPrepDialog 
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        self.set_setup(set_finv=False)
        rlayRaw_l = list(self.listView_expo_rlays.get_selected_layers().values())
        aoi_vlay = self.aoi_vlay

        #raster prep parameters
        clip_rlays = subDia.checkBox_HS_clip.isChecked()
        allow_download = subDia.checkBox_HS_dpConv.isChecked()
        allow_rproj = subDia.checkBox_HS_rproj.isChecked()
        scaleFactor = subDia.doubleSpinBox_HS_sf.value()

        
        #=======================================================================
        # precheck
        #=======================================================================
        
        #check rastsers
        for rlay in rlayRaw_l:
            if not isinstance(rlay, QgsRasterLayer):
                raise Error('unexpected type on raster layer')
            

        
        
        #raster prep checks
        assert isinstance(clip_rlays, bool)
        assert isinstance(allow_download, bool)
        assert isinstance(allow_rproj, bool)
        assert isinstance(scaleFactor, float)
        
        if clip_rlays:
            assert isinstance(aoi_vlay, QgsVectorLayer), 'for clip_rlays=True, must provide AOI'
            
        self.feedback.setProgress(10)
        #=======================================================================
        # execute
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Rsamp(**kwargs)
        

        #execute the tool
        rlay_l = wrkr.runPrep(rlayRaw_l, 
                        aoi_vlay = aoi_vlay,
                        clip_rlays = clip_rlays,
                        allow_download = allow_download,
                        allow_rproj = allow_rproj,
                        scaleFactor = scaleFactor,
                            )
        

        #=======================================================================
        # load results onto list widget
        #=======================================================================
        
        self.listView_expo_rlays.clear_checks()
            
            
        if self.checkBox_loadres.isChecked():
            log.debug('loading %i result layers onto widget'%len(rlay_l))
            
            for rlay in rlay_l:
                self._load_toCanvas(rlay, logger=log)
                
            #update the widget
            self.listView_expo_rlays.populate_layers() #referesh all
            self.listView_expo_rlays.check_byName([l.name() for l in rlay_l]) 



        else:
            log.warning('prepped rasters not loaded to canvas!')
             
 
             
        #=======================================================================
        # wrap
        #=======================================================================
         
        self.feedback.upd_prog(None) #set the progress bar back down to zero
 
        log.push('run_rPrep finished in %s'%(datetime.datetime.now() - start))
         
        return
        

    



    def run_rsamp(self): #execute raster sampler
        log = self.logger.getChild('run_rsamp')
        start = datetime.datetime.now()
        log.info('start \'run_rsamp\' at %s'%start)
        self.feedback.setProgress(1)
        self.set_setup(set_finv=True) #common setup routines and attachments
        #=======================================================================
        # assemble/prepare inputs-----
        #=======================================================================
        rlay_l = list(self.listView_expo_rlays.get_selected_layers().values())

        finv = self.finv_vlay #set by set_setup()
 
        
        #=======================================================================
        # #exposure configuration
        #=======================================================================
        #pull parameters from dialog
        psmp_stat, psmp_fieldName, as_inun, dtm_rlay, dthresh = self._get_rsamp_pars()
            
        self.feedback.setProgress(5)
        #=======================================================================
        # checks
        #=======================================================================
        for rlay in rlay_l:
            if not isinstance(rlay, QgsRasterLayer):
                raise Error('unexpected type on raster layer')
            assert rlay.crs()==self.qproj.crs(), 'raster layer CRS does not match project'
            

        
        self.feedback.setProgress(10)
        #======================================================================
        # execute----
        #======================================================================
        
        #build the sample
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Rsamp(**kwargs)
        

        #execute the tool
        res_vlay = wrkr.run(rlay_l, finv,
                            psmp_stat=psmp_stat, psmp_fieldName=psmp_fieldName,
                            as_inun=as_inun, dtm_rlay=dtm_rlay, dthresh=dthresh,
                            )
        
        self.feedback.setProgress(90)
        #check it
        wrkr.check()
        
        #save csv results to file
        wrkr.write_res(res_vlay, )
        
        #update ocntrol file
        wrkr.update_cf(self.cf_fp)
        
        #=======================================================================
        # plots
        #=======================================================================
        if self.checkBox_ras_pBox.isChecked():
            fig = wrkr.plot_boxes()
            self.output_fig(fig)
            
        if self.checkBox_ras_pHist.isChecked():
            fig = wrkr.plot_hist()
            self.output_fig(fig)
        
        #======================================================================
        # post---------
        #======================================================================
        """
        the hazard sampler sets up a lot of the other tools
        """
        #======================================================================
        # add to map
        #======================================================================
        if self.checkBox_loadres.isChecked():
            self._load_toCanvas(res_vlay, logger=log)

            
        #======================================================================
        # update event names
        #======================================================================
        self.event_name_set = [lay.name() for lay in rlay_l]
        
        log.info('set %i event names: \n    %s'%(len(self.event_name_set), 
                                                         self.event_name_set))
        
        #======================================================================
        # populate Event Likelihoods table
        #======================================================================
        
        l = self.event_name_set
        for tbl in [self.fieldsTable_EL]:

            tbl.setRowCount(len(l)) #add this many rows
            
            for rindx, ename in enumerate(l):
                tbl.setItem(rindx, 0, QTableWidgetItem(ename))
            
        log.info('populated tables with event names')
        self.feedback.setProgress(95)
        #======================================================================
        # populate Conditional P
        #======================================================================
        """todo: some more intelligent populating"""
        #get the mlcb
        try:
            self._CP_clear() #clear everything
            
            #loop through each of the raster layers and collcet those with 'fail' in the name
            rFail_l = []
            for rlay in rlay_l:
                if 'fail' in rlay.name():
                    rFail_l.append(rlay)

            #loop through and re-key
            rFail_d = dict()
            for indxr, rlay in enumerate(rFail_l):
                rFail_d[list(self.ls_cb_d.keys())[indxr]] = rlay
                

            #loop through each combobox pair and assign a raster to it
            res_d = dict()
            for lsKey, (mlcb_h, mlcb_v) in self.ls_cb_d.items():
                if lsKey in rFail_d:
                    mlcb_h.setLayer(rFail_d[lsKey])
                    res_d[lsKey] = rFail_d[lsKey].name()

            #wrap
            log.info('populated %i Conditional P diaglogs'%len(res_d))
 
        except Exception as e:
            log.error('failed to populate lisamp fields w/\n    %s'%e)
            
        
        #======================================================================
        # wrap
        #======================================================================
        self.feedback.upd_prog(None) #set the progress bar back down to zero

        log.push('run_rsamp finished in %s'%(datetime.datetime.now() - start))
        
        return
    
    def run_dsamp(self): #sample dtm raster
        
        self.logger.info('user pressed \'pushButton_DTMsamp\'')

        
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        self.set_setup(set_finv=True)
        rlay = self.comboBox_dtm.currentLayer()
        finv = self.finv_vlay

        psmp_stat, psmp_fieldName, as_inun, _, _ = self._get_rsamp_pars()
        self.feedback.setProgress(5)
        #======================================================================
        # precheck
        #======================================================================
        if not isinstance(rlay, QgsRasterLayer):
            raise Error('unexpected type on raster layer')

            
        #check if we got a valid sample stat
        gtype = QgsWkbTypes().displayString(finv.wkbType())
        if not 'Point' in gtype:
            assert (psmp_stat is None) or (psmp_fieldName is None), 'sampling statistic requried'
        else:
            assert (psmp_stat is None) and (psmp_fieldName is None), 'no sampling stat allowed for point type finv' 
            
        assert not as_inun, 'dtm sampler can not use area-threshold sampling'
        #======================================================================
        # execute
        #======================================================================

        #build the sample
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Rsamp(fname='gels', **kwargs)
        
        res_vlay = wrkr.run([rlay], finv,
                            psmp_stat=psmp_stat, psmp_fieldName=psmp_fieldName)
        
        #check it
        wrkr.dtm_check(res_vlay)
        
        #save csv results to file
        wrkr.write_res(res_vlay)
        
        #update ocntrol file
        wrkr.upd_cf_dtm()
        
        #======================================================================
        # add to map
        #======================================================================
        if self.checkBox_loadres.isChecked():
            self._load_toCanvas(res_vlay)
            
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        self.logger.push('dsamp finished')    
        
    def _get_rsamp_pars(self): #extract raster sampling paraeters from dialog
        
        #=======================================================================
        # get defautls
        #=======================================================================
        log = self.logger.getChild('_get_rsamp_pars')
        finv = self.finv_vlay #set by set_setup()
        gtype = QgsWkbTypes().displayString(finv.wkbType())
        
        psmp_stat, psmp_fieldName, dthresh, dtm_rlay = None, None, None, None #defaults
        as_inun = False
        
        #=======================================================================
        # build from logic and user selections
        #=======================================================================
        
        if not 'Point' in gtype:
            ec_type = dict(zip(self.hs_expoType_d.values(), self.hs_expoType_d.keys()))[
                self.comboBox_HS_EC_type.currentText()]
            #value sampling
            if ec_type == 'value':
                vs_type = dict(zip(self.HSvalueSamplingType_d.values(), self.HSvalueSamplingType_d.keys()))[self.comboBox_HS_VS_type.currentText()]
                if vs_type == 'global':
                    psmp_stat = self.comboBox_HS_VS_stat.currentText()
                    assert psmp_stat in ('Mean', 'Median', 'Min', 'Max'), 'select a valid sample statistic'
                elif vs_type == 'passet':
                    psmp_fieldName = self.comboBox_HS_VS_stat.currentText()
                else:
                    raise Error('bad vs_type: \"%s\'' % vs_type)
            #area-threshold
            elif ec_type == 'area':
                as_inun = True
                dthresh = self.mQgsDoubleSpinBox_HS.value() #depth threshold
                dtm_rlay = self.comboBox_HS_DTM.currentLayer()
                assert isinstance(dthresh, float), 'must provide a depth threshold'
                assert isinstance(dtm_rlay, QgsRasterLayer), 'must select a DTM layer'
            else:
                raise Error('bad ec_type: \"%s\'' % ec_type)
            
            
        log.debug('for gtype \'%s\' got \n'%gtype + \
                  '    psmp_stat=%s, psmp_fieldName=%s, dthresh=%s, dtm_rlay=%s'%(
                      psmp_stat, psmp_fieldName, dthresh, dtm_rlay))
            
        return psmp_stat, psmp_fieldName, as_inun, dtm_rlay, dthresh
        
    def run_lisamp(self): #liklihood polygon sampling
        
        self.logger.info('user pressed \'run_lisamp\'')
        
        
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        self.set_setup()
 
        
        lfield = self.mFieldComboBox_LSfn.currentField()
        
        #collect lpols
        lpol_d = dict()
        for sname, (mlcb_haz, mlcb_lpol) in self.ls_cb_d.items():
            hlay = mlcb_haz.currentLayer()
            
            if not isinstance(hlay, QgsRasterLayer):
                continue
            
            lpol_vlay = mlcb_lpol.currentLayer()
            
            if not isinstance(lpol_vlay, QgsVectorLayer):
                raise Error('must provide a matching VectorLayer for set %s'%sname)

            lpol_d[hlay.name()] = lpol_vlay 
            
        #get relation type
        if self.radioButton_LS_mutEx.isChecked():
            event_rels='mutEx'
        elif self.radioButton_LS_indep.isChecked():
            event_rels='indep'
        else:
            raise Error('button logic fail')
 
        #======================================================================
        # precheck
        #======================================================================
 
        if lfield is None or lfield=='':
            raise Error('must select a valid lfield')
 
        #======================================================================
        # execute
        #======================================================================
        #build the sample
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = LikeSampler(**kwargs)
        
        #connect the status bar
        #wrkr.feedback.progressChanged.connect(self.upd_prog)
        
        res_df = wrkr.run(self.finv_vlay, lpol_d,lfield=lfield, event_rels=event_rels)
        
        #check it
        wrkr.check()
        
        #save csv results to file
        wrkr.write_res(res_df)
        
        #update ocntrol file
        wrkr.update_cf()
        
        #=======================================================================
        # summary plots
        #=======================================================================
        if self.checkBox_LS_hist.isChecked():
            fig = wrkr.plot_hist()
            self.output_fig(fig)

            
        if self.checkBox_LS_box.isChecked():
            fig = wrkr.plot_boxes()
            self.output_fig(fig)
        
        #======================================================================
        # add to map
        #======================================================================
        if self.loadRes:
            res_vlay = wrkr.vectorize(res_df)
            self._load_toCanvas(res_vlay)
            
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        self.logger.push('lisamp finished')    
        
        return
        
    def _pop_el_table(self): #developing the table widget
        

        l = ['e1', 'e2', 'e3']
        tbl = self.fieldsTable_EL
        tbl.setRowCount(len(l)) #add this many rows
        
        for rindx, ename in enumerate(l):
            tbl.setItem(rindx, 0, QTableWidgetItem(ename))
            
        self.logger.push('populated likelihoods table with event names')
            
            
    
    def set_event_vals(self): #saving the event likelihoods table to file

        log = self.logger.getChild('set_event_vals')
        #log.info('user pushed \'pushButton_ELstore\'')
        
        pcoln = 'Probability'
        ecoln = 'EventName'
        #======================================================================
        # collect variables
        #======================================================================
        tag = self.linEdit_ScenTag.text() #set the secnario tag from user provided name
        #get displayed control file path
        cf_fp = self.get_cf_fp()
        out_dir = self.lineEdit_wdir.text()
        
        #likelihood paramter
        if self.radioButton_ELari.isChecked():
            event_probs = 'ari'
        else:
            event_probs = 'aep'
        self.logger.info('\'event_probs\' set to \'%s\''%event_probs)
        
        #event_rels
        if self.radioButton_EL_max.isChecked():
            event_rels = 'max'
        elif self.radioButton_EL_mutEx.isChecked():
            event_rels='mutEx'
        elif self.radioButton_EL_indep.isChecked():
            event_rels='indep'
        else:
            raise Error('event_rels radio logic fail')
        
        self.feedback.upd_prog(10)
        #======================================================================
        # collcet table data
        #======================================================================

        df = hlpr.plug.qtbl_get_df(self.fieldsTable_EL)
        
        self.logger.info('extracted data w/ %s \n%s'%(str(df.shape), df))
        
        # check it
        if df[pcoln].isna().any():
            raise Error('got %i nulls in the \'%s\' column'%(
                df[pcoln].isna().sum(), pcoln))
        
        miss_l = set(self.event_name_set).symmetric_difference(df[ecoln].values)
        if len(miss_l)>0:
            raise Error('event name mismatch')
        
        self.feedback.upd_prog(50)
        #======================================================================
        # clean it
        #======================================================================
        aep_df = df.set_index(ecoln, drop=True).T
        
        self.feedback.upd_prog(70)
        
        #======================================================================
        # #write to file
        #======================================================================
        ofn = os.path.join(self.lineEdit_wdir.text(), 'evals_%i_%s.csv'%(len(aep_df.columns), tag))
        
        from hlpr.basic import ComWrkr
        
        #build a shell worker for these taxks
        wrkr = ComWrkr(logger=log, tag=tag, feedback=self.feedback, out_dir=out_dir)
        
        eaep_fp = wrkr.output_df(aep_df, ofn, 
                                  overwrite=self.overwrite, write_index=False)
        
        
        self.feedback.upd_prog(90)
        #======================================================================
        # update the control file
        #======================================================================
        wrkr.set_cf_pars(
            {
                'parameters':({
                    'event_probs':event_probs, 'event_rels':event_rels},),
                'risk_fps':({'evals':eaep_fp}, 
                            '#evals file path set from %s.py at %s'%(
                                __name__, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')))
                          
             },
            cf_fp = cf_fp
            )
        
        
            
        self.logger.push('generated \'aeps\' and set \'event_probs\' to control file')
        self.feedback.upd_prog(None)
        
    def run_validate(self):
        """only validating the text in the control file for now (not the data objects)
        """
        log = self.logger.getChild('run_validate')
        log.info('user pressed \'pushButton_Validate\'')
        
        #======================================================================
        # collect form ui
        #======================================================================
        self._set_setup()
        
        #===================================================================
        # setup validation worker
        #===================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = Vali(**kwargs)
        

        #======================================================================
        # assemble the validation parameters
        #======================================================================
        #import the class objects
        from model.dmg2 import Dmg2
        from model.risk2 import Risk2
        from model.risk1 import Risk1
        
        #populate all possible test parameters
        vpars_all_d = {
                    'risk1':(self.checkBox_Vr1, Risk1),
                    'dmg2':(self.checkBox_Vi2, Dmg2),
                    'risk2':(self.checkBox_Vr2, Risk2),
                    #'risk3':(self.checkBox_Vr3, None), 
                                           }
        
        #loop and collect based on check boxes
        vpars_d = dict()
        for vtag, (checkBox, modObj) in vpars_all_d.items():
            if not checkBox.isChecked(): continue #skip this one
            vpars_d[vtag] = modObj
        
        self.feedback.upd_prog(10)
        
        #======================================================================
        # loop through each possibility and validate
        #======================================================================
        res_d = dict()
        for vtag, modObj in vpars_d.items():
            log.debug('checking \"%s\''%vtag)
            #===================================================================
            # parameter value/type check
            #===================================================================
            errors = wrkr.cf_check(modObj)
            

            # #report on all the errors
            for indxr, msg in enumerate(errors):
                log.warning('%s error %i: \n%s'%(vtag, indxr+1, msg))
                
            #===================================================================
            # update control file
            #===================================================================
            wrkr.cf_mark()
            
            self.feedback.upd_prog(80/len(vpars_d), method='append')
            
            #store
            if len(errors) == 0: 
                res_d[vtag] = True
            else:
                res_d[vtag] = False
            
        #=======================================================================
        # wrap
        #=======================================================================
        self.feedback.upd_prog(100)
        
        log.push('passed %i (of %i) validations. see log for errors'%(
             np.array(list(res_d.values())).sum(), len(vpars_d)
             ))
        
        self.feedback.upd_prog(None)
        return
    
    #==========================================================================
    # Helpers--------------
    #==========================================================================

    def _CP_clear(self): #clear all the drop downs
        
        for sname, (mlcb_haz, mlcb_lpol) in self.ls_cb_d.items():
            mlcb_haz.setCurrentIndex(-1) #set selection to none
            mlcb_lpol.setCurrentIndex(-1) #set selection to none
                

    

            
            
    
     
            
                    
                
            
        

            
            
             
        
        
        
                
  
 

           
            
                    
            