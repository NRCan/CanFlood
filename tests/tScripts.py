'''
Created on Jan. 26, 2021

@author: cefect

common scripts to share across testing modules
'''
#===============================================================================
# imports
#===============================================================================
import unittest, tempfile, inspect, logging, os, fnmatch, re
from unittest import TestLoader
import pandas as pd
import numpy as np

mod_logger = logging.getLogger('tModCom')
#===============================================================================
# classes
#===============================================================================
class tWorker(unittest.TestCase): #common model level testing methods
    prec=4 #precision for some rounding tests
    def __init__(self, *args, 
                 Model=None, #model object to test
                 tdata_d = None, #container of data to test against

                 **kwargs):

        #=======================================================================
        # attach
        #=======================================================================
        self.Model=Model
        self.tdata_d = tdata_d
        self.name=Model.tag

        assert inspect.isclass(type(Model))
        
        #print('init \'%s\' w/ \'%s\' \n    args: %s'%(self.__class__.__name__, self.Model.tag,   args))
        

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
    # test methods---------
    #===========================================================================

#===============================================================================
# funcs-------
#===============================================================================
def load_test_data(
                   res_dir, #directory containing all the results files
                   dataLoad_pars = {},
                   ext='.csv'
                    ):
    if len(dataLoad_pars)==0: return dict()
    d = dict()
    assert os.path.exists(res_dir), res_dir
    #get all csv files in the folder
    allfns_l = [e for e in os.listdir(res_dir) if e.endswith(ext)]
    
    #loop and load for each search
    for searchPattern, load_kwargs in dataLoad_pars.items():
        
        k = searchPattern.replace('*','').replace(ext,'') #drop all the asterisks from the key
        
        match_l = fnmatch.filter(allfns_l, searchPattern) #get those matching the search
        
        assert not len(match_l)>1, 'got multiple matches for \'%s\' \n    %s'%(searchPattern, match_l)
        assert len(match_l)==1, 'failed to get a match for \'%s\''%searchPattern
        
        
        #load the data
        fp = os.path.join(res_dir, match_l[0])
        d[k] = pd.read_csv(fp, **load_kwargs)
        
        #print('loaded \'%s\'  w/ %s'%(searchPattern, str(d[k].shape)))
        
    
    return d

def get_suite(
            suitePars_d, #build the tDmg testing suite from a set of paramters
              testClassObj,
              dataLoad_pars={},
              absolute_fp=True,
              **kwargsModel
                ):
    
    suite = unittest.TestSuite() #start the suite container
    
    for testName, d in suitePars_d.items():

        #setup the model to test
        Model = testClassObj.modelClassObj(cf_fp=d['cf_fp'], 
                    out_dir=tempfile.mkdtemp(), #get a dummy temp directory
                    logger=mod_logger.getChild(testName), 
                    tag=testName, 
                     absolute_fp=absolute_fp, 
                     **kwargsModel)._setup()
                     
        #load the check data
        tdata_d = load_test_data(d['res_dir'],dataLoad_pars=dataLoad_pars)
        
        #build a test for each mathing method in the class
        for tMethodName in TestLoader().getTestCaseNames(testClassObj):
            suite.addTest(testClassObj(tMethodName, Model=Model, tdata_d=tdata_d))

    print('built suites')
    return suite