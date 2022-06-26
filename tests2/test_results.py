'''
Created on Jun. 26, 2022

@author: cefect

unit tests for CanFlood's 'results' toolset
'''


import pytest, os, shutil

import pandas as pd

from pandas.testing import assert_frame_equal

from pytest_qgis.utils import clean_qgis_layer

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem

from results.dialog import ResultsDialog


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
    dial.checkBox_SSoverwrite.setChecked(False)
    
 
    
    return dial

#===============================================================================
# tests---------
#===============================================================================
@pytest.mark.parametrize('dialogClass',[ResultsDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_model_02_r2_ModelDialog_t0\CanFlood_test_01.txt'], indirect=True) #from build test_07
def test_res_01_riskPlot(dial, true_dir): #test risk plots
    QTest.mouseClick(dial.pushButton_RP_plot, Qt.LeftButton)
    
    """TODO: check figures were created"""
    
    
def test_res_02_pdf_report(dial):
    """generate a pdf report
    check all the expected pages are there"""
    pass 
    
    
    
    