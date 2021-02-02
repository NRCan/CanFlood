'''
Created on Feb. 9, 2020

@author: cefect

simple build routines
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, shutil



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd
from pandas import IndexSlice as idx

#Qgis imports
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsMapLayerStore, QgsFeatureRequest, QgsProcessingParameterExpression,\
    QgsExpression
import processing
#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, view, stat_pars_d, \
    vlay_rename_fields
    
from results.riskPlot import Plotr
    
#from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class Dvuln(Plotr):
    """

    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """
    #data labels
    wsln = 'wsl'
    celn = 'crest_el'
    sdistn = 'seg_dist'
    fbn = 'freeboard'
    sid = 'sid' #global segment identifier
    nullSamp = -999 #value for bad samples

    def __init__(self,
                 figsize     = (10, 4),                  
                  *args,  **kwargs):
        
        super().__init__(*args, figsize=figsize,**kwargs)
        
        #=======================================================================
        # attach
        #=======================================================================

        
        self.logger.debug('Diker.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def load_fcurves(self):
        pass
    

    

    

            
        