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
#from .resources import *


#import weakref
import os.path
from qgis.core import Qgis, QgsMessageLog, QgsExpression



#===============================================================================
# custom imports
#===============================================================================

"""
relative references seem to work in Qgis.. but IDE doesnt recognize
"""
from .hlpr.plug import plugLogger
from .hlpr.exceptions import QError as Error


from .build.dialog import BuildDialog
from .model.dialog import ModelDialog
from .results.dialog import ResultsDialog
from .sensi.dialog import SensiDialog

from .misc.rfda.dialog import RfdaDialog
from .misc.dikes.dialog import DikesDialog
from .misc.webConnections import WebConnectAction
from. misc.layerStyles import StylesAction




class CanFlood(object):
    """
    called by __init__.py 's classFactor method
    """
    menu_name = "CanFlood"
 
 
    
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
            'webConectinos':WebConnectAction,
            'styles'    :StylesAction
            
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
        """todo: only construct these on first pass"""
        for attn, DialogClass in self.dialogPars_d.items():
            try:
                self.dialogs_d[attn] = DialogClass(self.iface, session=self)
            except Exception as e:
                raise Error('failed to load \'%s\' w/ \n    %s'%(attn, e))
                

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None
        
        self.pars_dir = os.path.join(os.path.dirname(__file__), '_pars')
        self.icon_dir = os.path.join(os.path.dirname(__file__), 'icons')
        
        
        #=======================================================================
        # logger
        #=======================================================================
        self.logger=plugLogger(self, log_nm='CanFlood')
        


    def initGui(self): #add UI elements to Qgis
        """
        called on Qgis Load?
        
        """
        log = self.logger.getChild('initGui')
        #=======================================================================
        # configure toolbar
        #=======================================================================
        """Create the menu entries and toolbar icons inside the QGIS GUI."""  
        toolbar = self.iface.addToolBar(self.menu_name) #build a QToolBar
        toolbar.setObjectName(self.menu_name)
        
        #=======================================================================
        # setup actions
        #=======================================================================
        self.actions_d = {'toolbar':dict(), 'menu':dict()}
 
        cnt = 0
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
                    
                
                self.actions_d[wrkr.icon_location][attn] = action
                cnt+=1
                
            except Exception as e:
                raise Error('failed to build action for \'%s\' w/ \n    %s'%(attn, e))
            
        #wrap
        self.toolbar=toolbar
        log.debug('attached %i actions'%cnt)
 

    
    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI.
        called when user unchecks the plugin
        """
        log=self.logger.getChild('unload')
        #=======================================================================
        # unload toolbars
        #=======================================================================

        self.iface.mainWindow().removeToolBar( self.toolbar )
        del self.toolbar
 

        #=======================================================================
        # unload menu
        #=======================================================================
        d = self.actions_d['menu']
        """not sure if this is needed"""
        for attn, action in d.items():
            self.iface.removePluginMenu(self.menu_name, action)
 
        log.debug('unloaded %i from the menu: %s'%(len(d), list(d.keys())))
        
        #=======================================================================
        # unload expression functions
        #=======================================================================
        from canflood.misc.expressionFunctions import all_funcs_l
        for func in all_funcs_l:
            QgsExpression.unregisterFunction(func.name())
            
        log.debug('unloaded %i expression functions'%len(all_funcs_l))
            
 
 
        
