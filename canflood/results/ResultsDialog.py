# -*- coding: utf-8 -*-
"""


"""

import os, copy

#===============================================================================
# PyQT
#===============================================================================

from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem
from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer, QgsWkbTypes

#==============================================================================
# custom imports
#==============================================================================

import hlpr.plug


#from hlpr.Q import *
from hlpr.basic import force_open_dir
from hlpr.exceptions import QError as Error

import results.djoin
import results.riskPlot
import results.compare
import results.attribution

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
        self.pushButton_wd.clicked.connect(
                lambda: self.browse_button(self.lineEdit_wd, 
                                           prompt='Select Working Directory',
                                      qfd = QFileDialog.getExistingDirectory)
                )

        #WD Open
        self.pushButton_wd_open.clicked.connect(
                lambda: force_open_dir(self.lineEdit_wd.text()))
                
        #Control File browse
        self.pushButton_SS_cf_browse.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_SS_cf, 
                                          caption='Select Control File',
                                          path = self.lineEdit_wd.text(),
                                          filters="Text Files (*.txt)")
                )
        
        #CF update RP label
        self.lineEdit_SS_cf.textChanged.connect(
            lambda:self.label_RP_cfPath.setText(self.lineEdit_SS_cf.text()))
        
        """
        TODO: open the cf and display the plot styles
        """
        #=======================================================================
        # Risk PLot-------------
        #=======================================================================
        self.pushButton_RP_plot.clicked.connect(self.run_plotRisk) 
        self.pushButton_RP_pStacks.clicked.connect(self.run_pStack)
        self.pushButton_RP_pNoFail.clicked.connect(self.run_pNoFail)
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
        
        #=======================================================================
        # COMPARE--------
        #=======================================================================
        #=======================================================================
        # browse/open buttons
        #=======================================================================

        for scName, d in {
            '1':{
                #'rd_browse':self.pushButton_C_Rdir_browse_1,
                #'rd_open':self.pushButton_C_Rdir_open_1,
                #'rd_line':self.lineEdit_C_Rdir_1,
                'cf':self.pushButton_C_cf_browse_1,
                'cf_line':self.lineEdit_C_cf_1,
                #'ttl':self.pushButton_C_ttl_browse_1,
                #'ttl_line':self.lineEdit_C_ttl_1,
                },
            '2':{
                #'rd_browse':self.pushButton_C_Rdir_browse_2,
                #'rd_open':self.pushButton_C_Rdir_open_2,
                #'rd_line':self.lineEdit_C_Rdir_2,
                'cf':self.pushButton_C_cf_browse_2,
                'cf_line':self.lineEdit_C_cf_2,
                #'ttl':self.pushButton_C_ttl_browse_2,
                #'ttl_line':self.lineEdit_C_ttl_2,
                },
            '3':{
                #'rd_browse':self.pushButton_C_Rdir_browse_3,
                #'rd_open':self.pushButton_C_Rdir_open_3,
                #'rd_line':self.lineEdit_C_Rdir_3,
                'cf':self.pushButton_C_cf_browse_3,
                'cf_line':self.lineEdit_C_cf_3,
                #'ttl':self.pushButton_C_ttl_browse_3,
                #'ttl_line':self.lineEdit_C_ttl_3,
                },
            '4':{
                #'rd_browse':self.pushButton_C_Rdir_browse_4,
                #'rd_open':self.pushButton_C_Rdir_open_4,
                #'rd_line':self.lineEdit_C_Rdir_4,
                'cf':self.pushButton_C_cf_browse_4,
                'cf_line':self.lineEdit_C_cf_4,
                #'ttl':self.pushButton_C_ttl_browse_4,
                #'ttl_line':self.lineEdit_C_ttl_4,
                }
            }.items():
            

                
            #Results Directory
            #===================================================================
            # cap1='Select Results Directory for Scenario %s'%scName
            # d['rd_browse'].clicked.connect(
            #     lambda a, x=d['rd_line'], c=cap1: \
            #     self.browse_button(x, prompt=c))
            # 
            # d['rd_open'].clicked.connect(
            #     lambda a, x=d['rd_line']: force_open_dir(x.text()))
            #===================================================================

            
            #Control File
            cap1='Select Control File for Scenario %s'%scName
            fil1="Control Files (*.txt)"
            d['cf'].clicked.connect(
                lambda a, x=d.pop('cf_line'), c=cap1, f=fil1: \
                self.fileSelect_button(x, caption=c, filters=f, path=self.lineEdit_wd.text()))
            
            #total results
            #===================================================================
            # cap1='Select Total Results for Scenario %s'%scName
            # fil1="Data Files (*.csv)"
            # d['ttl'].clicked.connect(
            #     lambda a, x=d.pop('ttl_line'), c=cap1, f=fil1: \
            #     self.fileSelect_button(x, caption=c, filters=f, path=self.lineEdit_wd.text()))
            #===================================================================


        #=======================================================================
        # execute button
        #=======================================================================
        
        self.pushButton_C_compare.clicked.connect(self.run_compare)
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
        
    def run_plotRisk(self): #single risk plot of total results
        log = self.logger.getChild('run_plotRisk')
        log.info('user pushed \'plotRisk\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================

        #general
        out_dir = self.lineEdit_wd.text()
        tag = self.linEdit_Stag.text() #set the secnario tag from user provided name
        cf_fp = self.lineEdit_SS_cf.text()
        
        
        #=======================================================================
        # checks
        #=======================================================================
        assert isinstance(tag, str)
        assert os.path.exists(cf_fp), 'invalid cf_fp: %s'%cf_fp
        assert os.path.exists(out_dir), 'working directory does not exist'
            
        #=======================================================================
        # setup and load
        #=======================================================================
        self.feedback.setProgress(5)
        #setup
        wrkr = results.riskPlot.Plotr(cf_fp=cf_fp, 
                                      logger=self.logger, 
                                     tag = tag,
                                     feedback=self.feedback,
                                     out_dir=out_dir)._setup()
        
        self.feedback.setProgress(10)

        #=======================================================================
        # #execute
        #=======================================================================
        if self.checkBox_RP_aep.isChecked():
            fig = wrkr.plot_riskCurve(y1lab='AEP')
            wrkr.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
            
        if self.checkBox_RP_ari.isChecked():
            fig = wrkr.plot_riskCurve(y1lab='impacts')
            wrkr.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
        
        #=======================================================================
        # wrap    
        #=======================================================================
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        log.push('plotRisk finished')
        
        
    def run_pStack(self): #single risk plot of total results
        """
        similar to plotRisk for now... may choose to expand later
        """
        log = self.logger.getChild('run_pStack')
        log.info('user pushed \'run_pStack\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        #general
        out_dir = self.lineEdit_wd.text()
        tag = self.linEdit_Stag.text() #set the secnario tag from user provided name
        cf_fp = self.lineEdit_SS_cf.text()
        
        
        #=======================================================================
        # checks
        #=======================================================================
        assert isinstance(tag, str)
        assert os.path.exists(cf_fp), 'invalid cf_fp: %s'%cf_fp
        assert os.path.exists(out_dir), 'working directory does not exist'
            
        #=======================================================================
        # setup and load
        #=======================================================================
        self.feedback.setProgress(5)
        #setup
        wrkr = results.attribution.Attr(cf_fp=cf_fp, 
                                      logger=self.logger, 
                                     tag = tag,
                                     feedback=self.feedback,
                                     out_dir=out_dir)._setup()
        
        
        
        self.feedback.setProgress(10)
        
        stack_dxind, sEAD_ser = wrkr.get_stack()
        
        self.feedback.setProgress(20)
        #=======================================================================
        # #execute
        #=======================================================================
        if self.checkBox_RP_aep.isChecked():
            fig = wrkr.plot_stackdRCurves(stack_dxind, sEAD_ser, y1lab='AEP')
            wrkr.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
            
        if self.checkBox_RP_ari.isChecked():
            fig = wrkr.plot_stackdRCurves(stack_dxind, sEAD_ser, y1lab='impacts')
            wrkr.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
        
        #=======================================================================
        # wrap    
        #=======================================================================
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        log.push('pStack finished')
        
    def run_pNoFail(self): #plot split between totals and no-fail
        """
        similar to plotRisk for now... may choose to expand later
        """
        log = self.logger.getChild('run_pNoFail')
        log.info('user pushed \'run_pNoFail\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        #general
        out_dir = self.lineEdit_wd.text()
        tag = self.linEdit_Stag.text() #set the secnario tag from user provided name
        cf_fp = self.lineEdit_SS_cf.text()
        
        
        #=======================================================================
        # checks
        #=======================================================================
        assert isinstance(tag, str)
        assert os.path.exists(cf_fp), 'invalid cf_fp: %s'%cf_fp
        assert os.path.exists(out_dir), 'working directory does not exist'
            
        #=======================================================================
        # setup and load
        #=======================================================================
        self.feedback.setProgress(5)
        #setup
        wrkr = results.attribution.Attr(cf_fp=cf_fp, 
                                      logger=self.logger, 
                                     tag = tag,
                                     feedback=self.feedback,
                                     out_dir=out_dir)._setup()
        
        
        
        self.feedback.setProgress(10)
        
        si_ttl = wrkr.get_slice_noFail()
        
        self.feedback.setProgress(20)
        #=======================================================================
        # #execute
        #=======================================================================
        if self.checkBox_RP_aep.isChecked():
            fig = wrkr.plot_slice(si_ttl, y1lab='AEP')
            wrkr.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
            
        if self.checkBox_RP_ari.isChecked():
            fig = wrkr.plot_slice(si_ttl, y1lab='impacts')
            wrkr.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
        
        #=======================================================================
        # wrap    
        #=======================================================================
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        log.push('pNoFail finished')
        
    def run_joinGeo(self):
        log = self.logger.getChild('run_joinGeo')
        log.info('user pushed \'run_joinGeo\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        #general
        wd = self.lineEdit_wd.text()
        
        tag = self.linEdit_Stag.text() #set the secnario tag from user provided name
        
        cf_fp = self.lineEdit_SS_cf.text()
        
        #local
        """pulling from cf_fp now
        cid = self.mFieldComboBox_JGfinv.currentField() #user selected field
        data_fp = self.lineEdit_JG_resfp.text()"""
        
        geo_vlay = self.comboBox_JGfinv.currentLayer()
        res_style_fp = self.comboBox_JG_style.currentText()
        
        #=======================================================================
        # check inputs
        #=======================================================================
        assert isinstance(wd, str)

        assert isinstance(tag, str)
        
        assert isinstance(geo_vlay, QgsVectorLayer)
        
        #check cid
        #=======================================================================
        # assert isinstance(cid, str), 'bad index FieldName passed'
        # if cid == '' or cid in self.invalid_cids:
        #     raise Error('user selected index FieldName \'%s\''%cid)
        # 
        # assert cid in [field.name() for field in geo_vlay.fields()] 
        #=======================================================================
        
        #assert os.path.exists(data_fp), 'invalid data_fp'
        
        assert isinstance(res_style_fp, str), 'bad style var'
         

        #=======================================================================
        # execute
        #=======================================================================
        #setup
        wrkr = results.djoin.Djoiner(logger=self.logger, 
                                     tag = tag, cf_fp=cf_fp,
                                     feedback=self.feedback,
                                     #cid=cid, 
                                     out_dir=wd)
        #execute
        res_vlay = wrkr.run(geo_vlay, 
                            #data_fp, 
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
    
    def run_compare(self):
        log = self.logger.getChild('run_compare')
        log.info('user pushed \'run_compare\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        #general
        out_dir = self.lineEdit_wd.text()
        if not os.path.exists(out_dir): os.makedirs(out_dir)
        
        tag = self.linEdit_Stag.text() #set the secnario tag from user provided name
        main_cf_fp = self.lineEdit_SS_cf.text() #for general plot styles
        
        #scenario filepaths
        raw_d = {
            '1':{
                'cf_fp':self.lineEdit_C_cf_1.text(),
                #'ttl_fp':self.lineEdit_C_ttl_1.text(),
                },
            '2':{
                'cf_fp':self.lineEdit_C_cf_2.text(),
                #'ttl_fp':self.lineEdit_C_ttl_2.text(),              
                },
            '3':{
                'cf_fp':self.lineEdit_C_cf_3.text(),
                #'ttl_fp':self.lineEdit_C_ttl_3.text(),
                },
            '4':{
                'cf_fp':self.lineEdit_C_cf_4.text(),
                #'ttl_fp':self.lineEdit_C_ttl_4.text(),                
                }
            }
        
        #clean it out
        fps_d = dict()
        for k1, rd in copy.copy(raw_d).items():
            
            if not rd['cf_fp']=='':
                fps_d[k1] = rd['cf_fp']
            
    
        log.debug('pars w/ %i keys'%(len(fps_d)))
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert os.path.exists(main_cf_fp), 'bad filepath for main control file'
        for k, v in fps_d.items(): assert os.path.exists(v), 'bad fp on %s'%k
        
        self.feedback.setProgress(10)
        
        #=======================================================================
        # working dir
        #=======================================================================
        

    
        #=======================================================================
        # init
        #=======================================================================
        wrkr = results.compare.Cmpr(fps_d = fps_d,
                    out_dir=out_dir, tag=tag, logger=self.logger,
                    cf_fp = main_cf_fp)._setup()
    
        #load
        #sWrkr_d = wrkr.load_scenarios(list(fp_d.values()))
        self.feedback.setProgress(20)
        #=======================================================================
        # #compare the control files
        #=======================================================================
        if self.checkBox_C_cf.isChecked():
            mdf = wrkr.cf_compare()
            mdf.to_csv(os.path.join(out_dir, 'CFcompare_%s_%i.csv'%(tag, len(mdf.columns))))
        
        self.feedback.setProgress(60)
        #=======================================================================
        # #plot curves
        #=======================================================================
        if self.checkBox_C_rplot.isChecked():
            
            if self.checkBox_C_ari.isChecked():
                fig = wrkr.riskCurves(y1lab='impacts')
                wrkr.output_fig(fig)
            if self.checkBox_C_aep.isChecked():
                fig = wrkr.riskCurves(y1lab='AEP')
                wrkr.output_fig(fig)
                
            
        self.feedback.setProgress(90)
        
        #=======================================================================
        # wrap
        #=======================================================================
        self.feedback.upd_prog(None)
        log.push('run_compare finished')
    
    
    
    
    
    
