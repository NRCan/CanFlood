'''
Created on Feb. 9, 2020

@author: cefect
'''
import os
from qgis.core import QgsWkbTypes
from hp import Error

class WSLSampler(object):
    
    def run(self,
            raster_l, #set of rasters to sample 
            finv, #inventory layer
            control_fp = '', #control file path
            cid = 'xid', #index field name on finv
            ):
        
        """
        #======================================================================
        # dev inputs
        #======================================================================
        raster_l:
            Gld_10e2_fail_cT1.tif
            Gld_10e2_si_cT1.tif
            Gld_20e1_fail_cT1.tif
            Gld_20e1_si_cT1.tif
            
        finv:
            finv_icomp_cT1.gpkg
        
        
        """
        
        #======================================================================
        # #load the data
        #======================================================================
                
        
        #======================================================================
        # #check the data
        #======================================================================
        
        #======================================================================
        # slice data by project aoi
        #======================================================================
        
        #======================================================================
        # sample
        #======================================================================
        gtype = QgsWkbTypes().displayString(finv.wkbType())
        
        if 'Polygon' in gtype: pass
            
            #ask for sample type (min/max/mean)
            
            #sample each raster
            
        elif 'Line' in gtype: pass
        
            #ask for sample type (min/max/mean)
            
            #sample each raster
            
            
        elif 'Point' in gtype: pass
        
            #sample each raster
        
        
            
        
        else:
            raise Error('unexpected geo type')
        

        
        #======================================================================
        # #check results
        #======================================================================
        #check results cid column matches set in finv
        
        #make sure there are no negative values
        
        #report on number of nulls
        

        
        #======================================================================
        # wrap
        #======================================================================
        #set 'event_name_set' variable based on names of loaded rasters
        

        
        #save reuslts to file
        out_fp = self.output(res_df)
        
        if not os.path.exists(control_fp): pass
            #create control file template
            
        #update control file: expos = out_fp
            
        