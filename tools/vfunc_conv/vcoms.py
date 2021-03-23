'''
Created on Feb. 9, 2021

@author: cefect
'''
import os, datetime


import pandas as pd
import numpy as np


from hlpr.logr import basic_logger
mod_logger = basic_logger() 
from hlpr.basic import force_open_dir, view, get_valid_filename
from hlpr.exceptions import Error

from misc.curvePlot import CurvePlotr
#from model.modcom import DFunc

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

        
        super().__init__(**kwargs) #initilzie teh baseclass
        
    def output(self,
               d,
               ofn = None,
               out_dir = None,
               ):
        #=======================================================================
        # defaults
        #=======================================================================
        if out_dir is None: out_dir=self.out_dir
        if not os.path.exists(out_dir):os.makedirs(out_dir)
        if ofn is None:
            ofn = '%s_%s.xls'%(self.libName, today_str)
        
        ofn = get_valid_filename(ofn)
        assert os.path.splitext(ofn)[1]=='.xls', ofn
        #=======================================================================
        # precheck
        #=======================================================================
        for k, v in d.items():
            assert isinstance(v, pd.DataFrame), 'bad type on %s: %s'%(k, type(v))
        
        #=======================================================================
        # patsh
        #=======================================================================
        ofp = os.path.join(out_dir, ofn)
        assert len(d)>0
        if os.path.exists(ofp): assert self.overwrite
        
        #write to multiple tabs
        with pd.ExcelWriter(ofp, engine='xlsxwriter') as writer:
            for tabnm, df in d.items():
                #write handles
                if tabnm=='_smry':
                    index, header = True, True
                else:
                    index, header = False, False
                    
                #tab check
                if len(tabnm)>30:
                    tabnm = tabnm.replace(' ','')
                    
                df.to_excel(writer, sheet_name=tabnm, index=index, header=header)
            
            
        print('wrote %i sheets to %s'%(len(d), ofp))
            
        return ofp