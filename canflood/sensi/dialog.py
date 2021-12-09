'''
Created on Nov. 18, 2021

@author: cefect

ui class for the sensitivity analysis menu
'''
#===============================================================================
# imports------------
#===============================================================================
import os,  os.path, time, datetime, copy
from qgis.core import QgsExpression, QgsVectorLayer

from PyQt5 import uic, QtWidgets, QtGui
from PyQt5.QtWidgets import QTableWidgetItem, QWidget, QHeaderView, QFileDialog
 
from PyQt5.QtCore import Qt




from hlpr.exceptions import QError as Error
#===============================================================================
# customs
#===============================================================================
import hlpr.plug
import misc.expressionFunctions as expF

import numpy as np
import pandas as pd
from hlpr.basic import view
from hlpr.Q import vlay_get_fdf

#===============================================================================
# load qt ui
#===============================================================================
ui_fp = os.path.join(os.path.dirname(__file__), 'sensi.ui')
assert os.path.exists(ui_fp)
FORM_CLASS, _ = uic.loadUiType(ui_fp)

#===============================================================================
# Classes ---------
#===============================================================================
from sensi.coms import SensiShared
from sensi.sbuild import SensiConstructor
from sensi.srun import SensiSessRunner, SensiSessResults

from model.modcom import Model #for data loading parameters

 
 

class SensiDialog(QtWidgets.QDialog, FORM_CLASS,  
                       hlpr.plug.QprojPlug):
    
    colorMap = 'hsv' #cyclical
    
 
    dataFile_vlay = None #loaded datafile vlay
    
    
    #action parameters
    icon_fn = 'target.png'
    icon_name = 'Sensitivity'
    icon_location = 'menu'
    
    def __init__(self, iface, parent=None, **kwargs):
        """Constructor."""
        super(SensiDialog, self).__init__(parent) #init QtWidgets.QDialog

        self.setupUi(self)
        

        self.qproj_setup(iface=iface, **kwargs)
        
        #self.connect_slots()
        
        
 
        
        
    def connect_slots(self, #connect ui slots to functions 
 
                      ): 
        log = self.logger.getChild('connect_slots')
        #======================================================================
        # general----------------
        #======================================================================
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        
        #connect to status label
        self.logger.statusQlab=self.progressText
        self.logger.statusQlab.setText('SensiDialog initialized')
        
        
        #======================================================================
        # setup-----------
        #======================================================================
        #=======================================================================
        # base model
        #=======================================================================
        #control file
        self.pushButton_cf.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_cf_fp, 
                                          caption='Select Control File',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Text Files (*.txt)")
                )
        
        self.pushButton_s_cfOpen.clicked.connect(lambda: os.startfile(self.lineEdit_cf_fp.text()))
        
        #loading
        self.comboBox_S_ModLvl.addItems(['L1', 'L2'])
        self.pushButton_s_load.clicked.connect(self.setup_load)
        
 
        #=======================================================================
        # #working directory
        #=======================================================================
        default_wdir = os.path.join(os.path.expanduser('~'), 'CanFlood', 'sensi', datetime.datetime.now().strftime('%m%d'))
        #Working Directory 
        self._connect_wdir(self.pushButton_wd, self.pushButton_wd_open, self.lineEdit_wdir,
                           default_wdir = default_wdir)
        
        
        #=======================================================================
        # compile----
        #=======================================================================
        #bind custom methods to the table widget
        hlpr.plug.bind_TableWidget(self.tableWidget_P, log)
         
        self.pushButton_P_addCand.clicked.connect(self.compile_add)
        self.pushButton_C_remove.clicked.connect(self.compile_remove)
        
        self.pushButton_P_addColors.clicked.connect(self.compile_randomColors)
        
        self.pushButton_P_compile.clicked.connect(self.compile_candidates)
        
        #=======================================================================
        # run-----
        #=======================================================================
        hlpr.plug.bind_TableWidget(self.tableWidget_R, log)
        
        self.pushButton_R_run.clicked.connect(self.run_RunSuite)
        
        
        #=======================================================================
        # DataFiles------------
        #=======================================================================
 
        #=======================================================================
        # selection 
        #=======================================================================
        #candidate and parameter dropdowns
        """each time either of these change make a new guess at the source
        candidateName:
            enabled when we compile_candidates
        parameter:
            enabled when we load the master
        """
        self.comboBox_DF_candName.setDisabled(True) #activated when a enw datafile is loaded
        self.comboBox_DF_candName.activated.connect(self._dataFiles_sourceFile)

        
        self.comboBox_DF_par.setDisabled(True) #activated when a enw datafile is loaded
        self.comboBox_DF_par.activated.connect(self._dataFiles_sourceFile)
        

        
        #browse button
        self.pushButton_DF_browse.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_DF_fp, 
                                          caption='Select Data File',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Data Files (*.csv)")
                            )
        
 
        
        #loader button
        self.pushButton_DF_load.clicked.connect(self.datafiles_load)
        
        #=======================================================================
        # Data Manipulations
        #=======================================================================
        #hlpr.plug.bind_TableWidget(self.tableWidget_DF, log)
        
        #self.pushButton_DF_plot.clicked.connect(self.datafiles_plot)
        
        def triggerAction(attn):
            action = getattr(self.iface, attn)()
            action.trigger()
 
 
            
        #self.pushButton_DF_apply.clicked.connect(lambda: triggerAction('actionOpenFieldCalculator'))
        self.pushButton_DF_attTable.clicked.connect(lambda: triggerAction('actionOpenTable'))
        
        #=======================================================================
        # Generating New Files
        #=======================================================================
        self.pushButton_DF_browse2.clicked.connect(
                lambda: self.newFileSelect_button(self.linEdit_DF_new_fp, 
                                          caption='Select New Data Filename',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Data Files (*.csv)")
                            )
        
        self.pushButton_DF_save.clicked.connect(self.datafiles_save)
        #=======================================================================
        # expression functions
        #=======================================================================
        
        for func in [expF.finv_elv_add, expF.finv_scale_add]:
 
            QgsExpression.registerFunction(func) 
 
        
        #=======================================================================
        # Analyze----------
        #=======================================================================
        hlpr.plug.bind_TableWidget(self.tableWidget_A, log)
        
        #pickel file
        self.pushButton_A_browse.clicked.connect(
                lambda: self.fileSelect_button(self.lineEdit_A_pick_fp, 
                                          caption='Select suite results .pickle',
                                          path = self.lineEdit_wdir.text(),
                                          filters="Pickles (*.pickle)")
                )
        
        self.pushButton_A_load.clicked.connect(self.analysis_loadPick)

        self.pushButton_A_plotRiskCurves.clicked.connect(self.analysis_plotRiskCurves)
        
        self.pushButton_A_plotBox.clicked.connect(self.analysis_plotBox)
        
        self.pushButton_A_print.clicked.connect(self.analysis_print)
        
        self.pushButton_A_saveAs.clicked.connect(lambda :self.tableWidget_A.save_df(path=self.out_dir))
        
        
        

            
        
        
        
        
        #=======================================================================
        # dev-----------
        #=======================================================================
        if self.dev:
            #add control file
            self.lineEdit_cf_fp.setText(r'C:\LS\09_REPOS\03_TOOLS\CanFlood\tut_builds\8\20211119\CanFlood_tut8.txt')
            self.radioButton_SS_fpRel.setChecked(True)
            self.comboBox_S_ModLvl.setCurrentIndex(1) #modLevel=L2
            
            """seems to be buggy during tests"""
            self.lineEdit_wdir.setText(default_wdir) 

        
        
        
    def set_setup(self, #attach parameters from setup tab
                  set_cf_fp=True,
                  set_absolute_fp=False, #whether to include the absolute_fp in the setu  
                  logger=None,): 
        
        if logger is None: logger=self.logger
        log = logger.getChild('set_setup')
        #=======================================================================
        # #call the common
        #=======================================================================
        self._set_setup(set_cf_fp=set_cf_fp)
        #self.inherit_fieldNames.append('init_q_d')
        #=======================================================================
        # custom setups
        #=======================================================================
 
        #file behavior
        self.loadRes = self.checkBox_loadres.isChecked()
        
        #model type
        self.modLevel = self.comboBox_S_ModLvl.currentText()
        assert self.modLevel in ['L1', 'L2'], 'must specify a model level'
        self.inherit_fieldNames.append('modLevel')
        
        #absolutes
        """because were moving files around... need special handling of filepaths
        
        generally only using this for the first control file load
        then we convert the maincontrol file to absolute"""
        
        if not set_absolute_fp:
            self.inherit_fieldNames.remove('absolute_fp') #dont inherit
            self.absolute_fp = True #refert to default
        

    def _change_tab(self, tabObjectName): #try to switch the tab on the gui
        try:
            tabw = self.tabWidget
            index = tabw.indexOf(tabw.findChild(QWidget, tabObjectName))
            assert index > 0, 'failed to find index?'
            tabw.setCurrentIndex(index)
        except Exception as e:
            self.logger.error('failed to change to compile tab w/ \n    %s' % e)

    def setup_load(self, #load teh base control file
                  ):
        #=======================================================================
        # default
        #=======================================================================
        log = self.logger.getChild('setup_load')
        
        self.set_setup(set_cf_fp=True, set_absolute_fp=True)
        log.info('loading base from %s'%self.cf_fp)
        #=======================================================================
        # prechecks
        #======================================================================= 
        self.feedback.upd_prog(10)
        
        #=======================================================================
        # prep control file
        #=======================================================================
        

 
        # clear results from main control file
        log.info('clearing results from main control file')
        rkeys = list(SensiShared.master_pars['results_fps'].keys())
        self.set_cf_pars({'risk_fps':({'dmgs':''},'#cleared dmg2 results'),
                          'results_fps':({k:'' for k in rkeys},'#cleared results'),
                          }, logger=log)
        

        
        
        #=======================================================================
        # load the base values----
        #=======================================================================
 
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiShared(**kwargs) as wrkr:
            
            #change to absolute fps
            """
            Model.setup()
                Model.init_model()
                    if not absolute_fp:
                        Model._cf_relative()
                            reverts cfPars_d to absolute
            """
            
            wrkr.setup() #init the model
 
            cfPars_d = wrkr.cfPars_d #retrieve the loaded parameters
            
        #get just the parameters with values
        pars_d = {k:v  for sect, d in cfPars_d.items() for k,v in d.items() if not v==''}
        
 
        #=======================================================================
        # populate the table
        #=======================================================================
        log.info('populating \'Parameters\' tab w/ %i base values'%len(pars_d))
        tbw = self.tableWidget_P
        tbw.clear() #clear everything
        
        #set dimensions
        tbw.setRowCount(1) #always start w/ 1.. then call add column
        tbw.setColumnCount(len(pars_d))
        
        #set lables
 
        tbw.setHorizontalHeaderLabels(list(pars_d.keys()))
        tbw.setVerticalHeaderLabels(['base'])
        
        #populate w/ base parameter values
        self.feedback.upd_prog(50)
        for j, (attn, val_raw) in enumerate(pars_d.items()): #loop on columns
                
            tbw.setItem(0, j, QTableWidgetItem(str(val_raw)))
            
 
 
        tbw.call_all_headers('setTextAlignment',Qt.AlignLeft, axis=1)           
        log.debug('filled table')
        
        #add the first column
        self._change_tab('tab_compile')
        self.compile_add()
        
        #=======================================================================
        # #populate the DataFiles comboBox_DF_par
        #=======================================================================
        #get raw the data files
        datafile_pars_d = dict()
        for sectName, pars_d in cfPars_d.items():
            if sectName in ['results_fps']: #skip these
                continue
            if sectName.endswith('_fps'):
                datafile_pars_d.update(pars_d)
                
        #clear out any nulls
        datafile_pars_d = {k:v for k,v in datafile_pars_d.items() if not v==''}
        
        #clear csvs only
        datafile_pars_d = {k:v for k,v in datafile_pars_d.items() if v.endswith('.csv')}
                
        #add these to the combo box
        self.comboBox_DF_par.clear()
        self.comboBox_DF_par.addItems(list(datafile_pars_d.keys()))
        self.comboBox_DF_par.setCurrentIndex(-1)
        self.comboBox_DF_par.setDisabled(False)
        
 
        
        
        return
        
    def compile_add(self, #add a new column to the parmaeters tab
                     ):
        
        #=======================================================================
        # default
        #=======================================================================
        log = self.logger.getChild('compile_add')
        
        self.set_setup(set_cf_fp=False)
        
        tbw = self.tableWidget_P
        self.feedback.upd_prog(10, method='portion')
        
        #add a row
        i = tbw.rowCount()  #new index (base=0)
        tbw.insertRow(i)
        
        #set a new header
        mtag = 'cand%02i'%i
        tbw.setVerticalHeaderItem(i, QTableWidgetItem(mtag))
        
        #populate it w/ values from teh base column
        for j in range(0,tbw.columnCount(),1):
            tbw.setItem(i,j, QTableWidgetItem(tbw.item(0,j)))
            
        self.feedback.upd_prog(90, method='portion')
        
        #set a new name
        baseName = tbw.item(0,0).text()
        tbw.setItem(i,0,QTableWidgetItem('%s_%02i'%(baseName, i)))
        

        
        #set alignment
        #tbw.call_all_items('setTextAlignment', 2)
        
        log.push('added \'%s\''%mtag)
        
        self.feedback.upd_prog(None) #set the progress bar back down to zero
        
    def compile_remove(self, #remove a candidate column
                       ):
        
        self.feedback.upd_prog(5)
        tbw = self.tableWidget_P
        tbw.removeRow(tbw.rowCount()-1)
        self.feedback.upd_prog(90)
        self.logger.push('removed row')
        self.feedback.upd_prog(None)
            
    def compile_randomColors(self, #add a row of random colors
                          ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        
        log = self.logger.getChild('compile_randomColors')
        self.set_setup(set_cf_fp=False)
        tbw = self.tableWidget_P
        colorMap=self.colorMap
        
        #=======================================================================
        # get old colors
        #=======================================================================
        #identify the row w/ color in it
        index_d = tbw.get_headers(axis=1)
        log.info('randomizing colors')
        self.feedback.upd_prog(10)
        
        #no color...add your own
        if not 'color' in index_d:
            """would only happen for controFiles w/o color?"""
            log.info('\'color\' not found... adding row')
            j = tbw.columnCount()
            
            #add the row
            tbw.insertColumn(j)
            tbw.setHorizontalHeaderItem(j, QTableWidgetItem('color'))
            
            #set to black
            tbw.setItem(0,j,QTableWidgetItem('black'))
            
        
        #just retrieve
        else:
            j = index_d['color']
            
        log.debug('color row=%i'%j)
        
        #get these values
        oldColorVals_d = tbw.get_values(j, axis=1)
        self.feedback.upd_prog(50)
        #=======================================================================
        # get new colors
        #=======================================================================
        import matplotlib.pyplot as plt
        import matplotlib.colors
        #retrieve the color map
        cmap = plt.cm.get_cmap(name=colorMap)
        #get a dictionary of index:color values           
        d = {i:cmap(ni) for i, ni in enumerate(np.linspace(0, 1, len(oldColorVals_d)))}
        
        #convert to hex
        newColor_d = {i:matplotlib.colors.rgb2hex(tcolor) for i,tcolor in d.items()}
        self.feedback.upd_prog(75)
        
        #replcae hashtag 
        """parser treats hashtags as comments"""
        #newColor_d = {k:v.replace('#','?') for k,v in newColor_d.items()}
        
        #reset the base

        newColor_d[0] = oldColorVals_d['base'] #dont convert to hex
        
        #=======================================================================
        # update the table
        #=======================================================================
        tbw.set_values(j, newColor_d, axis=1)
        self.feedback.upd_prog(99)
        log.debug('set %i colors'%len(newColor_d))
        self.feedback.upd_prog(None)
        return
    
    def compile_candidates(self,
                           ):
        log = self.logger.getChild('compile_cand')
        tbw = self.tableWidget_P
        
        self.set_setup(set_cf_fp=True, set_absolute_fp=True)
        #=======================================================================
        # get data from ui
        #=======================================================================
        df_raw = tbw.get_df()
        log.debug('retrieved %s'%str(df_raw.shape))
        
        """
        TODO: format those that dont match
        """
        self.feedback.upd_prog(20)
        #=======================================================================
        # construct candidate suite
        #=======================================================================
        log.debug('on %s'%str(df_raw.shape))
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiConstructor(**kwargs) as wrkr:
            wrkr.setup() #load the cf from the setup tab
            meta_lib = wrkr.build_candidates(df_raw, copyDataFiles=self.checkBox_P_copyData.isChecked())
            
            
        log.info('compiled %i candidate models'%len(meta_lib))
        self.feedback.upd_prog(50)
        
        
        #=======================================================================
        # mmake display pretty
        #=======================================================================
        #=======================================================================
        # pretty_df = self._pretty_parameters() #retrieve from tableWidget_P
        # tbw.populate(pretty_df)
        #=======================================================================
        
        #=======================================================================
        # update if we made new datafiles
        #=======================================================================
        if self.checkBox_P_copyData.isChecked():
            
            #collect the new parameters
            newPars_d = {k:dict() for k in meta_lib.keys()} #empty container
            for mtag, meta_d in meta_lib.items():
                for sectName, val_d in meta_d['pars_d'].items():
                    if not sectName.endswith('_fps'): continue #skip these
                    
                    #clear the blanks
                    d = {k:v for k,v in val_d.items() if not v==''}
                    
                    newPars_d[mtag].update(d)
                    
            #add these to the table
            df_raw1 = tbw.get_df() 
            
            
            
            jdf = pd.DataFrame.from_dict(newPars_d).T
            
            boolcol = df_raw1.columns.isin(jdf.columns)
 
            df1 = df_raw1.loc[:, ~boolcol].join(jdf)
 
            tbw.populate(df1)

        
       
        self.feedback.upd_prog(90)
        #=======================================================================
        # update run tab
        #=======================================================================
        #collect control files
        cf_fp_d = {mtag:d['cf_fp'] for mtag, d in meta_lib.items()}
        cf_fp_d ={**{'base':self.cf_fp}, **cf_fp_d} #add the base
        cf_fp_d = {k:{'cf_fp':v} for k,v in cf_fp_d.items()}
        
        
        self.tableWidget_R.populate(pd.DataFrame.from_dict(cf_fp_d).T)
        self.pushButton_R_run.setDisabled(False)
        
        #=======================================================================
        # update datFiles
        #=======================================================================
        self.pushButton_DF_load.setDisabled(False)
        
        #candidate name
 
        self.comboBox_DF_candName.setDisabled(False)
        self.comboBox_DF_candName.clear()
        head_d = self.tableWidget_P.get_headers(axis=0)
        del head_d['base'] #never want this
        self.comboBox_DF_candName.addItems(list(head_d.keys()))
        self.comboBox_DF_candName.setCurrentIndex(-1)
        
        """parameters are handled when the master datafile is loaded"""
        
        
        
        self._change_tab('tab_dataFiles')
        self.feedback.upd_prog(None)
 
        
        
        return
    
    def run_RunSuite(self):
        
        log = self.logger.getChild('compile_cand')
        tabw = self.tableWidget_R
        self.set_setup(set_cf_fp=True)
        
        self.feedback.upd_prog(5)
        #=======================================================================
        # retrieve control files from table
        #=======================================================================
        cf_d=tabw.get_values(0, axis=1)
        self.feedback.upd_prog(10)
        #=======================================================================
        # execute sutie
        #=======================================================================
        
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiSessRunner(**kwargs) as ses:
            res_lib, meta_d= ses.run_batch(cf_d)
            
            output = ses.write_pick()
            
        self.feedback.upd_prog(90)
        #=======================================================================
        # update ui
        #=======================================================================
        self.lineEdit_A_pick_fp.setText(output)
        
        self.analysis_loadPick()
        
        self._change_tab('tab_analysis')
        
        
    def analysis_loadPick(self): #update the UI with results found in pickle
        log = self.logger.getChild('analysis_loadPick')
        self.set_setup(set_cf_fp=True)
        rcoln = 'ead_tot'
        pick_fp = self.lineEdit_A_pick_fp.text()
        
        self.feedback.upd_prog(5, method='portion')
        #=======================================================================
        # run analysis on complied results
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiSessResults(**kwargs) as ses:
            pick_d = ses.load_pick(pick_fp)
            meta_d = pick_d['meta_d']
        
            rdf_raw = ses.analy_evalTot()
            
            impactFmtFunc = ses.impactFmtFunc
 
        self.feedback.upd_prog(50, method='portion')
        #=======================================================================
        # update the summary labels
        #=======================================================================
        self.label_A_S_count.setText(str(len(rdf_raw)))
        self.label_A_S_eMin.setText(impactFmtFunc(rdf_raw[rcoln].min()))
        self.label_A_S_eMax.setText(impactFmtFunc(rdf_raw[rcoln].max()))
        self.label_A_S_eVar.setText(impactFmtFunc(rdf_raw[rcoln].var()))
        
        self.label_A_S_runTag.setText(meta_d['runTag'])
        self.label_A_S_runDate.setText(str(meta_d['runDate']))
        self.label_A_S_runTime.setText("{:,.2f} sec".format(meta_d['runTime'].total_seconds()))
        
        #=======================================================================
        # add the parameters to the display
        #=======================================================================
        #format results columns
        rdf1 = rdf_raw.copy()
            
        """TODO: load parameters from pickle instead"""
        try:
            #retrieve the parameter/copmile df
            par_df = self._pretty_parameters() 
            
            assert np.array_equal(rdf_raw.index, par_df.index), 'mismatch between pickle and parameters'
            

            for coln, col in rdf_raw.copy().items():
                
                #apply the formatter
                if coln in [rcoln, 'delta']:
                    rdf1.loc[:, coln] = col.apply(impactFmtFunc)
            
            #join in parameters
            df1 = rdf1.join(par_df)
            
            #promote name column
            l = df1.columns.tolist()
            l.remove('name')
            
            df1 = df1.loc[:, ['name'] + l]
            
        except Exception as e:
            log.warning('failed to join parameters w/ \n    %s'%e)
            df1 = rdf1
            
        self.feedback.upd_prog(50, method='portion')
        #=======================================================================
        # update the table
        #=======================================================================
        tbw = self.tableWidget_A
        tbw.populate(df1.reset_index())
        
        #make not editable
        tbw.call_all_items('setFlags',Qt.ItemIsEditable)
        tbw.call_all_headers('setTextAlignment',Qt.AlignLeft, axis=1)
        
        #change color
        for coln in rdf1.columns.tolist() + ['name']:
            tbw.call_row_items('setBackground', coln, QtGui.QColor(255, 0, 0, 50)) #transparent red
            
        
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.push('loaded pickel from %s'%os.path.basename(pick_fp))
        self.feedback.upd_prog(None)
        

        
        #=======================================================================
        # save for tests
        #=======================================================================
        self.run_pick_d = pick_d
        
        
            
            
    def analysis_plotRiskCurves(self):
        log = self.logger.getChild('analysis_loadPick')
        self.set_setup(set_cf_fp=True)
        self.feedback.upd_prog(5)
        pick_fp = self.lineEdit_A_pick_fp.text()
        
        #plut controls
        y1labs = list()
        for y1lab, checkBox in {
            'impacts':self.checkBox_A_ari,
            'AEP':self.checkBox_A_aep,
            }.items():
            if checkBox.isChecked():y1labs.append(y1lab)
        self.feedback.upd_prog(10)
        #=======================================================================
        # run analysis on complied results
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiSessResults(**kwargs) as ses:
            pick_d = ses.load_pick(pick_fp)
            fig_d = ses.plot_riskCurves(y1labs=y1labs)
            
        self.feedback.upd_prog(80)
        log.push('built %i curves'%len(fig_d))
        
        #output the figures
 
        for y1lab, fig in fig_d.items():
            self.feedback.upd_prog(50, method='portion')
            self.output_fig(fig)
            
        self.feedback.upd_prog(None)
            
        #=======================================================================
        # save for tests
        #=======================================================================
        self.fig_d=fig_d
        
        return
            
            
    
    def analysis_plotBox(self):
        log = self.logger.getChild('analysis_plotBox')
        self.set_setup(set_cf_fp=True)
 
        pick_fp = self.lineEdit_A_pick_fp.text()
        
        self.feedback.upd_prog(10)
        #=======================================================================
        # run analysis on complied results
        #=======================================================================
        kwargs = {attn:getattr(self, attn) for attn in self.inherit_fieldNames}
        with SensiSessResults(**kwargs) as ses:
            pick_d = ses.load_pick(pick_fp)
            
 
            fig = ses.plot_box()
            
        log.push('built box plot')
        
        self.feedback.upd_prog(80)
        self.output_fig(fig)
            
        
        self.feedback.upd_prog(None)
        return
    
    def analysis_print(self):
        self.logger.warning('not implemented')
        
        
        
        
        
        
    
    def _pretty_parameters(self, #get just the parameters that are different
                           df_raw=None):
 
        
 
        if df_raw is None:
            """transposing for type preservation"""
            df_raw = self.tableWidget_P.get_df()
            
            
        assert 'name' in df_raw.columns
        
        #find where a row has all the same values
        boolcol = np.invert(df_raw.eq(df_raw.iloc[0,:], axis=1).all(axis=0))
        
 
        df1 = df_raw.loc[:, boolcol].copy()
        
        #fix color values
        #=======================================================================
        # if 'color' in df1.columns:
        #     df1.loc[:, 'color'] = df1['color'].str.replace('?','#')
        #=======================================================================
        
        return df1 
    
    def datafiles_load(self): #load a data file
        log = self.logger.getChild('datafiles_load')
        self.set_setup(set_cf_fp=False)
 
        #=======================================================================
        # check parameter
        #=======================================================================
        parName = self.comboBox_DF_par.currentText()
        if parName=='':
            log.error('must provide a valid paramater')
            return
        
        #get valid pars
        validPars_d = dict()
        for sectName, pars_d in Model.master_pars.copy().items():
            if sectName in ['dmg_fps', 'risk_fps']:
                validPars_d.update(pars_d)
                
        if not parName in validPars_d:
            log.error('\'%s\' not a valid parameter'%parName)
            return
 
        #=======================================================================
        # #retrieve from  ui and check
        #=======================================================================
        fp = self.lineEdit_DF_fp.text()
        valid=None
        if not isinstance(fp, str):
            valid='no filepath provided'
        
        if not os.path.exists(fp):
            valid='filepath does not exist'
        
        ext= os.path.splitext(os.path.basename(fp))[1]
        if not ext in ['.csv']:
            valid='unrecognized extension: %s'%ext
            
        if isinstance(valid, str):
            log.error(valid)
            return
        
    
        #=======================================================================
        # load
        #=======================================================================
        #retrieve loading parameters
        self.feedback.upd_prog(20)
        dtag_d = Model.dtag_d.copy()
        if parName in dtag_d:
            loadPars_d = dtag_d[parName]
        else:
            loadPars_d = {}
        
        df_raw = pd.read_csv(fp, **loadPars_d)
        
        #clean up index
        if isinstance(df_raw.index.name, str):
            df = df_raw.reset_index()
        else:
            df=df_raw.copy()
        
        """use the field calculator
 
        """
        self.feedback.upd_prog(40)
        #=======================================================================
        # load to gui
        #=======================================================================
        #vlay_raw = self.load_vlay(fp, logger=log, providerLib='delimitedtext', addSpatialIndex=False)
        vlay = self.vlay_new_df2(df, logger=log, layname=os.path.splitext(os.path.basename(fp))[0])
        self.qproj.addMapLayer(vlay, True)  
        
        self.dataFile_vlay = vlay #attach to self for saving
        
        log.info('loaded %s'%vlay.name())
        
        self.feedback.upd_prog(90)
        #=======================================================================
        # handle siblings
        #=======================================================================
        #set filepath on the sink
        self.linEdit_DF_new_fp.setText(fp)
        
        #activate the save button
        self.pushButton_DF_save.setDisabled(False)
        self.feedback.upd_prog(None)
        self.datafile_df = df.copy() #for testing
        return
    
    def _dataFiles_sourceFile(self): #set the datafile path when the combobox changes
 
        #get value on combo box
        parName = self.comboBox_DF_par.currentText()
        candName = self.comboBox_DF_candName.currentText()
        
        for v in [parName, candName]:
            if v=='':
                return
        
        #retrieve filepath
        pars_d = self.tableWidget_P.get_values(candName, axis=0)
        assert parName in pars_d, 'failed to get \'%s\' for \'%s\''%(parName, candName)
        data_fp = pars_d[parName]
        
        #empty check
        if pd.isnull(data_fp):
            self.logger.push('got null filepath for \'%s\''%data_fp)
            return
        
        assert isinstance(data_fp, str), 'got bad filepath for %s'%parName
        assert os.path.exists(data_fp), 'requested file path for \'%s\' does not exist'%parName
        
        #set on the source lineedit
        self.lineEdit_DF_fp.setText(data_fp)
        
        """setting the sink filepath once the user clicks Load"""
        
    def datafiles_save(self): #save the datafile
        log = self.logger.getChild('datafiles_save')
        self.set_setup(set_cf_fp=False)
        self.feedback.upd_prog(10)
        
        #retrieve datavlay
        vlay = self.dataFile_vlay
        assert isinstance(vlay, QgsVectorLayer), 'must load a datafile'
        
        #get the output 
        out_fp = self.linEdit_DF_new_fp.text()
        assert isinstance(out_fp, str), 'must provide a valid outpath'
        assert out_fp.endswith('.csv'), 'must specify a csv file'
        #=======================================================================
        # #retrieve data
        #=======================================================================
        df = vlay_get_fdf(vlay, logger=log)
        
        self.feedback.upd_prog(50)
        #=======================================================================
        # write data
        #=======================================================================
        #=======================================================================
        #retrieve loading parameters
        parName = self.comboBox_DF_par.currentText()
        # assert not parName=='', 'must select a valid parameter name'
        # dtag_d = copy.deepcopy(Model.dtag_d)
        # if parName in dtag_d:
        #     """getting strange overwriting bhavior on class"""
        #     loadPars_d = dict()
        #     
        #     #convert
        #     """not sure why read/write pars are different"""
        #     for k,v in copy.deepcopy(dtag_d[parName]).items():
        #         
        #         if k=='index_col':
        #             k1 = 'index'
        #             
        #             if v is None:
        #                 v1=False
        #             else:
        #                 v1=False #we reset the index
        #         else:
        #             k1,v1 = k,v
        #             
        #         loadPars_d[k1]=v1
        #         
        #                 
        #                 
        # else:
        #     loadPars_d = {}
        #=======================================================================
        loadPars_d={'index':False}
        self.feedback.upd_prog(80)
        #=======================================================================
        # #save to file
        #=======================================================================
        log.debug('writing %s w/ %s \n%s'%(str(df.shape), loadPars_d, df))
        df.to_csv(out_fp, **loadPars_d)
        log.debug('wrote to %s'%out_fp)
        self.feedback.upd_prog(90)
        #=======================================================================
        # clean up
        #=======================================================================
        self.pushButton_DF_save.setDisabled(True) #turn the button off
        self.linEdit_DF_new_fp.setText('') #clear the datafile name
        self.lineEdit_DF_fp.setText('')
        
 
        self.qproj.removeMapLayer(vlay.id())
        
        log.push('saved modified \'%s\' to %s'%(parName, os.path.basename(out_fp)))
        self.feedback.upd_prog(None)
        return
        
        

 
 
 
        
        
 
 
            
            
        
        
            
            
        
        
        