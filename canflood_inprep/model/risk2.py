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
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
    
#plugin runs
else:
    mod_logger = logging.getLogger('risk2') #get the root logger

    from hlpr.exceptions import QError as Error

from hlpr.Q import *
from hlpr.basic import *
from model.modcom import Model

#==============================================================================
# functions----------------------
#==============================================================================
class Risk2(Model):
    """Risk T2 tool for calculating expected value for a set of events from impact results
    
    METHODS:
        run(): main model executor

    Control File Parameters:
        dmgs -- damage data results file path (default N/A)
            
        exlikes -- secondary exposure likelihood data file path (default N/A)
        
        aeps -- event probability data file path (default N/A)
        
        event_probs -- format of event probabilities (in 'aeps' data file) 
                        (default 'ari')
                        
            'aeps'           event probabilities in aeps file expressed as 
                            annual exceedance probabilities
            'aris'           expressed as annual recurrance intervals
            
        
        ltail -- zero probability event extrapolation handle 
                (default 'extrapolate')
            'flat'           set the zero probability event equal to the most 
                            extreme impacts in the passed series
            'extrapolate'    set the zero probability event by extrapolating from 
                            the most extreme impact
            'none'           do not extrapolate (not recommended)
            float            use the passed value as the zero probability impact value
             
        
        rtail -- zreo impacts event extrapolation handle    (default 0.5)
            'extrapolate'    set the zero impact event by extrapolating from the 
                            least extreme impact
            'none'           do not extrapolate (not recommended) 
            float           use the passed value as the zero impacts aep value
        
        drop_tails -- flag to drop the extrapolated values from the results 
                            (default True)
        
        integrate -- numpy integration method to apply (default 'trapz')
        
        risk2 -- Risk2 validation flag (default False)
        
        res_per_asset -- flag to generate results per asset 
        


    
    
    
    """


    #==========================================================================
    # #program vars
    #==========================================================================
    
    valid_par = 'risk2'

    
    #expectations from parameter file
    exp_pars_md = {#mandataory: section: {variable: handles} 
        'parameters' :
            {'name':{'type':str}, 'cid':{'type':str},

             'felv':{'values':('ground', 'datum')},
             'event_probs':{'values':('aep', 'ari')},
             'ltail':None, 'rtail':None, 'drop_tails':{'type':bool},
             'integrate':{'values':('trapz',)}, 
             'prec':{'type':int}, 
             },
            
        'dmg_fps':{
             'finv':{'ext':('.csv',)},

                    },
        'risk_fps':{
             'dmgs':{'ext':('.csv',)},
             'aeps':{'ext':('.csv',)},

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
    # plot controls
    #==========================================================================
    plot_fmt = '${:,.0f}'
    y1lab = '$dmg'
    

    
    
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
        self.init_model()
        
        self.resname = 'risk2_%s_%s'%(self.tag, self.name)
        
        #self.setup_data()
        self.load_finv()
        self.load_aeps()
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
        ddf, aep_ser, cid = self.data_d['dmgs'],self.data_d['aeps'], self.cid
        
        assert isinstance(res_per_asset, bool)
        
        #======================================================================
        # resolve alternate damages (per evemt)
        #======================================================================
        #take maximum expected value at each asset
        if 'exlikes' in self.data_d:
            ddf1 = self.resolve_multis(ddf, self.data_d['exlikes'], aep_ser, log)
            
        #no duplicates. .just rename by aep
        else:
            ddf1 = ddf.rename(columns = aep_ser.to_dict()).sort_index(axis=1)
            

        #======================================================================
        # checks
        #======================================================================
        #check the columns
        assert np.array_equal(ddf1.columns.values, aep_ser.unique()), 'column name problem'
        _ = self.check_monot(ddf1)
            
        #======================================================================
        # totals
        #======================================================================        
        res_ser = self.calc_ead(ddf1.sum(axis=0).to_frame().T, logger=log).iloc[0]
        self.res_ser = res_ser.copy() #set for risk_plot()
        #======================================================================
        # get ead per asset
        #======================================================================
        if res_per_asset:
            res_df = self.calc_ead(ddf1, drop_tails=self.drop_tails, logger=log)
                        
        else:
            res_df = None
            
        

        log.info('finished on %i assets and %i damage cols'%(len(ddf1), len(res_ser)))
        

        #format resul series
        res = res_ser.to_frame()
        res.index.name = 'aep'
        res.columns = ['$']
        
        #remove tails
        if self.drop_tails:
            res = res.iloc[1:-2,:] #slice of ends 
            res.loc['ead'] = res_ser['ead'] #add ead back
        
         
        log.info('finished')


        return res, res_df

    
    


            
        
if __name__ =="__main__": 
    
    #==========================================================================
    # run controls
    #==========================================================================
    ead_plot = True
    res_per_asset = True
    #==========================================================================
    # dev data
    #=========================================================================
    #==========================================================================
    # tag = 'dev'
    # cf_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk2\wex\CanFlood_dmg2.txt'
    # out_dir = os.path.join(os.getcwd(), 'risk2')
    #==========================================================================
    
    #==========================================================================
    # tutorial 2
    #==========================================================================
    runpars_d={
        'Tut2':{
            'out_dir':os.path.join(os.getcwd(), 'risk2', 'Tut2'),
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200305\CanFlood_Tut2.txt',
            }
        }
    
    
    
    #==========================================================================
    # build/execute
    #==========================================================================
    for tag, pars in runpars_d.items():
        cf_fp, out_dir = pars['cf_fp'], pars['out_dir']
        log = mod_logger.getChild(tag)
        assert os.path.exists(cf_fp)
        
        
        wrkr = Risk2(cf_fp, out_dir=out_dir, logger=mod_logger, tag=tag)._setup()
        
        res_ser, res_df = wrkr.run(res_per_asset=res_per_asset)
        
    
        
        #======================================================================
        # plot
        #======================================================================
        if ead_plot:
            fig = wrkr.risk_plot()
            _ = wrkr.output_fig(fig)
            
        
        #==========================================================================
        # output
        #==========================================================================
        wrkr.output_df(res_ser, '%s_%s'%(wrkr.resname, 'ttl'))
        
        if not res_df is None:
            _ = wrkr.output_df(res_df, '%s_%s'%(wrkr.resname, 'passet'))
    


    force_open_dir(out_dir)

    print('finished')
    
    
    