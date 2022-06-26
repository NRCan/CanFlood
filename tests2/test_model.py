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
    # copy over control file
    #===========================================================================
    cf_fp = shutil.copy2(cf_fp, os.path.join(session.out_dir, os.path.basename(cf_fp)))
    
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
    
    

@pytest.fixture(scope='function')
def cf_fp(base_dir, request):
    return os.path.join(base_dir, request.param)

#===============================================================================
# tests---------
#===============================================================================
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_07_build_valid_tests2__da0\CanFlood_test_01.txt'], indirect=True) #from build test_07
@pytest.mark.parametrize('dialogClass',[ModelDialog], indirect=True)
def test_model_01_i2(dial, true_dir): #impacts L2
    
    #===========================================================================
    # setup ipmacts 2
    #===========================================================================
    dial._change_tab('tab_i2')
    
    dial.checkBox_i2_outExpnd.setChecked(True)
    dial.checkBox_i2_pbox.setChecked(False) #no plots
    
    #===========================================================================
    # exceute
    #===========================================================================
    QTest.mouseClick(dial.pushButton_i2run, Qt.LeftButton)   #Run dmg2
    
    #retrieve
    fp = dial.get_cf_par(dial.get_cf_fp(), sectName='risk_fps', varName='dmgs')
    assert os.path.exists(fp)
    df = pd.read_csv(fp, index_col=0)
    #===========================================================================
    # load trues
    #===========================================================================
    true_fp = os.path.join(true_dir, [e for e in os.listdir(true_dir) if e.startswith('dmgs_test')][0])
    true_df = pd.read_csv(true_fp, index_col=0)
    
    assert_frame_equal(df, true_df)
    

