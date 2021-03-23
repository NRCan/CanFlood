'''
Created on Feb. 7, 2020

@author: cefect

impacts model 2
'''



#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import configparser, os, logging, datetime

"""not sure what happened to the weak references..."""

import pandas as pd
import numpy as np
#import math
idx = pd.IndexSlice
#==============================================================================
# custom imports
#==============================================================================

#mod_logger = logging.getLogger('dmg2') #get the root logger

from hlpr.exceptions import QError as Error

#from hlpr.Q import *
from hlpr.basic import view
#from model.modcom import Model
from hlpr.plot import Plotr
from model.modcom import DFunc, Model

#==============================================================================
# functions----------------------
#==============================================================================
class Dmg2(Model, DFunc, Plotr):
    #==========================================================================
    # #program vars
    #==========================================================================
    valid_par = 'dmg2'
    attrdtag_out = 'attrimat02'
    #datafp_section = 'dmg_fps'
    
    group_cnt = 4
    
    plot_fmt = '${:,.0f}'
    
    #minimum inventory expectations
    finv_exp_d = {
        'tag':{'type':np.object},
        'scale':{'type':np.number},
        'elv':{'type':np.number},
        }
    
    dfuncs_d = dict() #container for damage functions
    mi_meta_d = dict() #container for mitigation threshold counters
    #===========================================================================
    # #expectations from parameter file
    #===========================================================================
    exp_pars_md = {#mandataory: section: {variable: handles} 
        'parameters' :
            {'name':{'type':str}, 
             'cid':{'type':str},
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
        'parameters':{
            'apply_miti':{'type':bool}
            },
        'dmg_fps':{
            'gels':{'ext':('.csv',)},
                    },
        'risk_fps':{
             'evals':{'ext':('.csv',)}, #only required for checks
                    },
                    }

    
    def __init__(self, **kwargs):
        

        
        #init the baseclass
        super().__init__(**kwargs) #initilzie Model
        
        self.dtag_d={**self.dtag_d,**{
            'expos':{'index_col':0},
            'curves':{'sheet_name':None, 'header':None, 'index_col':None}
            }}
        
        
        
        self.logger.debug('finished __init__ on Dmg2')
        
    def prep_model(self):
        #======================================================================
        # setup funcs
        #======================================================================
        self.set_finv()
        
        """evals are optional"""
        if not self.evals == '':
            self.set_evals(check=False) #never pre-loaded
        else:
            self.expcols = pd.Series(dtype=np.object).index
            
        self.set_expos()
    
        #self.data_d['curves'] = pd.read_excel(self.curves, sheet_name=None, header=None, index_col=None)
        
        if self.felv == 'ground':
            self.set_gels()
            self.add_gels()
        

        
        self.build_exp_finv() #build the expanded finv
        self.build_depths()
        
        self.setup_dfuncs(self.raw_d['curves'])
        

        #======================================================================
        # checks
        #======================================================================
        self.check_ftags() #check dfuncs against the finv tags
        
        #======================================================================
        # wrap
        #======================================================================
        
        self.logger.debug('finished setup() on Dmg2')
        
        return 
         
    def setup_dfuncs(self, # build curve workers from loaded xlsx data
                 df_d, #{tab name: raw curve data
                 ):
 
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
        
        if np.nan in ftags_valid:
            raise Error('got some nulls')

        log.debug('loading for %i valid ftags in the finv'%len(ftags_valid))
        #=======================================================================
        # #loop through each frame and build the func
        #=======================================================================
        for tabn, df in df_d.items():
            if tabn.startswith('_'):
                log.debug('skipping dummy tab \'%s\''%tabn)
                continue
            
            tabn = tabn.strip() #remove whitespace
            
            #skip those not in the finv
            if not tabn in ftags_valid:
                log.debug('\'%s\' not in valid list'%tabn)
                continue
            
            if not isinstance(df, pd.DataFrame):
                raise Error('unexpected type on tab \'%s\': %s'%(tabn, type(df)))
            
            #build it
            dfunc = DFunc(tabn, curves_fp=self.curves).build(df, log)
            
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
        # get the impact var
        #=======================================================================
        
        
        #=======================================================================
        # wrap
        #=======================================================================
        
        self.df_minD_d = minDep_d
        
        log.info('finishe building %i curves \n    %s'%(
            len(self.dfuncs_d), list(self.dfuncs_d.keys())))
        
        return
        
        


    def run(self, #main runner fucntion
            set_impactUnits=True, #set impact_units from the dfunc
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        self.feedback.upd_prog(10, method='raw') #add from here
        
        #=======================================================================
        # get impacts-----
        #=======================================================================
        #======================================================================
        # dfunc, scale, and cap per bid
        #======================================================================
        bres_df = self.bdmg_raw()
        self.feedback.upd_prog(5, method='append')
        
        bres_df = self.bdmg_scaled(res_df = bres_df)
        self.feedback.upd_prog(5, method='append')
        
        bres_df = self.bdmg_capped(res_df=bres_df)
        self.feedback.upd_prog(5, method='append')
        
        #=======================================================================
        # mitigations
        #=======================================================================
        res_colg = 'capped' #take the capped values as the final damages
        if self.apply_miti:
            """checking that one of thiese will trip in load_finv()"""
            #lower depth threshold
            if self.miLtcn in self.finv_cdf.columns:
                bres_df, res_colg = self.bdmg_mitiT(res_df = bres_df, res_colg=res_colg)
                self.feedback.upd_prog(5, method='append')
            
            #intermediate scale
            if self.miScn in self.finv_cdf.columns:
                bres_df, res_colg = self.bdmg_mitiS(res_df = bres_df, res_colg=res_colg)
                self.feedback.upd_prog(5, method='append')
            
            #intermediate value
            if self.miVcn in self.finv_cdf.columns:
                bres_df, res_colg = self.bdmg_mitiV(res_df = bres_df, res_colg=res_colg)
                self.feedback.upd_prog(5, method='append')

            #force positives
            """ mitigation vaslue shifts bdmg_mitiS() especially can lead to negative values"""
            booldf = bres_df <0 #find negatives
            if booldf.any().any():
                log.warning('mitigation handles got %i (of %i) negative values... replacing with zeros'%(
                    booldf.sum().sum(), booldf.size))
                
                bres_df = bres_df.where(~booldf,
                        pd.DataFrame(0, index=bres_df.index, columns=bres_df.columns))
        #=======================================================================
        # finalize damages
        #=======================================================================
        """attaches cres_df to self"""
        bres_df, cres_df = self.bdmg_cleaned(res_df=bres_df, res_colg=res_colg)
        self.feedback.upd_prog(70, method='raw')
        
        #=======================================================================
        # wrap----
        #=======================================================================
        #=======================================================================
        # get labels
        #=======================================================================
        if set_impactUnits:
            """
            if user wants to use the value in the c ontrol file.. pass set_impactUnits=False
            otherwise we attempt to read from control file
            
            both should default to the modcom.Model.impact_units=impacts
            """
            try:
                dFunc_iu = self.get_DF_att(attn='impact_units')
                if not dFunc_iu == '' or dFunc_iu is None:
                    self.impact_units = dFunc_iu
            except Exception as e:
                log.warning('failed to set \'impact_units\' w/ %s'%e)
                
        #for plotting
        #=======================================================================
        # report
        #=======================================================================
        log.debug('maxes:\n%s'%(
            cres_df.max()))
        
        log.info('finished w/ %s and TtlDmg = %.2f'%(
            str(cres_df.shape), cres_df.sum().sum()))
        
        self.feedback.upd_prog(80, method='raw')
        
        return cres_df
    

    def bdmg_raw(self, #get damages on expanded finv
             
            bdf = None, #expanded finv. see modcom.build_exp_finv(). each row has 1 ftag
            ddf = None,  #expanded exposure set. depth at each bid. see build_depths() or get_mitid()
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('bdmg')
        #defaults
        if ddf is None: ddf = self.ddf
        if bdf is None: bdf = self.bdf
  

        """ddf is appending _1 to column names"""
        cid, bid = self.cid, self.bid
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert len(self.dfuncs_d)>0
        assert bid in ddf.columns
        assert ddf.index.name == bid
        assert np.array_equal(ddf.index.values, ddf[bid].values)
        
        #identifier for depth columns
        dboolcol = ~ddf.columns.isin([cid, bid])
        
        log.debug('running on %i assets and %i events'%(len(bdf), len(ddf.columns)-2))
        

        #======================================================================
        # adjust depths by exposure grade
        #======================================================================
        """
        see get_mitid()
        """
        #======================================================================
        # setup-----
        #======================================================================
        edf = ddf.loc[:, dboolcol] #just the exposure values
        
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
        self.events_df = events_df #set for later
        #=======================================================================
        # id valid bids
        #=======================================================================
        if self.ground_water:
            mdval = min(self.df_minD_d.values())
        else:
            mdval = 0
        
        """this marks nulls as False"""
        dep_booldf = edf >= mdval #True= depth is valid
        
        #report those faling the check
        if not dep_booldf.all().all():
            log.debug('marked %i (of %i) entries w/ excluded depths (<= %.2f or NULL)'%(
                np.invert(dep_booldf).sum().sum(), dep_booldf.size, mdval))
        
        #check if EVERYTHING failed
        if not dep_booldf.any().any():
            log.warning('ZERO (of %i) exposures exceed the minimum threshold (%.2f)! returning all zeros'%(
                dep_booldf.size, mdval))
            
            self.res_df = pd.DataFrame(0, index=edf.index, columns= ['%s_raw'%e for e in edf.columns])
            
            return self.res_df
            
            
        

        
        #======================================================================
        # RAW: loop and calc raw damage by ftag-------------
        #======================================================================

        res_df = None
        
        for indxr, (ftag, dfunc) in enumerate(self.dfuncs_d.items()):
            log = self.logger.getChild('bdmg.%s'%ftag)
                       
            #entries matching this tag
            tag_booldf = pd.DataFrame(np.tile(bdf['ftag']==ftag, (len(dep_booldf.columns),1)).T,
                                   index=dep_booldf.index, columns=dep_booldf.columns)
            
            booldf = np.logical_and(
                dep_booldf, #entries w/ valid depths
                tag_booldf #entries matching this tag
                )
            
            log.info('(%i/%i) calculating \'%s\' w/ %i un-nested assets (of %i)'%(
                indxr+1, len(self.dfuncs_d), ftag, 
                booldf.any(axis=1).sum(), len(booldf)))
            
            if not booldf.any().any():
                log.debug('    no valid entries!')
                continue
            #==================================================================
            # calc damage by tag.depth
            #==================================================================
            """
            to improve performance,
                we only calculate each depth once, then join back to the results
                
            todo: add check for max depth to improve performance
            """
            
            #get just the unique depths that need calculating
            deps_ar = pd.Series(np.unique(np.ravel(edf[booldf].values))
                                ).dropna().values
            
            log.debug('calc for %i (of %i) unique depths'%(
                len(deps_ar), edf.size))
            
            """multi-threading would nice for this loop"""
            
            #loop each depth through the damage function to get the result                
            e_impacts_d = {dep:dfunc.get_dmg(dep) for dep in deps_ar}
            
            #===================================================================
            # link
            #===================================================================

            ri_df = edf[booldf].replace(e_impacts_d)
            
            # update master=
            if res_df is None:
                res_df = ri_df
            else:
                res_df.update(ri_df, overwrite=False, errors='raise')
                
            
         
        #=======================================================================
        # wrap-------
        #=======================================================================
        log = self.logger.getChild('bdmg')
        assert not res_df is None, 'failed to get any valid entries'
        res_df.columns = ['%s_raw'%e for e in res_df.columns] #add the suffix
        
        #attach
        self.res_df = res_df
        
        
        
        log.info('got raw impacts for %i dfuncs and %i events: \n    %s'%(
            len(self.dfuncs_d),dboolcol.sum(), self._rdf_smry('_raw')))
        
        return res_df
    
    def bdmg_scaled(self,
                    res_df = None,
                    ):
        log = self.logger.getChild('bdmg_scaled')
        #=======================================================================
        # get data
        #=======================================================================
        if res_df is None: res_df = self.res_df
        events_df = self.events_df
        
        bdf = self.bdf
        #=======================================================================
        # #loop and add scaled damages
        #=======================================================================
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
                res_df[e_ser['scaled']] = res_df.loc[:, boolcol].multiply(bdf['fscale'], axis=0)
            except Exception as e:
                raise Error('failed w/ \n    %s'%e)
                
        #=======================================================================
        # wrap
        #=======================================================================
        self.res_df = res_df
        log.info('got scaled impacts: \n    %s'%(self._rdf_smry('_scaled')))
        return res_df
        
        
    def bdmg_capped(self, #apply the  optional 'fcap' values to the scaled damages
                    res_df = None,
                    ):
        
        """
        bdf can ber passed w/o fcap
            shouldn't be passed w/ all nulls... but this would still wortk I thihnk
        """
        
        log = self.logger.getChild('bdmg_capped')
        #=======================================================================
        # get data
        #=======================================================================
        if res_df is None: res_df = self.res_df
        events_df = self.events_df
        
        bdf = self.bdf
        cid, bid = self.cid, self.bid

        #=======================================================================
        # start meta
        #=======================================================================
        meta_d = dict()
        cmeta_df =bdf.loc[:,bdf.columns.isin([cid, bid, 'ftag', 'fcap', 'fscale', 'nestID'])]

        #=======================================================================
        # #loop and add scaled damages
        #=======================================================================

        for event, e_ser in events_df.iterrows():
            
            #join scaled values and cap values for easy comparison
            if 'fcap' in bdf.columns:
                sc_df = res_df[e_ser['scaled']].to_frame().join(bdf['fcap'])
            else:
                sc_df = res_df[e_ser['scaled']].to_frame()
            
            #identify nulls
            boolidx = res_df[e_ser['scaled']].notna()
            
            #calc and set the scalecd values
            """this will ignore any null fcap values when determining theminimum"""
            res_df.loc[boolidx, e_ser['capped']] = sc_df[boolidx].min(axis=1, skipna=True)
            
 
            #===================================================================
            # #meta
            #===================================================================
            
            #where the scaled values were capped
            if 'fcap' in bdf.columns:
                mser = res_df.loc[boolidx, e_ser['scaled']] >bdf.loc[boolidx, 'fcap'] 
            else:
                #all FALSE
                mser = pd.Series(index=cmeta_df.index, dtype=bool)
                
            cmeta_df= cmeta_df.join(mser.rename(event), how='left')
            
            #totals
            meta_d[event] = mser.sum()
                
        #=======================================================================
        # wrap
        #=======================================================================
        """written by bdmg_smry"""
        """
        view(cmeta_df)
        """
        self.cmeta_df = cmeta_df
        self.res_colg = 'capped' #needed by  mitigation funcs
        
        
        self.res_df = res_df
        log.info('cappd %i events w/ bid cnts maxing out (of %i) \n    %s\n    %s'%(
            len(meta_d), len(res_df), meta_d, self._rdf_smry('_capped')))

        return res_df
    

    def bdmg_mitiT(self, #apply mitigation thresholds
                   res_df = None,

                  res_colg = None, #predecessor results column group to work off

                  ):
        """
        TODO: consider moving to common for Risk1
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('bdmg_mitiT')
        
        #column names
        cid, bid = self.cid, self.bid
        if res_colg is None: res_colg=self.res_colg
        mcoln = self.miLtcn #mitigation data columns 
        
        #datasets

        if res_df is None: res_df = self.res_df

        
        #=======================================================================
        # setup results
        #=======================================================================
        events_df, rdf_raw = self._mi_resSetup(res_df, mcoln, res_colg)

        #=======================================================================
        # retrieve expanded threshold data
        #=======================================================================
        ddf, dt_df = self._get_fexpnd(mcoln)

        
        #=======================================================================
        # apply threshold
        #=======================================================================
        
        #find those meeting the threshold
        booldf = ddf >=dt_df
        
        #raw results, with those not meeting the threshold as 0
        rdf = rdf_raw.where(booldf, other=0.0)
        
        #retireve the nulls
        """
        user 0.0 as the threshold force.. but preserving nulls
        """
        rdf = rdf.where(rdf_raw.notna(), other=np.nan)
        
        #=======================================================================
        # wrap
        #=======================================================================
        return self._mi_wrap(rdf, events_df, mcoln, booldf, log)
    

        
        
    
    def bdmg_mitiS(self, #apply mitigation scale values
                   res_df = None,
 
                  res_colg = None, #predecessor results column group to work off

                  ):
        """
        TODO: consider moving to common for Risk1
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('bdmg_mitiT')
        
        #column names
        if res_colg is None: res_colg=self.res_colg
        mcoln = self.miScn #mitigation data columns 
        
        #datasets
        
        if res_df is None: res_df = self.res_df
        bdf = self.bdf
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert bdf[mcoln].notna().any(), 'got all nulls for %s'%mcoln

        #=======================================================================
        # setup results
        #=======================================================================
        events_df, rdf_raw = self._mi_resSetup(res_df, mcoln, res_colg)
        
        
        #=======================================================================
        # retrieve data
        #=======================================================================
        ddf, dt_df = self._get_fexpnd(self.miUtcn,logger=log)
        
        #get scale data
        
        
        #=======================================================================
        # apply scales to threshold
        #=======================================================================
        #find those we want to apply teh scale to
        booldf = np.logical_and(
            ddf<=dt_df, #exposure less than threshold
            np.logical_and( #nether set is null
                ddf.notna(),
                dt_df.notna())
                )
        
        if not booldf.any().any():
            log.warning('got no entries to apply %s to!'%mcoln)
            return res_df, res_colg
        
        #get scaled results
        scale_ser = bdf[mcoln].fillna(1.0) #replace nulls
        rdf_S = rdf_raw.multiply(scale_ser, axis=0)
        
        #take scaled where selected... otherwise use the raw
        rdf = rdf_S.where(booldf, other=rdf_raw)
        
        return self._mi_wrap(rdf, events_df, mcoln, booldf, log)
        
        


    def bdmg_mitiV(self, #apply mitigation scale values
                   res_df = None,
 
                  res_colg = None, #predecessor results column group to work off

                  ):
        """
        consider moving to common for Risk1
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('bdmg_mitiT')
        
        #column names
        if res_colg is None: res_colg=self.res_colg
        mcoln = self.miVcn #mitigation data columns 
        
        #datasets
        
        if res_df is None: res_df = self.res_df
        bdf = self.bdf
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert bdf[mcoln].notna().any(), 'got all nulls for %s'%mcoln

        #=======================================================================
        # setup results
        #=======================================================================
        events_df, rdf_raw = self._mi_resSetup(res_df, mcoln, res_colg)
        
        
        #=======================================================================
        # retrieve data
        #=======================================================================
        ddf, dt_df = self._get_fexpnd(self.miUtcn,logger=log)
        
        #get scale data
        
        
        #=======================================================================
        # apply scales to threshold
        #=======================================================================
        #find those we want to apply teh scale to
        booldf = np.logical_and(
            ddf<=dt_df, #exposure less than threshold
            np.logical_and( #nether set is null
                ddf.notna(),
                dt_df.notna())
                )
        
        if not booldf.any().any():
            log.warning('got no entries to apply %s to!'%mcoln)
            return res_df, res_colg
        
        #get scaled results
        mser = bdf[mcoln].fillna(0) #replace nulls
        rdf_S = rdf_raw.add(mser, axis=0)
        
        #take new where selected... otherwise use the raw
        rdf = rdf_S.where(booldf, other=rdf_raw)
        
        return self._mi_wrap(rdf, events_df, mcoln, booldf, log)
    


    def _rdf_smry(self, #get a summary string of the bid results data
                          
                          sfx,
                          df_raw = None,
                          ):
        
        if df_raw is None: df_raw = self.res_df
        
        boolcol = df_raw.columns.str.endswith(sfx) #id these columns
        assert boolcol.any(), sfx
        df = df_raw.loc[:, boolcol] #get just this data
        
        return 'count = %i, nulls = %i, min = %.2f, mean = %.2f, max = %.2f %s'%(
            df.size, df.isna().sum().sum(), df.min().min(), df.mean().mean(), df.max().max(),
            self.impact_units 
            )
        
    def _mi_resSetup(self, 
                     res_df, mcoln, res_colg):
        
        events_df = self.events_df
        
        #=======================================================================
        # precheck
        #=======================================================================
        #check the results data
        assert res_colg in events_df.columns
        miss_l = set(events_df[res_colg].values).difference(res_df.columns)
        assert len(miss_l)==0, 'missing results columns: %s'%miss_l
        
        #=======================================================================
        # setup data
        #=======================================================================
        events_df[mcoln] = events_df.index + '_%s'%mcoln #update events metadata
        
        #raw results with names matching the events 
        rdf_raw = res_df.loc[:, events_df[res_colg]].rename(
            columns={v:k for k,v in events_df[res_colg].to_dict().items()})
        
        return events_df, rdf_raw
    
    def _mi_wrap(self, #wrapper function for mitigation series 
                 rdf, events_df, mcoln, booldf, log):
        

        #join these back onto the main results (and rename columns)
        self.res_df = self.res_df.join(rdf.rename(
            columns=events_df[mcoln].to_dict())) 

        self.res_colg=mcoln #set for next
        
        
        self.mi_meta_d[mcoln] = pd.Series(booldf.sum(axis=0), name='miti_hit_cnt')
        #=======================================================================
        # report
        #=======================================================================
        log.info('got %i (of %i) below \'%s\': \n    %s \n    %s'%(
            booldf.sum().sum(), booldf.size, mcoln, booldf.sum(axis=0).to_dict(),
            self._rdf_smry(mcoln)))

        return self.res_df, mcoln
        
        
         
    def bdmg_cleaned(self, #fill nulls and build some results versions
                     res_colg = 'capped', #column group to take as final results
                    res_df = None,
                    ):
        
        log = self.logger.getChild('bdmg_cleaned')
        #=======================================================================
        # get data
        #=======================================================================
        if res_df is None: res_df = self.res_df
        events_df = self.events_df
        
        bdf = self.bdf
        cid, bid = self.cid, self.bid
        fdf = self.data_d['finv']
        
        
        #=======================================================================
        # duplicate onto cleaned columns and fill nulls
        #=======================================================================
        for event, e_ser in self.events_df.iterrows():
            boolcol = res_df.columns == e_ser[res_colg]
            res_df[e_ser['dmg']] = res_df.loc[:, boolcol].fillna(0)
            
      
        
        #=======================================================================
        # join some other data
        #=======================================================================
        assert np.array_equal(res_df.index, bdf.index), 'index mismatch'
        #join some info from the bdf (for later functions)
        res_df = bdf.loc[:, [bid, cid, 'nestID']].join(res_df) 


        #=======================================================================
        # get cleaned version----
        #=======================================================================
        resC_df = res_df.loc[:, [bid, cid]+events_df['dmg'].tolist()] #just the dmg values
        
        #drop _dmg suffix
        resC_df = resC_df.rename(columns={v:k for k,v in events_df['dmg'].to_dict().items()})
        
        #=======================================================================
        # checks
        #=======================================================================
        
        assert resC_df.notna().all().all(), 'got some nulls'
        
        #=======================================================================
        # # recast as cid----
        #=======================================================================
        cres_df = resC_df.groupby(cid).sum().drop(bid, axis=1)
        
        log.info('got damages for %i events and %i assets'%(
            len(cres_df), len(cres_df.columns)))
        
        
        #======================================================================
        # checks
        #======================================================================
        
        miss_l = set(fdf.index.values).symmetric_difference(cres_df.index.values)
        
        assert len(miss_l) == 0, 'result inventory mismatch: \n    %s'%miss_l
        assert np.array_equal(fdf.index, cres_df.index), 'index mismatch'
        
        #=======================================================================
        # sort cres
        #=======================================================================
        
        

        #=======================================================================
        # wrap
        #=======================================================================
        """
        view(resC_df.round(self.prec))
        """

        #raw damages by bid
        """output by output_bdmg()"""
        self.res_df = res_df 
        
        #total damages by bid
        """doesnt look like this isoutput anywhere"""
        self.bdmgC_df = resC_df.round(self.prec) 
        
        #total damages by cid
        """written by output_cdmg()
        sent to control file as 'dmgs' in update_cf()"""
        self.cres_df = cres_df.loc[:, cres_df.sum(axis=0).sort_values(ascending=True).index] #set for plotting
        
        
        log.info('got cleaned impacts: \n    %s'%(self._rdf_smry('_dmg')))

        return self.bdmgC_df, self.cres_df
    
    
    def bdmg_smry(self, #generate summary of damages
                  res_df_raw=None,  #built results
                  events_df=None,  #event name matrix
                  cmeta_df=None, #cap by asset
                  gCn = 'ftag', #column name to group on
                  
                  
                  logger=None,
                  
                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if res_df_raw is None: res_df_raw=self.res_df.copy()
        if events_df is None: events_df=self.events_df
        if cmeta_df is None: cmeta_df=self.cmeta_df
        if logger is None: logger=self.logger
        
        bdf = self.bdf
        #cid = self.cid
        
        log=logger.getChild('bdmg_smry')
        

        #=======================================================================
        # precheck
        #=======================================================================
        assert gCn in bdf.columns, gCn
        #rename conversion
        
        #=======================================================================
        # add some common cols
        #=======================================================================
        res_df = res_df_raw.join(bdf.loc[:,[gCn]])
        
        #=======================================================================
        # impact meta for each result type
        #=======================================================================
        #move the 'dmg' colum to the end
        if not events_df.columns[-1]=='dmg':
            cols = events_df.columns.tolist()
            cols.remove('dmg')
            events_df = events_df.loc[:, cols + ['dmg']]
        
        
        res_d = dict() #container for meta
        for rtName, rser in events_df.items():
            
            #slice to results columns of this type
            rdf = res_df.loc[:, rser.values.tolist()+[gCn]]
            
            #group and get totals per dfunc
            rnm_d= dict(zip(rser.to_dict().values(), rser.to_dict().keys()))
            mdf =  rdf.dropna(how='all').groupby(gCn).sum().rename( columns=rnm_d)
            
            #mitigation threshold counters
            if rtName in self.mi_meta_d:
                mdf = mdf.append(self.mi_meta_d[rtName])
            
            #add count columns
            """
            groupBy needs a dummy column for count()
            """
            mdf['cnt'] = rdf.loc[:, gCn].to_frame().reset_index(drop=False).groupby(gCn).count()
            
            res_d[rtName] = mdf
            

        #=======================================================================
        # cap counts
        #=======================================================================
        df = cmeta_df.drop(['fcap', 'fscale', self.cid, self.bid], axis=1, errors='ignore').fillna(False)
        cm_df1  = df.groupby(gCn).sum().astype(np.int) #count all the trues
        

        #=======================================================================
        # progression summary
        #=======================================================================

        p_df = None
        for coln, cser in events_df.items():
            rser = res_df.loc[:, cser.values].sum(axis=0)
            rdf1 = pd.Series(rser, name=coln).to_frame().T.rename(
                columns = {v:k for k,v in cser.items()})
            if p_df is None:
                p_df = rdf1
            else:
                p_df = p_df.append(rdf1)

        #=======================================================================
        # write results
        #=======================================================================
        
        out_fp = os.path.join(self.out_dir, 'dmg2_smry_%s_%s_%i.xls'%(self.tag, gCn, len(res_df)))
        
        d = {
            '_smry':p_df.round(self.prec),
            **res_d, 
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
                  maxStr_len = 11, #maximum string length for truncating event names
                  dfmt=None,
                  
                  linkSrch_d = {'top':'simu', 'bot':'fail'}, #how to separate data
                  gCn = 'ftag', #group column (for title)
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
        
        fig.suptitle('%s_%s_%s Damage pies on %i'%(self.name, self.tag, gCn, len(df.columns)),
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
                    dser, 
                    #labels=dser.values, 
                       autopct='%1.1f%%',
                       #autopct=lambda pct: func(pct, dser),
                       )
                
                #===============================================================
                # #fix labels
                # for e in texts:
                #     ov = e.get_text()
                #     e.set_text(dfmt.format(float(ov)))
                #===============================================================
                
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

        fig.legend(wedges, df.index.values, loc='center')
        
        
        fig.tight_layout()
        log.info('built pies')
        
        
        return fig
    
    def get_attribution(self, #build the attreibution matrix
                        cres_df, # asset totals (asset:eventRaster:impact)
                        bdmg_df=None, # nested impacts (bid:eventRaster:impact)
                        events_df=None,  #keys to bdmg_df column
                        grpColn = 'nestID', #column name (in bdmg_df) to group on
                        logger=None):

        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        
        """
        even though we're called explicitly...
            adding the check for consistency
        """
        assert self.attriMode
        
        log = logger.getChild('get_attribution')
        cid = self.cid
        
        if bdmg_df is None: bdmg_df=self.res_df.copy()
        if events_df is None: events_df = self.events_df.copy()
        
        #=======================================================================
        # check data
        #=======================================================================
        assert cid in bdmg_df.columns
        assert grpColn in bdmg_df.columns
        
        #check asset cids
        miss_l = set(bdmg_df[cid]).symmetric_difference(cres_df.index)
        assert len(miss_l)==0, 'key mismatch'
        

        
        #=======================================================================
        # clean bdmg
        #=======================================================================
        #get conversion d {oldName:newName}
        d1 = pd.Series(events_df['dmg'].index, index=events_df['dmg']).to_dict()
        
        #get just the columsn of interest (and drop the _dmg sufix)
        boolcol = bdmg_df.columns.isin([cid, grpColn]+ list(d1.keys()))
        bdf = bdmg_df.loc[:, boolcol].rename(columns=d1) 
        
        #=======================================================================
        # check data2
        #=======================================================================
        #check eventRasters
        miss_l = set(cres_df.columns).difference(bdf.columns)
        assert len(miss_l)==0, 'event rastesr mismatch'

        
        #=======================================================================
        # get pivot
        #=======================================================================
        #cid: dxcol(l1:eventName, l2:nestID)
        bdmg_dxcol = bdf.pivot(
            index=cid, columns=grpColn, values=cres_df.columns.to_list())
        
        #set new level names
        bdmg_dxcol.columns.set_names(['rEventName', grpColn], inplace=True)
        
        
        
        #=======================================================================
        # calc attribution
        #=======================================================================
        assert np.array_equal(cres_df.index, bdmg_dxcol.index), ' index mismatch'
        
        #divide bdmg entries by total results values (for each level)
        """ for asset, revents, nestID couples with zero impact, will get null
        leaving these so the summation validation still works"""
        atr_dxcol_raw = bdmg_dxcol.divide(cres_df, axis='columns', level='rEventName')
        

        log.debug('built raw attriM w/ %i (of %i) nulls'%(
            atr_dxcol_raw.isna().sum().sum(), atr_dxcol_raw.size))

        
        #=======================================================================
        # handle nulls----
        #=======================================================================
        atr_dxcol = self._attriM_nulls(cres_df, atr_dxcol_raw, logger=log)

        
        #=======================================================================
        # wrap
        #=======================================================================
        
        
        #set for writing
        self.att_df = atr_dxcol.copy()
        log.info('finished w/ %s'%str(atr_dxcol.shape))
        return atr_dxcol
        
    def get_DF_att(self, #get an attribute across all the dfuncs
                       logger=None,
                       attn = 'impact_units'
                       ):
        if logger is None: logger=self.logger
        log = logger.getChild('get_DF_att')
        
        d = self.dfuncs_d
        
        log.debug('on %i dfuncs'%len(d))
        
        attv_d = {k:getattr(w, attn).strip() for k,w in d.items() }
        
        attv_s = set(attv_d.values())
        
        attv = list(attv_s)[0]
        if not len(attv_s)==1:
            
            log.warning('got %i \'%s\' (from %i DFuncs), taking first: %s'%(
                len(attv_s), attn, len(d), attv))
            
        log.debug('got \'%s\' = \'%s\''%(attn, attv))
        
        return attv
    
    #===========================================================================
    # VALIDATORS----
    #===========================================================================
    def check_ftags(self): #check fx_tag values against loaded dfuncs
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
        
    def check(self,
              df=None,
              logger=None,
              ):
        #=======================================================================
        # defaults
        #=======================================================================
        if df is None: df = self.cres_df.copy()
        if logger is None: logger=self.logger
        log = logger.getChild('check')
        
        #=======================================================================
        # check xis:exposure results dataset
        #=======================================================================
        """
        similar to check_eDmg() but without the aep logic
        
        """
        
        #=======================================================================
        # #check everything is positive
        #=======================================================================
        booldf = df>=0
        if not booldf.all().all():
            log.debug(df[booldf])
            raise Error('got %i (of %i) negative values... see logger'%(
                np.invert(booldf).sum().sum(), booldf.size))
        
        

    #===========================================================================
    # OUTPUTRS-------------
    #===========================================================================
    def update_cf(self, #update the control file 
               out_fp = None,
               cf_fp = None,
               ):
        #======================================================================
        # set defaults
        #======================================================================
        if out_fp is None: out_fp = self.out_fp
        if cf_fp is None: cf_fp = self.cf_fp
        
        #=======================================================================
        # convert to relative
        #=======================================================================
        if not self.absolute_fp:
            out_fp = os.path.split(out_fp)[1]
        
        return self.set_cf_pars(
            {
            'parameters':(
                {'impact_units':self.impact_units},
                ),
            
            'risk_fps':(
                {'dmgs':out_fp}, 
                '#\'dmgs\' file path set from dmg2.py at %s'%(
                    datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                ),
            'validation':({'risk2':'True'},)
             },
            cf_fp = cf_fp
            )
    
    def output_cdmg(self,
                    ofn=None):
        
        
        
        if ofn is None:
            ofn = 'dmgs_%s_%s'%(self.name, self.tag)
        
        """
        view(self.res_df)
        """
        #store for upd_cf
        self.out_fp = self.output_df(self.cres_df, ofn, write_index=True)
            
        return self.out_fp
    
    
    def output_bdmg(self, #short cut for saving the expanded reuslts
                    ofn = None):
        if ofn is None:
            ofn = 'dmgs_expnd_%s_%s_%i_%i'%(self.name, self.tag, len(self.events_df), len(self.res_df))
        
        """
        view(self.res_df)
        
        """
        #get just the useful stuff off the expanded finv
        l = set(self.bdf.columns).difference(self.res_df.columns)
        bdf1 = self.bdf.loc[:, l]
        bdf1.index.name = None
                             
        rdf = self.res_df.drop(self.bid, axis=1).join(bdf1)
        rdf.index.name = self.bid
            
        return self.output_df(rdf, ofn, write_index=True)
    
    def output_depths_df(self,
                         ofn = None):
        
        if ofn is None: 
            ofn = 'depths_%s_%s_%i_%i'%(self.name, self.tag, len(self.events_df), len(self.ddf))
        
        return self.output_df(self.ddf, ofn, write_index=False)
    
    #===========================================================================
    # PLOTRS------
    #===========================================================================
    def _set_valstr(self, df):
        self.val_str = 'asset count=%i \napply_miti=%s \nground_water=%s \nfelv=\'%s\' \ndate= %s'%(
            len(df), self.apply_miti, self.ground_water, self.felv, self.today_str)
        
    def plot_boxes(self, #box plots for each event 
                   df=None, 
                      
                    #labelling
                    impact_name = None, 

                    #figure parametrs
                     plotTag=None,        
                    
                    **kwargs
                      ): 

        if impact_name is None: impact_name=self.impact_units
        if plotTag is None: plotTag=self.tag
        if df is None: 
            df = self.cres_df.replace({0.0:np.nan})

        title = '%s %s dmg2.Impact Boxplots on %i Events'%(plotTag, self.name, len(df.columns))
        self._set_valstr(df) 

        return self.plot_impact_boxes(df,
                      title=title, xlab = 'hazard event raster', ylab = impact_name,
                       val_str=self.val_str, **kwargs)
            
    def plot_hist(self, #box plots for each event 
                   df=None, 
                      
                    #labelling
                    impact_name = None, 

                    #figure parametrs
                     plotTag=None,        
                    
                    **kwargs
                      ): 

        if impact_name is None: impact_name=self.impact_units
        if plotTag is None: plotTag=self.tag
        if df is None: df = self.cres_df.replace({0.0:np.nan})

        title = '%s %s dmg2.Impact Histograms on %i Events'%(plotTag, self.name, len(df.columns))
        self._set_valstr(df) 
        return self.plot_impact_hist(df,
                      title=title, xlab = impact_name,
                       val_str=self.val_str, **kwargs)
            
        
                   


    
    