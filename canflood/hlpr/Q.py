'''
Created on Feb. 25, 2020

@author: cefect

helper functions w/ Qgis api
'''

#==============================================================================
# imports------------
#==============================================================================
#python
import os, configparser, logging, inspect, copy, datetime, re
import pandas as pd
import numpy as np
#qgis
from qgis.core import *
    
from qgis.analysis import QgsNativeAlgorithms
from qgis.gui import QgisInterface
from PyQt5.QtCore import QVariant, QMetaType 
from PyQt5.QtWidgets import QProgressBar

"""throws depceciationWarning"""
import processing  



#==============================================================================
# customs
#==============================================================================

mod_logger = logging.getLogger('Q') #get the root logger
    
    

from hlpr.exceptions import QError as Error
    

import hlpr.basic as basic
from hlpr.basic import get_valid_filename


#==============================================================================
# globals
#==============================================================================
fieldn_max_d = {'SpatiaLite':50, 'ESRI Shapefile':10, 'Memory storage':50, 'GPKG':50}

npc_pytype_d = {'?':bool,
                'b':int,
                'd':float,
                'e':float,
                'f':float,
                'q':int,
                'h':int,
                'l':int,
                'i':int,
                'g':float,
                'U':str,
                'B':int,
                'L':int,
                'Q':int,
                'H':int,
                'I':int, 
                'O':str, #this is the catchall 'object'
                }

type_qvar_py_d = {10:str, 2:int, 135:float, 6:float, 4:int, 1:bool, 16:datetime.datetime, 12:str} #QVariant.types to pythonic types

#parameters for lots of statistic algos
stat_pars_d = {'First': 0, 'Last': 1, 'Count': 2, 'Sum': 3, 'Mean': 4, 'Median': 5,
                'St dev (pop)': 6, 'Minimum': 7, 'Maximum': 8, 'Range': 9, 'Minority': 10,
                 'Majority': 11, 'Variety': 12, 'Q1': 13, 'Q3': 14, 'IQR': 15}

#==============================================================================
# classes -------------
#==============================================================================

class Qcoms(basic.ComWrkr): #baseclass for working w/ pyqgis outside the native console
    
    
    
    driverName = 'SpatiaLite' #default data creation driver type
    

    out_dName = driverName #default output driver/file type

    
    q_hndls = ['crs', 'crsid', 'algo_init', 'qap', 'vlay_drivers']
    
    algo_init = False #flag indicating whether the algos have been initialized
    qap = None
    mstore = None
    

    

    
    def __init__(self,
                 feedback=None, 
                 
                  #init controls
                 init_q_d = {}, #container of initilzied objects
                 
                 crsid = 'EPSG:4326', #default crsID if no init_q_d is passed
                 
                 **kwargs
                 ):
        
        """"
        #=======================================================================
        # plugin use
        #=======================================================================
        QprojPlugs don't execute super cascade
        
        #=======================================================================
        # Qgis inheritance
        #=======================================================================
        for single standalone runs
            all the handles will be generated and Qgis instanced
            
        for console runs
            handles should be passed to avoid re-instancing Qgis
            
        for session standalone runs
            handles passed
            
            for swapping crs
                run set_crs() on the session prior to spawning the child
            

        
        
        """


        #=======================================================================
        # defaults
        #=======================================================================
        if feedback is None:
            """by default, building our own feedbacker
            passed to ComWrkr.setup_feedback()
            """
            feedback = MyFeedBackQ()
        
        #=======================================================================
        # cascade
        #=======================================================================
        super().__init__(
            feedback = feedback, 
            **kwargs) #initilzie teh baseclass
        
        log = self.logger
        #=======================================================================
        # attachments
        #=======================================================================
        self.fieldn_max_d=fieldn_max_d
        self.crsid=crsid
        #=======================================================================
        # Qgis setup COMMON
        #=======================================================================
        """both Plugin and StandAlone runs should call these"""
        self.qproj = QgsProject.instance()
        
        

        """
        each worker will have their own store
        used to wipe any intermediate layers
        """
        self.mstore = QgsMapLayerStore() #build a new map store
        
        
        #do your own init (standalone r uns)
        if len(init_q_d) == 0:
            self._init_standalone()
        else:
            #check everything is there
            miss_l = set(self.q_hndls).difference(init_q_d.keys())
            assert len(miss_l)==0, 'init_q_d missing handles: %s'%miss_l
                            
            #set the handles
            for k,v in init_q_d.items():
                setattr(self, k, v)

                
        self._upd_qd()
        self.proj_checks()
        #=======================================================================
        # attach inputs
        #=======================================================================

        self.logger.debug('Qcoms.__init__ finished w/ out_dir: \n    %s'%self.out_dir)
        
        return
    
    #==========================================================================
    # standalone methods-----------
    #==========================================================================
        
    def _init_standalone(self,  #setup for qgis runs
                       crsid = None,
                       ):
        """
        WARNING! do not call twice (phantom crash)
        """
        log = self.logger.getChild('_init_standalone')
        if crsid is None: crsid = self.crsid
        #=======================================================================
        # #crs
        #=======================================================================

        crs = QgsCoordinateReferenceSystem(crsid)
            
        assert isinstance(crs, QgsCoordinateReferenceSystem), 'bad crs type'
        assert crs.isValid()
            
        self.crs = crs
        self.qproj.setCrs(crs)
        
        log.info('crs set to \'%s\''%self.crs.authid())
        #=======================================================================
        # setup qgis
        #=======================================================================
        
        self.qap = self.init_qgis()
        self.algo_init = self.init_algos()
        
        self.set_vdrivers()
        #=======================================================================
        # wrap
        #=======================================================================
        self._upd_qd()
        

        log.debug('Qproj._init_standalone finished')
        
        
        return
    
    def _upd_qd(self): #set a fresh parameter set
        self.init_q_d = {k:getattr(self, k) for k in self.q_hndls}
    
    def init_qgis(self, #instantiate qgis
                  gui = False): 
        """
        WARNING: need to hold this app somewhere. call in the module you're working in (scripts)
        
        """
        log = self.logger.getChild('init_qgis')
        
        try:
            
            QgsApplication.setPrefixPath(r'C:/OSGeo4W64/apps/qgis-ltr', True)
            
            app = QgsApplication([], gui)
            #   Update prefix path
            #app.setPrefixPath(r"C:\OSGeo4W64\apps\qgis", True)
            app.initQgis()
            #logging.debug(QgsApplication.showSettings())
            """ was throwing unicode error"""
            log.info(u' QgsApplication.initQgis. version: %s, release: %s'%(
                Qgis.QGIS_VERSION.encode('utf-8'), Qgis.QGIS_RELEASE_NAME.encode('utf-8')))
            return app
        
        except:
            raise Error('QGIS failed to initiate')
        
    def init_algos(self): #initiilize processing and add providers
        """
        crashing without raising an Exception
        """
    
    
        log = self.logger.getChild('init_algos')
        
        if not isinstance(self.qap, QgsApplication):
            raise Error('qgis has not been properly initlized yet')
        
        from processing.core.Processing import Processing
    
        Processing.initialize() #crashing without raising an Exception
    
        QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
        
        assert not self.feedback is None, 'instance needs a feedback method for algos to work'
        
        log.info('processing initilzied w/ feedback: \'%s\''%(type(self.feedback).__name__))
        

        return True

    def set_vdrivers(self):
        log = self.logger.getChild('set_vdrivers')
        #build vector drivers list by extension
        """couldnt find a good built-in to link extensions with drivers"""
        vlay_drivers = {'SpatiaLite':'sqlite', 'OGR':'shp'}
        
        
        #vlay_drivers = {'sqlite':'SpatiaLite', 'shp':'OGR','csv':'delimitedtext'}
        
        for ext in QgsVectorFileWriter.supportedFormatExtensions():
            dname = QgsVectorFileWriter.driverForExtension(ext)
            
            if not dname in vlay_drivers.keys():
            
                vlay_drivers[dname] = ext
            
        #add in missing/duplicated
        for vdriver in QgsVectorFileWriter.ogrDriverList():
            if not vdriver.driverName in vlay_drivers.keys():
                vlay_drivers[vdriver.driverName] ='?'
                
        self.vlay_drivers = vlay_drivers
        
        log.debug('built driver:extensions dict: \n    %s'%vlay_drivers)
        
        return
        
    def set_crs(self, #load, build, and set the project crs
                crsid =  None, #integer
                crs = None, #QgsCoordinateReferenceSystem
                logger=None,
                ):
        
        #=======================================================================
        # setup and defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('set_crs')
        
        if crsid is None: 
            crsid = self.crsid
        
        #=======================================================================
        # if not isinstance(crsid, int):
        #     raise IOError('expected integer for crs')
        #=======================================================================
        
        #=======================================================================
        # build it
        #=======================================================================
        if crs is None:
            crs = QgsCoordinateReferenceSystem(crsid)

        assert isinstance(crs, QgsCoordinateReferenceSystem)
        self.crs=crs #overwrite
        
        if not self.crs.isValid():
            raise IOError('CRS built from %i is invalid'%self.crs.authid())
        
        #=======================================================================
        # attach to project
        #=======================================================================
        self.qproj.setCrs(self.crs)
        self.crsid = self.crs.authid()
        
        if not self.qproj.crs().description() == self.crs.description():
            raise Error('qproj crs does not match sessions')
        
        log.info('crs set to EPSG: %s, \'%s\''%(self.crs.authid(), self.crs.description()))
        self._upd_qd()
        self.proj_checks(logger=log)
        
        return self.crs
           
    def proj_checks(self,
                    logger=None):
        #log = self.logger.getChild('proj_checks')
        
        if not self.driverName in self.vlay_drivers:
            raise Error('unrecognized driver name')
        
        if not self.out_dName in self.vlay_drivers:
            raise Error('unrecognized driver name')
        
        
        assert self.algo_init
        
        assert not self.feedback is None
        
        assert not self.progressBar is None
        
        #=======================================================================
        # crs checks
        #=======================================================================
        assert isinstance(self.crs, QgsCoordinateReferenceSystem)
        assert self.crs.isValid()
        
        assert self.crs.authid()==self.qproj.crs().authid(), 'crs mismatch'
        assert self.crs.authid() == self.crsid, 'crs mismatch'
        
        assert not self.crs.authid()=='', 'got empty CRS!'
        
        #=======================================================================
        # handle checks
        #=======================================================================
        assert isinstance(self.init_q_d, dict)
        miss_l = set(self.q_hndls).difference(self.init_q_d.keys())
        assert len(miss_l)==0, 'init_q_d missing handles: %s'%miss_l
        
        for k,v in self.init_q_d.items():
            assert getattr(self, k) == v, k
        
        #log.info('project passed all checks')
        
        return 
    
    def print_qt_version(self):
        import inspect
        from PyQt5 import Qt
         
        vers = ['%s = %s' % (k,v) for k,v in vars(Qt).items() if k.lower().find('version') >= 0 and not inspect.isbuiltin(v)]
        print('\n'.join(sorted(vers)))
    
    #===========================================================================
    # LOAD/WRITE LAYERS-----------
    #===========================================================================
    
    def load_vlay(self, 
                  fp, 
                  logger=None, 
                  providerLib='ogr',
                  aoi_vlay = None,
                  allow_none=True, #control check in saveselectedfeastures
                  addSpatialIndex=True,
                  ):
        
        assert os.path.exists(fp), 'requested file does not exist: %s'%fp
        
        if logger is None: logger = self.logger
        log = logger.getChild('load_vlay')
        
        basefn = os.path.splitext(os.path.split(fp)[1])[0]
        
        log.debug('loading from %s'%fp)
        
        vlay_raw = QgsVectorLayer(fp,basefn,providerLib)
        
        
        

        #=======================================================================
        # # checks
        #=======================================================================
        if not isinstance(vlay_raw, QgsVectorLayer): 
            raise IOError
        
        #check if this is valid
        if not vlay_raw.isValid():
            raise Error('loaded vlay \'%s\' is not valid. \n \n did you initilize?'%vlay_raw.name())
        
        #check if it has geometry
        if vlay_raw.wkbType() == 100:
            raise Error('loaded vlay has NoGeometry')
        
        assert isinstance(self.mstore, QgsMapLayerStore)
        
        """only add intermediate layers to store
        self.mstore.addMapLayer(vlay_raw)"""
        
        if not vlay_raw.crs()==self.qproj.crs():
            log.warning('crs mismatch: \n    %s\n    %s'%(
            vlay_raw.crs(), self.qproj.crs()))
        
        #=======================================================================
        # aoi slice
        #=======================================================================
        if isinstance(aoi_vlay, QgsVectorLayer):
            log.info('slicing by aoi %s'%aoi_vlay.name())
            
            vlay = self.selectbylocation(vlay_raw, aoi_vlay, allow_none=allow_none,
                                 logger=log, result_type='layer')
            
            #check for no selection
            if vlay is None:
                return None
            
            vlay.setName(vlay_raw.name()) #reset the name
            
            #clear original from memory
            self.mstore.addMapLayer(vlay_raw)
            self.mstore.removeMapLayers([vlay_raw])
            
        else: 
            vlay = vlay_raw
            
        #=======================================================================
        # clean------
        #=======================================================================
        #spatial index
        if addSpatialIndex and (not vlay_raw.hasSpatialIndex()==QgsFeatureSource.SpatialIndexPresent):
            self.createspatialindex(vlay_raw, logger=log)
        
 
        #=======================================================================
        # wrap
        #=======================================================================
        dp = vlay.dataProvider()

        log.info('loaded vlay \'%s\' as \'%s\' %s geo  with %i feats from file: \n     %s'
                    %(vlay.name(), dp.storageType(), QgsWkbTypes().displayString(vlay.wkbType()), dp.featureCount(), fp))
        

        return vlay
    
    def load_rlay(self, fp, 
                  aoi_vlay = None,
                  logger=None):
        
        if logger is None: logger = self.logger
        log = logger.getChild('load_rlay')
        
        assert os.path.exists(fp), 'requested file does not exist: %s'%fp
        assert QgsRasterLayer.isValidRasterFileName(fp),  \
            'requested file is not a valid raster file type: %s'%fp
        
        basefn = os.path.splitext(os.path.split(fp)[1])[0]
        

        #Import a Raster Layer
        log.debug('QgsRasterLayer(%s, %s)'%(fp, basefn))
        rlayer = QgsRasterLayer(fp, basefn)
        """
        hanging for some reason...
        QgsRasterLayer(C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\haz_rast\haz_1000.tif, haz_1000)
        """
        #=======================================================================
        # rlayer = QgsRasterLayer(r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\1\haz_rast\haz_1000.tif',
        #                 'haz_1000')
        #=======================================================================
        
        
        #===========================================================================
        # check
        #===========================================================================
        assert isinstance(rlayer, QgsRasterLayer), 'failed to get a QgsRasterLayer'
        assert rlayer.isValid(), "Layer failed to load!"
        
        
        if not rlayer.crs() == self.qproj.crs():
            log.warning('loaded layer \'%s\' crs mismatch!'%rlayer.name())

        log.debug('loaded \'%s\' from \n    %s'%(rlayer.name(), fp))
        
        #=======================================================================
        # aoi
        #=======================================================================
        if not aoi_vlay is None:
            log.debug('clipping w/ %s'%aoi_vlay.name())
            assert isinstance(aoi_vlay, QgsVectorLayer)
            rlay2 = self.cliprasterwithpolygon(rlayer,aoi_vlay, logger=log, layname=rlayer.name())
            
            #clean up
            mstore = QgsMapLayerStore() #build a new store
            mstore.addMapLayers([rlayer]) #add the layers to the store
            mstore.removeAllMapLayers() #remove all the layers
        else:
            rlay2 = rlayer
        
        return rlay2
    
    
    def write_rlay(self, #make a local copy of the passed raster layer
                   rlayer, #raster layer to make a local copy of
                   extent = 'layer', #write extent control
                        #'layer': use the current extent (default)
                        #'mapCanvas': use the current map Canvas
                        #QgsRectangle: use passed extents
                   
                   
                   resolution = 'raw', #resolution for output
                   
                   
                   opts = ["COMPRESS=LZW"], #QgsRasterFileWriter.setCreateOptions
                   
                   out_dir = None, #directory for puts
                   newLayerName = None,
                   
                   logger=None,
                   ):
        """
        because  processing tools only work on local copies
        
        #=======================================================================
        # coordinate transformation
        #=======================================================================
        NO CONVERSION HERE!
        can't get native API to work. use gdal_warp instead
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        if out_dir is None: out_dir = self.out_dir
        if newLayerName is None: newLayerName = rlayer.name()
        
        newFn = get_valid_filename('%s.tif'%newLayerName) #clean it
        
        out_fp = os.path.join(out_dir, newFn)

        
        log = logger.getChild('write_rlay')
        
        log.debug('on \'%s\' w/ \n    crs:%s \n    extents:%s\n    xUnits:%.4f'%(
            rlayer.name(), rlayer.crs(), rlayer.extent(), rlayer.rasterUnitsPerPixelX()))
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(rlayer, QgsRasterLayer)
        assert os.path.exists(out_dir)
        
        if os.path.exists(out_fp):
            msg = 'requested file already exists! and overwrite=%s \n    %s'%(
                self.overwrite, out_fp)
            if self.overwrite:
                log.warning(msg)
            else:
                raise Error(msg)

        #=======================================================================
        # extract info from layer
        #=======================================================================
        """consider loading the layer and duplicating the renderer?
        renderer = rlayer.renderer()"""
        provider = rlayer.dataProvider()
        
        
        #build projector
        projector = QgsRasterProjector()
        #projector.setCrs(provider.crs(), provider.crs())
        

        #build and configure pipe
        pipe = QgsRasterPipe()
        if not pipe.set(provider.clone()): #Insert a new known interface in default place
            raise Error("Cannot set pipe provider")
             
        if not pipe.insert(2, projector): #insert interface at specified index and connect
            raise Error("Cannot set pipe projector")

        #pipe = rlayer.pipe()
            
        
        #coordinate transformation
        """see note"""
        transformContext = self.qproj.transformContext()
        
        #=======================================================================
        # extents
        #=======================================================================
        if extent == 'layer':
            extent = rlayer.extent()
            
        elif extent=='mapCanvas':
            assert isinstance(self.iface, QgisInterface), 'bad key for StandAlone?'
            
            #get the extent, transformed to the current CRS
            extent =  QgsCoordinateTransform(
                self.qproj.crs(), 
                rlayer.crs(), 
                transformContext
                    ).transformBoundingBox(self.iface.mapCanvas().extent())
                
        assert isinstance(extent, QgsRectangle), 'expected extent=QgsRectangle. got \"%s\''%extent
        
        #expect the requested extent to be LESS THAN what we have in the raw raster
        assert rlayer.extent().width()>=extent.width(), 'passed extents too wide'
        assert rlayer.extent().height()>=extent.height(), 'passed extents too tall'
        #=======================================================================
        # resolution
        #=======================================================================
        #use the resolution of the raw file
        if resolution == 'raw':
            """this respects the calculated extents"""
            
            nRows = int(extent.height()/rlayer.rasterUnitsPerPixelY())
            nCols = int(extent.width()/rlayer.rasterUnitsPerPixelX())
            

            
        else:
            """dont think theres any decent API support for the GUI behavior"""
            raise Error('not implemented')

        

        
        #=======================================================================
        # #build file writer
        #=======================================================================

        file_writer = QgsRasterFileWriter(out_fp)
        #file_writer.Mode(1) #???
        
        if not opts is None:
            file_writer.setCreateOptions(opts)
        
        log.debug('writing to file w/ \n    %s'%(
            {'nCols':nCols, 'nRows':nRows, 'extent':extent, 'crs':rlayer.crs()}))
        
        #execute write
        error = file_writer.writeRaster( pipe, nCols, nRows, extent, rlayer.crs(), transformContext)
        
        log.info('wrote to file \n    %s'%out_fp)
        #=======================================================================
        # wrap
        #=======================================================================
        if not error == QgsRasterFileWriter.NoError:
            raise Error(error)
        
        assert os.path.exists(out_fp)
        
        assert QgsRasterLayer.isValidRasterFileName(out_fp),  \
            'requested file is not a valid raster file type: %s'%out_fp
        
        
        return out_fp
    
    def vlay_write(self, #write  a VectorLayer
        vlay,
        out_fp=None, 

        driverName='GPKG',
        fileEncoding = "CP1250", 
        opts = QgsVectorFileWriter.SaveVectorOptions(), #empty options object
        overwrite=None,
        logger=None):
        """
        help(QgsVectorFileWriter.SaveVectorOptions)
        QgsVectorFileWriter.SaveVectorOptions.driverName='GPKG'
        opt2 = QgsVectorFileWriter.BoolOption(QgsVectorFileWriter.CreateOrOverwriteFile)
        help(QgsVectorFileWriter)

        
        """
        
        #==========================================================================
        # defaults
        #==========================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('vlay_write')
        if overwrite is None: overwrite=self.overwrite
        
        if out_fp is None: out_fp = os.path.join(self.out_dir, '%s.gpkg'%vlay.name())
        
        #===========================================================================
        # assemble options
        #===========================================================================
        opts.driverName = driverName
        opts.fileEncoding = fileEncoding
        
        
        #===========================================================================
        # checks
        #===========================================================================
        #file extension
        fhead, ext = os.path.splitext(out_fp)
        
        if not 'gpkg' in ext:
            raise Error('unexpected extension: %s'%ext)
        
        if os.path.exists(out_fp):
            msg = 'requested file path already exists!. overwrite=%s \n    %s'%(
                overwrite, out_fp)
            if overwrite:
                log.warning(msg)
                os.remove(out_fp) #workaround... should be away to overwrite with the QgsVectorFileWriter
            else:
                raise Error(msg)
            
        
        if vlay.dataProvider().featureCount() == 0:
            raise Error('\'%s\' has no features!'%(
                vlay.name()))
            
        if not vlay.isValid():
            Error('passed invalid layer')
            
        #=======================================================================
        # write
        #=======================================================================
        
        error = QgsVectorFileWriter.writeAsVectorFormatV2(
                vlay, out_fp, 
                QgsCoordinateTransformContext(),
                opts,
                )
        
        
        #=======================================================================
        # wrap and check
        #=======================================================================
          
        if error[0] == QgsVectorFileWriter.NoError:
            log.info('layer \' %s \' written to: \n     %s'%(vlay.name(),out_fp))
            return out_fp
         
        raise Error('FAILURE on writing layer \' %s \'  with code:\n    %s \n    %s'%(vlay.name(),error, out_fp))
        

    
    def load_dtm(self, #convienece loader for assining the correct attribute 
                 fp, 
                 logger=None,
                 **kwargs):
        if logger is None: logger=self.logger
        log=logger.getChild('load_dtm')
        
        self.dtm_rlay = self.load_rlay(fp, logger=log, **kwargs)
        
        return self.dtm_rlay
        

    #==========================================================================
    # GENERIC METHODS-----------------
    #==========================================================================

    def vlay_new_df2(self, #build a vlay from a df
            df_raw,
            
            geo_d = None, #container of geometry objects {fid: QgsGeometry}

            crs=None,
            gkey = None, #data field linking with geo_d (if None.. uses df index)
            
            layname='df',
            
            index = False, #whether to include the index as a field
            logger=None, 

            ):
        """
        performance enhancement over vlay_new_df
            simpler, clearer
            although less versatile
        """
        #=======================================================================
        # setup
        #=======================================================================
        if crs is None: crs = self.qproj.crs()
        if logger is None: logger = self.logger
            
        log = logger.getChild('vlay_new_df')
        
        
        #=======================================================================
        # index fix
        #=======================================================================
        df = df_raw.copy()
        
        if index:
            if not df.index.name is None:
                coln = df.index.name
                df.index.name = None
            else:
                coln = 'index'
                
            df[coln] = df.index
            
        #=======================================================================
        # precheck
        #=======================================================================
        
        
        #make sure none of hte field names execeed the driver limitations
        max_len = self.fieldn_max_d[self.driverName]
        
        #check lengths
        boolcol = df_raw.columns.str.len() >= max_len
        
        if np.any(boolcol):
            log.warning('passed %i columns which exeed the max length=%i for driver \'%s\'.. truncating: \n    %s'%(
                boolcol.sum(), max_len, self.driverName, df_raw.columns[boolcol].tolist()))
            
            
            df.columns = df.columns.str.slice(start=0, stop=max_len-1)

        
        #make sure the columns are unique
        assert df.columns.is_unique, 'got duplicated column names: \n    %s'%(df.columns.tolist())
        
        #check datatypes
        assert np.array_equal(df.columns, df.columns.astype(str)), 'got non-string column names'

        
        #check the geometry
        if not geo_d is None:
            assert isinstance(geo_d, dict)
            if not gkey is None:
                assert gkey in df_raw.columns
        
                #assert 'int' in df_raw[gkey].dtype.name
                
                #check gkey match
                l = set(df_raw[gkey].drop_duplicates()).difference(geo_d.keys())
                assert len(l)==0, 'missing %i \'%s\' keys in geo_d: %s'%(len(l), gkey, l)
                
            #against index
            else:
                
                #check gkey match
                l = set(df_raw.index).difference(geo_d.keys())
                assert len(l)==0, 'missing %i (of %i) fid keys in geo_d: %s'%(len(l), len(df_raw), l)

        #===========================================================================
        # assemble the fields
        #===========================================================================
        #column name and python type
        fields_d = {coln:np_to_pytype(col.dtype) for coln, col in df.items()}
        
        #fields container
        qfields = fields_build_new(fields_d = fields_d, logger=log)
        
        #=======================================================================
        # assemble the features
        #=======================================================================
        #convert form of data
        
        feats_d = dict()
        for fid, row in df.iterrows():
    
            feat = QgsFeature(qfields, fid) 
            
            #loop and add data
            for fieldn, value in row.items():
    
                #skip null values
                if pd.isnull(value): continue
                
                #get the index for this field
                findx = feat.fieldNameIndex(fieldn) 
                
                #get the qfield
                qfield = feat.fields().at(findx)
                
                #make the type match
                ndata = qtype_to_pytype(value, qfield.type(), logger=log)
                
                #set the attribute
                if not feat.setAttribute(findx, ndata):
                    raise Error('failed to setAttribute')
                
            #setgeometry
            if not geo_d is None:
                if gkey is None:
                    gobj = geo_d[fid]
                else:
                    gobj = geo_d[row[gkey]]
                
                feat.setGeometry(gobj)
            
            #stor eit
            feats_d[fid]=feat
        
        log.debug('built %i \'%s\'  features'%(
            len(feats_d),
            QgsWkbTypes.geometryDisplayString(feat.geometry().type()),
            ))
        
        
        #=======================================================================
        # get the geo type
        #=======================================================================\
        if not geo_d is None:
            gtype = QgsWkbTypes().displayString(next(iter(geo_d.values())).wkbType())
        else:
            gtype='None'

        #===========================================================================
        # buidl the new layer
        #===========================================================================
        vlay = vlay_new_mlay(gtype,
                             crs, 
                             layname,
                             qfields,
                             list(feats_d.values()),
                             logger=log,
                             )
        self.createspatialindex(vlay, logger=log)
        #=======================================================================
        # post check
        #=======================================================================
        if not geo_d is None:
            if vlay.wkbType() == 100:
                raise Error('constructed layer has NoGeometry')



        
        return vlay
    

    
    def check_aoi(self, #special c hecks for AOI layers
                  vlay):
        
        assert isinstance(vlay, QgsVectorLayer)
        assert 'Polygon' in QgsWkbTypes().displayString(vlay.wkbType())
        assert vlay.dataProvider().featureCount()==1
        assert vlay.crs() == self.qproj.crs(), 'aoi CRS (%s) does not match project (%s)'%(vlay.crs(), self.qproj.crs())
        
        return 
    
    #==========================================================================
    # ALGOS--------------
    #==========================================================================
    def deletecolumn(self,
                     in_vlay,
                     fieldn_l, #list of field names
                     invert=False, #whether to invert selected field names
                     layname = None,

                     logger=None,
                     ):

        #=======================================================================
        # presets
        #=======================================================================
        algo_nm = 'qgis:deletecolumn'
        if logger is None: logger=self.logger
        log = logger.getChild('deletecolumn')
        self.vlay = in_vlay

        #=======================================================================
        # field manipulations
        #=======================================================================
        fieldn_l = self._field_handlr(in_vlay, fieldn_l,  invert=invert, logger=log)
        
            

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

    def joinattributesbylocation(self,
                                 #data definitions
                                 vlay,
                                 join_vlay, #layer from which to extract attribue values onto th ebottom vlay
                                 jlay_fieldn_l, #list of field names to extract from the join_vlay
                                 selected_only = False,
                                 jvlay_selected_only = False, #only consider selected features on the join layer
                                 
                                 #algo controls
                                 prefix = '',
                                 method=0, #one-to-many
                                 predicate_l = ['intersects'],#list of geometric serach predicates
                                 discard_nomatch = False, #Discard records which could not be joined
                                 
                                 #data expectations
                                 join_nullvs = True, #allow null values on  jlay_fieldn_l on join_vlay
                                 join_df = None, #if join_nullvs=FALSE, data to check for nulls (skips making a vlay_get_fdf)
                                 allow_field_rename = False, #allow joiner fields to be renamed when mapped onto the main
                                 allow_none = False,

                                 #geometry expectations
                                 expect_all_hits = False, #wheter every main feature intersects a join feature
                                 expect_j_overlap = False, #wheter to expect the join_vlay to beoverlapping
                                 expect_m_overlap = False, #wheter to expect the mainvlay to have overlaps
                                 
                                 logger=None,
                     ):
        """        
        TODO: really need to clean this up...
        
        discard_nomatch: 
            TRUE: two resulting layers have no features in common
            FALSE: in layer retains all non matchers, out layer only has the non-matchers?
        
        METHOD: Join type

        - 0: Create separate feature for each located feature (one-to-many)
        - 1: Take attributes of the first located feature only (one-to-one)
        
        """
        #=======================================================================
        # presets
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('joinattributesbylocation')
        self.vlay = vlay
        algo_nm = 'qgis:joinattributesbylocation'
        
        predicate_d = {'intersects':0,'contains':1,'equals':2,'touches':3,'overlaps':4,'within':5, 'crosses':6}
        

        

        jlay_fieldn_l = self._field_handlr(join_vlay, 
                                           jlay_fieldn_l, 
                                           invert=False)
        
        #=======================================================================
        # jgeot = vlay_get_bgeo_type(join_vlay)
        # mgeot = vlay_get_bgeo_type(self.vlay)
        #=======================================================================
        
        mfcnt = self.vlay.dataProvider().featureCount()
        #jfcnt = join_vlay.dataProvider().featureCount()
        
        mfnl = vlay_fieldnl(self.vlay)
        
        expect_overlaps = expect_j_overlap or expect_m_overlap
        #=======================================================================
        # geometry expectation prechecks
        #=======================================================================
        """should take any geo
        if not (jgeot == 'polygon' or mgeot == 'polygon'):
            raise Error('one of the layres has to be a polygon')
        
        if not jgeot=='polygon':
            if expect_j_overlap:
                raise Error('join vlay is not a polygon, expect_j_overlap should =False')
            
        if not mgeot=='polygon':
            if expect_m_overlap:
                raise Error('main vlay is not a polygon, expect_m_overlap should =False')
        
        if expect_all_hits:
            if discard_nomatch:
                raise Error('discard_nomatch should =FALSE if  you expect all hits')
            
            if allow_none:
                raise Error('expect_all_hits=TRUE and allow_none=TRUE')

            
        #method checks
        if method==0:
            if not jgeot == 'polygon':
                raise Error('passed method 1:m but jgeot != polygon')
            
        if not expect_j_overlap:
            if not method==0:
                raise Error('for expect_j_overlap=False, method must = 0 (1:m) for validation')
                """

               
        #=======================================================================
        # data expectation checks
        #=======================================================================
        #make sure none of the joiner fields are already on the layer
        if len(mfnl)>0: #see if there are any fields on the main
            l = basic.linr(jlay_fieldn_l, mfnl, result_type='matching')
            
            if len(l) > 0:
                #w/a prefix
                if not prefix=='':
                    log.debug('%i fields on the joiner \'%s\' are already on \'%s\'... prefixing w/ \'%s\': \n    %s'%(
                        len(l), join_vlay.name(), self.vlay.name(), prefix, l))
                else:
                    log.debug('%i fields on the joiner \'%s\' are already on \'%s\'...renameing w/ auto-sufix: \n    %s'%(
                        len(l), join_vlay.name(), self.vlay.name(), l))
                    
                    if not allow_field_rename:
                        raise Error('%i field names overlap: %s'%(len(l), l))
                
                
        #make sure that the joiner attributes are not null
        if not join_nullvs:
            if jvlay_selected_only:
                raise Error('not implmeneted')
            
            #pull thedata
            if join_df is None:
                join_df = vlay_get_fdf(join_vlay, fieldn_l=jlay_fieldn_l, db_f=self.db_f, logger=log)
                
            #slice to the columns of interest
            join_df = join_df.loc[:, jlay_fieldn_l]
                
            #check for nulls
            booldf = join_df.isna()
            
            if np.any(booldf):
                raise Error('got %i nulls on \'%s\' field %s data'%(
                    booldf.sum().sum(), join_vlay.name(), jlay_fieldn_l))
            

        #=======================================================================
        # assemble pars
        #=======================================================================
        #convert predicate to code
        pred_code_l = [predicate_d[name] for name in predicate_l]

            
        #selection flags
        if selected_only:
            """WARNING! This will limit the output to only these features
            (despite the DISCARD_NONMATCHING flag)"""
            
            main_input = self._get_sel_obj(self.vlay)
        else:
            main_input = self.vlay
        
        if jvlay_selected_only:
            join_input = self._get_sel_obj(join_vlay)
        else:
            join_input = join_vlay

        #assemble pars
        ins_d = { 'DISCARD_NONMATCHING' : discard_nomatch, 
                 'INPUT' : main_input, 
                 'JOIN' : join_input, 
                 'JOIN_FIELDS' : jlay_fieldn_l,
                 'METHOD' : method, 
                 'OUTPUT' : 'TEMPORARY_OUTPUT', 
                 #'NON_MATCHING' : 'TEMPORARY_OUTPUT', #not working as expected. see get_misses
                 'PREDICATE' : pred_code_l, 
                 'PREFIX' : prefix}
        
        
        
        log.info('extracting %i fields from %i feats from \'%s\' to \'%s\' join fields: %s'%
                  (len(jlay_fieldn_l), join_vlay.dataProvider().featureCount(), 
                   join_vlay.name(), self.vlay.name(), jlay_fieldn_l))
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        res_vlay, join_cnt = res_d['OUTPUT'], res_d['JOINED_COUNT']
        
        log.debug('got results: \n    %s'%res_d)

        #===========================================================================
        # post checks
        #===========================================================================
        
        hit_fcnt = res_vlay.dataProvider().featureCount()
        
        
        if not expect_overlaps:
            if not discard_nomatch:
                if not hit_fcnt == mfcnt:
                    raise Error('in and out fcnts dont match')

        else:
            pass
            #log.debug('expect_overlaps=False, unable to check fcnts')



        #all misses
        if join_cnt == 0:
            log.warning('got no joins from \'%s\' to \'%s\''%(
                self.vlay.name(), join_vlay.name()))
            
            if not allow_none:
                raise Error('got no joins!')
            
            if discard_nomatch:
                if not hit_fcnt == 0:
                    raise Error('no joins but got some hits')
           
        #some hits 
        else:
            #check there are no nulls
            if discard_nomatch and not join_nullvs:
                #get data on first joiner
                fid_val_ser = vlay_get_fdata(res_vlay, jlay_fieldn_l[0], logger=log, fmt='ser')
                
                if np.any(fid_val_ser.isna()):                  
                    raise Error('discard=True and join null=FALSe but got %i (of %i) null \'%s\' values in the reuslt'%(
                        fid_val_ser.isna().sum(), len(fid_val_ser), fid_val_ser.name
                        ))
                

        #=======================================================================
        # get the new field names
        #=======================================================================
        new_fn_l = set(vlay_fieldnl(res_vlay)).difference(vlay_fieldnl(self.vlay))
                    
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('finished joining %i fields from %i (of %i) feats from \'%s\' to \'%s\' join fields: %s'%
                  (len(new_fn_l), join_cnt, self.vlay.dataProvider().featureCount(),
                   join_vlay.name(), self.vlay.name(), new_fn_l))
        

        return res_vlay, new_fn_l, join_cnt
    
    
    def joinbylocationsummary(self,
                                vlay, #polygon layer to sample from
                                 join_vlay, #layer from which to extract attribue values onto th ebottom vlay
                                 jlay_fieldn_l, #list of field names to extract from the join_vlay
                                 jvlay_selected_only = False, #only consider selected features on the join layer

                                 predicate_l = ['intersects'],#list of geometric serach predicates
                                 smry_l = ['sum'], #data summaries to apply
                                 discard_nomatch = False, #Discard records which could not be joined
                                 
                                 use_raw_fn=False, #whether to convert names back to the originals
                                 layname=None,
                                 
                     ):
        """
        WARNING: This ressets the fids
        
        discard_nomatch: 
            TRUE: two resulting layers have no features in common
            FALSE: in layer retains all non matchers, out layer only has the non-matchers?
        
        """
        
        """
        view(join_vlay)
        """
        #=======================================================================
        # presets
        #=======================================================================
        algo_nm = 'qgis:joinbylocationsummary'
        
        predicate_d = {'intersects':0,'contains':1,'equals':2,'touches':3,'overlaps':4,'within':5, 'crosses':6}
        summaries_d = {'count':0, 'unique':1, 'min':2, 'max':3, 'range':4, 'sum':5, 'mean':6}

        log = self.logger.getChild('joinbylocationsummary')
        
        #=======================================================================
        # defaults
        #=======================================================================
        if isinstance(jlay_fieldn_l, set):
            jlay_fieldn_l = list(jlay_fieldn_l)
            
            
        #convert predicate to code
        pred_code_l = [predicate_d[pred_name] for pred_name in predicate_l]
            
        #convert summaries to code
        sum_code_l = [summaries_d[smry_str] for smry_str in smry_l]
        
        
        if layname is None:  layname = '%s_jsmry'%vlay.name()
            
        #=======================================================================
        # prechecks
        #=======================================================================
        if not isinstance(jlay_fieldn_l, list):
            raise Error('expected a list')
        
        #check requested join fields
        fn_l = [f.name() for f in join_vlay.fields()]
        s = set(jlay_fieldn_l).difference(fn_l)
        assert len(s)==0, 'requested join fields not on layer: %s'%s
        
        #check crs
        assert join_vlay.crs().authid() == vlay.crs().authid()
                
        #=======================================================================
        # assemble pars
        #=======================================================================
        main_input=vlay

        if jvlay_selected_only:
            join_input = self._get_sel_obj(join_vlay)
        else:
            join_input = join_vlay

        #assemble pars
        ins_d = { 'DISCARD_NONMATCHING' : discard_nomatch,
                  'INPUT' : main_input,
                   'JOIN' : join_input,
                   'JOIN_FIELDS' : jlay_fieldn_l,
                  'OUTPUT' : 'TEMPORARY_OUTPUT', 
                  'PREDICATE' : pred_code_l, 
                  'SUMMARIES' : sum_code_l,
                   }
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
 
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
 
        res_vlay = res_d['OUTPUT']
 
        #===========================================================================
        # post formatting
        #===========================================================================
        res_vlay.setName(layname) #reset the name
        
        #get new field names
        nfn_l = set([f.name() for f in res_vlay.fields()]).difference([f.name() for f in vlay.fields()])
        
        """
        view(res_vlay)
        """
        #=======================================================================
        # post check
        #=======================================================================
        for fn in nfn_l:
            rser = vlay_get_fdata(res_vlay, fieldn=fn, logger=log, fmt='ser')
            if rser.isna().all().all():
                log.warning('%s \'%s\' got all nulls'%(vlay.name(), fn))

        
        #=======================================================================
        # rename fields
        #=======================================================================
        if use_raw_fn:
            assert len(smry_l)==1, 'rename only allowed for single sample stat'
            rnm_d = {s:s.replace('_%s'%smry_l[0],'') for s in nfn_l}
            
            s = set(rnm_d.values()).symmetric_difference(jlay_fieldn_l)
            assert len(s)==0, 'failed to convert field names'
            
            res_vlay = vlay_rename_fields(res_vlay, rnm_d, logger=log)
            
            nfn_l = jlay_fieldn_l
        
        
        
        log.info('sampled \'%s\' w/ \'%s\' (%i hits) and \'%s\'to get %i new fields \n    %s'%(
            join_vlay.name(), vlay.name(), res_vlay.dataProvider().featureCount(), 
            smry_l, len(nfn_l), nfn_l))
        
        return res_vlay, nfn_l

    def joinattributestable(self, #join csv edata to a vector layer
                            vlay, table_fp, fieldNm, 
                            
                      method = 1,  #join type
                              #- 0: Create separate feature for each matching feature (one-to-many)
                              #- 1: Take attributes of the first matching feature only (one-to-one)

                      csv_params = {'encoding':'System',
                                    'type':'csv',
                                    'maxFields':'10000',
                                    'detectTypes':'yes',
                                    'geomType':'none',
                                    'subsetIndex':'no',
                                    'watchFile':'no'},
                      
                     logger=None, 
                      layname=None,
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        
        if layname is None: 
            layname = '%s_j'%vlay.name()
        
        algo_nm = 'native:joinattributestable'
        log = self.logger.getChild('joinattributestable')

        #=======================================================================
        # prechecks
        #=======================================================================
        assert isinstance(vlay, QgsVectorLayer)
        assert os.path.exists(table_fp)
        assert fieldNm in [f.name() for f in vlay.fields()], 'vlay missing link field %s'%fieldNm
        
        #=======================================================================
        # setup table layer
        #=======================================================================
        uriW = QgsDataSourceUri()
        for pName, pValue in csv_params.items():
            uriW.setParam(pName, pValue)
        
        table_uri = r'file:///' + table_fp.replace('\\','/') +'?'+ str(uriW.encodedUri(), 'utf-8')
       
        table_vlay = QgsVectorLayer(table_uri,'table',"delimitedtext")
        
        assert fieldNm in [f.name() for f in table_vlay.fields()], 'table missing link field %s'%fieldNm
        #=======================================================================
        # assemble p ars
        #=======================================================================
        
        ins_d = { 'DISCARD_NONMATCHING' : True, 
                 'FIELD' : 'xid', 'FIELDS_TO_COPY' : [],
                  'FIELD_2' : 'xid', 
                  'INPUT' : vlay, 
                  'INPUT_2' : table_vlay,
                  'METHOD' : method, 
                  'OUTPUT' : 'TEMPORARY_OUTPUT', 'PREFIX' : '' }
        
        #=======================================================================
        # execute
        #=======================================================================
        log.debug('executing \'native:buffer\' with ins_d: \n    %s'%ins_d)
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        res_vlay = res_d['OUTPUT']

        res_vlay.setName(layname) #reset the name
        
        log.debug('finished w/ %i feats'%res_vlay.dataProvider().featureCount())

        return res_vlay

    def cliprasterwithpolygon(self,
                              rlay_raw,
                              poly_vlay,
                              layname = None,
                              #output = 'TEMPORARY_OUTPUT',
                              logger = None,
                              ):
        """
        clipping a raster layer with a polygon mask using gdalwarp
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('cliprasterwithpolygon')
        
        if layname is None:
            layname = '%s_clipd'%rlay_raw.name()
            
            
        algo_nm = 'gdal:cliprasterbymasklayer'
            

        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(rlay_raw, QgsRasterLayer)
        assert isinstance(poly_vlay, QgsVectorLayer)
        assert 'Poly' in QgsWkbTypes().displayString(poly_vlay.wkbType())
        
        assert rlay_raw.crs() == poly_vlay.crs()
            
            
        #=======================================================================
        # run algo        
        #=======================================================================

        
        ins_d = {   'ALPHA_BAND' : False,
                    'CROP_TO_CUTLINE' : True,
                    'DATA_TYPE' : 0,
                    'EXTRA' : '',
                    'INPUT' : rlay_raw,
                    'KEEP_RESOLUTION' : True, 
                    'MASK' : poly_vlay,
                    'MULTITHREADING' : False,
                    'NODATA' : None,
                    'OPTIONS' : '',
                    'OUTPUT' : 'TEMPORARY_OUTPUT',
                    'SET_RESOLUTION' : False,
                    'SOURCE_CRS' : None,
                    'TARGET_CRS' : None,
                    'X_RESOLUTION' : None,
                    'Y_RESOLUTION' : None,
                     }
        
        log.debug('executing \'%s\' with ins_d: \n    %s \n\n'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        log.debug('finished w/ \n    %s'%res_d)
        
        if not os.path.exists(res_d['OUTPUT']):
            """failing intermittently"""
            raise Error('failed to get a result')
        
        res_rlay = QgsRasterLayer(res_d['OUTPUT'], layname)

        #=======================================================================
        # #post check
        #=======================================================================
        assert isinstance(res_rlay, QgsRasterLayer), 'got bad type: %s'%type(res_rlay)
        assert res_rlay.isValid()
           
   
        res_rlay.setName(layname) #reset the name
           
        log.debug('finished w/ %s'%res_rlay.name())
          
        return res_rlay
    
    def cliprasterwithpolygon2(self, #with saga
                              rlay_raw,
                              poly_vlay,
                              ofp = None,
                              layname = None,
                              #output = 'TEMPORARY_OUTPUT',
                              logger = None,
                              ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('cliprasterwithpolygon')
        
        if layname is None:
            if not ofp is None:
                layname = os.path.splitext(os.path.split(ofp)[1])[0]
            else:
                layname = '%s_clipd'%rlay_raw.name()
            
        if ofp is None: 
            ofp = os.path.join(self.out_dir,layname+'.sdat')
            
        if os.path.exists(ofp):
            msg = 'requseted filepath exists: %s'%ofp
            if self.overwrite:
                log.warning('DELETING'+msg)
                os.remove(ofp)
            else:
                raise Error(msg)
            
        algo_nm = 'saga:cliprasterwithpolygon'
            

        #=======================================================================
        # precheck
        #=======================================================================
        
        if os.path.exists(ofp):
            msg = 'requested filepath exists: %s'%ofp
            if self.overwrite:
                log.warning(msg)
            else:
                raise Error(msg)
            
        if not os.path.exists(os.path.dirname(ofp)):
            os.makedirs(os.path.dirname(ofp))
            
        #assert QgsRasterLayer.isValidRasterFileName(ofp), 'invalid filename: %s'%ofp
            
        assert 'Poly' in QgsWkbTypes().displayString(poly_vlay.wkbType())
        
        assert rlay_raw.crs() == poly_vlay.crs()
            
            
        #=======================================================================
        # run algo        
        #=======================================================================
        ins_d = { 'INPUT' : rlay_raw, 
                 'OUTPUT' : ofp, 
                 'POLYGONS' : poly_vlay }
        
        log.debug('executing \'%s\' with ins_d: \n    %s \n\n'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        log.debug('finished w/ \n    %s'%res_d)
        
        if not os.path.exists(res_d['OUTPUT']):
            """failing intermittently"""
            raise Error('failed to get a result')
        
        res_rlay = QgsRasterLayer(res_d['OUTPUT'], layname)

        #=======================================================================
        # #post check
        #=======================================================================
        assert isinstance(res_rlay, QgsRasterLayer), 'got bad type: %s'%type(res_rlay)
        assert res_rlay.isValid()
           
   
        res_rlay.setName(layname) #reset the name
           
        log.debug('finished w/ %s'%res_rlay.name())
          
        return res_rlay
    
    
    def srastercalculator(self,
                          formula,
                          rlay_d, #container of raster layers to perform calculations on
                          logger=None,
                          layname=None,
                          ofp=None,
                          ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('srastercalculator')
        
        
        assert 'a' in rlay_d
        
        if layname is None:
            if not ofp is None:
                layname = os.path.splitext(os.path.split(ofp)[1])[0]
            else:
                layname = '%s_calc'%rlay_d['a'].name()
            
        if ofp is None: 
            ofp = os.path.join(self.out_dir, layname+'.sdat')
            
        if not os.path.exists(os.path.dirname(ofp)):
            log.info('building basedir: %s'%os.path.dirname(ofp))
            os.makedirs(os.path.dirname(ofp))
            
        if os.path.exists(ofp):
            msg = 'requseted filepath exists: %s'%ofp
            if self.overwrite:
                log.warning(msg)
                os.remove(ofp)
            else:
                raise Error(msg)
            
        #=======================================================================
        # execute
        #=======================================================================
            
        algo_nm = 'saga:rastercalculator'
        
        
        
        ins_d = { 'FORMULA' : formula, 
                'GRIDS' : rlay_d.pop('a'),
                'RESAMPLING' : 3,
                'RESULT' : ofp,
                'TYPE' : 7,
                'USE_NODATA' : False,
                'XGRIDS' : list(rlay_d.values())}
        
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        log.debug('finished w/ \n    %s'%res_d)
        
        if not os.path.exists(res_d['RESULT']):
            raise Error('failed to get a result')
        

        
        res_rlay = QgsRasterLayer(res_d['RESULT'], layname)

        #=======================================================================
        # #post check
        #=======================================================================
        assert isinstance(res_rlay, QgsRasterLayer), 'got bad type: %s'%type(res_rlay)
        assert res_rlay.isValid()
           
   
        res_rlay.setName(layname) #reset the name
           
        log.debug('finished w/ %s'%res_rlay.name())
          
        return res_rlay
    
    def grastercalculator(self, #GDAL raster calculator
                          formula,
                          rlay_d, #container of raster layers to perform calculations on
                          nodata=0,
                          logger=None,
                          layname=None,

                          ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('grastercalculator')
        algo_nm = 'gdal:rastercalculator'
        
        

        
        if layname is None:
            layname = '%s_calc'%rlay_d['a'].name()
            
            
        #=======================================================================
        # prechecks
        #=======================================================================
        assert 'A' in rlay_d

            
        #=======================================================================
        # populate
        #=======================================================================
        for rtag in ('A', 'B', 'C', 'D', 'E', 'F'):
            #set dummy placeholders for missing rasters
            if not rtag in rlay_d:
                rlay_d[rtag] = None
                
            #check what the usre pasased
            else:
                assert isinstance(rlay_d[rtag], QgsRasterLayer), 'passed bad %s'%rtag
                assert rtag in formula, 'formula is missing a reference to \'%s\''%rtag
                
        #=======================================================================
        # execute
        #=======================================================================
            
        
        
        ins_d = { 'BAND_A' : 1, 'BAND_B' : -1, 'BAND_C' : -1, 'BAND_D' : -1, 'BAND_E' : -1, 'BAND_F' : -1,
                  'EXTRA' : '',
                   'FORMULA' : formula,
                   
                    'INPUT_A' : rlay_d['A'], 'INPUT_B' : rlay_d['B'], 'INPUT_C' :  rlay_d['C'],
                     'INPUT_D' :  rlay_d['D'], 'INPUT_E' :  rlay_d['E'], 'INPUT_F' : rlay_d['F'],
                    
                  
                   'NO_DATA' : nodata,
                    'OPTIONS' : '',
                    'OUTPUT' : 'TEMPORARY_OUTPUT',
                     'RTYPE' : 5 }
        
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        log.debug('finished w/ \n    %s'%res_d)
        
        assert os.path.exists(res_d['OUTPUT']), 'failed to get result'
        
        res_rlay = QgsRasterLayer(res_d['OUTPUT'], layname)
        #=======================================================================
        # #post check
        #=======================================================================
        assert isinstance(res_rlay, QgsRasterLayer), 'got bad type: %s'%type(res_rlay)
        assert res_rlay.isValid()
           
   
        res_rlay.setName(layname) #reset the name
           
        log.debug('finished w/ %s'%res_rlay.name())
          
        return res_rlay
    
    def qrastercalculator(self, #QGIS native raster calculator
                          formula,
                          ref_layer = None, #reference layer
                          logger=None,
                          layname=None,

                          ):
        """executes the algorhithim... better to use the constructor directly
        QgsRasterCalculator"""
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('qrastercalculator')
        algo_nm = 'qgis:rastercalculator'
        
        

        
        if layname is None:
            if ref_layer is None:
                layname = 'qrastercalculator'
            else:
                layname = '%s_calc'%ref_layer.name()
            

        #=======================================================================
        # execute
        #=======================================================================
        """
        formula = '\'haz_100yr_cT2@1\'-\'dtm_cT1@1\''
        """
        
        
        ins_d = { 'CELLSIZE' : 0,
                  'CRS' : None,
                  'EXPRESSION' : formula,
                   'EXTENT' : None,
                  'LAYERS' : [ref_layer], #referecnce layer
                   'OUTPUT' : 'TEMPORARY_OUTPUT' }
        
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        log.debug('finished w/ \n    %s'%res_d)
        
        if not os.path.exists(res_d['RESULT']):
            raise Error('failed to get a result')
        

        
        res_rlay = QgsRasterLayer(res_d['RESULT'], layname)

        #=======================================================================
        # #post check
        #=======================================================================
        assert isinstance(res_rlay, QgsRasterLayer), 'got bad type: %s'%type(res_rlay)
        assert res_rlay.isValid()
           
   
        res_rlay.setName(layname) #reset the name
           
        log.debug('finished w/ %s'%res_rlay.name())
          
        return res_rlay
    
    
    def addgeometrycolumns(self, #add geometry data as columns
                           vlay,
                           layname=None,
                           logger=None,
                           ): 
        if logger is None: logger=self.logger
        log = logger.getChild('addgeometrycolumns')
        
        algo_nm = 'qgis:exportaddgeometrycolumns'

        

        #=======================================================================
        # assemble pars
        #=======================================================================
        #assemble pars
        ins_d = { 'CALC_METHOD' : 0,  #use layer's crs
                 'INPUT' : vlay, 
                 'OUTPUT' : 'TEMPORARY_OUTPUT'}
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        res_vlay = res_d['OUTPUT']
        

        
        #===========================================================================
        # post formatting
        #===========================================================================
        if layname is None: 
            layname = '%s_gcol'%self.vlay.name()
            
        res_vlay.setName(layname) #reset the name


        return res_vlay
    
    def buffer(self, vlay,
                    distance, #buffer distance to apply
                      dissolve = False,
                      end_cap_style = 0,
                      join_style = 0,
                      miter_limit = 2,
                      segments = 5,
                      logger=None, 
                      layname=None,
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        
        if layname is None: 
            layname = '%s_buf'%vlay.name()
        
        algo_nm = 'native:buffer'
        log = self.logger.getChild('buffer')
        
        distance = float(distance)
        

        #=======================================================================
        # prechecks
        #=======================================================================
        if distance==0 or np.isnan(distance):
            raise Error('got no buffer!')
        
        
        #=======================================================================
        # build ins
        #=======================================================================
        """
        distance = 3.0
        
        dcopoy = copy.copy(distance)
        """
        
        ins_d = { 
            'INPUT': vlay,
            'DISSOLVE' : dissolve, 
            'DISTANCE' : distance, 
            'END_CAP_STYLE' : end_cap_style, 
            'JOIN_STYLE' : join_style, 
            'MITER_LIMIT' : miter_limit, 
            'OUTPUT' : 'TEMPORARY_OUTPUT', 
            'SEGMENTS' : segments}
        
        #=======================================================================
        # execute
        #=======================================================================
        log.debug('executing \'native:buffer\' with ins_d: \n    %s'%ins_d)
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        res_vlay = res_d['OUTPUT']

        res_vlay.setName(layname) #reset the name

        log.debug('finished')
        return res_vlay
    
    
    def selectbylocation(self, #select features (from main laye) by geoemtric relation with comp_vlay
                vlay, #vlay to select features from
                comp_vlay, #vlay to compare 
                
                result_type = 'select',
                
                method= 'new',  #Modify current selection by
                pred_l = ['intersect'],  #list of geometry predicate names
                
                #expectations
                allow_none = False,
                
                logger = None,

                ):
        
        #=======================================================================
        # setups and defaults
        #=======================================================================
        if logger is None: logger=self.logger    
        algo_nm = 'native:selectbylocation'   
        log = logger.getChild('selectbylocation')
        
        #===========================================================================
        # #set parameter translation dictoinaries
        #===========================================================================
        meth_d = {'new':0}
            
        pred_d = {
                'are within':6,
                'intersect':0,
                'overlap':5,
                  }
        
        #predicate (name to value)
        pred_l = [pred_d[pred_nm] for pred_nm in pred_l]
    
        #=======================================================================
        # setup
        #=======================================================================
        ins_d = { 
            'INPUT' : vlay, 
            'INTERSECT' : comp_vlay, 
            'METHOD' : meth_d[method], 
            'PREDICATE' : pred_l }
        
        log.debug('executing \'%s\' on \'%s\' with: \n     %s'
            %(algo_nm, vlay.name(), ins_d))
            
        #===========================================================================
        # #execute
        #===========================================================================
        _ = processing.run(algo_nm, ins_d,  feedback=self.feedback)
        
        
        #=======================================================================
        # check
        #=======================================================================
        fcnt = vlay.selectedFeatureCount()
        
        if fcnt == 0:
            msg = 'No features selected!'
            if allow_none:
                log.warning(msg)
            else:
                raise Error(msg)
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.debug('selected %i (of %i) features from %s'
            %(vlay.selectedFeatureCount(),vlay.dataProvider().featureCount(), vlay.name()))
        
        return self._get_sel_res(vlay, result_type=result_type, logger=log, allow_none=allow_none)
        
    def saveselectedfeatures(self,#generate a memory layer from the current selection
                             vlay,
                             logger=None,
                             allow_none = False,
                             layname=None): 
        
        
        
        #===========================================================================
        # setups and defaults
        #===========================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('saveselectedfeatures')
        algo_nm = 'native:saveselectedfeatures'
        
        if layname is None: 
            layname = '%s_sel'%vlay.name()
              
        #=======================================================================
        # precheck
        #=======================================================================
        fcnt = vlay.selectedFeatureCount()
        if fcnt == 0:
            msg = 'No features selected!'
            if allow_none:
                log.warning(msg)
                return None
            else:
                raise Error(msg)
        
        log.debug('on \'%s\' with %i feats selected'%(
            vlay.name(), vlay.selectedFeatureCount()))
        #=======================================================================
        # # build inputs
        #=======================================================================
        ins_d = {'INPUT' : vlay,
                 'OUTPUT' : 'TEMPORARY_OUTPUT'}
        
        log.debug('\'native:saveselectedfeatures\' on \'%s\' with: \n   %s'
            %(vlay.name(), ins_d))
        
        #execute
        res_d = processing.run(algo_nm, ins_d,  feedback=self.feedback)

        
        res_vlay = res_d['OUTPUT']
        
        assert isinstance(res_vlay, QgsVectorLayer)
        #===========================================================================
        # wrap
        #===========================================================================

        res_vlay.setName(layname) #reset the name

        return res_vlay
    
    def polygonfromlayerextent(self,
                             vlay,
                             round_to=0, #adds a buffer to the result?
                             logger=None,
                             layname=None): 
        """
        This algorithm takes a map layer and generates a new vector layer with the
         minimum bounding box (rectangle polygon with N-S orientation) that covers the input layer.
          Optionally, the extent can be enlarged to a rounded value.
        """
        
        #===========================================================================
        # setups and defaults
        #===========================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('polygonfromlayerextent')
        algo_nm = 'qgis:polygonfromlayerextent'
        
        if layname is None: 
            layname = '%s_exts'%vlay.name()
              
        #=======================================================================
        # precheck
        #=======================================================================
        

        #=======================================================================
        # # build inputs
        #=======================================================================
        ins_d = {'INPUT' : vlay,
                 'OUTPUT' : 'TEMPORARY_OUTPUT',
                 'ROUND_TO':round_to}
        
        log.debug('\'%s\' on \'%s\' with: \n   %s'
            %(algo_nm, vlay.name(), ins_d))
        
        #execute
        res_d = processing.run(algo_nm, ins_d,  feedback=self.feedback)

        
        res_vlay = res_d['OUTPUT']
        
        assert isinstance(res_vlay, QgsVectorLayer)
        #===========================================================================
        # wrap
        #===========================================================================

        res_vlay.setName(layname) #reset the name

        return res_vlay
    
    def fixgeometries(self, vlay,

                      logger=None, 
                      layname=None,
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        
        if layname is None: 
            layname = '%s_fix'%vlay.name()
        
        algo_nm = 'native:fixgeometries'
        log = self.logger.getChild('fixgeometries')



        
        
        #=======================================================================
        # build ins
        #=======================================================================
        """
        distance = 3.0
        
        dcopoy = copy.copy(distance)
        """
        
        ins_d = { 
            'INPUT': vlay,
            'OUTPUT' : 'TEMPORARY_OUTPUT',
            }
        
        #=======================================================================
        # execute
        #=======================================================================
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        res_vlay = res_d['OUTPUT']

        res_vlay.setName(layname) #reset the name

        log.debug('finished')
        return res_vlay
    
    def createspatialindex(self,
                     in_vlay,
                     logger=None,
                     ):

        #=======================================================================
        # presets
        #=======================================================================
        algo_nm = 'qgis:createspatialindex'
        if logger is None: logger=self.logger
        log = self.logger.getChild('createspatialindex')
        in_vlay

 
        #=======================================================================
        # assemble pars
        #=======================================================================
        #assemble pars
        ins_d = { 'INPUT' : in_vlay }
        
        log.debug('executing \'%s\' with ins_d: \n    %s'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        
        #===========================================================================
        # post formatting
        #===========================================================================
        #=======================================================================
        # if layname is None: 
        #     layname = '%s_si'%self.vlay.name()
        #     
        # res_vlay.setName(layname) #reset the name
        #=======================================================================

        
        return 


    def warpreproject(self, #repojrect a raster
                              rlay_raw,
                              
                              crsOut = None, #crs to re-project to
                              layname = None,
                              options = 'COMPRESS=DEFLATE|PREDICTOR=2|ZLEVEL=9',
                              output = 'TEMPORARY_OUTPUT',
                              logger = None,
                              ):

        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('warpreproject')
        
        if layname is None:
            layname = '%s_rproj'%rlay_raw.name()
            
            
        algo_nm = 'gdal:warpreproject'
            
        if crsOut is None: crsOut = self.crs #just take the project's
        #=======================================================================
        # precheck
        #=======================================================================
        """the algo accepts 'None'... but not sure why we'd want to do this"""
        assert isinstance(crsOut, QgsCoordinateReferenceSystem), 'bad crs type'
        assert isinstance(rlay_raw, QgsRasterLayer)

        assert rlay_raw.crs() != crsOut, 'layer already on this CRS!'
            
            
        #=======================================================================
        # run algo        
        #=======================================================================

        
        ins_d =  {
             'DATA_TYPE' : 0,
             'EXTRA' : '',
             'INPUT' : rlay_raw,
             'MULTITHREADING' : False,
             'NODATA' : None,
             'OPTIONS' : options,
             'OUTPUT' : output,
             'RESAMPLING' : 0,
             'SOURCE_CRS' : None,
             'TARGET_CRS' : crsOut,
             'TARGET_EXTENT' : None,
             'TARGET_EXTENT_CRS' : None,
             'TARGET_RESOLUTION' : None,
          }
        
        log.debug('executing \'%s\' with ins_d: \n    %s \n\n'%(algo_nm, ins_d))
        
        res_d = processing.run(algo_nm, ins_d, feedback=self.feedback)
        
        log.debug('finished w/ \n    %s'%res_d)
        
        if not os.path.exists(res_d['OUTPUT']):
            """failing intermittently"""
            raise Error('failed to get a result')
        
        res_rlay = QgsRasterLayer(res_d['OUTPUT'], layname)

        #=======================================================================
        # #post check
        #=======================================================================
        assert isinstance(res_rlay, QgsRasterLayer), 'got bad type: %s'%type(res_rlay)
        assert res_rlay.isValid()
        assert rlay_raw.bandCount()==res_rlay.bandCount(), 'band count mismatch'
           
   
        res_rlay.setName(layname) #reset the name
           
        log.debug('finished w/ %s'%res_rlay.name())
          
        return res_rlay
    
    #===========================================================================
    # ALGOS - CUSTOM--------
    #===========================================================================
    def vlay_pts_dist(self, #get the distance between points in a given order
        vlay_raw, 
        ifn = 'fid', #fieldName to index by
        request = None,
        
        result = 'vlay_append', #result type
        logger=None):
        #===========================================================================
        # defaults
        #===========================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('vlay_pts_dist')
        
        
        if request is None: 
            request =  QgsFeatureRequest(
                ).addOrderBy(ifn, ascending=True
                             ).setSubsetOfAttributes([ifn], vlay_raw.fields())
                             
        #===========================================================================
        # precheck
        #===========================================================================
        assert 'Point' in QgsWkbTypes().displayString(vlay_raw.wkbType()), 'passed bad geo type'
        
        #see if indexer is unique
        ifn_d = vlay_get_fdata(vlay_raw, fieldn=ifn, logger=log)
        assert len(set(ifn_d.values()))==len(ifn_d)
        #===========================================================================
        # loop and calc
        #===========================================================================
        
        d = dict()
        first, geo_prev = True, None 
        for i, feat in enumerate(vlay_raw.getFeatures(request)):
            assert not feat.attribute(ifn) in d, 'indexer is not unique!'
            geo = feat.geometry()
            if first:
                first=False
            else:
                d[feat.attribute(ifn)] = geo.distance(geo_prev)
                
            geo_prev = geo
    
        log.info('got %i distances using \"%s\''%(len(d), ifn))
        #===========================================================================
        # check
        #===========================================================================
        assert len(d) == (vlay_raw.dataProvider().featureCount() -1)
        
        
        #===========================================================================
        # results typing 
        #===========================================================================
        if result == 'dict': return d
        elif result == 'vlay_append':
            #data manip
            ncoln = '%s_dist'%ifn
            df_raw = vlay_get_fdf(vlay_raw, logger=log)
            df = df_raw.join(pd.Series(d, name=ncoln), on=ifn)
            
            assert df[ncoln].isna().sum()==1, 'expected 1 null'
            
            #reassemble
            geo_d = vlay_get_fdata(vlay_raw, geo_obj=True, logger=log)
            return self.vlay_new_df2(df, geo_d=geo_d, logger=log,
                                   layname='%s_%s'%(vlay_raw.name(), ncoln))
    
    
    
    #==========================================================================
    # privates----------
    #==========================================================================
    def _field_handlr(self, #common handling for fields
                      vlay, #layer to check for field presence
                      fieldn_l, #list of fields to handle
                      invert = False,
                      logger=None,
                      ):
        if logger is None: logger=self.logger
        log = logger.getChild('_field_handlr')

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
        
        
    
    
        #vlay_check(vlay, exp_fieldns=fieldn_l)
        
        
        #=======================================================================
        # #handle inversions
        #=======================================================================
        if invert:
            big_fn_s = set(vlay_fieldnl(vlay)) #get all the fields

            #get the difference
            fieldn_l = list(big_fn_s.difference(set(fieldn_l)))
            
            log.debug('inverted selection from %i to %i fields'%
                      (len(big_fn_s),  len(fieldn_l)))
            
            
        
        
        return fieldn_l
    
    def _get_sel_obj(self, vlay): #get the processing object for algos with selections
        
        log = self.logger.getChild('_get_sel_obj')
        
        assert isinstance(vlay, QgsVectorLayer)
        if vlay.selectedFeatureCount() == 0:
            raise Error('Nothing selected on \'%s\'. exepects some pre selection'%(vlay.name()))
 
        
        #handle project layer store
        if self.qproj.mapLayer(vlay.id()) is None:
            #layer not on project yet. add it
            if self.qproj.addMapLayer(vlay, False) is None:
                raise Error('failed to add map layer \'%s\''%vlay.name())
            

        log.debug('based on %i selected features from \'%s\''%(len(vlay.selectedFeatureIds()), vlay.name()))
        
        return QgsProcessingFeatureSourceDefinition(source=vlay.id(), 
                                                    selectedFeaturesOnly=True, 
                                                    featureLimit=-1, 
                                                    geometryCheck=QgsFeatureRequest.GeometryAbortOnInvalid)
        
 
    
    
    def _get_sel_res(self, #handler for returning selection like results
                        vlay, #result layer (with selection on it
                         result_type='select',
                         
                         #expectiions
                         allow_none = False,
                         logger=None
                         ):
        
        #=======================================================================
        # setup
        #=======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('_get_sel_res')
        #=======================================================================
        # precheck
        #=======================================================================
        if vlay.selectedFeatureCount() == 0:
            if not allow_none:
                raise Error('nothing selected')
            
            return None

        
        #log.debug('user specified \'%s\' for result_type'%result_type)
        #=======================================================================
        # by handles
        #=======================================================================
        if result_type == 'select':
            #log.debug('user specified \'select\', doing nothing with %i selected'%vlay.selectedFeatureCount())
            
            result = None
            
        elif result_type == 'fids':
            
            result = vlay.selectedFeatureIds() #get teh selected feature ids
            
        elif result_type == 'feats':
            
            result =  {feat.id(): feat for feat in vlay.getSelectedFeatures()}
            
            
        elif result_type == 'layer':
            
            result = self.saveselectedfeatures(vlay, logger=log)
            
        else: 
            raise Error('unexpected result_type kwarg')
            
        return result
    
    def _in_out_checking(self,res_vlay,
                         ):
        """placeholder"""
        
    def __exit__(self, #destructor
                 *args,**kwargs):
        
        self.mstore.removeAllMapLayers()
        
        super().__exit__(*args,**kwargs) #initilzie teh baseclass

    

class MyFeedBackQ(QgsProcessingFeedback):
    """
    wrapper for easier reporting and extended progress
    
    Dialogs:
        built by QprojPlug.qproj_setup()
    
    Qworkers:
        built by Qcoms.__init__()
    
    """
    
    def __init__(self,
                 logger=mod_logger):
        
        self.logger=logger.getChild('FeedBack')
        
        super().__init__()

    def setProgressText(self, text):
        self.logger.debug(text)

    def pushInfo(self, info):
        self.logger.info(info)

    def pushCommandInfo(self, info):
        self.logger.info(info)

    def pushDebugInfo(self, info):
        self.logger.info(info)

    def pushConsoleInfo(self, info):
        self.logger.info(info)

    def reportError(self, error, fatalError=False):
        self.logger.error(error)
        
    
    def upd_prog(self, #advanced progress handling
             prog_raw, #pass None to reset
             method='raw', #whether to append value to the progress
             ): 
            
        #=======================================================================
        # defaults
        #=======================================================================
        #get the current progress
        progress = self.progress() 
    
        #===================================================================
        # prechecks
        #===================================================================
        #make sure we have some slots connected
        """not sure how to do this"""
        
        #=======================================================================
        # reseting
        #=======================================================================
        if prog_raw is None:
            """
            would be nice to reset the progressBar.. .but that would be complicated
            """
            self.setProgress(0)
            return
        
        #=======================================================================
        # setting
        #=======================================================================
        if method=='append':
            prog = min(progress + prog_raw, 100)
        elif method=='raw':
            prog = prog_raw
        elif method == 'portion':
            rem_prog = 100-progress
            prog = progress + rem_prog*(prog_raw/100)
            
        assert prog<=100
        
        #===================================================================
        # emit signalling
        #===================================================================
        self.setProgress(prog)
        



        
        

#==============================================================================
# FUNCTIONS----------
#==============================================================================

def init_q(gui=False):
    try:
        
        QgsApplication.setPrefixPath(r'C:/OSGeo4W64/apps/qgis-ltr', True)
        
        app = QgsApplication([], gui)
        #   Update prefix path
        #app.setPrefixPath(r"C:\OSGeo4W64\apps\qgis", True)
        app.initQgis()
        #logging.debug(QgsApplication.showSettings())
        """ was throwing unicode error"""
        print(u' QgsApplication.initQgis. version: %s, release: %s'%(
            Qgis.QGIS_VERSION.encode('utf-8'), Qgis.QGIS_RELEASE_NAME.encode('utf-8')))
        return app
    
    except:
        raise Error('QGIS failed to initiate')
        
def vlay_check( #helper to check various expectations on the layer
                    vlay,
                    exp_fieldns = None, #raise error if these field names are OUT
                    uexp_fieldns = None, #raise error if these field names are IN
                    real_atts = None, #list of field names to check if attribute value are all real
                    bgeot = None, #basic geo type checking
                    fcnt = None, #feature count checking. accepts INT or QgsVectorLayer
                    fkey = None, #optional secondary key to check 
                    mlay = False, #check if its a memory layer or not
                    chk_valid = False, #check layer validty
                    logger = mod_logger, 
                    db_f = False,
                    ):
    #=======================================================================
    # prechecks
    #=======================================================================
    if vlay is None:
        raise Error('got passed an empty vlay')
    
    if not isinstance(vlay, QgsVectorLayer):
        raise Error('unexpected type: %s'%type(vlay))
    
    log = logger.getChild('vlay_check')
    checks_l = []
    

    #=======================================================================
    # expected field names
    #=======================================================================
    if not basic.is_null(exp_fieldns): #robust null checking
        skip=False
        if isinstance(exp_fieldns, str):
            if exp_fieldns=='all':
                skip=True
            
        
        
        if not skip:
            fnl = basic.linr(exp_fieldns, vlay_fieldnl(vlay),
                                      'expected field names', vlay.name(),
                                      result_type='missing', logger=log, fancy_log=db_f)
            
            if len(fnl)>0:
                raise Error('%s missing expected fields: %s'%(
                    vlay.name(), fnl))
                
            checks_l.append('exp_fieldns=%i'%len(exp_fieldns))
        
    #=======================================================================
    # unexpected field names
    #=======================================================================
        
    if not basic.is_null(uexp_fieldns): #robust null checking
        #fields on the layer
        if len(vlay_fieldnl(vlay))>0:
        
            fnl = basic.linr(uexp_fieldns, vlay_fieldnl(vlay),
                                      'un expected field names', vlay.name(),
                                      result_type='matching', logger=log, fancy_log=db_f)
            
            if len(fnl)>0:
                raise Error('%s contains unexpected fields: %s'%(
                    vlay.name(), fnl))
                
        #no fields on the layer
        else:
            pass
            
        checks_l.append('uexp_fieldns=%i'%len(uexp_fieldns))
        
    
    #=======================================================================
    # null value check
    #=======================================================================
    #==========================================================================
    # if not real_atts is None:
    #     
    #     #pull this data
    #     df = vlay_get_fdf(vlay, fieldn_l = real_atts, logger=log)
    #     
    #     #check for nulls
    #     if np.any(df.isna()):
    #         raise Error('%s got %i nulls on %i expected real fields: %s'%(
    #             vlay.name(), df.isna().sum().sum(), len(real_atts), real_atts))
    #         
    #     
    #     checks_l.append('real_atts=%i'%len(real_atts))
    #==========================================================================

            
            
    #=======================================================================
    # basic geometry type
    #=======================================================================
    #==========================================================================
    # if not bgeot is None:
    #     bgeot_lay =  vlay_get_bgeo_type(vlay)
    #     
    #     if not bgeot == bgeot_lay:
    #         raise Error('basic geometry type expectation \'%s\' does not match layers \'%s\''%(
    #             bgeot, bgeot_lay))
    #         
    #     checks_l.append('bgeot=%s'%bgeot)
    #==========================================================================
            
    #=======================================================================
    # feature count
    #=======================================================================
    if not fcnt is None:
        if isinstance(fcnt, QgsVectorLayer):
            fcnt=fcnt.dataProvider().featureCount()
        
        if not fcnt == vlay.dataProvider().featureCount():
            raise Error('\'%s\'s feature count (%i) does not match %i'%(
                vlay.name(), vlay.dataProvider().featureCount(), fcnt))
            
        checks_l.append('fcnt=%i'%fcnt)
        
    #=======================================================================
    # fkey
    #=======================================================================
#==============================================================================
#     if isinstance(fkey, str):
#         fnl = vlay_fieldnl(vlay)
#         
#         if not fkey in fnl:
#             raise Error('fkey \'%s\' not in the fields'%fkey)
#         
#         fkeys_ser = vlay_get_fdata(vlay, fkey, logger=log, fmt='ser').sort_values()
#         
#         if not np.issubdtype(fkeys_ser.dtype, np.number):
#             raise Error('keys are non-numeric. type: %s'%fkeys_ser.dtype)
#         
#         if not fkeys_ser.is_unique:
#             raise Error('\'%s\' keys are not unique'%fkey)
# 
#         if not fkeys_ser.is_monotonic:
#             raise Error('fkeys are not monotonic')
#         
#         if np.any(fkeys_ser.isna()):
#             raise Error('fkeys have nulls')
#         
#         checks_l.append('fkey \'%s\'=%i'%(fkey, len(fkeys_ser)))
#==============================================================================
        
    #=======================================================================
    # storage type
    #=======================================================================
    if mlay:
        if not 'Memory' in vlay.dataProvider().storageType():
            raise Error('\"%s\' unexpected storage type: %s'%(
                vlay.name(), vlay.dataProvider().storageType()))
        
        checks_l.append('mlay')
        
    #=======================================================================
    # validty
    #=======================================================================
    #==========================================================================
    # if chk_valid:
    #     vlay_chk_validty(vlay, chk_geo=True)
    #     
    #     checks_l.append('validity')
    #==========================================================================
        
    
    #=======================================================================
    # wrap
    #=======================================================================

    log.debug('\'%s\' passed %i checks: %s'%(
        vlay.name(), len(checks_l), checks_l))
    return
    
def load_vlay( #load a layer from a file
        fp,
        providerLib='ogr',
        logger=mod_logger):
    """
    what are we using this for?
    
    see instanc emethod
    """
    log = logger.getChild('load_vlay') 
    
    
    assert os.path.exists(fp), 'requested file does not exist: %s'%fp

    
    basefn = os.path.splitext(os.path.split(fp)[1])[0]
    

    #Import a Raster Layer
    vlay_raw = QgsVectorLayer(fp,basefn,providerLib)
    
    #check if this is valid
    if not vlay_raw.isValid():
        log.error('loaded vlay \'%s\' is not valid. \n \n did you initilize?'%vlay_raw.name())
        raise Error('vlay loading produced an invalid layer')
    
    #check if it has geometry
    if vlay_raw.wkbType() == 100:
        log.error('loaded vlay has NoGeometry')
        raise Error('no geo')
    
    #==========================================================================
    # report
    #==========================================================================
    vlay = vlay_raw
    dp = vlay.dataProvider()

    log.info('loaded vlay \'%s\' as \'%s\' %s geo  with %i feats from file: \n     %s'
                %(vlay.name(), dp.storageType(), QgsWkbTypes().displayString(vlay.wkbType()), dp.featureCount(), fp))
    
    return vlay


def vlay_write( #write  a VectorLayer
        vlay, out_fp, 

        driverName='GPKG',
        fileEncoding = "CP1250", 
        opts = QgsVectorFileWriter.SaveVectorOptions(), #empty options object
        overwrite=False,
        logger=mod_logger):
    """
    help(QgsVectorFileWriter.SaveVectorOptions)
    QgsVectorFileWriter.SaveVectorOptions.driverName='GPKG'
    
    
    opt2 = QgsVectorFileWriter.BoolOption(QgsVectorFileWriter.CreateOrOverwriteFile)
    
    help(QgsVectorFileWriter)
    
    TODO: Move this back onto Qcoms
    
    """
    
    #==========================================================================
    # defaults
    #==========================================================================
    log = logger.getChild('vlay_write')
    

    
    #===========================================================================
    # assemble options
    #===========================================================================
    opts.driverName = driverName
    opts.fileEncoding = fileEncoding
    
    
    #===========================================================================
    # checks
    #===========================================================================
    #file extension
    fhead, ext = os.path.splitext(out_fp)
    
    if not 'gpkg' in ext:
        raise Error('unexpected extension: %s'%ext)
    
    if os.path.exists(out_fp):
        msg = 'requested file path already exists!. overwrite=%s \n    %s'%(
            overwrite, out_fp)
        if overwrite:
            log.warning(msg)
            os.remove(out_fp) #workaround... should be away to overwrite with the QgsVectorFileWriter
        else:
            raise Error(msg)
        
    
    if vlay.dataProvider().featureCount() == 0:
        raise Error('\'%s\' has no features!'%(
            vlay.name()))
        
    if not vlay.isValid():
        Error('passed invalid layer')
        

    
    error = QgsVectorFileWriter.writeAsVectorFormatV2(
            vlay, out_fp, 
            QgsCoordinateTransformContext(),
            opts,
            )
    
    
    #=======================================================================
    # wrap and check
    #=======================================================================
      
    if error[0] == QgsVectorFileWriter.NoError:
        log.info('layer \' %s \' written to: \n     %s'%(vlay.name(),out_fp))
        return out_fp
     
    raise Error('FAILURE on writing layer \' %s \'  with code:\n    %s \n    %s'%(vlay.name(),error, out_fp))
    
    
    
    
def vlay_get_fdf( #pull all the feature data and place into a df
                    vlay,
                    fmt='df', #result fomrat key. 
                        #dict: {fid:{fieldname:value}}
                        #df: index=fids, columns=fieldnames
                    
                    #limiters
                    request = None, #request to pull data. for more customized requestes.
                    fieldn_l = None, #or field name list. for generic requests
                    
                    #modifiers
                    reindex = None, #optinal field name to reindex df by
                    
                    #expectations
                    expect_all_real = False, #whether to expect all real results
                    allow_none = False,
                    
                    db_f = False,
                    logger=mod_logger,
                    feedback=MyFeedBackQ()):
    """
    performance improvement
    
    Warning: requests with getFeatures arent working as expected for memory layers
    
    this could be combined with vlay_get_feats()
    also see vlay_get_fdata() (for a single column)
    
    
    RETURNS
    a dictionary in the Qgis attribute dictionary format:
        key: generally feat.id()
        value: a dictionary of {field name: attribute value}

    """
    #===========================================================================
    # setups and defaults
    #===========================================================================
    log = logger.getChild('vlay_get_fdf')
    
    assert isinstance(vlay, QgsVectorLayer)
    all_fnl = [fieldn.name() for fieldn in vlay.fields().toList()]
    
    if fieldn_l is None: #use all the fields
        fieldn_l = all_fnl
        
    else:
        vlay_check(vlay, fieldn_l, logger=logger, db_f=db_f)
        

    
    if allow_none:
        if expect_all_real:
            raise Error('cant allow none and expect all reals')
        
    
    #===========================================================================
    # prechecks
    #===========================================================================
    if not reindex is None:
        if not reindex in fieldn_l:
            raise Error('requested reindexer \'%s\' is not a field name'%reindex)
    
    if not vlay.dataProvider().featureCount()>0:
        raise Error('no features!')

    if len(fieldn_l) == 0:
        raise Error('no fields!')
    
    if fmt=='dict' and not (len(fieldn_l)==len(all_fnl)):
        raise Error('dict results dont respect field slicing')
    
    assert hasattr(feedback, 'setProgress')
    
    #===========================================================================
    # build the request
    #===========================================================================
    feedback.setProgress(2)
    if request is None:
        """WARNING: this doesnt seem to be slicing the fields.
        see Alg().deletecolumns()
            but this will re-key things
        
        request = QgsFeatureRequest().setSubsetOfAttributes(fieldn_l,vlay.fields())"""
        request = QgsFeatureRequest()
        
    #never want geometry   
    request = request.setFlags(QgsFeatureRequest.NoGeometry) 
               

    log.debug('extracting data from \'%s\' on fields: %s'%(vlay.name(), fieldn_l))
    #===========================================================================
    # loop through each feature and extract the data
    #===========================================================================
    
    fid_attvs = dict() #{fid : {fieldn:value}}
    fcnt = vlay.dataProvider().featureCount()

    for indxr, feat in enumerate(vlay.getFeatures(request)):
        
        #zip values
        fid_attvs[feat.id()] = feat.attributes()
        
        feedback.setProgress((indxr/fcnt)*90)


    #===========================================================================
    # post checks
    #===========================================================================
    if not len(fid_attvs) == vlay.dataProvider().featureCount():
        log.debug('data result length does not match feature count')

        if not request.filterType()==3: #check if a filter fids was passed
            """todo: add check to see if the fiter request length matches tresult"""
            raise Error('no filter and data length mismatch')
        
    #check the field lengthes
    if not len(all_fnl) == len(feat.attributes()):
        raise Error('field length mismatch')

    #empty check 1
    if len(fid_attvs) == 0:
        log.warning('failed to get any data on layer \'%s\' with request'%vlay.name())
        if not allow_none:
            raise Error('no data found!')
        else:
            if fmt == 'dict': 
                return dict()
            elif  fmt == 'df':
                return pd.DataFrame()
            else:
                raise Error('unexpected fmt type')
            
    
    #===========================================================================
    # result formatting
    #===========================================================================
    log.debug('got %i data elements for \'%s\''%(
        len(fid_attvs), vlay.name()))
    
    if fmt == 'dict':
        
        return fid_attvs
    elif fmt=='df':
        
        #build the dict
        
        df_raw = pd.DataFrame.from_dict(fid_attvs, orient='index', columns=all_fnl)
        
        
        #handle column slicing and Qnulls
        """if the requester worked... we probably  wouldnt have to do this"""
        df = df_raw.loc[:, tuple(fieldn_l)].replace(NULL, np.nan)
        
        feedback.setProgress(95)
        
        if isinstance(reindex, str):
            """
            reindex='zid'
            view(df)
            """
            #try and add the index (fids) as a data column
            try:
                df = df.join(pd.Series(df.index,index=df.index, name='fid'))
            except:
                log.debug('failed to preserve the fids.. column already there?')
            
            #re-index by the passed key... should copy the fids over to 'index
            df = df.set_index(reindex, drop=True)
            
            log.debug('reindexed data by \'%s\''%reindex)
            
        return df
    
    else:
        raise Error('unrecognized fmt kwarg')

    
    
def vlay_get_fdata( #get data for a single field from all the features
            vlay,
            fieldn = None, #get a field name. 'None' returns a dictionary of np.nan
            geopropn = None, #get a geometry property
            geo_obj = False, #whether to just get the geometry object
            request = None, #additional requester (limiting fids). fieldn still required. additional flags added
            selected= False, #whether to limit data to just those selected features
            fmt = 'dict', #format to return results in
                #'singleton' expect and aprovide a unitary value
                
            rekey = None, #field name to rekey dictionary like results by
                
            expect_all_real = False, #whether to expect all real results
            dropna = False, #whether to drop nulls from the results
            allow_none = False,
            
            logger = mod_logger, db_f=False):
    
    """
    TODO: combine this with vlay_get_fdatas
    consider combining with vlay_get_feats
    
    I'm not sure how this will handle requests w/ expressions
    """
    
    log = logger.getChild('vlay_get_fdata')
    
    if request is None:
        request = QgsFeatureRequest()
    
    #===========================================================================
    # prechecks
    #===========================================================================
    if geo_obj:
        if fmt == 'df': raise IOError
        if not geopropn is None: raise IOError
        
    if dropna:
        if expect_all_real:
            raise Error('cant expect_all_reals AND dropna')
    
    if allow_none:
        if expect_all_real:
            raise Error('cant allow none and expect all reals')
        
    vlay_check(vlay, exp_fieldns=[fieldn], logger=log, db_f=db_f)
    
    #===========================================================================
    # build the request
    #===========================================================================
    #no geometry
    if (geopropn is None) and (not geo_obj): 
        
        if fieldn is None: 
            raise Error('no field name provided')
        

        request = request.setFlags(QgsFeatureRequest.NoGeometry)
        request = request.setSubsetOfAttributes([fieldn],vlay.fields())
        
    else:
        
        request = request.setNoAttributes() #dont get any attributes
        
    #===========================================================================
    # selection limited
    #===========================================================================
    if selected:
        """
        todo: check if there is already a fid filter placed on the reuqester
        """
        log.debug('limiting data pull to %i selected features on \'%s\''%(
            vlay.selectedFeatureCount(), vlay.name()))
        
        sfids = vlay.selectedFeatureIds()
        
        request = request.setFilterFids(sfids)
        
    #===========================================================================
    # loop through and collect hte data
    #===========================================================================
    #if db_f: req_log(request, logger=log)
    d = dict() #empty container for results
    for feat in vlay.getFeatures(request):
        
        #=======================================================================
        # get geometry
        #=======================================================================
        if geo_obj:
            d[feat.id()] = feat.geometry()
            
        #=======================================================================
        # get a geometry property
        #=======================================================================
        elif not geopropn is None:
            geo = feat.geometry()
            
            func = getattr(geo, geopropn) #get the method
            
            d[feat.id()] = func() #call the method and store

            
        #=======================================================================
        # field request
        #=======================================================================
        else:
            #empty shortcut
            if qisnull(feat.attribute(fieldn)): 
                d[feat.id()] = np.nan
            else: #pull real data
                d[feat.id()] = feat.attribute(fieldn)
        

    log.debug('retrieved %i attributes from features on \'%s\''%(
        len(d), vlay.name()))
              
    #===========================================================================
    # null handling
    #===========================================================================
    if selected:
        if not len(d) == vlay.selectedFeatureCount():
            raise Error('failed to get data matching %i selected features'%(
                vlay.selectedFeatureCount()))
    
    if expect_all_real:
        boolar = pd.isnull(np.array(list(d.values()))) 
        if np.any(boolar):
            raise Error('got %i nulls'%boolar.sum())
        
    if dropna:
        """faster to use dfs?"""
        log.debug('dropping nulls from %i'%len(d))
        
        d2 = dict()
        
        for k, v in d.items():
            if np.isnan(v):
                continue
            d2[k] = v
            
        d = d2 #reset
        
    #===========================================================================
    # post checks
    #===========================================================================
    if len(d) == 0:
        log.warning('got no results! from \'%s\''%(
            vlay.name()))
        if not allow_none:
            raise Error('allow_none=FALSE and no results')
        
        """
        view(vlay)
        """
        
    #===========================================================================
    # rekey
    #===========================================================================
    if isinstance(rekey, str):
        assert fmt=='dict'
        
        d, _ = vlay_key_convert(vlay, d, rekey, id1_type='fid', logger=log)
        
        
    
    #===========================================================================
    # results
    #===========================================================================

  
    
    if fmt == 'dict': 
        return d
    elif fmt == 'df': 
        return pd.DataFrame(pd.Series(d, name=fieldn))
    elif fmt == 'singleton':
        if not len(d)==1:
            raise Error('expected singleton')
        return next(iter(d.values()))
    
    elif fmt == 'ser': 
        return pd.Series(d, name=fieldn)
    else: 
        raise IOError
    
def vlay_new_mlay(#create a new mlay
                      gtype, #"Point", "LineString", "Polygon", "MultiPoint", "MultiLineString", or "MultiPolygon".
                      crs,
                      layname,
                      qfields,
                      feats_l,

                      logger=mod_logger,
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = logger.getChild('vlay_new_mlay')

        #=======================================================================
        # prechecks
        #=======================================================================
        if not isinstance(layname, str):
            raise Error('expected a string for layname, isntead got %s'%type(layname))
        
        if gtype=='None':
            log.warning('constructing mlay w/ \'None\' type')
        #=======================================================================
        # assemble into new layer
        #=======================================================================
        #initilzie the layer
        EPSG_code=int(crs.authid().split(":")[1]) #get teh coordinate reference system of input_layer
        uri = gtype+'?crs=epsg:'+str(EPSG_code)+'&index=yes'
        
        vlaym = QgsVectorLayer(uri, layname, "memory")
        
        # add fields
        if not vlaym.dataProvider().addAttributes(qfields):
            raise Error('failed to add fields')
        
        vlaym.updateFields()
        
        #add feats
        if not vlaym.dataProvider().addFeatures(feats_l):
            raise Error('failed to addFeatures')
        
        vlaym.updateExtents()
        

        
        #=======================================================================
        # checks
        #=======================================================================
        if vlaym.wkbType() == 100:
            msg = 'constructed layer \'%s\' has NoGeometry'%vlaym.name()
            if gtype == 'None':
                log.debug(msg)
            else:
                raise Error(msg)

        
        log.debug('constructed \'%s\''%vlaym.name())
        return vlaym
    
    
def vlay_new_df(#build a vlay from a df
            df_raw,
            crs,
            
            geo_d = None, #container of geometry objects {fid: QgsGeometry}
            geo_fn_tup = None, #if geo_d=None, tuple of field names to search for coordinate data
            
            layname='df_layer',

            allow_fid_mismatch = False,
            
            infer_dtypes = True, #whether to referesh the dtyping in the df
            
            driverName = 'GPKG',
            
            #expectations
            expect_unique_colns = True,

            logger=mod_logger, db_f = False,
            ):
        """
        todo: migrate off this
        """
        
        #=======================================================================
        # setup
        #=======================================================================
        log = logger.getChild('vlay_new_df')
        log.warning('Depcreciate me')    

            
            
        #=======================================================================
        # precheck
        #=======================================================================
        df = df_raw.copy()
        
        max_len=50

        
        
        #check lengths
        boolcol = df_raw.columns.str.len() >= max_len
        
        if np.any(boolcol):
            log.warning('passed %i columns which exeed the max length %i for driver \'%s\'.. truncating: \n    %s'%(
                boolcol.sum(), max_len, driverName, df_raw.columns.values[boolcol]))
            
            
            df.columns = df.columns.str.slice(start=0, stop=max_len-1)

        
        #make sure the columns are unique
        if not df.columns.is_unique:
            """
            this can happen especially when some field names are super long and have their unique parts truncated
            """
            boolcol = df.columns.duplicated(keep='first')
            
            log.warning('got %i duplicated columns: \n    %s'%(
                boolcol.sum(), df.columns[boolcol].values))
            
            if expect_unique_colns:
                raise Error('got non unique columns')
            
            #drop the duplicates
            log.warning('dropping second duplicate column')
            df = df.loc[:, ~boolcol]
        
            
        #===========================================================================
        # assemble the features
        #===========================================================================
        """this does its own index check"""
        
        feats_d = feats_build(df, logger=log, geo_d = geo_d,infer_dtypes=infer_dtypes,
                                        geo_fn_tup = geo_fn_tup, 
                                        allow_fid_mismatch=allow_fid_mismatch, db_f=db_f)
        
        
        #=======================================================================
        # get the geo type
        #=======================================================================
        if not geo_d is None:
            #pull geometry type from first feature
            gtype = QgsWkbTypes().displayString(next(iter(geo_d.values())).wkbType())
        elif not geo_fn_tup is None:
            gtype = 'Point'
        else:
            gtype = 'None'
            
            
        #===========================================================================
        # buidl the new layer
        #===========================================================================
        vlay = vlay_new_mlay(gtype, #no geo
                             crs, 
                             layname,
                             list(feats_d.values())[0].fields(),
                             list(feats_d.values()),
                             logger=log,
                             )
        
        #=======================================================================
        # post check
        #=======================================================================
        if db_f:
            if vlay.wkbType() == 100:
                raise Error('constructed layer has NoGeometry')
            #vlay_chk_validty(vlay, chk_geo=True, logger=log)


        
        return vlay
    

            
def vlay_fieldnl(vlay):
    return [field.name() for field in vlay.fields()]


def feats_build( #build a set of features from teh passed data
                 data, #data from which to build features from (either df or qvlayd)
                 
                 geo_d = None, #container of geometry objects {fid: QgsGeometry}
                 geo_fn_tup = None, #if geo_d=None, tuple of field names to search for coordinate data
                 
                 allow_fid_mismatch = False, #whether to raise an error if the fids set on the layer dont match the data
                 
                 infer_dtypes = True, #whether to referesh the dtyping in the df
                 
                 logger=mod_logger, db_f=False):
    
    log = logger.getChild('feats_build')
    #===========================================================================
    # precheck
    #===========================================================================
    #geometry input logic
    if (not geo_d is None) and (not geo_fn_tup is None):
        raise Error('todo: implement non geo layers')
    
    #index match
    if isinstance(geo_d, dict):
        #get the data fid_l
        if isinstance(data, pd.DataFrame):
            dfid_l = data.index.tolist()
        elif isinstance(data, dict):
            dfid_l = list(data.keys())
        else:
            raise Error('unexpected type')
        
        if not basic.linr(dfid_l, list(geo_d.keys()),'feat_data', 'geo_d', 
                            sort_values=True, result_type='exact', logger=log):
            raise Error('passed geo_d and data indexes dont match')
    
    #overrides
    if geo_fn_tup: 
        geofn_hits = 0
        sub_field_match = False #dropping geometry fields
    else: 
        sub_field_match = True
        


    log.debug('for %i data type %s'%(
        len(data), type(data)))
    #===========================================================================
    # data conversion
    #===========================================================================
    if isinstance(data, pd.DataFrame):
        
        #check the index (this will be the fids)
        if not data.index.dtype.char == 'q':
            raise Error('expected integer index')
        
        fid_ar = data.index.values
        
        #infer types
        if infer_dtypes:
            data = data.infer_objects()
            
        #convert the data
        qvlayd = df_to_qvlayd(data)
        
        #=======================================================================
        # build fields container from data
        #=======================================================================
        """we need to convert numpy types to pytypes.
            these are later convert to Qtypes"""
        
        fields_d = dict()
        for coln, col in data.items():
            if not geo_fn_tup is None:
                if coln in geo_fn_tup: 
                    geofn_hits +=1
                    continue #skip this one
                
            #set the type for this name
            fields_d[coln] = np_to_pytype(col.dtype, logger=log)
            
        qfields = fields_build_new(fields_d = fields_d, logger=log)
        
        #=======================================================================
        # some checks
        #=======================================================================
        
        
        if db_f:
            #calc hte expectation
            if geo_fn_tup is None:
                exp_cnt= len(data.columns)
            else:
                exp_cnt = len(data.columns) - len(geo_fn_tup)
            
            if not exp_cnt == len(fields_d):
                raise Error('only generated %i fields from %i columns'%(
                    len(data.columns), len(fields_d)))
                
            #check we got them all
            if not exp_cnt == len(qfields):
                raise Error('failed to create all the fields')
        
        """
        for field in qfields:
            print(field)
        
        qfields.toList()
        
        new_qfield = QgsField(fname, qtype, typeName=QMetaType.typeName(QgsField(fname, qtype).type()))
        
        """
        
    else:
        fid_ar = np.array(list(data.keys()))
        #set the data
        qvlayd = data
        
    
        #===========================================================================
        # build fields container from data
        #===========================================================================
        #slice out geometry data if there
        sub_d1 = list(qvlayd.values())[0] #just get the first
        sub_d2 = dict()
        
        
        for fname, value in sub_d1.items():
            if not geo_fn_tup is None:
                if fname in geo_fn_tup: 
                    geofn_hits +=1
                    continue #skip this one
            sub_d2[fname] = value
        
        #build the fields from this sample data
        qfields = fields_build_new(samp_d = sub_d2, logger=log)
        
        
    #check for geometry field names
    if not geo_fn_tup is None:
        if not geofn_hits == len(geo_fn_tup):
            log.error('missing some geometry field names form the data')
            raise IOError
        
        
    #===========================================================================
    # extract geometry
    #===========================================================================
    if geo_d is None:
        #check for nulls
        if db_f:
            chk_df= pd.DataFrame.from_dict(qvlayd, orient='index')
            
            if chk_df.loc[:, geo_fn_tup].isna().any().any():
                raise Error('got some nulls on the geometry fields: %s'%geo_fn_tup)

            
        
        geo_d = dict()
        for fid, sub_d in copy.copy(qvlayd).items():
            #get the xy
            xval, yval = sub_d.pop(geo_fn_tup[0]), sub_d.pop(geo_fn_tup[1])
            
            #build the geometry
            geo_d[fid] = QgsGeometry.fromPointXY(QgsPointXY(xval,yval))
            
            #add the cleaned data back in
            qvlayd[fid] = sub_d
            
    #===========================================================================
    # check geometry
    #===========================================================================
    if db_f:
        #precheck geometry validty
        for fid, geo in geo_d.items():
            if not geo.isGeosValid():
                raise Error('got invalid geometry on %i'%fid)

            
        
    
    #===========================================================================
    # loop through adn build features
    #===========================================================================
    feats_d = dict()
    for fid, sub_d in qvlayd.items():
        #=======================================================================
        # #log.debug('assembling feature %i'%fid)
        # #=======================================================================
        # # assmble geometry data
        # #=======================================================================
        # if isinstance(geo_d, dict):
        #     geo = geo_d[fid]
        #     
        # elif not geo_fn_tup is None:
        #     xval = sub_d[geo_fn_tup[0]]
        #     yval = sub_d[geo_fn_tup[1]]
        #     
        #     if pd.isnull(xval) or pd.isnull(yval):
        #         log.error('got null geometry values')
        #         raise IOError
        #     
        #     geo = QgsGeometry.fromPointXY(QgsPointXY(xval,yval))
        #     #Point(xval, yval) #make the point geometry
        # 
        # else:
        #     geo = None
        #=======================================================================
            
        
        #=======================================================================
        # buidl the feature
        #=======================================================================
        #=======================================================================
        # feats_d[fid] = feat_build(fid, sub_d, qfields=qfields, geometry=geo, 
        #                           sub_field_match = sub_field_match, #because we are excluding the geometry from the fields
        #                           logger=log, db_f=db_f)
        #=======================================================================
        feat = QgsFeature(qfields, fid) 
        
        for fieldn, value in sub_d.items():
            """
            cut out feat_build() for simplicity
            """
        
            #skip null values
            if pd.isnull(value): continue
            
            #get the index for this field
            findx = feat.fieldNameIndex(fieldn) 
            
            #get the qfield
            qfield = feat.fields().at(findx)
            
            #make the type match
            ndata = qtype_to_pytype(value, qfield.type(), logger=log)
            
            #set the attribute
            if not feat.setAttribute(findx, ndata):
                raise Error('failed to setAttribute')
            
            #setgeometry
            feat.setGeometry(geo_d[fid])
            
            #stor eit
            feats_d[fid]=feat
        
        
    #===========================================================================
    # checks
    #===========================================================================
    
    if db_f:
        #fid match
        nfid_ar = np.array(list(feats_d.keys()))
        
        if not np.array_equal(nfid_ar, fid_ar):
            log.warning('fid mismatch')
            
            if not allow_fid_mismatch:
                raise Error('fid mismatch')
            
        #feature validty
        for fid, feat in feats_d.items():
            if not feat.isValid():
                raise Error('invalid feat %i'%feat.id())

            if not feat.geometry().isGeosValid():
                raise Error('got invalid geometry on feat \'%s\''%(feat.id()))
            
            """
            feat.geometry().type()
            
            
            """
            
        
        
    log.debug('built %i \'%s\'  features'%(
        len(feats_d),
        QgsWkbTypes.geometryDisplayString(feat.geometry().type()),
        ))
    
    return feats_d
  
  
def fields_build_new( #build qfields from different data containers
                    samp_d = None, #sample data from which to build qfields {fname: value}
                    fields_d = None, #direct data from which to build qfields {fname: pytype}
                    fields_l = None, #list of QgsField objects
                    logger=mod_logger):

    log = logger.getChild('fields_build_new')
    #===========================================================================
    # buidl the fields_d
    #===========================================================================
    if (fields_d is None) and (fields_l is None): #only if we have nothign better to start with
        if samp_d is None: 
            log.error('got no data to build fields on!')
            raise IOError
        
        fields_l = []
        for fname, value in samp_d.items():
            if pd.isnull(value):
                log.error('for field \'%s\' got null value')
                raise IOError
            
            elif inspect.isclass(value):
                raise IOError
            
            fields_l.append(field_new(fname, pytype=type(value)))
            
        log.debug('built %i fields from sample data'%len(fields_l))
        
    
    
    #===========================================================================
    # buidl the fields set
    #===========================================================================
    elif fields_l is None:
        fields_l = []
        for fname, ftype in fields_d.items():
            fields_l.append(field_new(fname, pytype=ftype))
            
        log.debug('built %i fields from explicit name/type'%len(fields_l))
            
        #check it 
        if not len(fields_l) == len(fields_d):
            raise Error('length mismatch')
            
    elif fields_d is None: #check we have the other
        raise IOError
    
    
    
            
    #===========================================================================
    # build the Qfields
    #===========================================================================
    
    Qfields = QgsFields()
    
    fail_msg_d = dict()
    
    for indx, field in enumerate(fields_l): 
        if not Qfields.append(field):
            fail_msg_d[indx] = ('%i failed to append field \'%s\''%(indx, field.name()), field)

    #report
    if len(fail_msg_d)>0:
        for indx, (msg, field) in fail_msg_d.items():
            log.error(msg)
            
        raise Error('failed to write %i fields'%len(fail_msg_d))
    
    """
    field.name()
    field.constraints().constraintDescription()
    field.length()
    
    """
    
    
    #check it 
    if not len(Qfields) == len(fields_l):
        raise Error('length mismatch')


    return Qfields

def field_new(fname, 
              pytype=str, 
              driverName = 'SpatiaLite', #desired driver (to check for field name length limitations)
              fname_trunc = True, #whether to truncate field names tha texceed the limit
              logger=mod_logger): #build a QgsField
    
    #===========================================================================
    # precheck
    #===========================================================================
    if not isinstance(fname, str):
        raise IOError('expected string for fname')
    
    #vector layer field name lim itation
    max_len = fieldn_max_d[driverName]
    """
    fname = 'somereallylongname'
    """
    if len(fname) >max_len:
        log = logger.getChild('field_new')
        log.warning('got %i (>%i)characters for passed field name \'%s\'. truncating'%(len(fname), max_len, fname))
        
        if fname_trunc:
            fname = fname[:max_len]
        else:
            raise Error('field name too long')
        
    
    qtype = ptype_to_qtype(pytype)
    
    """
    #check this type
    QMetaType.typeName(QgsField(fname, qtype).type())
    
    QVariant.String
    QVariant.Int
    
     QMetaType.typeName(new_qfield.type())
    
    """
    #new_qfield = QgsField(fname, qtype)
    new_qfield = QgsField(fname, qtype, typeName=QMetaType.typeName(QgsField(fname, qtype).type()))
    
    return new_qfield

def vlay_get_bgeo_type(vlay,
                       match_flags=re.IGNORECASE,
                       ):
    
    gstr = QgsWkbTypes().displayString(vlay.wkbType()).lower()
    
    for gtype in ('polygon', 'point', 'line'):
        if re.search(gtype, gstr,  flags=match_flags):
            return gtype
        
    raise Error('failed to match')


def vlay_rename_fields(
        vlay_raw,
        rnm_d, #field name conversions to apply {old FieldName:newFieldName}
        logger=None,
        feedback=None,

        ):
    """
    todo: replace with coms.hp.Qproj.vlay_rename_fields
    
    """
    
    if logger is None: logger=mod_logger
    log=logger.getChild('vlay_rename_fields')
    
    #get a working layer
    vlay_raw.selectAll()
    vlay = processing.run('native:saveselectedfeatures', 
            {'INPUT' : vlay_raw, 'OUTPUT' : 'TEMPORARY_OUTPUT'}, 
            feedback=feedback)['OUTPUT']
    
    #get fieldname index conversion for layer
    fni_d = {f.name():vlay.dataProvider().fieldNameIndex(f.name()) for f in vlay.fields()}
    
    #check it
    for k in rnm_d.keys():
        assert k in fni_d.keys(), 'requested field \'%s\' not on layer'%k
    
    #re-index rename request
    fiRn_d = {fni_d[k]:v for k,v in rnm_d.items()}

    #apply renames
    if not vlay.dataProvider().renameAttributes(fiRn_d):
        raise Error('failed to rename')
    vlay.updateFields()
    
    #check it
    fn_l = [f.name() for f in vlay.fields()]
    s = set(rnm_d.values()).difference(fn_l)
    assert len(s)==0, 'failed to rename %i fields: %s'%(len(s), s)
    
    vlay.setName(vlay_raw.name())
    
    log.debug('applied renames to \'%s\' \n    %s'%(vlay.name(), rnm_d))
    
    
    return vlay

def vlay_key_convert(#convert a list of ids in one form to another
        vlay,
        id1_objs, #list of ids (or dict keyed b y ids)  to get conversion of
        id_fieldn, #field name for field type ids
        id1_type = 'field', #type of ids passed in the id_l (result will return a dict of th eopposit etype)
            #'field': keys in id1_objs are values from some field (on the vlay)
            #'fid': keys in id1_objs are fids (on the vlay)
        fid_fval_d = None, #optional pre-calced data (for performance improvement)
        logger=mod_logger,
        db_f = False, #extra checks
        ):
    
    log = logger.getChild('vlay_key_convert')
    
    #===========================================================================
    # handle variable inputs
    #===========================================================================
    if isinstance(id1_objs, dict):
        id1_l = list(id1_objs.keys())
    elif isinstance(id1_objs, list):
        id1_l = id1_objs
    else:
        raise Error('unrecognized id1_objs type')
    
    #===========================================================================
    # extract the fid to fval conversion
    #===========================================================================
    if fid_fval_d is None:
        #limit the pull by id1s
        if id1_type == 'fid':
            request = QgsFeatureRequest().setFilterFids(id1_l)
            log.debug('pulling \'fid_fval_d\' from %i fids'%(len(id1_l)))
            
        #by field values
        elif id1_type == 'field': #limit by field value
            raise Error(' not implemented')
            #build an expression so we only query features with values matching the id1_l
            #===================================================================
            # qexp = exp_vals_in_field(id1_l, id_fieldn, qfields = vlay.fields(),  logger=log)
            # request =  QgsFeatureRequest(qexp)
            # 
            # log.debug('pulling \'fid_fval_d\' from %i \'%s\' fvals'%(
            #     len(id1_l), id_fieldn))
            #===================================================================
        else:
            raise Error('unrecognized id1_type')
            
        
        fid_fval_d = vlay_get_fdata(vlay, fieldn=id_fieldn, request =request, logger=log,
                                    expect_all_real=True, fmt='dict')
    #no need
    else:
        log.debug('using passed \'fid_fval_d\' with %i'%len(fid_fval_d))
        
    #check them
    if db_f:
        
        #log.debug('\'fid_fval_d\': \n    %s'%fid_fval_d)
        
        
        for dname, l in (
            ('keys', list(fid_fval_d.keys())),
            ('values', list(fid_fval_d.values()))
            ):
            
            if not len(np.unique(np.array(l))) == len(l):
                raise Error('got non unique \'%s\' on fid_fval_d'%dname)
        
        
    
    #===========================================================================
    # swap keys
    #===========================================================================
    if id1_type == 'fid':
        id1_id2_d = fid_fval_d #o flip necessary

    elif id1_type == 'field': #limit by field value
        log.debug('swapping keys')
        id1_id2_d = dict(zip(
            fid_fval_d.values(), fid_fval_d.keys()
            ))
        

    else:
        raise Error('unrecognized id1_type')
        
    #=======================================================================
    # #make conversion
    #=======================================================================
    #for dictionaries
    if isinstance(id1_objs, dict):
        res_objs = dict()
        for id1, val in id1_objs.items():
            res_objs[id1_id2_d[id1]] = val
            
        log.debug('got converted DICT results with %i'%len(res_objs))
        
    #for lists
    elif isinstance(id1_objs, list):
        
        res_objs = [id1_id2_d[id1] for id1 in id1_objs]
        
        log.debug('got converted LIST results with %i'%len(res_objs))
        
    else:
        raise Error('unrecognized id1_objs type')

    return res_objs, fid_fval_d #converted objects, conversion dict ONLY FOR THSE OBJECTS!
            
  

        

#==============================================================================
# type checks-----------------
#==============================================================================

def qisnull(obj):
    if obj is None:
        return True
    
    if isinstance(obj, QVariant):
        if obj.isNull():
            return True
        else:
            return False
        
    
    if pd.isnull(obj):
        return True
    else:
        return False
    
def is_qtype_match(obj, qtype_code, logger=mod_logger): #check if the object matches the qtype code
    log = logger.getChild('is_qtype_match')
    
    #get pythonic type for this code
    try:
        py_type = type_qvar_py_d[qtype_code]
    except:

        if not qtype_code in type_qvar_py_d.keys():
            log.error('passed qtype_code \'%s\' not in dict from \'%s\''%(qtype_code, type(obj)))
            raise IOError
    
    if not isinstance(obj, py_type):
        #log.debug('passed object of type \'%s\' does not match Qvariant.type \'%s\''%(type(obj), QMetaType.typeName(qtype_code)))
        return False
    else:
        return True


#==============================================================================
# type conversions----------------
#==============================================================================

def np_to_pytype(npdobj, logger=mod_logger):
    
    if not isinstance(npdobj, np.dtype):
        raise Error('not passed a numpy type')
    
    try:
        return npc_pytype_d[npdobj.char]

    except Exception as e:
        log = logger.getChild('np_to_pytype')
        
        if not npdobj.char in npc_pytype_d.keys():
            log.error('passed npdtype \'%s\' not found in the conversion dictionary'%npdobj.name)
            
        raise Error('failed oto convert w/ \n    %s'%e)
    

def qtype_to_pytype( #convert object to the pythonic type taht matches the passed qtype code
        obj, 
        qtype_code, #qtupe code (qfield.type())
        logger=mod_logger): 
    
    if is_qtype_match(obj, qtype_code): #no conversion needed
        return obj 
    
    
    #===========================================================================
    # shortcut for nulls
    #===========================================================================
    if qisnull(obj):
        return None

        
    
        
    
    
    #get pythonic type for this code
    py_type = type_qvar_py_d[qtype_code]
    
    try:
        return py_type(obj)
    except:
        #datetime
        if qtype_code == 16:
            return obj.toPyDateTime()
        
        
        log = logger.getChild('qtype_to_pytype')
        if obj is None:
            log.error('got NONE type')
            
        elif isinstance(obj, QVariant):
            log.error('got a Qvariant object')
            
        else:
            log.error('unable to map object \'%s\' of type \'%s\' to type \'%s\''
                      %(obj, type(obj), py_type))
            
            
            """
            QMetaType.typeName(obj)
            """
        raise IOError
    
def ptype_to_qtype(py_type, logger=mod_logger): #get the qtype corresponding to the passed pytype
    """useful for buildign Qt objects
    
    really, this is a reverse 
    
    py_type=str
    
    """
    if not inspect.isclass(py_type):
        logger.error('got unexpected type \'%s\''%type(py_type))
        raise Error('bad type')
    
    #build a QVariant object from this python type class, then return its type
    try:
        qv = QVariant(py_type())
    except:
        logger.error('failed to build QVariant from \'%s\''%type(py_type))
        raise IOError
    
    """
    #get the type
    QMetaType.typeName(qv.type())
    """
    
    
    return qv.type()
        

    
def df_to_qvlayd( #convert a data frame into the layer data structure (keeyd by index)
        df, #data to convert. df index should match fid index
        logger=mod_logger):
    
    log = logger.getChild('df_to_qvlayd')
    
    d = dict() #data dictionary in qgis structure
    
    #prechecks
    if not df.index.is_unique:
        log.error('got passed non-unique index')
        raise IOError
    
    #===========================================================================
    # loop and fill
    #===========================================================================
    for fid, row in df.iterrows():
        
        #=======================================================================
        # build sub data 
        #=======================================================================
        sub_d = dict() #sub data structure
        
        for fieldn, value in row.items():
            sub_d[fieldn] = value
            
        #=======================================================================
        # add the sub into the main
        #=======================================================================
        d[fid] = sub_d
        
    
    if not len(df) == len(d):
        log.error('got length mismatch')
        raise IOError
    
    log.debug('converted df %s into qvlayd'%str(df.shape))
        
    
    
    return d

def view(#view the vector data (or just a df) as a html frame
        obj, logger=mod_logger,
        #**gfd_kwargs, #kwaqrgs to pass to vlay_get_fdatas() 'doesnt work well with the requester'
        ):
    
    if isinstance(obj, pd.DataFrame) or isinstance(obj, pd.Series):
        df = obj
    elif isinstance(obj, QgsVectorLayer):
        """this will index the viewed frame by fid"""
        df = vlay_get_fdf(obj)
    else:
        raise Error('got unexpected object type: %s'%type(obj))
    
    basic.view(df)
    
    logger.info('viewer closed')
    
    return


if __name__ == '__main__':
    

    print('???')

