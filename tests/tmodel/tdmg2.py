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







class tDmg(unittest.TestCase):
    
    def __init__(self, *args, 
                 cf_fp='',
                 **kwargs):
        #attach passed
        self.cf_fp = cf_fp
        
        
        print('init \'%s\' w/ \n    args: %s \n    kwargs: %s'%(
            self.__class__.__name__, args, kwargs))
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
        
    






def get_suite(suitePars_d, #build the tDmg testing suite from a set of paramters
                ):
    
    for testName, d in suitePars_d.items():
        
        unittest.TestLoader().loadTestsFromTestCase(tDmg)
        pass
    









if __name__ == '__main__':

    runpars_d={
        'Tut2a':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\CanFlood_tut2a.txt',
             'out_dir':r'C:\LS\03_TOOLS\CanFlood\tut_builds\2\a\dev\dmg',
             }, 
        }
    
    suite = get_suite()
    
    unittest.TextTestRunner().run(suite)
        )
      

    
    #===========================================================================
    # unittest.main(
    #     module='__main__', #pull tests from this module
    #     defaultTest=None, #None=all TestCases
    #     exit=False, #True: command line (call sys.exit())
    #     )
    #===========================================================================
    
    
    
    
    
    
    
    
    
    
    
    
    