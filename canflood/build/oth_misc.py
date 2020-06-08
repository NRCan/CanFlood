'''
Created on Mar. 5, 2020

@author: cefect

converting from rfda formats
'''


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging, datetime

import pandas as pd
import numpy as np

start, ymd = datetime.datetime.now(), datetime.datetime.now().strftime('%Y%m%d')

#==============================================================================
# pars---
#==============================================================================
l1 = ['False', 'FALSE', 'false', 'NO', 'No', 'no', 'N', 'n']
l2 = ['True','TRUE','true', 'yes','YES','Yes', 'Y', 'y']
truefalse_d = {
    **dict(zip(l1, np.full(len(l1), False))),
    **dict(zip(l2, np.full(len(l2), True)))
    }


#==============================================================================
# custom imports------
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
    
#plugin runs
else:
    mod_logger = logging.getLogger('rfda') #get the root logger

    from hlpr.exceptions import QError as Error

import hlpr.Q as hQ
from hlpr.basic import view
from model.dmg2 import DFunc


mod_name = 'misc'

class Misc(hQ.Qcoms):
    
    # legacy index numbers
    legacy_ind_d = {0:'id1',1:'address',2:'id2',10:'class', 11:'struct_type', 13:'area', 
                    18:'bsmt_f', 19:'ff_height', 20:'lon',21:'lat', 25:'gel'}
    
    ctag_cLibN_d = None #curve tag location
    

    def __init__(self, 

                  **kwargs):
        

        
        mod_logger.info('%s.__init__ start'%mod_name)
        super().__init__(**kwargs) #initilzie teh baseclass
        
    def crv_lib_smry(self,
                     crv_d, #dictionary of curves
                     logger=None,
                     ):
        if logger is None: logger=self.logger
        log = logger.getChild('crv_lib_smry')
        
        raise Error('gave up')
    
    def crv_consol(self, #scan a set of curve librarires and consolidate necessary curves
                   fdf, #inventory data 
                   cLib_all_d, #a set of curve librarires {libName:{ctag:curve_df}}
                   logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('crvCons')
        mdf = pd.DataFrame()
        #=======================================================================
        # collect tags from inventory
        #=======================================================================
        boolcol = np.logical_and(
            fdf.columns.str.contains('_tag'),
            fdf.columns.str.startswith('f'))
            
        assert boolcol.any(), 'failed to find any tag fields'
        log.info('collecting tags from %i tagcolumns \n    %s'%(
            boolcol.sum(),  fdf.columns[boolcol].tolist()))
        
        #loop these columns and collect tags
        ftags_d = dict()
        for coln, cser in fdf.loc[:, boolcol].items():
            ftags_d[coln] = cser.dropna().unique().tolist()
            
            #collect tag count meta
            mdf = mdf.join(cser.value_counts(dropna=False), how='outer')
            
        mdf['total'] = mdf.sum(axis=1, skipna=True).astype(np.int)
        log.info('collected %i tags in inventory across all nests \n    %s'%(
                 len(mdf), mdf['total']))
        
        #=======================================================================
        # build index of curve locations
        #=======================================================================
        if self.ctag_cLibN_d is None:
            d = dict()
            for cLname, cLib_d in cLib_all_d.items():
                for ctag, cdf in cLib_d.items():
                    if ctag.startswith('_'):continue #skip these
                    if not ctag in d:
                        d[ctag] = [cLname]
                    else:
                        d[ctag].append(cLname)
            
            log.info('built index of %i curves from %i librarires'%(len(d), len(cLib_d)))
            self.ctag_cLibN_d = d
            """
            view(pd.Series(d))
            """
        
        ctagL_d = self.ctag_cLibN_d

        #=======================================================================
        # collect tags from curve library
        #=======================================================================
        ctags = set(mdf.index.dropna().tolist())
        log.info('collecting %i ctags from %i loaded'%(len(ctags), len(ctagL_d)))
        
        #check coverage
        s = ctags.difference(ctagL_d.keys())
        if len(s)>0:
            log.warning('%i finv tags not found in passed librarries \n    %s'%(len(s), s))
            raise Error('dome')
        
        
        res_lib = dict() #results container for curves
               
        #loop through each request and collect thre data
        mcdf = pd.DataFrame()
        for ctag in ctags:
            
            #===================================================================
            # get the lib names
            #===================================================================
            libNames = ctagL_d[ctag]
            if len(libNames)>1:
                log.warning('%s found in %i librarires... taking first\n    %s'%(
                    ctag, len(libNames), libNames))
                libName = libNames[0]
            elif len(libNames)==1:
                libName = libNames[0]
            else:
                raise Error('bad length')
                
            #===================================================================
            # get the curve data
            #===================================================================
            cdf = cLib_all_d[libName][ctag]
            
            assert isinstance(cdf,  pd.DataFrame)
            assert len(cdf.columns)==2
            
            Dfo = DFunc().build(cdf, log)
            
            res_lib[ctag] = cdf
            
            #===================================================================
            # meta
            #===================================================================
            md = Dfo.get_stats()
            md['cLibName'] = libName
            
            mcdf = mcdf.append(pd.Series(md, name=ctag), verify_integrity=True)
            
        log.info('collected %i curves'%len(res_lib))
        
        s = ctags.symmetric_difference(res_lib.keys())
        assert len(s)==0
        
        return res_lib, mcdf
        
        
        
        
        



     
    
if __name__ =="__main__": 
    print('start')

    print('finished')