# -*- coding: utf-8 -*-
"""
ui class for the MODEL toolset
"""

import os,  os.path, time
from shutil import copyfile

from PyQt5 import uic, QtWidgets


#from PyQt5.QtCore import QSettings, QTranslator, QCoreApplication, QObject
#from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget

# Initialize Qt resources from file resources.py
#from .resources import *
# Import the code for the dialog



# User defined imports
from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer
#from qgis.analysis import *
import qgis.utils
import processing
from processing.core.Processing import Processing



import numpy as np
import pandas as pd



#==============================================================================
# custom imports 
#==============================================================================
from model.risk1 import Risk1
from model.risk2 import Risk2
from model.dmg2 import Dmg2


import results.djoin


import hlpr.plug
from hlpr.basic import force_open_dir
from hlpr.exceptions import QError as Error


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'model.ui')
assert os.path.exists(ui_fp)
FORM_CLASS, _ = uic.loadUiType(ui_fp)


class Modelling_Dialog(QtWidgets.QDialog, FORM_CLASS,  
                       hlpr.plug.QprojPlug):
    
    def __init__(self, iface, parent=None):
        """Constructor."""
        super(Modelling_Dialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        

        self.iface = iface
        
        self.qproj_setup()
        
        self.connect_slots()
        
    def connect_slots(self):
        """connect ui slots to functions"""
        #======================================================================
        # general----------------
        #======================================================================
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        #connect to status label
        self.logger.statusQlab=self.progressText
        self.logger.statusQlab.setText('BuildDialog initialized')
        
        #======================================================================
        # setup-----------
        #======================================================================
        #control file
        def cf_browse():
            return self.browse_button(self.lineEdit_cf_fp, 
                                      prompt='Select Control File',
                                      qfd = QFileDialog.getOpenFileName)
            
        self.pushButton_cf.clicked.connect(cf_browse)
        
        #=======================================================================
        # #working directory
        #=======================================================================
        #browse button
        def wd_browse():
            return self.browse_button(self.lineEdit_wd, 
                                      prompt='Select Working Directory',
                                      qfd = QFileDialog.getExistingDirectory)
            
        self.pushButton_wd.clicked.connect(wd_browse)
        
        #open button
        def open_wd():
            wd = self.lineEdit_wd.text()
            if not os.path.exists(wd):
                os.makedirs(wd)
            force_open_dir(wd)
        
        self.pushButton_wd_open.clicked.connect(open_wd)
        

        #overwrite control
        self.checkBox_SSoverwrite.stateChanged.connect(self.set_overwrite)
        #=======================================================================
        # Join Geometry 
        #=======================================================================

        #vector geometry layer
        self.comboBox_JGfinv.setFilters(QgsMapLayerProxyModel.VectorLayer) 
        
        """not working"""
        self.comboBox_JGfinv.clear() #by default, lets have this be blank
        
        def upd_cid(): #change the 'cid' display when the finv selection changes
            return self.mfcb_connect(
                self.mFieldComboBox_JGfinv, self.comboBox_JGfinv.currentLayer(),
                fn_str = 'xid' )
        
        self.comboBox_JGfinv.layerChanged.connect(upd_cid)
        
        

        
        
        
        #======================================================================
        # risk level 1----------
        #======================================================================
        self.pushButton_r1Run.clicked.connect(self.run_risk1)
        
        #conditional check boxes
        def tog_jg(): #toggle thte join_geo option
            
            
            pstate = self.checkBox_r2rpa_2.isChecked()
            #if checked, enable the second box
            self.checkBox_r2ires_2.setDisabled(np.invert(pstate))
            self.checkBox_r2ires_2.setChecked(False) #clear the check
            
        self.checkBox_r2rpa_2.stateChanged.connect(tog_jg)
        
        #======================================================================
        # impacts level 2--------
        #======================================================================
        self.pushButton_i2run.clicked.connect(self.run_impact2)
        
        #======================================================================
        # risk level 2----
        #======================================================================
        self.pushButton_r2Run.clicked.connect(self.run_risk2)
        
        #conditional check boxes
        def tog_jg2(): #toggle thte join_geo option
            
            
            pstate = self.checkBox_r2rpa.isChecked()
            #if checked, enable the second box
            self.checkBox_r2ires.setDisabled(np.invert(pstate))
            self.checkBox_r2ires.setChecked(False) #clear the check
            
        self.checkBox_r2rpa.stateChanged.connect(tog_jg2)
        
        #======================================================================
        # risk level 3-----
        #======================================================================
        self.pushButton_r3Run.clicked.connect(self.run_risk3)
        
        
        def r3_browse():
            return self.browse_button(self.lineEdit_r3cf, 
                                      prompt='Select SOFDA Control File',
                                      qfd = QFileDialog.getOpenFileName)
            
        
        self.pushButton_r3.clicked.connect(r3_browse)
        

        
        self.logger.debug('Model ui connected')
        
        #======================================================================
        # dev
        #======================================================================
        """"
        to speed up testing.. manually configure the project
        """
        
        debug_dir =os.path.join(os.path.expanduser('~'), 'CanFlood', 'model')
        self.lineEdit_cf_fp.setText(os.path.join(debug_dir, 'CanFlood_scenario1.txt'))
        self.lineEdit_wd.setText(debug_dir)
        

        
        
        
    def select_output_folder(self):
        foldername = QFileDialog.getExistingDirectory(self, "Select Directory")
        print(foldername)
        if foldername is not "":
            self.lineEdit_wd.setText(os.path.normpath(foldername))
            self.lineEdit_wd_2.setText(os.path.normpath(foldername)) #i2. bar
            self.lineEdit_cf_1.setText(os.path.normpath(os.path.join(foldername, 'CanFlood_control_01.txt'))) #r1. browse
            self.lineEdit_cf_2.setText(os.path.normpath(os.path.join(foldername, 'CanFlood_control_01.txt')))
    
    def select_output_file(self):
        filename = QFileDialog.getOpenFileName(self, "Select File") 
        self.lineEdit_cf_1.setText(str(filename[0])) #r1. browse
        self.lineEdit_cf_2.setText(str(filename[0]))
        
    def set_run_pars(self): #setting generic parmaeters for a run
        self.wd= self.get_wd()
        self.cf_fp = self.get_cf_fp()
        self.tag = self.linEdit_Stag.text()
        
    #==========================================================================
    # run commands
    #==========================================================================
    def run_risk1(self):
        """
        risk T1 runner
        """
        #=======================================================================
        # variables
        #=======================================================================
        log = self.logger.getChild('run_risk1')
        cf_fp = self.get_cf_fp()
        out_dir = self.get_wd()
        tag = self.linEdit_Stag.text()
        res_per_asset = self.checkBox_r2rpa_2.isChecked()
        absolute_fp = self._get_absolute_fp()

        #=======================================================================
        # setup/execute
        #=======================================================================
        model = Risk1(cf_fp=cf_fp, out_dir=out_dir, logger=self.logger, tag=tag,absolute_fp=absolute_fp,
                      feedback=self.feedback)._setup()
        
        res, res_df = model.run(res_per_asset=res_per_asset)
        
        log.info('user pressed RunRisk1')
        #======================================================================
        # plot
        #======================================================================
        if self.checkBox_r2ep_2.isChecked():
            fig = model.risk_plot()
            _ = model.output_fig(fig)
            
        
        #==========================================================================
        # output
        #==========================================================================
        out_fp = model.output_df(res, '%s_%s'%(model.resname, 'ttl'))
        
        out_fp2 = None
        if not res_df is None:
            out_fp2 = model.output_df(res_df, '%s_%s'%(model.resname, 'passet'))
            
        self.logger.push('Risk1 Complete')
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
        #=======================================================================
        # links
        #=======================================================================
        if self.checkBox_r2ires_2.isChecked():
            assert os.path.exists(out_fp2), 'need to generate results per asset'
            self.results_joinGeo(out_fp2, out_dir, tag)
        

            
        return
        
    def run_impact2(self):
        log = self.logger.getChild('run_impact2')
        #=======================================================================
        # retrive variable values
        #=======================================================================
        cf_fp = self.get_cf_fp()
        out_dir = self.get_wd()
        tag = self.linEdit_Stag.text()
        absolute_fp = self._get_absolute_fp()
        
        #======================================================================
        # #build worker
        #======================================================================
        model = Dmg2(cf_fp=cf_fp, out_dir = out_dir, logger = self.logger, tag=tag, 
                     absolute_fp=absolute_fp, feedback=self.feedback,
                     attriMode=self.checkBox_SS_attr.isChecked(),
                     )._setup()
        self.feedback.setProgress(5)
        
        #=======================================================================
        # #run the model        
        #=======================================================================
        cres_df = model.run()
        self.feedback.setProgress(70)
        
        #attribution
        if self.checkBox_SS_attr.isChecked():
            _ = model.get_attribution(cres_df)
            model.output_attr(upd_cf = self.checkBox_SS_updCf.isChecked())
        
        self.feedback.setProgress(80)
        #======================================================================
        # save reuslts
        #======================================================================
        out_fp = model.output_df(cres_df, model.resname)
        self.feedback.setProgress(85)
        
        #update parameter file
        if self.checkBox_SS_updCf.isChecked():
            model.upd_cf()
        self.feedback.setProgress(90)
            
        #calc summary
        if self.checkBox_i2bSmry.isChecked():
            _ = model.bdmg_smry()
        self.feedback.setProgress(92)
            
        #output expanded results
        if self.checkBox_i2_outExpnd.isChecked():
            _ = model.output_bdmg()
        self.feedback.setProgress(95)
        
        if self.checkBox_i2_ddf.isChecked():
            _=model.output_depths_df()
            
        #box plots
        if self.checkBox_i2plot.isChecked():
            fig = model.plot_boxes()
            _ = model.output_fig(fig)
            
        self.feedback.setProgress(99)

        self.logger.push('Impacts2 complete')
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
        #======================================================================
        # links
        #======================================================================
        
        if self.checkBox_i2RunRisk.isChecked():
            self.logger.info('linking in Risk 2')
            self.run_risk2()
            
    def run_risk2(self):
        #======================================================================
        # get run vars
        #======================================================================
        log = self.logger.getChild('run_risk2')
        start = time.time()
        cf_fp = self.get_cf_fp()
        out_dir = self.get_wd()
        tag = self.linEdit_Stag.text()
        res_per_asset = self.checkBox_r2rpa.isChecked()
        absolute_fp = self._get_absolute_fp()
        

        #======================================================================
        # run the model
        #======================================================================
        model = Risk2(cf_fp=cf_fp, out_dir=out_dir, logger=self.logger, tag=tag,absolute_fp=absolute_fp,
                      feedback=self.feedback, attriMode=self.checkBox_SS_attr.isChecked(),
                      )._setup()
        
        res_ttl, res_df = model.run(res_per_asset=res_per_asset)
        
        #======================================================================
        # plot
        #======================================================================
        if self.checkBox_r2plot.isChecked():
            ttl_df = model.prep_ttl(tlRaw_df=res_ttl)
            """just giving one curve here"""
            fig = model.plot_riskCurve(ttl_df, y1lab='impacts')
            _ = model.output_fig(fig)
       
        #=======================================================================
        # output
        #=======================================================================
        #risk results
        model.output_ttl(upd_cf = self.checkBox_SS_updCf.isChecked())
        
        out_fp2=''
        if not res_df is None:
            out_fp2= model.output_passet(upd_cf = self.checkBox_SS_updCf.isChecked())
            

            
        #attribution
        if self.checkBox_SS_attr.isChecked():
            model.output_attr(upd_cf = self.checkBox_SS_updCf.isChecked())
        
        #event metadata
        model.output_etype(upd_cf = self.checkBox_SS_updCf.isChecked())
        #=======================================================================
        # wrap
        #=======================================================================
        tdelta = (time.time()-start)/60.0
        self.logger.push('Risk2 complete in %.4f mins'%tdelta)
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        #======================================================================
        # links
        #======================================================================
        if self.checkBox_r2ires.isChecked():
            assert os.path.exists(out_fp2), 'need to generate results per asset'
            self.results_joinGeo(out_fp2, out_dir, tag)


        return

    def run_risk3(self):
        
        #======================================================================
        # get run vars
        #======================================================================
        log = self.logger.getChild('run_risk3')

        cf_fp = self.lineEdit_r3cf.text()
        out_dir = self.get_wd()
        tag = self.linEdit_Stag.text()
        
        #=======================================================================
        # defaults
        #=======================================================================
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert os.path.exists(cf_fp), 'passed bad control file path: \n    %s'%cf_fp
        assert os.path.exists(out_dir)
        
        
        #=======================================================================
        # run the model
        #=======================================================================
        
        
        log.info('init SOFDA from cf: %s'%cf_fp)
        from model.sofda.scripts import Session as Sofda
        self.feedback.setProgress(3)
        session = Sofda(parspath = cf_fp, 
                          outpath = out_dir, 
                          _dbgmstr = 'none', 
                          logger=self.logger
                        )
        

        self.feedback.setProgress(10)
        session.load_models()
        
        self.feedback.setProgress(20)
        session.run_session()

        self.feedback.setProgress(90)
        session.write_results()

        self.feedback.setProgress(95)
        session.wrap_up()

        log.info('sofda finished')
        

    
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
    def results_joinGeo(self, 
                        data_fp, #filepath to res_per asset tabular results data 
                        wd, tag):
        """
        not a good way to have the user specify the 
        
        helper to execute results joiner
        
        passing all values exliclpity to rely on assertion checks in caller
        """
        log = self.logger.getChild('results_joinGeo')
        #=======================================================================
        # collect inputs
        #=======================================================================
        geo_vlay = self.comboBox_JGfinv.currentLayer()
        cid = self.mFieldComboBox_JGfinv.currentField() #user selected field

        #=======================================================================
        # check inputs
        #=======================================================================
        assert isinstance(geo_vlay, QgsVectorLayer), \
            'need to specify a geometry layer on the \'Setup\' tab to join results to'
            
        
        #check cid
        assert isinstance(cid, str), 'bad index FieldName passed'
        if cid == '' or cid in self.invalid_cids:
            raise Error('user selected index FieldName \'%s\''%cid)
        
        assert cid in [field.name() for field in geo_vlay.fields()] 
        
        assert os.path.exists(data_fp), 'invalid data_fp'
        
        #=======================================================================
        # execute
        #=======================================================================
        #setup
        wrkr = results.djoin.Djoiner(logger=self.logger, 
                                     tag = tag,
                                     feedback=self.feedback,
                                     cid=cid, 
                                     out_dir=wd)
        #execute
        res_vlay = wrkr.run(geo_vlay, data_fp, cid,
                 keep_fnl='all', #todo: setup a dialog to allow user to select any of the fields
                 )
        
        self.qproj.addMapLayer(res_vlay)
        
        #=======================================================================
        # wrap
        #=======================================================================

        
        self.feedback.upd_prog(None)
        log.push('run_joinGeo finished')
        
    def _get_absolute_fp(self): #helper to get the absoulte filepath flag
        if self.radioButton_S_fpAbs.isChecked():
            absolute_fp=True
            assert not self.radioButton_S_fpRel.isChecked()
            
        elif self.radioButton_S_fpRel.isChecked():
            absolute_fp=False
            
        else:
            raise Error('butotn logic fail')
        
        return absolute_fp
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        