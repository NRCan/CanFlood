'''
Created on Feb. 9, 2020

@author: cefect

Template for worker scripts
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, copy



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd





#==============================================================================
# Logger
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
#plugin runs
else:
    #base_class = object
    from hlpr.exceptions import QError as Error
    




#===============================================================================
# non-Qgis
#===============================================================================
from hlpr.basic import ComWrkr
from model.modcom import Model

#==============================================================================
# functions-------------------
#==============================================================================
class Cmpr(ComWrkr):
    """
    general methods to be called by the Dialog class
    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """
    
    #keys to expect on the sub co ntainers
    exp_pSubKeys = (
        'cf_fp', 
        )

    def __init__(self,

                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        

        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
        
    def rCompare(self,
                 parsG_d, #container of filepaths 
                 
                 ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('rCompare')
        
        log.info('on %i scenarios'%len(parsG_d))
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        for sName, parsN_d in parsG_d.items():
            assert isinstance(sName, str)
            assert isinstance(parsN_d, dict)
            
            #check all the keys match
            miss_l = set(self.exp_pSubKeys).difference(parsN_d.keys())
            assert len(miss_l)==0, 'bad keys: %s'%miss_l
            
            #check all the filepaths are good
            for pName, fp in parsN_d.items():
                assert os.path.exists(fp), 'bad filepath for \'%s.%s\': %s'%(
                    sName, pName, fp)
                
            log.debug('checked scenario \'%s\''%sName)
            
        #=======================================================================
        # build each scenario
        #=======================================================================
        for sName, parsN_d in parsG_d.items():
            
            sWrkr = Scenario(self, sName)
            sWrkr.load_cf(parsN_d['cf_fp'])
             
            if 'ttl_fp' in parsN_d:
                sWrkr.load_ttl(parsN_d['ttl_fp'])
        
        
        
    
class Scenario(Model): #simple class for a scenario
    
    name='ScenarioName'
    

    

    
    def __init__(self,
                 parent,
                 nameRaw,              
                 ):
        
        self.logger = parent.logger.getChild(nameRaw)
        
        """we'll set another name from the control file"""
        self.nameRaw = nameRaw 
        
        
        
        
    def load_cf(self, #load the control file
                cf_fp):
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_cf')
        assert os.path.exists(cf_fp)
        
        #=======================================================================
        # init the config parser
        #=======================================================================
        cfParsr = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%cfParsr.read(cf_fp))
        
        
        
        #=======================================================================
        # check values
        #=======================================================================
        """just for information I guess....
        self.cf_chk_pars(cfParsr, copy.copy(self.exp_pars_md), optional=False)"""
        
        #=======================================================================
        # load/attach parameters
        #=======================================================================
        self.cfPars_d = self.cf_attach_pars(cfParsr, setAttr=False)
        
        log.debug('finished w/ %i pars loaded'%len(self.cfPars_d))
        
        return
    
    def load_ttl(self, 
                 fp):
        
        log = self.logger.getChild('load_ttl')
        
        assert os.path.exists(fp)
        
        
        
        
        
        

    
    
    

    

            
        