'''
Created on Nov. 27, 2021

@author: cefect

dialog testing
'''
import os


from dialogs.testDialComs import DialWF, test_set
from hlpr.plug import QTableWidgetItem

from PyQt5.QtTest import QTest 
from PyQt5.QtCore import Qt
#===============================================================================
# sensitivity analysis
#===============================================================================
from sensi.dialog import SensiDialog

class SensiDialogTester(SensiDialog):
    
    def connect_slots(self, #
                      ):
        
        super(SensiDialogTester, self).connect_slots()  


class Tut8(DialWF):
    name='tut8'
    DialogClass=SensiDialogTester
    base_dir = r'C:\LS\03_TOOLS\CanFlood\_git'
    
    
 
    
    
    def run(self, #pre-launch
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
        
        self.D.lineEdit_cf_fp.setText(r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\8\baseModel\CanFlood_tut8.txt')
        self.D.radioButton_SS_fpRel.setChecked(True)
        self.D.comboBox_S_ModLvl.setCurrentIndex(1) #modLevel=L2
        
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
                df
                
            self.D.dataFile_vlay = self.D.vlay_new_df2(df, layname=os.path.splitext(os.path.basename(fp))[0])
            #===================================================================
            # write
            #===================================================================
 
            QTest.mouseClick(self.D.pushButton_DF_save, Qt.LeftButton)
    
    def _4Run(self): #run the suite
        QTest.mouseClick(self.D.pushButton_R_run, Qt.LeftButton)
        
    def _5Analy(self): #analyze results
        QTest.mouseClick(self.D.pushButton_A_plotRiskCurves, Qt.LeftButton)
        QTest.mouseClick(self.D.pushButton_A_plotBox, Qt.LeftButton)
        

        
        
        
#===============================================================================
# executeors------------
#===============================================================================
 
wFlow_l = [Tut8] #used below and by test scripts to bundle workflows

if __name__ == '__main__':
    test_set(wFlow_l)