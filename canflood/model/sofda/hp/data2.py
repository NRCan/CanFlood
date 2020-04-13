'''
Created on Oct 12, 2018

@author: cef


Data analysis 

'''

#===============================================================================
# # IMPORTS --------------------------------------------------------------------
#===============================================================================
import os, time, logging, gc, weakref, copy, sys, re
import pandas as pd
import numpy as np

from collections import OrderedDict
from weakref import WeakValueDictionary as wdict
from weakref import proxy


import model.sofda.hp.pd as hp_pd
import model.sofda.hp.oop as hp_oop
import model.sofda.hp.dict as hp_dict
import model.sofda.hp.data as hp_data2

#===============================================================================
# mod_logger
#===============================================================================
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')


class Dataset(hp_oop.Child):
    data = None
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dataset') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
                #initilzie the first baseclass
        super(Dataset, self).__init__(*vars, **kwargs) 
        
    def calc_spread(self):
        
        #variance
        
        #coefficient of variation
        
        #interquartile range
        
        #root mean square
        
        return
    
    def calc_moments(self):
        
        return
    
    
    def fit_pdist(self, dist_name = 'norm'):
        
        return
    
    
        
        

    
    
