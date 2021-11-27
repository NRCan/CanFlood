'''
Created on Nov. 27, 2021

@author: cefect

unit tests for dialog workflows
'''

#===============================================================================
# imports
#===============================================================================
import unittest, tempfile, inspect, logging, os, pickle, datetime
from unittest import TestLoader

start = datetime.datetime.now()

#===============================================================================
# custom imports
#===============================================================================

from testAll import TestParent, WorkFlow_t
from testAll import Session_t as SessTestBasic

from dialogs.wfDialComs import DSession

import matplotlib.pyplot as plt

#===============================================================================
# test hanlder------
#===============================================================================
class Session_t(DSession, SessTestBasic):
    pass

#===============================================================================
# UNIT TESTS--------
#===============================================================================

class Test_dwf_basic(TestParent): #test for all dialog workflows
    def test_figD(self):
        chk_d = self._get_data('fig_d') 
        
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            #check keys
            miss_l = set(valC.keys()).symmetric_difference(valT.keys())
            self.assertEqual(len(miss_l),0, msg=nm+' key mismatch')
            
            for figName, fig in valC.items():
                assert isinstance(fig, plt.Figure), type(fig)
                
                #check they have the same number of plotting lines
                self.assertEqual(len(fig.gca().lines), len(valT[figName].gca().lines))
                
                

class Test_tut8(Test_dwf_basic):
    def test_dataFiles(self):
        for candName, parName in [
            ('cand03', 'finv'),
            ('cand04', 'gels'),
            ]:
        
            chk_d = self._get_data('%s.%s'%(candName, parName)) #get the zipped checking data
        
            #loop and compare each
            for k, (valC, valT) in chk_d.items():
                nm = '%s.%s'%(self.name, k)
                self._df_chks(valC, valT, nm)
                
    def test_runPick(self): #check the results pickele
        
        chk_d = self._get_data('run_pick_d') #get the zipped checking data

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            
            #check keys
            miss_l = set(valC.keys()).symmetric_difference(valT.keys())
            self.assertEqual(len(miss_l),0, msg=nm+' key mismatch')
            
            #check metadta
            for k1, v1 in valC['meta_d'].items():
                if 'run' in k1: continue #skip these
                self.assertEqual(v1, valT['meta_d'][k1], msg = nm+k1+' meta mismatch: %s'%v1)
                    
 


#===============================================================================
# workflows ------
#===============================================================================
from dialogs.wfDialogs import Tut8a
class Tut8_t(WorkFlow_t, Tut8a):
    Test = Test_tut8
    
    tdata_keys = ['cand03.finv', 'cand04.gels', 'run_pick_d', 'fig_d']
 

#===============================================================================
# execute--------
#===============================================================================
wFlow_l = [Tut8_t]
    
if __name__ == '__main__':
    
    """
    #===========================================================================
    # INSTRUCTIONS: BUILDING NEW TESTS
    #===========================================================================
    build a WorkFlow subclass of the workflow you want to test
    
    wrap it with a WorkFlow_t to add teh test methods
    
    run the session to build_pickels()
    
    #===========================================================================
    # INSTRUCTIONS: UPDATING TEST COMPARISON DATAT
    #===========================================================================
    comment out all the other tests in wFlow_l
    fix comments below to also execute build_picles()
    revert comments
    NOTE: ensure 'tdata_keys' on the worker are approriate
    
    #===========================================================================
    # INSTRUCTIONS: RUNNING TESTS
    #===========================================================================
    
    run the session to get_tests()
    execute the test suite using TextTestRunner
    ensure 'build_pickels' is commented out
    """
    
    wrkr = Session_t(write=True)
 
    #===========================================================================
    # run tests
    #===========================================================================
    wrkr.run_suite(wFlow_l,
                   build_pickels=True, #results to pickels (only for adding tests)
                   get_tests=True, #assemble the test stuie
                   ) 
 
    unittest.TextTestRunner(verbosity=3).run(wrkr.suite)
    
    
    #===========================================================================
    # wrap
    #===========================================================================
    print('finished in %s'%(datetime.datetime.now() - start))