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


import unittest, nose







class Tmodel(unittest.TestCase):
     
    def __init__(self, *args, 
                 name='caseName',
                 cf_fp='',
                 **kwargs):
        #attach passed
        self.cf_fp = cf_fp
        self.name = name
         
         
        print('init \'%s\' \'%s\' w/ \n    args: %s \n    kwargs: %s'%(
            self.__class__.__name__, self.name, args, kwargs))
         
         
        #unittest.TestLoader().getTestCaseNames(self)
        #super().__init__(*args, **kwargs) #initilzie the baseclass cascade
         
    #===========================================================================
    # expected handler methods---------
    #===========================================================================
    @classmethod
    def setupClass(self):
        print('setting up class \'%s\''%self.__class__.__name__)
        
    def setUp(self):
        print('setting up \'%s\''%self.__name__)
    def tearDown(self):
        print('tearing down')
         
    #===========================================================================
    # test methods---------
    #===========================================================================
    def test_one(self):
        print('test child_one')
        assert True

     
 
class Tdmg(Tmodel):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) #initilzie the baseclass cascade
    
    @classmethod
    def setupClass(self):
        print('setting up parent class \'%s\'\n'%self.__class__.__name__)
      
    def test_parent_one(self):
        print('test parent1 on \"%s\''%self.name)
        assert False
        
    def test_parent_two(self):
        print('test_parent_two on \"%s\''%self.name)
        assert True
 

def test_suite(
    suitePars_d={
        'tut2_01.b01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\CanFlood_tut2b_20210123.txt',
             #'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\dmg2',
             }, 
        'tut2_01.a01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\CanFlood_tut2a_20210123.txt',
             #'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\dmg2',
             }, 
             }
     
    ):
    
    for testName, d in suitePars_d.items():
        yield Tdmg, testName, d['cf_fp']
        """couldnt figure out how to collect and run all the tests using this generator"""
        #cases_d[testName] = tDmg(name=testName, cf_fp=d['cf_fp'])
          

 
#===============================================================================
# def get_suite(suitePars_d, #build the tDmg testing suite from a set of paramters
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
 
 

#===============================================================================
# class Test_data():
#     def testNumbers(self):
#         numbers = [0,11,222,33,44,555,6,77,8,9999]
#         for i in numbers:
#             yield checkNumber, i
# 
# def checkNumber(num):
#     assert num == 33
#===============================================================================
#===============================================================================
# def test():
#     print('basic test')
#     assert False
#===============================================================================





if __name__ == '__main__':

    #===========================================================================
    # runpars_d={
    #     'tut2_01.b01':{
    #          'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\CanFlood_tut2b_20210123.txt',
    #          #'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\dmg2',
    #          }, 
    #     'tut2_01.a01':{
    #          'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\CanFlood_tut2a_20210123.txt',
    #          #'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\dmg2',
    #          }, 
    #          }
    # 
    # suite = get_suite(runpars_d)
    # 
    # unittest.TextTestRunner().run(suite)
    #===========================================================================

    #run tests in this module and allow all print statements to display
    nose.runmodule(argv=['--verbosity=3', '--nocapture', '--with-id'])

    
    #===========================================================================
    # unittest.main(
    #     module='__main__', #pull tests from this module
    #     defaultTest=None, #None=all TestCases
    #     exit=False, #True: command line (call sys.exit())
    #     )
    #===========================================================================
    
    
    
    
    
    
    
    
    
    
    
    
    