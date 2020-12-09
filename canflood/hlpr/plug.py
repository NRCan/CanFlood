'''
Created on Feb. 25, 2020

@author: cefect


helper functions for use in plugins
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, sys

#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd


#Qgis imports
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject


from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog, QPushButton
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt 

#==============================================================================
# custom imports
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error

#plugin runs
else:

    from hlpr.exceptions import QError as Error

    

from hlpr.Q import *
from hlpr.basic import *

#==============================================================================
# classes-----------
#==============================================================================
class QprojPlug(Qcoms): #baseclass for plugins
    
    tag='scenario1'
    overwrite=True
    wd = ''
    progress = 0
    
    invalid_cids = ['fid', 'ogc_fid']
    
    """not a great way to init this one
    def __init__(self):
        self.logger = logger()"""
    
    def qproj_setup(self): #project inits for Dialog Classes
        """
        todo: change this to an __init__
        """
        
        self.logger = logger(self) #init the logger
        self.qproj = QgsProject.instance()
        
        self.crs = self.qproj.crs()
        
        """connect to UI's progress bar
            expects 'progressBar' as the widget name
            start feedback instance"""
            
        self.setup_feedback(progressBar = self.progressBar,
                            feedback = MyFeedBackQ())
        
        #=======================================================================
        # default directories
        #=======================================================================

        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars')
        assert os.path.exists(self.pars_dir)

        

    def get_cf_fp(self):
        cf_fp = self.lineEdit_cf_fp.text()
        
        if cf_fp is None or cf_fp == '':
            raise Error('need to specficy a control file path')
        if not os.path.exists(cf_fp):
            raise Error('need to specficy a valid control file path')
        
        if not os.path.splitext(cf_fp)[1] == '.txt':
            raise Error('unexpected extension on Control File')
        
        return cf_fp
    
    def get_wd(self):
        wd = self.lineEdit_wd.text()
        
        if wd is None or wd == '':
            raise Error('need to specficy a Working Directory')
        if not os.path.exists(wd):
            os.makedirs(wd)
            self.logger.info('built new working directory at:\n    %s'%wd)
        
        
        return wd
    
    def browse_button(self, 
                      lineEdit, #text bar where selected directory should be displayed
                      prompt = 'Select Directory', #title of box
                      qfd = QFileDialog.getExistingDirectory, #dialog to launch
                      ):
        
        #get the currently displayed filepath
        fp_old = lineEdit.text()
        
        #change to default if nothing useful is there
        if not os.path.exists(fp_old):
            fp_old = os.getcwd()
        
        #launch the dialog and get the new fp from the user
        fp = qfd(self, prompt, fp_old)
        
        #just take the first
        if len(fp) == 2:
            fp = fp[0]
        
        #see if they picked something
        if fp == '':
            self.logger.error('user failed to make a selection. skipping')
            return 
        
        #update the bar
        lineEdit.setText(fp)
        
        self.logger.info('user selected: %s'%fp)
        
    def fileSelect_button(self, #
                      lineEdit, #text bar where selected directory should be displayed
                      caption = 'Select File', #title of box
                      path = None,
                      filters = "All Files (*)",
                      qfd = QFileDialog.getOpenFileName, #dialog to launch
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        if path is None:
            path = os.getcwd()
            
        assert os.path.exists(path)
        #ask the user for the path
        """
        using the Dialog instance as the QWidge parent
        """
        self.logger.info(filters)
        
        fp = qfd(self, caption, path, filters)
        
        #just take the first
        if len(fp) == 2:
            fp = fp[0]
        
        #see if they picked something
        if fp == '':
            self.logger.error('user failed to make a selection. skipping')
            return 
        
        #update the bar
        lineEdit.setText(fp)
        
        self.logger.info('user selected: \n    %s'%fp)
        
    def mfcb_connect(self, #helper to update a field combo box
                           mfcb, #mFieldComboBox
                           layer, #layer to set in the combo box
                           fn_str = None, #optional field name for auto setting
                           ):
        
        mfcb.clear()
        if isinstance(layer, QgsVectorLayer):
            try:
                mfcb.setLayer(layer)
                
                #try and match
                for field in layer.fields():
                    if fn_str in field.name():
                        break
                    
                mfcb.setField(field.name())
                
            except Exception as e:
                self.logger.warning('failed set current layer w/ \n    %s'%e)
        else:
            self.logger.warning('failed to get a vectorlayer')
            
        return 
    

    def set_overwrite(self): #action for checkBox_SSoverwrite state change
        if self.checkBox_SSoverwrite.isChecked():
            self.overwrite= True
        else:
            self.overwrite= False
            
        self.logger.push('overwrite set to %s'%self.overwrite)
        
    def field_selectM(self, #select mutliple fields
                      vlay):
        """
        TODO: mimc the Qgis Algo multiple feature selection dialog
        """
        
        class NewDialog(QWidget):
            def __init__(self):
                super().__init__()
                
                self.initUI()
                
            def initUI(self):      
    
                
                self.le = QLineEdit(self)
                self.le.move(130, 22)
                
                self.setGeometry(300, 300, 290, 150)
                self.setWindowTitle('Multiple Selection')
                self.show()
                
    def setup_comboBox(self, #helper for setting up a combo box with a default selection
                       comboBox,
                       selection_l, #list of values to set as selectable options
                       default = 'none', #default selection string ot set
                       
                       ):
        
        assert isinstance(selection_l, list)
        
        assert default in selection_l
        
        comboBox.clear()
        #set the selection
        comboBox.addItems(selection_l)
        
        #set the default
        index = comboBox.findText(default, Qt.MatchFixedString)
        if index >= 0:
            comboBox.setCurrentIndex(index)
        
        

class logger(object): #workaround for qgis logging pythonic
    log_tabnm = 'CanFlood' # qgis logging panel tab name
    
    log_nm = '' #logger name
    
    def __init__(self, parent,
                 statusQlab = None, #Qlabel widget to duplicate push messages
                 ):
        #attach
        self.parent = parent
        
        self.iface = parent.iface
        
        self.statusQlab = statusQlab
        
    def getChild(self, new_childnm):
        
        #build a new logger
        child_log = logger(self.parent, 
                           statusQlab=self.statusQlab)
        
        #nest the name
        child_log.log_nm = '%s.%s'%(self.log_nm, new_childnm)
        
        return child_log
    
    def setLevel(self,*args):
        """
        todo: have this behave more like a real python logger
        """
        pass 
        
    def info(self, msg):
        self._loghlp(msg, Qgis.Info, push=False, status=True)


    def debug(self, msg_raw):
        msg = '%s: %s'%(self.log_nm, msg_raw)
        QgsLogger.debug(msg)
        
    def warning(self, msg):
        self._loghlp(msg, Qgis.Warning, push=False)

        
    def push(self, msg):
        self._loghlp(msg, Qgis.Info, push=True)

    def error(self, msg):
        self._loghlp(msg, Qgis.Critical, push=True)
        
    def _loghlp(self, #helper function for generalized logging
                msg_raw, qlevel, 
                push=False,
                status=False):
        
        msg = '%s: %s'%(self.log_nm, msg_raw)
        
        QgsMessageLog.logMessage(msg, self.log_tabnm, level=qlevel)
        
        #Qgis bar
        if push:
            self.iface.messageBar().pushMessage(self.log_tabnm, msg, level=qlevel)
        
        #Optional widget
        if status or push:
            if not self.statusQlab is None:
                self.statusQlab.setText(msg_raw)
                
            
#==============================================================================
# functions-----------
#==============================================================================
         
def qtbl_get_df( #extract data to a frame from a qtable
        table, 
            ):

    #get lables    
    coln_l = qtlb_get_axis_l(table, axis=1)
    rown_l = qtlb_get_axis_l(table, axis=0)
    


    tmp_df = pd.DataFrame( 
                columns=coln_l, # Fill columnets
                index=rown_l # Fill rows
                ) 

    for i in range(len(rown_l)):
        for j in range(len(coln_l)):
            qval = table.item(i, j)
            
            if not qval is None:
                tmp_df.iloc[i, j] = qval.text()

    return tmp_df


def qtlb_get_axis_l(table, axis=0): #get axis lables from a qtable
    #row names
    if axis == 1:
        q_l  = [table.horizontalHeaderItem(cnt) for cnt in range(table.rowCount())]
    elif axis == 0:
        q_l  = [table.verticalHeaderItem(cnt) for cnt in range(table.rowCount())]
        
    
    #get data
    l = []
    for qval in q_l:
        if qval is None:
            l.append('UnNamed')
        else:
            l.append(qval.text())
        
    return l
            

if __name__ =="__main__": 
    
    class Example(QWidget):
    
        def __init__(self):
            super().__init__()
            
            self.initUI()
            
            
        def initUI(self):      
    
            self.btn = QPushButton('Dialog', self)
            self.btn.move(20, 20)
            self.btn.clicked.connect(self.showDialog)
            
            self.le = QLineEdit(self)
            self.le.move(130, 22)
            
            self.setGeometry(300, 300, 290, 150)
            self.setWindowTitle('Input dialog')
            self.show()
            
            
        def showDialog(self):
            
            text, ok = QInputDialog.getText(self, 'Input Dialog', 
                'Enter your name:')
            
            if ok:
                self.le.setText(str(text))
            
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
            
            
    
    print('finisshed')
        