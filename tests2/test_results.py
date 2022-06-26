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

