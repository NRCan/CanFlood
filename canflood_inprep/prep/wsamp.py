'''
Created on Feb. 9, 2020

@author: cefect
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, logging.config, configparser
#logcfg_file = r'C:\LS\03_TOOLS\CanFlood\0.0.2\_pars\logger.conf'
logger = logging.getLogger() #get the root logger
#logging.config.fileConfig(logcfg_file) #load the configuration file
#logger.info('root logger initiated and configured from file: %s'%(logcfg_file))


#==============================================================================
# imports------------
#==============================================================================
import os
from qgis.core import *



import numpy as np
import pandas as pd


#Qgis imports


from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject

from qgis.analysis import QgsNativeAlgorithms

"""throws depceciationWarning"""
import processing
from processing.core.Processing import Processing

# custom imports
import hp
from hp import *
from hp import Error, view, Qproj

#==============================================================================
# functions-------------------
#==============================================================================
class WSLSampler(Qproj):

    
    def __init__(self,
                 logger, out_dir, tag='test',
                 ):
        
        logger.info('simple wrapper inits')
        
        
        
        #=======================================================================
        # attach inputs
        #=======================================================================
        self.logger = logger.getChild('Qsimp')
        self.out_dir = out_dir
        self.tag = tag

        
        super().__init__() #initilzie teh baseclass
        
        self.logger.info('init finished')
        
        
        
    def load_layers(self, #load data to project
                    rfp_l, finv_fp,
                    providerLib='ogr'
                    ):
        
        """Im assuming for the plugin these layers will be loaded already"""
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
            control_fp = '', #control file path (for writing results to the control file)
            cid = 'xid', #index field name on finv
            crs = None,
            ):
        
        """
        #======================================================================
        # dev inputs
        #======================================================================
        raster_l:
            Gld_10e2_fail_cT1.tif
            Gld_10e2_si_cT1.tif
            Gld_20e1_fail_cT1.tif
            Gld_20e1_si_cT1.tif
            
        finv_raw:
            finv_raw_icomp_cT1.gpkg
        
        
        """
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        if crs is None: crs = self.crs
        
        #======================================================================
        # #check the data
        #======================================================================
        assert isinstance(crs, QgsCoordinateReferenceSystem)
        
        #check the finv_raw
        assert isinstance(finv_raw, QgsVectorLayer), 'bad type on finv_raw'
        assert finv_raw.crs() == crs, 'finv_raw crs doesnt match project'
        assert cid in [field.name() for field in finv_raw.fields()], \
            'requested cid field \'%s\' not found on the finv_raw'
        
        
        #check the rasters
        for rlay in raster_l:
            assert isinstance(rlay, QgsRasterLayer)
            assert rlay.crs() == crs, 'rlay %s crs doesnt match project'%(rlay.name())
        
        #======================================================================
        # slice data by project aoi
        #======================================================================
        """todo"""
        
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
        
        if 'Polygon' in gtype or 'Line' in gtype: 
            #ask for sample type (min/max/mean)
            
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
            for indxr, rlay in enumerate(raster_l):
                
    
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
                    
                log.debug('sampled %i values on raster \'%s\''%(
                    finv.dataProvider().featureCount(), rlay.name()))
                

        
        else:
            raise Error('unexpected geo type')
        

        log.info('sampling finished')
        
        res_name = 'expos_%s_%i_%i'%(self.tag, len(raster_l), finv.dataProvider().featureCount())
        
        finv.setName(res_name)
        #======================================================================
        # #check results
        #======================================================================
        #check results cid column matches set in finv
        
        #make sure there are no negative values
        
        #report on number of nulls
        
        
        #======================================================================
        # write data
        #======================================================================
        #extract data
        df = vlay_get_fdf(finv)
        out_fp = self.output_df(df, '%s.csv'%res_name, out_dir = self.out_dir)
        
        
        #======================================================================
        # set control file
        #======================================================================
        #build it
        if not os.path.exists(control_fp):
            raise Error('not implemented')
            #create control file template
            
        #load it
        log.info('reading parameters from \n     %s'%control_fp)
        pars = configparser.ConfigParser(inline_comment_prefixes='#', allow_no_value=True)
        _ = pars.read(control_fp)
        

        #pars['dmg_fps']['expos'] = out_fp
        pars.set('dmg_fps', 'expos', out_fp)
        pars.set('dmg_fps', '#expos file path set from wsamp.py')
        
        #write it
        with open(control_fp, 'w') as configfile:
            pars.write(configfile)
            
        log.info('updated dmg_fps.expos = %s'%out_fp)

        
        #======================================================================
        # wrap
        #======================================================================
        #set 'event_name_set' variable based on names of loaded rasters
        


        
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
        
        
def main_run(ras, vec, outp, cf):
    
    
    print('executing')
    
    #==========================================================================
    # dev data
    #==========================================================================
    #data_dir = r'C:\Users\tony.decrescenzo\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\floodiq\Geo_Files'
    #raster_fns = ['Gld_10e2_fail_cT1.tif', 'Gld_10e2_si_cT1.tif', 'Gld_20e1_fail_cT1.tif', 'Gld_20e1_si_cT1.tif']
    
    #raster_fps = [os.path.join(data_dir, fn) for fn in raster_fns]
    
    #finv_fp = r'C:\Users\tony.decrescenzo\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\floodiq\Geo_Files\finv_icomp_cT1.gpkg'
    
    #==========================================================================
    # initilize
    #==========================================================================
    wrkr =  WSLSampler(logger=logger, 
                       out_dir = outp,
                       tag='test')
    
    #set the coordinate system
    """I assume this will just be the project coordinate system"""
    wrkr.set_crs(authid = 3005) 
    
    #load the data
    """ (I assume these will already be loaded in the project)"""
    #raster_l, finv = wrkr.load_layers(raster_fps, finv_fp)
    
    #==========================================================================
    # run
    #==========================================================================
    dirname = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    wrkr.run(ras, vec,
             control_fp =  cf,
             )
    
    print('finished')
    

            
        