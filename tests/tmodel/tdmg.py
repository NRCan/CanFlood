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

'''


import unittest







class tModel(unittest.TestCase):
    
    def __init__(self, *args, 
                 name='caseName',
                 cf_fp='',
                 **kwargs):
        #attach passed
        self.cf_fp = cf_fp
        self.name = name
        
        
        print('init \'%s\' \'%s\' w/ \n    args: %s \n    kwargs: %s'%(
            self.__class__.__name__, self.name, args, kwargs))
        
        
        unittest.TestLoader().getTestCaseNames(self)
        super().__init__(*args, **kwargs) #initilzie the baseclass cascade
        
    #===========================================================================
    # expected handler methods---------
    #===========================================================================
    def setUp(self):
        print('setting up')
    def tearDown(self):
        print('tearing down')
        
    def runTest(self): #called by the suite
        print('runTest')
        
    
        
    #===========================================================================
    # test methods---------
    #===========================================================================
    def test_main(self):
        print('test_main w/ cf_fp: %s'%self.cf_fp)
    def test_one(self):
        print('test_one')
        self.assertEqual('foo'.upper(), 'FOO')
    def test_two(self):
        print('test_two')
        self.assertEqual('foo'.upper(), 'x')
        
    def tno(self):
        print('tno')
        self.assertEqual('foo'.upper(), 'FOO')
        
    

class tDmg(tModel):
    
    def test_parent1(self):
        print('test parent1 on \"%s\''%self.name)




def get_suite(suitePars_d, #build the tDmg testing suite from a set of paramters
                ):
    
    cases_d = dict()
    for testName, d in suitePars_d.items():
        cases_d[testName] = tDmg(name=testName, cf_fp=d['cf_fp'])
        
        #=======================================================================
        # unittest.TestLoader().loadTestsFromTestCase(tDmg)
        # pass
        #=======================================================================
    
    return unittest.TestSuite(cases_d.values())









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
    
    unittest.TextTestRunner().run(suite)
        
      

    
    #===========================================================================
    # unittest.main(
    #     module='__main__', #pull tests from this module
    #     defaultTest=None, #None=all TestCases
    #     exit=False, #True: command line (call sys.exit())
    #     )
    #===========================================================================
    
    
    
    
    
    
    
    
    
    
    
    
    