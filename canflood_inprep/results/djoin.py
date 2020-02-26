'''
Created on Feb. 9, 2020

@author: cefect
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
from qgis.core import *
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject



#==============================================================================
# # custom
#==============================================================================
#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
    
    from hlpr.plug import QprojPlug as base_class

#plugin runs
else:
    base_class = object
    from hlpr.exceptions import QError as Error
    


from hlpr.Q import *
from hlpr.basic import *


#==============================================================================
# functions-------------------
#==============================================================================
class Djoiner(base_class):

    
    def __init__(self,
                 logger, out_dir, tag='test',
                 ):
        
        """inherited by the dialog.
        init is not called during the plugin"""
        logger.info('simple wrapper inits')
        
        #=======================================================================
        # attach inputs
        #=======================================================================
        self.logger = logger.getChild('Djoiner')
        self.wd = out_dir
        self.tag = tag

        
        super().__init__() #initilzie teh baseclass
        
        self.logger.info('init finished')
        
        
    def djoinRun(self,
              vlay_raw, #layer to join csv to (finv)
              data_fp, #filepath to tabular data
              link_coln, #linking column/field name
              keep_fnl = 'all', #list of field names to keep from the vlay (or 'all' to keep all)
              layname = None,
              tag = None,
              
              ): #join a vectorlay to a data frame from a key
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('djoin')
        if tag is None: tag = self.tag


        
        #=======================================================================
        # get the left data
        #=======================================================================
        
        df_raw = vlay_get_fdf(vlay_raw, logger=log).drop(['ogc_fid', 'fid'],axis=1, errors='ignore' )
        df_raw['fid'] = df_raw.index
        
        
        #======================================================================
        # drop to keeper fields
        #======================================================================
        if keep_fnl == 'all':
            log.info('keeping all fields')
            df1 = df_raw.copy()
        elif isinstance(keep_fnl, list):
            #check the request
            miss_l = set(keep_fnl).difference(df_raw.columns)
            if len(miss_l) > 0:
                raise Error('%i requested keeper fields not in data: \n    %s'%(len(miss_l), miss_l))
            
            #make sure the linker is in there
            if not link_coln in keep_fnl:
                keep_fnl.append(link_coln)
                
            if not 'fid' in keep_fnl:
                keep_fnl.append('fid')
            
            #make the slice
            df1 = df_raw.loc[:, keep_fnl]
            
            log.info('dropped to %i columns (from %i)'%(
                len(df1.columns), len(df_raw.columns)))
            
            
        else:
            raise Error('unexpected type on keep_fnl')
        
        

        #=======================================================================
        # get the join table
        #=======================================================================     
        basefn = os.path.splitext(os.path.split(data_fp)[1])[0]                          
        lkp_df1 = pd.read_csv(data_fp, index_col=None)
        
        # cleaning
        lkp_df = lkp_df1.dropna(axis = 'columns', how='all').dropna(axis = 'index', how='all')
        
        #======================================================================
        # checks
        #======================================================================
        if not len(df1) == len(lkp_df):
            raise Error('length mismatch')
        
        
        #=======================================================================
        # layer name
        #=======================================================================
        if layname is None: 
            layname='%s_%s_djoin'%(tag, basefn)
        
        #===========================================================================
        # chcek link column
        #===========================================================================
        boolcol = np.isin(df1.columns, lkp_df.columns) #find the column intersection
        
        if not np.any(boolcol):
            raise IOError('no intersecting columns in the loaded sets!')
        
        pos_cols = df1.columns[boolcol].tolist() #get these
        
        if len(pos_cols) == 0:
            raise Error('no overlapping columns/field names!')
        
        if not link_coln in lkp_df.columns:
            raise Error('requested link field \'%s\' not in the csv data!'%link_coln)
        
        """always expect a 1:1 on these"""
        if not lkp_df[link_coln].is_unique:
            raise Error('non-unique lookup keys \'%s\''%link_coln)
            
        if not df1[link_coln].is_unique:
            raise Error('non-unique vlay keys')
        
        #===========================================================================
        # do the lookup
        #===========================================================================
        res_df = df1.merge(lkp_df, 
                                how='inner', #only use intersect keys
                               on = link_coln,
                               validate= '1:1', #check if merge keys are unique in right dataset
                               indicator=False, #flag where the rows came from (_merge)
                               )
        
        log.info('merged %s w/ %s to get %s'%(
            str(df1.shape), str(lkp_df.shape), str(res_df.shape)))    
        

        
        #=======================================================================
        # generate hte new layer     
        #=======================================================================
        #get the raw goemetry
        geo_d = vlay_get_fdata(vlay_raw, geo_obj=True, logger=log)
        
        #expand it
        """shouldnt be necessary for 1:1"""
        if not res_df['fid'].is_unique:
            raise Error('bad link')
            #==================================================================
            # log.info('non unique keys (1:m) join... expanding geometry')
            # rfid_geo_d = hp.basic.expand_dict(geo_d, res_df['fid'].to_dict(),
            #                                   constructor=QgsGeometry)
            # res_df= res_df.drop('fid', axis=1)
            #==================================================================
        else:
            rfid_geo_d = geo_d
            res_df = res_df.set_index('fid', drop=True)
        
        
        
        res_vlay = vlay_new_df(res_df, geo_d=rfid_geo_d, crs = vlay_raw.crs(),
                                    layname=layname, logger=log)
        
        
        log.info('finished on \'%s\''%res_vlay.name())
        
        return res_vlay
     
    

if __name__ =="__main__": 
    
    out_dir = os.getcwd()
    
    #==========================================================================
    # load layers
    #==========================================================================
    finv_fp = r'C:\LS\03_TOOLS\CanFlood\_ins\20200225\finv_cconv_20200224_aoiT4.gpkg'
    
    """
    fid    xid    f0_tag    f0_scale    f0_cap    f0_elv    f1_cap    f1_elv    f1_scale    f1_tag    f3_cap    f3_elv    f3_scale    f3_tag    zid    fclass    sclass    gel    buck_id

    
    """
    vlay_raw = load_vlay(finv_fp)
    
    data_fp = r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200224\scenario1_risk_passet.csv'
    
    #==========================================================================
    # execute
    #==========================================================================
    res_vlay = Djoiner(mod_logger, out_dir).djoinRun(
        vlay_raw, data_fp,'xid', tag='CanFlood',
        keep_fnl=['fclass', 'xid', 'sclass'])
    
    #==========================================================================
    # save results
    #==========================================================================
    vlay_write(res_vlay, 
               os.path.join(os.getcwd(), '%s.gpkg'%res_vlay.name()),
               overwrite=True)    
    print('finished')
    

    
    
       


        