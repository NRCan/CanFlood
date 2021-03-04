'''
Created on Jan. 23, 2021

@author: cefect


testing the batch runner
'''


import unittest, tempfile, inspect, logging, os, fnmatch
from unittest import TestLoader

import pandas as pd
import numpy as np




from tScripts import tWorker
from tScripts import load_test_data, get_suite


from cfBatch import CFbatch

class Runner(CFbatch): #class to run
    
    smry_d = {
              }

    def __init__(self,pars_d,
         out_dir=None,
         **kwargs):

        super().__init__(pars_d,
                 proj_dir=r'C:\LS\03_TOOLS\CanFlood\outs\lang\0228',
                 projName='Langley',
                 crs_id = 'EPSG:3005',
                 figsize=(8,6),
                 out_dir=out_dir,
             **kwargs)


class Tester(unittest.TestCase): #test worker
    prec=4 #precision for some rounding tests
    def __init__(self, *args, 
                 Runner=None, #model object to test
                 tdata_d = None, #container of data to test against

                 **kwargs):

        #=======================================================================
        # attach
        #=======================================================================
        self.Runner=Runner
        self.tdata_d = tdata_d
        self.name=Runner.tag

        assert inspect.isclass(type(Runner))
        
        #print('init \'%s\' w/ \'%s\' \n    args: %s'%(self.__class__.__name__, self.Model.tag,   args))
        

        super().__init__(*args, **kwargs) #initilzie the baseclass cascade
        
    #===========================================================================
    # expected handler methods---------
    #===========================================================================
        
    def setUp(self):
        #print('setting up %s (%s) %s'%(self.__class__.__name__, self.Model.tag, self._testMethodName))
        pass
    def tearDown(self):
        #print('tearing down %s (%s) %s \n'%(self.__class__.__name__, self.Model.tag, self._testMethodName))
        pass

 

def gen_suite( #generate the test suites


    pars_lib={
        'tut2_01.b01':{
             'cf_fp':r'tut2_01\b01\CanFlood_tut2b_20210123.txt',
             'res_dir':r'tut2_01\b01\dmg2',
             }, 

        }
    ):
    """
    should load a dataset, add a sequence of tools
    """
    
    suite = unittest.TestSuite() #start the suite container
    
    for testName, d in pars_lib.items():
        
        # setup the batch runner on these inputs
        runr = Runner(**d)
        
        tdata_d = load()
        
        
        #build a test for each mathing method in the class
        for tMethodName in TestLoader().getTestCaseNames(Tester):
            """inits the testClassObj each time"""
            suite.addTest(Tester(tMethodName, Runner=runr, tdata_d=tdata_d))
        
        
    
    return 
    
if __name__ == '__main__':
    print('executing tests \n\n')
    suite = gen_suite()
    unittest.TextTestRunner(verbosity=3).run(suite)
    

    
    
    
    
    
    
    
    
    
    
    
    