'''
Created on Dec. 29, 2021

@author: cefect

miscellaneous tools for dealing with vfuncLibs
'''


#==============================================================================
# imports------------
#==============================================================================
import os, datetime
start =  datetime.datetime.now()
import numpy as np
import pandas as pd

from canflood.hlpr.basic import view, force_open_dir
from canflood.hlpr.exceptions import Error

from vfunc_conv.vcoms import VfConv
from canflood.model.dmg2 import Dmg2


import wFlow.scripts 

class Session(VfConv, Dmg2, wFlow.scripts.Session):
    def __init__(self,
                 projName='vfMisc',
                 **kwargs):
        
        super().__init__(projName=projName,
                         **kwargs) 




 

def add_smry( #add a summary page to a vfunc library
        fp=r'C:\LS\04_LIB\02_spatial\AEP\AlbertaCurves\CanFlood_curves_rfda_20200218.xls',
        ftags_valid=None, #optional tab names to include
        ):
    
    
    
    with Session( write=True, plot=False) as ses:
        
        #load the data
        cdf_d = ses.load_data(fp)
        
        assert not '_smry' in cdf_d
        
        #get ftags
        """setup_dfuncs is configured to only load those dfuncs
        found in the finv... this is ignored when ftags_valid is passed"""
        if ftags_valid is None:
            ftags_valid = list(cdf_d.keys())
        
        #build the dfuncs
        ses.setup_dfuncs(cdf_d, ftags_valid=ftags_valid)
        
        #retreive
        dfuncs_d = ses.dfuncs_d
        clib_d = {k:v.df_raw for k,v in dfuncs_d.items()} #get loaded frames
        
        #generate the summary frame
        smry_df = pd.DataFrame.from_dict({k:v.get_stats() for k,v in dfuncs_d.items()}).T
        
        #write
        ofp = ses.output({**{'_smry':smry_df}, **clib_d},
                          ofn='%s_%s.xls'%(os.path.basename(fp).replace('.xls', ''), datetime.datetime.now().strftime('%m%d')),
                          )
        
 
        
    return ofp
        
        
        
        
    
    


if __name__ == "__main__": 
    
    #output = run_use1()
    output = add_smry()
    # reader()
    
    tdelta = datetime.datetime.now() - start
    print('finished in %s \n    %s' % (tdelta, output))