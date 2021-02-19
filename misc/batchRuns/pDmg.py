'''
Created on Dec. 17, 2020

@author: cefect
'''
import os, datetime
import pandas as pd
from hlpr.logr import basic_logger
mod_logger = basic_logger().getChild('d2')

from model.dmg2 import Dmg2
from hlpr.basic import force_open_dir
from hlpr.exceptions import Error



start =  datetime.datetime.now()
print('start at %s'%start)
    

def run_dmg(runPars_d, 
            
            absolute_fp=True,
            
            output_bdmg=True,
            attribution=False,
            set_impactUnits = False,
            plot = True,
            upd_cf = True,
            
            logger=None,
            ):
    if logger is None: logger=mod_logger
    #==========================================================================
    # build/execute------------
    #==========================================================================
    meta_d=dict()
    out_dir=None
    
    wrkr = Dmg2(out_dir=os.getcwd(), logger=logger, tag='dmg2', 
                     absolute_fp=absolute_fp, attriMode=attribution,
                     figsize=(14,8)
                     )
                     
                     
    for atag, pars in runPars_d.items():
        cf_fp = pars['cf_fp']
        assert os.path.exists(cf_fp)
        
        #=======================================================================
        # get info from filepath
        #=======================================================================
        basedir = os.path.split(cf_fp)[0]
        #tag  = os.path.basename(basedir)
        #tag = 'dmg2'
        out_dir = os.path.join(basedir, 'dmg2')
        if not os.path.exists(out_dir):os.makedirs(out_dir)
        #=======================================================================
        # update for this loop
        #=======================================================================
        wrkr.cf_fp = cf_fp
        wrkr.out_dir = out_dir
        wrkr.logger = logger.getChild(atag)
        wrkr._setup()
        #=======================================================================
        # run
        #=======================================================================


        
        res_df = wrkr.run(set_impactUnits=set_impactUnits)
        
        """
        getting some phantom crash here
        """
        
        if attribution:
            _ = wrkr.get_attribution(res_df)
        
        #=======================================================================
        # plots
        #=======================================================================
        if plot:
            fig = wrkr.plot_boxes()
            _ = wrkr.output_fig(fig)
            
            fig = wrkr.plot_hist()
            _ = wrkr.output_fig(fig)
        
        #==========================================================================
        # outputs
        #==========================================================================
         
        out_fp = wrkr.output_cdmg()
         
        if upd_cf: 
            wrkr.update_cf()
        
        if output_bdmg:
            _ = wrkr.output_bdmg()
            _ = wrkr.bdmg_smry()
            _ = wrkr.output_depths_df()
            
        if attribution:
            _ = wrkr.output_attr()
            
        #=======================================================================
        # meta
        #=======================================================================
        meta_d[atag] = {
            'dmg_ttl':res_df.sum().sum()
            }

        
    return out_dir, meta_d
    

    
    

    
    
if __name__ =="__main__": 
    print('???')