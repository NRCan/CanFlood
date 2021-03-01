'''
Created on Feb. 9, 2020

@author: cefect

cost benefit calculations
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, copy, shutil



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd


import openpyxl




#===============================================================================
# customs
#===============================================================================
from hlpr.exceptions import QError as Error
from hlpr.basic import view
 
from results.riskPlot import RiskPlotr

#==============================================================================
# functions-------------------
#==============================================================================
class CbaWrkr(RiskPlotr):
 
    
 

    def __init__(self,
 
                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        #=======================================================================
        # paramters directory
        #=======================================================================
        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars')
        
        #=======================================================================
        # get the temlpate file
        #=======================================================================
        self.template_fp = os.path.join(self.pars_dir, 'cf_bca_template_01.xlsx')

        assert os.path.exists(self.template_fp), 'passed template_fp is bad: \'%s\''%self.template_fp
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
    def copy_template(self, #copy the cba template worksheet
                          template_fp = None,
                          logger=None,
                          ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('copy_template')
        
        if template_fp is None: template_fp=self.template_fp
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert os.path.exists(template_fp), 'passed template_fp is bad: \'%s\''%template_fp
        
        #=======================================================================
        # load
        #=======================================================================
        wbook = openpyxl.load_workbook(template_fp)
        wsheet = wbook['smry']
        log.info('loaded worksheet from: \n    %s'%template_fp)
        #=======================================================================
        # add data----
        #=======================================================================
        #=======================================================================
        # scenario description
        #=======================================================================
        meta_d = dict() #collect for reporting
        #loop through select rows, check, and set the new value
        for evalA, nvalB in {
            'name':self.name,
            'control_filename':os.path.basename(self.cf_fp),
            'ead_total':'?',
            'timestamp':self.today_str
            }.items():
            
            #===================================================================
            # #find first location with this expectstion
            #===================================================================
            cellA = None
            for row in wsheet.iter_rows(max_col=1, max_row=30, min_row=5):
                for c in row:
                    if c.value==evalA:
                        cellA = c
                        break #stop heere and  use this cell
            
            #check fail
            if cellA is None:
                log.warning('unable to locate \'%s\' on template... skipping'%evalA)
                continue #skip 
                
            log.debug('found \'%s\' at %s'%(evalA, cellA.coordinate))
            
            #===================================================================
            # set the value
            #===================================================================
            #get value cell
            cellB = wsheet.cell(row=cellA.row, column=2)
            
            #set the new value
            cellB.value=nvalB
            
            #report
            log.debug('set %s=%s'%(cellB.coordinate, nvalB))
            meta_d[cellB.coordinate] = cellB.value
            
        log.info('updated template \'smry\' tab w/\n      %s'%meta_d)
        
    
        #=======================================================================
        # wrap
        #=======================================================================
        self.wbook = wbook #set for saving
        return self.wbook
    
    def write_wbook(self, #helper to write the openpyxl workbo0ok to file
                       wbook=None,
                       ofp=None,
                       logger=None):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if wbook is None: wbook=self.wbook
        if ofp is None: ofp = os.path.join(self.out_dir, '%s_%s_cba.xlsx'%(self.name, self.tag))
        if logger is None: logger=self.logger
        log=logger.getChild('write_wbook')
        
        #=======================================================================
        # write
        #=======================================================================
        wbook.save(ofp)
        log.info('wrote workbook to file \n    %s'%(ofp))
        
        return ofp
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        

            
 
        
        
        
        
        
        
        
        

    
    
    

    

            
        