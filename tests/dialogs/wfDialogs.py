'''
Created on Nov. 27, 2021

@author: cefect

dialog workflows
'''
#===============================================================================
# globals
#===============================================================================
base_dir = r'C:\LS\09_REPOS\03_TOOLS\CanFlood\_git'

#===============================================================================
# imports
#===============================================================================
import os
import pandas as pd


from dialogs.wfDialComs import DialWF, run_set, WF_handler
from wFlow.scripts import WorkFlow
from hlpr.plug import QTableWidgetItem

from PyQt5.QtTest import QTest 
from PyQt5.QtCore import Qt
#===============================================================================
# custom imports
#===============================================================================
from model.modcom import Model
#===============================================================================
# dialog testers---------
#===============================================================================

#===============================================================================
# Sensitivity Dialog
#===============================================================================
from sensi.dialog import SensiDialog

class SensiDialogTester(SensiDialog):
    def connect_slots(self, ):        
        super(SensiDialogTester, self).connect_slots() 
        
#===============================================================================
# build
#===============================================================================
from build.dialog import BuildDialog
class BuildDialogTester(BuildDialog):
    def connect_slots(self, ):        
        super(BuildDialogTester, self).connect_slots() 
        
#===============================================================================
# model
#===============================================================================
from model.dialog import ModelDialog
class ModelDialogTester(ModelDialog):
    def connect_slots(self, ):        
        super(ModelDialogTester, self).connect_slots() 
        
#===============================================================================
# results        
#===============================================================================
from results.dialog import ResultsDialog
class ResultsDialogTester(ResultsDialog):
    def connect_slots(self, ):        
        super(ResultsDialogTester, self).connect_slots() 


#===============================================================================
# workflows------
#===============================================================================
class Tut8a(DialWF):
    name='tut8a'
    DialogClass=SensiDialogTester
    base_dir = base_dir
    pars_d = {}
    
 
    
    
    def pre(self, #pre-launch
            ):
        print('SensiDialogWF.run')
        
        """
        
        """
        
    def post(self,
             ):
        print('post')
        
        self._1setup()
        self._2compile()
        self._3DataFiles()
        self._4Run()
        self._5Analy()
        
    def _1setup(self):
        #=======================================================================
        # load
        #=======================================================================
        
        self.D.lineEdit_cf_fp.setText(os.path.join(self.base_dir, r'tutorials\8\baseModel\CanFlood_tut8.txt'))
        self.D.radioButton_SS_fpRel.setChecked(True)
        self.D.comboBox_S_ModLvl.setCurrentIndex(1) #modLevel=L2
        
        self.D.radioButton_s_pltFile.setChecked(True)
        
        QTest.mouseClick(self.D.pushButton_s_load, Qt.LeftButton)
 
        
    def _2compile(self):
        
        
        #add 4 candidates
        for i in range(0,3): 
            QTest.mouseClick(self.D.pushButton_P_addCand, Qt.LeftButton)
 
 
        #=======================================================================
        # change table values
        #=======================================================================
        tbw = self.D.tableWidget_P
        
        for candName, parName, pval in [
            ('cand01', 'rtail', '0.1'),
            ('cand02', 'curve_deviation', 'lo'),
            ]:
 
            j = tbw.get_indexer(parName, axis=1)
            i = tbw.get_indexer(candName, axis=0)
            tbw.setItem(i,j, QTableWidgetItem(pval))
        
        #=======================================================================
        # randomize colors
        #=======================================================================
        QTest.mouseClick(self.D.pushButton_P_addColors, Qt.LeftButton)
 
        
        #=======================================================================
        # compile
        #=======================================================================
        self.D.checkBox_P_copyData.setChecked(True)
        
        QTest.mouseClick(self.D.pushButton_P_compile, Qt.LeftButton)
        
    def _3DataFiles(self): #Manipulate Datafiles
        

        for candName, parName in [
            ('cand03', 'finv'),
            ('cand04', 'gels'),
            ]:
            
            #=======================================================================
            # select datafile
            #=======================================================================
        
            self.D.comboBox_DF_candName.setCurrentText(candName)
            self.D.comboBox_DF_par.setCurrentText(parName)
    
            self.D._dataFiles_sourceFile() #populate filepath
            
            #click the button
            QTest.mouseClick(self.D.pushButton_DF_load, Qt.LeftButton)
            
            #===================================================================
            # file manipulations
            #===================================================================
            """these wont be possible"""
            #open attribute table
            #open field calculator
            
            df = self.D.datafile_df.copy() #just pull off the dialog
            fp = self.D.lineEdit_DF_fp.text()
            
            if candName == 'cand03':
                df.loc[:, 'f0_elv'] = df['f0_elv'] -0.5
                
            elif candName=='cand04':
                df.loc[:, 'dtm_tut8'] = df['dtm_tut8'] - 0.5
                
            self.D.dataFile_vlay = self.D.vlay_new_df2(df, layname=os.path.splitext(os.path.basename(fp))[0])
            #===================================================================
            # write
            #===================================================================
 
            QTest.mouseClick(self.D.pushButton_DF_save, Qt.LeftButton)
            
            #===================================================================
            # save
            #===================================================================
            self.res_d['%s.%s'%(candName, parName)] = df.copy()
    
    def _4Run(self): #run the suite
        QTest.mouseClick(self.D.pushButton_R_run, Qt.LeftButton)
        
        self.res_d['run_pick_d'] = self.D.run_pick_d
        
        
    def _5Analy(self): #analyze results
        QTest.mouseClick(self.D.pushButton_A_plotRiskCurves, Qt.LeftButton)
        QTest.mouseClick(self.D.pushButton_A_plotBox, Qt.LeftButton)
        
        self.res_d['fig_d'] =self.D.fig_d


#===============================================================================
# Tut1a----------
#===============================================================================
class Tut1a_1build(DialWF):
    DialogClass=BuildDialogTester
    pars_d=dict()

    def pre(self, #pre-launch
            ):
        log = self.logger.getChild('pre')
        
        #=======================================================================
        # #load hazard rasters
        #=======================================================================
        rlay_d = self.load_rlays(os.path.join(self.base_dir, self.pars_d['raster_dir']), logger=log, mstore=self.mstore)
        self.session.data_d['rlay_d']= rlay_d
        self.qproj.addMapLayers(list(rlay_d.values()))
        #=======================================================================
        # #load inveneotyr.
        #=======================================================================
        finv_vlay = self.load_vlay(os.path.join(self.base_dir, self.pars_d['finv_fp']), logger=log, mstore=self.mstore)
        self.session.data_d['finv_vlay'] = finv_vlay
        self.qproj.addMapLayer(finv_vlay)
        
        log.info('finished loading layers')

    def post(self, #post launch
             ):
        print('post')
        self._1setup()
        self._2inventory()
        self._3hsamp()
        self._4eventVars()
        self._5valid()
        
    def _1setup(self):
        
        #=======================================================================
        # set session controls
        #=======================================================================
        self._setup_coms()
        
        #precision
        """
        prec=2
        """
        prec = self.pars_d['prec']
        assert isinstance(prec, int)
        self.D.spinBox_s_prec.setValue(prec)
        #prec = str(int(self.D.spinBox_s_prec.value())) #need a string for setting
        
 
        
        #=======================================================================
        # start control file
        #=======================================================================
        QTest.mouseClick(self.D.pushButton_generate, Qt.LeftButton) #calls build_scenario()
        cf_fp = self.D.lineEdit_cf_fp.text()
        assert os.path.exists(cf_fp)
        self.session.res_d['cf_fp'] = self.D.lineEdit_cf_fp.text()
 
        
    def _2inventory(self):
        
        self.D._change_tab('tab_inventory')
        
        
        #select the inventory layer (finv_tut1a) 
        self.D.comboBox_ivlay.setLayer(self.session.data_d['finv_vlay'])
        
        #set fevl
        comboBox = self.D.comboBox_SSelv
        index = comboBox.findText(self.pars_d['felv'], Qt.MatchFixedString)
        comboBox.setCurrentIndex(index)
        
        #set cid
        comboBox = self.D.mFieldComboBox_cid
        comboBox.setField(self.pars_d['cid'])
        
        #execute
        QTest.mouseClick(self.D.pushButton_Inv_store, Qt.LeftButton) 
        
    def _3hsamp(self):
        self.D._change_tab('tab_HazardSampler')
        
        #check all the loaded rastsers
        self.D.listView_expo_rlays.check_all()
        
        #execute
 
        QTest.mouseClick(self.D.pushButton_HSgenerate, Qt.LeftButton) 
        
    def _4eventVars(self):
        self.D._change_tab('tab_eventVars')
        
        #load the csv
        evals_fp = os.path.join(self.base_dir, self.pars_d['evals_fp'])
        kwargs = Model.dtag_d['evals']
        """may need something more sophisticated for different eval files"""
        evals_d = pd.read_csv(evals_fp, **kwargs).iloc[0, :].to_dict()
        
        #populate the table
        table = self.D.fieldsTable_EL
        for i, (k,v) in enumerate(evals_d.items()):
            #check
            assert table.item(i, 0).text() == k
            
            #set
            table.setItem(i,1, QTableWidgetItem(str(v)))
            
        #execute
        QTest.mouseClick(self.D.pushButton_ELstore, Qt.LeftButton) 
        
    def _5valid(self):
        #check the box
        self.D._change_tab('tab_Valid')
        self.D.checkBox_Vr1.setChecked(True)
        
        #execute
        QTest.mouseClick(self.D.pushButton_Validate, Qt.LeftButton) 
 
        
        
class Tut1a_2mod(DialWF):
    DialogClass=ModelDialogTester
    pars_d=dict()

    def pre(self, #pre-launch
            ):
        print('pre')

    def post(self, #post launch
             ):
        print('post')
        self._1setup()
        self._2riskL1()
        
    def _1setup(self):
        self._setup_coms()
        
    def _2riskL1(self):
        self.D._change_tab('tab_r1')
        
        #run controls
        self.D.checkBox_r1_rpa.setChecked(True)
        
        #plot controls
        self.D.checkBox_r1_ari.setChecked(True)
        
        #execute
        QTest.mouseClick(self.D.pushButton_r1Run, Qt.LeftButton) 
        
        #retrieve
        
 
        
class Tut1a_3res(DialWF):
    DialogClass=ResultsDialogTester
    pars_d=dict()

    def pre(self, #pre-launch
            ):
        print('pre')

    def post(self, #post launch
             ):
        print('post')
        self._1setup()
        #self._2joinGeo()
        self._3report()
 
    def _1setup(self):
        
        #=======================================================================
        # set session controls
        #=======================================================================
        self._setup_coms()
        
    def _2joinGeo(self):
        
        self.D._change_tab('tab_JoinGeo')
        
        #select the asset inventory layer
        self.comboBox_JGfinv.setLayer(self.session.data_d['finv_vlay'])
 
        #select results to join
        comboBox = self.D.comboBox_jg_par
        index = comboBox.findText('r_passet', Qt.MatchFixedString)
        comboBox.setCurrentIndex(index)
        
        #results layer styles

        comboBox = self.D.comboBox_JG_style
        comboBox.setCurrentIndex(2) #pick the style from teh tutoriral
        
 
        comboBox = self.D.comboBox_jg_relabel
        index = comboBox.findText('aep', Qt.MatchFixedString)
        comboBox.setCurrentIndex(index)
        
        
        #execute
        QTest.mouseClick(self.D.pushButton_JG_join, Qt.LeftButton) 
    
    def _3report(self):
        self.D._change_tab('tab_report')

        
        QTest.mouseClick(self.D.pushButton_rpt_create, Qt.LeftButton) #calls run_reporter()
 
        


class Tut1a(WF_handler, WorkFlow):
    name='tut1a'
    crsid ='EPSG:3005'
    workflow_l=[Tut1a_1build, Tut1a_2mod, Tut1a_3res]
 
    base_dir=base_dir
    res_d = dict() #container for results
 
    
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'finv_fp':r'tutorials\1\finv_tut1a.gpkg',
                'raster_dir':r'tutorials\1\haz_rast',
                'evals_fp':r'tests\_data\tuts\evals_4_tut1a.csv',
                #'fpol_dir':r'tutorials\1\haz_fpoly',
                
                #run controls
                'felv':'datum', 'validate':'risk1', 'prec':4, 'cid':'xid'
                        }
        
        self.tpars_d = { #kwargs for individual tools
            'Risk1':{
                'res_per_asset':True,
                }
            }
        
        super().__init__(**kwargs)
        
 
#===============================================================================
# executeors------------
#===============================================================================
 
wFlow_l = [Tut1a] #used below and by test scripts to bundle workflows

if __name__ == '__main__':
    run_set(wFlow_l)