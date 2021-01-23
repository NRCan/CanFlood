'''
Created on Dec. 17, 2020

@author: cefect
'''
import os, datetime

from hlpr.logr import basic_logger
mod_logger = basic_logger() 

from results.compare import Cmpr
from hlpr.basic import force_open_dir


def compareGroup(runpars_d):
    
    for tag, pars in runpars_d.items():
        
        #=======================================================================
        # setup
        #=======================================================================
        log = mod_logger.getChild(tag)
        out_dir = pars['out_dir']
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        
        fps_d = pars['fps_d']

        wrkr = Cmpr(out_dir=out_dir, tag=tag, logger=log,
                    cf_fp = fps_d[list(fps_d)[0]]
                    #cf_fp = gPars_d[list(gPars_d.keys())[0]]['cf_fp'] #pull first control file for style controls
                    )
    
        #load
        sWrkr_d = wrkr.load_scenarios(list(fps_d.values()))
        
        #=======================================================================
        # #compare the control files
        #=======================================================================
        mdf = wrkr.cf_compare(sWrkr_d)
        mdf.to_csv(os.path.join(out_dir, 'CFcompare_%s_%i.csv'%(tag, len(mdf.columns))))
        
        #=======================================================================
        # #plot curves
        #=======================================================================
        for y1lab in ['AEP', 'impacts']:
            fig = wrkr.riskCurves(sWrkr_d, y1lab=y1lab)
            wrkr.output_fig(fig)
        

    
    return out_dir




if __name__ =="__main__": 
    
    runpars_d = {
 
        #=======================================================================
        # 'LML.b4.extrap':{
        #     'gPars_d':{
        #         'mutEx':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\CanFlood_LML.bs4_mutEx.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\extrap.05\r2_mutEx\risk2_LML.bs4.mutEx_b4.mutEx_ttl.csv',
        #             },
        #         'max':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\CanFlood_LML.bs4_max.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\extrap.05\r2_max\risk2_LML.bs4.max_b4.max_ttl.csv',
        #             },
        #         'indep':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\CanFlood_LML.bs4_indep.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\extrap.05\r2_indep\risk2_LML.bs4.indep_b4.indep_ttl.csv',
        #             },
        #         },
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\extrap.05\compare',
        #     'basev':1, 'dfmt':'{:.2e}',
        #         },
        #=======================================================================
        #=======================================================================
        # 
        # 'LML.b4':{
        #     'gPars_d':{
        #         'mutEx':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\CanFlood_LML.bs4_mutEx.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\none.none\r2_mutEx\risk2_LML.bs4.mutEx_b4.mutEx_ttl.csv',
        #             },
        #         'max':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\CanFlood_LML.bs4_max.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\none.none\r2_max\risk2_LML.bs4.max_b4.max_ttl.csv',
        #             },
        #         'indep':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\CanFlood_LML.bs4_indep.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\none.none\r2_indep\risk2_LML.bs4.indep_b4.indep_ttl.csv',
        #             },
        #         },
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs4\b_aoi01_01\none.none\compare',
        #     'basev':1, 'dfmt':'{:.2e}',
        #         },
        #=======================================================================
        
        #=======================================================================
        # 'LML.b5.none':{
        #     'gPars_d':{
        #         'mutEx':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\CanFlood_LML.bs5_mutEx.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\none.none\r2_mutEx\risk2_LML.bs5.mutEx_b5.mutEx_ttl.csv',
        #             },
        #         'max':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\CanFlood_LML.bs5_max.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\none.none\r2_max\risk2_LML.bs5.max_b5.max_ttl.csv',
        #             },
        #         'indep':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\CanFlood_LML.bs5_indep.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\none.none\r2_indep\risk2_LML.bs5.indep_b5.indep_ttl.csv',
        #             },
        #         },
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\none.none\compare',
        #     'basev':1, 'dfmt':'{:.2e}',
        #         },
        #=======================================================================
        
        #=======================================================================
        # 'LML.b5.extrap':{
        #     'gPars_d':{
        #         'mutEx':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\CanFlood_LML.bs5_mutEx.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\extrap.05\r2_mutEx\risk2_LML.bs5.mutEx_b5.mutEx_ttl.csv',
        #             },
        #         'max':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\CanFlood_LML.bs5_max.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\extrap.05\r2_max\risk2_LML.bs5.max_b5.max_ttl.csv',
        #             },
        #         'indep':{
        #             'cf_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\CanFlood_LML.bs5_indep.txt',
        #             'ttl_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\extrap.05\r2_indep\risk2_LML.bs5.indep_b5.indep_ttl.csv',
        #             },
        #         },
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs5\b01_a1\extrap.05\compare',
        #     'basev':1, 'dfmt':'{:.2e}',
        #         }
        #=======================================================================
        
        'tut2c':{
            'fps_d':{ #adding keys here... but the worker take a FP list and reads the tags from the control file
                'mutEx':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\CanFlood_tut2c.txt',
                'max':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\CanFlood_tut2c_max.txt'
                    },
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c\dev\cmpre',
                }
        
        }#close runPars
        

 
    start =  datetime.datetime.now()
    print('start at %s'%start)
    

    
    out_dir = r'C:\Users\cefect\CanFlood\results\compare\out'
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
      


    #plot_single(out_dir)
    out_dir = compareGroup(runpars_d)
    
    force_open_dir(out_dir)
 

    print('finished in %s'%(datetime.datetime.now() - start))
          
          
          
          
          
          
          
          
          
          