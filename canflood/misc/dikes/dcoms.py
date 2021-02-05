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
    cbfn = 'crest_buff' #crest buffer field name
    nullSamp = -999 #value for bad samples
    
    lfxn = 'lenfx_SF'
    pfn = 'p_fail'

    
    #program containers
    expo_dxcol = None #exposure data

    def __init__(self,                  
             dikeID = 'dikeID', #dike identifier field
             segID = 'segID', #segment identifier field
                  *args,  **kwargs):
        
        super().__init__(*args,**kwargs)
        
        #=======================================================================
        # attach
        #=======================================================================
        self.dikeID, self.segID = dikeID, segID #done during init
        
        self.logger.debug('Dcoms.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def load_expo(self, #load the dike segment exposure data
                  fp,
                  prop_colns = None,
                  logger=None):
        """
        TODO: make this more general (for dRes)
        """
        
        if logger is None: logger=self.logger
        
        log = logger.getChild('load_expo')
        
        df = pd.read_csv(fp, header=0, index_col=0)
        
        #=======================================================================
        # precheck
        #=======================================================================
        if prop_colns is None:
            prop_colns = [self.dikeID, self.segID, self.segln, self.cbfn]
        miss_l = set(prop_colns).difference(df.columns)
        assert len(miss_l)==0, 'missing some expected colns: %s'%miss_l
        
        #=======================================================================
        # tags
        #=======================================================================
        tag_l = [c for c in df.columns if c.endswith('_dtag')]
        assert len(tag_l)>0, 'failed to find any tag columns'
        
        #=======================================================================
        # events
        #=======================================================================
        l1 = set(prop_colns).union(tag_l) #those we dont want
        etag_l = list(set(df.columns).difference(l1))
        assert len(etag_l)>0, 'failed to get any eTags'
        etag_l.sort()
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('loaded expos_df w/ %i dtags and %i etags'%(len(tag_l), len(etag_l)))
        
        #collapse all dtags
        l1 = [col.unique().tolist() for coln, col in df.loc[:, tag_l].items()]
        self.dtag_l = set([item for sublist in l1 for item in sublist])
        
        self.etag_l = etag_l
        self.expo_df = df.round(self.prec)
        
        return self.expo_df
        
        
        
        
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


 
    
    
    

    

            
        