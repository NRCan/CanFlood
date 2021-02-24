'''
Created on Feb. 24, 2021

@author: cefect

common methods for runner scripts
'''


import os, datetime
from qgis.core import QgsCoordinateReferenceSystem, QgsRasterLayer


from hlpr.logr import basic_logger
mod_logger = basic_logger() 



class Runner(object): #base worker for runner scripts
    
    proj_dir = None #useful to add here for wrappers
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
    com_hndls = ('absolute_fp', 'figsize', 'overwrite', 'attriMode')
    absolute_fp = True
    figsize = (14,8)
    overwrite=True
    attriMode=False

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
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        