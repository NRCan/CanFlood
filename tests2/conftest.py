'''
Created on Feb. 21, 2022

@author: cefect

 
'''
import os, shutil, sys, datetime, traceback
import pytest
import numpy as np
from numpy.testing import assert_equal
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal, assert_index_equal
 


from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsWkbTypes, QgsRasterLayer, \
    QgsMapLayer
    
from PyQt5.QtWidgets import QApplication 
from PyQt5.QtCore import QTimer
import processing


import pytest_qgis #install check (needed by fixtures)
 
 

from wFlow.scripts import Session

def excepthook(exc_type, exc_value, exc_tb):
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    print("error message:\n", tb)
    QApplication.quit()

sys.excepthook = excepthook
 

class Session_pytest(Session): #QGIS enabled session handler for testing dialogs
    """see also
    dial_coms.DTestSessionQ
    """
    iface=None
    finv_vlay=None
    def __init__(self, 
                 crs=None,logger=None,
                  **kwargs):
        
        if logger is None:
            """unlike the wflow session, plugin loggers use special methods for interfacing with QGIS"""

            logger= devPlugLogger(self, log_nm='L')
            
            
 
        super().__init__(crsid = crs.authid(), logger=logger, 
                         #feedbac=MyFeedBackQ(logger=logger),
                         **kwargs)  
        
        
 
        self.logger.info('finished Session_pytest.__init__')
        
    def init_dialog(self,
                    DialogClass, iface=None,
                    ):
        
        if not iface is None:
            self.iface=iface
        if iface is None:
            iface = self.iface
            
        if hasattr(self, 'Dialog'):
            self.Dialog.close()
            
        self.Dialog = DialogClass(iface, session=self, plogger=self.logger)
                    
        self.Dialog.launch()
        
        return self.Dialog

        
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
         
        
 
        
        self.Dialog.close()
        self.qproj.clear() #cleare the project
 
        #sys.exit(self.qap.exec_()) #wrap
        
        #sys.exit() #wrap
        print('exiting DialTester')
        
@pytest.fixture(scope='function')
def dialogClass(request): #always passing this as an indirect
    return request.param

@pytest.fixture(scope='function')
def finv_fp(base_dir, request): #always passing this as an indirect
    return os.path.join(base_dir, request.param)

@pytest.fixture(scope='function')
def cf_fp(base_dir, request):
    return os.path.join(base_dir, request.param)
 

@pytest.fixture(scope='function')
def session(tmp_path,
  
            true_dir,
            write,  # (scope=session)
            crs, dialogClass,
            
            #pytest-qgis fixtures
            qgis_app, qgis_processing, qgis_iface
                    
                    ):
    """TODO: fix logger"""
 
    np.random.seed(100)
    
    #configure output
    out_dir=tmp_path
    if write:
        #retrieves a directory specific to the test... useful for writing compiled true data
        """this is dying after the yield statement for some reason...."""
        out_dir = true_dir

 
    
    with Session_pytest( 
                 name='test', #probably a better way to propagate through this key
   
                 out_dir=out_dir, 
                 temp_dir=os.path.join(tmp_path, 'temp'),
 
                 crs=crs, 
                 
                   overwrite=True,
                   write=write, #avoid writing prep layers
                   
                   qgis_app=qgis_app,qgis_processing=True,
  
        ) as ses:
        
        ses.init_dialog(dialogClass, iface=qgis_iface)
 
        yield ses

@pytest.fixture(scope='session')
def write():
 
    write=False
 
    
    if write:
        print('WARNING!!! runnig in write mode')
    return write

#===============================================================================
# function.fixtures-------
#===============================================================================
 
 
#===============================================================================
# session.fixtures----------
#===============================================================================
 
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
            
 
 

@pytest.fixture(scope='session')
def base_dir():
    from definitions import base_dir
 
    return base_dir

@pytest.fixture(scope='session')
def test_dir(base_dir):
    return os.path.join(base_dir, r'tests2\data')
    



@pytest.fixture
def true_dir(write, tmp_path, test_dir):
    true_dir = os.path.join(test_dir, os.path.basename(tmp_path))
    if write:
        if os.path.exists(true_dir):
            try: 
                shutil.rmtree(true_dir)
                os.makedirs(true_dir) #add back an empty folder
                #os.makedirs(os.path.join(true_dir, 'working')) #and the working folder
            except Exception as e:
                print('failed to cleanup the true_dir: %s w/ \n    %s'%(true_dir, e))
        
        """no... this is controlled with the out_dir on the session        
        #not found.. create a fresh one
        if not os.path.exists(true_dir):
            os.makedirs(true_dir)"""

    #assert os.path.exists(true_dir)
    return true_dir
    
  
            
            
            
            
            
            
            
            
