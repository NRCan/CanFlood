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
import results.riskPlot



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
        
        self.logger.debug('Results_Dialog init')
        
        
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
        
        
                #WD force open
        def open_wd():
            force_open_dir(self.lineEdit_wd.text())
        
        self.pushButton_wd_open.clicked.connect(open_wd)
        
        #=======================================================================
        # Risk PLot-------------
        #=======================================================================

        #data file browse
        def browse_pd():
            return self.fileSelect_button(self.lineEdit_RP_fp, 
                                          caption='Select Total Results Data File',
                                          path = self.lineEdit_wd.text(),
                                          filters="Data Files (*.csv)")
            
        self.pushButton_RP_fp.clicked.connect(browse_pd)
        
        self.pushButton_RP_plot.clicked.connect(self.run_plotRisk) 
        
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
                                          caption='Select Asset Results Data File',
                                          path = self.lineEdit_wd.text(),
                                          filters="Data Files (*.csv)")
            
        self.pushButton_JG_resfp_br.clicked.connect(browse_jg) 
        
        #styles
        def set_style(): #set the style options based on the selecte dlayer
            vlay = self.comboBox_JGfinv.currentLayer()
            
            if not isinstance(vlay, QgsVectorLayer):
                return
            
            gtype = QgsWkbTypes().displayString(vlay.wkbType())
            
            #get the directory for thsi type of style
            subdir = None
            for foldernm in ['Point']:
                if foldernm in gtype:
                    subdir = foldernm
                    break
            
            #set the options
            if isinstance(subdir, str):
                srch_dir = os.path.join(self.pars_dir, 'qmls', subdir)
                assert os.path.exists(srch_dir)
                
                #keeping the subdir for easy loading
                l = [os.path.join(subdir, fn) for fn in os.listdir(srch_dir)]
            else:
                l=[]
        
            l.append('none')
            self.setup_comboBox(self.comboBox_JG_style,l)
            
        self.comboBox_JGfinv.layerChanged.connect(set_style)
        
        


        
        #execute
        self.pushButton_JG_join.clicked.connect(self.run_joinGeo)
        
        
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
        
        
        
        
        log.debug('connect_slots finished')
        
    def run_plotRisk(self): 
        log = self.logger.getChild('run_plotRisk')
        log.info('user pushed \'plotRisk\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================

        #general
        wd = self.lineEdit_wd.text()
        tag = self.linEdit_Stag.text() #set the secnario tag from user provided name
        
        #local
        data_fp = self.lineEdit_RP_fp.text()
        
        #=======================================================================
        # checks
        #=======================================================================
        assert isinstance(wd, str)
        assert isinstance(tag, str)
        
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
        self.feedback.setProgress(5)
        #setup
        wrkr = results.riskPlot.Plotr(logger=self.logger, 
                                     tag = tag,
                                     feedback=self.feedback,
                                     out_dir=wd)
        
        self.feedback.setProgress(10)
        #load tabular
        res_ser = wrkr.load_data(data_fp)
        
        self.feedback.setProgress(20)
        #execute
        fig = wrkr.run(res_ser, dfmt='{0:.0f}', y1lab='impacts')
        
        self.feedback.setProgress(80)
        #save
        out_fp = wrkr.output_fig(fig)
        self.feedback.setProgress(95)
        
        log.info('riskPlot saved to file: %s'%out_fp)
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
        
        
    def run_joinGeo(self):
        log = self.logger.getChild('run_joinGeo')
        log.info('user pushed \'run_joinGeo\'')
        
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
        res_style_fp = self.comboBox_JG_style.currentText()
        
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
        
        assert isinstance(res_style_fp, str), 'bad style var'
         
        
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
        # styleize
        #=======================================================================
        #load the layer into the project
        self.qproj.addMapLayer(res_vlay)
        
        if not res_style_fp == 'none':
            """res_style_fp should contain the subdirectory (e.g. Points/style)"""
            style_fp = os.path.join(self.pars_dir, 'qmls', res_style_fp)
            assert os.path.exists(style_fp)
            res_vlay.loadNamedStyle(style_fp)
            res_vlay.triggerRepaint()
        #=======================================================================
        # wrap
        #=======================================================================

        
        self.feedback.upd_prog(None)
        log.push('run_joinGeo finished')
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
