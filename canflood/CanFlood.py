# -*- coding: utf-8 -*-
"""
second call
"""
#==============================================================================
#import------------------------------------------------------------------ 
#==============================================================================
from PyQt5.QtCore import QSettings, QTranslator, QCoreApplication, QObject
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog

#from .canFlood_inPrep_dialog import CanFlood_inPrepDialog
import os.path
from qgis.core import QgsProject, Qgis, QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest

# User defined imports
from qgis.core import *
from qgis.analysis import *
import qgis.utils
import processing
from processing.core.Processing import Processing
import sys, os, warnings, tempfile, logging, configparser


import numpy as np
import pandas as pd
"""
Tony's testing workaround?
the absolute imports don't seem to work at this

there has to be a better way"""


#file_dir = os.path.dirname(os.path.abspath(__file__))
#sys.path.append(file_dir)




#from canFlood_model import CanFlood_Model
from .hlpr.exceptions import QError as Error
from shutil import copyfile

from .build.BuildDialog import DataPrep_Dialog
from .model.ModelDialog import Modelling_Dialog
from .results.ResultsDialog import Results_Dialog

#===============================================================================
# imports for PluginReloader
#===============================================================================



class CanFlood:


    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        #=======================================================================
        # self.ras = []
        # self.ras_dict = {}
        # self.vec = None
        # self.wd = None
        # self.cf = None
        #=======================================================================
        
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'CanFlood_inPrep_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg1 = DataPrep_Dialog(self.iface)
        self.dlg2 = Modelling_Dialog(self.iface)
        self.dlg3 = Results_Dialog(self.iface)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&CanFlood_inPrep')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None

    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('CanFlood_inPrep', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        
        #icon_path = ':/plugins/canflood_inprep/icons/CanFlood_Icon.png'
        """Create the menu entries and toolbar icons inside the QGIS GUI."""  
        self.toolbar = self.iface.addToolBar('CanFlood')
        self.toolbar.setObjectName('CanFloodToolBar')
        
        # 1----first button---------------------------------
        self.toolbarProjectDataPrep = QAction(QIcon(
            ':/plugins/canflood_inprep/icons/Andy_Tools_Hammer_Spanner_23x23.png'), 
            'Build', self.iface.mainWindow())
         
        self.toolbarProjectDataPrep.setObjectName('Build')
        self.toolbarProjectDataPrep.setCheckable(False)
        self.toolbarProjectDataPrep.triggered.connect(self.showToolbarDataPrep)
        self.toolbar.addAction(self.toolbarProjectDataPrep)

        # 2----second button---------------------------------
        self.toolbarProjectModelling = QAction(
            QIcon(':/plugins/canflood_inprep/icons/house_flood.png'),
            'Model', self.iface.mainWindow())
        
        self.toolbarProjectModelling.setObjectName('Model')
        self.toolbarProjectModelling.setCheckable(False)
        self.toolbarProjectModelling.triggered.connect(self.showToolbarProjectModelling)
        self.toolbar.addAction(self.toolbarProjectModelling)

        # 3----third button---------------------------------
        self.toolbarProjectResults = QAction(
            QIcon(':/plugins/canflood_inprep/icons/eye_23x23.png'), 
            'Results', self.iface.mainWindow())
        
        self.toolbarProjectResults.setObjectName('toolbarProjectResults')
        self.toolbarProjectResults.setCheckable(False)
        self.toolbarProjectResults.triggered.connect(self.showToolbarProjectResults)
        self.toolbar.addAction(self.toolbarProjectResults)
        
        #=======================================================================
        # plugin reloadert
        #=======================================================================
        from .build import lisamp, rsamp, oth_rfda
        from .hlpr import basic,  exceptions, logr,  plug, Q
        from .model import dmg2, modcom, risk1, risk2
        from .results import djoin, riskPlot

        

    def showToolbarDataPrep(self):
        # Using exec_() creating a blocking dialog, show creates a non-blocking dialog
        #self.dlg1.exec_()
        self.dlg1.show()
    
    def showToolbarProjectModelling(self):
        self.dlg2.show()
    
    def showToolbarProjectResults(self):
        self.dlg3.show()
    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&CanFlood_inPrep'),
                action)
            self.iface.removeToolBarIcon(action)

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            pass