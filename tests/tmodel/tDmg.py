'''
Created on Jan. 23, 2021

@author: cefect



'''


import unittest, tempfile, inspect, logging, os, fnmatch

import pandas as pd
import numpy as np




from model.dmg2 import Dmg2


"""just using the default console logger"""


from tmodel.tModCom import tModel, get_suite


        

class tDmg(tModel): #worker for testing the damage model
    
    
    
    def __init__(self, *args, **kwargs):
        """called for each test METHOD"""
        super().__init__(*args, **kwargs) #init baseclass
    
    def test_main(self, #testing the main output
                  dtag='dmgs',
                  ): 
        print('test_main on \'%s\''%self.name)
        
        #=======================================================================
        # #check test data is available
        #=======================================================================
        assert dtag in self.tdata_d, 'missing required test data \'%s\''%dtag
        chk_df = self.tdata_d[dtag].copy()
        #=======================================================================
        # #run the model
        #=======================================================================
        res_df = self.Model.run()
        
        #=======================================================================
        # #do the checking        
        #=======================================================================
        self.assertIsInstance(res_df, pd.DataFrame)
        
        self.assertEqual(res_df.shape, chk_df.shape, msg='%s'%self.name)
        
        self.assertEqual(res_df.sum().sum(), chk_df.sum().sum(),  
                         msg='%s data failed to sum'%self.name)
        
        
        
        
    def test_attrim(self,
                    dtag = 'attr02'):
        print('test_attrim on \'%s\''%self.name)
        #=======================================================================
        # #check test data is available
        #=======================================================================
        assert dtag in self.tdata_d, 'missing required test data \'%s\''%dtag
        chk_df = self.tdata_d[dtag].copy()
        #=======================================================================
        # #run the model
        #=======================================================================
        #run the mode
        res_df = self.Model.run()
        """have to re-run the model :("""
        
        #generate attributions
        atr_dxcol = self.Model.get_attribution(res_df)
        
        #=======================================================================
        # #do the checking        
        #=======================================================================
        self.assertIsInstance(atr_dxcol, pd.DataFrame)
        self.assertIsInstance(atr_dxcol.columns, pd.MultiIndex)
        
        self.assertEqual(atr_dxcol.shape, chk_df.shape, msg='%s'%self.name)
        
        self.assertEqual(atr_dxcol.sum().sum(), chk_df.sum().sum(),  
                         msg='%s data failed to sum'%self.name)
        
        

def gen_suite(

    runpars_d={
        'tut2_01.b01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\CanFlood_tut2b_20210123.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\dmg2',
             }, 
        'tut2_01.a01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\CanFlood_tut2a_20210123.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\dmg2',
             }, 
        'tut2_01.c01.mutEx':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\CanFlood_tut2c_20210123_mutEx.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\dmg2',
             },
        #=======================================================================
        # 'tut2_01.c01.max':{ #same as mutEx
        #      'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\CanFlood_tut2c_20210123_max.txt',
        #      'res_dir':r'CC:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\dmg2',
        #      },
        #=======================================================================
        'LM_bs.b01':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b01\CanFlood_Lbs6.ind.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b01\dmg'
            },
        'LM_bs.b02':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b02\CanFlood_LML.bs7_b02_20210123.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b02\dmg'
            },
        'LM_bs.b03_max':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\CanFlood_LML.bs7.b03_max_20210123.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\dmg'
            },
        #=======================================================================
        # 'LM_bs.b02_mutEx':{ #same
        #     'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\CanFlood_LML.bs7.b03_mutEx_20210123.txt',
        #     'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\dmg'
        #     },
        #=======================================================================
        }
    ):
    
    return get_suite(runpars_d,
                      Dmg2,tDmg,
                      dataLoad_pars = {'attr02*':{'header':[0,1], 'index_col':0}, 
                                    'dmgs*':{'index_col':0}},
                      )
    
if __name__ == '__main__':
    print('executing tests \n\n')
    suite = gen_suite()
    unittest.TextTestRunner(verbosity=3).run(suite)
    

    
    
    
    
    
    
    
    
    
    
    
    