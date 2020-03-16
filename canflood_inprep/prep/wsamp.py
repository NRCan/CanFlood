'''
Created on Feb. 9, 2020

@author: cefect
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd


#Qgis imports
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject

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
    

from hlpr.Q import *
from hlpr.basic import *

#==============================================================================
# functions-------------------
#==============================================================================
class WSLSampler(Qcoms):
    """
    sampling hazard rasters from the inventory
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

    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        #flip the codes
        self.psmp_codes = dict(zip(self.psmp_codes.values(), self.psmp_codes.keys()))

                
    def load_layers(self, #load data to project (for console runs)
                    rfp_l, finv_fp,
                    providerLib='ogr'
                    ):
        
        """
        special input loader for standalone runs
        Im assuming for the plugin these layers will be loaded already"""
        log = self.logger.getChild('load_layers')
        #======================================================================
        # load rasters
        #======================================================================
        raster_d = dict()
        
        for fp in rfp_l:
            assert os.path.exists(fp), 'requested file does not exist: %s'%fp
            assert QgsRasterLayer.isValidRasterFileName(fp),  \
                'requested file is not a valid raster file type: %s'%fp
            
            basefn = os.path.splitext(os.path.split(fp)[1])[0]
            

            #Import a Raster Layer
            rlayer = QgsRasterLayer(fp, basefn)
            if not rlayer.isValid():
                print("Layer failed to load!")
            
            
            #===========================================================================
            # checks
            #===========================================================================
            if not isinstance(rlayer, QgsRasterLayer): 
                raise IOError
            

            #add it to the store
            self.mstore.addMapLayer(rlayer)
            
            log.info('loaded \'%s\' from file: %s'%(rlayer.name(), fp))
            
            #add it in
            raster_d[basefn] = rlayer
            
        #======================================================================
        # load finv vector layer
        #======================================================================
        fp = finv_fp
        basefn = os.path.splitext(os.path.split(fp)[1])[0]
        vlay_raw = QgsVectorLayer(fp,basefn,providerLib)
        
        
        

        # checks
        if not isinstance(vlay_raw, QgsVectorLayer): 
            raise IOError
        
        #check if this is valid
        if not vlay_raw.isValid():
            log.error('loaded vlay \'%s\' is not valid. \n \n did you initilize?'%vlay_raw.name())
            raise Error('vlay loading produced an invalid layer')
        
        #check if it has geometry
        if vlay_raw.wkbType() == 100:
            log.error('loaded vlay has NoGeometry')
            raise Error('no geo')
        
        
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
            raster_l, #set of rasters to sample 
            finv_raw, #inventory layer
            cid = None, #index field name on finv
            crs = None,
            fname='expos', #prefix for file name
            psmp_stat='Max', #for polygon finvs, statistic to sample
            
            ):
        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        if cid is None: cid = self.cid
        if crs is None: crs = self.crs

        
        log.info('executing on %i rasters'%len(raster_l))
        #======================================================================
        # #check the data
        #======================================================================
        assert isinstance(crs, QgsCoordinateReferenceSystem)
        
        #check the finv_raw
        assert isinstance(finv_raw, QgsVectorLayer), 'bad type on finv_raw'
        assert finv_raw.crs() == crs, 'finv_raw crs doesnt match project'
        assert cid in [field.name() for field in finv_raw.fields()], \
            'requested cid field \'%s\' not found on the finv_raw'%cid
        
        
        #check the rasters
        rname_l = []
        for rlay in raster_l:
            assert isinstance(rlay, QgsRasterLayer)
            assert rlay.crs() == crs, 'rlay %s crs doesnt match project'%(rlay.name())
            rname_l.append(rlay.name())
        
        self.rname_l = rname_l
        #======================================================================
        # prep the finv_raw
        #======================================================================
        finv_name = finv_raw.name()
        
        #drop all the fields except the cid
        finv = self.deletecolumn(finv_raw, [cid], invert=True)
        
        #check field lengths
        finv_fcnt = len(finv.fields())
        assert finv_fcnt== 1, 'failed to drop all the fields'
        
        #=======================================================================
        # prep the loop
        #=======================================================================
        gtype = QgsWkbTypes().displayString(finv.wkbType())
        if 'Polygon' in gtype: 
            assert psmp_stat in self.psmp_codes, 'unrecognized psmp_stat' 
            psmp_code = self.psmp_codes[psmp_stat] #sample each raster
            algo_nm = 'qgis:zonalstatistics'
            
            
        elif 'Point' in gtype:
            algo_nm = 'qgis:rastersampling'


        
        #=======================================================================
        # sample loop-------
        #=======================================================================
        
        names_d = dict()
        
        log.info('sampling %i raster layers w/ algo \'%s\' and gtype: %s'%(len(raster_l), algo_nm, gtype))
        for indxr, rlay in enumerate(raster_l):
            
            log.info('    %i/%i sampling \'%s\' on \'%s\''%(indxr+1, len(raster_l), finv.name(), rlay.name()))
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
                raise Error('not implemented')
            
                #ask for sample type (min/max/mean)
                
                #sample each raster
        
                
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
            assert len(finv.fields()) == finv_fcnt + indxr +1, \
                'bad field length on %i'%indxr
                
            finv.setName('%s_%i'%(finv_name, indxr))
            
            #===================================================================
            # correct field names
            #===================================================================
            """
            algos don't assign good field names.
            collecting a conversion dictionary then adjusting below
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
            
        

        log.info('sampling finished')
        
        res_name = '%s_%s_%i_%i'%(fname, self.tag, len(raster_l), finv.dataProvider().featureCount())
        
        finv.setName(res_name)
        
        self.names_d = names_d #needed by write()

        
        return finv
    

    

    
    
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
        
    def check(self):
        pass
        
    def write_res(self, 
                  vlay,
              out_dir = None, #directory for puts
              names_d = None, #names conversion
              rname_l = None,
              ):
        
        log = self.logger.getChild('run')
        #======================================================================
        # defaults
        #======================================================================
        if names_d is None: names_d = self.names_d
        if rname_l is None: rname_l = self.rname_l
        if out_dir is None: out_dir = self.out_dir
        res_name = vlay.name()
        
        #======================================================================
        # prechekss
        #======================================================================
        assert os.path.exists(out_dir), 'bad out_dir'
        #======================================================================
        # write data----------------
        #======================================================================
        #extract data
        df = vlay_get_fdf(vlay)
        
        #rename
        if len(names_d) > 0:
            df = df.rename(columns=names_d)
            log.info('renaming columns: %s'%names_d)
            
        
        
        #check the raster names
        miss_l = set(rname_l).difference(df.columns.to_list())
        if len(miss_l)>0:
            raise Error('failed to map %i raster layer names onto results: \n    %s'%(len(miss_l), miss_l))
        
        
        out_fp = self.output_df(df, '%s.csv'%res_name, out_dir = out_dir, write_index=False)
        
        self.out_fp = out_fp
        
        return 


    def upd_cf(self, cf_fp): #configured control file updater
        return self.update_cf(
            {'dmg_fps':(
                {'expos':self.out_fp}, 
                '#\'expos\' file path set from wsamp.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                )
             },
            cf_fp = cf_fp
            )

if __name__ =="__main__": 
    write_vlay=True
    #===========================================================================
    # tutorial 1 (points)
    #===========================================================================
    #===========================================================================
    # data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\1\data'
    # 
    # raster_fns = ['haz_1000yr_cT2.tif', 'haz_1000yr_fail_cT2.tif', 'haz_100yr_cT2.tif', 
    #               'haz_200yr_cT2.tif','haz_50yr_cT2.tif']
    # 
    # 
    # 
    # finv_fp = os.path.join(data_dir, 'finv_cT2b.gpkg')
    # 
    # cf_fp = os.path.join(data_dir, 'CanFlood_control_01.txt')
    # 
    # 
    # cid='xid'
    # tag='tut1'
    #===========================================================================
    
    #==========================================================================
    # tutorial 3 (polygons)
    #==========================================================================
    data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\3\data'
     
    raster_fns = ['haz_1000yr_cT2.tif', 'haz_1000yr_fail_cT2.tif', 'haz_100yr_cT2.tif', 
                  'haz_200yr_cT2.tif','haz_50yr_cT2.tif']
     
     
     
    finv_fp = os.path.join(data_dir, r'finv_polys_t3.gpkg')
     
    cf_fp = os.path.join(data_dir, 'CanFlood_control_01.txt')
     
     
    cid='zid'
    tag='tut3'
    
    
    out_dir = os.path.join(os.getcwd(), 'wsamp', tag)
    raster_fps = [os.path.join(data_dir, fn) for fn in raster_fns]
    #==========================================================================
    # load the data
    #==========================================================================
    wrkr = WSLSampler(logger=mod_logger, tag=tag, out_dir=out_dir)
    wrkr.ini_standalone()
    
    
    rlay_l, finv_vlay = wrkr.load_layers(raster_fps, finv_fp)
    
    
    #==========================================================================
    # execute
    #==========================================================================
    res_vlay = wrkr.run(rlay_l, finv_vlay, 
             cid=cid,
             crs = finv_vlay.crs(),
             )
       
    wrkr.check()
    
    #==========================================================================
    # save results
    #==========================================================================
    outfp = wrkr.write_res(res_vlay)
    if write_vlay:
        ofp = os.path.join(out_dir, res_vlay.name()+'.gpkg')
        vlay_write(res_vlay,ofp, overwrite=True)
    
    wrkr.upd_cf(cf_fp)

    force_open_dir(out_dir)

    print('finished')
    
    
    

    

            
        