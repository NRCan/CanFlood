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
             'ground_water':{'type':bool},
             },
        'dmg_fps':{
             'finv':{'ext':('.csv',)},
             'curves':{'ext':('.xls',)},
             'expos':{'ext':('.csv',)},
                    },

             
        'validation':{
            'dmg2':{'type':bool}
                    }
                    }
    
    exp_pars_op = {#optional expectations
        'dmg_fps':{
            'gels':{'ext':('.csv',)},
                    },
        'risk_fps':{
             'evals':{'ext':('.csv',)}, #only required for checks
                    },
                    }
    
    group_cnt = 4
    
    plot_fmt = '${:,.0f}'
    
    #minimum inventory expectations
    finv_exp_d = {
        'f0_tag':{'type':np.object},
        'f0_scale':{'type':np.number},
        'f0_elv':{'type':np.number},
        }


    
    def __init__(self,
                 cf_fp,

                 **kwargs
                 ):
        

        
        #init the baseclass
        super().__init__(cf_fp, **kwargs) #initilzie Model
       
        self.dfuncs_d = dict() #container for damage functions
        

        
        self.logger.debug('finished __init__ on Dmg2')
        
    def setup(self):
        
        
        
        #======================================================================
        # setup funcs
        #======================================================================
        self.init_model()
        self.resname = 'dmgs_%s_%s'%(self.name, self.tag)
        

        self.load_finv()
        
        if not self.evals == '':
            """evals are optional"""
            self.load_evals()
        else:
            self.expcols = pd.Series(dtype=np.object).index
            
        self.load_expos()
    
        self.data_d['curves'] = pd.read_excel(self.curves, sheet_name=None, header=None, index_col=None)
        
        if self.felv == 'ground':
            self.load_gels()
            self.add_gels()
        

        
        self.build_exp_finv() #build the expanded finv
        self.build_depths()
        
        self.setup_dfuncs(self.data_d['curves'])
        
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
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('setup_dfuncs')
        minDep_d = dict() #minimum depth container
        
        #=======================================================================
        # get list of dfuncs in the finv
        #=======================================================================
        assert self.bdf['ftag'].dtype.char == 'O'
        ftags_valid = self.bdf['ftag'].unique().tolist()

        log.info('loading for %i valid ftags in the finv'%len(ftags_valid))
        #=======================================================================
        # #loop through each frame and build the func
        #=======================================================================
        for tabn, df in df_d.items():
            if tabn.startswith('_'):
                log.warning('skipping dummy tab \'%s\''%tabn)
                continue
            
            #skip those not in the finv
            if not tabn in ftags_valid:
                continue
            
            if not isinstance(df, pd.DataFrame):
                raise Error('unexpected type on tab \'%s\': %s'%(tabn, type(df)))
            
            
            
            #build it
            dfunc = DFunc(tabn).build(df, log)
            
            #store it
            self.dfuncs_d[dfunc.tag] = dfunc
            
            #collect stats
            assert isinstance(dfunc.min_dep, float)
            minDep_d[tabn] = dfunc.min_dep
            

        #=======================================================================
        # post checks
        #=======================================================================
        #check we loaded everything
        l = set(ftags_valid).difference(self.dfuncs_d.keys())
        assert len(l)==0,'failed to load: %s'%l
        
        #check ground_water condition vs minimum value passed in dfuncs.
        if not self.ground_water:
            if min(minDep_d.values())<0:
                log.warning('ground_water=False but some dfuncs have negative depth values')
        
        #=======================================================================
        # wrap
        #=======================================================================
        
        self.df_minD_d = minDep_d
        
        log.info('finishe building %i curves \n    %s'%(
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
        
        self.feedback.setProgress(5)
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
        self.feedback.setProgress(95)
        fdf = self.data_d['finv']
        
        miss_l = set(fdf.index.values).symmetric_difference(cres_df.index.values)
        
        assert len(miss_l) == 0, 'result inventory mismatch: \n    %s'%miss_l
        assert np.array_equal(fdf.index, cres_df.index), 'index mismatch'
        
        log.info('maxes:\n%s'%(
            cres_df.max()))
        log.info('finished w/ %s and TtlDmg = %.2f'%(
            str(cres_df.shape), cres_df.sum().sum()))
        
        return cres_df
        
    def bdmg(self, #get damages on expanded finv
             
             #run controls

            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('bdmg')
        
        #set some locals
        bdf = self.bdf  #expanded finv. see modcom.build_exp_finv(). each row has 1 ftag
        ddf = self.ddf
        """ddf is appending _1 to column names"""
        cid, bid = self.cid, self.bid
        


        
        
        assert bid in ddf.columns
        assert ddf.index.name == bid
        assert np.array_equal(ddf.index.values, ddf[bid].values)
        
        #identifier for depth columns
        dboolcol = ~ddf.columns.isin([cid, bid])
        
        log.info('running on %i assets and %i events'%(len(bdf), len(ddf.columns)-2))
        
        self.feedback.setProgress(10)
        #======================================================================
        # adjust depths by exposure grade
        #======================================================================
        """
        resserved for future dev
        
        one value per cid?
        """

        
        #======================================================================
        # setup-----
        #======================================================================
        #=======================================================================
        # id valid bids
        #=======================================================================
        if self.ground_water:
            mdval = min(self.df_minD_d.values())
        else:
            mdval = 0
        
        dep_boolcol = ddf.loc[:, dboolcol] >= mdval
        
        #report those faling the check
        if not dep_boolcol.all().all():
            log.warning('got %i (of %i) entries w/ invalid depths (<= %.2f)'%(
                np.invert(dep_boolcol).sum().sum(), dep_boolcol.size, mdval))
        
        #combine
        vboolidx = pd.DataFrame(np.logical_and(
            dep_boolcol, #those exceeding min depth
            ddf.loc[:,dboolcol].notna()) #real depths
            ).any(axis=1)  
        
        #check
        if not vboolidx.any():
            log.warning('no valid depths!')
            return None
        
        #=======================================================================
        # #get  valid dfunc tags
        #=======================================================================
        """indexes shoul dmatchy"""
        all_tags =  bdf.loc[:, 'ftag'].unique().tolist()
        valid_tags = bdf.loc[vboolidx, 'ftag'].unique().tolist() #all tags w/ valid depths
        
        log.info('calculating for %i (of %i) ftags w/ positive depths: %s'%(
            len(valid_tags), len(all_tags), valid_tags))
        
        #=======================================================================
        # #start results container
        #=======================================================================
        res_df = bdf.loc[:, [bid, cid, 'ftag', 'fcap', 'fscale']].copy()
        """need this for the joiner to work (bid is ambigious)"""
        res_df.index.name = None
        
        #=======================================================================
        # build the events matrix
        #=======================================================================
        """makes it easier to keep track of all the results by event
        view(events_df)
        """
        #get events name set
        events_df = pd.DataFrame(index = ddf.columns[dboolcol])       
        for sufix in ['raw', 'scaled', 'capped', 'dmg']:
            events_df[sufix] = events_df.index + '_%s'%sufix
        
        #======================================================================
        # RAW: loop and calc raw damage by ftag-------------
        #======================================================================
        #setup loop pars
        first = True
        for indxr, ftag in enumerate(valid_tags):
            log = self.logger.getChild('bdmg.%s'%ftag)
            
            dfunc = self.dfuncs_d[ftag] #get this DFunc
            
            #identify these entries
            boolidx = np.logical_and(
                bdf['ftag'] == ftag, #with the right ftag
                vboolidx) #and in the valid set
            
            assert boolidx.any()
            
            log.info('(%i/%i) calculating \'%s\' w/ %i assets (of %i)'%(
                indxr+1, len(valid_tags), ftag, boolidx.sum(), len(boolidx)))
            #==================================================================
            # calc damage by tag.depth
            #==================================================================
            """
            to improve performance,
                we only calculate each depth once, then join back to the results
                
            todo: add check for max depth to improve performance
            """
            
            #get all  depths (per asset)
            tddf = ddf.loc[boolidx, :]
            
            #get just the unique depths that need calculating
            deps_ar = pd.Series(np.unique(np.ravel(tddf.loc[:, dboolcol].values))
                                ).dropna().values
            
            log.debug('calc for %i (of %i) unique depths'%(
                len(deps_ar), tddf.size))
            
            """multi-threading would nice for this loop"""
            
            #loop each depth through the damage function to get the result                
            res_d = {dep:dfunc.get_dmg(dep) for dep in deps_ar}
                
            #==================================================================
            # link these damages back to the results
            #==================================================================
            dep_dmg_df = pd.Series(res_d, name='dmg_raw').to_frame().reset_index(
                ).rename(columns={'index':'dep'})
                
            #checks
            assert np.array_equal(dep_dmg_df.dtypes.values, np.array([np.dtype('float64'), np.dtype('float64')], dtype=object))
            assert dep_dmg_df.notna().all().all()
                
                
            for event in tddf.columns[dboolcol]:
                
                #get just the depths for this event and the bid
                df = tddf.loc[:, [bid, event]].rename(columns={event: 'dep'}
                                                      ).dropna(subset=['dep'], how='all')
                
                #join damages to this
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

            # update progress variable
            self.feedback.upd_prog((indxr+1)/len(valid_tags)*60, method='raw')
            first = False
            log.debug('finished raw_damages for %i events'%dboolcol.sum())
         
           
        log = self.logger.getChild('bdmg')

        
        log.info('finished getting raw damages for %i dfuncs and %i events'%(
            len(valid_tags),dboolcol.sum()))
            
        #======================================================================
        # SCALED--------------
        #======================================================================
        #loop and add scaled damages
        """
        view(events_df)
        view(res_df)
        """
        for event, e_ser in events_df.iterrows():

            #find this raw damage column
            boolcol =  res_df.columns == e_ser['raw']
            
            #check it
            if not boolcol.sum() == 1:
                raise Error('\'%s\' got bad match count'%event)
            
            if res_df.loc[:, boolcol].isna().all().iloc[0]:
                log.warning('%s got all nulls!'%event)

            #calc and set the scalecd values
            try:
                res_df[e_ser['scaled']] = res_df.loc[:, boolcol].multiply(res_df['fscale'], axis=0)
            except Exception as e:
                raise Error('failed w/ \n    %s'%e)
                
        log.info('scaled damages')
        self.feedback.setProgress(80)
        #======================================================================
        #CAPPED------------
        #======================================================================
        #loop and add scaled damages
        meta_d = dict()
        cmeta_df =res_df.loc[:,[cid, bid, 'ftag', 'fcap', 'fscale']]
        for event, e_ser in events_df.iterrows():
            """add some sort of reporting on what damages are capped?"""

            #get teh scaled and the cap
            boolcol =  np.logical_or(
                res_df.columns == e_ser['scaled'],
                res_df.columns == 'fcap')

            assert boolcol.sum() == 2, 'bad column match'
            
            """
            boolidx.sum()
            len(boolidx)
            """
             
            
            
            #identify nulls
            boolidx = res_df[e_ser['scaled']].notna()
            #calc and set the scalecd values
            res_df.loc[boolidx, e_ser['capped']] = res_df.loc[boolidx, boolcol].min(axis=1)
            
            
            #report
            """written by bdmg_smry"""
            mser = res_df.loc[boolidx, e_ser['scaled']] >res_df.loc[boolidx, 'fcap']
            cmeta_df= cmeta_df.join(mser.rename(event), how='left')
            meta_d[event] = mser.sum()
                
        log.info('cappd %i events w/ bid cnts maxing out (of %i) \n    %s'%(
            len(meta_d), len(res_df), meta_d))
        
        log.info('capped damages')
        self.feedback.setProgress(90)
        #======================================================================
        # DMG-------------
        #======================================================================
        #just duplicating the capped columns for now
        for event, e_ser in events_df.iterrows():
            boolcol = res_df.columns == e_ser['capped']
            res_df[e_ser['dmg']] = res_df.loc[:, boolcol].fillna(0)
            
        log.info('got final damages')
        self.feedback.setProgress(92)
        
        #=======================================================================
        # meta--------
        #=======================================================================
        #set these for use later
        self.bdmg_df = res_df
        self.events_df = events_df.copy()
        self.cmeta_df = cmeta_df


        #======================================================================
        # wrap------------
        #======================================================================
        #======================================================================
        # checks
        #======================================================================
        assert np.array_equal(res_df.index, bdf.index), 'index mismatch'
                
        #columns to keep
        boolcol = res_df.columns.isin([cid, bid]+ events_df['dmg'].tolist())
        
        res_df1 = res_df.loc[:, boolcol]
        
        assert res_df1.notna().all().all(), 'got some nulls'
        
        log.info('finished w/ %s'%str(res_df1.shape))
        return res_df1
        """
        view(res_df)
        view(res_df1)
        """
         
    def bdmg_smry(self, #generate summary of damages
                  res_df=None,  #built results
                  events_df=None,  #event name matrix
                  cmeta_df=None, #cap by asset
                  gCn = 'ftag', #column name to group on
                  
                  
                  logger=None,
                  
                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if res_df is None: res_df=self.bdmg_df
        if events_df is None: events_df=self.events_df
        if cmeta_df is None: cmeta_df=self.cmeta_df
        if logger is None: logger=self.logger
        log=logger.getChild('bdmg_smry')
        
        """
        view(events_df)
        view(res_df)
        """
        #rename conversion

        #=======================================================================
        # impact meta for each result type
        #=======================================================================
        res_d = dict() #container for meta
        for rtName, rser in events_df.items():
            
            #slice to results columns of this type
            rdf = res_df.loc[:, [gCn]+ rser.values.tolist()].dropna(how='all')
            
            #group and get totals per dfunc
            rnm_d= dict(zip(rser.to_dict().values(), rser.to_dict().keys()))
            mdf =  rdf.groupby(gCn).sum().rename( columns=rnm_d)
            
            #add count columns
            mdf['cnt'] = res_df.loc[:, [gCn, self.cid]].groupby(gCn).count()
            
            res_d[rtName] = mdf
            

        #=======================================================================
        # cap counts
        #=======================================================================
        df = cmeta_df.drop(['fcap', 'fscale', self.cid, self.bid], axis=1).fillna(False)
        cm_df1  = df.groupby(gCn).sum().astype(np.int)
        

        
        
        
        #=======================================================================
        # write results
        #=======================================================================
        
        out_fp = os.path.join(self.out_dir, '_smry_bdmg_%s_%i.xls'%(self.tag, len(res_df)))
        
        d = {**res_d, 
             'cap_cnts':cm_df1, 
             'cap_data':cmeta_df.fillna(False),
             }
   
        with pd.ExcelWriter(out_fp) as writer:
            for tabnm, df in d.items():
                assert isinstance(df, pd.DataFrame), tabnm
                try:
                    df.to_excel(writer, sheet_name=tabnm, index=True, header=True)
                except Exception as e:
                    log.error('failed to write tab \'%s\' w/ \n    %s'%(tabnm, e))
        
        log.info('wrote %i tabs to \n    %s'%(len(d), out_fp))

        
        return d
    
    def bdmg_pies(self, #generate pie charts of the damage summaries
                  df_raw, #generate a pie chart for each column
                  figsize     = (18, 6), 
                  maxStr_len = 14, #maximum string length for truncating event names
                  dfmt=None,
                  
                  linkSrch_d = {'top':'simu', 'bot':'fail'}, #how to separate data
                  logger=None,
                  ):
        
        if logger is None: logger=self.logger
        log=logger.getChild('bdmg_pies')
        
        #=======================================================================
        # defaults
        #=======================================================================
        if dfmt is None: dfmt = self.plot_fmt
        
        #======================================================================
        # setup
        #======================================================================
        
        import matplotlib
        matplotlib.use('Qt5Agg') #sets the backend (case sensitive)
        import matplotlib.pyplot as plt
        
        #set teh styles
        plt.style.use('default')
        
        #font
        matplotlib_font = {
                'family' : 'serif',
                'weight' : 'normal',
                'size'   : 8}
        
        matplotlib.rc('font', **matplotlib_font)
        matplotlib.rcParams['axes.titlesize'] = 10 #set the figure title size

        
        #spacing parameters
        matplotlib.rcParams['figure.autolayout'] = False #use tight layout
        
        
        #=======================================================================
        # prep data
        #=======================================================================
        df = df_raw.sort_index(axis=1)
        def get_colns(srch):
            #id the columns
            bcx = df.columns.str.contains(srch,  case=False)
            return df.columns[bcx].to_list()
        
        tcolns = get_colns(linkSrch_d['top']) 
        bcolns = get_colns(linkSrch_d['bot'])

        

        #======================================================================
        # figure setup
        #======================================================================\
        
        plt.close()

        #build the figure canvas
        fig = plt.figure(figsize=figsize,
                     tight_layout=True,
                     constrained_layout = False,
                     )
        
        fig.suptitle('%s_%s Damage pies on %i'%(self.name, self.tag, len(df.columns)),
                     fontsize=12, fontweight='bold')
        
        #populate with subplots
        ax_ar = fig.subplots(nrows=2, ncols=len(tcolns))
        
        #convert axis array into useful dictionary
        tax_d = dict(zip(tcolns, ax_ar[0].tolist()))
        bax_d = dict(zip(bcolns, ax_ar[1].tolist()))
        
        #=======================================================================
        # loop and plot
        #=======================================================================
        def loop_axd(ax_d, rowLab):
            #===================================================================
            # def func(pct, allvals):
            #     absolute = int(pct/100.*np.sum(allvals)) #convert BACK to the value
            #     return "{:.1f}%\n{:.2f}".format(pct, absolute)
            #===================================================================
            first = True
            for coln, ax in ax_d.items():
                
                #get data
                dser = df.loc[:, coln]
                
                
                wedges, texts, autotexts = ax.pie(
                    dser, labels=dser.values, 
                       autopct='%1.1f%%',
                       #autopct=lambda pct: func(pct, dser),
                       )
                
                #fix labels
                for e in texts:
                    ov = e.get_text()
                    e.set_text(dfmt.format(float(ov)))
                
                #set truncated title
                titlestr = (coln[:maxStr_len]) if len(coln) > maxStr_len else coln
                ax.set_title(titlestr)
                
                #add text
                if first:
                    xmin, xmax1 = ax.get_xlim()
                    ymin, ymax1 = ax.get_ylim()
                    x_text = xmin + (xmax1 - xmin)*0 # 1/10 to the right of the left ax1is
                    y_text = ymin + (ymax1 - ymin)*.5 #1/10 above the bottom ax1is
                    anno_obj = ax.text(x_text, y_text, rowLab, fontsize=12, color='red', fontweight='bold')
                    first=False
            
            return wedges, ax #return for legend handles
                
                
        loop_axd(tax_d, linkSrch_d['top'])
        wedges, ax = loop_axd(bax_d, linkSrch_d['bot'])
        
        #turn the legend on 

        ax.legend(wedges, df.index.values)
        
        
        fig.tight_layout()
        log.info('built pies')
        
        
        return fig
    """
    plt.show()
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
                   
class DFunc(ComWrkr, 
            ): #damage function
    
    #==========================================================================
    # program pars
    #==========================================================================

    
    dd_df = pd.DataFrame() #depth-damage data
    
    """lets just do columns by location
    exp_coln = []"""
    
    #==========================================================================
    # user pars
    #==========================================================================
    tag = 'dfunc'
    min_dep = None
    pars_d = {}
    
    def __init__(self,
                 tabn='damage_func', #optional tab name for logging
                 
                 **kwargs):
        
        self.tabn= tabn
        
        #init the baseclass
        super().__init__(**kwargs) #initilzie Model
        
    
    def build(self,
              df_raw, #raw parameters to build the DFunc w/ 
              logger):
        
        
        
        log = logger.getChild('%s'%self.tabn)
        
        #log.info('on df %s:\n%s'%(str(df_raw.shape), df_raw))
        
        #======================================================================
        # precheck
        #======================================================================
        #=======================================================================
        # #check all the rows are there
        # miss_l = set(self.exp_row_nm).difference(df_raw.iloc[:, 0])
        # assert len(miss_l) == 0, \
        #     'tab \'%s\' missing %i expected row names: %s'%(
        #         self.tabn, len(miss_l), miss_l)
        #=======================================================================
        
            

        
        #======================================================================
        # identify depth-damage data
        #======================================================================
        #slice and clean
        df = df_raw.iloc[:, 0:2].dropna(axis=0, how='all')
        
        #validate the curve
        self.check_curve(df.set_index(df.columns[0]).iloc[:,0].to_dict(),
                         logger=log)
        
        #locate depth-damage data
        boolidx = df.iloc[:,0]=='exposure' #locate
        
        assert boolidx.sum()==1, \
            'got unepxected number of \'exposure\' values on %s'%(self.tabn)
            
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
        self.pars_d = pars_d.copy()
        
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
        
        #=======================================================================
        # get stats
        #=======================================================================
        self.min_dep = min(ar[0])
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('\'%s\' built w/ dep min/max %.2f/%.2f and dmg min/max %.2f/%.2f'%(
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
    
    
    def get_stats(self): #get basic stats from the dfunc
        deps = self.dd_ar[0]
        dmgs = self.dd_ar[1]
        return {**{'min_dep':min(deps), 'max_dep':max(deps), 
                'min_dmg':min(dmgs), 'max_dmg':max(dmgs), 'dcnt':len(deps)},
                **self.pars_d}
#===============================================================================
# def run():
# 
#     #==========================================================================
#     # dev data
#     #=========================================================================
#     #==========================================================================
#     # out_dir = os.path.join(os.getcwd(), 'dmg2')
#     # tag='dev'
#     # 
#     # cf_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\dmg2\CanFlood_dmg2.txt'
#     #==========================================================================
#     
#     #==========================================================================
#     # tutorial 2
#     #==========================================================================
# 
#     runpars_d={
#         'Tut2':{
#             'out_dir':os.path.join(os.getcwd(), 'dmg2', 'Tut2'),
#             'cf_fp':r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\2\built\CanFlood_tut2.txt',
#             }
#         }
#     
#     #===========================================================================
#     # GolderHazard test
#     #===========================================================================
#     runpars_d={
#         'run1':{
#             'out_dir':r'C:\LS\03_TOOLS\CanFlood\_ins\IBI_GolderHazard_20200507\results\wi_noFail2',
#             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_ins\IBI_GolderHazard_20200507\build\CanFlood_GH_wi_noFail.txt',
#             }
#         }
# 
#     
#     #==========================================================================
#     # build/execute
#     #==========================================================================
#     for tag, pars in runpars_d.items():
#         cf_fp, out_dir = pars['cf_fp'], pars['out_dir']
#         log = mod_logger.getChild(tag)
#         assert os.path.exists(cf_fp)
#         
#         wrkr = Dmg2(cf_fp, out_dir=out_dir, logger=log, tag=tag).setup()
#         
#         res_df = wrkr.run()
#         
#         if res_df is None:
#             log.warning('skipping')
#             continue
#         #==========================================================================
#         # output
#         #==========================================================================
#         
#         out_fp = wrkr.output_df(res_df, wrkr.resname)
#         
#         wrkr.upd_cf()
# 
#     #===========================================================================
#     # wrap--------
#     #===========================================================================
#     force_open_dir(out_dir)
#     
#===============================================================================
if __name__ =="__main__": 

    print('finished')
    
    
    
    
    
    
    
    
    