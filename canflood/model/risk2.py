'''
Created on Feb. 7, 2020

@author: cefect
'''

    
#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging

import pandas as pd
import numpy as np



#==============================================================================
# custom imports
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    root_logger = basic_logger()  
    mod_logger = root_logger.getChild('risk2')
    from hlpr.exceptions import Error
    
#plugin runs
else:
    mod_logger = logging.getLogger('risk2') #get the root logger

    from hlpr.exceptions import QError as Error

#from hlpr.Q import *
from hlpr.basic import force_open_dir
from model.modcom import Model

#==============================================================================
# functions----------------------
#==============================================================================
class Risk2(Model):
    """Risk T2 tool for calculating expected value for a set of events from impact results
    
    METHODS:
        run(): main model executor

    """


    #==========================================================================
    #program vars----
    #==========================================================================
    
    valid_par = 'risk2'

    
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
                    }
                    }
    
    exp_pars_op = {#optional expectations
        'risk_fps':{
            'exlikes':{'ext':('.csv',)},
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
        
        self.logger.debug('finished __init__ on Risk')
        
        
    def _setup(self):
        #======================================================================
        # setup funcs
        #======================================================================
        self.init_model() #mostly just attaching and checking parameters from file
        
        self.resname = 'risk2_%s_%s'%(self.tag, self.name)
        
        if self.as_inun:
            raise Error('risk2 inundation percentage not implemented')
        
        #self.setup_data()
        self.load_finv()
        self.load_evals()
        self.load_dmgs()
        
        if not self.exlikes == '':
            self.load_exlikes()
        
        
        
        self.logger.debug('finished _setup() on Risk2')
        
        return self
        

    def run(self, #main runner fucntion
            res_per_asset=False,
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        ddf, aep_ser, cid = self.data_d['dmgs'],self.data_d['evals'], self.cid
        
        assert isinstance(res_per_asset, bool)
        self.feedback.setProgress(5)
        #======================================================================
        # resolve alternate damages (per evemt)
        #======================================================================
        #take maximum expected value at each asset
        if 'exlikes' in self.data_d:
            ddf1 = self.ev_multis(ddf, self.data_d['exlikes'], aep_ser, log)
            
        #no duplicates. .just rename by aep
        else:
            ddf1 = ddf.rename(columns = aep_ser.to_dict()).sort_index(axis=1)
            
        ddf1 = ddf1.round(self.prec)
        #======================================================================
        # checks
        #======================================================================
        #check the columns
        assert np.array_equal(ddf1.columns.values, aep_ser.unique()), 'column name problem'
        log.info('checking monotonoticy on %s'%str(ddf1.shape))
        _ = self.check_monot(ddf1)
        
        self.feedback.setProgress(40)
        #======================================================================
        # get ead per asset
        #======================================================================
        if res_per_asset:
            res_df = self.calc_ead(ddf1, drop_tails=self.drop_tails, logger=log)
                        
        else:
            res_df = None
            
        #======================================================================
        # totals
        #======================================================================    
        self.feedback.setProgress(80)    
        res_ttl = self.calc_ead(
            ddf1.sum(axis=0).to_frame().T, #rounding at end of calc_ead()
            drop_tails=False, #handle beslow 
            logger=log,
            ).T #1 column df
            
        self.res_ser = res_ttl.iloc[:, 0].copy() #set for risk_plot()

            
        self.feedback.setProgress(95)

        log.info('finished on %i assets and %i damage cols'%(
            len(ddf1), len(res_ttl)))
        

        #format total results for writing
        res_ttl.index.name = 'aep'
        res_ttl.columns = ['impacts']
        
        #add labels
        miss_l = set(self.extrap_vals_d.keys()).difference(res_ttl.index)
        assert len(miss_l)==0


        res_ttl = res_ttl.join(
            pd.Series(np.full(len(self.extrap_vals_d), 'extraploated'), 
                  index=self.extrap_vals_d, name='note')
            )
        res_ttl.loc['ead', 'note'] = 'integration'
        res_ttl.loc[:, 'note'] = res_ttl.loc[:, 'note'].fillna('impact_sum')
        
        #plot lables
        res_ttl['plot'] = True
        res_ttl.loc['ead', 'plot'] = False
         
        log.info('finished')


        return res_ttl, res_df




    
    
    