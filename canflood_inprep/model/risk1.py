'''
Created on Feb. 27, 2020

@author: cefect

impact lvl 1 model
'''


#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, logging.config
#logcfg_file = r'C:\Users\tony.decrescenzo\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\floodiq\_pars\logger.conf'
logger = logging.getLogger() #get the root logger
#logging.config.fileConfig(logcfg_file) #load the configuration file
#logger.info('root logger initiated and configured from file: %s'%(logcfg_file))
    
#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os

import pandas as pd
import numpy as np

from scipy import interpolate, integrate

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
from model.common import Model



class Risk1(Model):
    """
    model for summarizing inundation counts (positive depths)
    """
    
    valid_par='risk1'
    
    #expectations from parameter file
    exp_pars_md = {#mandataory: section: {variable: handles} 
        'parameters' :
            {'name':{'type':str}, 'cid':{'type':str},'res_per_asset':{'type':bool}, 
             'event_probs':{'values':('ari', 'aep')}, 'felv':{'values':('ground', 'datum')},
             'prec':{'type':int}, 'res_per_asset':{'type':bool}
             },
        'dmg_fps':{
             'finv':{'ext':('.csv',)},
             'expos':{'ext':('.csv',)},
                    },
        'risk_fps':{
             'aeps':{'ext':('.csv',)}
                    },
        'validation':{
            'risk1':{'type':bool}
                    }
         }
    
    exp_pars_op = {#optional expectations
        'dmg_fps':{
            'gels':{'ext':('.csv',)}
            
            }
        }
    
    def __init__(self,
                 par_fp,
                 out_dir = None,
                 logger = None
                 ):
        
        #init the baseclass
        super().__init__(par_fp, out_dir, logger) #initilzie teh baseclass
        
        #======================================================================
        # setup funcs
        #======================================================================
        
        
        self.load_data()
        
        self.logger.debug('finished __init__ on Risk1')
        
    def load_data(self): #load the data files
        cid = self.cid
        #load exposure data
        ddf = pd.read_csv(self.expos, index_col=None)
        
        #check it
        assert cid in ddf.columns, 'expos missing index column \"%s\''%cid
        
        #clean it
        ddf = ddf.set_index(cid, drop=True).sort_index(axis=1).sort_index(axis=0)
        
        #load remainders
        
        self.load_risk_data(ddf)
        







if __name__ =="__main__": 
    
    out_dir = os.path.join(os.getcwd(), 'risk1')
    
    """
    l = [0.0, 0.0, 1.0]
    
    l.remove(0.0)
    """

    #==========================================================================
    # dev data
    #==========================================================================

    
    cf_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk1\CanFlood_scenario1.txt'
    
    Risk1(cf_fp, out_dir=out_dir, logger=mod_logger)
    

    print('finished')