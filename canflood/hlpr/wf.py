'''
Created on Nov. 18, 2021

@author: cefect

WorkFlow scripts common to tools and sensivity analysis
'''

#===============================================================================
# imports
#===============================================================================
import inspect, logging, os,  datetime, shutil, gc, weakref
from hlpr.basic import ComWrkr, view, Error

class Session(ComWrkr):
    """
    simplified version of wFlow.scripts.Session
    """
    def _run_wflow(self, #execute a single workflow 
                   WorkFlow, #workflow object to run
                   **kwargs):
        
        log = self.logger.getChild('r.%s'%WorkFlow.name)
        log.debug('on %s w/ %s'%(WorkFlow.__name__, WorkFlow.crsid))
        #=======================================================================
        # update crs
        #=======================================================================
        if not WorkFlow.crsid == self.crsid:
            log.debug('crsid mismatch... switching to crs of workflow')
            self.set_crs(WorkFlow.crsid, logger=log)

        #===================================================================
        # # init the flow 
        #===================================================================
        
        #collect pars
        """similar to _get_wrkr().. but less flexible"""
        for k in list(self.com_hndls) + self.flow_hndls:
            kwargs[k] = getattr(self, k)

        #init
        kstr = ''.join(['\n    %s: %s'%(k,v) for k,v in kwargs.items()]) #plot string
        log.debug('building w/ %s'%kstr)
        runr = WorkFlow(logger=self.logger, session=self,**kwargs)

        #===================================================================
        # execute the flow
        #===================================================================
        log.debug('running \n\n')
        runr.run()
        
        log.debug('finished')
        return runr
        

    
    #==========================================================================
    # RUNNERS----------
    #==========================================================================

    def run(self, #run a set of WorkFlows
            wFlow_l, #set of workflows to run
            **kwargs
            ):
        """
        lets the user define their own methods for batching together workflows
        
        """
        log=self.logger.getChild('r')
        log.info('running %i flows: \n    %s'%(len(wFlow_l), wFlow_l))
 
 
        rlib = dict()
        for fWrkr in wFlow_l:
            runr = self._run_wflow(fWrkr, **kwargs)
            
            rlib[runr.name] = runr.res_d.copy()
            
            runr.__exit__()
            
        log.info('finished on %i: \n    %s'%(len(rlib), list(rlib.keys())))
        return rlib
    
    
    
    
    
    
class WorkFlow(Session): #worker with methods to build a CF workflow from
    """
    #===========================================================================
    # INSTRUCTIONS
    #===========================================================================
    sub-class this method for each CanFLood 'workflow' you wish to execute
        set a 'pars_d' attribute with all the parameters and filepaths
        and a 'name' attribute for the name of the flow
        
    add a 'run' method calling all the functions desired by the workflow
        this can use the 'tools' and 'toolbox' methods found in this baseclass
        
    
    """
    
    #===========================================================================
    # required attributes
    #===========================================================================
    name = None
    pars_d = None #parameters for control file
    tpars_d = dict() #parameters for passing to tools
    

    
    def __init__(self,
                 session=None,

                 #init_q_d = {},
                 **kwargs):
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(self.name, str), 'must overwrite the \'name\' attribute with a subclass'

        #=======================================================================
        # init cascade
        #=======================================================================

        super().__init__(out_dir=os.path.join(session.out_dir, self.name),
                         tag = '%s'%datetime.datetime.now().strftime('%Y%m%d'),
                         crsid=self.crsid, #overrwrite the default with your default
                         **kwargs) #Session -> Qcoms -> ComWrkr

        #=======================================================================
        # attachments
        #=======================================================================
        self.session = session

        self.cf_tmpl_fp = os.path.join(self.session.cf_dir, r'canflood\_pars\CanFlood_control_01.txt')
        assert os.path.exists(self.cf_tmpl_fp), self.cf_tmpl_fp
        
        
        self.com_hndls = list(session.com_hndls) +[
            'out_dir', 'name', 'tag', 'cid']
        
        self.data_d = dict() #empty container for data
        
        self.wrkr_d = dict() #container for loaded workers
        
        #=======================================================================
        # checks
        #=======================================================================
        assert isinstance(self.pars_d, dict)
        
        
    def run(self, **kwargs):
        raise Error('overwrite with your own run method!')
    
    
    def __exit__(self, #destructor
                 *args,**kwargs):
        """
        call this before moving onto the next workflow
        """
        #clear your own
        self.mstore.removeAllMapLayers()
        
        #clear your children
        for cn, wrkr in self.wrkr_d.items():
            wrkr.__exit__(*args,**kwargs)
            
        #del self.wrkr_d
        
        #remove data objects
        del self.data_d
        
        super().__exit__(*args,**kwargs) #initilzie teh baseclass
        gc.collect()