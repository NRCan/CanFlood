'''
Created on Feb. 9, 2020

@author: cefect

Template for 'build' scripts
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


#Qgis imports
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject

#==============================================================================
# custom imports
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
    

from hlpr.Q import *
from hlpr.basic import *

#==============================================================================
# functions-------------------
#==============================================================================
class Gen(Qcoms):
    """
    general methods for the Build dialog
    
    broken out for development/testing
    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """


    def __init__(self,

                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        

        
        self.logger.debug('Gen.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
    


                


if __name__ =="__main__": 
    write_vlay=True
    
   
    
    
    out_dir = os.path.join(os.getcwd(), 'wsamp', tag)

    #==========================================================================
    # load the data
    #==========================================================================

    wrkr = Gen(logger=mod_logger, tag=tag, out_dir=out_dir, cid=cid,
                 )
    

    

    
    #==========================================================================
    # save results
    #==========================================================================

     

 
    force_open_dir(out_dir)
 
    print('finished')
    
    
    

    

            
        