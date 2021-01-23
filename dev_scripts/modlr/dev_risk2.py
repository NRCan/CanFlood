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

#for Djoiner
from hlpr.Q import vlay_write
from qgis.core import QgsCoordinateReferenceSystem

#import models
from model.risk2 import Risk2
from results.djoin import Djoiner


def generic( #generic runner for the risk2 model
            runpars_d,
            ead_plot = True,
            res_per_asset = True,
            join_res = False,
            absolute_fp=True,
            attriMode=True,
    ):


    
    
    #==========================================================================
    # build/execute------------
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
        
        wrkr = Risk2(cf_fp, out_dir=out_dir, logger=log, tag=tag,
                     absolute_fp=absolute_fp, attriMode=attriMode,
                     )._setup()
        
        res_ttl, res_df = wrkr.run(res_per_asset=res_per_asset)
        
        """
        res_df.columns
        """
        #======================================================================
        # plot
        #======================================================================
        if ead_plot:
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
        # join
        #=======================================================================
        #=======================================================================
        # if join_res:
        #     """
        #     this will crash for multple tag loops
        #     """
        #     #setup
        #     wrkr = Djoiner(logger=log, tag = tag, cid=pars['cid'],  out_dir=out_dir,
        #                 ).ini_standalone(
        #                     crs=QgsCoordinateReferenceSystem(pars['crs_id']))
        #     
        #     #load vectorlayer
        #     geo_vlay = wrkr.load_vlay(pars['finv_fp'])
        #     
        #     #join
        #     res_vlay = wrkr.run(geo_vlay, passet_fp, pars['cid'],
        #              keep_fnl='all', #todo: setup a dialog to allow user to select any of the fields
        #              )
        #     
        #     #save results
        #     vlay_write(res_vlay, 
        #                os.path.join(out_dir, '%s_risk2.gpkg'%tag), 
        #                logger=log)
        #=======================================================================
            
    return out_dir
    

    
    


if __name__ =="__main__": 
    
    #===========================================================================
    # run parameters
    #===========================================================================
    runpars_d={
   #============================================================================
   #      'Tut2a':{
   #           'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\CanFlood_tut2a.txt',
   #           'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\dev\r2',
   #           }, 
   # 
   #      'Tut2b':{
   #          'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b\CanFlood_tut2b.txt',
   #          'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b\dev\r2',
   #          },
   #============================================================================
         
        'Tut2c':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\CanFlood_tut2c.txt',
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\dev\r2',
            },
        
        'Tut2c_max':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\CanFlood_tut2c_max.txt',
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\dev\r2_max',
            }
 
        
        
        #=======================================================================
        # 'bs6.ind.ind':{
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs6\b02_ind\CanFlood_LML.bs6.indep.ind.txt',
        #     'absolute_fp':True,
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs6\b02_ind\r01_ind',
        #     },
        #=======================================================================
        #=======================================================================
        # 'bs6.ind.mut':{
        #     'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs6\b02_ind\CanFlood_LML.bs6.indep.mut.txt',
        #     'absolute_fp':True,
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs6\b02_ind\r02_mut',
        #     
        #      #plot handles
        #     'basev':1, 'dfmt':'{:.2e}',
        #     },
        #=======================================================================
        
  #=============================================================================
  #       'LML.bs7.b01':{
  #           'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b01\CanFlood_Lbs6.ind.txt',
  #           'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b01\r01',
  # 
  #           },
  #       
  #       'LML.bs7.b02':{
  #           'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b02\CanFlood_LML.bs7.txt',
  #           'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b02\r01',
  #           },
  #=============================================================================
   #============================================================================
   #      'LML.bs7.b03.max':{
   #          'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\CanFlood_LML.bs7_max.txt',
   #          'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\r01_max',
   # 
   #          },
   #       
   #      'LML.bs7.b03.mutEx':{
   #          'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\CanFlood_LML.bs7_mutEx.txt',
   #          'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03\r02_mutEx',
   #          },
        }
     

    #===========================================================================
    # run
    #===========================================================================
    #test1(out_dir)
    out_dir = generic(runpars_d)
    
    
    #===========================================================================
    # wrap
    #===========================================================================
    force_open_dir(out_dir)
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)