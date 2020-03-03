'''
Created on Feb. 7, 2020

@author: cefect

common helper functions for use across project
'''

"""
todo: migrate off of here

"""
#==============================================================================
# logger----------
#==============================================================================
import logging, os
mod_logger = logging.getLogger('hp') #creates a child logger of the root

#==============================================================================
# dependency check
#==============================================================================



#==============================================================================
# imports------------
#==============================================================================
#python
import os, configparser
import pandas as pd
import numpy as np
#qgis
from qgis.core import *
from qgis.analysis import QgsNativeAlgorithms
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QListWidget


QgsMessageLog.logMessage('todo: migrate off of hp','CanFlood', level=Qgis.Critical)
#==============================================================================
# classes------------
#==============================================================================
class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, msg):
        from qgis.utils import iface
        
        iface.messageBar().pushMessage("Error", msg, level=Qgis.Critical)
        QgsMessageLog.logMessage(msg,'CanFlood', level=Qgis.Critical)
        

        
        
    
class Qproj(object): #baseclass for working w/ pyqgis outside the native console
    
    crs_id = 4326
    crs = QgsCoordinateReferenceSystem(crs_id)
    driverName = 'SpatiaLite' #default data creation driver type
    

    out_dName = driverName #default output driver/file type
    SpatiaLite_pars = dict() #dictionary of spatialite pars

    algo_init = False #flag indicating whether the algos have been initialized
    
    
    overwrite=True
    
    
    
    
    def __init__(self, 
                 **kwargs):

        """
        should run during plugin init
        """
        mod_logger.debug('Qproj super')
        
        super().__init__(**kwargs) #initilzie teh baseclass
        
        
        #=======================================================================
        # setup qgis
        #=======================================================================
        #self.qap = self.init_qgis()
        self.qproj = QgsProject.instance()

        self.algo_init = self.init_algos()
        
        self.set_vdrivers()
        
        self.mstore = QgsMapLayerStore() #build a new map store
        
        
        
        if not self.proj_checks():
            raise Error('failed checks')
        
        
        self.logger.info('Qproj __INIT__ finished')
        
        
        return
    
    def init_qgis(self, #instantiate qgis
                  gui = False): 
        """
        WARNING: need to hold this app somewhere. call in the module you're working in (scripts)
        
        """
        log = self.logger.getChild('init_qgis')
        
        try:
            
            QgsApplication.setPrefixPath(r'C:/OSGeo4W64/apps/qgis', True)
            
            app = QgsApplication([], gui)
            #   Update prefix path
            #app.setPrefixPath(r"C:\OSGeo4W64\apps\qgis", True)
            app.initQgis()
            #logging.debug(QgsApplication.showSettings())
            log.info(' QgsApplication.initQgis. version: %s, release: %s'%
                        (Qgis.QGIS_VERSION, Qgis.QGIS_RELEASE_NAME))
            return app
        
        except:
            raise Error('QGIS failed to initiate')
        
    def init_algos(self): #initiilize processing and add providers
    
    
        log = self.logger.getChild('init_algos')
        from processing.core.Processing import Processing
    
        Processing.initialize()
    
        QgsApplication.processingRegistry().addProvider(QgsNativeAlgorithms())
        
        log.info('processing initilzied')
        
        self.feedback = QgsProcessingFeedback()

        return True

    def set_vdrivers(self):
        
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
        
        self.logger.debug('built driver:extensions dict: \n    %s'%vlay_drivers)
        
        return
        
        
    
    def set_crs(self, #load, build, and set the project crs
                authid =  None):
        
        #=======================================================================
        # setup and defaults
        #=======================================================================
        log = self.logger.getChild('set_crs')
        
        if authid is None: 
            authid = self.crs_id
        
        if not isinstance(authid, int):
            raise IOError('expected integer for crs')
        
        #=======================================================================
        # build it
        #=======================================================================
        self.crs = QgsCoordinateReferenceSystem(authid)
        
        if not self.crs.isValid():
            raise IOError('CRS built from %i is invalid'%authid)
        
        #=======================================================================
        # attach to project
        #=======================================================================
        self.qproj.setCrs(self.crs)
        
        if not self.qproj.crs().description() == self.crs.description():
            raise Error('qproj crs does not match sessions')
        
        log.info('Session crs set to EPSG: %i, \'%s\''%(authid, self.crs.description()))
        
        
    def proj_checks(self):
        log = self.logger.getChild('proj_checks')
        
        if not self.driverName in self.vlay_drivers:
            raise Error('unrecognized driver name')
        
        if not self.out_dName in self.vlay_drivers:
            raise Error('unrecognized driver name')
        
        log.info('project passed all checks')
        
        return True
    
    
    def output_df(self, #dump some outputs
                      df, 
                      out_fn,
                      out_dir = None,
                      overwrite=None,
            ):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.wd
        if overwrite is None: overwrite = self.overwrite
        log = self.logger.getChild('output')
        
        assert isinstance(out_dir, str), 'unexpected type on out_dir: %s'%type(out_dir)
        assert os.path.exists(out_dir), 'requested output directory doesnot exist: \n    %s'%out_dir
        
        
        #extension check
        if not out_fn.endswith('.csv'):
            out_fn = out_fn+'.csv'
        
        #output file path
        out_fp = os.path.join(out_dir, out_fn)
        
        #======================================================================
        # checeks
        #======================================================================
        if os.path.exists(out_fp):
            log.warning('file exists \n    %s'%out_fp)
            if not overwrite:
                raise Error('file already exists')
            

        #======================================================================
        # writ eit
        #======================================================================
        df.to_csv(out_fp, index=True)
        
        log.info('wrote to %s to file: \n    %s'%(str(df.shape), out_fp))
        
        return out_fp
        
        
class logger(object): #workaround for qgis logging pythonic
    log_tabnm = 'CanFlood' # qgis logging panel tab name
    
    log_nm = '' #logger name
    
    def __init__(self, parent):
        #attach
        self.parent = parent
        
        self.iface = parent.iface
        
    def getChild(self, new_childnm):
        
        #build a new logger
        child_log = logger(self.parent)
        
        #nest the name
        child_log.log_nm = '%s.%s'%(self.log_nm, new_childnm)
        
        return child_log
        
    def info(self, msg):
        self._loghlp(msg, Qgis.Info, push=False)


    def debug(self, msg_raw):
        msg = '%s: %s'%(self.log_nm, msg_raw)
        QgsLogger.debug(msg)
        
    def warning(self, msg):
        self._loghlp(msg, Qgis.Warning, push=False)

        
    def push(self, msg):
        self._loghlp(msg, Qgis.Info, push=True)

    def error(self, msg):
        self._loghlp(msg, Qgis.Critical, push=True)
        
    def _loghlp(self, #helper function for generalized logging
                msg_raw, qlevel, push=False):
        
        msg = '%s: %s'%(self.log_nm, msg_raw)
        
        QgsMessageLog.logMessage(msg, self.log_tabnm, level=qlevel)
        
        if push:
            self.iface.messageBar().pushMessage(self.log_tabnm, msg, level=qlevel)
        
        
     
class xxxQprojPlug(object): #baseclass for plugins
    
    tag='scenario1'
    overwrite=True
    wd = ''
    
    """not a great way to init this one
    def __init__(self):
        self.logger = logger()"""
    
    def qproj_setup(self): #workaround to setup the project
        
        self.logger = logger(self) #init the logger
        self.qproj = QgsProject.instance()
        self.feedback = QgsProcessingFeedback()
        
        self.crs = self.qproj.crs()
        
        
    
    def output_df(self, #dump some outputs
                      df, 
                      out_fn,
                      out_dir = None,
                      overwrite=None,
                      write_index=True, 
            ):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.wd
        if overwrite is None: overwrite = self.overwrite
        log = self.logger.getChild('output_df')
        
        assert isinstance(out_dir, str), 'unexpected type on out_dir: %s'%type(out_dir)
        assert os.path.exists(out_dir), 'requested output directory doesnot exist: \n    %s'%out_dir
        
        
        #extension check
        if not out_fn.endswith('.csv'):
            out_fn = out_fn+'.csv'
        
        #output file path
        out_fp = os.path.join(out_dir, out_fn)
        
        #======================================================================
        # checeks
        #======================================================================
        if os.path.exists(out_fp):
            log.warning('file exists \n    %s'%out_fp)
            if not overwrite:
                raise Error('file already exists')
            

        #======================================================================
        # writ eit
        #======================================================================
        df.to_csv(out_fp, index=write_index)
        
        log.info('wrote to %s to file: \n    %s'%(str(df.shape), out_fp))
        
        return out_fp
    
    def get_cf_fp(self):
        cf_fp = self.lineEdit_cf_fp.text()
        
        if cf_fp is None or cf_fp == '':
            raise Error('need to specficy a control file path')
        if not os.path.exists(cf_fp):
            raise Error('need to specficy a valid control file path')
        
        if not os.path.splitext(cf_fp)[1] == '.txt':
            raise Error('unexpected extension on Control File')
        
        return cf_fp
    
    def get_wd(self):
        wd = self.lineEdit_wd.text()
        
        if wd is None or wd == '':
            raise Error('need to specficy a Working Directory')
        if not os.path.exists(wd):
            os.makedirs(wd)
            self.logger.info('built new working directory at:\n    %s'%wd)
        
        
        return wd
    
    def browse_button(self, 
                      lineEdit, #text bar where selected directory should be displayed
                      prompt = 'Select Directory', #title of box
                      qfd = QFileDialog.getExistingDirectory, #dialog to launch
                      ):
        #ask the user for the path
        fp = qfd(self, prompt)
        
        #just take the first
        if len(fp) == 2:
            fp = fp[0]
        
        #see if they picked something
        if fp == '':
            self.logger.error('user failed to make a selection. skipping')
            return 
        
        #update the bar
        lineEdit.setText(fp)
        
        self.logger.info('user selected: \n    %s'%fp)
        
    def set_overwrite(self): #action for checkBox_SSoverwrite state change
        if self.checkBox_SSoverwrite.isChecked():
            self.overwrite= True
        else:
            self.overwrite= False
            
        self.logger.push('overwrite set to %s'%self.overwrite)
        
    def update_cf(self, #update one parameter  control file 
                  new_pars_d, #new paraemeters {section : {valnm : value }}
                  cf_fp = None):
        
        log = self.logger.getChild('update_cf')
        
        #get defaults
        if cf_fp is None: cf_fp = self.cf_fp
        
        #initiliae the parser
        pars = configparser.ConfigParser(allow_no_value=True)
        _ = pars.read(self.cf_fp) #read it from the new location
        
        #loop and make updates
        for section, val_d in new_pars_d.items():
            for valnm, value in val_d.items():
                pars.set(section, valnm, value)
        
        #write the config file 
        with open(self.cf_fp, 'w') as configfile:
            pars.write(configfile)
            
        log.info('updated contyrol file w/ %i pars at :\n    %s'%(
            len(new_pars_d), cf_fp))
        
        return
        
        

        
        
        
      
        
        
            
    def testit(self): #for testing the ui
        self.iface.messageBar().pushMessage("CanFlood", "youre doing a test", level=Qgis.Info)
        
        self.logger.info('test the logger')
        self.logger.error('erro rtest')
        
        log = self.logger.getChild('testit')
        
        log.info('testing the child')
        

#==============================================================================
# functions-------------
#==============================================================================
def vlay_fieldnl(vlay):
    return [field.name() for field in vlay.fields()]

def view(df):
    if isinstance(df, pd.Series):
        df = pd.DataFrame(df)
    import webbrowser
    #import pandas as pd
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
        #type(f)
        df.to_html(buf=f)
        
    webbrowser.open(f.name)
    
    
def is_null(obj): #check if the object is none

    if obj is None:
        return True
    """might not work for non string multi element objects"""
    if np.any(pd.isnull(obj)):
        return True
    
    #excel checks
    if obj in ('', 0, '0', '0.0'):
        return True
    
    return False

def linr( #fancy check if left elements are in right elements
        ldata_raw, rdata_raw, 
                  lname_raw = 'left',
                  rname_raw = 'right',
                  sort_values = False, #whether to sort the elements prior to checking
                  result_type = 'bool', #format to return result in
                    #missing: return a list of left elements not in the right
                    #matching: list of elements in both
                    #boolar: return boolean where True = left element found in right (np.isin)
                    #bool: return True if all left elements are found on the right
                    #exact: return True if perfect element match
                  invert = False, #flip left and right
                  
                  #expectations
                  dims= 1, #expected dimeions
                  
                  fancy_log = False, #whether to log stuff                  
                  logger=mod_logger
                  ):
    
    #===========================================================================
    # precheck
    #===========================================================================
    if isinstance(ldata_raw, str):
        raise Error('expected array type')
    if isinstance(rdata_raw, str):
        raise Error('expected array type')
    
    #===========================================================================
    # do flipping
    #===========================================================================
    if invert:
        ldata = rdata_raw
        lname = rname_raw
        rdata = ldata_raw
        rname = lname_raw
    else:
        ldata = ldata_raw
        lname = lname_raw
        rdata = rdata_raw
        rname = rname_raw
        
        
    #===========================================================================
    # data conversion
    #===========================================================================
    if not isinstance(ldata, np.ndarray):
        l_ar = np.array(list(ldata))
    else:
        l_ar = ldata
        
    if not isinstance(rdata, np.ndarray):
        r_ar = np.array(list(rdata))
    else:
        r_ar = rdata
        
    #===========================================================================
    # do any sorting
    #===========================================================================
    if sort_values:
        l_ar = np.sort(l_ar)
        r_ar = np.sort(r_ar)
        
        #check logic validty of result type
        if result_type =='boolar':
            raise Error('requested result type does not make sense with sorted=True')

        
    #===========================================================================
    # pre check
    #===========================================================================
    #check for empty containers and uniqueness
    for data, dname in (
        (l_ar, lname),
        (r_ar, rname)
        ):
        #empty container
        if data.size == 0:
            raise Error('got empty container for \'%s\''%dname)
        
        #simensions/shape
        """probably not necessary"""
        if not len(data.shape) == dims:
            raise Error('expected %i dimensions got %s'%(
                dims, str(data.shape)))
            
        
        if not pd.Series(data).is_unique:
            #get detailed print outs
            ser = pd.Series(data)
            boolidx = ser.duplicated(keep=False)            
            
            raise Error('got %i (of %i) non-unique elements for \'%s\' \n    %s'%(
                boolidx.sum(), len(boolidx), dname, ser[boolidx]))
        
        #=======================================================================
        # #uniqueness
        # if not data.size == np.unique(data).size:
        #     raise Error('got non-unique elements for \'%s\' \n    %s'%(dname, data))
        #=======================================================================
        
        """data
        data.shape
        
        """
        

    

    #===========================================================================
    # do the chekcing
    #===========================================================================

    boolar = ~np.isin(l_ar, r_ar) #misses from left to right
    
    if fancy_log:
        
        log = logger.getChild('left_in_right')
        msg = ('%i (of %i) elements in \'%s\'  not found in \'%s\': \n    mismatch: %s \n    \'%s\' %s: %s \n    \'%s\' %s: %s'
                    %(boolar.sum(),len(boolar), lname, rname, 
                      l_ar[boolar].tolist(),
                      lname, str(l_ar.shape), l_ar.tolist(), 
                      rname, str(r_ar.shape), r_ar.tolist()
                      )
                    )
        if np.any(boolar):
            logger.debug(msg)
        elif result_type=='exact' and (not np.array_equal(l_ar, r_ar)):
            logger.debug(msg)
        
    #===========================================================================
    # reformat and return result
    #===========================================================================
    if result_type == 'boolar': #left elements in the right
        return ~boolar
    elif result_type == 'bool': #all left elements in the right
        if np.any(boolar):
            return False
        else:
            return True
        
    elif result_type == 'missing':
        return l_ar[boolar].tolist()
    
    elif result_type == 'matching':
        return l_ar[~boolar].tolist()
    
    elif result_type == 'exact':
        return np.array_equal(l_ar, r_ar)
    
    else:
        raise Error('unrecognized result format')
    
 
    
    
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
                    logger = mod_logger, db_f = False,
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
    if not is_null(exp_fieldns): #robust null checking
        skip=False
        if isinstance(exp_fieldns, str):
            if exp_fieldns=='all':
                skip=True
            
        
        
        if not skip:
            fnl = linr(exp_fieldns, vlay_fieldnl(vlay),
                                      'expected field names', vlay.name(),
                                      result_type='missing', logger=log, fancy_log=db_f)
            
            if len(fnl)>0:
                raise Error('%s missing expected fields: %s'%(
                    vlay.name(), fnl))
                
            checks_l.append('exp_fieldns=%i'%len(exp_fieldns))
        
    #=======================================================================
    # unexpected field names
    #=======================================================================
        
    if not is_null(uexp_fieldns): #robust null checking
        #fields on the layer
        if len(vlay_fieldnl(vlay))>0:
        
            fnl = linr(uexp_fieldns, vlay_fieldnl(vlay),
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
                    
                    db_f = False,logger=mod_logger):
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
    
    #===========================================================================
    # build the request
    #===========================================================================
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

    for feat in vlay.getFeatures(request):
        
        #zip values
        fid_attvs[feat.id()] = feat.attributes()


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
            



        
    #===========================================================================
    # wrap and reuslt
    #===========================================================================
    
    return df
    
   
def qtbl_get_df( #extract data to a frame from a qtable
        table, 
            ):

    #get lables    
    coln_l = qtlb_get_axis_l(table, axis=1)
    rown_l = qtlb_get_axis_l(table, axis=0)
    


    tmp_df = pd.DataFrame( 
                columns=coln_l, # Fill columnets
                index=rown_l # Fill rows
                ) 

    for i in range(len(rown_l)):
        for j in range(len(coln_l)):
            qval = table.item(i, j)
            
            if not qval is None:
                tmp_df.iloc[i, j] = qval.text()

    return tmp_df


def qtlb_get_axis_l(table, axis=0): #get axis lables from a qtable
    #row names
    if axis == 1:
        q_l  = [table.horizontalHeaderItem(cnt) for cnt in range(table.rowCount())]
    elif axis == 0:
        q_l  = [table.verticalHeaderItem(cnt) for cnt in range(table.rowCount())]
        
    
    #get data
    l = []
    for qval in q_l:
        if qval is None:
            l.append('UnNamed')
        else:
            l.append(qval.text())
        
    return l
            
    

    

    
    
    
  
        
        
       
    