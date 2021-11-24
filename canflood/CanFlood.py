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


import weakref
import os.path
from qgis.core import Qgis, QgsMessageLog, QgsStyle



#===============================================================================
# custom imports
#===============================================================================
"""
relative references seem to work in Qgis.. but IDE doesnt recognize
"""

from hlpr.exceptions import QError as Error


from build.dialog import BuildDialog
from model.dialog import ModelDialog
from results.dialog import ResultsDialog
from sensi.dialog import SensiDialog

from misc.rfda.dialog import RfdaDialog
from misc.dikes.dialog import DikesDialog




class CanFlood:
    """
    called by __init__.py 's classFactor method
    """
    menu_name = "&CanFlood"
    act_menu_l = []
    act_toolbar_l = []
    
    cf_fp = '' #control file pathf or passing between dialogs
    finv_vlay = None #finv layer for passing
    
    
    """lets keep all the parameters on the class object"""
    dialogPars_d = {
            'build'     :BuildDialog,
            'model'     :ModelDialog,
            'results'   :ResultsDialog,
            'rfda'      :RfdaDialog,
            'dikes'     :DikesDialog,
            'sensi'     :SensiDialog,
            
            }

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """

        
        self.iface = iface
        self.dialogs_d = dict()
        #=======================================================================
        # build dialog children
        #=======================================================================
        for attn, DialogClass in self.dialogPars_d.items():
            try:
                self.dialogs_d[attn] = DialogClass(self.iface, session=self)
            except Exception as e:
                raise Error('failed to load \'%s\' w/ \n    %s'%(attn, e))
                
 
        #=======================================================================
        # self.dlg1 = BuildDialog(self.iface, session=self)
        # self.dlg2 = ModelDialog(self.iface, session=self)
        # self.dlg3 = ResultsDialog(self.iface, session=self)
        # 
        # self.dlg_rfda = RfdaDialog.rDialog(self.iface)
        # self.dlg_dikes = DikesDialog(self.iface)
        # self.dlg_sensi = SensiDialog(self.iface, session=self)
        #=======================================================================
        
        


        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        
        self.pars_dir = os.path.join(os.path.dirname(__file__), '_pars')
        self.icon_dir = os.path.join(os.path.dirname(__file__), 'icons')
        


    def initGui(self): #add UI elements to Qgis
        """
        called on Qgis Load?
        
        """
        #=======================================================================
        # configure toolbar
        #=======================================================================
        """Create the menu entries and toolbar icons inside the QGIS GUI."""  
        toolbar = self.iface.addToolBar('CanFlood') #build a QToolBar
        toolbar.setObjectName('CanFloodToolBar')
        
        #=======================================================================
        # setup actions
        #=======================================================================
        self.actions_d = dict()
 
        for attn, wrkr in self.dialogs_d.items():
            try:
                #build the icon
                icon_fp = os.path.join(self.icon_dir, wrkr.icon_fn)
                assert os.path.exists(icon_fp), 'bad filepath: %s'%icon_fp
                icon = QIcon(icon_fp)
     
                #assemble the action
                action = QAction(
                    icon, 
                    wrkr.icon_name, 
                    self.iface.mainWindow())
                
                action.setObjectName(wrkr.icon_name)
                action.setCheckable(False)
                action.triggered.connect(wrkr.launch)
                
                #add to the gui
                if wrkr.icon_location == 'toolbar':
                    toolbar.addAction(action)
                elif wrkr.icon_location=='menu':
                    self.iface.addPluginToMenu(self.menu_name, action)
                    
                
                self.actions_d[attn] = action
            except Exception as e:
                raise Error('failed to build action for \'%s\' w/ \n    %s'%(attn, e))
            
        #wrap
        self.toolbar=toolbar
        

        
        #=======================================================================
        # menus---------
        #=======================================================================
        #=======================================================================
        # #=======================================================================
        # # Add Connections
        # #=======================================================================
        # #build the action
        # icon = QIcon(os.path.dirname(__file__) + "/icons/download-cloud.png")
        # 
        # self.action_dl = QAction(QIcon(icon), 'Add Connections', self.iface.mainWindow())
        # self.action_dl.triggered.connect(self.webConnect) #connect it
        # self.act_menu_l.append(self.action_dl) #add for cleanup
        # 
        # #use helper method to add to the PLugins menu
        # self.iface.addPluginToMenu(self.menu_name, self.action_dl)
        # 
        # 
        # #=======================================================================
        # # rfda
        # #=======================================================================
        # """
        # TODO: replace this w/ a for loop
        # """
        # #build the action
        # icon = QIcon(os.path.dirname(__file__) + "/icons/rfda.png")
        # self.action_rfda = QAction(QIcon(icon), 'RFDA Conversions', self.iface.mainWindow())
        # self.action_rfda.triggered.connect(self.dlg_rfda.show)
        # self.act_menu_l.append(self.action_rfda) #add for cleanup
        # 
        # #add to the menu
        # self.iface.addPluginToMenu(self.menu_name, self.action_rfda)
        # 
        # #=======================================================================
        # # dikes
        # #=======================================================================
        # icon = QIcon(os.path.dirname(__file__) + "/icons/dike.png")
        # self.action_dikes = QAction(QIcon(icon), 'Dike Fragility Mapper', self.iface.mainWindow())
        # self.action_dikes.triggered.connect(self.dlg_dikes.launch)
        # self.act_menu_l.append(self.action_dikes) #add for cleanup
        # 
        # #add to the menu
        # self.iface.addPluginToMenu(self.menu_name, self.action_dikes)
        # 
        # #=======================================================================
        # # styles
        # #=======================================================================
        # icon = QIcon(os.path.dirname(__file__) + "/icons/paint-palette.png")
        # self.action_styles = QAction(QIcon(icon), 'Add Styles', self.iface.mainWindow())
        # self.action_styles.triggered.connect(self.load_style_xml)
        # self.act_menu_l.append(self.action_styles) #add for cleanup
        # 
        # #add to the menu
        # self.iface.addPluginToMenu(self.menu_name, self.action_styles)
        # 
        # #=======================================================================
        # # sensitivity analysis
        # #=======================================================================
        # icon = QIcon(os.path.dirname(__file__) + "/icons/target.png")
        # self.action_sensi = QAction(QIcon(icon), 'Sensitivity Analysis', self.iface.mainWindow())
        # self.action_sensi.triggered.connect(self.dlg_sensi.launch)
        # self.act_menu_l.append(self.action_sensi)
        # self.iface.addPluginToMenu(self.menu_name, self.action_sensi)
        #=======================================================================
        
        
        
    def webConnect(self):
        """no GUI here.. just executing a script"""
        self.logger('pushed webConnect')
        
        from misc.webConnections import WebConnect
        
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
        from hlpr.plug import plugLogger
        log = plugLogger(self)
        
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
                self.iface.removePluginMenu(self.menu_name, action)
            except Exception as e:
                self.logger('failed to unload action w/ \n    %s'%e)
                
        #=======================================================================
        # custom unload actions
        #=======================================================================
        

            
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
        
