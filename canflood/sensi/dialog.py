'''
Created on Nov. 18, 2021

@author: cefect

ui class for the sensitivity analysis menu
'''
#===============================================================================
# imports------------
#===============================================================================
import os,  os.path, time, datetime


from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem, QWidget

from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer

from hlpr.exceptions import QError as Error
#===============================================================================
# customs
#===============================================================================
import hlpr.plug

import numpy as np
import pandas as pd


#===============================================================================
# load qt ui
#===============================================================================
ui_fp = os.path.join(os.path.dirname(__file__), 'sensi.ui')
assert os.path.exists(ui_fp)
FORM_CLASS, _ = uic.loadUiType(ui_fp)

#===============================================================================
# Classes ---------
#===============================================================================
from sensi.coms import SensiShared
from sensi.sbuild import SensiConstructor
from sensi.srun import SensiSessRunner


 
 

class SensiDialog(QtWidgets.QDialog, FORM_CLASS,  
                       hlpr.plug.QprojPlug):
    
    colorMap = 'hsv' #cyclical
    
    def __init__(self, iface, parent=None, **kwargs):
        """Constructor."""
        super(SensiDialog, self).__init__(parent) #init QtWidgets.QDialog

        self.setupUi(self)
        

        self.qproj_setup(iface=iface, **kwargs)
        
        self.connect_slots()
        
        
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
        
        
    def connect_slots(self, #connect ui slots to functions 
                      dev=True,
                      ): 
        log = self.logger.getChild('connect_slots')
        #======================================================================
        # general----------------
        #======================================================================
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        #connect to status label
        self.logger.statusQlab=self.progressText
        self.logger.statusQlab.setText('SensiDialog initialized')
        
        
        #======================================================================
        # setup-----------
        #======================================================================
        #=======================================================================
        # base model
        #=======================================================================
        #control file
        self.pushButton_cf.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_cf_fp, 
                                          caption='Select Control File',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Text Files (*.txt)")
                )
        
        self.pushButton_s_cfOpen.clicked.connect(lambda: os.startfile(self.lineEdit_cf_fp.text()))
        
        #loading
        self.comboBox_S_ModLvl.addItems(['L1', 'L2'])
        self.pushButton_s_load.clicked.connect(self.load_base)
        #=======================================================================
        # #working directory
        #=======================================================================
        #Working Directory 
        self._connect_wdir(self.pushButton_wd, self.pushButton_wd_open, self.lineEdit_wdir,
                           default_wdir = os.path.join(os.path.expanduser('~'), 
                                       'CanFlood', 'sensi', datetime.datetime.now().strftime('%m%d')))
        
        
        #=======================================================================
        # compile----
        #=======================================================================
        #bind custom methods to the table widget
        hlpr.plug.bind_TableWidget(self.tableWidget_P, log)
         
        self.pushButton_P_addCand.clicked.connect(self.add_cand_col)
        
        self.pushButton_P_addColors.clicked.connect(self.add_random_colors)
        
        self.pushButton_P_compile.clicked.connect(self.compile_candidates)
        
        #=======================================================================
        # run-----
        #=======================================================================
        hlpr.plug.bind_TableWidget(self.tableWidget_R, log)
        
        self.pushButton_R_run.clicked.connect(self.run_suite)
        #=======================================================================
        # Analyze----------
        #=======================================================================
        #pickel file
        self.pushButton_A_browse.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_A_pick_fp, 
                                          caption='Select suite results .pickle',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Pickles (*.pickle)")
                )
        
        self.pushButton_A_load.clicked.connect(self.load_pick)
        #=======================================================================
        # dev
        #=======================================================================
        if dev:
            self.lineEdit_cf_fp.setText(r'C:\LS\03_TOOLS\CanFlood\tut_builds\8\20211119\CanFlood_tut8.txt')
            self.load_base()
            for i in range(0,2):
                self.add_cand_col()
            self.add_random_colors()
            self.compile_candidates()
            self.run_suite()
        
        
        
    def set_setup(self, #attach parameters from setup tab
                  set_cf_fp=True,  
                  logger=None,): 
        
        if logger is None: logger=self.logger
        log = logger.getChild('set_setup')
        #=======================================================================
        # #call the common
        #=======================================================================
        self._set_setup(set_cf_fp=set_cf_fp)
        #self.inherit_fieldNames.append('init_q_d')
        #=======================================================================
        # custom setups
        #=======================================================================
 
        #file behavior
        self.loadRes = self.checkBox_loadres.isChecked()
        
        #model type
        self.modLevel = self.comboBox_S_ModLvl.currentText()
        assert self.modLevel in ['L1', 'L2'], 'must specify a model level'
        self.inherit_fieldNames.append('modLevel')
        

    def _change_tab(self, tabObjectName): #try to switch the tab on the gui
        try:
            tabw = self.tabWidget
            index = tabw.indexOf(tabw.findChild(QWidget, tabObjectName))
            assert index > 0, 'failed to find index?'
            tabw.setCurrentIndex(index)
        except Exception as e:
            self.logger.error('failed to change to compile tab w/ \n    %s' % e)

    def load_base(self, #load teh base control file
                  ):
        #=======================================================================
        # default
        #=======================================================================
        log = self.logger.getChild('load_base')
        
        self.set_setup(set_cf_fp=True)
        log.info('loading base from %s'%self.cf_fp)
        #=======================================================================
        # prechecks
        #======================================================================= 
        if self.radioButton_SS_fpRel.isChecked():
            raise Error('Relative filepaths not implemented')

        self.feedback.upd_prog(10)
        
        #=======================================================================
        # load the base values----
        #=======================================================================
        """here we are only retrieving the 
        """
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiShared(**kwargs) as wrkr:
            wrkr.setup() #init the model
            """
            calls Model.cf_attach_pars()
            """
            cfPars_d = wrkr.cfPars_d #retrieve the loaded parameters
            
        #get just the parameters with values
        pars_d = {k:v  for sect, d in cfPars_d.items() for k,v in d.items() if not v==''}
        
    
        """
        for k,v in cfPars_d.items():
            print('%s    %s'%(k,v))
        self.modLevel
        """
        #=======================================================================
        # populate the table
        #=======================================================================
        log.info('populating \'Parameters\' tab w/ %i base values'%len(pars_d))
        tbw = self.tableWidget_P
        tbw.clear() #clear everything
        
        #set dimensions
        tbw.setColumnCount(1) #always start w/ 1.. then call add column
        tbw.setRowCount(len(pars_d))
        
        #set lables
        tbw.setVerticalHeaderLabels(list(pars_d.keys()))
        tbw.setHorizontalHeaderLabels(['base'])
        
        #populate w/ base parameter values
        self.feedback.upd_prog(50)
        for row, (attn, val_raw) in enumerate(pars_d.items()):
            
            val = val_raw
            
            #===================================================================
            # #drop to relative filename'
            # if isinstance(val_raw, str):
            #     if ':' in val_raw:
            #         val = os.path.basename(val_raw)
            #===================================================================
 
                
                
            tbw.setItem(row, 0, QTableWidgetItem(str(val)))
            
        log.debug('filled table')
        
        #add the first column
        self.add_cand_col()
        

        
        #=======================================================================
        # change to Compile tab
        #=======================================================================
        self._change_tab('tab_compile')
 
 
        
        
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
        return
        
    def add_cand_col(self, #add a new column to the parmaeters tab
                     ):
        
        #=======================================================================
        # default
        #=======================================================================
        log = self.logger.getChild('add_cand_col')
        
        self.set_setup(set_cf_fp=False)
        
        tbw = self.tableWidget_P
        
        
        #add a column
        i = tbw.columnCount()  #new index (base=0)
        tbw.insertColumn(i)
        mtag = 'cand%02i'%i
        
        #populate it w/ values from teh base column
        for j in range(0,tbw.rowCount(),1):
            tbw.setItem(j, i, QTableWidgetItem(tbw.item(j,0)))
        
        #set a new name
        baseName = tbw.item(0,0).text()
        tbw.setItem(0,i,QTableWidgetItem('%s_%02i'%(baseName, i)))
        
        #set a new header
        tbw.setHorizontalHeaderItem(i, QTableWidgetItem(mtag))
        
        #set alignment
        #tbw.call_all_items('setTextAlignment', 2)
        
        log.info('added parameter column for \'%s\''%mtag)
        
    def add_random_colors(self, #add a row of random colors
                          ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        
        log = self.logger.getChild('add_random_colors')
        self.set_setup(set_cf_fp=False)
        tbw = self.tableWidget_P
        colorMap=self.colorMap
        
        #=======================================================================
        # get old colors
        #=======================================================================
        #identify the row w/ color in it
        index_d = tbw.get_headers(axis=0)
        
        #no color...add your own
        if not 'color' in index_d:
            log.info('\'color\' not found... adding row')
            j = tbw.rowCount()
            
            #add the row
            tbw.insertRow(j)
            tbw.setVerticalHeaderItem(j, QTableWidgetItem('color'))
            
            #set to black
            tbw.setItem(j,0,QTableWidgetItem('black'))
            
        
        #just retrieve
        else:
            j = index_d['color']
            
        log.debug('color row=%i'%j)
        
        #get these values
        oldColorVals_d = tbw.get_values(j, axis=0)
        
        #=======================================================================
        # get new colors
        #=======================================================================
        import matplotlib.pyplot as plt
        import matplotlib.colors
        #retrieve the color map
        cmap = plt.cm.get_cmap(name=colorMap)
        #get a dictionary of index:color values           
        d = {i:cmap(ni) for i, ni in enumerate(np.linspace(0, 1, len(oldColorVals_d)))}
        
        #convert to hex
        newColor_d = {i:matplotlib.colors.rgb2hex(tcolor) for i,tcolor in d.items()}
        
        #replcae hashtag 
        """parser treats hashtags as comments"""
        newColor_d = {k:v.replace('#','?') for k,v in newColor_d.items()}
        
        #reset the base

        newColor_d[0] = oldColorVals_d['base'] #dont convert to hex
        
        #=======================================================================
        # update the table
        #=======================================================================
        tbw.set_values(j, newColor_d, axis=0)
        
        log.debug('set %i colors'%len(newColor_d))
        
        return
    
    
    def compile_candidates(self,
                           ):
        log = self.logger.getChild('compile_cand')
        tbw = self.tableWidget_P
        
        self.set_setup(set_cf_fp=True)
        #=======================================================================
        # get data from ui
        #=======================================================================
        df_raw = tbw.get_df()
        log.debug('retrieved %s'%str(df_raw.shape))
        
        """
        TODO: format those that dont match
        """
        self.feedback.upd_prog(20)
        #=======================================================================
        # construct candidate suite
        #=======================================================================
        log.debug('on %s'%str(df_raw.shape))
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiConstructor(**kwargs) as wrkr:
            wrkr.setup()
            meta_lib = wrkr.build_candidates(df_raw, copyDataFiles=self.checkBox_P_copyData.isChecked())
            

        log.info('compiled %i candidate models'%len(meta_lib))
        self.feedback.upd_prog(90)
        #=======================================================================
        # update run tab
        #=======================================================================
        #collect control files
        cf_fp_d = {mtag:d['cf_fp'] for mtag, d in meta_lib.items()}
        cf_fp_d ={**{'base':self.cf_fp}, **cf_fp_d} #add the base
        cf_fp_d = {k:{'cf_fp':v} for k,v in cf_fp_d.items()}
        
        self._change_tab('tab_run')
        self.tableWidget_R.populate(pd.DataFrame.from_dict(cf_fp_d).T)
        

        self.feedback.upd_prog(None)
        
        return
    
    def run_suite(self):
        
        log = self.logger.getChild('compile_cand')
        tabw = self.tableWidget_R
        self.set_setup(set_cf_fp=True)
        
        
        #=======================================================================
        # retrieve control files from table
        #=======================================================================
        cf_d=tabw.get_values(0, axis=1)
        #=======================================================================
        # execute sutie
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiSessRunner(**kwargs) as ses:
            res_lib, meta_d= ses.run_batch(cf_d, modLevel='L2')
            
            res_df = ses.analy_evalTot(res_lib)
            
            output = ses.write_pick(res_lib)
            
        #=======================================================================
        # update ui
        #=======================================================================
        self.lineEdit_A_pick_fp.setText(output)
        
        self.load_pick()
        
    def load_pick(self):
        log = self.logger.getChild('load_pick')
        self.set_setup(set_cf_fp=False)
        
        pick_fp = self.lineEdit_A_pick_fp.text()
        
        
 
 
            
            
        
        
            
            
        
        
        