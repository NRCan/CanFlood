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
    plot_fmt = '{0:.2f}' #floats w/ 2 decimal
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
        
        
        
        self.logger.debug('finished __init__ on Risk1')
        
        
    def setup(self):
        
        self.init_model()
        
        self.load_data()
        
        self.setup_finv()
        
        """really.. should just restric to one function per asset for level1"""
        self.setup_expo()
        
        self.resname = 'risk1_%s_%s'%(self.tag, self.name)
        
        self.logger.debug('finished setup_data on Risk1')
        
        return self
        
        
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
        
        if not self.gels == '':
            self.data_d['gels'] = pd.read_csv(self.gels)
        
        #======================================================================
        # #load remainders
        #======================================================================
        
        self.load_risk_data(ddf)
        
        
        log.info('finished')
        
    def run(self,
            res_per_asset=False):
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
        assert isinstance(res_per_asset, bool)
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
        res.columns = ['$']
        
        #remove tails
        if self.drop_tails:
            res = res.iloc[1:-2,:] #slice of ends 
            res.loc['ead'] = res_ser['ead'] #add ead back
        
         
        log.info('finished')


        return res, res_df
    
    def setup_expo(self):
        """
        risk1 only requires an elv column
        
        todo: consolidate this with modcom.setup_expo_data()
        
        """
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('setup_binv')
        fdf = self.data_d['finv']
        cid, bid = self.cid, self.bid
        
        assert fdf.index.name == cid, 'bad index on fdf'
        
        """
        fdf.columns
        """
        #======================================================================
        # expand
        #======================================================================
        miss_l = set(['f0_scale', 'f0_elv']).difference(fdf.columns)
        if len(miss_l) > 0:
            raise Error('passed inventory missing %i columns: \n    %s'%(len(miss_l), miss_l))

        #get tag column names
        tag_coln_l = fdf.columns[fdf.columns.str.endswith('elv')].tolist()
        
        assert len(tag_coln_l) > 0, 'no \'elv\' columns found in inventory'
        
        assert tag_coln_l[0] == 'f0_elv', 'expected first tag column to be \'f0_elv\''
        
        #get nested prefixes
        prefix_l = [coln[:2] for coln in tag_coln_l]
        
        #======================================================================
        # expand: nested entries
        #======================================================================
        if len(prefix_l) > 1:
        
            #loop and collected nests
            bdf = None
            
            for prefix in prefix_l:
                #identify prefix columns
                pboolcol = fdf.columns.str.startswith(prefix) #columns w/ prefix
                
                assert pboolcol.sum() <= 4, 'expects 4 columns w/ prefix %s'%prefix
                assert pboolcol.sum() >= 1, 'expects at least 1 w/ prefix %s'%prefix
                
                #get slice and clean
                df = fdf.loc[:, pboolcol].dropna(axis=0, how='all').sort_index(axis=1)
                
                #get clean column names
                
                
                df.columns = df.columns.str.replace('%s_'%prefix, 'f')
                df = df.reset_index()
                
                #add to main
                if bdf is None:
                    bdf = df
                else:
                    bdf = bdf.append(df, ignore_index=True, sort=False)
                            
                log.info('for \"%s\' got %s'%(prefix, str(df.shape)))
                
                
            #add back in other needed columns
            boolcol = fdf.columns.isin(['gels']) #additional columns to pivot out
            if boolcol.any(): #if we are only linking in gels, these may not exist
                bdf = bdf.merge(fdf.loc[:, boolcol], on=cid, how='left',validate='m:1')
            
            log.info('expanded inventory from %i nest sets %s to finv %s'%(
                len(prefix_l), str(fdf.shape), str(bdf.shape)))
        #======================================================================
        # expand: nothing nested
        #======================================================================
        else:
            """
            todo: 
            """
            log.info('no nested columns. using raw inventory')
            bdf = fdf.copy()
            bdf[cid] = bdf.index #need to duplicate it
            
            bdf = bdf.rename(columns={'f0_scale':'fscale', 'f0_elv':'felv'})
            
            """
            bdf.columns
            
            """
            
            
        #set an indexer columns
        """safer to keep this index as a column also"""
        bdf[bid] = bdf.index
        bdf.index.name=bid
        
        if not cid in bdf.columns:
            raise Error('bdf missing %s'%cid)
        
        assert 'fscale' in bdf.columns
        assert 'felv' in bdf.columns
        
        #======================================================================
        # adjust fscale
        #======================================================================

        boolidx = bdf['fscale'].isna()
        if boolidx.any():
            log.info('setting %i null fscale values to 1'%boolidx.sum())
            bdf.loc[:, 'fscale'] = bdf['fscale'].fillna(1.0)
            
        #======================================================================
        # convert asset heights to elevations
        #======================================================================
        if self.felv == 'ground':
            assert 'gels' in bdf.columns, 'missing gels column'
            
            bdf.loc[:, 'felv'] = bdf['felv'] + bdf['gels']
                
            log.info('converted asset ground heights to datum elevations')
        else:
            log.debug('felv = \'%s\' no conversion'%self.felv)
            
        #======================================================================
        # get depths (from wsl and elv)
        #======================================================================
        wdf = self.data_d['expos'] #wsl
        
        #pivot these out to bids
        ddf = bdf.loc[:, [bid, cid]].join(wdf.round(self.prec), 
                                          on=cid
                                          ).set_index(bid, drop=False)
               
        #loop and subtract to get depths
        boolcol = ~ddf.columns.isin([cid, bid]) #columns w/ depth values
        
        for coln in ddf.columns[boolcol]:
            ddf.loc[:, coln] = (ddf[coln] - bdf['felv']).round(self.prec)
            
        #log.info('converted wsl (min/max/avg %.2f/%.2f/%.2f) to depths (min/max/avg %.2f/%.2f/%.2f)'%( ))
        log.debug('converted wsl to depth %s'%str(ddf.shape))
        
        # #check that wsl is above ground

        """
        should also add this to the input validator tool
        """
        boolidx = ddf.drop([bid, cid], axis=1) < 0 #True=wsl below ground

        if boolidx.any().any():
            msg = 'got %i (of %i) wsl below ground'%(boolidx.sum().sum(), len(boolidx))
            if self.ground_water:
                raise Error(msg)
            else:
                log.warning(msg)
        
        #======================================================================
        # wrap
        #======================================================================
        #attach frames
        self.bdf, self.ddf = bdf, ddf
        
        log.debug('finished')
        
        #======================================================================
        # check aeps
        #======================================================================
        if 'aeps' in self.pars['risk_fps']:
            aep_fp = self.pars['risk_fps'].get('aeps')
            
            if not os.path.exists(aep_fp):
                log.warning('aep_fp does not exist... skipping check')
            else:
                aep_data = pd.read_csv(aep_fp)
                
                miss_l = set(aep_data.columns).difference(wdf.columns)
                if len(miss_l) > 0:
                    raise Error('exposure file does not match aep data: \n    %s'%miss_l)
            

        
        return





if __name__ =="__main__": 
    

    ead_plot = True
    #==========================================================================
    # dev data
    #==========================================================================
    out_dir = os.path.join(os.getcwd(), 'risk1')
    tag = 'dev'
    cf_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk1\wex\CanFlood_risk1.txt'
    
    #==========================================================================
    # 20200304 ICI.rec
    #==========================================================================
    #==========================================================================
    # tag = 'ICI_rec'
    # out_dir = r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\model'
    # cf_fp = r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\CanFlood_scenario1.txt'
    #==========================================================================
    
    #==========================================================================
    # execute
    #==========================================================================
    wrkr = Risk1(cf_fp, out_dir=out_dir, logger=mod_logger, tag=tag)
    
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
    

    force_open_dir(out_dir)

    print('finished')