'''
Created on Mar. 5, 2020

@author: cefect

converting from rfda formats
'''


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging, datetime

import pandas as pd
import numpy as np

from scipy import interpolate, integrate

start, ymd = datetime.datetime.now(), datetime.datetime.now().strftime('%Y%m%d')

#==============================================================================
# parametessr
#==============================================================================
l1 = ['False', 'FALSE', 'false', 'NO', 'No', 'no', 'N', 'n']
l2 = ['True','TRUE','true', 'yes','YES','Yes', 'Y', 'y']
truefalse_d = {
    **dict(zip(l1, np.full(len(l1), False))),
    **dict(zip(l2, np.full(len(l2), True)))
    }


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
    mod_logger = logging.getLogger('rfda') #get the root logger

    from hlpr.exceptions import QError as Error

from hlpr.Q import *
from hlpr.basic import *

mod_name = 'misc'

class Misc(Qcoms):
    
    # legacy index numbers
    legacy_ind_d = {0:'id1',1:'address',2:'id2',10:'class', 11:'struct_type', 13:'area', 
                    18:'bsmt_f', 19:'ff_height', 20:'lon',21:'lat', 25:'gel'}
    

    def __init__(self, 

                  **kwargs):
        

        
        mod_logger.info('%s.__init__ start'%mod_name)
        super().__init__(**kwargs) #initilzie teh baseclass
        
    def crv_lib_smry(self,
                     crv_d, #dictionary of curves
                     logger=None,
                     ):
        if logger is None: logger=self.logger
        log = logger.getChild('crv_lib_smry')
        
        raise Error('gave up')
        
def run2():
    """
    consolidate librarires
    """
    
    #===========================================================================
    # LMRFRA curves
    #===========================================================================
    tag ='%s_LMFRA'%mod_name
    out_dir = r'C:\LS\03_TOOLS\CanFlood\_outs\crv_consol\20200529'
    data_dir = r'C:\LS\03_TOOLS\CanFlood\_ins\20200529'
    
    
    #directory w/ curve librarires
    cLib_dir=r'C:\LS\03_TOOLS\CanFlood\_ins\20200529\curves'
    
    runpars_d={
        'sfd':{
            'out_dir':os.path.join(out_dir, 'sfd'),
            'finv_fp':os.path.join(data_dir, 'finv_tagSFD_01_20200522_pts.gpkg'),
            },
        'nrp':{
            'out_dir':os.path.join(out_dir, 'nrp'),
            'finv_fp':os.path.join(data_dir, 'finv_tagNRP_01_20200521_pts.gpkg'),
            },

        }
    
    #==========================================================================
    # setup session------
    #==========================================================================
         
    Wrkr = Misc(logger=mod_logger, out_dir=out_dir, tag=tag)
    log = mod_logger.getChild(tag)
    
    #===========================================================================
    # load------
    #===========================================================================
    crv_lib_d = dict()
    for dname, d in runpars_d.items():
        fp = d['curves_fp']
        assert os.path.exists(fp), '%s got bad fp: %s'%(dname, fp)
        
        crv_lib_d[dname] = pd.read_excel(fp, sheet_name=None, index=None, header=None)
        
        log.info('loaded %i tabs from %s'%(len(crv_lib_d[dname]), fp))
        
    
    #==========================================================================
    # execute
    #==========================================================================
    

def run1():

    
    out_dir = os.path.join(os.getcwd(),'build','other')

    #==========================================================================
    # dev data: curve conversion
    #==========================================================================
    tag ='%s_nrp'%mod_name
    data_dir = r'C:\LS\03_TOOLS\LML\_keeps2\curves\nrp\nrpPer_20200517125446'
    
    runpars_d={
        'inEq':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_inEq.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'inStk':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_inStk.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'outEq':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_outEq.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'outStk':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_outStk.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        }
     
    #==========================================================================
    # setup session------
    #==========================================================================
         
    Wrkr = Misc(logger=mod_logger, out_dir=out_dir, tag=tag)
    log = mod_logger.getChild(tag)
    
    #===========================================================================
    # load------
    #===========================================================================
    crv_lib_d = dict()
    for dname, d in runpars_d.items():
        fp = d['curves_fp']
        assert os.path.exists(fp), '%s got bad fp: %s'%(dname, fp)
        
        crv_lib_d[dname] = pd.read_excel(fp, sheet_name=None, index=None, header=None)
        
        log.info('loaded %i tabs from %s'%(len(crv_lib_d[dname]), fp))
        
    
    #==========================================================================
    # execute
    #==========================================================================
    #collect summary data from each library
    smry_d = dict()
    for dname, crv_d in crv_lib_d.items():
        smry_d = Wrkr.crv_lib_smry(crv_d)
    
    
    return out_dir
     
 
     
    
if __name__ =="__main__": 
    print('start')
    out_dir = run2()
    #force_open_dir(out_dir)
    print('finished')