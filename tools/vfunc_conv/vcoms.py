'''
Created on Feb. 9, 2021

@author: cefect
'''
import os, datetime


import pandas as pd
import numpy as np


#from canflood.hlpr.logr import basic_logger
#mod_logger = basic_logger() 
from canflood.hlpr.basic import force_open_dir, view, get_valid_filename
from canflood.hlpr.exceptions import Error

from canflood.misc.curvePlot import CurvePlotr
#from canflood.model.modcom import DFunc

mod_name = 'misc.vcoms'
today_str = datetime.datetime.today().strftime('%Y%m%d')


class VfConv(CurvePlotr):
    #===========================================================================
    # program pars
    #===========================================================================
    ft_m = 0.3048
    dcoln = 'depth_m'
    res_d = dict() #container of each library created
    
    
        #tag cleaning
    tag_cln_d = {
        ' ':'',
        'Agricultural':'Ag',
        'Agriculture':'Ag',
        'buildings':'Bldgs',
        'Curve':'C'
        }
    
    exposure_units = 'meters'
    
    def __init__(self,
 
                 **kwargs
                 ):
        
        
        
        super().__init__(  **kwargs) #initilzie teh baseclass
        
