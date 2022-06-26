'''
Created on Jun. 24, 2022

@author: cefect

tutorial 2 integration tests
'''

import pytest, os, shutil

import pandas as pd
from pandas.testing import assert_frame_equal

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

from matplotlib import pyplot as plt

from build.dialog import BuildDialog
from model.dialog import ModelDialog
from results.dialog import ResultsDialog

@pytest.fixture(scope='module')
def crs():
    return QgsCoordinateReferenceSystem('EPSG:3005')

@pytest.fixture(scope='module')
def data_dir(base_dir):
    return os.path.join(base_dir, r'tutorials\2')
    



@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
def test_t2_A(session, data_dir, true_dir, tmp_path, write):
    #===========================================================================
    # Build---------
    #===========================================================================
    dial = session.Dialog
    
    out_dir = session.out_dir #send the outputs we care about here
    session.out_dir = tmp_path #overwrite so we don't capture all outputs
    
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
    
    #populate table
    tblW = dial.fieldsTable_EL
    evals_l = [1000, 200, 100, 50]
    for i, pval in enumerate(evals_l):
        tblW.setItem(i, 1, QTableWidgetItem(str(pval)))
        
    #store
    QTest.mouseClick(dial.pushButton_ELstore, Qt.LeftButton) #refresh
    
    #check it
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='risk_fps', varName='evals')
    assert os.path.exists(fp)
    
    df = pd.read_csv(fp)
    assert len(df.columns)==len(evals_l)
    
    #===========================================================================
    # dtm sampler
    #===========================================================================
    dial._change_tab('tab_dtmSamp')
    #add raster
    fp = os.path.join(data_dir, 'dtm_tut2.tif')
    dtm_rlay = session.load_rlay(fp)
    
    #select it
    dial.comboBox_dtm.setLayer(dtm_rlay)
    
    #sample
    QTest.mouseClick(dial.pushButton_DTMsamp, Qt.LeftButton)  
    
    
    #check it
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='dmg_fps', varName='gels')
    assert os.path.exists(fp)
    
    df = pd.read_csv(fp, index_col=0)
    assert len(df)==finv_vlay.dataProvider().featureCount()
    
    #===========================================================================
    # validation
    #===========================================================================
    dial._change_tab('tab_validation')
    
    #check the boxes
    dial.checkBox_Vi2.setChecked(True)
    #dial.checkBox_Vr2.setChecked(True)
    
    QTest.mouseClick(dial.pushButton_Validate, Qt.LeftButton)  
    
    
    #===========================================================================
    # model----------
    #===========================================================================
    dial = session.init_dialog(ModelDialog)
    
    dial._change_tab('tab_setup')
    
    dial.radioButton.setChecked(True) #save plots to file
    dial.comboBox_JGfinv.setCurrentIndex(-1) #clear finv
    #===========================================================================
    # impacts (L2)
    #===========================================================================
    dial._change_tab('tab_i2')
    
    dial.checkBox_i2_outExpnd.setChecked(True)
    dial.checkBox_i2_pbox.setChecked(False) #no plots
    
    QTest.mouseClick(dial.pushButton_i2run, Qt.LeftButton)   #Run dmg2
    
    #check it
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='risk_fps', varName='dmgs')
    assert os.path.exists(fp)
    
    #===========================================================================
    # risk (L2)
    #===========================================================================
    dial._change_tab('tab_r2')
    
    dial.checkBox_r2rpa.setChecked(True)
    dial.checkBox_r2_ari.setChecked(True)
    
    
    QTest.mouseClick(dial.pushButton_r2Run, Qt.LeftButton) 
    
    #check it
    res_d = dict()
    for varName in ['r_passet', 'r_ttl', 'eventypes']:
        fp = dial.get_cf_par(dial.get_cf_fp(), sectName='results_fps', varName=varName)
        assert os.path.exists(fp), varName
        res_d[varName] = fp
        
        #copy over for validation
        if varName=='r_ttl' and write:
            shutil.copy2(fp, os.path.join(out_dir, os.path.basename(fp)))
        
    #clean up plots
    """shouldnt be needed if 'save to file' is working"""
    plt.close() 
    #===========================================================================
    # results------
    #===========================================================================
    dial = session.init_dialog(ResultsDialog)
 
    #===========================================================================
    # setup
    #===========================================================================
    dial._change_tab('tab_setup')
    
    dial.radioButton.setChecked(True) #save plots to file
    dial.checkBox_SSoverwrite.setChecked(False)
    
    #===========================================================================
    # risk plots
    #===========================================================================
    dial._change_tab('tab_riskPlot')
    
    """TODO: add plot formatting customization parameters and checks"""
    
    
    QTest.mouseClick(dial.pushButton_RP_plot, Qt.LeftButton) 
    
    #===========================================================================
    # validate-----
    #===========================================================================
    varName = 'r_ttl'
    fp = res_d[varName]
 
    df = pd.read_csv(fp)
    
    #load trues
    match_l = [e for e in os.listdir(true_dir) if e.endswith('ttl.csv')]
    assert len(match_l)==1
    
    
    true_fp = os.path.join(true_dir, match_l[0])
    true_df = pd.read_csv(true_fp)
    
    assert_frame_equal(df, true_df)
    
    
    
    
    
    
    

 
    
 