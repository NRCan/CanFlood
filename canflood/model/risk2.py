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
from model.modcom import Model
from results.riskPlot import Plotr

#==============================================================================
# functions----------------------
#==============================================================================
class Risk2(Model, 
            Plotr, #TODO: consider moviing this onto Model
             
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
             'event_rels':   {'type':str, 'values':('max', 'mutEx', 'indep')}
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
        'risk_fps':{
            'exlikes':{'ext':('.csv',)},
                    },
        
        'results_fps':{
             'attrimat02':{'ext':('.csv',)},
                    }
                }
    
    #==========================================================================
    # plot controls----
    #==========================================================================
    plot_fmt = '{:,.0f}'
    y1lab = 'impacts'
    

    
    
    def __init__(self,
                 cf_fp,
                 **kwargs
                 ):
        
        #init the baseclass
        super().__init__(cf_fp, **kwargs) #initilzie Model
        self._init_plt() #setup matplotlib
        
        self.logger.debug('finished __init__ on Risk')
        
        
    def _setup(self):
        #======================================================================
        # setup funcs
        #======================================================================
        self.init_model() #mostly just attaching and checking parameters from file
        
        self.resname = 'risk2_%s_%s'%(self.tag, self.name)
        
        if self.as_inun:
            raise Error('risk2 inundation percentage not implemented')
        
        #data loaders
        self.load_finv()
        self.load_evals()
        self.load_dmgs()
        if not self.exlikes == '':
            self.load_exlikes()
        if self.attriMode:
            self.load_attrimat(dxcol_lvls=2)
            self.promote_attrim()
        
        """consider makeing riskPloter a child of modcom?"""    
        self.upd_impStyle() 
        
        
        self.logger.debug('finished _setup() on Risk2')
        
        return self
        


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
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        ddf, aep_ser = self.data_d['dmgs'],self.data_d['evals']

        

        self.feedback.setProgress(5)

        #======================================================================
        # resolve alternate damages (per evemt)-----------
        #======================================================================

        #=======================================================================
        # #take maximum expected value at each asset
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
        assert np.array_equal(ddf1.columns.values, aep_ser.unique()), 'column name problem'
        log.info('checking monotonoticy on %s'%str(ddf1.shape))
        _ = self.check_monot(ddf1)
        
        
        self.feedback.setProgress(40)
        #======================================================================
        # get ead per asset-----
        #======================================================================
        if res_per_asset:
            res_df = self.calc_ead(ddf1, drop_tails=self.drop_tails, logger=log)
                        
        else:
            res_df = None
            
        #======================================================================
        # get EAD totals-------
        #======================================================================    
        self.feedback.setProgress(80)    
        res_ttl = self.calc_ead(
            ddf1.sum(axis=0).to_frame().T, #rounding at end of calc_ead()
            drop_tails=False, #handle beslow 
            logger=log,
            ).T #1 column df
            
        #self.res_ser = res_ttl.iloc[:, 0].copy() #set for risk_plot()
        self.ead_tot = res_ttl.iloc[:,0]['ead'] #set for plot_riskCurve()
            
        self.feedback.setProgress(95)

        log.info('finished on %i assets and %i damage cols'%(
            len(ddf1), len(res_ttl)))
        

        #=======================================================================
        # #format total results for writing
        #=======================================================================
        res_ttl.index.name = 'aep'
        res_ttl.columns = ['impacts']
        
        #add labels
        miss_l = set(self.extrap_vals_d.keys()).difference(res_ttl.index)
        assert len(miss_l)==0


        res_ttl = res_ttl.join(
            pd.Series(np.full(len(self.extrap_vals_d), 'extrap'), 
                  index=self.extrap_vals_d, name='note')
            )
        
        res_ttl.loc['ead', 'note'] = 'integration'
        res_ttl.loc[:, 'note'] = res_ttl.loc[:, 'note'].fillna('impact_sum')
        
        #plot lables
        res_ttl['plot'] = True
        res_ttl.loc['ead', 'plot'] = False
        
        res_ttl=res_ttl.reset_index(drop=False)
        
        #=======================================================================
        # wrap----
        #=======================================================================
        #plotting string
        self.val_str = 'annualized impacts = %s \nltail=\'%s\',  rtail=\'%s\''%(
            self.impactFmtFunc(self.ead_tot), self.ltail, self.rtail) + \
            '\nassets = %i, event_rels = \'%s\', prec = %i'%(
                self.asset_cnt, self.event_rels, self.prec)
            
        
        self.res_ttl=res_ttl #for convenioence outputters
        self.res_df = res_df
        log.info('finished')


        return res_ttl, res_df
    
    def output_ttl(self,  #helper to o utput the total results file
                    dtag='r2_ttl',
                   ofn=None,
                   upd_cf= True,
                   logger=None,
                   ):
 
        if ofn is None:
            ofn = '%s_%s'%(self.resname, 'ttl') 
            
        out_fp = self.output_df(self.res_ttl, ofn, write_index=False, logger=logger)
        
        if upd_cf:
            self.update_cf( {
                    'results_fps':(
                        {dtag:out_fp}, 
                        '#\'%s\' file path set from output_ttl at %s'%(
                            dtag, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                        ), }, cf_fp = self.cf_fp )
        
        return out_fp
    
    def output_passet(self,  #helper to o utput the total results file
                      dtag='r2_passet',
                   ofn=None,
                   upd_cf= True,
                   logger=None,
                   ):
        """using these to help with control file writing"""
        if ofn is None:
            ofn = '%s_%s'%(self.resname, dtag)
            
        out_fp = self.output_df(self.res_df, ofn, logger=logger)
        
        if upd_cf:
            self.update_cf( {
                    'results_fps':(
                        {dtag:out_fp}, 
                        '#\'%s\' file path set from output_passet at %s'%(
                            dtag, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                        ), }, cf_fp = self.cf_fp )
        
        return out_fp
        
    

    
    




    
    
    