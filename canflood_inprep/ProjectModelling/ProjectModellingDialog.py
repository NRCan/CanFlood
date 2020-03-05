# -*- coding: utf-8 -*-
"""
ui class for the MODEL toolset
"""

import os,  os.path, warnings, tempfile, logging, configparser, sys
from shutil import copyfile

from qgis.PyQt import uic
from qgis.PyQt import QtWidgets

from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QObject
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QListWidget

# Initialize Qt resources from file resources.py
#from .resources import *
# Import the code for the dialog

#from .canFlood_inPrep_dialog import CanFlood_inPrepDialog

from qgis.core import QgsProject, Qgis, QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest

# User defined imports
from qgis.core import *
from qgis.analysis import *
import qgis.utils
import processing
from processing.core.Processing import Processing


sys.path.append(r'C:\IBI\_QGIS_\QGIS 3.8\apps\Python37\Lib\site-packages')
#sys.path.append(os.path.join(sys.exec_prefix, 'Lib/site-packages'))
import numpy as np
import pandas as pd

file_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(file_dir)

#==============================================================================
# custom imports 
#==============================================================================
from model.risk1 import Risk1
from model.risk2 import Risk2
from model.dmg2 import Dmg2


import hlpr.plug
from hlpr.basic import *


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ProjectModellingDialog_Base.ui'))


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
        
        """remapped everything
        self.pushButton_wd.clicked.connect(self.select_output_folder) #risk
        self.pushButton_br_2.clicked.connect(self.select_output_file)
        self.pushButton_cf.clicked.connect(self.select_output_folder)
        self.pushButton_br_4.clicked.connect(self.select_output_file)
        self.pushButton_run_1.clicked.connect(self.run_risk) #r1. run
        self.pushButton_run_2.clicked.connect(self.run_dmg)"""
        
        #======================================================================
        # setup
        #======================================================================
        """
        lineEdit_wd
        pushButton_wd
        """
        #control file
        def cf_browse():
            return self.browse_button(self.lineEdit_cf_fp, 
                                      prompt='Select Control File',
                                      qfd = QFileDialog.getOpenFileName)
            
        self.pushButton_cf.clicked.connect(cf_browse)
        
        #working directory
        def wd_browse():
            return self.browse_button(self.lineEdit_wd, 
                                      prompt='Select Working Directory',
                                      qfd = QFileDialog.getExistingDirectory)
            
        self.pushButton_wd.clicked.connect(wd_browse)
        
        """
        development
        """
        #======================================================================
        # self.lineEdit_cf_fp.setText(r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200223d\CanFlood_scenario1.txt')
        # self.lineEdit_wd.setText(r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200223d')
        #======================================================================
        
        
        #overwrite control
        self.checkBox_SSoverwrite.stateChanged.connect(self.set_overwrite)
        
        #======================================================================
        # risk level 1
        #======================================================================
        self.pushButton_r1Run.clicked.connect(self.run_risk1)
        
        #======================================================================
        # impacts level 2
        #======================================================================
        self.pushButton_i2run.clicked.connect(self.run_impact2)
        
        #======================================================================
        # risk level 2
        #======================================================================
        self.pushButton_r2Run.clicked.connect(self.run_risk2)
        
        #======================================================================
        # risk level 3
        #======================================================================
        self.pushButton_r3Run.clicked.connect(self.run_risk3)
        
        
        def r3_browse():
            return self.browse_button(self.lineEdit_r3cf, 
                                      prompt='Select SOFDA Control File',
                                      qfd = QFileDialog.getOpenFileName)
            
        
        self.pushButton_r3.clicked.connect(r3_browse)
        
        #======================================================================
        # commons
        #======================================================================
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        self.logger.info('Model ui connected')
        
        #======================================================================
        # dev
        #======================================================================
        """"
        to speed up testing.. manually configure the project
        """
        
        self.lineEdit_cf_fp.setText(r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\CanFlood_tutorial2.txt')
        self.lineEdit_wd.setText(r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\model')
        
        
        
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
        log = self.logger.getChild('run_risk1')
        cf_fp = self.get_cf_fp()
        out_dir = self.get_wd()
        tag = self.linEdit_Stag.text()
        res_per_asset = self.checkBox_r2rpa_2.isChecked()

        
        model = Risk1(cf_fp, out_dir=out_dir, logger=self.logger, tag=tag).setup()
        
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
        model.output_df(res, '%s_%s'%(model.resname, 'ttl'))
        
        if not res_df is None:
            _ = model.output_df(res_df, '%s_%s'%(model.resname, 'passet'))
            
        self.logger.push('Risk1 Complete')
        #======================================================================
        # links
        #======================================================================
        if self.checkBox_r2ires_2.isChecked():
            log.error('results to inventory linking not implemented')
            
        return
        
    def run_impact2(self):
        log = self.logger.getChild('run_impact2')
        cf_fp = self.get_cf_fp()
        out_dir = self.get_wd()
        tag = self.linEdit_Stag.text()

        #======================================================================
        # #build/run model
        #======================================================================
        model = Dmg2(cf_fp, out_dir = out_dir, logger = self.logger, tag=tag).setup()
        
        #run the model        
        cres_df = model.run()
        

        #======================================================================
        # save reuslts
        #======================================================================
        out_fp = model.output_df(cres_df, model.resname)
        
        #update parameter file
        model.upd_cf()

        self.logger.push('Impacts2 complete')
        
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
        cf_fp = self.get_cf_fp()
        out_dir = self.get_wd()
        tag = self.linEdit_Stag.text()
        res_per_asset = self.checkBox_r2rpa.isChecked()
        

        #======================================================================
        # run the model
        #======================================================================
        model = Risk2(cf_fp, out_dir=out_dir, logger=self.logger, tag=tag).setup()
        
        res_ser, res_df = model.run(res_per_asset=res_per_asset)
        
        #======================================================================
        # plot
        #======================================================================
        if self.checkBox_r2plot.isChecked():
            fig = model.risk_plot()
            _ = model.output_fig(fig)
       
        #=======================================================================
        # output
        #=======================================================================
        model.output_df(res_ser, '%s_%s'%(model.resname, 'ttl'))
        
        if not res_df is None:
            _ = model.output_df(res_df, '%s_%s'%(model.resname, 'passet'))
        
        
        
        self.logger.push('Risk2 complete')
        #======================================================================
        # links
        #======================================================================
        if self.checkBox_r2ires.isChecked():
            log.error('results to inventory linking not implemented')
            
            """
            TODO: link up  Results to Inventory Geometry

            """
        return

        
    def run_risk3(self):
        raise Error('not implemented')