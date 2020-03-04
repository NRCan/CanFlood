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
    
    #==========================================================================
    # parameters from user
    #==========================================================================

    #==========================================================================
    # ground_water = False
    # felv = 'datum'
    # event_probs = 'aep'
    # ltail = 'extrapolate'
    # rtail = 'extrapolate'
    # drop_tails = False
    # integrate = 'trapz'
    # ead_plot = False
    # res_per_asset = False
    # valid_par = 'risk2'
    #==========================================================================
    
    

    #==========================================================================
    # #program vars
    #==========================================================================
    
    valid_par = 'risk2'

    
    #expectations from parameter file
    exp_pars_md = {#mandataory: section: {variable: handles} 
        'parameters' :
            {'name':{'type':str}, 'cid':{'type':str},
             'res_per_asset':{'type':bool}, 
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
    
    #bid = 'bid' #indexer for expanded finv
    #datafp_section = 'risk_fps'

    #minimum expectations for parameter file
    #==========================================================================
    # exp_pars = {'parameters':list(),
    #               'risk_fps':['dmgs','aeps'], #exlikes is optional
    #               }
    # 
    # opt_dfiles = ['exlikes']
    # 
    # #expected data properties
    # exp_dprops = {'dmgs':{'ext':'.csv', 'colns':[]},
    #                'exlikes':{'ext':'.csv', 'colns':[]},
    #                 'aeps':{'ext':'.csv', 'colns':[]},
    #                 }
    #==========================================================================
    

    #dirname = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    
    def __init__(self,
                 cf_fp,
                 **kwargs
                 ):
        
        #init the baseclass
        super().__init__(cf_fp, **kwargs) #initilzie Model
        
        #======================================================================
        # setup funcs
        #======================================================================
        self.resname = 'risk2_%s_%s'%(self.tag, self.name)
        
        self.setup_data()
        
        self.logger.debug('finished __init__ on Risk')
        
        
    def setup_data(self):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('setup_data')
        cid = self.cid
        
        #======================================================================
        # setup damages
        #======================================================================
        #get event names from damages
        ddf = pd.read_csv(self.dmgs)
        
        #trim suffix
        boolcol = ddf.columns.str.endswith('_dmg')
        enm_l = ddf.columns[boolcol].str.replace('_dmg', '').tolist()
        
        #rename these
        ren_d = dict(zip(ddf.columns[boolcol].values, enm_l))
        ddf = ddf.rename(columns=ren_d)
        
        #some checks
        assert len(enm_l) > 1, 'failed to identify sufficient damage columns'
        assert cid in ddf.columns, 'missing %s in damages'%cid
        assert ddf[cid].is_unique, 'expected unique %s'%cid
        assert ddf.notna().any().any(), 'got some nulls on dmgs'
        
        #set indexes
        ddf = ddf.set_index(cid, drop=True).sort_index(axis=1).sort_index(axis=0)
        
        
        ddf = ddf.round(self.prec)
        
        log.info('prepared ddf w/ %s'%str(ddf.shape))
        
        #set it
        self.data_d['dmgs'] = ddf
        
        self.load_risk_data(ddf)
        
        log.info('finished')
        

    def run(self, #main runner fucntion
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        ddf, aep_ser, cid = self.data_d['dmgs'],self.data_d['aeps'], self.cid
        
        
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
        if self.res_per_asset:
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
    
    out_dir = os.path.join(os.getcwd(), 'risk2')
    
    #==========================================================================
    # dev data
    #=========================================================================
    cf_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk2\CanFlood_dmg2.txt'
    ead_plot = True
    
    #==========================================================================
    # build/execute
    #==========================================================================
    wrkr = Risk2(cf_fp, out_dir=out_dir, logger=mod_logger)
    
    res_ser, res_df = wrkr.run()
    

    
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
    
    
    