'''
Created on Nov. 27, 2021

@author: cefect

commons for testing dialogs
'''

#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging, datetime, time, sys, traceback
from PyQt5.QtWidgets import QApplication, QMainWindow 

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject
from wFlow.scripts import WorkFlow, Session

from hlpr.exceptions import Error

from hlpr.plug import plugLogger



#===============================================================================
# #add a special hook tot he exception
#===============================================================================
def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("error message:\n", tb)
    QApplication.quit()

sys.excepthook = excepthook


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



class DTestSessionQ(Session): #QGIS enabled session handler for testing dialogs
    """sub class this and add your own methods
    then call using a 'with' statement"""
    name='dialog tests'
    iface = None
    
    #placeholders expected on teh session by some dialogs
    finv_vlay=None
    def __init__(self,
                 DialogClass=None, #dialog class to test
                 crs=None,
                 Qenabled=True,
                 exitDialogMethod=None, #special dialog setup 
                 logger=None,
                 tag='devDial',
                 **kwargs):
        

        #setup logger
 
        if logger is None:
            """unlike the wflow session, plugin loggers use special methods for interfacing with QGIS"""

            logger= devPlugLogger(self, log_nm='L')
        
        
        super().__init__(crsid = crs.authid(),tag=tag, logger=logger, **kwargs)  
 
 
        
        #init the dialog        
        self.logger.push('init the DialogClass: \'%s\''%DialogClass.__name__)
        self.Dialog = DialogClass(None, session=self, plogger=self.logger)
        
        #set project attributes
        """these are typically inherted from the QGIS interface"""
        #self.Dialog.set_crs(crs=crs, crsid='')
        #assert self.Dialog.qproj.crs().authid() == crs.authid()
        if Qenabled:
            print('set crs to %s'%self.Dialog.qproj.crs().authid())
 
 
        #=======================================================================
        # atach
        #=======================================================================
        self.Qenabled=Qenabled
        self.exitDialogMethod=exitDialogMethod
        
        
        self.logger.info('finished DialTester.init')
        

        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        
        #=======================================================================
        # if not self.exitDialogMethod is None:
        #     f = getattr(self.Dialog, self.exitDialogMethod)
        #     f()
        #=======================================================================
        
 
        self.Dialog.launch()
        
        sys.exit(self.qap.exec_()) #wrap
        #sys.exit() #wrap
        print('exiting DialTester')
        
        
class DialWF(WorkFlow): #workflow to run on your dialog
    name='DialWF'
    pars_d = {}
    DialogClass=None #replace with the dialog class you want to test on
    
    crs = QgsCoordinateReferenceSystem('EPSG:4326')
    
    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        
        self.D = self.session.Dialog  
    
    def run(self):
        raise Error('subclass and create your own run function')
    
    
    
    
def test_set(
        workflow_l, **kwargs):
    res_d = dict()
    for workflow in workflow_l:
        
        #star tthe session
        ses = DTestSessionQ(DialogClass=workflow.DialogClass, crs=workflow.crs, **kwargs)
        
        #workflow pre-launch
        runr = ses._run_wflow(workflow)
        
        #launch the dialog
        ses.Dialog.launch()
        
        #post
        runr.post()
        
        
        
    return res_d


def test_setz(
        workflow_l, **kwargs):
    res_d = dict()
    for wf in workflow_l:
        res_d[wf.name] = test_dialog(wf, **kwargs)
        
    return res_d
    
def test_dialog( #runner for dialog test
        workflow, **kwargs):
    
    assert not workflow.DialogClass is None, 'need to assign a DialogClass'
    
    with DTestSessionQ(DialogClass=workflow.DialogClass, crs=workflow.crs, **kwargs) as ses:
        ses._run_wflow(workflow)
        out_dir = ses.out_dir
        
    return out_dir