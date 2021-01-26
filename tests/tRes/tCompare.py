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

        

class tAtw(tRes): #worker for testing the damage model
    """not testing any data... just making sure we get a figure"""
    
    modelClassObj = Cmpr
    
    
    def __init__(self, *args, **kwargs):
        """called for each test METHOD"""
        super().__init__(*args, **kwargs) #init baseclass
    
    def test_noFail(self, #testing the main output

                  ): 
        print('test_noFail on \'%s\''%self.name)
        

        #=======================================================================
        # #run the model
        #=======================================================================
        si_ttl = self.Model.get_slice_noFail()
        """TODO: add data check?"""
        self.assertTrue(len(si_ttl)>0, msg=self.name)
        #=======================================================================
        # plot
        #=======================================================================
        for y1lab in ['AEP', 'impacts']:
            fig = self.Model.plot_slice(si_ttl, y1lab=y1lab)
            self.assertIsInstance(fig, plt.Figure,  msg='%s'%self.name)
            
    def test_stacks(self):
        print('test_stacks on \'%s\''%self.name)
        stack_dxind, sEAD_ser = self.Model.get_stack()
        
        self.assertTrue(len(stack_dxind)>0, msg=self.name)
        
        #loop and check plots
        for y1lab in ['impacts', 'AEP']:
            fig = self.Model.plot_stackdRCurves(stack_dxind, sEAD_ser, y1lab=y1lab)
            self.assertIsInstance(fig, plt.Figure,  msg='%s'%self.name)

        

        
        

def gen_suite(

    runpars_d={
        'tut2':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\CanFlood_tut2a_20210123.txt',
            'fps_d':{
                 'tut2_01.a01':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\CanFlood_tut2a_20210123.txt',
                 'tut2_01.b01':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\CanFlood_tut2b_20210123.txt',
                'tut2_01.c01.mutEx':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\CanFlood_tut2c_20210123_mutEx.txt',
                }
            }
        }

    ):
    
    return get_suite(runpars_d,tAtw,
                      dataLoad_pars = {},
                      )
    
if __name__ == '__main__':
    print('executing tests \n\n')
    suite = gen_suite()
    unittest.TextTestRunner(verbosity=3).run(suite)
    

    
    
    
    
    
    
    
    
    
    
    
    