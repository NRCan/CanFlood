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

#qgis
from PyQt5 import uic
from PyQt5 import QtWidgets

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QObject 
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

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

from build.wsamp import Rsamp
from build.lisamp import LikeSampler
from build.oth_rfda import RFDAconv

#from canFlood_model import CanFlood_Model
#import hp

from hlpr.plug import *
from hlpr.Q import *
from hlpr.basic import *

# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'build.ui')
assert os.path.exists(ui_fp)
FORM_CLASS, _ = uic.loadUiType(ui_fp)


class DataPrep_Dialog(QtWidgets.QDialog, FORM_CLASS, QprojPlug):
    
    event_name_set = [] #event names
    
    invalid_cids = ['fid', 'ogc_fid']
    
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
        
        self.qproj_setup()
        

        
        """todo: connect this with status bar?"""
        self.feedback = QgsProcessingFeedback()
        
        self.connect_slots()
        

    def connect_slots(self):
        
        #self.testit()
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
        #=======================================================================
        # def test():
        #     self.logger.push('test button pushed')
        #     
        #     for i in range(10):
        #         time.sleep(.5)
        #         self.progressBar.setValue(i + 1)
        #         
        #     self.logger.push('finished')
        #=======================================================================
        #ok/cancel buttons
        self.buttonBox.accepted.connect(self.reject)
        self.buttonBox.rejected.connect(self.reject)
        
        
        #connect to status label
        self.logger.statusQlab=self.progressText
        self.logger.statusQlab.setText('BuildDialog initialized')
                
        #======================================================================
        # scenario setup tab----------
        #======================================================================
        #populate guis
        self.comboBox_vec.setFilters(QgsMapLayerProxyModel.VectorLayer) #SS. Inventory Layer: Drop down
        self.comboBox_aoi.setFilters(QgsMapLayerProxyModel.VectorLayer) #SS. Project AOI
        self.comboBox_SSelv.addItems(['datum', 'ground']) #ss elevation type
               
        
        #Working Directory browse
        def browse_wd():
            return self.browse_button(self.lineEdit_wd, prompt='Select Working Directory',
                                      qfd = QFileDialog.getExistingDirectory)
            
        self.pushButton_wd.clicked.connect(browse_wd) # SS. Working Dir. Browse
        
        #WD force open
        def open_wd():
            force_open_dir(self.lineEdit_wd.text())
        
        self.pushButton_wd_open.clicked.connect(open_wd)
        
        #======================================================================
        # #Inventory Vector Layer
        #======================================================================
        #change the 'cid' display when the finv selection changes
        def upd_cid():
            return self.mfcb_connect(
                self.mFieldComboBox_cid, self.comboBox_vec.currentLayer(),
                fn_str = 'id' )
                
        self.comboBox_vec.layerChanged.connect(upd_cid) #SS inventory vector layer
        
        #find a good layer
        try:
            for layname, vlay in vlays_d.items():
                if layname.startswith('finv'):
                    break
            
            self.logger.info('setting comboBox_vec = %s'%vlay.name())
            self.comboBox_vec.setLayer(vlay)
        except Exception as e:
            self.logger.warning('failed to set inventory layer w: \n    %s'%e)
        
        #Vulnerability Curve Set
        def browse_curves():
            return self.browse_button(self.lineEdit_curve, prompt='Select Curve Set',
                                      qfd = QFileDialog.getOpenFileName)
            
        self.pushButton_SScurves.clicked.connect(browse_curves)# SS. Vuln Curve Set. Browse
        
        #program controls
        self.checkBox_SSoverwrite.stateChanged.connect(self.set_overwrite) #SS overwrite data files
        
        #generate new control file      
        self.pushButton_generate.clicked.connect(self.build_scenario) #SS. generate
        
        #CanFlood Control File
        def browse_cf():
            return self.browse_button(self.lineEdit_cf_fp, prompt='Select CanFlood control file',
                           qfd=QFileDialog.getOpenFileName)
            
        self.pushButton_cf.clicked.connect(browse_cf)# SS. Model Control File. Browse
        
        #======================================================================
        # hazard sampler---------
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
        #connect dtm layer name to display box
        def upd_dtmlayname():
            vlay = self.comboBox_dtm.currentLayer()
            if isinstance(vlay,QgsVectorLayer):
                self.label_HS_dtmln.setText(vlay.name())
                
        self.comboBox_dtm.layerChanged.connect(upd_dtmlayname)
            

        #=======================================================================
        # #complex
        #=======================================================================
        #display the gtype when the finv changes
        def upd_gtype():
            vlay = self.comboBox_vec.currentLayer()
            if isinstance(vlay,QgsVectorLayer):
                gtype = QgsWkbTypes().displayString(vlay.wkbType())
                self.label_HS_finvgtype.setText(gtype)
            
        self.comboBox_vec.layerChanged.connect(upd_gtype) #SS inventory vector layer
        
        #display sampling stats options to user 
        def upd_stat():
            vlay = self.comboBox_vec.currentLayer()
            if isinstance(vlay,QgsVectorLayer):
                gtype = QgsWkbTypes().displayString(vlay.wkbType())
                self.comboBox_HS_stat.clear()
                
                if 'Polygon' in gtype:
                    self.comboBox_HS_stat.addItems(
                        ['Mean','Median','Min','Max'])
                
        self.comboBox_vec.layerChanged.connect(upd_stat) #SS inventory vector layer
            
        
        #=======================================================================
        # #execute
        #=======================================================================
        self.pushButton_HSgenerate.clicked.connect(self.run_wsamp)
        
        #======================================================================
        # event likelihoods
        #======================================================================
        self.pushButton_ELstore.clicked.connect(self.set_event_vals)
        
        """dev button
        self.pushButton_ELdev.clicked.connect(self._pop_el_table)"""
        
        
        #======================================================================
        # Likelihood Sampler-----------
        #======================================================================
        """todo: rename the buttons so they align w/ the set labels"""
        #list of combo box names on the likelihood sampler tab
        self.ls_cb_d = { #set {hazard raster : lpol}
            1: (self.MLCB_LS1_event_3, self.MLCB_LS1_lpol_3),
            2: (self.MLCB_LS1_event_4, self.MLCB_LS1_lpol_4),
            3: (self.MLCB_LS1_event_5, self.MLCB_LS1_lpol_5),
            4: (self.MLCB_LS1_event, self.MLCB_LS1_lpol),
            5: (self.MLCB_LS1_event_6, self.MLCB_LS1_lpol_6),
            6: (self.MLCB_LS1_event_7, self.MLCB_LS1_lpol_7),
            7: (self.MLCB_LS1_event_2, self.MLCB_LS1_lpol_2),
            8: (self.MLCB_LS1_event_8, self.MLCB_LS1_lpol_8)
            }
        
        #loop and set filteres
        first = True
        for sname, (mlcb_haz, mlcb_lpol) in self.ls_cb_d.items():
            #set drop down filters
            mlcb_haz.setFilters(QgsMapLayerProxyModel.RasterLayer)
            mlcb_haz.setAllowEmptyLayer(True)
            mlcb_lpol.setFilters(QgsMapLayerProxyModel.PolygonLayer)
            mlcb_lpol.setAllowEmptyLayer(True)
            
            if first:
                mlcb_lpol_1 = mlcb_lpol
                first = False

            
        #connect to update the field name box
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
        # other------------
        #======================================================================
        #Vulnerability Curve Set
        def browse_rfda_crv():
            return self.browse_button(self.lineEdit_wd_OthRf_cv, prompt='Select RFDA curve .xls',
                                      qfd = QFileDialog.getOpenFileName)
            
        self.pushButton_wd_OthRf_cv.clicked.connect(browse_rfda_crv)
            
        self.mMapLayerComboBox_OthR_rinv.setFilters(QgsMapLayerProxyModel.PointLayer)
        
        self.pushButton_OthRfda.clicked.connect(self.run_rfda)



        self.logger.info('DataPrep ui initilized')
        #======================================================================
        # dev
        #======================================================================
        """"
        to speed up testing.. manually configure the project
        """

        debug_dir =os.path.join(os.path.expanduser('~'), 'CanFlood', 'build')
        self.lineEdit_cf_fp.setText(os.path.join(debug_dir, 'CanFlood_scenario1.txt'))
        self.lineEdit_wd.setText(debug_dir)
        
        
        
    def upd_prog(self, progress): #Dialog level progress bar updating
        """
        connect each tool to this function
        """
        
        self.progressBar.setValue(progress)

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

    #==========================================================================
    # tool commands------------                   
    #==========================================================================
    def slice_aoi(self, finv):
        return finv

    def build_scenario(self): #'Generate' on the setup tab
        """
        Generate a CanFlood project from scratch
        
        This tab facilitates the creation of a Control File from user specified parameters and inventory, 
            as well as providing general file control variables for the other tools in the toolset.
            
        
        
        """
        log = self.logger.getChild('build_scenario')
        self.tag = self.linEdit_ScenTag.text() #set the secnario tag from user provided name
        
        self.cid = self.mFieldComboBox_cid.currentField() #user selected field
        
        self.wd =  self.lineEdit_wd.text() #pull the wd filepath from the user provided in 'Browse'
        
        
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert isinstance(self.wd, str)
        assert isinstance(self.cid, str)
        assert isinstance(self.tag, str)
        
        if not os.path.exists(self.wd):
            os.makedirs(self.wd)
            log.info('built working directory: %s'%self.wd)
            
        
        
        #======================================================================
        # build the control file
        #======================================================================
        finv_fp = self.convert_finv() #convert the finv to csv and write to file
        assert os.path.exists(finv_fp)
        
        #called by build_scenario()
        dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        #get the default template from the program files
        cf_src = os.path.join(dirname, '_pars/CanFlood_control_01.txt')
        assert os.path.exists(cf_src)
        #cf_src = os.path.join(dirname, '_documents/CanFlood_control_01.txt')
        
        #start the scratch file
        #scratch_src = os.path.join(dirname, '_documents/scratch.txt')
        
        #get control file name from user provided tag
        cf_fn = 'CanFlood_%s.txt'%self.tag
        cf_path = os.path.join(self.wd, cf_fn)
        #cf_path = os.path.join(self.wd, 'CanFlood_control_01.txt')
        
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
            
        #=======================================================================
        # if not os.path.exists(scratch_src):
        #     open(scratch_src, 'w').close()
        #=======================================================================
        
        #======================================================================
        # update the control file
        #======================================================================
        """todo: switch over to helper function"""
        pars = configparser.ConfigParser(allow_no_value=True)
        _ = pars.read(cf_path) #read it from the new location
        
        #parameters
        pars.set('parameters', 'cid', self.cid) #user selected field
        pars.set('parameters', 'name', self.tag) #user selected field
        pars.set('parameters', 'felv', self.comboBox_SSelv.currentText()) #user selected field
        
        #filepaths
        pars.set('dmg_fps', 'curves',  self.lineEdit_curve.text())
        pars.set('dmg_fps', 'finv', finv_fp)
        
        
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
        
        #======================================================================
        # wrap
        #======================================================================
        
        #display the control file in the dialog
        self.lineEdit_cf_fp.setText(cf_path)
        
        """not sure what this is
        self.lineEdit_control_2.setText(os.path.normpath(os.path.join(self.wd, 'CanFlood_control_01.txt')))"""
        
        log.push("Scenario \'%s\' control file created"%self.tag)

        
    def convert_finv(self): #convert the finv vector to csv file
        
        #======================================================================
        # check the cid
        #======================================================================
        if self.cid == '' or self.cid in self.invalid_cids:
            raise Error('user selected invalid cid \'%s\''%self.cid)  
        
            
        
        #store the vecotr layer
        self.finv_vlay = self.comboBox_vec.currentLayer()
        
        #extract data
        df = vlay_get_fdf(self.finv_vlay)
          
        #drop geometery indexes
        for gindx in self.invalid_cids:   
            df = df.drop(gindx, axis=1, errors='ignore')
            
        if not self.cid in df.columns:
            raise Error('cid not found in finv_df')
        
        #write it as a csv
        out_fp = os.path.join(self.wd, 'finv_%s_%s.csv'%(self.tag, self.finv_vlay.name()))
        df.to_csv(out_fp, index=False)  
        
        QgsMessageLog.logMessage("inventory csv written to file:\n    %s"%out_fp,
                                 'CanFlood', level=Qgis.Info)
        
        return out_fp
                
        

    
    def run_wsamp(self): #execute wsamp
        log = self.logger.getChild('run_wsamp')

        log.info('user pressed \'pushButton_HSgenerate\'')
        
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        finv_raw = self.comboBox_vec.currentLayer()
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
            dtm_rlay=self.comboBox_dtm.currentLayer()
            
            assert isinstance(dthresh, float)
            assert isinstance(dtm_rlay, QgsRasterLayer)
            
        else:
            dthresh, dtm_rlay = None, None
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
        #======================================================================
        # execute
        #======================================================================
        """
        finv = self.wsampRun(rlay_l, finv, control_fp=cf_fp1, cid=cid, crs=crs)"""
        #build the sample
        wrkr = Rsamp(logger=self.logger, 
                          tag = self.tag, #set by build_scenario() 
                          feedback = None, #let the instance build its own feedback worker
                          cid=cid,crs = crs,
                          out_dir = out_dir
                          )
        
        #connect the status bar
        wrkr.feedback.progressChanged.connect(self.upd_prog)
        
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
        if self.checkBox_HSloadres.isChecked():
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
        self.upd_prog(0) #set the progress bar back down to zero

        log.push('wsamp finished')
        
        return
    
    def run_dsamp(self): #sample dtm raster
        
        self.logger.info('user pressed \'pushButton_DTMsamp\'')

        
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        
        finv_raw = self.comboBox_vec.currentLayer()
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
        wrkr.feedback.progressChanged.connect(self.upd_prog)
        
        res_vlay = wrkr.run([rlay], finv, psmp_stat=psmp_stat)
        
        #check it
        wrkr.dtm_check(res_vlay)
        
        #save csv results to file
        wrkr.write_res(res_vlay, out_dir = out_dir)
        
        #update ocntrol file
        wrkr.update_cf({
            'dmg_fps':(
                {'gels':wrkr.out_fp},
                '#\'gels\' file path set from wsamp.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                    ),
            'parameters':(
                {'felv':'ground'},                
                )
            
                    },cf_fp)
        
        #======================================================================
        # add to map
        #======================================================================
        if self.checkBox_DTMloadres.isChecked():
            self.qproj.addMapLayer(finv)
            self.logger.info('added \'%s\' to canvas'%finv.name())
            
        self.logger.push('dsamp finished')    
        
    def run_lisamp(self): #sample dtm raster
        
        self.logger.info('user pressed \'pushButton_DTMsamp\'')

        
        #=======================================================================
        # assemble/prepare inputs
        #=======================================================================
        finv_raw = self.comboBox_vec.currentLayer()
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
        wrkr.feedback.progressChanged.connect(self.upd_prog)
        
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
        if self.checkBox_LSloadres.isChecked():
            res_vlay = wrkr.vectorize(res_df)
            self.qproj.addMapLayer(res_vlay)
            self.logger.info('added \'%s\' to canvas'%finv.name())
            
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
        
        log.push('completed %i validations'%len(vpars_d))
        
        return
    
    def run_rfda(self): #Other.Rfda tab
        log = self.logger.getChild('run_rfda')
        
        #======================================================================
        # collect from  ui
        #======================================================================
        rinv_vlay = self.mMapLayerComboBox_OthR_rinv.currentLayer()
        crv_fp = self.lineEdit_wd_OthRf_cv.text()
        bsmt_ht = self.lineEdit_OthRf_bht.text()
        #cid = self.mFieldComboBox_cid.currentField() #user selected field
        
        crs = self.qproj.crs()
        out_dir = self.lineEdit_wd.text()
        
        try:
            bsmt_ht = float(bsmt_ht)
        except Exception as e:
            raise Error('failed to convert bsmt_ht to float w/ \n    %s'%e)
        
        
        #======================================================================
        # input checks
        #======================================================================
        #======================================================================
        # if cid is None or cid=='':
        #     raise Error('need to select a cid')
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
            

            
            
    
     
            
                    
                
            
        

            
            
             
        
        
        
                
  
 

           
            
                    
            