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
from pandas import IndexSlice as idx




from hlpr.exceptions import QError as Error
    




#===============================================================================
# non-Qgis
#===============================================================================
from model.modcom import Model
from results.riskPlot import Plotr as riskPlotr
from hlpr.basic import view

#==============================================================================
# functions-------------------
#==============================================================================
class Attr(Model, riskPlotr):
    
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
        
        self.attriMode=True #always for this worker
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
    def _setup(self):
        log = self.logger.getChild('setup')
        
        #load the control file
        self.init_model()
        self._init_plt()
        #upldate your group plot style container
        self.upd_impStyle()
        
        #load and prep the total results
        _ = self.load_ttl(logger=log)
        _ = self.prep_dtl(logger=log)
        
        self.load_passet()
        
        self.load_attrimat(dxcol_lvls=3)
        
        #=======================================================================
        # post fix attrim
        #=======================================================================
        """ROUNDING
        forcing the project precision aon all hte aep values...
            not the greatest.. but only decent way to ensure they are treated as members
        """
        #reformat aep values
        atr_dxcol = self.data_d.pop(self.attrdtag_in)
        
        mdex = atr_dxcol.columns
        atr_dxcol.columns = mdex.set_levels(
            np.around(mdex.levels[0].astype(np.float), decimals=self.prec), 
            level=0)
        
        #store
        self.data_d[self.attrdtag_in] = atr_dxcol
 
        
        #=======================================================================
        # check
        #=======================================================================
        miss_l = set(atr_dxcol.columns.levels[0]).symmetric_difference(
            self.aep_df.loc[~self.aep_df['extrap'], 'aep'])
 
        assert len(miss_l)==0, 'event mismatch'
        
        #=======================================================================
        # get TOTAL multiplied values
        #=======================================================================
        self.mula_dxcol = self.get_mult(self.data_d[self.attrdtag_in].copy(), logger=log)
 
        
        return self
        

        
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
        """
        df_raw.columns
        df.columns
        """
        
        #drop ead and format column
        df = df_raw.drop('ead', axis=1)
        df.columns = np.around(df.columns.astype(np.float), decimals=self.prec)
        
        #drop extraploators and ead
        boolcol = df.columns.isin(self.aep_df.loc[~self.aep_df['extrap'], 'aep'])
        assert boolcol.sum() >2, 'suspicious event match count'
        df = df.loc[:, boolcol].sort_index(axis=1, ascending=True)
        

        
        #=======================================================================
        # check
        #=======================================================================
        """a bit redundant.. because we just selected for these above"""
        miss_l = set(df.columns).symmetric_difference(
            self.aep_df.loc[~self.aep_df['extrap'], 'aep'])
 
        assert len(miss_l)==0, 'event mismatch'
        
        #=======================================================================
        # set it
        #=======================================================================
        self.cindex = df.index.copy() #set this for checks later
        self.data_d[dtag] = df
            
    def get_slice(self,
                  lvals_d, #mdex lvl values {lvlName:(lvlval1, lvlval2...)}
                  atr_dxcol=None,
                  logger=None,
                  sliceName='slice', #
                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is  None: logger=self.logger
        if atr_dxcol is None: atr_dxcol=self.data_d[self.attrdtag_in].copy()
        log=logger.getChild('get_slice')
        
        mdex = atr_dxcol.columns
        """
        view(mdex.to_frame())
        """
        nameRank_d= {lvlName:i for i, lvlName in enumerate(mdex.names)}
        rankName_d= {i:lvlName for i, lvlName in enumerate(mdex.names)}
        #=======================================================================
        # precheck
        #=======================================================================
        #quick check on the names
        miss_l = set(lvals_d.keys()).difference(mdex.names)
        assert len(miss_l)==0, '%i requested lvlNames not on mdex: %s'%(len(miss_l), miss_l)
        
        #chekc values
        for lvlName, lvals in lvals_d.items():
            
            #chekc all these are in there
            miss_l = set(lvals).difference(mdex.levels[nameRank_d[lvlName]])
            assert len(miss_l)==0, '%i requsted lvals on \"%s\' not in mdex: %s'%(len(miss_l), lvlName, miss_l)
            

        #=======================================================================
        # get slice            
        #=======================================================================
        log.info('from %i levels on %s'%(len(lvals_d), str(atr_dxcol.shape)))
        """
        s_dxcol = atr_dxcol.loc[:, idx[:, lvals_d['rEventName'], :]].columns.to_frame())
        """
        
        
        """seems like there should be a better way to do this...
        could force the user to pass request with all levels complete"""
        s_dxcol = atr_dxcol.copy()
        #populate missing elements
        for lvlName, lRank  in nameRank_d.items():
            if not lvlName in lvals_d: continue 
            
            if lRank == 0: continue #always keeping this
            elif lRank == 1:
                s_dxcol = s_dxcol.loc[:, idx[:, lvals_d[lvlName]]]
            elif lRank == 2:
                s_dxcol = s_dxcol.loc[:, idx[:, :, lvals_d[lvlName]]]
            else:
                raise Error
                
 
        log.info('sliced  to %s'%str(s_dxcol.shape))
        
        return s_dxcol

    def get_mult(self, #multiply dxcol by the asset event totals
                atr_dxcol,
                logger=None,
 
                ): 
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('get_ttl')
        rp_df = self.data_d['r2_passet'].copy()
        
        #=======================================================================
        # precheck
        #=======================================================================
        #aep set
        miss_l = set(atr_dxcol.columns.levels[0]).difference(rp_df.columns)
        assert len(miss_l)==0, 'event mismatch'
        
        #attribute matrix logic
        """note we accept slices... so sum=1 wont always hold"""
        assert atr_dxcol.notna().all().all()
        assert (atr_dxcol.max()<=1.0).all().all()
        assert (atr_dxcol.max()>=0.0).all().all()
        for e in atr_dxcol.dtypes.values: assert e==np.dtype(float)
        
        #=======================================================================
        # prep
        #=======================================================================
        """
        view(rp_df)
        """
        #=======================================================================
        # multiply
        #=======================================================================
        return atr_dxcol.multiply(rp_df, level='aeps')
    
    def get_ttl(self, #get a total impacts summary from an impacts dxcol 
                i_dxcol, #impacts (not attribution ratios)
                ):

        df =  i_dxcol.sum(axis=1, level='aeps').sum(axis=0).rename('impacts'
                     ).reset_index(drop=False).rename(columns={'aeps':'aep'})
                     
        #add ari
        df['ari'] = (1/df['aep']).astype(int)
        
        #add plot keys
        df['plot']=True
        
        
        #calc ead
        
        return df
        

    
    def plot_slice(self, #plot slice against original risk c urve
                   sttl_df, #sliced data
                   ttl_df=None, #original (full) data
                   logger=None,
                   
                   #plot keys
                   y1lab='AEP',
                   **plotKwargs
                   ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_slice')
        if ttl_df is None: ttl_df=self.data_d['ttl'].copy()
        
        #=======================================================================
        # precheck
        #=======================================================================

        
        #check aep membership
        miss_l = set(sttl_df['aep']).difference(ttl_df['aep'])
        assert len(miss_l)==0, 'aep miss: %s'%miss_l
        
        """
        self.color
        """
        #=======================================================================
        # plot the group
        #=======================================================================
        plotParsG_d = {
            'slice':{
                    'ttl_df':sttl_df,
                    'ead_tot':0.0,
                    'impStyle_d':dict(),
                    },
            'full':{
                    'ttl_df':ttl_df,
                    'ead_tot':self.ead_tot,
                    'impStyle_d':self.impStyle_d,
                    'hatch_f':True
                    }
            }
        
        return self.plot_mRiskCurves(plotParsG_d,y1lab=y1lab, logger=log, **plotKwargs)
                    
            
        
        
        
        
        
        
        
        
        
        
            