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
    

#from .dcoms import Dcoms
from .dPlot import DPlotr
from hlpr.basic import ComWrkr, view
    
#from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class Dvuln(DPlotr):
    """ not using config files for now.. just pass all parameteres explicity"""

    def __init__(self,
                 
                  *args,  **kwargs):
        
        super().__init__(*args,**kwargs)

        self.dfuncs_d = dict() #container for damage functions
        
        self.logger.debug('Dvuln.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
    def _setup(self,
               dexpo_fp = '',
               dcurves_fp = '',
               ): #loader function sequence
        
        self.load_expo(dexpo_fp)
        self.load_fragFuncs(dcurves_fp)

   
    def load_fragFuncs(self, #load the fragility curves
                     fp):
        """ similar to Dmg2.setup_dfuncs"""
        log =self.logger.getChild('load_fragFuncs')
        
        #load data
        
        df_d = pd.read_excel(fp, sheet_name=None, header=None, index_col=None)
        
        log.info('loaded %i fcurves from \n     %s'%(len(df_d), fp))
        
        #=======================================================================
        # #loop through each frame and build the func
        #=======================================================================
        maxFB_d, minFB_d = dict(), dict()
        for tabn, df in df_d.items():
            if tabn.startswith('_'):
                log.warning('skipping dummy tab \'%s\''%tabn)
                continue
            
            tabn = tabn.strip() #remove whitespace
            
            if not tabn in self.dtag_l:
                log.debug('skipping \'%s\''%tabn)
                continue
            
            #build it
            dfunc = FragFunc(tabn).build(df, log)
            
            #check
            assert dfunc.tag == tabn
            assert not tabn in self.dfuncs_d
            
            #store it
            self.dfuncs_d[dfunc.tag] = dfunc
            
            #get extremes
            """for fragility curves... negative = HIGHER exposure"""
            maxFB_d[tabn], minFB_d[tabn] = dfunc.max_dep, dfunc.min_dep
 
        #=======================================================================
        # wrap
        #=======================================================================
        assert len(self.dfuncs_d)==len(self.dtag_l)
        
        self.maxFB_d, self.minFB_d = maxFB_d, minFB_d
        
        log.info('finished building %i fragility curves \n    %s'%(
            len(self.dfuncs_d), list(self.dfuncs_d.keys())))
        
        return 
        

    
    
    def get_failP(self, #get the failure probabilyt of each segment
                  dfuncs_d = None,
                  expo_df = None,
                  ): 
        """
        unlike the damage model... our 'inventory' and exposure data is on the same frame
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('get_failP')
        if dfuncs_d is None: dfuncs_d = self.dfuncs_d #i guess were not using weak refs
        if expo_df is None: expo_df = self.expo_df.copy()
        
        log.info('on expo %s w/ %i dfuncs'%(str(expo_df.shape), len(dfuncs_d)))
        
        #=======================================================================
        # precheck
        #=======================================================================
        tagCols = [c for c in expo_df.columns if c.endswith('_dtag')] #id tag columns
        
        assert len(tagCols) == 1, 'only 1 tag column is supported now'
        """ TODO: expand to handle multiple functins per curve
        (where we calc union or mutEx probability for the combination)"""
        
        tag_ser = expo_df[tagCols[0]]
        #=======================================================================
        # get valid exposure entries
        #=======================================================================
        edf = expo_df.loc[:, self.etag_l]
        """
        view(expo_df)
        
        TODO: consider filling in with boundary falues first
        """
        
        vbooldf = pd.DataFrame(np.logical_and(
            edf >= min(self.minFB_d.values()),
            edf <= max(self.maxFB_d.values()),
            ))
        

        
        #=======================================================================
        # calc loop
        #=======================================================================
        rdf = None
        for indxr, (dtag, Dfunc) in enumerate(dfuncs_d.items()):
            log.debug('on %s'%dtag)
            
            #===================================================================
            # get calc data for this set
            #===================================================================
            #identify these entries
            booldf1 = pd.DataFrame(np.tile(tag_ser==dtag, (len(vbooldf.columns),1)).T,
                                   index=vbooldf.index, columns=vbooldf.columns)
            
            booldf = np.logical_and(
                booldf1, #matching this tag
                vbooldf) #valid exposures
 
            if not booldf.any().any():
                log.warning('%s got no valid calcs.. skipping'%dtag)
                continue
            
            log.info('(%i/%i) calculating \'%s\' w/ %i assets (of %i)'%(
                indxr+1, len(dfuncs_d), dtag, booldf.any(axis=1).sum(), len(booldf)))
            
            #===================================================================
            # get exposure data
            #===================================================================
            
            
            #get just the unique depths that need calculating
            """rounding done during loading"""
            deps_ar = pd.Series(np.unique(np.ravel(edf[booldf].dropna(how='all')))
                                ).dropna().values
                                
            #===================================================================
            # execute curves
            #===================================================================
            #loop each depth through the damage function to get the result                
            res_d = {dep:Dfunc.get_dmg(dep) for dep in deps_ar}
            #==================================================================
            # link these damages back to the results
            #==================================================================
            
            ri_df = edf[booldf].replace(res_d)
            
            log.debug('%s got %i vals'%(dtag, ri_df.notna().sum().sum()))
            #===================================================================
            # update master
            #===================================================================
            if rdf is None:
                rdf = ri_df
            else:
                rdf.update(ri_df, overwrite=False, errors='raise')

            #===================================================================
            # post checks
            #===================================================================
            assert rdf.max().max()<=1
            assert rdf.min().min()>=0
            
        #=======================================================================
        # fill boundary values-----
        #=======================================================================
        """
        view(rdf)
        """
        log.info('filling %i (of %i) blanks'%(rdf.isna().sum().sum(), rdf.size))
        
        
        assert np.array_equal(rdf.notna(), vbooldf), 'failed to fill all valid entries'
        
        #=======================================================================
        # #minimumes
        #=======================================================================
        """
        water is WELL above the crest (negative freeboard)
        """
        min_booldf = edf < min(self.minFB_d.values())
        if min_booldf.any().any():
            log.info('filling %i MIN vals (%.2f) w/ pFail=1.0'%(
                min_booldf.sum().sum(),min(self.minFB_d.values()) ))
            
            rdf = rdf.where(~min_booldf, other=1.0)
        
        #=======================================================================
        # maximums
        #=======================================================================
        max_booldf =   edf > max(self.maxFB_d.values())
        if max_booldf.any().any():
            log.info('filling %i MAX vals (%.2f) w/ pFail=0.0'%(
                max_booldf.sum().sum(),max(self.maxFB_d.values())) )
            
            rdf = rdf.where(~max_booldf, other=0.0)

            
            

    
from model.dmg2 import DFunc

class FragFunc(DFunc): #simple wrapper around DFunc
    def __init__(self, 
                 *args, **kwargs):
        
        super().__init__(*args,monotonic=False, **kwargs) #initilzie Model
        
        
#===============================================================================
# class FragFunc(ComWrkr, 
#             ): #damage function
#     
#     #==========================================================================
#     # program pars
#     #==========================================================================
#     dd_df = pd.DataFrame() #depth-pFail data
#     
#      
#     #==========================================================================
#     # user pars
#     #==========================================================================
#     tag = 'dfunc'
#     min_dep = 0
# 
#     pars_d = {}
#     
#     def __init__(self,
#                  tabn='FragFunc', #optional tab name for logging
#                  
#                  **kwargs):
#         
#         self.tabn= tabn
#         """
#         todo: reconcile tabn vs tag
#         """
#         
#         #init the baseclass
#         super().__init__(**kwargs) #initilzie Model
#         
#     
#     def build(self,
#               df_raw, #raw parameters to build the DFunc w/ 
#               logger):
#         
#         
#         
#         log = logger.getChild('%s'%self.tabn)
#         #======================================================================
#         # identify depth-damage data
#         #======================================================================
#         #slice and clean
#         df = df_raw.iloc[:, 0:2].dropna(axis=0, how='all')
#         
#         #validate the curve
#         self.check_curve(df.set_index(df.columns[0]).iloc[:,0].to_dict(),
#                          logger=log)
#         
#         #locate depth-damage data
#         boolidx = df.iloc[:,0]=='exposure' #locate
#         
#         assert boolidx.sum()==1, \
#             'got unepxected number of \'exposure\' values on %s'%(self.tabn)
#             
#         depth_loc = df.index[boolidx].tolist()[0]
#         
#         boolidx = df.index.isin(df.iloc[depth_loc:len(df), :].index)
#         
#         
#         #======================================================================
#         # attach other pars
#         #======================================================================
#         #get remainder of data
#         mser = df.loc[~boolidx, :].set_index(df.columns[0], drop=True ).iloc[:,0]
#         mser.index =  mser.index.str.strip() #strip the whitespace
#         pars_d = mser.to_dict()
#         
#         #check it
#         assert 'tag' in pars_d, '%s missing tag'%self.tabn
#         
#         assert pars_d['tag']==self.tabn, 'tag/tab mismatch (\'%s\', \'%s\')'%(
#             pars_d['tag'], self.tabn)
#         
#         for varnm, val in pars_d.items():
#             setattr(self, varnm, val)
#             
#         log.debug('attached %i parameters to Dfunc: \n    %s'%(len(pars_d), pars_d))
#         self.pars_d = pars_d.copy()
#         
#         #======================================================================
#         # extract depth-dmaage data
#         #======================================================================
#         #extract depth-damage data
#         dd_df = df.loc[boolidx, :].reset_index(drop=True)
#         dd_df.columns = dd_df.iloc[0,:].to_list()
#         dd_df = dd_df.drop(dd_df.index[0], axis=0).reset_index(drop=True) #drop the depth-damage row
#         
#         #typeset it
#         dd_df.iloc[:,0:2] = dd_df.iloc[:,0:2].astype(float)
#         
#        
#         ar = np.sort(np.array([dd_df.iloc[:,0].tolist(), dd_df.iloc[:,1].tolist()]), axis=1)
#         self.dd_ar = ar
#         
#         #=======================================================================
#         # get stats
#         #=======================================================================
#         self.min_dep = min(ar[0])
#         
#         #=======================================================================
#         # wrap
#         #=======================================================================
#         log.debug('\'%s\' built w/ dep min/max %.2f/%.2f and dmg min/max %.2f/%.2f'%(
#             self.tag, min(ar[0]), max(ar[0]), min(ar[1]), max(ar[1])
#             ))
#         
#         return self
#         
#         
#     def get_dmg(self, #get damage from depth using depth damage curve
#                 depth):
#         
#         ar = self.dd_ar
#         
#         dmg = np.interp(depth, #depth find damage on
#                         ar[0], #depths 
#                         ar[1], #damages
#                         left=0, #depth below range
#                         right=max(ar[1]), #depth above range
#                         )
# #==============================================================================
# #         #check for depth outside bounds
# #         if depth < min(ar[0]):
# #             dmg = 0 #below curve
# # 
# #             
# #         elif depth > max(ar[0]):
# #             dmg = max(ar[1]) #above curve
# # 
# #         else:
# #             dmg = np.interp(depth, ar[0], ar[1])
# #==============================================================================
#             
#         return dmg
#     
#     
#     def get_stats(self): #get basic stats from the dfunc
#         deps = self.dd_ar[0]
#         dmgs = self.dd_ar[1]
#         return {**{'min_dep':min(deps), 'max_dep':max(deps), 
#                 'min_dmg':min(dmgs), 'max_dmg':max(dmgs), 'dcnt':len(deps)},
#                 **self.pars_d}
# 
#             
#===============================================================================
        