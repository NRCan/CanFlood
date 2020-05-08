'''
Created on Feb. 9, 2020

@author: cefect
'''
#==============================================================================
# logger----------
#==============================================================================

#==============================================================================
# imports------------
#==============================================================================

import configparser, os, inspect, logging
import pandas as pd
import numpy as np

from scipy import interpolate, integrate

#==============================================================================
# custom
#==============================================================================
#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   

    
#plugin runs
else:
    mod_logger = logging.getLogger('common') #get the root logger

from hlpr.exceptions import QError as Error
    
from hlpr.basic import *

#==============================================================================
# class-----------
#==============================================================================
class Model(ComWrkr):
    """
    common methods for model classes
    
    
    Control File Parameters:
        [parameters]

        event_probs -- format of event probabilities (in 'aeps' data file) 
                        (default 'ari')
                        
            'aeps'           event probabilities in aeps file expressed as 
                            annual exceedance probabilities
            'aris'           expressed as annual recurrance intervals
            
        
        ltail -- zero probability event extrapolation handle 
                (default 'extrapolate')
            'flat'           set the zero probability event equal to the most 
                            extreme impacts in the passed series
            'extrapolate'    set the zero probability event by extrapolating from 
                            the most extreme impact
            'none'           do not extrapolate (not recommended)
            float            use the passed value as the zero probability impact value
             
        
        rtail -- zreo impacts event extrapolation handle    (default 0.5)
            'extrapolate'    set the zero impact event by extrapolating from the 
                            least extreme impact
            'none'           do not extrapolate (not recommended) 
            float           use the passed value as the zero impacts aep value
        
        drop_tails -- flag to drop the extrapolated values from the results 
                            (default True)
        
        integrate -- numpy integration method to apply (default 'trapz')
        
        res_per_asset -- flag to generate results per asset 
        
        ground_water -- flag to include negative depths in the analysis
        
        as_inun    -- flag whether to treat exposures as %inundation
        
        [dmg_fps]

        
        [risk_fps]
        dmgs -- damage data results file path (default N/A)
            
        exlikes -- secondary exposure likelihood data file path (default N/A)
        
        evals -- event probability data file path (default N/A)
        
        [validation]
        risk2 -- Risk2 validation flag (default False)
    
    """
    
    #==========================================================================
    # parameters from control file
    #==========================================================================
    #[parameters]
    name = ''
    cid = ''
    prec = 2
    ground_water = False
    felv = ''
    event_probs = 'ari'
    ltail = 'extrapolate'
    rtail = 0.5
    drop_tails = True
    integrate = 'trapz'
    as_inun = False


    
    #[dmg_fps]
    curves = ''
    finv = ''
    expos = ''
    gels = ''
    
    #[risk_fps]
    dmgs = ''
    exlikes = ''
    evals = ''

    
    #[validation]
    risk1 = True
    dmg2 = False
    risk2 = False
    risk3 = False
    
    #==========================================================================
    # program vars
    #==========================================================================
    bid = 'bid' #indexer for expanded finv

    #minimum inventory expectations
    finv_exp_d = {
        'f0_scale':{'type':np.number},
        'f0_elv':{'type':np.number}
        }
    
    max_depth = 20 #maximum depth for throwing an error in build_depths()
    

    
    
    def __init__(self,
                 cf_fp, #control file path """ note: this could also be attached by basic.ComWrkr.__init__()"""
                 split_key=None,#for checking monotonicy on exposure sets with duplicate events


                 **kwargs):
        
        mod_logger.info('Model.__init__ start')
        assert os.path.exists(cf_fp), 'bad control filepath: %s'%cf_fp
        
        super().__init__(**kwargs) #initilzie teh baseclass
        
        self.cf_fp = cf_fp
        self.split_key= split_key
        

        #attachments
        self.data_d = dict() #dictionary for loaded data sets
        
        self.logger.debug('finished Model.__init__')
        
        
    def init_model(self, #common inits for all model classes
                   ):
        """
        should be called by the model's own 'setup()' func
            during standalones and Dialog runs
        """        
        
        #parameter setup
        self.cf_attach_pars(self.cf_fp)
        
        
        #check our validity tag
        if not getattr(self, self.valid_par):
            raise Error('control file not validated for \'%s\'. please run InputValidator'%self.valid_par)
        
        #wrap
        self.logger.debug('finished init_modelon Model')
        
        
        
    def cf_attach_pars(self, #load parmaeteres from file, check, and attach
                    cf_fp):
        
        log = self.logger.getChild('cf_attach_pars')
        
        assert os.path.exists(cf_fp), 'provided parameter file path does not exist \n    %s'%cf_fp
        
        #======================================================================
        # validate the control file for this run
        #======================================================================
        #load/build
        self.pars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%self.pars.read(cf_fp))
        
        #======================================================================
        # check control file against expectations
        #======================================================================
        #check sections
        miss_l = set(self.exp_pars_md.keys()).difference(self.pars.sections())
        
        if len(miss_l) > 0:
            raise Error('missing %i expected sections in control file: %s'%(len(miss_l), miss_l))
        
        #======================================================================
        # mandatory check and collect 
        #======================================================================
        cpars_d = dict()
        cnt = 0
        for sect, vchk_d in self.exp_pars_md.items():
            cpars_d[sect] = dict()
            
            if not sect in self.pars.sections():
                raise Error('missing section %s'%sect)
            
            #check presence
            miss_l = set(vchk_d.keys()).difference(self.pars[sect])
            if len(miss_l) > 0:
                raise Error('\'%s\' missing %i (of %i) expected varirables: \n    %s'%(
                    sect, len(miss_l), len(vchk_d), miss_l))
                
            #check attributes
            for varnm, achk_d in vchk_d.items():
                """no! allow None
                assert isinstance(achk_d, dict), '%s.%s bad type'%(sect, varnm)"""
                assert hasattr(self, varnm), '\'%s\' does not exist on %s'%(varnm, self)

                
                #==============================================================
                # #get value from parameter                
                #==============================================================
                pval_raw = self.pars[sect][varnm]
                
                #get native type
                ntype = type(getattr(self, varnm))
                
                #special type retrivial
                if ntype == bool:
                    pval = self.pars[sect].getboolean(varnm)
                else:
                    #set the type
                    pval = ntype(pval_raw)
                
                #==============================================================
                # check it
                #==============================================================
                self.par_hndl_chk(sect, varnm, pval, achk_d)
                

                #==============================================================
                # store value
                #==============================================================
                
                cpars_d[sect][varnm] = pval
                cnt +=1
        
        log.info('collected MANDATORY %i variables from %i sections from paramter file'%(
            cnt, len(cpars_d)))
        #======================================================================
        # optional check and collect
        #======================================================================
        cnt2 = 0
        for sect, vchk_d in self.exp_pars_op.items(): 
            #add a page to the container
            if not sect in cpars_d:
                cpars_d[sect] = dict()
                
            #loop and see if they have been provided
            for varnm, achk_d in vchk_d.items():
                #assert isinstance(achk_d, dict), '%s.%s bad type'%(sect, varnm)
                assert hasattr(self, varnm), '\'%s\' does not exist on %s'%(varnm, self)
                assert varnm in self.pars[sect], '%s.%s is not a valid parameter'%(sect, varnm)
                
                #==============================================================
                # #get value from parameter                
                #==============================================================
                pval_raw = self.pars[sect][varnm]
                
                if pval_raw is None or pval_raw == '':
                    log.debug('%s.%s blank.. skipping'%(sect, varnm))
                    continue
                
                #get native type
                ntype = type(getattr(self, varnm))
                
                #special type retrivial
                if ntype == bool:
                    pval = self.pars[sect].getboolean(varnm)
                else:
                    #set the type
                    pval = ntype(pval_raw)
                
                #==============================================================
                # check it
                #==============================================================
                self.par_hndl_chk(sect, varnm, pval, achk_d)
                
                #==============================================================
                # store value
                #==============================================================
                log.debug('%s.%s passed %i checks'%(sect, varnm, len(achk_d)))
                cpars_d[sect][varnm] = pval
                cnt2+=1
        
        log.info('collected OPTIONAl %i variables from %i sections from paramter file'%(
            cnt2, len(cpars_d)))
        
        #======================================================================
        # attach all the paramers
        #======================================================================
        cnt = 0
        for sect, spars_d in cpars_d.items():
            for varnm, val in spars_d.items():
                setattr(self, varnm, val)
                log.debug('set %s=%s'%(varnm, val))
                cnt +=1
                
        log.info('attached %i parmaeters to self'%cnt)
                
        
        
        return cpars_d
                
                
                
    def par_hndl_chk(self, #check a parameter aginast provided handles
                     sect, varnm, pval, achk_d
                     ):
        
        log = self.logger.getChild('par_hndl_chk')
        assert not pval is None or pval == '', '%s.%s got none'%(sect, varnm)
        if achk_d is None:
            log.warning('no checks provided for %s.%s'%(sect, varnm))
            return
        #==============================================================
        # #check each handle
        #==============================================================
        for chk_hndl, hvals in achk_d.items():
            
            if chk_hndl is None:
                pass
            elif chk_hndl == 'type':
                assert inspect.isclass(hvals)
                assert isinstance(pval,hvals), '%s.%s expected %s got type: %s'%(sect, varnm, hvals, type(pval))
                
            elif chk_hndl == 'values':
                assert isinstance(hvals, tuple), '%s.%s got bad type on hvals: %s'%(sect, varnm, type(hvals))
                assert pval in hvals, '%s.%s unexpected value: %s'%(sect, varnm, type(pval))
            
            elif chk_hndl == 'ext':
                assert isinstance(pval, str), '%s.%s expected a filepath '%(sect, varnm)
                if pval == '':
                    raise Error('must provided a valid \'%s.%s\' filepath'%(sect, varnm))
                assert os.path.exists(pval), '%s.%s passed invalid filepath: \'%s\''%(sect, varnm, pval)
                
                ext = os.path.splitext(os.path.split(pval)[1])[1]

                
                if isinstance(hvals, tuple):
                    assert ext in hvals, '%s.%s  unrecognized extension: %s'%( sect, varnm, ext)
                elif isinstance(hvals, str):
                    assert ext == hvals, '%s.%s  unrecognized extension: %s'%( sect, varnm, ext)
                else:
                    raise Error('%s.%s bad hvals'%sect, varnm)
                    
            
            else:
                raise Error('unrecognized check handle: %s'%chk_hndl)
        log.debug('%s.%s passed %i checks'%(sect, varnm, len(achk_d)))
        return
    

    def load_finv(self,#loading expo data
                   fp = None,
                   dtag = 'finv',
                   finv_exp_d = None, #finv expeectations
                   ):
        
        log = self.logger.getChild('load_finv')
        if fp is None: fp = getattr(self, dtag)
        if finv_exp_d is None: finv_exp_d = self.finv_exp_d
        cid = self.cid
        
        #======================================================================
        # precehcsk
        #======================================================================
        assert os.path.exists(fp), '%s got invalid filepath \n    %s'%(dtag, fp)
        #======================================================================
        # load it
        #======================================================================
        df_raw = pd.read_csv(fp, index_col=None)
        
        #======================================================================
        # check it
        #======================================================================
        assert cid in df_raw.columns, '%s missing index column \"%s\''%(dtag, cid)
        
        
        #======================================================================
        # clean it
        #======================================================================
        #df = df_raw
        df = df_raw.set_index(cid, drop=True).sort_index(axis=0)
        
        #======================================================================
        # post check
        #======================================================================
        
        #use expectation handles
        for coln, hndl_d in finv_exp_d.items():
            assert isinstance(hndl_d, dict)
            assert coln in df.columns, \
                '%s missing expected column \'%s\''%(dtag, coln)
            ser = df[coln]
            for hndl, cval in hndl_d.items():
                
                if hndl=='type':
                    assert np.issubdtype(ser.dtype, cval), '%s.%s bad type: %s'%(dtag, coln, ser.dtype)
                    
                    """
                    throwing  FutureWarning: Conversion of the second argument of issubdtype
                    
                    https://stackoverflow.com/questions/48340392/futurewarning-conversion-of-the-second-argument-of-issubdtype-from-float-to
                    """
                    
                elif hndl == 'contains':
                    assert cval in ser, '%s.%s should contain %s'%(dtag, coln, cval)
                else:
                    raise Error('unexpected handle: %s'%hndl)
        
        #======================================================================
        # set it
        #======================================================================
        self.cindex = df.index.copy() #set this for checks later
        self.data_d[dtag] = df
        
        log.info('finished loading %s as %s'%(dtag, str(df.shape)))
        

            
            
        
    def load_evals(self,#loading expo data
                   fp = None,
                   dtag = 'evals',
                   ):
        
        log = self.logger.getChild('load_evals')
        if fp is None: fp = getattr(self, dtag)

        #check load sequence
        assert os.path.exists(fp), '%s got invalid filepath \n    %s'%(dtag, fp)
        assert 'finv' in self.data_d, 'call load_finv first'
        
        #======================================================================
        # load it
        #======================================================================
        adf = pd.read_csv(fp)
        
        #======================================================================
        # precheck
        #======================================================================
        assert len(adf) ==1, 'expected only 1 row on aeps'
        

        #convert to a series
        aser_raw = adf.iloc[0,:]
        
        #======================================================================
        # check
        #======================================================================
        boolar = aser_raw == 0
        assert not boolar.any(), 'got some zeros in aep_ser'
        #======================================================================
        # convert
        #======================================================================
        #convert to aep
        if self.event_probs == 'ari':
            aep_ser = aser_raw.astype(int)
            aep_ser = 1/aep_ser
            log.info('converted %i aris to aeps'%len(aep_ser))
        elif self.event_probs == 'aep': 
            aep_ser = aser_raw.astype(float)
            pass
        else: 
            raise Error('unepxected event_probs key %s'%self.event_probs)
        
        #extreme to likely
        aep_ser = aep_ser.sort_values(ascending=True)
        aep_ser.name='aeps'
        #======================================================================
        # check range
        #======================================================================
        #check all aeps are below 1
        boolar = np.logical_and(
            aep_ser < 1,
            aep_ser > 0)
        
        assert np.all(boolar), 'passed aeps out of range'
        
        #======================================================================
        # #wrap
        #======================================================================
        log.debug('prepared aep_ser w/ %i: \n    %s'%(len(aep_ser), aep_ser.to_dict()))
        
        
        #self.aep_ser = aep_ser.sort_values()
        self.data_d[dtag] = aep_ser #setting for consistency. 
        
        self.expcols = aep_ser.index.copy() #set for later checks
        
    def load_expos(self,#loading any exposure type data (expos, or exlikes)
                   fp = None,
                   dtag = 'expos',
                   check_monot=False, #whether to check monotonciy
                   logger=None,
                   ):
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('load_expos')
        if fp is None: fp = getattr(self, dtag)
        cid = self.cid
        
        assert 'finv' in self.data_d, 'call load_finv first'
        #assert 'evals' in self.data_d, 'call load_aep first'
        #assert isinstance(self.expcols, pd.Index), 'bad expcols'
        assert isinstance(self.cindex, pd.Index), 'bad cindex'
        assert os.path.exists(fp), '%s got invalid filepath \n    %s'%(dtag, fp)
        #======================================================================
        # load it
        #======================================================================
        df_raw = pd.read_csv(fp, index_col=None)
        
        #======================================================================
        # precheck
        #======================================================================
        assert cid in df_raw.columns, '%s missing index column \"%s\''%(dtag, cid)
        assert df_raw.columns.dtype.char == 'O','bad event names on %s'%dtag
        
        #======================================================================
        # clean it
        #======================================================================
        df = df_raw.set_index(cid, drop=True).sort_index(axis=1).sort_index(axis=0)
        
        #======================================================================
        # postcheck
        #======================================================================
        """
        NO! exlikes generally is shorter
        allowing the expos to be larger than the finv 
        
        """
        #check cids
        miss_l = set(self.cindex).difference(df.index)
        assert len(miss_l) == 0, 'some assets on %s not found in finv'%dtag
        
        #check events
        """
        must match the aeps
        """
        if dtag == 'exlikes':
            miss_l = set(df.columns).difference(self.expcols)
        else:
            miss_l = set(self.expcols).difference(df.columns)
            
        assert len(miss_l) == 0, '%i events on \'%s\' not found in aep_ser: \n    %s'%(
            len(miss_l), dtag, miss_l)
        
        
        #check dtype of columns
        for ename, chk_dtype in df.dtypes.items():
            assert np.issubdtype(chk_dtype, np.number), 'bad dtype %s.%s'%(dtag, ename)
            
        #======================================================================
        # slice
        #======================================================================
        df = df.loc[self.cindex,:]
        
        #======================================================================
        # postcheck2
        #======================================================================
        booldf = df.isna()
        if booldf.any().any():
            """wsl nulls are left as such by build_depths()"""
            log.warning('\'%s\' got %i (of %i) null values'%(
                dtag, booldf.sum().sum(), booldf.size))
        
        assert np.array_equal(self.cindex, df.index), 'cid mismatch'
        

        if check_monot and 'evals' in self.data_d:
            self.check_monot(df, aep_ser = self.data_d['evals'])
            
        #for  percent inundation 
        if self.as_inun:
            booldf = df >1
            assert booldf.sum().sum()==0, \
                'for pct inundation got %i (of %i) exposure values great than 1'%(
                    booldf.sum().sum(), booldf.size)
                
            assert self.felv =='datum', 'felv must equal \'datum\' for pct inundation runs'

        #======================================================================
        # set it
        #======================================================================
        
        self.data_d[dtag] = df
        
        log.info('finished loading %s as %s'%(dtag, str(df.shape)))
        
    def load_exlikes(self,#loading any exposure type data (expos, or exlikes)
                     dtag = 'exlikes',
                   **kwargs
                   ):
        
        log = self.logger.getChild('load_exlikes')
        assert 'evals' in self.data_d, 'evals data set required with conditional exposure exlikes'
        aep_ser = self.data_d['evals']
        #======================================================================
        # load the data
        #======================================================================
        
        self.load_expos(dtag=dtag, **kwargs) #use the load_expos
        
        edf = self.data_d.pop(dtag)
        
        log.info('loading w/ %s'%str(edf.shape))
        #======================================================================
        # repair assets w/ missing secondaries
        #======================================================================
        #replace nulls w/ 1
        """better not to pass any nulls.. but if so.. should treat them as ZERO!!
        Null = no failure polygon = no failure
        also best not to apply precision to these values
        """
        booldf = edf.isna()
        if booldf.any().any():
            log.warning('got %i (of %i) nulls!... filling with zeros'%(booldf.sum().sum(), booldf.size))
        edf = edf.fillna(0.0)
        
        #==================================================================
        # check
        #==================================================================
        #check logic against aeps
        if aep_ser.is_unique:
            raise Error('passed exlikes, but there are no duplicated event: \n    %s'%aep_ser)
        

        #==================================================================
        # #add missing likelihoods
        #==================================================================
        """
        missing column = no secondary likelihoods at all for this event.
        all = 1
        """
        
        miss_l = set(self.expcols).difference(edf.columns)
        if len(miss_l) > 0:
            
            log.info('passed exlikes missing %i secondary exposure likelihoods... treating these as 1\n    %s'%(
                len(miss_l), miss_l))
            
            for coln in miss_l:
                edf[coln] = 1.0
            
        
    
        log.info('prepared edf w/ %s'%str(edf.shape))
        
        #==================================================================
        # check it
        #==================================================================

        
        #set it
        self.data_d[dtag] = edf
        
    def load_gels(self,#loading expo data
                   fp = None,
                   dtag = 'gels'):
        
        log = self.logger.getChild('load_gels')
        if fp is None: fp = getattr(self, dtag)
        cid = self.cid
        
        #======================================================================
        # precheck
        #======================================================================
        assert 'finv' in self.data_d, 'call load_finv first'
        assert isinstance(self.cindex, pd.Index), 'bad cindex'
        assert os.path.exists(fp), '%s got invalid filepath \n    %s'%(dtag, fp)
        assert not self.as_inun, 'loading ground els for as_inun =True is invalid'
        #======================================================================
        # load it
        #======================================================================
        df_raw = pd.read_csv(fp, index_col=None)
        
        #======================================================================
        # check it
        #======================================================================
        assert cid in df_raw.columns, '%s missing index column \"%s\''%(dtag, cid)
        assert len(df_raw.columns)==2, 'expected 1 column on gels, got %i'%len(df_raw.columns)
        
        #======================================================================
        # clean it
        #======================================================================
        #df = df_raw
        df = df_raw.set_index(cid, drop=True).sort_index(axis=0)
        
        df = df.rename(columns={df.columns[0]:'gels'}).round(self.prec)
        
        #slice down to cids in the cindex
        """requiring dmg and expos inputs to match
        allowing minor inputs to be sliced"""
        l = set(self.cindex.values).difference(df.index.values)
        assert len(l)==0, 'gels missing %i cids: %s'%(len(l), l)
        
        boolidx = df.index.isin(self.cindex.values)
        df = df.loc[boolidx, :]
        
        log.debug('sliced from %i to %i'%(len(boolidx), boolidx.sum()))
        
        #======================================================================
        # post checks
        #======================================================================
        #check cids
        assert np.array_equal(self.cindex, df.index), 'cid mismatch'

        
        #check dtype of columns
        for ename, chk_dtype in df.dtypes.items():
            assert np.issubdtype(chk_dtype, np.number), 'bad dtype %s.%s'%(dtag, ename)
            
        boolidx = df.iloc[:,0].isna()
        if boolidx.any():
            raise Error('got %i (of %i) null ground elevation values'%(boolidx.sum(), len(boolidx)))
        
        boolidx = df.iloc[:,0] < 0
        if boolidx.any():
            log.warning('got %i ground elevations below zero'%boolidx.sum())
        
        #======================================================================
        # set it
        #======================================================================
        self.data_d[dtag] = df
        
        log.info('finished loading %s as %s w/ \n    min=%.2f, mean=%.2f, max=%.2f'%(
            dtag, str(df.shape), df.min().min(), df.mean().mean(), df.max().max()))
        
        
    def load_dmgs(self,#loading any exposure type data (expos, or exlikes)
                   fp = None,
                   dtag = 'dmgs',
                   check_monot=False, #whether to check monotonciy
                   logger=None,
                   ):
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('load_dmgs')
        if fp is None: fp = getattr(self, dtag)
        cid = self.cid
        
        assert 'finv' in self.data_d, 'call load_finv first'
        assert 'evals' in self.data_d, 'call load_evals first'
        assert isinstance(self.expcols, pd.Index), 'bad expcols'
        assert isinstance(self.cindex, pd.Index), 'bad cindex'
        assert os.path.exists(fp), '%s got invalid filepath \n    %s'%(dtag, fp)
        #======================================================================
        # load it
        #======================================================================
        df_raw = pd.read_csv(fp, index_col=None)
        
        #======================================================================
        # precheck
        #======================================================================
        assert cid in df_raw.columns, '%s missing index column \"%s\''%(dtag, cid)
        assert df_raw.columns.dtype.char == 'O','bad event names on %s'%dtag
        

        
        #======================================================================
        # clean it
        #======================================================================
        df = df_raw.copy()
        #drop dmg suffix
        boolcol = df.columns.str.endswith('_dmg')
        enm_l = df.columns[boolcol].str.replace('_dmg', '').tolist()
        
        #rename these
        ren_d = dict(zip(df.columns[boolcol].values, enm_l))
        df = df.rename(columns=ren_d)
        
        
        df = df.set_index(cid, drop=True).sort_index(axis=0)
        
        df = df.round(self.prec)
        
        #======================================================================
        # postcheck
        #======================================================================
        assert len(enm_l) > 1, 'failed to identify sufficient damage columns'
        

        #check cid index match
        assert np.array_equal(self.cindex, df.index), \
            'provided \'%s\' index (%i) does not match finv index (%i)'%(dtag, len(df), len(self.cindex))
        
        #check events
        """
        must match the aeps
        """
        miss_l = set(self.expcols).difference(df.columns)
            
        assert len(miss_l) == 0, '%i events on \'%s\' not found in aep_ser: \n    %s'%(
            len(miss_l), dtag, miss_l)
        
        
        #check dtype of columns
        for ename, chk_dtype in df.dtypes.items():
            assert np.issubdtype(chk_dtype, np.number), 'bad dtype %s.%s'%(dtag, ename)
            
        
        #======================================================================
        # postcheck2
        #======================================================================
        if check_monot:
            self.check_monot(df, aep_ser = self.data_d['evals'])


        #======================================================================
        # set it
        #======================================================================
        
        self.data_d[dtag] = df
        
        log.info('finished loading %s as %s'%(dtag, str(df.shape)))
    
   
    def add_gels(self): #add gels to finv (that's heights)
        log = self.logger.getChild('add_gels')
        
        
        assert self.felv == 'ground'
        assert 'gels' in self.data_d
        assert 'finv' in self.data_d
        
        #======================================================================
        # get data
        #======================================================================
        gdf = self.data_d['gels']
        fdf = self.data_d.pop('finv')

        log.info('on dtm values %s and finv %s'%(str(gdf.shape), str(fdf.shape)))
        #==================================================================
        # checks
        #==================================================================
        #check length expectation
        assert 'gels' not in fdf.columns, 'gels already on fdf'
        
                
        #======================================================================
        # #do the join join
        #======================================================================
        fdf = fdf.join(gdf)
        
        log.debug('finished with %s'%str(fdf.shape))
        
        self.data_d['finv'] = fdf
            
        
        
    def build_exp_finv(self, #assemble the expanded finv
                    group_cnt = None, #number of groups to epxect per prefix
                    ):
        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('build_exp_finv')
        fdf = self.data_d['finv']
        cid, bid = self.cid, self.bid
        
        if group_cnt is None: group_cnt = self.group_cnt
        
        #======================================================================
        # group_cnt defaults
        #======================================================================
        assert isinstance(group_cnt, int)
        
        exp_fcolns = [cid, 'fscale', 'felv']
        if group_cnt == 2:
            pass
            
        elif group_cnt == 4:
            exp_fcolns = exp_fcolns + ['ftag', 'fcap']
            
        else:
            raise Error('bad group_cnt %i'%group_cnt)
            
        
        
        #======================================================================
        # precheck
        #======================================================================
        """do this in the loaders"""
        assert fdf.index.name == cid, 'bad index on fdf'
        
        #======================================================================
        # get prefix values
        #======================================================================
        #pull all the elv columns
        tag_coln_l = fdf.columns[fdf.columns.str.endswith('elv')].tolist()
        
        assert len(tag_coln_l) > 0, 'no \'elv\' columns found in inventory'
        assert tag_coln_l[0] == 'f0_elv', 'expected first tag column to be \'f0_elv\''
        
        #get nested prefix values
        prefix_l = [coln[:2] for coln in tag_coln_l]
        
        log.info('got %i prefixes: %s'%(len(prefix_l), prefix_l))
        
        
        #======================================================================
        # expand: nested entries---------------
        #======================================================================
        if len(prefix_l) > 1:
        
            #==================================================================
            # #loop and collected nests
            #==================================================================
            bdf = None
            
            for prefix in prefix_l:
                #identify prefix columns
                pboolcol = fdf.columns.str.startswith(prefix) #columns w/ prefix
                
                assert pboolcol.sum()>=group_cnt, 'prefix \'%s\' group_cnt %i != %i'%(
                    prefix, pboolcol.sum(), group_cnt)
                
                 
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
                
                
            #==================================================================
            # #add back in other needed columns
            #==================================================================
            boolcol = fdf.columns.isin(['gels']) #additional columns to pivot out
            
            if boolcol.any(): #if we are only linking in gels, these may not exist
                bdf = bdf.merge(fdf.loc[:, boolcol], on=cid, how='left',validate='m:1')
                
                log.debug('joined back in %i columns: %s'%(
                    boolcol.sum(), fdf.loc[:, boolcol].columns.tolist()))
            
            #wrap
            log.info('expanded inventory from %i nest sets %s to finv %s'%(
                len(prefix_l), str(fdf.shape), str(bdf.shape)))
        #======================================================================
        # expand: nothing nested
        #======================================================================
        elif len(prefix_l) == 1:
            log.info('no nested columns. using raw inventory')
            

            #identify and check prefixes
            prefix = prefix_l.pop(0)
            pboolcol = fdf.columns.str.startswith(prefix) #columns w/ prefix
            
            assert pboolcol.sum() == group_cnt, 'prefix \'%s\' group_cnt %i != %i'%(
                prefix, pboolcol.sum(), group_cnt)
                
            #build dummy bdf
            bdf = fdf.copy()
            bdf[cid] = bdf.index #need to duplicate it
            
            #fix the columns
            bdf.columns = bdf.columns.str.replace('%s_'%prefix, 'f')
            
            #reset the index
            bdf = bdf.reset_index(drop=True)
            
        else:
            raise Error('bad prefix match')
        
        #set indexers
        bdf[bid] = bdf.index
        bdf.index.name=bid
        
        #======================================================================
        # check
        #======================================================================
        miss_l = set(exp_fcolns).difference(bdf.columns)
        assert len(miss_l) == 0
        
        
        #======================================================================
        # adjust fscale--------------
        #======================================================================
        boolidx = bdf['fscale'].isna()
        if boolidx.any():
            log.info('setting %i null fscale values to 1'%boolidx.sum())
            bdf.loc[:, 'fscale'] = bdf['fscale'].fillna(1.0)
            
        
        #======================================================================
        # convert heights ----------
        #======================================================================
        s = bdf.loc[:, 'felv']
        
        log.info('\'%s\' felv: \n    min=%.2f, mean=%.2f, max=%.2f'%(
             self.felv, s.min(), s.mean(), s.max()))
            
        if self.felv == 'ground':
            assert not self.as_inun
            assert 'gels' in bdf.columns, 'missing gels column'            
            assert bdf['gels'].notna().all()


            bdf.loc[:, 'felv'] = bdf['felv'] + bdf['gels']
                
            #log.info('converted asset ground heights to datum elevations')
            s = bdf.loc[:, 'felv']
            
            log.info('converted felv to \'datum\' \n    min=%.2f, mean=%.2f, max=%.2f'%(
                 s.min(), s.mean(), s.max()))
            
        elif self.felv=='datum':
            log.debug('felv = \'%s\' no conversion'%self.felv)
        else:
            raise Error('unrecognized felv=%s'%self.felv)
        
        #======================================================================
        # wrap
        #======================================================================
        log.info('finished with %s'%str(bdf.shape))
        self.bdf = bdf
        
        
        
        
    def build_depths(self): #build the expanded depths data
        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('build_depths')
        bdf = self.bdf.copy() #expanded finv
        cid, bid = self.cid, self.bid


        wdf = self.data_d['expos'] #wsl

        #======================================================================
        # expand
        #======================================================================
        #get the indexers from the expanded finv
        edx_df = self.bdf.loc[:, [bid, cid]]
        
        #pivot these out to bids
        ddf = edx_df.join(wdf.round(self.prec),  on=cid
                                          ).set_index(bid, drop=False)
                                          
        #=======================================================================
        # precheck
        #=======================================================================
        if self.as_inun:
            boolidx = bdf['felv'] !=0
            if not boolidx.sum().sum() == 0:
                raise Error('with as_inun=True got %i (of %i) elv values with non-zero depths'%(
                    boolidx.sum().sum(), boolidx.size))

        #======================================================================
        # calc depths
        #======================================================================
        #loop and subtract to get depths
        boolcol = ~ddf.columns.isin([cid, bid]) #columns w/ depth values
        
        for coln in ddf.columns[boolcol]:
            ddf.loc[:, coln] = (ddf[coln] - bdf['felv']).round(self.prec)

            """
            maintains nulls
            """
            
        log.debug('converted wsl to depth %s'%str(ddf.shape))
        
        
        #======================================================================
        # fill nulls
        #======================================================================
        """no! dont want to mix these up w/ negatives.
        filtering nulls in risk1.run() and dmg2.bdmg()
        booldf = ddf.drop([bid, cid], axis=1).isna()
        if booldf.any().any():
            log.warning('setting %i (of %i) null depth values to zero'%(
                booldf.sum().sum(), booldf.size))
            
            ddf = ddf.fillna(0.0)"""
        
        #======================================================================
        # negative depths
        #======================================================================
        booldf = ddf.loc[:,boolcol] < 0 #True=wsl below ground
        
        if booldf.any().any():
            assert not self.as_inun
            """
            note these are un-nesetd assets, so counts will be larger than expected
            """
            #user wants to ignore ground_water, set all negatives to zero
            if not self.ground_water:
                log.warning('setting %i (of %i) negative depths to zero'%(
                    booldf.sum().sum(), booldf.size))
                
                """NO! filtering negatives during dmg2.bdmg()
                ddf.loc[:, boolcol] = ddf.loc[:,boolcol].where(~booldf, other=0)"""
                
            #user wants to keep negative depths.. leave as is
            else:
                log.info('gorund_water=True. preserving %i (of %i) negative depths'%(
                    booldf.sum().sum(), booldf.size))
            
        #======================================================================
        # post checks
        #======================================================================
                
        assert np.array_equal(ddf.index, bdf.index)        
        assert bid in ddf.columns
        assert ddf.index.name == bid
        assert np.array_equal(ddf.index.values, ddf[bid].values)
        
        #max depth
        boolidx = ddf.loc[:,boolcol].max(axis=1)>self.max_depth
        if boolidx.any():
            log.debug('\n%s'%ddf[boolidx])
            raise Error('%i (of %i) nested curves exceed max depth: %.2f. see logger'%(
                boolidx.sum(), len(boolidx), self.max_depth))
        
        
                
        #======================================================================
        # wrap
        #======================================================================
        log.info('assembled depth_df w/ \nmax:\n%s\nmean: \n%s'%(
            ddf.loc[:,boolcol].max(),
            ddf.loc[:,boolcol].mean()
            ))
        
        self.ddf = ddf
        

        
        
    def resolve_multis(self, #selecting maximum expected value for repeat events
                       ddf, #damages per event
                       edf, #secondary liklihoods per event
                       aep_ser,
                       logger):
        """
        selecting maximum expected value for repeat events
        
        CanFlood selects the maximum expected value of impacts per asset from the duplicated events.
        e.g. resolved damage = max(damage w/o fail, damage w/ fail * fail prob)
        
        
        we accept multiple exposure sets for a single event likelihood (
        e.g. 'failure' raster and 'no fail').
        Each event can be assigned conditional probabilities in the edf
        

        """
        #======================================================================
        # setup
        #======================================================================
        log = logger.getChild('resolve_multis')
        
        #======================================================================
        # precheck
        #======================================================================
        aep_ser = aep_ser.astype(float)
        
        if len(aep_ser.unique()) == len(aep_ser):
            raise Error('resolving multi but there are no duplicated events')
        

        #======================================================================
        # get expected values of all damages
        #======================================================================
        assert ddf.shape == edf.shape, 'shape mismatch'
        """where edf > 0 ddf should also be > 0
        but leave this check for the input validator"""
        evdf = ddf*edf
        
        log.info('calculating expected values for %i damages'%evdf.size)
        assert not evdf.isna().any().any()
        #======================================================================
        # loop by unique aep and resolve
        #======================================================================
        res_df = pd.DataFrame(index=evdf.index, columns = aep_ser.unique().tolist())
        
        for indxr, aep in enumerate(aep_ser.unique().tolist()):
            self.feedback.setProgress((indxr/len(aep_ser.unique())*80))
            assert isinstance(aep, float)
            #==================================================================
            # get these events
            #==================================================================
            #find event names at this aep
            boolar = aep_ser == aep
            
            #handle by match count
            if boolar.sum() == 0:
                raise Error('problem with event matching')
            
            #get these event names
            evn_l = aep_ser.index[boolar].tolist()
            
            #==================================================================
            # resolve
            #==================================================================
            log.debug('resolving with %i event names: %s'%(len(evn_l), evn_l))
            #only 1 event.. nothing to resolve
            if len(evn_l) == 1:
                """
                possible if a hazard layer doesn't have a corresponding failure layer
                """
                log.warning('only got 1 event \'%s\' for aep %.2e'%(
                    aep_ser.index[boolar].values, aep))
                
                #use these
                res_df.loc[:, aep] =  evdf.loc[:, evn_l].iloc[:, 0]
            
            #multiple events... take maximum
            else:
                log.info('resolving alternate damages for aep %.2e from %i events: \n    %s'%(
                    aep, len(evn_l), evn_l))
                
                res_df.loc[:, aep] = evdf.loc[:, evn_l].max(axis=1)
                
            if res_df[aep].isna().any():
                print('yay')
                raise Error('got nulls on %s'%aep)
                
        #======================================================================
        # warp
        #======================================================================
        if not res_df.notna().all().all():
            raise Error('got %i nulls'%res_df.isna().sum().sum())
        
        log.info('resolved to %i unique event damages'%len(res_df.columns))
        
        return res_df.sort_index(axis=1)
    
    #==========================================================================
    # validators-----------
    #==========================================================================
    
    def check_monot(self,
                     df_raw, #event:asset like data. expectes columns as aep 
                     split_key = False, #optional key to split hazard columns with (for fail/noFail sets)
                     aep_ser=None, event_probs = 'aep', #optional kwargs for column conversion
                     logger=None
                     ):
        """
        if damages are equal the warning will be thrown
        
        todo: store this as an output
        """
        
        
        #======================================================================
        # defaults
        #======================================================================
        
        if logger is None: logger=self.logger
        if split_key is None: split_key = self.split_key
        log = logger.getChild('check_monot')
        
        #======================================================================
        # worker func
        #======================================================================
        def chk_func(df_raw, log):
        
            #======================================================================
            # convresions
            #======================================================================
            if not aep_ser is None:
                df, d = self.conv_expo_aep(df_raw, aep_ser, event_probs=event_probs, logger=log)
            else:
                df = df_raw.copy()
            
            log.debug('on %s w/ cols: \n    %s'%(str(df.shape), df.columns.tolist()))
            #======================================================================
            # prechecks
            #======================================================================
            
            assert np.issubdtype(df.columns.dtype, np.number)
            """should be ok
            assert np.all(df.notna()), 'got some nulls'"""
            assert df.columns.is_monotonic_increasing #extreme to likely
            assert df.columns.max() <1
            
            #======================================================================
            # clean
            #======================================================================
            if df.isna().any().any():
                log.warning('replacing %i nulls w/ zeros for check'%df.isna().sum().sum())
                df = df.fillna(0).copy()
                
            #======================================================================
            # check
            #======================================================================
            """
                    #apply the ead func
            df.loc[boolidx, 'ead'] = df.loc[boolidx, :].apply(
                self.get_ev, axis=1, dx=dx)
            """
            def chk_func(ser):
                return ser.is_monotonic_decreasing
        
            #check for damage monotonicity (should go from left BIG/extreme to right small/likely
            """
            view(df)
            view(df[boolidx])
            """
            #get offenders (from 
            boolidx = np.logical_and(
                ~df.apply(chk_func, axis=1), #NOT going left big to righ textreme
                df.nunique(axis=1) > 1, #only one value per row
                )
    
            if boolidx.any():
                with pd.option_context(
                                'display.max_rows', None, 
                               'display.max_columns', None,
                               #'display.height',1000,
                               'display.width',1000):
                        
                    log.debug('\n%s'%df.loc[boolidx, :])
                    log.debug('\n%s'%df[boolidx].index.tolist())
                    log.warning(' %i (of %i)  assets have non-monotonic-increasing damages. see logger'%(
                        boolidx.sum(), len(boolidx)))
                
                return False
            else:
                log.debug('all %i passed'%len(df))
                return True
        
        #======================================================================
        # splitting
        #======================================================================
        if not split_key == False:
            boolcol = df_raw.columns.str.contains(split_key)
            
            if not boolcol.any():
                raise Error('failed to split events by \"%s\''%split_key)
            
            res1 = chk_func(df_raw.loc[:,boolcol], log.getChild(split_key))
            res2 = chk_func(df_raw.loc[:,~boolcol], log.getChild('no%s'%split_key))
            
            result = res1 and res2
            
        else:
            result= chk_func(df_raw, log)
            
        return result
            

    def calc_ead(self,
                 df_raw, #xid: aep
                 ltail = None,
                 rtail = None,
                 drop_tails = False, #whether to remove the dummy tail values from results
                 logger = None
                 ):      
        
        """
        #======================================================================
        # inputs
        #======================================================================
        ltail: left tail treatment code (low prob high damage)
            flat: extend the max damage to the zero probability event
            extrapolate: extend the fucntion to the zero aep value
            float: extend the function to this damage value (must be greater than max)
            none: don't extend the tail (not recommended)
            
        rtail: right trail treatment (high prob low damage)
            extrapolate: extend the function to the zero damage value
            float: extend the function to this aep
            none: don't extend (not recommended)

        
        """
        #======================================================================
        # setups and defaults
        #======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('calc_ead')
        if ltail is None: ltail = self.ltail
        if rtail is None: rtail = self.rtail
        
        #format tail values
        
        if not ltail in ['flat', 'extrapolate', 'none']:
            ltail  = float(ltail)
        if not rtail in ['extrapolate', 'none']:
            rtail = float(rtail)
            
        log.info('getting ead on %s w/ ltail=%s and rtail=%s'%(
            str(df_raw.shape), ltail, rtail))
        
        #identify columns to calc ead for
        boolidx = (df_raw > 0).any(axis=1) #only want those with some real damages
        
        #======================================================================
        # left tail-------------
        #======================================================================
        df = df_raw.copy()
        #flat projection
        if ltail == 'flat':
            df.loc[:,0] = df.iloc[:,0] 
            
        elif ltail == 'extrapolate':
            df.loc[boolidx,0] = df.loc[boolidx, :].apply(
                self.extrap, axis=1, left=True)

        elif isinstance(ltail, float):
            """this cant be a good idea...."""
            df.loc[boolidx,0] = ltail
        elif ltail == 'none':
            pass
        else:
            raise Error('unexected ltail key'%ltail)
        
        #======================================================================
        # right tail------------
        #======================================================================
        if rtail == 'extrapolate':
            """just using the average for now...
            could extraploate for each asset but need an alternate method"""
            aep_ser = df.loc[boolidx, :].apply(
                self.extrap, axis=1, left=False)
            
            aep_val = round(aep_ser.mean(), 5)
            
            assert aep_val > df.columns.max()
            
            df.loc[boolidx, aep_val] = 0
            
            log.info('using right intersection of aep= %.2e from average extraploation'%(
                aep_val))
        
        elif isinstance(rtail, float):
            aep_val = round(rtail, 5)
            assert aep_val > df.columns.max()
            
            df.loc[boolidx, aep_val] = 0
            
            log.info('using right intersection of aep= %.2e from user val'%(
                aep_val))
            
            
            
        elif rtail == 'none':
            log.warning('passed \'none\' no right tail set!')
        
        else:
            raise Error('unexpected rtail %s'%rtail)
            
        
        
        df = df.sort_index(axis=1)
        
        #======================================================================
        # check monoticiy again
        #======================================================================
        #check for damage monoticyt
        cboolidx = df.apply(lambda x: x.is_monotonic_increasing, axis=1)
        if cboolidx.any():
            log.debug(df.loc[cboolidx, :])
            raise Error(' %i (of %i)  assets have non-monotonic-increasing damages. see logger'%(
                cboolidx.sum(), len(cboolidx)))
            
            
        #======================================================================
        # get ead per row
        #======================================================================
        #get reasonable dx (integrating along damage axis)
        dx = df.max().max()/100
        
        #re-arrange columns so x is ascending
        df = df.sort_index(ascending=False, axis=1)
        
        #apply the ead func
        df.loc[boolidx, 'ead'] = df.loc[boolidx, :].apply(
            self.get_ev, axis=1, dx=dx)
        
        
        df.loc[:, 'ead'] = df['ead'].fillna(0) #fill remander w/ zeros
        
        #======================================================================
        # check it
        #======================================================================
        boolidx = df['ead'] < 0
        if boolidx.any():
            log.warning('got %i (of %i) negative eads'%( boolidx.sum(), len(boolidx)))
        
        #======================================================================
        # clean results
        #======================================================================
        if drop_tails:
            res_df = df_raw.join(df['ead'].round(self.prec))
        else:
            res_df = df
            

        
        
        return res_df

    def extrap(self, 
               ser, #row of dmages (y values) from big df
               left=True, #whether to extraploate left or gihtt
               ):
        
        #build interpolation function from data
        if left:
            #xvalues = aep
            f = interpolate.interp1d(ser.index.values, ser.values, 
                                     fill_value='extrapolate')
            
        else:
            #xvalues = damages
            f = interpolate.interp1d( ser.values, ser.index.values,
                                     fill_value='extrapolate')
            
        
        #calculate new y value by applying interpolation function
        result = f(0)
        
        return float(result) 
    
    def get_ev(self, 
               ser, #row from damage results
               dx = 0.1,
               ):
        """
        should integrate along the damage axis (0 - infinity)
        """
        
        
        #print('%i.%s    %s'%(self.cnt, ser.name, ser.to_dict()))
        
        x = ser.tolist()
        y = ser.index.tolist()
        
        #======================================================================
        # ser_inv = ser.sort_index(ascending=False)
        # 
        # x = ser_inv.tolist()
        # y = ser_inv.index.tolist()
        # 
        #======================================================================
        if self.integrate == 'trapz':
        
            ead_tot = integrate.trapz(
                y, #yaxis - aeps
                x=x, #xaxis = damages 
                dx = dx)
            
        elif self.integrate == 'simps':
            self.logger.warning('integration method not tested')
            
            ead_tot = integrate.simps(
                y, #yaxis - aeps
                x=x, #xaxis = damages 
                dx = dx)
            
        else:
            raise Error('integration method \'%s\' not recognized'%self.integrate)
            
        
        #======================================================================
        # np.trapz(x, x=y)
        # 
        # np.trapz(y, x=x, dx=4000)
        # 
        # if ead_tot < 0:
        #     raise Error('bad ead tot')
        #======================================================================
        return ead_tot
    
    def risk_plot(self, #generate and save a figure that summarizes the damages 
                  dmg_ser = None,
                  
                  #labels
                  xlab='ARI', y1lab=None, y2lab='AEP',
                  
                  #format controls
                  grid = True, logx = False, 
                  basev = 1, #base value for dividing damage values
                  dfmt = None, #formatting of damage values 
                  
                  
                  #figure parametrs
                figsize     = (6.5, 4), 
                    
                #hatch pars
                    hatch =  None,
                    h_color = 'blue',
                    h_alpha = 0.1,
                  ):
        
        """
        TODO: fix the title
        
        """
        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('risk_plot')
        if dmg_ser is None: dmg_ser = self.res_ser
        if dfmt is None: dfmt = self.plot_fmt
        if y1lab is None: y1lab = self.y1lab
        #======================================================================
        # precheck
        #======================================================================
        assert isinstance(dmg_ser, pd.Series)
        assert 'ead' in dmg_ser.index, 'dmg_ser missing ead index'
        #======================================================================
        # setup
        #======================================================================
        
        import matplotlib
        matplotlib.use('SVG') #sets the backend (case sensitive)
        import matplotlib.pyplot as plt
        
        #set teh styles
        plt.style.use('default')
        
        #font
        matplotlib_font = {'family' : 'serif',
                'weight' : 'normal',
                'size'   : 8}
        
        matplotlib.rc('font', **matplotlib_font)
        matplotlib.rcParams['axes.titlesize'] = 10 #set the figure title size
        
        #spacing parameters
        matplotlib.rcParams['figure.autolayout'] = False #use tight layout
        
        #======================================================================
        # data manipulations
        #======================================================================
        #get ead
        ead_tot = dmg_ser['ead']
        del dmg_ser['ead'] #remove it from plotter values
        
        
        #get damage series to plot
        ar = np.array([dmg_ser.index, dmg_ser.values]) #convert to array
        
        #invert aep (w/ zero handling)
        ar[0] = 1/np.where(ar[0]==0, #replaced based on zero value
                           sorted(ar[0])[1]/10, #dummy value for zero (take the second smallest value and divide by 10)
                           ar[0]) 
        
        dmg_ser = pd.Series(ar[1], index=ar[0], dtype=float) #back into series
        dmg_ser.index = dmg_ser.index.astype(int) #format it
                
        
        #get aep series
        aep_ser = dmg_ser.copy()
        aep_ser.loc[:] = 1/dmg_ser.index
        
        
        #======================================================================
        # labels
        #======================================================================
        
        val_str = 'total Annualized = ' + dfmt.format(ead_tot/basev)
        
        title = 'CanFlood \'%s.%s\' Annualized-%s plot on %i events'%(self.name,self.tag, xlab, len(dmg_ser))
        
        #======================================================================
        # figure setup
        #======================================================================
        plt.close()
        fig = plt.figure(1)
        fig.set_size_inches(figsize)
        
        #axis setup
        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx()
        ax1.set_xlim(max(aep_ser.index), 1) #aep limits 
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_ylabel(y1lab)
        ax2.set_ylabel(y2lab)
        ax1.set_xlabel(xlab)
        
        #======================================================================
        # fill the plot
        #======================================================================
        #damage plot
        xar,  yar = dmg_ser.index.values, dmg_ser.values
        pline1 = ax1.semilogx(xar,yar,
                            label       = y1lab,
                            color       = 'black',
                            linestyle   = 'dashdot',
                            linewidth   = 2,
                            alpha       = 0.5,
                            marker      = 'x',
                            markersize  = 2,
                            fillstyle   = 'full', #marker fill style
                            )
        #add a hatch
        polys = ax1.fill_between(xar, yar, y2=0, 
                                color       = h_color, 
                                alpha       = h_alpha,
                                hatch       = hatch)
        
        #aep plot
        xar,  yar = aep_ser.index.values, aep_ser.values
        pline2 = ax2.semilogx(xar,yar,
                            label       = y2lab,
                            color       = 'blue',
                            linestyle   = 'dashed',
                            linewidth   = 1,
                            alpha       = 1,
                            marker      = 'x',
                            markersize  = 0,
                            )
        

        
        #=======================================================================
        # Add text string 'annot' to lower left of plot
        #=======================================================================
        xmin, xmax1 = ax1.get_xlim()
        ymin, ymax1 = ax1.get_ylim()
        
        x_text = xmin + (xmax1 - xmin)*.1 # 1/10 to the right of the left ax1is
        y_text = ymin + (ymax1 - ymin)*.1 #1/10 above the bottom ax1is
        anno_obj = ax1.text(x_text, y_text, val_str)
        
        #=======================================================================
        # format axis labels
        #======================================================= ================
        #damage values (yaxis for ax1)
        old_tick_l = ax1.get_yticks() #get teh old labels
         
        # build the new ticks
        l = [dfmt.format(value/basev) for value in old_tick_l]
              
        #apply the new labels
        ax1.set_yticklabels(l)
        
        
        
        #ARI (xaxis for ax1)
        ax1.get_xaxis().set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        #=======================================================================
        # post formatting
        #=======================================================================
        if grid: ax1.grid()
        

        #legend
        h1, l1 = ax1.get_legend_handles_labels() #pull legend handles from axis 1
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1+h2, l1+l2, loc=2) #turn legend on with combined handles
        
        return fig
    
    
    def conv_expo_aep(self, #converting exposure data set to aep column values 
                      df, 
                      aep_ser,
                      event_probs = 'aep',
                      logger = None,):
        
        if logger is None: logger = self.logger
        log = self.logger.getChild('conv_expo_aep')
        
        assert isinstance(aep_ser, pd.Series)
        
        assert len(df.columns) > 0
        assert np.issubdtype(aep_ser.dtype, np.number)
        
        miss_l = set(df.columns).difference(aep_ser.index)
        assert len(miss_l) == 0, 'some event columns in the ddf not in the aep'
        
        #slice down aep_ser
        aep_ser = aep_ser
        
        aep_ser = aep_ser[aep_ser.index.isin(df.columns)]
        
        
        if not aep_ser.is_unique:
            raise Error('only setup for unique aeps')
        
        #======================================================================
        # conversions
        #======================================================================
        if event_probs == 'ari':
            aep_ser = 1/aep_ser
            log.info('converted %i aris to aeps'%len(aep_ser))
        elif event_probs == 'aep':
            pass
        else:
            raise Error('unrecognized event_probs')
        
        #most extreme events from left to right (less extreme)
        df1 = df.rename(columns = aep_ser.to_dict()).sort_index(axis=1, ascending=True)
        
        return df1, aep_ser.to_dict()
            
            
        
    def force_monot(self, #forcing monotoncity on an exposure data set
                   df_raw,
                   aep_ser = None, #optional aep_ser to format here
                   event_probs = 'ari',
                   logger = None,
                   ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('force_monot')
        
        assert isinstance(df_raw, pd.DataFrame)
        
        log.info('on %s'%str(df_raw.shape))
        
        #======================================================================
        # convresions
        #======================================================================
        if not aep_ser is None:
            df, d = self.conv_expo_aep(df_raw, aep_ser, event_probs=event_probs, logger=log)
            
            #get conversion dict to map it back at the end

            rename_d = dict(zip(d.values(),d.keys()))
            
        else:
            rename_d = dict()
            df = df_raw.copy()
            
            
        #======================================================================
        # checks
        #======================================================================
        assert np.issubdtype(df.columns.dtype, np.number)
        """should be ok
        assert np.all(df.notna()), 'got some nulls'"""
        assert df.columns.is_monotonic_increasing #extreme to likely
        assert df.columns.max() <1


        #======================================================================
        # identify offenders
        #======================================================================
        boolidx1 = ~df.apply(lambda x: x.is_monotonic_decreasing, axis=1)
        boolidx2 = df.nunique(axis=1, dropna=False) > 1
        
        """
        212 in df[boolidx1].index
        212 in df[boolidx2].index
        
        df.loc[[212, 1462],:].nunique(axis=1, dropna=False) >1
        
        """
        #get offenders (from 
        boolidx = np.logical_and(
            boolidx1, #NOT going left big to righ textreme
            boolidx2, #more than 1 value per row
            )
        
        if not boolidx.any():
            raise Error('no offending entries!')
        
        log.info('fixing %i (of %i) non-monos'%(boolidx.sum(), len(boolidx)))
        
        #======================================================================
        # apply
        #======================================================================
        def force_mo(ser):
            #get first non-null
            first = True
            for indxr, val in ser[ser.notna().idxmax():].items():
                if first:
                    lval = val
                    first=False
                    continue
                
                if pd.isnull(val):
                    ser.loc[indxr] = lval
                elif val < lval:
                    ser.loc[indxr] = lval
                else:
                    lval = val
                    
            #check
            if not ser.dropna().is_monotonic_increasing:
                raise Error('failed')
            
                    
            return ser
                

                
        #flip the column order (likely -> extreme)
        df = df.sort_index(axis=1, ascending=False)
        
        #apply the forcing
        res_df = df.copy()
        res_df.loc[boolidx,:] = res_df[boolidx].apply(force_mo, axis=1)
        
        #flip columns back
        res_df = res_df.sort_index(axis=1, ascending=True)
        
        """
        212 in res_df[boolidx].index
        """
        
        #======================================================================
        # check it
        #======================================================================
        if not self.check_monot(res_df):
            raise Error('failed to fix')
        
        log.info('finished')
        """
        view(res_df)
        """
        
        
        return res_df.rename(columns=rename_d)
        

if __name__ =="__main__":
    

    """checking monotonocity
    #==========================================================================
    # chekc failure events
    #==========================================================================
    log = mod_logger.getChild('fail')
    log.info('testing failures')
    boolcol = ddf_raw.columns.str.contains('fail')
    
    assert boolcol.sum() <= len(ddf_raw.columns)/2
     
    ddf = ddf_raw.loc[:, boolcol]
    aep_ser = adf.iloc[0, adf.columns.isin(ddf.columns)].astype(int).sort_values().copy()
      
  
    wrkr.check_monot(ddf, aep_ser, logger=log)
    
    
    #==========================================================================
    # check normal events
    #==========================================================================
    log = mod_logger.getChild('norm')
    log.info('testing normal events')
    ddf = ddf_raw.loc[:, ~boolcol]
    aep_ser = adf.iloc[0, adf.columns.isin(ddf.columns)].astype(int).sort_values()
    
    wrkr.check_monot(ddf, aep_ser, logger=log)
    
    
    #==========================================================================
    # check exlikes
    #==========================================================================
    exdf = pd.read_csv(exl_fp).set_index(cid)
    aep_ser = adf.iloc[0, adf.columns.isin(exdf.columns)].astype(int).sort_values()
     
    wrkr.check_monot(exdf, aep_ser, logger=log)
    """
    
    
    
    print('finished')
    
    
    
    
    
    
    
    
    
    