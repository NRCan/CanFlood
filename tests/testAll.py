'''
Created on Jan. 23, 2021

@author: cefect

standalone scrip to collect all testing suites and run in bulk
'''

import unittest, importlib
#===============================================================================
# collect the suites
#===============================================================================
suite = unittest.TestSuite() #start the suite container

for packageName, modName_l in {
    'tmodel':['tRisk2', 'tDmg'],
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

