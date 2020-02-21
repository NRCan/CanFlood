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
    name = 'damage model'
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

    
    
    def __init__(self, par_fp, out_dir, logger=mod_logger):
        
        #attachments
        self.out_dir = out_dir
        self.logger = logger.getChild('Model')
        
        #parameter setup
        self.setup_pars(par_fp)
        
        #wrap
        assert self.validated, 'please run Input Validator tool prior to this model'
        self.logger.debug('finished __init__ on Model')
        return
    
    
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
        
        read_file = self.pars.read(par_fp)
        log.info('reading parameters from \n     %s'%read_file)
        

        
        
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
        # special checks
        #======================================================================
        assert self.felv in ['datum', 'ground'], \
            'got unexpected felv value \'%s\''%self.felv
            
        #remove the dtm if the inventory is already absolute
        if self.felv == 'datum':
            del self.exp_dprops['gels']
                  
        #======================================================================
        # load data files        
        #======================================================================
        for varnm, fp in self.pars[self.datafp_section].items():
            """no... lets load everything
            #skip those not found (incase we've removed the gels)
            if not varnm in self.exp_dprops:
                continue """
            
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
                data = pd.read_excel(fp, sheet_name=None)

                
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
        
        return out_fp

      