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


    
    #[dmg_fps]
    curves = ''
    finv = ''
    expos = ''
    gels = ''
    
    #[risk_fps]
    dmgs = ''
    exlikes = ''
    aeps = ''

    
    #[validation]
    risk1 = True
    dmg2 = False
    risk2 = False
    risk3 = False
    
    #==========================================================================
    # program vars
    #==========================================================================
    bid = 'bid' #indexer for expanded finv
    

    
    
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
        


        self.logger.debug('finished __init__ on Model')
        
        
    def init_model(self, #plugin runs
                   ):

        
        
        #parameter setup
        self.setup_pars2(self.cf_fp)
        
        
        #check our validity tag
        if not getattr(self, self.valid_par):
            raise Error('control file not validated for \'%s\'. please run InputValidator'%self.valid_par)
        
        #wrap
        self.logger.debug('finished init_modelon Model')
        
        
        
    def setup_pars2(self, #load parmaeteres from file, check, and attach
                    cf_fp):
        
        log = self.logger.getChild('setup_pars')
        
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
                assert os.path.exists(pval), '%s.%s passed bad filepath: \'%s\''%(sect, varnm, pval)
                
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
            
            
        
        

    
    def xxxsetup_pars(self, #load parameters from file
                       cf_fp):
        
        """
        TODO: fix so:
        1) calculate the necessary parameters for this run
        2) pull those parameters from the control file
        3) load the data from the parameters
        4) check the data against expectations
        """
        #======================================================================
        # prechecks and setup
        #======================================================================

        log = self.logger.getChild('setup_pars')
        
        assert os.path.exists(cf_fp), 'provided parameter file path does not exist \n    %s'%cf_fp
        
        #======================================================================
        # load and build
        #======================================================================
        self.pars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%self.pars.read(cf_fp))

        
        
        #======================================================================
        # post checks
        #======================================================================       
        #check variables
        for section, vars_l in self.exp_pars.items():
            assert section in self.pars.sections(), 'missing expected section %s'%section
            
            for varnm in vars_l:
                assert varnm in self.pars[section], 'missing expected variable \'%s.%s\''%(section, varnm)
                

            
        #======================================================================
        # attach all parmaetrs to class
        #======================================================================
        for varnm, val in self.pars['parameters'].items():
            if not hasattr(self, varnm):
                log.warning('no parameter \'%s\' found.. skipping'%varnm)
                continue

            
            #get the type
            set_type = type(getattr(self, varnm))
            
            #special type retrivial
            if set_type == bool:
                nval = self.pars['parameters'].getboolean(varnm)
            else:
                #set the type
                nval = set_type(val)

            #attach
            setattr(self, varnm, nval)
            log.debug('set \'%s\' type %s as \'%s\''%(varnm, set_type.__name__, nval))
            
        log.debug('attached %i variables to self: \n    %s'%(
            len(self.pars['parameters']), self.pars['parameters']))
        
        
        #======================================================================
        # attach validity flags
        #======================================================================
        for varnm, val in self.pars['validation'].items():
            setattr(self, varnm, self.pars['validation'].getboolean(varnm))
            
        #======================================================================
        # special checks
        #======================================================================
        assert self.felv in ['datum', 'ground'], \
            'got unexpected felv value \'%s\''%self.felv
            
        #remove the dtm if the inventory is already absolute
        if self.felv == 'datum':
            try:
                del self.exp_dprops['gels']
            except:
                pass
                  
        #======================================================================
        # load data files        
        #======================================================================
        for varnm, fp in self.pars[self.datafp_section].items():
            
            
            if fp is None or fp == '':
                if varnm in self.opt_dfiles:
                    log.warning('%s.%s is optional and not provided... skipping'%(
                        self.datafp_section, varnm))
                    continue
                else:
                    raise Error('no filepath specfied for \'%s\''%varnm)
                 
                
            #==================================================================
            # if not varnm in self.exp_dprops: #set it as a dummy
            #     self.exp_dprops[varnm] = ''
            #     
            # #check if there
            # if self.exp_dprops[varnm] == '':
            #     if varnm in self.opt_dfiles:
            #         log.warning('%s.%s is optional and not provided... skipping'%(
            #             self.datafp_section, varnm))
            #         continue
            #     else:
            #         raise Error('missing required \'%s\''%varnm)
            #==================================================================
            


            #pull parameters
            dprops = self.exp_dprops[varnm]
            

            
            fh_clean, ext = os.path.splitext(os.path.split(fp)[1])

            #==================================================================
            # prechecks
            #==================================================================
            #check existance
            assert os.path.exists(fp), 'passed \'%s\' filepath does not exist: \n    %s'%(varnm, fp)
            
            #check extension
            assert ext == self.exp_dprops[varnm]['ext'], 'unexpected filepath for %s'%varnm
            
            #==================================================================
            # #load to frame
            #==================================================================
            if ext == '.csv':
                #load the data
                data = pd.read_csv(fp, header=0, index_col=None)
                
                #check the column names
                miss_l = set(dprops['colns']).difference(data.columns)
                assert len(miss_l)==0, '\'%s\' is missing %i expected column names: %s'%(
                    varnm, len(miss_l), miss_l)
                
            #==================================================================
            # #load spreadsheet
            #==================================================================
            elif ext == '.xls':
                data = pd.read_excel(fp, sheet_name=None, header=None, index_col=None)
                
                """
                import pandas as pd
                fp = r'C:\LS\03_TOOLS\CanFlood\_ins\prep\cT2\CanFlood_curves_rfda_20200218.xls'
                pd.read_excel(fp, sheet
                
                data.keys()
                
                data['AA_MC']
                
                """
                log.info('loadedd %i sheets from xls:\n    %s'%(len(data), list(data.keys())))

                if not isinstance(data, dict):
                    raise Error('unexpected type')
                
            else:
                raise Error('unepxected extnesion \"%s\''%ext)
                
            #add
            
            self.data_d[varnm] = data
            
            log.info('loaded \'%s\' w/ %i from \'%s\''%(
                    varnm, len(data), fh_clean))
        
        
        log.debug('finished loading and checking parameter file')
        
    def load_risk_data(self, 
                       ddf, #dmaage or exposure data to compare against
                       ): #data setups and checks
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('setup_data')
        cid = self.cid
        
        

        
        #======================================================================
        # aeps
        #======================================================================
        adf = pd.read_csv(self.aeps) 
        assert len(adf) ==1, 'expected only 1 row on aeps'
        
        #column names
        miss_l = set(ddf.columns).difference(adf.columns)
        assert len(miss_l) == 0, '%i column mismatch between aeps and damages: %s'%(
            len(miss_l), miss_l)
        
        #convert to a series
        aep_ser = adf.iloc[0, adf.columns.isin(ddf.columns)].astype(int).sort_values()
        
        #convert to aep
        if self.event_probs == 'ari':
            aep_ser = 1/aep_ser
            log.info('converted %i aris to aeps'%len(aep_ser))
        elif self.event_probs == 'aep': pass
        else: raise Error('unepxected event_probs key %s'%self.event_probs)
        
        #check all aeps are below 1
        boolar = np.logical_and(
            aep_ser < 1,
            aep_ser > 0)
        
        assert np.all(boolar), 'passed aeps out of range'
        
        #wrap
        log.debug('prepared aep_ser w/ %i'%len(aep_ser))
        #self.aep_ser = aep_ser.sort_values()
        self.data_d['aeps'] = aep_ser.sort_values().copy() #setting for consistency. 
        
        
        
        #======================================================================
        # exlikes
        #======================================================================
        #check against ddf
        if not self.exlikes == '':
            edf = pd.read_csv(self.exlikes)
            
            assert cid in edf.columns, 'exlikes missing %s'%cid
            
            #==================================================================
            # clean
            #==================================================================
            #slice it
            edf = edf.set_index(cid).sort_index(axis=1).sort_index(axis=0)
            
            #replace nulls w/ 1
            """better not to pass any nulls.. but if so.. should treat them as ZERO!!
            Null = no failure polygon = no failure
            also best not to apply precision to these values
            """
            edf = edf.fillna(0.0)
            
            #==================================================================
            # check
            #==================================================================
            #check event name membership
            miss_l = set(edf.columns).difference(ddf.columns)
            if len(miss_l) >0:
                raise Error('passed exlikes columns dont match ddf: %s'%miss_l)
            
            #check logic against aeps
            """todo: add this to the validator tool somehow"""
            if len(aep_ser.unique()) == len(aep_ser):
                raise Error('passed exlikes, but there are no duplicated event: \n    %s'%aep_ser)
            
            #check monotoncity
            if not self.check_monot(edf, aep_ser=aep_ser,event_probs='aep'):
                raise Error('exlikes data non-monotonic')
            
            #==================================================================
            # #add missing likelihoods
            #==================================================================
            """
            missing column = no secondary likelihoods at all for this event.
            all = 1
            """
            
            miss_l = set(ddf.columns).difference(edf.columns)
            if len(miss_l) > 0:
                
                log.info('passed exlikes missing %i secondary exposure likelihoods... treating these as 1\n    %s'%(
                    len(miss_l), miss_l))
                
                for coln in miss_l:
                    edf[coln] = 1.0
                
                #column names
                miss_l = set(ddf.columns).difference(edf.columns)
                assert len(miss_l) == 0, '%i column mismatch between exlikes and ddf: %s'%(
                    len(miss_l), miss_l)
            
            #xids
            miss_l = set(ddf.index).difference(edf.index)
            assert len(miss_l) == 0, '%i column mismatch between exlikes and damages: %s'%(
                len(miss_l), miss_l)
            
            #slice down to those in teh damages
            """not sure if we'll ever have to deal w/ more data in the edf than in the damages"""
            edf = edf.loc[edf.index.isin(ddf.index), edf.columns.isin(ddf.columns)]
        
            log.info('prepared edf w/ %s'%str(edf.shape))
            
            #==================================================================
            # check it
            #==================================================================

            
            #set it
            self.data_d['exlikes'] = edf
        
        #======================================================================
        # post checks
        #======================================================================
        #check if we have duplicate events and require exposure likelihoods
        if not aep_ser.is_unique:
            assert 'exlikes' in self.data_d, 'duplicate aeps passed but no exlikes data provdied'
            
            log.info('duplicated aeps provided... maximum expected values will be calculated')


        #======================================================================
        # wrap
        #======================================================================
        self.logger.debug('finished')
        
    def setup_finv(self): #check and consolidate inventory like data sets
        
        log = self.logger.getChild('setup_finv')
        cid = self.cid
        fdf = self.data_d['finv']
        #======================================================================
        # check ftag membership
        #======================================================================
        if hasattr(self, 'dfunc_d'):
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
            assert cid in df.columns, '%s is missing the special index column \'%s\''%(
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
            
            
            gdf = self.data_d['gels']
    
            #==================================================================
            # checks
            #==================================================================
            #check length expectation
            assert 'gels' not in fdf.columns, 'gels already on fdf'
            assert len(gdf.columns)==1, 'expected 1 column on gels, got %i'%len(gdf.columns)
            boolidx = gdf.iloc[:,0].isna()
            if boolidx.any():
                raise Error('got %i (of %i) null ground elevation values'%(boolidx.sum(), len(boolidx)))
            
            boolidx = gdf.iloc[:,0] < 0
            if boolidx.any():
                log.warning('got %i ground elevations below zero'%boolidx.sum())
    
            
            #rename the column
            gdf = gdf.rename(columns={gdf.columns[0]:'gels'}).round(self.prec)
            
            #do the join join
            fdf = fdf.join(gdf)
            

        
        #update
        self.data_d['finv'] = fdf
        

        
    def setup_expo_data(self):# expand finv to  unitary (one curve per row)
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('setup_binv')
        fdf = self.data_d['finv']
        cid, bid = self.cid, self.bid
        
        assert fdf.index.name == cid, 'bad index on fdf'
        
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
            
            log.info('expanded inventory from %i nest sets %s to finv %s'%(
                len(prefix_l), str(fdf.shape), str(bdf.shape)))
        #======================================================================
        # expand: nothing nested
        #======================================================================
        else:
            bdf = fdf.copy()
            
        #set an indexer columns
        """safer to keep this index as a column also"""
        bdf[bid] = bdf.index
        bdf.index.name=bid
        
        assert cid in bdf.columns, 'bdf missing %s'%cid
            
        #======================================================================
        # convert asset heights to elevations
        #======================================================================
        if self.felv == 'ground':
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
        # check monotocity
        #======================================================================
        
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
        
    def resolve_multis(self,
                       ddf, edf, aep_ser,
                       logger):
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
        
        log.info('calucated expected values for %i damages'%evdf.size)
        
        

        assert not evdf.isna().any().any()
        #======================================================================
        # loop by unique aep and resolve
        #======================================================================
        res_df = pd.DataFrame(index=evdf.index, columns = aep_ser.unique().tolist())
        for aep in aep_ser.unique().tolist():
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
                     #split_key = None, #optional key to split hazard columns by
                     aep_ser=None, event_probs = 'ari', #optional kwargs for column conversion
                     logger=None
                     ):
        """
        if damages are equal the warning will be thrown
        """
        
        
        #======================================================================
        # defaults
        #======================================================================
        
        if logger is None: logger=self.logger
        split_key = self.split_key
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
        if not split_key is None:
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
        # setup left tail
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
        # setup right tail
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
            raise Error('not tested')
            
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
        
        title = 'CanFlood \'%s\' Annualized-%s plot on %i events'%(self.name,xlab, len(dmg_ser))
        
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
        

        
    def output_df(self, #dump some outputs
                      df, 
                      out_fn,
                      out_dir = None,
                      overwrite=None,
            ):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.out_dir
        if overwrite is None: overwrite = self.overwrite
        log = self.logger.getChild('output')
        
        assert isinstance(out_dir, str), 'unexpected type on out_dir: %s'%type(out_dir)
        assert os.path.exists(out_dir), 'requested output directory doesnot exist: \n    %s'%out_dir
        
        
        #extension check
        if not out_fn.endswith('.csv'):
            out_fn = out_fn+'.csv'
        
        #output file path
        out_fp = os.path.join(out_dir, out_fn)
        
        #======================================================================
        # checeks
        #======================================================================
        if os.path.exists(out_fp):
            log.warning('file exists \n    %s'%out_fp)
            if not overwrite:
                raise Error('file already exists')
            

        #======================================================================
        # writ eit
        #======================================================================
        df.to_csv(out_fp, index=True)
        
        log.info('wrote to %s to file: \n    %s'%(str(df.shape), out_fp))
        
        self.out_fp = out_fp #set for some other methods
        
        return out_fp

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
    
    
    
    
    
    
    
    
    
    