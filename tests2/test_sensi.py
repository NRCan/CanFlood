'''
Created on Feb. 20, 2025

@author: cef

TODO: 
    add more unit tests
    add tutorial 8 test (see  tests.dialogs.wfDialogs.Tut8a)

'''


import pytest, os, shutil, configparser

import pandas as pd

from pandas.testing import assert_frame_equal


from qgis.core import QgsCoordinateReferenceSystem

from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt

from canflood.sensi.dialog import SensiDialog

#from .conftest import _build_dialog_validate_handler, base_dir

#===============================================================================
# params-----
#===============================================================================
from definitions import tutorial_data_dir as tutorial_data_dir_base
tutorial_data_dir = os.path.join(tutorial_data_dir_base, '8')

#===============================================================================
# fixtures-----
#===============================================================================
@pytest.fixture(scope='module')
def crs():
    return QgsCoordinateReferenceSystem('EPSG:3005')

#===============================================================================
# tests---------
#===============================================================================

@pytest.mark.parametrize('dialogClass',[SensiDialog], indirect=True)
@pytest.mark.parametrize('cf_fp',[os.path.join(tutorial_data_dir, 'baseModel', 'CanFlood_tut8.txt')])
def test_sensi_01_setup(session, cf_fp):
    """basic tests on the 'setup' tab"""
    dial = session.Dialog
    dial._change_tab('tab_setup')

    #configure file behavior
    dial.radioButton_SS_fpRel.setChecked(True)
    dial.radioButton_s_pltFile.setChecked(True) #plot handling
    
    #configure base model
    dial.lineEdit_cf_fp.setText(cf_fp)    
    dial.comboBox_S_ModLvl.setCurrentIndex(1) #modLevel=L2
    
    
    
    QTest.mouseClick(dial.pushButton_s_load, Qt.LeftButton)