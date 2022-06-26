'''
Created on Jun. 24, 2022

@author: cefect

tutorial 2 integration tests
'''

import pytest, os, shutil

import pandas as pd

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt

from build.dialog import BuildDialog

@pytest.fixture(scope='module')
def crs():
    return QgsCoordinateReferenceSystem('EPSG:3005')

@pytest.fixture(scope='module')
def data_dir(base_dir):
    return os.path.join(base_dir, r'tutorials\2')
    



@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
def test_01_build(session, data_dir):
    dial = session.Dialog
    
    #===========================================================================
    # scenario setup
    #===========================================================================
    dial._change_tab('tab_setup')
    dial.lineEdit_wdir.setText(str(session.out_dir))
    dial.linEdit_ScenTag.setText('tut2a')
    
    """BuildDialog.build_scenario()"""
    QTest.mouseClick(dial.pushButton_generate, Qt.LeftButton)

    assert os.path.exists(dial.lineEdit_cf_fp.text())
    
    #===========================================================================
    # Inventory setup
    #===========================================================================
    dial._change_tab('tab_inventory')
    
    #select the finv
    fp = os.path.join(data_dir, 'finv_tut2.gpkg')
    finv_vlay = session.load_vlay(fp)
    dial.comboBox_ivlay.setLayer(finv_vlay)
    
    #indeix field name
    dial.mFieldComboBox_cid.setField('xid')
    
    dial.comboBox_SSelv.setCurrentIndex(1) #ground
    
    #click Store
    QTest.mouseClick(dial.pushButton_Inv_store, Qt.LeftButton)
    
    
    #check it
    #retrieve the filepath from the control file
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='dmg_fps', varName='finv')
    assert os.path.exists(fp)
    
    df = pd.read_csv(fp)
    assert len(df)==finv_vlay.dataProvider().featureCount()
 
    #===========================================================================
    # Select Vulnerability Function Set
    #===========================================================================
    
    """too tricky to use this UI. should add at somepoint though
    QTest.mouseClick(dial.pushButton_inv_vfunc, Qt.LeftButton)"""
    
    #specify curves
    raw_fp = os.path.join(session.pars_dir, 'vfunc\IBI_2015\IBI2015_DamageCurves.xls')
    
    #copy over
    ofp = os.path.join(session.out_dir, os.path.basename(raw_fp))
    shutil.copy2(raw_fp,ofp)
    
    #update the gui
    dial.lineEdit_curve.setText(ofp)
    
    #check
    assert os.path.exists(dial.lineEdit_curve.text())
    
    #purge it
    QTest.mouseClick(dial.pushButton_Inv_purge, Qt.LeftButton)
    
    #update control file
    QTest.mouseClick(dial.pushButton_Inv_curves, Qt.LeftButton)
    
    #===========================================================================
    # hazard sampler
    #===========================================================================
    dial._change_tab('tab_HazardSampler')
    
    #load rasters
    lay_d = session.load_layers_dirs([os.path.join(data_dir, 'haz_rast')])
    
    QTest.mouseClick(dial.pushButton_expo_refr, Qt.LeftButton) #refresh
    QTest.mouseClick(dial.pushButton_expo_sAll, Qt.LeftButton) #select All
    QTest.mouseClick(dial.pushButton_HSgenerate, Qt.LeftButton) #sample
    
    #check it
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='dmg_fps', varName='expos')
    assert os.path.exists(fp)
    
    df = pd.read_csv(fp, index_col=0)
    assert len(df)==finv_vlay.dataProvider().featureCount()
    assert len(df.columns)==len(lay_d)
    
    #===========================================================================
    # event variables
    #===========================================================================
    dial._change_tab('tab_eventVars')
    
    
        
    
    
    
    
    
    

 
    
 