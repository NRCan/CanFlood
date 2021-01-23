'''
Created on Dec. 14, 2020

@author: cefect

test some raster functions
'''
import os, datetime
from qgis.core import QgsCoordinateReferenceSystem, QgsDataSourceUri, QgsRasterLayer,\
    QgsRectangle


from hlpr.logr import basic_logger
mod_logger = basic_logger() 
    
    
from hlpr.Q import Qcoms, vlay_write
from hlpr.basic import force_open_dir


def local_raster_copy(
        tag='local_raster_copy',
        out_dir = None,
        
        ):
    

    
    crs = QgsCoordinateReferenceSystem('EPSG:3978')
    
    
    
    #===========================================================================
    # setup
    #===========================================================================
    wrkr = Qcoms(logger=mod_logger, tag=tag, out_dir=out_dir).ini_standalone()
    
    
    
    
    
    #===========================================================================
    # load a rastesr layer
    #===========================================================================
    

    #load from file
    rlayRaw_fp = r'C:\Users\cefect\CanFlood\GAR15\from_local\GAR15_1000y_4326.tif'
    rlayRaw = wrkr.load_rlay(rlayRaw_fp)
    extents='layer'
    
 
    #load from WCS
    #GAR2015:flood_hazard_1000_yrp layer parameters
    
    pars_d = {
        'url':r'http://preview.grid.unep.ch/geoserver/wcs?bbox%3D-179,-45,180,124%26styles%3D%26version%3D1.0.0%26coverage%3DGAR2015:flood_hazard_1000_yrp%26width%3D640%26height%3D309%26crs%3DEPSG:4326',
        'cache':'AlwaysNetwork',
        'crs':'EPSG:4326',
        'dpiMode':'all',
        'format':'GeoTIFF',
        'identifier':'GAR2015:flood_hazard_1000_yrp',
        }
    
    #build uI of thiese
    uriW = QgsDataSourceUri()
    for pName, pValue in pars_d.items():
        uriW.setParam(pName, pValue)
    
    uri = str(uriW.encodedUri(), 'utf-8') #get encoded string of this uri
        
    #uri = r'dpiMode=all&identifier=GAR2015:flood_hazard_1000_yrp&url=http://preview.grid.unep.ch/geoserver/wcs?bbox%3D-180,-89,180,84%26styles%3D%26version%3D1.0.0%26coverage%3DGAR2015:flood_hazard_1000_yrp%26width%3D640%26height%3D309%26crs%3DEPSG:4326'
        
    rlayRaw = QgsRasterLayer(uri, 'GAR15_1000yr_WCS','wcs')
       
    print('loaded \'%s\' w/ \n    extents:%s \n    crs:%s'%(
        rlayRaw.name(), rlayRaw.extent(), rlayRaw.crs()))
       
    extents =  QgsRectangle(-127.6, 44.1, -106.5, 54.1)
     
    rlayRaw.providerType()

    dp = rlayRaw.dataProvider()
    dp.sourceDataType(1)
    #===========================================================================
    # make copy
    #===========================================================================
    
    out_fp1 = wrkr.write_rlay(rlayRaw, 
                    extent=extents, newLayerName='%s_Local'%rlayRaw.name(),
                    )
    
    #===========================================================================
    # reproject
    #===========================================================================
    rlayLocal = wrkr.load_rlay(out_fp1)
    
    assert rlayRaw.bandCount()==rlayLocal.bandCount(), 'band count mismatch!'
    
    ofp2 = os.path.join(out_dir, '%s_Local_%s.tif'%(rlayRaw.name(), crs.authid()[5:]))
    
    rlayLocal_proj = wrkr.warpreproject(rlayLocal, crsOut = crs, output=ofp2)
    
    
    #save it
    #out_fp2 = wrkr.write_rlay(rlayLocal_proj, newLayerName='%s_Local_%s'%(rlayRaw.name(), crs.authid()[5:]))
    
    
    #print('finished w/ \n    %s'%out_fp2)
    
    return ofp2

def rsamps(
        out_dir,
        ):
    
    write_vlay=True


    #===========================================================================
    # tutorial 1 (points)
    #===========================================================================
    #===========================================================================
    # data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1\data'
    #  
    # raster_fns = ['haz_1000yr_cT2.tif', 'haz_1000yr_fail_cT2.tif', 'haz_100yr_cT2.tif', 
    #               'haz_200yr_cT2.tif','haz_50yr_cT2.tif']
    #  
    #  
    #  
    # finv_fp = os.path.join(data_dir, 'finv_cT2b.gpkg')
    #  
    # cf_fp = os.path.join(data_dir, 'CanFlood_control_01.txt')
    #  
    #  
    # cid='xid'
    # tag='tut1'
    # as_inun=False
    # dtm_fp, dthresh = None, None
    #===========================================================================
    
    #===========================================================================
    # tutorial 2  
    #===========================================================================
#===============================================================================
#     data_dir = r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\data'
# 
#     finv_fp = os.path.join(data_dir, 'finv_cT2.gpkg')
#     
#     raster_fns = [
#         'haz_1000yr_cT2.tif',
#         'haz_1000yr_fail_cT3.tif',
#         'haz_100yr_cT2.tif',
#         'haz_200yr_cT2.tif',
#         'haz_50yr_cT2.tif',
#         ]
# 
#      
#     cid='xid'
#     tag='tut2'
#     as_inun=False
#     dtm_fp, dthresh = None, None
#===============================================================================
    
    #==========================================================================
    # tutorial 4a (polygons as inundation)--------
    #==========================================================================
     
    #===========================================================================
    #  
    # data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\4\data'
    #        
    # raster_fns = [
    #              'haz_1000yr_cT2.tif', 
    #               'haz_100yr_cT2.tif', 
    #               'haz_200yr_cT2.tif',
    #               'haz_50yr_cT2.tif',
    #               ]
    #       
    #       
    #         
    # finv_fp = os.path.join(data_dir, 'finv_tut4.gpkg')
    # 
    #       
    # #inundation sampling
    # dtm_fp = os.path.join(data_dir, 'dtm_cT1.tif')
    # as_inun=True
    # dthresh = 0.5
    #       
    # cid='xid'
    # tag='tut4a'
    #  
    #===========================================================================
    #===========================================================================
    # tutorial 4b (inundation of lines)---------
    #===========================================================================
  #=============================================================================
  #   data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\4\data'
  #   raster_fns = [
  #                'haz_1000yr_cT2.tif', 
  #                 'haz_100yr_cT2.tif', 
  #                 'haz_200yr_cT2.tif',
  #                 'haz_50yr_cT2.tif',
  #                 ]
  #      
  #   finv_fp = os.path.join(data_dir, 'finv_tut5_lines.gpkg')
  # 
  # 
  #      
  #   #inundation sampling
  #   dtm_fp = os.path.join(data_dir, 'dtm_cT1.tif')
  #   as_inun=True
  #   dthresh = 2.0
  #       
  #   cid='xid'
  #   tag='tut4b'
  #=============================================================================
  
    #===========================================================================
    # tutorial 5b: GAR15  from local
    #===========================================================================
    data_dir = r'C:\Users\cefect\CanFlood\GAR15\from_local'

    finv_fp = r'C:\Users\cefect\CanFlood\GAR15\finv_NPRI_3978.gpkg'
    
    raster_fns = [
        'GAR15_500y_4326.tif',
        'GAR15_1000y_4326.tif',
        ]

    aoi_fp = os.path.join(data_dir, 'tut5_aoi_3978.gpkg')
    
    cid='xid'
    tag='transf'

    as_inun=False
    dtm_fp, dthresh, clip_dtm = None, None, False
    

     

    #===========================================================================
    # build directories
    #===========================================================================

    raster_fps = [os.path.join(data_dir, fn) for fn in raster_fns]

    #===========================================================================
    #run--------
    #===========================================================================

    
    from build.rsamp import Rsamp
    wrkr = Rsamp(logger=mod_logger, tag=tag, out_dir=out_dir, cid=cid, LogLevel=20
                 ).ini_standalone(
                     crs = QgsCoordinateReferenceSystem('EPSG:3978'))
    
    #==========================================================================
    # load the data
    #==========================================================================
    #mandatory
    rlayRaw_l, finv_vlay = wrkr.load_layers(raster_fps, finv_fp)
    
    #optionals
    if not dtm_fp is None:
        dtm_rlay = wrkr.load_rlay(dtm_fp)
    else:
        dtm_rlay = None
        
    if not aoi_fp is None:
        aoi_vlay = wrkr.load_vlay(aoi_fp)
    else:
        aoi_vlay = None
    
    #==========================================================================
    # execute
    #==========================================================================
    #prep
    rlayPrep_l = wrkr.runPrep(rlayRaw_l,
                    aoi_vlay = aoi_vlay, #if passed, slice rasters to this AOI (finv should already be sliced)
                    clip_rlays=True,
                    allow_download = True, #whether to allow downloading of non-gdal dataProviders
                    allow_rproj = True,
                    scaleFactor = .01, #factor to apply to all raster values 
            )
    
    res_vlay = wrkr.run(rlayPrep_l, finv_vlay, 
                        
            cid = cid, #index field name on finv
                        
            #exposure value controls
            psmp_stat='Max', #for polygon finvs, statistic to sample
            
            #inundation sampling controls
            as_inun=as_inun, #whether to sample for inundation (rather than wsl values)
            dtm_rlay=dtm_rlay, #dtm raster
            dthresh = dthresh, #fordepth threshold
            clip_dtm=clip_dtm,

             )
       
    wrkr.check()

    #==========================================================================
    # save results
    #==========================================================================
    outfp = wrkr.write_res(res_vlay) #write csv dataset
    if write_vlay:
        ofp = os.path.join(out_dir, res_vlay.name()+'.gpkg')
        vlay_write(res_vlay,ofp, overwrite=True)
     
    #wrkr.upd_cf(cf_fp)



if __name__ =="__main__": 
    start =  datetime.datetime.now()
    print('start at %s'%start)
    
    from qgis.core import Qgis
    Qgis.Critical
    
    out_dir = os.path.join(r'C:\Users\cefect\CanFlood\GAR15', 'rsamps')
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)
      
    #local_raster_copy(out_dir=out_dir)
    rsamps(out_dir)
    
    force_open_dir(out_dir)
 
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)