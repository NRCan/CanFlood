'''
Created on Jan. 23, 2021

@author: cefect

unit tests for the Risk2 model

TODO: add some tests for model builds that should FAIL?
'''


import unittest, tempfile, inspect, logging, os, fnmatch

import pandas as pd
import numpy as np



from model.risk2 import Risk2


"""just using the default console logger"""
mod_logger = logging.getLogger('testing')


from tmodel.tModCom import tModel, get_suite


        

class tRisk(tModel): #worker for testing the damage model
    
    
    
    def __init__(self, *args, **kwargs):
        """called for each test METHOD"""
        super().__init__(*args, **kwargs) #init baseclass
    
    def test_main(self, #testing the main output (totals)
                  dtag='ttl', 
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
        self.Model.attriMode=False #not needed for this test
        res_ttl, _  = self.Model.run(res_per_asset=False)
        
        #=======================================================================
        # #do the checking        
        #=======================================================================
        self.assertIsInstance(res_ttl, pd.DataFrame)
        
        self.assertEqual(res_ttl.shape, chk_df.shape, msg='%s'%self.name)
        
        self.assertEqual(res_ttl['impacts'].round(self.prec).sum(), 
                         chk_df['impacts'].round(self.prec).sum(),  
                         msg='%s data failed to sum'%self.name)
        
    def test_passet(self,
                    dtag='passet'):
        print('test_passet on \'%s\''%self.name)
        
        #=======================================================================
        # #check test data is available
        #=======================================================================
        assert dtag in self.tdata_d, 'missing required test data \'%s\''%dtag
        chk_df = self.tdata_d[dtag].copy()

        #=======================================================================
        # #run the model
        #=======================================================================
        self.Model.attriMode=False #not needed for this test
        _, res_df  = self.Model.run(res_per_asset=True)
        
        #=======================================================================
        # #do the checking        
        #=======================================================================
        self.assertIsInstance(res_df, pd.DataFrame)
        
        self.assertEqual(res_df.shape, chk_df.shape, msg='%s'%self.name)
        
        
        
        self.assertTrue(
            np.array_equal(
                res_df.sum().round(self.prec).values, 
                chk_df.sum().round(self.prec).values),  
                         msg='%s.%s failed to sum'%(dtag, self.name))
        
        
        
    def test_attrim(self,
                    dtag = 'attr03'):
        print('test_attrim on \'%s\''%self.name)
        #=======================================================================
        # #check test data is available
        #=======================================================================
        assert dtag in self.tdata_d, 'missing required test data \'%s\''%dtag
        chk_df = self.tdata_d[dtag].copy()
        #=======================================================================
        # #run the model
        #=======================================================================
        self.Model.attriMode=True
        #run the mode
        _, _ = self.Model.run(res_per_asset=True)
        
        #get the attributions
        atr_dxcol = self.Model.att_df
        
        #=======================================================================
        # #do the checking        
        #=======================================================================
        self.assertIsInstance(atr_dxcol, pd.DataFrame)
        self.assertIsInstance(atr_dxcol.columns, pd.MultiIndex)
        
        self.assertEqual(atr_dxcol.shape, chk_df.shape, msg='%s'%self.name)
        self.assertEqual(atr_dxcol.columns.names, chk_df.columns.names, 
                         msg='%s.%s bad mindex'%(self.name, dtag))
        
        self.assertTrue(np.array_equal(
            atr_dxcol.sum().round(self.prec).values, chk_df.sum().round(self.prec).values),  
                         msg='%s.%s failed to sum'%(self.name, dtag)
            )
        
        

        


def gen_suite(    runpars_d={

        'tut2_01.a01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\CanFlood_tut2a_20210123.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\r2',
             }, 
        'tut2_01.b01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\CanFlood_tut2b_20210123.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\r2',
             }, 
        'tut2_01.c01.mutEx':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\CanFlood_tut2c_20210123_mutEx.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\r2_mutex',
             },
        'tut2_01.c01.max':{ 
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\CanFlood_tut2c_20210123_max.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\r2_max',
             },
        'LM_bs.b01':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b01\CanFlood_Lbs6.ind.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b01\r01'
            },
        'LM_bs.b02':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b02\CanFlood_LML.bs7_b02_20210123.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b02\r01'
            },
        'LM_bs.b03_max':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\CanFlood_LML.bs7.b03_max_20210123.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\r01_max'
            },
        'LM_bs.b02_mutEx':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\CanFlood_LML.bs7.b03_mutEx_20210123.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\r02_mutEx'
            },
        }
        ):


    return get_suite(runpars_d,
                      Risk2,tRisk,
                   dataLoad_pars = {'attr03*':{'header':[0,1,2], 'index_col':0}, 
                                    '*passet.csv':{'index_col':0},
                                    '*ttl.csv':{}}
                      
                      )



    
if __name__ == '__main__':
    suite = gen_suite()
    
    print('executing tests \n\n')
    unittest.TextTestRunner(verbosity=3).run(suite)
    
    
    
    
    
    
    
    
    
    
    