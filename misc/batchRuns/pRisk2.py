'''
Created on Dec. 17, 2020

@author: cefect

basic risk2 run script
'''
import os, datetime
start =  datetime.datetime.now()
print('start at %s'%start)

import pandas as pd

from hlpr.logr import basic_logger
mod_logger = basic_logger().getChild('r2')



#import helpers
from hlpr.basic import force_open_dir

 

#import models
from model.risk2 import Risk2



def run_r2( #generic runner for the risk2 model
            runPars_d,
            smry_d = None,
            plot = True,
            res_per_asset = True,

            absolute_fp=True,
            attriMode=False,
            
            overwrite=True,
    ):
    
    #==========================================================================
    # build/execute------------
    #==========================================================================
    res_d = dict()
    out_dir=None
    for atag, pars in runPars_d.items():
        cf_fp = pars['cf_fp']
        assert os.path.exists(cf_fp)
        
        #=======================================================================
        # get info from filepath
        #=======================================================================
        basedir = os.path.split(cf_fp)[0]
        #tag  = os.path.basename(basedir)
        tag='r2'
        out_dir = os.path.join(basedir, 'risk2')
        
        #=======================================================================
        # runit
        #=======================================================================
        log = mod_logger.getChild(atag)
        wrkr = Risk2(cf_fp, out_dir=out_dir, logger=log, tag=tag,
                     absolute_fp=absolute_fp, attriMode=attriMode,overwrite=overwrite,
                     )._setup()
        
        res_ttl, res_df = wrkr.run(res_per_asset=res_per_asset)
        
        """
        res_df.columns
        """
        #======================================================================
        # plot
        #======================================================================
        if plot:
            ttl_df = wrkr.prep_ttl(tlRaw_df=res_ttl)
            for y1lab in ['AEP', 'impacts']:
                fig = wrkr.plot_riskCurve(ttl_df, y1lab=y1lab)
                _ = wrkr.output_fig(fig)
            
            

        #==========================================================================
        # output
        #==========================================================================
        wrkr.output_ttl()
        wrkr.output_etype()
        
        if not res_df is None:
            wrkr.output_passet()
            

        if attriMode:
            wrkr.output_attr()
            
        #=======================================================================
        # meta
        #=======================================================================
        res_d[atag] = {
            'ead':wrkr.ead_tot
            }
                
        if not smry_d is None:
            #get summaries from handles
            miss_l = set(smry_d.keys()).difference(res_df.columns)
            assert len(miss_l)==0, 'missing summary columns on results:%s'%miss_l
            
            for coln, smry_str in smry_d.items():
                f = getattr(res_df[coln], smry_str) 
                
                res_d[atag]['%s_%s'%(coln, smry_str)] = f()
        
        #=======================================================================
        # wrap
        #=======================================================================
        del wrkr
        print('finished %s \n\n\n'%atag)
        
        
        

    print('finished w/ %i'%len(res_d))
    return out_dir, res_d
    

    

    
if __name__ =="__main__": 
    print('??')