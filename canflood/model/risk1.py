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

#from hlpr.Q import *
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
             'evals':{'ext':('.csv',)}
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
    
    group_cnt = 2
    

    
    #==========================================================================
    # plot controls
    #==========================================================================
    plot_fmt = '{0:.0f}' #floats w/ 2 decimal
    y1lab = 'impacts'
    
    def __init__(self,
                 cf_fp,
                 **kwargs
                 ):
        
        #init the baseclass
        super().__init__(cf_fp, **kwargs) #initilzie Model
        
        
        self.logger.debug('finished __init__ on Risk1')
        
        
    def setup(self): 
        """
        called by Dialog and standalones
        """
        
        self.init_model()
        
        self.resname = 'risk1_%s_%s'%(self.tag, self.name)
        #self.load_data()
        #======================================================================
        # load data files
        #======================================================================
        self.load_finv()
        self.load_evals()
        self.load_expos(dtag='expos')
        
        if not self.exlikes == '':
            self.load_exlikes()
        
        if self.felv == 'ground':
            self.load_gels()
            self.add_gels()
        
        #self.setup_finv()
        

        #self.setup_expo()
        self.build_exp_finv() #build the expanded finv
        self.build_depths()
        
        
        
        self.logger.debug('finished setup_data on Risk1')
        
        return self

    def run(self,
            res_per_asset=False):
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
        
        self.feedback.setProgress(5)
        
        #======================================================================
        # check monotocity
        #======================================================================

        #======================================================================
        # adjust depths by exposure grade
        #======================================================================
        """
        resserved for future dev
        
        one value per cid?
        """
        #======================================================================
        # convert exposures to binary
        #======================================================================
        boolcol = ddf.columns.isin([bid, cid])
        
        ddf1 = ddf.loc[:, ~boolcol]
        
        #get relvant bids
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
        
        self.feedback.setProgress(10)
        #======================================================================
        # scale
        #======================================================================
        if 'fscale' in bdf:
            log.info('scaling binaries values by \'fscale\' column')
            bidf = bidf.multiply(bdf.set_index(bid)['fscale'], axis=0)
            
            
        #======================================================================
        # drop down to worst case
        #======================================================================
        #reattach indexers
        bidf1 = bidf.join(ddf.loc[:, boolcol])
        
        
        cdf = bidf1.groupby(cid).max().drop(bid, axis=1)
        """what does this do for nulls?"""
        

        #======================================================================
        # resolve alternate impacts (per evemt)
        #======================================================================
        #take maximum expected value at each asset
        if 'exlikes' in self.data_d:
            bres_df = self.resolve_multis(cdf, self.data_d['exlikes'], aep_ser, log)
            
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
        
        #======================================================================
        # totals
        #======================================================================        
        res_ser = self.calc_ead(bres_df.sum(axis=0).to_frame().T, logger=log).iloc[0]
        self.res_ser = res_ser.copy() #set for risk_plot()
        #======================================================================
        # get ead per asset
        #======================================================================
        if res_per_asset:
            res_df = self.calc_ead(bres_df, drop_tails=self.drop_tails, logger=log)
                        
        else:
            res_df = None
            
        

        log.info('finished on %i assets and %i damage cols'%(len(bres_df), len(res_ser)))
        

        #format resul series
        res = res_ser.to_frame()
        res.index.name = 'aep'
        res.columns = ['impacts']
        
        #remove tails
        if self.drop_tails:
            res = res.iloc[1:-2,:] #slice of ends 
            res.loc['ead'] = res_ser['ead'] #add ead back
        
         
        log.info('finished')


        return res, res_df
    

if __name__ =="__main__": 
    

    ead_plot = True
    #==========================================================================
    # dev data
    #==========================================================================
    #==========================================================================
    # runpars_d = {
    #     'Dev':{
    #         'out_dir': os.path.join(os.getcwd(), 'risk1'),
    #         'cf_fp':r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk1\wex\CanFlood_risk1.txt',
    #         }
    #     }
    #==========================================================================
    
    #==========================================================================
    # tutorials
    #==========================================================================
    runpars_d={
        'Tut1a':{
            'out_dir':os.path.join(os.getcwd(), 'Tut1a'),
            'cf_fp':r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1a\built_1a\CanFlood_tut1a.txt',
            },
        'Tut1b':{
            'out_dir':os.path.join(os.getcwd(), 'Tut1b'),
            'cf_fp':r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1a\built_1b\CanFlood_tut1b.txt',
            }
        }
    #==========================================================================
    # 20200304
    #==========================================================================
    #==========================================================================
    # runpars_d = {
    #     'TDDnrp':{
    #         'out_dir':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDDnrp\risk1',
    #         'cf_fp': r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDDnrp\CanFlood_TDDnrp.txt',
    #          },
    #     'TDDres':{
    #         'out_dir':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDD_res\risk1',
    #         'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDD_res\CanFlood_TDDres.txt',            
    #         },
    #     'ICIrec':{
    #         'out_dir':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\risk1',
    #         'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\CanFlood_ICIrec.txt',
    #         }
    #     }
    #==========================================================================
    
    

    
    for tag, pars in runpars_d.items():
        cf_fp, out_dir = pars['cf_fp'], pars['out_dir']
        assert os.path.exists(cf_fp)
        log = mod_logger.getChild(tag)
        #==========================================================================
        # execute
        #==========================================================================
        wrkr = Risk1(cf_fp, out_dir=out_dir, logger=log, tag=tag, split_key='fail')
        
        wrkr.setup()
        
        res, res_df = wrkr.run(res_per_asset=True)
        
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
            
        log.info('finished')
    

    force_open_dir(out_dir)

    print('finished')