# -*- coding: utf-8 -*-
"""


"""

import os

#===============================================================================
# PyQT
#===============================================================================

from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem


#==============================================================================
# custom imports
#==============================================================================

import hlpr.plug


from hlpr.Q import *
from hlpr.basic import *

import results.djoin



# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'results.ui')
assert os.path.exists(ui_fp)
FORM_CLASS, _ = uic.loadUiType(ui_fp)


class Results_Dialog(QtWidgets.QDialog, FORM_CLASS, hlpr.plug.QprojPlug):
    def __init__(self, iface, parent=None):

        super(Results_Dialog, self).__init__(parent)
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)
        
        #custom setup
        self.iface = iface
        self.qproj_setup()
        self.connect_slots()
        
        self.logger.info('Results_Dialoginitilized')
        
        
    def connect_slots(self): #connect your slots
        log = self.logger.getChild('connect_slots')
        
        #=======================================================================
        # general----------------
        #=======================================================================
        #ok/cancel buttons
        self.buttonBox.accepted.connect(self.reject)
        self.buttonBox.rejected.connect(self.reject)
        
        #status label
        self.logger.statusQlab=self.progressText
        self.logger.statusQlab.setText('BuildDialog initialized')
        
        
        #=======================================================================
        # setup------------
        #=======================================================================
        #Working Directory browse
        def browse_wd():
            return self.browse_button(self.lineEdit_wd, prompt='Select Working Directory',
                                      qfd = QFileDialog.getExistingDirectory)
            
        self.pushButton_wd.clicked.connect(browse_wd) # SS. Working Dir. Browse
        
        #=======================================================================
        # Join Geometry------------
        #=======================================================================

        #vector geometry layer
        self.comboBox_JGfinv.setFilters(QgsMapLayerProxyModel.VectorLayer) 
        
        def upd_cid(): #change the 'cid' display when the finv selection changes
            return self.mfcb_connect(
                self.mFieldComboBox_JGfinv, self.comboBox_JGfinv.currentLayer(),
                fn_str = 'xid' )
        
        self.comboBox_JGfinv.layerChanged.connect(upd_cid)
        
        
        #data file browse
        def browse_jg():
            return self.fileSelect_button(self.lineEdit_JG_resfp, 
                                          caption='Select Results Data File',
                                          path = self.lineEdit_wd.text(),
                                          filters="Data Files (*.csv)")
            
        self.pushButton_JG_resfp_br.clicked.connect(browse_jg) # SS. Working Dir. Browse
        
        #execute
        self.pushButton_JG_join.clicked.connect(self.join_geo)
        
        
        #======================================================================
        # defaults-----------
        #======================================================================
        """"
        to speed up testing.. manually configure the project
        """

        debug_dir =os.path.join(os.path.expanduser('~'), 'CanFlood', 'results')
        self.lineEdit_wd.setText(debug_dir)
        
        if not os.path.exists(debug_dir):
            log.info('builg directory: %s'%debug_dir)
            os.makedirs(debug_dir)
        
        
        
        
        log.info('finished')
        
    def join_geo(self):
        log = self.logger.getChild('join_geo')
        log.info('user pushed \'join_geo\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        #general
        wd = self.lineEdit_wd.text()
        crs = self.qproj.crs()
        tag = self.linEdit_Stag.text() #set the secnario tag from user provided name
        
        #local
        cid = self.mFieldComboBox_JGfinv.currentField() #user selected field
        geo_vlay = self.comboBox_JGfinv.currentLayer()
        data_fp = self.lineEdit_JG_resfp.text()
        
        #=======================================================================
        # check inputs
        #=======================================================================
        assert isinstance(wd, str)
        assert isinstance(crs, QgsCoordinateReferenceSystem)
        assert crs.isValid()
        assert isinstance(tag, str)
        
        assert isinstance(geo_vlay, QgsVectorLayer)
        
        #check cid
        assert isinstance(cid, str), 'bad index FieldName passed'
        if cid == '' or cid in self.invalid_cids:
            raise Error('user selected index FieldName \'%s\''%cid)
        
        assert cid in [field.name() for field in geo_vlay.fields()] 
        
        assert os.path.exists(data_fp), 'invalid data_fp'
        
         
        
        #=======================================================================
        # working dir
        #=======================================================================
        if not os.path.exists(wd):
            os.makedirs(wd)
            log.info('built working directory: %s'%wd)
        
        
        #=======================================================================
        # execute
        #=======================================================================
        #setup
        wrkr = results.djoin.Djoiner(logger=self.logger, 
                                     tag = tag,
                                     feedback=self.feedback,
                                     cid=cid, crs=crs,
                                     out_dir=wd)
        #execute
        res_vlay = wrkr.run(geo_vlay, data_fp, cid,
                 keep_fnl='all', #todo: setup a dialog to allow user to select any of the fields
                 )
        
        
        #=======================================================================
        # wrap
        #=======================================================================
        #load the layer into the project
        self.qproj.addMapALayer(res_vlay)
        
        log.push('join_geo finished')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
