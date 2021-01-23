'''
Created on Dec. 17, 2020

@author: cefect

building a complete L2 model from scratch
'''
import os, datetime, configparser
from shutil import copyfile

from qgis.core import QgsCoordinateReferenceSystem

start =  datetime.datetime.now()
print('start at %s'%start)

from hlpr.logr import basic_logger
mod_logger = basic_logger() 


from hlpr.basic import force_open_dir
from build.prepr import Preparor
from build.rsamp import Rsamp
from build.lisamp import LikeSampler
from build.validator import Vali



class MasterBuilder(#combine all the build workers for a single run
        Preparor, Rsamp, LikeSampler, Vali):
    """
    needed to avoid reinitilziing qgis each time
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.baseClassConv_d = self.get_baseClassConv_d()
        
    def get_baseClassConv_d(self):
        
        baseClassConv_d = dict()
        first=True
        last=None
        for baseClass in self.__class__.__mro__:
            bcName = baseClass.__name__
            if first:
                first=False
            else:
                baseClassConv_d[bcName]=last
            
            last = baseClass
            
        return baseClassConv_d


def build( #generic runner for the risk1 model
            runpars_d,
    ):

    #==========================================================================
    # build/execute
    #==========================================================================
    first = True
    for tag, pars in runpars_d.items():
        log = mod_logger.getChild(tag)
        
        #pull form parameters
        out_dir, cid = pars['out_dir'], pars['cid']

        #paths
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        #=======================================================================
        # start worker
        #=======================================================================
        if first:
            wrkr = MasterBuilder(logger=log,  out_dir=out_dir, tag=tag, cid=cid,
                            ).ini_standalone(
                                crs=QgsCoordinateReferenceSystem(pars['crs_id']))
            first=False
            
        #try and recycle
        else:
            wrkr.log=log
            wrkr.out_dir=out_dir
            wrkr.tag=tag
            wrkr.cid=cid
            wrkr.crs=QgsCoordinateReferenceSystem(pars['crs_id'])

        #=======================================================================
        # prepare
        #=======================================================================
        wrkrPR = super(wrkr.baseClassConv_d['Preparor'], wrkr) #get a special worker
        #copy the template
        cf_fp = wrkrPR.copy_cf_template(out_dir)
        
        #set some basics
        if not 'curves_fp' in pars: pars['curves_fp'] = None #add a dummy
        wrkrPR.upd_cf_first(curves_fp = pars['curves_fp'])
            
        log.info('control file created: %s'%cf_fp)
        
        
        #=======================================================================
        # convert_finv
        #=======================================================================
        #load the aoi
        if 'aoi_fp' in pars:
            aoi_vlay = wrkrPR.load_vlay(pars['aoi_fp'])
        else:
            aoi_vlay=None
            
        #load the finv
        finv_vlay = wrkrPR.load_vlay(pars['finv_fp'], aoi_vlay=aoi_vlay)
        #convert
        wrkrPR.finv_to_csv(finv_vlay, felv=pars['felv'])
        del wrkrPR
        #=======================================================================
        # sample hazard rasters
        #=======================================================================
        wrkrHR = super(wrkr.baseClassConv_d['Rsamp'], wrkr) #get a special worker
        #load rasters
        rlay_d = wrkrHR.load_rlays(pars['raster_dir'])
                            
        #execute the tool
        res_vlay = wrkrHR.run(list(rlay_d.values()), finv_vlay)
    
        #post
        wrkrHR.check()
        wrkrHR.write_res(res_vlay) #save csv results to file
        wrkrHR.upd_cf(cf_fp) #update ocntrol file
        
        #=======================================================================
        # DTM
        #=======================================================================
        if 'dtm_fp' in pars:

            dtm_vlay = wrkrHR.load_rlay(pars['dtm_fp'])
            res_vlay = wrkrHR.run([dtm_vlay], finv_vlay, fname='gels')
            wrkrHR.dtm_check(res_vlay)
            wrkrHR.write_res(res_vlay)
            wrkrHR.upd_cf_dtm()
        
        del wrkrHR
         
        #=======================================================================
        # event variables
        #=======================================================================
        assert os.path.exists(pars['evals_fp']), pars['evals_fp']
        wrkr.update_cf(
            {
                'parameters':({'event_probs':'ari'},),
                'risk_fps':({'evals':pars['evals_fp']},)                          
             }
            )
        
        #=======================================================================
        # conditionals 
        #=======================================================================
        if 'lpol_fn_d' in pars:
            wrkrLS = super(wrkr.baseClassConv_d['LikeSampler'], wrkr) #get a special worker
              
            #load lpols
            lpol_d = wrkrLS.load_lpols(pars['lpol_fn_d'], basedir=pars['lpol_basedir'])
              
            #run it      
            res_df = wrkrLS.run(finv_vlay, lpol_d, cid=cid, 
                                lfield=pars['lfield'], event_rels=pars['event_rels'])          
            #post
            wrkrLS.check()
            wrkrLS.write_res(res_df, out_dir = out_dir)
            wrkrLS.upd_cf(cf_fp)
            
            #plot
            fig = wrkrLS.plot_hist_all(res_df)
            wrkrLS.output_fig(fig)
            
            fig = wrkrLS.plot_box_all(res_df)
            wrkrLS.output_fig(fig)
            del wrkrLS
        #=======================================================================
        # validator
        #=======================================================================
        wrkrVA =  super(wrkr.baseClassConv_d['Vali'], wrkr) #get a special worker
        from model.risk1 import Risk1
        from model.risk2 import Risk2
        from model.dmg2 import Dmg2
        
        wrkrVA.config_cf() #initlize the parser
        
        #loop and check each model
        for vtag, modObj in {
            'risk1':Risk1, 
            'risk2':Risk2,
            'dmg2':Dmg2,
            }.items():
            
            if vtag in pars['validate']:
            
                errors = wrkrVA.cf_check(modObj)
                assert len(errors)==0, '\'%s\' got some errors \n    %s'%(vtag, errors)
                #update control file
                wrkr.cf_mark()
            
        del wrkrVA
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished building')
    
    log.info('wrap w/ %s'%out_dir)
 
    return out_dir
    


    


if __name__ =="__main__": 
    
    #===========================================================================
    # run parameters
    #===========================================================================
    runPars_d2={

        
        #=======================================================================
        # 'Lbs6.mut':{
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b01',
        #     'crs_id':'EPSG:3005', 'cid':'zid2', 'felv':'datum',
        #     
        #     'aoi_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\aoi01.gpkg',
        #     'finv_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\finv_tagSFD_20200608_pts.gpkg',
        #     'curves_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\curves_CFcc_20200608_sfd.xls',
        #     'raster_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\rlays',
        #     'dtm_fp':r'C:\LS\02_WORK\IBI\201909_FBC\02_INFO\DTM\NHC_2019_dtm_lores_aoi05h.tif',
        #     'evals_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\evals_fresh_20200603.csv',
        #     
        #     #LikeSampler
        #     'lpol_fn_d':{
        #         'AG4_Fr_0010_WL_fail_0415':'AG4_Fr_0010_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0030_WL_fail_0415':'AG4_Fr_0030_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0050_WL_fail_0415':'AG4_Fr_0050_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0100_WL_fail_0415':'AG4_Fr_0100_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0200_WL_fail_0415':'AG4_Fr_0200_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0500_WL_fail_0415':'AG4_Fr_0500_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0750_WL_fail_0415':'AG4_Fr_0750_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_1000_WL_fail_0415':'AG4_Fr_1000_Ind_Bd_0415c.gpkg'
        #         },
        #     'lpol_basedir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\lpols',
        #     'lfield':'p_fail2', 'event_rels':'mutEx'
        #     },
        #=======================================================================
        
        #=======================================================================
        # 'LML.bs7':{
        #     'out_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\b03',
        #     'crs_id':'EPSG:3005', 'cid':'zid2', 'felv':'datum',
        # 
        #     'aoi_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\aoi05.gpkg',
        #      'finv_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\finv_tagSFD_20200608_pts.gpkg',
        #      'curves_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\curves_CFcc_20200608_sfd.xls',
        #     'raster_dir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\rlays',
        #      'dtm_fp':r'C:\LS\02_WORK\IBI\201909_FBC\02_INFO\DTM\NHC_2019_dtm_lores_aoi05h.tif',
        #      'evals_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\evals_fresh_20200603.csv',
        # 
        #     #LikeSampler
        #     'lpol_fn_d':{
        #         'AG4_Fr_0010_WL_fail_0415':'AG4_Fr_0010_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0030_WL_fail_0415':'AG4_Fr_0030_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0050_WL_fail_0415':'AG4_Fr_0050_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0100_WL_fail_0415':'AG4_Fr_0100_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0200_WL_fail_0415':'AG4_Fr_0200_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0500_WL_fail_0415':'AG4_Fr_0500_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_0750_WL_fail_0415':'AG4_Fr_0750_Ind_Bd_0415c.gpkg',
        #         'AG4_Fr_1000_WL_fail_0415':'AG4_Fr_1000_Ind_Bd_0415c.gpkg'
        #         },
        #     'lpol_basedir':r'C:\Users\cefect\CanFlood\LMFRA\bs7\lpols',
        #     'lfield':'p_fail2', 'event_rels':'indep'
        #     },
        #=======================================================================
        
        #=======================================================================
        # 'tut2a':{
        #     'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a',
        #     'crs_id':'EPSG:3005', 'cid':'xid', 'felv':'ground','validate':'dmg2',
        #     
        #     #'aoi_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\aoi05.gpkg',
        #      'finv_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\finv_cT2.gpkg',
        #      'curves_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\CanFlood_curves_rfda_20200218.xls',
        #     'raster_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\rlays',
        #      'dtm_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\dtm_cT1.tif',
        #      'evals_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\evals_4_tut2a.csv',
        #     },
        #=======================================================================
         
        #=======================================================================
        # 'tut2b':{
        #     'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\b',
        #     'crs_id':'EPSG:3005', 'cid':'xid', 'felv':'ground','validate':'dmg2',
        #   
        #     #'aoi_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\aoi05.gpkg',
        #      'finv_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\finv_cT2.gpkg',
        #      'curves_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\CanFlood_curves_rfda_20200218.xls',
        #     'raster_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\rlays',
        #      'dtm_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\dtm_cT1.tif',
        #      'evals_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\evals_4_tut2a.csv',
        #        
        #      #LikeSampler
        #     'lpol_fn_d':{
        #         'haz_1000yr_fail_A_cT4':'expoProbPoly_1000yr_A_T2d.gpkg',
        #         },
        #      
        #     'lpol_basedir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\lpols',
        #     'lfield':'p_fail', 'event_rels':'mutEx'
        #     },
        #=======================================================================

        
        'tut2c':{
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\c',
            'crs_id':'EPSG:3005', 'cid':'xid', 'felv':'ground','validate':'dmg2',
         
            #'aoi_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\aoi05.gpkg',
             'finv_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\finv_cT2.gpkg',
             'curves_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\CanFlood_curves_rfda_20200218.xls',
            'raster_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\rlays',
             'dtm_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\dtm_cT1.tif',
             'evals_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\evals_4_tut2c.csv',
              
             #LikeSampler
            'lpol_fn_d':{
                'haz_1000yr_fail_A_cT4':'expoProbPoly_1000yr_A_T2d.gpkg',
                'haz_1000yr_fail_B_cT4':'expoProbPoly_1000yr_B_T2d.gpkg',
                },
            'lpol_basedir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\lpols',
            'lfield':'p_fail', 
            'event_rels':'mutEx', #just for likesamp... need to set another flag in the CF for Risk
            }
 
        }
    
    runPars_d1={
        'tut1a':{
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\1a',
            'crs_id':'EPSG:3005', 'cid':'xid', 'felv':'datum','validate':'risk1',
              
            #'aoi_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\aoi05.gpkg',
            'finv_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\data\finv_cT2b.gpkg',
  
            'raster_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\data',
            #'dtm_fp':r'C:\LS\02_WORK\IBI\201909_FBC\02_INFO\DTM\NHC_2019_dtm_lores_aoi05h.tif',
            'evals_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\1a\evals_4_tut1a.csv',
            },
        'tut1b':{
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\1b',
            'crs_id':'EPSG:3005', 'cid':'xid', 'felv':'datum','validate':'risk1',
             
            #'aoi_fp':r'C:\Users\cefect\CanFlood\LMFRA\bs7\aoi05.gpkg',
            'finv_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\data\finv_cT2b.gpkg',
 
            'raster_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\data',
            #'dtm_fp':r'C:\LS\02_WORK\IBI\201909_FBC\02_INFO\DTM\NHC_2019_dtm_lores_aoi05h.tif',
            'evals_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\1b\evals_5_tut1b.csv',
            
            #LikeSampler
            'lpol_fn_d':{
                'haz_1000yr_fail_cT2':'exlikes_1000yr_cT2.gpkg',
                },
            'lpol_basedir':r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\data',
            'lfield':'p_fail', 'event_rels':'indep'
             
            },
        
        }
    

      
    #===========================================================================
    # run
    #===========================================================================
    #out_dir = build(runPars_d1)
    out_dir = build(runPars_d2)
    
    
    #===========================================================================
    # wrap
    #===========================================================================
    force_open_dir(out_dir)
 
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)