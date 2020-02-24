'''
Created on Apr 1, 2019

@author: cef
'''


#===============================================================================
# # IMPORT STANDARD MODS -------------------------------------------------------
#===============================================================================

import os, time, logging, gc, weakref, datetime




import pandas as pd
import numpy as np


from qgis.core import QgsFeatureRequest, QgsWkbTypes, QgsVectorLayer, QgsMapLayerStore

#===============================================================================
#  IMPORT CUSTOM MODS ---------------------------------------------------------
#===============================================================================
import hp.basic, hp.pd, hp.oop

from hp.pd import df_check
from hp.np import left_in_right as linr

from hp.exceptions import Error


import hp.Q.core, hp.Q.proj
from hp.Q.core import *
from hp.Q.algos import Alg







#===============================================================================
# mod_logger
#===============================================================================
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')




class Session(
        hp.Q.proj.Qproj, 
        hp.oop.Session):
    
    
    #===========================================================================
    # program pars
    #===========================================================================


    
    coms_df = pd.DataFrame()
    


    #===========================================================================
    # #attributse from paramater .xls
    #===========================================================================

    coms_dir = ''
    write_vlay = True
    report = False
    new_nm = 'finv'


      
    
    def __init__(self, **kwargs):
        
        super().__init__(**kwargs) #initilzie teh baseclass
        
        self.logger.debug('initilized with pars_fp: %s'%self.pars_fp)
        

            
if __name__ == '__main__':
    print('finished running %s'%__name__)




        

        
        
    
        
        
        
        
        
        
        
        
        