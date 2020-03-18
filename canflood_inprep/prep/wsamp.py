'''
Created on Feb. 9, 2020

@author: cefect
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
class Rsamp(Qcoms):
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

    
    
    def __init__(self,
                 fname='expos', #prefix for file name
                  *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.fname=fname
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
            rlayer = self.load_rlay(fp)
            
            #add it in
            basefn = os.path.splitext(os.path.split(fp)[1])[0]
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
            as_inun=False, #whether to sample for inundation (rather than wsl values)
            cid = None, #index field name on finv
            crs = None,
            
            #exposure value controls
            psmp_stat='Max', #for polygon finvs, statistic to sample
            
            #inundation sampling controls
            dtm_rlay=None, #dtm raster
            dthresh = 0, #fordepth threshold
            
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
        self.finv_name = finv_raw.name()
        
        #drop all the fields except the cid
        finv = self.deletecolumn(finv_raw, [cid], invert=True)
        
        #check field lengths
        self.finv_fcnt = len(finv.fields())
        assert self.finv_fcnt== 1, 'failed to drop all the fields'
        
        self.gtype = QgsWkbTypes().displayString(finv.wkbType())
        #=======================================================================
        # exercute
        #=======================================================================
        if as_inun:
            res_vlay = self.samp_inun(finv,raster_l, dtm_rlay, dthresh)
        else:
            res_vlay = self.samp_vals(finv,raster_l, psmp_stat)
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('sampling finished')
        
        res_name = '%s_%s_%i_%i'%(self.fname, self.tag, len(raster_l), res_vlay.dataProvider().featureCount())
        
        res_vlay.setName(res_name)
            
        return res_vlay
        
    def samp_vals(self, finv, raster_l,psmp_stat):
        
        log = self.logger.getChild('samp_vals')
        #=======================================================================
        # prep the loop
        #=======================================================================
        gtype=self.gtype
        if 'Polygon' in gtype: 
            assert psmp_stat in self.psmp_codes, 'unrecognized psmp_stat' 
            psmp_code = self.psmp_codes[psmp_stat] #sample each raster
            algo_nm = 'qgis:zonalstatistics'
            
            
        elif 'Point' in gtype:
            algo_nm = 'qgis:rastersampling'


        
        #=======================================================================
        # sample loop
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
            assert len(finv.fields()) == self.finv_fcnt + indxr +1, \
                'bad field length on %i'%indxr
                
            finv.setName('%s_%i'%(self.finv_name, indxr))
            
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
            
        self.names_d = names_d #needed by write()

        
        return finv
    
    def samp_inun(self,finv, raster_l, dtmlay_raw, dthresh,
                   ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('samp_inun')
        gtype=self.gtype
        
        master_od = self.out_dir
        self.out_dir = os.path.join(master_od, 'inun')
        
        #clear the working directory
        """neded for SAGA algo workaround"""
        if os.path.exists(self.out_dir):
            log.warning('specified out_dir exists. clearing contents')
            try:
                shutil.rmtree(self.out_dir)
            except Exception as e:
                raise Error('failed to clear working directory. remove layers from workspace? \n    %s'%e)
        os.makedirs(self.out_dir)
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert 'Polygon' in gtype
        assert isinstance(dtmlay_raw, QgsRasterLayer)
        assert isinstance(dthresh, float)
        
        #=======================================================================
        # setup the dtm------
        #=======================================================================
        log.info('trimming dtm raster')
        #add a buffer and dissolve
        """makes the raster clipping a bitcleaner and faster"""
        finv_buf = self.buffer(finv,
                                dtmlay_raw.rasterUnitsPerPixelX()*3,#buffer by 3x the pixel size
                                 dissolve=True, logger=log )
        
        #clip to just the polygons
        dtm_rlay = self.cliprasterwithpolygon(dtmlay_raw,finv_buf, logger=log)
        
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


            #get depth raster
            self.out_dir = os.path.join(master_od, 'inun', 'dep')
            log.info('calculating depth raster')
            dep_rlay = self.srastercalculator('a-b',
                               {'a':rlay, 'b':dtm_rlay},
                               logger=log,
                               layname= '%s_dep'%rlay.name(),
                               )
            
            #reduce to all values above depththreshold
            self.out_dir = os.path.join(master_od, 'inun', 'dthresh')
            log.info('calculating %.2f threshold raster'%dthresh) 
            thr_rlay = self.srastercalculator(
                                'ifelse(a>%.1f,1,0/0)'%dthresh, #null if not above minval
                               {'a':dep_rlay},
                               logger=log,
                               layname= '%s_mv'%dep_rlay.name()
                               )
        
            #get cell size of raster
            
            #===================================================================
            # #get cell counts per polygon
            #===================================================================
            log.info('getting pixel counts on %i polys'%finv.dataProvider().featureCount())
            algo_nm = 'qgis:zonalstatistics'
            ins_d = {       'COLUMN_PREFIX':indxr, 
                            'INPUT_RASTER':thr_rlay, 
                            'INPUT_VECTOR':finv, 
                            'RASTER_BAND':1, 
                            'STATS':[1],#0: pixel counts, 1: sum
                            }
                
            #execute the algo
            res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
            #extract and clean results
            finv = res_d['INPUT_VECTOR']
            
            #===================================================================
            # update pixel size
            #===================================================================
            parea_d[rlay.name()] = rlay.rasterUnitsPerPixelX()*rlay.rasterUnitsPerPixelY()
            
            
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
            
        #=======================================================================
        # area calc-----------
        #=======================================================================
        log = self.logger.getChild('samp_inun')
        self.out_dir = os.path.join(master_od, 'inun')
        log.info('calculating areas on %i results fields:\n    %s'%(len(names_d), list(names_d.keys())))
        
        #add geometry fields
        finv = self.addgeometrycolumns(finv, logger = log)
        
        df_raw  = vlay_get_fdf(finv, logger=log)
        
        df = df_raw.rename(columns=names_d)

        self.names_d

        
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
        ofp = os.path.join(self.out_dir, 'res_df.csv')
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
        res_vlay = vlay_new_df(res_df, finv.crs(), geo_d=geo_d, logger=log,
                               layname='%s_inun'%finv.name())
        
        log.info('finisished w/ %s'%res_vlay.name())
        self.out_dir = master_od
        
        return res_vlay
        

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
     
    raster_fns = ['haz_1000yr_cT2.tif', 
                  #'haz_1000yr_fail_cT2.tif', 
                  #'haz_100yr_cT2.tif', 
                  #'haz_200yr_cT2.tif',
                  'haz_50yr_cT2.tif',
                  ]
    
    
      
    finv_fp = os.path.join(data_dir, 'finv_polys_t3.gpkg')
     
    cf_fp = os.path.join(data_dir, 'CanFlood_control_01.txt')
    
    #inundation sampling
    dtm_fp = os.path.join(data_dir, 'dtm_cT1.tif')
    as_inun=True
    dthresh = 0.5
    
    cid='zid'
    tag='tut3'
    
    
    out_dir = os.path.join(os.getcwd(), 'wsamp', tag)
    raster_fps = [os.path.join(data_dir, fn) for fn in raster_fns]
    #==========================================================================
    # load the data
    #==========================================================================
    wrkr = Rsamp(logger=mod_logger, tag=tag, out_dir=out_dir, cid=cid)
    wrkr.ini_standalone()
    
    
    rlay_l, finv_vlay = wrkr.load_layers(raster_fps, finv_fp)
    
    if not dtm_fp is None:
        dtm_rlay = wrkr.load_rlay(dtm_fp)
    else:
        dtm_rlay = None
    
    #==========================================================================
    # execute
    #==========================================================================
    res_vlay = wrkr.run(rlay_l, finv_vlay, 
             crs = finv_vlay.crs(), 
             as_inun=as_inun, dtm_rlay=dtm_rlay,dthresh=dthresh,
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
    
    
    

    

            
        