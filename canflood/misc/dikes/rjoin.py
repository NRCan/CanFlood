'''
Created on Feb. 9, 2020

@author: cefect

mapping dike analysis results back onto geometry
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
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsMapLayerStore, QgsGeometry

 
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
class DikeJoiner(Qcoms, DPlotr):
    """

    """
 
    #ifidN = 'ifzID'


    def __init__(self,
                  *args,
 
                    **kwargs):
        
        super().__init__(*args,**kwargs)
 
        self.logger.debug('Diker.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
    def load_pfail_df(self,
                      df=None,
                      fp=None,
                      ):
        

        if df is None:
            assert not fp=='', 'must specify a filepath for pfails'
            assert os.path.exists(fp), 'passed filepath for pfails does not exist\n    %s'%fp
            df = pd.read_csv(fp, header=0, index_col=0)
        
        assert isinstance(df, pd.DataFrame)
        #=======================================================================
        # identify columns
        #=======================================================================
        
        prop_colns = [self.dikeID, self.segID, self.segln, self.lfxn, self.celn, self.cbfn, self.ifidN]
        self.etag_l = self._get_etags(df, prop_colns=prop_colns)
        #=======================================================================
        # checks
        #=======================================================================
        assert (df.loc[:, self.etag_l] <=1.0).all().all()
        assert (df.loc[:, self.etag_l] >=0.0).all().all()
        assert self.ifidN in df.columns
        
        self.pfail_df = df
        self.sid_l = df.index.values.tolist()
        """
        view(df)
        """
        return self.pfail_df
        
        
    def load_ifz_fps(self, #load filepaths in an ifz map and replace with layer referneces
                 eifz_d, #ifz map w/ filepaths
                 aoi_vlay=None,
                 base_dir=None,
                 ):
        """
        plugin runs dont need this.
            just pass eifz_d with vlays (no fps)
            what about copies??
            
        #=======================================================================
        # data structure:
        #=======================================================================
        each event (eTag) should have its own ifz polygon layer
            (here we allow for the re-use of layers... but a single layer is still expected)
        each ifz poly feature corresponds to a dike (sid) segment (for that event) (1 ifzID: many sid)
        these ifz polys can be overlapping
        
        often users may duplicate layers/maps between events
            but our structure allows for unique vals 
            
        #=======================================================================
        # TODO:
        #=======================================================================
        setup to assign map based on name matching (between ifz and raster)
            
        """
        log = self.logger.getChild('load_ifz')
        
        
        #=======================================================================
        # prechecks
        #=======================================================================
        miss_l = set(eifz_d.keys()).difference(self.etag_l)
        assert len(miss_l)==0, 'eTag mismatch on eifz_d and pfail_df: %s'%miss_l
        
        
        fp_vlay_d = dict() #container for repeat layers
        #=======================================================================
        # loop and load
        #=======================================================================
        log.info('loading on %i events'%len(eifz_d))
        for eTag, fp_raw in eifz_d.copy().items():
            
            #===================================================================
            # relative filepaths
            #===================================================================
            if not base_dir is None:
                fp = os.path.join(base_dir, fp_raw)
            else:
                fp = fp_raw

            #===================================================================
            # get the layer
            #===================================================================

            #check if its already loaded
            if fp in fp_vlay_d:
                vlay = self.fixgeometries(fp_vlay_d[fp], logger=log, layname=fp_vlay_d[fp].name())
            else:
                vlay = self.load_vlay(fp, aoi_vlay=aoi_vlay, logger=log)
                
                fp_vlay_d[fp] = vlay #add it for next time
                
            #===================================================================
            # check it
            #===================================================================
            assert self._check_ifz(vlay)
            
            #===================================================================
            # #check sid_ifz_d
            #===================================================================
            """
            could force a symmetric_difference... 
                but not a great reason to break when the user passes a map thats too big
                
                because some pfails may get filtered out... 
                    we may not want to throw this error
            """
            #===================================================================
            # miss_l = set(self.sid_l).difference(e_d['sid_ifz_d'])
            # assert len(miss_l)==0, '%s sid_ifz_d missing some %s keys: %s'%(eTag, self.sid, miss_l)
            #===================================================================

            #===================================================================
            # update the container
            #===================================================================
            dp = vlay.dataProvider()
            log.info('%s got vlay \'%s\' w/ %i features'%(eTag, vlay.name(), dp.featureCount()))
            eifz_d[eTag] = vlay
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished loading %i layers for %i events'%(len(fp_vlay_d), len(eifz_d)))
        
        self.eifz_d = eifz_d
        
        return self.eifz_d
            
    def _check_ifz(self, #typical checks for an ifz poly layer
                   vlay):
        assert isinstance(vlay, QgsVectorLayer), type(vlay)
        dp = vlay.dataProvider()
        assert 'Polygon' in QgsWkbTypes().displayString(vlay.wkbType())
        
        
        assert dp.featureCount()>0
        
        miss_l = set([self.ifidN]).difference([f.name() for f in vlay.fields()])
        assert len(miss_l)==0, 'missing some fields: %s'%miss_l
        
        return True
        
    def join_pfails(self, #join the pfail data onto the ifz polys
                    eifz_d=None, #influence poilygions {eTag: poly Vlay}
                        
                    pf_df = None, 
                    
                    pf_min = 0.0, #threshold below which to ignore
                    
                    split_dikes=False, #generate a fpoly layer for each dike
                        #where a breach raster 
                    ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('jp')
        if eifz_d is None: eifz_d=self.eifz_d
        if pf_df is None: pf_df = self.pfail_df
        
        log.info('on %i events w/ pfail %s'%(len(eifz_d), str(pf_df.shape)))
        #=======================================================================
        # precheck
        #=======================================================================
        miss_l = set(self.etag_l).difference(pf_df.columns)
        assert len(miss_l)==0, 'event mismatch: %s'%miss_l
        
        
        #check library keys
        miss_l = set(self.etag_l).difference(eifz_d)
        assert len(miss_l)==0, 'event mismatch: %s'%miss_l
        
        #=======================================================================
        # for eTag, ed in eifz_d.items():
        #     miss_l = set(['ifz_vlay']).difference(ed.keys())
        #     assert len(miss_l)==0, '%s keys mismatch: %s'%(eTag, miss_l)
        #=======================================================================
            
        #=======================================================================
        # loop on events----
        #=======================================================================
        res_d = dict()
        for eTag, vlay_raw in eifz_d.items():
            log = self.logger.getChild('jp.%s'%eTag)
            #===================================================================
            # pull the data----
            #===================================================================
            """
            ed.keys()
            """
            #===================================================================
            # #vlay
            #===================================================================
            #vlay_raw = ed['ifz_vlay']
            self._check_ifz(vlay_raw)
            vdf = vlay_get_fdf(vlay_raw, logger=log)
            geoR_d = vlay_get_fdata(vlay_raw, geo_obj=True, logger=log, rekey=self.ifidN)
            
            log.debug("on \'%s\' w/ %i feats"%(vlay_raw.name(), len(geoR_d)))
            #===================================================================
            # #keys
            #===================================================================
            """get from dike sinstead
            sid_ifz_d = ed['sid_ifz_d']"""
            sid_ifz_d = pf_df[self.ifidN].to_dict()

            #check keysr
            miss_l = set(sid_ifz_d.values()).symmetric_difference(vdf[self.ifidN])
            assert len(miss_l)==0, '%s got key mismatch: %s'%(eTag, miss_l)
            
            #===================================================================
            # pfail
            #===================================================================
            #clean to just our event
            l = set(self.etag_l).difference([eTag]) #other event data
            idf = pf_df.drop(l, axis=1).rename(columns={eTag:self.pfn}) 
            
            idf.loc[:, self.pfn] = idf[self.pfn].round(self.prec) #force rouind (again)

            #idf = idf.join(pd.Series(sid_ifz_d, name=self.ifidN))
            idf['eTag'] = eTag #nice to have this on there
            """
            view(idf)
            """
            
            #apply threshold
            boolidx = idf[self.pfn]<=pf_min
            
            if boolidx.all():
                log.warning('all (of %i) %s below threshold... skipping'%(len(boolidx), self.pfn))
                continue
            elif boolidx.any():
                log.info('got %i (of %i) %s below threshold (%.2f)'%(
                    boolidx.sum(), len(boolidx), self.pfn, pf_min))
                idf = idf.loc[~boolidx, :]
            
            #make sure all these keys are there
            miss_l = set(idf.index.values).difference(sid_ifz_d.keys())
            assert len(miss_l)==0, 'missing keys in sid_ifz_d: %s'%miss_l
            
            #clean out keys            
            sid_ifz_d2 = {k:v for k,v in sid_ifz_d.items() if k in idf.index.values}
            assert len(sid_ifz_d2)==len(idf), 'failed to get the expected matches'
            #===================================================================
            # build new layer-----
            #===================================================================
            """keying everything by sid... one feature per segment"""

            #duplicate the geometry on our keys
            geo_d = {sk:QgsGeometry(geoR_d[ik]) for sk, ik in sid_ifz_d2.items()}
            
            
            if not split_dikes:
                res_d[eTag] = self.vlay_new_df2(idf, geo_d=geo_d, logger=log, index=True,
                                         layname='%s_%s_ifz'%(self.tag, eTag))
                
            else: #separate layers per dike
                did_l = idf[self.dikeID].unique()
                log.info('splitting into %i layers by \'%s\''%(len(did_l), self.dikeID))
                for did in did_l:
                    df_i = idf.loc[idf[self.dikeID]==did, :]
                    
                    geo_d_i = {k:geo_d[k] for k in df_i.index.values} #get these fatures
                    res_d['%s.%s'%(eTag, did)] = self.vlay_new_df2(df_i, geo_d=geo_d_i, logger=log, index=True,
                                         layname='%s_%s_%s_ifz'%(self.tag, eTag, did))
                    
 
            
            log.debug('df %s'%str(idf.shape))
            
        #=======================================================================
        # wrap
        #=======================================================================
        log = self.logger.getChild('jp')
        log.info('finished building %i layers'%len(res_d))
        
        self.ipf_vlay_d = res_d
        return self.ipf_vlay_d
    
    def output_vlays(self,#convenience for outputting all the exposure data
                     vlay_d = None,
                     logger=None,
                    ): 
        #=======================================================================
        # defaults
        #=======================================================================

        if logger is None: logger=self.logger
        log=logger.getChild('output_vlays')

        if vlay_d is None: vlay_d = self.ipf_vlay_d
        
        #=======================================================================
        # setup sub folder
        #=======================================================================

        
        #=======================================================================
        # loop and write
        #=======================================================================
        d = dict()
        log.info('writing %i vlays to file'%len(vlay_d))
        for eTag, vlay in vlay_d.items():
            d[eTag] = self.vlay_write(vlay,  logger=log)
            
        log.debug('finished writing %i'%len(d))
        return d
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
    
    
    

    

            
        