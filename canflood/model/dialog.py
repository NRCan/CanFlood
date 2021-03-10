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


class ModelDialog(QtWidgets.QDialog, FORM_CLASS,  
                       hlpr.plug.QprojPlug):
    
    def __init__(self, iface, parent=None, **kwargs):
        """Constructor."""
        super(ModelDialog, self).__init__(parent)

        self.setupUi(self)
        

        self.qproj_setup(iface=iface, **kwargs)
        
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
        #CanFlood Control 
        self.pushButton_cf.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_cf_fp, 
                                          caption='Select Control File',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Text Files (*.txt)")
                )
        
        #=======================================================================
        # #working directory
        #=======================================================================
        #Working Directory 
        self._connect_wdir(self.pushButton_wd, self.pushButton_wd_open, self.lineEdit_wdir,
                           default_wdir = os.path.join(os.path.expanduser('~'), 'CanFlood', 'build'))
        #=======================================================================
        # Join Geometry 
        #=======================================================================

        hlpr.plug.bind_MapLayerComboBox(self.comboBox_JGfinv, 
                      layerType=QgsMapLayerProxyModel.VectorLayer, iface=self.iface)
                
        self.launch_actions['attempt finv'] = lambda: self.comboBox_JGfinv.attempt_selection('finv')
 
        
        #======================================================================
        # risk level 1----------
        #======================================================================
        self.pushButton_r1Run.clicked.connect(self.run_risk1)
        

        
        #======================================================================
        # impacts level 2--------
        #======================================================================
        self.pushButton_i2run.clicked.connect(self.run_impact2)
        
        #======================================================================
        # risk level 2----
        #======================================================================
        self.pushButton_r2Run.clicked.connect(self.run_risk2)
        

        
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
        self.feedback.upd_prog(5)
        self._set_setup()

        #=======================================================================
        # setup/execute
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        model = Risk1(upd_cf = self.checkBox_SS_updCf.isChecked(), **kwargs).setup()
        
        res_ttl, res_df = model.run(res_per_asset=self.checkBox_r1_rpa.isChecked())
        
        self.feedback.upd_prog(80)
        #======================================================================
        # plots
        #======================================================================
        self._risk_plots(model, res_ttl,
            {'AEP':self.checkBox_r1_aep,'impacts':self.checkBox_r1_ari},
            )
        self.feedback.upd_prog(90)
        #==========================================================================
        # output
        #==========================================================================
        model.output_ttl()
        model.output_etype()
        
        out_fp2 = None
        if not res_df is None:
            out_fp2 = model.output_passet()
            
        self.feedback.upd_prog(95)
        self.logger.push('Risk1 Complete')
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
        #=======================================================================
        # links
        #=======================================================================
        if not self.comboBox_JGfinv.currentLayer() is None:
            if self.checkBox_r1_rpa.isChecked():
                self.results_joinGeo()
            
        

            
        return
        
    def run_impact2(self):
        log = self.logger.getChild('run_impact2')
        start = time.time()
        self.feedback.upd_prog(5)
        #=======================================================================
        # retrive variable values
        #=======================================================================
        
        self._set_setup()
        self.feedback.upd_prog(10)
        #======================================================================
        # #build worker
        #======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        model = Dmg2(attriMode=self.checkBox_SS_attr.isChecked(),
                     upd_cf = self.checkBox_SS_updCf.isChecked(),**kwargs
                     ).setup()
                             
        #=======================================================================
        # #run the model        
        #=======================================================================
        cres_df = model.run()
        self.feedback.upd_prog(81) 
        
        #attribution
        if self.checkBox_SS_attr.isChecked():
            _ = model.get_attribution(cres_df)
            model.output_attr(upd_cf = self.checkBox_SS_updCf.isChecked())
        
        self.feedback.upd_prog(5, method='append') 
        #======================================================================
        # save reuslts
        #======================================================================
        out_fp = model.output_cdmg()

        
        #update parameter file
        if self.checkBox_SS_updCf.isChecked():
            model.update_cf()

            
        #calc summary
        if self.checkBox_i2bSmry.isChecked():
            _ = model.bdmg_smry()

            
        #output expanded results
        if self.checkBox_i2_outExpnd.isChecked():
            _ = model.output_bdmg()

        
        if self.checkBox_i2_ddf.isChecked():
            _=model.output_depths_df()
            
        self.feedback.upd_prog(90) 
        #=======================================================================
        # plots
        #=======================================================================
        if self.checkBox_i2_pbox.isChecked():
            fig = model.plot_boxes()
            self.output_fig(fig)
            
        if self.checkBox_i2_phist.isChecked():
            fig = model.plot_hist()
            self.output_fig(fig)
            
        self.feedback.setProgress(99)
        
        #=======================================================================
        # wrap
        #=======================================================================
        tdelta = (time.time()-start)/60.0
        self.logger.push('Impacts2 complete in %.4f mins'%tdelta)
 
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
        self.feedback.upd_prog(5)
                               
                               
        self._set_setup()
        self.feedback.upd_prog(10)
        #======================================================================
        # run the model
        #======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        model = Risk2(attriMode=self.checkBox_SS_attr.isChecked(),
                      upd_cf = self.checkBox_SS_updCf.isChecked(),**kwargs
                      ).setup()
        
        res_ttl, res_df = model.run(res_per_asset=self.checkBox_r2rpa.isChecked())
        self.feedback.upd_prog(80)
        #======================================================================
        # plots
        #======================================================================
        self._risk_plots(model, res_ttl,
            {'AEP':self.checkBox_r2_aep,'impacts':self.checkBox_r2_ari},
            )
        
        self.feedback.upd_prog(90)
        #=======================================================================
        # output
        #=======================================================================
        
        model.output_ttl() #risk results
        model.output_etype() #event metadata
        
        out_fp2=''
        if not res_df is None:
            out_fp2= model.output_passet()
            
        #attribution
        if self.checkBox_SS_attr.isChecked():
            model.output_attr()
        self.feedback.upd_prog(99)
        #=======================================================================
        # wrap
        #=======================================================================
        tdelta = (time.time()-start)/60.0
        self.logger.push('Risk2 complete in %.4f mins'%tdelta)
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        #======================================================================
        # links
        #======================================================================
        if not self.comboBox_JGfinv.currentLayer() is None:
            if self.checkBox_r2rpa.isChecked():
                self.results_joinGeo()


        return
    
    def _risk_plots(self,model, res_ttl,d):
        
        #prep the data for plotting
        model.raw_d['r_ttl'] = res_ttl.copy()
        model.set_ttl()
        
        #loop and get each plot
        for y1lab, cbox in d.items():
            if not cbox.isChecked(): continue 

            #plot it
            fig = model.plot_riskCurve(y1lab=y1lab)
            self.output_fig(fig)

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
                        fp_attn = 'r_passet',
                        
                        style_fn =None, #for loading specific styles
                        ):

        log = self.logger.getChild('results_joinGeo')
        #=======================================================================
        # collect inputs
        #=======================================================================
        self._set_setup()  #only need the common
        geo_vlay = self.comboBox_JGfinv.currentLayer()

        self.feedback.setProgress(5)
        #=======================================================================
        # check inputs
        #=======================================================================
        assert isinstance(geo_vlay, QgsVectorLayer), \
            'need to specify a geometry layer on the \'Setup\' tab to join results to'
        #=======================================================================
        # execute
        #=======================================================================
        
        #setup
        kwargs = {attn:getattr(self, attn) for attn in ['logger', 'tag', 'cf_fp', 'out_dir', 'feedback', 'init_q_d']}
        wrkr = results.djoin.Djoiner(**kwargs).setup()
        

        
        self.feedback.setProgress(25)
        #=======================================================================
        # #execute
        #=======================================================================
        """running with all defaults
            more customization is done on teh Resultd dialog"""
        res_vlay = wrkr.run(geo_vlay, keep_fnl='all') 
        self.feedback.setProgress(80)
        
        #=======================================================================
        # load
        #=======================================================================
        self._load_toCanvas(res_vlay, logger=log, style_fn=style_fn)
        self.feedback.setProgress(99)
        
        #=======================================================================
        # wrap
        #=======================================================================

        
        
        log.push('run_joinGeo finished')
        self.feedback.upd_prog(None)
        

        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        