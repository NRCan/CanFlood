'''
Created on Feb. 14, 2021

@author: cefect

2021-04-20: I think this is obsolete now... see wFlow

CanFlood asset groups build, model, results batch runs.




linking together the following workflows via python scripts:
        tools (build, model, cresults)
        assetModels (e.g., residential, NRP, infrastrdutrue)
        sceanrios (e.g., climate change, baseline) 
            NOTE: minimal support for scenarios... need to run each separately still
                just providing logical naming and output handling
        
    no GUI planned for this
    
call the CFbatch object from your projects script, passing all the parameters and filepaths
    to facilitate individual tool runs, and linked runs, batch runs are controlled w/ 2 files
        
        batch_control.csv: 
            updated after each toolbox run. 
            flags for which assetmodels should run under which toolbox
            has some results summary, timestamps, and filepaths
            iniitally created after the buildToolbox run when start_lib =True
        
        batch BUILD control.xls
            created by user to control the build toolbox and parameters for each assetModel
            on first run, 'start_lib' should be set to TRUE to set the batch_contro.csv
        
'''
#===============================================================================
# imports-------------
#===============================================================================
#===============================================================================
# python basics
#===============================================================================
import os, datetime
import pandas as pd
import numpy as np

#today_str = datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')

#===============================================================================
# Qgis
#===============================================================================
from qgis.core import QgsCoordinateReferenceSystem

#===============================================================================
# CanFlood generals
#===============================================================================
from hlpr.basic import view
from hlpr.exceptions import Error

from hlpr.logr import basic_logger
mod_logger = basic_logger() 

from runComs import Runner

#===============================================================================
# definitiions-------
#===============================================================================

class CFbatch(Runner): #handerl of batch CanFlood runs (build, model, results)
    

    #===========================================================================
    # program vars---------
    #===========================================================================

    meta_d = dict() #summary counter for reporting
    #===========================================================================
    # #run handles per tool
    #===========================================================================
    """WARNING! these are handles for the batch HANDLES (not the data)
    key order is important here for run_all()"""
    hndl_lib = {
        'build':
            {
                'finv_fn':{'type':np.object},
                'cid':{'type':np.object},
                'modelType':{'type':np.object, 'values':['L1', 'L2']},
                'as_inun':{'type':bool},
                'felv':{'type':np.object},
                'dthresh':{'type':float},
                'Levent_rels':{'type':np.object},
                'event_rels':{'type':np.object},
                'rtail':{'type':np.object},
                'prec':{'type':int},
                'impact_units':{'type':np.object},
                'impactfmt_str':{'type':np.object},
                'curves_fn':{'type':np.object}
                },
        'dmg2':{
                'cf_fp':{'type':np.object}
                },
        
        'risk2':{
            'cf_fp':{'type':np.object}
            },
        'risk1':{
            'cf_fp':{'type':np.object}
            },
        'djoin':{
            'cf_fp':{'type':np.object},
            'finv_fp':{'type':np.object},
            },
        'compare':{
            'cf_fp':{'type':np.object},
            }
        
        }
    
    #===========================================================================
    # #flow controls per tool
    #===========================================================================
    #column name to set in control file for next toolboox
    nbcoln_d = {  #
        'build':'dmg2', #uses set_mixed_controls() for sophisticated flow control
        'risk1':'results',
        'risk2':'results',
        'dmg2':'risk2'
        }
    
    #column name to use for your flow control (default is to use your own toolname
    bcoln_d = {
        'djoin':'results',
        'compare':'results',
        }
    
    


            
    def __init__(self,
                 #project tool parameters
                 pars_d, # parameters for this scenario (all tools and assetModels) {parameter: value}. 
                    #each tool run has expectations
                    #run_build() needs a second dict for unique assetModel pars
                 
                 #run controls
                 start_lib=False, #whether to start the csv data from the xlss

                 
                 #file pahts
                 control_fp = None, #optional path to batch control file

                 
                 **kwargs #for standard attributes
                 ):

        super().__init__(pars_d,**kwargs)
        #=======================================================================
        # #attachments
        #=======================================================================
        self.start_lib=start_lib

       
        #=======================================================================
        # control file paths
        #=======================================================================
        if control_fp is None:
            control_fp = os.path.join(self.out_dir, 
                          'cf_batchAssetControl_%s_%s.csv'%(self.projName, self.scenarioName))
            
        self.control_fp = control_fp
        

            
        self.logger.info('CFbatch __init__ finished')
        
    


    #===========================================================================
    # PARAMETER LOADING ---------
    #===========================================================================
    def load_buildControl(self,
                     fp, #headers on row 2
                     sheet_name='finv',
                     header=1, #default is to ignore the first line
                     ):
        #=======================================================================
        # defaults
        #=======================================================================
        #if fp is None: fp=self.buildControl_fp
        self.buildControl_fp = fp #reset

        hcolns = list(self.hndl_lib['build'].keys())
        #=======================================================================
        # load
        #=======================================================================
        df_raw = pd.read_excel(fp, sheet_name=sheet_name, index_col=None, header=header)
        
        #=======================================================================
        # precheck
        #=======================================================================
        miss_l = set(hcolns + ['tag']).difference(df_raw.columns)
        assert len(miss_l)==0, 'BuildControl \'%s\' file mising %i columns \n    %s \n check header row number?'%(
            os.path.basename(fp), len(miss_l), miss_l)
        #=======================================================================
        # #clean---------
        #=======================================================================
        df = df_raw.dropna(subset=['tag'], axis=0, how='any').copy()
        

            
        #=======================================================================
        # trim
        #=======================================================================
        df.loc[:, 'include'] = df['include'].astype(bool)
        #first drop
        df = df.loc[df['include'], :].set_index('tag', drop=True)
        

        #get just these columns
        #df1= df.loc[:, df.columns.isin(['tag'] +hcolns + self.fcolns)]
        
        #=======================================================================
        # wrap
        #=======================================================================
        self.bCntrl_df = df.infer_objects()
        if self.start_lib:
            """this will voerwrite the csv"""
            self.pars_df = df.loc[:, df.columns.isin(hcolns)] #only for first build
        #self.control_df = df1.copy() #for outputting
        
        return self.bCntrl_df
    
    def load_control(self,
                 fp=None,
                 ):
        if fp is None: fp = self.control_fp
        assert isinstance(fp, str)
 
        
        df_raw = pd.read_csv(fp, index_col=0)
        assert len(df_raw)>0, 'loaded empty batch control file'
        assert 'cf_fp' in df_raw.columns, 'missing cf_fp'
        
        """when the build routine slices out all features... no cf_fp will write"""
        df = df_raw.dropna(subset=['cf_fp'], axis=0)
        
        #=======================================================================
        # for coln in self.fcolns:
        #     if not coln in df.columns: continue
        #     df.loc[:, coln]  = df[coln].astype(bool)
        #=======================================================================
        
        self.pars_df = df
        self.control_df = df
        return self.control_df.copy()
    
    #===========================================================================
    # PARAMETER EXTRACTIOn-------
    #===========================================================================
    def get_pars(self, #generic  parameter extraction
                 control_df = None,
                 toolName = None, #key for handles and bool column
                 bool_coln = None, #run control column (toolName as default)
                 out_type = 'dict', #type of output to return
                 logger=None,
                 ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('get_pars')
        if control_df is None: control_df=self.control_df.copy()
        if toolName is None: toolName=self.toolName
        
        #column name with your asset flow control boolean
        if bool_coln is None: 
            if toolName in self.bcoln_d:
                bool_coln = self.bcoln_d[toolName]
            else:
                bool_coln = toolName
            


        #get these handles        
        hndl_d = self.hndl_lib[toolName]
        #=======================================================================
        # precheck
        #=======================================================================
        #check we got the handles and the control column
        miss_l = set(list(hndl_d.keys()) + [bool_coln]).difference(control_df.columns)
        if not len(miss_l)==0:
            raise Error('control_df for \'%s\' missing %i cols \n    %s'%(
                toolName, len(miss_l), miss_l))
        
        #=======================================================================
        # clean the batch control file
        #=======================================================================
        if not toolName == 'build':
            control_df=control_df.dropna(subset=['cf_fp'], axis=0)

        df = control_df.loc[control_df[bool_coln], control_df.columns.isin(hndl_d.keys())]
        
        if not len(df)>0:
            log.warning('for \'%s\' got zero runs flagged... returning empty dict'%bool_coln)
            return dict()
        
        #=======================================================================
        # typeset
        #=======================================================================
        """NO! hanldes are for data typesetting"""
 
        for coln, col_hndls in hndl_d.items():
            for hndl, hval in col_hndls.items():
                if hndl=='type':

                        
                    try:
                        df.loc[:, coln] = df[coln].astype(hval)
                    except Exception as e:
                        raise Error('failed to typeset %s=%s w/ \n    %s'%(coln, hval, e))
                    
                    #treat blanks as false
                    if hval == bool:
                        df.loc[:, coln] = df[coln].fillna(False)
                        
                elif hndl=='values':
                    assert df[coln].isin(hval).all(), '%s got unrecognized values'

                    
                else:
                    raise Error('got unrecognized hnalde %s=%s'%(coln, hndl))
        """
        df.dtypes
        view(df)
        
        df.dtypes
        """
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('got %s'%str(df.shape))
        if out_type=='dict':
        
            return self._to_dict(df)
        
        elif out_type=='df':
            return df
        else:
            raise Error('bad out_type:%s'%out_type)
        
    def get_pars_build( self, #special pars collector for the build tool
        
        #spreadsheet with loading parameters
        df_raw = None,
        
        
        #relative filepath info
        rel_d = {
            'finv_fn':r'C:\LS\02_WORK\NHC\202007_Mission\04_CALC\risk\assetModels',
            'curves_fn':r'C:\LS\02_WORK\NHC\202007_Mission\03_SOFT\03_py\_ins\cf\20210210\build\CFcc_20200608141946',
            },
        
        logger=None,
        ):
    
        #===========================================================================
        # defaults 
        #===========================================================================
        assert self.toolName == 'build'
        if df_raw is None: df_raw = self.bCntrl_df.copy()
        
        if logger is None: logger=self.logger
        log = logger.getChild('gp_build')
        

        #===========================================================================
        # pull parmaeters
        #===========================================================================
        df = self.get_pars(control_df=df_raw, out_type='df', logger=log)
        

        #===========================================================================
        # build filepaths
        #===========================================================================
        miss_l = set(rel_d.keys()).difference(df.columns)
        assert len(miss_l)==0, 'missing %s'%miss_l
        
        
        for coln, data_dir in rel_d.items():
            assert os.path.exists(data_dir), coln
            boolidx = df[coln].notna()
            
            d = {k:os.path.join(data_dir, v) for k,v in df.loc[boolidx, coln].items()}
            assert pd.Series(d).notna().all(), coln
            ncoln = coln[:-3]+'_fp'
            
            
            df.loc[boolidx, ncoln] = pd.Series(d)
            
            
            #check filepaths
            for k,v in df[ncoln].dropna().items():
                assert os.path.exists(v), 'bad \'%s\' fp on \'%s\': \n    %s'%(coln, k, v)
                
            df = df.drop(coln, axis=1)
            
        #===========================================================================
        # add validation type
        #===========================================================================
        for mtype, vflag in {
                            'L1':'risk1',
                            'L2':'dmg2',
                            }.items():
            bx = df['modelType']== mtype
            
            if bx.any():
                df.loc[bx, 'validate'] = vflag
                log.info('set %i validate=%s'%(bx.sum(), vflag))
            

        
        #specials
        df = df.rename(columns={'curves_fp':'curves'})

    
        #===========================================================================
        # check
        #===========================================================================
        #check inundation logic
        assert df.loc[df['as_inun'], 'dthresh'].notna().all(), 'dthresh as_inun mismatch'
        
        assert np.array_equal(df['curves'].notna(), df['modelType']=='L2'), 'missing some curves on L2 models'
        
        
        #===========================================================================
        # wrap
        #===========================================================================
        log.info('built %s'%str(df.shape))
        """
        view(df)
        """
        return self._to_dict(df)
    
    def _to_dict(self, df): #get a dictionary w/o nulls and fancy type handling
        
        rd = dict()
        for k, d in df.to_dict('index').items():
            rd[k] = {k:v for k,v in d.items() if not pd.isnull(v)}
            
            rd[k] = dict()
            for k1,v in d.items():
                
                if pd.isnull(v):continue
                
                """should be a better way to do this..."""
                if df.dtypes[k1].char == 'O':
                    rd[k][k1] = str(v)
                else:
                    rd[k][k1] = v

                
            
        """
        view(df.dtypes)
        """
            
        return rd
    
    #===========================================================================
    # PARAMETER SETTING--------
    #===========================================================================
    def update_pars(self, #update the run control file
                    new_df, #summary data from individual tool run
                    old_df = None,
                    toolName = None,
                    next_bcoln = None, #next column w/ control flag
                    clear_bcoln = None, #whether to overwite inherited flags on next_bcoln
                    logger=None,
                        ):
        """
        respecting any unaltered values on meta.csv
            overwriting with anything new from this run
        """
        #=======================================================================
        # defaults
        #=======================================================================
        assert isinstance(new_df, pd.DataFrame)
        if old_df is None: old_df = self.pars_df.copy()
        if toolName is None: toolName = self.toolName
        
        if logger is None: logger=self.logger
        log=logger.getChild('update_pars')
        
        
        #determine the name of the control column to write for next run
        if next_bcoln is None:
            if toolName in self.nbcoln_d:
                next_bcoln=self.nbcoln_d[toolName]
                
        #default is to clear all previous flags unless the next step is results
        if clear_bcoln is None:
            clear_bcoln = next_bcoln!='results'
        
        #=======================================================================
        # add data
        #=======================================================================
        if not next_bcoln is None:

            new_df[next_bcoln] = True
            
            df = old_df.drop(next_bcoln, axis=1, errors='ignore')
        else:
            df = old_df.copy()
        

        new_df['rTime_%s'%self.toolName] = self.today_str
        

        #=======================================================================
        # add any new columns
        #=======================================================================
        new_colns = set(new_df.columns).difference(df.columns)
        new_indx = set(new_df.index).difference(df.index)
        
        if len(new_colns)>0 or len(new_indx)>0:
            log.debug('adding %i new colns: %s'%(len(new_colns), new_colns))
            df = df.merge(
                new_df.loc[new_indx, new_colns],
                how='outer',
                left_index=True, right_index=True,
                )
        
        #=======================================================================
        # overwrite and fill with new values
        #=======================================================================
        
        df.update(new_df, overwrite=True, errors='ignore')
        #=======================================================================
        # check index
        #=======================================================================
        miss_l = set(new_df.index).difference(df.index)
        assert len(miss_l)==0, 'didnt add new rows'
        """
        view(df)
        old_df = old_df.drop('cf_fp', axis=1)
        old_df = old_df.drop('bldg.sfd')
        df.columns
        view(old_df[next_bcoln])
        """

        #=======================================================================
        # control inheritance
        #=======================================================================
        if not next_bcoln is None:
            if clear_bcoln:
                df.loc[:, next_bcoln] = df[next_bcoln].fillna(False) #tell the rest not to go
            else:

                if next_bcoln in old_df.columns:
                    log.info('inheriting \"%s\' vals from old w/ %i =True and %i=Null'%(
                    next_bcoln, df[next_bcoln].sum(),df[next_bcoln].isna().sum()))
                                        
                    df.update(old_df[next_bcoln], overwrite=False)
                else:
                    df.loc[:, next_bcoln] = df[next_bcoln].fillna(False) #tell the rest not to go

        

        
        self.pars_df = df
        
        return self.pars_df
    """
    self.toolName
    view(df)
    """
    
    def set_mixed_controls(self, #fix mixed handles for build runs
                           d_fp, #build parameters
                           pars_df, #output of update pars
                          ):
        """
        TODO: Clean this up
        """
        
        """need to separate r1 and r2 models when we flag"""
        df = pd.DataFrame.from_dict(d_fp, orient='index').reindex(index=pars_df.index)
        
        #all r1 (no curve)
        if not 'curves' in df.columns:
            df['risk1'] = df.iloc[:,0].notna()
            df['dmg2'] = False
    
        
        #mixed or r2
        else:
            
        
            df['dmg2'] = df['curves'].notna()==True
            df['risk1'] = np.logical_and(
                                        df.index.isin(d_fp.keys()), #calculated here
                                        ~df['dmg2']) #not flagged as r2
            
            
        df = df.loc[:, ('dmg2', 'risk1')]
        df['risk2'] = False #the dmg module should set all these
        
        #loop and set
        for coln in ['dmg2', 'risk1', 'risk2']:
            if not coln in df.columns: continue
            pars_df.loc[:, coln] = df[coln]
    
    
        #fix build column
        pars_df.loc[pars_df.index.isin(d_fp.keys()), 'build'] = True
        pars_df.loc[~pars_df.index.isin(d_fp.keys()), 'build'] = False
        """
        view(df)
        view(pars_df)
        view(pars_df.loc[:, ('dmg2','risk1', 'build')])
        """
        
        return pars_df
    #===========================================================================
    # OUTPUTS-------
    #===========================================================================
    def write_pars(self, #write batch control file
                  df=None,
                  ofp = None,
                  
                  ):
        #=======================================================================
        # defaults
        #=======================================================================
        if ofp is None: ofp = self.control_fp
        if df is None: df=self.pars_df
        #=======================================================================
        # write it
        #=======================================================================
        try:
            df.sort_index(axis=0, ascending=True).to_csv(ofp, index=True)
            print('wrote pars_df %s to file: %s'%(str(df.shape), ofp))
        except Exception as e:
            self.logger.error('failed to write meta.csv w/ \n    %s'%e)
            
        return ofp
    

            
    #===========================================================================
    # TOOL RUNS-----------
    #===========================================================================
    """
    for running a group of assetModels
    
    controlled by batch runners for individual tool runs or linked runs
    """
    def tools_build(self, #run build tools for an assetModel group (same scenario)
            tag_d, #assetModel parameters {tag:am_d}}
            pars_d=None, #common running parameters
            out_dir = None,
            plot=None, 
            logger=None,
            **MBkwargs
            ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if pars_d is None: pars_d = self.pars_d
        if logger is None: logger=self.logger
        if plot is None: plot=self.plot
        
        if out_dir is None:
            out_dir = os.path.join(self.out_dir, 'assetModels')
            if self.runTag is None:
                out_dir = out_dir
            else:
                out_dir = os.path.join(out_dir, self.runTag)
        
        log = logger.getChild('tBuild')
        
        #=======================================================================
        # imports
        #=======================================================================
        # CanFlood tool imports
        from build.prepr import Preparor
        from build.rsamp import Rsamp
        from build.lisamp import LikeSampler
        from build.validator import Vali
        

        
        class MasterBuilder(#combine all the build workers for a single run
                Preparor, Rsamp, LikeSampler, Vali):
            """
            needed to avoid reinitilziing qgis each time
            """
            
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                
                self.baseClassConv_d = self.get_baseClassConv_d()
                
            def get_baseClassConv_d(self):
                
                baseClassConv_d = dict()
                first=True
                last=None
                for baseClass in self.__class__.__mro__:
                    bcName = baseClass.__name__
                    if first:
                        first=False
                    else:
                        baseClassConv_d[bcName]=last
                    
                    last = baseClass
                    
                return baseClassConv_d
        
        #=======================================================================
        # tool setup
        #=======================================================================
        base_dir =  pars_d['base_dir']
        
        #=======================================================================
        # precheck
        #=======================================================================
        #check we didnt try and pass some parameters that should be on the worker
        miss_l = set(['out_dir', 'crs_id']).intersection(pars_d.keys())
        assert len(miss_l)==0, 'passed some keys that should be on the worker: %s'%miss_l

        #=======================================================================
        # start worker
        #=======================================================================

        wrkr = MasterBuilder(out_dir=out_dir,**MBkwargs)
        
        self._init_child_q(wrkr) #setup Q
        self._init_child_pars(wrkr) #pass standard attributies 
                                
        #==========================================================================
        # build/execute----------
        #==========================================================================
        #containers
        rlay_d, dtm_rlay, lpol_d = None, None, None
        cf_d = dict()
    
        #loop and build each asset model
        for tag, am_d in tag_d.items():
            cf_d[tag] = dict() #add the page

            #=======================================================================
            # #variables for this asset model
            #=======================================================================
            od1 = os.path.join(out_dir, tag)
            if not os.path.exists(od1):os.makedirs(od1)
            
            wrkr.out_dir = od1
            wrkr.tag = tag
            wrkr.cid = am_d['cid']
            wrkr.logger=logger.getChild('tBuild.%s'%tag)
            #=======================================================================
            # prepare----
            #=======================================================================
            wrkrPR = super(wrkr.baseClassConv_d['Preparor'], wrkr) #get a special worker
            
            #copy the template
            cf_fp = wrkrPR.copy_cf_template(cf_src=os.path.join(base_dir, pars_d['cf_tmpl_fn']))
            
            
            #set some basics
            new_pars_d =dict()
            for sect, keys in {
                'parameters':['impact_units', 'rtail', 'event_rels', 'felv', 'prec'],
                'dmg_fps':['curves'],
                'plotting':['impactfmt_str']
                }.items():
                d = {k:str(am_d[k]) for k in keys if k in am_d} #get these keys where present
                
                if sect == 'parameters':
                    d['name']=tag
                
                if len(d)>0:
                    new_pars_d[sect] = tuple([d, '#set by build_all.py on %s'%wrkr.today_str])
    
            wrkrPR.set_cf_pars(new_pars_d)
    
            log.info('control file created: %s'%cf_fp)
            
            #=======================================================================
            # convert_finv
            #=======================================================================
            #load the aoi
            if 'aoi_fp' in pars_d:
                aoi_vlay = wrkrPR.load_vlay(pars_d['aoi_fp'])
            else:
                aoi_vlay=None
                
            #load the finv
            finv_vlay = wrkrPR.load_vlay(am_d['finv_fp'], aoi_vlay=aoi_vlay)
            
            #aoi slice check
            if finv_vlay is None:
                """
                would be nice to write some meta on this... 
                """
                log.warning('%s got no features.. skipping'%tag)
                del wrkrPR
                continue
                
            
            #convert
            wrkrPR.finv_to_csv(finv_vlay, felv=am_d['felv'])
            del wrkrPR
            
            #=======================================================================
            # sample hazard rasters----
            #=======================================================================
            wrkrHR = super(wrkr.baseClassConv_d['Rsamp'], wrkr) #get a special worker
            
            #=======================================================================
            # #load rasters
            #=======================================================================
            if rlay_d is None:
                rlay_d = wrkrHR.load_rlays(pars_d['raster_dir'],aoi_vlay=aoi_vlay)
                
            if 'dtm_fp' in pars_d:
                if dtm_rlay is None:
                    dtm_rlay = wrkrHR.load_rlay(pars_d['dtm_fp'])
                    
            """TODO: add check against evals"""
            #=======================================================================
            # #run samples
            #=======================================================================
            kwargs = {k:am_d[k] for k in ['dthresh', 'as_inun'] if k in am_d}
            res_vlay = wrkrHR.run(list(rlay_d.values()), finv_vlay, dtm_rlay=dtm_rlay,
                                  **kwargs)
        
            #=======================================================================
            # #post
            #=======================================================================
            wrkrHR.check()
            wrkrHR.write_res(res_vlay) #save csv results to file
            wrkrHR.update_cf(cf_fp) #update ocntrol file
            
            if plot:
                fig = wrkrHR.plot_boxes()
                wrkrHR.output_fig(fig)
                
                fig = wrkrHR.plot_hist()
                wrkrHR.output_fig(fig)
            #=======================================================================
            # DTM----
            #=======================================================================
            if am_d['felv']=='ground':
                res_vlay = wrkrHR.run([dtm_rlay], finv_vlay, fname='gels')
                wrkrHR.dtm_check(res_vlay)
                wrkrHR.write_res(res_vlay)
                wrkrHR.upd_cf_dtm()
            
            del wrkrHR
             
            #=======================================================================
            # event variables----
            #=======================================================================
            aep_ser = None
            if 'evals_fn' in pars_d:
                evals_fp = os.path.join(base_dir, pars_d['evals_fn'])
                assert os.path.exists(evals_fp), evals_fp
                wrkr.set_cf_pars(
                    {
                        'parameters':({'event_probs':'ari'},),
                        'risk_fps':({'evals':evals_fp},)                          
                     }
                    )
                
                aep_ser = wrkr.load_evals(fp = evals_fp, logger=log, check=False) #load for checks
            
            #=======================================================================
            # pFail----- 
            #=======================================================================
            if 'lpol_fn_d' in pars_d:
                wrkrLS = super(wrkr.baseClassConv_d['LikeSampler'], wrkr) #get a special worker
                  
                #load lpols
                if lpol_d is None:
                    lpol_d = wrkrLS.load_lpols(pars_d['lpol_fn_d'], basedir=pars_d['lpol_basedir'])
                  
                #run it      
    
                res_df = wrkrLS.run(finv_vlay, lpol_d, 
                                    lfield=pars_d['lfield'], 
                                    event_rels=am_d['Levent_rels'])          
                #post
                wrkrLS.check(res_df, aep_ser=aep_ser)
                wrkrLS.write_res(res_df)
                wrkrLS.update_cf(cf_fp)
                
                #plot
                if plot:
                    fig = wrkrLS.plot_hist()
                    wrkrLS.output_fig(fig)
                    
                    fig = wrkrLS.plot_boxes()
                    wrkrLS.output_fig(fig)
                del wrkrLS
                
            #=======================================================================
            # validator----
            #=======================================================================
            wrkrVA =  super(wrkr.baseClassConv_d['Vali'], wrkr) #get a special worker
            from model.risk1 import Risk1
            #from model.risk2 import Risk2
            from model.dmg2 import Dmg2
            
            wrkrVA.config_cf() #initlize the pars_der
            
            #loop and check each model
            for vtag, modObj in {
                'risk1':Risk1, 
                'dmg2':Dmg2,
                }.items():
                
                if vtag in am_d['validate']:
                
                    errors = wrkrVA.cf_check(modObj)
                    if not len(errors)==0:
                        """letting those that fail to validate pass"""
                        log.warning('\'%s\' got some errors \n    %s'%(vtag, errors))
    
                    #update control file
                    wrkr.cf_mark()
                
            del wrkrVA
            
            #=======================================================================
            # meta----
            #=======================================================================
            cf_d[tag].update({
                'cf_fp':cf_fp,
                'finv_fp':am_d['finv_fp'],
                })
    
            #=======================================================================
            # wrap
            #=======================================================================
            log.info('finished building')
            wrkr.out_dir = out_dir #reset
        
        log.info('wrap w/ %s'%wrkr.out_dir)
     
        return out_dir, cf_d
    
    def tools_dmg2(self,
                  runPars_d, 
            

            output_bdmg=True,

            set_impactUnits = False,
            
             smry_d = None, #results summary parameters {coln: dataFrame method to summarize with}

            #flow ontrols
            plot=None,
            upd_cf = True,
            
            logger=None,
            **kwargs
            ):
        #=======================================================================
        # defaults
        #=======================================================================
        if plot is None: plot=self.plot
        if logger is None: logger=self.logger
        log = logger.getChild(self.toolName)
        #==========================================================================
        # setup the tool
        #==========================================================================
        meta_d=dict()
        out_dir=None
        
        from model.dmg2 import Dmg2
        
        wrkr = Dmg2(out_dir=os.getcwd(), #overwriting below
                    logger=logger, tag='dmg2',**kwargs)
        
        self._init_child_pars(wrkr) #pass standard attributies
                         
        for k,v in runPars_d.items():assert 'cf_fp' in v
        #=======================================================================
        # execute tool on each assetModel                         
        #=======================================================================
        for atag, pars in runPars_d.items():
            cf_fp = pars['cf_fp']
            assert os.path.exists(cf_fp)
            
            #=======================================================================
            # get info from filepath
            #=======================================================================
            basedir = os.path.split(cf_fp)[0]
            #tag  = os.path.basename(basedir)
            #tag = 'dmg2'
            out_dir = os.path.join(basedir, 'dmg2')
            if not os.path.exists(out_dir):os.makedirs(out_dir)
            #=======================================================================
            # update for this loop
            #=======================================================================
            wrkr.cf_fp = cf_fp
            wrkr.out_dir = out_dir
            wrkr.logger = logger.getChild('tdmg.%s'%atag)
            wrkr.tag = atag

            #=======================================================================
            # run
            #=======================================================================
            #execute setup
            wrkr._setup()

            res_df = wrkr.run(set_impactUnits=set_impactUnits)
            

            if self.attriMode:
                _ = wrkr.get_attribution(res_df)
            
            #=======================================================================
            # plots
            #=======================================================================
            if plot:
                fig = wrkr.plot_boxes()
                _ = wrkr.output_fig(fig)
                
                fig = wrkr.plot_hist()
                _ = wrkr.output_fig(fig)
            
            #==========================================================================
            # outputs
            #==========================================================================
             
            out_fp = wrkr.output_cdmg()
             
            if upd_cf: 
                wrkr.update_cf()
            
            if output_bdmg:
                _ = wrkr.output_bdmg()
                _ = wrkr.bdmg_smry()
                _ = wrkr.output_depths_df()
                
            if self.attriMode:
                _ = wrkr.output_attr()
                
            #=======================================================================
            # meta
            #=======================================================================
            
            meta_d[atag] = {**{'dmg_ttl':res_df.sum().sum()}, **self._get_smry(res_df)}
    
            
        return out_dir, meta_d
        
    def _riskTools(self, #generic runner for the risk2 model
            runPars_d,
            RiskClass,
            
            #smry_d = None, #default risk model results summary parameters {coln: dataFrame method to summarize with}
            plot = None,
            res_per_asset = True,

            logger=None,

        ):

        #=======================================================================
        # defaults
        #=======================================================================
        if plot is None: plot=self.plot
        #if smry_d is None: smry_d=self.smry_d
        if logger is None: logger=self.logger
        
        log = logger.getChild(self.toolName)
        
        #=======================================================================
        # precheck
        #=======================================================================

        #==========================================================================
        # build/execute
        #==========================================================================
        res_d = dict()
        out_dir=None
        for atag, pars in runPars_d.items():
            cf_fp = pars['cf_fp']
            assert os.path.exists(cf_fp)
            
            #=======================================================================
            # get info from filepath
            #=======================================================================
            basedir = os.path.split(cf_fp)[0]
            #tag  = os.path.basename(basedir)
            #tag=self.runTag
            out_dir = os.path.join(basedir, self.toolName)
            
            #=======================================================================
            # runit
            #=======================================================================
 
            wrkr = RiskClass(cf_fp, out_dir=out_dir, logger=logger.getChild('rTool.%s'%atag), tag=atag,
                         )

            self._init_child_pars(wrkr) #pass standard attributies
            
            wrkr._setup()
            
            res_ttl, res_df = wrkr.run(res_per_asset=res_per_asset)
            
            """
            res_df.columns
            """
            #======================================================================
            # plot
            #======================================================================
            if plot:
                ttl_df = wrkr.prep_ttl(tlRaw_df=res_ttl)
                for y1lab in ['AEP', 'impacts']:
                    fig = wrkr.plot_riskCurve(ttl_df, y1lab=y1lab)
                    _ = wrkr.output_fig(fig)
                
                
    
            #==========================================================================
            # output
            #==========================================================================
            wrkr.output_ttl()
            wrkr.output_etype()
            
            if not res_df is None:
                wrkr.output_passet()
                
    
            if self.attriMode:
                wrkr.output_attr()
                
            #=======================================================================
            # meta
            #=======================================================================
            
            res_d[atag] = {**{'ead':wrkr.ead_tot}, **self._get_smry(res_df)}
                    

            
            #=======================================================================
            # wrap
            #=======================================================================
            del wrkr
            print('finished %s \n\n\n'%atag)
            
            
            
    
        log.info('finished w/ %i'%len(res_d))
        return out_dir, res_d
    
    def tools_risk2(self, pars_d, **kwargs):
        
        from model.risk2 import Risk2
        
        return self._riskTools(pars_d, Risk2, **kwargs)
    
    
    def tools_risk1(self,pars_d, **kwargs):
        
        from model.risk1 import Risk1
        
        return self._riskTools(pars_d, Risk1, **kwargs)
    
    def tools_djoin(self,
            runPars_d,
            write_vlay=None,
            logger=None,
            **kwargs):
        #=======================================================================
        # defaults
        #=======================================================================
        if write_vlay is None: write_vlay=self.write_vlay
        if logger is None: logger=self.logger
        log=logger.getChild('rDj')
        #=======================================================================
        # setup
        #=======================================================================
        from results.djoin import Djoiner
        wrkr = Djoiner(tag=self.scenarioName, **kwargs)
        
        self._init_child_q(wrkr) #setup Q
        self._init_child_pars(wrkr) #pass standard attributies 
        
        #==========================================================================
        # build/execute
        #==========================================================================
        meta_d = dict()
        for name, pars in runPars_d.items():
            cf_fp, vlay_fp = pars['cf_fp'], pars['finv_fp']
            #=======================================================================
            # get info from filepath
            #=======================================================================
            basedir = os.path.split(cf_fp)[0]
            #tag  = os.path.basename(basedir)
            
            out_dir = os.path.join(basedir, 'res_djoin')
            
            #=======================================================================
            # setup fr this run
            #=======================================================================       
            wrkr.logger=logger.getChild('rDj.%s'%name)
            #wrkr.tag = tag
            wrkr.cf_fp = cf_fp
            wrkr.out_dir=out_dir
     
            
            if not os.path.exists(wrkr.out_dir):os.makedirs(wrkr.out_dir)
            
            
            wrkr.init_model() #load the control file
            #=======================================================================
            # load the layer
            #=======================================================================
            vlay_raw = wrkr.load_vlay(vlay_fp)

            #=======================================================================
            # run join
            #=======================================================================
            #kwargs = {k:pars[k] for k in ['cf_fp', 'out_dir', 'cid']}
            jvlay = wrkr.run(vlay_raw, keep_fnl='all')
            
            #=======================================================================
            # write result
            #=======================================================================
            if write_vlay:
                out_fp = wrkr.vlay_write(jvlay, logger=log)
                
            else:
                out_fp=''
                
            #=======================================================================
            # meta
            #=======================================================================
            meta_d[name] = {
                'djoin_fp':out_fp
                }
    
            
            
    
        log.info('finished on %i'%len(runPars_d))
        return wrkr.out_dir, meta_d
    
    def tools_compare(self, #generic runner for the risk2 model
                runpars_d,
                logger=None,
        ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('tCompare')
        
        
        #=======================================================================
        # setup the worker
        #=======================================================================
        from results.compare import Cmpr
        fps_d = {k:d['cf_fp'] for k,d in runpars_d.items()}
    
        wrkr = Cmpr(fps_d = fps_d, logger=log,cf_fp = fps_d[list(fps_d)[0]],
                    out_dir = os.path.join(self.out_dir, 'res_compare'))
        
        self._init_child_pars(wrkr) #pass standard attributies
        
        #set some attributes used by the title block
        wrkr.tag = '%s_%s'%(self.projName, self.scenarioName)
        wrkr._setup()
        #===========================================================================
        # get data
        #===========================================================================
        cdxind, cWrkr = wrkr.build_composite()
        
        #===========================================================================
        # plot
        #===========================================================================
        for y1lab in ['AEP', 'impacts']:
            fig = wrkr.plot_rCurveStk_comb(y1lab=y1lab)
            wrkr.output_fig(fig)
    
        log.info('finished on %i'%len(runpars_d))
        
        #=======================================================================
        # store the composite worker
        #=======================================================================
        cWrkr.write(logger=log)
        
        #=======================================================================
        # get meta
        #=======================================================================
        meta_d = cdxind.droplevel(axis=0, level=['note', 'plot']
                      ).sum().rename('impacts').to_frame().to_dict(orient='index')
        
        return wrkr.out_dir, meta_d
    

    #===========================================================================
    # SINGLE TOOL HANDLER-------
    #===========================================================================
    def run_toolbox(self,
                    toolName, #run a specific tool group (other than build)
                        #build, dmg2, risk1, risk2, djoin
            pars_d=None, #common parameters for build toolbox
            control_df = None,
            writePars = True, #whether to save the control parameters to file
            
            bool_coln=None, #control column name for asset flow (see get_pars())
            
            logger=None,
            **kwargs, #passed to 'tools_xxx()' function
            ):
    
        #===========================================================================
        # defaults
        #===========================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('rT')
    
        self.toolName=toolName
        
        #=======================================================================
        # precheck
        #=======================================================================
        #assert not toolName =='build', 'build toolbox has a custom caller'
        assert toolName in self.hndl_lib, 'unrecognized toolName: \'%s\''%toolName
        
        fName = 'tools_%s'%toolName
        assert hasattr(self, fName)        
        
     
        #===========================================================================
        # #run BUILD toolbox------
        #===========================================================================
        """
        easier just to code this one explicitly
        """
        if toolName == 'build':
            if pars_d is None: pars_d=self.pars_d
            _ = self.load_buildControl(pars_d.pop('buildControl_fp'))
        
            #extract pars
            tag_d = self.get_pars_build(rel_d = pars_d.pop('rel_d'), logger=log)

            # construct models
            tool_od, meta_d = self.tools_build(tag_d, pars_d=pars_d, **kwargs)
            
        #=======================================================================
        # other Toolbox------
        #=======================================================================
        else:
            #load pars
            if control_df is None:
                control_df = self.load_control()

            runPars_d = self.get_pars(control_df=control_df, bool_coln=bool_coln)
        
            #execute run
            if len(runPars_d)==0:
                log.warning('%s got no pars.. skipping'%self.toolName)
                tool_od = self.out_dir
                meta_d = dict()
            else:
                #get the runner
                f = getattr(self, fName)            
                tool_od, meta_d = f(runPars_d, logger=log, **kwargs)
    
        #===========================================================================
        # run sunnarty data --------
        #===========================================================================
        self.meta_d = meta_d #set this for run_all()'s reporting
        
        #intelligent updating, setting up next run, and outputting
        if len(meta_d)>0:
            #if toolName in self.nbcoln_d:
            pars_df = pd.DataFrame.from_dict(meta_d, orient='index')
            pars_df = self.update_pars(pars_df)
            
            if toolName == 'build':
                pars_df = self.set_mixed_controls(tag_d, pars_df)
        else:
            pars_df = self.pars_df
            
        if writePars:
            self.write_pars(df=pars_df)
    
        log.info('finished on %s'%toolName)
        return tool_od, pars_df
    
    
    #===========================================================================
    # LINKED TOOL HANDLER-------
    #===========================================================================


            
            
            
            
            
            
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
