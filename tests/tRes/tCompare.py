'''
Created on Jan. 23, 2021

@author: cefect



'''


import unittest, tempfile, inspect, logging, os, fnmatch

import pandas as pd

import matplotlib
matplotlib.use('Qt5Agg') #sets the backend (case sensitive)
import matplotlib.pyplot as plt

#import models
from results.compare import Cmpr


"""just using the default console logger"""



from tRes.tResCom import tRes
from tScripts import get_suite

        

class tObj(tRes): #worker for testing the damage model
    """not testing any data... just making sure we get a figure"""
    
    modelClassObj = Cmpr
    
    
    def __init__(self, *args, **kwargs):
        """called for each test METHOD"""
        super().__init__(*args, **kwargs) #init baseclass
    
    def test_cf(self, #testing the main output

                  ): 
        print('test_cf on \'%s\''%self.name)
        
        mdf = self.Model.cf_compare()
        self.assertEqual(mdf.columns[-1], 'compare', msg=self.name)
        self.assertTrue(len(mdf)>0, msg=self.name)

        
    def test_riskCurves(self):
        print('test_riskCurves on \'%s\''%self.name)
        for y1lab in ['AEP', 'impacts']:
            fig = self.Model.riskCurves(y1lab=y1lab)
            self.assertIsInstance(fig, plt.Figure,  msg='%s'%self.name)
        

        
        

def gen_suite(
    runpars_d={
        'tut2':{
            'cf_fp':r'compare\CanFlood_tut2a_20210123.txt',
            'fps_d':{
                 'tut2_01.a01':r'compare\a01\CanFlood_tut2a_20210123.txt',
                 'tut2_01.b01':r'compare\b01\CanFlood_tut2b_20210123.txt',
 
                },
            'res_dir':None,
            },
        #=======================================================================
        # 'tut2_short':{ #nice to test only 2 control files
        #     'cf_fp':r'tut2_01\a01\CanFlood_tut2a_20210123.txt',
        #     'fps_d':{
        #          'tut2_01.a01':r'tut2_01\a01\CanFlood_tut2a_20210123.txt',
        #          'tut2_01.b01':r'tut2_01\b01\CanFlood_tut2b_20210123.txt',
        #         },
        #     'res_dir':None,
        #     }
        #=======================================================================
        }

    ):
    """
    Note on filepaths:
        test modules specify a base_dir higher than the control file
    however, for methods that spawn scenarios (e.g., compare)
        teh base_dir is always the location of the control file
    
    """
    
    return get_suite(runpars_d,tObj,
                      dataLoad_pars = {},
                      )
    
if __name__ == '__main__':
    print('executing tests \n\n')
    suite = gen_suite()
    unittest.TextTestRunner(verbosity=3).run(suite)
    

    
    
    
    
    
    
    
    
    
    
    
    