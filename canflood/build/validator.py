'''
Created on Feb. 9, 2020

@author: cefect

Template for 'build' scripts
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
    #base_class = object
    from hlpr.exceptions import QError as Error
    

from hlpr.Q import *
from hlpr.basic import *

#==============================================================================
# functions-------------------
#==============================================================================
class Vali(Qcoms):
    """
    
    model validator worker
    
    kept separate from the model workers to keep init sequences clean

    """


    def __init__(self,
                 modObj, #model object to run check against
                 cf_fp, #control file path
                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.modObj=modObj
        
        #=======================================================================
        # load the control file
        #=======================================================================
        assert os.path.exists(cf_fp), 'provided parameter file path does not exist \n    %s'%cf_fp

        cpars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('validating parameters from \n     %s'%cpars.read(cf_fp))
        
        self.cpars = cpars
        
        
        self.logger.debug('Vali.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def cf_check(self,

                 ):
        
        modObj = self.modObj        
        cpars = self.cpars
        
        #=======================================================================
        # check against expectations
        #=======================================================================
        errors = []
        for chk_d, opt_f in ((modObj.exp_pars_md,False), (modObj.exp_pars_op,True)):
            _, l = modObj.cf_chk_pars(cpars, copy.copy(chk_d), optional=opt_f)
            errors = errors + l
            
            
        return errors

    


                


if __name__ =="__main__": 
    tag='tag'
    
   
    
    
    out_dir = os.path.join(os.getcwd(), 'wsamp', tag)

    #==========================================================================
    # load the data
    #==========================================================================

    wrkr = Gen(logger=mod_logger, tag=tag, out_dir=out_dir, 
                 )
    

    

    
    #==========================================================================
    # save results
    #==========================================================================

     

 
    force_open_dir(out_dir)
 
    print('finished')
    
    
    

    

            
        