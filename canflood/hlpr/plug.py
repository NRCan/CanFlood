'''
Created on Feb. 25, 2020

@author: cefect


helper functions for use in plugins
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime

#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd


#Qgis imports
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject


from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, QObject 
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

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
class QprojPlug(ComWrkr): #baseclass for plugins
    
    tag='scenario1'
    overwrite=True
    wd = ''
    progress = 0
    
    """not a great way to init this one
    def __init__(self):
        self.logger = logger()"""
    
    def qproj_setup(self): #project inits for Dialog Classes
        
        self.logger = logger(self) #init the logger
        self.qproj = QgsProject.instance()
        

        
        self.crs = self.qproj.crs()
        
        """todo: 
        dont house feedback on the dialogs... use separate workers for this
        """
        self.feedback = QgsProcessingFeedback()
        

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
        #ask the user for the path
        fp = qfd(self, prompt)
        
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
        
    
    def setProgress(self, #Dialog level progress bar updating
                 prog_raw, #pass None to reset
                 method='raw', #whether to append value to the progress
                 ): 
        """
        method to update progress bar (and track progress)
        
        connect each tool to this function
        
        if your QProgressBar is not named 'progressBar', you'll need to set this attribute somewhere
        """
        #=======================================================================
        # reseting
        #=======================================================================
        if prog_raw is None:
            self.progessBar.reset()
            return
        
        #=======================================================================
        # setting
        #=======================================================================
        if method=='append':
            prog = min(self.progress + prog_raw, 100)
        elif method=='raw':
            prog = prog_raw
        elif method == 'portion':
            rem_prog = 100-self.progress
            prog = self.progress + rem_prog*(prog_raw/100)
            
        assert prog<=100
        self.progressBar.setValue(prog)
        
        self.progress=prog #set for later
        


        
        
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
            
        