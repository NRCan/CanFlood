'''
Created on Feb. 21, 2022

@author: cefect

 
'''
import os, shutil
import pytest
import numpy as np
from numpy.testing import assert_equal
import pandas as pd
from pandas.testing import assert_frame_equal, assert_series_equal, assert_index_equal
 

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsWkbTypes, QgsRasterLayer, \
    QgsMapLayer
    
import processing
  

@pytest.fixture(scope='session')
def write():
    #===========================================================================
    # write key
    #===========================================================================
    write=False
    #===========================================================================
    # write key
    #===========================================================================
    
    if write:
        print('WARNING!!! runnig in write mode')
    return write

#===============================================================================
# function.fixtures-------
#===============================================================================
 
 
#===============================================================================
# session.fixtures----------
#===============================================================================
@pytest.fixture(scope='session')
def root_dir():
    from definitions import root_dir
    return root_dir



@pytest.fixture(scope='session')
def logger(root_dir):

    os.chdir(root_dir) #set this to the working directory
    print('working directory set to \"%s\''%os.getcwd())

    from hp.logr import BuildLogr
    lwrkr = BuildLogr()
    return lwrkr.logger

@pytest.fixture(scope='session')
def feedback(logger):
    from hp.Q import MyFeedBackQ
    return MyFeedBackQ(logger=logger)
 

@pytest.fixture(scope='session')
def base_dir():
    
    #'C:\\LS\\09_REPOS\\03_TOOLS\\RICorDE\\tests\\data\\compiled'
    base_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'compiled')
 
    assert os.path.exists(base_dir)
    return base_dir



@pytest.fixture
def true_dir(write, tmp_path, base_dir):
    true_dir = os.path.join(base_dir, os.path.basename(tmp_path))
    if write:
        if os.path.exists(true_dir):
            try: 
                shutil.rmtree(true_dir)
                os.makedirs(true_dir) #add back an empty folder
                os.makedirs(os.path.join(true_dir, 'working')) #and the working folder
            except Exception as e:
                print('failed to cleanup the true_dir: %s w/ \n    %s'%(true_dir, e))

            
    return true_dir
    
#===============================================================================
# helper funcs-------
#===============================================================================
def search_fp(dirpath, ext, pattern): #get a matching file with extension and beginning
    assert os.path.exists(dirpath), 'searchpath does not exist: %s'%dirpath
    fns = [e for e in os.listdir(dirpath) if e.endswith(ext)]
    
    result= None
    for fn in fns:
        if pattern in fn:
            result = os.path.join(dirpath, fn)
            break
        
    if result is None:
        raise IOError('failed to find a match for \'%s\' in %s'%(pattern, dirpath))
    
    assert os.path.exists(result), result
        
        
    return result


def retrieve_data(dkey, fp, ses): #load some compiled result off the session (using the dkey)
    assert dkey in ses.data_retrieve_hndls
    hndl_d = ses.data_retrieve_hndls[dkey]
    assert 'compiled' in hndl_d, '%s has no compliled handles'%dkey
    
    return hndl_d['compiled'](fp=fp, dkey=dkey)

 
            
def rasterstats(rlay): 
      
    ins_d = { 'BAND' : 1, 
             'INPUT' : rlay,
              'OUTPUT_HTML_FILE' : 'TEMPORARY_OUTPUT' }
 
    return processing.run('native:rasterlayerstatistics', ins_d )   
            
            
            
            
            
            
            
            
