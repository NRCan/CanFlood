'''
Created on Dec. 17, 2020

@author: cefect

Total plot dev
'''
import os, datetime
start =  datetime.datetime.now()
print('start at %s'%start)

from hlpr.logr import basic_logger
mod_logger = basic_logger() 



#import helpers
from hlpr.basic import force_open_dir



#import models

from results.riskPlot import Plotr


def one_plot( #generic runner for the risk2 model
            runpars_d,
            absolute_fp=False,

    ):

    #==========================================================================
    # build/execute
    #==========================================================================
    for tag, pars in runpars_d.items():
        
        log = mod_logger.getChild(tag)
        
        #pull form parameters
        cf_fp = pars['cf_fp']
        out_dir = pars['out_dir']

        #paths
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        assert os.path.exists(cf_fp)
        
        #=======================================================================
        # runit
        #=======================================================================
        
        wrkr = Plotr(cf_fp=cf_fp, out_dir=out_dir, logger=log, tag=tag,
                     impactFmtFunc=None,
                     absolute_fp=absolute_fp)._setup()
        
        
        #=======================================================================
        # plot
        #=======================================================================
        for y1lab in ['AEP', 'impacts']:
            fig = wrkr.plot_riskCurve(y1lab=y1lab)
            wrkr.output_fig(fig)
        
        
        

            
    return out_dir

 
    


if __name__ =="__main__": 
    
    #===========================================================================
    # run parameters
    #===========================================================================
    runpars_d={

        
 #==============================================================================
 #        'LML.bs7.b02.r01':{
 #            'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b02\CanFlood_LML.bs7.txt',
 #            'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b02\r01\at01',
 #             
 #            'slice_d':{
 #                'rEventName':('AG4_Fr_1000_WL_fail_0415','AG4_Fr_1000_WL_fail_0415','AG4_Fr_0750_WL_fail_0415','AG4_Fr_0500_WL_fail_0415','AG4_Fr_0200_WL_fail_0415','AG4_Fr_0100_WL_fail_0415','AG4_Fr_0050_WL_fail_0415','AG4_Fr_0030_WL_fail_0415'),
 #                },
 #             
 #            'stackLvlName':'nestID',
 # 
 #            },
 #        
 #        'LML.bs7.b01.r01':{
 #            'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b01\CanFlood_Lbs6.ind.txt',
 #            'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b01\r01\at01',
 #             
 #            },
 #==============================================================================
        #=======================================================================
        # 
        # 'LML.bs7.b03.max':{
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\CanFlood_LML.bs7_max.txt',
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\r01_max\at1',
        #     'stackLvlName':'nestID',
        #     },
        # 
        # 'LML.bs7.b03.mutEx':{
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\CanFlood_LML.bs7_mutEx.txt',
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\r02_mutEx\a11',
        #     'stackLvlName':'nestID',
        #     },
        #=======================================================================
        
        'Tut2a':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\CanFlood_tut2a.txt',
             'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\dev\r2\plt',
             }, 
   
        'Tut2b':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b\CanFlood_tut2b.txt',
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b\dev\r2\plt',
            },
         
        'Tut2c':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\CanFlood_tut2c.txt',
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\dev\r2\plt',
            },

        }
    
    #test()
    #===========================================================================
    # run
    #===========================================================================

    out_dir = one_plot(runpars_d)
    
    
    #===========================================================================
    # wrap
    #===========================================================================
    force_open_dir(out_dir)
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)