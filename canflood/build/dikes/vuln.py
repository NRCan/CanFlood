'''
Created on Feb. 9, 2020

@author: cefect

simple build routines
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, shutil



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd
from pandas import IndexSlice as idx

#Qgis imports

import processing
#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    

from build.dikes.dcoms import Dcoms
from hlpr.basic import ComWrkr, view
    
#from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class Dvuln(Dcoms):
    """ not using config files for now.. just pass all parameteres explicity"""

    def __init__(self,
                 
                  *args,  **kwargs):
        
        super().__init__(*args,**kwargs)

        self.dfuncs_d = dict() #container for damage functions
        
        self.logger.debug('Dvuln.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
   
    def load_fragFuncs(self, #load the fragility curves
                     fp):
        log =self.logger.getChild('load_fragFuncs')
        
        #load data
        
        df_d = pd.read_excel(fp, sheet_name=None, header=None, index_col=None)
        
        log.info('loaded %i fcurves from \n     %s'%(len(df_d), fp))
        
        #=======================================================================
        # #loop through each frame and build the func
        #=======================================================================
        for tabn, df in df_d.items():
            if tabn.startswith('_'):
                log.warning('skipping dummy tab \'%s\''%tabn)
                continue
            
            tabn = tabn.strip() #remove whitespace
            
            
            #build it
            dfunc = FragFunc(tabn).build(df, log)
            
            #store it
            self.dfuncs_d[dfunc.tag] = dfunc
            

    
    def load_expo(self, #load the exposure data
                  fp):
        
        pass
    
    
    def get_failP(self): #get the failure probabilyt of each segment
        pass

    

class FragFunc(ComWrkr, 
            ): #damage function
    
    #==========================================================================
    # program pars
    #==========================================================================
    dd_df = pd.DataFrame() #depth-pFail data
    
     
    #==========================================================================
    # user pars
    #==========================================================================
    tag = 'dfunc'

    pars_d = {}
    
    def __init__(self,
                 tabn='FragFunc', #optional tab name for logging
                 
                 **kwargs):
        
        self.tabn= tabn
        """
        todo: reconcile tabn vs tag
        """
        
        #init the baseclass
        super().__init__(**kwargs) #initilzie Model
        
    
    def build(self,
              df_raw, #raw parameters to build the DFunc w/ 
              logger):
        
        
        
        log = logger.getChild('%s'%self.tabn)
        #======================================================================
        # identify depth-damage data
        #======================================================================
        #slice and clean
        df = df_raw.iloc[:, 0:2].dropna(axis=0, how='all')
        
        #validate the curve
        self.check_curve(df.set_index(df.columns[0]).iloc[:,0].to_dict(),
                         logger=log)
        
        #locate depth-damage data
        boolidx = df.iloc[:,0]=='exposure' #locate
        
        assert boolidx.sum()==1, \
            'got unepxected number of \'exposure\' values on %s'%(self.tabn)
            
        depth_loc = df.index[boolidx].tolist()[0]
        
        boolidx = df.index.isin(df.iloc[depth_loc:len(df), :].index)
        
        
        #======================================================================
        # attach other pars
        #======================================================================
        #get remainder of data
        mser = df.loc[~boolidx, :].set_index(df.columns[0], drop=True ).iloc[:,0]
        mser.index =  mser.index.str.strip() #strip the whitespace
        pars_d = mser.to_dict()
        
        #check it
        assert 'tag' in pars_d, '%s missing tag'%self.tabn
        
        assert pars_d['tag']==self.tabn, 'tag/tab mismatch (\'%s\', \'%s\')'%(
            pars_d['tag'], self.tabn)
        
        for varnm, val in pars_d.items():
            setattr(self, varnm, val)
            
        log.debug('attached %i parameters to Dfunc: \n    %s'%(len(pars_d), pars_d))
        self.pars_d = pars_d.copy()
        
        #======================================================================
        # extract depth-dmaage data
        #======================================================================
        #extract depth-damage data
        dd_df = df.loc[boolidx, :].reset_index(drop=True)
        dd_df.columns = dd_df.iloc[0,:].to_list()
        dd_df = dd_df.drop(dd_df.index[0], axis=0).reset_index(drop=True) #drop the depth-damage row
        
        #typeset it
        dd_df.iloc[:,0:2] = dd_df.iloc[:,0:2].astype(float)
        
       
        ar = np.sort(np.array([dd_df.iloc[:,0].tolist(), dd_df.iloc[:,1].tolist()]), axis=1)
        self.dd_ar = ar
        
        #=======================================================================
        # get stats
        #=======================================================================
        self.min_dep = min(ar[0])
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('\'%s\' built w/ dep min/max %.2f/%.2f and dmg min/max %.2f/%.2f'%(
            self.tag, min(ar[0]), max(ar[0]), min(ar[1]), max(ar[1])
            ))
        
        return self
        
        
    def get_dmg(self, #get damage from depth using depth damage curve
                depth):
        
        ar = self.dd_ar
        
        dmg = np.interp(depth, #depth find damage on
                        ar[0], #depths 
                        ar[1], #damages
                        left=0, #depth below range
                        right=max(ar[1]), #depth above range
                        )
#==============================================================================
#         #check for depth outside bounds
#         if depth < min(ar[0]):
#             dmg = 0 #below curve
# 
#             
#         elif depth > max(ar[0]):
#             dmg = max(ar[1]) #above curve
# 
#         else:
#             dmg = np.interp(depth, ar[0], ar[1])
#==============================================================================
            
        return dmg
    
    
    def get_stats(self): #get basic stats from the dfunc
        deps = self.dd_ar[0]
        dmgs = self.dd_ar[1]
        return {**{'min_dep':min(deps), 'max_dep':max(deps), 
                'min_dmg':min(dmgs), 'max_dmg':max(dmgs), 'dcnt':len(deps)},
                **self.pars_d}

            
        