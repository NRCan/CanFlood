'''
Created on Feb. 9, 2020

@author: cefect

mapping dike analysis results back onto geometry
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
#import logging, configparser, datetime, shutil



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd
from pandas import IndexSlice as idx

#Qgis imports
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsMapLayerStore
 
import processing
#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, view, stat_pars_d, \
    vlay_rename_fields
    
 

from .dPlot import DPlotr
    
#from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class DRes(Qcoms, DPlotr):
    """

    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """


    def __init__(self,
                 
                  *args,  **kwargs):
        
        super().__init__(*args,**kwargs)
        

        
        self.logger.debug('Diker.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        

    
    
    

    

            
        