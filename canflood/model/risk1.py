'''
Created on Feb. 27, 2020

@author: cefect

impact lvl 1 model

this should run w/o any qgis bindings.
'''
    
#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging

import pandas as pd
import numpy as np

#from scipy import interpolate, integrate

#==============================================================================
# custom imports
#==============================================================================

#standalone runs
mod_logger = logging.getLogger('risk1') #get the root logger

from hlpr.exceptions import QError as Error
 
from model.riskcom import RiskModel



class Risk1(RiskModel):
    """
    model for summarizing inundation counts (positive depths)
    """
    
    valid_par='risk1'
    
    #expectations from parameter file
    exp_pars_md = {#mandataory: section: {variable: handles} 
        'parameters' :
            {'name':{'type':str}, 'cid':{'type':str},
             
             'event_probs':{'values':('ari', 'aep')}, 
             'felv':{'values':('ground', 'datum')},
             'prec':{'type':int}, 
             'ltail':None, 'rtail':None, 'drop_tails':{'type':bool},
             'as_inun':{'type':bool},
              #'ground_water':{'type':bool}, #NO! risk1 only accepts positive depths
             },
            
        'dmg_fps':{
             'finv':{'ext':('.csv',)}, #should only need the expos
             'expos':{'ext':('.csv',)},
                    },
        'risk_fps':{
             'evals':{'ext':('.csv',)}
                    },
        'validation':{
            'risk1':{'type':bool}
                    }
         }
    
    exp_pars_op = {#optional expectations
       'parameters':{
            'impact_units': {'type':str}
            },
        'dmg_fps':{
            'gels':{'ext':('.csv',)},
                 },
        'risk_fps':{
            'exlikes':{'ext':('.csv',)}
                    },
        
        }
    

    
    #number of groups to epxect per prefix
    group_cnt = 2
    
    #minimum inventory expectations
    finv_exp_d = {
        'scale':{'type':np.number},
        'elv':{'type':np.number}
        }
    """
    NOTE: for as_inun=True, 
    using this flag to skip conversion of exposure to binary
    we dont need any elevations (should all be zero)
    but allowing the uesr to NOT pass an elv column would be very difficult
    """
    

    
    def __init__(self,**kwargs):
        super().__init__(**kwargs) #initilzie Model
        
        self.dtag_d={**self.dtag_d,**{
            'expos':{'index_col':0}
            }}
        

        
        self.logger.debug('finished __init__ on Risk1')
        

        
        
    def prep_model(self, #attach and prepare data for  model run

               ): 
        """
        called by Dialog and standalones
        """

            
            
        self.set_finv()
        self.set_evals() 
        self.set_expos()
        
        if not self.exlikes == '':
            self.set_exlikes()
        
        if self.felv == 'ground':
            self.set_gels()
            self.add_gels()
        

        self.build_exp_finv() #build the expanded finv
        self.build_depths()
        
        
        self.logger.debug('finished setup_data on Risk1')
        
        return 

    def run(self,
            res_per_asset=False, #whether to generate results per asset
            calc_risk=True, #whether to run integration algo
            ):
        """
        main caller for L1 risk model
        
        TODO: clean this up and divide into more functions
            extend impact only support to GUI and tests
        """
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        #ddf_raw, finv,  = self.data_d['expos'],self.data_d['finv'] 
        aep_ser = self.data_d['evals']
        cid, bid = self.cid, self.bid        
        bdf ,ddf = self.bdf, self.ddf
        
        #======================================================================
        # prechecks
        #======================================================================
        assert isinstance(res_per_asset, bool)
        assert cid in ddf.columns, 'ddf missing %s'%cid
        assert bid in ddf.columns, 'ddf missing %s'%bid
        assert ddf.index.name == bid, 'ddf bad index'
        
        #identifier for depth columns
        #dboolcol = ~ddf.columns.isin([cid, bid])
        log.info('running on %i assets and %i events'%(len(bdf), len(ddf.columns)-2))
        self.feedback.upd_prog(20, method='raw')

        #=======================================================================
        # clean exposure
        #=======================================================================
        boolcol = ddf.columns.isin([bid, cid])
        
        ddf1 = ddf.loc[:, ~boolcol]
        
        if calc_risk:
            assert len(ddf1.columns)>3, 'must pass at least 3 exposure columns to calculate ead'
        
        #======================================================================
        # convert exposures to binary
        #======================================================================
        if not self.as_inun: #standard impact/noimpact analysis
            #get relvant bids
            """
            because there are no curves, Risk1 can only use positive depths.
            ground_water flag is ignored
            """
            booldf = pd.DataFrame(np.logical_and(
                ddf1 > 0,#get bids w/ positive depths
                ddf1.notna()) #real depths
                )
    
    
            if booldf.all().all():
                log.warning('got all %i entries as null... no impacts'%(ddf.size))
                raise Error('dome')
                return
            
            log.info('got %i (of %i) exposures'%(booldf.sum().sum(), ddf.size))
            
            bidf = ddf1.where(booldf, other=0.0)
            bidf = bidf.where(~booldf, other=1.0)
        
        #=======================================================================
        # leave as percentages
        #=======================================================================
        else:
            bidf = ddf1.copy()
            assert bidf.max().max() <=1
            
            #fill nulls with zero
            bidf = bidf.fillna(0)
        
        self.feedback.upd_prog(10, method='append')
        #======================================================================
        # scale
        #======================================================================
        if 'fscale' in bdf:
            log.info('scaling impact values by \'fscale\' column')
            bidf = bidf.multiply(bdf.set_index(bid)['fscale'], axis=0).round(self.prec)
            
            
        #======================================================================
        # drop down to worst case
        #======================================================================
        #reattach indexers
        bidf1 = bidf.join(ddf.loc[:, boolcol])
        
        assert not bidf1.isna().any().any()
        
        cdf = bidf1.groupby(cid).max().drop(bid, axis=1)
 
        #======================================================================
        # resolve alternate impacts (per evemt)-----
        #======================================================================
        #take maximum expected value at each asset
        if 'exlikes' in self.data_d:
            bres_df = self.ev_multis(cdf, self.data_d['exlikes'], aep_ser, logger=log)
            
        #no duplicates. .just rename by aep
        else:
            bres_df = cdf.rename(columns = aep_ser.to_dict()).sort_index(axis=1)
            
            assert bres_df.columns.is_unique, 'duplicate aeps require exlikes'
            
        log.info('got damages for %i events and %i assets'%(
            len(bres_df), len(bres_df.columns)))
        
        #======================================================================
        # checks
        #======================================================================
        #check the columns
        assert np.array_equal(bres_df.columns.values, aep_ser.unique()), 'column name problem'
        _ = self.check_monot(bres_df)
        self.feedback.upd_prog(10, method='append')
        
        #======================================================================
        # get ead per asset------
        #======================================================================
        if calc_risk:
            if res_per_asset:
                res_df = self.calc_ead(bres_df)
                            
            else:
                res_df = None
            self.res_df = res_df
            self.feedback.upd_prog(10, method='append')
            #======================================================================
            # totals
            #======================================================================        
            res_ttl = self.calc_ead(bres_df.sum(axis=0).to_frame().T,
                                    drop_tails=False,
                                    ).T #1 column df
            
            self.ead_tot = res_ttl.iloc[:,0]['ead'] #set for plot_riskCurve()
            
            self.res_ttl = self._fmt_resTtl(res_ttl)
            self._set_valstr()
        #=======================================================================
        # impacts only----
        #=======================================================================
        else:
            self.res_df = bres_df.rename(
                columns={e[1]:e[0] for e in self.eventType_df.drop('noFail', axis=1).values})
            
            
            self.res_ttl  = pd.Series()

        
        log.info('finished on %i assets and %i damage cols'%(len(bres_df), len(self.res_ttl)))
        #=======================================================================
        # #format total results for writing
        #=======================================================================
        
            
        
        #=======================================================================
        # wrap
        #=======================================================================
        

        log.info('finished')


        return self.res_ttl, self.res_df
    

    

if __name__ =="__main__": 
      print('???')