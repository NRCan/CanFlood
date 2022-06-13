# -*- coding: utf-8 -*-
"""
results toolbox dialog
"""

import os, copy

#===============================================================================
# PyQT
#===============================================================================

from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QAction, QFileDialog, QListWidget, QTableWidgetItem
from qgis.core import QgsMapLayerProxyModel, QgsVectorLayer, QgsWkbTypes
import pandas as pd
#==============================================================================
# custom imports
#==============================================================================

import hlpr.plug

from hlpr.basic import force_open_dir
from hlpr.exceptions import QError as Error
from model.modcom import Model

import results.djoin
import results.riskPlot
import results.compare
import results.attribution

import misc.curvePlot


# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'results.ui')
assert os.path.exists(ui_fp)
FORM_CLASS, _ = uic.loadUiType(ui_fp)


class ResultsDialog(QtWidgets.QDialog, FORM_CLASS, hlpr.plug.QprojPlug):
    
    groupName = 'CanFlood.results'
    
    r_passet = '' #needed for typesetting from parameter file
    
    #action parameters
    icon_fn = 'eye_23x23.png'
    icon_name = 'Results'
    icon_location = 'toolbar'
    
    def __init__(self, iface, parent=None, **kwargs):

        super(ResultsDialog, self).__init__(parent)

        self.setupUi(self)
        
        #custom setup

        self.qproj_setup(iface=iface, **kwargs)
        
        self.logger.debug('ResultsDialog init')
        
        
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
        #working directory
        self._connect_wdir(self.pushButton_wd_brwse, self.pushButton_wd_open, self.lineEdit_wdir,
                           default_wdir = os.path.join(os.path.expanduser('~'), 'CanFlood', 'results'))
                
        #Control File browse
        self.pushButton_SS_cf_browse.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_cf_fp, 
                                          caption='Select Control File',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Text Files (*.txt)")
                )
        
        #update control file display labels
        self.lineEdit_cf_fp.textChanged.connect(
            lambda:self.label_RP_cfPath.setText(self.lineEdit_cf_fp.text()))
        
        self.lineEdit_cf_fp.textChanged.connect(
            lambda:self.label_jg_cfPath.setText(self.lineEdit_cf_fp.text()))
        
        self.lineEdit_cf_fp.textChanged.connect(
            lambda:self.label_cba_cfPath.setText(self.lineEdit_cf_fp.text()))
        
        self.lineEdit_cf_fp.textChanged.connect(
            lambda:self.label_rpt_cfPath.setText(self.lineEdit_cf_fp.text()))
        

        #=======================================================================
        # Risk Plot-------------
        #=======================================================================
        self.pushButton_RP_plot.clicked.connect(self.run_plotRisk) 
        self.pushButton_RP_pStacks.clicked.connect(self.run_pStack)
        self.pushButton_RP_pNoFail.clicked.connect(self.run_pNoFail)
        #=======================================================================
        # Join Geometry------------
        #=======================================================================

        #vector geometry layer
        hlpr.plug.bind_MapLayerComboBox(self.comboBox_JGfinv, 
                      layerType=QgsMapLayerProxyModel.VectorLayer, iface=self.iface)
        
        self.launch_actions['attempt finv'] = lambda: self.comboBox_JGfinv.attempt_selection('finv')
                
        #=======================================================================
        # results data
        #=======================================================================
        
        #data file browse
        self.pushButton_JG_resfp_br.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_JG_resfp, 
                                          caption='Select Asset Results Data File',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Data Files (*.csv)")
                )

        #populate the combobox
        self.comboBox_jg_par.addItems(['r_passet', ''])
        
        #set the tabular data file path based on the dropdown
        self.comboBox_jg_par.currentTextChanged.connect(
            lambda x: self.lineEdit_JG_resfp.setText(
                self.get_cf_par(self.lineEdit_cf_fp.text(), varName=x)
                                                    ))
        
        #also connect the layer
        self.comboBox_JGfinv.layerChanged.connect(            
            lambda x: self.lineEdit_JG_resfp.setText(
                self.get_cf_par(self.lineEdit_cf_fp.text(), 
                                varName=self.comboBox_jg_par.currentText())
                                                    ))
        
        self.comboBox_jg_par.setCurrentIndex(0)
        
        
        #=======================================================================
        # results layer style
        #=======================================================================
        #relabel
        self.setup_comboBox(self.comboBox_jg_relabel,['', 'ari', 'aep'], default='ari')
        
        #styles
        def set_style(): #set the style options based on the selected layer
            vlay = self.comboBox_JGfinv.currentLayer()
            
            if not isinstance(vlay, QgsVectorLayer):
                return
            
            gtype = QgsWkbTypes().displayString(vlay.wkbType())
            
            #get the directory for thsi type of style
            subdir = None
            for foldernm in ['Point', 'Polygon']:
                if foldernm in gtype:
                    subdir = foldernm
                    break
            
            #set the options
            if isinstance(subdir, str):
                srch_dir = os.path.join(self.pars_dir, 'qmls', subdir)
                assert os.path.exists(srch_dir), 'requested qml search dir doesnt exist: %s'%srch_dir
                
                #keeping the subdir for easy loading
                l = [os.path.join(subdir, fn) for fn in os.listdir(srch_dir)]
            else:
                l=[]
        
            l.append('') #add teh empty selection
            self.setup_comboBox(self.comboBox_JG_style,l)
            
        self.comboBox_JGfinv.layerChanged.connect(set_style)
        
        
        #execute
        self.pushButton_JG_join.clicked.connect(self.run_joinGeo)
        
        #=======================================================================
        # COMPARE + COMBINE--------
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
            

            #Control File
            cap1='Select Control File for Scenario %s'%scName
            fil1="Control Files (*.txt)"
            d['cf'].clicked.connect(
                lambda a, x=d.pop('cf_line'), c=cap1, f=fil1: \
                self.fileSelect_button(x, caption=c, filters=f, path=self.lineEdit_wdir.text()))
            


        #=======================================================================
        # execute button
        #=======================================================================
        
        self.pushButton_C_compare.clicked.connect(self.run_compare)
        self.pushButton_C_combine.clicked.connect(self.run_combine)
        
        #=======================================================================
        # CBA-----------
        #=======================================================================
        #template copy
        self.pushButton_cba_copy.clicked.connect(self.run_cba_copy)
        
        #data file browse
        self.pushButton_cba_browse.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_cba_cf, 
                                          caption='Select CBA Calculation Spreadsheet',
                                          path = self.lineEdit_cba_cf.text(),
                                          filters="Excel Workbook (*.xlsx)")
                )
        
        #data file open
        self.pushButton_cba_open.clicked.connect(lambda: os.startfile(self.lineEdit_cba_cf.text()))
        
        self.pushButton_cba_plot.clicked.connect(self.run_cba_plot)
        
        #=======================================================================
        # reporter-----------
        #=======================================================================
        
        
        #create the template
        self.pushButton_rpt_create.clicked.connect(self.run_reporter)
        
        #=======================================================================
        # wrap--------
        #=======================================================================

        log.debug('connect_slots finished')
        

        
    def run_joinGeo(self):
        log = self.logger.getChild('run_joinGeo')
        log.info('user pushed \'run_joinGeo\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        self._set_setup()
        
        #local
        """pulling from cf_fp now
        cid = self.mFieldComboBox_JGfinv.currentField() #user selected field"""
        
        """using controlFile parameter to populate the data_fp in the gui
            then pulling the data_fp from the gui"""
        data_fp = self.lineEdit_JG_resfp.text()
        assert os.path.exists(data_fp), 'passed invalid data_fp: %s'%data_fp
        df_raw = pd.read_csv(data_fp, index_col=0)
        
        geo_vlay = self.comboBox_JGfinv.currentLayer()
        
        #relabel kwarg
        relabel = self.comboBox_jg_relabel.currentText()
        if relabel == '':relabel = None
        
        self.feedback.setProgress(5)
        #=======================================================================
        # check inputs
        #=======================================================================        
        assert isinstance(geo_vlay, QgsVectorLayer)
        

        #=======================================================================
        # #setup
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in ['logger', 'tag', 'cf_fp', 
                                            'out_dir', 'feedback', 'init_q_d']}
        
        wrkr = results.djoin.Djoiner(**kwargs).setup()
        
        """shortened setup... loading the data here"""
        #wrkr.init_model() #load the control file
        
        
        #=======================================================================
        # execute
        #=======================================================================

        
        res_vlay = wrkr.run(geo_vlay, relabel=relabel, df_raw=df_raw,
                            keep_fnl='all', #todo: setup a dialog to allow user to select any of the fields
                 )
        
        self.feedback.setProgress(75)
        #=======================================================================
        # load and stylize
        #=======================================================================
        self._load_toCanvas(res_vlay, logger=log, style_fn = self.comboBox_JG_style.currentText())
        
        #=======================================================================
        # wrap
        #=======================================================================
        #set the layer for the reporter
        try:
            self.comboBox_rpt_vlay.setLayer(res_vlay)
        except Exception as e:
            log.error('failed to set report layer w/ %s'%e)
            
        self.feedback.setProgress(95)
        
        
        log.push('run_joinGeo finished')
        self.feedback.upd_prog(None)

    def run_dmgCurvePlot(self):
        log = self.logger.getChild('run_dmgCurvePlot')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        self._set_setup(set_cf_fp=True)

        #=======================================================================
        # setup and load
        #=======================================================================
        # setup
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = misc.curvePlot.CurvePlotr(**kwargs)

        with Model(**kwargs) as model:
            #load the control file
            model.init_model(check_pars=False)
            
            #get curves filepath from the model
            filePath = model.curves

        if filePath is None:
            return

        #load data
        cLib_d = wrkr.load_data(filePath)

        #plot
        fig = wrkr.plotAll(cLib_d)
        output = self.output_fig(fig, plt_window=False)
        self.feedback.upd_prog(30, method='append')

        return output
    
    def run_plotRisk(self,
                     plt_window=None,
                     ): #single risk plot of total results
        log = self.logger.getChild('run_plotRisk')
        log.info('user pushed \'plotRisk\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        self._set_setup(set_cf_fp=True)

            
        #=======================================================================
        # setup and load
        #=======================================================================
        self.feedback.setProgress(5)
        #setup
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = results.riskPlot.RiskPlotr(**kwargs).setup()
        
        self.feedback.setProgress(10)

        #=======================================================================
        # #execute
        #=======================================================================
        res_d = dict()
        if self.checkBox_RP_aep.isChecked():
            fig = wrkr.plot_riskCurve(y1lab='AEP')
            res_d['aep'] = self.output_fig(fig, plt_window=plt_window)
            self.feedback.upd_prog(30, method='append')
            
        if self.checkBox_RP_ari.isChecked():
            fig = wrkr.plot_riskCurve(y1lab='impacts')
            res_d['impacts'] = self.output_fig(fig, plt_window=plt_window)
            self.feedback.upd_prog(30, method='append')
        
        #=======================================================================
        # wrap    
        #=======================================================================
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        log.push('plotRisk finished')
        
        return res_d
        
    def run_pStack(self): #single risk plot of total results
        """
        similar to plotRisk for now... may choose to expand later
        """
        log = self.logger.getChild('run_pStack')
        log.info('user pushed \'run_pStack\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================
        self._set_setup(set_cf_fp=True)
        self.feedback.setProgress(5)
        
        #=======================================================================
        # setup and load
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = results.attribution.Attr(**kwargs).setup()
        
        
        
        self.feedback.setProgress(10)
        
        stack_dxind, sEAD_ser = wrkr.get_stack()
        
        self.feedback.setProgress(20)
        #=======================================================================
        # execute
        #=======================================================================
        if self.checkBox_RP_aep.isChecked():
            fig = wrkr.plot_stackdRCurves(stack_dxind, sEAD_ser, y1lab='AEP')
            self.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
            
        if self.checkBox_RP_ari.isChecked():
            fig = wrkr.plot_stackdRCurves(stack_dxind, sEAD_ser, y1lab='impacts')
            self.output_fig(fig)
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
        self._set_setup(set_cf_fp=True)
        self.feedback.setProgress(5)
        
        #=======================================================================
        # setup and load
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = results.attribution.Attr(**kwargs).setup()
        self.feedback.setProgress(10)
        
        si_ttl = wrkr.get_slice_noFail()
        self.feedback.setProgress(20)
        #=======================================================================
        # execute
        #=======================================================================
        if self.checkBox_RP_aep.isChecked():
            fig = wrkr.plot_slice(si_ttl, y1lab='AEP')
            self.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
            
        if self.checkBox_RP_ari.isChecked():
            fig = wrkr.plot_slice(si_ttl, y1lab='impacts')
            self.output_fig(fig)
            self.feedback.upd_prog(30, method='append')
        
        #=======================================================================
        # wrap    
        #=======================================================================
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        log.push('pNoFail finished')
        
        
    def _set_fps(self, logger=None): #retrieve control file paths on Compare/Combine tab from user
        if logger is None: logger=self.logger
        log=logger.getChild('_set_fps')
        
        #scenario filepaths
        raw_d = {
            '1':{
                'cf_fp':self.lineEdit_C_cf_1.text(),
 
                },
            '2':{
                'cf_fp':self.lineEdit_C_cf_2.text(),
           
                },
            '3':{
                'cf_fp':self.lineEdit_C_cf_3.text(),
 
                },
            '4':{
                'cf_fp':self.lineEdit_C_cf_4.text(),
              
                }
            }
        
        #clean it out
        fps_d = dict()
        for k1, rd in copy.copy(raw_d).items():
            
            if not rd['cf_fp']=='':
                fps_d[k1] = rd['cf_fp']
            
        #=======================================================================
        # check
        #=======================================================================
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('pars w/ %i keys'%(len(fps_d)))
        
        return fps_d

    # Retrieve inventory table from results
    def get_finv(self):
        self._set_setup(set_cf_fp=True)

        #=======================================================================
        # get finv from control file
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        
        with Model(**kwargs) as wrkr:
            #load the control file
            wrkr.init_model(check_pars=False)
            
            #load data from the control file
            dtag_d = {k:d for k,d in wrkr.dtag_d.items() if k=='finv'}
            wrkr.load_df_ctrl(dtag_d=dtag_d)
            df_raw = wrkr.raw_d.pop('finv')

        return df_raw

    def run_compare(self):
        log = self.logger.getChild('run_compare')
        log.info('user pushed \'run_compare\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================

        self._set_setup(set_cf_fp=True)
        fps_d = self._set_fps() #retrieve filepaths from user
        
        self.feedback.setProgress(10)
    
        #=======================================================================
        # init
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = results.compare.Cmpr(fps_d = fps_d,**kwargs).setup()
    
        #load
        #sWrkr_d = wrkr.load_scenarios(list(fp_d.values()))
        self.feedback.setProgress(20)
        #=======================================================================
        # #compare the control files
        #=======================================================================
        if self.checkBox_C_cf.isChecked():
            mdf = wrkr.cf_compare()
            mdf.to_csv(os.path.join(wrkr.out_dir, 'CFcompare_%s_%i.csv'%(wrkr.tag, len(mdf.columns))))
        
        self.feedback.setProgress(70)
        #=======================================================================
        # plot curves
        #=======================================================================
        if self.checkBox_C_ari.isChecked():
            fig = wrkr.riskCurves(y1lab='impacts')
            self.output_fig(fig)
        if self.checkBox_C_aep.isChecked():
            fig = wrkr.riskCurves(y1lab='AEP')
            self.output_fig(fig)
                
            
        
        
        #=======================================================================
        # wrap
        #=======================================================================
        self.feedback.setProgress(95)
        log.push('run_compare finished')
        self.feedback.upd_prog(None)
        
    
    def run_combine(self):
        log = self.logger.getChild('run_combine')
        log.info('user pushed \'run_combine\'')
        
        #=======================================================================
        # collect inputs
        #=======================================================================

        self._set_setup(set_cf_fp=True)
        fps_d = self._set_fps()
        
        self.feedback.setProgress(10)
    
        #=======================================================================
        # init
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = results.compare.Cmpr(fps_d = fps_d,**kwargs).setup()
        
        self.feedback.setProgress(50)
        #===========================================================================
        # get data
        #===========================================================================
        cWrkr = wrkr.build_composite()
        
        
        self.feedback.setProgress(70)
        #=======================================================================
        # #plot curves
        #=======================================================================
 
            
        if self.checkBox_C_ari.isChecked():
            fig = wrkr.plot_rCurveStk_comb(y1lab='impacts')
            self.output_fig(fig)
        if self.checkBox_C_aep.isChecked():
            fig = wrkr.plot_rCurveStk_comb(y1lab='AEP')
            self.output_fig(fig)
                
        self.feedback.setProgress(80)
        #=======================================================================
        # write
        #=======================================================================
        if self.checkBox_C_composite.isChecked():
            cWrkr.write(logger=log, out_dir=self.out_dir)
            self.lineEdit_cf_fp.setText(cWrkr.cf_fp) #change the dialog's selection
            
        self.feedback.setProgress(95)
        log.push('run_combine finished')
        self.feedback.upd_prog(None)
        
    def run_cba_copy(self):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('run_cba_copy')
        log.info('user pushed \'run_cba_copy\'')
        
        """put this here to avoid the global openpyxl dependency"""
        from results.cba import CbaWrkr 
        self.feedback.setProgress(10)
        #=======================================================================
        # collect inputs
        #=======================================================================

        self._set_setup(set_cf_fp=True)
        self.feedback.setProgress(20)
        #=======================================================================
        # init
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = results.cba.CbaWrkr(**kwargs).setup()
        
        self.feedback.setProgress(50)
        
        #=======================================================================
        # copy and write
        #=======================================================================
        
        wrkr.copy_template()
        self.feedback.setProgress(70)
        ofp = wrkr.write_wbook()
        self.feedback.setProgress(90)
        
        #=======================================================================
        # update gui
        #=======================================================================
        """populate for convenience of the cba_plot tool"""
        self.lineEdit_cba_cf.setText(ofp)
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.push('run_cba_copy finished')
        self.feedback.upd_prog(None)
        
        
    def run_cba_plot(self):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('run_cba_plot')
        log.info('user pushed \'run_cba_copy\'')
        
        
        
        self.feedback.setProgress(5)
        #=======================================================================
        # collect inputs
        #=======================================================================

        self._set_setup(set_cf_fp=True)
        self.feedback.setProgress(20)
        #=======================================================================
        # init
        #=======================================================================
        """put this here to avoid the global openpyxl dependency
        
        TODO: cleanup this import using a with statement"""
        #from results.cba import CbaWrkr 
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        wrkr = results.cba.CbaWrkr(**kwargs).setup()
        
        self.feedback.setProgress(50)
        
        #=======================================================================
        # execute
        #=======================================================================
        fig = wrkr.plot_cba(presentVal = self.radioButton_cba_pv.isChecked())
        self.feedback.setProgress(80)
        self.output_fig(fig)
        self.feedback.setProgress(95)
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.push('run_cba_copy finished')
        self.feedback.upd_prog(None)
        
    def run_reporter(self):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('run_reporter')
        log.info('user pushed \'run_reporter\'')
         
        self.feedback.setProgress(5)
        #=======================================================================
        # collect inputs
        #=======================================================================

        self._set_setup(set_cf_fp=True)
        self.feedback.setProgress(20)
        
        #=======================================================================
        # retrieve from other functions
        #=======================================================================
        geo_vlay = self.comboBox_rpt_vlay.currentLayer()

        plots_d = self.run_plotRisk(plt_window=False)

        dmg_plot = self.run_dmgCurvePlot()

        finv_df = self.get_finv() #retrieve the inventory frame
        assert isinstance(finv_df, pd.DataFrame), 'failed to load finv'
        #=======================================================================
        # init
        #=======================================================================  
        from results.reporter import ReportGenerator
        
        kwargs = {attn:getattr(self, attn) for attn in ['logger', 'tag', 'cf_fp', 
                                    'out_dir', 'feedback', 'init_q_d']}
        
        with ReportGenerator(**kwargs) as wrkr:
        
            wrkr.setup()
            
            #start the report
            report = wrkr.add_report()
            self.feedback.setProgress(20)
            
            wrkr.add_header()
            self.feedback.setProgress(30)
            
            #add the map section
            if isinstance(geo_vlay, QgsVectorLayer):
                wrkr.add_map(vlay=geo_vlay)
            self.feedback.setProgress(35)

            wrkr.add_finv_smry(finv_df) #making this mandatory
            self.feedback.setProgress(45)
            
            # add the total plots
            for name, fp in plots_d.items():
                wrkr.add_picture(fp)
            self.feedback.setProgress(50)

            if dmg_plot is not None:
                wrkr.add_picture(dmg_plot)
            self.feedback.setProgress(55)
            
            
            # add the control file report
            html_fp = wrkr.build_html()          
            wrkr.add_html(html_fp=html_fp)
            self.feedback.setProgress(60)
            
            
            """this will crash the test run""" 
            if not self.iface is None:
                self.iface.openLayoutDesigner(report)
 
        #=======================================================================
        # wrap
        #=======================================================================
        self.feedback.setProgress(95)
        
        log.push('run_reporter finished')
        self.feedback.upd_prog(None)