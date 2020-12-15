'''
Created on Feb. 9, 2020

@author: cefect
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, shutil, gc
start = datetime.datetime.now()


#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd


#Qgis imports
from qgis.core import *
    
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
import processing
#==============================================================================
# custom imports
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
#plugin runs
else:
    #base_class = object
    from hlpr.exceptions import QError as Error
    

#from hlpr.Q import *
from hlpr.Q import Qcoms,vlay_get_fdf, vlay_get_fdata
import hlpr.basic as basic

#==============================================================================
# functions-------------------
#==============================================================================
class Rsamp(Qcoms):
    """ sampling hazard rasters from the inventory
    
    METHODS:
        run(): main caller for Hazard Sampler 'Sample' button
    
    
    """
    out_fp = None
    names_d = None
    rname_l =None
    
    
    psmp_codes = {
                 0:'Count',
                 1: 'Sum',
                 2: 'Mean',
                 3: 'Median',
                 #4: Std. dev.
                 5: 'Min',
                 6: 'Max',
                # 7: Range
                # 8: Minority
                # 9: Majority (mode)
                # 10: Variety
                # 11: Variance
                # 12: All
                }
    

    
    
    def __init__(self,
                 fname='expos', #prefix for file name
                  *args, **kwargs):
        """
        Plugin: called by each button push
        """
        
        super().__init__(*args, **kwargs)
        
        self.fname=fname
        #flip the codes
        self.psmp_codes = dict(zip(self.psmp_codes.values(), self.psmp_codes.keys()))
        
        self.logger.info('Rsamp.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)

                
    def load_layers(self, #load data to project (for console runs)
                    rfp_l, finv_fp,
                    providerLib='ogr'
                    ):
        
        """
        special input loader for StandAlone runs
        Im assuming for the plugin these layers will be loaded already"""
        log = self.logger.getChild('load_layers')
        
        
        #======================================================================
        # load rasters
        #======================================================================
        raster_d = dict()
        
        for fp in rfp_l:
            rlayer = self.load_rlay(fp)
            
            #add it in
            basefn = os.path.splitext(os.path.split(fp)[1])[0]
            raster_d[basefn] = rlayer
            
        #======================================================================
        # load finv vector layer
        #======================================================================
        fp = finv_fp
        assert os.path.exists(fp), fp
        basefn = os.path.splitext(os.path.split(fp)[1])[0]
        vlay_raw = QgsVectorLayer(fp,basefn,providerLib)
        
        
        

        # checks
        if not isinstance(vlay_raw, QgsVectorLayer): 
            raise IOError
        
        #check if this is valid
        if not vlay_raw.isValid():
            raise Error('loaded vlay \'%s\' is not valid. \n \n did you initilize?'%vlay_raw.name())
        
        #check if it has geometry
        if vlay_raw.wkbType() == 100:
            raise Error('loaded vlay has NoGeometry')
        
        
        self.mstore.addMapLayer(vlay_raw)
        
        
        vlay = vlay_raw
        dp = vlay.dataProvider()

        log.info('loaded vlay \'%s\' as \'%s\' %s geo  with %i feats from file: \n     %s'
                    %(vlay.name(), dp.storageType(), QgsWkbTypes().displayString(vlay.wkbType()), dp.featureCount(), fp))
        
        
        #======================================================================
        # wrap
        #======================================================================
        
        return list(raster_d.values()), vlay
    

    def run(self, 
            rlayRaw_l, #set of rasters to sample 
            finv_raw, #inventory layer
            
            cid = None, #index field name on finv
                        
            #exposure value controls
            psmp_stat='Max', #for polygon finvs, statistic to sample
            
            #inundation sampling controls
            as_inun=False, #whether to sample for inundation (rather than wsl values)
            dtm_rlay=None, #dtm raster
            dthresh = 0, #fordepth threshold
            clip_dtm=False,
            
            #prep controls
            aoi_vlay = None, #aoi for downloading and clipping
            clip_rlays=False, #whether to clip the rasters by the pased aoi_vlay
            allow_download = True, #whether to allow downloading of non-gdal dataProviders
            allow_rproj = True,
            scaleFactor=1.0, #whether to scale raster values
            
            ):
        """
        Generate the exposure dataset ('expos') from a set of hazard event rasters
        
        """
        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        if cid is None: cid = self.cid

        self.as_inun = as_inun

        
        log.info('executing on %i rasters'%(len(rlayRaw_l)))

        #======================================================================
        # precheck
        #======================================================================
        assert self.crs == self.qproj.crs(), 'crs mismatch!'
        
        
        #check the finv_raw
        assert isinstance(finv_raw, QgsVectorLayer), 'bad type on finv_raw'
        """rasteres are checked below"""
        assert finv_raw.crs() == self.qproj.crs(), 'finv_raw crs %s doesnt match projects \'%s\'' \
            %(finv_raw.crs().authid(), self.qproj.crs().authid())
        assert cid in [field.name() for field in finv_raw.fields()], \
            'requested cid field \'%s\' not found on the finv_raw'%cid
            
        #check the aoi
        if not aoi_vlay is None:
            self.check_aoi(aoi_vlay)

        
        #check the rasters
        rname_l = []
        for rlay in rlayRaw_l:
            assert isinstance(rlay, QgsRasterLayer)
            """allowing conversion now
            assert rlay.crs() == crs, 'rlay %s crs doesnt match project'%(rlay.name())"""
            rname_l.append(rlay.name())
        
        self.rname_l = rname_l
        
        #======================================================================
        # prep the finv for sampling
        #======================================================================
        self.finv_name = finv_raw.name()
        
        #drop all the fields except the cid
        finv = self.deletecolumn(finv_raw, [cid], invert=True)
        
        
        #fix the geometry
        finv = self.fixgeometries(finv, logger=log)
        

        #check field lengths
        self.finv_fcnt = len(finv.fields())
        assert self.finv_fcnt== 1, 'failed to drop all the fields'
        
        self.gtype = QgsWkbTypes().displayString(finv.wkbType())
        
        if self.gtype.endswith('Z'):
            log.warning('passed finv has Z values... these are not supported')
            
        self.feedback.setProgress(20)
        #=======================================================================
        # prep the raster layers------
        #=======================================================================
        raster_l = []
        
        for rlayRaw in rlayRaw_l:
            rlay =  self.prep(rlayRaw, 
                              allow_download=allow_download,
                              aoi_vlay=aoi_vlay,
                             allow_rproj=allow_rproj, clip_rlays=clip_rlays,
                             scaleFactor=scaleFactor)

            raster_l.append(rlay)
        

            
        gc.collect()
        self.feedback.setProgress(40)
        #=======================================================================
        # #inundation runs--------
        #=======================================================================
        if as_inun:
            #===================================================================
            # #prep DTM
            #===================================================================
            if clip_dtm:
                
                """makes the raster clipping a bitcleaner
                
                2020-05-06
                ran 2 tests, and this INCREASED run times by ~20%
                set default to clip_dtm=False
                """
                log.info('trimming dtm \'%s\' by finv extents'%(dtm_rlay.name()))
                finv_buf = self.polygonfromlayerextent(finv,
                                        round_to=dtm_rlay.rasterUnitsPerPixelX()*3,#buffer by 3x the pixel size
                                         logger=log )
        
                
                #clip to just the polygons
                dtm_rlay1 = self.cliprasterwithpolygon(dtm_rlay,finv_buf, logger=log)
            else:
                dtm_rlay1 = dtm_rlay
                
            self.feedback.setProgress(60)
            #===================================================================
            # sample by goetype
            #===================================================================
            if 'Polygon' in self.gtype:
                res_vlay = self.samp_inun(finv,raster_l, dtm_rlay1, dthresh)
            elif 'Line' in self.gtype:
                res_vlay = self.samp_inun_line(finv, raster_l, dtm_rlay1, dthresh)
            else:
                raise Error('bad gtype')
            
            res_name = '%s_%s_%i_%i_d%.2f'%(
                self.fname, self.tag, len(raster_l), res_vlay.dataProvider().featureCount(), dthresh)
        
        #=======================================================================
        # #WSL value sampler------
        #=======================================================================
        else:
            res_vlay = self.samp_vals(finv,raster_l, psmp_stat)
            res_name = '%s_%s_%i_%i'%(self.fname, self.tag, len(raster_l), res_vlay.dataProvider().featureCount())
            
        res_vlay.setName(res_name)
        #=======================================================================
        # wrap
        #=======================================================================
        #max out the progress bar
        self.feedback.setProgress(90)

        log.info('sampling finished')
        
        return res_vlay
    

        
    def prep(self,
             rlayRaw, #set of raw raster to apply prep handles to
             allow_download=False,
             aoi_vlay=None,
             
             allow_rproj=False,
             
             clip_rlays=False,
             
             scaleFactor=1.00,
             ):
        
        log = self.logger.getChild('prep')
        
        log.info('on \'%s\''%rlayRaw.name())

        res_d = dict() #reporting container
        #=======================================================================
        # dataProvider check/conversion-----
        #=======================================================================
        if not rlayRaw.providerType() == 'gdal':
            msg = 'raster \'%s\' providerType = \'%s\' and allow_download=%s' % (
                rlayRaw.name(), rlayRaw.providerType(), allow_download)
            #check if we're allowed to fix
            if not allow_download:
                raise Error(msg)
            log.info(msg)
            #set extents
            if not aoi_vlay is None: #aoi extents in correct CRS
                extent = QgsCoordinateTransform(aoi_vlay.crs(), rlayRaw.crs(), 
                                                self.qproj.transformContext()
                                                ).transformBoundingBox(aoi_vlay.extent())
            else:
                extent = rlayRaw.extent() #layers extents
            #save a local copy
            ofp = self.write_rlay(rlayRaw, extent=extent, 
                newLayerName='%s_gdal' % rlayRaw.name(), 
                logger=log)
            #load this file
            rlayDp = self.load_rlay(ofp, logger=log)
            #check
            assert rlayDp.bandCount() == rlayRaw.bandCount()
            assert rlayDp.providerType() == 'gdal'
            
            res_d['download'] = 'from \'%s\' to \'gdal\''%rlayRaw.providerType()

        else:
            rlayDp = rlayRaw
            log.debug('%s has expected dataProvider \'gdal\''%rlayRaw.name())

        #=======================================================================
        # re-projection--------
        #=======================================================================
        if not rlayDp.crs() == self.qproj.crs():
            msg = 'raster \'%s\' crs = \'%s\' and allow_rproj=%s' % (
                rlayDp.name(), rlayDp.crs(), allow_rproj)
            if not allow_rproj:
                raise Error(msg)
            log.info(msg)
            #save a local copy?
            newName = '%s_%s' % (rlayDp.name(), self.qproj.crs().authid()[5:])
            
            """just write at the end
            if allow_download:
                output = os.path.join(self.out_dir, '%s.tif' % newName)
            else:
                output = 'TEMPORARY_OUTPUT'"""
            output = 'TEMPORARY_OUTPUT'
            #change the projection
            rlayProj = self.warpreproject(rlayDp, crsOut=self.qproj.crs(), 
                output=output, layname=newName)
            
            res_d['rproj'] = 'from %s to %s'%(rlayDp.crs().authid(), self.qproj.crs().authid())

        else:
            log.debug('\'%s\' crs matches project crs: %s'%(rlayDp.name(), rlayDp.crs()))
            rlayProj = rlayDp
            
        #=======================================================================
        # aoi slice----
        #=======================================================================
        if clip_rlays:
            log.debug('trimming raster %s by AOI'%rlayRaw.name())
            log.warning('not Tested!')
            
            #clip to just the polygons
            rlayTrim = self.cliprasterwithpolygon(rlayProj,aoi_vlay, logger=log)
            
            res_d['clip'] = 'with \'%s\''%aoi_vlay.name()
        else:
            rlayTrim = rlayProj
            
        #===================================================================
        # scale
        #===================================================================
        if not float(scaleFactor) ==float(1.00):
            rlayScale = self.raster_mult(rlayTrim, scaleFactor, logger=log)
            
            res_d['scale'] = 'by %.4f'%scaleFactor
        else:
            rlayScale = rlayTrim
            
        #=======================================================================
        # final write
        #=======================================================================
        resLay = rlayScale
        write=False
        if len(res_d)>0: #only where we did some operations
            write=True
        if len(res_d)==1 and 'download' in res_d.keys():
            write=False
            
            
        if write:
            ofp = self.write_rlay(resLay,  
                newLayerName='%s_prepd' % rlayRaw.name(), 
                logger=log)
            
            #use the filestore layer
            resLay = self.load_rlay(ofp, logger=log)

            
        
        
        #=======================================================================
        # wrap
        #=======================================================================
        
        resLay.setName(rlayRaw.name())
        
        log.info('finished w/ %i prep operations on \'%s\' \n    %s'%(
            len(res_d), resLay.name(), res_d))
        
        return rlayScale
    


        
        
    def samp_vals(self, #sample a set of rasters with a vectorlayer
                  finv, raster_l,psmp_stat):
        """
        this is NOT for inundation percent
        can handle all 3 geometries"""
        
        log = self.logger.getChild('samp_vals')
        #=======================================================================
        # build the loop
        #=======================================================================
        gtype=self.gtype
        if 'Polygon' in gtype: 
            assert psmp_stat in self.psmp_codes, 'unrecognized psmp_stat' 
            psmp_code = self.psmp_codes[psmp_stat] #sample each raster
            algo_nm = 'qgis:zonalstatistics'
            
            
        elif 'Point' in gtype:
            algo_nm = 'qgis:rastersampling'
            
        elif 'Line' in gtype:
            algo_nm = 'native:pointsalonglines'
        else:
            raise Error('unsupported gtype: %s'%gtype)

        #=======================================================================
        # sample loop
        #=======================================================================
        names_d = dict()
        
        log.info('sampling %i raster layers w/ algo \'%s\' and gtype: %s'%(
            len(raster_l), algo_nm, gtype))
        
        for indxr, rlay in enumerate(raster_l):
            
            log.info('%i/%i sampling \'%s\' on \'%s\''%(
                indxr+1, len(raster_l), finv.name(), rlay.name()))
            
            ofnl =  [field.name() for field in finv.fields()]
            #===================================================================
            # sample.poly----------
            #===================================================================
            if 'Polygon' in gtype: 
                params_d = {'COLUMN_PREFIX':indxr, 
                            'INPUT_RASTER':rlay, 
                            'INPUT_VECTOR':finv, 
                            'RASTER_BAND':1, 
                            'STATS':[psmp_code]}
                
                
                
                #execute the algo
                res_d = processing.run(algo_nm, params_d, feedback=self.feedback)
                #extract and clean results
                finv = res_d['INPUT_VECTOR']
        
            #=======================================================================
            # sample.Line--------------
            #=======================================================================
            elif 'Line' in gtype: 
                finv = self.line_sample_stats(finv, rlay,[psmp_stat], logger=log)


            #======================================================================
            # sample.Points----------------
            #======================================================================
            elif 'Point' in gtype: 
                #build the algo params
                params_d = { 'COLUMN_PREFIX' : rlay.name(),
                             'INPUT' : finv,
                              'OUTPUT' : 'TEMPORARY_OUTPUT',
                               'RASTERCOPY' : rlay}
                
                #execute the algo
                res_d = processing.run(algo_nm, params_d, feedback=self.feedback)
        
                #extract and clean results
                finv = res_d['OUTPUT']

            else:
                raise Error('unexpected geo type: %s'%gtype)
            
            #===================================================================
            # sample.wrap
            #===================================================================
            assert len(finv.fields()) == self.finv_fcnt + indxr +1, \
                'bad field length on %i'%indxr
                
            finv.setName('%s_%i'%(self.finv_name, indxr))
            
            #===================================================================
            # correct field names
            #===================================================================
            """
            algos don't assign good field names.
            collecting a conversion dictionary then adjusting below
            
            TODO: propagate these field renames to the loaded result layers
            """
            #get/updarte the field names
            nfnl =  [field.name() for field in finv.fields()]
            new_fn = set(nfnl).difference(ofnl) #new field names not in the old
            
            if len(new_fn) > 1:
                raise Error('bad mismatch: %i \n    %s'%(len(new_fn), new_fn))
            elif len(new_fn) == 1:
                names_d[list(new_fn)[0]] = rlay.name()
            else:
                raise Error('bad fn match')
                 
                
            log.debug('sampled %i values on raster \'%s\''%(
                finv.dataProvider().featureCount(), rlay.name()))
            
        self.names_d = names_d #needed by write()
        
        log.info('finished w/ %s'%self.names_d)
        
        return finv
    
    def samp_inun(self, #inundation percent for polygons
                  finv, raster_l, dtm_rlay, dthresh,
                   ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('samp_inun')
        gtype=self.gtype
        
        #setup temp dir
        import tempfile #todo: move this up top
        temp_dir = tempfile.mkdtemp()        
        #=======================================================================
        # precheck
        #=======================================================================
        dp = finv.dataProvider()

        assert isinstance(dtm_rlay, QgsRasterLayer)
        assert isinstance(dthresh, float)
        assert 'Memory' in dp.storageType() #zonal stats makes direct edits
        assert 'Polygon' in gtype

        
        
        #=======================================================================
        # sample loop---------
        #=======================================================================
        """
        too memory intensive to handle writing of all these.
        an advanced user could retrive from the working folder if desiered
        """
        names_d = dict()
        parea_d = dict()
        for indxr, rlay in enumerate(raster_l):
            log = self.logger.getChild('samp_inun.%s'%rlay.name())
            ofnl = [field.name() for field in finv.fields()]


            #===================================================================
            # #get depth raster
            #===================================================================
            log.info('calculating depth raster')

            #using Qgis raster calculator constructor
            dep_rlay = self.raster_subtract(rlay, dtm_rlay, logger=log,
                                            out_dir = os.path.join(temp_dir, 'dep'))
            
            #===================================================================
            # get threshold
            #===================================================================
            #reduce to all values above depththreshold

            log.info('calculating %.2f threshold raster'%dthresh) 
            
            thr_rlay = self.grastercalculator(
                                'A*(A>%.2f)'%dthresh, #null if not above minval
                               {'A':dep_rlay},
                               logger=log,
                               layname= '%s_mv'%dep_rlay.name()
                               )
        
            #===================================================================
            # #get cell counts per polygon
            #===================================================================
            log.info('getting pixel counts on %i polys'%finv.dataProvider().featureCount())
            
            algo_nm = 'qgis:zonalstatistics'
            
            ins_d = {       'COLUMN_PREFIX':indxr, 
                            'INPUT_RASTER':thr_rlay, 
                            'INPUT_VECTOR':finv, 
                            'RASTER_BAND':1, 
                            'STATS':[0],#0: pixel counts, 1: sum
                            }
                
            #execute the algo
            res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
            """this edits the finv in place"""
            
           
            #===================================================================
            # check/correct field names
            #===================================================================
            """
            algos don't assign good field names.
            collecting a conversion dictionary then adjusting below
            """
            #get/updarte the field names
            nfnl =  [field.name() for field in finv.fields()]
            new_fn = set(nfnl).difference(ofnl) #new field names not in the old
            
            if len(new_fn) > 1:
                """
                possible error with Q3.12
                """
                raise Error('zonalstatistics generated more new fields than expected: %i \n    %s'%(len(new_fn), new_fn))
            elif len(new_fn) == 1:
                names_d[list(new_fn)[0]] = rlay.name()
            else:
                raise Error('bad fn match')
            
            
            #===================================================================
            # update pixel size
            #===================================================================
            parea_d[rlay.name()] = rlay.rasterUnitsPerPixelX()*rlay.rasterUnitsPerPixelY()
            
        #=======================================================================
        # area calc-----------
        #=======================================================================
        log = self.logger.getChild('samp_inun')
        log.info('calculating areas on %i results fields:\n    %s'%(len(names_d), list(names_d.keys())))
        
        #add geometry fields
        finv = self.addgeometrycolumns(finv, logger = log)
        
        df_raw  = vlay_get_fdf(finv, logger=log)
        
        df = df_raw.rename(columns=names_d)

        
        #multiply each column by corresponding raster's cell size
        res_df = df.loc[:, names_d.values()].multiply(pd.Series(parea_d)).round(self.prec)
        res_df = res_df.rename(columns={coln:'%s_a'%coln for coln in res_df.columns})
        
        #divide by area of each polygon
        frac_df = res_df.div(df_raw['area'], axis=0).round(self.prec)
        d = {coln:'%s_pct_raw'%coln for coln in frac_df.columns}
        frac_df = frac_df.rename(columns=d)
        res_df = res_df.join(frac_df)#add back in results
        
        #adjust for excessive fractions
        booldf = frac_df>1
        d1 = {coln:'%s_pct'%ename for ename, coln in d.items()}
        if booldf.any().any():
            log.warning('got %i (of %i) pct values >1.00. setting to 1.0 (bad pixel/polygon ratio?)'%(
                booldf.sum().sum(), booldf.size))
            
            fix_df = frac_df.where(~booldf, 1.0)
            fix_df = fix_df.rename(columns=d1)
            res_df = res_df.join(fix_df)
            
        else:
            res_df = res_df.rename(columns=d1)
        
        #add back in all the raw
        res_df = res_df.join(df_raw.rename(columns=names_d))
        
        #set the reuslts converter
        self.names_d = {coln:ename for coln, ename in dict(zip(d1.values(), names_d.values())).items()}
        
        #=======================================================================
        # write working reuslts
        #=======================================================================
        ofp = os.path.join(temp_dir, 'RAW_rsamp_SampInun_%s_%.2f.csv'%(self.tag, dthresh))
        res_df.to_csv(ofp, index=None)
        log.info('wrote working data to \n    %s'%ofp)
        
        #slice to results only
        res_df = res_df.loc[:,[self.cid]+list(d1.values())]
        
        log.info('data assembed w/ %s: \n    %s'%(str(res_df.shape), res_df.columns.tolist()))
        
        """
        view(res_df)
        """
        
        
        #=======================================================================
        # bundle back into vectorlayer
        #=======================================================================
        geo_d = vlay_get_fdata(finv, geo_obj=True, logger=log)
        res_vlay = self.vlay_new_df2(res_df, crs=finv.crs(), geo_d=geo_d, logger=log,
                               layname='%s_%s_inun'%(self.tag, finv.name()))
        
        log.info('finisished w/ %s'%res_vlay.name())

        
        return res_vlay

    def samp_inun_line(self, #inundation percent for polygons
                  finv, raster_l, dtm_rlay, dthresh,
                   ):
        
        """"
        couldn't find a great pre-made algo
        
        option 1:
            SAGA profile from lines (does not retain line attributes)
            join attributes by nearest (to retrieve XID)
            
        option 2:
            Generate points (pixel centroids) along line 
                (does not retain line attributes)
                generates points on null pixel values
            sample points
            join by nearest
            
        option 3:
            add geometry attributes
            Points along geometry (retains attribute)
            sample raster
            count those above threshold
            divide by total for each line
            get % above threshold for each line
            get km inundated for each line
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('samp_inun_line')
        gtype=self.gtype
        
        #setup temp dir
        import tempfile #todo: move this up top
        temp_dir = tempfile.mkdtemp()        
        #=======================================================================
        # precheck
        #=======================================================================
        dp = finv.dataProvider()

        assert isinstance(dtm_rlay, QgsRasterLayer)
        assert isinstance(dthresh, float), 'expected float for dthresh. got %s'%type(dthresh)
        assert 'Memory' in dp.storageType() #zonal stats makes direct edits
        assert 'Line' in gtype

        #=======================================================================
        # sample loop---------
        #=======================================================================
        """
        too memory intensive to handle writing of all these.
        an advanced user could retrive from the working folder if desiered
        """
        names_d = dict()

        for indxr, rlay in enumerate(raster_l):
            log = self.logger.getChild('samp_inun.%s'%rlay.name())
            ofnl = [field.name() for field in finv.fields()]


            #===================================================================
            # #get depth raster
            #===================================================================
            log.info('calculating depth raster')

            #using Qgis raster calculator constructor
            dep_rlay = self.raster_subtract(rlay, dtm_rlay, logger=log,
                                            out_dir = os.path.join(temp_dir, 'dep'))
            
            #===============================================================
            # #convert to points
            #===============================================================
            params_d = { 'DISTANCE' : dep_rlay.rasterUnitsPerPixelX(), 
                        'END_OFFSET' : 0, 
                        'INPUT' : finv, 
                        'OUTPUT' : 'TEMPORARY_OUTPUT', 
                        'START_OFFSET' : 0 }
            
    
            res_d = processing.run('native:pointsalonglines', params_d, feedback=self.feedback)
            fpts_vlay = res_d['OUTPUT']
            
            #===============================================================
            # #sample the raster
            #===============================================================
            ofnl2 = [field.name() for field in fpts_vlay.fields()]
            params_d = { 'COLUMN_PREFIX' : rlay.name(),
                         'INPUT' : fpts_vlay,
                          'OUTPUT' : 'TEMPORARY_OUTPUT',
                           'RASTERCOPY' : dep_rlay}
            
            res_d = processing.run('qgis:rastersampling', params_d, feedback=self.feedback)
            fpts_vlay = res_d['OUTPUT']

            #get new field name
            new_fn = set([field.name() for field in fpts_vlay.fields()]).difference(ofnl2) #new field names not in the old
            
            assert len(new_fn)==1
            new_fn = list(new_fn)[0]
            
            #===================================================================
            # clean/pull data
            #===================================================================
            #drop all the other fields
            fpts_vlay = self.deletecolumn(fpts_vlay,[new_fn, self.cid], invert=True, logger=log )
            
            #pull data
            """
            the builtin statistics algo doesn't do a good job handling nulls
            """
            pts_df = vlay_get_fdf(fpts_vlay, logger=log)
            
            #===================================================================
            # calc stats
            #===================================================================
            #set those below threshold to null
            boolidx = pts_df[new_fn]<=dthresh
            
            pts_df.loc[boolidx, new_fn] = np.nan
            log.debug('set %i (of %i) \'%s\' vals <= %.2f to null'%(
                boolidx.sum(), len(boolidx), new_fn, dthresh))
            """
            view(pts_df)
            (pts_df[self.cid]==4).sum()
            """
            #get count of REAL values in each xid group
            pts_df['all']=1 #add dummy column for the demoninator
            sdf = pts_df.groupby(self.cid).count().reset_index(drop=False).rename(
                columns={new_fn:'real'})
            
            #get ratio (non-NAN count / all count)
            new_fn = rlay.name()
            sdf[new_fn] = sdf['real'].divide(sdf['all']).round(self.prec)
            
            assert sdf[new_fn].max() <=1
            #===================================================================
            # link in result
            #===================================================================
            #convert df back to a mlay
            pstat_vlay = self.vlay_new_df2(sdf.drop(['all', 'real'], axis=1),
                                            layname='%s_stats'%(finv.name()), logger=log)

            
            #join w/ algo
            params_d = { 'DISCARD_NONMATCHING' : False,
                         'FIELD' : self.cid, 
                         'FIELDS_TO_COPY' : [new_fn],
                         'FIELD_2' : self.cid,
                          'INPUT' : finv,
                          'INPUT_2' : pstat_vlay,
                         'METHOD' : 1, #Take attributes of the first matching feature only (one-to-one)
                          'OUTPUT' : 'TEMPORARY_OUTPUT',
                           'PREFIX' : ''}
            
            res_d = processing.run('native:joinattributestable', params_d, feedback=self.feedback)
            finv = res_d['OUTPUT']

            #===================================================================
            # check/correct field names
            #===================================================================
            """
            algos don't assign good field names.
            collecting a conversion dictionary then adjusting below
            """
            #get/updarte the field names
            nfnl =  [field.name() for field in finv.fields()]
            new_fn = set(nfnl).difference(ofnl) #new field names not in the old
            
            if len(new_fn) > 1:
                raise Error('unexpected algo behavior... bad new field count: %s'%new_fn)
            elif len(new_fn) == 1:
                names_d[list(new_fn)[0]] = rlay.name()
                log.debug('updated names_d w/ %s'%rlay.name())
            else:
                raise Error('bad fn match')
        #=======================================================================
        # wrap-------------
        #=======================================================================
        self.names_d = dict() #names should be fine
        log.debug('finished')
        """
        view(finv)
        """

        return finv
    
    def raster_subtract(self, #performs raster calculator rlayBig - rlaySmall
                        rlayBig, rlaySmall,
                        out_dir = None,
                        layname = None,
                        logger = None,
                        ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger =  self.logger
        log = self.logger.getChild('raster_subtract')
        
        if out_dir is None:
            out_dir = os.environ['TEMP']
            
        if layname is None:
            layname = '%s_dep'%rlayBig.name()
        
        #=======================================================================
        # assemble the entries
        #=======================================================================
        entries_d = dict() 

        for tag, rlay in {'Big':rlayBig, 'Small':rlaySmall}.items():
            rcentry = QgsRasterCalculatorEntry()
            rcentry.raster=rlay
            rcentry.ref = '%s@1'%tag
            rcentry.bandNumber=1
            entries_d[tag] = rcentry

            
        #=======================================================================
        # assemble parameters
        #=======================================================================
        formula = '%s - %s'%(entries_d['Big'].ref, entries_d['Small'].ref)
        outputFile = os.path.join(out_dir, '%s.tif'%layname)
        outputExtent  = rlayBig.extent()
        outputFormat = 'GTiff'
        nOutputColumns = rlayBig.width()
        nOutputRows = rlayBig.height()
        rasterEntries =list(entries_d.values())
        

        #=======================================================================
        # precheck
        #=======================================================================
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
        if os.path.exists(outputFile):
            msg = 'requseted outputFile exists: %s'%outputFile
            if self.overwrite:
                log.warning(msg)
                os.remove(outputFile)
            else:
                raise Error(msg)
            
            
        assert not os.path.exists(outputFile), 'requested outputFile already exists! \n    %s'%outputFile
        
        #=======================================================================
        # execute
        #=======================================================================
        """throwing depreciation warning"""
        rcalc = QgsRasterCalculator(formula, outputFile, outputFormat, outputExtent,
                            nOutputColumns, nOutputRows, rasterEntries)
        
        result = rcalc.processCalculation(feedback=self.feedback)
        
        #=======================================================================
        # check    
        #=======================================================================
        if not result == 0:
            raise Error(rcalc.lastError())
        
        assert os.path.exists(outputFile)
        
        
        log.info('saved result to: \n    %s'%outputFile)
            
        #=======================================================================
        # retrieve result
        #=======================================================================
        rlay = QgsRasterLayer(outputFile, layname)
        
        return rlay
    
    def raster_mult(self, #performs raster calculator rlayBig - rlaySmall
                        rlayRaw,
                        scaleFactor,
                        out_dir = None,
                        layname = None,
                        logger = None,
                        ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger =  self.logger
        log = self.logger.getChild('raster_mult')
        
        if out_dir is None:
            out_dir = os.environ['TEMP']
            
        if layname is None:
            layname = '%s_scaled'%rlayRaw.name()
        
        #=======================================================================
        # assemble the entries
        #=======================================================================
        entries_d = dict() 

        for tag, rlay in {'rlayRaw':rlayRaw}.items():
            rcentry = QgsRasterCalculatorEntry()
            rcentry.raster=rlay
            rcentry.ref = '%s@1'%tag
            rcentry.bandNumber=1
            entries_d[tag] = rcentry

            
        #=======================================================================
        # assemble parameters
        #=======================================================================
        formula = '%s * %.2f'%(entries_d['rlayRaw'].ref, scaleFactor)
        outputFile = os.path.join(out_dir, '%s.tif'%layname)
        outputExtent  = rlayRaw.extent()
        outputFormat = 'GTiff'
        nOutputColumns = rlayRaw.width()
        nOutputRows = rlayRaw.height()
        rasterEntries =list(entries_d.values())
        

        #=======================================================================
        # precheck
        #=======================================================================
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            
        if os.path.exists(outputFile):
            msg = 'requseted outputFile exists: %s'%outputFile
            if self.overwrite:
                log.warning(msg)
                os.remove(outputFile)
            else:
                raise Error(msg)
            
            
        assert not os.path.exists(outputFile), 'requested outputFile already exists! \n    %s'%outputFile
        
        #=======================================================================
        # execute
        #=======================================================================
        """throwing depreciation warning"""
        rcalc = QgsRasterCalculator(formula, outputFile, outputFormat, outputExtent,
                            nOutputColumns, nOutputRows, rasterEntries)
        
        result = rcalc.processCalculation(feedback=self.feedback)
        
        #=======================================================================
        # check    
        #=======================================================================
        if not result == 0:
            raise Error(rcalc.lastError())
        
        assert os.path.exists(outputFile)
        
        
        log.info('saved result to: \n    %s'%outputFile)
            
        #=======================================================================
        # retrieve result
        #=======================================================================
        rlay = QgsRasterLayer(outputFile, layname)
        
        return rlay
        
        

    def dtm_check(self, vlay):
        
        log = self.logger.getChild('dtm_check')
        
        df = vlay_get_fdf(vlay)
        
        boolidx = df.isna()
        if boolidx.any().any():
            log.error('got some nulls')
        
        log.info('passed checks')
        
        #======================================================================
        # #check results
        #======================================================================
        #check results cid column matches set in finv
        
        #make sure there are no negative values
        
        #report on number of nulls
        
    def line_sample_stats(self, #get raster stats using a line
                    line_vlay, #line vectorylayer with geometry to sample from
                    rlay, #raster to sample
                    sample_stats, #list of stats to sample
                    logger=None,
                    ):
        """
        sampliung a raster layer with a line and a statistic
        """
        if logger is None: logger=self.logger
        log=logger.getChild('line_sample_stats')
        log.debug('on %s'%(line_vlay.name()))
        
        #drop everythin gto lower case
        sample_stats = [e.lower() for e in sample_stats]
        #===============================================================
        # #convert to points
        #===============================================================
        params_d = { 'DISTANCE' : rlay.rasterUnitsPerPixelX(), 
                    'END_OFFSET' : 0, 
                    'INPUT' : line_vlay, 
                    'OUTPUT' : 'TEMPORARY_OUTPUT', 
                    'START_OFFSET' : 0 }
        

        res_d = processing.run('native:pointsalonglines', params_d, feedback=self.feedback)
        fpts_vlay = res_d['OUTPUT']
        
        #===============================================================
        # #sample the raster
        #===============================================================
        ofnl2 = [field.name() for field in fpts_vlay.fields()]
        params_d = { 'COLUMN_PREFIX' : rlay.name(),
                     'INPUT' : fpts_vlay,
                      'OUTPUT' : 'TEMPORARY_OUTPUT',
                       'RASTERCOPY' : rlay}
        

        res_d = processing.run('qgis:rastersampling', params_d, feedback=self.feedback)
        fpts_vlay = res_d['OUTPUT']
        """
        view(fpts_vlay)
        """
        #get new field name
        new_fn = set([field.name() for field in fpts_vlay.fields()]).difference(ofnl2) #new field names not in the old
        
        assert len(new_fn)==1
        new_fn = list(new_fn)[0]
        
        #===============================================================
        # get stats
        #===============================================================
        """note this does not return xid values where everything sampled as null"""
        params_d = { 'CATEGORIES_FIELD_NAME' : [self.cid], 
                    'INPUT' : fpts_vlay,
                    'OUTPUT' : 'TEMPORARY_OUTPUT', 
                    'VALUES_FIELD_NAME' :new_fn}
        
        res_d = processing.run('qgis:statisticsbycategories', params_d, feedback=self.feedback)
        stat_tbl = res_d['OUTPUT']
        
        #===============================================================
        # join stats back to line_vlay
        #===============================================================
        #check that the sample stat is in there
        s = set(sample_stats).difference([field.name() for field in stat_tbl.fields()])
        assert len(s)==0, 'requested sample statistics \"%s\' failed to generate'%s 
        
        #run algo
        params_d = { 'DISCARD_NONMATCHING' : False,
                     'FIELD' : self.cid, 
                     'FIELDS_TO_COPY' : sample_stats,
                     'FIELD_2' : self.cid,
                      'INPUT' : line_vlay,
                      'INPUT_2' : stat_tbl,
                     'METHOD' : 1, #Take attributes of the first matching feature only (one-to-one)
                      'OUTPUT' : 'TEMPORARY_OUTPUT',
                       'PREFIX' : line_vlay }
        
        res_d = processing.run('native:joinattributestable', params_d, feedback=self.feedback)
        line_vlay = res_d['OUTPUT']
        
        """
        view(line_vlay)
        """
                
                

        return line_vlay
        
    def check(self):
        pass
        
    def write_res(self, #save expos dataset to file
                  vlay,
              out_dir = None, #directory for puts
              names_d = None, #names conversion
              rname_l = None,
              ):
        
        log = self.logger.getChild('write_res')
        #======================================================================
        # defaults
        #======================================================================
        if names_d is None: names_d = self.names_d
        if rname_l is None: rname_l = self.rname_l
        if out_dir is None: out_dir = self.out_dir
        res_name = vlay.name()
        log.debug("on \'%s\'"%res_name)
        #======================================================================
        # prechekss
        #======================================================================
        assert os.path.exists(out_dir), 'bad out_dir'
        #======================================================================
        # write data
        #======================================================================
        #extract data
        df = vlay_get_fdf(vlay)
        
        #rename
        if len(names_d) > 0:
            df = df.rename(columns=names_d)
            log.info('renaming columns: \n    names_d: %s \n    df.cols:%s'%(
                names_d, df.columns.tolist()))
            

        #check the raster names
        miss_l = set(rname_l).difference(df.columns.to_list())
        if len(miss_l)>0:
            log.warning('failed to map %i raster layer names onto results: \n    %s'%(len(miss_l), miss_l))
        
        
        out_fp = self.output_df(df, '%s.csv'%res_name, out_dir = out_dir, write_index=False)
        
        self.out_fp = out_fp
        
        return 


    def upd_cf(self, cf_fp): #configured control file updater
        """make sure you write the file first"""
        return self.update_cf(
            {
            'dmg_fps':(
                {'expos':self.out_fp}, 
                '#\'expos\' file path set from rsamp.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                ),
            'parameters':(
                {'as_inun':str(self.as_inun)},
                )
             },
            cf_fp = cf_fp
            )


    


    
    
    

    

            
        