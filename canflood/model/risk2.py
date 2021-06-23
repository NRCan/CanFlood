'''
Created on Feb. 7, 2020

@author: cefect
'''

    
#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging, datetime

import pandas as pd
import numpy as np



#==============================================================================
# custom imports
#==============================================================================

mod_logger = logging.getLogger('risk2') #get the root logger

from hlpr.exceptions import QError as Error

#from hlpr.Q import *
from hlpr.basic import view
#from model.modcom import Model
#from results.riskPlot import Plotr
from model.riskcom import RiskModel
#==============================================================================
# functions----------------------
#==============================================================================
class Risk2(RiskModel, #This inherits 'Model'
             
            ):
    """Risk T2 tool for calculating expected value for a set of events from impact results
    
    METHODS:
        run(): main model executor

    """


    #==========================================================================
    #program vars----
    #==========================================================================
    
    valid_par = 'risk2'
    rttl_ofp=None
    rpasset_ofp=None
    attrdtag_out = 'attrimat03'
    attrdtag_in = 'attrimat02' #also check exp_pars_op below
    
    #===========================================================================
    # #expectations from parameter file
    #===========================================================================
    #control file expectation handles: MANDATORY
    #{section : {variable {check handle type: check values}
    exp_pars_md = {
        'parameters' :
            {
             'name':        {'type':str},
             'cid':         {'type':str},
             'felv':        {'values':('ground', 'datum')},
             'event_probs': {'values':('aep', 'ari')},
             'ltail':None,
             'rtail':None,
             'drop_tails':  {'type':bool},
             'integrate':   {'values':('trapz',)}, 
             'prec':        {'type':int}, 
             'as_inun':     {'type':bool},
             'event_rels':   {'type':str, 'values':('max', 'mutEx', 'indep')},
             
             },
            
        'dmg_fps':{
             'finv':{'ext':('.csv',)},
                    },
        
        'risk_fps':{
             'dmgs':{'ext':('.csv',)},
             'evals':{'ext':('.csv',)},
                    },
                
        'validation':{
            'risk2':{'type':bool}
                    },
                }
    
    exp_pars_op = {#optional expectations
        'parameters':{
            'impact_units': {'type':str}
            },
        'risk_fps':{
            'exlikes':{'ext':('.csv',)},
                    },
        
        'results_fps':{
             'attrimat02':{'ext':('.csv',)},
                    }
                }
    
    #===========================================================================
    # METHODS-------------
    #===========================================================================
    def __init__(self,**kwargs):
        super().__init__(**kwargs) #initilzie Model
 

        
        self.dtag_d={**self.dtag_d,**{
            'dmgs':{'index_col':0},
            self.attrdtag_in:{'index_col':0, 'header':list(range(0,2))}
            }}
                
                
        self.logger.debug('finished __init__ on Risk2')
        
        
    def prep_model(self,
                   event_slice=False,  #allow the expolike data to pass MORE events than required 
                   ):

        if self.as_inun:
            raise Error('risk2 inundation percentage not implemented')
        
        #data loaders
        self.set_finv()
        self.set_evals() 
        self.set_dmgs()
        
        if not self.exlikes == '':
            self.set_exlikes(event_slice=event_slice)

            
        if self.attriMode:
            """the control file parameter name changes depending on the model"""
            self.set_attrimat()
            self.promote_attrim()
        
        #activate plot styles

        
        self.logger.debug('finished  on Risk2')
        
        return

    def set_dmgs(self,#loading any exposure type data (expos, or exlikes)

                   dtag = 'dmgs',
                   check_monot=False, #whether to check monotonciy
                   logger=None,
                   ):
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('set_dmgs')
 
        cid = self.cid
        
        #=======================================================================
        # prechecks
        #=======================================================================
        
        assert 'finv' in self.data_d, 'call load_finv first'
        assert 'evals' in self.data_d, 'call load_evals first'
        assert isinstance(self.expcols, pd.Index), 'bad expcols'
        assert isinstance(self.cindex, pd.Index), 'bad cindex'
 
        #======================================================================
        # load it
        #======================================================================
        df_raw = self.raw_d[dtag]
        
        #======================================================================
        # precheck
        #======================================================================
        assert df_raw.index.name == cid, 'expected \'%s\' index on %s'%(self.cid, dtag)
 
        assert df_raw.columns.dtype.char == 'O','bad event names on %s'%dtag
        

        
        #======================================================================
        # clean it
        #======================================================================
        df = df_raw.copy()
        
        #drop dmg suffix
        """2021-01-13: dropped the _dmg suffix during dmg2.run()
        left this cleaning for backwards compatailibity"""
        boolcol = df.columns.str.endswith('_dmg')
        enm_l = df.columns[boolcol].str.replace('_dmg', '').tolist()
        
        ren_d = dict(zip(df.columns[boolcol].values, enm_l))
        df = df.rename(columns=ren_d)
        
        #set new index
 
        
        #apply rounding
        df = df.round(self.prec)
        
        #======================================================================
        # postcheck
        #======================================================================
        #assert len(enm_l) > 1, 'failed to identify sufficient damage columns'
        

        #check cid index match
        assert np.array_equal(self.cindex, df.index), \
            'provided \'%s\' index (%i) does not match finv index (%i)'%(dtag, len(df), len(self.cindex))
        
        #check rEvents
        miss_l = set(self.expcols).difference(df.columns)
            
        assert len(miss_l) == 0, '%i events on \'%s\' not found in aep_ser: \n    %s'%(
            len(miss_l), dtag, miss_l)
        
        
        #check dtype of columns
        for ename, chk_dtype in df.dtypes.items():
            assert np.issubdtype(chk_dtype, np.number), 'bad dtype %s.%s'%(dtag, ename)
            
        
        #======================================================================
        # postcheck2
        #======================================================================
        if check_monot:
            self.check_monot(df, aep_ser = self.data_d['evals'])


        #======================================================================
        # set it
        #======================================================================
        
        self.data_d[dtag] = df
        
        log.info('finished building %s as %s'%(dtag, str(df.shape)))


    def promote_attrim(self, dtag=None): #add new index level
        if dtag is None: dtag = self.attrdtag_in
        """
        risk1 doesnt use dmg1... so the attrim will be differnet
        """
        
        aep_ser = self.data_d['evals'].copy()
        atr_dxcol = self.data_d[dtag].copy()
        """
        view(atr_dxcol)
        """
        
        #get the new mindex we want to join in
        mindex2 = pd.MultiIndex.from_frame(
            aep_ser.to_frame().reset_index().rename(columns={'index':'rEventName'}))
        #join this in and move it up some levels
        atr_dxcol.columns = atr_dxcol.columns.join(mindex2)[0].swaplevel(i=2, j=1).swaplevel(i=1, j=0)
        #check the values all match
        """nulls are not matching for somereaseon"""
        booldf = atr_dxcol.droplevel(level=0, axis=1).fillna(999) == self.data_d[dtag].fillna(999)
        assert booldf.all().all(), 'bad conversion'
        del self.data_d[dtag]
        self.att_df = atr_dxcol.sort_index(axis=1, level=0, sort_remaining=True, 
                                           inplace=False, ascending=True)
        
        assert self.attriMode
        
        return 

    def run(self, #main runner fucntion
            res_per_asset=False, 
            #event_rels=None, NO! needs to be consistent with loading
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        ddf, aep_ser = self.data_d['dmgs'],self.data_d['evals']

        

        self.feedback.setProgress(20)

        #======================================================================
        # resolve alternate damages (per evemt)-----------
        #======================================================================

        #=======================================================================
        # conditional exposure
        #=======================================================================
        if 'exlikes' in self.data_d:
            ddf1 = self.ev_multis(ddf, self.data_d['exlikes'], aep_ser, logger=log)
            
        #=======================================================================
        # #no duplicates. .just rename by aep
        #=======================================================================
        else:            
            ddf1 = ddf.rename(columns = aep_ser.to_dict()).sort_index(axis=1)

        #======================================================================
        # cleans and checks
        #======================================================================
        ddf1 = ddf1.round(self.prec)
        
        #check the columns
        assert np.array_equal(ddf1.columns.values, aep_ser.unique()), \
            'expect unique evals to match resolved damages'
        log.debug('checking monotonoticy on %s'%str(ddf1.shape))
        _ = self.check_monot(ddf1)
        
        
        self.feedback.upd_prog(10, method='append')
        #======================================================================
        # get ead per asset-----
        #======================================================================
        if res_per_asset:
            res_df = self.calc_ead(ddf1)
                        
        else:
            res_df = None
            
        #======================================================================
        # get EAD totals-------
        #======================================================================    
        self.feedback.upd_prog(10, method='append')   
        res_ttl = self.calc_ead(
            ddf1.sum(axis=0).to_frame().T, #rounding at end of calc_ead()
            drop_tails=False, #handle beslow 
            ).T #1 column df
            
        #self.res_ser = res_ttl.iloc[:, 0].copy() #set for risk_plot()
        self.ead_tot = res_ttl.iloc[:,0]['ead'] #set for plot_riskCurve()
            
        self.feedback.upd_prog(10, method='append')

        log.info('finished on %i assets and %i damage cols'%(
            len(ddf1), len(res_ttl)))
        

        #=======================================================================
        # #format total results for writing
        #=======================================================================
        res_ttl = self._fmt_resTtl(res_ttl)
        
        #=======================================================================
        # wrap----
        #=======================================================================
        self._set_valstr()
            
        
        self.res_ttl=res_ttl #for convenioence outputters
        self.res_df = res_df
        log.info('finished')
        self.feedback.upd_prog(10, method='append')

        return res_ttl, res_df

    

        
    

    
    




    
    
    