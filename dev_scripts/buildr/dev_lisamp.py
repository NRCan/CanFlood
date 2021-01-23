'''
Created on Dec. 17, 2020

@author: cefect
'''
import os, datetime

from qgis.core import QgsCoordinateReferenceSystem

from hlpr.logr import basic_logger
mod_logger = basic_logger() 

from build.lisamp import LikeSampler
from hlpr.basic import force_open_dir
from hlpr.Q import vlay_write


def generic(runPars_d,
            out_dir = None):
    
    
    
    for tag, pars in runPars_d.items():
        
        #=======================================================================
        # setup run
        #=======================================================================
        log = mod_logger.getChild(tag)
        
        if 'out_dir' in pars: out_dir = pars['out_dir']

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        
        wrkr = LikeSampler(logger=log, tag=tag, out_dir=out_dir, cid=pars['cid'],
                           prec=4).ini_standalone(
                               crs=QgsCoordinateReferenceSystem(pars['crs_id'])) #setup for a standalone run
        
        
        
        #==========================================================================
        # load the data
        #==========================================================================
        #load the aoi
        aoi_vlay = wrkr.load_vlay(pars['aoi_fp'])
        #load the finv (and slice)
        finv_vlay = wrkr.load_vlay(pars['finv_fp'], aoi_vlay=aoi_vlay)
        #load lpols
        lpol_d = wrkr.load_lpols(pars['lpol_fn_d'], basedir=pars['lpol_basedir'])

        #==========================================================================
        # execute
        #==========================================================================
        res_df = wrkr.run(finv_vlay, lpol_d, event_rels=pars['event_rels'])
        
        #plot histogram
        fig = wrkr.plot_box_all(res_df)
        wrkr.output_fig(fig)
        
        #convet to a vector
        res_vlay = wrkr.vectorize(res_df)
        
        
        wrkr.check()
        
        #==========================================================================
        # save results
        #==========================================================================
        vlay_write(res_vlay, 
                   os.path.join(wrkr.out_dir, '%s.gpkg'%wrkr.resname),
                   overwrite=True, logger=mod_logger)
        
        out_fp = wrkr.write_res(res_df)
        
        log.info('finished')
        
    return out_dir

    
    

    
    


if __name__ =="__main__": 
    
    runPars_d={
        #=======================================================================
        # 'dev2':{
        #     'data_dir':r'C:\Users\cefect\CanFlood\lisamp',
        #     'finv_fn':'finv_cT2.gpkg',
        #     #'out_dir':os.path.join(os.getcwd(), 'risk2', 'Tut2'),
        #     'cf_fn':'CanFlood_tut2b.txt',
        #     
        #     'lpol_fn_d':{
        #         'haz_1000yr_fail_cT3.tif':'exlikes_1000yr_cT2.gpkg', 
        #         },
        #     'crs_id':'EPSG:3005',
        #     'absolute_fp':False,
        #     },
        #=======================================================================
        'LMFRA.bldgs.sfd3':{
            'crs_id':'EPSG:3005','cid':'zid2', 'felv':'datum',
            'aoi_fp':r'C:\Users\cefect\CanFlood\LMFRA\bldgs.sfd3\aoi02.gpkg',
            'finv_fp':r'C:\Users\cefect\CanFlood\LMFRA\bldgs.sfd3\finv_tagSFD_20200608_pts.gpkg',
            
            'lpol_fn_d':{
                #'AG4_Fr_0010_WL_fail_0415':'AG4_Fr_0010_Ind_Bd_0415c.gpkg',
                #'AG4_Fr_0030_WL_fail_0415':'AG4_Fr_0030_Ind_Bd_0415c.gpkg',
                #'AG4_Fr_0050_WL_fail_0415':'AG4_Fr_0050_Ind_Bd_0415c.gpkg',
                #'AG4_Fr_0100_WL_fail_0415':'AG4_Fr_0100_Ind_Bd_0415c.gpkg',
                'AG4_Fr_0200_WL_fail_0415':'AG4_Fr_0200_Ind_Bd_0415c.gpkg',
                'AG4_Fr_0500_WL_fail_0415':'AG4_Fr_0500_Ind_Bd_0415c.gpkg',
                'AG4_Fr_0750_WL_fail_0415':'AG4_Fr_0750_Ind_Bd_0415c.gpkg',
                'AG4_Fr_1000_WL_fail_0415':'AG4_Fr_1000_Ind_Bd_0415c.gpkg'
                },
            'lpol_basedir':r'C:\LS\03_TOOLS\LML\_ins2\cf\amodel\haz\freshet\pFail',
            'lfield':'p_fail2','event_rels':'indep'
            }
        }
        
        
    start =  datetime.datetime.now()
    print('start at %s'%start)
    

    

      
    

    #test1(out_dir)
    out_dir = generic(runPars_d, 
            out_dir = r'C:\Users\cefect\CanFlood\LMFRA\bldgs.sfd3\outs',
            )
    
    force_open_dir(out_dir)
 

    print('finished in %s'%(datetime.datetime.now() - start))