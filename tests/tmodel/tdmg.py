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


import unittest, tempfile
#import nose
#from nose import tools

#from nose.loader import TestLoader
from unittest import TestLoader

from model.dmg2 import Dmg2


#===============================================================================
# class Dummy(object):
#     def __init__(self,
#                  cf_fp='',
#                  name='dummyName'):
#         self.cf_fp=cf_fp
#         self.name=name
#         
#         print('init \'%s\' w/ %s'%(self.__class__.__name__, self.name))
#         
#         
#     def foo(self):
#         print('yea!')
#===============================================================================


class tModel(unittest.TestCase): #common model level testing methods
    
    def __init__(self, *args, 
                 wrkr=None,
                 #==============================================================
                 # name='caseName',
                 # cf_fp='',
                 #==============================================================
                 **kwargs):
        #attach passed
        #=======================================================================
        # self.cf_fp = cf_fp
        # self.name = name
        #=======================================================================
        
        #print(type(wrkr))
        self.wrkr=wrkr
        
        print('init \'%s\' w/ \'%s\' \n    args: %s'%(
            self.__class__.__name__, self.wrkr.name,   args))
        

        super().__init__(*args, **kwargs) #initilzie the baseclass cascade
        
    #===========================================================================
    # expected handler methods---------
    #===========================================================================
    @classmethod
    def setupClass(self):
        print('setting up class \'%s\''%self.__class__.__name__)
        
        
    def setUp(self):
        print('setting up %s (%s) %s'%(self.__class__.__name__, self.wrkr.name, self._testMethodName))
    def tearDown(self):
        print('tearing down\n')
        
    def runTest(self): #called by the suite
        print('runTest')
        
    
        
    #===========================================================================
    # test methods---------
    #===========================================================================
    def test_main(self):
        print('test_main w/ \'%s\''%self.wrkr.name)
        self.wrkr.foo()
        self.assertTrue(False)
        
    def test_one(self):
        print('test_one')
        self.assertTrue(True)

        
    
#@tools.nottest
class tDmg(tModel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) #init baseclass
    
    def test_parent1(self):
        print('test parent1 on \"%s\''%self.wrkr.name)
        self.assertTrue(False)




#===============================================================================
# def get_suite1(suitePars_d, #build the tDmg testing suite from a set of paramters
#                 ):
#     
#     cases_d = dict()
#     for testName, d in suitePars_d.items():
#         cases_d[testName] = tDmg(name=testName, cf_fp=d['cf_fp'])
#         
#         #=======================================================================
#         # unittest.TestLoader().loadTestsFromTestCase(tDmg)
#         # pass
#         #=======================================================================
#     
#     return unittest.TestSuite(cases_d.values())
#===============================================================================



def get_suite(suitePars_d, #build the tDmg testing suite from a set of paramters
                ):
    
    suite = unittest.TestSuite() #start the suite container
    
    for testName, d in suitePars_d.items():

        wrkr = Dmg2(d['cf_fp'], 
                    out_dir=tempfile.mkdtemp(), #get a dummy temp directory
                    logger=mod_logger.getChild(testName), 
                    tag=tag, 
                     absolute_fp=absolute_fp, attriMode=attribution,
                     )._setup()
        
        #build a test for each mathing method in the class
        for tMethodName in TestLoader().getTestCaseNames(tDmg):
            suite.addTest(tDmg(tMethodName, wrkr=wrkr))

    print('built suites')
    return suite





if __name__ == '__main__':

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
    
    suite = get_suite(runpars_d)
    
    print('executing tests \n\n')
    unittest.TextTestRunner(verbosity=3).run(suite)
    

    
    
    
    
    
    
    
    
    
    
    
    