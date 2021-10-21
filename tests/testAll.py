'''
Created on Jan. 23, 2021

@author: cefect


testing workflows rather than models
    gets more testing out of a dataset
    better reflects real use
    tests the tutorials better
    
each test method is 1 workflow
    each call should be for one set of inputs
    
using pickels to hold comparison data

see below for instructions on use


'''

#===============================================================================
# imports----------
#===============================================================================
import unittest, tempfile, inspect, logging, os, fnmatch, pickle, datetime
from unittest import TestLoader
from qgis.core import QgsCoordinateReferenceSystem, QgsMapLayerStore
import pandas as pd
import numpy as np

start = datetime.datetime.now()

#===============================================================================
# cf helpers
#===============================================================================
#import hlpr.basic
#from hlpr.logr import basic_logger
 
from hlpr.exceptions import Error


#===============================================================================
# CF workers
#===============================================================================
from wFlow.scripts import Session, WorkFlow

from model.riskcom import RiskModel


#===============================================================================
# methods---------
#===============================================================================
class RMwrkr(RiskModel):
    def __init__(self):pass
riskmodel = RiskModel()


#===============================================================================
# UNIT TESTS--------
#===============================================================================
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
        self.name='%s.%s'%(runr.name, runr.tag)


        super().__init__(*args, **kwargs) #initilzie the baseclass cascade
        
        self.logger = runr.logger.getChild('utest')
    #===========================================================================
    # expected handler methods---------
    #===========================================================================
        
    def setUp(self):
        #print('setting up %s (%s) %s'%(self.__class__.__name__, self.Model.tag, self._testMethodName))
        pass
    def tearDown(self):
        #print('tearing down %s (%s) %s \n'%(self.__class__.__name__, self.Model.tag, self._testMethodName))
        pass
    
    def _get_data(self, keys):
        """
        keys passed NOT found in teh CALC set will be ignored
        """
        #=======================================================================
        # get the data
        #=======================================================================
        calc_d = {k:v for k,v in self.runr.res_d.items() if k in keys} #requested keys from calc set
        test_d = self.runr.pick_d #test library 
        
        """
        self.runr.res_d['si_ttl']
        """
        #=======================================================================
        # key check
        #=======================================================================
        #check we have everything found in teh calc set in the test set
        miss_l = set(calc_d.keys()).difference(test_d.keys())
        assert len(miss_l)==0, 'missing keys: %s'%miss_l
        
        return {k:(v, test_d[k]) for k,v in calc_d.items()}
    
    def _df_chks(self, valC, valT, nm):

        assert isinstance(valC, pd.DataFrame), nm
        
        #column dtypes
        self.assertEqual(valC.dtypes[0].char, valT.dtypes[0].char, msg=nm)
        
        #shape
        self.assertEqual(valC.shape, valT.shape, msg=nm)
        
        #colum names
        miss_l = set(valC.columns).symmetric_difference(valT.columns)
        self.assertEqual(len(miss_l), 0, msg=nm + 'column mismatch: %s'%miss_l)
        
        #null counts
        self.assertEqual(valC.isna().sum().sum(), valT.isna().sum().sum(),
                         msg = nm + 'null count mismatch')
        
        #float checks
        boolcol = valC.dtypes.apply(lambda x:np.issubdtype(x, np.number))
        sumC = round(valC.loc[:, boolcol].sum().sum(), self.prec)
        sumT = round(valT.loc[:, boolcol].sum().sum(), self.prec)        
        self.assertEqual(sumC, sumT, msg= nm + 'sum fail')
    


class Test_wf_basic(TestParent): #test for all risk model workflows
    

    def test_finv(self):
        self.logger.info('test_finv on %s'%self.name)
        keys = ['finv']
        
        chk_d = self._get_data(keys) #get the zipped checking data

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            self._df_chks(valC, valT, nm)

    def test_expos(self):
        self.logger.info('test_expos on %s'%self.name)
        #get the zipped checking data
        chk_d = self._get_data(['expos', 'exlikes', 'r_passet', 'gels'])

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            assert len(valC.dtypes.unique())==1, 'got multiple dtypes'
            self._df_chks(valC, valT, nm)
            
class Test_wf_L1(Test_wf_basic): #tests for level 1 models
    def test_rttl(self):
        keys = ['r_ttl']
        
        chk_d = self._get_data(keys) #get the zipped checking data

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            #clean these up
            valC = riskmodel.set_ttl(tlRaw_df=valC)
            eadC = riskmodel.ead_tot
            valT = riskmodel.set_ttl(tlRaw_df=valT)
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
            

class Test_wf_L2(Test_wf_L1): #tests for level 2 models
    
    def test_dmgs(self):
        self.logger.info('test_dmgs on %s'%self.name)
        #get the zipped checking data
        chk_d = self._get_data(['dmgs'])

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            assert len(valC.dtypes.unique())==1, 'got multiple dtypes'
            self._df_chks(valC, valT, nm)

class Test_wf_cmpre(Test_wf_L1): #tests for models w/ compare
    
    def test_cmpre(self):
        self.logger.info('test_cmpre on %s'%self.name)
        #get the zipped checking data
        chk_d = self._get_data(['cf_compare'])

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            self._df_chks(valC, valT, nm)
            
class Test_wf_rprep(Test_wf_basic): #for truncated build tests
    def test_rlayCRS(self):
        keys = ['rlay_crs_d']
        
        chk_d = self._get_data(keys)

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            
            
            self.assertTrue(np.array_equal(
                pd.Series(valC),
                pd.Series(valT)
                ), msg=nm + 'rlay crs mismatch')
            
class Test_wf_dikes(TestParent):
    
    def test_exposure(self):
        keys = ['dExpo']
        chk_d = self._get_data(keys)

        #loop and compare each
        for k, (valC, valT) in chk_d.items():

            nm = '%s.%s'%(self.name, k)
            
            self._df_chks(valC, valT, nm)
            
    def test_pfail(self):
        keys= ['dike_pfail', 'dike_pfail_lfx']
        
        chk_d = self._get_data(keys)

        #loop and compare each
        for k, (valC, valT) in chk_d.items():
            nm = '%s.%s'%(self.name, k)
            self._df_chks(valC, valT, nm)
    

#===============================================================================
# TEST HANLDER--------
#===============================================================================
class Session_t(Session): #handle one test session 
    
    #===========================================================================
    # program vars
    #===========================================================================
    pickel_dir = r'tests\_data\pickles' #folder with the pickes in it
    
    def __init__(self,
                 write=False,
                 **kwargs):
        
        #init the cascade 
        """will need to pass some of these to children"""
        super().__init__(
 
            projName='test',
            plot=False, write=write,
            **kwargs) #Qcoms -> ComWrkr
        
        #=======================================================================
        # attach
        #=======================================================================

        self.pickel_dir = os.path.join(self.base_dir, self.pickel_dir)
        assert os.path.exists(self.pickel_dir), self.pickel_dir


    #==========================================================================
    # RUNNERS----------
    #==========================================================================

    def get_tests(self, #generate the test suites
              wFLow_l,
              **kwargs):
        log = self.logger.getChild('get_tests')
        #=======================================================================
        # defaults
        #=======================================================================

        #===========================================================================
        # assemble suite
        #===========================================================================
        suite = unittest.TestSuite() #start the suite container


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
            
            runr.mstore.removeAllMapLayers()
        log.info('constructed test suite from %i flows w/ %i tests in %s\n \n'%(
            len(wFlow_l), suite.countTestCases(), datetime.datetime.now()-start))
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
            
            runr.__exit__()

        log.info('finished on %i \n    %s'%(len(d), list(d.keys())))
        return d
    
#===============================================================================
# TEST WORKFLOWS----------
#===============================================================================
class WorkFlow_t(WorkFlow): #wrapper for test workflows
    
    Test = Test_wf_basic #unit test worker for this flow
    

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
        
        if data is None: 
            data={k:self.res_d[k] for k in self.tdata_keys} #just get those required by the keys
        if ofp is None:
            ofp = os.path.join(self.session.pickel_dir, '%s.pickle'%self.name)
        
        log.debug('on %s'%type(data))
        
        
        #check data
        for k,v in data.items():
            assert not hasattr(v, 'crs'), k
        
        
        with open(ofp, 'wb') as f:
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(data, f, pickle.HIGHEST_PROTOCOL)
            
        log.info('wrote pick w/ %i: %s \n    %s'%(len(data), list(data.keys()), ofp))
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
        
        #=======================================================================
        # load
        #=======================================================================
        with open(fp, 'rb') as f:
            data = pickle.load(f)
            
        #=======================================================================
        # check
        #=======================================================================
        assert isinstance(data, dict)
        miss_l = set(self.tdata_keys).difference(data.keys())
        assert len(miss_l)==0, 'pickle missing some required keys; %s'%miss_l
        log.info('got %i: %s'%(len(data), list(data.keys())))
        
        self.pick_d = data
            
#===============================================================================
# IMPORT TUTORIALS----------------
#===============================================================================
from wFlow.tutorials import Tut1a, Tut2a, Tut2b, Tut2c_mutex, Tut2c_max, Tut4a, Tut4b, \
    Tut6a, Tut5a, Tut7a

#===============================================================================
# tutorial 1
#===============================================================================
class Tut1a_t(WorkFlow_t, Tut1a): #tutorial 1a
    Test = Test_wf_L1
    #keys to include in test pickels
    tdata_keys = ['finv', 'expos', 'evals', 'r_ttl', 'eventypes', 'r_passet']

#===============================================================================
# Turorial 2
#===============================================================================
class Tut2_t(WorkFlow_t): #generic for all tutorial 2s
    Test = Test_wf_L2
    tdata_keys = ['finv', 'expos', 'evals', 'r_ttl', 'eventypes', 'r_passet', 'gels', 'dmgs']
    
class Tut2a_t(Tut2_t, Tut2a): 
    pass


class Tut2b_t(Tut2_t, Tut2b): 
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tdata_keys = self.tdata_keys.copy() + ['exlikes']
        
class Tut2c_mutex_t(Tut2c_mutex, Tut2b_t):
    pass

class Tut2c_max_t(Tut2c_max, Tut2b_t):
    Test = Test_wf_cmpre
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.tdata_keys = self.tdata_keys.copy() + ['cf_compare']
        
#===============================================================================
# Tutorial 4
#===============================================================================
class Tut4_t(WorkFlow_t):
    """"same as Tut1"""
    Test = Test_wf_L1
    tdata_keys = ['finv', 'expos', 'evals', 'r_ttl', 'eventypes', 'r_passet']
    
class Tut4a_t(Tut4a, Tut4_t):  
    pass

class Tut4b_t(Tut4b, Tut4_t):  
    pass

#===============================================================================
# tutorial 5
#===============================================================================
class Tut5a_t(WorkFlow_t, Tut5a):
    """"same as Tut1"""
    Test = Test_wf_rprep
    tdata_keys = ['finv', 'expos','rlay_crs_d']

#===============================================================================
# Tutorial 6
#===============================================================================
class Tut6a_t(WorkFlow_t, Tut6a):
    """"same as Tut1"""
    Test = Test_wf_dikes
    tdata_keys = ['dExpo_dxcol', 'dExpo', 'dike_pfail', 'dike_pfail_lfx']
    
#===============================================================================
# Tutorial 7
#===============================================================================
class Tut7_t(WorkFlow_t):
    """"same as Tut1"""
    Test = Test_wf_L1
    tdata_keys = ['finv', 'expos', 'evals', 'r_ttl', 'eventypes', 'r_passet', 'gels']
    
class Tut7a_t(Tut7a, Tut7_t):  
    pass
    
    
#===============================================================================
# extrasx
#===============================================================================
class L1_t(WorkFlow_t): 
    crsid ='EPSG:3005'
    Test = Test_wf_basic
    tdata_keys = ['finv', 'expos']
    
    def __init__(self, **kwargs):
        self.pars_d = {
                'raster_dir':r'tutorials\4\haz_rast',
                'as_inun':False,'felv':'datum'
                        }
        
        self.tpars_d = { #kwargs for individual tools
            'Rsamp':{
                'psmp_stat':'Max'
                }
            }
        

        super().__init__(**kwargs)
        
    def run(self):
        log = self.logger.getChild('r')
        
        res_d = dict()
        pars_d = self.pars_d
        
        cf_fp = self.prep_cf(pars_d, logger=log) #setuip the control file
        res_d['finv'] = self.prep_finv(pars_d, logger=log)
        res_d['expos'] = self.rsamp_haz(pars_d, logger=log)
        
        self.res_d = res_d
        
class PolyL1_t(L1_t):
    name='PolyL1'
    """
    L1 polygons (not %inundation) partial using tut4 data
    """
    def __init__(self, **kwargs):


        super().__init__(**kwargs)
        
        self.pars_d.update({
                'finv_fp':r'tutorials\4\finv_tut4a_polygons.gpkg',
                        })
    
class LineL1_t(L1_t):
    name='LineL1'
    """
    L1 lines (not %inundation) partial using tut4 data
    """
    def __init__(self, **kwargs):

        super().__init__(**kwargs)
        
        self.pars_d.update({
                'finv_fp':r'tutorials\4\finv_tut4b_lines.gpkg',
                        })

wFlow_l = [
           Tut1a_t, 
           #Tut2a_t,Tut2b_t, #these are mostly redundant w/ 2c
            
           Tut2c_mutex_t, 
           Tut2c_max_t,  #compares with Tut2c_mutex_t. write=True
           Tut4a_t, Tut4b_t, 
           Tut5a_t, 
           Tut6a_t, 
           Tut7a_t,
           PolyL1_t, LineL1_t,
           ]

#wFlow_l = [Tut7a_t]

 
    
    

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
    # build test pickesl
    #===========================================================================
    #ofp = wrkr.build_pickels(wFlow_l) #update or write test pickle
    
    #===========================================================================
    # run tests
    #===========================================================================
    suite = wrkr.get_tests(wFlow_l)
    unittest.TextTestRunner(verbosity=3).run(suite)
    
    
    #===========================================================================
    # wrap
    #===========================================================================
    print('finished in %s'%(datetime.datetime.now() - start))
    
    
     
    

    
    
    
    
    
    
    
    
    
    
    
    