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
    layname = None
    
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
        
        self.dtag_d={fp_attn:{'index_col':0},
                     'r_ttl':{'index_col':None}}
        
        
        
        self.logger.debug('init finished')
        
        
    
    def prep_model(self):
        #copy the raw over to the cleaned
        assert self.fp_attn in self.raw_d, 'missing \'%s\' in data'%self.fp_attn 
        self.data_d[self.fp_attn] = self.raw_d[self.fp_attn]
        self.resname='%s_%s_%s'%(self.fp_attn, self.tag, self.name)
        


        
    def run(self,#join tabular results back to the finv
              vlay_raw, #finv vlay (to join results to)
              df_raw=None,
              cid=None, #linking column/field name

            #data cleaning
              relabel = 'ari', #how to relable event fields using the ttl values
                #None: no relabling
                #aep: use aep values (this is typically teh form already)
                #ari: convert to ari values
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
        if cid is None: cid = self.cid
        if layname is None: layname=self.resname
        if layname is None: layname = 'djoin_%s_%s'%(self.tag, vlay_raw.name())
        assert isinstance(layname, str), 'got bad type on layname: %s'%type(layname)
        if df_raw is None: df_raw=self.data_d[self.fp_attn]

        #=======================================================================
        # get data
        #=======================================================================
        lkp_df = self._prep_table(df_raw, relabel, log=log)
        vlay_df = self._prep_vlay(vlay_raw, keep_fnl, log=log)

        
        #=======================================================================
        # join data
        #=======================================================================
        res_df = self.fancy_join(vlay_df, lkp_df, logger=log)

        #=======================================================================
        # generate hte new layer--------   
        #=======================================================================
        geo_d = vlay_get_fdata(vlay_raw, geo_obj=True, logger=log)

        #reformat column names as strings
        df = res_df.copy()
        df.columns = res_df.columns.astype(str)
        
        res_vlay = self.vlay_new_df2(df, geo_d=geo_d, crs = vlay_raw.crs(),
                                    layname=layname, logger=log)
        
        """
        view(df)
        view(df.isna())
        """

        
        log.info('finished on \'%s\''%res_vlay.name())
        
        return res_vlay
     
    def _prep_vlay(self, vlay_raw, keep_fnl, log=None):
        if log is None: log = self.logger.getChild('_prep_vlay') 
        
        assert vlay_raw.crs()==self.qproj.crs(), 'crs mismatch: \n    %s\n    %s'%(
        vlay_raw.crs(), self.qproj.crs())
        

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
            if not self.cid in keep_fnl:
                keep_fnl.append(self.cid)
                
            if not 'fid' in keep_fnl:
                keep_fnl.append('fid')
            
            #make the slice
            df1 = df_raw.loc[:, keep_fnl]
            
            log.info('dropped to %i columns (from %i)'%(
                len(df1.columns), len(df_raw.columns)))
            
            
        else:
            raise Error('unexpected type on keep_fnl')
        
        if not df1[self.cid].is_unique:
            raise Error('non-unique vlay keys')
        
        return df1
    
    def _prep_table(self, df_raw, relabel, log=None):
        if log is None: log = self.logger.getChild('_prep_table') 
        
        #basefn = os.path.splitext(os.path.split(data_fp)[1])[0]                          
        df_raw = df_raw.dropna(
            axis = 'columns', how='all').dropna(axis = 'index', how='all')
            
        #log.debug('loaded %s from %s'%(str(df_raw.shape), data_fp))
        #=======================================================================
        # convert event probs
        #=======================================================================
        if not relabel is None: #aep to ari
            #===================================================================
            # attn = 'r_ttl'
            # #load the events data
            # assert hasattr(self, attn)
            # attv = getattr(self, attn)
            # assert not attv=='', 'passed empty %s filepath!'%attn
            # assert os.path.exists(attv), 'bad %s filepath: \'%s\''%(attn, attv)
            # rttl_df_raw = pd.read_csv(attv)
            #===================================================================
            rttl_df_raw = self.raw_d['r_ttl']
            
            #drop the aep row
            rttl_df = rttl_df_raw.loc[np.invert(rttl_df_raw['note']=='integration'), :]
            assert 'ead' not in rttl_df['aep']
            
            #check the raw event column types
            #===================================================================
            # col_types = np.array([type(e).__name__ for e in df_raw.columns])
            # assert len(np.unique(col_types))==1, 'expected data column labels to be type: str'
            #===================================================================
            
            #find event columns
            boolcol = df_raw.columns.astype(str).isin(rttl_df['aep'].astype(str))
            assert boolcol.any(), 'failed to identify aep columns in raw data'
            
            #do the conversion
            if relabel == 'aep':
                #convert columns to float
                """not really necessary... but consistent typesetting may be useful"""
                d = {coln:float(coln) for coln in df_raw.columns[boolcol]}
                
            elif relabel == 'ari':
                """very similar to _get_ttl_ari()"""
                ar = df_raw.columns[boolcol].astype(float).values
                
                ar_ari = 1/np.where(ar==0, #replaced based on zero value
                           sorted(ar)[1]/10, #dummy value for zero (take the second smallest value and divide by 10)
                           ar)
                                                   
                d = dict(zip(df_raw.columns[boolcol], ar_ari.astype(np.int)))
                
                #add padd
                d = {k:'%05d'%v for k,v in d.items()}
            
            else:raise Error('unrecognized relable key: \'%s\''%relabel)
            
            #add prefix
            d = {k:'%s_%s'%(relabel, v) for k,v in d.items()}
            df = df_raw.rename(columns=d)
            

        else:
            df = df_raw.copy()
                
        
        #===========================================================================
        # chcek link column
        #===========================================================================
        assert self.cid ==df.index.name, 'requested link field \'%s\' not in the csv data!'%self.cid
        
        """always expect a 1:1 on these"""
        if not df.index.is_unique:
            raise Error('non-unique lookup keys \'%s\''%self.cid)
        
        try:
            df = df.round(self.prec)
        except:
            log.warning('failed to round')
        
        
        return df.reset_index(drop=False)
    
    def fancy_join(self, 
                   lkp_df, vlay_df, 
                   logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('fancy_join')
        #=======================================================================
        # #check key intersect
        #=======================================================================
        """we allow the results lkp_df to be smaller than the vector layer"""
        l = set(lkp_df[self.cid]).difference(vlay_df[self.cid])
        if not len(l)==0:
            
            bx = ~lkp_df[self.cid].isin(vlay_df[self.cid])
            with pd.option_context('display.max_rows', None, 
                           'display.max_columns', None,
                           'display.width',1000):
                log.debug('missing entries %i (of %i)\n%s'%(bx.sum(), len(bx), lkp_df[bx]))
            
            
            raise Error('%i (of %i) \'%s\' entries in the results not found in the finv_vlay. .see logger: \n    %s'%(
            len(l), len(lkp_df), self.cid, l))
            
        #=======================================================================
        # column intersect
        #=======================================================================
        icols = set(lkp_df.columns).union(vlay_df.columns)
        icols.remove(self.cid)
        
        if len(icols)>0:
            log.warning('got %i overlapping columns...taking data from vlay \n    %s'%(len(icols), icols))
        
        #===========================================================================
        # join-----------
        #===========================================================================
        boolidx = vlay_df[self.cid].isin(lkp_df[self.cid].values)
        
        res_df = vlay_df.loc[boolidx, :].merge(lkp_df, 
                                how='inner', #only use intersect keys
                               on = self.cid,
                               validate= '1:1', #check if merge keys are unique in right dataset
                               indicator=False, #flag where the rows came from (_merge)
                               )
        

        assert res_df.columns.is_unique
        #reset index
        assert res_df['fid'].is_unique
        res_df = res_df.set_index('fid', drop=True).sort_index(axis=0)
        
        
        if not np.array_equal(res_df.index, vlay_df.index):
            """aoi slicing?"""
            log.warning('index mismatch')
        
        log.info('merged %s w/ %s to get %s'%(
            str(vlay_df.shape), str(lkp_df.shape), str(res_df.shape)))   
        
        return res_df
    




        