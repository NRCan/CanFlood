'''
Created on Feb. 24, 2021

@author: cefect

scripted dike runs
'''


import os, datetime
from qgis.core import QgsCoordinateReferenceSystem, QgsRasterLayer


from hlpr.logr import basic_logger
mod_logger = basic_logger() 
    
    
from hlpr.Q import Qcoms, vlay_write
from hlpr.basic import force_open_dir

from runComs import Runner

class DikeRunner(Runner):

    def __init__(self,
                 pars_d,
                 **kwargs):
        
        super().__init__(pars_d, **kwargs)