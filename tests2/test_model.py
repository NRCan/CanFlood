'''
Created on Jun. 26, 2022

@author: cefect
unit tests for CanFlood's 'model' toolset
'''


import pytest, os, shutil

import pandas as pd

from pandas.testing import assert_frame_equal

from pytest_qgis.utils import clean_qgis_layer

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

from model.dialog import ModelDialog


#===============================================================================
# fixtures-------
#===============================================================================
@pytest.fixture(scope='module')
def crs():
    return QgsCoordinateReferenceSystem('EPSG:3005')

@pytest.fixture(scope='function')
def dial(session, cf_fp): #configured dialog
    
    dial = session.Dialog
    
    #===========================================================================
    # copy over files
    #===========================================================================
    # Get the directory containing cf_fp
    cf_dir = os.path.dirname(cf_fp)
    
    # Iterate over all files in the directory
    for file_name in os.listdir(cf_dir):
        full_file_path = os.path.join(cf_dir, file_name)
    
        # Ensure it's a file (skip directories)
        if os.path.isfile(full_file_path):
            # Copy the file to the output directory
            shutil.copy2(full_file_path, os.path.join(session.out_dir, file_name))
    
    cf_fp = os.path.join(session.out_dir, os.path.basename(cf_fp))
    #===========================================================================
    # setup
    #===========================================================================
    dial._change_tab('tab_setup')
    assert os.path.exists(cf_fp)
    
    
    #set the working directory
    dial.lineEdit_wdir.setText(str(session.out_dir))
 
    #set the control file
    dial.lineEdit_cf_fp.setText(cf_fp)
    
    dial.radioButton.setChecked(True) #save plots to file
    dial.comboBox_JGfinv.setCurrentIndex(-1) #clear finv
    
    return dial
    
    



#===============================================================================
# tests---------
#===============================================================================
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_07_build_valid_tests2__da0\CanFlood_test_01.txt'], indirect=True) #from build test_07
@pytest.mark.parametrize('dialogClass',[ModelDialog], indirect=True)
def test_model_01_i2(dial, true_dir): #impacts L2
    
    #===========================================================================
    # setup impacts 2
    #===========================================================================
    dial._change_tab('tab_i2')
    
    dial.checkBox_i2_outExpnd.setChecked(True)
    dial.checkBox_i2_pbox.setChecked(False) #no plots
 
    #===========================================================================
    # execute
    #===========================================================================
    QTest.mouseClick(dial.pushButton_i2run, Qt.LeftButton)   #model.dialog.ModelDialog.run_impact2()
    
    #retrieve
    cf_fp = dial.get_cf_fp()
    fp = dial.get_cf_par(cf_fp, sectName='risk_fps', varName='dmgs')
    assert not fp == '', 'failed to get a result'
    fp = os.path.join(os.path.dirname(cf_fp), fp)    
    assert os.path.exists(fp), 'failed to generate risk_fps'
    
    #load
    df = pd.read_csv(fp, index_col=0)
    #===========================================================================
    # load trues
    #===========================================================================
    true_fp = os.path.join(true_dir, [e for e in os.listdir(true_dir) if e.startswith('dmgs_test')][0])
    true_df = pd.read_csv(true_fp, index_col=0)
    
    assert_frame_equal(df, true_df)

@pytest.mark.dev
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_model_01_i2_ModelDialog_t0\CanFlood_test_01.txt'], indirect=True) #from build test_07
@pytest.mark.parametrize('dialogClass',[ModelDialog], indirect=True)
def test_model_02_r2(dial, true_dir, cf_fp): #risk L2
    
    #===========================================================================
    # setup 
    #===========================================================================
    dial._change_tab('tab_r2')
    
    dial._change_tab('tab_r2')
    
    dial.checkBox_r2rpa.setChecked(True)
    dial.checkBox_r2_ari.setChecked(False)

    
    QTest.mouseClick(dial.pushButton_r2Run, Qt.LeftButton) 
    
    #retrieve
    cf_fp = dial.get_cf_fp()
    fp = dial.get_cf_par(cf_fp, sectName='results_fps', varName='r_ttl')
    assert not fp == '', 'failed to get a result'
    #fp = os.path.join(os.path.dirname(cf_fp), fp)   
    assert os.path.exists(fp), 'failed to generate risk_fps'
    
        #load
    df = pd.read_csv(fp, index_col=0)
    #===========================================================================
    # load trues
    #===========================================================================
    true_fp = os.path.join(true_dir, [e for e in os.listdir(true_dir) if e.endswith('_ttl.csv')][0])
    true_df = pd.read_csv(true_fp, index_col=0)
    
    assert_frame_equal(df, true_df)

0