'''
Created on Feb. 9, 2020

@author: cefect

Template for 'build' scripts
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, copy



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd


#Qgis imports
#from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject

#==============================================================================
# custom imports
#==============================================================================

from hlpr.exceptions import QError as Error
    

from hlpr.basic import ComWrkr
"""do we need the pyqgis handles?"""
#from hlpr.basic import *

#==============================================================================
# functions-------------------
#==============================================================================
class Vali(ComWrkr):
    """
    
    model validator worker
    
    kept separate from the model workers to keep init sequences clean
    
     TODO: add some more data checks?

    """
    valid_par = None #validation parmater for control file writing
    valid = False

    def __init__(self, **kwargs):
        
        super().__init__(**kwargs)
        
        #initlize the config parser
        if os.path.exists(self.cf_fp):
            self.config_cf()

        
        self.logger.debug('Vali.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
    def config_cf(self, #helper to initilaize the configParser
                 cf_fp=None,
                 logger=None):
        """
        broke this out for complex console runs where we don't have the cf_fp during init
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('config_cf')
        if cf_fp is None: cf_fp=self.cf_fp
        
        assert os.path.exists(cf_fp), \
            'provided parameter file path does not exist \n    %s'%cf_fp

        #=======================================================================
        # initilzie
        #=======================================================================
        cpars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('validating parameters from \n     %s'%cpars.read(cf_fp))
        
        self.cpars = cpars
        
        return cpars
        
        
    def cf_check(self, #check the control file against a passed model's expectation handles
                 modObj #model object to run check against
                 ):
        

        wrkr = modObj(cf_fp = self.cf_fp, logger=self.logger) #initilize it
        #=======================================================================
        # check against expectations
        #=======================================================================
        errors = wrkr.validate(self.cpars)
            
        #record which validation prameter this referes to (for control file updating)
        self.valid_par = modObj.valid_par
        if len(errors) == 0:
            self.valid = True
        else:
            self.valid = False
            
        return errors
    
    def cf_mark(self,#mark the validation in the control file
                valid_par = None,
                ): 
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('cf_mark')
        
        if valid_par is None: valid_par = self.valid_par
        
        assert isinstance(valid_par, str)
        
        #=======================================================================
        # write result to control file
        #=======================================================================
        self.set_cf_pars(
            {
                'validation':({valid_par:str(self.valid)},
                '# \'%s\' validated by validator.py at %s'%(
                    valid_par, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S'))
                                                                            )
             },
            cf_fp = self.cf_fp
            )
        
        log.info('%s=%s'%(valid_par, self.valid))
        
        return

        

    


                

    
    
    

    

            
        