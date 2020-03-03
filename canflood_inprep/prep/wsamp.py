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
    
from hlpr.Q import Qcoms as base_class
    

from hlpr.Q import *
from hlpr.basic import *

#==============================================================================
# functions-------------------
#==============================================================================
class WSLSampler(base_class):
    out_fp = None
    names_d = None
    rname_l =None
    
    def __init__(self,
                 logger, tag='test',
                 ):
        

        logger.info('simple wrapper inits')

        #=======================================================================
        # attach inputs
        #=======================================================================
        self.logger = logger.getChild('Qsimp')
        self.tag = tag

        self.logger.info('init finished')
        
        return
        
    def ini_base(self):
        super().__init__() #initilzie teh baseclass
                
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
        
        #======================================================================
        # sample-----------------
        #======================================================================
        gtype = QgsWkbTypes().displayString(finv.wkbType())
        names_d = dict()
        if 'Polygon' in gtype: 
            
            """TODO:
            #ask for sample type (min/max/mean)
            
            does this do lines also?
            """
            
            #sample each raster
            
            algo_nm = 'qgis:zonalstatistics'
            
            log.info('sampling %i raster layers'%len(raster_l))
            
            #loop and sample each raster on these points
            
            for indxr, rlay in enumerate(raster_l):
                
    
                log.info('    %i/%i sampling \'%s\' on \'%s\''%(indxr+1, len(raster_l), finv.name(), rlay.name()))
            
                #build the algo params
                params_d = {'COLUMN_PREFIX' : rlay.name(),
                            'INPUT_RASTER' : rlay,
                            'INPUT_VECTOR' : finv,
                            'RASTER_BAND' : 1,
                            'STATS' : [2]}
                
                #execute the algo
                res_d = processing.run(algo_nm, params_d, feedback=self.feedback)
            
                #extract and clean results
                finv = res_d['INPUT_VECTOR']
                print(finv)
                #finv = processing.getObject(res_d['OUTPUT'])
                finv.setName('%s_%i'%(finv_name, indxr))
                
                assert len(finv.fields()) == finv_fcnt + indxr +1, \
                    'bad field length on %i'%indxr
                    
                log.debug('sampled %i values on raster \'%s\''%(
                    finv.dataProvider().featureCount(), rlay.name()))
                
                
            
        elif 'Line' in gtype: 
            raise Error('not implemented')
        
            #ask for sample type (min/max/mean)
            
            #sample each raster
    
            
        #======================================================================
        # sample.points
        #======================================================================
        elif 'Point' in gtype: 
            algo_nm = 'qgis:rastersampling'
            
            log.info('sampling %i raster layers'%len(raster_l))
            
            #loop and sample each raster on these points
            names_d = dict()
            for indxr, rlay in enumerate(raster_l):
                
                ofnl =  [field.name() for field in finv.fields()]
    
                log.info('    %i/%i sampling \'%s\' on \'%s\''%(indxr+1, len(raster_l), finv.name(), rlay.name()))
            
                #build the algo params
                params_d = { 'COLUMN_PREFIX' : rlay.name(),
                             'INPUT' : finv,
                              'OUTPUT' : 'TEMPORARY_OUTPUT',
                               'RASTERCOPY' : rlay}
                
                #execute the algo
                res_d = processing.run(algo_nm, params_d, feedback=self.feedback)
        
                #extract and clean results
                finv = res_d['OUTPUT']
                finv.setName('%s_%i'%(finv_name, indxr))
                
                assert len(finv.fields()) == finv_fcnt + indxr +1, \
                    'bad field length on %i'%indxr
                    
                """this is adding a suffix onto the names... need to clean below
                if not rlay.name() in [field.name() for field in finv.fields()]:
                    raise Error('rlay name \'%s\' failed to get set'%rlay.name())"""
                    
                #get/updarte the field names
                nfnl =  [field.name() for field in finv.fields()]
                new_fn = set(nfnl).difference(ofnl) #new field names not in the old
                
                if len(new_fn) > 1:
                    raise Error('bad mismatch: %i \n    %s'%(len(new_fn), new_fn))
                elif len(new_fn) == 1:
                    names_d[list(new_fn)[0]] = rlay.name()
                     
                    
                log.debug('sampled %i values on raster \'%s\''%(
                    finv.dataProvider().featureCount(), rlay.name()))
                
        else:
            raise Error('unexpected geo type')
        

        log.info('sampling finished')
        
        res_name = 'expos_%s_%i_%i'%(self.tag, len(raster_l), finv.dataProvider().featureCount())
        
        finv.setName(res_name)
        
        self.names_d = names_d #needed by write()

        
        return finv
    
    def check(self):
        pass
        #======================================================================
        # #check results
        #======================================================================
        #check results cid column matches set in finv
        
        #make sure there are no negative values
        
        #report on number of nulls
        
    def write(self, vlay,
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
        
    def deletecolumn(self,
                     in_vlay,
                     fieldn_l, #list of field names
                     invert=False, #whether to invert selected field names
                     layname = None,


                     ):

        #=======================================================================
        # presets
        #=======================================================================
        algo_nm = 'qgis:deletecolumn'
        log = self.logger.getChild('deletecolumn')
        self.vlay = in_vlay

        #=======================================================================
        # field manipulations
        #=======================================================================
        fieldn_l = self._field_handlr(in_vlay, fieldn_l,  invert=invert)
        
            

        if len(fieldn_l) == 0:
            log.debug('no fields requsted to drop... skipping')
            return self.vlay

        #=======================================================================
        # assemble pars
        #=======================================================================
        #assemble pars
        ins_d = { 'COLUMN' : fieldn_l, 
                 'INPUT' : in_vlay, 
                 'OUTPUT' : 'TEMPORARY_OUTPUT'}
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        res_vlay = res_d['OUTPUT']

        
        #===========================================================================
        # post formatting
        #===========================================================================
        if layname is None: 
            layname = '%s_delf'%self.vlay.name()
            
        res_vlay.setName(layname) #reset the name

        
        return res_vlay 
    
    def _field_handlr(self, #common handling for fields
                      vlay, #layer to check for field presence
                      fieldn_l, #list of fields to handle
                      invert = False,
                      
                      ):
        
        log = self.logger.getChild('_field_handlr')

        #=======================================================================
        # all flag
        #=======================================================================
        if isinstance(fieldn_l, str):
            if fieldn_l == 'all':

                fieldn_l = vlay_fieldnl(vlay)
                log.debug('user passed \'all\', retrieved %i fields: \n    %s'%(
                    len(fieldn_l), fieldn_l))
                                
                
            else:
                raise Error('unrecognized fieldn_l\'%s\''%fieldn_l)
            
        #=======================================================================
        # type setting
        #=======================================================================
        if isinstance(fieldn_l, tuple) or isinstance(fieldn_l, np.ndarray) or isinstance(fieldn_l, set):
            fieldn_l = list(fieldn_l)
            
        #=======================================================================
        # checking
        #=======================================================================
        if not isinstance(fieldn_l, list):
            raise Error('expected a list for fields, instead got \n    %s'%fieldn_l)
        
        
    
    
        vlay_check(vlay, exp_fieldns=fieldn_l)
        
        
        #=======================================================================
        # #handle inversions
        #=======================================================================
        if invert:
            big_fn_s = set(vlay_fieldnl(vlay)) #get all the fields

            #get the difference
            fieldn_l = list(big_fn_s.difference(set(fieldn_l)))
            
            self.logger.debug('inverted selection from %i to %i fields'%
                      (len(big_fn_s),  len(fieldn_l)))
            
            
        
        
        return fieldn_l
    

if __name__ =="__main__": 
    #==========================================================================
    # dev data
    #==========================================================================
    data_dir = r'C:\LS\03_TOOLS\CanFlood\_ins\prep\wsamp\cT1'
    
    raster_fns = ['Gld_10e2_fail_cT1.tif', 'Gld_10e2_si_cT1.tif', 'Gld_20e1_fail_cT1.tif', 'Gld_20e1_si_cT1.tif']
    raster_fps = [os.path.join(data_dir, fn) for fn in raster_fns]
    
    finv_fp = os.path.join(data_dir, r'finv_icomp_cT1.gpkg')
    #==========================================================================
    # load the data
    #==========================================================================
    wrkr = WSLSampler(mod_logger)
    wrkr.ini_base()
    rlay_l, finv_vlay = wrkr.load_layers(raster_fps, finv_fp)
    
    
    #==========================================================================
    # execute
    #==========================================================================
    res_vlay = wrkr.run(rlay_l, finv_vlay, 
             cid='zid',
             crs = finv_vlay.crs(),
             )
       
    wrkr.check()
    
    #==========================================================================
    # save results
    #==========================================================================
    outfp = wrkr.write(res_vlay, )
    
    wrkr.upd_cf(os.path.join(data_dir, 'CanFlood_control_01.txt'))

    force_open_dir(os.getcwd())

    print('finished')
    
    
    

    

            
        