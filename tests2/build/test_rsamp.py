'''
Created on Apr. 1, 2023

@author: cefect

testing build raster sampling backends (build.rsamp)
'''

import pytest, os, shutil
from qgis.core import QgsVectorLayer, QgsRasterLayer
from build.rsamp import Rsamp
from definitions import src_dir
#===============================================================================
# test data
#===============================================================================

test_dir = os.path.join(src_dir, r'tests2\data\build\rsamp')

proj_dir = {
    'ip1':{
        'dir':os.path.join(test_dir, 'inun_poly_20230401'),
        'rlay_fp_l':[
            #'g214_WSE_0010_OW1.tif', 'g214_WSE_0020_OW1.tif', 
            'g214_WSE_0035_OW1.tif', 
            #'g214_WSE_0050_OW1.tif',
            ],
        'finv_fp':'copy_park_inv.gpkg',
        'dem_fp':'dem_clip_r1.tif',
        'run_kwargs':dict(dthresh=0.3, as_inun=True),
        }
    }

#make absolute
for k0, d0 in proj_dir.copy().items():
    diri = d0['dir']
    assert os.path.exists(diri), k0
    
    k1 = 'rlay_fp_l'    
    proj_dir[k0][k1]=[os.path.join(diri, fname) for fname in d0[k1]]
    
    for k1 in ['finv_fp', 'dem_fp']:
        proj_dir[k0][k1] = os.path.join(diri, proj_dir[k0][k1])
 
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


@pytest.mark.dev 
@pytest.mark.parametrize('projName',[
    'ip1', #build.rsamp.Rsamp.samp_inun()
    ], indirect=True)
def test_build_rsamp_run(wrkr, rlayRaw_l, finv_rlay, dem_rlay, run_kwargs):
    wrkr.set_crs(crs=finv_rlay.crs())
    wrkr.run(rlayRaw_l, finv_rlay, dtm_rlay=dem_rlay, **run_kwargs)
    
    #validate
    res_df = wrkr.res_df.copy()
    
    print(wrkr.out_dir)
