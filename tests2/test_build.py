'''
Created on Jun. 24, 2022

@author: cefect

unit tests for CanFlood's 'build' toolset

lets launch one dialog worker per module

one test per button click

see tutorials for integration tests


'''

import pytest, os, shutil

import pandas as pd

from pandas.testing import assert_frame_equal

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

from build.dialog import BuildDialog





@pytest.fixture(scope='module')
def crs():
    return QgsCoordinateReferenceSystem('EPSG:3005')


def test_00_version(qgis_version):
    assert qgis_version==32207, 'bad version: %s'%qgis_version
    

@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
def test_01_build_scenario(session):
    dial = session.Dialog
    dial._change_tab('tab_setup')
    #===========================================================================
    # setup
    #===========================================================================
    dial.linEdit_ScenTag.setText('test_01')
    dial.lineEdit_wdir.setText(str(session.out_dir)) #set the working directory
    #===========================================================================
    # execute
    #===========================================================================
    """BuildDialog.build_scenario()"""
 
    QTest.mouseClick(dial.pushButton_generate, Qt.LeftButton)
 
    #===========================================================================
    # check
    #===========================================================================
    assert os.path.exists(dial.lineEdit_cf_fp.text())
    
 
@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
@pytest.mark.parametrize('finv_fp',[r'tutorials\2\finv_tut2.gpkg'])
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_01_build_scenario_BuildDi0\CanFlood_test_01.txt']) #from test_01
def test_02_build_inv(session, base_dir, finv_fp, cf_fp):
    dial = session.Dialog
    
    #===========================================================================
    # setup
    #===========================================================================
    out_dir = session.out_dir
    cf_fp = build_setup(base_dir, cf_fp, dial, out_dir, testName='test_02')
    
    
    #===========================================================================
    # inventory setup
    #===========================================================================
    #select the finv
    dial._change_tab('tab_inventory')
    finv_vlay = session.load_vlay(os.path.join(base_dir, finv_fp))
    dial.comboBox_ivlay.setLayer(finv_vlay)
    
    #indeix field name
    dial.mFieldComboBox_cid.setField('xid')
    
    dial.comboBox_SSelv.setCurrentIndex(1) #ground
    #===========================================================================
    # execute
    #===========================================================================
    #click Store
    QTest.mouseClick(dial.pushButton_Inv_store, Qt.LeftButton)
 
    #===========================================================================
    # check
    #===========================================================================
    #retrieve the filepath from the control file
    fp = dial.get_cf_par(cf_fp, sectName='dmg_fps', varName='finv')
    assert os.path.exists(fp)
    
    df = pd.read_csv(fp)
    assert len(df)==finv_vlay.dataProvider().featureCount()
    
    
    

@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_02_build_inv_tests2__data0\CanFlood_test_01.txt']) #from test_02
def test_03_build_inv_curves(session, base_dir, cf_fp):
    dial = session.Dialog
 
    #===========================================================================
    # setup
    #===========================================================================
    out_dir = session.out_dir
    cf_fp = build_setup(base_dir, cf_fp, dial, out_dir, testName='test_03')
    
    #===========================================================================
    # setup curves
    #===========================================================================
    dial._change_tab('tab_inventory')
    
    
    raw_fp = os.path.join(session.pars_dir, 'vfunc\IBI_2015\IBI2015_DamageCurves.xls')
    
    #update the gui
    dial.lineEdit_curve.setText(raw_fp)
    #===========================================================================
    # execute
    #===========================================================================
    #purge it
    """BuildDialog.purge_curves()"""
    #dial.purge_curves()
    QTest.mouseClick(dial.pushButton_Inv_purge, Qt.LeftButton)
     
    #update control file
    QTest.mouseClick(dial.pushButton_Inv_curves, Qt.LeftButton)
  
    #===========================================================================
    # check
    #===========================================================================
    #retrieve the filepath from the control file
    fp = dial.get_cf_par(cf_fp, sectName='dmg_fps', varName='curves')
    assert os.path.exists(fp)
    
 
@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_03_build_inv_curves_tests0\CanFlood_test_01.txt']) #from test_03
@pytest.mark.parametrize('finv_fp',[r'tutorials\2\finv_tut2.gpkg'])
@pytest.mark.parametrize('rast_dir',[r'tutorials\2\haz_rast'])
def test_04_build_hsamp(session, base_dir, cf_fp, rast_dir, finv_fp, true_dir):
    dial = session.Dialog
    
    #===========================================================================
    # setup
    #===========================================================================
    out_dir = session.out_dir
    cf_fp = build_setup(base_dir, cf_fp, dial, out_dir, testName='test_04')
    
    #===========================================================================
    # setup finv
    #===========================================================================
    #select the finv
    dial._change_tab('tab_inventory')
    finv_vlay = session.load_vlay(os.path.join(base_dir, finv_fp))
    dial.comboBox_ivlay.setLayer(finv_vlay)
    
    #indeix field name
    dial.mFieldComboBox_cid.setField('xid')
    
    #===========================================================================
    # setup rasters
    #===========================================================================
    dial._change_tab('tab_HazardSampler')
    
    
    #load rasters
    lay_d = session.load_layers_dirs([os.path.join(base_dir, rast_dir)])
    
    QTest.mouseClick(dial.pushButton_expo_refr, Qt.LeftButton) #refresh
    QTest.mouseClick(dial.pushButton_expo_sAll, Qt.LeftButton) #select All
    

    
    #===========================================================================
    # execute
    #===========================================================================
    QTest.mouseClick(dial.pushButton_HSgenerate, Qt.LeftButton) #sample
    
    #===========================================================================
    # load result from control file
    #===========================================================================
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='dmg_fps', varName='expos')
    assert os.path.exists(fp)
    
    df = pd.read_csv(fp, index_col=0)
    
    #===========================================================================
    # load trues
    #===========================================================================
    
    true_fp = os.path.join(true_dir, [e for e in os.listdir(true_dir) if e.endswith('.csv')][0])
    true_df = pd.read_csv(true_fp, index_col=0)
    
    #===========================================================================
    # check
    #===========================================================================
    assert_frame_equal(df, true_df)
 
 
@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_04_build_hsamp_tutorials_0\CanFlood_test_01.txt']) #from test_04
def test_05_build_evals(session, base_dir, cf_fp, true_dir):
    dial = session.Dialog
    
    #===========================================================================
    # setup
    #===========================================================================
    out_dir = session.out_dir
    cf_fp = build_setup(base_dir, cf_fp, dial, out_dir, testName='test_05')
    
    #===========================================================================
    # get event names
    #===========================================================================
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='dmg_fps', varName='expos')
    eventNames_l = pd.read_csv(fp, index_col=0).columns.to_list()
    dial.event_name_set = eventNames_l
    #===========================================================================
    # setup table
    #===========================================================================
    dial._change_tab('tab_eventVars')
    tblW = dial.fieldsTable_EL
    evals_l = [1000, 200, 100, 50]
    evals_l.sort()
    tblW.setRowCount(len(evals_l)) #add this many rows
    for i, (eName, pval) in enumerate(zip(eventNames_l, evals_l)):
        tblW.setItem(i, 0, QTableWidgetItem(str(eName)))
        tblW.setItem(i, 1, QTableWidgetItem(str(pval)))
    
    #===========================================================================
    # #store
    #===========================================================================
    QTest.mouseClick(dial.pushButton_ELstore, Qt.LeftButton) #refresh
    
    #===========================================================================
    # load result from control file
    #===========================================================================
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='risk_fps', varName='evals')
    assert os.path.exists(fp)
    
    df = pd.read_csv(fp, index_col=None)
    
    #===========================================================================
    # load trues
    #===========================================================================
    true_fp = os.path.join(true_dir, [e for e in os.listdir(true_dir) if e.endswith('.csv')][0])
    true_df = pd.read_csv(true_fp, index_col=None)
    
 
    #===========================================================================
    # check
    #===========================================================================
    assert_frame_equal(df, true_df)
    
 
@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_05_build_evals_tests2__da0\CanFlood_test_01.txt']) #from test_05
@pytest.mark.parametrize('finv_fp',[r'tutorials\2\finv_tut2.gpkg'])
@pytest.mark.parametrize('dtm_fp',[r'tutorials\2\dtm_tut2.tif'])
def test_06_build_dtm(session, base_dir, cf_fp, true_dir, finv_fp, dtm_fp):
    dial = session.Dialog
    
    #===========================================================================
    # setup
    #===========================================================================
    out_dir = session.out_dir
    cf_fp = build_setup(base_dir, cf_fp, dial, out_dir, testName='test_06')
    
    #===========================================================================
    # setup finv
    #===========================================================================
    #select the finv
    dial._change_tab('tab_inventory')
    finv_vlay = session.load_vlay(os.path.join(base_dir, finv_fp))
    dial.comboBox_ivlay.setLayer(finv_vlay)
    
    #indeix field name
    dial.mFieldComboBox_cid.setField('xid')
    
    
    #===========================================================================
    # setup dtm rlay
    #===========================================================================
    dial._change_tab('tab_dtmSamp')
    #add raster
    fp = os.path.join(base_dir, dtm_fp)
    dtm_rlay = session.load_rlay(fp)
    
    #select it
    dial.comboBox_dtm.setLayer(dtm_rlay)
    
    
    #===========================================================================
    # execute
    #===========================================================================
    #sample
    QTest.mouseClick(dial.pushButton_DTMsamp, Qt.LeftButton) 
    
    #===========================================================================
    # load result from control file
    #===========================================================================
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='dmg_fps', varName='gels')
    assert os.path.exists(fp)
    
    df = pd.read_csv(fp, index_col=0)
    
    #===========================================================================
    # load trues
    #===========================================================================
    true_fp = os.path.join(true_dir, [e for e in os.listdir(true_dir) if e.endswith('.csv')][0])
    true_df = pd.read_csv(true_fp, index_col=0)
    
 
    #===========================================================================
    # check
    #===========================================================================
    assert_frame_equal(df, true_df)


@pytest.mark.dev 
@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_06_build_dtm_tutorials__20\CanFlood_test_01.txt']) #from test_06
def test_07_build_valid(session, base_dir, cf_fp):
    dial = session.Dialog
    
    #===========================================================================
    # setup
    #===========================================================================
    out_dir = session.out_dir
    cf_fp = build_setup(base_dir, cf_fp, dial, out_dir, testName='test_06')
    
    #===========================================================================
    # validation
    #===========================================================================
    dial._change_tab('tab_validation')
    
    #check the boxes
    dial.checkBox_Vi2.setChecked(True)
    #dial.checkBox_Vr2.setChecked(True)
    
    QTest.mouseClick(dial.pushButton_Validate, Qt.LeftButton)  
    
    
def build_setup(base_dir, cf_fp, dial, out_dir, testName='testName'): #typical setup for build toolset
    dial._change_tab('tab_setup')
    #copy over the control file
    assert os.path.exists(os.path.join(base_dir, cf_fp))
    cf_fp = shutil.copy2(os.path.join(base_dir, cf_fp), os.path.join(out_dir, os.path.basename(cf_fp)))
    #set the working directory
    dial.lineEdit_wdir.setText(str(out_dir))
    dial.linEdit_ScenTag.setText(testName)
    #set the control file
    dial.lineEdit_cf_fp.setText(cf_fp)
    
    return cf_fp
