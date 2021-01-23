'''
Created on Dec. 17, 2020

@author: cefect
'''
import os, datetime
start =  datetime.datetime.now()
print('start at %s'%start)

from hlpr.logr import basic_logger
mod_logger = basic_logger() 



#import helpers
from hlpr.basic import force_open_dir



#import models
from results.attribution import Attr


def noFail_slice( #generic runner for the risk2 model
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
        
        wrkr = Attr(cf_fp, out_dir=out_dir, logger=log, tag=tag,
                     absolute_fp=absolute_fp,
                     )._setup()
        
        

        si_ttl = wrkr.get_slice_noFail()
        #=======================================================================
        # plot
        #=======================================================================
        for y1lab in ['AEP', 'impacts']:
            fig = wrkr.plot_slice(si_ttl, y1lab=y1lab)
            wrkr.output_fig(fig)

    return out_dir

def stacks( #generic runner for the risk2 model
            runpars_d,
            absolute_fp=False,

    ):

    #==========================================================================
    # build/execut
    #==========================================================================
    for tag, pars in runpars_d.items():
        log = mod_logger.getChild(tag)
        out_dir = pars['out_dir']

        #paths
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        
        #=======================================================================
        # runit
        #=======================================================================
        
        wrkr = Attr(pars['cf_fp'], out_dir=out_dir, logger=log, tag=tag,
                     absolute_fp=absolute_fp,
                     impactFmtFunc=lambda x:'{:,.0f}'.format(x),   #(thousands separator)
                     )._setup()
        
        stack_dxind, sEAD_ser = wrkr.get_stack()
        
        #=======================================================================
        # plot
        #=======================================================================
        for y1lab in ['impacts', 'AEP']:
            fig = wrkr.plot_stackdRCurves(stack_dxind, sEAD_ser, y1lab=y1lab)
            wrkr.output_fig(fig)
            
    return out_dir
        

def one_slice( #generic runner for the risk2 model
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
        
        wrkr = Attr(cf_fp, out_dir=out_dir, logger=mod_logger, tag=tag,
                     absolute_fp=absolute_fp)._setup()
        
        
        s1_dxcol = wrkr.get_slice(pars['slice_d']) #slice of attribution values
        
        s1i_dxcol = wrkr.get_mult(s1_dxcol) #multiply by impacts
        
        s1i_ttl = wrkr.get_ttl(s1i_dxcol) #sum to aeps
        
        #=======================================================================
        # plot
        #=======================================================================
        for y1lab in ['AEP', 'impacts']:
            fig = wrkr.plot_slice(s1i_ttl, y1lab=y1lab)
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
             'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\dev\r2\att',
             }, 
   
        'Tut2b':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b\CanFlood_tut2b.txt',
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b\dev\r2\att',
            },
         
        'Tut2c':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\CanFlood_tut2c.txt',
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\dev\r2\att',
            },

        }
    
    #test()
    #===========================================================================
    # run
    #===========================================================================
    out_dir = stacks(runpars_d)
    out_dir = noFail_slice(runpars_d)
    
    
    #===========================================================================
    # wrap
    #===========================================================================
    force_open_dir(out_dir)
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)