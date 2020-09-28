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

from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject



#==============================================================================
# # custom
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
    
from hlpr.Q import Qcoms

from hlpr.Q import *
from hlpr.basic import *


#==============================================================================
# functions-------------------
#==============================================================================
class Djoiner(Qcoms):
    """
    joining tabular data to vector geometry
    """

    
    def __init__(self,
                 **kwargs
                 ):
        

        mod_logger.info('simple wrapper inits')
        

        
        super().__init__(**kwargs) #initilzie teh baseclass
        
        self.logger.debug('init finished')
        
        
    def run(self,#join tabular results back to the finv
              vlay_raw, #finv vlay (to join results to)
              data_fp, #filepath to res_per asset tabular results data
              link_coln, #linking column/field name
              keep_fnl = 'all', #list of field names to keep from the vlay (or 'all' to keep all)
              layname = None,
              tag = None,
              logger = None,
              ): 
        """
        todo: clean this up and switch over to joinattributestable algo
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('djoin')
        if tag is None: tag = self.tag
        cid = link_coln

        
        #=======================================================================
        # get the left data from the vlay geomtry
        #=======================================================================
        
        df_raw = vlay_get_fdf(vlay_raw, logger=log, feedback=self.feedback
                              ).drop(['ogc_fid', 'fid'],axis=1, errors='ignore' )
                              
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
        
        
            
        #check key intersect
        """we allow the results lkp_df to be smaller than the vector layer"""
        l = set(lkp_df[cid]).difference(df1[link_coln])
        if not len(l)==0:
            
            bx = ~lkp_df[cid].isin(df1[link_coln])
            with pd.option_context('display.max_rows', None, 
                           'display.max_columns', None,
                           'display.width',1000):
                log.debug('missing entries %i (of %i)\n%s'%(bx.sum(), len(bx), lkp_df[bx]))
            
            
            raise Error('%i (of %i) \'%s\' entries in the results not found in the finv_vlay \'%s\'.. .see logger: \n    %s'%(
            len(l), len(lkp_df), cid, vlay_raw.name(), l))
        
        #===========================================================================
        # do the lookup
        #===========================================================================
        boolidx = df1[cid].isin(lkp_df[cid].values)
        
        res_df = df1.loc[boolidx, :].merge(lkp_df, 
                                how='inner', #only use intersect keys
                               on = link_coln,
                               validate= '1:1', #check if merge keys are unique in right dataset
                               indicator=False, #flag where the rows came from (_merge)
                               )
        
        assert len(res_df) == len(lkp_df)
        
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
            # rfid_geo_d = hp_basic.expand_dict(geo_d, res_df['fid'].to_dict(),
            #                                   constructor=QgsGeometry)
            # res_df= res_df.drop('fid', axis=1)
            #==================================================================
        else:
            rfid_geo_d = geo_d
            res_df = res_df.set_index('fid', drop=True)
        
        
        
        res_vlay = self.vlay_new_df2(res_df, geo_d=rfid_geo_d, crs = vlay_raw.crs(),
                                    layname=layname, logger=log)
        
        
        log.info('finished on \'%s\''%res_vlay.name())
        
        return res_vlay
     
    

if __name__ =="__main__": 
    print('start')
    out_dir = os.path.join(os.getcwd(), 'djoin')
    
    #==========================================================================
    # dev data
    #==========================================================================
    #==========================================================================
    # data_d = {
    #     'cconv':(
    #         r'C:\LS\03_TOOLS\CanFlood\_ins\20200225\finv_cconv_20200224_aoiT4.gpkg',
    #         r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200224\scenario1_risk_passet.csv'
    #         )
    #     
    #     }
    #==========================================================================
    
    #===========================================================================
    # tutorials
    #===========================================================================
    runpars_d={
        'Tut1a':{
            'finv_fp':r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1\data\finv_cT2b.gpkg',
            'data_fp':r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1\res_1a\risk1_Tut1_tut1a_passet.csv',
            'keep_fn':'all',
            'link_coln':'xid',
            },
        
        }

    runpars_d={
        'Tut1b':{
            'finv_fp':r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1\data\finv_cT2b.gpkg',
            'data_fp':r'C:\Users\cefect\CanFlood\build\1b\results\risk1_run1_tut2b_passet.csv',
            'keep_fn':'all',
            'link_coln':'xid',
            },
        
        }
        
    #==========================================================================
    # 20200304
    #==========================================================================
    #===========================================================================
    # runpars_d = {
    #     'ICIrec':{
    #         'finv_fp':r'C:\LS\03_TOOLS\CanFlood\_ins\20200304\finv\ICI_rec\finv_ICIrec_20200304_aoi05f.gpkg',
    #         'data_fp':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\risk1\risk1_ICIrec_scenario1_passet.csv',
    #         'keep_fn':'all',
    #         'link_coln':'xid',
    #         },
    #     'TDDres':{
    #         'finv_fp':r'C:\LS\03_TOOLS\CanFlood\_ins\20200304\finv\TDD_res\finv_cconv_20200224_TDDres.gpkg',
    #         'data_fp':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDD_res\risk1\risk1_TDDres_TDDres_passet.csv',
    #         'keep_fn':'all',
    #         'link_coln':'xid',
    #         },
    #     'TDDnrp':{
    #         'finv_fp':r'C:\LS\03_TOOLS\CanFlood\_ins\20200304\finv\TDD_nrp\finv_cconv_20200224_TDDnrp.gpkg',
    #         'data_fp':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDDnrp\risk1\risk1_TDDnrp_scenario1_passet.csv',
    #         'keep_fn':'all',
    #         'link_coln':'xid',          
    #         }
    #     }
    #===========================================================================
    
    #==========================================================================
    # execute
    #==========================================================================
    wrkr = Djoiner(logger=mod_logger, out_dir=out_dir)
    
    for tag, pars_d in runpars_d.items():
        log = mod_logger.getChild(tag)
        vlay_raw = load_vlay(pars_d['finv_fp'])
        
        """
                      vlay_raw, #layer to join csv to (finv)
              data_fp, #filepath to tabular data
              link_coln, #linking column/field name
              keep_fnl = 'all', #list of field names to keep from the vlay (or 'all' to keep all)
        """
        
        res_vlay = wrkr.run(
            vlay_raw, 
            pars_d['data_fp'],pars_d['link_coln'], tag=tag,
            keep_fnl=pars_d['keep_fn'],
            logger=log)
        
        #==========================================================================
        # save results
        #==========================================================================
        ofp = os.path.join(out_dir, '%s.gpkg'%res_vlay.name())
        vlay_write(res_vlay, ofp, overwrite=True)
        
        log.info('finished')    
        
        
    
    force_open_dir(out_dir)
    
    print('finished')
    

    
    
       


        