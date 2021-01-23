'''
Created on Dec. 16, 2020

@author: cefect
'''


import os, datetime
from qgis.core import QgsCoordinateReferenceSystem, QgsDataSourceUri, QgsRasterLayer,\
    QgsRectangle


from hlpr.logr import basic_logger
mod_logger = basic_logger() 
    
    
from hlpr.Q import Qcoms, vlay_write
from hlpr.basic import force_open_dir


from build.validator import Vali

def vchk(out_dir):
    
    tag='vchk'
    cf_fp = r'C:\Users\cefect\CanFlood\build\CanFlood_scenario1.txt'
   
    


    #==========================================================================
    # load the data
    #==========================================================================

    wrkr = Vali(cf_fp=cf_fp, logger=mod_logger, tag=tag, out_dir=out_dir, 
                 ).ini_standalone()
    
    from model.dmg2 import Dmg2
    from model.risk2 import Risk2
    
    res_d = dict()
    for vtag, modObj in {
        'dmg2':Dmg2,
        'risk2':Risk2
        }.items():
    
        #=======================================================================
        # run the check
        #=======================================================================
        errors = wrkr.cf_check(modObj)
        for e in errors:
            print('%s: %s'%(vtag, e))
            
        #=======================================================================
        # mark the control file
        #=======================================================================
        wrkr.cf_mark()
        
        #store results
        if len(errors) == 0: 
            res_d[vtag] = True
        else:
            res_d[vtag] = False
            
    #===========================================================================
    # wrap
    #===========================================================================
    for k, v in res_d.items():
        print(k,v)
        
    return res_d





if __name__ =="__main__": 
    start =  datetime.datetime.now()
    print('start at %s'%start)
    

    
    out_dir = r'C:\Users\cefect\CanFlood\build'
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
      
    #local_raster_copy(out_dir=out_dir)
    vchk(out_dir)
    
    #force_open_dir(out_dir)
 
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)