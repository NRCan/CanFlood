'''
Created on Feb. 14, 2021

@author: cefect
'''
import os, datetime
import pandas as pd
import numpy as np

today_str = datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')

from hlpr.basic import view, ComWrkr
from hlpr.exceptions import Error

class CFbatch(ComWrkr): #handerl of batch CanFlood runs (build, model, results)
    
    """
    this facilitates linking together the following workflows via python scripts:
        tools (build, model, cresults)
        assetModels (e.g., residential, NRP, infrastrdutrue)
        sceanrios (e.g., climate change, baseline)
        
    no GUI planned for this
    """

    
    #handles per tool
    """WARNING! these are handles for the batch HANDLES (not the data)"""
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
        'dmg':{
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
            }
        
        }
    
    smry_d = None #default risk model results summary parameters {coln: dataFrame method to summarize with}
            
    def __init__(self,
                 buildControl_fp = None,
                 control_fp = None,
                 projName='project',
                 toolName='build', #tool name of this run
                 tag = 'r', #mostly for column suffixes and repeat run labelling
                 out_dir = None,
                 crs_id='EPSG:4326',
                 #logger=None,
                 start_lib=False, #whether to start the csv data from the xlss
                 **kwargs
                 ):
        
        #output directory
        if out_dir is None: out_dir = os.path.join(os.getcwd(), projName)
        #if not os.path.exists(out_dir):os.makedirs(out_dir)
        
        #logger
        super().__init__(out_dir=out_dir,tag=tag,
                          **kwargs) #initilzie teh baseclass
        
        
        #attachments
        self.crs_id=crs_id
        self.buildControl_fp=buildControl_fp
        self.control_fp=control_fp
        #self.out_dir=out_dir
        self.projName=projName
        self.toolName = toolName
        #self.tag=tag
        
        #checks
        assert toolName in self.hndl_lib
        
        self.start_lib=start_lib
        if not start_lib:
            assert isinstance(control_fp, str), 'for start_lib=False, need to specificy a control_fp'
 
            self.load_control()
            
        self.logger.info('CFbatch __init__ finished')


    
    def load_buildControl(self,
                     fp=None, #headers on row 2
                     sheet_name='finv',
                     header=1, #default is to ignore the first line
                        
                     ):
        #=======================================================================
        # defaults
        #=======================================================================
        if fp is None: fp=self.buildControl_fp
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
        # #=======================================================================
        # # #typeset
        # #=======================================================================
        # for coln in self.fcolns:
        #     if not coln in df.columns: continue
        #     df.loc[:, coln]  = df[coln].astype(bool)
        #     
        # if 'rtail' in df.columns:
        #     df.loc[:, 'rtail'] = df['rtail'].astype(str) #weird expectation on this one
        #=======================================================================
            
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
        self.xls_df = df.infer_objects()
        if self.start_lib:
            """this will voerwrite the csv"""
            self.df_raw = df.loc[:, df.columns.isin(hcolns)] #only for first build
        #self.pars_df = df1.copy() #for outputting
        
        return self.xls_df
    
    def load_control(self,
                 fp=None,


                 ):
        if fp is None: fp = self.control_fp
        assert isinstance(fp, str)
 
        
        df_raw = pd.read_csv(fp, index_col=0)
        df = df_raw.copy()
        
        #=======================================================================
        # for coln in self.fcolns:
        #     if not coln in df.columns: continue
        #     df.loc[:, coln]  = df[coln].astype(bool)
        #=======================================================================
        

        self.df_raw = df
        return self.df_raw.copy()
    
    def get_pars(self, #generic  parameter extraction
                 df_raw = None,
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
        if df_raw is None: df_raw=self.df_raw.copy()
        if toolName is None: toolName=self.toolName
        if bool_coln is None: bool_coln=toolName

        #get these handles        
        hndl_d = self.hndl_lib[toolName]
        #=======================================================================
        # precheck
        #=======================================================================
        #check we got the handles and the control column
        miss_l = set(list(hndl_d.keys()) + [bool_coln]).difference(df_raw.columns)
        assert len(miss_l)==0, miss_l
        
        #=======================================================================
        # clean 
        #=======================================================================\
        bx = df_raw[bool_coln]
        if not bx.any():
            log.warning('for \'%s\' got zero runs flagged... returning empty dict'%bool_coln)
            return dict()
        
        df = df_raw.loc[bx, df_raw.columns.isin(hndl_d.keys())]
        
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
        
        
        ):
    
        #===========================================================================
        # defaults 
        #===========================================================================
        assert self.toolName == 'build'
        if df_raw is None: df_raw = self.xls_df.copy()
        log = self.logger.getChild('gp_build')
        

        #===========================================================================
        # pull parmaeters
        #===========================================================================
        df = self.get_pars(df_raw=df_raw, out_type='df', logger=log)
        

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
    

    
    
    def update_pars(self, #update the run control file
                    new_df,
                    old_df = None,
                    next_bcoln = 'dmg', #next column w/ control flag
                    clear_bcoln = True, #whether to overwite inherited flags on next_bcoln
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
        if old_df is None: old_df = self.df_raw.copy()
        
        if logger is None: logger=self.logger
        log=logger.getChild('update_pars')
        
        """using this mostly to keep track of the spatial data"""
        #=======================================================================
        # add data
        #=======================================================================
        if not next_bcoln is None:
            #assert next_bcoln in self.fcolns, next_bcoln
            new_df[next_bcoln] = True
            
            df = old_df.drop(next_bcoln, axis=1, errors='ignore')
        else:
            df = old_df.copy()
        

        new_df['rTime_%s'%self.toolName] = today_str
        

        #=======================================================================
        # add any new columns
        #=======================================================================
        new_colns = set(new_df.columns).difference(df.columns)
        new_indx = set(new_df.index).difference(df.index)
        if len(new_colns)>0 or len(new_indx)>0:
            log.info('adding %i new colns: %s'%(len(new_colns), new_colns))
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
            df['dmg'] = False
    
        
        #mixed or r2
        else:
            
        
            df['dmg'] = df['curves'].notna()==True
            df['risk1'] = np.logical_and(
                                        df.index.isin(d_fp.keys()), #calculated here
                                        ~df['dmg']) #not flagged as r2
            
            
        df = df.loc[:, ('dmg', 'risk1')]
        df['risk2'] = False #the dmg module should set all these
        
        #loop and set
        for coln in ['dmg', 'risk1', 'risk2']:
            if not coln in df.columns: continue
            pars_df.loc[:, coln] = df[coln]
    
    
        #fix build column
        pars_df.loc[pars_df.index.isin(d_fp.keys()), 'build'] = True
        pars_df.loc[~pars_df.index.isin(d_fp.keys()), 'build'] = False
        """
        view(df)
        view(pars_df)
        view(pars_df.loc[:, ('dmg','risk1', 'build')])
        """
        
        return pars_df
    
    def write_pars(self,
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
            df.to_csv(self.control_fp, index=True)
        except Exception as e:
            self.logger.error('failed to write meta.csv w/ \n    %s'%e)
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
