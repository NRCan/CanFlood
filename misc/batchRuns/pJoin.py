'''
Created on Dec. 17, 2020

@author: cefect

join tabular to spatial worker
'''
import os, datetime
start =  datetime.datetime.now()
print('start at %s'%start)

import pandas as pd

from hlpr.logr import basic_logger
mod_logger = basic_logger().getChild('dj')




#import helpers
from hlpr.basic import force_open_dir
from qgis.core import QgsCoordinateReferenceSystem
from hlpr.Q import vlay_write, view

 

#import models

from results.djoin import Djoiner



def run_djoin( #generic runner for the risk2 model
            runpars_d,
            absolute_fp=True,
            overwrite=True,
            
            write_vlay=True,
            
            tag='djoin',
            crs_id='EPSG:3005',

    ):

    wrkr = Djoiner(overwrite=overwrite, absolute_fp=absolute_fp, tag=tag).ini_standalone(
        crs=QgsCoordinateReferenceSystem(crs_id))
    #==========================================================================
    # build/execute
    #==========================================================================
    meta_d = dict()
    for name, pars in runpars_d.items():
        cf_fp, vlay_fp = pars['cf_fp'], pars['finv_fp']
        #=======================================================================
        # get info from filepath
        #=======================================================================
        basedir = os.path.split(cf_fp)[0]
        #tag  = os.path.basename(basedir)
        
        out_dir = os.path.join(basedir, 'res', 'djoin')
        
        #=======================================================================
        # setup fr this run
        #=======================================================================       
        wrkr.logger=mod_logger.getChild(name)
        #wrkr.tag = tag
        wrkr.cf_fp = cf_fp
        wrkr.out_dir=out_dir
 
        
        if not os.path.exists(wrkr.out_dir):os.makedirs(wrkr.out_dir)
        
        
        wrkr.init_model() #load the control file
        #=======================================================================
        # load the layer
        #=======================================================================
        vlay_raw = wrkr.load_vlay(vlay_fp)
        
        """
        view(vlay_raw)
        """
        
        #=======================================================================
        # run join
        #=======================================================================
        #kwargs = {k:pars[k] for k in ['cf_fp', 'out_dir', 'cid']}
        jvlay = wrkr.run(vlay_raw, keep_fnl='all')
        
        #=======================================================================
        # write result
        #=======================================================================
        if write_vlay:
            out_fp = vlay_write(jvlay, 
                            os.path.join(wrkr.out_dir, '%s.gpkg'%jvlay.name()),
                                    logger=wrkr.logger, overwrite=overwrite)
            
        else:
            out_fp=''
            
        #=======================================================================
        # meta
        #=======================================================================
        meta_d[name] = {
            'djoin_fp':out_fp
            }

        
        

    print('finished on %i'%len(runpars_d))
    return wrkr.out_dir, meta_d


if __name__ =="__main__":
    print('???')