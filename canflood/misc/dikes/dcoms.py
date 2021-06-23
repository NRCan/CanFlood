'''
Created on Feb. 9, 2020

@author: cefect

simple build routines
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
from pandas import IndexSlice as idx

#Qgis imports

import processing
#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    
from hlpr.basic import ComWrkr, view
    

    
#from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class Dcoms(ComWrkr):
    """
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """
    #data labels
    wsln = 'wsl'
    celn = 'crest_el'
    sdistn = 'segTr_dist' #profile distance of transect (along dike)
    segln = 'sid_len'
    fbn = 'freeboard'
    sid = 'sid' #global segment identifier
    
    nullSamp = -999 #value for bad samples
    
    lfxn = 'lenfx_SF'
    pfn = 'p_fail'

    
    #program containers
    expo_dxcol = None #exposure data

    def __init__(self,                  
             dikeID = 'dikeID', #dike identifier field
             segID = 'segID', #segment identifier field
             cbfn = 'crest_buff', #crest buffer field name
             ifidN = 'ifzID', #influence polygon id field name
                  *args,  **kwargs):
        
        super().__init__(*args,**kwargs)
        
        #=======================================================================
        # attach
        #=======================================================================
        self.dikeID, self.segID = dikeID, segID #done during init
        self.cbfn = cbfn
        self.ifidN = ifidN
        

        
        #=======================================================================
        # checks
        #=======================================================================
        for coln in [self.dikeID, self.segID, self.segln, self.cbfn, self.celn, self.ifidN]:
            assert isinstance(coln, str), 'bad type on %s: %s'%(coln, type(coln))
            assert not coln =='', 'got empty string for \'%s\''%coln
            
        self.logger.debug('Dcoms.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        

    def load_expo(self, #load the dike segment exposure data
                  fp=None,
                  df=None,
                  prop_colns = None,
                  logger=None):
        """
        TODO: make this more general (for dRes)
        """
        
        if logger is None: logger=self.logger
        
        log = logger.getChild('load_expo')
        
        if df is None:
            df = pd.read_csv(fp, header=0, index_col=0)
        
        

        
        #=======================================================================
        # tags
        #=======================================================================
        """duplicated in _get_etags()"""
        tag_l = [c for c in df.columns if c.endswith('_dtag')]
        assert len(tag_l)>0, 'failed to find any tag columns'
        
        etag_l = self._get_etags(df, prop_colns=prop_colns)
        
        """
        view(df)
        view(self.expo_df)
        """
        df.loc[:, etag_l] = df.loc[:, etag_l].round(self.prec)
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('loaded expos_df w/ %i dtags and %i etags'%(len(tag_l), len(etag_l)))
        
        #collapse all dtags
        l1 = [col.unique().tolist() for coln, col in df.loc[:, tag_l].items()]
        self.dtag_l = set([item for sublist in l1 for item in sublist])
        
        self.etag_l = etag_l
        self.expo_df = df
        
        return self.expo_df
        
    def _get_etags(self,   #exposure column names
                   df,
                   prop_colns = None,
                   ):
        
        #=======================================================================
        # precheck
        #=======================================================================
        if prop_colns is None:
            prop_colns = [self.dikeID, self.segID, self.segln, self.cbfn, self.celn, self.ifidN]
        miss_l = set(prop_colns).difference(df.columns)
        assert len(miss_l)==0, 'passed data is missing %i required columns. are the dike fields correct? \n    %s'%(
            len(miss_l), miss_l)
        
        
        #=======================================================================
        # tags
        #=======================================================================
        tag_l = [c for c in df.columns if c.endswith('_dtag')]
        assert len(tag_l)>0, 'failed to find any tag columns'
        
        #=======================================================================
        # scratch columns
        #=======================================================================
        l1 = set(prop_colns).union(tag_l)
        
        scratch_l = df.columns[df.columns.str.contains('~')].values.tolist()
        assert len(set(scratch_l).intersection(l1))==0, 'got some scratch columns in required set'
        #=======================================================================
        # events
        #=======================================================================
        #those we dont want
        etag_l = list(set(df.columns).difference(l1.union(set(scratch_l))))
        assert len(etag_l)>0, 'failed to get any eTags'
        etag_l.sort()
        
        return etag_l
        
        
        
    def load_expo_dx(self, #load the transect exposure data
                  fp):
        
        log = self.logger.getChild('load_expo_dx')
        
        dxcol_raw = pd.read_csv(fp, header=[0,1], index_col=0)
        
        #=======================================================================
        # precheck
        #=======================================================================
        mdex = dxcol_raw.columns
        assert 'common' in mdex.levels[0]
        
        #check l2 headers
        miss_l = set([self.wsln, self.celn, self.sdistn, self.fbn]).difference(
            mdex.levels[1])
        assert len(miss_l)==0, 'missing some l2 colns: %s'%miss_l
        
        #=======================================================================
        # extract some sumaries
        #=======================================================================
        """
        view(dxcol_raw)
        """
        self.sid_vals = dxcol_raw.loc[:, ('common', self.sid)].unique().tolist()
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('loaded expo dxcol w/ %s \n%s'%(str(dxcol_raw.shape), mdex))
        
        self.expo_dxcol = dxcol_raw
        return self.expo_dxcol


 
    
    
    

    

            
        