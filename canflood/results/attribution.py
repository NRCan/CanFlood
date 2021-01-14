'''
Created on Feb. 9, 2020

@author: cefect

attribution analysis
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, copy

from weakref import WeakValueDictionary as wdict

#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd




from hlpr.exceptions import QError as Error
    




#===============================================================================
# non-Qgis
#===============================================================================
from model.modcom import Model
from hlpr.basic import view

#==============================================================================
# functions-------------------
#==============================================================================
class Attr(Model):
    
    #===========================================================================
    # program vars
    #===========================================================================
    """todo: fix this"""
    valid_par='risk2' 
    attrdtag_in = 'attrimat03'
    #===========================================================================
    # expectations from parameter file
    #===========================================================================
    exp_pars_md = {
        'results_fps':{
             'attrimat03':{'ext':('.csv',)},
             'r2_ttl':{'ext':('.csv',)},
             'r2_passet':{'ext':('.csv',)},
             }
        }
    
    exp_pars_op=dict()
 
    


    def __init__(self,
                 cf_fp,

                  *args, **kwargs):
        
        super().__init__(cf_fp, *args, **kwargs)
        

        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
    def _setup(self):
        self.init_model()
        
        self.load_ttl()
        self.load_passet()
        
        self.load_attrimat(dxcol_lvls=3)
        
        #=======================================================================
        # post fix attrim
        #=======================================================================
        #reformat aep values
        atr_dxcol = self.data_d.pop(self.attrdtag_in)
        mdex = atr_dxcol.columns
        atr_dxcol.columns = mdex.set_levels(mdex.levels[0].astype(np.float), level=0)
        self.data_d[self.attrdtag_in] = atr_dxcol
        
        
        #=======================================================================
        # check
        #=======================================================================
        miss_l = set(atr_dxcol.columns.levels[0]).symmetric_difference(self.data_d['r2_passet'].columns)
        assert len(miss_l)==0, 'event mismatch'
        
        return self
        
    def load_ttl(self,
                   fp = None,
                   dtag = 'r2_ttl',

                   logger=None,
                    
                    ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('load_ttl')
        if fp is None: fp = getattr(self, dtag)
 
        
        
        #======================================================================
        # load it
        #======================================================================
        df_raw = pd.read_csv(fp, index_col=None)
        self.data_d[dtag] = df_raw.copy()
        #=======================================================================
        # clean
        #=======================================================================
        df = df_raw.drop('plot', axis=1)
        
        #drop EAD row
        boolidx = df['aep']=='ead'
        df = df.loc[~boolidx, :]
        df.loc[:, 'aep'] = df['aep'].astype(np.float)
        
        #drop extraploated
        boolidx = df['note']=='extraploated'
        df = df.loc[~boolidx, :].drop('note', axis=1)
        #=======================================================================
        # set it
        #=======================================================================
        self.eventNames = df['aep'].values
        
        self.data_d['ttl'] = df
        
        
    
    def load_passet(self, #load the per-asset results
                   fp = None,
                   dtag = 'r2_passet',

                   logger=None,
                    
                    ):
        #=======================================================================
        # defa8ults
        #=======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('load_passet')
        if fp is None: fp = getattr(self, dtag)
        cid = self.cid
        
        #======================================================================
        # load it
        #======================================================================
        df_raw = pd.read_csv(fp, index_col=0)
        
        #drop ead and format column
        df = df_raw.drop('ead', axis=1)
        df.columns = df.columns.astype(np.float)
        
        #drop extraploators and ead
        boolcol = df.columns.isin(self.eventNames)
        df = df.loc[:, boolcol].sort_index(axis=1, ascending=True)
        
        
        #=======================================================================
        # set it
        #=======================================================================
        self.cindex = df.index.copy() #set this for checks later
        self.data_d[dtag] = df
        
    def get_slice(self, #calculate new totals from a slice of the attriMat
                  slice_str,
                  logger=None):
        pass
    
    
    
    def get_mvals(self, #multiply attM to get attributed impacts
                  logger=None): 
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('get_mvals')
        
        rp_df = self.data_d['r2_passet'].copy()
        atr_dxcol = self.data_d[self.attrdtag_in].copy()
        
    
        

        
        
        #=======================================================================
        # multiply
        #=======================================================================
        dxcol = atr_dxcol.multiply(rp_df, level='aeps')
        """
        view(dxcol)
        view(atr_dxcol)
        view(rp_df)
        """

        
        
        
        return dxcol
        
        
        
        
        
            