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
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsMapLayerStore, QgsFeatureRequest
import processing
#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, view, stat_pars_d, \
    vlay_rename_fields
    
#from hlpr.basic import get_valid_filename

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
        self.dikeID, self.segID = dikeID, segID
        
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
                    
                    #cross profile (transect) parameters
                    simp_dike = 2, #value to simplify dike cl by
                    dist_dike = 40, #distance along dike to draw perpindicular profiles
                    dist_trans = 100, #length (from dike cl) of transect 
                    tside = 'Left', #side of dike line to draw transect
                    dens_int = None, #density of sample points along transect 
                    nullSamp = -999, #value for bad samples
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
        
        mstore = QgsMapLayerStore() #build a new map store
        #=======================================================================
        # prechecks
        #=======================================================================
        assert sid in [f.name() for f in dike_vlay.fields()], 'failed to get sid on dikes'
        
        
        #tside
        tside_d = {'Left':0, 'Right':1, 'Both':2}
        assert tside in tside_d, 'bad tside: \'%s\''%tside
        assert not tside =='Both', 'Both not supported'
        
        #wsl sampling
        #=======================================================================
        # assert wsl_stat in stat_pars_d, 'bad wsl_stat: %s'%wsl_stat
        # assert wsl_stat == 'Max', 'wsl_stat has to be maximum'
        #=======================================================================
        
        #=======================================================================
        # crossProfiles---
        #=======================================================================
        #=======================================================================
        # simplify
        #=======================================================================
        """because transects draws at each vertex, we wanna reduce the number.
        each vertex will still be on the original line"""
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
        #mstore.addMapLayer(dvlay) #need to keep this alive for the intersect calc below
        
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
        ifn_d = vlay_get_fdata(tr_vlay, fieldn='TR_ID', logger=log)
        assert len(set(ifn_d.values()))==len(ifn_d)
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
        
        #=======================================================================
        # #clean it up
        #=======================================================================
        tr_vlay.setName('%s_%s_transects'%(self.tag, dike_vlay.name()))
        
        """
        view(tr_vlay)
        vlay_write(tr_vlay, r'C:\LS\03_TOOLS\CanFlood\ins\MFRA\20210131\outs\tr_vlay.gpkg', overwrite=True)
        """
        
        #remove unwanted fields
        """
        the raw transects have a 'fid' based on the dike fid (which is now non-unique)
        TR_ID is a new feature id (for the transects)
        """
        dp = tr_vlay.dataProvider()
        drop_l = set([f.name() for f in tr_vlay.fields()]).difference(
            [sid, self.dikeID, self.segID, 'TR_ID'])
        fdrop_l = [dp.fieldNameIndex(f) for f in drop_l] #get indexes
        dp.deleteAttributes(fdrop_l)
        tr_vlay.updateFields()
        
        # #rename field
        tr_vlay  = vlay_rename_fields(tr_vlay, {'TR_ID':'fid_tr'})
        
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
        d = { 'COLUMN_PREFIX' : 'dtm', 'INPUT' : cPts_vlay, 'OUTPUT' : 'TEMPORARY_OUTPUT',
          'RASTERCOPY' : dtm_rlay }
        algo_nm = 'qgis:rastersampling'
        cPts_vlay = processing.run(algo_nm, d, feedback=self.feedback)['OUTPUT']
        #store.addMapLayer(cPts_vlay)
        
        #=======================================================================
        # clean up
        #=======================================================================
        cPts_vlay  = vlay_rename_fields(cPts_vlay, {'dtm_1':'crest_el'})
        cPts_vlay.setName('%s_cPts'%(tr_vlay.name()))
        
        """
        self.vlay_write(cPts_vlay)
        """
        
        #=======================================================================
        # calc distance
        #=======================================================================
        if calc_dist:
            cPts_vlay = self.vlay_pts_dist(cPts_vlay, ifn='fid_tr', logger=log)
        
        #=======================================================================
        # join values back
        #=======================================================================
        
            
        

        
        #=======================================================================
        # output
        #=======================================================================
        if write_tr:
            self.vlay_write(tr_vlay)
         
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
            df = vlay_get_fdf(cPts_vlay, logger=log
                          ).rename(columns={'dtm_1':'crest_el', wslField:'wsl'}
                                   ).drop('dike_fid', axis=1, errors='ignore')
            
            #clear out bad samples
            boolidx = df['wsl']==nullSamp
            df.loc[boolidx, 'wsl'] = np.nan
            log.debug('\'%s\' droped %i (of %i) bad wsl samples'%(eTag, boolidx.sum(), len(boolidx)))
            
            #calc freeboard
            df['freeboard'] = df['crest_el'] - df['wsl']
            
            df.loc[:, ('freeboard', 'crest_el', 'wsl')] = df.loc[:, ('freeboard', 'crest_el', 'wsl')].round(self.prec)
            
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
        self.expo_vlay_d = res_d
        self.expo_dxcol = dxcol
        """
        view(dxcol)
        """
            
        return self.expo_dxcol, self.expo_vlay_d
    
    #===========================================================================
    # plot-----
    #===========================================================================
    def plot_profile(self):
        pass

    
    #===========================================================================
    # outputs----------
    #===========================================================================
    def output_dxcol(self,#convenience for outputting all the exposure data
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
                           '%s_expo_dxcol_%i.csv'%(self.tag, len(dxcol.columns.levels[0])))
        if os.path.exists(ofp):
            assert overwrite
            
        dxcol.to_csv(ofp, header=True)
        
        log.info('wrote expo_dxcol to %s'%ofp)
        
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
            
                

 
    
    
    

    

            
        