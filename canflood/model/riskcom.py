'''
Created on Mar. 9, 2021

@author: cefect
'''

import os, inspect, logging, copy, itertools, datetime
import pandas as pd
idx = pd.IndexSlice
import numpy as np
from scipy import interpolate, integrate

from hlpr.exceptions import QError as Error
from hlpr.plot import Plotr, view
from model.modcom import Model


class RiskModel(Plotr, Model): #common methods for risk1 and risk2
    
    exp_ttl_colns = ('note', 'plot', 'aep')
    ead_tot=''
    

    
    def __init__(self,**kwargs):
        self.dtag_d={**self.dtag_d, 
                     **{
                        'exlikes':{'index_col':0},
                      }}
        
        super().__init__(**kwargs) 
        
    #===========================================================================
    # LOADERS------------
    #===========================================================================

            
    def set_exlikes(self,#loading exposure probability data (e.g. failure raster poly samples)
                     dtag = 'exlikes',
                   **kwargs
                   ):
        """
        load, fill nulls, add 1.0 for missing, set in data_d
        called by:
            risk1
            risk2
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('set_exlikes')
        assert 'evals' in self.data_d, 'evals data set required with conditional exposure exlikes'
        aep_ser = self.data_d['evals'].astype(float)

        #======================================================================
        # load the data-------
        #======================================================================
        edf = self._get_expos(dtag, log, **kwargs)

        #======================================================================
        # fill nulls-----
        #======================================================================
        """
        better not to pass any nulls.. but if so.. should treat them as ZERO!!
            Null = no failure polygon = no failure
            
        also best not to apply precision to these values
        
        2020-01-12: moved null filling to lisamp.py
            keeping it here as well for backwards compatability
        """
        booldf = edf.isna()
        if booldf.any().any():
            log.warning('got %i (of %i) nulls!... filling with zeros'%(booldf.sum().sum(), booldf.size))
        edf = edf.fillna(0.0)
        
        #=======================================================================
        # if self.event_rels=='indep':
        #     raise Error('2021-06-23: I dont think the sum to 1 assumption is valid for independent events')
        #=======================================================================
        #==================================================================
        # check/add event probability totals----
        #==================================================================
        
        #=======================================================================
        # assemble complex aeps
        #=======================================================================
        #collect event names
        cplx_evn_d, cnt = self._get_cplx_evn(aep_ser)

        assert cnt>0, 'passed \'exlikes\' but there are no complex events'


        def get_cplx_df(df, aep=None, exp_l=None): #retrieve complex data helper
            if exp_l is None:
                exp_l = cplx_evn_d[aep]
            return df.loc[:, df.columns.isin(exp_l)]
            
        #=======================================================================
        # check we dont already exceed 1
        #=======================================================================
        valid = True
        for aep, exp_l in cplx_evn_d.items():
            cplx_df = get_cplx_df(edf, exp_l=exp_l) #get data for this event
            boolidx = cplx_df.sum(axis=1).round(self.prec)>1.0 #find those exceeding 1.0

            if boolidx.any():
                valid = False
                rpt_df = cplx_df[boolidx].join(
                    cplx_df[boolidx].sum(axis=1).rename('sum'))
                
                with pd.option_context('display.max_rows', 500,'display.max_columns', None,'display.width',1000):
                    log.debug('aep%.4f: \n\n%s'%(aep, rpt_df))
                    
                log.error('aep%.4f w/ %i exEvents failed %i (of %i) Psum<1 checks (Pmax=%.2f).. see logger \n    %s'%(
                    aep, len(exp_l), boolidx.sum(), len(boolidx),cplx_df.sum(axis=1).max(), exp_l))
         
        """seems like event_rels=indep should allow for the simple summation to exceed 1"""       
        assert valid, 'some complex event probabilities exceed 1 w/ \'%s\'... see logger'%self.event_rels
            
        #=======================================================================
        # #identify those events that need filling
        #=======================================================================
        fill_exn_d = dict()
        for aep, exn_l in cplx_evn_d.items(): 

            miss_l = set(exn_l).difference(edf.columns)
            if not len(miss_l)<2:
                """
                check if you forgot to specify a hazard layer during exlikes sampling
                """
                raise Error('can only fill one exposure column per complex event\n     %s'%miss_l)
            
            if len(miss_l)==1:
                fill_exn_d[aep] = list(miss_l)[0]
            elif len(miss_l)==0:
                pass #not filling any events
            else: raise Error('only allowed 1 empty')

                
        log.debug('calculating probaility for %i complex events with remaining secnodaries'%(
            len(fill_exn_d)))
            
        self.noFailExn_d =copy.copy(fill_exn_d) #set this for the probability calcs
        

        #=======================================================================
        # fill in missing 
        #=======================================================================
        res_d = dict()
        for aep, exn_miss in fill_exn_d.items():
            """typically this is a single column generated for the failure raster
                but this should work for multiple failure rasters"""
            #===================================================================
            # legacy method
            #===================================================================
            if self.event_rels == 'max':
                edf[exn_miss]=1
                
            #===================================================================
            # rational (sum to 1)
            #===================================================================
            else:

                #data provided on this event
                cplx_df = get_cplx_df(edf, aep=aep)
                assert len(cplx_df.columns)==(len(cplx_evn_d[aep])-1), 'bad column count'
                assert (cplx_df.sum(axis=1)<=1).all() #check we don't already exceed 1 (redundant)
                
                #set remainder values
                edf[exn_miss] = 1- cplx_df.sum(axis=1)
                
                log.debug('for aep %.4f \'%s\' set %i remainder values (mean=%.4f)'%(
                    aep, exn_miss, len(cplx_df), edf[exn_miss].mean()))
                
            res_d[exn_miss] = round(edf[exn_miss].mean(), self.prec)
            
        if len(res_d)>0: log.info(
            'set %i complex event conditional probabilities using remainders \n    %s'%(
                len(res_d), res_d))
 

        """NO! probabilities must sum to 1
        missing column = no secondary likelihoods at all for this event.
        all probabilities = 1
        
        #identify those missing in the edf (compared with the expos)
        miss_l = set(self.expcols).difference(edf.columns)
        
        #add 1.0 for any missing
        if len(miss_l) > 0:
            
            log.info('\'exlikes\' missing %i events... setting to 1.0\n    %s'%(
                len(miss_l), miss_l))
            
            for coln in miss_l:
                edf[coln] = 1.0"""
            
        log.debug('prepared edf w/ %s'%str(edf.shape))
        

        #=======================================================================
        # #check conditional probabilities sum to 1----
        #=======================================================================

        valid = True
        for aep, exp_l in cplx_evn_d.items():
            cplx_df = get_cplx_df(edf, exp_l=exp_l) #get data for this event
            boolidx = cplx_df.sum(axis=1)!=1.0 #find those exceeding 1.0

            if boolidx.any():
                """allowing this to pass when event_rels=max"""
                valid = False
                log.warning('aep%.4f failed %i (of %i) Psum<=1 checks (Pmax=%.2f)'%(
                    aep, boolidx.sum(), len(boolidx), cplx_df.sum(axis=1).max()))
        
        if not self.event_rels == 'max':
            assert valid, 'some complex event probabilities exceed 1'
            

        #==================================================================
        # wrap
        #==================================================================

        # update event type  frame
        """this is a late add.. would have been nice to use this more in multi_ev
        see load_evals()
        """
        
        self.eventType_df['noFail'] = self.eventType_df['rEventName'].isin(fill_exn_d.values())
        
        
        self.data_d[dtag] = edf
        self.cplx_evn_d = cplx_evn_d
        
        return
    
    def _get_cplx_evn(self, aep_ser): #get complex event sets from aep_ser
        cplx_evn_d = dict()
        cnt=0
        for aep in aep_ser.unique(): #those aeps w/ duplicates:
            cplx_evn_d[aep] = aep_ser[aep_ser==aep].index.tolist()
            cnt=max(cnt, len(cplx_evn_d[aep])) #get the size of the larget complex event
            
        return cplx_evn_d, cnt

    def set_ttl(self, # prep the raw results for plotting
                tlRaw_df = None,
                 dtag='r_ttl',
                 logger=None,
                 ):
        """
        when ttl is output, we add the EAD data, drop ARI, and add plotting handles
            which is not great for data manipulation
        here we clean it up and only take those for plotting
        
        see also Artr.get_ttl()
            Model._fmt_resTtl()
            riskPlot.load_ttl()
        """
        
 
        if logger is None: logger=self.logger
        log = logger.getChild('set_ttl')
        if tlRaw_df is None: tlRaw_df = self.raw_d[dtag]
        #=======================================================================
        # precheck
        #=======================================================================
        
        assert isinstance(tlRaw_df, pd.DataFrame)
 
        
        #check the column expectations
        miss_l = set(self.exp_ttl_colns).difference(tlRaw_df.columns)
        assert len(miss_l)==0, 'missing some columns: %s'%miss_l

        assert 'ead' in tlRaw_df.iloc[:,0].values, 'dmg_ser missing ead entry'
        
        #=======================================================================
        # column labling
        #=======================================================================
        """letting the user pass whatever label for the impacts
            then reverting"""
        df1 = tlRaw_df.copy()
        
        """
        TODO: harmonize this with 'impact_units' loaded from control file
        """
        self.impact_name = list(df1.columns)[1] #get the label for the impacts
        
        newColNames = list(df1.columns)
        newColNames[1] = 'impacts'
        
        df1.columns = newColNames

        #=======================================================================
        # #get ead
        #=======================================================================
        bx = df1['aep'] == 'ead' #locate the ead row
        assert bx.sum()==1

        self.ead_tot = df1.loc[bx, 'impacts'].values[0]
        
        assert not pd.isna(self.ead_tot)
        assert isinstance(self.ead_tot, float), '%s got bad type on ead_tot: %s'%(self.name, type(self.ead_tot))
        
        #=======================================================================
        # #get plot values
        #=======================================================================
        df2 = df1.loc[df1['plot'], :].copy() #drop those not flagged for plotting
        
        #typeset aeps
        df2.loc[:, 'aep'] = df2['aep'].astype(np.float64)
        
        """
        view(df2)
        df2['aep'].astype(np.float64).values
        """

        #=======================================================================
        # #invert aep (w/ zero handling)
        #=======================================================================
        self._get_ttl_ari(df2)

        #=======================================================================
        # re-order
        #=======================================================================
        log.debug('finished w/ %s'%str(df2.shape))
        
        ttl_df = df2.loc[:, sorted(df2.columns)].sort_values('ari', ascending=True)
        
        
        #shortcut for datachecks
        df1 = ttl_df.loc[:, ('aep', 'note')]
        df1['extrap']= df1['note']=='extrap'

        self.aep_df = df1.drop('note', axis=1)  #for checking
        self.data_d[dtag] = ttl_df.copy()
        
        return ttl_df
    


    #===========================================================================
    # CALCULATORS-------
    #===========================================================================
    def ev_multis(self, #calculate (discrete) expected value from events w/ multiple exposure sets
           ddf, #damages per exposure set 
           edf, #secondary liklihoods per exposure set ('exlikes'). see set_exlikes()
                # nulls were replaced by 0.0 (e.g., asset not provided a secondary probability)
                # missing colums were replaced by 1.0 (e.g., non-failure events)
            
           aep_ser,
           event_rels=None, #ev calculation method
            #WARNING: not necessarily the same as the parameter used by LikeSampler
                #max:  maximum expected value of impacts per asset from the duplicated events
                    #resolved damage = max(damage w/o fail, damage w/ fail * fail prob)
                    #default til 2020-12-30
                #mutEx: assume each event is mutually exclusive (only one can happen)
                    #lower bound
                #indep: assume each event is independent (failure of one does not influence the other)
                    #upper bound
           logger=None,
                       ):
        """
        
        we accept multiple exposure sets for a single event  
            e.g. 'failure' raster and 'no fail'
            
            where each exposure set is assigned a conditional probability in 'exlikes' (edf)
                e.g. exlikes=1.0  means only one exposure set
        
        
        for resolving conditional probabilities for a single exposure set:
            see build.lisamp.LikeSampler.run()
            (no impacts)
        
        view(edf)
        """
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('ev_multis')
        cplx_evn_d = self.cplx_evn_d #{aep: [eventName1, eventName2,...]}
        
        """needs to be consistent with what was done during set_exlikes()"""
        if event_rels is None: event_rels = self.event_rels

        #======================================================================
        # precheck
        #======================================================================
        assert isinstance(cplx_evn_d, dict)
        assert len(cplx_evn_d)>0
        assert (edf.max(axis=1)<=1).all(), 'got probs exceeding 1'
        assert (edf.min(axis=1)>=0).all(), 'got negative probs'
        
        assert ddf.shape == edf.shape, 'shape mismatch'
        """where edf > 0 ddf should also be > 0
        but leave this check for the input validator"""
        #======================================================================
        # get expected values of all damages
        #======================================================================
        """ skip this based on event_rels?"""
        evdf = ddf*edf
        
        log.info('resolving EV w/ %s, %i event sets, and event_rels=\'%s\''%(
            str(evdf.shape), len(cplx_evn_d), event_rels))
        assert not evdf.isna().any().any()
        assert evdf.min(axis=1).min()>=0
        #======================================================================
        # loop by unique aep and resolve-----
        #======================================================================
        res_df = pd.DataFrame(index=evdf.index, columns = aep_ser.unique().tolist())
        meta_d = dict()

        #for indxr, aep in enumerate(aep_ser.unique().tolist()):
        for indxr, (aep, exn_l) in enumerate(cplx_evn_d.items()):
            self.exn_max = max(self.exn_max, len(exn_l)) #use don plot
            #===================================================================
            # setup
            #===================================================================
            self.feedback.setProgress((indxr/len(aep_ser.unique())*80))
            assert isinstance(aep, float)
            
            if not event_rels=='max':
                if not (edf.loc[:, exn_l].sum(axis=1).round(self.prec) == 1.0).all():
 
                    raise Error('aep %.4f probabilities fail to sum'%aep)
            
            log.debug('resolving aep %.4f w/ %i event names: %s'%(aep, len(exn_l), exn_l))
            
            """
            view(self.att_df)
            """
            #===================================================================
            # simple events.. nothing to resolve----
            #===================================================================
            if len(exn_l) == 1:
                """
                where hazard layer doesn't have a corresponding failure layer
                """
                res_df.loc[:, aep] =  evdf.loc[:, exn_l].iloc[:, 0]
                meta_d[aep] = 'simple noFail'
                
                """no attribution modification required"""
                
            #===================================================================
            # one failure possibility-----
            #===================================================================
            elif len(exn_l) == 2:
                
                if event_rels == 'max':
                    """special legacy method... see below"""
                    res_df.loc[:, aep] = evdf.loc[:, exn_l].max(axis=1)

                else:
                    """where we only have one failure event
                        events are mutually exclusive by default"""
                    res_df.loc[:, aep] = evdf.loc[:, exn_l].sum(axis=1)
                meta_d[aep] = '1 fail'
            #===================================================================
            # complex events (more than 2 failure event)----
            #===================================================================
            else:

                """
                view(edf.loc[:, exn_l])
                view(ddf.loc[:, exn_l])
                view(evdf.loc[:, exn_l])
                """
                
                log.info('resolving alternate damages for aep %.2e from %i events: \n    %s'%(
                    aep, len(exn_l), exn_l))
                
                #===============================================================
                # max
                #===============================================================
                if event_rels == 'max':
                    """
                    matching 2020 function
                    taking the max EV on each asset
                        where those rasters w/o exlikes P=1 (see load_exlikes())
                        
                    WARNING: this violates probability logic
                    
                    """
                    
                    res_df.loc[:, aep] = evdf.loc[:, exn_l].max(axis=1)
                    
                #===============================================================
                # mutex
                #===============================================================
                elif event_rels == 'mutEx':
                    res_df.loc[:, aep] = evdf.loc[:, exn_l].sum(axis=1)

                #===============================================================
                # independent
                #===============================================================
                elif event_rels == 'indep':
                    """
                    NOTE: this is a very slow routine
                    TODO: parallel processing
                    """
                    
                    #identify those worth calculating
                    bx = np.logical_and(
                        (edf.loc[:, exn_l]>0).sum(axis=1)>1, #with multiple real probabilities
                        ddf.loc[:,exn_l].sum(axis=1).round(self.prec)>0  #with some damages
                        )
                    
                    #build the event type flags
                    etype_df = pd.Series(index=exn_l, dtype=np.bool, name='mutEx').to_frame()

                    #mark the failure event
                    etype_df.loc[etype_df.index.isin(self.noFailExn_d.values()), 'mutEx']=True
                    assert etype_df.iloc[:,0].sum()==1

                    """todo: consider using 'apply'
                    tricky w/ multiple data frames...."""
                    log.info('aep %.4f calculating %i (of %i) EVs from %i events w/ indepedence'%(
                        aep, bx.sum(), len(bx), len(exn_l)))
                    
                    #loop and resolve each asset
                    for cindx, pser in edf.loc[bx, exn_l].iterrows():
                   
                        #assemble the prob/consq set for this asset
                        inde_df = pser.rename('prob').to_frame().join(
                            ddf.loc[cindx, exn_l].rename('consq').to_frame()
                            ).join(etype_df)
                            
                        #resolve for this asset
                        res_df.loc[cindx, aep] = self._get_indeEV(inde_df)
                        
                    #fill in remainderes
                    assert res_df.loc[~bx, aep].isna().all()
                    res_df.loc[~bx, aep] = evdf.loc[~bx, exn_l].max(axis=1)
                        
                        
                        
                else: raise Error('bad event_rels: %s'%event_rels)
                #===============================================================
                # wrap complex
                #===============================================================
                meta_d[aep] = 'complex fail'
                

            #===================================================================
            # wrap this aep
            #===================================================================
            if res_df[aep].isna().any():
                raise Error('got nulls on %s'%aep)
                
        #=======================================================================
        # # check
        #=======================================================================
        assert res_df.min(axis=1).min()>=0
        if not res_df.notna().all().all():
            raise Error('got %i nulls'%res_df.isna().sum().sum())
        #=======================================================================
        # attribution------
        #=======================================================================
        if self.attriMode:
            atr_dxcol_raw = self.att_df.copy()
            mdex = atr_dxcol_raw.columns
            nameRank_d= {lvlName:i for i, lvlName in enumerate(mdex.names)}
            edf = edf.sort_index(axis=1, ascending=False)

            if event_rels == 'max':
                """                
                turns out we need to get the ACTUAL expected value matrix
                    here we reconstruct by gettin a max=0, no=1, shared=0.5 matrix
                    then mutiplyling that by the evdf to get the ACTUAL ev matrix"""
                
                #===============================================================
                # build multipler (boolean based on max)
                #===============================================================
                mbdxcol=None
                for aep, gdf in atr_dxcol_raw.groupby(level=0, axis=1):
                    #get events on this aep
                    exn_l = gdf.columns.remove_unused_levels().levels[nameRank_d['rEventName']]
                    
                    #identify maximums
                    booldf = evdf.loc[:, exn_l].isin(evdf.loc[:, exn_l].max(axis=1)).astype(int)
                    
                    #handle duplicates (assign equal portion)
                    if len(exn_l)>1:
                        boolidx =  booldf.eq(booldf.iloc[:,0], axis=0).all(axis=1)
                        booldf.loc[boolidx, :] = float(1/len(exn_l))

                    #add in the dummy lvl0 aep
                    bdxcol = pd.concat([booldf], keys=[aep], axis=1)

                    if mbdxcol is None:
                        mbdxcol = bdxcol
                    else:
                        mbdxcol = mbdxcol.merge(bdxcol, how='outer', left_index=True, right_index=True)
                        
                    log.debug('%.4f: got %s'%(aep, str(mbdxcol.shape)))
                    
                #check it
                self.check_attrimat(atr_dxcol=mbdxcol, logger=log)


                #===============================================================
                # apply multiplication
                #===============================================================
                #get EV from this
                evdf1 = mbdxcol.multiply(evdf, axis='column', level=1).droplevel(level=0, axis=1)
                

                    
            elif event_rels=='mutEx':
 
                evdf1=evdf

            elif event_rels=='indep':
                raise Error('attribution not implemented for event_rels=\'indep\'')
            else: raise Error('bad evnet-Rels')
            
            #===================================================================
            # common
            #===================================================================
            #multiply thorugh to get all the expected value components 
            i_dxcol = atr_dxcol_raw.multiply(evdf1, axis='columns', level=1)
                
            #divide by the event totals to get ratios back
            atr_dxcol = i_dxcol.divide(res_df, axis='columns', level='aep')
            
            #apportion null values
            atr_dxcol = self._attriM_nulls(res_df, atr_dxcol, logger=log)
            
            self.att_df = atr_dxcol
        #======================================================================
        # wrap
        #======================================================================
        #find those w/ zero fail
        bx = res_df.max(axis=1)==0

        log.info('resolved %i asset (%i w/ pfail=0) to %i unique event damages to \n    %s'%(
            len(bx), bx.sum(), len(res_df.columns), res_df.mean(axis=0).to_dict()))
        
        return res_df.sort_index(axis=1)
    
    def calc_ead(self, #get EAD from a set of impacts per event
                 df_raw, #xid: aep
                 ltail = None,
                 rtail = None,
                 drop_tails = None, #whether to remove the dummy tail values from results
                 dx = None, #damage step for integration (default:None)
                 logger = None
                 ):      
        
        """
        #======================================================================
        # inputs
        #======================================================================
        ltail: left tail treatment code (low prob high damage)
            flat: extend the max damage to the zero probability event
            extrapolate: extend the fucntion to the zero aep value (interp1d)
            float: extend the function to this damage value (must be greater than max)
            none: don't extend the tail (not recommended)
            
        rtail: right trail treatment (high prob low damage)
            extrapolate: extend the function to the zero damage value
            float: extend the function to this aep
            none: don't extend (not recommended)

        
        """
        #======================================================================
        # setups and defaults
        #======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('calc_ead')
        if ltail is None: ltail = self.ltail
        if rtail is None: rtail = self.rtail
        if drop_tails is None: drop_tails=self.drop_tails
        assert isinstance(drop_tails, bool)
        
        #format tail values
        assert not ltail is None
        assert not rtail is None
        
        if not ltail in ['flat', 'extrapolate', 'none']:
            try:
                ltail  = float(ltail)
            except Exception as e:
                raise Error('failed to convert \'ltail\'=\'%s\' to numeric \n    %s'%(ltail, e))
            
        if rtail == 'flat':
            raise Error('rtail=flat. not implemented')
        
        if not rtail in ['extrapolate', 'none']:
            rtail = float(rtail)
            
        log.info('getting ead on %s w/ ltail=\'%s\' and rtail=\'%s\''%(
            str(df_raw.shape), ltail, rtail))
        

        #=======================================================================
        # data prep-----
        #=======================================================================
        """
        view(df_raw)
        """
        df = df_raw.copy().sort_index(axis=1, ascending=False)
        
        #=======================================================================
        # no value----
        #=======================================================================
        """
        this can happen for small inventories w/ no failure probs
        """
        #identify columns to calc ead for
        bx = (df > 0).any(axis=1) #only want those with some real damages
        
        if not bx.any():
            log.warning('%s got no positive damages %s'%(self.tag, str(df.shape)))
            
            #apply dummy tails as 'flat'
            if not ltail is None:
                df.loc[:,0] = df.iloc[:,0] 
            if not rtail is None:
                aep_val = max(df.columns.tolist())*(1+10**-(self.prec+2))
                df[aep_val] = 0
                
            #re-arrange columns so x is ascending
            df = df.sort_index(ascending=False, axis=1)
            
            #apply dummy ead
            df['ead'] = 0
            
        #=======================================================================
        # some values---------
        #=======================================================================
        else:
            #=======================================================================
            # get tail values-----
            #=======================================================================
            self.check_eDmg(df, dropna=True, logger=log)
    
            #======================================================================
            # left tail
            #======================================================================
            
            #flat projection
            if ltail == 'flat':
                """
                view(df)
                """
                df.loc[:,0] = df.iloc[:,-1] 
                
                if len(df)==1: 
                    self.extrap_vals_d[0] = df.loc[:,0].mean().round(self.prec) #store for later
                
            elif ltail == 'extrapolate': #DEFAULT
                df.loc[bx,0] = df.loc[bx, :].apply(self._extrap_rCurve, axis=1, left=True)
                
                #extrap vqalue will be different for each entry
                if len(df)==1: 
                    self.extrap_vals_d[0] = df.loc[:,0].mean().round(self.prec) #store for later
    
            elif isinstance(ltail, float):
                """this cant be a good idea...."""
                df.loc[bx,0] = ltail
                
                self.extrap_vals_d[0] = ltail #store for later
                
            elif ltail == 'none':
                pass
            else:
                raise Error('unexected ltail key'%ltail)
            
            
            #======================================================================
            # right tail
            #======================================================================
            if rtail == 'extrapolate':
                """just using the average for now...
                could extraploate for each asset but need an alternate method"""
                aep_ser = df.loc[bx, :].apply(
                    self._extrap_rCurve, axis=1, left=False)
                
                aep_val = round(aep_ser.mean(), 5)
                
                assert aep_val > df.columns.max()
                
                df.loc[bx, aep_val] = 0
                
                log.info('using right intersection of aep= %.2e from average extraploation'%(
                    aep_val))
                
                
                self.extrap_vals_d[aep_val] = 0 #store for later 
                
            
            elif isinstance(rtail, float): #DEFAULT
                aep_val = round(rtail, 5)
                assert aep_val > df.columns.max(), 'passed rtail value (%.2f) not > max aep (%.2f)'%(
                    aep_val, df.columns.max())
                
                df.loc[bx, aep_val] = 0
                
                log.debug('setting ZeroDamage event from user passed \'rtail\' aep=%.7f'%(
                    aep_val))
                
                self.extrap_vals_d[aep_val] = 0 #store for later 
    
            elif rtail == 'flat':
                #set the zero damage year as the lowest year in the model (with a small buffer) 
                aep_val = max(df.columns.tolist())*(1+10**-(self.prec+2))
                df.loc[bx, aep_val] = 0
                
                log.info('rtail=\'flat\' setting ZeroDamage event as aep=%.7f'%aep_val)
                
            elif rtail == 'none':
                log.warning('no rtail extrapolation specified! leads to invalid integration bounds!')
            
            else:
                raise Error('unexpected rtail %s'%rtail)
                
            #re-arrange columns so x is ascending
            df = df.sort_index(ascending=False, axis=1)
            #======================================================================
            # check  again
            #======================================================================
            self.check_eDmg(df, dropna=True, logger=log)
    
            #======================================================================
            # calc EAD-----------
            #======================================================================
            #get reasonable dx (integration step along damage axis)
            """todo: allow the user to set t his"""
            if dx is None:
                dx = df.max().max()/100
            assert isinstance(dx, float)
            
    
            
            #apply the ead func
            df.loc[bx, 'ead'] = df.loc[bx, :].apply(
                self._get_ev, axis=1, dx=dx)
        
        
        df.loc[:, 'ead'] = df['ead'].fillna(0) #fill remander w/ zeros
        
        #======================================================================
        # check it
        #======================================================================
        boolidx = df['ead'] < 0
        if boolidx.any():
            log.warning('got %i (of %i) negative eads'%( boolidx.sum(), len(boolidx)))
        
        """
        df.columns.dtype
        """
        #======================================================================
        # clean results
        #======================================================================
        if drop_tails:
            #just add the results values onto the raw
            res_df = df_raw.sort_index(axis=1, ascending=False).join(df['ead']).round(self.prec)
        else:
            #take everything
            res_df = df.round(self.prec)
            
        #final check
        """nasty conversion because we use aep as a column name..."""
        cdf = res_df.drop('ead', axis=1)
        cdf.columns = cdf.columns.astype(float)
            
        self.check_eDmg(cdf, dropna=True, logger=log)
            
        return res_df

    def _get_indeEV(self,
                    inde_df #prob, consq, mutual exclusivity flag for each exposure event 
                    ):
        
        """
        get the expected value at an asset with 
            n>1 indepednet failure events (w/ probabilities)
            and 1 noFail event
        """
        
        #=======================================================================
        # prechecks  
        #=======================================================================
        #check the columns
        miss_l = set(['prob', 'consq', 'mutEx']).symmetric_difference(inde_df.columns)
        assert len(miss_l)==0
        
        #=======================================================================
        # failures---------
        #=======================================================================
        bxf = ~inde_df['mutEx']
        #=======================================================================
        # assemble complete scenario matrix
        #=======================================================================
        n = len(inde_df[bxf])
        
        #build it
        if not n in self.scen_ar_d:
            scenFail_ar = np.array([i for i in itertools.product(['yes','no'], repeat=n)])
            self.scen_ar_d[n] = copy.copy(scenFail_ar)
        
        #retrieve pre-built
        else:
            scenFail_ar = copy.copy(self.scen_ar_d[n])

        
        #=======================================================================
        #  probs
        #=======================================================================
        sFailP_df = pd.DataFrame(scenFail_ar, columns=inde_df[bxf].index)
        
        #expand probabilities to mathc size
        prob_ar  = np.tile(inde_df.loc[bxf, 'prob'].to_frame().T.values, (len(sFailP_df), 1))
        
        #swap in positives
        sFailP_df = sFailP_df.where(
            np.invert(sFailP_df=='yes'), 
            prob_ar, inplace=False)
        
        #swap in negatives
        sFailP_df = sFailP_df.where(
            np.invert(sFailP_df=='no'), 
            1-prob_ar, inplace=False).astype(np.float64)
        
        #combine
        sFailP_df['pTotal'] = sFailP_df.prod(axis=1)
        assert round(sFailP_df['pTotal'].sum(), self.prec)==1, inde_df
        
        #=======================================================================
        # consequences
        #=======================================================================
        sFailC_df = pd.DataFrame(scenFail_ar, columns=inde_df[bxf].index).replace(
            {'yes':1.0, 'no':0.0}).astype(np.float64)
        
        #add in consequences
        sFailC_df = sFailC_df.multiply(inde_df.loc[bxf, 'consq'])
        
        #get maximums
        sFailC_df['cTotal'] = sFailC_df.max(axis=1)
        
        #=======================================================================
        # expected values
        #=======================================================================
        evFail_ser = sFailP_df['pTotal']*sFailC_df['cTotal']
        
        #=======================================================================
        # total-------
        #=======================================================================
        noFail_ar = inde_df.loc[~bxf, ['prob', 'consq']].iloc[0, :].values
        
        return evFail_ser.sum() + noFail_ar[0]*noFail_ar[1]




    def _extrap_rCurve(self,  #extraploating EAD curve data
               ser, #row of dmages (y values) from big df
               left=True, #whether to extraploate left or right
               ):
        
        """
        
        #=======================================================================
        # plot helper
        #=======================================================================
        from matplotlib import pyplot as plt

        plt.close()
        
        fig = plt.figure()
        ax = fig.add_subplot()
        
        ax.plot(ser.index.values,  ser.values, 
            linestyle='None', marker="o")
            
        ax.plot(0, f(0), marker='x', color='red')

        ax.grid()
        plt.show()
        

        """
        
        #build interpolation function from data
        if left:
            """
            typically this just extends the line from the previous 2 extreme impacts
            shouldnt effect results much when modeled extremes are 'extreme'
            
            theres probably a better function to use since we're only using the 'extrapolate' bit
            """
            f = interpolate.interp1d(
                ser.index.values, #xvals: aep
                ser.values, #yvals: impacts 
                 fill_value='extrapolate', #all we're using
                 )
            
        else:
            #xvalues = damages
            f = interpolate.interp1d(ser.values, ser.index.values,
                                     fill_value='extrapolate')
            
        
        #calculate new y value by applying interpolation function
        result = float(f(0)) #y value at x=0
        
        if not result >=0:
            raise Error('got negative extrapolation on \'%s\': %.2f'%(ser.name, result))
        
        return result 
    

    def _get_ev(self, #integration caller
               ser, #row from damage results
               dx = 0.1,
               ):
        """
        should integrate along the damage axis (0 - infinity)
        """
        
        
        #print('%i.%s    %s'%(self.cnt, ser.name, ser.to_dict()))
        
        x = ser.tolist() #impacts
        y = ser.index.values.round(self.prec+2).tolist() #AEPs
        
        """
        from matplotlib import pyplot as plt
        #build plot
        lines = plt.plot(x, y)
        #lines = plt.semilogx(x, y)
        
        #format
        ax = plt.gca()
        ax.grid()
        ax.set_xlim(1, max(x)) #aep limits
        ax.set_ylabel('AEP')
        ax.set_xlabel('impacts')
        
        
        plt.show()
        
        self.rtail
        """
        
        #======================================================================
        # ser_inv = ser.sort_index(ascending=False)
        # 
        # x = ser_inv.tolist()
        # y = ser_inv.index.tolist()
        # 
        #======================================================================
        if self.integrate == 'trapz':
        
            ead_tot = integrate.trapz(
                y, #yaxis - aeps
                x=x, #xaxis = damages 
                dx = dx)
            
        elif self.integrate == 'simps':
            self.logger.warning('integration method not tested')
            
            ead_tot = integrate.simps(
                y, #yaxis - aeps
                x=x, #xaxis = damages 
                dx = dx)
            
        else:
            raise Error('integration method \'%s\' not recognized'%self.integrate)
            

        return round(ead_tot, self.prec)
    
    def get_ttl(self, #get a total impacts summary from an impacts dxcol 
                df, # index: {aep, impacts}
                logger=None,
                cols_include = ['ari', 'plot']
                ):
        """
        see also Plotr.prep_ttl()
        """
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(df, pd.DataFrame)
        miss_l = set(['aep', 'impacts']).symmetric_difference(df.columns)
        assert len(miss_l)==0, 'bad column labels: %s'%df.columns.tolist()
        cols_include = cols_include.copy()
                     
        
        #=======================================================================
        # get ead and tail values
        #=======================================================================
        """should apply the same ltail/rtail parameters from the cf"""
        
        if df['impacts'].sum()==0:
            ead = 0.0
            df1 = df.copy()
            
        elif df['impacts'].sum()>0:
            dfc = df.loc[:, ('aep', 'impacts')].set_index('aep').T
            ttl_ser = self.calc_ead(dfc,
                drop_tails=False, logger=logger, )
            
            ead = ttl_ser['ead'][0] 
            df1 = ttl_ser.drop('ead', axis=1).T.reset_index()
            
 
        else:
            raise Error('negative impacts!')
            
        assert isinstance(ead, float)
        assert df1['impacts'].min()>=0
        #=======================================================================
        # add ari 
        #=======================================================================
        if 'ari' in cols_include:
            self._get_ttl_ari(df1) #add ari column
            cols_include.remove('ari')
        
        #=======================================================================
        # add plot columns from ttl
        #=======================================================================
        ttl_df=self.data_d['r_ttl'].copy()
        df1 = df1.merge(ttl_df.loc[:, ['aep']+cols_include], on='aep', how='inner')
        
        #=======================================================================
        # wrap
        #=======================================================================
        
        self.slice_ead = ead #set for plotter
        
        return df1, ead
    
    
    #===========================================================================
    # OUTPUTTERS------
    #===========================================================================
    def output_ttl(self,  #helper to o utput the total results file
                   df= None,
                    dtag='r_ttl',
                   ofn=None,
                   upd_cf= None,
                   logger=None,
                   ):
 
        #=======================================================================
        # defaults
        #=======================================================================
        if upd_cf is None: upd_cf = self.upd_cf
        if ofn is None: ofn = '%s_%s'%(self.resname, 'ttl') 
        if df is None: df = self.res_ttl
            
        out_fp = self.output_df(df, ofn, write_index=False, logger=logger)
        
        if upd_cf:
            self.set_cf_pars( {
                    'results_fps':(
                        {dtag:out_fp}, 
                        '#\'%s\' file path set from output_ttl at %s'%(
                            dtag, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                        ), }, cf_fp = self.cf_fp )
        
        return out_fp
    
    def output_passet(self,  #helper to o utput the total results file
                      dtag='r_passet',
                   ofn=None,
                   upd_cf= None,
                   logger=None,
                   ):
        """using these to help with control file writing"""
        if ofn is None:
            ofn = '%s_%s'%(self.resname, dtag)
        if upd_cf is None: upd_cf = self.upd_cf
            
        out_fp = self.output_df(self.res_df, ofn, logger=logger)
        
        if upd_cf:
            self.set_cf_pars( {
                    'results_fps':(
                        {dtag:out_fp}, 
                        '#\'%s\' file path set from output_passet at %s'%(
                            dtag, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                        ), }, cf_fp = self.cf_fp )
        
        return out_fp
    
    def output_etype(self, #save event t ypes
                     df = None,
                     dtag='eventypes',
                     ofn=None,
                     upd_cf=None,
                     logger=None):
        
        
        
        #=======================================================================
        # defaults
        #=======================================================================
        if upd_cf is None: upd_cf = self.upd_cf
        if df is None: df = self.eventType_df
        if ofn is None:
            ofn = '%s_%s_%s'%(dtag, self.tag, self.name)

            
        out_fp = self.output_df(df, ofn, logger=logger, write_index=False)
        
        #update the control file
        if upd_cf:
            self.set_cf_pars(
                    {
                    'results_fps':(
                        {dtag:out_fp}, 
                        '#\'%s\' file path set from output_etype at %s'%(
                            dtag, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                        ),
                     },
                    cf_fp = self.cf_fp
                )
        return out_fp
    #===========================================================================
    # PLOTTING----------
    #===========================================================================

    def plot_riskCurve(self, #risk plot
                  res_ttl=None, #dataframe(columns=['aep','ari','impacts']
                  y1lab='AEP', #yaxis label and plot type c ontrol
                    #'impacts': impacts vs. ARI (use self.impact_name)
                    #'AEP': AEP vs. impacts 
                    
                    impactFmtFunc=None, #tick label format function for impact values
                    #lambda x:'{:,.0f}'.format(x) #thousands comma
                    
                    val_str=None, #text to write on plot. see _get_val_str()
                    figsize=None, logger=None,  plotTag=None,                
                  ):
        
        """
        summary risk results plotter
        
        This is similar to what's  on modcom.risk_plot()
        
        self.impactfmt_str
        """
        
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_riskCurve')
        plt, matplotlib = self.plt, self.matplotlib
        if figsize is None: figsize    =    self.figsize

        if y1lab =='impacts':
            y1lab = self.impact_name
            
        if impactFmtFunc is None: impactFmtFunc=self.impactFmtFunc
            
        if res_ttl is None: res_ttl = self.data_d['r_ttl']
        if plotTag is None: plotTag=self.tag
        #=======================================================================
        # prechecks
        #=======================================================================
        assert isinstance(res_ttl, pd.DataFrame)
        miss_l = set(['aep', 'ari', 'impacts']).difference(res_ttl.columns)
        assert len(miss_l)==0, miss_l
        


        #======================================================================
        # labels
        #======================================================================
        val_str = self._get_val_str(val_str, impactFmtFunc)
        
        
        if y1lab == 'AEP':
            title = '%s %s AEP-Impacts plot for %i events'%(self.name, plotTag, len(res_ttl))
            xlab=self.impact_name
        elif y1lab == self.impact_name:
            title = '%s %s Impacts-ARI plot for %i events'%(self.name, plotTag, len(res_ttl))
            xlab='ARI'
        else:
            raise Error('bad y1lab: %s'%y1lab)
            
 
        #=======================================================================
        # figure setup
        #=======================================================================
        """
        plt.show()
        """
        plt.close()
        fig = plt.figure(figsize=figsize, constrained_layout = True)
        
        #axis setup
        ax1 = fig.add_subplot(111)
        #ax2 = ax1.twinx()
        
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_ylabel(y1lab)


        ax1.set_xlabel(xlab)
        
        #=======================================================================
        # add the line
        #=======================================================================
        self._lineToAx(res_ttl, y1lab, ax1, lineLabel=self.name)
        
        #set limits
        if y1lab == 'AEP':
            ax1.set_xlim(0, max(res_ttl['impacts'])) #aep limits 
            ax1.set_ylim(0, max(res_ttl['aep'])*1.1)
            xLocScale, yLocScale = 0.3,0.6
            
        elif y1lab == self.impact_name:
            ax1.set_xlim(max(res_ttl['ari']), 1) #aep limits 
            xLocScale, yLocScale = 0.2,0.1
        else:
            log.warning('unrecognized y1lab: %s'%y1lab)
            xLocScale, yLocScale = 0.1,0.1
        #=======================================================================
        # post format
        #=======================================================================
        self._postFmt(ax1, val_str=val_str, xLocScale=xLocScale, yLocScale=yLocScale)
        
        #assign tick formatter functions
        if y1lab == 'AEP':
            xfmtFunc = impactFmtFunc
            yfmtFunc=lambda x:'%.4f'%x
        elif y1lab==self.impact_name:
            xfmtFunc = lambda x:'{:,.0f}'.format(x) #thousands separatro
            yfmtFunc=impactFmtFunc
            
        self._tickSet(ax1, xfmtFunc=xfmtFunc, yfmtFunc=yfmtFunc)
        
        return fig
    
    def _lineToAx(self, #add a line to the axis
              res_ttl,
              y1lab,
              ax,
              lineLabel=None,
              impStyle_d=None,
              hatch_f=True,
              h_color=None, h_alpha=None, hatch=None,
              ): #add a line to an axis
        
        #=======================================================================
        # defaults
        #=======================================================================
        plt, matplotlib = self.plt, self.matplotlib
        if impStyle_d is None: impStyle_d = self.impStyle_d
        
        if h_color is None: h_color=self.h_color
        if h_alpha is None: h_alpha=self.h_alpha
        if hatch is None: hatch=self.hatch
        if lineLabel is  None: lineLabel=self.tag

        """
        plt.show()
        """
        #======================================================================
        # fill the plot
        #======================================================================
        if y1lab == self.impact_name:
            xar,  yar = res_ttl['ari'].values, res_ttl['impacts'].values
            pline1 = ax.semilogx(xar,yar,
                                label       = lineLabel,
                                **impStyle_d
                                )
            #add a hatch
            if hatch_f:
                polys = ax.fill_between(xar, yar, y2=0, 
                                        color       = h_color, 
                                        alpha       = h_alpha,
                                        hatch       = hatch)
        
        elif y1lab == 'AEP':
            xar,  yar = res_ttl['impacts'].values, res_ttl['aep'].values
            pline1 = ax.plot(xar,yar,
                            label       = lineLabel,
                            **impStyle_d
                            )
                    
            if hatch_f:
                polys = ax.fill_betweenx(yar.astype(np.float), x1=xar, x2=0, 
                                    color       = h_color, 
                                    alpha       = h_alpha,
                                    hatch       = hatch)
        else:
            raise Error('bad yl1ab: %s'%y1lab)
            
        
        return ax
            
    def _set_valstr(self): 
        """"
        only the risk models should 
        """
        
        #plotting string
        self.val_str =  'annualized impacts = %s %s \nltail=\'%s\' \nrtail=\'%s\''%(
            self.impactFmtFunc(self.ead_tot), self.impact_units, self.ltail, self.rtail) + \
            '\nassets = %i\nevent_rels = \'%s\'\nprec = %i \nmax_fails=%i \ndate=%s'%(
                self.asset_cnt, self.event_rels, self.prec, self.exn_max, self.today_str)
    
    