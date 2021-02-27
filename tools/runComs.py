'''
Created on Feb. 24, 2021

@author: cefect

common methods for runner scripts
'''


import os, datetime
from qgis.core import QgsCoordinateReferenceSystem
import pandas as pd

from hlpr.logr import basic_logger
mod_logger = basic_logger() 



class Runner(object): #base worker for runner scripts
    
    
    #===========================================================================
    # #qgis attributes
    #===========================================================================
    """
    Qgis should only be init when necessary
        each tool handler should check to see if q has been initilized
        try and take init pars from the handler
        otherwise, build and pass to the handler
    """
    qinit = False
    qhandl_d = {'qproj':None, 'crs':None, 'qap':None, 'algo_init':None, 'vlay_drivers':None}

    #===========================================================================
    # #CanFlood attributes   
    #===========================================================================
    com_hndls = ('absolute_fp', 'figsize', 'overwrite', 'attriMode', 'projName', 'scenarioName')
    absolute_fp = True
    figsize = (14,8)
    overwrite=True
    attriMode=False
    
    #===========================================================================
    # program vars
    #===========================================================================
    
    proj_dir = None #useful to add here for wrappers
    
    
    qinit = False #flag whether qgis has been initiated or not yet
    
    smry_d = None #default risk model results summary parameters 
        #{coln: dataFrame method to summarize with}

    def __init__(self,
             #project tool parameters
             pars_d, # parameters for this scenario (all tools and assetModels) {parameter: value}. 
                #each tool run has expectations
                #run_build() needs a second dict for unique assetModel pars
             
             #run controls

             plot = True, #whether to execute plot tools
             write_vlay = True, #whether to write vlays to file
             
             
             #file pahts
             proj_dir = None, #optional direcotry for saving results for this project
             out_dir = None, #optoinal output directory overwrite (default is to build from tags)
             
             #tags and names
             projName='project',
             scenarioName = 'baseline', #scenario run
             runTag = None, #optional secondary tag for batch runs (nice for testing/building models)

             
             #project properties
             crs_id='EPSG:4326', #project coordinate system
             
             #program objects
             logger=mod_logger,
             
             **kwargs #for standard attributes
             ):
        

        

        assert isinstance(pars_d, dict)
        #=======================================================================
        # #attachments
        #=======================================================================
        self.pars_d = pars_d
        self.crs_id=crs_id
        self.projName=projName
        self.runTag=runTag
        self.logger=logger
        self.plot=plot
        self.today_str = datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')
        self.write_vlay=write_vlay
        self.scenarioName=scenarioName
        
        for k,v in kwargs.items():
            setattr(self, k, v)
        
        #=======================================================================
        # #output directory setupo
        #=======================================================================
        if out_dir is None: 
            if proj_dir is None: 
                proj_dir = os.getcwd()
            
            out_dir = os.path.join(proj_dir, scenarioName)
            
            if not runTag is None:
                out_dir = os.path.join(out_dir, runTag)
            
        if not os.path.exists(out_dir):os.makedirs(out_dir)
        self.out_dir = out_dir
        
        self.logger.info('set output directory: %s'%out_dir)
        
        #=======================================================================
        # wrap
        #=======================================================================
        self.logger.debug('Runner __init__ finished')
        
    
    #===========================================================================
    # CHILD HANDLING--------
    #===========================================================================
    def _init_child_q(self,  #handle the q setup on a child
                      child): 
        
        #pass onto child
        if self.qinit:
            assert not self.toolName=='Build', 'should never init_q for a build tool'
            
            for k,v in self.qhandl_d.items():
                setattr(child, k, v)
                
        #build and get from child
        else:
            child.ini_standalone(crs = QgsCoordinateReferenceSystem(self.crs_id))
            
            #collect for the next child
            for k in self.qhandl_d.keys():
                self.qhandl_d[k] = getattr(child, k)
            
            self.qinit=True
            
        #=======================================================================
        # check
        #=======================================================================
        assert child.crs.authid()==self.crs_id
        assert child.qproj.crs().authid()==self.crs_id
            
        return child

    def _init_child_pars(self, #pass attributes onto a child tool worker
                         child):
        
        for attn in self.com_hndls:
            assert hasattr(self, attn)
            setattr(child, attn, getattr(self, attn))
            
        return child

    
    #===========================================================================
    # RUNNERS-------
    #===========================================================================
    def run_all(self, #run all tool sets against all assetModels
            toolNames = None, #sequence of toolNames to execute

            logger=None,
            tool_kwargs = {}, #oprtional kwargs to pass onto each tool

                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================

        if logger is None: logger=self.logger
        log = logger.getChild('all')
    
        if toolNames is None:
            toolNames = self.hndl_lib.keys()
        #=======================================================================
        # loop and run each toolbox
        #=======================================================================
        log.info('running %i toolboxes'%len(self.hndl_lib))
        pars_df = None #ignored by build
        meta_d = dict()
        for toolName in toolNames:
            try:
                #get kwargs
                if toolName in tool_kwargs:
                    kwargs = tool_kwargs[toolName]
                else:
                    kwargs={}
                
                tool_od, pars_df = self.run_toolbox(toolName, 
                                            control_df=pars_df, writePars=False, logger = log,
                                            **kwargs)
                
                meta_d[toolName] = '    finished on %i w/ %s'%(len(self.meta_d), self.meta_d)
            except Exception as e:
                msg = 'failed on \'%s\' w/ \n    %s'%(toolName, e)
                meta_d[toolName] = 'FAIL=%s'%e
                log.error(msg)

        #=======================================================================
        # write the run summary
        #=======================================================================
        if not pars_df is None:
            self.write_pars(df=pars_df)
            
        self.write_parsd()
        
        #=======================================================================
        # wrap
        #=======================================================================
        for toolName, msg in meta_d.items():
            log.info('%s:    %s'%(toolName, msg))
        
        return self.out_dir, pars_df
        
    def _get_smry(self,  #retrieve some extra summary info from teh data
                  df, smry_d=None,
                  expect_all=False,#whether to expect all columns to hit
                  ):
        if smry_d is None: smry_d = self.smry_d
        
        if not smry_d is None:
            """allowing request to pass for columns not there"""
            
            if expect_all:
                #get summaries from handles
                miss_l = set(smry_d.keys()).difference(df.columns)
                assert len(miss_l)==0, 'missing summary columns on results:%s'%miss_l
             
            d = dict()
            for coln, smry_str in smry_d.items():
                if not coln in df.columns:
                    continue
                f = getattr(df[coln], smry_str) 
                
                d['%s_%s'%(coln, smry_str)] = f()
            return d
        else:
            return dict()
    #===========================================================================
    # OUTPUTTERs----------
    #===========================================================================
    def write_parsd(self, #write the raw parameter dictionary
                    d = None,
                    ofp=None,
                    ):
        
        if d is None: d = self.pars_d
        #=======================================================================
        # filepaths
        #=======================================================================
        ofn = 'cf_batchPars_%s_%s'%(self.projName, self.scenarioName)
        if self.runTag is None:
            ofn = ofn+'.csv'
        else:
            ofn = ofn+'%s.csv'%self.runTag
            
        if ofp is None: 
            ofp = os.path.join(self.out_dir, ofn)
                                           
                                           
        try:
            pd.Series(d, name='pval').to_csv(ofp, index=True)
            print('wrote pars_d %i to file: %s'%(len(d), ofp))
        except Exception as e:
            self.logger.error('failed to write %s  w/ \n    %s'%(ofn, e))
            
        return ofp
        
        
        
        
        
        
        
        
        
        
        