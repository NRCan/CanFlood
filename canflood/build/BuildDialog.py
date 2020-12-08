# -*- coding: utf-8 -*-
"""
ui class for the BUILD toolset
"""
#==============================================================================
# imports
#==============================================================================
import sys, os, warnings, tempfile, logging, configparser, datetime, time
import os.path
from shutil import copyfile

#PyQt
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

#===============================================================================
# from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QObject 
# from qgis.PyQt.QtGui import QIcon
#===============================================================================


from qgis.core import *
from qgis.analysis import *
import qgis.utils
import processing
from processing.core.Processing import Processing


import resources

import pandas as pd
import numpy as np #Im assuming if pandas is fine, numpy will be fine


#==============================================================================
# custom imports
#==============================================================================

from build.rsamp import Rsamp
from build.lisamp import LikeSampler
from build.rfda import RFDAconv
from build.npri import Npri



from hlpr.plug import *
from hlpr.Q import *
from hlpr.basic import *

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'build.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)


class DataPrep_Dialog(QtWidgets.QDialog, FORM_CLASS, QprojPlug):
    
    event_name_set = [] #event names
    

    def __init__(self, iface, parent=None):
        """these will only ini tthe first baseclass (QtWidgets.QDialog)
        
        required"""
        super(DataPrep_Dialog, self).__init__(parent)
        #super(DataPrep_Dialog, self).__init__(parent)
        self.setupUi(self)
        
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect

        self.ras = []
        self.ras_dict = {}
        self.vec = None

        self.iface = iface
        
        self.qproj_setup() #basic dialog worker setup
        
        self.connect_slots()
        
        
        self.logger.debug('DataPrep_Dialog initilized')
        

    def connect_slots(self):
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
        self.logger.statusQlab=self.progressText #connect to the progress text above the bar
        #self.logger.statusQlab.setText('BuildDialog initialized')
                
        #======================================================================
        #TAB: SETUP----------
        #======================================================================
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
        
        #AOI
        self.comboBox_aoi.setFilters(QgsMapLayerProxyModel.PolygonLayer) #SS. Project AOI
        self.comboBox_aoi.setCurrentIndex(-1) #by default, lets have this be blank
        
        #Controls
        self.checkBox_SSoverwrite.stateChanged.connect(self.set_overwrite) #SS overwrite data files

        
        #CanFlood Control File
        def browse_cf():
            return self.browse_button(self.lineEdit_cf_fp, prompt='Select CanFlood control file',
                           qfd=QFileDialog.getOpenFileName)
            
        self.pushButton_cf.clicked.connect(browse_cf)# SS. Model Control File. Browse
        

        
        
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
        # Store IVlayer
        #=======================================================================
        #inventory vector layer box
        self.comboBox_ivlay.setFilters(QgsMapLayerProxyModel.VectorLayer) #SS. Inventory Layer: Drop down
        


        #find a good layer
        try:
            for layname, vlay in vlays_d.items():
                if layname.startswith('finv'):
                    break
            
            self.logger.debug('setting comboBox_vec = %s'%vlay.name())
            self.comboBox_ivlay.setLayer(vlay)
        except Exception as e:
            self.logger.debug('failed to set inventory layer w: \n    %s'%e)
            

        #index field name
        #change the 'cid' display when the finv selection changes
        def upd_cid():
            return self.mfcb_connect(
                self.mFieldComboBox_cid, self.comboBox_ivlay.currentLayer(),
                fn_str = 'xid' )
                
        self.comboBox_ivlay.layerChanged.connect(upd_cid) #SS inventory vector layer
        
        #connect button
        self.pushButton_Inv_store.clicked.connect(self.convert_finv)
        
        
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
        # NRPI
        #=======================================================================
        #filter the vector layer
        self.mMapLayerComboBox_inv_nrpi.setFilters(QgsMapLayerProxyModel.VectorLayer) 
        self.mMapLayerComboBox_inv_nrpi.setCurrentIndex(-1) #clear the selection
        
        #connect the push button
        self.pushButton_inv_nrpi.clicked.connect(self.convert_nrpi)



        #======================================================================
        # TAB: HAZARD SAMPLER---------
        #======================================================================
        # Set GUI elements
        self.comboBox_ras.setFilters(QgsMapLayerProxyModel.RasterLayer)
        """
        todo: swap this out with better selection widget
        """
        #selection       
        self.pushButton_remove.clicked.connect(self.remove_text_edit)
        self.pushButton_clear.clicked.connect(self.clear_text_edit)
        self.pushButton_add_all.clicked.connect(self.add_all_text_edit)
        
        self.comboBox_ras.currentTextChanged.connect(self.add_ras)
        
        #=======================================================================
        # inundation
        #=======================================================================
        self.comboBox_HS_DTM.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.comboBox_HS_DTM.setAllowEmptyLayer(True)
        self.comboBox_HS_DTM.setCurrentIndex(-1) #set selection to none
        #=======================================================================
        # #complex
        #=======================================================================
        #display the gtype when the finv changes
        def upd_gtype():
            vlay = self.comboBox_ivlay.currentLayer()
            if isinstance(vlay,QgsVectorLayer):
                gtype = QgsWkbTypes().displayString(vlay.wkbType())
                self.label_HS_finvgtype.setText(gtype)
            
        self.comboBox_ivlay.layerChanged.connect(upd_gtype) #SS inventory vector layer
        
        #display sampling stats options to user 
        def upd_stat():
            vlay = self.comboBox_ivlay.currentLayer()
            self.comboBox_HS_stat.clear()
            if isinstance(vlay,QgsVectorLayer):
                gtype = QgsWkbTypes().displayString(vlay.wkbType())
                self.comboBox_HS_stat.setCurrentIndex(-1)
                
                if 'Polygon' in gtype or 'Line' in gtype:
                    self.comboBox_HS_stat.addItems(
                        ['','Mean','Median','Min','Max'])
                
        self.comboBox_ivlay.layerChanged.connect(upd_stat) #SS inventory vector layer
            
            
        #disable sample stats when %inundation is checked
        def tog_SampStat(): #toggle the sample stat dropdown
            pstate = self.checkBox_HS_in.isChecked()
            #if checked, enable the second box
            self.comboBox_HS_stat.setDisabled(pstate) #disable it
            self.comboBox_HS_stat.setCurrentIndex(-1) #set selection to none
            
        self.checkBox_HS_in.stateChanged.connect(tog_SampStat)
        
        
        #=======================================================================
        # #execute
        #=======================================================================
        self.pushButton_HSgenerate.clicked.connect(self.run_rsamp)
        
        #======================================================================
        # event likelihoods
        #======================================================================
        self.pushButton_ELstore.clicked.connect(self.set_event_vals)
        
        """dev button
        self.pushButton_ELdev.clicked.connect(self._pop_el_table)"""
        
        
        #======================================================================
        # Conditional Probabilities-----------
        #======================================================================
        """todo: rename the buttons so they align w/ the set labels
        
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
                    
        #======================================================================
        # DTM sampler---------
        #======================================================================
        self.comboBox_dtm.setFilters(QgsMapLayerProxyModel.RasterLayer)
        self.pushButton_DTMsamp.clicked.connect(self.run_dsamp)
        
        #======================================================================
        # validator-----------
        #======================================================================
        self.pushButton_Validate.clicked.connect(self.run_validate)
        




        
        #======================================================================
        # defaults-----------
        #======================================================================
        """"
        to speed up testing.. manually configure the project
        """

        debug_dir =os.path.join(os.path.expanduser('~'), 'CanFlood', 'build')
        #self.lineEdit_cf_fp.setText(os.path.join(debug_dir, 'CanFlood_scenario1.txt'))
        self.lineEdit_wd.setText(debug_dir)
        
        if not os.path.exists(debug_dir):
            log.info('building directory: %s'%debug_dir)
            os.makedirs(debug_dir)
            
        #=======================================================================
        # wrap
        #=======================================================================
            
        
        
        
        
        


    #==========================================================================
    # Layer Loading---------------
    #==========================================================================
    def add_ras(self):
        x = [str(self.listWidget_ras.item(i).text()) for i in range(self.listWidget_ras.count())]
        self.ras_dict.update({ (self.comboBox_ras.currentText()) : (self.comboBox_ras.currentLayer()) })
        if (self.comboBox_ras.currentText()) not in x:
            self.listWidget_ras.addItem(self.comboBox_ras.currentText())
            self.ras_dict.update({ (self.comboBox_ras.currentText()) : (self.comboBox_ras.currentLayer()) })
        
    def clear_text_edit(self):
        if len(self.ras_dict) > 0:
            self.listWidget_ras.clear()
            self.ras_dict = {}
    
    def remove_text_edit(self):
        if (self.listWidget_ras.currentItem()) is not None:
            value = self.listWidget_ras.currentItem().text()
            item = self.listWidget_ras.takeItem(self.listWidget_ras.currentRow())
            item = None
            for k in list(self.ras_dict):
                if k == value:
                    self.ras_dict.pop(value)

    def add_all_text_edit(self):
        layers = self.iface.mapCanvas().layers()
        #layers_vec = [layer for layer in layers if layer.type() == QgsMapLayer.VectorLayer]
        layers_ras = [layer for layer in layers if layer.type() == QgsMapLayer.RasterLayer]
        x = [str(self.listWidget_ras.item(i).text()) for i in range(self.listWidget_ras.count())]
        for layer in layers_ras:
            if (layer.name()) not in x:
                self.ras_dict.update( { layer.name() : layer} )
                self.listWidget_ras.addItem(str(layer.name()))

    #===========================================================================
    # common methods----------
    #===========================================================================
    def slice_aoi(self, vlay):
        
        aoi_vlay = self.comboBox_aoi.currentLayer()
        log = self.logger.getChild('slice_aoi')
        
        
        #=======================================================================
        # selection
        #=======================================================================
        if self.checkBox_sels.isChecked():
            if not aoi_vlay is None: 
                raise Error('only one method of aoi selection is allowed')
            
            log.info('slicing finv \'%s\' w/ %i selected feats'%(
                vlay.name(), vlay.selectedFeatureCount()))
            
            res_vlay = self.saveselectedfeatures(vlay, logger=log)
        #=======================================================================
        # check for no selection
        #=======================================================================
        elif aoi_vlay is None:
            log.debug('no aoi selected... not slicing')
            return vlay

        #=======================================================================
        # slice
        #=======================================================================
        else:
            vlay.removeSelection()
            log.info('slicing finv \'%s\' and %i feats w/ aoi \'%s\''%(
                vlay.name(),vlay.dataProvider().featureCount(), aoi_vlay.name()))
            
            res_vlay =  self.selectbylocation(vlay, aoi_vlay, result_type='layer', logger=log)
            
            assert isinstance(res_vlay, QgsVectorLayer)
            
            vlay.removeSelection()
        
        #=======================================================================
        # wrap
        #=======================================================================
        if self.checkBox_loadres.isChecked():
            self.qproj.addMapLayer(res_vlay)
            self.logger.info('added \'%s\' to canvas'%res_vlay.name())
            
        
            
        return res_vlay
            
            


    def build_scenario(self): #'Generate' on the setup tab
        """
        Generate a CanFlood project from scratch
        
        This tab facilitates the creation of a Control File from user specified parameters and inventory, 
            as well as providing general file control variables for the other tools in the toolset.
            
        
        
        """
        log = self.logger.getChild('build_scenario')
        log.info('build_scenario started')
        self.tag = self.linEdit_ScenTag.text() #set the secnario tag from user provided name
        """
        todo: make a fresh pull of this for each tool
        """
        
        self.wd =  self.lineEdit_wd.text() #pull the wd filepath from the user provided in 'Browse'
        

        #=======================================================================
        # prechecks
        #=======================================================================
        assert isinstance(self.wd, str)
        
        assert isinstance(self.tag, str)

        
        if not os.path.exists(self.wd):
            os.makedirs(self.wd)
            log.info('built working directory: %s'%self.wd)
            
        
        #======================================================================
        # build the control file
        #======================================================================
        
        
        self.feedback.upd_prog(50)
        
        #called by build_scenario()
        dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        #get the default template from the program files
        cf_src = os.path.join(dirname, '_pars/CanFlood_control_01.txt')
        assert os.path.exists(cf_src)

        
        #get control file name from user provided tag
        cf_fn = 'CanFlood_%s.txt'%self.tag
        cf_path = os.path.join(self.wd, cf_fn)

        
        #see if this exists
        if os.path.exists(cf_path):
            msg = 'generated control file already exists. overwrite=%s \n     %s'%(
                self.overwrite, cf_path)
            if self.overwrite:
                log.warning(msg)
            else:
                raise Error(msg)
            
        
        #copy over the default template
        copyfile(cf_src, cf_path)
            

        self.feedback.upd_prog(75)
        #======================================================================
        # update the control file
        #======================================================================
        """todo: switch over to helper function"""
        pars = configparser.ConfigParser(allow_no_value=True)
        _ = pars.read(cf_path) #read it from the new location
        
        #parameters
        
        pars.set('parameters', 'name', self.tag) #user selected field
        pars.set('parameters', 'felv', self.comboBox_SSelv.currentText()) #user selected field
        
        #damage curves
        dmg_fps = self.lineEdit_curve.text()
        if dmg_fps == '':
            pass
        else:
            assert os.path.exists(dmg_fps), 'bad dmg_fps: %s'%dmg_fps
            pars.set('dmg_fps', 'curves', dmg_fps)
        
        
        
        #set note
        pars.set('parameters', '#control file template created from \'scenario setup\' on  %s'%(
            datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')
            ))
        
        #write the config file 
        with open(cf_path, 'w') as configfile:
            pars.write(configfile)
            
        log.info("default CanFlood model config file created :\n    %s"%cf_path)
        
        """NO. should only populate this automatically from ModelControlFile.Browse
        self.lineEdit_curve.setText(os.path.normpath(os.path.join(self.wd, 'CanFlood - curve set 01.xls')))"""
        
        """TODO:
        write aoi filepath to scratch file
        """
        self.feedback.upd_prog(95)
        #======================================================================
        # wrap
        #======================================================================
        
        #display the control file in the dialog
        self.lineEdit_cf_fp.setText(cf_path)
        
        """not sure what this is
        self.lineEdit_control_2.setText(os.path.normpath(os.path.join(self.wd, 'CanFlood_control_01.txt')))"""
        
        log.push('control file created for "\'%s\''%self.tag)
        self.feedback.upd_prog(None) #set the progress bar back down to zero

        
    def convert_finv(self): #aoi slice and convert the finv vector to csv file
        
        
        log = self.logger.getChild('convert_finv')
        log.info('started')
        self.feedback.upd_prog(10)
        
        
        #=======================================================================
        # retrieve data
        #=======================================================================
        cid = self.mFieldComboBox_cid.currentField() #user selected field
        
        vlay_raw = self.comboBox_ivlay.currentLayer()
        
        cf_fp = self.get_cf_fp()
        

        #======================================================================
        # prechecks
        #======================================================================
        assert isinstance(vlay_raw, QgsVectorLayer), 'must select a VectorLayer'
        assert os.path.exists(cf_fp), 'bad cf_fp: %s'%cf_fp
        
        
        #check cid
        assert isinstance(cid, str)
        if cid == '':
            raise Error('must specify a cid') 
        if cid in self.invalid_cids:
            raise Error('user selected invalid cid \'%s\''%cid)  
        
        assert cid in [field.name() for field in vlay_raw.fields()]
        
        
        
        #=======================================================================
        # aoi slice
        #=======================================================================
        vlay = self.slice_aoi(vlay_raw)
        
        
        if self.checkBox_loadres.isChecked():
            self.qproj.addMapLayer(vlay)
            self.logger.info('added \'%s\' to canvas'%vlay.name())
        
        

        self.feedback.upd_prog(30)
        #=======================================================================
        # #extract data
        #=======================================================================
        
        log.info('extracting data on \'%s\' w/ %i feats'%(
            vlay.name(), vlay.dataProvider().featureCount()))
                
        df = vlay_get_fdf(vlay, feedback=self.feedback)
          
        #drop geometery indexes
        for gindx in self.invalid_cids:   
            df = df.drop(gindx, axis=1, errors='ignore')
            
        #more cid checks
        if not cid in df.columns:
            raise Error('cid not found in finv_df')
        
        assert df[cid].is_unique
        assert 'int' in df[cid].dtypes.name
        
        self.feedback.upd_prog(50)
        #=======================================================================
        # #write to file
        #=======================================================================
        out_fp = os.path.join(self.wd, 'finv_%s_%s.csv'%(self.tag, vlay.name()))
        
        #see if this exists
        if os.path.exists(out_fp):
            msg = 'generated finv.csv already exists. overwrite=%s \n     %s'%(
                self.overwrite, out_fp)
            if self.overwrite:
                log.warning(msg)
            else:
                raise Error(msg)
            
            
        df.to_csv(out_fp, index=False)  
        
        log.info("inventory csv written to file:\n    %s"%out_fp)
        
        self.feedback.upd_prog(80)
        #=======================================================================
        # write to control file
        #=======================================================================
        assert os.path.exists(out_fp)

        
        self.update_cf(
            {
            'dmg_fps':(
                {'finv':out_fp}, 
                '#\'finv\' file path set from BuildDialog.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                ),
            'parameters':(
                {'cid':str(cid)},
                )
             },
            cf_fp = cf_fp
            )
        
        self.feedback.upd_prog(99)
        #=======================================================================
        # wrap
        #=======================================================================
        log.push('inventory vector layer stored "\'%s\''%vlay.name())
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
        return out_fp
    
    
    def convert_rfda(self): #Other.Rfda tab
        log = self.logger.getChild('convert_rfda')
        
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
        
        
        #======================================================================
        # input checks
        #======================================================================
        
        wrkr = RFDAconv(logger=self.logger, out_dir=out_dir, tag=self.tag, bsmt_ht = bsmt_ht)
        #======================================================================
        # invnentory convert
        #======================================================================
        if isinstance(rinv_vlay, QgsVectorLayer):
            
            
            finv_vlay = wrkr.to_finv(rinv_vlay)
            
            self.qproj.addMapLayer(finv_vlay)
            log.info('added \'%s\' to canvas'%finv_vlay.name())
            
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
            
        #======================================================================
        # wrap
        #======================================================================
        self.logger.push('finished')
            

    def convert_nrpi(self):
        log = self.logger.getChild('convert_nrpi')
        
        #=======================================================================
        # collect from UI
        #=======================================================================
        in_vlay = self.mMapLayerComboBox_inv_nrpi.currentLayer()
        out_dir = self.lineEdit_wd.text()
        
        #=======================================================================
        # input checks
        #=======================================================================
        wrkr = Nrpi(logger=self.logger,  out_dir=out_dir, tag=self.tag)
        assert isinstance(in_vlay, QgsVectorLayer), 'no VectorLayer selected!'
        
        #=======================================================================
        # aoi slice
        #=======================================================================
        in_vlay_aoi = self.slice_aoi(in_vlay)
        
                
        #=======================================================================
        # run converter
        #=======================================================================
        
        
        finv_vlay = wrkr.to_finv(in_vlay_aoi)
        
        #=======================================================================
        # wrap
        #=======================================================================
        self.qproj.addMapLayer(finv_vlay)
        log.info('added \'%s\' to canvas'%finv_vlay.name())
        
        log.push('finished NRPI conversion')
        self.feedback.upd_prog(None) #set the progress bar back down to zero

    
    def run_rsamp(self): #execute rsamp
        log = self.logger.getChild('run_rsamp')
        start = datetime.datetime.now()
        log.info('user pressed \'pushButton_HSgenerate\'')
        
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        finv_raw = self.comboBox_ivlay.currentLayer()
        rlay_l = list(self.ras_dict.values())
        
        crs = self.qproj.crs()

        cf_fp = self.get_cf_fp()
        out_dir = self.lineEdit_wd.text()
        

        #update some parameters
        cid = self.mFieldComboBox_cid.currentField() #user selected field
        psmp_stat = self.comboBox_HS_stat.currentText()
        
        #inundation
        as_inun = self.checkBox_HS_in.isChecked()
        
        if as_inun:
            dthresh = self.mQgsDoubleSpinBox_HS.value()
            dtm_rlay=self.comboBox_HS_DTM.currentLayer()
            
            assert isinstance(dthresh, float), 'must provide a depth threshold'
            assert isinstance(dtm_rlay, QgsRasterLayer), 'must select a DTM layer'
            
        else:
            dthresh, dtm_rlay = None, None
            
        
        #=======================================================================
        # slice aoi
        #=======================================================================
        finv = self.slice_aoi(finv_raw)

        #======================================================================
        # precheck
        #======================================================================
        if finv is None:
            raise Error('got nothing for finv')
        if not isinstance(finv, QgsVectorLayer):
            raise Error('did not get a vector layer for finv')
        
        gtype = QgsWkbTypes().displayString(finv.wkbType())
        
        for rlay in rlay_l:
            if not isinstance(rlay, QgsRasterLayer):
                raise Error('unexpected type on raster layer')
            
        if not os.path.exists(out_dir):
            raise Error('working directory does not exist:  %s'%out_dir)
        
        if cid is None or cid=='':
            raise Error('need to select a cid')
        
        if not cid in [field.name() for field in finv.fields()]:
            raise Error('requested cid field \'%s\' not found on the finv_raw'%cid)
        

        assert os.path.exists(cf_fp), 'bad control file specified'
        
        #geometry specific input checks
        if 'Polygon' in gtype or 'Line' in gtype:
            if not as_inun:
                assert psmp_stat in ('Mean','Median','Min','Max'), 'select a valid sample statistic'
            else:
                assert psmp_stat == '', 'expects no sample statistic for %Inundation'
        elif 'Point' in gtype:
            assert not as_inun, '%Inundation only valid for polygon type geometries'
        else:
            raise Error('unrecognized gtype: %s'%gtype)
        #======================================================================
        # execute
        #======================================================================

        #build the sample
        wrkr = Rsamp(logger=self.logger, 
                          tag = self.tag, #set by build_scenario() 
                          feedback = self.feedback, #let the instance build its own feedback worker
                          cid=cid,crs = crs,
                          out_dir = out_dir
                          )
        
        """try just passing the Dialog's feedback
        #connect the status bar to the worker's feedback
        wrkr.feedback.progressChanged.connect(self.upd_prog)"""
        
        
        
        #execute the tool
        res_vlay = wrkr.run(rlay_l, finv,
                            psmp_stat=psmp_stat,
                            as_inun=as_inun, dtm_rlay=dtm_rlay, dthresh=dthresh)
        
        #check it
        wrkr.check()
        
        #save csv results to file
        wrkr.write_res(res_vlay, )
        
        #update ocntrol file
        wrkr.upd_cf(cf_fp)
        
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
            self.qproj.addMapLayer(res_vlay)
            self.logger.info('added \'%s\' to canvas'%res_vlay.name())
            
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
        
        #======================================================================
        # populate lisamp
        #======================================================================
        
        #get the mlcb
        try:
            rlay_d = {indxr: rlay for indxr, rlay in enumerate(rlay_l)}
            
            for indxr, (sname, (mlcb_h, mlcb_v)) in enumerate(self.ls_cb_d.items()):
                if indxr in rlay_d:
                    mlcb_h.setLayer(rlay_l[indxr])
                    
                else:
                    """
                    todo: clear the remaining comboboxes
                    """
                    break


        except Exception as e:
            log.error('failed to populate lisamp fields w/\n    %s'%e)
            
        
        #======================================================================
        # wrap
        #======================================================================
        self.feedback.upd_prog(None) #set the progress bar back down to zero

        log.push('Rsamp finished in %s'%(datetime.datetime.now() - start))
        
        return
    
    def run_dsamp(self): #sample dtm raster
        
        self.logger.info('user pressed \'pushButton_DTMsamp\'')

        
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        
        finv_raw = self.comboBox_ivlay.currentLayer()
        rlay = self.comboBox_dtm.currentLayer()
        
        crs = self.qproj.crs()

        cf_fp = self.get_cf_fp()
        out_dir = self.lineEdit_wd.text()
        

        #update some parameters
        cid = self.mFieldComboBox_cid.currentField() #user selected field
        psmp_stat = self.comboBox_HS_stat.currentText()
        

        #======================================================================
        # aoi slice
        #======================================================================
        finv = self.slice_aoi(finv_raw)
        

        #======================================================================
        # precheck
        #======================================================================
                
        if finv is None:
            raise Error('got nothing for finv')
        if not isinstance(finv, QgsVectorLayer):
            raise Error('did not get a vector layer for finv')
        

        if not isinstance(rlay, QgsRasterLayer):
            raise Error('unexpected type on raster layer')
            
        if not os.path.exists(out_dir):
            raise Error('working directory does not exist:  %s'%out_dir)
        
        if cid is None or cid=='':
            raise Error('need to select a cid')
        
        if not cid in [field.name() for field in finv.fields()]:
            raise Error('requested cid field \'%s\' not found on the finv_raw'%cid)
            
        #check if we got a valid sample stat
        gtype = QgsWkbTypes().displayString(finv.wkbType())
        if not 'Point' in gtype:
            assert not psmp_stat=='', \
            'for %s type finvs must specifcy a sample statistic on the Hazard Sampler tab'%gtype
            """the module does a more robust check"""
        #======================================================================
        # execute
        #======================================================================

        #build the sample
        wrkr = Rsamp(logger=self.logger, 
                          tag=self.tag, #set by build_scenario() 
                          feedback = self.feedback, #needs to be connected to progress bar
                          cid=cid,crs=crs, 
                          out_dir = out_dir, fname='gels'
                          )
        
        
        #connect the status bar
        #wrkr.feedback.progressChanged.connect(self.upd_prog)
        
        res_vlay = wrkr.run([rlay], finv, psmp_stat=psmp_stat)
        
        #check it
        wrkr.dtm_check(res_vlay)
        
        #save csv results to file
        wrkr.write_res(res_vlay, out_dir = out_dir)
        
        #update ocntrol file
        wrkr.update_cf({
            'dmg_fps':(
                {'gels':wrkr.out_fp},
                '#\'gels\' file path set from rsamp.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                    ),
            'parameters':(
                {'felv':'ground'},                
                )
            
                    },cf_fp)
        
        #======================================================================
        # add to map
        #======================================================================
        if self.checkBox_loadres.isChecked():
            self.qproj.addMapLayer(finv)
            self.logger.info('added \'%s\' to canvas'%finv.name())
            
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        self.logger.push('dsamp finished')    
        
    def run_lisamp(self): #sample dtm raster
        
        self.logger.info('user pressed \'pushButton_DTMsamp\'')

        
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        finv_raw = self.comboBox_ivlay.currentLayer()
        crs = self.qproj.crs()
        cf_fp = self.get_cf_fp()
        out_dir = self.lineEdit_wd.text()
        cid = self.mFieldComboBox_cid.currentField() #user selected field
        
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
            
        #======================================================================
        # aoi slice
        #======================================================================
        finv = self.slice_aoi(finv_raw)
        

        #======================================================================
        # precheck
        #======================================================================
                
        if finv is None:
            raise Error('got nothing for finv')
        if not isinstance(finv, QgsVectorLayer):
            raise Error('did not get a vector layer for finv')
                    
        if not os.path.exists(out_dir):
            raise Error('working directory does not exist:  %s'%out_dir)
        
        if cid is None or cid=='':
            raise Error('need to select a cid')
        
        if lfield is None or lfield=='':
            raise Error('must select a valid lfield')
        
        if not cid in [field.name() for field in finv.fields()]:
            raise Error('requested cid field \'%s\' not found on the finv_raw'%cid)
            
        
        
        #======================================================================
        # execute
        #======================================================================

        #build the sample
        wrkr = LikeSampler(logger=self.logger, 
                          tag=self.tag, #set by build_scenario() 
                          feedback = self.feedback, #needs to be connected to progress bar
                          crs = crs,
                          )
        
        #connect the status bar
        #wrkr.feedback.progressChanged.connect(self.upd_prog)
        
        res_df = wrkr.run(finv, lpol_d, cid=cid, lfield=lfield)
        
        #check it
        wrkr.check()
        
        #save csv results to file
        wrkr.write_res(res_df, out_dir = out_dir)
        
        #update ocntrol file
        wrkr.upd_cf(cf_fp)
        
        #======================================================================
        # add to map
        #======================================================================
        if self.checkBox_loadres.isChecked():
            res_vlay = wrkr.vectorize(res_df)
            self.qproj.addMapLayer(res_vlay)
            self.logger.info('added \'%s\' to canvas'%finv.name())
            
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
        """store user specified event variables into the 'evals' dataset
        
        
        """
        log = self.logger.getChild('set_event_vals')
        log.info('user pushed \'pushButton_ELstore\'')
        

        #======================================================================
        # collect variables
        #======================================================================
        #get displayed control file path
        cf_fp = self.get_cf_fp()
        out_dir = self.lineEdit_wd.text()
        
        #likelihood paramter
        if self.radioButton_ELari.isChecked():
            event_probs = 'ari'
        else:
            event_probs = 'aep'
        self.logger.info('\'event_probs\' set to \'%s\''%event_probs)
        
        
        #======================================================================
        # collcet table data
        #======================================================================

        df = qtbl_get_df(self.fieldsTable_EL)
        
        self.logger.info('extracted data w/ %s \n%s'%(str(df.shape), df))
        
        # check it
        if df.iloc[:, 1].isna().any():
            raise Error('got %i nulls in the likelihood column'%df.iloc[:,1].isna().sum())
        
        miss_l = set(self.event_name_set).symmetric_difference(df.iloc[:,0].values)
        if len(miss_l)>0:
            raise Error('event name mismatch')
        
        
        #======================================================================
        # clean it
        #======================================================================
        aep_df = df.set_index(df.columns[0]).iloc[:,0].to_frame().T
        

        
        #======================================================================
        # #write to file
        #======================================================================
        ofn = os.path.join(self.lineEdit_wd.text(), 'evals_%i_%s.csv'%(len(aep_df.columns), self.tag))
        
        from hlpr.Q import Qcoms
        #build a shell worker for these taxks
        wrkr = Qcoms(logger=log, tag=self.tag, feedback=self.feedback, out_dir=out_dir)
        
        eaep_fp = wrkr.output_df(aep_df, ofn, 
                                  overwrite=self.overwrite, write_index=False)
        
        
        
        #======================================================================
        # update the control file
        #======================================================================
        wrkr.update_cf(
            {
                'parameters':({'event_probs':event_probs},),
                'risk_fps':({'evals':eaep_fp}, 
                            '#evals file path set from %s.py at %s'%(
                                __name__, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')))
                          
             },
            cf_fp = cf_fp
            )
        
        
            
        self.logger.push('generated \'aeps\' and set \'event_probs\' to control file')
        
    def run_validate(self):
        #raise Error('broken')
        """
        a lot of this is duplicated in  model.scripts_.setup_pars
        
        TODO: consolidate with setup_pars
        move to separate module
        
        """
        log = self.logger.getChild('valid')
        log.info('user pressed \'pushButton_Validate\'')
        
        #======================================================================
        # load the control file
        #======================================================================
        #get the control file path
        cf_fp = self.get_cf_fp()
        
        #build/run theparser
        log.info('validating control file: \n    %s'%cf_fp)
        pars = configparser.ConfigParser(inline_comment_prefixes='#', allow_no_value=True)
        _ = pars.read(cf_fp) #read it
        
        self.feedback.upd_prog(10)
        #======================================================================
        # assemble the validation parameters
        #======================================================================
        #import the class objects
        from model.dmg2 import Dmg2
        from model.risk2 import Risk2
        from model.risk1 import Risk1
        
        #populate all possible test parameters
        """
        todo: finish this
        """
        vpars_pos_d = {
                    'risk1':(self.checkBox_Vr1, Risk1),
                   'dmg2':(self.checkBox_Vi2, Dmg2),
                   'risk2':(self.checkBox_Vr2, Risk2),
                   #'risk3':(self.checkBox_Vr3, (None, None, None)),
                                           }
        
        #select based on user check boxes
        vpars_d = dict()
        
        for vtag, (checkBox, model) in vpars_pos_d.items():
            
            if checkBox.isChecked():
                vpars_d[vtag] = model
                
        if len(vpars_d) == 0:
            raise Error('no validation options selected!')
        
        log.info('user selected %i validation parameter sets'%len(vpars_d))
        
        #======================================================================
        # validate
        #======================================================================

        
        vflag_d = dict()
        for vtag, model in vpars_d.items():
            self.feedback.upd_prog(80/len(vpars_d), method='append')

            """needto play with init sequences to get this to work"""

                    
            #==================================================================
            # set validation flag
            #==================================================================
            vflag_d[model.valid_par] = 'True'
            
        #======================================================================
        # update control file
        #======================================================================
        self.update_cf(
            {'validation':(vflag_d, )
             },
            cf_fp = cf_fp
            )
        self.feedback.upd_prog(100)
        
        log.push('completed %i validations'%len(vpars_d))
        
        self.feedback.upd_prog(None)
        return
    

            
            
    
     
            
                    
                
            
        

            
            
             
        
        
        
                
  
 

           
            
                    
            