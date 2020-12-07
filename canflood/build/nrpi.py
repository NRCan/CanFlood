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
class Nrpi(Qcoms):
    """
    general methods for the Build dialog
    
    broken out for development/testing
    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """


    def __init__(self,

                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        

        
        self.logger.info('Nrpi.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    
    def to_finv(self,
                in_vlay,
                drop_colns=['ogc_fid', 'fid'], #optional columns to drop from df
                new_data = {'f0_scale':1.0, 'f0_elv':0.0},
                ):
        
        log = self.logger.getChild('to_finv')
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(in_vlay, QgsVectorLayer)
        assert 'Point' in QgsWkbTypes().displayString(in_vlay.wkbType())
        dp = in_vlay.dataProvider()
        
        log.info('on %s w/ %i feats'%(in_vlay.name(), dp.featureCount()))
        
        
        #=======================================================================
        # extract data
        #=======================================================================
        df_raw = vlay_get_fdf(in_vlay, logger=log)
        df = df_raw.drop(drop_colns,axis=1, errors='ignore')
        
        geo_d = vlay_get_fdata(in_vlay, geo_obj=True, logger=log)
        
        
        #=======================================================================
        # add fields
        #=======================================================================
        #build the new data
        log.info('adding\n    %s'%new_data)
        new_df = pd.DataFrame(index=df.index, data=new_data)
        
        #join the two
        df1 = new_df.join(df)


        
        #=======================================================================
        # reconstruct layer
        #=======================================================================
        finv_vlay = self.vlay_new_df2(df1,  geo_d=geo_d, crs=in_vlay.crs(),
                                logger=log,
                                layname = '%s_finv'%in_vlay.name())
        
        #=======================================================================
        # wrap
        #=======================================================================
        fcnt = finv_vlay.dataProvider().featureCount()
        assert fcnt == dp.featureCount()
        
        log.info('finished w/ \'%s\' w/ %i feats'%(finv_vlay.name(), fcnt))
        
        
        return  finv_vlay
    
















                


if __name__ =="__main__": 
    write_vlay=True
    
    #===========================================================================
    # tutorial 5
    #===========================================================================
    tag = 'tut5'
    

    

    
    out_dir = os.path.join(r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\5\built')
    
    #===========================================================================
    # setup project
    #===========================================================================

    

    wrkr = Nrpi(logger=mod_logger, tag=tag, out_dir=out_dir)
    wrkr.ini_standalone()
    
    
    #===========================================================================
    # #w/ connect to vectorlayer
    #===========================================================================
    uriW = QgsDataSourceUri()
    uriW.setParam('crs','EPSG:3978')
    uriW.setParam('bbox','-2103574.4,343903.6,-1715268.4,576272.7')
    uriW.setParam('url', r'https://maps-cartes.ec.gc.ca/arcgis/rest/services/NPRI_INRP/NPRI_INRP/MapServer/0')
    
    in_vlay = QgsVectorLayer(uriW.uri(), 'NRPI_raw', 'arcgisfeatureserver')
    
    er_l = in_vlay.error().messageList()
    assert len(er_l)==0, er_l
    assert in_vlay.error().isEmpty()
    
    #===========================================================================
    # run converter
    #===========================================================================
    
    finv_vlay = wrkr.to_finv(in_vlay)
    

    
    #==========================================================================
    # save results
    #==========================================================================
    ofp = os.path.join(out_dir, finv_vlay.name()+'.gpkg')
    vlay_write(finv_vlay, ofp)

     

 
    force_open_dir(out_dir)
 
    print('finished')
    
    
    

    

            
        