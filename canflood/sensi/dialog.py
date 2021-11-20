'''
Created on Nov. 18, 2021

@author: cefect

ui class for the sensitivity analysis menu
'''
#===============================================================================
# imports------------
#===============================================================================
import os,  os.path, time


from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer

from hlpr.exceptions import QError as Error
#===============================================================================
# customs
#===============================================================================
import hlpr.plug

from sensi.coms import Shared as SensiWorker

#===============================================================================
# load qt ui
#===============================================================================
ui_fp = os.path.join(os.path.dirname(__file__), 'sensi.ui')
assert os.path.exists(ui_fp)
FORM_CLASS, _ = uic.loadUiType(ui_fp)

#===============================================================================
# Classes ---------
#===============================================================================
 

class SensiDialog(QtWidgets.QDialog, FORM_CLASS,  
                       hlpr.plug.QprojPlug):
    
    def __init__(self, iface, parent=None, **kwargs):
        """Constructor."""
        super(SensiDialog, self).__init__(parent)

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
        
        
    def connect_slots(self): #connect ui slots to functions 
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
                           default_wdir = os.path.join(os.path.expanduser('~'), 'CanFlood', 'build'))
        
        
        #=======================================================================
        # parameters----
        #=======================================================================
        self.pushButton_P_addCand.clicked.connect(self.add_cand_col)
        
        
        
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
        
    def load_base(self, #load teh base control file
                  ):
        #=======================================================================
        # default
        #=======================================================================
        log = self.logger.getChild('load_base')
        
        self.set_setup(set_cf_fp=True)
        
        #=======================================================================
        # prechecks
        #======================================================================= 
        if self.radioButton_SS_fpRel.isChecked():
            raise Error('Relative filepaths not implemented')

        self.feedback.upd_prog(10)
        
        #=======================================================================
        # load the base values----
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiWorker(**kwargs) as wrkr:
            wrkr.setup() #init the model
            cfPars_d = wrkr.cfPars_d #retrieve the loaded parameters
            
        #get just the parameters
        pars_d = {k:v  for sect, d in cfPars_d.items() for k,v in d.items() if not v==''}
        
    
        
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
        
        #populate w/ parameter values
        self.feedback.upd_prog(50)
        for row, (attn, val_raw) in enumerate(pars_d.items()):
            #drop to relative filename'
            val = val_raw
            if isinstance(val_raw, str):
                if ':' in val_raw:
                    val = os.path.basename(val_raw)
 
                
                
            tbw.setItem(row, 0, QTableWidgetItem(str(val)))
            
        log.debug('filled table')
        
        #add the first column
        self.add_cand_col()
        
        
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
        return
        
    def add_cand_col(self, #add a new column to the parmaeters tab
                     ):
        
        #=======================================================================
        # default
        #=======================================================================
        log = self.logger.getChild('load_base')
        
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
        
        log.info('added parameter column for \'%s\''%mtag)
        

        
        
        
            
            
        
        
        