'''
Created on Dec. 17, 2020

@author: cefect
'''
import os, datetime

from hlpr.logr import basic_logger
mod_logger = basic_logger() 

from model.dmg2 import Dmg2
from hlpr.basic import force_open_dir
from hlpr.exceptions import Error


def generic(runpars_d, 
            output_bdmg=False,
            attribution=True,
            absolute_fp=True,
            ):

    #==========================================================================
    # build/execute------------
    #==========================================================================
    for tag, pars in runpars_d.items():
        log = mod_logger.getChild(tag)
        #=======================================================================
        # setup
        #=======================================================================
        out_dir = pars['out_dir']
            
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        
        
        cf_fp = pars['cf_fp']
 
        
        assert os.path.exists(cf_fp)
        
        #=======================================================================
        # run
        #=======================================================================
        
        wrkr = Dmg2(cf_fp, out_dir=out_dir, logger=log, tag=tag, 
                     absolute_fp=absolute_fp, attriMode=attribution,
                     )._setup()
        
        res_df = wrkr.run()
        
        if attribution:
            _ = wrkr.get_attribution(res_df)
        
    
        
        #==========================================================================
        # outputs
        #==========================================================================
         
        out_fp = wrkr.output_df(res_df, wrkr.resname)
         
        wrkr.upd_cf()
        
        if output_bdmg:
            _ = wrkr.output_bdmg()
            
        if attribution:
            _ = wrkr.output_attr()

        
    return out_dir
    

    
    


if __name__ =="__main__": 
    
    runpars_d={        
        'Tut2c':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\CanFlood_tut2c_20210123.txt',
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\dmg2',
            },
        
    #===========================================================================
    #     'Tut2a':{
    #          'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\CanFlood_tut2a.txt',
    #          'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\dev\dmg',
    #          }, 
    # 
    #     'Tut2b':{
    #         'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b\CanFlood_tut2b.txt',
    #         'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b\dev\dmg',
    #         },
    #      
    #     'Tut2c':{
    #         'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\CanFlood_tut2c.txt',
    #         'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\dev\dmg',
    #         },
    #===========================================================================
        
        #=======================================================================
        # 'LMFRA.bldgs.sfd3':{
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bldgs.sfd3\build_aoi02\dmg2',
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bldgs.sfd3\build_aoi02\CanFlood_LMFRA.bldgs.sfd3.txt',
        #     'absolute_fp':True,
        #     },
        #=======================================================================
        #=======================================================================
        # 'LML.bs4':{
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01',
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\CanFlood_LML.bs4.txt',
        #     'absolute_fp':True,
        #     },
        #=======================================================================

        #=======================================================================
        # 'bs6.b02':{
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs6\b02_ind\dmg',
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs6\b02_ind\CanFlood_LML.bs6.indep.ind.txt',
        #     },
        #=======================================================================
        
        #=======================================================================
        # 'bs7.b01':{
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b01\dmg',
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b01\CanFlood_Lbs6.ind.txt',
        #     },
        #=======================================================================
                
        #=======================================================================
        # 'bs7.b02':{
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b02\dmg',
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b02\CanFlood_LML.bs7.txt',
        #     },
        #=======================================================================
        
        #=======================================================================
        # 'bs7.b03':{
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\dmg',
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\CanFlood_LML.bs7.txt',
        #     }
        #=======================================================================
        
        }
        
        
    start =  datetime.datetime.now()
    print('start at %s'%start)
 

      

    #test1(out_dir)
    out_dir = generic(runpars_d)
    
    force_open_dir(out_dir)
 

    print('finished in %s'%(datetime.datetime.now() - start))