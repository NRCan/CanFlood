'''
Created on Feb. 27, 2020

@author: cefect

impact lvl 1 model
'''


#==========================================================================
# logger setup-----------------------
#==========================================================================

    
#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging

import pandas as pd
import numpy as np

from scipy import interpolate, integrate

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
    mod_logger = logging.getLogger('risk1') #get the root logger

    from hlpr.exceptions import QError as Error

from hlpr.Q import *
from hlpr.basic import *
from model.modcom import Model



class Risk1(Model):
    """
    model for summarizing inundation counts (positive depths)
    """
    
    valid_par='risk1'
    
    #expectations from parameter file
    exp_pars_md = {#mandataory: section: {variable: handles} 
        'parameters' :
            {'name':{'type':str}, 'cid':{'type':str},
             'res_per_asset':{'type':bool}, 
             'event_probs':{'values':('ari', 'aep')}, 
             'felv':{'values':('ground', 'datum')},
             'prec':{'type':int}, 
             'drop_tails':{'type':bool},
             },
        'dmg_fps':{
             'finv':{'ext':('.csv',)}, #should only need the expos
             'expos':{'ext':('.csv',)},
                    },
        'risk_fps':{
             'aeps':{'ext':('.csv',)}
                    },
        'validation':{
            'risk1':{'type':bool}
                    }
         }
    
    exp_pars_op = {#optional expectations
        'dmg_fps':{
            'gels':{'ext':('.csv',)},
                 },
        'risk_fps':{
            'exlikes':{'ext':('.csv',)}
                    },
        
        }
    
    #==========================================================================
    # plot controls
    #==========================================================================
    plot_fmt = '{0}'
    y1lab = 'impacts'
    
    def __init__(self,
                 cf_fp,
                 **kwargs
                 ):
        
        #init the baseclass
        super().__init__(cf_fp, **kwargs) #initilzie Model
        
        #======================================================================
        # setup funcs
        #======================================================================
        self.resname = 'risk1_%s_%s'%(self.tag, self.name)
        
        self.load_data()
        
        self.setup_finv()
        
        """really.. should just restric to one function per asset for level1"""
        self.setup_expo_data()
        
        self.logger.debug('finished __init__ on Risk1')
        
    def load_data(self): #load the data files
        log = self.logger.getChild('load_data')
        cid = self.cid
        #======================================================================
        # #load exposure data
        #======================================================================
        ddf = pd.read_csv(self.expos, index_col=None)
        self.data_d['expos'] = ddf.copy()
        
        #check it
        assert cid in ddf.columns, 'expos missing index column \"%s\''%cid
        
        #clean it
        ddf = ddf.set_index(cid, drop=True).sort_index(axis=1).sort_index(axis=0)
        
        #======================================================================
        # load finv
        #======================================================================
        self.data_d['finv'] = pd.read_csv(self.finv, index_col=None)
        
        #======================================================================
        # #load remainders
        #======================================================================
        
        self.load_risk_data(ddf)
        
        
        log.info('finished')
        
    def run(self):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        #ddf_raw, finv,  = self.data_d['expos'],self.data_d['finv'] 
        aep_ser = self.data_d['aeps']
        cid, bid = self.cid, self.bid        
        bdf ,ddf = self.bdf, self.ddf
        
        #======================================================================
        # prechecks
        #======================================================================
        assert cid in ddf.columns, 'ddf missing %s'%cid
        assert bid in ddf.columns, 'ddf missing %s'%bid
        assert ddf.index.name == bid, 'ddf bad index'
        
        #identifier for depth columns
        #dboolcol = ~ddf.columns.isin([cid, bid])
        log.info('running on %i assets and %i events'%(len(bdf), len(ddf.columns)-2))
        
        #======================================================================
        # adjust depths by exposure grade
        #======================================================================
        """
        resserved for future dev
        
        one value per cid?
        """
        
        #======================================================================
        # drop down to worst case
        #======================================================================
        cdf = ddf.groupby(self.cid).max().drop(self.bid, axis=1)
        """what does this do for nulls?"""

        
        #======================================================================
        # convert exposures to binary
        #======================================================================
        #get relvant bids
        booldf = pd.DataFrame(np.logical_and(
            cdf > 0,#get bids w/ positive depths
            cdf.notna()) #real depths
            )


        if booldf.all().all():
            log.warning('got all %i entries as null... no impacts'%(ddf.size))
            raise Error('dome')
            return
        
        log.info('got %i (of %i) exposures'%(booldf.sum().sum(), ddf.size))
        
        bdf = cdf.where(booldf, other=0.0)
        bdf = bdf.where(~booldf, other=1.0)
        

        #======================================================================
        # resolve alternate impacts (per evemt)
        #======================================================================
        #take maximum expected value at each asset
        if 'exlikes' in self.data_d:
            bres_df = self.resolve_multis(bdf, self.data_d['exlikes'], aep_ser, log)
            
        #no duplicates. .just rename by aep
        else:
            bres_df = bdf.rename(columns = aep_ser.to_dict()).sort_index(axis=1)
            


        
        log.info('got damages for %i events and %i assets'%(
            len(bres_df), len(bres_df.columns)))
        
        #======================================================================
        # checks
        #======================================================================
        #check the columns
        assert np.array_equal(bres_df.columns.values, aep_ser.unique()), 'column name problem'
        
        
        _ = self.check_monot(bres_df)
        
        #======================================================================
        # totals
        #======================================================================        
        res_ser = self.calc_ead(bres_df.sum(axis=0).to_frame().T, logger=log).iloc[0]
        self.res_ser = res_ser.copy() #set for risk_plot()
        #======================================================================
        # get ead per asset
        #======================================================================
        if self.res_per_asset:
            res_df = self.calc_ead(bres_df, drop_tails=self.drop_tails, logger=log)
                        
        else:
            res_df = None
            
        

        log.info('finished on %i assets and %i damage cols'%(len(bres_df), len(res_ser)))
        

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
    
    out_dir = os.path.join(os.getcwd(), 'risk1')
    tag = 'test'
    ead_plot = True
    """
    l = [0.0, 0.0, 1.0]
    
    l.remove(0.0)
    """

    #==========================================================================
    # dev data
    #==========================================================================

    
    cf_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk1\basic\CanFlood_risk1.txt'
    
    wrkr = Risk1(cf_fp, out_dir=out_dir, logger=mod_logger, tag=tag)
    
    res, res_df = wrkr.run()
    
    #======================================================================
    # plot
    #======================================================================
    if ead_plot:
        fig = wrkr.risk_plot()
        _ = wrkr.output_fig(fig)
    
    #==========================================================================
    # output
    #==========================================================================
    wrkr.output_df(res, '%s_%s'%(wrkr.resname, 'ttl'))
    
    if not res_df is None:
        _ = wrkr.output_df(res_df, '%s_%s'%(wrkr.resname, 'passet'))
    

    force_open_dir(out_dir)

    print('finished')