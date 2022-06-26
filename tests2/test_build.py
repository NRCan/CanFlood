'''
Created on Jun. 24, 2022

@author: cefect

unit tests for CanFlood's 'build' toolset

lets launch one dialog worker per module

one test per button click

see tutorials for integration tests


'''

import pytest, os

from qgis.core import QgsCoordinateReferenceSystem, QgsVectorLayer, QgsProject
from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt

from build.dialog import BuildDialog





@pytest.fixture(scope='module')
def crs():
    return QgsCoordinateReferenceSystem('EPSG:3005')

 

@pytest.mark.parametrize('dialogClass',[BuildDialog], indirect=True)
def test_01_build_scenario(session):
    dial = session.Dialog
    dial._change_tab('tab_setup')
    #===========================================================================
    # setup
    #===========================================================================
    dial.linEdit_ScenTag.setText('testName')
    #===========================================================================
    # execute
    #===========================================================================
    """BuildDialog.build_scenario()"""
    QTest.mouseClick(dial.pushButton_generate, Qt.LeftButton)
 
    #===========================================================================
    # check
    #===========================================================================
    assert os.path.exists(dial.lineEdit_cf_fp.text())
