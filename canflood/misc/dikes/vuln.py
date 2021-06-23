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
    
    #===========================================================================
    # program containers
    #===========================================================================
    pfL_df = None
    pf_df = None
    pfmax = 0.999 #maximum failure probability to apply

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
            
            #check probability logic
            assert dfunc.dd_ar[1].max() <=1.0
            assert dfunc.dd_ar[1].max() >=0.0
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
                  expo_df = None, #freeboard data (without crest buffer)
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
        # add crest buffers----------
        #=======================================================================

        edf_raw = expo_df.loc[:, self.etag_l]
        
        cb_ser = expo_df[self.cbfn] #pull out buffer data
        assert cb_ser.notna().all(), 'got nulls on %s data'%self.cbfn
        if cb_ser.min()<0:
            log.warning('%s got some negative values!!!'%self.cbfn)
        
        edf = edf_raw.add(cb_ser, axis=0)
        
        log.info('added %s values \n    %s'%(self.cbfn, cb_ser.to_dict()))
        
        #=======================================================================
        # get valid exposure entries
        #=======================================================================
        """

        TODO: consider filling in with boundary falues first
        """
        #flag exposures outside boundary as False (also flags Nulls as false)
        vbooldf = pd.DataFrame(np.logical_and(
            edf >= min(self.minFB_d.values()),
            edf <= max(self.maxFB_d.values()),
            ))
        """
        view(edf)
        """
        assert vbooldf.any().any(), 'all exposures outside bounds'

        
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

        assert isinstance(rdf, pd.DataFrame), 'failed to get any valid calcs'
        #=======================================================================
        # fill boundary values-----
        #=======================================================================
        """
        view(rdf)
        """
        log.info('filling %i (of %i) blanks'%(rdf.isna().sum().sum(), rdf.size))
        
        
        assert np.array_equal(rdf.notna(), vbooldf), 'failed to fill all valid entries'
        
        #=======================================================================
        # nulls
        #=======================================================================
        if edf.isna().any().any():
            log.info('filling %i NULL vals w/ pFail = 0.0'%edf.isna().sum().sum())
            rdf = rdf.where(~edf.isna(), other=0.0)
        
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
            
            rdf = rdf.where(~min_booldf, other=self.pfmax)
        
        #=======================================================================
        # maximums
        #=======================================================================
        max_booldf =   edf > max(self.maxFB_d.values())
        if max_booldf.any().any():
            log.info('filling %i MAX vals (%.2f) w/ pFail=0.0'%(
                max_booldf.sum().sum(),max(self.maxFB_d.values())) )
            
            rdf = rdf.where(~max_booldf, other=0.0)
            
        #=======================================================================
        # checks
        #=======================================================================
        assert rdf.notna().all().all()
        assert rdf.max().max()<=1
        assert rdf.min().min()>=0
        
        #=======================================================================
        # wrap
        #=======================================================================
        smry_df = rdf.mean().to_frame().rename(columns={0:'mean'}).join(
            rdf.max().to_frame().rename(columns={0:'max'})).join(
                rdf.min().to_frame().rename(columns={0:'min'}))
        
        
        log.info('finished calculating pfail %s  w/ \n%s'%(str(rdf.shape), smry_df))
        
        #=======================================================================
        # join back in metadat
        #=======================================================================
        l = set(expo_df.columns).difference(rdf.columns) #columns to add back
        rdf = rdf.join(expo_df.loc[:, l])
        
        #add dummy length effect values
        """lets the user feed either set into results modules while keeping headers the same"""
        rdf[self.lfxn] = 1.0 
        
        self.pf_df = rdf
        
        return self.pf_df
    
    def set_lenfx(self, #apply length effects to raw pfail data
                  pfail_df=None, 

                  method = 'URS2007', #method for applying the length effect
                  ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('set_lenfx')
        if pfail_df is None: pfail_df = self.pf_df.copy().drop(self.lfxn, axis=1, errors='ignore')


        #=======================================================================
        # pull out data
        #=======================================================================
        
        len_ser = pfail_df[self.segln]
        
        pf_df = pfail_df.loc[:, self.etag_l] #just the results from get_faipP
        #=======================================================================
        # get scale factors
        #=======================================================================
        if method == 'URS2007':
            
            sf_ser = 1+(len_ser-max(len_ser))/max(len_ser)
            
            
        else:
            raise Error('unrecognized method: \'%s\''%method)
        
        log.info('got %i lfx_SF from \'%s\'. min=%.4f, mean=%.4f, max=%.4f'%(
            len(sf_ser), method, sf_ser.min(), sf_ser.mean(), sf_ser.max()))
        #=======================================================================
        # apply scale factors
        #=======================================================================
        sf_ser.name = self.lfxn
        
        rdf = pf_df.multiply(sf_ser, axis=0).round(self.prec)
        
        #summary data
        smry_df = rdf.mean().to_frame().rename(columns={0:'mean'}).join(
            rdf.max().to_frame().rename(columns={0:'max'})).join(
                rdf.min().to_frame().rename(columns={0:'min'}))
        
        #=======================================================================
        # join back in metadat
        #=======================================================================
        df = rdf.join(sf_ser)
        
        l = set(pfail_df.columns).difference(df.columns) #columns to add back
        df = df.join(pfail_df.loc[:, l])
        
        log.info('finished applying lfx_sf on %i segments w/ \n%s'%(
            len(df), smry_df))
            
        self.pfL_df = df
            
        return self.pfL_df
    
    def output_vdfs(self, #output the dike data (for the vuln calc
                  df = None, df_lfx = None,

                     logger=None,
                     overwrite=None,

                     ): 
        #=======================================================================
        # defaults
        #=======================================================================
        if overwrite is None: overwrite=self.overwrite
        if logger is None: logger=self.logger
        log=logger.getChild('output_vuln_dfs')
        
        if df is None: df = self.pf_df
        if df_lfx is None: df_lfx = self.pfL_df

        
        #=======================================================================
        # raw tabular
        #=======================================================================
        ecnt = len(df.columns)
        ofp = os.path.join(self.out_dir, '%s_pfail_%i_%i.csv'%(
            self.tag, ecnt,len(df) ))
        
        if os.path.exists(ofp):assert self.overwrite
            
        df.to_csv(ofp, index=True)
        
        log.info('wrote %s to file \n    %s'%(str(df.shape), ofp))
        
        #=======================================================================
        # length fx tabular
        #=======================================================================
        if not df_lfx is None:
            df = df_lfx
            ofp1 = os.path.join(self.out_dir, '%s_pfail_lfx_%i_%i.csv'%(
                self.tag, ecnt,len(df)))
        
            if os.path.exists(ofp1):assert self.overwrite
                
            df.to_csv(ofp1, index=True)
            
            log.info('wrote %s to file \n    %s'%(str(df.shape), ofp1))
            
        return ofp
            
            

    
from model.dmg2 import DFunc

class FragFunc(DFunc): #simple wrapper around DFunc
    def __init__(self, 
                 *args, **kwargs):
        
        super().__init__(*args,monot=False, **kwargs) #initilzie Model
        
      