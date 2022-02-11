'''
Created on Feb. 11, 2022

@author: cefect

generating report template
'''
#==============================================================================
# imports------------
#==============================================================================
import logging, configparser, datetime, copy, shutil




import os
import numpy as np
import pandas as pd


#===============================================================================
# customs
#===============================================================================
from hlpr.exceptions import QError as Error
from hlpr.basic import view
 
from results.riskPlot import RiskPlotr


#==============================================================================
# functions-------------------
#==============================================================================
class ReportGenerator(RiskPlotr):
 
 
    #===========================================================================
    # expectations from parameter file
    #===========================================================================
    exp_pars_md = {
        'results_fps':{
             'r_ttl':{'ext':('.csv',)},
             }
        }
    
    exp_pars_op={
 
        }
    
    def __init__(self,
                figsize=(10,6),
                 **kwargs):
        
        super().__init__(figsize=figsize, **kwargs)
        
        self.dtag_d={**self.dtag_d,**{
            'r_ttl':{'index_col':None}}}
        
        #=======================================================================
        # paramters directory
        #=======================================================================
        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars')
        
        #=======================================================================
        # get the temlpate file
        #=======================================================================
        self.template_fp = os.path.join(self.pars_dir, 'CanFlood_report_template_01.qpt')

        assert os.path.exists(self.template_fp), 'passed template_fp is bad: \'%s\''%self.template_fp
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
    def prep_model(self):

        
        self.set_ttl() #load and prep the total results

        
        return 
    
    
    def create_report(self):
        pass