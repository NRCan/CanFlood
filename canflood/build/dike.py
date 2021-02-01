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


#Qgis imports
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsMapLayerStore
import processing
#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, view
from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class Diker(Qcoms):
    """

    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """

    def __init__(self,

                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.logger.debug('Diker.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def load_rlays(self,
                   layfp_d,
                   logger=None,
                   **kwargs):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('load_rlays')
        
        log.info('on %i layers'%len(layfp_d))
        
        #=======================================================================
        # load it
        #=======================================================================
        d = dict()
        
        for layTag, fp in layfp_d.items():
            d[layTag] = self.load_rlay(fp, logger=log, **kwargs)
            
        log.info('loaded %i layers'%len(d))
        
        return d
    
    def load_dike(self, fp,
                  dikeID = 'dikeID', #dike identifier field
                  segID = 'segID', #segment identifier field
                   logger=None, **kwargs):
        
        if logger is None: logger=self.logger
        log = logger.getChild('load_dikes')
        
        vlay = self.load_vlay(fp, **kwargs)
        

        df = vlay_get_fdf(vlay, logger=log)

        #=======================================================================
        # checks
        #=======================================================================
        miss_l = set([dikeID, segID]).difference(df.columns)
        assert len(miss_l)==0, 'missing expected columns on dike layer: %s'%miss_l
        
        """try forcing
        assert 'int' in df[segID].dtype.name, 'bad dtype on dike layer %s'%segID
        assert 'int' in df[dikeID].dtype.name, 'bad dtype on dike layer %s'%dikeID"""
        
        #geometry
        assert 'Line' in QgsWkbTypes().displayString(vlay.wkbType()), 'bad vector type on dike'
        
        dp = vlay.dataProvider()
        
        #=======================================================================
        # build global segment ids
        #=======================================================================
        #type forcing
        for coln in [dikeID, segID]:
            try:
                df[coln] = df[coln].astype(int)
            except Exception as e:
                raise Error('failed to type set dike column \'%s\' w/ \n%s'%(coln, e))
        
        
        s1 = df[dikeID].astype(str).str.pad(width=3, side='left', fillchar='0')
        s2 = df[segID].astype(str).str.pad(width=2, side='left', fillchar='0')
        
        df['sid'] = s1.str.cat(others=s2).astype(int)
        
        assert df['sid'].is_unique, 'failed to get unique global segment ids... check your dikeID and segID'
        # bundle back into vectorlayer
        geo_d = vlay_get_fdata(vlay, geo_obj=True, logger=log)
        res_vlay = self.vlay_new_df2(df, geo_d=geo_d, logger=log,
                               layname=vlay.name())
        
        
        #=======================================================================
        # wrap
        #=======================================================================

        log.info('loaded dike layer \'%s\'  w/ %i segments'%(vlay.name(), dp.featureCount()))

        self.dike_vlay = res_vlay
        
        """
        view(res_vlay)
        
        """
        
        return self.dike_vlay
    
    def load_fcurves(self):
        pass
    
    def get_dike_expo(self, #get exposure set for dikes
                    noFailr_d,
                    dike_vlay = None,
                    dtm_rlay = None,
                    
                    #dike layer parameters
                    sid = 'sid', #global segment identifier
                    
                    #cross profile parameters
                    dist_line = 40, #distance along dike to draw perpindicular profiles
                    dist_profile = 100, #half length of profile from dike CL
                    dens_int = None,
                    nullSamp = -999, #value for bad samples
                    
                    
                    logger=None,
                    ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('get_dike_expo')
        if dike_vlay is None: dike_vlay = self.dike_vlay
        if dtm_rlay is None: dtm_rlay = self.dtm_rlay
        
        mstore = QgsMapLayerStore() #build a new map store
        #=======================================================================
        # prechecks
        #=======================================================================
        assert sid in [f.name() for f in dike_vlay.fields()], 'failed to get sid on dikes'
        
        #=======================================================================
        # crossProfiles---
        #=======================================================================
        #=======================================================================
        # get the raw
        #=======================================================================
        algo_nm='saga:crossprofiles'
        d = {'DEM' : dtm_rlay, 
             'DIST_LINE' : dist_line, 
             'DIST_PROFILE' : dist_profile, 
             'LINES' : dike_vlay, 
             'NUM_PROFILE' : 3, #number of samples (we are not using the sample values.. just the geo
             'PROFILES' : 'TEMPORARY_OUTPUT' }
        
        res_d = processing.runAndLoadResults(algo_nm, d, feedback=self.feedback)
        
        #checks
        assert os.path.exists(res_d['PROFILES']), '%s failed to generate a result'%algo_nm
        
        cp_vlay_raw = QgsVectorLayer(res_d['PROFILES'])
        assert isinstance(cp_vlay_raw, QgsVectorLayer), '%s failed to get a vectorlayer'%algo_nm
        
        
        self.createspatialindex(cp_vlay_raw)
        
        """
        view(cp_vlay)
        """
        #drop some fields
        
        #=======================================================================
        # #retrieve the sid
        #=======================================================================
        cp_vlay, new_fn_l, join_cnt = self.joinattributesbylocation(cp_vlay_raw, dike_vlay,
                                                [sid], method=1, expect_all_hits=True, 
                                                logger=log)
        
        #=======================================================================
        # densify
        #=======================================================================
        #add additional veritifies to improve the resolution of the wsl sample
        if dens_int is None: desn_int = min(dist_line, dist_profile/2)
        d = { 'INPUT' : cp_vlay,'INTERVAL' : desn_int, 'OUTPUT' : 'TEMPORARY_OUTPUT' }
        
        algo_nm='native:densifygeometriesgivenaninterval'
        
        cp_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']

        cp_vlay = self.fixgeometries(cp_vlay, logger=log)
        
        #=======================================================================
        # #clean it up
        #=======================================================================
        cp_vlay.setName('%s_cp'%dike_vlay.name())
        
        #remove unwanted fields
        dp = cp_vlay.dataProvider()
        drop_l = set([f.name() for f in cp_vlay.fields()]).difference([sid, 'ID'])
        fdrop_l = [dp.fieldNameIndex(f) for f in drop_l] #get indexes
        dp.deleteAttributes(fdrop_l)
        cp_vlay.updateFields()
         
        #=======================================================================
        # get wsls----
        #=======================================================================
        res_d = dict()
        dxcol = None

        log.info('building %i cross profile sets'%len(noFailr_d))
        for eTag, wsl_rlay in noFailr_d.items():
        
            #===================================================================
            # drape---
            #===================================================================
            d = { 'BAND' : 1, 'INPUT' : cp_vlay, 'NODATA' : nullSamp, 
                 'OUTPUT' : 'TEMPORARY_OUTPUT', 'RASTER' : wsl_rlay,
                  'SCALE' : 1,
                   }
            algo_nm = 'native:setzfromraster'
            cpi_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            mstore.addMapLayer(cpi_vlay)
            #===================================================================
            # extract z
            #===================================================================
            d = { 'COLUMN_PREFIX' : 'z_', 'INPUT' : cpi_vlay,
                  'OUTPUT' : 'TEMPORARY_OUTPUT', 'SUMMARIES' : [8], #max
                   }
            algo_nm = 'native:extractzvalues'
            cpi_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            mstore.addMapLayer(cpi_vlay)
            
            #===================================================================
            # centroids---
            #===================================================================
            d = { 'ALL_PARTS' : False, 'INPUT' :cpi_vlay, 'OUTPUT' : 'TEMPORARY_OUTPUT' }
            algo_nm = 'native:centroids'
            cPts_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            mstore.addMapLayer(cPts_vlay)
            #===================================================================
            # centroids - sample
            #===================================================================
            d = { 'COLUMN_PREFIX' : 'dtm', 'INPUT' : cPts_vlay, 'OUTPUT' : 'TEMPORARY_OUTPUT',
              'RASTERCOPY' : dtm_rlay }
            algo_nm = 'qgis:rastersampling'
            cPts_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            mstore.addMapLayer(cPts_vlay)
            #===================================================================
            # collect----
            #===================================================================
            df = vlay_get_fdf(cPts_vlay, logger=log).rename(columns={'dtm_1':'dtm', 'z_max':'wsl_max'})
            
            #clear out bad samples
            boolidx = df['wsl_max']==nullSamp
            df.loc[boolidx, 'wsl_max'] = np.nan
            log.debug('\'%s\' droped %i (of %i) bad wsl samples'%(eTag, boolidx.sum(), len(boolidx)))
            
            #calc freeboard
            df['freeboard'] = df['dtm'] - df['wsl_max']
            
            #===================================================================
            # #re-assemble layer
            #===================================================================
            geo_d = vlay_get_fdata(cPts_vlay, geo_obj=True, logger=log)
            res_d[eTag] = self.vlay_new_df2(df, geo_d=geo_d, logger=log,
                                   layname='%s_%s_expo'%(dike_vlay.name(), eTag))
            """
            view(df)
            view(df2)
            """
            
            mstore.removeAllMapLayers() #clear the store
            
            #===================================================================
            # add to master data
            #===================================================================
            dxi = pd.concat([df.T], keys=[eTag], names=['eTag']).T
            if dxcol is None:
                #add a dummy level
                dxcol = dxi
            else:
                dxcol = dxcol.join(dxi)
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished building exposure on %i events'%len(res_d))
        self.expo_cPts_vlay_d = res_d
        self.expo_dxcol = dxcol
            
        return self.expo_dxcol, self.expo_cPtsV_d
    
    #===========================================================================
    # outputs----------
    #===========================================================================
    def output_expos(self,#convenience for outputting all the exposure data
                     dxcol=None,
                     vlay_d = None,
                     logger=None,): 
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('output_expos')
        if dxcol is None: dxcol = self.expo_dxcol
        if vlay_d is None: vlay_d = self.expo_cPts_vlay_d
        #=======================================================================
        # dxcol
        #=======================================================================
        ofp = os.path.join(self.out_dir, '%s_expo_dxcol_%i.csv'%(self.tag, len(1)))
        dxcol.to_csv(ofp, header=True)
        

                

 
    
    
    

    

            
        