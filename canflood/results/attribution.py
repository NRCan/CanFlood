'''
Created on Feb. 9, 2020

@author: cefect

attribution analysis
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, copy



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

from results.riskPlot import RiskPlotr
from hlpr.basic import view

#==============================================================================
# functions-------------------
#==============================================================================
class Attr(RiskPlotr):
    
    #===========================================================================
    # program vars
    #===========================================================================
    """todo: fix this"""

    sliceName='slice'
    attrdtag_in = 'attrimat03' 
    #===========================================================================
    # expectations from parameter file
    #===========================================================================
    exp_pars_md = {
        'results_fps':{
             'attrimat03':{'ext':('.csv',)},
             'r_ttl':{'ext':('.csv',)},
             'r_passet':{'ext':('.csv',)},
             'eventypes':{'ext':('.csv',)}
             }
        }
    
    exp_pars_op=dict()
 
    


    def __init__(self, *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.attriMode=True #always for this worker
        
        self.dtag_d={'r_ttl':{'index_col':None},
                     'r_passet':{'index_col':0},
                     'eventypes':{'index_col':None},
                     self.attrdtag_in:{'index_col':0, 'header':list(range(0,3))}}
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
    def prep_model(self):
        log = self.logger.getChild('prep_model')
        

        
        self.set_ttl() #load and prep the total results
        
        self.set_passet()
        self.set_etypes()
        
        self.set_attrimat()
        
        #=======================================================================
        # attrim----
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
        
        #sort them
        """this flips the usual atr_dxcol order.. but matches the EAD calc expectation"""
        atr_dxcol = atr_dxcol.sort_index(axis=1, level=0, ascending=False)


        #=======================================================================
        # check
        #=======================================================================
        mdex = atr_dxcol.columns
        #check aep values
        miss_l = set(mdex.levels[0]).symmetric_difference(
            self.aep_df.loc[~self.aep_df['extrap'], 'aep'])
 
        assert len(miss_l)==0, 'aep mismatch: %s'%miss_l
        
        #check rEventNames
        miss_l = set(mdex.levels[1]).symmetric_difference(
            self.data_d['eventypes']['rEventName'])
        assert len(miss_l)==0, 'rEventName mismatch: %s'%miss_l
        
        #store
        self.data_d[self.attrdtag_in] = atr_dxcol
        #=======================================================================
        # get TOTAL multiplied values---
        #=======================================================================
        self.mula_dxcol = self.get_mult(atr_dxcol.copy(), logger=log)
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('finished')
 
        
        return 

    def set_passet(self, #load the per-asset results
                   fp = None,
                   dtag = 'r_passet',

                   logger=None,
                    
                    ):
        """
        TODO: Consider moving to a results common
        """
        #=======================================================================
        # defa8ults
        #=======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('load_passet')
 
        
        #=======================================================================
        # precheck
        #=======================================================================

        #======================================================================
        # load it
        #======================================================================
        df_raw = self.raw_d[dtag]
        """
        df_raw.columns
        df.columns
        """
        
        #=======================================================================
        # clean
        #=======================================================================
        #drop ead and format column
        df = df_raw.drop('ead', axis=1)
        df.columns = np.around(df.columns.astype(np.float), decimals=self.prec)
        
        #drop extraploators and ead
        boolcol = df.columns.isin(self.aep_df.loc[~self.aep_df['extrap'], 'aep'])
        assert boolcol.sum() >2, 'suspicious event match count'
        df = df.loc[:, boolcol].sort_index(axis=1, ascending=False)
        

        
        #=======================================================================
        # check
        #=======================================================================
        """a bit redundant.. because we just selected for these above"""
        miss_l = set(df.columns).symmetric_difference(
            self.aep_df.loc[~self.aep_df['extrap'], 'aep'])
 
        assert len(miss_l)==0, 'event mismatch'
        
        #=======================================================================
        # if not self.check_eDmg(df, dropna=False, logger=log):
        #     raise Error('failed check')
        #=======================================================================
        self.check_eDmg(df, dropna=False, logger=log)
        
        #=======================================================================
        # set it
        #=======================================================================
        self.cindex = df.index.copy() #set this for checks later
        self.data_d[dtag] = df
        
    def set_etypes(self,
                   fp = None,
                   dtag = 'eventypes',

                   logger=None,
                    
                    ):
        """
        TODO: Consider moving to a results common
        """
        #=======================================================================
        # defa8ults
        #=======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('set_etypes')

        #=======================================================================
        # load
        #=======================================================================
        df_raw = self.raw_d[dtag]
        
        #=======================================================================
        # check
        #=======================================================================
        assert np.array_equal(np.array(['rEventName', 'aep', 'noFail']), df_raw.columns)
        
        #=======================================================================
        # clean
        #=======================================================================
        df = df_raw.copy()
        df['aep'] = df_raw['aep'].astype(np.float).round(self.prec)
        
        #=======================================================================
        # post-check
        #=======================================================================
        miss_l = set(self.aep_df.loc[~self.aep_df['extrap'],'aep']).difference(df['aep'])
        assert len(miss_l)==0, 'aep match fail: %s'%miss_l
        
        
        self.data_d[dtag] = df

        
    def get_slice_noFail(self, #slice of noFail and fail
                         
                         atr_dxcol=None,
                         et_df = None,
                         logger=None,
                         ): 
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is  None: logger=self.logger
        if atr_dxcol is None: atr_dxcol=self.data_d[self.attrdtag_in].copy()
        if et_df is  None: et_df=self.data_d['eventypes']
        log=logger.getChild('get_slice_noFail')
        
        #=======================================================================
        # precheck
        #=======================================================================
        
        #=======================================================================
        # build slice of noFails
        #=======================================================================
        #get nofail event names
        renf_ar = et_df.loc[et_df['noFail'], 'rEventName'].values
        
        #get slice of this        
        s1_dxcol = self.get_slice({'rEventName':renf_ar.tolist()}, logger=log,
                                  sliceName='noFail',
                                  slice_impStyle_d={
                                      'color':'red'
                                      }) 
        """
        view(atr_dxcol)
        view(s1_dxcol)
        view(s1i_ttl)

        view(self.data_d['r_passet'])
        """
        #multiply by impacts
        s1i_dxcol = self.get_mult(s1_dxcol, logger=log)
        
        #compress to event totals
        s1i_df =  s1i_dxcol.sum(axis=1, level='aep').sum(axis=0).rename('impacts'
                     ).reset_index(drop=False)
        
        s1i_ttl, ead = self.get_ttl(s1i_df, logger=log) #sum to aeps
        
        return s1i_ttl
            
    def get_slice(self,
                  lvals_d, #mdex lvl values {lvlName:(lvlval1, lvlval2...)}
                  atr_dxcol=None,
                  logger=None,
                  sliceName='slice', #plot identifying?
                  slice_impStyle_d=dict(),
                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is  None: logger=self.logger
        if atr_dxcol is None: atr_dxcol=self.data_d[self.attrdtag_in].copy()
        log=logger.getChild('get_slice')
        
        self.sliceName=sliceName #setting for plot
        self.slice_impStyle_d=slice_impStyle_d
        
        mdex = atr_dxcol.columns
        """
        view(mdex.to_frame())
        """
        nameRank_d= {lvlName:i for i, lvlName in enumerate(mdex.names)}
        #rankName_d= {i:lvlName for i, lvlName in enumerate(mdex.names)}
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
        rp_df = self.data_d['r_passet'].copy()
        
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
        
        view(rp_df.round(0))
        rp_df.sum(axis=0)
        view(mdxcol)
        
        view(atr_dxcol.sum(axis=1, level=0))
        """
        #=======================================================================
        # multiply
        #=======================================================================
        mdxcol = atr_dxcol.multiply(rp_df, level='aep')
        
        #=======================================================================
        # check it
        #=======================================================================
        if not self.check_eDmg(mdxcol.sum(axis=1, level=0), logger=log):
            """allowing this as we still want to give the user the plot
            can happen if a slice/component reduces with aep
            likely something with bad failure data"""
            pass
        
            #raise Error('failed damage monotonciy check')
        
        return mdxcol
    

    def get_stack(self, #get a set of stacked data for a stack plot
                  lvlName='nestID', #level from which to build stacked data from
                    #eventually we could support different unstacking dimensions.. but nestID is the only obviuos one now
                  atr_dxcol=None,
                  logger=None,
                  
                  ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is  None: logger=self.logger
        if atr_dxcol is None: atr_dxcol=self.data_d[self.attrdtag_in].copy()
        log=logger.getChild('get_slice')
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert lvlName in atr_dxcol.columns.names
        
        #=======================================================================
        # get impact values
        #=======================================================================
        i_dxcol = self.get_mult(atr_dxcol, logger=log)

        #=======================================================================
        # get stack
        #=======================================================================
        """
        view(i_dxcol.columns.to_frame())
        view(sdf)
        """
        #compres rows to totals. pivot out new columns. compress all remaining mindex rows to sums
        sdf = i_dxcol.sum(axis=0).unstack(level=lvlName).sum(axis=0, level='aep')
        
        #=======================================================================
        # add in tails
        #=======================================================================
        sdf1 = None
        ead_d = dict()
        for coln, cser in sdf.items():
            tdf, ead_d[coln] = self.get_ttl(cser.to_frame().reset_index().rename(columns={coln:'impacts'}))
            
            assert 'ari' in tdf.columns, coln
            if sdf1 is None:
                sdf1 = tdf.drop('impacts', axis=1)

            sdf1 = sdf1.join(tdf['impacts']).rename(columns={'impacts':coln})

        #=======================================================================
        # reformat as dxind
        #=======================================================================
        dxind = sdf1.set_index('aep', drop=True).drop('ari', axis=1)
        mindex = pd.MultiIndex.from_frame(sdf1.loc[:, ('aep', 'ari')])
        dxind.index = dxind.index.join(mindex)
        
        #drop no plotters
        dxind = dxind.loc[dxind['plot'], :].sort_index(level=1).drop('plot', axis=1)
        
        #=======================================================================
        # add plot text
        #=======================================================================

        self.plotTag = lvlName

        
        return dxind, pd.Series(ead_d)
    
 
    def plot_slice(self, #plot slice against original risk c urve
                   sttl_df, #sliced data
                   ttl_df=None, #original (full) data
                   logger=None,
                   
                   #plot keys
                   y1lab='AEP',
                   slice_impStyle_d=None,
                   slice_ead=None, plotTag=None,
                   **plotKwargs
                   ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_slice')
        
        if plotTag is None: plotTag='%s byFail'%self.tag
        
        if ttl_df is None: ttl_df=self.data_d['r_ttl'].copy()
        
        #slice default attributes
        if slice_impStyle_d is None: slice_impStyle_d=self.slice_impStyle_d
        if slice_ead is None: slice_ead=self.slice_ead
        
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
        """
        nice for FULL to plot first
        """
        plotParsG_d = {
            'full':{
                    'ttl_df':ttl_df,
                    'label':'\'%s\' annualized = '%'Total' + self.impactFmtFunc(self.ead_tot),
                    'impStyle_d':self.impStyle_d,
                    'hatch_f':True
                    },
                        
            self.sliceName:{
                    'ttl_df':sttl_df,
                    'label':'\'%s\' annualized = '%self.sliceName + self.impactFmtFunc(self.slice_ead),
                    'impStyle_d':slice_impStyle_d,
                    },

            }
        
        return self.plot_mRiskCurves(plotParsG_d,y1lab=y1lab, logger=log, plotTag=plotTag,
                                     **plotKwargs)
                    
            
        

 
        
        
        
        
        
        
        
        
            