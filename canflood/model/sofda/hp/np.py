'''
Created on May 17, 2018

@author: cef

library of custom hp functions for numpy

'''

# Import Python LIbraries 
import os, logging, shutil, random

from datetime import datetime


import numpy as np


mod_logger = logging.getLogger(__name__)


def isar(ar):
    
    if isinstance(ar, np.ndarray): return True
    return False

def dropna(ar_raw, logger=mod_logger): #drop na values from teh array
    logger = logger.getChild('dropna')
    
    boolar = np.isnan(ar_raw)
    
    if boolar.sum() > 0: logger.warning('found %i na values'%(boolar.sum()))
        
    return ar_raw[~boolar]

def np_isin_workaround(a_mat, b_mat): #elementwise test
    'numpy 1.13 has the builtin function np.isin'
    
    #check that a_mat is longer than b_mat
    """
    if not int(a_mat.shape[0]) >= int((b_mat.shape[0])):
        logger.error('a_mat should be longer than b_mat: \n %s \n %s'%(a_mat, b_mat))
        raise IOError
    """
    #check that both are 1d?
    
    return np.array([item in b_mat for item in a_mat])

def String2dtype(text_str): #convert a text string to its obvious numpy type
    """TESTING:
    text_str = 'str'
    type = String2dtype(text_str)
    """
    if text_str == 'str':
        return np.object
    elif text_str == 'int':
        return np.int64
        
    elif text_str == 'float':
        return np.float64
    else:
        logger.warning('No dtype match for: %s'%text_str)
        raise IOError
    
def Str2dtype_list(str_list): #convert strings to a list of np.dtypes
    dtype_list = []
    for text_str in str_list:
        dtype = String2dtype(text_str)
        dtype_list.append(dtype)
    
    return dtype_list

def recast_np_to_py(obj_np, logger = mod_logger): #recast a numpy object back into a pythonic one
    logger = logger.getChild('recast_np_to_py')
    if hasattr(obj_np, 'dtype'): #check if this is a numpy object
        try:
            obj_py = np.asscalar(obj_np)
        except:
            logger.debug('failed to recast numpy (%s) to pythonic')
            obj_py = obj_np
            
        return obj_py
    else: return obj_np
    
def make_1D(raw_ar, logger=mod_logger): #coerce and check the data is 1D
    
    logger = logger.getChild('make_1D')

    if not len(raw_ar.shape) == 1:
        logger.warning('got passed data with %i dimensions'%len(raw_ar.shape))
        raise IOError #todo: add some coercian
    
    
    
    return raw_ar

def get_stats_str_l(raw_ar, logger=mod_logger):
    
    l = list()
    
    try:
        l.append('mean = %.2f'%raw_ar.mean())
    except:    pass
    
    try: l.append('std = %.2f'%raw_ar.std())
    except: pass
    
    try: l.append('var = %.2f'%raw_ar.var())
    except: pass
    
    return l
    