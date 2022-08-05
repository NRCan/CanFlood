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

    
@pytest.mark.parametrize('dialogClass',[ResultsDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_model_02_r2_ModelDialog_t0\CanFlood_test_01.txt'], indirect=True) #from build test_07
def test_res_02_pdf_report(dial):
    """generate a pdf report, check the report has been created"""
    dial.iface = None # Preventing layout window opening

    # Calling method directly to gain access to report object
    report = ResultsDialog.run_reporter(dial)

    assert isinstance(report, QgsReport)

@pytest.mark.dev
@pytest.mark.parametrize('dialogClass',[ResultsDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[r'tests2\data\test_model_02_r2_ModelDialog_t0\CanFlood_test_01.txt'], indirect=True) #from build test_07
def test_res_03_report_sections(dial):
    """generate a pdf report, check that the expected sections are included"""
    dial.iface = None # Preventing layout window opening

    # Calling method directly to gain access to report object
    report = ResultsDialog.run_reporter(dial)

    assert isinstance(report, QgsReport)
    sections = report.childSections()

    pageCount = len(sections)

    # The control file being used will create 4 sections
    if pageCount == 5:
        pass
    else:
        fail('Report has incorrect amount of pages')
