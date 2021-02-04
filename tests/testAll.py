'''
Created on Jan. 23, 2021

@author: cefect

standalone scrip to collect all testing suites and run in bulk

unit tests for model modules


best use case seems to be testing a model to see if it still generates the expected outputs from inputs
this means testing on a broad-range of inputs against each model's 'run' method
lets use one 'TestCase' for each input
    with a 'test_main' method to perform the main check against the outputs
    can always add secondary tests on the non'run' functions that sure the setUp methods
    
    
#===============================================================================
# LOGGING
#===============================================================================
see tScripts to configure the logging level
    
'''

import unittest, importlib
#===============================================================================
# collect the suites
#===============================================================================
suite = unittest.TestSuite() #start the suite container

for packageName, modName_l in {
    'tmodel':['tRisk2', 'tDmg'],
    'tRes':['tAttrib', 'tCompare'],
    }.items():
    #import the module
    for modName in modName_l:
        module =  importlib.import_module('%s.%s'%(packageName, modName))
    
        #add the suite
        suite.addTest(module.gen_suite())

    
print('collected %i testCases'%suite.countTestCases())
#===============================================================================
# run test suite
#===============================================================================
unittest.TextTestRunner(verbosity=3).run(suite)

