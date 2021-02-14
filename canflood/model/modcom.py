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

from scipy import interpolate, integrate

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
        r2_passet -- per_asset results from the risk2 model
        r2_ttl  -- total results from risk2
        eventypes -- df of aep, noFail, and rEventName
    
    
    [plotting]
        impactfmt_str -- python formatter to use for formatting the impact results values
    
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
    r2_passet=''
    r2_ttl =''
    eventypes=''
    
    #[plotting]
    """see Plotr"""
    
    #==========================================================================
    # program vars
    #==========================================================================
    

    #minimum inventory expectations
    finv_exp_d = {
        'scale':{'type':np.number},
        'elv':{'type':np.number}
        }
    
    max_depth = 20 #maximum depth for throwing an error in build_depths()
    
    extrap_vals_d = {} #extraploation used {aep:val}
    cplx_evn_d = None #complex event sets {aep: [exEventName1, exEventName1]}
    asset_cnt = 0 #for plotting
    scen_ar_d = dict() #container for empty scenario matrix
    
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
                 absolute_fp=True, #whether filepaths in control file are absolute (False=Relative). 
                 base_dir =None, #for absolute_fp=False, base directory to use (defaults 
                 attriMode = False, #flow control for some attribution matrix functions
                 
                 **kwargs):
        
        #=======================================================================
        # precheck
        #=======================================================================
        mod_logger.info('Model.__init__ start')
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
        
        """TODO: Consider moving this to ComWrkr so Build dialogs can access"""
        self.absolute_fp=absolute_fp
        
        if base_dir is None:
            base_dir = os.path.split(cf_fp)[0]
        self.base_dir = base_dir
        
        
        self.attriMode=attriMode


        """moved to comWrkr
        self.data_d = dict() #dictionary for loaded data sets"""
        
        #=======================================================================
        # wrap
        #=======================================================================
        
        self.logger.debug('finished Model.__init__')
        
        
    def init_model(self, #common inits for all model classes
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
        errors = []
        for chk_d, opt_f in ((self.exp_pars_md,False), (self.exp_pars_op,True)):
            _, l = self.cf_chk_pars(self.pars, copy.copy(chk_d), optional=opt_f)
            errors = errors + l
            
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
        if not getattr(self, self.valid_par):
            raise Error('control file not validated for \'%s\'. please run InputValidator'%self.valid_par)
        
        #wrap
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
                    
            
            
        log.info('finished checking %i sections w/ %i errors. optional=%s \n'%(len(cpars), len(errors), optional))
        
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
    
    def _get_from_cpar(self, #special parameter extraction recognizing object's t ype
                      cpars,
                      sectName,
                      varName,
                      logger = None):
        
        """each parameter should exist on teh class instance.
                we use this to set the type"""
        
        if logger is None: logger=self.logger
        log = logger.getChild('_get_from_cpar')
        #=======================================================================
        # get native type on class
        #=======================================================================
        assert hasattr(self, varName), '\'%s\' does not exist on %s'%(varName, self)
        
        
        #get class instance's native type
        ntype = type(getattr(self, varName))
        
        #==============================================================
        # retrive and typeset  (using native t ype)            
        #==============================================================
        assert isinstance(cpars, configparser.ConfigParser)
        
        csect = cpars[sectName]
        pval_raw = csect[varName] #raw value (always a string)
        
        #boolean
        if ntype == bool:
            pval = csect.getboolean(varName)
        
        #no check or type conversion
        elif getattr(self, varName) is None:
            pval = pval_raw 

        #other types
        else:
            try:
                pval = ntype(pval_raw)
            except Exception as e:
                raise Error('failed to set %s.%s  with input \'%s\' (%s) to %s \n %s'%(
                    sectName, varName, pval_raw, type(pval_raw), ntype, e))
        
        #=======================================================================
        # blank set
        #=======================================================================
        """seems like we're setup for ''.... not sure the value in switching everything over
        if pval == '':
            pval = np.nan"""
        
        log.debug('retrieved \'%s.%s\'=\'%s\' w/ type: \'%s\''%(sectName, varName, pval, type(pval)))
        return pval

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
            log.warning('no checks provided for \'%s.%s\'... skipping'%(sect, varnm))
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
                    
                    raise Error('%s.%s passed aboslute_fp=False but fp exists \n    %s'%(
                        sectName, varName, valRaw))
                else:
                
                    #get the absolute filepath
                    fp = os.path.join(base_dir, valRaw)
                    """dont bother... some models may not use all the fps
                    better to let the check with handles catch things
                    assert os.path.exists(fp), '%s.%s not found'%(sectName, varName)"""
                    if not os.path.exists(fp):
                        log.debug('%s.%s got bad fp: %s'%(sectName, varName, fp))
                
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
    def load_finv(self,#load asset inventory
                   fp = None,
                   dtag = 'finv',
                   #finv_exp_d = None, #finv expeectations
                   ):
        """
        see build_exp_finv() for construction of the expanded binv
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_finv')
        if fp is None: fp = getattr(self, dtag)
        #if finv_exp_d is None: finv_exp_d = self.finv_exp_d #minimum expecatations
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
        """
        this is only checking the first nest
        """
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
        self.cindex = df.index.copy() #set this for checks later
        self.finv_cdf = cdf
        self.data_d[dtag] = df
        
        log.info('finished loading %s as %s'%(dtag, str(df.shape)))
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
            
        
    def load_evals(self,#loading event probability data
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
 
        #======================================================================
        # check2
        #======================================================================
        #check all aeps are below 1
        boolar = np.logical_and(
            aep_ser < 1,
            aep_ser > 0)
        
        assert np.all(boolar), 'passed aeps out of range'
        
        #check logic against whether this model considers failure
        log.debug('\n%s'%aep_ser.to_frame().join(aep_ser.duplicated(keep=False).rename('dupes')))
        if self.exlikes == '': #no failure
            
            assert len(aep_ser.unique())==len(aep_ser), \
            'got duplicated \'evals\' but no \'exlikes\' data was provided.. see logger'
        else:
            assert len(aep_ser.unique())!=len(aep_ser), \
            'got unique \'evals\' but \'exlikes\' data is provided... see logger'
        
        #=======================================================================
        # #assemble event type  frame
        #=======================================================================
        """this is a late add.. would have been nice to use this more in multi_ev"""
        df = aep_ser.to_frame().reset_index(drop=False).rename(columns={'index':'rEventName'})
        df['noFail'] = True
        
        self.eventType_df = df
        
        #======================================================================
        # #wrap
        #======================================================================
        log.debug('prepared aep_ser w/ %i: \n    %s'%(len(aep_ser), aep_ser.to_dict()))
        
        
        #self.aep_ser = aep_ser.sort_values()
        self.data_d[dtag] = aep_ser #setting for consistency. 
        
        self.expcols = aep_ser.index.copy() #set for later checks
        
    def load_expos(self,#generic exposure loader
                   fp = None,
                   dtag = 'expos',
                   check_monot=False, #whether to check monotonciy
                   logger=None,
                   ):
        """
        loads, sets index, slices to finv, and lots of checks, adds result to data_d
        
        called by:
            dmg2
            risk1
            risk2 (via load_exlikes())
        """
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        
        log = logger.getChild('load_expos')
        if fp is None: fp = getattr(self, dtag)
        cid = self.cid
        
        #=======================================================================
        # prechecks1
        #=======================================================================
        assert 'finv' in self.data_d, 'call load_finv first'
        assert isinstance(self.cindex, pd.Index), 'bad cindex'
        assert os.path.exists(fp), '%s got invalid filepath \n    %s'%(dtag, fp)
        #======================================================================
        # load it
        #======================================================================
        df_raw = pd.read_csv(fp, index_col=None)
        
        #======================================================================
        # check raw data
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

        if dtag == 'exlikes':
            miss_l = set(df.columns).difference(self.expcols)
        else:
            miss_l = set(self.expcols).symmetric_difference(df.columns)
            
        assert len(miss_l) == 0, '%i eventName mismatch on \'%s\' and \'evals\': \n    %s'%(
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
            """forcing this becuase %inundation should never add ground elevations"""
            assert self.felv =='datum', 'felv must equal \'datum\' for pct inundation runs'

        #======================================================================
        # set it
        #======================================================================
        """consider passing this to caller and letting the caller handel"""
        self.data_d[dtag] = df
        
        
        log.info('finished loading %s as %s'%(dtag, str(df.shape)))
        
        return
        
    def load_exlikes(self,#loading exposure probability data (e.g. failure raster poly samples)
                     dtag = 'exlikes',
                   **kwargs
                   ):
        """
        load, fill nulls, add 1.0 for missing, set in data_d
        called by:
            risk1
            risk2
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_exlikes')
        assert 'evals' in self.data_d, 'evals data set required with conditional exposure exlikes'
        aep_ser = self.data_d['evals'].astype(float)
        

        
        #======================================================================
        # load the data-------
        #======================================================================
        self.load_expos(dtag=dtag, **kwargs) #load, clean, slice, add to data_d
        edf = self.data_d.pop(dtag) #pull out the reuslt
        log.debug('loading w/ %s'%str(edf.shape))

        """TODO: Consider moving these onto the build tool"""
        #======================================================================
        # fill nulls-----
        #======================================================================
        """
        better not to pass any nulls.. but if so.. should treat them as ZERO!!
            Null = no failure polygon = no failure
            
        also best not to apply precision to these values
        
        2020-01-12: moved null filling to lisamp.py
            keeping it here as well for backwards compatability
        """
        booldf = edf.isna()
        if booldf.any().any():
            log.warning('got %i (of %i) nulls!... filling with zeros'%(booldf.sum().sum(), booldf.size))
        edf = edf.fillna(0.0)
        
        #==================================================================
        # check/add event probability totals----
        #==================================================================
        
        #=======================================================================
        # assemble complex aeps
        #=======================================================================
        #collect event names
        cplx_evn_d = dict()
        cnt=0
        for aep in aep_ser.unique(): #those aeps w/ duplicates:
            cplx_evn_d[aep] = aep_ser[aep_ser==aep].index.tolist()
            cnt=max(cnt, len(cplx_evn_d[aep])) #get the size of the larget complex event
        

        assert cnt > 1, 'passed \'exlikes\' but there are no complex events'
        

        def get_cplx_df(df, aep=None, exp_l=None): #retrieve complex data helper
            if exp_l is None:
                exp_l = cplx_evn_d[aep]
            return df.loc[:, df.columns.isin(exp_l)]
            
        #=======================================================================
        # check we dont already exceed 1
        #=======================================================================
        valid = True
        for aep, exp_l in cplx_evn_d.items():
            cplx_df = get_cplx_df(edf, exp_l=exp_l) #get data for this event
            boolidx = cplx_df.sum(axis=1).round(self.prec)>1.0 #find those exceeding 1.0

            if boolidx.any():
                valid = False
                rpt_df = cplx_df[boolidx].join(
                    cplx_df[boolidx].sum(axis=1).rename('sum'))
                log.debug('aep%.4f: \n\n%s'%(aep, rpt_df))
                log.error('aep%.4f w/ %i exEvents failed %i (of %i) Psum<1 checks (Pmax=%.2f).. see logger \n    %s'%(
                    aep, len(exp_l), boolidx.sum(), len(boolidx),cplx_df.sum(axis=1).max(), exp_l))
                
        assert valid, 'some complex event probabilities exceed 1'
            
        #=======================================================================
        # #identify those events that need filling
        #=======================================================================
        fill_exn_d = dict()
        for aep, exn_l in cplx_evn_d.items(): 
            
            miss_l = set(exn_l).difference(edf.columns)
            assert len(miss_l)<2, 'can only fill one exposure column per complex event: %s'%miss_l
            
            if len(miss_l)==1:
                fill_exn_d[aep] = list(miss_l)[0]
            elif len(miss_l)==0:
                pass #not filling any events
            else: raise Error('only allowed 1 empty')

                
        log.debug('calculating probaility for %i complex events with remaining secnodaries'%(
            len(fill_exn_d)))
            
        self.noFailExn_d =copy.copy(fill_exn_d) #set this for the probability calcs
        
        
 
        
        #=======================================================================
        # fill in missing 
        #=======================================================================
        res_d = dict()
        for aep, exn_miss in fill_exn_d.items():
            """typically this is a single column generated for the failure raster
                but this should work for multiple failure rasters"""
            #===================================================================
            # legacy method
            #===================================================================
            if self.event_rels == 'max':
                edf[exn_miss]=1
                
            #===================================================================
            # rational (sum to 1)
            #===================================================================
            else:

                #data provided on this event
                cplx_df = get_cplx_df(edf, aep=aep)
                assert len(cplx_df.columns)==(len(cplx_evn_d[aep])-1), 'bad column count'
                assert (cplx_df.sum(axis=1)<=1).all() #check we don't already exceed 1 (redundant)
                
                #set remainder values
                edf[exn_miss] = 1- cplx_df.sum(axis=1)
                
                log.debug('for aep %.4f \'%s\' set %i remainder values (mean=%.4f)'%(
                    aep, exn_miss, len(cplx_df), edf[exn_miss].mean()))
                
            res_d[exn_miss] = round(edf[exn_miss].mean(), self.prec)
            
        if len(res_d)>0: log.info(
            'set %i complex event conditional probabilities using remainders \n    %s'%(
                len(res_d), res_d))
 

        """NO! probabilities must sum to 1
        missing column = no secondary likelihoods at all for this event.
        all probabilities = 1
        
        #identify those missing in the edf (compared with the expos)
        miss_l = set(self.expcols).difference(edf.columns)
        
        #add 1.0 for any missing
        if len(miss_l) > 0:
            
            log.info('\'exlikes\' missing %i events... setting to 1.0\n    %s'%(
                len(miss_l), miss_l))
            
            for coln in miss_l:
                edf[coln] = 1.0"""
            
        log.debug('prepared edf w/ %s'%str(edf.shape))
        

        #=======================================================================
        # #check conditional probabilities sum to 1----
        #=======================================================================

        valid = True
        for aep, exp_l in cplx_evn_d.items():
            cplx_df = get_cplx_df(edf, exp_l=exp_l) #get data for this event
            boolidx = cplx_df.sum(axis=1)!=1.0 #find those exceeding 1.0
        


            if boolidx.any():
                """allowing this to mass when event_rels=max"""
                valid = False
                log.warning('aep%.4f failed %i (of %i) Psum<=1 checks (Pmax=%.2f)'%(
                    aep, boolidx.sum(), len(boolidx), cplx_df.sum(axis=1).max()))
        
        if not self.event_rels == 'max':
            assert valid, 'some complex event probabilities exceed 1'
            
            


        #==================================================================
        # wrap
        #==================================================================

        # update event type  frame
        """this is a late add.. would have been nice to use this more in multi_ev
        see load_evals()
        """
        
        self.eventType_df['noFail'] = self.eventType_df['rEventName'].isin(fill_exn_d.values())
        
        
        self.data_d[dtag] = edf
        self.cplx_evn_d = cplx_evn_d
        
        return
        
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
        
        #=======================================================================
        # prechecks
        #=======================================================================
        
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
        """2021-01-13: dropped the _dmg suffix during dmg2.run()
        left this cleaning for backwards compatailibity"""
        boolcol = df.columns.str.endswith('_dmg')
        enm_l = df.columns[boolcol].str.replace('_dmg', '').tolist()
        
        ren_d = dict(zip(df.columns[boolcol].values, enm_l))
        df = df.rename(columns=ren_d)
        
        #set new index
        df = df.set_index(cid, drop=True).sort_index(axis=0)
        
        #apply rounding
        df = df.round(self.prec)
        
        #======================================================================
        # postcheck
        #======================================================================
        #assert len(enm_l) > 1, 'failed to identify sufficient damage columns'
        

        #check cid index match
        assert np.array_equal(self.cindex, df.index), \
            'provided \'%s\' index (%i) does not match finv index (%i)'%(dtag, len(df), len(self.cindex))
        
        #check rEvents
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
        
        self.asset_cnt=len(df) #for plotting

    def load_attrimat(self,
                      dxcol_lvls=2, #levels present in passed data
                      fp=None,
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
        log = logger.getChild('load_attrimat')
        if dtag is None: dtag = self.attrdtag_in
        if fp is None: fp = getattr(self, dtag)
        cid = self.cid
        
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert self.attriMode
        #assert 'dmgs' in self.data_d, 'dmgs data set required with attrimat'
        assert not fp=='', 'passed attriMode=True but got no value for \'%s\''%dtag
        assert os.path.exists(fp), '%s got invalid filepath \n    %s'%(dtag, fp)
        
        #assert isinstance(self.expcols, pd.Index), 'bad expcols'
        #assert isinstance(self.cindex, pd.Index), 'bad cindex'

        #======================================================================
        # load it
        #======================================================================
        dxcol = pd.read_csv(fp, index_col=0, header=list(range(0,dxcol_lvls)))
        
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
        self.data_d[dtag] = dxcol

        log.info('finished loading %s as %s'%(dtag, str(dxcol.shape)))
  
        
   
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
            exp_fcolns = exp_fcolns + ['ftag', 'fcap']
            
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
        for coln in ['ftag']:
            bx =  bdf[coln].isna()
            if bx.any():
                log.debug('\n%s'%bdf.loc[bx, :])
                raise Error('got %i \'%s\' nulls...see logger'%(bx.sum(), coln))
            """
            view(bdf)
            """
        
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
        
    def ev_multis(self, #calculate (discrete) expected value from events w/ multiple exposure sets
           ddf, #damages per exposure set (
           edf, #secondary liklihoods per exposure set ('exlikes'). see load_exlikes()
                # nulls were replaced by 0.0 (e.g., asset not provided a secondary probability)
                # missing colums were replaced by 1.0 (e.g., non-failure events)
            
           aep_ser,
           event_rels=None, #ev calculation method
                #max:  maximum expected value of impacts per asset from the duplicated events
                    #resolved damage = max(damage w/o fail, damage w/ fail * fail prob)
                    #default til 2020-12-30
                #mutEx: assume each event is mutually exclusive (only one can happen)
                    #lower bound
                #indep: assume each event is independent (failure of one does not influence the other)
                    #upper bound
           logger=None,
                       ):
        """
        
        we accept multiple exposure sets for a single event  
            e.g. 'failure' raster and 'no fail'
            
            where each exposure set is assigned a conditional probability in 'exlikes' (edf)
                e.g. exlikes=1.0  means only one exposure set
        
        
        for resolving conditional probabilities for a single exposure set:
            see build.lisamp.LikeSampler.run()
            (no impacts)
        
        view(edf)
        """
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('ev_multis')
        cplx_evn_d = self.cplx_evn_d #{aep: [eventName1, eventName2,...]}
        if event_rels is None: event_rels = self.event_rels

        #======================================================================
        # precheck
        #======================================================================
        assert isinstance(cplx_evn_d, dict)
        assert len(cplx_evn_d)>0
        assert (edf.max(axis=1)<=1).all(), 'got probs exceeding 1'
        assert (edf.min(axis=1)>=0).all(), 'got negative probs'
        
        assert ddf.shape == edf.shape, 'shape mismatch'
        """where edf > 0 ddf should also be > 0
        but leave this check for the input validator"""
        #======================================================================
        # get expected values of all damages
        #======================================================================
        """ skip this based on event_rels?"""
        evdf = ddf*edf
        
        log.info('resolving EV w/ %s, %i event sets, and event_rels=\'%s\''%(
            str(evdf.shape), len(cplx_evn_d), event_rels))
        assert not evdf.isna().any().any()
        assert evdf.min(axis=1).min()>=0
        #======================================================================
        # loop by unique aep and resolve-----
        #======================================================================
        res_df = pd.DataFrame(index=evdf.index, columns = aep_ser.unique().tolist())
        meta_d = dict() 
        #for indxr, aep in enumerate(aep_ser.unique().tolist()):
        for indxr, (aep, exn_l) in enumerate(cplx_evn_d.items()):
            
            #===================================================================
            # setup
            #===================================================================
            self.feedback.setProgress((indxr/len(aep_ser.unique())*80))
            assert isinstance(aep, float)
            
            if not event_rels=='max':
                if not (edf.loc[:, exn_l].sum(axis=1).round(self.prec) == 1.0).all():
 
                    raise Error('aep %.4f probabilities fail to sum'%aep)
            
            log.debug('resolving aep %.4f w/ %i event names: %s'%(aep, len(exn_l), exn_l))
            
            """
            view(self.att_df)
            """
            #===================================================================
            # simple events.. nothing to resolve----
            #===================================================================
            if len(exn_l) == 1:
                """
                where hazard layer doesn't have a corresponding failure layer
                """
                res_df.loc[:, aep] =  evdf.loc[:, exn_l].iloc[:, 0]
                meta_d[aep] = 'simple event'
                
                """no attribution modification required"""
                
            #===================================================================
            # one failure possibility-----
            #===================================================================
            elif len(exn_l) == 2:
                
                if event_rels == 'max':
                    """special legacy method... see below"""
                    res_df.loc[:, aep] = evdf.loc[:, exn_l].max(axis=1)
                else:
                    """where we only have one failure event
                        events are mutually exclusive by default"""
                    res_df.loc[:, aep] = evdf.loc[:, exn_l].sum(axis=1)
                    

            
            #===================================================================
            # complex events (more than 2 failure event)----
            #===================================================================
            else:

                """
                view(edf.loc[:, exn_l])
                view(ddf.loc[:, exn_l])
                view(evdf.loc[:, exn_l])
                """
                
                log.info('resolving alternate damages for aep %.2e from %i events: \n    %s'%(
                    aep, len(exn_l), exn_l))
                
                if event_rels == 'max':
                    """
                    matching 2020 function
                    taking the max EV on each asset
                        where those rasters w/o exlikes P=1 (see load_exlikes())
                        
                    WARNING: this violates probability logic
                    
                    """
                    
                    res_df.loc[:, aep] = evdf.loc[:, exn_l].max(axis=1)
                    
                elif event_rels == 'mutEx':
                    res_df.loc[:, aep] = evdf.loc[:, exn_l].sum(axis=1)

                elif event_rels == 'indep':
                    """
                    NOTE: this is a very slow routine
                    TODO: parallel processing
                    """
                    
                    #identify those worth calculating
                    bx = np.logical_and(
                        (edf.loc[:, exn_l]>0).sum(axis=1)>1, #with multiple real probabilities
                        ddf.loc[:,exn_l].sum(axis=1).round(self.prec)>0  #with some damages
                        )
                    
                    #build the event type flags
                    etype_df = pd.Series(index=exn_l, dtype=np.bool, name='mutEx').to_frame()

                    #mark the failure event
                    etype_df.loc[etype_df.index.isin(self.noFailExn_d.values()), 'mutEx']=True
                    assert etype_df.iloc[:,0].sum()==1

                    """todo: consider using 'apply'
                    tricky w/ multiple data frames...."""
                    log.info('aep %.4f calculating %i (of %i) EVs from %i events w/ indepedence'%(
                        aep, bx.sum(), len(bx), len(exn_l)))
                    
                    #loop and resolve each asset
                    for cindx, pser in edf.loc[bx, exn_l].iterrows():
                   
                        #assemble the prob/consq set for this asset
                        inde_df = pser.rename('prob').to_frame().join(
                            ddf.loc[cindx, exn_l].rename('consq').to_frame()
                            ).join(etype_df)
                            
                        #resolve for this asset
                        res_df.loc[cindx, aep] = self._get_indeEV(inde_df)
                        
                    #fill in remainderes
                    assert res_df.loc[~bx, aep].isna().all()
                    res_df.loc[~bx, aep] = evdf.loc[~bx, exn_l].max(axis=1)
                        
                        
                        
                else: raise Error('bad event_rels: %s'%event_rels)

                
            if res_df[aep].isna().any():
                raise Error('got nulls on %s'%aep)
                
        #=======================================================================
        # # check
        #=======================================================================
        assert res_df.min(axis=1).min()>=0
        if not res_df.notna().all().all():
            raise Error('got %i nulls'%res_df.isna().sum().sum())
        #=======================================================================
        # attribution------
        #=======================================================================
        if self.attriMode:
            atr_dxcol_raw = self.att_df.copy()
            mdex = atr_dxcol_raw.columns
            nameRank_d= {lvlName:i for i, lvlName in enumerate(mdex.names)}
            edf = edf.sort_index(axis=1, ascending=False)
            """
            view(edf)
            view(atr_dxcol_raw)
            view(atr_dxcol)
            view(bool_dxcol)
            view(mult_dxcol)
            pd.__version__
            """
            if event_rels == 'max':
                """                
                turns out we need to get the ACTUAL expected value matrix
                    here we reconstruct by gettin a max=0, no=1, shared=0.5 matrix
                    then mutiplyling that by the evdf to get the ACTUAL ev matrix"""
                
                #===============================================================
                # build multipler (boolean based on max)
                #===============================================================
                mbdxcol=None
                for aep, gdf in atr_dxcol_raw.groupby(level=0, axis=1):
                    #get events on this aep
                    exn_l = gdf.columns.remove_unused_levels().levels[nameRank_d['rEventName']]
                    
                    #identify maximums
                    booldf = evdf.loc[:, exn_l].isin(evdf.loc[:, exn_l].max(axis=1)).astype(int)
                    
                    #handle duplicates (assign equal portion)
                    if len(exn_l)>1:
                        boolidx =  booldf.eq(booldf.iloc[:,0], axis=0).all(axis=1)
                        booldf.loc[boolidx, :] = float(1/len(exn_l))

                    #add in the dummy lvl0 aep
                    bdxcol = pd.concat([booldf], keys=[aep], axis=1)

                    if mbdxcol is None:
                        mbdxcol = bdxcol
                    else:
                        mbdxcol = mbdxcol.merge(bdxcol, how='outer', left_index=True, right_index=True)
                        
                    log.debug('%.4f: got %s'%(aep, str(mbdxcol.shape)))
                    
                #check it
                self.check_attrimat(atr_dxcol=mbdxcol, logger=log)


                #===============================================================
                # apply multiplication
                #===============================================================
                #get EV from this
                evdf1 = mbdxcol.multiply(evdf, axis='column', level=1).droplevel(level=0, axis=1)
                

                    
            elif event_rels=='mutEx':
 
                evdf1=evdf

            elif event_rels=='indep':
                raise Error('attribution not implemented for event_rels=\'indep\'')
            else: raise Error('bad evnet-Rels')
            
            #===================================================================
            # common
            #===================================================================
            #multiply thorugh to get all the expected value components 
            i_dxcol = atr_dxcol_raw.multiply(evdf1, axis='columns', level=1)
                
            #divide by the event totals to get ratios back
            atr_dxcol = i_dxcol.divide(res_df, axis='columns', level='aep')
            
            #apportion null values
            atr_dxcol = self._attriM_nulls(res_df, atr_dxcol, logger=log)
            
            self.att_df = atr_dxcol
        #======================================================================
        # wrap
        #======================================================================

        
        log.info('resolved to %i unique event damages'%len(res_df.columns))
        
        return res_df.sort_index(axis=1)
    
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
    
    def _get_indeEV(self,
                    inde_df #prob, consq, mutual exclusivity flag for each exposure event 
                    ):
        
        """
        get the expected value at an asset with 
            n>1 indepednet failure events (w/ probabilities)
            and 1 noFail event
        """
        
        #=======================================================================
        # prechecks  
        #=======================================================================
        #check the columns
        miss_l = set(['prob', 'consq', 'mutEx']).symmetric_difference(inde_df.columns)
        assert len(miss_l)==0
        
        #=======================================================================
        # failures---------
        #=======================================================================
        bxf = ~inde_df['mutEx']
        #=======================================================================
        # assemble complete scenario matrix
        #=======================================================================
        n = len(inde_df[bxf])
        
        #build it
        if not n in self.scen_ar_d:
            scenFail_ar = np.array([i for i in itertools.product(['yes','no'], repeat=n)])
            self.scen_ar_d[n] = copy.copy(scenFail_ar)
        
        #retrieve pre-built
        else:
            scenFail_ar = copy.copy(self.scen_ar_d[n])

        
        #=======================================================================
        #  probs
        #=======================================================================
        sFailP_df = pd.DataFrame(scenFail_ar, columns=inde_df[bxf].index)
        
        #expand probabilities to mathc size
        prob_ar  = np.tile(inde_df.loc[bxf, 'prob'].to_frame().T.values, (len(sFailP_df), 1))
        
        #swap in positives
        sFailP_df = sFailP_df.where(
            np.invert(sFailP_df=='yes'), 
            prob_ar, inplace=False)
        
        #swap in negatives
        sFailP_df = sFailP_df.where(
            np.invert(sFailP_df=='no'), 
            1-prob_ar, inplace=False).astype(np.float64)
        
        #combine
        sFailP_df['pTotal'] = sFailP_df.prod(axis=1)
        assert round(sFailP_df['pTotal'].sum(), self.prec)==1, inde_df
        
        #=======================================================================
        # consequences
        #=======================================================================
        sFailC_df = pd.DataFrame(scenFail_ar, columns=inde_df[bxf].index).replace(
            {'yes':1.0, 'no':0.0}).astype(np.float64)
        
        #add in consequences
        sFailC_df = sFailC_df.multiply(inde_df.loc[bxf, 'consq'])
        
        #get maximums
        sFailC_df['cTotal'] = sFailC_df.max(axis=1)
        
        #=======================================================================
        # expected values
        #=======================================================================
        evFail_ser = sFailP_df['pTotal']*sFailC_df['cTotal']
        
        #=======================================================================
        # total-------
        #=======================================================================
        noFail_ar = inde_df.loc[~bxf, ['prob', 'consq']].iloc[0, :].values
        
        return evFail_ser.sum() + noFail_ar[0]*noFail_ar[1]



    def calc_ead(self, #get EAD from a set of impacts per event
                 df_raw, #xid: aep
                 ltail = None,
                 rtail = None,
                 drop_tails = False, #whether to remove the dummy tail values from results
                 dx = None, #damage step for integration (default:None)
                 logger = None
                 ):      
        
        """
        #======================================================================
        # inputs
        #======================================================================
        ltail: left tail treatment code (low prob high damage)
            flat: extend the max damage to the zero probability event
            extrapolate: extend the fucntion to the zero aep value (interp1d)
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
        assert not ltail is None
        assert not rtail is None
        
        if not ltail in ['flat', 'extrapolate', 'none']:
            try:
                ltail  = float(ltail)
            except Exception as e:
                raise Error('failed to convert \'ltail\'=\'%s\' to numeric \n    %s'%(ltail, e))
            
        if not rtail in ['extrapolate', 'none']:
            rtail = float(rtail)
            
        log.info('getting ead on %s w/ ltail=\'%s\' and rtail=\'%s\''%(
            str(df_raw.shape), ltail, rtail))
        

        #=======================================================================
        # get tail values-----
        #=======================================================================
        df = df_raw.copy().sort_index(axis=1, ascending=False)
        
        #identify columns to calc ead for
        bx = (df > 0).any(axis=1) #only want those with some real damages
        
        assert bx.any(), 'no valid results on %s'%str(df.shape)
        #=======================================================================
        # precheck
        #=======================================================================
        self.check_eDmg(df, dropna=True, logger=log)

        #======================================================================
        # left tail
        #======================================================================
        
        #flat projection
        if ltail == 'flat':
            df.loc[:,0] = df.iloc[:,0] 
            
            if len(df)==1: 
                self.extrap_vals_d[0] = df.loc[:,0].mean().round(self.prec) #store for later
            
        elif ltail == 'extrapolate': #DEFAULT
            df.loc[bx,0] = df.loc[bx, :].apply(self._extrap_rCurve, axis=1, left=True)
            
            #extrap vqalue will be different for each entry
            if len(df)==1: 
                self.extrap_vals_d[0] = df.loc[:,0].mean().round(self.prec) #store for later

        elif isinstance(ltail, float):
            """this cant be a good idea...."""
            df.loc[bx,0] = ltail
            
            self.extrap_vals_d[0] = ltail #store for later
            
        elif ltail == 'none':
            pass
        else:
            raise Error('unexected ltail key'%ltail)
        
        
        #======================================================================
        # right tail
        #======================================================================
        if rtail == 'extrapolate':
            """just using the average for now...
            could extraploate for each asset but need an alternate method"""
            aep_ser = df.loc[bx, :].apply(
                self._extrap_rCurve, axis=1, left=False)
            
            aep_val = round(aep_ser.mean(), 5)
            
            assert aep_val > df.columns.max()
            
            df.loc[bx, aep_val] = 0
            
            log.info('using right intersection of aep= %.2e from average extraploation'%(
                aep_val))
            
            
            self.extrap_vals_d[aep_val] = 0 #store for later 
            
        
        elif isinstance(rtail, float): #DEFAULT
            aep_val = round(rtail, 5)
            assert aep_val > df.columns.max(), 'passed rtail value (%.2f) not > max aep (%.2f)'%(
                aep_val, df.columns.max())
            
            df.loc[bx, aep_val] = 0
            
            log.debug('setting ZeroDamage event from user passed \'rtail\' aep=%.7f'%(
                aep_val))
            
            self.extrap_vals_d[aep_val] = 0 #store for later 

        elif rtail == 'flat':
            #set the zero damage year as the lowest year in the model (with a small buffer) 
            aep_val = max(df.columns.tolist())*(1+10**-(self.prec+2))
            df.loc[bx, aep_val] = 0
            
            log.info('rtail=\'flat\' setting ZeroDamage event as aep=%.7f'%aep_val)
            
        elif rtail == 'none':
            log.warning('no rtail extrapolation specified! leads to invalid integration bounds!')
        
        else:
            raise Error('unexpected rtail %s'%rtail)
            
        #re-arrange columns so x is ascending
        df = df.sort_index(ascending=False, axis=1)
        #======================================================================
        # check  again
        #======================================================================
        self.check_eDmg(df, dropna=True, logger=log)

        #======================================================================
        # calc EAD-----------
        #======================================================================
        #get reasonable dx (integration step along damage axis)
        """todo: allow the user to set t his"""
        if dx is None:
            dx = df.max().max()/100
        assert isinstance(dx, float)
        

        
        #apply the ead func
        df.loc[bx, 'ead'] = df.loc[bx, :].apply(
            self._get_ev, axis=1, dx=dx)
        
        
        df.loc[:, 'ead'] = df['ead'].fillna(0) #fill remander w/ zeros
        
        #======================================================================
        # check it
        #======================================================================
        boolidx = df['ead'] < 0
        if boolidx.any():
            log.warning('got %i (of %i) negative eads'%( boolidx.sum(), len(boolidx)))
        
        """
        df.columns.dtype
        """
        #======================================================================
        # clean results
        #======================================================================
        if drop_tails:
            #just add the results values onto the raw
            res_df = df_raw.join(df['ead']).round(self.prec)
        else:
            #take everything
            res_df = df.round(self.prec)
            
        #final check
        """nasty conversion because we use aep as a column name..."""
        cdf = res_df.drop('ead', axis=1)
        cdf.columns = cdf.columns.astype(float)
            
        self.check_eDmg(cdf, dropna=True, logger=log)
            
        return res_df


    def _extrap_rCurve(self,  #extraploating EAD curve data
               ser, #row of dmages (y values) from big df
               left=True, #whether to extraploate left or right
               ):
        
        """
        
        #=======================================================================
        # plot helper
        #=======================================================================
        from matplotlib import pyplot as plt

        plt.close()
        
        fig = plt.figure()
        ax = fig.add_subplot()
        
        ax.plot(ser.index.values,  ser.values, 
            linestyle='None', marker="o")
            
        ax.plot(0, f(0), marker='x', color='red')

        ax.grid()
        plt.show()
        

        """
        
        #build interpolation function from data
        if left:
            """
            typically this just extends the line from the previous 2 extreme impacts
            shouldnt effect results much when modeled extremes are 'extreme'
            
            theres probably a better function to use since we're only using the 'extrapolate' bit
            """
            f = interpolate.interp1d(
                ser.index.values, #xvals: aep
                ser.values, #yvals: impacts 
                 fill_value='extrapolate', #all we're using
                 )
            
        else:
            #xvalues = damages
            f = interpolate.interp1d(ser.values, ser.index.values,
                                     fill_value='extrapolate')
            
        
        #calculate new y value by applying interpolation function
        result = float(f(0)) #y value at x=0
        
        if not result >=0:
            raise Error('got negative extrapolation: %.2f'%result)
        
        return result 
    
    def _get_ev(self, #integration caller
               ser, #row from damage results
               dx = 0.1,
               ):
        """
        should integrate along the damage axis (0 - infinity)
        """
        
        
        #print('%i.%s    %s'%(self.cnt, ser.name, ser.to_dict()))
        
        x = ser.tolist() #impacts
        y = ser.index.values.round(self.prec+2).tolist() #AEPs
        
        """
        from matplotlib import pyplot as plt
        #build plot
        lines = plt.plot(x, y)
        #lines = plt.semilogx(x, y)
        
        #format
        ax = plt.gca()
        ax.grid()
        ax.set_xlim(1, max(x)) #aep limits
        ax.set_ylabel('AEP')
        ax.set_xlabel('impacts')
        
        
        plt.show()
        
        self.rtail
        """
        
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
            

        return round(ead_tot, self.prec)
    
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
    
    def _get_ttl_ari(self, df): #add an ari column to a frame (from the aep vals)
        
        ar = df.loc[:,'aep'].T.values
        
        ar_ari = 1/np.where(ar==0, #replaced based on zero value
                           sorted(ar)[1]/10, #dummy value for zero (take the second smallest value and divide by 10)
                           ar) 
        
        df['ari'] = ar_ari.astype(np.int32)
        
        return 
            
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
    
    #===========================================================================
    # PLOTTING-------
    #===========================================================================
    def risk_plot(self, #impacts vs ARI 
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
        TODO: harmonize w/ riskPlot()
        """
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('risk_plot')
        log.warning('depreciated!!')
        if dmg_ser is None: dmg_ser = self.res_ser.copy()
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
        """todo: move this up"""
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
        
        #======================================================================
        # data manipulations
        #======================================================================
        #get ead
        ead_tot, dmg_ser1 = self.fmt_dmg_plot(dmg_ser)
                
        
        #get aep series
        aep_ser = dmg_ser1.copy()
        aep_ser.loc[:] = 1/dmg_ser1.index
        
        
        #======================================================================
        # labels
        #======================================================================\
        
        val_str = 'annualized impacts = %s \nltail=\'%s\',  \nrtail=\'%s\''%(
            dfmt.format(ead_tot/basev), self.ltail, self.rtail) + \
            '\nfinv_cnt = %i, \nevent_rels = \'%s\', \nprec = %i'%(
                self.asset_cnt, self.event_rels, self.prec)
        
        title = '%s.%s Impact-%s plot on %i events'%(self.name,self.tag, xlab, len(dmg_ser1))
        
        #======================================================================
        # figure setup
        #======================================================================
        plt.close()
        fig = plt.figure(figsize=figsize,
                     tight_layout=False,
                     constrained_layout = True,
                     )

        
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
        xar,  yar = dmg_ser1.index.values, dmg_ser1.values
        pline1 = ax1.semilogx(xar,yar,
                            label       = y1lab,
                            color       = self.color,
                            linestyle   = self.linestyle,
                            linewidth   = self.linewidth,
                            alpha       = self.alpha,
                            marker      = self.marker,
                            markersize  = self.markersize,
                            fillstyle   = self.fillstyle, #marker fill style
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
        y_text = ymin + (ymax1 - ymin)*.2 #1/10 above the bottom ax1is
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
        if grid: 
            ax1.grid()
        

        #legend
        h1, l1 = ax1.get_legend_handles_labels() #pull legend handles from axis 1
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1+h2, l1+l2, loc=1) #turn legend on with combined handles
        
        return fig
    """
    plt.show()
    """
    
    def plot_aep(self, #AEP vs impacts
                  dmg_ser = None,
                  
                  #labels
                  y1lab='AEP',   xlab=None, 
                  
                  #format controls
                  grid = True, 
                  basev = 1, #base value for dividing damage values
                  dfmt = None, #formatting of damage values 
                  
                  
                  #figure parametrs
                  figsize     = (6.5, 4), 
                    
                    #hatch pars
                    hatch =  None,
                    h_color = 'red',
                    h_alpha = 0.1,
                    
                    xlrot = 45, #rotration for xlabels
                  ):
        

        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('plot_aep')
        log.warning('depreciated!!')
        if dmg_ser is None: dmg_ser = self.res_ser.copy()
        if dfmt is None: dfmt = self.plot_fmt
        if xlab is None: xlab = self.y1lab #pull from risk_plot notation

        #======================================================================
        # precheck
        #======================================================================
        assert isinstance(dmg_ser, pd.Series)
        assert 'ead' in dmg_ser.index, 'dmg_ser missing ead index'
        
        log.info('on %i events \n    %s'%(len(dmg_ser), dmg_ser.to_dict()))
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
        
        #======================================================================
        # data manipulations
        #======================================================================
        aep_ser = dmg_ser.drop('ead')
        ead_tot = dmg_ser['ead']
                
        #======================================================================
        # labels
        #======================================================================\
        
        val_str = 'annualized impacts = %s \nltail=\"%s\',  rtail=\'%s\''%(
            dfmt.format(ead_tot/basev), self.ltail, self.rtail)
        
        title = '%s.%s Impact-%s plot on %i events'%(self.name,self.tag, y1lab, len(aep_ser))
        
        #======================================================================
        # figure setup
        #======================================================================
        plt.close()
        fig = plt.figure(figsize=figsize,
                     tight_layout=False,
                     constrained_layout = True,
                     )

        
        #axis setup
        ax1 = fig.add_subplot(111)
        
        #aep units
        ax1.set_xlim(0, max(aep_ser)) #aep limits 
        ax1.set_ylim(0, max(aep_ser.index)*1.1)
        
        """I think we need to use a label formatter instead
        #ari units
        ax2 = ax1.twiny()
        ax2.set_xlabel(x2lab)
        ax2.set_xlim(99999999, 1/max(aep_ser.index))"""
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_ylabel(y1lab)

        ax1.set_xlabel(xlab)
        """
        plt.close()
        plt.show()
        """
        #======================================================================
        # fill the plot
        #======================================================================
        #damage plot
        xar,  yar = aep_ser.values.astype(np.float), aep_ser.index.values
        pline1 = ax1.plot(xar,yar,
                            label       = y1lab,
                            color       = self.color,
                            linestyle   = self.linestyle,
                            linewidth   = self.linewidth,
                            alpha       = self.alpha,
                            marker      = self.marker,
                            markersize  = self.markersize,
                            fillstyle   = self.fillstyle, #marker fill style
                            )
        
        #add a hatch

        polys = ax1.fill_betweenx(yar.astype(np.float), x1=xar, x2=0, 
                                color       = h_color, 
                                alpha       = h_alpha,
                                hatch       = hatch)
        


        #=======================================================================
        # Add text string 'annot' to lower left of plot
        #=======================================================================
        xmin, xmax1 = ax1.get_xlim()
        ymin, ymax1 = ax1.get_ylim()
        
        x_text = xmin + (xmax1 - xmin)*.5 # 1/10 to the right of the left ax1is
        y_text = ymin + (ymax1 - ymin)*.2 #1/10 above the bottom ax1is
        anno_obj = ax1.text(x_text, y_text, val_str)
        
        #=======================================================================
        # format axis labels
        #======================================================= ================
        #damage values (xaxis)
        old_tick_l = ax1.get_xticks() #get teh old labels
         
        # build the new ticks
        l = [dfmt.format(value/basev) for value in old_tick_l]
              
        #apply the new labels
        ax1.set_xticklabels(l, rotation=xlrot)

        #=======================================================================
        # #ARI (xaxis for ax1)
        # ax1.get_xaxis().set_major_formatter(
        #         matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        #=======================================================================
        
        #=======================================================================
        # post formatting
        #=======================================================================
        if grid: 
            ax1.grid()
        

        #legend
        h1, l1 = ax1.get_legend_handles_labels() #pull legend handles from axis 1

        ax1.legend(h1, l1, loc=2) #turn legend on with combined handles
        
        return fig
    """
    plt.show()
    """
    
    def fmt_dmg_plot(self,#formatting damages for plotting
                     dmg_ser_raw): 
        
        #get ead
        dmg_ser = dmg_ser_raw.copy()
        ead_tot = dmg_ser['ead']
        del dmg_ser['ead'] #remove it from plotter values
        
        
        #get damage series to plot
        ar = np.array([dmg_ser.index, dmg_ser.values]) #convert to array
        
        #invert aep (w/ zero handling)
        ar[0] = 1/np.where(ar[0]==0, #replaced based on zero value
                           sorted(ar[0])[1]/10, #dummy value for zero (take the second smallest value and divide by 10)
                           ar[0]) 
        
        dmg_ser1 = pd.Series(ar[1], index=ar[0], dtype=float) #back into series
        dmg_ser1.index = dmg_ser1.index.astype(int) #format it
        
        return ead_tot, dmg_ser1
        
    
   

    #==========================================================================
    # VALIDATORS-----------
    #==========================================================================
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

        
        #=======================================================================
        # #check expectations
        #=======================================================================
        if not 'float' in df_raw.columns.dtype.name:
            raise Error('expected aep values in columns')
        assert len(df_raw.columns)>2
        
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
        assert np.all(np.diff(df.columns) <=0), 'passed headers are not descending'
        #=======================================================================
        # #check everything is positive
        #=======================================================================
        booldf = df>=0
        if not booldf.all().all():
            raise Error('got %i (of %i) negative values'%(
                np.invert(booldf).sum().sum(), booldf.size))
        
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
            log = logger.getChild('chk_eDmg')
            log.debug('%s/n'%df.loc[cboolidx, :])
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
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('check_finv')
        if cid is None: cid = self.cid
        if finv_exp_d is None: finv_exp_d=self.finv_exp_d
        
        df = df_raw.copy()
        
        
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
                        assert np.issubdtype(ser.dtype, cval), '%s_%s bad type: %s'%(
                            nestID, coln, ser.dtype)
                        
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
        
        assert np.array_equal(df1.index, df.index)
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
                    upd_cf= True,
                    logger=None,
                    ):
        assert self.attriMode
        #=======================================================================
        # defaults
        #=======================================================================
        if ofn is None:
            ofn = 'attr%02d_%s_%s'%(self.att_df.columns.nlevels, self.name, self.tag)
        if dtag is None: dtag = self.attrdtag_out
            
        out_fp = self.output_df(self.att_df, ofn, logger=logger)
        
        #update the control file
        if upd_cf:
            self.update_cf(
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
    
    def output_etype(self,
                     df = None,
                     dtag='eventypes',
                     ofn=None,
                     upd_cf=True,
                     logger=None):
        
        
        
        #=======================================================================
        # defaults
        #=======================================================================
        if df is None: df = self.eventType_df
        if ofn is None:
            ofn = '%s_%s_%s'%(dtag, self.tag, self.name)

            
        out_fp = self.output_df(df, ofn, logger=logger, write_index=False)
        
        #update the control file
        if upd_cf:
            self.update_cf(
                    {
                    'results_fps':(
                        {dtag:out_fp}, 
                        '#\'%s\' file path set from output_etype at %s'%(
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
        dd_df.iloc[:,0:2] = dd_df.iloc[:,0:2].astype(float)
        
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
                  
                  
                  
                  #handle column names
                  add_colns = [], #additional column names to include
                   pgCn='plot_group',
                  pfCn='plot_f',
                  
                  
                  logger=None,
                  ):
        if logger is None: logger=self.logger
        log = logger.getChild('_get_smry')
        
        """
        clib_d.keys()
        """
        #=======================================================================
        # conversion
        #=======================================================================
        if clib_fmt_df:
            clib_d = {k:df.iloc[:,0].to_dict() for k,df in clib_d.items()}
        
        #=======================================================================
        # build data
        #=======================================================================
        df_raw = pd.DataFrame(clib_d).T
        
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
        sdf['dmg_mono']=pd.DataFrame(np.diff(ddf)>=0, index=sdf.index).all(axis=1)
        
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
        
        log.info('finished w/ %s'%str(sdf.shape))
        
        """
        view(sdf)
        """
        return sdf

        
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

    
    
    