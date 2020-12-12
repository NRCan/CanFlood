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
    valid_par = None #validation parmater for control file writing
    valid = False

    def __init__(self,

                 cf_fp, #control file path
                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        

        
        #=======================================================================
        # load the control file
        #=======================================================================
        assert os.path.exists(cf_fp), 'provided parameter file path does not exist \n    %s'%cf_fp

        cpars = configparser.ConfigParser(inline_comment_prefixes='#')
        self.logger.info('validating parameters from \n     %s'%cpars.read(cf_fp))
        
        self.cpars = cpars
        self.cf_fp = cf_fp
        
        self.logger.debug('Vali.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def cf_check(self,
                 modObj #model object to run check against
                 ):
        
      
        cpars = self.cpars
        wrkr = modObj(self.cf_fp) #initilize it
        #=======================================================================
        # check against expectations
        #=======================================================================
        errors = []
        for chk_d, opt_f in ((modObj.exp_pars_md,False), (modObj.exp_pars_op,True)):
            _, l = wrkr.cf_chk_pars(cpars, copy.copy(chk_d), optional=opt_f)
            errors = errors + l
            
        #record which validation prameter this referes to (for control file updating)
        self.valid_par = modObj.valid_par
        if len(errors) == 0:
            self.valid = True
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
        self.update_cf(
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

        

    


                

#===============================================================================
# dev testing
#===============================================================================
if __name__ =="__main__": 
    tag='tag'
    cf_fp = r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\built\CanFlood_tut2.txt'
   
    
    
    out_dir = os.path.join(os.getcwd(), 'validator', tag)

    #==========================================================================
    # load the data
    #==========================================================================

    wrkr = Vali(cf_fp, logger=mod_logger, tag=tag, out_dir=out_dir, 
                 )
    
    from model.dmg2 import Dmg2
    from model.risk2 import Risk2
    
    res_d = dict()
    for vtag, modObj in {
        'dmg2':Dmg2,
        'risk2':Risk2
        }.items():
    
        
        errors = wrkr.cf_check(modObj)
        for e in errors:
            print('%s: %s'%(vtag, e))
        wrkr.cf_mark()
        
        #store
        if len(errors) == 0: 
            res_d[vtag] = True
        else:
            res_d[vtag] = False
    
    
    
    
    log.push('passed %i validations'%(len(res_d)))
    
    print('finished')
    
    
    

    

            
        