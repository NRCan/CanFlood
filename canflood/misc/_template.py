'''
Created on Feb. 9, 2020

@author: cefect

Template for worker scripts
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd





#==============================================================================
# Logger
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
#plugin runs
else:
    #base_class = object
    from hlpr.exceptions import QError as Error
    


#===============================================================================
# Qgis imports
#===============================================================================
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject

from hlpr.Q import Qcoms

#===============================================================================
# non-Qgis
#===============================================================================
from hlpr.basic import ComWrkr

#==============================================================================
# functions-------------------
#==============================================================================
class Gen(ComWrkr):
    """
    general methods to be called by the Dialog class
    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """


    def __init__(self,

                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        

        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(self.__class__.__name__, type(self.feedback).__name__))
        
    


    
    
    

    

            
        