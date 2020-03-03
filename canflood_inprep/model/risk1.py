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

#custom imports
import hp
from hp import Error, view


from model.common import Model



class Risk1(Model):
    pass







if __name__ =="__main__": 
    
    out_dir = os.path.join(os.getcwd(), 'risk1')
    
    """
    l = [0.0, 0.0, 1.0]
    
    l.remove(0.0)
    """

    #==========================================================================
    # dev data
    #==========================================================================
    data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk1'
    
    finv_fp = os.path.join(data_dir, r'finv_cT2.gpkg')
    
    lpol_fn_d = {'Gld_10e2_fail_cT1':r'exposure_likes_10e2_cT1_20200209.gpkg', 
              'Gld_20e1_fail_cT1':r'exposure_likes_20e1_cT1_20200209.gpkg'}
    
    
    lpol_fp_d = {k:os.path.join(data_dir, v) for k, v in lpol_fn_d.items()}
    
    #==========================================================================
    # load the data
    #==========================================================================
    
    wrkr = LikeSampler(mod_logger, tag='lisamp_testr', feedback=QgsProcessingFeedback())
    wrkr.ini_standalone(out_dir=out_dir) #setup for a standalone run
    
    lpol_d, finv_vlay = wrkr.load_layers(lpol_fp_d, finv_fp)
    
    #==========================================================================
    # execute
    #==========================================================================
    res_df = wrkr.run(finv_vlay, lpol_d)
    
    #convet to a vector
    res_vlay = wrkr.vectorize(res_df)
    
    
    wrkr.check()
    
    #==========================================================================
    # save results
    #==========================================================================
    vlay_write(res_vlay, 
               os.path.join(wrkr.out_dir, '%s.gpkg'%wrkr.resname),
               overwrite=True, logger=mod_logger)
    
    outfp = wrkr.write_res(res_df)
    
    wrkr.upd_cf(os.path.join(data_dir, 'CanFlood_scenario1.txt'))

    force_open_dir(out_dir)

    print('finished')