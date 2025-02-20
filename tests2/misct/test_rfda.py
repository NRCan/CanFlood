'''
Created on Feb. 20, 2025

@author: cef
'''


import pytest, os, shutil, configparser

import pandas as pd

from pandas.testing import assert_frame_equal


from qgis.core import QgsCoordinateReferenceSystem

from PyQt5.QtTest import QTest
from PyQt5.Qt import Qt

from canflood.misc.rfda.dialog import RfdaDialog



#===============================================================================
# fixtures-----
#===============================================================================
@pytest.fixture(scope='module')
def crs():
    return QgsCoordinateReferenceSystem('EPSG:3005')

#===============================================================================
# tests---------
#===============================================================================

@pytest.mark.parametrize('dialogClass',[RfdaDialog], indirect=True)
#@pytest.mark.parametrize('cf_fp',[os.path.join(tutorial_data_dir, 'baseModel', 'CanFlood_tut8.txt')])
def test_misc_rfda_01_init(session):
    """basic init"""
    dial = session.Dialog
    
    