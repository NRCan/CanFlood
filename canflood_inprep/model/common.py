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

import configparser, os, inspect
import pandas as pd
import numpy as np

#==============================================================================
# custom
#==============================================================================
#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
    
#plugin runs
else:

    from hlpr.exceptions import QError as Error
    
from hlpr.basic import *

#==============================================================================
# class-----------
#==============================================================================
class Model(object):
    
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
    ead_plot = True
    res_per_asset = True

    
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
    imp2 = False
    risk2 = False
    risk3 = False
    
    
    #==========================================================================
    # data containers
    #==========================================================================
    data_d = dict() #dictionary for loaded data sets
    
    #==========================================================================
    # program vars
    #==========================================================================
    par_fp = ''
    out_dir = ''
    overwrite=True, #whether to overwrite output files (if they exist) or raise an error

    
    
    def __init__(self, #console runs
                 par_fp, out_dir, logger=mod_logger):
        
        #attachments
        self.wd = out_dir
        self.out_dir = out_dir
        self.logger = logger.getChild('Model')
        
        #parameter setup
        self.setup_pars2(par_fp)
        
        
        #check our validity tag
        if not getattr(self, self.valid_par):
            raise Error('control file not validated for \'%s\'. please run InputValidator'%self.valid_par)
        
        #wrap

        self.logger.debug('finished __init__ on Model')
        
        
    def xxxinit_model(self, #plugin runs
                   par_fp, out_dir):

        #attachments
        self.wd = out_dir
        
        #parameter setup
        self.setup_pars(par_fp)
        
        self.logger.debug('finished __init__ on Model')
        
        
    def setup_pars2(self, #load parmaeteres from file, check, and attach
                    par_fp):
        
        log = self.logger.getChild('setup_pars')
        
        assert os.path.exists(par_fp), 'provided parameter file path does not exist \n    %s'%par_fp
        
        #======================================================================
        # validate the control file for this run
        #======================================================================
        #load/build
        self.pars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%self.pars.read(par_fp))
        
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
                assert isinstance(achk_d, dict), '%s.%s bad type'%(sect, varnm)
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
                log.debug('%s.%s passed %i checks'%(sect, varnm, len(achk_d)))
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
                assert isinstance(achk_d, dict), '%s.%s bad type'%(sect, varnm)
                assert hasattr(self, varnm), '\'%s\' does not exist on %s'%(varnm, self)
                
                
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
        
        assert not pval is None, '%s.%s got none'%(sect, varnm)
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
                assert isinstance(hvals, tuple)
                assert pval in hvals, '%s.%s unexpected value: %s'%(sect, varnm, type(pval))
            
            elif chk_hndl == 'ext':
                assert isinstance(pval, str), '%s.%s expected a filepath '%(sect, varnm)
                assert os.path.exists(pval), '%s.%s passed bad filepath: %s'%(sect, varnm, pval)
                
                ext = os.path.splitext(os.path.split(pval)[1])[1]

                
                if isinstance(hvals, tuple):
                    assert ext in hvals, '%s.%s  unrecognized extension: %s'%( sect, varnm, ext)
                elif isinstance(hvals, str):
                    assert ext == hvals, '%s.%s  unrecognized extension: %s'%( sect, varnm, ext)
                else:
                    raise Error('%s.%s bad hvals'%sect, varnm)
                    
            
            else:
                raise Error('unrecognized check handle: %s'%chk_hndl)
                        
        return
            
            
        
        

    
    def setup_pars(self, #load parameters from file
                       par_fp):
        
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
        
        assert os.path.exists(par_fp), 'provided parameter file path does not exist \n    %s'%par_fp
        
        #======================================================================
        # load and build
        #======================================================================
        self.pars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%self.pars.read(par_fp))

        
        
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
        
        #check if we have duplicate events and require exposure likelihoods
        if not aep_ser.is_unique:
            assert 'exlikes' in self.data_d, 'duplicate aeps passed but no exlikes data provdied'
            
            log.info('duplicated aeps provided... maximum expected values will be calculated')

        
        
        #wrap
        log.debug('prepared aep_ser w/ %i'%len(aep_ser))
        self.aep_ser = aep_ser.sort_values()
        
        
        
        #======================================================================
        # exlikes
        #======================================================================
        #check against ddf
        if not self.exlikes == '':
            edf = pd.read_csv(self.exlikes)
            
            assert cid in edf.columns, 'exlikes missing %s'%cid
            
            #slice it
            edf = edf.set_index(cid).sort_index(axis=1).sort_index(axis=0)
            
            #replace nulls w/ 1
            """better not to pass any nulls.. but if so.. should treat them as 1
            also best not to apply precision to these values
            """
            edf = edf.fillna(1.0)
            
            
            
            
            #column names
            miss_l = set(ddf.columns).difference(edf.columns)
            assert len(miss_l) == 0, '%i column mismatch between exlikes and damages: %s'%(
                len(miss_l), miss_l)
            
            #xids
            miss_l = set(ddf.index).difference(edf.index)
            assert len(miss_l) == 0, '%i column mismatch between exlikes and damages: %s'%(
                len(miss_l), miss_l)
            
            #slice down to those in teh damages
            """not sure if we'll ever have to deal w/ more data in the edf than in the damages"""
            edf = edf.loc[edf.index.isin(ddf.index), edf.columns.isin(ddf.columns)]
        
            log.info('prepared edf w/ %s'%str(edf.shape))
            
            #set it
            self.data_d['exlikes'] = edf
        

        #======================================================================
        # wrap
        #======================================================================
        self.logger.debug('finished')
        
        
        
    def output(self, #dump some outputs
                      df, 
                      out_fn,
                      out_dir = None,
                      overwrite=None,
            ):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.wd
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
        
        return out_fp

      