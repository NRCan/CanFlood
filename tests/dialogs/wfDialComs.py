'''
Created on Nov. 27, 2021

@author: cefect

commons for dialog workflow
'''

#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging, datetime, time, sys, traceback, unittest, copy
from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject
from PyQt5.QtWidgets import QApplication, QMainWindow 


from wFlow.scripts import WorkFlow, Session

from hlpr.exceptions import Error

from hlpr.plug import plugLogger


from unittest import TestLoader


#===============================================================================
# #add a special hook tot he exception
#===============================================================================
def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("error message:\n", tb)
    QApplication.quit()




#===============================================================================
# logger
#===============================================================================
from hlpr.plug import plugLogger
from hlpr.logr import basic_logger
mod_logger = basic_logger()

class devPlugLogger(plugLogger):
    """wrapper to overwriting Qspecific methods with python logging"""
    
    def getChild(self, new_childnm):
        
 
        log_nm = '%s.%s'%(self.log_nm, new_childnm)
        
        #build a new logger
        child_log = devPlugLogger(self.parent,log_nm=log_nm)
        

        
        return child_log
        
          
    
    def _loghlp(self, #helper function for generalized logging
                msg_raw, qlevel, 
                push=False, #treat as a push message on Qgis' bar
                status=False, #whether to send to the status widget
                ):
        
        #=======================================================================
        # send message based on qlevel
        #=======================================================================
        msgDebug = '%s    %s: %s'%(datetime.datetime.now().strftime('%d-%H.%M.%S'), self.log_nm,  msg_raw)
        if qlevel < 0: #file logger only
            
            mod_logger.debug('D_%s'%msgDebug)
            push, status = False, False #should never trip
        else:#console logger
            msg = '%s:   %s'%(self.log_nm, msg_raw)
            mod_logger.info(msg)
 
        
        #Qgis bar
        if push:
            print('PUSH: ' +msg_raw)



        
        
class WF_handler(object): #common functions for handling workflows
    """because sometimes the session handles workflows
    and sometimes other workflows need to handle workflows"""
    
    def run_suite(self,
                  workflow_l=None,
                  build_pickels = False,
                  get_tests=False,
                  **kwargs):
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('run_suite')
        if workflow_l is None: workflow_l=self.workflow_l
        
        #=======================================================================
        # user check
        #=======================================================================
        if build_pickels:
            assert input('\n    rebuild pickels on %i workflows? (y/n)'%len(workflow_l))=='y'
        

        
        #=======================================================================
        # loop and execute each workflow
        #=======================================================================
        first = True
        for WorkFlow in workflow_l:
            
            #===================================================================
            # crs
            #===================================================================
            if not WorkFlow.crsid == self.crsid:
                log.debug('crsid mismatch... switching to crs of workflow')
                self.set_crs(WorkFlow.crsid, logger=log)
                
                
            #=======================================================================
            # #collect pars
            #=======================================================================
            """similar to _get_wrkr().. but less flexible"""
            for k in list(self.com_hndls) + self.flow_hndls:
                kwargs[k] = getattr(self, k)
    
            #init
            kstr = ''.join(['\n    %s: %s'%(k,v) for k,v in kwargs.items()]) #plot string
            log.debug('building w/ %s'%kstr)
            
            
            #===================================================================
            # launch the flow
            #===================================================================
            
 
            with WorkFlow(logger=self.logger, session=self, **kwargs) as wflow:
                
                #run the children
                if hasattr(wflow, 'run_suite'):
                    """our parameter handling isn't very good
                     telling the parent to include its own pars_d during children inits"""

                    wflow.run_suite(build_pickels=False, get_tests=False, pars_d = copy.deepcopy(wflow.pars_d))
                    
                #no children. run the object
                else:
                
                    wflow.pre()
                    
                    wflow.D.launch()
                    
                    wflow.post()
                
                #test extraction
                if build_pickels:
                    if first:
                        pick_d = dict()
                    pick_d[wflow.name] = wflow.write_pick()
                    
                if get_tests:
                    wflow.load_pick()
                    if first:
                        suite = unittest.TestSuite() #start the suite container
                        
                    for tMethodName in TestLoader().getTestCaseNames(wflow.Test):
                        """inits TestU only 1 test method per TeestU for now"""
                        suite.addTest(wflow.Test(tMethodName, runr=wflow))
                    
            #===================================================================
            # wrap this workerse loop    
            #===================================================================
            first=False
                    
                
            log.info('finished \'%s\''%WorkFlow.name)
            
        #=======================================================================
        # wrap
        #=======================================================================
        #attach results
        if build_pickels:
            self.pick_d = pick_d
            log.info('wrote %i pickles'%len(pick_d))
        if get_tests:
            self.suite=suite
            
        return self.out_dir

    
class DSession(WF_handler, Session):
    
    
    
    #placeholders expected on teh session by some dialogs
    finv_vlay=None
    iface = None
 
    def __init__(self,
                 logger=None, 
                 tag='devDial',
                 **kwargs
                 ):
        
        #add the exception hook
        sys.excepthook = excepthook
        
        
        if logger is None:
            """unlike the wflow session, plugin loggers use special methods for interfacing with QGIS"""

            logger= devPlugLogger(self, log_nm='L')
        
        
        super().__init__(logger=logger,tag=tag, **kwargs) 
        
        self.logger.info('finished DSession.init')
        

    
    def xxxrun_wflow(self, #usin the sutie only?
                  WorkFlow,
                  **kwargs):
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('run_wflow')
        
        #===================================================================
        # crs
        #===================================================================
        if not WorkFlow.crsid == self.crsid:
            log.debug('crsid mismatch... switching to crs of workflow')
            self.set_crs(WorkFlow.crsid, logger=log)
            
            
        #=======================================================================
        # #collect pars
        #=======================================================================
        """similar to _get_wrkr().. but less flexible"""
        for k in list(self.com_hndls) + self.flow_hndls:
            kwargs[k] = getattr(self, k)
        
        #init
        kstr = ''.join(['\n    %s: %s'%(k,v) for k,v in kwargs.items()]) #plot string
        log.debug('building w/ %s'%kstr)
        
        
        #===================================================================
        # launch the flow
        #===================================================================
        with WorkFlow(logger=self.logger, session=self, **kwargs) as wflow:
            log.info('\n    PRE\n')
            wflow.pre()
            log.info('\n    LAUNCH\n')
            wflow.D.launch()
            
            wflow.post()
            
            sys.exit(self.qap.exec_()) #wrap
            
            
        log.info('finished')
            
    
    
class DialWF(WorkFlow): #workflow to run on your dialog
    name='DialWF'
    #pars_d = {} #best to define this on the child to avoid passing container to siblings
    DialogClass=None #replace with the dialog class you want to test on
    
    crs = QgsCoordinateReferenceSystem('EPSG:4326')
    
    def __init__(self,
                 DialogClass=None,
                 **kwargs):
        super().__init__(**kwargs)
        
        #=======================================================================
        # setup the dialog
        #=======================================================================
        if DialogClass is None: DialogClass=self.DialogClass
        self.D = DialogClass(None, session=self.session, plogger=self.logger)
        self.res_d=dict()  
    
    def pre(self): #pre launch
        pass #subclass to make your own
    
    def post(self):
        pass #subclass to create your own
    
    def _setup_coms(self): #common CanFlood dialog setups
        self.D._change_tab('tab_setup')
        # working directory
        assert os.path.exists(self.out_dir)
        self.D.lineEdit_wdir.setText(self.out_dir)
        
        
        #control file
        if 'cf_fp' in self.session.res_d:
            cf_fp = self.session.res_d['cf_fp']
            assert os.path.exists(cf_fp)
            self.D.lineEdit_cf_fp.setText(cf_fp)
            
            
        #tag
        tag = self.name
        assert isinstance(tag, str)
        self.D.linEdit_ScenTag.setText(tag)
        
    def __exit__(self, #destructor
                 *args,**kwargs):
        
        #clear the dialog
        self.D.__exit__() #not sure this is doing anything
        self.D.accept() #close it
        super().__exit__(*args,**kwargs) #initilzie teh baseclass
    
 
def run_set(workflow_l,
           **kwargs):
    
    with DSession(**kwargs) as ses:
        
        ses.run_suite(workflow_l)
        
        out_dir = ses.out_dir
        
    return out_dir

def open_dial(Workflow, #just open a dialog
              **kwargs):
    
    with DSession(**kwargs) as ses:
        
        ses.run_wflow(Workflow)
        
        out_dir = ses.out_dir
        
    return out_dir
    
    
    
        
        
