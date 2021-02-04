'''
Created on Jan. 23, 2021

@author: cefect



'''


import unittest
#import pandas as pd

import matplotlib
matplotlib.use('Qt5Agg') #sets the backend (case sensitive)
import matplotlib.pyplot as plt

#import models
from results.attribution import Attr


"""just using the default console logger"""



from tRes.tResCom import tRes
from tScripts import get_suite

        

class tAtw(tRes): #worker for testing the damage model
    """not testing any data... just making sure we get a figure"""
    
    modelClassObj = Attr
    
    
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
        'tut2_01.b01':{
             'cf_fp':r'tut2_01\b01\CanFlood_tut2b_20210123.txt',
             'res_dir':r'tut2_01\b01\dmg2',
             }, 

        'LM_bs.b02':{
            'cf_fp':r'LM_bs\b02\CanFlood_LML.bs7_b02_20210123.txt',
            'res_dir':r'LM_bs\b02\dmg'
            },
        }

    ):
    
    return get_suite(runpars_d,tAtw,
                      dataLoad_pars = {},
                      )
    
if __name__ == '__main__':
    print('executing tests \n\n')
    suite = gen_suite()
    unittest.TextTestRunner(verbosity=3).run(suite)
    

    
    
    
    
    
    
    
    
    
    
    
    