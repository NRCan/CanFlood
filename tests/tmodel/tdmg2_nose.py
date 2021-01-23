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


import unittest
import nose
from nose import tools

#from nose.loader import TestLoader
from unittest import TestLoader


def Tdmg(object):
    def __init__(self, *args, **kwargs):
        #super().__init__(*args, **kwargs) #initilzie the baseclass cascade
        print('init \'%s\' \'%s\' w/ \n    args: %s \n    kwargs: %s'%(
            self.__class__.__name__, self.name, args, kwargs))
    
    
    @classmethod
    def setupClass(self):
        print('setting up parent class \'%s\'\n'%self.__class__.__name__)
    
    def test_one(self):
        assert True
    def test_two(self):
        assert False
    


def test_all():
    runpars_d={
        'tut2_01.b01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\CanFlood_tut2b_20210123.txt',
             #'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\dmg2',
             }, 
        'tut2_01.a01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\CanFlood_tut2a_20210123.txt',
             #'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\dmg2',
             }, 
             }
    
    for testName, d in runpars_d.items():
        
    
    
        



if __name__ == '__main__':


    
    #suite = get_suite(runpars_d)
    
    #unittest.TextTestRunner(verbosity=0).run(suite)
    
    #nose.core.TextTestRunner(verbosity=0).run(Test_dmg)
    nose.runmodule(argv=['--verbosity=3', '--nocapture', '--with-id'])
        
      

    
    #===========================================================================
    # unittest.main(
    #     module='__main__', #pull tests from this module
    #     defaultTest=None, #None=all TestCases
    #     exit=False, #True: command line (call sys.exit())
    #     )
    #===========================================================================
    
    
    
    
    
    
    
    
    
    
    
    
    