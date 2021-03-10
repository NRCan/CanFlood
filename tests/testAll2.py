'''
Created on Jan. 23, 2021

@author: cefect


testing workflows rather than models
    gets more testing out of a dataset
    better reflects real use
    tests the tutorials better
    
each test method is 1 workflow
    each call should be for one set of inputs
    
let's also use pickles 

NO! we don't need the fancy multi-asset handling
    using the CFbatch to link together all the tools
'''

#===============================================================================
# imports----------
#===============================================================================
import unittest, tempfile, inspect, logging, os, fnmatch, pickle, datetime
from unittest import TestLoader
from qgis.core import QgsCoordinateReferenceSystem, QgsMapLayerStore
import pandas as pd
import numpy as np


#===============================================================================
# cf helpers
#===============================================================================
import hlpr.basic
from hlpr.logr import basic_logger
 
from hlpr.exceptions import Error


#===============================================================================
# CF workers
#===============================================================================
from wFlow.scripts import Session, WorkFlow
from wFlow.tutorials import Tut1a
from model.modcom import RiskModel


#===============================================================================
# methods---------
#===============================================================================
class RMwrkr(RiskModel):
    def __init__(self):pass
riskmodel = RiskModel()


class TestParent(unittest.TestCase): #unit test (one per test call)
    prec=4 #precision for some rounding tests
    
    """
    one test method per workflow (i.e. tutorial)
        workflows are only valid on certain datasets
        
    one test method call per dataset
         unlike the batch runner... which runs lots of assetmodels against some common inputs
        
        
    """
    def __init__(self, 
                 *args, #testmethod name should be in here 
                 runr=None, #model object to test

                 **kwargs):

        #=======================================================================
        # attach
        #=======================================================================
        self.runr=runr
        self.name=runr.tag


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
    
    #===========================================================================
    # tests-----
    #===========================================================================

class Test_wf(TestParent):
    prec=4
    
    def _get_data(self, keys):
        
        #=======================================================================
        # get the data
        #=======================================================================
        calc_d = {k:v for k,v in self.runr.res_d.items() if k in keys} #just calculated
        test_d = self.runr.pick_d #test library 
        
        #=======================================================================
        # key check
        #=======================================================================
        miss_l = set(calc_d.keys()).difference(test_d.keys())
        assert len(miss_l)==0, 'missing keys: %s'%miss_l
        
        return {k:(v, test_d[k]) for k,v in calc_d.items()}
    
    def _df_chks(self, valC, valT, nm):
        
        #self.assertIsInstance(valC, type(valT), msg=nm + 'bad type: %s'%(type(valC)))

        assert isinstance(valC, pd.DataFrame), nm
        
        #column dtypes
        
        self.assertEqual(valC.dtypes[0].char, valT.dtypes[0].char, msg=nm)
        
        #shape
        self.assertEqual(valC.shape, valT.shape, msg=nm)
        
        #colum names
        miss_l = set(valC.columns).symmetric_difference(valT.columns)
        self.assertEqual(len(miss_l), 0, msg=nm + 'column mismatch: %s'%miss_l)
        
        #float checks
        boolcol = valC.dtypes.apply(lambda x:np.issubdtype(x, np.number))
        sumC = round(valC.loc[:, boolcol].sum().sum(), self.prec)
        sumT = round(valT.loc[:, boolcol].sum().sum(), self.prec)        
        self.assertEqual(sumC, sumT, msg= nm + 'sum fail')
            
    
    def test_finv(self):
        print('test_finv on %s'%self.name)
        keys = ['finv']
        
        chk_d = self._get_data(keys) #get the zipped checking data

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            self._df_chks(valC, valT, nm)
            
    def test_rttl(self):
        keys = ['r_ttl']
        
        chk_d = self._get_data(keys) #get the zipped checking data

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            #clean these up
            valC = riskmodel.prep_ttl(tlRaw_df=valC)
            eadC = riskmodel.ead_tot
            valT = riskmodel.prep_ttl(tlRaw_df=valT)
            eadT = riskmodel.ead_tot
            
            self.assertEqual(eadC, eadT, msg= nm + 'ead mismatch')

            
            self._df_chks(valC, valT, nm)
            
    def test_etypes(self):
        keys = ['eventypes']
        chk_d = self._get_data(keys) #get the zipped checking data

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            self._df_chks(valC, valT, nm)
            
            self.assertEqual(valC['noFail'].sum(), valT['noFail'].sum(), 
                             msg= nm + 'noFail count mismatch')

            
    def test_expos(self):
        print('test_outs on %s'%self.name)
        #get the zipped checking data
        chk_d = self._get_data(['expos', 'exlikes', 'r_passet'])

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            assert len(valC.dtypes.unique())==1, 'got multiple dtypes'
            self._df_chks(valC, valT, nm)

            
class Session_t(Session): #handle one test session 
    

    
    #===========================================================================
    # program vars
    #===========================================================================
    pickel_dir = r'tests\_data\all2\pickles' #folder with the pickes in it


    def __init__(self,
                 **kwargs):
        
        #init the cascade 
        """will need to pass some of these to children"""
        super().__init__(
 
            projName='tests2',
            plot=False, write=False,
            **kwargs) #Qcoms -> ComWrkr
        
        #=======================================================================
        # attach
        #=======================================================================

        self.pickel_dir = os.path.join(self.base_dir, self.pickel_dir)
        assert os.path.exists(self.pickel_dir), self.pickel_dir

    #===========================================================================
    # CHILD HANDLING--------
    #===========================================================================


     
    #==========================================================================
    # RUNNERS----------
    #==========================================================================

    def get_tests(self, #generate the test suites
              wFLow_l,
              **kwargs):
        
        #=======================================================================
        # defaults
        #=======================================================================

        #===========================================================================
        # assemble suite
        #===========================================================================
        suite = unittest.TestSuite() #start the suite container

        d = dict()
        for fWrkr in wFLow_l:
            
            #===================================================================
            # setup the flow
            #===================================================================
            """tests handle flows AFTER they've run
            lets us run many tests on a completed flow without having to re-run teh flow each time"""
            runr = self._run_wflow(fWrkr, **kwargs)
            runr.load_pick()

            #build a test for each mathing method in the class
            for tMethodName in TestLoader().getTestCaseNames(runr.Test):
                """inits TestU
                only 1 test method per TeestU for now"""
                suite.addTest(runr.Test(tMethodName, runr=runr))
            
            
        
        return suite
    
    def build_pickels(self, #build the input and output pickels 
            wFLow_l,
            **kwargs):
        """
        should have a pickle for inputs
            and one for the outputs (that we'll test against)
        """
        log = self.logger.getChild('build_pickels')
 
        #=======================================================================
        # loop and load, execute, and save each test
        #=======================================================================
        d = dict()
        for fWrkr in wFLow_l:
            runr = self._run_wflow(fWrkr, **kwargs)
            
            d[fWrkr.name] = runr.write_pick()

        log.info('finished on %i \n    %s'%(len(d), list(d.keys())))
        return d
    
class WorkFlow_t(WorkFlow): #wrapper for test workflows
    
    Test = Test_wf #unit test worker for this flow
    prec = 4

    def __init__(self,

                 **kwargs):

        super().__init__( **kwargs) #initilzie the baseclass cascade
        self.tag = 't%s'%datetime.datetime.now().strftime('%Y%m%d')
        
        #load the pickels
        
    def write_pick(self, #write apickle of your results data
                   data=None,
                   ofp=None,
                   logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('write_pick')
        
        if data is None: data=self.res_d
        if ofp is None:ofp = os.path.join(self.session.pickel_dir, '%s.pickle'%self.name)
        
        log.info('on %s'%type(data))
        """
        data.keys()
        """
        
        with open(ofp, 'wb') as f:
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            
        log.info('wrote to %s'%ofp)
        return ofp
    
    def load_pick(self, #load your test library data from the pickle
                  fp = None,
                  logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('load_pick')
        if fp is None:
            fp = os.path.join(self.session.pickel_dir, '%s.pickle'%self.name)
        
        assert os.path.exists(fp), 'got a bad pickel fp: %s'%fp
        with open(fp, 'rb') as f:
            data = pickle.load(f)
            
        log.info('got %i: %s'%(len(data), list(data.keys())))
        
        self.pick_d = data
            
class Tut1a_t(WorkFlow_t, Tut1a): #tutorial 1a
    pass
        

        
        

        
wFlow_l = [Tut1a_t]
    
    

if __name__ == '__main__':
    
    wrkr = Session_t()
    #===========================================================================
    # build test pickesl
    #===========================================================================
    #ofp = wrkr.build_pickels(wFlow_l)
    
    #===========================================================================
    # run tests
    #===========================================================================
    suite = wrkr.get_tests(wFlow_l)
    unittest.TextTestRunner(verbosity=3).run(suite)
    
    
     
    

    
    
    
    
    
    
    
    
    
    
    
    