'''
Created on Feb. 27, 2020

@author: cefect

impact lvl 1 model
'''


#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, logging.config
#logcfg_file = r'C:\Users\tony.decrescenzo\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\floodiq\_pars\logger.conf'
logger = logging.getLogger() #get the root logger
#logging.config.fileConfig(logcfg_file) #load the configuration file
#logger.info('root logger initiated and configured from file: %s'%(logcfg_file))


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import configparser, os

import pandas as pd
import numpy as np
import math
#custom imports
import hp
from hp import Error, view

from canflood_inprep.model.common import Model



class Dmg21(Model):
    pass