'''
Created on Feb. 7, 2020

@author: cefect
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, logging.config
#logcfg_file = r'C:\Users\tony.decrescenzo\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\floodiq\_pars\logger.conf'
logger = logging.getLogger() #get the root logger
#logging.config.fileConfig(logcfg_file) #load the configuration file
#logger.info('root logger initiated and configured from file: %s'%(logcfg_file))


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import configparser, os

import pandas as pd
import numpy as np

#custom imports
import hp
from hp import Error, view

from canflood_inprep.model.common import Model


#==============================================================================
# functions----------------------
#==============================================================================
class DmgModel(Model):
    
    #==========================================================================
    # parameters from user
    #==========================================================================

    ground_water = False
    felv = 'datum'
    
    
    #==========================================================================
    # data containers
    #==========================================================================
    
    dfuncs_d = dict() #container for damage functions
    
    
    #==========================================================================
    # #program vars
    #==========================================================================
    valid_par = 'imp2'
    datafp_section = 'dmg_fps'
    bid = 'bid' #indexer for expanded finv

    
    #expected data properties
    exp_dprops = {'curves':{'ext':'.xls'},
                   'expos':{'ext':'.csv', 'colns':[]},
                    'gels':{'ext':'.csv', 'colns':[]},
                    'finv':{'ext':'.csv', 'colns':['f0_tag', 'f0_scale', 'f0_cap', 'f0_elv']},
                    }
    
    opt_dfiles = ['gels'] #optional data files
    
    exp_pars = {'parameters':list(),
                  'dmg_fps':['curves','expos', 'gels', 'finv']}
    
    dirname = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    
    def __init__(self,
                 par_fp = None,
                 out_dir = None,
                 logger = None,
                 ):
        
        #init the baseclass
        super().__init__(par_fp, out_dir, logger=logger) #initilzie teh baseclass
       
        
        
        #======================================================================
        # setup funcs
        #======================================================================
    
        self.setup_dfuncs(self.data_d['curves'])
        
        self.setup_finv()
        
        self.setup_binv()
        
        #======================================================================
        # wrap
        #======================================================================
        
        self.logger.debug('finished __init__ on Dmg')
        

 
    def setup_dfuncs(self, # build curve workers
                 df_d, #{tab name: raw curve data
                 ):
        """
        consider only building curves found in the inventory
        """
        
        log = self.logger.getChild('setup_dfuncs')
        
        #loop through each frame and build the func
        for tabn, df in df_d.items():
            if not isinstance(df, pd.DataFrame):
                raise Error('unexpected type on tab \'%s\': %s'%(tabn, type(df)))
            
            #build it
            dfunc = DFunc(tabn).build(df, log)
            
            #store it
            self.dfuncs_d[dfunc.tag] = dfunc
            
        log.info('finishe building %i curves \n    %s'%(
            len(self.dfuncs_d), list(self.dfuncs_d.keys())))
        
        
    def setup_finv(self): #check and consolidate inventory like data sets
        
        log = self.logger.getChild('setup_finv')
        cid = self.cid
        
        #======================================================================
        # check ftag membership
        #======================================================================
        #check all the tags are in the dfunc
        fdf = self.data_d['finv']
        tag_boolcol = fdf.columns.str.contains('tag')
        
        f_ftags = pd.Series(pd.unique(fdf.loc[:, tag_boolcol].values.ravel())
                            ).dropna().to_list()

        c_ftags = list(self.dfuncs_d.keys())
        
        miss_l = set(f_ftags).difference(c_ftags)
        
        assert len(miss_l) == 0, '%i ftags in the finv not in the curves: \n    %s'%(
            len(miss_l), miss_l)
        
        
        #set this for later
        self.f_ftags = f_ftags
        
        
        #======================================================================
        # set indexes on data sets
        #======================================================================
        #get list of data sets
        if self.felv == 'datum':
            l = ['finv', 'expos']
        elif self.felv == 'ground':
            l = ['finv', 'expos', 'gels']
        else:
            raise Error('unexpected \'felv\' key %s'%self.felv)
        
        #loop and set
        first = True
        for dname, df in {dname:self.data_d[dname] for dname in l}.items():
            
            #check the indexer is there
            assert cid in df.columns, '%s is missing the speciied index column \'%s\''%(
                dname, cid)
            
            #set the indexer
            df = df.set_index(cid, drop=True).sort_index(axis=0)
            
            #check the indexes match
            if first:
                fdf = df.copy() #set again
                first = False
            else:

                assert np.array_equal(fdf.index, df.index), \
                    '\"%s\' index does not match the finv'%dname
                    
            #update the dict
            self.data_d[dname] = df
        log.debug('finished index check on %i'%len(l))
        
        #======================================================================
        # add gel to the fdf
        #======================================================================
        if self.felv == 'ground':
            assert 'gels' not in fdf.columns, 'gels already on fdf'
            
            gdf = self.data_d['gels']
    
            #check length expectation
            assert len(gdf.columns)==1, 'expected 1 column on gels, got %i'%len(gdf.columns)
    
            
            #rename the column
            gdf = gdf.rename(columns={gdf.columns[0]:'gels'}).round(self.prec)
            
            #do the join join
            fdf = fdf.join(gdf)
            

        
        #update
        self.data_d['finv'] = fdf
        
    def setup_binv(self): # expand finv to  unitary (one curve per row)
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('setup_binv')
        fdf = self.data_d['finv']
        cid, bid = self.cid, self.bid
        
        #======================================================================
        # expand
        #======================================================================

        #get tag column names
        tag_coln_l = fdf.columns[fdf.columns.str.endswith('tag')].tolist()
        
        assert tag_coln_l[0] == 'f0_tag', 'expected first tag column to be \'ftag\''
        
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
                
                assert pboolcol.sum() == 4, 'expects 4 columns w/ prefix %s'%prefix
                
                #get slice and clean
                df = fdf.loc[:, pboolcol].dropna(axis=0, how='all').sort_index(axis=1)
                df.columns = ['fcap', 'felv', 'fscale', 'ftag']
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
            
            log.info('expanded inventory from %i nest sets to finv %s'%(
                len(prefix_l), str(bdf.shape)))
        #======================================================================
        # expand: nothing nested
        #======================================================================
        else:
            bdf = fdf.copy()
            
        #set an indexer columns
        """safer to keep this index as a column also"""
        bdf[bid] = bdf.index
        bdf.index.name=bid
            
        #======================================================================
        # convert asset heights to elevations
        #======================================================================
        if self.felv == 'ground':
            bdf.loc[:, 'felv'] = bdf['felv'] + bdf['gels']
                
            log.info('converted asset ground heights to datum elevations')
            
        #======================================================================
        # get depths (from wsl and elv)
        #======================================================================
        wdf = self.data_d['expos'] #wsl
        
        #pivot these out to bids
        ddf = bdf.loc[:, [bid, cid]].join(wdf.round(self.prec), on=cid
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
        cid = self.cid
        fdf = self.data_d['finv']
        
        miss_l = set(fdf.index.values).symmetric_difference(cres_df.index.values)
        
        assert len(miss_l) == 0, 'result inventory mismatch'
        assert np.array_equal(fdf.index, cres_df.index), 'index mismatch'
        
        
        
        """handle outputs with the dialog.
        for external runs, user can use output method
        #======================================================================
        # output
        #======================================================================
        self.output(cres_df, 'dmg_results')"""

        
        
        log.info('finished')
        
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
            """not sure what to return here"""
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
        for indxr, ftag in enumerate(valid_tags):
            log = logger.getChild('run.%s'%ftag)
            
            #identify these entries
            boolidx = np.logical_and(
                bdf['ftag'] == ftag, #with the right ftag
                vboolidx) #and in the valid set
            
            log.info('(%i/%i) claculting \'%s\' w/ %i assets'%(
                indxr+1, len(valid_tags), ftag, boolidx.sum()))
            
            #==================================================================
            # calc damage by tag.depth
            #==================================================================
            #get these depths
            tddf = ddf.loc[boolidx, :]
            
            deps_ar = pd.Series(np.unique(np.ravel(tddf.loc[:, dboolcol].values))
                                ).dropna().values
            
            #get this DFunc
            dfunc = self.dfuncs_d[ftag]
            
            log.debug('calc for %i (of %i) uniqe depths'%(
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
            
        log = logger.getChild('run')

        
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
        fp = r'C:\LS\03_TOOLS\CanFlood\_ins\prep\cT2\CanFlood_curves_rfda_20200218.xls'
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


            

    
def main_run(wd, cf):
    print('executing')

    _ = DmgModel(par_fp=cf,
                 out_dir=wd,
                 logger=logger).run()
    
    print('finished')
    
    
    
    
    
    
    
    
    
    
    