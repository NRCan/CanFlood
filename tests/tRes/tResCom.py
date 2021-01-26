'''
Created on Jan. 23, 2021

@author: cefect

common model testing methods
'''
import unittest, tempfile, inspect, logging, os, fnmatch, re
import pandas as pd
import numpy as np
from unittest import TestLoader

#customs
from tScripts import tWorker, load_test_data

mod_logger = logging.getLogger('tModCom')


class tRes(tWorker): #common model level testing methods
    pass #just a placeholder for now





def get_suite(suitePars_d, #build the tDmg testing suite from a set of paramters
              testClassObj,
              dataLoad_pars={},
              absolute_fp=True,
 
                ):
    
    suite = unittest.TestSuite() #start the suite container
    
    for testName, d in suitePars_d.items():

        #setup the model to test
        Model = testClassObj.modelClassObj(d['cf_fp'], 
                    out_dir=tempfile.mkdtemp(), #get a dummy temp directory
                    logger=mod_logger.getChild(testName), 
                    tag=testName, 
                     absolute_fp=absolute_fp, 
                     )._setup()
                     
        #load the check data
        """returns an empty dict if no datLoad_pars are passed"""
        tdata_d = load_test_data(d['res_dir'],dataLoad_pars=dataLoad_pars)
        
        #build a test for each mathing method in the class
        for tMethodName in TestLoader().getTestCaseNames(testClassObj):
            suite.addTest(testClassObj(tMethodName, Model=Model, tdata_d=tdata_d))

    print('built suites')
    return suite



    
    
    
    
    
    
    
    
