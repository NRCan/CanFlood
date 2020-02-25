'''
Created on Feb. 9, 2020

@author: cefect
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, logging.config, configparser, datetime



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd


#Qgis imports
from qgis.core import *
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject



# custom imports
if __name__ =="__main__": 
    from hlpr.exceptions import Error
else:
    from hlpr.exceptions import QError as Error


#==============================================================================
# functions-------------------
#==============================================================================
class Djoiner(object):

    
    def __init__(self,
                 logger, out_dir, tag='test',
                 ):
        
        """inherited by the dialog.
        init is not called during the plugin"""
        logger.info('simple wrapper inits')
        
        #=======================================================================
        # attach inputs
        #=======================================================================
        self.logger = logger.getChild('Qsimp')
        self.wd = out_dir
        self.tag = tag

        
        super().__init__() #initilzie teh baseclass
        
        self.logger.info('init finished')
        
        
    def djoin(self,
              vlay_raw, #layer to join csv to
              data_fp, #filepath to tabular data
              link_coln, #linking column/field name
              layname = None,
              
              ): #join a vectorlay to a data frame from a key
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('djoin')


        
        #=======================================================================
        # get the left data
        #=======================================================================
        
        df_raw = vlay_get_fdf(vlay_raw, logger=log).drop(['ogc_fid'],axis=1, errors='raise' )
        df_raw['fid'] = df_raw.index
        
        

        #=======================================================================
        # get the join table
        #=======================================================================                               
        lkp_df_raw = hp.pd.load_csv_df(data_fp, index_col=None, logger=log)
        
        # cleaning
        lkp_df = lkp_df_raw.dropna(axis = 'columns', how='all').dropna(axis = 'index', how='all')
        
        #=======================================================================
        # layer name
        #=======================================================================
        if layname is None: 
            basefn = hp.basic.get_basefn(fp)
            layname='%s_%s'%(basefn, tag)
        
        #===========================================================================
        # chcek link column
        #===========================================================================
        boolcol = np.isin(df_raw.columns, lkp_df.columns) #find the column intersection
        
        if not np.any(boolcol):
            raise IOError('no intersecting columns in the loaded sets!')
        
        pos_cols = df_raw.columns[boolcol].tolist() #get these
        
        if len(pos_cols) == 0:
            raise Error('no overlapping columns/field names!')
        
        if not link_coln in lkp_df.columns:
            raise Error('requested link field \'%s\' not in the csv data!'%link_coln)
        
        """always expect a 1:1 on these"""
        if not lkp_df[link_coln].is_unique:
            raise Error('non-unique lookup keys \'%s\''%link_coln)
            
        if not df_raw[link_coln].is_unique:
            raise Error('non-unique vlay keys')
        
        #===========================================================================
        # do the lookup
        #===========================================================================
        res_df = df_raw.merge(lkp_df, 
                                how='inner', #only use intersect keys
                               on = link_coln,
                               validate= '1:1', #check if merge keys are unique in right dataset
                               indicator=False, #flag where the rows came from (_merge)
                               )
        
        log.info('merged %s w/ %s to get %s'%(
            str(df_raw.shape), str(lkp_df.shape), str(res_df.shape)))    
        

        
        #=======================================================================
        # generate hte new layer     
        #=======================================================================
        #get the raw goemetry
        geo_d = vlay_get_fdata(vlay_raw, geo_obj=True, logger=log)
        
        #expand it
        """shouldnt be necessary for 1:1"""
        if not res_df['fid'].is_unique:
            raise Error('bad link')
            log.info('non unique keys (1:m) join... expanding geometry')
            rfid_geo_d = hp.basic.expand_dict(geo_d, res_df['fid'].to_dict(),
                                              constructor=QgsGeometry)
            res_df= res_df.drop('fid', axis=1)
        else:
            rfid_geo_d = geo_d
            res_df = res_df.set_index('fid', drop=True)
        
        
        
        res_vlay = self.vlay_new_df(res_df, geo_d=rfid_geo_d, crs = vlay_raw.crs(),
                                    layname=layname, logger=log)
        
        
        log.info('finished on \'%s\''%res_vlay.name())
        
        return res_vlay
     
    

if __name__ =="__main__": 
    

    base_dir = os.path.dirname(os.path.dirname(__file__)) #canflood
    logcfg_file = os.path.join(base_dir, '_pars', 'logger.conf')
    
    if not os.path.exists(logcfg_file):
        raise Error('logger config file does not exist:\n    %s'%logcfg_file)    
    
    from pathlib import Path
    
    os.getcwd()
    
    logger = logging.getLogger() #get the root logger
    logging.config.fileConfig(logcfg_file) #load the configuration file
    logger.info('root logger initiated and configured from file: %s'%(logcfg_file))
    
    
       


        