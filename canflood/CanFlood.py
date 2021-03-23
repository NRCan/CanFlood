# -*- coding: utf-8 -*-
"""
main plugin parent
"""
#==============================================================================
#imports
#==============================================================================
#from PyQt5.QtCore import QSettings, QTranslator, QCoreApplication, QObject
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QMenu

# Initialize Qt resources from file resources.py
from .resources import *



import os.path
from qgis.core import Qgis, QgsMessageLog, QgsStyle



#===============================================================================
# custom imports
#===============================================================================
"""
relative references seem to work in Qgis.. but IDE doesnt recognize
"""

from .hlpr.exceptions import QError as Error


from build.dialog import BuildDialog
from model.dialog import ModelDialog
from results.dialog import ResultsDialog
from .misc.wc import WebConnect
from .misc.rfda import rfda_dialog
from .misc.dikes.dialog import DikesDialog




class CanFlood:
    """
    called by __init__.py 's classFactor method
    """
    menu_name = "&CanFlood"
    act_menu_l = []
    act_toolbar_l = []
    
    cf_fp = '' #control file pathf or passing between dialogs
    finv_vlay = None #finv layer for passing

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        
        self.iface = iface

        # Create the dialog (after translation) and keep reference
        self.dlg1 = BuildDialog(self.iface, session=self)
        self.dlg2 = ModelDialog(self.iface, session=self)
        self.dlg3 = ResultsDialog(self.iface, session=self)
        
        self.dlg_rfda = rfda_dialog.rDialog(self.iface)
        self.dlg_dikes = DikesDialog(self.iface)


        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        
        self.pars_dir = os.path.join(os.path.dirname(__file__), '_pars')
        


    def initGui(self): #add UI elements to Qgis
        """
        called on Qgis Load?
        
        """
        #=======================================================================
        # toolbar--------
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
        self.button_build.triggered.connect(self.dlg1.launch)
        
        #add button to th etoolbar
        self.toolbar.addAction(self.button_build)

        #=======================================================================
        # button 2: Model
        #=======================================================================
        #build
        self.button_model = QAction(
            QIcon(':/plugins/canflood_inprep/icons/house_flood.png'),
            'Model', self.iface.mainWindow())
        
        self.button_model.setObjectName('Model')
        self.button_model.setCheckable(False)
        self.button_model.triggered.connect(self.dlg2.launch)
        
        #add it
        self.toolbar.addAction(self.button_model)

        #=======================================================================
        # button 3: Results
        #=======================================================================
        #build
        self.button_results = QAction(
            QIcon(':/plugins/canflood_inprep/icons/eye_23x23.png'), 
            'Results', self.iface.mainWindow())
        
        self.button_results.setObjectName('button_results')
        self.button_results.setCheckable(False)
        self.button_results.triggered.connect(self.dlg3.launch)
        
        #add
        self.toolbar.addAction(self.button_results)
        
        #=======================================================================
        # menus---------
        #=======================================================================
        #=======================================================================
        # Add Connections
        #=======================================================================
        #build the action
        icon = QIcon(os.path.dirname(__file__) + "/icons/download-cloud.png")
        
        self.action_dl = QAction(QIcon(icon), 'Add Connections', self.iface.mainWindow())
        self.action_dl.triggered.connect(self.webConnect) #connect it
        self.act_menu_l.append(self.action_dl) #add for cleanup
        
        #use helper method to add to the PLugins menu
        self.iface.addPluginToMenu(self.menu_name, self.action_dl)
        
        
        #=======================================================================
        # rfda
        #=======================================================================
        #build the action
        icon = QIcon(os.path.dirname(__file__) + "/icons/rfda.png")
        self.action_rfda = QAction(QIcon(icon), 'RFDA Conversions', self.iface.mainWindow())
        self.action_rfda.triggered.connect(self.dlg_rfda.show)
        self.act_menu_l.append(self.action_rfda) #add for cleanup
        
        #add to the menu
        self.iface.addPluginToMenu(self.menu_name, self.action_rfda)
        
        #=======================================================================
        # dikes
        #=======================================================================
        icon = QIcon(os.path.dirname(__file__) + "/icons/dike.png")
        self.action_dikes = QAction(QIcon(icon), 'Dike Fragility Mapper', self.iface.mainWindow())
        self.action_dikes.triggered.connect(self.dlg_dikes.launch)
        self.act_menu_l.append(self.action_dikes) #add for cleanup
        
        #add to the menu
        self.iface.addPluginToMenu(self.menu_name, self.action_dikes)
        
        #=======================================================================
        # styles
        #=======================================================================
        icon = QIcon(os.path.dirname(__file__) + "/icons/paint-palette.png")
        self.action_styles = QAction(QIcon(icon), 'Add Styles', self.iface.mainWindow())
        self.action_styles.triggered.connect(self.load_style_xml)
        self.act_menu_l.append(self.action_styles) #add for cleanup
        
        #add to the menu
        self.iface.addPluginToMenu(self.menu_name, self.action_styles)


        
        
    def webConnect(self):
        """no GUI here.. just executing a script"""
        self.logger('pushed webConnect')
        
        wc1 = WebConnect(
            iface = self.iface
            )
        
        newCons_d = wc1.addAll()
        
        self.iface.reloadConnections()
        
        wc1.logger.push('added %i connections'%(len(newCons_d)))
        
    def load_style_xml(self): #load the xml style file
        #=======================================================================
        #setup the logger
        #=======================================================================
        from hlpr.plug import logger
        log = logger(self)
        
        #=======================================================================
        # filepath
        #=======================================================================
        
        fp = os.path.join(self.pars_dir, 'CanFlood.xml')
        assert os.path.exists(fp), 'requested xml filepath does not exist: %s'%fp
        
        #=======================================================================
        # add the sylte
        #=======================================================================
        style = QgsStyle.defaultStyle() #get the users style database

        if style.importXml(fp):
            log.push('imported styles from %s'%fp)
        else:
            log.error('failed to import styles')
        
    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI.
        called when user unchecks the plugin
        """
        #=======================================================================
        # unload toolbars
        #=======================================================================
        
        """toolbar seems to unload without this
        self.logger('attempting to unload %i actions from toolbar'%len(self.actions))
        for action in self.actions: #loop through each action and unload it
            self.iface.removeToolBarIcon(action) #try and remove from plugin menu and toolbar
            """

        #=======================================================================
        # unload menu
        #=======================================================================
        """not sure if this is needed"""
        for action in self.act_menu_l:
            try:
                self.iface.removePluginMenu( self.menu_name, action)
            except Exception as e:
                self.logger('failed to unload action w/ \n    %s'%e)

            
        self.logger('unloaded CanFlood')
            
            
    def logger(self, msg):
        QgsMessageLog.logMessage(msg, 'CanFlood', level=Qgis.Info)
            
        

    def run(self):

        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            pass
        
