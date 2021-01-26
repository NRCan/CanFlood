'''
Created on Jan. 23, 2021

@author: cefect



'''


import unittest, tempfile, inspect, logging, os, fnmatch

import pandas as pd
import matplotlib.pyplot as plt

#import models
from results.attribution import Attr


"""just using the default console logger"""


from tScripts import tWorker


        

class tAtw(tWorker): #worker for testing the damage model
    """not testing any data... just making sure we get a figure"""
    
    
    
    def __init__(self, *args, **kwargs):
        """called for each test METHOD"""
        super().__init__(*args, **kwargs) #init baseclass
    
    def test_noFail(self, #testing the main output

                  ): 
        print('test_main on \'%s\''%self.name)
        

        #=======================================================================
        # #run the model
        #=======================================================================
        si_ttl = self.Model.get_slice_noFail()
        """TODO: add data check?"""
        
        #=======================================================================
        # plot
        #=======================================================================
        for y1lab in ['AEP', 'impacts']:
            fig = self.Model.plot_slice(si_ttl, y1lab=y1lab)
            self.assertIsInstance(fig, plt.Figure)
        

        
        

        
        

def gen_suite(

    runpars_d={
        'tut2_01.b01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\CanFlood_tut2b_20210123.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\b01\dmg2',
             }, 
        'tut2_01.a01':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\CanFlood_tut2a_20210123.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\a01\dmg2',
             }, 
        'tut2_01.c01.mutEx':{
             'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\CanFlood_tut2c_20210123_mutEx.txt',
             'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\dmg2',
             },
        #=======================================================================
        # 'tut2_01.c01.max':{ #same as mutEx
        #      'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\CanFlood_tut2c_20210123_max.txt',
        #      'res_dir':r'CC:\LS\03_TOOLS\CanFlood\_git\tests\_data\tut2_01\c01\dmg2',
        #      },
        #=======================================================================
        'LM_bs.b01':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b01\CanFlood_Lbs6.ind.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b01\dmg'
            },
        'LM_bs.b02':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b02\CanFlood_LML.bs7_b02_20210123.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b02\dmg'
            },
        'LM_bs.b03_max':{
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\CanFlood_LML.bs7.b03_max_20210123.txt',
            'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\dmg'
            },
        #=======================================================================
        # 'LM_bs.b02_mutEx':{ #same
        #     'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\CanFlood_LML.bs7.b03_mutEx_20210123.txt',
        #     'res_dir':r'C:\LS\03_TOOLS\CanFlood\_git\tests\_data\LM_bs\b03\dmg'
        #     },
        #=======================================================================
        }
    ):
    
    return get_suite(runpars_d,
                      Dmg2,tDmg,
                      dataLoad_pars = {'attr02*':{'header':[0,1], 'index_col':0}, 
                                    'dmgs*':{'index_col':0}},
                      )
    
if __name__ == '__main__':
    print('executing tests \n\n')
    suite = gen_suite()
    unittest.TextTestRunner(verbosity=3).run(suite)
    

    
    
    
    
    
    
    
    
    
    
    
    