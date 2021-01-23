'''
Created on Dec. 17, 2020

@author: cefect
'''
import os, datetime

from hlpr.logr import basic_logger
mod_logger = basic_logger() 

from model.risk1 import Risk1
from hlpr.basic import force_open_dir


def generic(runpars_d,
            absolute_fp=True,    
            ead_plot = True,
            res_per_asset = True,
    ):
    #==========================================================================

    #==========================================================================
    # build/execute------------
    #==========================================================================
    for tag, pars in runpars_d.items():
        cf_fp = pars['cf_fp']
        out_dir = pars['out_dir']
        log = mod_logger.getChild(tag)       
        
        wrkr = Risk1(cf_fp, out_dir=out_dir, logger=log, tag=tag, 
                     absolute_fp=absolute_fp,
                     )._setup()
        
        res_ser, res_df = wrkr.run(res_per_asset=res_per_asset)
        
    
        
        #======================================================================
        # plot
        #======================================================================
        if ead_plot:
            fig = wrkr.risk_plot()
            _ = wrkr.output_fig(fig)
            
        
        #==========================================================================
        # output
        #==========================================================================
        wrkr.output_df(res_ser, '%s_%s'%(wrkr.resname, 'ttl'))
        
        if not res_df is None:
            _ = wrkr.output_df(res_df, '%s_%s'%(wrkr.resname, 'passet'))
            
        
    return out_dir

    
    


if __name__ =="__main__": 
    start =  datetime.datetime.now()
    print('start at %s'%start)
    

    
    runpars_d={
        'Tut1a':{
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\1a\r1_out',
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\1a\CanFlood_tut1a.txt',
            },
                
        'Tut1b':{
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\1b\r1_out',
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\1b\CanFlood_tut1b.txt',
            }
        }
      

    #test1(out_dir)
    out_dir = generic(runpars_d)
    
    force_open_dir(out_dir)
 

    print('finished in %s'%(datetime.datetime.now() - start))