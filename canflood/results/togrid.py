'''


@author: cefect

convert asset geometry results to new spatial grids
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime



#==============================================================================
# imports------------
#==============================================================================
import os, logging, datetime, gc
import numpy as np
import pandas as pd


#Qgis imports

from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject



#==============================================================================
# # custom
#==============================================================================

from hlpr.exceptions import QError as Error
    
from hlpr.Q import Qcoms




#==============================================================================
# functions-------------------
#==============================================================================
class Gwrk(Qcoms):
    """
    sampling asset geometry up to polygon grids
    """


    
    def __init__(self,
                 **kwargs
                 ):
        

        

        
        super().__init__(**kwargs) #initilzie teh baseclass
        
        self.logger.debug('init finished')
        
        


        