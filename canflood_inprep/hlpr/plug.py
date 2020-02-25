'''
Created on Feb. 25, 2020

@author: cefect


helper functions for use in plugins
'''

#==============================================================================
# imports------------
#==============================================================================
#python
import os, configparser, logging
import pandas as pd
import numpy as np
#qgis
from qgis.core import *
from qgis.analysis import QgsNativeAlgorithms
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QListWidget

mod_logger = logging.getLogger('Q') #creates a child logger of the root

#==============================================================================
# customs
#==============================================================================
if __name__ =="__main__": 
    from hlpr.exceptions import Error
else:
    from hlpr.exceptions import QError as Error

#==============================================================================
# classes-----------
#==============================================================================
class QprojPlug(object): #baseclass for plugins
    
    tag='scenario1'
    overwrite=True
    wd = ''
    
    """not a great way to init this one
    def __init__(self):
        self.logger = logger()"""
    
    def qproj_setup(self): #workaround to setup the project
        
        self.logger = logger(self) #init the logger
        self.qproj = QgsProject.instance()
        self.feedback = QgsProcessingFeedback()
        
        self.crs = self.qproj.crs()
        
        
    
    def output_df(self, #dump some outputs
                      df, 
                      out_fn,
                      out_dir = None,
                      overwrite=None,
                      write_index=True, 
            ):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.wd
        if overwrite is None: overwrite = self.overwrite
        log = self.logger.getChild('output_df')
        
        assert isinstance(out_dir, str), 'unexpected type on out_dir: %s'%type(out_dir)
        assert os.path.exists(out_dir), 'requested output directory doesnot exist: \n    %s'%out_dir
        
        
        #extension check
        if not out_fn.endswith('.csv'):
            out_fn = out_fn+'.csv'
        
        #output file path
        out_fp = os.path.join(out_dir, out_fn)
        
        #======================================================================
        # checeks
        #======================================================================
        if os.path.exists(out_fp):
            log.warning('file exists \n    %s'%out_fp)
            if not overwrite:
                raise Error('file already exists')
            

        #======================================================================
        # writ eit
        #======================================================================
        df.to_csv(out_fp, index=write_index)
        
        log.info('wrote to %s to file: \n    %s'%(str(df.shape), out_fp))
        
        return out_fp
    
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
        
    def set_overwrite(self): #action for checkBox_SSoverwrite state change
        if self.checkBox_SSoverwrite.isChecked():
            self.overwrite= True
        else:
            self.overwrite= False
            
        self.logger.push('overwrite set to %s'%self.overwrite)
        
    def update_cf(self, #update one parameter  control file 
                  new_pars_d, #new paraemeters {section : {valnm : value }}
                  cf_fp = None):
        
        log = self.logger.getChild('update_cf')
        
        #get defaults
        if cf_fp is None: cf_fp = self.cf_fp
        
        #initiliae the parser
        pars = configparser.ConfigParser(allow_no_value=True)
        _ = pars.read(self.cf_fp) #read it from the new location
        
        #loop and make updates
        for section, val_d in new_pars_d.items():
            for valnm, value in val_d.items():
                pars.set(section, valnm, value)
        
        #write the config file 
        with open(self.cf_fp, 'w') as configfile:
            pars.write(configfile)
            
        log.info('updated contyrol file w/ %i pars at :\n    %s'%(
            len(new_pars_d), cf_fp))
        
        return
    
    def deletecolumn(self,
                     in_vlay,
                     fieldn_l, #list of field names
                     invert=False, #whether to invert selected field names
                     layname = None,


                     ):

        #=======================================================================
        # presets
        #=======================================================================
        algo_nm = 'qgis:deletecolumn'
        log = self.logger.getChild('deletecolumn')
        self.vlay = in_vlay

        #=======================================================================
        # field manipulations
        #=======================================================================
        fieldn_l = self._field_handlr(in_vlay, fieldn_l,  invert=invert)
        
            

        if len(fieldn_l) == 0:
            log.debug('no fields requsted to drop... skipping')
            return self.vlay

        #=======================================================================
        # assemble pars
        #=======================================================================
        #assemble pars
        ins_d = { 'COLUMN' : fieldn_l, 
                 'INPUT' : in_vlay, 
                 'OUTPUT' : 'TEMPORARY_OUTPUT'}
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        res_vlay = res_d['OUTPUT']

        
        #===========================================================================
        # post formatting
        #===========================================================================
        if layname is None: 
            layname = '%s_delf'%self.vlay.name()
            
        res_vlay.setName(layname) #reset the name

        
        return res_vlay 
        
        

        
        
        
      
        
        
            
    def testit(self): #for testing the ui
        self.iface.messageBar().pushMessage("CanFlood", "youre doing a test", level=Qgis.Info)
        
        self.logger.info('test the logger')
        self.logger.error('erro rtest')
        
        log = self.logger.getChild('testit')
        
        log.info('testing the child')
        


class logger(object): #workaround for qgis logging pythonic
    log_tabnm = 'CanFlood' # qgis logging panel tab name
    
    log_nm = '' #logger name
    
    def __init__(self, parent):
        #attach
        self.parent = parent
        
        self.iface = parent.iface
        
    def getChild(self, new_childnm):
        
        #build a new logger
        child_log = logger(self.parent)
        
        #nest the name
        child_log.log_nm = '%s.%s'%(self.log_nm, new_childnm)
        
        return child_log
        
    def info(self, msg):
        self._loghlp(msg, Qgis.Info, push=False)


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
                msg_raw, qlevel, push=False):
        
        msg = '%s: %s'%(self.log_nm, msg_raw)
        
        QgsMessageLog.logMessage(msg, self.log_tabnm, level=qlevel)
        
        if push:
            self.iface.messageBar().pushMessage(self.log_tabnm, msg, level=qlevel)
            
            
            
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
                tmp_df.ix[i, j] = qval.text()

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
            
        