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
from qgis.gui import QgisInterface

#pyQt
from PyQt5.QtWidgets import QFileDialog, QGroupBox, QComboBox
from PyQt5.QtGui import QStandardItem, QStandardItemModel
from PyQt5.QtCore import Qt, QAbstractTableModel, QObject 
from PyQt5 import QtCore


#==============================================================================
# custom imports
#==============================================================================

from hlpr.exceptions import QError as Error
from hlpr.Q import MyFeedBackQ, Qcoms
import hlpr.Q
from hlpr.basic import force_open_dir
from hlpr.plt_qt import PltWindow

#==============================================================================
# classes-----------
#==============================================================================
class QprojPlug(Qcoms): #baseclass for plugins
    
    groupName = 'CanFlood' #default group for loading layers to canvas
    
    tag='scenario1'
    overwrite=True
    wd = ''
    progress = 0
    
    
    loadRes = False #whether to load layers to canvas
    
    plt_window = False #control whether to launch the plot window
    
    
    
    
    """not a great way to init this one
    Plugin classes are only initilaizing the first baseclass
    def __init__(self):
        self.logger = logger()"""
    
    def qproj_setup(self,
                    iface = None,
                    plogger=None, #alternate logger for standalone tests
                    session=None, #main CanFlood.CanFlood session worker 
 
                    ): #project inits for Dialog Classes

        #=======================================================================
        # attacyhments
        #=======================================================================
        self.session=session #used for passing between windows
        
        self.launch_actions = dict() #container of actions to execute when 'launch' is pressed

        
        #=======================================================================
        # interface
        #=======================================================================
        if not iface is None:
            """only checking real iface for compatabilitgy"""
            assert isinstance(iface, QgisInterface), 'got bad iface type: %s'%type(iface)
        self.iface = iface
            
        #=======================================================================
        # logger
        #=======================================================================
        if plogger is None: 
            """this needs iface to be set"""
            plogger = logger(self) 
        
        self.logger = plogger
            
        
        #=======================================================================
        # Qsetupts
        #=======================================================================
        self.qproj = QgsProject.instance()

            
        
        self.crs = self.qproj.crs()
        
        self.layerTree = QgsProject.instance().layerTreeRoot() #for groups
        
        """connect to UI's progress bar
            expects 'progressBar' as the widget name
            start feedback instance"""
            
        self.setup_feedback(progressBar = self.progressBar,
                            feedback = MyFeedBackQ())
        

        self.set_vdrivers()
        
        #set some dummies for children
        self.qap = None #I dont think this ever gets referenced
        self.algo_init=True
        
        #=======================================================================
        # default directories
        #=======================================================================

        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars')
        assert os.path.exists(self.pars_dir)

    def launch(self): #placeholder for launching the dialog
        """allows children to customize what happens when called"""
        log = self.logger.getChild('launch')
        #=======================================================================
        # #customs
        #=======================================================================
        """
        lets each dialog attach custom functions when they are launched
            useful for automatically setting some dialog boxes
            
        prioritizinmg inheritanve over customs
        """
        for fName, f in self.launch_actions.items():
            log.debug('%s: %s'%(fName, f))
            try:
                f()
            except Exception as e:
                log.warning('failed to execute \'%s\' w/ \n    %s'%(fName, e))
        
        #=======================================================================
        # inherit from other tools
        #=======================================================================
        #try and set the control file path from the session if there
        if os.path.exists(self.session.cf_fp):
            #set the control file path
            self.lineEdit_cf_fp.setText(self.session.cf_fp)
            
            #set the working directory
            newdir = os.path.join(os.path.dirname(self.session.cf_fp))
            assert os.path.exists(newdir), 'this should  exist...%s'%newdir
            self.lineEdit_wdir.setText(newdir)
            
        #default catch for working directory
        if self.lineEdit_wdir.text() == '':
            newdir = os.path.join(os.getcwd(), 'CanFlood')
            if not os.path.exists(newdir): os.makedirs(newdir)
            self.lineEdit_wdir.setText(newdir)
            
            
        #inventory vector layer
        if isinstance(self.session.finv_vlay, QgsVectorLayer):
            if hasattr(self, 'comboBox_JGfinv'): #should just skip the Build
                self.comboBox_JGfinv.setLayer(self.session.finv_vlay)
                
                

        
        self.show()



    
    def _load_toCanvas(self,  #helper to load a layers to canvas w/ some reporting
                       layers, 
                       
                       groupName=None, #optional group name to load to
                       style_fn = None, #optional qml styule file name to apply
                       logger=None, 
                       ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        """forcing layers into a group"""
        if logger is None: logger=self.logger
        log=logger.getChild('load_toCanvas')
        if groupName is None: groupName = self.groupName
        if style_fn == '': style_fn=None
        log.debug('loading \'%s\': %s'%(type(layers), layers))
        #=======================================================================
        # precheck
        #=======================================================================
        if not self.loadRes: log.warning('load results to canvas control mismatch!')
        
        #=======================================================================
        # groups
        #=======================================================================
        if not groupName is None:
            group = self.layerTree.findGroup(groupName) #search
            if group is None: #nothign found.. add the group
                group = self.layerTree.addGroup(groupName)
                log.debug('group not found.. added \'%s\''%groupName)
        else:
            group = None
            
        def add_layer(lay):
            assert isinstance(lay, QgsMapLayer), 'passed bad layer\'%s\''%lay
            if not group is None:
                group.addLayer(lay)
                self.qproj.addMapLayer(lay, False) #add tot he project, but hide
            else:
                self.qproj.addMapLayer(lay, True) #just add to teh selected group
                
        
        #=======================================================================
        # #load
        #=======================================================================
        if isinstance(layers, list):
            for layer in layers:
                add_layer(layer)

            #report
            layNames = [lay.name() for lay in layers]
            log.info('loaded %i layers: %s'%(len(layNames), layNames))
            
        elif isinstance(layers, QgsMapLayer):
            add_layer(layers)
            log.info('laoded \'%s\' to project'%layers.name())
            layers = [layers] #throw it into a list for below
            
        else:
            raise Error('unrecognized layer container type: %s'%type(layers))
            
        #=======================================================================
        # stylieze
        #=======================================================================
        if not style_fn is None:

            style_fp = os.path.join(self.pars_dir, 'qmls', style_fn)
            assert os.path.exists(style_fp)
            for layer in layers:
                layer.loadNamedStyle(style_fp)
                layer.triggerRepaint()
            
        return
    
    
    #===========================================================================
    # widget setup----------
    #===========================================================================
    
    def browse_button(self, #browse to a directory
                      lineEdit, #text bar where selected directory should be displayed
                      prompt = 'Select Directory', #title of box
                      qfd = QFileDialog.getExistingDirectory, #dialog to launch
                      ):
        """
        TODO: migrate to standalone function?
        see fileSelect_button() for borwsing to a file
        """
        
        
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
            self.logger.debug('user failed to make a selection. skipping')
            return 
        
        #update the bar
        lineEdit.setText(fp)
        
        self.logger.debug('user selected: %s'%fp)
        
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
                           fn_no_str = None, #optional field name to EXCVLUDE from auto setting
                           ):
        """
        TODO: migrate to bind function
        """
        log = self.logger.getChild('mfcb_connect')
        mfcb.clear()
        if isinstance(layer, QgsVectorLayer):
            try:
                mfcb.setLayer(layer)
                
                #try and match
                for field in layer.fields():
                    if not fn_no_str is None:
                        if field.name()==fn_no_str: continue #keep looking
                        
                    if fn_str in field.name():
                        break
                    
                mfcb.setField(field.name())
                
            except Exception as e:
                log.warning('failed set current layer w/ \n    %s'%e)
        else:
            log.debug('passed layer w/ unrecognized type: %s'%(type(layer)))
            
        return 
    


        

                
    def setup_comboBox(self, #helper for setting up a combo box with a default selection
                       comboBox,
                       selection_l, #list of values to set as selectable options
                       default = None, #default selection string ot set
                       
                       ):
        """
        TODO: change this to bind to the combo box
        """
        
        assert isinstance(selection_l, list)
        

        
        comboBox.clear()
        #set the selection
        comboBox.addItems(selection_l)
        
        #set the default
        if not default is None:
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
            
    #===========================================================================
    # run function helpers------
    #===========================================================================
    def get_cf_fp(self):
        """"
        TODO: migrate all of these to _set_setup
        """
        cf_fp = self.lineEdit_cf_fp.text()
        
        if cf_fp is None or cf_fp == '':
            raise Error('need to specficy a control file path')
        if not os.path.exists(cf_fp):
            raise Error('need to specficy a valid control file path')
        
        if not os.path.splitext(cf_fp)[1] == '.txt':
            raise Error('unexpected extension on Control File')
        
        return cf_fp

    def get_cf_par(self, #load a parameter value from a controlFile path
                      cf_fp, #control file path
                      sectName='results_fps',
                      varName = 'r_ttl',
                      varType = str,
                      logger=None,
                      ):
        """
        wrapper for  _get_from_cpar()
            but loads the control file each time and 
        """
        #handle the default empty selection
        if varName=='':return 'no selection'
        if cf_fp == '':return 'no selection'
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('get_cf_par')
        
        #=======================================================================
        # load the control file
        #=======================================================================

        assert os.path.exists(cf_fp), 'provided parameter file path does not exist \n    %s'%cf_fp

        pars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.debug('reading parameters from \n     %s'%pars.read(cf_fp))
        
        #=======================================================================
        # get the value
        #=======================================================================
        """
        see _get_from_cpar()  for fancy typesetting
            seems like we should only be pulling strings here...
        """
        return varType(pars[sectName][varName])
    
    def _set_setup(self, set_cf_fp=True,): #attach parameters from setup tab
        
        inherit_fieldNames = ['logger', 'out_dir','tag', 'overwrite', 'absolute_fp', 'feedback']
        
        #secssion controls
        self.tag = self.linEdit_ScenTag.text()
        self.out_dir = self.lineEdit_wdir.text()
        
        assert not self.out_dir == '', 'must specify a working directory!'
        if not os.path.exists(self.out_dir): os.makedirs(self.out_dir)
        
        if set_cf_fp:

            #pull from the line
            self.cf_fp = self.lineEdit_cf_fp.text()
            assert not self.cf_fp=='', 'must specify a control file!'
            assert os.path.exists(self.cf_fp), 'got invalid controlFile path: %s'%self.cf_fp
            
            inherit_fieldNames.append('cf_fp')
            
            self.session.cf_fp = self.cf_fp #set for other dialogs

        
        #file behavior
        self.overwrite=self.checkBox_SSoverwrite.isChecked()
        self.absolute_fp = self.radioButton_SS_fpAbs.isChecked()
        
        #layer loading
        self.groupName = 'CanFlood.%s'%self.tag
        self.inherit_fieldNames = inherit_fieldNames
        
        #plot window
        if hasattr(self, 'radioButton_s_pltW'):
            self.plt_window = self.radioButton_s_pltW.isChecked()
            
        #qgis handles
        self.crs = self.qproj.crs()
        self.crsid = self.crs.authid()
        
        self._upd_qd() #update the q handles
        
            
    def _check_finv(self, logger=None): #check the finv and some paramter logic
        """
        see also Model.check_finv() for data level checks
        """
        if logger is None: logger=self.logger
        log=logger.getChild('_check_finv')
        #=======================================================================
        # selection checks
        #=======================================================================
        assert not self.cid is None, 'must specify a valid cid'
        assert isinstance(self.finv_vlay, QgsVectorLayer), 'must select a VectorLayer for the finv'
        
        
        #=======================================================================
        # data checks
        #=======================================================================
        #CRS
        assert self.finv_vlay.crs()==self.qproj.crs(), 'finv CRS (%s) does not match projects (%s)'%(
            self.finv_vlay.crs(), self.qproj.crs())
                
        
                
        #cid in the fields
        fields_d = {f.name():f for f in self.finv_vlay.fields()}
        assert self.cid in fields_d, 'specified cid not found on finv'
        
        #field type
        assert 'int' in fields_d[self.cid].typeName().lower(), \
        'cid field \'%s\' must be integer type not \'%s\''%(
            self.cid, fields_d[self.cid].typeName())
                
        #unique values
        cid_ser = hlpr.Q.vlay_get_fdata(self.finv_vlay, fieldn=self.cid, fmt='df', logger=log)
        boolidx = cid_ser.duplicated(keep=False)
        if boolidx.any():
            log.debug('duplicated values \n%s'%cid_ser[boolidx])
            
            raise Error('passed finv cid=\'%s\' values contain %i duplicates... see logger'%(
                self.cid, boolidx.sum()))
        


            
        
            
        
    #===========================================================================
    # OUTPUTS------------
    #===========================================================================
    def output_fig(self, fig,
                   
                   plt_window=None, #whether to launch the matplotlib  window
                   
                   #file controls
                   out_dir = None, 
                   overwrite=None,
                   fname = None, #filename
                   
                   #figure write controls
                 fmt='svg', 
                  transparent=True, 
                  dpi = 150,
                  logger=None,
                  ):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.out_dir
        if overwrite is None: overwrite = self.overwrite
        if plt_window is None: plt_window=self.plt_window
        if logger is None: logger=self.logger
        log = logger.getChild('output_fig')
        
        #=======================================================================
        # precheck
        #=======================================================================
        """avoiding importing matplotlib here"""
        #assert isinstance(fig, self.matplotlib.figure.Figure)
        log.debug('plt_window=%s on  %s'%(plt_window, fig))
        #======================================================================
        # save file
        #======================================================================
        if not plt_window:
            #file setup
            if fname is None:
                try:
                    fname = fig._suptitle.get_text()
                except:
                    fname = self.name
                
            out_fp = os.path.join(out_dir, '%s.%s'%(fname, fmt))
                
            if os.path.exists(out_fp): assert overwrite
    
                
            #write the file
            try: 
                fig.savefig(out_fp, dpi = dpi, format = fmt, transparent=transparent)
                log.info('saved figure to file:   %s'%out_fp)
            except Exception as e:
                raise Error('failed to write figure to file w/ \n    %s'%e)
            
            return out_fp
            
        #=======================================================================
        # launch window
        #=======================================================================
        else:
            
            app = PltWindow(fig, out_dir=out_dir)
            app.show()
            log.info('launched matplotlib window on %s'%fig._suptitle.get_text())
            app.activateWindow()
            app.raise_()
            
        
        
        

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
        
        if hasattr(self.parent, 'logger'):
            log_nm = '%s.%s'%(self.parent.logger.log_nm, new_childnm)
        else:
            log_nm = new_childnm
        
        #build a new logger
        child_log = logger(self.parent, 
                           statusQlab=self.statusQlab,
                           log_nm=log_nm)
        

        
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
        """similar behavior to raising a QError.. but without throwing the execption"""
        self._loghlp(msg, Qgis.Critical, push=True)
        
    def _loghlp(self, #helper function for generalized logging
                msg_raw, qlevel, 
                push=False, #treat as a push message on Qgis' bar
                status=False, #whether to send to the status widget
                ):
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
            try:
                self.iface.messageBar().pushMessage(self.log_tabnm, msg_raw, level=qlevel)
            except:
                QgsLogger.debug('failed to push to interface') #used for standalone tests
        
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
    
#===============================================================================
# widget binds-------------
#===============================================================================
class ListModel(QStandardItemModel): #wrapper for list functions with check boxes
    
    def add_checkable_data(self, data_l):
        
        for item in data_l:
            item.setCheckable(True)
            item.setCheckState(Qt.Unchecked)
            self.appendRow(item)
            
    def get_items(self):
        return [self.item(i) for i in range(self.rowCount())]
    def get_checked(self, state=Qt.Checked): #retrieve all items taht are checked
        return [i for i in self.get_items() if i.checkState()==state]

    def set_checked_byVal(self, val_l): #assign check state to items based on those matching the values
        for item in self.get_items():
            if item.text() in val_l:
                item.setCheckState(Qt.Checked)
            else:
                item.setCheckState(Qt.Unchecked)
                
    def set_checked_all(self, state=Qt.Unchecked):
        for item in self.get_items():
            item.setCheckState(state)




def bind_layersListWidget(widget, #instanced widget
                          log,
                          layerType=None, #optional layertype to enforce
                          iface=None,
                          
                         ):
    """
    because Qgis passes instanced widgets, need to bind any new methods programatically
    """
    #assert not iface is None
        
    widget.iface = iface
    widget.layerType = layerType
    widget.setModel(ListModel())
    
    #===========================================================================
    # populating and setting selection
    #===========================================================================
    def populate_layers(self, layers=None):
        if layers is None:
            #get all from the project
            layers = [layer for layer in QgsProject.instance().mapLayers().values()]
            
            #apply filters
            if not self.layerType is None:
                layers = self._apply_filter(layers)
                
        
        assert isinstance(layers, list), 'bad type on layeres: %s'%type(layers)
        model = self.model()
        
        model.clear()
        
        model.add_checkable_data([QStandardItem(l.name()) for l in layers])

            
    def _apply_filter(self, layers):
        return [rl for rl in layers if rl.type()==self.layerType]
            
    def select_visible(self):
        #print('selecint only visible layers')
        lays_l = self.iface.mapCanvas().layers()
        self.model().set_checked_byVal([l.name() for l in lays_l])
        
    def select_canvas(self):
 
        lays_l = self.iface.layerTreeView().selectedLayers()
        #log.info('setting selection to %i layers from layerTreeView'%len(lays_l))
        self.model().set_checked_byVal([l.name() for l in lays_l])
        

    def clear_checks(self):
        self.model().set_checked_all()
        
            
    def check_all(self):
        self.model().set_checked_all(state=Qt.Checked)
        
    def check_byName(self, layName_l):
        self.model().set_checked_byVal(layName_l)
            
    #===========================================================================
    # retriving selection
    #===========================================================================
    def get_selected_layers(self):
        qproj = QgsProject.instance()

        items = self.model().get_checked() #names of layers checked by user
        nms_l = [item.text() for item in items]
        
        assert len(nms_l)>0, 'no selection!'
        
        
        #retrieve layers from canvas
        lays_d = {nm:qproj.mapLayersByName(nm) for nm in nms_l} 
        
        
        
        
        #check we only got one hit
        d = dict()
        for k,hits_all in lays_d.items():
            
            """when a raster and vector layer have the same name"""
            hits = self._apply_filter(hits_all) #remove any not matching the type
            
            
            assert not len(hits)>1, 'matched multiple layers for \'%s\'... layers need unique names'%k
            assert not len(hits)==0, 'failed to match any layers with \'%s\''%k
            
            lay = hits[0]
            assert isinstance(lay, QgsMapLayer), 'bad type on %s: %s'%(k, type(lay))
            
            d[k] = lay
        
        #drop to singular elements
        
        return d
        
        
    #===========================================================================
    # bind them
    #===========================================================================
    for fName in ['populate_layers', '_apply_filter', 'select_visible', 'select_canvas', 
                  'get_selected_layers', 'clear_checks','check_all', 'check_byName']:
        setattr(widget, fName, types.MethodType(eval(fName), widget)) 
        
def bind_MapLayerComboBox(widget, #add some bindings to layer combo boxes
                          iface=None, layerType=None): 
    
    widget.iface=iface
    #default selection
    if not layerType is None:
        widget.setFilters(layerType)
    widget.setAllowEmptyLayer(True)
    widget.setCurrentIndex(-1) #set selection to none
    
    #===========================================================================
    # define new methods
    #===========================================================================
    def attempt_selection(self, layName):
        layer = get_layerbyName(layName)
        
        if not layer is None:
            self.setLayer(layer)
            
    #===========================================================================
    # bind functions
    #===========================================================================
    for fName in ['attempt_selection']:
        setattr(widget, fName, types.MethodType(eval(fName), widget)) 
        
        
def bind_link_boxes(widget, #wrapper for widget containing comboboxes linking layers (1:1)
                         types_d, #column type parameterse {comboBox.name string: comboBox layer type}
                         childWidgetType=QComboBox, #lowest container with layer selection
                         iface=None):
    
    widget.iface=iface
    #===========================================================================
    # #collect all the widgets and set the filters
    #===========================================================================
    d = dict()
    for gBox in widget.findChildren(QGroupBox):
        d[gBox.objectName()] = dict() #start page
        allChildren = gBox.findChildren(childWidgetType)
        
        #get all those matching the the name strings
        for name_str, layType in types_d.items():
            
            #find children matching the name
            childMatch = [c for c in allChildren if name_str in c.objectName()]
            
            assert len(childMatch)==1, '%s.%s got multiple children matching %s'%(
                widget.objectName(), gBox.objectName(), name_str)
            
            #collect
            d[gBox.objectName()][name_str] = childMatch[0]
            
            #apply the filter
            childMatch[0].setFilters(layType)
            childMatch[0].setAllowEmptyLayer(True)
            childMatch[0].setCurrentIndex(-1)
        #wrap gBox
    #wrap widget
    widget.children_links_d = d #{groupBoxName: {name:ComboBox}}
    #set all the filters
    
    def get_linked_layers(self,  #get all the layers selected in the combo boxes
                          keyByFirst=False, #whether to re-key the results by the first layer's name
                          ):
        
        rLib = dict()
        for gName, gd in self.children_links_d.items():
            #get from each widget
            rLib[gName] = {nstr:w.currentLayer() for nstr,w in gd.items() if not w.currentLayer() is None}
            
        #clear empties
        rLib = {k:v for k,v in rLib.items() if len(v)>0}
        
        #=======================================================================
        # fancy re-key by the first layers name (then drop that layer)
        #=======================================================================
        if keyByFirst:
            d = dict()

            for k, sub_d in rLib.items():
                
                first = True
                for nstr, layer in sub_d.items():
                    if first:
                        newKey =layer.name()
                        first =False
                    else:
                        d[newKey] = layer
                        break #just taking the first
            rLib = d #reset the result
                    
        return rLib 
    
    def clear_all(self): #clear all the combo boxes
        for child in widget.findChildren(childWidgetType):
            child.setCurrentIndex(-1)
            
    def fill_down(self,  #take the first entry in the combo box column matching the name, and propagate
                  name_str,
                  name_str2= None, #optional paired name_str to stop filling when blank
                  ):
        
        first = True
        for gName, gd in self.children_links_d.items():
            assert name_str in gd
            
            #get the selection to propagate
            if first:
                layer1 = gd[name_str].currentLayer()
                first = False
            else:
                if not name_str2 is None:
                    if gd[name_str2].currentLayer() is None:
                        break #stop the filling here
                gd[name_str].setLayer(layer1)
                
    def set_selections(self, #populate a column with layers
                       name_str,
                       layers, #list of layers to populate combo boxes with
                       ):
        
        for indx, (gName, gd) in enumerate(self.children_links_d.items()):
            assert name_str in gd
            if len(layers)<indx+1: break #stop here
 
            
            gd[name_str].setLayer(layers[indx])

                

    #===========================================================================
    # bind functions
    #===========================================================================
    for fName in ['get_linked_layers', 'clear_all', 'fill_down', 'set_selections']:
        setattr(widget, fName, types.MethodType(eval(fName), widget)) 
        
def bind_fieldSelector( #setup a groupbox collection for field selection
                        groupBox, # groupbox containing the collection
                       layerWidget, #widget w/ layer
                       logger,
                       default_selection = ['xid'], #default field to select
                       ):
    
    groupBox.logger=logger
    
    #collect children widgets
    
    
    
    
    
    #define funcs
    def launch_selector(self):
        pass
    
    def set_selection(self, select_fields):
        pass
    
    def get_selection(self):
        pass
    
    def clear(self):
        pass
    

    
    
    #===========================================================================
    # bind functions
    #===========================================================================
    for fName in ['launch_selector', 'get_selection', 'clear']:
        setattr(groupBox, fName, types.MethodType(eval(fName), groupBox)) 
        
        
    #connect to layer
    layerWidget.layerChanged.connect(groupBox.clear())
    
    #set the default
    groupBox.set_selection(default_selection)
    
 
#==============================================================================
# functions-----------
#==============================================================================
def get_layerbyName(layName, #flexible search for layers by name
                    qproj = None,
                    ):
    """
    couldnt find native support for partial name matching
    """
    if qproj is None: qproj = QgsProject.instance()
    
    names = [layer.name() for layer in qproj.mapLayers().values()]
    
    #find the matching name
    match = None
    for name in names:
        if layName.lower() in name.lower().strip():
            match = name
            break
        
    #get this layer
    if not match is None:
        layer = qproj.mapLayersByName(match)[0]
        
    else:
        layer=None
        
    return layer
        
         
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
            
            
    
    print('?"??')
        