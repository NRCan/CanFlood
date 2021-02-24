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

from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, view
#from hlpr.basic import *
from model.modcom import Model

#==============================================================================
# functions-------------------
#==============================================================================
class Djoiner(Qcoms, Model):
    """
    joining tabular data to vector geometry
    """
    #===========================================================================
    # expectations from parameter file
    #===========================================================================
    exp_pars_md = {
        'parameters':{
            'cid':{'type':str}
            },

        }
    
    exp_pars_op={

        'risk_fps':{
             'dmgs':{'ext':('.csv',)},
             },
        'results_fps':{
             'r_passet':{'ext':('.csv',)},
             }
        }
    

    
    
    def __init__(self,
                 fp_attn = 'r_passet', #default attribute name to pull tabulat data from
                 **kwargs
                 ):

        super().__init__(**kwargs) #initilzie teh baseclass
        
        assert hasattr(self, fp_attn), 'bad dfp_attn: %s'%fp_attn
        self.fp_attn=fp_attn
        
        self.logger.debug('init finished')
        
        
    def run(self,#join tabular results back to the finv
              vlay_raw, #finv vlay (to join results to)
              data_fp=None, #filepath to res_per asset tabular results data
              fp_attn = None, #if no data_fp is provided, attribute name to use
              cid=None, #linking column/field name
              keep_fnl = 'all', #list of field names to keep from the vlay (or 'all' to keep all)
              layname = None,


              ): 
        """
        todo: clean this up and switch over to joinattributestable algo
 
        """
        
        #=======================================================================
        # defaults
        #=======================================================================

        log = self.logger.getChild('djoin')
        tag = self.tag
        if cid is None: cid = self.cid
        
        
        
        if data_fp is None:
            if fp_attn is None: fp_attn=self.fp_attn 
            data_fp = getattr(self, fp_attn)
            log.debug('using \'%s\' for data_fp and got : %s'%(fp_attn, data_fp))
            
            if layname is None:  layname='%s_%s_%s'%(fp_attn, self.name, tag)
        else:
            if layname is None:  layname='res_%s_%s'%(self.name, tag)
            
        assert os.path.exists(data_fp), '\'%s\' got bad data_fp: \'%s\''%(self.tag, data_fp)
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert vlay_raw.crs()==self.qproj.crs(), 'crs mismatch: \n    %s\n    %s'%(
            vlay_raw.crs(), self.qproj.crs())
        
        
        
        #=======================================================================
        # get the left data from the vlay geomtry
        #=======================================================================
        
        df_raw = vlay_get_fdf(vlay_raw, logger=log, feedback=self.feedback
                              ).drop(['ogc_fid', 'fid'],axis=1, errors='ignore' )
                              
        df_raw['fid'] = df_raw.index
        
        """
        view(df_raw)
        """
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
            if not cid in keep_fnl:
                keep_fnl.append(cid)
                
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
        #basefn = os.path.splitext(os.path.split(data_fp)[1])[0]                          
        lkp_df = pd.read_csv(data_fp, index_col=None).dropna(axis = 'columns', how='all').dropna(axis = 'index', how='all')
        

        #===========================================================================
        # chcek link column
        #===========================================================================
        

        
        assert cid in lkp_df.columns, 'requested link field \'%s\' not in the csv data!'%cid
        
        """always expect a 1:1 on these"""
        if not lkp_df[cid].is_unique:
            raise Error('non-unique lookup keys \'%s\''%cid)
            
        if not df1[cid].is_unique:
            raise Error('non-unique vlay keys')
        
        
            
        #check key intersect
        """we allow the results lkp_df to be smaller than the vector layer"""
        l = set(lkp_df[cid]).difference(df1[cid])
        if not len(l)==0:
            
            bx = ~lkp_df[cid].isin(df1[cid])
            with pd.option_context('display.max_rows', None, 
                           'display.max_columns', None,
                           'display.width',1000):
                log.debug('missing entries %i (of %i)\n%s'%(bx.sum(), len(bx), lkp_df[bx]))
            
            
            raise Error('%i (of %i) \'%s\' entries in the results not found in the finv_vlay \'%s\'.. .see logger: \n    %s'%(
            len(l), len(lkp_df), cid, vlay_raw.name(), l))
            
        #=======================================================================
        # column intersect
        #=======================================================================
        icols = set(lkp_df.columns).union(df1.columns)
        icols.remove(cid)
        
        if len(icols)>0:
            log.warning('got %i overlapping columns...taking data from vlay \n    %s'%(len(icols), icols))
        
        #===========================================================================
        # do the lookup
        #===========================================================================
        """
        view(lkp_df)
        view(res_df)
        view(res_vlay)
        res_df.columns
        """
        boolidx = df1[cid].isin(lkp_df[cid].values)
        
        res_df = df1.loc[boolidx, :].merge(lkp_df, 
                                how='inner', #only use intersect keys
                               on = cid,
                               validate= '1:1', #check if merge keys are unique in right dataset
                               indicator=False, #flag where the rows came from (_merge)
                               )
        

        assert res_df.columns.is_unique
        #reset index
        assert res_df['fid'].is_unique
        res_df = res_df.set_index('fid', drop=True).sort_index(axis=0)
        
        
        if not np.array_equal(res_df.index, df_raw.index):
            """aoi slicing?"""
            log.warning('index mismatch')
        
        log.info('merged %s w/ %s to get %s'%(
            str(df1.shape), str(lkp_df.shape), str(res_df.shape)))    
        
        #=======================================================================
        # generate hte new layer     
        #=======================================================================
        geo_d = vlay_get_fdata(vlay_raw, geo_obj=True, logger=log)

        res_vlay = self.vlay_new_df2(res_df, geo_d=geo_d, crs = vlay_raw.crs(),
                                    layname=layname, logger=log)
        
        
        log.info('finished on \'%s\''%res_vlay.name())
        
        return res_vlay
     
    




        