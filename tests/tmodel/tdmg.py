'''
Created on Jan. 23, 2021

@author: cefect

unit tests for model modules


best use case seems to be testing a model to see if it still generates the expected outputs from inputs
this means testing on a broad-range of inputs against each model's 'run' method
lets use one 'TestCase' for each input
    with a 'test_main' method to perform the main check against the outputs
    can always add secondary tests on the non'run' functions that sure the setUp methods
    
use a test suite to run all the tests on that model


#===============================================================================
# 2021-01-23
#===============================================================================
This is working ... but difficult to tell which test (in the suite loop) is failing
also there are no class-level fixtures (i.e., all the data would have to be re-loaded for each test)

'''


import unittest, tempfile, inspect, logging, os, fnmatch

import pandas as pd
import numpy as np


from unittest import TestLoader

from model.dmg2 import Dmg2


"""just using the default console logger"""
mod_logger = logging.getLogger('testing')


from .tModCom import tModel


        

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
        
        

        
        
#===========================================================================
# results loading functions--------
#===========================================================================
"""not called during tests"""
def load_test_data(
                   res_dir, #directory containing all the results files
                   dataLoad_pars = {'attr02*':{'header':[0,1], 'index_col':0}, 
                                    'dmgs*':{'index_col':0}}
                    ):
    
    d = dict()
    
    #get all csv files in the folder
    allfns_l = [e for e in os.listdir(res_dir) if e.endswith('.csv')]
    
    #loop and load for each search
    for searchPattern, load_kwargs in dataLoad_pars.items():
        match_l = fnmatch.filter(allfns_l, searchPattern) #get those matching the search
        assert len(match_l)==1, 'got multiple matches for \'%s\''%searchPattern
        
        #load the data
        fp = os.path.join(res_dir, match_l[0])
        d[searchPattern[:-1]] = pd.read_csv(fp, **load_kwargs)
        
        print('loaded \'%s\'  w/ %s'%(searchPattern, str(d[searchPattern[:-1]].shape)))
        
    
    return d
        
        

        






def get_suite(suitePars_d, #build the tDmg testing suite from a set of paramters
              absolute_fp=True,
              attribution=True,
                ):
    
    suite = unittest.TestSuite() #start the suite container
    
    for testName, d in suitePars_d.items():

        #setup the model to test
        Model = Dmg2(d['cf_fp'], 
                    out_dir=tempfile.mkdtemp(), #get a dummy temp directory
                    logger=mod_logger.getChild(testName), 
                    tag=testName, 
                     absolute_fp=absolute_fp, attriMode=attribution,
                     )._setup()
                     
        #load the check data
        tdata_d = load_test_data(d['res_dir'])
        
        #build a test for each mathing method in the class
        for tMethodName in TestLoader().getTestCaseNames(tDmg):
            suite.addTest(tDmg(tMethodName, Model=Model, tdata_d=tdata_d))

    print('built suites')
    return suite





if __name__ == '__main__':

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
        #      }
        #=======================================================================
        }
    
    suite = get_suite(runpars_d)
    
    print('executing tests \n\n')
    unittest.TextTestRunner(verbosity=3).run(suite)
    

    
    
    
    
    
    
    
    
    
    
    
    