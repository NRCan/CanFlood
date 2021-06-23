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

import configparser, os, inspect, logging, copy, itertools, datetime
import pandas as pd
idx = pd.IndexSlice
import numpy as np



#==============================================================================
# custom
#==============================================================================

mod_logger = logging.getLogger('common') #get the root logger

from hlpr.exceptions import QError as Error
    
from hlpr.basic import ComWrkr, view


#==============================================================================
# class-----------
#==============================================================================
class Model(ComWrkr,
            #Plotr #making each child inherit this speifically
                #keeps damage modeuls without plotting a bit simpler
            ):
    """
    common methods for model classes
    
    
    Control File Parameters:
    [parameters]
        
        name -- name of the scenario/model run
        
        cid -- index column for the 3 inventoried data sets (finv, expos, gels)
        
        prec -- float precision for calculations
        
        ground_water -- flag to include negative depths in the analysis
        
        felv -- 'datum' or 'ground': whether felv values provided in the
                     inventory are heights or elevations

        event_probs -- format of event probabilities (in 'evals' data file) 
                        (default 'ari')
                        
            'aep'           event probabilities in aeps file expressed as 
                            annual exceedance probabilities
            'ari'           expressed as annual recurrance intervals
            
        
        ltail -- zero probability event  handle  (default 'extrapolate')
            'flat'           set the zero probability event equal to the most 
                            extreme impacts in the passed series
            'extrapolate'    set the zero probability event by extrapolating from 
                            the most extreme impact (interp1d)
            'none'           do not extrapolate (not recommended)
            float            use the passed value as the zero probability impact value
             
        
        rtail -- zreo impacts event  handle    (default float(0.5))
            'extrapolate'    set the zero impact event by extrapolating from the 
                            least extreme impact
            'none'            no enforcing of a zero impact event (not recommended)
            'flat'           duplicates the minimum AEP as the zero damage event 
            float           use the passed value as the zero impacts aep value
        
        drop_tails -- EAD extrapolation: whether to remove the extrapolated values
                         before writing the per-asset results (default: False)
        
        integrate -- numpy integration method to apply (default 'trapz')

        as_inun    -- flag whether to treat exposures as %inundation
        
        event_rels -- assumption for calculated expected value on complex events
            #max:  maximum expected value of impacts per asset from the duplicated events
                #resolved damage = max(damage w/o fail, damage w/ fail * fail prob)
                #default til 2020-12-30
            #mutEx: assume each event is mutually exclusive (only one can happen)
                #lower bound
            #indep: assume each event is independent (failure of one does not influence the other)
                #upper bound
                
        impact_units -- value to label impacts axis with (generally set by Dmg2)
        
        apply_miti -- whether to apply mitigation algorthihims

            
            
        
    [dmg_fps]
        

        
    [risk_fps]
        dmgs -- damage data results file path (default N/A)
            
        exlikes -- secondary exposure likelihood data file path (default N/A)
        
        evals -- event probability data file path (default N/A)
        
    [validation]
        risk2 -- Risk2 validation flag (default False)
        
    [results_fps]
        attrimat02 -- lvl2 attribution matrix fp (post dmg model)
        attrimat03 -- lvl3 attribution matrix fp (post risk model)
        r_passet -- per_asset results from the risk2 model
        r_ttl  -- total results from risk2
        eventypes -- df of aep, noFail, and rEventName
    
    
    [plotting]
        impactfmt_str -- python formatter to use for formatting the impact results values
    
    """
    
    #==========================================================================
    # parameters from control file
    #==========================================================================
    #[parameters]
    #name = '' #moved to COmWrkr
    cid = ''
    prec = 2
    ground_water = False
    felv = ''
    event_probs = 'ari'
    ltail = None
    rtail = None
    drop_tails = True
    integrate = 'trapz'
    as_inun = False
    event_rels = 'max'

    impact_units = 'impacts'
    apply_miti = False 


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
    
    #[results_fps]
    attrimat02=''
    attrimat03=''
    r_passet=''
    r_ttl =''
    eventypes=''
    
    #[plotting]
    """see Plotr"""
    
    
    #===========================================================================
    # expectations (overwritten by parent)
    #===========================================================================
    dtag_d = { #loading data from the control file
        'finv':{'index_col':0},
        'evals':{'index_col':None},
        'gels':{'index_col':0},
        }
        
    valid_par = None
    
    #==========================================================================
    # program vars
    #==========================================================================
    #minimum inventory expectations
    finv_exp_d = {
        'scale':{'type':np.number},
        'elv':{'type':np.number}
        }
    
    max_depth = 20 #maximum depth for throwing an error in build_depths()
    
    
    cplx_evn_d = None #complex event sets {aep: [exEventName1, exEventName1]}
    asset_cnt = 0 #for plotting
    scen_ar_d = dict() #container for empty scenario matrix
    exn_max = 0 #for models w/ failre.. maximum complex count. see ev_multis()
    

    #===========================================================================
    # field names
    #===========================================================================
    bid = 'bid' #indexer for expanded finv
    miLtcn = 'mi_Lthresh'
    miUtcn = 'mi_Uthresh'
    miVcn = 'mi_iVal'
    miScn = 'mi_iScale'
    

    def __init__(self,
                 cf_fp='', #control file path TODO: make this a kwarg
                    #note: this could also be attached by basic.ComWrkr.__init__()
                    #now that this is a parent... wish this was a kwarg
                 
                 split_key=None,#for checking monotonicy on exposure sets with duplicate events
                 
                 base_dir =None, #for absolute_fp=False, base directory to use (defaults 
                 attriMode = False, #flow control for some attribution matrix functions
                 upd_cf = True, #control ssome updating of control file writes
                 
                 **kwargs):
        
        #=======================================================================
        # precheck
        #=======================================================================
        #mod_logger.debug('Model.__init__ start')
        """no.. letting dummy cf_fps get passed
        assert os.path.exists(cf_fp), 'bad control filepath: %s'%cf_fp"""
        
        #=======================================================================
        # parent setup
        #=======================================================================
        super().__init__(cf_fp=cf_fp, **kwargs) #initilzie teh baseclass
        
        """have to call on child's init
        self._init_plt() #setup matplotlib"""
        
        #=======================================================================
        # attachments
        #=======================================================================
        """ moved to Comwrkr
        self.cf_fp = cf_fp"""
        self.split_key= split_key 
        
        if base_dir is None:
            base_dir = os.path.split(cf_fp)[0]
        self.base_dir = base_dir
        
        
        self.attriMode=attriMode
        self.upd_cf=upd_cf


        """moved to comWrkr
        self.data_d = dict() #dictionary for loaded data sets"""
        
        """weird behavior on shared classes otherwise"""
        self.extrap_vals_d = {} #extraploation used {aep:val}
        
        self.raw_d = dict() #container for raw data
        #=======================================================================
        # wrap
        #=======================================================================
        
        self.logger.debug('finished Model.__init__')
        
        
    def setup(self): #standard setup sequence
        
        self.init_model() #attach control file
        
        self.load_df_ctrl()  #load data from control file
        
        self.prep_model() 
        
        return self
    
    def setup_fromData(self, #setup the model from loaded data 
                      data,
                      logger=None,
                      prep_kwargs={},
                      ):
        """typically for linked sessions"""
        
        if logger is None: logger=self.logger
        log = logger.getChild('setup')
        
        
        self.init_model(check_pars=False)
        
        #=======================================================================
        # #collect data
        #=======================================================================
        #everything but the layers
        self.raw_d = {k:v.copy() for k,v in data.items() if not hasattr(v, 'crs')}
        
        #=======================================================================
        # #check requirements
        #=======================================================================
        """similar to the checks in init_model... but on the keys"""
        #assemble requirements
        req_dtags = list()
        for k, d in self.exp_pars_md.items():
            if k.endswith('_fps'):
                req_dtags = req_dtags + list(d.keys())
                
        miss_l = set(req_dtags).difference(self.raw_d.keys())
        if not len(miss_l)==0:
            log.warning('missing %i: %s... loading from cf'%(len(miss_l), miss_l))
            
            self.load_df_ctrl({k:v for k,v in self.dtag_d.items() if k in miss_l})
            
            
        """todo: load missing"""
        
        log.info('loading w/ %i: %s'%(len(self.raw_d), self.raw_d.keys()))
        
        self.prep_model(**prep_kwargs)
        return self
        
    #===========================================================================
    # CONTROL FILE------
    #===========================================================================
    def init_model(self, #load and attach control file parameters
                   check_pars=True,
                   ):
        """
        should be called by the model's own 'setup()' func
            during standalones and Dialog runs
        """        
        log = self.logger.getChild('init_model')
        #=======================================================================
        # #parameter setup-----
        #=======================================================================
        #=======================================================================
        # load the control file
        #=======================================================================
        cf_fp = self.cf_fp
        if cf_fp == '':
            raise Error('passed an empty cf_fp!')
        assert os.path.exists(cf_fp), 'provided parameter file path does not exist \n    %s'%cf_fp

        self.pars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%self.pars.read(cf_fp))
        
        #=======================================================================
        # filepaths
        #=======================================================================
        if not self.absolute_fp:
            log.info('converting relative filepaths')
            self.pars = self._cf_relative(self.pars)
 
        #=======================================================================
        # check against expectations
        #=======================================================================
        if check_pars:
            errors = self._get_cf_miss(self.pars)
                
            #report on all the errors
            for indxr, msg in enumerate(errors):
                log.error('error %i: \n%s'%(indxr+1, msg))
                        
                    
            #final trip
            """lets us loop through all the checks before failing"""
            if not len(errors)==0:        
                raise Error('failed to validate ControlFile w/ %i error(s)... see log'%len(errors))
                
        #=======================================================================
        # attach control file parameter values
        #=======================================================================

        self.cfPars_d = self.cf_attach_pars(self.pars)
        
        
        #=======================================================================
        # #check our validity tag
        #=======================================================================
        if check_pars:
            if not self.valid_par is None:
                if not getattr(self, self.valid_par):
                    raise Error('control file not validated for \'%s\'. please run InputValidator'%self.valid_par)
        
        #=======================================================================
        # update plotting handles
        #=======================================================================
        if hasattr(self, 'upd_impStyle'):
            self.upd_impStyle()
            self._init_fmtFunc()
            
        self.resname = '%s_%s_%s'%(self.valid_par, self.name, self.tag)
        #=======================================================================
        # #wrap
        #=======================================================================
        self.logger.debug('finished init_modelon Model')
        
        
    def cf_chk_pars(self,
                   cpars,
                   chk_d,
                   optional=False, #whether the parameters are optional
                   ):
        """
        
        """
        
        log = self.logger.getChild('cf_chk_pars')
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(cpars, configparser.ConfigParser)
        """checks are done on a configparser (rather than a dictionary)
        to better handle python's type reading from files"""
        assert isinstance(chk_d, dict)
        if not optional: assert len(chk_d)>0
        assert len(cpars)>0
        
        log.debug('\'%s\' optional=%s chk_d:\n    %s'%(self.__class__.__name__, optional, chk_d))
        #=======================================================================
        # #section check
        #=======================================================================
        miss_l = set(chk_d.keys()).difference(cpars.sections())
        
        if len(miss_l) > 0:
            log.warning('missing %i expected sections in control file: %s'%(len(miss_l), miss_l))
        
        
        #=======================================================================
        # variable check
        #=======================================================================
        errors = [] #container for errors
        for sectName, vchk_d in chk_d.items():
            if not sectName in cpars: continue #allow for backward scompatailbiity
            csectName = cpars[sectName] #get these parameters
            
            #===================================================================
            # #check all the expected keys are there
            #===================================================================
            miss_l = set(vchk_d.keys()).difference(list(csectName))
            if len(miss_l) > 0:
                """changed this to a warning for backwards compatability"""
                log.warning('\'%s\' missing %i (of %i) expected varirables: \n    %s'%(
                    sectName, len(miss_l), len(vchk_d), miss_l))
                
                vchk_d = {k:v for k,v in vchk_d.items() if k in list(csectName)}
                if len(vchk_d)==0: continue

            #===================================================================
            # #check attributes with handles
            #===================================================================
            log.debug('checking section \'%s\' against %i variables'%(sectName, len(vchk_d)))
            for varName, achk_d in vchk_d.items(): #loop through the expectations
                
                try: #attempt to tpye set, better error reporting/catching
                    pval = self._get_from_cpar(cpars, sectName, varName, logger=log) #get the typeset variable
                    
                except Exception as e: #failed to even typeset... mark as an error and move forward
                    errors.append(e)
                    continue
                
                #===============================================================
                # blanks/nulls
                #===============================================================
                if (pd.isnull(pval) or pval==''):
                    msg = 'no value provided for \'%s.%s\'. optional=%s'%(sectName, varName, optional)
                    if optional:
                        log.debug(msg)
                        continue
                    else:
                        errors.append(msg)
                        
                else: #expected some value
                
                    try:
                        _ = self._par_hndl_chk(sectName, varName, pval, achk_d, logger=log) #check with handles
                    except Exception as e:
                        errors.append(e)
                    
            
            
        log.debug('finished checking %i sections w/ %i errors. optional=%s \n'%(len(cpars), len(errors), optional))
        
        return len(errors)==0, errors
        
    def cf_attach_pars(self, #load parmaeteres from file
                    cpars,
                    setAttr=True, #whether to save each attribute 
                    ):
        
        """
        cf_chk_pars() should be run first to make sure parameter membership and type matches expectations
        
        here we just update every parameter value found:
            on the class
            in the ControlFile
        """
        
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('cf_attach_pars')
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(cpars, configparser.ConfigParser)
        
        
        #=======================================================================
        # loop and retrieve
        #=======================================================================
        cpars_d = dict() #set values
        no_d = dict() #not set values
        noCnt = 0
        for sectName in cpars.sections():
            cpars_d[sectName], no_d[sectName] = dict(), dict() #add the page
            log.debug('loading %i parameters from section \'%s\''%(len(cpars[sectName]), sectName))
            
            #loop through each variable name/value in this section
            for varName, valRaw in cpars[sectName].items():
                
                #check we care about this
                if not hasattr(self, varName):
                    log.debug('passed variable \'%s\' not found on class... skipping'%varName)
                    no_d[sectName][varName] = valRaw
                    noCnt+=1
                    continue
                
                
                #retrieve typset value
                pval = self._get_from_cpar(cpars, sectName, varName, logger=log) #get the typeset variable
                
                #store it
                cpars_d[sectName][varName] = pval 
                
        #======================================================================
        # attach all the paramers
        #======================================================================
        cnt = 0
        if setAttr:
            
            for sectName, spars_d in cpars_d.items():
                for varnm, val in spars_d.items():
                    setattr(self, varnm, val)
                    log.debug('set %s=%s'%(varnm, val))
                    cnt +=1
                
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('attached %i parmaeters to self (skipped %i)'%(cnt, noCnt))
                
        
        
        return cpars_d
    



    
    def  _cf_relative(self, #convert filepaths from relative to absolute
                      cpars, #config parser
                      base_dir=None, #base directory to add
                      sections=['dmg_fps', 'risk_fps', 'results_fps'], #sections contaiing values to convert
                      
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        if base_dir is None: base_dir=self.base_dir
        log = self.logger.getChild('_cf_relative')
        
        assert os.path.exists(base_dir)

        #=======================================================================
        # #loop through parser and retireve then convert
        #=======================================================================
        res_d = dict() #container for new values
        for sectName in sections:
            assert sectName in cpars
            res_d[sectName]=dict()
            #loop through each variable in this section
            for varName, valRaw in cpars[sectName].items():
                if valRaw == '': continue #skip blanks
                
                if os.path.exists(valRaw):
                    """switchged to warning... some tools may not use this fp"""
                    log.warning(('%s.%s passed aboslute_fp=False but fp exists \n    %s'%(
                        sectName, varName, valRaw)))
                    continue
                else:
                
                    #get the absolute filepath
                    fp = os.path.join(base_dir, valRaw)
                    """dont bother... some models may not use all the fps
                    better to let the check with handles catch things
                    assert os.path.exists(fp), '%s.%s not found'%(sectName, varName)"""
                    if not os.path.exists(fp):
                        log.warning('%s.%s got bad fp: %s'%(sectName, varName, fp))
                
                #set it
                res_d[sectName][varName]=fp
                
        #=======================================================================
        # set the new values
        #=======================================================================
        cnt=0
        for sectName, sect_d in res_d.items():
            if len(sect_d)==0: continue #skip blanks
            
            for varName, newVal in sect_d.items():
                cpars.set(sectName, varName, newVal)
                cnt+=1
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('converted %i filepaths to absolute'%cnt)
            
        """
        cpars['dmg_fps']['finv']
        """
        
        
        return cpars
    
    #===========================================================================
    # LOADERS------
    #===========================================================================
    def load_df_ctrl(self,#load raw data from control file
                     dtag_d=None,
                      logger=None,
                      ): 
        #=======================================================================
        # default
        #=======================================================================
        if dtag_d is None: dtag_d=self.dtag_d
        if logger is None: logger=self.logger
        log=logger.getChild('load_df_cntrl')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert len(dtag_d)>0
        assert isinstance(self.pars, configparser.ConfigParser), 'did you init_model?'
        
        #=======================================================================
        # loop and load
        #=======================================================================
        for dtag, d in dtag_d.items():
            #get from control file
            assert hasattr(self, dtag)
            fp = getattr(self, dtag)
            if fp == '':
                log.debug('no \'%s\'... skipping'%dtag)
                continue
            
            #check it
            assert os.path.exists(fp), '\'%s\' got pad filepath: \n    %s'%(dtag, fp)
            
            #load by type
            ext = os.path.splitext(fp)[1]
            if ext == '.csv':
                data = pd.read_csv(fp, **d)
                log.info('loaded \'%s\' w/ %s'%(dtag, str(data.shape)))
            elif ext == '.xls':
                data = pd.read_excel(fp, **d)
                log.info('loaded %s w/ %i sheets'%(dtag, len(data)))
            else:
                raise Error('unrecognized filetype: %s'%ext)
                
            self.raw_d[dtag] = data
            
            
        #=======================================================================
        # wrap
        #=======================================================================
        assert len(self.raw_d)>0, 'failed to load any data!'
        log.debug('finished w/ %i'%len(self.raw_d))
            

        
    def set_finv(self, #set some special values from the finv
                 dtag = 'finv',
                 logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        cid = self.cid
        log=logger.getChild('set_finv')
        #======================================================================
        # pre check
        #======================================================================
        assert dtag in self.raw_d
        df_raw = self.raw_d[dtag]
        assert isinstance(df_raw, pd.DataFrame)
        assert df_raw.index.name == cid
        df = df_raw.sort_index(axis=0)
        

        self.check_finv(df)
        
        #=======================================================================
        # resolve column gruops----
        #=======================================================================
        cdf, prefix_l = self._get_finv_cnest(df)
        
        log.info('got %i nests: %s'%(len(prefix_l), prefix_l))
        #=======================================================================
        # mitigation----
        #=======================================================================
        #check these
        boolcol = cdf.loc['ctype', :]=='miti'
        
        if self.apply_miti: assert boolcol.any(), 'passed apply_miti=True but got no mitigation data'
        
        if boolcol.any() and self.apply_miti:
            mdf = df.loc[:, boolcol]
            
            #check names
            miss_l = set(mdf.columns).difference([self.miLtcn, self.miUtcn, self.miVcn, self.miScn])
            assert len(miss_l)==0, 'got some unrecognized mitigation column names on the finv:\n %s'%miss_l
            
            
            #check types
            assert np.array_equal(mdf.dtypes.unique(), 
                      np.array([np.dtype('float64')], dtype=object)), \
                      'bad type on finv \n%s'%mdf.dtypes
            
            #check threshold logic
            if self.miLtcn in mdf.columns and self.miUtcn in mdf.columns:
                boolidx = mdf[self.miLtcn]>mdf[self.miUtcn]
                if boolidx.any():
                    log.debug(mdf[boolidx])
                    raise Error('got %i (of %i) mi_Lthresh > mi_Uthresh... see logger'%(
                        boolidx.sum(), len(boolidx)))
                    
            #===================================================================
            # #check intermediate requirements
            #===================================================================
            for coln in [self.miVcn, self.miScn]:
                if not coln in mdf.columns: continue #not here.. dont check
                
                """requiring an upper threshold (height below which scale/vale is applied)
                but no lower threshold"""
                assert self.miUtcn in mdf.columns, 'for \'%s\'a \'%s\' is required'%(
                    coln, self.miUtcn)
                

                #check everywhere we have a scale/value we also have a lower thres
                boolidx_c = mdf[coln].notna()
                boolidx = np.logical_and(
                    boolidx_c, #scale/value is real
                    mdf[self.miUtcn].notna() #real threshold
                    )
                
                boolidx1 = np.invert(boolidx_c==boolidx)
                if boolidx1.any():
                    log.debug(mdf[boolidx1])
                    raise Error('null mismatch for \"%s\' against \'%s\' for %i (of %i) assets...see logger'%(
                        coln, self.miUtcn, boolidx1.sum(), len(boolidx1)))
                                
                #check negativity
                if coln == self.miVcn:
                    boolidx = mdf[coln]>0
                    if boolidx.any():
                        log.warning('got %i (of %i) \'%s\' values above zero'%(
                            boolidx.sum(), len(boolidx), coln))
                elif coln == self.miScn:
                    boolidx = mdf[coln]<0
                    assert not boolidx.any(), 'got %i negative %s vals'%(boolidx.sum(), coln)
            log.debug('finished miti checks')


        #=======================================================================
        # remainders
        #=======================================================================
        cdf.loc['ctype', :] = cdf.loc['ctype', :].fillna('extra') #fill remainders
        log.debug('mapped %i columns: \n%s'%(len(cdf.columns), cdf))
        #======================================================================
        # sets----
        #======================================================================
        self.data_d['finv'] = df.copy()
        self.asset_cnt = len(df) #used by risk plotters
        self.cindex = df.index.copy() #set this for checks later
        self.finv_cdf = cdf

        """
        view(df)
        """

    def _get_finv_cnest(self, #resolve column group relations
                        df, #finv data
                        ):
        
        """ this would have been easier with a dxcol"""
        
        #======================================================================
        # get prefix values (using elv columns)
        #======================================================================
        #pull all the elv columns
        tag_coln_l = df.columns[df.columns.str.endswith('_elv')].tolist()
        
        assert len(tag_coln_l) > 0, 'no \'elv\' columns found in inventory'
        assert tag_coln_l[0] == 'f0_elv', 'expected first tag column to be \'f0_elv\''
        
        #get nested prefix values
        prefix_l = [coln[:2] for coln in tag_coln_l]
        
        
        #check
        for e in prefix_l: 
            assert e.startswith('f'), 'bad prefix: \'%s\'.. check field names'
            
        #=======================================================================
        # add each nest column name
        #=======================================================================   
        cdf = pd.DataFrame(columns=df.columns, index=['ctype', 'nestID', 'bname']) #upgrade to a series
        
        """
        view(cdf)
        """     

        for pfx in prefix_l:
            l = [e for e in df.columns if e.startswith('%s_'%pfx)]
            
            for e in l:
                cdf.loc['nestID', e] = pfx
                cdf.loc['ctype', e] = 'nest'
                cdf.loc['bname', e] = e.replace('%s_'%pfx, '')
            
        #set flag for mitigation columns
        cdf.loc['ctype', cdf.columns.str.startswith('mi_')] = 'miti'
        
        return cdf, prefix_l
            
    def set_evals(self,#loading event probability data

                   dtag = 'evals',
                   check=True, #whether to perform special model loading logic tests
                   logger=None,
                   ):
        """
        called by:
            Risk1
            Risk2
            Dmg2 (for formatting columns)
        """
        if logger is None: logger=self.logger
        log = logger.getChild('set_evals')


        #check load sequence

        #======================================================================
        # load it
        #======================================================================
        adf = self.raw_d[dtag]
        
        assert len(adf) ==1, 'expected only 1 row on aeps'
        

        #convert to a series
        aser_raw = adf.iloc[0,:]
        
        #======================================================================
        # check
        #======================================================================
        assert aser_raw.notna().all(), 'got some nulls in evals'
        boolar = aser_raw == 0
        assert not boolar.any(), 'got some zeros in evals'
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
        aep_ser.name='aep'  
 
        if check:
            assert 'finv' in self.data_d, 'call load_finv first'
            log.debug('\n%s'%aep_ser.to_frame().join(aep_ser.duplicated(keep=False).rename('dupes')))
            self._check_evals(aep_ser)
            
        #=======================================================================
        # #assemble event type  frame
        #=======================================================================
        """this is a late add.. would have been nice to use this more in multi_ev"""
        df = aep_ser.to_frame().reset_index(drop=False).rename(columns={'index':'rEventName'})
        df['noFail'] = True
        
        
        
        #======================================================================
        # #wrap
        #======================================================================
        log.debug('prepared aep_ser w/ %i: \n    %s'%(len(aep_ser), aep_ser.to_dict()))
        
 
        self.data_d[dtag] = aep_ser #setting for consistency. 
        self.eventType_df = df
        self.expcols = aep_ser.index.copy() #set for later checks
        
        return aep_ser
    
    def _check_evals(self, aep_ser, logger=None):
        if logger is None: logger=self.logger
        log=logger.getChild('check_evals')

        #check all aeps are below 1
        boolar = np.logical_and(
            aep_ser < 1,
            aep_ser > 0)
        
        assert np.all(boolar), 'passed aeps out of range'
        
        #check logic against whether this model considers failure
        if self.exlikes == '': #no failure
            assert len(aep_ser.unique())==len(aep_ser), \
            'got duplicated \'evals\' but no \'exlikes\' data was provided.. see logger'
        else:
            assert len(aep_ser.unique())!=len(aep_ser), \
            'got unique \'evals\' but \'exlikes\' data is provided... see logger'
            
        #check minimum events for risk calculation
        if not len(aep_ser.unique())>2:
            log.warning("received %i unique events. this small number could cause unexpected behavior of the EAD algorhihtim"%(
                len(aep_ser.unique())))
        
    def set_expos(self,#set expos data

                   dtag = 'expos',
                   logger=None,
                   **kwargs):

        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('set_expos')
        
        df= self._get_expos(dtag, log, **kwargs)
        
        #=======================================================================
        # wrap
        #=======================================================================
        self.data_d[dtag] = df        
        log.info('finished loading %s as w/ \n    %s'%(dtag, self._get_stats(df)))
        
        return df
        

    def _get_expos(self,#generic exposure-type data handling
                   dtag, log,
                   event_slice=False, #allow the expolike data to pass MORE events than required 
                   check_monot=False, #whether to check monotonciy
                   ):
        
        """
        loads, sets index, slices to finv, and lots of checks, adds result to data_d
        
        called by:
            dmg2
            risk1
            risk2 (via load_exlikes())
        """
        
        #=======================================================================
        # prechecks1
        #=======================================================================
        assert 'finv' in self.data_d, 'call load_finv first'
        assert isinstance(self.cindex, pd.Index), 'bad cindex'
        
        #======================================================================
        # load it
        #======================================================================

        
        df_raw = self.raw_d[dtag]
        

        df = df_raw.sort_index(axis=1).sort_index(axis=0)
        #======================================================================
        # postcheck
        #======================================================================
        assert df.columns.dtype.char == 'O','bad event names on %s'%dtag
        assert df.index.name==self.cid, 'expected first column to be a \'%s\' index'%self.cid
        assert df.index.is_unique, 'got non-unique index \'%s\''%self.cid
        
        """
        exlikes generally is shorter
        allowing the expos to be larger than the finv 
        
        """
        #check cids
        miss_l = set(self.cindex).difference(df.index)
        assert len(miss_l) == 0, '%i assets on %s not found in finv \n    %s'%(
            len(miss_l), dtag, miss_l)
        
        #check events
        
        if dtag == 'exlikes':
            miss_l = set(df.columns).difference(self.expcols)
        else:
            miss_l = set(self.expcols).symmetric_difference(df.columns)
            
        if event_slice:
            boolcol = df.columns.isin(self.expcols)
            
            assert boolcol.any(), 'no columns match'
            if not boolcol.all():
                log.warning('%s jonly passed %i (of %i) matching columns'%(
                    dtag, boolcol.sum(), len(boolcol)))
        else:
            """todo: allow dmg only runs to pass w/o evals"""
            assert len(miss_l) == 0, '%i eventName mismatch on \'%s\' and \'evals\': \n    %s'%(
                len(miss_l), dtag, miss_l)
            
            boolcol = ~pd.Series(index=df.columns, dtype=bool) #all trues
        
 
        #======================================================================
        # slice
        #======================================================================
        df = df.loc[self.cindex,boolcol]
        
        
        
        #======================================================================
        # postcheck2
        #======================================================================
        
        #check dtype of columns
        for ename, chk_dtype in df.dtypes.items():
            assert np.issubdtype(chk_dtype, np.number), 'bad dtype %s.%s'%(dtag, ename)
            
            
        booldf = df.isna()
        if booldf.any().any():
            """wsl nulls are left as such by build_depths()"""
            log.warning('\'%s\' got %i (of %i) null values'%(
                dtag, booldf.sum().sum(), booldf.size))
        
        if not np.array_equal(self.cindex, df.index):
            raise Error('cid mismatch')
        

        if check_monot and 'evals' in self.data_d:
            self.check_monot(df, aep_ser = self.data_d['evals'])
            
        #for  percent inundation 
        if self.as_inun:
            booldf = df >1
            assert booldf.sum().sum()==0, \
                'for pct inundation got %i (of %i) exposure values great than 1'%(
                    booldf.sum().sum(), booldf.size)
            """forcing this becuase %inundation should never add ground elevations"""
            assert self.felv =='datum', 'felv must equal \'datum\' for pct inundation runs'

        
        return df
        

            
        
    def set_gels(self,#loading expo data

                   dtag = 'gels'):
        """
        TODO:  consolidate w/ __get_expos
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_gels')
 
        #======================================================================
        # precheck
        #======================================================================
        assert 'finv' in self.data_d, 'call load_finv first'
        assert isinstance(self.cindex, pd.Index), 'bad cindex'
        
        assert not self.as_inun, 'loading ground els for as_inun =True is invalid'
        
        #======================================================================
        # load it
        #======================================================================
        df_raw = self.raw_d[dtag]

            
        df = df_raw.sort_index(axis=0)
        
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
            log.debug(df.loc[boolidx, :])
            raise Error('got %i (of %i) null ground elevation values... see logger'%(boolidx.sum(), len(boolidx)))
        
        boolidx = df.iloc[:,0] < 0
        if boolidx.any():
            log.warning('got %i ground elevations below zero'%boolidx.sum())
        
        #======================================================================
        # set it
        #======================================================================
        self.data_d[dtag] = df
        
        log.info('finished loading \'%s\' w/ \n    %s'%(dtag, self._get_stats(df)))
        


    def set_attrimat(self,
 
                      dtag=None,
                      check_psum=True,
                      logger=None): #load the attributino matrix
        
        """
        this data file is built by dmg2.get_attribution()
        loader is called by:
            risk1
            risk2
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('set_attrimat')
        if dtag is None: dtag = self.attrdtag_in
 
        cid = self.cid
        
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert self.attriMode
 

        #======================================================================
        # load it
        #======================================================================
        #dxcol = pd.read_csv(fp, index_col=0, header=list(range(0,dxcol_lvls)))
        dxcol = self.raw_d[dtag]
        
        #build the name:rank keys
        nameRank_d = {lvlName:i for i, lvlName in enumerate(dxcol.columns.names)}
        
        #=======================================================================
        # data precheck
        #=======================================================================
        #index checks
        if hasattr(self, 'cindex'): 
            assert dxcol.index.name==cid, 'bad index name %s'%(dxcol.index.name)
            assert np.array_equal(dxcol.index, self.cindex), 'attrimat index mismatch'
        
        #dxcolumn check
        """leaving the column labels flexible
        risk models (dxcol_lvls=2) should get mdexcol lvl0 name = 'rEventName'
        as the matrix grows, the position of this name should change"""
        assert 'rEventName' in dxcol.columns.names,'missing rEventName from coldex'

        #check the rEventNames     
        if hasattr(self, 'expcols'):  
            miss_l = set(dxcol.columns.get_level_values(nameRank_d['rEventName'])
                         ).symmetric_difference(self.expcols)
            assert len(miss_l)==0, 'attimat rEventName mismatch: %s'%miss_l
        
        #check dtypes
        for e in dxcol.dtypes.values: assert e==np.dtype(float)
        
        
        #=======================================================================
        # check psum
        #=======================================================================
        if check_psum:
            self.check_attrimat(atr_dxcol = dxcol)
        
        #=======================================================================
        # set
        #=======================================================================
        """Risk2 will remove this with promote_attrim()"""
        assert not dtag in self.data_d
        self.data_d[dtag] = dxcol

        log.info('finished setting %s as %s'%(dtag, str(dxcol.shape)))
        return
  
    def _get_stats(self, df): #log stats of a frame
        
        return 'count = %i, nulls = %i, min = %.2f, mean = %.2f, max = %.2f'%(
            df.size, df.isna().sum().sum(), df.min().min(), df.mean().mean(), df.max().max())
   
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
        assert gdf.columns.tolist() == ['gels']
        
                
        #======================================================================
        # #do the join join
        #======================================================================
        fdf = fdf.join(gdf)
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('finished with %s'%str(fdf.shape))
        
        self.data_d['finv'] = fdf
        
        self.finv_cdf.loc['ctype', 'gels'] = 'gels'
        
        return
            
        
        
    def build_exp_finv(self, #assemble the expanded finv
                    group_cnt = None, #number of groups to epxect per prefix
                    ):
        """
        initial loading of the finv is done in load_finv()
            here we pivot out to 1nest on bids
        """
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('build_exp_finv')
        fdf = self.data_d['finv']
        finv_cdf = self.finv_cdf.copy() #metadata for finv columns. see load_finv()
        cid, bid = self.cid, self.bid
        
        if group_cnt is None: group_cnt = self.group_cnt
        
        bcolns = ['gels'] #columns to map back onto/copy over to each row of the expanded finv 
        #======================================================================
        # group_cnt defaults
        #======================================================================
        assert isinstance(group_cnt, int)
        
        exp_fcolns = [cid, 'fscale', 'felv']
        if group_cnt == 2: #Risk1
            pass
        elif group_cnt == 4: #Dmg2 and Risk2
            """fcap is optional"""
            exp_fcolns = exp_fcolns + ['ftag']
            
        else:
            raise Error('bad group_cnt %i'%group_cnt)

        #======================================================================
        # precheck
        #======================================================================
        assert fdf.index.name == cid, 'bad index on fdf'
        

        #======================================================================
        # expand: nested entries---------------
        #======================================================================

        bdf = None
        
        for prefix, fcolsi_df in finv_cdf.drop('ctype', axis=0).dropna(axis=1).T.groupby('nestID', axis=0):


            #get slice and clean
            df = fdf.loc[:, fcolsi_df.index].dropna(axis=0, how='all').sort_index(axis=1)
            
            #get clean column names
            df.columns = df.columns.str.replace('%s_'%prefix, 'f')
            df = df.reset_index()
            
            df['nestID'] = prefix
            
            #add to main
            if bdf is None:
                bdf = df
            else:
                bdf = bdf.append(df, ignore_index=True, sort=False)
                        
            log.info('for \"%s\' got %s'%(prefix, str(df.shape)))
            
            
        #==================================================================
        # #add back in other needed columns
        #==================================================================
        boolcol = fdf.columns.isin(bcolns) #additional columns to pivot out
        
        if boolcol.any(): #if we are only linking in gels, these may not exist
            bdf = bdf.merge(fdf.loc[:, boolcol], on=cid, how='left',validate='m:1')
            
            log.debug('joined back in %i columns: %s'%(
                boolcol.sum(), fdf.loc[:, boolcol].columns.tolist()))
        
        #wrap
        log.info('expanded inventory from %i nest sets %s to finv %s'%(
            len(finv_cdf.loc['nestID', :].dropna(axis=0).unique()), str(fdf.shape), str(bdf.shape)))
       
        
        #set indexers
        bdf[bid] = bdf.index
        bdf.index.name=bid
        
        #======================================================================
        # check
        #======================================================================
        miss_l = set(exp_fcolns).difference(bdf.columns)
        assert len(miss_l) == 0, miss_l
        
        
        #======================================================================
        # adjust fscale--------------
        #======================================================================
        """
        view(bdf)
        """
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
            
            log.info('converted felv from \'ground\' to \'datum\' \n    min=%.2f, mean=%.2f, max=%.2f'%(
                 s.min(), s.mean(), s.max()))
            
        elif self.felv=='datum':
            log.debug('felv = \'%s\' no conversion'%self.felv)
        else:
            raise Error('unrecognized felv=%s'%self.felv)
        
        #=======================================================================
        # add mitigation data---
        #=======================================================================
        if self.apply_miti:
            #get data
            bdf = bdf.join(fdf.loc[:, finv_cdf.columns[finv_cdf.loc['ctype', :]=='miti']],
                     on=cid)
            
        #=======================================================================
        # checks
        #=======================================================================
        """check_finv does this now
        for coln in ['ftag']:
            bx =  bdf[coln].isna()
            if bx.any():
                log.debug('\n%s'%bdf.loc[bx, :])
                raise Error('got %i \'%s\' nulls...see logger'%(bx.sum(), coln))"""

        
        #======================================================================
        # wrap
        #======================================================================
        log.info('finished with %s'%str(bdf.shape))
        self.bdf = bdf
        
    def _get_fexpnd(self, #reshape some finv data to math exposure indicies
                    mcoln, #finv column with threshol dinfo
                    ddf = None,
                    bdf=None,
                    logger=None,
                    ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('get_thresh')
        if ddf is None: ddf = self.ddf
        if bdf is None: bdf = self.bdf
        
        cid, bid = self.cid, self.bid
        
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        
        log.debug('on ddf %s'%(str(ddf.shape)))
        
        #check the depth data
        miss_l = set(self.events_df.index).difference(ddf.columns)
        assert len(miss_l)==0, 'column mismatch on depth data: %s'%miss_l
        
        assert cid in ddf.columns
        assert bid in ddf.columns
        
        
        assert mcoln in bdf.columns
        assert bdf.index.name == bid, 'bad index on expanded finv data'

        #=======================================================================
        # clean and expand
        #=======================================================================
        
        ddfc = ddf.drop([cid, bid], axis=1)
        
       
        #replicate across columns
        dt_df = pd.DataFrame(
            np.tile(bdf[mcoln], (len(ddfc.columns), 1)).T,
            index = bdf[mcoln].index, columns= ddfc.columns)
        
        return ddfc, dt_df
        
        
        
        
    def build_depths(self): #build the expanded depths data from the wsl data
        
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
        #add indexer columns expand w/ wsl data
        """would have been easier with a multindex"""
        ddf = self.bdf.loc[:, [bid, cid]].join(wdf.round(self.prec),  on=cid
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
            
            view(ddf)
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
            note these are expanded (un-nesetd) assets, so counts will be larger than expected
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
            raise Error('%i (of %i) nested assets exceed max depth: %.2f. see logger'%(
                boolidx.sum(), len(boolidx), self.max_depth))
        
        
                
        #======================================================================
        # wrap
        #======================================================================
        log.info('assembled depth_df w/ \nmax:\n%s\nmean: \n%s'%(
            ddf.loc[:,boolcol].max(),
            ddf.loc[:,boolcol].mean()
            ))
        
        self.ddf = ddf
        

    #===========================================================================
    # CALCULATORS-------
    #===========================================================================
        

    def _attriM_nulls(self, #handle nulls in an attribution matrix
                     idf, #impact values (of which we are calculating attributions)
                     aRaw_dxcol, #attribution matrix w/ nulls (that need filling)
                     logger=None,
                     
                     ):
        
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('_attriM_nulls')
        mdex = aRaw_dxcol.columns
        nameRank_d= {lvlName:i for i, lvlName in enumerate(mdex.names)}
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert np.array_equal(mdex.levels[0], idf.columns), 'impacts and top level dont match'
        #=======================================================================
        # zero damage for event across set: equal attribution---
        #=======================================================================
        #=======================================================================
        # #builld replacement locator frame
        #=======================================================================
        booldxcol = idf==0.0  #elements w/ zero impact
        
        booldxcol.columns.names=[mdex.names[0]]
        """not very elegant"""
        
        #propagate boolean values into dxcol
        for lRank, lvlName in enumerate(mdex.names):
            if lRank==0: continue #always skipping top level
            
            lvals = mdex.levels[lRank].tolist() 
            
            #propagate into this level
            booldxcol = pd.concat([booldxcol]*len(lvals), keys=lvals, axis=1,
                                  names=[lvlName]+booldxcol.columns.names
                                  )
        #re-order
        booldxcol = booldxcol.reorder_levels(mdex.names, axis=1)
        booldxcol = booldxcol.reindex(aRaw_dxcol.columns, axis=1)
        assert np.array_equal(booldxcol.columns, aRaw_dxcol.columns)
        """
        view(booldxcol)
        view(aRaw_dxcol)
        view(atr_dxcol)
        """
        #=======================================================================
        # #apply locator frame
        #=======================================================================

        #loop through each of the top-level values and figure out the set size
        fv_d = dict()
        dxcol = None
        for lval, gdf in aRaw_dxcol.groupby(level=0, axis=1):
            fv_d[lval] = 1/len(gdf.columns)
            booldf = booldxcol.loc[:, idx[lval,:,:]]
            
            gdxcol = gdf.where(~booldf, other=fv_d[lval])
            
            if dxcol is None:
                dxcol = gdxcol
            else:
                dxcol = dxcol.join(gdxcol) 
            
            log.debug('l0=%s. setting %i (of %i) full dmg=0 entries with equal attribution = %.2f'%(
                lval, booldf.sum().sum(), booldf.size, fv_d[lval]))
        
        #=======================================================================
        # remaining partial zero damage nests
        #=======================================================================
        log.debug('setting %i (of %i) partial dmg=0 entries w/ 0.0 attribution'%(
            dxcol.isna().sum().sum(), dxcol.size))
        
        dxcol = dxcol.fillna(0.0)
        
        #=======================================================================
        # checks
        #=======================================================================
        if not dxcol.notna().all().all():
            raise Error('got %i (of %i) remaining nulls after filling'%(
                dxcol.isna().sum().sum(), dxcol.size))
            
        self.check_attrimat(atr_dxcol=dxcol, logger=log)
        
        return dxcol
    


    def _conv_expo_aep(self, #converting exposure data set to aep column values 
                      df, 
                      aep_ser,
                      event_probs = 'aep',
                      logger = None,):
        """
        used by the force/check monotonociy
        
        also see '_get_ttl_ari()'
        """
        
        if logger is None: logger = self.logger
        log = self.logger.getChild('_conv_expo_aep')
        
        assert isinstance(aep_ser, pd.Series)
        
        assert len(df.columns) > 0
        assert np.issubdtype(aep_ser.dtype, np.number)
        
        miss_l = set(df.columns).difference(aep_ser.index)
        assert len(miss_l) == 0, 'some event columns in the ddf not in the aep'
        
        #slice down aep_ser       
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
    
    def _get_ttl_ari(self, df): #add an ari column to a frame (from the aep vals)
        
        ar = df.loc[:,'aep'].T.values
        
        ar_ari = 1/np.where(ar==0, #replaced based on zero value
                           sorted(ar)[1]/10, #dummy value for zero (take the second smallest value and divide by 10)
                           ar) 
        
        df['ari'] = ar_ari.astype(np.int32)
        
        return 
    
    def _fmt_resTtl(self,  #format res_ttl
                    df_raw):
        
        df = df_raw.copy()
        df.index.name = 'aep'
        df.columns = [self.impact_units]
        
        
        """
        self.rtail
        """
        #check extrapolation value matching


        #=======================================================================
        # #add labels
        #=======================================================================
        #note from extrap
        miss_l = set(self.extrap_vals_d.keys()).difference(df.index)
        assert len(miss_l)==0, miss_l
        
        
        df = df.join(
            pd.Series(np.full(len(self.extrap_vals_d), 'extrap'), 
                  index=self.extrap_vals_d, name='note')
            )
        
        #label the results row
        df.loc['ead', 'note'] = 'integration'
        
        #set the rest
        df.loc[:, 'note'] = df.loc[:, 'note'].fillna('impact_sum')
        
        #plot lables
        df['plot'] = True
        df.loc['ead', 'plot'] = False
        
        df=df.reset_index(drop=False)
        
        return df
        
            
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
            df, d = self._conv_expo_aep(df_raw, aep_ser, event_probs=event_probs, logger=log)
            
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
    

    
   

    #==========================================================================
    # VALIDATORS-----------
    #==========================================================================+
    def _par_hndl_chk(self, #check a parameter aginast provided handles
                     sect, varnm, pval, achk_d,
                     logger=None
                     ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('par_hndl_chk')
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert not pval is None or pval == '', '%s.%s got none'%(sect, varnm)
        
        if achk_d is None:
            log.debug('no checks provided for \'%s.%s\'... skipping'%(sect, varnm))
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
                assert pval in hvals, '%s.%s unexpected value: \'%s\''%(sect, varnm, pval)
            
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
            
        log.debug('    \'%s.%s\' passed %i checks'%(sect, varnm, len(achk_d)))
        return True
    
    def _get_cf_miss(self, #collect mismatch between expectations and control file parameter presenece
                      cpars):
        
        assert isinstance(cpars, configparser.ConfigParser)
        errors = []

        for chk_d, opt_f in ((self.exp_pars_md,False), (self.exp_pars_op,True)):
            _, l = self.cf_chk_pars(cpars, copy.copy(chk_d), optional=opt_f)
            errors = errors + l
            
        return errors
                
    def validate(self, #validate this model object
                 cpars, #initilzied config parser
                    #so a session can pass a control file... rather than usin gthe workers init
                 logger=None,
                 ):
        if logger is None: logger=self.logger
        
        """only 1 check for now"""
        #=======================================================================
        # check the control file expectations
        #=======================================================================
        errors = self._get_cf_miss(cpars)
        
        
        
        return errors
        
    def check_attrimat(self, #check the logic of the attrimat
                       atr_dxcol=None,
                       logger=None,

                       ):
        """
        attrimat rows should always sum to 1.0 on lvl0
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if atr_dxcol is None: atr_dxcol=self.att_df
        
        #mdex = atr_dxcol.columns
        #=======================================================================
        # #determine what level to perofrm sum check on
        # sumLvl = atr_dxcol.columns.nlevels -2 #should always be the last rank/level
        #=======================================================================
        
        #sum each of the grpColns nested under the rEventName        
        bool_df = atr_dxcol.sum(axis=1, level=0, skipna=False).round(self.prec)==1.0
        
        #=======================================================================
        # #drop all but the top level. identify null locations
        # nbool_df = atr_dxcol.droplevel(
        #     level=list(range(1, mdex.nlevels)), axis=1
        #     ).notna()
        # 
        # #check the failures line up with the nulls
        # bool2_df = psumBool_df==nbool_df.loc[:, ~nbool_df.columns.duplicated(keep='first')]
        #=======================================================================
        
        """

        view(atr_dxcol.sum(axis=1, level=0, skipna=False))
        view(bool_df)
        view(atr_dxcol)
        """
        if not bool_df.all().all():
            raise Error('%i (of %i) attribute matrix entries failed sum=1 test'%(
                np.invert(bool_df).sum().sum(), bool_df.size))
            
        return True
            
        
    
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
                df, d = self._conv_expo_aep(df_raw, aep_ser, event_probs=event_probs, logger=log)
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
                self._get_ev, axis=1, dx=dx)
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
    
    def check_eDmg(self, #check eap vs. impact like frames
                 df_raw,
                 dropna=True,
                 logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        log = logger.getChild('chk_eDmg')
        
        #=======================================================================
        # #check expectations
        #=======================================================================
        if not 'float' in df_raw.columns.dtype.name:
            raise Error('expected aep values in columns')
        
        #assert len(df_raw.columns)>2
        
        #=======================================================================
        # prep
        #=======================================================================
        if dropna:
            df = df_raw.dropna(how='any', axis=0)
        else:
            assert df_raw.notna().all().all(), 'got some nulls when dropna=False'
            df = df_raw
            
        #=======================================================================
        # check order
        #=======================================================================
        if not np.all(np.diff(df.columns) <=0):
            raise Error('passed headers are not descending')
        #=======================================================================
        # #check everything is positive
        #=======================================================================
        booldf = df>=0
        if not booldf.all().all():
            log.debug('\n%s'%df[booldf])
            log.warning('got %i (of %i) negative values... see logger'%(
                np.invert(booldf).sum().sum(), booldf.size))
            return False
        
        #=======================================================================
        # #check for damage monoticyt
        #=======================================================================
        """
        view(df)
        cboolidx.name='non-mono'
        view(df.join(cboolidx))
        """
        cboolidx = np.invert(df.apply(lambda x: x.is_monotonic_increasing, axis=1))
        if cboolidx.any():
            if logger is None: logger = self.logger
            
            log.debug('\n%s'%df.loc[cboolidx, :])
            log.warning(' %i (of %i)  assets have non-monotonic-increasing damages. see logger'%(
                cboolidx.sum(), len(cboolidx)))
            
            return False
        return True
    
    def check_finv(self, #check finv logic
                   df_raw,
                   finv_exp_d =None,
                   cid=None,
                   logger=None,
                   ):
        """
        see also QProjPlug._check_finv() for dialog level checks
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('check_finv')
        if cid is None: cid = self.cid
        if finv_exp_d is None: finv_exp_d=self.finv_exp_d
        
        df = df_raw.copy()
        
        #=======================================================================
        # dimensional checks
        #=======================================================================
        assert len(df)>0, self.tag
        
        #=======================================================================
        # null checks
        #=======================================================================
        boolcol = df.isna().all(axis=0)
        assert not boolcol.any(), '%s got %i empty columns: \n    %s'%(
            self.tag, boolcol.sum(), df.columns[boolcol].tolist())
        
        assert not df.isna().all(axis=1).any()
        
        #=======================================================================
        # index checks
        #=======================================================================
        assert 'int' in df.index.dtype.name, 'expected int type index'
        assert df.index.is_unique, '%s got non-unique index \'%s\''%(self.name, cid)
        #=======================================================================
        # #cid checks
        #=======================================================================
        
        if not df.index.name == cid:
            if not cid in df.columns:
                raise Error('cid not found in finv_df')
            
            assert df[cid].is_unique, 'got non-unique cid \"%s\''%(cid)
            assert 'int' in df[cid].dtypes.name, 'cid \'%s\' bad type'%cid
        
        #=======================================================================
        # nests
        #=======================================================================
        dxcol = self._get_finv_dxcol(df_raw)

        """
        view(df_raw)
        df_raw.dtypes
        view(dxcol)
        dxcol.dtypes
        """
        #===================================================================
        # loop and check each nest----
        #===================================================================
        for nestID, dfn in dxcol.groupby(level=0, axis=1):
            dfn = dfn.droplevel(0, axis=1).dropna(how='all', axis=0)
                
            #===================================================================
            # with handles
            #===================================================================
            for coln, hndl_d in finv_exp_d.items():
                assert isinstance(hndl_d, dict)
                assert coln in dfn.columns, \
                    '%s missing expected column \'%s\''%(nestID, coln)
                
                #check for nulls
                bx = dfn[coln].isna()
                if bx.any():
                    log.debug(dfn.loc[bx, :])
                    raise Error('%s_%s got nulls... see logger'%(nestID, coln))    
                
                ser = dfn[coln]
                for hndl, cval in hndl_d.items():
                    
                    if hndl=='type':
                        assert np.issubdtype(ser.dtype, cval), '%s  %s_%s expected %s got: %s'%(
                            self.tag, nestID, coln, cval, ser.dtype)
                        
                        """
                        throwing  FutureWarning: Conversion of the second argument of issubdtype
                        
                        https://stackoverflow.com/questions/48340392/futurewarning-conversion-of-the-second-argument-of-issubdtype-from-float-to
                        """
                        
                    elif hndl == 'contains':
                        assert cval in ser, '%s_%s should contain %s'%(nestID, coln, cval)
                        
                    elif hndl=='notna':
                        assert ser.notna().all(), '%s_%s should be all real'%(nestID, coln)
                    else:
                        raise Error('unexpected handle: %s'%hndl)
                    
            #===================================================================
            # column logic
            #===================================================================
        
        
        return True
    
    def _get_finv_dxcol(self, #get finv as a dxcol
                             df):
        """
        todo: transition everything to dxcols
        """
        dtypes = df.dtypes
        cdf, prefix_l = self._get_finv_cnest(df)
        
        df_c = cdf.append(df).dropna(subset=['nestID'], axis=1, how='any').drop('ctype')

        
        #get multindex from two rows
        mdex = pd.MultiIndex.from_frame(df_c.loc[['nestID', 'bname'], :].T)
        
        #cut these rows out and add them back as multindex
        df1 = df_c.drop(['nestID', 'bname'], axis=0)
        
        #remap old types
        dt_d = {k:v for k,v in dtypes.items() if k in df1.columns}
        df1 = df1.astype(dt_d)
        
        df1.columns = mdex
        df1.index.name = df.index.name
        
        if not np.array_equal(df1.index, df.index):
            raise Error('bad index')
        """
        view(df1)
        df1.dtypes
        """
        
        return df1
    
    #===========================================================================
    # OUTPUTS---------
    #===========================================================================
    def output_attr(self, #short cut for saving the expanded reuslts
                    dtag=None,
                    ofn = None,
                    upd_cf= None,
                    logger=None,
                    ):
        
        assert self.attriMode
        #=======================================================================
        # defaults
        #=======================================================================
        if upd_cf is None: upd_cf = self.upd_cf
        if ofn is None:
            ofn = 'attr%02d_%s_%s'%(self.att_df.columns.nlevels, self.name, self.tag)
        if dtag is None: dtag = self.attrdtag_out
            
        out_fp = self.output_df(self.att_df, ofn, logger=logger)
        
        #update the control file
        if upd_cf:
            self.set_cf_pars(
                    {
                    'results_fps':(
                        {dtag:out_fp}, 
                        '#\'%s\' file path set from output_attr at %s'%(
                            dtag, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                        ),
                     },
                    cf_fp = self.cf_fp
                )
        return out_fp
    

            



class DFunc(ComWrkr, #damage function or DFunc handler
            ): 
    """
    used by DFunc objects
    also DFunc handlers:
        model.dmg2.Dmg2
        misc.curvePlot.CurvePlotr
        misc.rfda.convert
        
    """
    #===========================================================================
    # pars from data
    #===========================================================================
    """see crve_d below"""
    impact_units = '' #units of impact prediction (used in axis labelling)
    
    
    #==========================================================================
    # program pars
    #==========================================================================

    
    dd_df = pd.DataFrame() #depth-damage data
    
    """lets just do columns by location
    exp_coln = []"""
    
    #default variables for building new curves
    """when DFunc is loaded from a curves.xlsx, these get assigned as attributes
    only those used by functions are set as class attributes (see above)"""
    crve_d = {'tag':'?',
            'desc':'?',
            'source':'?',
            'location':'?',
            'date':'?',
            'file_conversion':'CanFlood',
            'scale_units':'m2',
            'impact_units':'$CAD',
            'exposure_units':'m',
            'scale_var':'floor area',
            'exposure_var':'flood depth above floor',
            'impact_var':'damage',
            'exposure':'impact'}
    
    cdf_chk_d = {'tag':str, #parameters for checking the raw df
                 'exposure':str,
                 'impact_units':str}
    
    #==========================================================================
    # user pars
    #==========================================================================
    tag = 'dfunc'
    min_dep = None
    pars_d = {}
    
    def __init__(self,
                 tabn='damage_func', #optional tab name for logging
                 curves_fp = '', #filepath loaded from (for reporting)
                 monot=True,
                 **kwargs):
        
        #=======================================================================
        # attach
        #=======================================================================
        self.tabn= tabn
        
        """
        todo: reconcile tabn vs tag
        """
        self.curves_fp = curves_fp
        self.monot=monot
        
        #init the baseclass
        super().__init__(**kwargs) #initilzie Model
        
    
    def build(self,
              df_raw, #raw parameters to build the DFunc w/ 
              logger):
        
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = logger.getChild('%s'%self.tabn)
        log.debug('on %s from %s'%(str(df_raw.shape), self.curves_fp))
        #=======================================================================
        # precheck
        #=======================================================================
        self.check_cdf(df_raw)
        
        #======================================================================
        # identify depth-damage data
        #======================================================================
        #slice and clean
        df = df_raw.iloc[:, 0:2].dropna(axis=0, how='all')
        
        #validate the curve
        #=======================================================================
        # self.check_crvd(df.set_index(df.columns[0]).iloc[:,0].to_dict(),
        #                  logger=log)
        #=======================================================================
        """"
        todo: try 'get_loc'
        """
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
        mser = df.loc[~boolidx, :].set_index(df.columns[0], drop=True ).iloc[:,0]
        mser.index =  mser.index.str.strip() #strip the whitespace
        pars_d = mser.to_dict()
        
        #check it
        assert 'tag' in pars_d, '%s missing tag'%self.tabn
        assert isinstance(pars_d['tag'], str), 'bad tag parameter type: %s'%type(pars_d['tag'])
        
        assert pars_d['tag']==self.tabn, 'tag/tab mismatch (\'%s\', \'%s\')'%(
            pars_d['tag'], self.tabn)
        
        for varnm, val in pars_d.items():  #loop and store on instance
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
        try:
            dd_df.iloc[:,0:2] = dd_df.iloc[:,0:2].astype(float)
        except Exception as e:
            raise Error('failed to typsset the ddf w/ \n    %s'%e)
        
        """
        view(dd_df)
        """
        
        ar = dd_df.sort_values('exposure').T.values
        """NO! leave unsorted
        ar = np.sort(np.array([dd_df.iloc[:,0].tolist(), dd_df.iloc[:,1].tolist()]), axis=1)"""
        self.dd_ar = ar
        
        #=======================================================================
        # check
        #=======================================================================
        """This is a requirement of the interp function"""
        assert np.all(np.diff(ar[0])>0), 'exposure values must be increasing'
        
        #impact (y) vals
        if not np.all(np.diff(ar[1])>=0):
            msg = 'impact values are decreasing'
            if self.monot:
                raise Error(msg)
            else:
                log.debug(msg)
            

        #=======================================================================
        # get stats
        #=======================================================================
        self.min_dep = min(ar[0])
        self.max_dep = max(ar[0])
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('\'%s\' built w/ dep min/max %.2f/%.2f and dmg min/max %.2f/%.2f'%(
            self.tag, min(ar[0]), max(ar[0]), min(ar[1]), max(ar[1])
            ))
        
        return self
        
        
    def get_dmg(self, #get damage from depth using depth damage curve
                depth):
        """
        self.tabn
        pd.DataFrame(self.dd_ar).plot()
        view(pd.DataFrame(self.dd_ar))
        """
        
        ar = self.dd_ar
        
        dmg = np.interp(depth, #depth find damage on
                        ar[0], #depths (xcoords)
                        ar[1], #damages (ycoords)
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
        
        
        
    def _get_smry(self, #get a summary tab on a library
                  clib_d, #{curveName: {k:v}}
                  
                  
                  #library format
                  clib_fmt_df = False, #whether the curve data is a dataframe or not
                  set_index = False, #for clib_fmt_df=True, whether the index has been set (or is on col 0 still)
                  
                  
                  #handle column names
                  add_colns = [], #additional column names to include
                   pgCn='plot_group',
                  pfCn='plot_f',
                  
                  
                  logger=None,
                  ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('_get_smry')
        
        """
        clib_d.keys()
        """
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(clib_d, dict)
        #=======================================================================
        # conversion
        #=======================================================================
        if clib_fmt_df:
            if not set_index:
                clib_d = {k:df.iloc[:,0].to_dict() for k,df in clib_d.items()}
            else:
                
                clib_d = {k:df.set_index(0, drop=True).iloc[:,0].to_dict() for k,df in clib_d.items()}
            
        #check it
        for k,v in clib_d.items():
            self.tabn = k #set for reporting
            assert isinstance(v, dict), 'expected a dict for \'%s\''%k
            assert self.check_crvd(v), '%s failed the check'%k
        
        #=======================================================================
        # build data
        #=======================================================================
        try:
            df_raw = pd.DataFrame(clib_d).T
            

            
            """
            for k,v in clib_d.items():
                print(k)
                for k1,v1 in v.items():
                    print('    %s:%s'%(k1,v1))
            clib_d.keys()
            
            """
        except Exception as e:
            raise Error('faild to convert to frame w/ \n    %s'%e)
        
        cols = df_raw.columns
        assert 'exposure' in cols
        #=======================================================================
        # #location of depth values
        #=======================================================================
        boolcol = cols[cols.get_loc('exposure')+1:]
        
        ddf = df_raw.loc[:, boolcol]
        
        #check it
        try:
            ddf.columns = ddf.columns.astype(np.float)
            ddf = ddf.astype(np.float)
        except Exception as e:
            """
            wont work if you have a very messy library
            """
            raise Error('got bad type on depth values w/ \n    %s'%e)

        
        #min max
        sdf = pd.Series(ddf.min(axis=1), name='min').to_frame()
        sdf['max'] = ddf.max(axis=1)

        #depth-damage
        sdf['depths'] = pd.Series({i:row.dropna().index.tolist() for i, row in ddf.iterrows()})
        
        sdf['dep_dmg'] = pd.Series({i:row.dropna().to_dict() for i, row in ddf.iterrows()})
        
        #check montonoticy  
        """not sure how these do with variable lengths
        
        view(ddf)
        """        
            
        sdf['dmg_mono']=pd.Series({k:np.all(np.diff(ser.dropna())>=0) for k, ser in ddf.iterrows()})
        
        sdf['dep_mono']=pd.Series({i:np.all(np.diff(row.dropna().index.tolist())>0) for i, row in ddf.iterrows()})
        
        #=======================================================================
        # additional columns
        #=======================================================================
        if len(add_colns)>0:
            miss_l = set(add_colns).difference(cols)
            if not len(miss_l)==0:
                """letting this pass"""
                log.warning('requested add_colns not in data: %s'%miss_l)
            
            log.debug('adding %s'%add_colns)
            sdf = sdf.join(df_raw.loc[:, cols.isin(add_colns)])
        
        #=======================================================================
        # add handles
        #=======================================================================
        sdf[pgCn] = 'g1'
        sdf[pfCn] = True
        
        log.debug('finished w/ %s'%str(sdf.shape))
        
        """
        view(sdf)
        """
        return sdf
    
    def _get_split(self,#split the raw df into depth-damage and metadata
                   df_raw, #dummy index
                   fmt='dict', #result format
                   ): 
        
        df = df_raw.set_index(0, drop=True)
        
        #get dd
        assert 'exposure' in df.index
        
        dd_indx = df.index[df.index.get_loc('exposure')+1:] #get those after exposure
        ddf = df.loc[dd_indx, :]
        
        #get meta
        mdf = df.loc[~df.index.isin(dd_indx), :]
        
        if fmt=='df':
            return ddf, mdf
        elif fmt=='dict':
            return ddf.iloc[:,0].to_dict(), mdf.iloc[:,0].to_dict()
        
        
        

        
    def check_cdf(self, #convenience for checking the df as loaded
                  df, **kwargs): 
        """
        because we deal with multiple forms of the curve data
        """
        
        assert isinstance(df, pd.DataFrame)
        assert len(df.columns)==2
        
        assert df.iloc[:, 0].is_unique
        
        crv_d = df.set_index(0, drop=True).dropna().iloc[:, 0].to_dict()
        
        
        try:
            self.check_crvd(crv_d)
        except Exception as e:
            """letting this pass for backwards compatability"""
            self.logger.warning('curve failed check w/ \n    %s'%e)


    def check_crvd(self, #validate the passed curve_d  
                    crv_d,
                    logger=None):
        
        #=======================================================================
        # if logger is None: logger=self.logger
        # log = logger.getChild('check_crvd')
        #=======================================================================
        
        assert isinstance(crv_d, dict)
        
        #log.debug('on %i'%len(crv_d))
        
        #=======================================================================
        # #check key presence
        #=======================================================================
        miss_l = set(self.cdf_chk_d.keys()).difference(crv_d.keys())
        if not len(miss_l)==0:
            raise Error('dfunc \'%s\' missing keys: %s \n    %s'%(self.tabn, miss_l, self.curves_fp))
        
        #=======================================================================
        # value type
        #=======================================================================
        for k, v in self.cdf_chk_d.items():
            assert k in crv_d, 'passed df for \'%s\' missing key \'%s\''%(self.tabn, k)
            assert isinstance(crv_d[k], v), '%s got bad type on %s'%(self.tabn, k)
            
        #=======================================================================
        # order
        #=======================================================================
        """TODO: check order"""
        

        return True

    
    
    