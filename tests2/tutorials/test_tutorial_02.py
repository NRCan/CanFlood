'''
Created on Jun. 24, 2022

@author: cefect

tutorial 2 integration tests




'''

import pandas as pd
import numpy as np
from numpy.testing import assert_array_equal
import pytest, os, shutil

from PyQt5.Qt import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem
from build.dialog import BuildDialog
from matplotlib import pyplot as plt
from model.dialog import ModelDialog
from model.modcom import assert_rttl_valid
from pandas.testing import assert_frame_equal
from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject, QgsReport
from results.dialog import ResultsDialog

from tests2 import test_results

from hlpr.basic import view

from ..conftest import _build_dialog_validate_handler


def extract_between_char(s, char='_'):
    start = s.find(char) + 1
    end = s.find(char, start)
    return s[start:end]

@pytest.fixture(scope='module')
def crs():
    return QgsCoordinateReferenceSystem('EPSG:3005')


@pytest.fixture(scope='module')
def data_dir(base_dir):
    return os.path.join(base_dir, r'tutorials\2')




@pytest.mark.parametrize('absolute_fp',[True, False])
@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
def test_tutorial_02a(session, data_dir, true_dir, tmp_path, write, absolute_fp):
    """simulate tutorial 2A
    https://canflood.readthedocs.io/en/latest/06_tutorials.html#tutorial-2a-risk-l2-with-simple-events
    
    
    Validation
    ----------------
    uses '.pkl' file in the true_dir to validate risk L2 model results
    

    
    
    TODO: 
        refactor or shorten this code (we'll need to re-use a lot of it for subsequent tutorials)
        add more value tests
    """
    
    def get_true_fp(sfx):
        """retrieve the true/validation datafile from a suffix"""
        match_l = [e for e in os.listdir(true_dir) if e.endswith(sfx)]
        assert len(match_l)==1, f'failed to get a  unique match for {sfx}'
        return os.path.join(true_dir, match_l[0])
        
    #===========================================================================
    # Build---------
    #===========================================================================
    dial = session.Dialog
    
    out_dir = session.out_dir #send the outputs we care about here
    session.out_dir = tmp_path #overwrite so we don't capture all outputs
    
    if absolute_fp:
        dial.radioButton_SS_fpAbs.setChecked(True)
    else:
        dial.radioButton_SS_fpRel.setChecked(True)
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
    fp = os.path.join(data_dir, 'finv_tut2.geojson')
    finv_vlay = session.load_vlay(fp)
    dial.comboBox_ivlay.setLayer(finv_vlay)
    
    #index field name
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
    raw_fp = os.path.join(session.pars_dir, 'vfunc\\IBI_2015\\IBI2015_DamageCurves.xls')
    
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
    
    haz_df = pd.read_csv(fp, index_col=0)
    assert len(haz_df)==finv_vlay.dataProvider().featureCount()
    assert len(haz_df.columns)==len(lay_d)
    
    #===========================================================================
    # event variables
    #===========================================================================
    dial._change_tab('tab_eventVars')
    
    #populate table
    tblW = dial.fieldsTable_EL
    evals_l = [ 50.,  100.,  200., 1000.]
    for i, pval in enumerate(evals_l):
        tblW.setItem(i, 1, QTableWidgetItem(str(pval)))
        
    #store
    QTest.mouseClick(dial.pushButton_ELstore, Qt.LeftButton) #refresh
    
    #check it
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='risk_fps', varName='evals')
    assert os.path.exists(fp)
    
    eval_df = pd.read_csv(fp)
    assert len(eval_df.columns)==len(evals_l)
    
    #monotonicity
    evals_from_layerNames_l = [float(extract_between_char(e, char='_')) for e in eval_df.columns]
    
    assert_array_equal(np.array(evals_from_layerNames_l), np.array(evals_l, dtype=float))
    
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
    
    #BuildDialog.run_validate()
    _build_dialog_validate_handler(dial)
 
    
    #===========================================================================
    # MODEL----------
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
    
    QTest.mouseClick(dial.pushButton_i2run, Qt.LeftButton)   #ModelDialog.run_impact2()
    
    #check it
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='risk_fps', varName='dmgs')
    assert os.path.exists(fp)
    
    dmg_df = pd.read_csv(fp)
    assert set(eval_df.columns).difference(dmg_df.columns)==set()
    
    
    
    
    #===========================================================================
    # risk (L2)
    #===========================================================================
    dial._change_tab('tab_r2')
    
    dial.checkBox_r2rpa.setChecked(True)
    dial.checkBox_r2_ari.setChecked(True)
    
    
    QTest.mouseClick(dial.pushButton_r2Run, Qt.LeftButton)  #ModelDialog.run_risk2()
    
    #check it
    res_d = dict()
    for varName in ['r_passet', 'r_ttl', 'eventypes']:
        fp = dial.get_cf_par(dial.get_cf_fp(), sectName='results_fps', varName=varName)
        assert os.path.exists(fp), varName
        res_d[varName] = fp
        
    rttl_df = pd.read_csv(res_d['r_ttl'])
    
    #internal
    assert_rttl_valid(rttl_df, msg=os.path.basename(res_d['r_ttl']))
    
    if write:
        raise NotImplementedError('add validation writing code')
    
    #validate: against trues
    true_df = pd.read_pickle(get_true_fp('r_ttl.pkl'))    
    assert_frame_equal(rttl_df, true_df)
    
    """
    rttl_df.to_pickle('C:\\LS\\09_REPOS\\03_TOOLS\\CanFlood\\_git\\tests2\\data\\test_t2_A_BuildDialog_0\\20230305_r_ttl.pkl')
    view(rttl_df)
    """
 
            
 
        
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
    assert os.path.exists(dial.get_cf_fp())

    #set output directory
    dial.lineEdit_wdir.setText(str(session.out_dir))

    dial.lineEdit_cf_fp.setText(dial.get_cf_fp())
    
    dial.radioButton.setChecked(True) #save plots to file
    dial.checkBox_SSoverwrite.setChecked(True) #set to true to prevent run_reporter crash
    
    #===========================================================================
    # risk plots
    #===========================================================================
    dial._change_tab('tab_riskPlot')
    
    """TODO: add plot formatting customization parameters and checks"""
    dial.checkBox_RP_ari.setChecked(True)
    dial.checkBox_RP_aep.setChecked(False)
    
    QTest.mouseClick(dial.pushButton_RP_plot, Qt.LeftButton)

    svg_fp = os.path.join(dial.out_dir, [e for e in os.listdir(dial.out_dir) if e.endswith('.svg')][0])

    assert os.path.exists(svg_fp)
    
    #===========================================================================
    # pdf reporter
    #===========================================================================
 
    report = test_results.res_02_reporter(dial, finv_fp = os.path.join(data_dir, 'finv_tut2.geojson'))
 
 
    
    #===========================================================================
    # wrap
    #===========================================================================
    print(f'finished w/ ControlFile: {dial.get_cf_fp()}')
 
