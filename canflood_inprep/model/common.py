'''
Created on Feb. 9, 2020

@author: cefect
'''
#==============================================================================
# logger----------
#==============================================================================
import logging
mod_logger = logging.getLogger('hp') #creates a child logger of the root

#==============================================================================
# imports------------
#==============================================================================

import configparser, os
import pandas as pd
import numpy as np

from hp import Error



class Model(object):
    
    #==========================================================================
    # parameters from user
    #==========================================================================
    validated = False
    name = 'run1'
    cid = 'xid' #indexer
    prec = 2 #precision
    
    
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
        self.logger = logger.getChild('Model')
        
        #parameter setup
        self.setup_pars(par_fp)
        
        
        #check our validity tag
        if not getattr(self, self.valid_par):
            raise Error('control file not validated for \'%s\'. please run InputValidator'%self.valid_par)
        
        #wrap

        self.logger.debug('finished __init__ on Model')
        
        
    def init_model(self, #plugin runs
                   par_fp, out_dir):
        
        #attachments
        self.wd = out_dir
        
        #parameter setup
        self.setup_pars(par_fp)
        

        
        self.logger.debug('finished __init__ on Model')

    
    def setup_pars(self, #load parameters from file
                       par_fp):
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

      