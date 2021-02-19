'''
Created on Dec. 17, 2020

@author: cefect
'''
import os, datetime
start =  datetime.datetime.now()
import pandas as pd
from hlpr.logr import basic_logger
mod_logger = basic_logger().getChild('r1')

from model.risk1 import Risk1
from hlpr.basic import force_open_dir



def run_r1( #generic runner for the risk2 model
            runPars_d,
            
            smry_d = None, #additional columns on res_df to summarise
            

            
            #run controls
            plot = True,
            res_per_asset = True,
            absolute_fp=True,
            overwrite=True,
            logger=None,
    ):
    if logger is None: logger=mod_logger
    print('on %i'%len(runPars_d))
    #==========================================================================
    # build/execute------------
    #==========================================================================
    out_dir=None
    res_d = dict()
    for atag, pars in runPars_d.items():
        
        cf_fp = pars['cf_fp']
        assert isinstance(cf_fp, str), '%s got bad cf_fp type: %s'%(atag, type(cf_fp))
        assert os.path.exists(cf_fp)
        
        #=======================================================================
        # get info from filepath
        #=======================================================================
        basedir = os.path.split(cf_fp)[0]
        #tag  = os.path.basename(basedir)
        tag='r1'
        out_dir = os.path.join(basedir, 'risk1')
        
        #=======================================================================
        # runit     
        #=======================================================================
        log = logger.getChild(atag)
        wrkr = Risk1(cf_fp, out_dir=out_dir, logger=log, tag=tag,
                     absolute_fp=absolute_fp, overwrite=overwrite,
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
            
        
    return out_dir, res_d

    
    


    
if __name__ =="__main__": 
    print('???')