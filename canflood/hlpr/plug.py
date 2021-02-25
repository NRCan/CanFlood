'''
Created on Feb. 25, 2020

@author: cefect


helper functions for use in plugins
'''



#==============================================================================
# imports------------
#==============================================================================
#python
import logging, configparser, datetime, sys, os, types
import pandas as pd

#Qgis imports
from qgis.core import QgsVectorLayer, Qgis, QgsProject, QgsLogger, QgsMessageLog, QgsMapLayer

#pyQt
from PyQt5.QtWidgets import QApplication, QWidget, QInputDialog, QLineEdit, QFileDialog, QPushButton
#from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QAbstractTableModel
from PyQt5 import QtCore

#==============================================================================
# custom imports
#==============================================================================

from hlpr.exceptions import QError as Error
from hlpr.Q import MyFeedBackQ, Qcoms
from hlpr.basic import force_open_dir

#==============================================================================
# classes-----------
#==============================================================================
class QprojPlug(Qcoms): #baseclass for plugins
    
    tag='scenario1'
    overwrite=True
    wd = ''
    progress = 0
    
    
    
    """not a great way to init this one
    Plugin classes are only initilaizing the first baseclass
    def __init__(self):
        self.logger = logger()"""
    
    def qproj_setup(self,
                    plogger=None,
                    ): #project inits for Dialog Classes

        if plogger is None: plogger = logger(self) 
        
        self.logger = plogger
        self.qproj = QgsProject.instance()
        
        self.crs = self.qproj.crs()
        
        """connect to UI's progress bar
            expects 'progressBar' as the widget name
            start feedback instance"""
            
        self.setup_feedback(progressBar = self.progressBar,
                            feedback = MyFeedBackQ())
        
        #=======================================================================
        # default directories
        #=======================================================================

        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars')
        assert os.path.exists(self.pars_dir)

        

    def get_cf_fp(self):
        cf_fp = self.lineEdit_cf_fp.text()
        
        if cf_fp is None or cf_fp == '':
            raise Error('need to specficy a control file path')
        if not os.path.exists(cf_fp):
            raise Error('need to specficy a valid control file path')
        
        if not os.path.splitext(cf_fp)[1] == '.txt':
            raise Error('unexpected extension on Control File')
        
        return cf_fp
    
    def get_wd(self):
        wd = self.lineEdit_wd.text()
        
        if wd is None or wd == '':
            raise Error('need to specficy a Working Directory')
        if not os.path.exists(wd):
            os.makedirs(wd)
            self.logger.info('built new working directory at:\n    %s'%wd)
        
        
        return wd
    
    def browse_button(self, 
                      lineEdit, #text bar where selected directory should be displayed
                      prompt = 'Select Directory', #title of box
                      qfd = QFileDialog.getExistingDirectory, #dialog to launch
                      ):
        
        #get the currently displayed filepath
        fp_old = lineEdit.text()
        
        #change to default if nothing useful is there
        if not os.path.exists(fp_old):
            fp_old = os.getcwd()
        
        #launch the dialog and get the new fp from the user
        fp = qfd(self, prompt, fp_old)
        
        #just take the first
        if len(fp) == 2:
            fp = fp[0]
        
        #see if they picked something
        if fp == '':
            self.logger.error('user failed to make a selection. skipping')
            return 
        
        #update the bar
        lineEdit.setText(fp)
        
        self.logger.info('user selected: %s'%fp)
        
    def fileSelect_button(self, #
                      lineEdit, #text bar where selected directory should be displayed
                      caption = 'Select File', #title of box
                      path = None,
                      filters = "All Files (*)",
                      qfd = QFileDialog.getOpenFileName, #dialog to launch
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        if path is None:
            path = os.getcwd()
        
        if not os.path.exists(path):
            path = os.getcwd()
            
        #ask the user for the path
        """
        using the Dialog instance as the QWidge parent
        """
        self.logger.info(filters)
        
        fp = qfd(self, caption, path, filters)
        
        #just take the first
        if len(fp) == 2:
            fp = fp[0]
        
        #see if they picked something
        if fp == '':
            self.logger.warning('user failed to make a selection. skipping')
            return 
        
        #update the bar
        lineEdit.setText(fp)
        
        self.logger.info('user selected: \n    %s'%fp)
        
    def mfcb_connect(self, #helper to update a field combo box
                           mfcb, #mFieldComboBox
                           layer, #layer to set in the combo box
                           fn_str = None, #optional field name for auto setting
                           ):
        
        mfcb.clear()
        if isinstance(layer, QgsVectorLayer):
            try:
                mfcb.setLayer(layer)
                
                #try and match
                for field in layer.fields():
                    if fn_str in field.name():
                        break
                    
                mfcb.setField(field.name())
                
            except Exception as e:
                self.logger.warning('failed set current layer w/ \n    %s'%e)
        else:
            self.logger.warning('failed to get a vectorlayer')
            
        return 
    

    def set_overwrite(self): #action for checkBox_SSoverwrite state change
        if self.checkBox_SSoverwrite.isChecked():
            self.overwrite= True
        else:
            self.overwrite= False
            
        self.logger.push('overwrite set to %s'%self.overwrite)
        
    def field_selectM(self, #select mutliple fields
                      vlay):
        """
        TODO: mimc the Qgis Algo multiple feature selection dialog
        """
        
        class NewDialog(QWidget):
            def __init__(self):
                super().__init__()
                
                self.initUI()
                
            def initUI(self):      
    
                
                self.le = QLineEdit(self)
                self.le.move(130, 22)
                
                self.setGeometry(300, 300, 290, 150)
                self.setWindowTitle('Multiple Selection')
                self.show()
                
    def setup_comboBox(self, #helper for setting up a combo box with a default selection
                       comboBox,
                       selection_l, #list of values to set as selectable options
                       default = 'none', #default selection string ot set
                       
                       ):
        
        assert isinstance(selection_l, list)
        
        assert default in selection_l
        
        comboBox.clear()
        #set the selection
        comboBox.addItems(selection_l)
        
        #set the default
        index = comboBox.findText(default, Qt.MatchFixedString)
        if index >= 0:
            comboBox.setCurrentIndex(index)
            
    def _connect_wdir(self, #connect the workint direcotry buttons
                      browseButton, openButton, lineEdit,
                      default_wdir = None
                      ):
        #=======================================================================
        # connect buttons
        #=======================================================================
        #Working Directory browse            
        browseButton.clicked.connect(
                lambda: self.browse_button(lineEdit, 
                                           prompt='Select Working Directory',
                                      qfd = QFileDialog.getExistingDirectory)
                )

        #WD Open
        openButton.clicked.connect(
                lambda: force_open_dir(lineEdit.text()))
        
        #=======================================================================
        # set default
        #=======================================================================
        if not default_wdir is None:
            lineEdit.setText(default_wdir)
            
            if not os.path.exists(default_wdir): os.makedirs(default_wdir)
        

class logger(object): #workaround for qgis logging pythonic
    """
    plugin logging
    

    0.4.1
        log messages sent to 2 places based on level
            
    
    """
    log_tabnm = 'CanFlood' # qgis logging panel tab name
    
    log_nm = 'cf' #logger name
    
    def __init__(self, parent,
                 statusQlab = None, #Qlabel widget to duplicate push messages
                 log_nm = None,
                 ):
        #attach
        self.parent = parent
        
        #nest the name
        """theres probably a more elegant way to do this..."""
        if  log_nm is None: #normal calls
            self.log_nm = '%s.%s'%(self.log_nm, self.parent.__class__.__name__)
        else: #getChild calls
            self.log_nm = log_nm
        
        
        
        self.iface = parent.iface
        
        self.statusQlab = statusQlab
        
        """dont want to call this during getChild
        self.debug('logger initilized for %s at %s'%(parent.__class__.__name__, datetime.datetime.now()))"""
        
    def getChild(self, new_childnm):
        
        #build a new logger
        child_log = logger(self.parent, 
                           statusQlab=self.statusQlab,
                           log_nm = '%s.%s'%(self.parent.logger.log_nm, new_childnm)
                           )
        

        
        return child_log
    
    def setLevel(self,*args):
        """
        todo: have this behave more like a real python logger
        """
        pass 
        
    def info(self, msg):
        self._loghlp(msg, Qgis.Info, push=False, status=True)


    def debug(self, msg):
        self._loghlp(msg, -1, push=False, status=False)
        """
        msg = '%s: %s'%(self.log_nm, msg_raw)
        QgsLogger.debug(msg)
        """
        
    def warning(self, msg):
        self._loghlp(msg, Qgis.Warning, push=False)

        
    def push(self, msg):
        self._loghlp(msg, Qgis.Info, push=True)

    def error(self, msg):
        self._loghlp(msg, Qgis.Critical, push=True)
        
    def _loghlp(self, #helper function for generalized logging
                msg_raw, qlevel, 
                push=False,
                status=False):
        """
        QgsMessageLog writes to the message panel
            optionally, users can enable file logging
            this file logger 
        """

        #=======================================================================
        # send message based on qlevel
        #=======================================================================
        msgDebug = '%s    %s: %s'%(datetime.datetime.now().strftime('%d-%H.%M.%S'), self.log_nm,  msg_raw)
        if qlevel < 0: #file logger only
            
            QgsLogger.debug('D_%s'%msgDebug)
            push, status = False, False #should never trip
        else:#console logger
            msg = '%s:   %s'%(self.log_nm, msg_raw)
            QgsMessageLog.logMessage(msg, self.log_tabnm, level=qlevel)
            QgsLogger.debug('%i_%s'%(qlevel, msgDebug)) #also send to file
        
        
        
        #Qgis bar
        if push:
            self.iface.messageBar().pushMessage(self.log_tabnm, msg_raw, level=qlevel)
        
        #Optional widget
        if status or push:
            if not self.statusQlab is None:
                self.statusQlab.setText(msg_raw)
                
class pandasModel(QAbstractTableModel):
    """from here:
    https://learndataanalysis.org/display-pandas-dataframe-with-pyqt5-qtableview-widget/
    
    this is handy for displaying with a QTableView
        NOTE: QTableView wont display the df.index
    """
    def __init__(self, data):
        assert isinstance(data, pd.DataFrame)
        QAbstractTableModel.__init__(self)
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parnet=None):
        return self._data.shape[1]

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid():
            if role == Qt.DisplayRole:
                return str(self._data.iloc[index.row(), index.column()])
            if role == Qt.ToolTipRole:
                return str(self._data.iloc[index.row(), index.column()])
        return None

    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            """expanded to handle empty dataframes"""
            try:
                return self._data.columns[col]
            except:
                return None
        return None
    

def bind_layersListWidget(widget, #instanced widget
                          log,
                          layerType=None, #optional layertype to enforce
                          iface=None,
                          
                         ):
    """
    because Qgis passes instanced widgets, need to bind any new methods programatically
    """

        
    widget.iface = iface
    #===========================================================================
    # populating and setting selection
    #===========================================================================
    def populate_layers(self, layers=None):
        if layers is None:
            #get all from the project
            layers = [layer for layer in QgsProject.instance().mapLayers().values()]
            
            #apply filters
            if not layerType is None:
                layers = self._apply_filter(layers)
                
        self.clear()
        assert isinstance(layers, list), 'bad type on layeres: %s'%type(layers)
        
        #add all these
        for layer in layers:
            e = layer.name()
            self.addItem(e)
            #print('adding \'%s\''%e):
        del layers
            
    def _apply_filter(self, layers):
        return [rl for rl in layers if rl.type()==layerType]
            
    def select_visible(self):
        #print('selecint only visible layers')
        lays_l = self.iface.mapCanvas().layers()
        self._set_selection_byName([l.name() for l in lays_l])
        
    def select_canvas(self):
 
        lays_l = self.iface.layerTreeView().selectedLayers()
        #log.info('setting selection to %i layers from layerTreeView'%len(lays_l))
        self._set_selection_byName([l.name() for l in lays_l])
        
    def _set_selection_byName(self, names_l):
        for indx in range(0, self.count()):
            if self.item(indx).text() in names_l:
                self.item(indx).setSelected(True)
            else:
                self.item(indx).setSelected(False)
            
    #===========================================================================
    # retriving selection
    #===========================================================================
    def get_selected_layers(self):
        qproj = QgsProject.instance()
        #collected selected text
        nms_l = [e.text() for e in self.selectedItems()]
        
        assert len(nms_l)>0, 'no selection!'
        #retrieve layers from canvas
        lays_d = {nm:qproj.mapLayersByName(nm) for nm in nms_l}
        
        #check we only got one hit
        d = dict()
        for k,hits in lays_d.items(): 
            assert len(hits)==1, 'failed to match \'%s\''%k
            
            lay = hits[0]
            assert isinstance(lay, QgsMapLayer), 'bad type on %s: %s'%(k, type(lay))
            
            d[k] = lay
        
        #drop to singular elements
        
        return d
        
        
    #===========================================================================
    # bind them
    #===========================================================================
    for fName in ['populate_layers', '_apply_filter', 'select_visible', 'select_canvas', 
                  '_set_selection_byName', 'get_selected_layers']:
        setattr(widget, fName, types.MethodType(eval(fName), widget)) 
        
def bind_MapLayerComboBox(widget, #add some bindings to layer combo boxes
                          iface=None, layerType=None): 
    
    
    #default selection
    if not layerType is None:
        widget.setFilters(layerType)
    widget.setAllowEmptyLayer(True)
    widget.setCurrentIndex(-1) #set selection to none
    
    #===========================================================================
    # define new methods
    #===========================================================================
    def attempt_selection(self, layName):
        
        qproj = QgsProject.instance()
        layers = qproj.mapLayersByName(layName)
        
        if len(layers)>0:
            self.setLayer(layers[0])
            
    #===========================================================================
    # bind functions
    #===========================================================================
    for fName in ['attempt_selection']:
        setattr(widget, fName, types.MethodType(eval(fName), widget)) 
#==============================================================================
# functions-----------
#==============================================================================
         
def qtbl_get_df( #extract data to a frame from a qtable
        table, 
            ):
    """
    for indx in range(0, table.rowCount()+1):
        print(indx)
        print(table.horizontalHeaderItem(indx).text())
    """

    #get lables    
    coln_l = qtlb_get_axis_l(table, axis=1)
    rown_l = qtlb_get_axis_l(table, axis=0)
    


    tmp_df = pd.DataFrame( 
                columns=coln_l, # Fill columnets
                index=rown_l # Fill rows
                ) 

    for i in range(len(rown_l)):
        for j in range(len(coln_l)):
            qval = table.item(i, j)
            
            if not qval is None:
                tmp_df.iloc[i, j] = qval.text()
                
    #assert len(tmp_df.columns)>1

    return tmp_df


def qtlb_get_axis_l(table, axis=0): #get axis lables from a qtable
    
    if axis == 1: #column names
        q_l  = [table.horizontalHeaderItem(cnt) for cnt in range(0, table.columnCount())]
    elif axis == 0: #row names
        q_l  = [table.verticalHeaderItem(cnt) for cnt in range(0, table.rowCount())]
        
    """
    
    """
    l = []
    #get data

    for qval in q_l:

        if qval is None:
            l.append('UnNamed')
        else:
            l.append(qval.text())
        
    return l
            

if __name__ =="__main__": 
    
    class Example(QWidget):
    
        def __init__(self):
            super().__init__()
            
            self.initUI()
            
            
        def initUI(self):      
    
            self.btn = QPushButton('Dialog', self)
            self.btn.move(20, 20)
            self.btn.clicked.connect(self.showDialog)
            
            self.le = QLineEdit(self)
            self.le.move(130, 22)
            
            self.setGeometry(300, 300, 290, 150)
            self.setWindowTitle('Input dialog')
            self.show()
            
            
        def showDialog(self):
            
            text, ok = QInputDialog.getText(self, 'Input Dialog', 
                'Enter your name:')
            
            if ok:
                self.le.setText(str(text))
            
    app = QApplication(sys.argv)
    ex = Example()
    sys.exit(app.exec_())
            
            
    
    print('finisshed')
        