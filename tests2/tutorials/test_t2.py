'''
Created on Jun. 24, 2022

@author: cefect

tutorial 2 integration tests
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
def test_01_build(session):
    dial = session.Dialog
    
    #===========================================================================
    # scenario setup
    #===========================================================================
    dial._change_tab('tab_setup')
    dial.lineEdit_wdir.setText(str(session.out_dir))
    dial.linEdit_ScenTag.setText('testName')
    dial.build_scenario()

    assert os.path.exists(dial.lineEdit_cf_fp.text())
    
    #===========================================================================
    # Select Vulnerability Function Set
    #===========================================================================
    dial._change_tab('tab_inventory')
    
    """too tricky to use this UI. should add at somepoint though
    QTest.mouseClick(dial.pushButton_inv_vfunc, Qt.LeftButton)"""
    
 
    raw_fp = os.path.join(session.pars_dir, 'vfunc\IBI_2015\IBI2015_DamageCurves.xls')
 
    
    print('yay')
 