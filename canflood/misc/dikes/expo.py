'''
Created on Feb. 9, 2020

@author: cefect

generate dike exposure data
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
#import logging, configparser, datetime, shutil



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd
from pandas import IndexSlice as idx

#Qgis imports
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsMapLayerStore
 
import processing
#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, view, stat_pars_d, \
    vlay_rename_fields
    
 

from .dPlot import DPlotr
    
#from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class Dexpo(Qcoms, DPlotr):
 
    def __init__(self,
                 
                  *args,  **kwargs):
        
        super().__init__(*args,**kwargs)
        

        
        self.logger.debug('Diker.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def load_rlays(self,
                   layfp_d,
                   basedir=None,
                   logger=None,
                   **kwargs):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('load_rlays')
        
        log.info('on %i layers'%len(layfp_d))
        
        if not basedir is None: assert os.path.exists(basedir)
        assert isinstance(layfp_d, dict), 'bad type passed on layfp_d'
        #=======================================================================
        # load it
        #=======================================================================
        d = dict()
        
        for layTag, fp in layfp_d.items():
            if not basedir is None:
                fp = os.path.join(basedir, fp)
            d[layTag] = self.load_rlay(fp, logger=log, **kwargs)
            
        log.info('loaded %i layers'%len(d))
        
        return d
    
    def prep_dike(self, #do some pre-calcs on teh dike layer
                vlay_raw,
                  dikeID = None, #dike identifier field
                  segID = None, #segment identifier field
                  cbfn = None, #crest buffer fieldname
                  
 
                   logger=None):
        
        """
        not sure it makes sense to have this separate from get_dike_expo anymroe
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('load_dikes')
        
        if dikeID is None: dikeID = self.dikeID
        if segID is None: segID = self.segID
        if cbfn is None: cbfn = self.cbfn
        
        
        mstore = QgsMapLayerStore() #build a new map store
        
 
        
        #=======================================================================
        # precheck
        #=======================================================================
        fnl = [f.name() for f in vlay_raw.fields()]
        #jcolns = [self.sid, 'f0_dtag', self.cbfn, self.segln]
        miss_l =  set([dikeID, segID, 'f0_dtag', cbfn, self.ifidN]).difference(fnl)
        assert len(miss_l)==0, 'missing expected columns on dike layer: %s'%miss_l
        assert not 'length' in [s.lower() for s in fnl], '\'length\' field not allowed on dikes layer'
        
        """try forcing
        assert 'int' in df[segID].dtype.name, 'bad dtype on dike layer %s'%segID
        assert 'int' in df[dikeID].dtype.name, 'bad dtype on dike layer %s'%dikeID"""
        
        #geometry
        assert 'Line' in QgsWkbTypes().displayString(vlay_raw.wkbType()), 'bad vector type on dike'
        
        #=======================================================================
        # add geometry data
        #=======================================================================
        d = { 'CALC_METHOD' : 0, 'INPUT' : vlay_raw,'OUTPUT' : 'TEMPORARY_OUTPUT' }

        vlay = processing.run('qgis:exportaddgeometrycolumns', d, feedback=self.feedback)['OUTPUT']
        mstore.addMapLayer(vlay)
        
        """
        view(vlay)
        """
        #rename the vield
        vlay = vlay_rename_fields(vlay, {'length':self.segln})
        mstore.addMapLayer(vlay)
        #=======================================================================
        # pull data
        #=======================================================================
        df = vlay_get_fdf(vlay, logger=log)

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
        
        df[self.sid] = s1.str.cat(others=s2).astype(int)
        
        assert df[self.sid].is_unique, 'failed to get unique global segment ids... check your dikeID and segID'
        # bundle back into vectorlayer
        geo_d = vlay_get_fdata(vlay, geo_obj=True, logger=log)
        res_vlay = self.vlay_new_df2(df, geo_d=geo_d, logger=log,
                               layname='%s_dike_%s'%(self.tag, vlay_raw.name()))
        
        
        #=======================================================================
        # wrap
        #=======================================================================
        dp = res_vlay.dataProvider()
        log.info('loaded dike layer \'%s\'  w/ %i segments'%(vlay.name(), dp.featureCount()))

        self.dike_vlay = res_vlay
        self.dike_df = df
        
        """attching this again in case th user passes new values"""
        self.dikeID, self.segID, self.cbfn = dikeID, segID, cbfn #done during init
        self.sid_vals = df[self.sid].unique().tolist()
        mstore.removeAllMapLayers()
        
         
        return self.dike_vlay
    

    
    def get_dike_expo(self, #get exposure set for dikes
                    noFailr_d,
                    dike_vlay = None,
                    dtm_rlay = None,
                    
                    #dike layer parameters
                    sid = None,
                    
                    #cross profile (transect) parameters
                    simp_dike = 0, #value to simplify dike cl by
                    dist_dike = 40, #distance along dike to draw perpindicular profiles
                    dist_trans = 100, #length (from dike cl) of transect 
                    tside = 'Left', #side of dike line to draw transect
                    dens_int = None, #density of sample points along transect 
                    nullSamp = None, #value for bad samples
                    write_tr = False, #wheter to output the unsampled transect layer
                    calc_dist = True, #whether to calculate distance between transects
                    
                    #wsl sampling
                    #wsl_stat = 'Max', #for transect wsl zvals, stat to use for summary
                    
                    logger=None,
                    ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('get_dike_expo')
        if dike_vlay is None: dike_vlay = self.dike_vlay
        if dtm_rlay is None: dtm_rlay = self.dtm_rlay
        if sid is None: sid = self.sid
        if nullSamp is None: nullSamp = self.nullSamp
        mstore = QgsMapLayerStore() #build a new map store
        #=======================================================================
        # prechecks
        #=======================================================================
        assert isinstance(dike_vlay, QgsVectorLayer)
        assert sid in [f.name() for f in dike_vlay.fields()], \
            'failed to get sid \'%s\'on dikes vlay fields'%(sid)
        
        #crs
        for layer in [dike_vlay, dtm_rlay]:
            assert layer.crs().authid() == self.qproj.crs().authid(), \
                '\'%s\' crs (%s) does not match projects: %s'%(
                    layer.name(), layer.crs().authid(), self.qproj.crs().authid())
        
        #tside
        tside_d = {'Left':0, 'Right':1, 'Both':2}
        assert tside in tside_d, 'bad tside: \'%s\''%tside
        assert not tside =='Both', 'Both not supported'
        

        
        #=======================================================================
        # crossProfiles---
        #=======================================================================
        #=======================================================================
        # simplify
        #=======================================================================
        """because transects draws at each vertex, we wanna reduce the number.
        each vertex will still be on the original line
        
        NO! better to use the raw alignment... .
        even a small simplification can move the sampling off the DTM's dike crest"""
        if simp_dike > 0:
            d = { 'INPUT' : dike_vlay, 'METHOD' : 0, 'OUTPUT' : 'TEMPORARY_OUTPUT', 
                 'TOLERANCE' : simp_dike}
            algo_nm = 'native:simplifygeometries'
            dvlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            mstore.addMapLayer(dvlay)
        else:
            dvlay = dike_vlay
        #=======================================================================
        # densify
        #=======================================================================
        #make sure we get at least the number of transects requested
        d = { 'INPUT' : dvlay,'INTERVAL' : dist_dike, 'OUTPUT' : 'TEMPORARY_OUTPUT' }
        
        algo_nm='native:densifygeometriesgivenaninterval'
        dvlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
        dvlay.setName('%s_prepd'%dike_vlay.name())
        #mstore.addMapLayer(dvlay) #need to keep this alive for the intersect calc below
        """
        self.vlay_write(dvlay)
        """
        #=======================================================================
        # transects
        #=======================================================================
        """draws perpindicular lines at vertex.
        keeps all the fields and adds some new ones"""
        d = { 'ANGLE' : 90, 'INPUT' :dvlay, 'LENGTH' : dist_trans, 'OUTPUT' : 'TEMPORARY_OUTPUT', 
             'SIDE' : tside_d[tside]}

        algo_nm="native:transect"
        tr_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
        mstore.addMapLayer(tr_vlay)
        

        #see if indexer is unique
        tr_fid = 'TR_ID'
        ifn_d = vlay_get_fdata(tr_vlay, fieldn=tr_fid, logger=log)
        assert len(set(ifn_d.values()))==len(ifn_d)
        
        #=======================================================================
        # #clean it up
        #=======================================================================
        #remove unwanted fields
        """
        the raw transects have a 'fid' based on the dike fid (which is now non-unique)
        TR_ID is a new feature id (for the transects)
        """        
        tr_colns = [sid, self.dikeID, self.segID, tr_fid,  'TR_SEGMENT']
        tr_vlay = self.deletecolumn(tr_vlay, tr_colns, logger=log, invert=True)
        
        #tr_vlay  = vlay_rename_fields(tr_vlay, {tr_fid:'fid_tr'})
        
        
        #=======================================================================
        # calc distance----
        #=======================================================================
        if calc_dist:
            """
            optional to join in distance along dike field for transects
            
            view(tr_vpts_vlay)
            view(tr_vlay)
            """
            
            #===================================================================
            # #pull out the verticies
            #===================================================================
            d = { 'INPUT' : dvlay, 'OUTPUT' : 'TEMPORARY_OUTPUT' }

            algo_nm = 'native:extractvertices'
            tr_vpts_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            mstore.addMapLayer(tr_vpts_vlay)
            
            #===================================================================
            # #join in values
            #===================================================================
            """
            linking up ID fields between vertex points (which have the distances) and the transects
            
            vpts: vertex_part_index
            tr: TR_SEGMENT

            """
            tr_df = vlay_get_fdf(tr_vlay, logger=log)
            vpts_df = vlay_get_fdf(tr_vpts_vlay, logger=log).drop(
                ['vertex_part', 'vertex_part_index', 'angle','fid'], axis=1)
            
            #add shifted index
            vpts_df['TR_SEGMENT'] = vpts_df['vertex_index']+1
            
            vpts_df.loc[:, 'distance'] = vpts_df['distance'].round(self.prec)
            
            #check
            assert len(vpts_df)==len(tr_df)
            
            
            #loop in 'sid' blocks
            """TR_SEGMENT is indexed per-segment"""
            indxr = 'TR_SEGMENT'
            tr_dfR = None
            log.info('joining vertex data (%s) to transect data (%s) in %i \'%s\' blocks'%(
                str(vpts_df.shape), str(tr_df.shape), len(tr_df[sid].unique()), sid))
            
            for sidVal, tr_sdf in tr_df.copy().groupby(sid):
                vpts_sdf = vpts_df.groupby(sid).get_group(sidVal).loc[:, ('distance', indxr)]
                df = tr_sdf.join(vpts_sdf.set_index(indxr), on=indxr)
                
                #append results
                if tr_dfR is None:
                    tr_dfR = df
                else:
                    tr_dfR  = tr_dfR.append(df)
                
            #===================================================================
            # clean
            #===================================================================
            tr_dfR = tr_dfR.rename(columns={'distance':self.sdistn})
            tr_colns.append(self.sdistn)
            #===================================================================
            # check
            #===================================================================
            log.debug('finished w/ %s'%str(tr_dfR.shape))
            assert len(tr_df)==len(tr_dfR)
                
            #check index
            tr_dfR = tr_dfR.sort_index(axis=0)
            assert np.array_equal(tr_dfR.index, tr_df.index)
            
            #===================================================================
            # #recreate layer
            #===================================================================
            mstore.addMapLayer(tr_vlay) #add in old layer
            geo_d = vlay_get_fdata(tr_vlay, geo_obj=True, logger=log)
            tr_vlay = self.vlay_new_df2(tr_dfR, geo_d=geo_d, logger=log,
                                   layname='%s_%s_tr_dist'%(self.tag, dike_vlay.name()))
            
            log.debug('finished joining in distances')
            
            """
            self.vlay_write(tr_vlay)
            """
                 

        #=======================================================================
        # densify
        #=======================================================================
        #add additional veritifies to improve the resolution of the wsl sample
        if dens_int is None: desn_int = min(dist_dike, dist_trans/2)
        d = { 'INPUT' : tr_vlay,'INTERVAL' : desn_int, 'OUTPUT' : 'TEMPORARY_OUTPUT' }
        algo_nm='native:densifygeometriesgivenaninterval'
        tr_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
        mstore.addMapLayer(tr_vlay)

        tr_vlay = self.fixgeometries(tr_vlay, logger=log)
        mstore.addMapLayer(tr_vlay)
        #=======================================================================
        # #clean it up
        #=======================================================================
        #remove unwanted fields
        """
        the raw transects have a 'fid' based on the dike fid (which is now non-unique)
        TR_ID is a new feature id (for the transects)
        """        
        tr_vlay = self.deletecolumn(tr_vlay, tr_colns, logger=log, invert=True)
        mstore.addMapLayer(tr_vlay)

        tr_vlay.setName('%s_%s_transects'%(self.tag, dike_vlay.name()))
                
        log.info('got %i transects'%tr_vlay.dataProvider().featureCount())
        #=======================================================================
        # crest el----
        #=======================================================================
        #===================================================================
        # point on dike crest
        #===================================================================
        """gets a point for the vertex at the START of the line.
        should work fine for right/left.. but not for 'BOTH'
        """
        """this is cleaner for handling transects on either side... 
        but can result in MULTIPLE intersects for some geometries
        
        d = { 'INPUT' : tr_vlay, 'INPUT_FIELDS' : [], 'INTERSECT' : dvlay, 
             'INTERSECT_FIELDS' : ['fid'], 'INTERSECT_FIELDS_PREFIX' : 'dike_',
              'OUTPUT' : 'TEMPORARY_OUTPUT' }

        algo_nm = 'native:lineintersections'"""
        
        
        #get the head/tail point of the transect
        d = { 'INPUT' : tr_vlay, 'OUTPUT' : 'TEMPORARY_OUTPUT', 
             'VERTICES' : {'Left':'0', 'Right':'-1'}[tside] }  
        
        algo_nm = 'qgis:extractspecificvertices'
        cPts_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
        mstore.addMapLayer(cPts_vlay)
        """
        view(cPts_vlay)
        """
        #count check
        assert tr_vlay.dataProvider().featureCount()==cPts_vlay.dataProvider().featureCount()
        

        #===================================================================
        # crest sample
        #===================================================================
        assert cPts_vlay.crs().authid() == dtm_rlay.crs().authid(), 'CRS mismatch!'
        d = { 'COLUMN_PREFIX' : 'dtm', 'INPUT' : cPts_vlay, 'OUTPUT' : 'TEMPORARY_OUTPUT',
          'RASTERCOPY' : dtm_rlay }
        algo_nm = 'qgis:rastersampling'
        cPts_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
        mstore.addMapLayer(cPts_vlay)
        
        #=======================================================================
        # clean up
        #=======================================================================
        cPts_vlay  = vlay_rename_fields(cPts_vlay, {'dtm1':self.celn})
        
        tr_colns.append(self.celn)
        cPts_vlay = self.deletecolumn(cPts_vlay, tr_colns, logger=log, invert=True,
                                      layname = '%s_cPts'%(tr_vlay.name()))
        #mstore.addMapLayer(cPts_vlay)
        
        #=======================================================================
        # join back
        #=======================================================================
        """easier to keep all the data on the transects
        
        self.vlay_write(cPts_vlay)
        view(tr_vlay)
        """
        
        d = { 'DISCARD_NONMATCHING' : False, 'FIELD' : tr_fid, 
             'FIELDS_TO_COPY' : [self.celn], 'FIELD_2' : tr_fid, 
             'INPUT' : tr_vlay,'INPUT_2':cPts_vlay,
              'METHOD' : 1, 'OUTPUT' : 'TEMPORARY_OUTPUT', 'PREFIX' : '' }
        algo_nm = 'native:joinattributestable'
        tr_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
        #=======================================================================
        # output
        #=======================================================================
        tr_vlay.setName('%s_%s_transects'%(self.tag, dike_vlay.name()))
        if write_tr:
            self.vlay_write(tr_vlay, logger=log)
        self.tr_vlay=tr_vlay #set for loading by the dialog
        mstore.removeAllMapLayers() #clear the store
        
        log.info('joined crest elevations')
        #=======================================================================
        # get wsls----
        #=======================================================================
        res_d = dict()
        dxcol = None
        
        #comColns = [self.sdistn, self.celn, self.segID, self.dikeID] #common columns
        
        geo_d = vlay_get_fdata(cPts_vlay, rekey= tr_fid, geo_obj=True, logger=log)

        log.info('building %i cross profile sets'%len(noFailr_d))
        for eTag, wsl_rlay in noFailr_d.items():
        
            #===================================================================
            # drape---
            #===================================================================
            d = { 'BAND' : 1, 'INPUT' : tr_vlay, 'NODATA' : nullSamp, 
                 'OUTPUT' : 'TEMPORARY_OUTPUT', 'RASTER' : wsl_rlay,
                  'SCALE' : 1,}
            algo_nm = 'native:setzfromraster'
            tri_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            mstore.addMapLayer(tri_vlay)
            #===================================================================
            # extract z
            #===================================================================
            ofnl = [f.name() for f in tri_vlay.fields()]
            """because of the nullvalue handling... we should only be looking for a maximum here"""
            d = { 'COLUMN_PREFIX' : 'z_', 'INPUT' : tri_vlay,
                  'OUTPUT' : 'TEMPORARY_OUTPUT', 'SUMMARIES' : [stat_pars_d['Maximum']], 
                   }
            algo_nm = 'native:extractzvalues'
            tri_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            mstore.addMapLayer(tri_vlay)
            
            #get new fieldName
            wslField = list(set([f.name() for f in tri_vlay.fields()]).difference(ofnl))[0]

            #===================================================================
            # collect----
            #===================================================================
            """
            view(tri_vlay)
            """
            df = vlay_get_fdf(tri_vlay, logger=log).rename(columns={wslField:self.wsln})
            
            #clear out bad samples
            boolidx = df[self.wsln]==nullSamp
            df.loc[boolidx, self.wsln] = np.nan
            log.debug('\'%s\' droped %i (of %i) bad wsl samples'%(eTag, boolidx.sum(), len(boolidx)))
            
            #calc freeboard
            df[self.fbn] = df[self.celn] - df[self.wsln]
            
            df.loc[:, (self.fbn, self.celn, self.wsln)] = df.loc[:, (self.fbn, self.celn, self.wsln)].round(self.prec)
            
            #===================================================================
            # #re-assemble layer
            #===================================================================
            #building from points (should be keyed by 'TR_ID')
            res_d[eTag] = self.vlay_new_df2(df, geo_d=geo_d, logger=log, gkey=tr_fid,
                                   layname='%s_%s_expo'%(dike_vlay.name(), eTag))

            mstore.removeAllMapLayers() #clear the store
            
            #===================================================================
            # add to master data
            #===================================================================
            dxi = pd.concat([df.loc[:,(self.fbn, self.wsln)].T], keys=[eTag], names=['eTag']).T

            if dxcol is None:
                #add a dummy level
                dxcol = dxi
            else:
                dxcol = dxcol.join(dxi)
            
        #=======================================================================
        # clean up data
        #=======================================================================
        #join back in common columns
        """pulling from last loaded transect
        
        see get_fb_smry() for additional fields that we add to the summary results
            (used by the vuln model)
        """
        boolcol = df.columns.isin(dxcol.columns.levels[1])
        dxcol = dxcol.join(pd.concat([df.loc[:, ~boolcol].T], keys=['common'], names=['eTag']).T)
        
        
        #typeset
        for coln, dtype in df.dtypes.to_dict().items():
            dxcol.loc[:, idx[:, coln]] = dxcol.loc[:, idx[:, coln]].astype(dtype)

        #=======================================================================
        # wrap----
        #=======================================================================
        log.info('finished building exposure on %i events'%len(res_d))
        self.expo_vlay_d = res_d
        self.expo_dxcol = dxcol

        return self.expo_dxcol, self.expo_vlay_d
    
    def get_fb_smry(self, #get a summary of the freeboard value for feeding to the curves 
                      dxcol = None,
                      stat = 'min', #summary statistic to apply to the freeboard values (min=worst case)
                      logger=None,

                      **kwargs
                     ):

        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('get_smry_expo')
        if dxcol is None: dxcol = self.expo_dxcol.copy()
        
        log.info("on %s"%str(dxcol.shape))
        
        assert hasattr(dxcol, stat), 'unreocgnized function \'%s\''%stat
        
        #=======================================================================
        # get segment (common) attributes
        #=======================================================================
        cdf = dxcol.loc[:, idx['common', (self.dikeID, self.segID, self.sid)]
                        ].droplevel(level=0, axis=1)
        
        seg_df = cdf.groupby(self.sid).first()
        
        #join tags
        jcolns = [self.sid, 'f0_dtag', self.cbfn, self.segln, self.ifidN]
        """needed by vuln module"""
        seg_df = seg_df.join(self.dike_df.loc[:, jcolns].set_index(self.sid))
        #=======================================================================
        # loop and calc stat---
        #=======================================================================
        res_df = None
        for eTag, edxcol in dxcol.drop('wsl', level=1, axis=1).groupby(level=0, axis=1):
            if eTag == 'common': continue
            
            #get this frame (with the sid values attached)
            edf = edxcol.droplevel(level=0, axis=1).join(cdf[self.sid])
            """
            view(edxcol)
            """
            
            
        
            #get the stat (for each gruop)
            f = getattr(edf.groupby(self.sid), stat)
            esdf = f(**kwargs).rename(columns={self.fbn:eTag})

            
            #append result
            if res_df is None:
                res_df = seg_df.join(esdf)
            else:
                res_df = res_df.join(esdf)
                
        #=======================================================================
        # crest summary
        #=======================================================================
        for coln in [self.celn]:
            """dont rename anything here.. makes column detection difficult"""
            res_df = res_df.join(dxcol.loc[:, ('common', (self.sid, coln))].droplevel(level=0, axis=1
                             ).groupby(self.sid).min())
            

                
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('got summaries on %i events and %i segments'%(
            len(res_df.columns)-len(jcolns), len(res_df)))
        
        self.expo_df = res_df
        return self.expo_df
    
    def get_dikes_vlay(self, #promote the index on the dikes_vlay
                     df = None,
                     vlay = None, #geometry to use for writing
                    logger=None,
                       ):
        
        #=======================================================================
        # defautls
        #=======================================================================
 
        if logger is None: logger=self.logger
        log=logger.getChild('get_dikes_vlay')
        
        if df is None: df = self.expo_df.copy()
        if vlay is None: vlay = self.dike_vlay
        
        #=======================================================================
        # update the dikes layer
        #=======================================================================
        geo_d = vlay_get_fdata(vlay, geo_obj=True, logger=log, rekey=self.sid)
        
        #add the index as a column so it gets into the layer
        df.index.name=None
        df[self.sid] = df.index
        
        return self.vlay_new_df2(df, geo_d=geo_d, logger=log,
                           layname=vlay.name())
        
    

    def get_breach_vlays(self, #get exposure points with negative freeboard
                         vlay_d = None,
                         logger=None,
                         ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('get_breach_vlays')
        if vlay_d is None: vlay_d = self.expo_vlay_d
        
        #=======================================================================
        # loop and calc for each
        #=======================================================================
        log.info('on %i vlays'%len(vlay_d))
        res_d = dict()
        for eTag, vlay_raw in vlay_d.items():
            log.debug('on %s w/ %i feats'%(eTag, vlay_raw.dataProvider().featureCount()))
            
            #extract features with freeboard < 0
            
            d = { 'EXPRESSION' : ' \"freeboard\" <0', 'INPUT' :vlay_raw,'OUTPUT' : 'TEMPORARY_OUTPUT' }
            algo_nm = 'native:extractbyexpression'
            vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
            
            fcnt = vlay.dataProvider().featureCount()
            if fcnt ==0:
                log.debug('%s got no breach points'%eTag)
            else:
                log.debug('%s got %i breach poitns'%(eTag, fcnt))
                vlay.setName('%s_breach_%i_pts'%(eTag, fcnt))
                res_d[eTag] = vlay
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished w/ %i layers0'%len(res_d))
        self.breach_vlay_d = res_d
        return res_d
    
    def get_breach_area(self):
        """
        this would be very tricky to automate....
        
        check:
        SAGA 'fill sinks' for a simple dtm filler
        SAGA 'Lake flood' for filling a dtm up to a specified depth
        
        """
        raise Error('not implemented')
    

    #===========================================================================
    # outputs----------
    #===========================================================================
    def output_expo_dxcol(self,#convenience for outputting all the exposure data
                     dxcol=None,
                     logger=None,
                     overwrite=None,): 
        #=======================================================================
        # defaults
        #=======================================================================
        if overwrite is None: overwrite=self.overwrite
        if logger is None: logger=self.logger
        log=logger.getChild('output_dxcol')
        if dxcol is None: dxcol = self.expo_dxcol

        #=======================================================================
        # dxcol
        #=======================================================================
        ofp = os.path.join(self.out_dir, 
                           '%s_dExpo_dxcol_%i.csv'%(self.tag, len(dxcol.columns.levels[0])))
        if os.path.exists(ofp):
            assert overwrite
            
        dxcol.to_csv(ofp, header=True)
        
        log.info('wrote expo_dxcol to %s'%ofp)
        
        return ofp
    
    def output_expo_df(self, #output the dike data (for the vuln calc
                  df = None,
 
                     logger=None,
                     overwrite=None,
 
                     ): 
        """
        see also get_dikes_vlay()
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if overwrite is None: overwrite=self.overwrite
        if logger is None: logger=self.logger
        log=logger.getChild('output_dikes_csv')
        
        if df is None: df = self.expo_df.copy()
 
        
        #=======================================================================
        # tabular
        #=======================================================================
        ofp = os.path.join(self.out_dir, '%s_dExpo_%i_%i.csv'%(
            self.tag, len(df.columns)-4,len(df) ))
        
        if os.path.exists(ofp):assert self.overwrite
            
        df.to_csv(ofp, index=True)
        
        log.info('wrote %s to file \n    %s'%(str(df.shape), ofp))
        
 
        return ofp
        
        
    def output_vlays(self,#convenience for outputting all the exposure data
                     vlay_d = None,
                     logger=None,
                     overwrite=None,): 
        #=======================================================================
        # defaults
        #=======================================================================
        if overwrite is None: overwrite=self.overwrite
        if logger is None: logger=self.logger
        log=logger.getChild('output_vlays')

        if vlay_d is None: vlay_d = self.expo_vlay_d
        
        #=======================================================================
        # setup sub folder
        #=======================================================================
        out_dir = os.path.join(self.out_dir, 'expo_crest_pts')
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        
        #=======================================================================
        # loop and write
        #=======================================================================
        d = dict()
        log.info('writing %i vlays to file'%len(vlay_d))
        for eTag, vlay in vlay_d.items():
            ofp = os.path.join(out_dir, '%s_%s_expoPts_%i.gpkg'%(
                self.tag, eTag, vlay.dataProvider().featureCount()))
            
            if os.path.exists(ofp): assert self.overwrite
            
            d[eTag] = self.vlay_write(vlay, out_fp=ofp, logger=log)
            
        log.debug('finished writing %i'%len(d))
        return d
    
    def output_breaches(self, #conveninence for output of just breach points
                     vlay_d = None,
                     logger=None,
                     overwrite=None,): 
        #=======================================================================
        # defaults
        #=======================================================================
        if overwrite is None: overwrite=self.overwrite
        if logger is None: logger=self.logger
        log=logger.getChild('output_breaches')

        if vlay_d is None: vlay_d = self.breach_vlay_d
        
        #=======================================================================
        # setup sub folder
        #=======================================================================
        out_dir = os.path.join(self.out_dir, 'breach_pts')
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        
        #=======================================================================
        # loop and write
        #=======================================================================
        d = dict()
        log.info('writing %i vlays to file'%len(vlay_d))
        for eTag, vlay in vlay_d.items():
            ofp = os.path.join(out_dir, '%s_%s_breach_%i.gpkg'%(
                self.tag, eTag, vlay.dataProvider().featureCount()))
            
            if os.path.exists(ofp): assert self.overwrite
            
            d[eTag] = self.vlay_write(vlay, out_fp=ofp, logger=log)
            
        log.debug('finished writing %i'%len(d))
        return d
            
                

 
    
    
    

    

            
        