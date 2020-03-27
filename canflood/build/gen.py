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
        
    
    def slice_aoi(self, vlay):
        
        aoi_vlay = self.comboBox_aoi.currentLayer()
        
        if aoi_vlay is None:
            self.logger.info('no aoi selected... not slicing')
            return vlay
        else:
            self.logger.warning('aoi slicing not impelemented')
            return vlay
            
            #raise Error('aoi slicing not implemented')

                


if __name__ =="__main__": 
    write_vlay=True
    
    #===========================================================================
    # tutorial 1 (points)
    #===========================================================================
    data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1\data'
      
      
      
      
    finv_fp = os.path.join(data_dir, 'finv_cT2b.gpkg')
      
    cf_fp = os.path.join(data_dir, 'CanFlood_control_01.txt')
      
      
    cid='xid'
    tag='tut1'

    
    #===========================================================================
    # tutorial 2  (dtm)
    #===========================================================================
    #===========================================================================
    # data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\2\data'
    # raster_fns= ['dtm_cT1.tif']
    # finv_fp = os.path.join(data_dir, 'finv_cT2.gpkg')
    #  
    # cf_fp = os.path.join(data_dir, 'CanFlood_tutorial2.txt')
    # 
    # cid='xid'
    # tag='tut2_dtm'
    # as_inun=False
    # dtm_fp, dthresh = None, None
    #===========================================================================
    
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

    #==========================================================================
    # load the data
    #==========================================================================

    wrkr = Gen(logger=mod_logger, tag=tag, out_dir=out_dir, cid=cid,
                 )
    

    

    
    #==========================================================================
    # save results
    #==========================================================================

     

 
    force_open_dir(out_dir)
 
    print('finished')
    
    
    

    

            
        