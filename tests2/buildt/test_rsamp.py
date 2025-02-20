'''
Created on Apr. 1, 2023

@author: cefect

testing build raster sampling backends (build.rsamp)
'''

import pytest, os, shutil
from qgis.core import QgsVectorLayer, QgsRasterLayer,QgsCoordinateReferenceSystem
import pandas as pd
from pandas.testing import assert_frame_equal
import processing


from canflood.build.rsamp import Rsamp
from canflood.hlpr.Q import view
from definitions import test_data_dir
#===============================================================================
# test data
#===============================================================================

test_dir = os.path.join(test_data_dir, r'build\rsamp')

proj_dir = {
    'ip1':{
        'dir':os.path.join(test_dir, 'inun_poly_20230401'),
        'rlay_fp_l':[
            'g214_WSE_0010_OW1.tif', 'g214_WSE_0020_OW1.tif', 
            'g214_WSE_0035_OW1.tif', 
            'g214_WSE_0050_OW1.tif',
            ],
        'finv_fp':'copy_park_inv.geojson',
        'aoi_fp':'aoi_dummy.geojson',
        'dem_fp':'dem_clip_r1.tif',
        'run_kwargs':dict(dthresh=0.3, as_inun=True),
        'test_build_rsamp_run_fp':'test_build_rsamp_run_res_20230401.pkl'
        }
    }

#make absolute
for k0, d0 in proj_dir.copy().items():
    diri = d0['dir']
    assert os.path.exists(diri), k0
    
    k1 = 'rlay_fp_l'    
    proj_dir[k0][k1]=[os.path.join(diri, fname) for fname in d0[k1]]
    
    for k1, v in d0.items():
        if k1.endswith('_fp'):
            proj_dir[k0][k1] = os.path.join(diri, v)
 
#===============================================================================
# helpers
#===============================================================================
def load_rlay(fp):
    assert os.path.exists(fp), fp
    basefn = os.path.splitext(os.path.split(fp)[1])[0]
    return QgsRasterLayer(fp, basefn)

def load_vlay(fp):
    assert os.path.exists(fp), fp
    basefn = os.path.splitext(os.path.split(fp)[1])[0]
    return QgsVectorLayer(fp,basefn,'ogr')
    
    
#===============================================================================
# fixtures-------
#===============================================================================
"""
 ['logger', 'out_dir', 'tag', 'overwrite', 'absolute_fp', 'feedback', 'cf_fp', 'init_q_d', 'cid'])
"""

@pytest.fixture(scope='function')
def wrkr(logger, out_dir, test_name,
         qgis_app, 
        qgis_processing,
        #cf_fp,
        ):
    with Rsamp(
        logger=logger,out_dir=out_dir, tag=test_name, 
        overwrite=True,
        absolute_fp=True,
        qgis_app=qgis_app,
        qgis_processing=True,        
        ) as worker:
        yield worker

#===============================================================================
# data retrival
#===============================================================================
"""pulls from proj_dir using fixtures and projName"""
@pytest.fixture(scope='function')
def projName(request): #always passing this as an indirect
    """just return the parameter"""
    return request.param

@pytest.fixture(scope='function')  
def rlayRaw_l(projName, wrkr):
    #get filepaths
    fp_l = proj_dir[projName]['rlay_fp_l']
    
    #load layers
    l = list()
    for fp in fp_l:
        l.append(load_rlay(fp))    
    
    return l

@pytest.fixture(scope='function')  
def finv_rlay(projName):
    fp =  proj_dir[projName]['finv_fp']
    return load_vlay(fp)


@pytest.fixture(scope='function')  
def aoi_vlay(projName):
    fp =  proj_dir[projName]['aoi_fp']
    return load_vlay(fp)

@pytest.fixture(scope='function')  
def dem_rlay(projName):
    fp = proj_dir[projName]['dem_fp']
    return load_rlay(fp)

@pytest.fixture(scope='function')
def run_kwargs(projName):
    return proj_dir[projName]['run_kwargs']
#===============================================================================
# tests--------
#===============================================================================
def test_init(wrkr):
    pass


 
@pytest.mark.parametrize('projName',[
    'ip1', 
    ], indirect=True)
def test_build_rsamp_run(wrkr, rlayRaw_l, finv_rlay, dem_rlay, run_kwargs, projName): #build.rsamp.Rsamp.samp_inun()
    #run test
    wrkr.set_crs(crs=finv_rlay.crs())
    wrkr.run(rlayRaw_l, finv_rlay, dtm_rlay=dem_rlay, **run_kwargs)
 
    
    #validate
    res_df = wrkr.res_df.copy()
    vali_df = pd.read_pickle(proj_dir[projName]['test_build_rsamp_run_fp'])
    
    assert_frame_equal(res_df, vali_df)
    
    """
    view(res_df)
    res_df.to_pickle(os.path.join(proj_dir[projName]['dir'], 'test_build_rsamp_run_res_20230401.pkl'))
    """

 

@pytest.mark.dev
@pytest.mark.parametrize('projName', ['ip1'], indirect=True)
@pytest.mark.parametrize("clip_rlays, allow_rproj, scaleFactor", [
    (True, False, 1.00),    
    (False, True, 1.00),  
    (False, False, 0.99),    
    (False, False, 1.00),    # All defaults
])
def test_build_rsamp_runPrep(wrkr, rlayRaw_l, aoi_vlay, projName,
                             clip_rlays, allow_rproj, scaleFactor):
 
    

    #===========================================================================
    # prepare reprojected
    #===========================================================================
    if allow_rproj:
        dummy_crs = QgsCoordinateReferenceSystem("EPSG:3857")
        warped_layers = []
        # Set up the parameters for the GDAL warp reprojection.
        params = {
            'DATA_TYPE': 0,
            'EXTRA': '',
            'MULTITHREADING': False,
            'NODATA': None,
            'OPTIONS': '',
            'OUTPUT': 'TEMPORARY_OUTPUT',
            'RESAMPLING': 0,
            'SOURCE_CRS': None,
            'TARGET_CRS': dummy_crs.authid(),  # Use the dummy CRS authid
            'TARGET_EXTENT': None,
            'TARGET_EXTENT_CRS': None,
            'TARGET_RESOLUTION': None,
        }

        for rlay_raw in rlayRaw_l:
            params['INPUT'] = rlay_raw
            layer_name = f"{rlay_raw.name()}_rproj"
            result = processing.run('gdal:warpreproject', params)
            reprojected_layer = QgsRasterLayer(result['OUTPUT'], layer_name)
            # Assert that the reprojected layer's CRS matches the dummy CRS.
            assert reprojected_layer.crs().authid() == dummy_crs.authid(), \
                f"Reprojection failed for {layer_name}"
            warped_layers.append(reprojected_layer)

        # Reset the raster layer list to the warped versions.
        rlayRaw_l = warped_layers

    # Set the worker's CRS to the AOI's CRS.
    wrkr.set_crs(crs=aoi_vlay.crs())
    # Run the preparation process.
    wrkr.runPrep(rlayRaw_l, aoi_vlay=aoi_vlay,
                 clip_rlays=clip_rlays, allow_rproj=allow_rproj, scaleFactor=scaleFactor)

    
    
