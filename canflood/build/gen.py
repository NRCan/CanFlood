'''
Created on Feb. 9, 2020

@author: cefect

general methods for Building
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, shutil



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
class Gen(Qcoms):
    """
    general methods for the Build dialog
    
    broken out for development/testing
    """


    
    
    def __init__(self,
                 fname='expos', #prefix for file name
                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        

        
        self.logger.info('Rsamp.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)

                


if __name__ =="__main__": 
    write_vlay=True
    
    #===========================================================================
    # tutorial 1 (points)
    #===========================================================================
    #===========================================================================
    # data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1\data'
    #  
    # raster_fns = ['haz_1000yr_cT2.tif', 'haz_1000yr_fail_cT2.tif', 'haz_100yr_cT2.tif', 
    #               'haz_200yr_cT2.tif','haz_50yr_cT2.tif']
    #  
    #  
    #  
    # finv_fp = os.path.join(data_dir, 'finv_cT2b.gpkg')
    #  
    # cf_fp = os.path.join(data_dir, 'CanFlood_control_01.txt')
    #  
    #  
    # cid='xid'
    # tag='tut1'
    # as_inun=False
    # dtm_fp, dthresh = None, None
    #===========================================================================
    
    #===========================================================================
    # tutorial 2  (dtm)
    #===========================================================================
    data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\2\data'
    raster_fns= ['dtm_cT1.tif']
    finv_fp = os.path.join(data_dir, 'finv_cT2.gpkg')
     
    cf_fp = os.path.join(data_dir, 'CanFlood_tutorial2.txt')
    
    cid='xid'
    tag='tut2_dtm'
    as_inun=False
    dtm_fp, dthresh = None, None
    
    #==========================================================================
    # tutorial 3 (polygons as inundation)
    #==========================================================================
    #===========================================================================
    # data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\3\data'
    #  
    # raster_fns = ['haz_1000yr_cT2.tif', 
    #               #'haz_1000yr_fail_cT2.tif', 
    #               #'haz_100yr_cT2.tif', 
    #               #'haz_200yr_cT2.tif',
    #               'haz_50yr_cT2.tif',
    #               ]
    # 
    # 
    #   
    # finv_fp = os.path.join(data_dir, 'finv_polys_t3.gpkg')
    #  
    # cf_fp = os.path.join(data_dir, 'CanFlood_control_01.txt')
    # 
    # #inundation sampling
    # dtm_fp = os.path.join(data_dir, 'dtm_cT1.tif')
    # as_inun=True
    # dthresh = 0.5
    # 
    # cid='zid'
    # tag='tut3'
    #===========================================================================
    
    
    out_dir = os.path.join(os.getcwd(), 'wsamp', tag)
    raster_fps = [os.path.join(data_dir, fn) for fn in raster_fns]
    #==========================================================================
    # load the data
    #==========================================================================

    wrkr = Rsamp(logger=mod_logger, tag=tag, out_dir=out_dir, cid=cid,
                 )
    
    def prog(progress):
        print('!!!progress: %s'%progress)
    
    wrkr.feedback.progressChanged.connect(prog)
    
    wrkr.ini_standalone()
    
    
    rlay_l, finv_vlay = wrkr.load_layers(raster_fps, finv_fp)
    
    if not dtm_fp is None:
        dtm_rlay = wrkr.load_rlay(dtm_fp)
    else:
        dtm_rlay = None
    
    #==========================================================================
    # execute
    #==========================================================================
    res_vlay = wrkr.run(rlay_l, finv_vlay, 
             crs = finv_vlay.crs(), 
             as_inun=as_inun, dtm_rlay=dtm_rlay,dthresh=dthresh,
             
             )
       
    wrkr.check()

    
    #==========================================================================
    # save results
    #==========================================================================
    outfp = wrkr.write_res(res_vlay)
    if write_vlay:
        ofp = os.path.join(out_dir, res_vlay.name()+'.gpkg')
        vlay_write(res_vlay,ofp, overwrite=True)
     
    wrkr.upd_cf(cf_fp)
 
    force_open_dir(out_dir)
 
    print('finished')
    
    
    

    

            
        