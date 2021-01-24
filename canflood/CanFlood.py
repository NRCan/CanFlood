# -*- coding: utf-8 -*-
"""
main plugin parent
"""
#==============================================================================
#import------------------------------------------------------------------ 
#==============================================================================
#from PyQt5.QtCore import QSettings, QTranslator, QCoreApplication, QObject
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QMenu

# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog

#from .canFlood_inPrep_dialog import CanFlood_inPrepDialog
import os.path
from qgis.core import Qgis, QgsMessageLog

# User defined imports
#from qgis.core import *
#from qgis.analysis import *
#import qgis.utils
#import processing
#from processing.core.Processing import Processing
#import sys, os, warnings, tempfile, logging, configparser




"""
relative references seem to work in Qgis.. but IDE doesnt recognize
"""
#from canFlood_model import CanFlood_Model
from .hlpr.exceptions import QError as Error


from .build.BuildDialog import DataPrep_Dialog
from .model.ModelDialog import Modelling_Dialog
from .results.ResultsDialog import Results_Dialog
from .misc.wc import WebConnect






class CanFlood:
    """
    called by __init__.py 's classFactor method
    """


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
        
        """ some unused initilization stuff Tony needed?
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
            QCoreApplication.installTranslator(self.translator)"""

        # Create the dialog (after translation) and keep reference
        self.dlg1 = DataPrep_Dialog(self.iface)
        self.dlg2 = Modelling_Dialog(self.iface)
        self.dlg3 = Results_Dialog(self.iface)
        

        

        # Declare instance attributes
        """not sure how this gets populated"""
        self.actions = []
        
        """old menu pointer?
        self.menu = self.tr(u'&CanFlood_inPrep')"""

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        
        
        #start with an empty ref
        self.canflood_menu = None



    def initGui(self):
        """
        where is this called?
        called on Qgis Load?
        add UI elements to Qgis
        """
        

        #=======================================================================
        # add toolbar
        #=======================================================================
        """Create the menu entries and toolbar icons inside the QGIS GUI."""  
        self.toolbar = self.iface.addToolBar('CanFlood') #build a QToolBar
        self.toolbar.setObjectName('CanFloodToolBar')
        
        #=======================================================================
        # button 1: Build
        #=======================================================================
        #build the button
        """not sure how this icon is working...."""
        self.button_build = QAction(QIcon(
            ':/plugins/canflood_inprep/icons/Andy_Tools_Hammer_Spanner_23x23.png'), 
            'Build', self.iface.mainWindow())
         
        self.button_build.setObjectName('Build')
        self.button_build.setCheckable(False)
        self.button_build.triggered.connect(self.showToolbarDataPrep)
        
        
        self.toolbar.addAction(self.button_build)

        #=======================================================================
        # button 2: Model
        #=======================================================================
        self.button_model = QAction(
            QIcon(':/plugins/canflood_inprep/icons/house_flood.png'),
            'Model', self.iface.mainWindow())
        
        self.button_model.setObjectName('Model')
        self.button_model.setCheckable(False)
        self.button_model.triggered.connect(self.showToolbarProjectModelling)
        self.toolbar.addAction(self.button_model)

        #=======================================================================
        # button 3: Results
        #=======================================================================
        self.button_results = QAction(
            QIcon(':/plugins/canflood_inprep/icons/eye_23x23.png'), 
            'Results', self.iface.mainWindow())
        
        self.button_results.setObjectName('button_results')
        self.button_results.setCheckable(False)
        self.button_results.triggered.connect(self.showToolbarProjectResults)
        self.toolbar.addAction(self.button_results)
        
        #=======================================================================
        # add menus---------
        #=======================================================================
        #build the action
        icon = QIcon(os.path.dirname(__file__) + "/icons/download-cloud.png")
        self.action_dl = QAction(QIcon(icon), 'Add Connections', self.iface.mainWindow())
        self.action_dl.triggered.connect(self.webConnect) #connect it
        
        #use helper method to add to the PLugins menu
        self.iface.addPluginToMenu("&CanFlood", self.action_dl)
        

    def showToolbarDataPrep(self):
        # Using exec_() creating a blocking dialog, show creates a non-blocking dialog
        #self.dlg1.exec_()
        self.dlg1.show()
    
    def showToolbarProjectModelling(self):
        self.dlg2.show()
    
    def showToolbarProjectResults(self):
        self.dlg3.show()
        
    def webConnect(self):
        self.logger('pushed webConnect')
        
        wc1 = WebConnect(
            iface = self.iface
            #self.iface
            )
        
        newCons_d = wc1.addAll()
        
        self.iface.reloadConnections()
        
        wc1.logger.push('added %i connections'%(len(newCons_d)))
        
    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI.
        called when user unchecks the plugin?
        """
        for action in self.actions: #loop through each action and unload it
            #try and remove from plugin menu and toolbar

            
            self.iface.removeToolBarIcon(action)
            
        
        self.iface.removePluginMenu(
                "&CanFlood",
                self.action_dl)

            
        self.logger('unloaded CanFlood')
            
            
    def logger(self, msg):
        QgsMessageLog.logMessage(msg, 'CanFlood', level=Qgis.Info)
            
        

    def run(self):
        """Run method that performs all the real work"""
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            pass
        
