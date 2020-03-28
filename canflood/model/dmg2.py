'''
Created on Feb. 7, 2020

@author: cefect

impacts model 2
'''



#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import configparser, os, logging

import pandas as pd
import numpy as np
import math

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
    mod_logger = logging.getLogger('dmg2') #get the root logger

    from hlpr.exceptions import QError as Error

from hlpr.Q import *
from hlpr.basic import *
from model.modcom import Model


#==============================================================================
# functions----------------------
#==============================================================================
class Dmg2(Model):
    #==========================================================================
    # #program vars
    #==========================================================================
    valid_par = 'dmg2'
    #datafp_section = 'dmg_fps'
    
    
    #expectations from parameter file
    exp_pars_md = {#mandataory: section: {variable: handles} 
        'parameters' :
            {'name':{'type':str}, 'cid':{'type':str},
             'felv':{'values':('ground', 'datum')},
             'prec':{'type':int}, 
             },
        'dmg_fps':{
             'finv':{'ext':('.csv',)},
             'curves':{'ext':('.xls',)},
             'expos':{'ext':('.csv',)},
                    },
        'risk_fps':{
             'evals':{'ext':('.csv',)}, #only required for checks
                    },
             
        'validation':{
            'dmg2':{'type':bool}
                    }
                    }
    
    exp_pars_op = {#optional expectations
        'dmg_fps':{
            'gels':{'ext':('.csv',)},
                    }
                    }
    
    group_cnt = 4


    
    def __init__(self,
                 cf_fp,
                 **kwargs
                 ):
        
        #init the baseclass
        super().__init__(cf_fp, **kwargs) #initilzie Model
       
        self.dfuncs_d = dict() #container for damage functions
        
        #update the inventory expectations
        self.finv_exp_d = {**self.finv_exp_d,
                                   **{'f1_tag':{'type':np.object},
                                      }
                           }
        
        self.logger.debug('finished __init__ on Dmg2')
        
    def setup(self):
        
        
        
        #======================================================================
        # setup funcs
        #======================================================================
        self.init_model()
        self.resname = 'dmgs_%s_%s'%(self.name, self.tag)
        
        #self.load_data()
        self.load_finv()
        self.load_evals()
        self.load_expos()
    
        self.data_d['curves'] = pd.read_excel(self.curves, sheet_name=None, header=None, index_col=None)
        
        if self.felv == 'ground':
            self.load_gels()
            self.add_gels()
        
        self.setup_dfuncs(self.data_d['curves'])
        
        #self.setup_finv()
        
        
        #self.setup_expo_data()
        self.build_exp_finv() #build the expanded finv
        self.build_depths()
        
        #======================================================================
        # checks
        #======================================================================
        self.check_ftags()
        
        #======================================================================
        # wrap
        #======================================================================
        
        self.logger.debug('finished setup() on Dmg2')
        
        return self
         
    def setup_dfuncs(self, # build curve workers
                 df_d, #{tab name: raw curve data
                 ):
        """
        consider only building curves found in the inventory
        """
        
        log = self.logger.getChild('setup_dfuncs')
        
        #loop through each frame and build the func
        for tabn, df in df_d.items():
            if tabn.startswith('_'):
                log.warning('skipping dummy tab \'%s\''%tabn)
                continue
            
            if not isinstance(df, pd.DataFrame):
                raise Error('unexpected type on tab \'%s\': %s'%(tabn, type(df)))
            
            
            
            #build it
            dfunc = DFunc(tabn).build(df, log)
            
            #store it
            self.dfuncs_d[dfunc.tag] = dfunc
            
        log.debug('finishe building %i curves \n    %s'%(
            len(self.dfuncs_d), list(self.dfuncs_d.keys())))
        
    def check_ftags(self):
        fdf = self.data_d['finv']
        
        #check all the tags are in the dfunc
        
        tag_boolcol = fdf.columns.str.contains('tag')
        
        f_ftags = pd.Series(pd.unique(fdf.loc[:, tag_boolcol].values.ravel())
                            ).dropna().to_list()

        c_ftags = list(self.dfuncs_d.keys())
        
        miss_l = set(f_ftags).difference(c_ftags)
        
        assert len(miss_l) == 0, '%i ftags in the finv not in the curves: \n    %s'%(
            len(miss_l), miss_l)
        
        
        #set this for later
        self.f_ftags = f_ftags

    def run(self, #main runner fucntion
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        

        #======================================================================
        # get damages
        #======================================================================
        # #get damages per bid
        bres_df = self.bdmg()
        
        if bres_df is None:
            return None
        
        # recast as cid
        cres_df = bres_df.groupby(self.cid).sum().drop(self.bid, axis=1)
        
        log.info('got damages for %i events and %i assets'%(
            len(cres_df), len(cres_df.columns)))
        
        #======================================================================
        # checks
        #======================================================================

        fdf = self.data_d['finv']
        
        miss_l = set(fdf.index.values).symmetric_difference(cres_df.index.values)
        
        assert len(miss_l) == 0, 'result inventory mismatch'
        assert np.array_equal(fdf.index, cres_df.index), 'index mismatch'
        
        log.info('maxes:\n%s'%(
            cres_df.max()))
        log.info('finished w/ %s and TtlDmg = %.2f'%(
            str(cres_df.shape), cres_df.sum().sum()))
        
        return cres_df
        
    def bdmg(self, #get damages on binv
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('bdmg')
        
        #set some locals
        bdf ,ddf = self.bdf, self.ddf
        """ddf is appending _1 to column names"""
        cid, bid = self.cid, self.bid
        
        
        assert bid in ddf.columns
        assert ddf.index.name == bid
        assert np.array_equal(ddf.index.values, ddf[bid].values)
        
        #identifier for depth columns
        dboolcol = ~ddf.columns.isin([cid, bid])
        
        log.info('running on %i assets and %i events'%(len(bdf), len(ddf.columns)-2))
        

        #======================================================================
        # adjust depths by exposure grade
        #======================================================================
        """
        resserved for future dev
        
        one value per cid?
        """

        
        #======================================================================
        # calc setup
        #======================================================================
        #get relvant bids
        vboolidx = pd.DataFrame(np.logical_and(
            ddf.loc[:, dboolcol] > 0,#get bids w/ positive depths
            ddf.loc[:,dboolcol].notna()) #real depths
        ).any(axis=1)  
        
        #valid_bids = ddf.loc[boolidx, cid].values
        
        if not vboolidx.any():
            log.warning('no valid depths!')
            return None
        
        #get tags w/ depths
        """indexes shoul dmatchy"""
        all_tags =  bdf.loc[:, 'ftag'].unique().tolist()
        valid_tags = bdf.loc[vboolidx, 'ftag'].unique().tolist()
        
        log.info('calculating for %i (of %i) ftags w/ positive depths: %s'%(
            len(valid_tags), len(all_tags), valid_tags))
        
        #start results container
        res_df = bdf.loc[:, [bid, cid, 'ftag', 'fcap', 'fscale']]
        res_df.index.name = None
        
        #get events name set
        """makes it easier to keep track of all the results by event"""
        events_df = pd.DataFrame(index = ddf.columns[dboolcol])
        
        for sufix in ['raw', 'scaled', 'capped', 'dmg']:
            events_df[sufix] = events_df.index + '_%s'%sufix
        
        #======================================================================
        # RAW: loop and calc raw damage by ftag
        #======================================================================
        first = True
        self.progress = 0
        len_valid_tags = len(valid_tags)
        valid_tags_count = 0
        
        
        
        for indxr, ftag in enumerate(valid_tags):

            # update progress variable
            self.progress = math.ceil((100.0 * valid_tags_count) / len_valid_tags)
            valid_tags_count += 1
            
            log = self.logger.getChild('run.%s'%ftag)
            
            
            #identify these entries
            boolidx = np.logical_and(
                bdf['ftag'] == ftag, #with the right ftag
                vboolidx) #and in the valid set
            
            assert boolidx.any()
            
            log.info('(%i/%i) calculating \'%s\' w/ %i assets (of %i)'%(
                indxr+1, len(valid_tags), ftag, boolidx.sum(), len(boolidx)))
            
            log.info('%i progress'%(self.progress))
            #==================================================================
            # calc damage by tag.depth
            #==================================================================
            #get these depths
            tddf = ddf.loc[boolidx, :]
            
            """
            todo: add check for max depth to improve performance
            """
            
            deps_ar = pd.Series(np.unique(np.ravel(tddf.loc[:, dboolcol].values))
                                ).dropna().values
            
            #get this DFunc
            dfunc = self.dfuncs_d[ftag]
            
            log.debug('calc for %i (of %i) unique depths'%(
                len(deps_ar), tddf.size))
            
            """multi-threading would nice for this loop"""
            
            #loop and get 
            res_d = dict()
            for dep in deps_ar:
                res_d[dep] = dfunc.get_dmg(dep)
                
            #==================================================================
            # link these damages back to the results
            #==================================================================
            dep_dmg_df = pd.Series(res_d, name='dmg_raw').to_frame().reset_index(
                ).rename(columns={'index':'dep'})
                
                
            for event in tddf.columns[dboolcol]:
                
                #get just the depths for this event and the bid
                df = tddf.loc[:, [bid, event]].rename(columns={event: 'dep'}
                                                      ).dropna(subset=['dep'], how='all')
                
                #attach damages to this
                df = df.merge(dep_dmg_df, on='dep', how='left', validate='m:1')
                
                #give this column the correct name and slice down
                df = df.loc[:, [bid, 'dmg_raw']].rename(
                        columns={'dmg_raw':events_df.loc[event, 'raw']}
                                    ).set_index(bid)
                
                #add these to the results
                if first: #first time around.. add new columns
                    res_df = res_df.merge(df, on=bid, how='left', validate='1:1')
                else: #second time around.. update the existing columns
                    res_df.update(df, overwrite=False, errors='raise')
                    
                
                log.debug('added %i (of %i) raw damage values from tag \"%s\' to event \'%s\''%(
                    len(df), len(res_df), ftag, event))
                
                
            #==================================================================
            # wrap
            #==================================================================

                
            first = False
            log.debug('finished raw_damages for %i events'%dboolcol.sum())
         
        # finished loop
        self.progres = 100
           
        log = self.logger.getChild('run')

        
        log.info('finished getting raw damages for %i dfuncs and %i events'%(
            len(valid_tags),dboolcol.sum()))
            
        #======================================================================
        # SCALED--------------
        #======================================================================
        #loop and add scaled damages
        """
        view(events_df)
        """
        for event, e_ser in events_df.iterrows():

            #find this raw damage column
            boolcol =  res_df.columns == e_ser['raw']
            
            #check it
            if not boolcol.sum() == 1:
                raise Error('\'%s\' got bad match count'%event)

            #calc and set the scalecd values
            res_df[e_ser['scaled']] = res_df.loc[:, boolcol].multiply(res_df['fscale'], axis=0)
                
        


        log.info('scaled damages')
        #======================================================================
        #CAPPED------------
        #======================================================================
        
        #loop and add scaled damages
        for event, e_ser in events_df.iterrows():
            """add some sort of reporting on what damages are capped?"""

            #get teh scaled and the cap
            boolcol =  np.logical_or(
                res_df.columns == e_ser['scaled'],
                res_df.columns == 'fcap')

            assert boolcol.sum() == 2, 'bad column match'
            
            
            #identify nulls
            boolidx = res_df[e_ser['scaled']].notna()
            #calc and set the scalecd values
            res_df.loc[boolidx, e_ser['capped']] = res_df.loc[boolidx, boolcol].min(axis=1)
                

        
        log.info('capped damages')
        
        #======================================================================
        # DMG-------------
        #======================================================================
        #just duplicating the capped columns for now
        for event, e_ser in events_df.iterrows():
            boolcol = res_df.columns == e_ser['capped']
            res_df[e_ser['dmg']] = res_df.loc[:, boolcol].fillna(0)
            

        
        log.info('got final damages')
        
        #======================================================================
        # wrap------------
        #======================================================================
        #======================================================================
        # checks
        #======================================================================
        assert np.array_equal(res_df.index, self.bdf.index), 'index mismatch'
                
        #columns to keep
        boolcol = res_df.columns.isin([cid, bid]+ events_df['dmg'].tolist())
        
        res_df1 = res_df.loc[:, boolcol]
        
        #clean up columns
        
        
        assert res_df1.notna().all().all(), 'got some nulls'
        
        log.info('finished w/ %s'%str(res_df1.shape))
        return res_df1
        """
        view(res_df1)
        """
        
    def upd_cf(self, #update the control file 
               out_fp = None,cf_fp = None):
        #======================================================================
        # set defaults
        #======================================================================
        if out_fp is None: out_fp = self.out_fp
        if cf_fp is None: cf_fp = self.cf_fp
        
        return self.update_cf(
            {
            'risk_fps':(
                {'dmgs':self.out_fp}, 
                '#\'dmgs\' file path set from dmg2.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                ),
            'validation':(
                {'risk2':'True'},
                )
             },
            cf_fp = cf_fp
            )
                   
class DFunc(object, 
            ): #damage function
    
    #==========================================================================
    # program pars
    #==========================================================================
    #required names from file
    exp_row_nm = ['tag','depth']
    
    dd_df = pd.DataFrame() #depth-damage data
    
    """lets just do columns by location
    exp_coln = []"""
    
    #==========================================================================
    # user pars
    #==========================================================================
    tag = 'dfunc'
    
    def __init__(self,
                 tabn='damage_func', #optional tab name for logging
                 ):
        
        self.tabn= tabn
        
    
    def build(self,
              df_raw, #raw parameters to build the DFunc w/ 
              logger):
        
        
        
        log = logger.getChild('%s'%self.tabn)
        
        #log.info('on df %s:\n%s'%(str(df_raw.shape), df_raw))
        
        #======================================================================
        # precheck
        #======================================================================
        #check all the rows are there
        miss_l = set(self.exp_row_nm).difference(df_raw.iloc[:, 0])
        assert len(miss_l) == 0, \
            'tab \'%s\' missing %i expected row names: %s'%(
                self.tabn, len(miss_l), miss_l)
            
        """
        import pandas as pd
        fp = r'C:\LS\03_TOOLS\CanFlood\_ins\build\cT2\CanFlood_curves_rfda_20200218.xls'
        data.keys()
        df_raw = data['AA_MC']
        """
            
        
        #======================================================================
        # identify depth-damage data
        #======================================================================
        #slice and clean
        df = df_raw.iloc[:, 0:2].dropna(axis=0, how='all')
        
        #locate depth-damage data
        boolidx = df.iloc[:,0]=='depth' #locate
        assert boolidx.sum()==1, \
            'got unepxected number of \'depth\' values on %s'%(self.tabn)
            
        depth_loc = df.index[boolidx].tolist()[0]
        
        boolidx = df.index.isin(df.iloc[depth_loc:len(df), :].index)
        
        
        #======================================================================
        # attach other pars
        #======================================================================
        #get remainder of data
        pars_d = df.loc[~boolidx, :
                        ].set_index(df.columns[0], drop=True
                                    ).iloc[:,0].to_dict()
        
        for varnm, val in pars_d.items():
            setattr(self, varnm, val)
            
        log.debug('attached %i parameters to Dfunc: \n    %s'%(len(pars_d), pars_d))
        
        
        #======================================================================
        # extract depth-dmaage data
        #======================================================================
        #extract depth-damage data
        dd_df = df.loc[boolidx, :].reset_index(drop=True)
        dd_df.columns = dd_df.iloc[0,:].to_list()
        dd_df = dd_df.drop(dd_df.index[0], axis=0).reset_index(drop=True) #drop the depth-damage row
        
        #typeset it
        dd_df.iloc[:,0:2] = dd_df.iloc[:,0:2].astype(float)
        
       
        ar = np.sort(np.array([dd_df.iloc[:,0].tolist(), dd_df.iloc[:,1].tolist()]), axis=1)
        self.dd_ar = ar
        
        log.info('\'%s\' built w/ dep min/max %.2f/%.2f and dmg min/max %.2f/%.2f'%(
            self.tag, min(ar[0]), max(ar[0]), min(ar[1]), max(ar[1])
            ))
        
        return self
        
        
    def get_dmg(self, #get damage from depth using depth damage curve
                depth):
        
        ar = self.dd_ar
        
        dmg = np.interp(depth, #depth find damage on
                        ar[0], #depths 
                        ar[1], #damages
                        left=0, #depth below range
                        right=max(ar[1]), #depth above range
                        )

#==============================================================================
#         #check for depth outside bounds
#         if depth < min(ar[0]):
#             dmg = 0 #below curve
# 
#             
#         elif depth > max(ar[0]):
#             dmg = max(ar[1]) #above curve
# 
#         else:
#             dmg = np.interp(depth, ar[0], ar[1])
#==============================================================================
            
        return dmg


if __name__ =="__main__": 
    

    #==========================================================================
    # dev data
    #=========================================================================
    #==========================================================================
    # out_dir = os.path.join(os.getcwd(), 'dmg2')
    # tag='dev'
    # 
    # cf_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\dmg2\CanFlood_dmg2.txt'
    #==========================================================================
    
    #==========================================================================
    # tutorial 2
    #==========================================================================
    #===========================================================================
    # runpars_d={
    #     'Tut2':{
    #         'out_dir':os.path.join(os.getcwd(), 'dmg2', 'Tut2'),
    #         'cf_fp':r'C:\Users\cefect\CanFlood\build\2\CanFlood_tutorial2.txt',
    #          
    #         },
    #     }
    #===========================================================================
    
    #===========================================================================
    # tutorial 3
    #===========================================================================
    runpars_d={
        'Tut2':{
            'out_dir':os.path.join(os.getcwd(), 'dmg2', 'Tut2'),
            'cf_fp':r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\2\built\CanFlood_tut2.txt',
             
            }
        }
    
    #==========================================================================
    # build/execute
    #==========================================================================
    for tag, pars in runpars_d.items():
        cf_fp, out_dir = pars['cf_fp'], pars['out_dir']
        log = mod_logger.getChild(tag)
        assert os.path.exists(cf_fp)
        
        wrkr = Dmg2(cf_fp, out_dir=out_dir, logger=log, tag=tag).setup()
        
        res_df = wrkr.run()
        
        if res_df is None:
            log.warning('skipping')
            continue
        #==========================================================================
        # output
        #==========================================================================
        
        out_fp = wrkr.output_df(res_df, wrkr.resname)
        
        wrkr.upd_cf()

    force_open_dir(out_dir)

    print('finished')
    
    
    
    
    
    
    
    
    