'''
Created on Jun. 26, 2022

@author: cefect

unit tests for CanFlood's 'results' toolset
'''
from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject, QgsReport, QgsReportSectionLayout
from PyQt5.Qt import Qt
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem
from pandas.testing import assert_frame_equal
from pytest import fail
from pytest_qgis.utils import clean_qgis_layer

from results.dialog import ResultsDialog
import pandas as pd
import pytest, os, shutil


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
def test_res_01_riskPlot(dial): #test risk plots
    dial._change_tab('tab_riskPlot')

    QTest.mouseClick(dial.pushButton_RP_plot, Qt.LeftButton)

    # If an SVG is created, we can assume that the plotter has completed
    svg_fp = os.path.join(dial.out_dir, [e for e in os.listdir(dial.out_dir) if e.endswith('.svg')][0])

    if os.path.exists(svg_fp):
        pass
    else:
        fail('Failed to create risk plot svg')




@pytest.mark.dev
@pytest.mark.parametrize('dialogClass',[ResultsDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_model_02_r2_ModelDialog_t0\CanFlood_test_01.txt'], indirect=True) #from build test_07
@pytest.mark.parametrize('finv_fp',[r'tutorials\2\finv_tut2.gpkg'], indirect=True)
def test_res_02_pdf_report(dial, finv_fp):
    """generate a pdf report, validate
    
    TODO:
    add additional cases (e.g., no vector layer)
    """
    
    res_02_reporter(dial, finv_fp=finv_fp, vsect_cnt=6)

    
def res_02_reporter(dial, finv_fp=None, vsect_cnt = 5):
    """build and test report
    
    refacorted for use in tutoirals test
    
    ResultsDialog.run_reporter()
    """
    dial._change_tab('tab_report')
    
    #===========================================================================
    # attach layer
    #===========================================================================
    if not finv_fp is None:
        finv_vlay = dial.session.load_vlay(finv_fp)
        dial.comboBox_rpt_vlay.setLayer(finv_vlay)
 
    #===========================================================================
    # build report
    #===========================================================================
    QTest.mouseClick(dial.pushButton_rpt_create, Qt.LeftButton)
    report = dial.report
    #===========================================================================
    # validate
    #===========================================================================
    assert isinstance(report, QgsReport)
    sections = report.childSections()
 
    if not len(sections) == vsect_cnt:
        fail('expected %i sections got %i'%(vsect_cnt, len(sections)))
