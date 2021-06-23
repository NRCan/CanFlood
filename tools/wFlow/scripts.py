'''
Created on Jan. 23, 2021

@author: cefect


executing a CanFlood workflow froma python console
'''

#===============================================================================
# imports----------
#===============================================================================
import inspect, logging, os,  datetime, shutil, gc, weakref

from qgis.core import QgsMapLayer, QgsVectorLayer
import pandas as pd
import numpy as np


#===============================================================================
# cf_simp helpers
#===============================================================================
from hlpr.logr import basic_logger
 
from hlpr.exceptions import Error
import hlpr.Q
import hlpr.plot

from hlpr.Q import view
#===============================================================================
# CF workers
#===============================================================================
from build.prepr import Preparor
from build.rsamp import Rsamp
from build.lisamp import LikeSampler
from build.validator import Vali

from model.risk1 import Risk1
from model.risk2 import Risk2
from model.dmg2 import Dmg2

from results.djoin import Djoiner
from results.riskPlot import RiskPlotr
from results.attribution import Attr
from results.compare import Cmpr

from misc.dikes.dcoms import Dcoms
from misc.dikes.expo import Dexpo
from misc.dikes.vuln import Dvuln
from misc.dikes.rjoin import DikeJoiner
#===============================================================================
# methods---------
#===============================================================================

class Session(hlpr.Q.Qcoms, hlpr.plot.Plotr, Dcoms): #handle one test session 
    
    #===========================================================================
    # #qgis attributes
    #===========================================================================
    """
    Qgis should only be init when necessary
        each tool handler should check to see if q has been initilized
        try and take init pars from the handler
        otherwise, build and pass to the handler
    """
 
    qhandl_d = ('qproj','crs','qap','algo_init','vlay_drivers')

    #===========================================================================
    # inheritance handles
    #===========================================================================
    #set passed to all
    """this is picked up and modified by the workflow"""
    com_hndls = ['absolute_fp', 'overwrite']
    
    #set passed to workflows (in addition to com_hndls)
    flow_hndls = ['init_plt_d', 'init_q_d', 'write', 'base_dir', 'plot', 'upd_cf']

    #set passed to workers
    """see _get_wrkr()   
            a custom set is passed based on the worker attributes"""
    
    #===========================================================================
    # program vars
    #===========================================================================
    crsid = None #set forr your project?


    def __init__(self,
                 
                 #session parameters
                 
                 projName = 'proj01',
                 
                 logger=None,
                 
                 #workflow controls
                 write=True, #whether to write results to file
                 plot=False, #whether to write plots to file
                 
                 #ComWrkr controls
                 overwrite=True,
                 absolute_fp = True,
                 out_dir = None,
                 
                 #run model controls
                 base_dir = None, #CanFlood project directory
                #attriMode = False, #flow control for some attribution matrix functions
                 upd_cf = True, #control ssome updating of control file writes
                 
                 
                 **kwargs):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if out_dir is None: out_dir = os.path.join(os.path.expanduser('~'), 'CanFlood', projName)
        if logger is None: logger = basic_logger()
        
        #init the cascade 
        """will need to pass some of these to children"""
        super().__init__(logger = logger,out_dir=out_dir,
                         **kwargs) #Qcoms -> ComWrkr
        
        #=======================================================================
        # attach
        #=======================================================================
        self.projName = projName
        self.write=write
        self.plot = plot
        
        if base_dir is None:
            """C:\\LS\\03_TOOLS\\CanFlood\\_git"""
            base_dir = self.cf_dir
        self.base_dir=base_dir
        assert os.path.exists(self.base_dir), self.base_dir
        
        self.overwrite=overwrite
        self.absolute_fp=absolute_fp
        
        #self.attriMode=attriMode
        self.upd_cf=upd_cf #seems like this should always be True?
        #=======================================================================
        # checks
        #=======================================================================
        for k in self.flow_hndls + self.com_hndls:
            assert hasattr(self, k), k
        
        self.logger.debug('%s.__init__ finished \n'%self.__class__.__name__)

    #===========================================================================
    # CHILD HANDLING--------
    #===========================================================================

    def _run_wflow(self, #execute a single workflow 
                   WorkFlow, #workflow object to run
                   **kwargs):
        
        log = self.logger.getChild('r.%s'%WorkFlow.name)
        log.debug('on %s w/ %s'%(WorkFlow.__name__, WorkFlow.crsid))
        #=======================================================================
        # update crs
        #=======================================================================
        if not WorkFlow.crsid == self.crsid:
            log.debug('crsid mismatch... switching to crs of workflow')
            self.set_crs(WorkFlow.crsid, logger=log)

        #===================================================================
        # # init the flow 
        #===================================================================
        
        #collect pars
        """similar to _get_wrkr().. but less flexible"""
        for k in list(self.com_hndls) + self.flow_hndls:
            kwargs[k] = getattr(self, k)

        #init
        kstr = ''.join(['\n    %s: %s'%(k,v) for k,v in kwargs.items()]) #plot string
        log.debug('building w/ %s'%kstr)
        runr = WorkFlow(logger=self.logger, session=self,**kwargs)

        #===================================================================
        # execute the flow
        #===================================================================
        log.debug('running \n\n')
        runr.run()
        
        log.debug('finished')
        return runr
        

    
    #==========================================================================
    # RUNNERS----------
    #==========================================================================

    def run(self, #run a set of WorkFlows
            wFlow_l, #set of workflows to run
            **kwargs
            ):
        """
        lets the user define their own methods for batching together workflows
        
        """
        log=self.logger.getChild('r')
        log.info('running %i flows: \n    %s'%(len(wFlow_l), wFlow_l))
 
 
        rlib = dict()
        for fWrkr in wFlow_l:
            runr = self._run_wflow(fWrkr, **kwargs)
            
            rlib[runr.name] = runr.res_d.copy()
            
            runr.__exit__()
            
        log.info('finished on %i: \n    %s'%(len(rlib), list(rlib.keys())))
        return rlib
            

class WorkFlow(Session): #worker with methods to build a CF workflow from
    """
    #===========================================================================
    # INSTRUCTIONS
    #===========================================================================
    sub-class this method for each CanFLood 'workflow' you wish to execute
        set a 'pars_d' attribute with all the parameters and filepaths
        and a 'name' attribute for the name of the flow
        
    add a 'run' method calling all the functions desired by the workflow
        this can use the 'tools' and 'toolbox' methods found in this baseclass
        
    
    """
    
    #===========================================================================
    # required attributes
    #===========================================================================
    name = None
    pars_d = None #parameters for control file
    tpars_d = dict() #parameters for passing to tools
    
    #===========================================================================
    # flow control attributes
    #===========================================================================
    """should be passed onto children
    overwrite with custom class to change"""
    attriMode = False
    
    
    def __init__(self,
                 session=None,

                 #init_q_d = {},
                 **kwargs):
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(self.name, str), 'must overwrite the \'name\' attribute with a subclass'

        #=======================================================================
        # init cascade
        #=======================================================================

        super().__init__(out_dir=os.path.join(session.out_dir, self.name),
                         tag = '%s'%datetime.datetime.now().strftime('%Y%m%d'),
                         crsid=self.crsid, #overrwrite the default with your default
                         **kwargs) #Session -> Qcoms -> ComWrkr

        #=======================================================================
        # attachments
        #=======================================================================
        self.session = session

        self.cf_tmpl_fp = os.path.join(self.session.cf_dir, r'canflood\_pars\CanFlood_control_01.txt')
        assert os.path.exists(self.cf_tmpl_fp), self.cf_tmpl_fp
        
        
        self.com_hndls = list(session.com_hndls) +[
            'out_dir', 'name', 'tag', 'cid']
        
        self.data_d = dict() #empty container for data
        
        self.wrkr_d = dict() #container for loaded workers
        
        #=======================================================================
        # checks
        #=======================================================================
        assert isinstance(self.pars_d, dict)

    #===========================================================================
    # HANDLERS-----------
    #===========================================================================
    def _get_wrkr(self, Worker,#check if the worker is loaded and return a setup worker
                  logger=None,

                  **kwargs
                  ): 
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('get_wrkr')
        cn =  Worker.__name__
        
        #=======================================================================
        # pull previously loaded
        #=======================================================================
        if cn in self.wrkr_d:
            log.debug('pulled \'%s\' from container'%cn)
        #=======================================================================
        # start your own
        #=======================================================================
        else:
            
            
            #collect ComWrkr pars
            """
            prep_cf() appends 'cf_fp'
            """
            for k in self.com_hndls:
                #'out_dir', 'name', 'tag', 'cid' ['absolute_fp', 'overwrite']
                kwargs[k] = getattr(self, k)
            
            #colect init pars
            if hasattr(Worker, '_init_plt'): #plotters
                kwargs['init_plt_d'] = self.init_plt_d
            
            if hasattr(Worker, '_init_standalone'): #Qgis
                kwargs['init_q_d'] = self.init_q_d 
                
            if hasattr(Worker, 'init_model'): #models
                kwargs.update({k:getattr(self, k) for k in ['base_dir', 'attriMode', 'upd_cf']})
                
            if hasattr(Worker, 'sid'): #Dike workers
                kwargs.update({k:getattr(self, k) for k in ['dikeID', 'segID', 'cbfn', 'ifidN']})
                
            kstr = ''.join(['\n    %s: %s'%(k,v) for k,v in kwargs.items()])

                
            log.debug('building %s w/%s'%(Worker.__name__, kstr))
            self.wrkr_d[cn] = Worker(logger=logger, **kwargs)
            
            """
            for k, v in kwargs.items():
                print('%s: %s'%(k, v))
            """

        weakWrkr = weakref.proxy(self.wrkr_d[cn])
        
        assert weakWrkr.__class__.__name__ == cn
        
        return weakWrkr
    
    def _retrieve(self,  #intelligently pull (or load) a data set
                       dtag, 
                       f=None, #method to use to retrieve data if not found,
                       logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('retr.%s'%dtag)
        assert callable(f), 'bad retrieval function'
        
        if dtag in self.data_d:
            data = self.data_d[dtag]
            log.info('pulled \'%s\'=%s from data_d'%(dtag, type(data)))
        else:
            data = f(logger=log) #execute the method
            self.data_d[dtag] = data
            
            #add map layers
            if isinstance(data, QgsMapLayer):
                self.mstore.addMapLayer(data)
            
            if isinstance(data, dict):
                for k,v in data.items():
                    if isinstance(v, QgsMapLayer):
                        self.mstore.addMapLayer(v)
        
        log.debug("got %s"%type(data))
        return data
    
    def _get_kwargs(self, wName, d=None): #get run kwargs for specific tool
        if d is None: d=self.tpars_d
        if isinstance(d, dict):
            if wName in d:
                return d[wName]
            
        return dict()
    
    #===========================================================================
    # HELPERS-----
    #===========================================================================
    def load_layers(self, #load layers ffrom a list of filepaths
                    fp_l,
                    layType = 'raster',
                    logger=None,
                    base_dir=None,
                    addMapLayer=True,
                    **kwargs):
        if logger is None: logger=self.logger
        log=logger.getChild('load_layers')
        assert isinstance(fp_l, list)
        
        d = dict()
        for fp_raw in fp_l:
            if not base_dir is None:
                fp = os.path.join(base_dir, fp_raw)
            else:
                fp = fp_raw
                
            assert os.path.exists(fp), fp
            
            if layType == 'raster':
                layer = self.load_rlay(fp, logger=log, **kwargs)
            elif layType=='vector':
                layer = self.load_vlay(fp, logger=log, **kwargs)
            else:
                raise Error('unrecognized layType: %s'%layType)
            
            if addMapLayer: self.mstore.addMapLayer(layer)
            d[layer.name()] = layer
            
        log.info('loaded %i'%len(d))
        return d
    
    def load_layers_dirs(self, #load layers from multiple directories
                         dir_l,
                    ext = '.tif',
                    aoi_vlay=None,
                    base_dir=None, #optional incase dir_l is relative
                    logger=None,
                    **kwargs):
        
        if logger is None: logger=self.logger
        log=logger.getChild('load_layers_dirs')
        assert isinstance(dir_l, list)
        #=======================================================================
        # collect all files
        #=======================================================================
        fp_d = dict()
        for data_dir in dir_l:
            if not base_dir is None: data_dir = os.path.join(base_dir, data_dir)
            assert os.path.exists(data_dir), data_dir
            rfn_l = [e for e in os.listdir(data_dir) if e.endswith(ext)]
            
            #check these are not there
            l = set(rfn_l).intersection(fp_d.keys())
            assert len(l)==0, 'duplicate filenames found: \n%s'%l
            
            fp_d.update({fn:os.path.join(data_dir, fn) for fn in rfn_l})
        
        #=======================================================================
        # loop and load
        #=======================================================================
        d = self.load_layers(list(fp_d.values()), 
                         layType={'.tif':'raster'}[ext],
                         logger=log,
                         aoi_vlay=aoi_vlay, **kwargs)
        
 
        return d
    
 
            
    
    def load_layers_tree(self, #load all layers in a tree
                         data_dir,
                         ext='.tif',
                         logger=None,
                         **kwargs):
        if logger is None: logger=self.logger
        log=logger.getChild('load_layers_tree')
        
        
        #get all files matching extension
        fps_l = list()
        for dirpath, _, fns in os.walk(data_dir):
            fps_l = fps_l + [os.path.join(dirpath, e) for e in fns if e.endswith(ext)]
            
        log.info('found %i matching files in %s'%(len(fps_l), data_dir))

        #load each
        d = self.load_layers(fps_l, 
                 layType={'.tif':'raster'}[ext],
                 logger=log,
                  **kwargs)
        
 
        return d

        
            
    #===========================================================================
    # TOOLS.BUILD-------
    #===========================================================================
    def prep_cf(self, pars_d, #Preparor.copy_cf_template and set_cf_pars
                logger=None):
        """
        this ones a bit weird because the main mechanism is a file write...
        """
        if logger is None: logger=self.logger
        log = logger.getChild('prep_cf')
        
        wrkr = self._get_wrkr(Preparor)
        
        #copy the template
        wrkr.tag = '%s_%s'%(self.name, self.tag)
        cf_fp = wrkr.copy_cf_template() #just copy the default template
        
        
        #=======================================================================
        # #set some basics
        #=======================================================================
        #fix filepaths
       
        
        #loop and pull
        new_pars_d =dict()
        for sect, keys in {
            'parameters':['impact_units', 'rtail', 'event_rels', 'felv', 'prec'],
            'dmg_fps':['curves'],
            'plotting':['impactfmt_str', 'color'],
            #'risk_fps':['evals'],
            }.items():
            d = {k:str(pars_d[k]) for k in keys if k in pars_d} #get these keys where present
            
            if sect == 'parameters':
                d['name']=self.name
            
            if len(d)>0:
                new_pars_d[sect] = tuple([d, '#set by testAll.py on %s'%wrkr.today_str])

        wrkr.set_cf_pars(new_pars_d)

        #=======================================================================
        # wrap
        #=======================================================================
        #update the session
        """subsequent workers will inherit the control file for this workflow"""
        self.cf_fp = cf_fp
        self.com_hndls.append('cf_fp')
        log.info('control file created: %s'%cf_fp)
        
        
        
        return cf_fp
    
    def prep_finvConstruct(self, #convert data to nest like
                   pars_d,
                   nest_data = dict(),
                   miti_data = dict(),
                   nestID = 0,
                    logger=None,
                    dkey='finv_vlay',
                    ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('prep_finvConstruct')
        
        wrkr = self._get_wrkr(Preparor)
        
        #=======================================================================
        # load the data
        #=======================================================================
        finv_vlay = self._retrieve(dkey,
               f = lambda logger=None: wrkr.load_vlay(
                   os.path.join(self.base_dir, pars_d['finv_fp']), logger=logger)
               )
               
               
        #=======================================================================
        # run converter
        #=======================================================================
        #prepare the nest data
        if len(nest_data)>0:
            nest_data2 = wrkr.build_nest_data(nestID=nestID, d_raw = nest_data, logger=log)
        else:
            nest_data2 = dict()

        #build the finv
        finv_vlay = wrkr.to_finv(finv_vlay,new_data={**nest_data2, **miti_data}, logger=log)
        
        self.data_d[dkey] = finv_vlay #set for subsequent workers
        """
        view(finv_vlay)
        """
        
        
        

    
    def prep_finv(self, pars_d,
                    logger=None,
                    dkey='finv_vlay'):
        
        if logger is None: logger=self.logger
        log = logger.getChild('prep_cf')
        
        wrkr = self._get_wrkr(Preparor)
        
        #=======================================================================
        # load the data
        #=======================================================================
        finv_vlay = self._retrieve(dkey,
               f = lambda logger=None: wrkr.load_vlay(
                   os.path.join(self.base_dir, pars_d['finv_fp']), logger=logger)
                                   )
        assert isinstance(finv_vlay, QgsVectorLayer), self.name
        #=======================================================================
        # execute
        #=======================================================================
        df = wrkr.finv_to_csv(finv_vlay, felv=pars_d['felv'], write=self.write, logger=log)
        if not self.write: wrkr.upd_cf_finv('none')
        
        return df
    
    
    
    def prep_curves(self, pars_d,
                    logger=None):
        
        if logger is None: logger=self.logger
        log = logger.getChild('prep_curves')
        
        wrkr = self._get_wrkr(Preparor)
        
        #=======================================================================
        # load the data
        #=======================================================================
        fp = os.path.join(self.base_dir, pars_d['curves_fp'])
        assert os.path.exists(fp), 'bad curve_fp: %s'%fp
        df_d = pd.read_excel(fp, sheet_name=None, header=None, index_col=None)
        log.info('loaded %i from %s'%(len(df_d), fp))
        #=======================================================================
        # write to control file
        #=======================================================================
        if not self.write:
            wrkr.set_cf_pars(
                {
                'dmg_fps':(
                    {'curves':fp}, 
                    '#\'curves\' file path set  at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                    ),
                 },
                )
        
        return df_d
    
    def prep_evals(self,
                   pars_d,
                   duplicate=True, #whether to make a new copy of the evals
                   logger=None,):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('prep_evals')
        
        wrkr = self._get_wrkr(Preparor)
        
        #=======================================================================
        # #get raw filepath
        #=======================================================================
        fp_raw = os.path.join(self.base_dir, pars_d.pop('evals_fp'))
        assert os.path.exists(fp_raw), 'bad raw evals: %s'%fp_raw
        
        #=======================================================================
        # copy over file
        #=======================================================================
        if duplicate:
            #get new filepath
            fp = os.path.join(self.out_dir, os.path.basename(fp_raw))
            shutil.copyfile(fp_raw, fp)
        else:
            fp = fp_raw
            
        #=======================================================================
        # #update control file
        #=======================================================================
        wrkr.set_cf_pars(
            {

                'risk_fps':({'evals':fp}, 
                            '#evals file path set from %s.py at %s'%(
                                __name__, datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')))
                          
             },

            )
        
        #return loaded data
        return pd.read_csv(fp, **wrkr.dtag_d['evals'])
    
    def rsamp_prep(self, pars_d,  #hazar draster sampler
                  logger=None,
                  dkey = 'rlay_d',
                  rlay_d = None, #optional container of raster layers
                  **kwargs):
        
        if logger is None: logger=self.logger
        log = logger.getChild('rsamp_prep')
        
        wrkr = self._get_wrkr(Rsamp)
        
        #=======================================================================
        # load the data
        #=======================================================================
        if rlay_d is None:
            fp = os.path.join(self.base_dir, pars_d['raster_dir'])
            rlay_d = self._retrieve(dkey,
                   f = lambda logger=None: wrkr.load_rlays(fp, logger=logger))
            
        if 'aoi_fp' in pars_d:
            fp = os.path.join(self.base_dir, pars_d['aoi_fp'])
            aoi_vlay = self._retrieve('aoi_vlay',
                   f = lambda logger=None: wrkr.load_vlay(fp, logger=logger))
        else:
            aoi_vlay=None
        #=======================================================================
        # execute
        #=======================================================================
        
        rlay_l = wrkr.runPrep(list(rlay_d.values()), aoi_vlay = aoi_vlay,logger=log,
                              **kwargs)
        
        #=======================================================================
        # wrap
        #=======================================================================
        self.data_d['rlay_d'] = {lay.name():lay for lay in rlay_l}
        
        
    
    def rsamp_haz(self, pars_d,  #hazar draster sampler
                  logger=None,
                  dkey = 'rlay_d',
                  rlay_d = None, #optional container of raster layers
                  rkwargs=None,
                  ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('rsamp_haz')
        assert 'raster_dir' in pars_d, '%s missing raster_dir'%self.name
        
        wrkr = self._get_wrkr(Rsamp)
        
        
        #=======================================================================
        # load the data
        #=======================================================================
        if rlay_d is None:
            fp = os.path.join(self.base_dir, pars_d['raster_dir'])
            rlay_d = self._retrieve(dkey,
                   f = lambda logger=None: wrkr.load_rlays(fp, logger=logger))

        #dtm layer
        if 'dtm_fp' in pars_d:
            fp = os.path.join(self.base_dir, pars_d['dtm_fp'])
            dtm_rlay = self._retrieve('dtm_rlay',
                   f = lambda logger=None: wrkr.load_rlay(fp, logger=logger))
        else:
            dtm_rlay=None
        
                
        #pull previously loaded
        finv_vlay = self.data_d['finv_vlay']
        
        
        #=======================================================================
        # execute
        #=======================================================================
        #user provided run kwargs
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        #kwargs from control file
        kwargs = {k:pars_d[k] for k in ['dthresh', 'as_inun'] if k in pars_d}
        
        res_vlay = wrkr.run(list(rlay_d.values()), finv_vlay, dtm_rlay=dtm_rlay,
                              **{**rkwargs, **kwargs})
        
        #=======================================================================
        # #post
        #=======================================================================
        wrkr.check()
        
        df = wrkr.write_res(res_vlay, write=self.write)
        if not self.write: wrkr.out_fp = 'none' #placeholder
        wrkr.update_cf(self.cf_fp)
        
        
        #=======================================================================
        # plots
        #=======================================================================
        if self.plot:
            fig = wrkr.plot_boxes()
            self.output_fig(fig)
            fig = wrkr.plot_hist()
            self.output_fig(fig)
        
        return df
    """
    for k in df.columns:
        print(k)
    """

    def rsamp_dtm(self, pars_d,  #hazar draster sampler
                  logger=None,
                  rkwargs=None,
                  ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('rsamp_dtm')
        
        wrkr = self._get_wrkr(Rsamp)
        
        #=======================================================================
        # load the data
        #=======================================================================
        fp = os.path.join(self.base_dir, pars_d['dtm_fp'])
        dtm_rlay = self._retrieve('dtm_rlay',
               f = lambda logger=None: wrkr.load_rlay(fp, logger=logger))

        #pull previously loaded
        finv_vlay = self.data_d['finv_vlay']
        
        #=======================================================================
        # execute
        #=======================================================================
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        res_vlay = wrkr.run([dtm_rlay], finv_vlay,  fname='gels',
                              **rkwargs)
        #=======================================================================
        # #post
        #=======================================================================
        wrkr.dtm_check(res_vlay)
        df = wrkr.write_res(res_vlay, write=self.write)
        
        if not self.write: wrkr.out_fp = 'none' #placeholder
        wrkr.upd_cf_dtm(cf_fp = self.cf_fp)
        
        return df
    
    def lisamp(self, pars_d,  #fail poly sampler
                  logger=None,
                  dkey = 'fpol_d',
                  fpol_d = None,
                  ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('lisamp')
        
        wrkr = self._get_wrkr(LikeSampler)
        
        #=======================================================================
        # load the data
        #=======================================================================
        if fpol_d is None:
            fp = os.path.join(self.base_dir, pars_d['fpol_dir'])
            fpol_d = self._retrieve(dkey,
                   f = lambda logger=None: wrkr.load_lpols2(fp, logger=logger))

                
        #pull previously loaded
        finv_vlay = self.data_d['finv_vlay']
        
        
        #=======================================================================
        # execute
        #=======================================================================
        rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        kwargs = {k:pars_d[k] for k in [] if k in pars_d}
        
        """for event_rels, need to use tpars_d"""
        res_df = wrkr.run(finv_vlay, fpol_d,  **{**kwargs, **rkwargs})
        
        #=======================================================================
        # #post
        #=======================================================================
        wrkr.check()
        if self.write: 
            wrkr.write_res(res_df)
        else:
            wrkr.out_fp = 'none'
            
        wrkr.update_cf(self.cf_fp)
        
        #=======================================================================
        # plot
        #=======================================================================
        if self.plot:
            fig = wrkr.plot_hist()
            self.output_fig(fig)
            fig = wrkr.plot_boxes()
            self.output_fig(fig)
        
        return res_df

    def validate(self, pars_d,  #validation
                  logger=None,

                  ):
        """because we're not using the control file for testing... 
            no point in running the validator"""
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('validate')
        
        wrkr = self._get_wrkr(Vali)
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert 'validate' in pars_d
        
        vtag = pars_d.pop('validate')
        
        #=======================================================================
        # setup
        #=======================================================================
        wrkr.config_cf()
        
        #=======================================================================
        # validate by vtag
        #=======================================================================
        for k, modObj in {
                'risk1':Risk1, 
                'dmg2':Dmg2,
                            }.items(): 
            if not k == vtag: continue 
            
            #do the check
            errors = wrkr.cf_check(modObj)
            if not len(errors)==0:
                raise Error('\'%s\' got some errors \n    %s'%(vtag, errors))
            
            wrkr.cf_mark() #update the controlf ile
            
        log.debug('finished')
        
        
    #===========================================================================
    # TOOLS.MODEL------------
    #===========================================================================
    def risk1(self,
              pars_d=None,
              logger=None,
              plot=None, #for impact only runs we usually pass False here
              rkwargs = None, #flow control keys for this run
              ): #run risk1
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('risk1')
        if pars_d is None: pars_d = self.pars_d
        if plot is None: plot=self.plot
        
        
        #=======================================================================
        # setup
        #=======================================================================
        wrkr = self._get_wrkr(Risk1)
        
        #get control keys for this tool
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        

        wrkr.setup_fromData(self.data_d, logger=log) #setup w/ the pre-loaded data
        
        #=======================================================================
        # execute
        #=======================================================================
        res_ttl, res_df = wrkr.run(**rkwargs)
            
        #=======================================================================
        # plots
        #=======================================================================
        if plot:
            ttl_df = wrkr.set_ttl(tlRaw_df=res_ttl)
            for y1lab in ['AEP', 'impacts']:
                fig = wrkr.plot_riskCurve(ttl_df, y1lab=y1lab)
                self.output_fig(fig)
                
        #=======================================================================
        # output
        #=======================================================================
        if self.write:
            if len(res_ttl)>0: wrkr.output_ttl()
            wrkr.output_etype()
            if not res_df is None: wrkr.output_passet()
            
        #=======================================================================
        # wrap
        #=======================================================================
        res_d = dict()
        res_d['r_ttl'] = res_ttl
        res_d['eventypes'] = wrkr.eventType_df
        if not res_df is None:
            res_d['r_passet'] = res_df
        
        """"
        wrkr.exlikes
        self.data_d.keys()
        data_d['finv']
        self.cf_fp
        self.res_d.keys()
        self.com_hndls
        """
        self.data_d = {**self.data_d, **res_d}
        return res_d
    
    def dmg2(self,
              pars_d=None,
              logger=None,
              rkwargs = None, #flow control keys for this run
              
              #extra outputs
              bdmg_smry=False,
              dmgs_expnd =False,
              ): #run risk1
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('dmg2')
        if pars_d is None: pars_d = self.pars_d
        
        res_d = dict()
        #=======================================================================
        # setup
        #=======================================================================
        wrkr = self._get_wrkr(Dmg2)
        
        #get control keys for this tool
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        wrkr.setup_fromData(self.data_d) #setup w/ the pre-loaded data
        
        #=======================================================================
        # execute
        #=======================================================================
        cres_df = wrkr.run(**rkwargs)
        
        #handle main dmgs file
        if self.write: 
            wrkr.output_cdmg()
            if self.upd_cf: 
                wrkr.update_cf()
                
                
        res_d['dmgs'] = cres_df #total damages by cid
        self.data_d['dmgs'] = res_d['dmgs'].copy() #set for risk2
        
        #attribution
        if self.attriMode:
            res_d[wrkr.attrdtag_out] = wrkr.get_attribution(cres_df)
            self.data_d[wrkr.attrdtag_out] = res_d[wrkr.attrdtag_out].copy() #set for risk2
            if self.write: wrkr.output_attr(upd_cf = self.upd_cf)
            
        #summary damages workbook
        if bdmg_smry:
            res_d['dmgs_smry'] = wrkr.bdmg_smry() #writes excel to file
        
        #raw damages by bid
        if dmgs_expnd:
            res_d['dmgs_bid'] = wrkr.res_df 
            if self.write: wrkr.output_bdmg()
            
        res_d['depths'] = wrkr.ddf
        #=======================================================================
        # plots
        #=======================================================================
        if self.plot:
            fig = wrkr.plot_boxes(logger=log)
            self.output_fig(fig, logger=log)
            
            fig = wrkr.plot_hist(logger=log)
            self.output_fig(fig, logger=log)

        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished w/ %s'%list(res_d.keys()))
        
        """
        res_d.keys()
        """
        return res_d
    
    
    def risk2(self,
              pars_d=None,
              logger=None,
              rkwargs = None, #flow control keys for this run
              plot = None, #some workers may want to delay plotting

              ): #run risk1
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('risk2')
        if pars_d is None: pars_d = self.pars_d
        if plot is None: plot=self.plot
        
        #=======================================================================
        # setup
        #=======================================================================
        wrkr = self._get_wrkr(Risk2)
        
        #get control keys for this tool
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        """
        self.tpars_d
        """
        
        #pull out setup kwargs
        skwargs = {k:rkwargs.pop(k) for k in rkwargs.copy().keys() if k in ['prep_kwargs']}
        
        wrkr.setup_fromData(self.data_d, **skwargs) #setup w/ the pre-loaded data
        
        #=======================================================================
        # execute
        #=======================================================================
        """for event_rels, pass in the pars_d
                see prep_cf()"""
        res_ttl, res_df = wrkr.run(**rkwargs)
 
        #=======================================================================
        # plots
        #=======================================================================
        if plot:
            ttl_df = wrkr.set_ttl(tlRaw_df=res_ttl)
            for y1lab in ['AEP', 'impacts']:
                fig = wrkr.plot_riskCurve(ttl_df, y1lab=y1lab)
                self.output_fig(fig)
                
        #=======================================================================
        # output
        #=======================================================================
        if self.write:
            wrkr.output_ttl()
            wrkr.output_etype()
            if not res_df is None: wrkr.output_passet()
            if wrkr.attriMode: wrkr.output_attr()
            
        #=======================================================================
        # wrap
        #=======================================================================
        res_d = {
            'r_ttl': res_ttl,
            'eventypes':wrkr.eventType_df}
        
        if not res_df is None:
            res_d['r_passet'] = res_df
        
        if wrkr.attriMode:
            res_d[wrkr.attrdtag_out] = wrkr.att_df.copy()
            
        #set for results workers
        self.data_d = {**self.data_d, **res_d}
        
        return res_d

    #===========================================================================
    # TOOLS.RESULTS-----------------
    #===========================================================================
    def djoin(self, 
              pars_d=None,
                    logger=None,
                    dkey='finv_vlay',
                    dkey_tab='r_passet',
                    rkwargs=None,
                    ):
        """to run djoin on L2 dmg impacts only:
            pass the following tot his caller:
                    dkey_tab = 'dmgs'
                    rkwargs={'relabel':None}
                """
        raise Error('getting string type on some risk fields with nulls')
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('djoin')
        if pars_d is None: pars_d = self.pars_d
        
        #=======================================================================
        # setup
        #=======================================================================
        wrkr = self._get_wrkr(Djoiner, fp_attn=dkey_tab)
        
        """should load r_passet from the CF if not found"""
        wrkr.setup_fromData(self.data_d) #setup w/ the pre-loaded data
        #=======================================================================
        # load the data
        #=======================================================================
        finv_vlay = self._retrieve(dkey,
               f = lambda logger=None: wrkr.load_vlay(
                   os.path.join(self.base_dir, pars_d['finv_fp']), logger=logger)
                                   )
        #=======================================================================
        # execute
        #=======================================================================
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        jvlay = wrkr.run(finv_vlay, **rkwargs)
        
        #=======================================================================
        # write result
        #=======================================================================
        if self.write:
            out_fp = wrkr.vlay_write(jvlay, logger=log)
            

        
        return {'jvlay':jvlay}
    
    def plot_risk_ttl(self,  #single risk plot of total results
                      pars_d=None,
                    logger=None,
                    ylabs = ['AEP', 'impacts'], #types of plots to generate
                    rkwargs=None,
                    ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_risk_ttl')
        if pars_d is None: pars_d = self.pars_d
        
        """just let it pass... if the function is called the user wants to plot"""
        #assert self.plot 
        
        #=======================================================================
        # setup worker
        #=======================================================================
        wrkr = self._get_wrkr(RiskPlotr)
        wrkr.setup_fromData(self.data_d) #setup w/ the pre-loaded data
        #=======================================================================
        # get plots
        #=======================================================================
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        for ylab in ylabs:
            fig = wrkr.plot_riskCurve(y1lab=ylab, **rkwargs)
            self.output_fig(fig)
        
    def plot_failSplit(self,  #single risk plot of total results

                    logger=None,
                    ylabs = ['AEP', 'impacts'], #types of plots to generate
                    rkwargs=None,
                    ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_risk_ttl')
        assert self.attriMode
        
        #=======================================================================
        # setup worker
        #=======================================================================
        wrkr = self._get_wrkr(Attr)
        wrkr.setup_fromData(self.data_d) #setup w/ the pre-loaded data
        
        si_ttl = wrkr.get_slice_noFail()
        
        #=======================================================================
        # get plots
        #=======================================================================
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        
        for ylab in ylabs:
            fig = wrkr.plot_slice(si_ttl, y1lab=ylab, logger=log, **rkwargs)
            self.output_fig(fig)
            
        return {'si_ttl':si_ttl}
    
    def compare(self, #run compare tools 
                    fps_d, 
                    logger=None,
                    cf_compare=True,
                    ylabs = ['AEP', 'impacts'], #types of plots to generate

                    ):
        """
        no point in passing parameters...
        """
        assert self.write, 'write needs to be enabled for spawning the children'
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('compare')

        
        wrkr = self._get_wrkr(Cmpr, fps_d=fps_d)
        wrkr.setup_fromData(self.data_d) #setup w/ the pre-loaded data
        #=======================================================================
        # comapre control files
        #=======================================================================
        res_d = dict()
        if cf_compare:
            mdf = wrkr.cf_compare()
            res_d['cf_compare'] = mdf.copy()
            if self.write:
                mdf.to_csv(os.path.join(wrkr.out_dir, 'CFcompare_%s_%i.csv'%(wrkr.tag, len(mdf.columns))))
                
        #=======================================================================
        # plots
        #=======================================================================
        if self.plot:
            for ylab in ylabs:
                fig = wrkr.riskCurves(y1lab=ylab, logger=log)
                self.output_fig(fig, logger=log)
            
        return res_d
    
    def merge(self, fps_d,
              logger=None,
              ylabs = ['AEP', 'impacts'], #types of plots to generate
              ):
        
        assert self.write, 'write needs to be enabled for spawning the children'
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('merge')

        
        wrkr = self._get_wrkr(Cmpr, fps_d=fps_d)
        wrkr.setup_fromData(self.data_d) #setup w/ the pre-loaded data
        
        #=======================================================================
        # get data
        #=======================================================================
        cdxind, cWrkr = wrkr.build_composite()
        
        
        #=======================================================================
        # plots
        #=======================================================================
        if self.plot:
            for ylab in ylabs:
                fig = wrkr.riskCurves(y1lab=ylab, logger=log)
                self.output_fig(fig, logger=log)
        
        
        
    
    #===========================================================================
    # TOOLS DIKES-----------
    #===========================================================================
    def dikes_expo(self,
                     pars_d,
                    logger=None,
                    rlay_d=None,
                    rkwargs=None,
                    
                    #run contgrols
                    breach_pts=True,
                    
                   ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('dikes_expo')
        if pars_d is None: pars_d = self.pars_d
        
        
        wrkr = self._get_wrkr(Dexpo)
        #=======================================================================
        # load the data
        #=======================================================================
        if rlay_d is None:
            fp = os.path.join(self.base_dir, pars_d['raster_dir'])
            rlay_d = self._retrieve('dikes_rlay_d',
                   f = lambda logger=None: self.load_layers_dirs([fp], logger=logger))

        #dtm layer
        fp = os.path.join(self.base_dir, pars_d['dtm_fp'])
        dtm_rlay = self._retrieve('dtm_rlay',
               f = lambda logger=None: wrkr.load_dtm(fp, logger=logger))

            
        #dikes layer
        fp = os.path.join(self.base_dir, pars_d['dikes_fp'])
        dike_vlay = self._retrieve('dike_vlay',
           f = lambda logger=None: wrkr.load_vlay(fp, logger=logger))
        
        dike_vlay = wrkr.prep_dike(dike_vlay)
        
        
        #==========================================================================
        # execute
        #==========================================================================
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        dxcol, vlay_d = wrkr.get_dike_expo(rlay_d, dike_vlay=dike_vlay, dtm_rlay=dtm_rlay,
                                           **rkwargs)
        
        expo_df = wrkr.get_fb_smry()
        
        #get just the breach points
        if breach_pts:
            breach_vlay_d = wrkr.get_breach_vlays()
        
        #=======================================================================
        # plots
        #=======================================================================
        if self.plot:

            for sidVal in wrkr.sid_vals:
                fig = wrkr.plot_seg_prof(sidVal)
                wrkr.output_fig(fig)
        #=======================================================================
        # outputs
        #=======================================================================
        

        
        if self.write: 
            wrkr.output_expo_dxcol()
            _ = wrkr.output_expo_df()
        
            wrkr.output_vlays()
            if breach_pts:
                wrkr.output_breaches()
                
        #=======================================================================
        # wrap
        #=======================================================================
        res_d = {
            'dExpo_dxcol':wrkr.expo_dxcol,
            'dExpo':wrkr.expo_df
            
            }
        
        #set for siblings
        self.data_d['dExpo'] = wrkr.expo_df.copy() 
        
        return res_d

    def dikes_vuln(self,
                     pars_d,
                    logger=None,

                    rkwargs=None,
                    

                    
                   ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('dikes_vuln')
        if pars_d is None: pars_d = self.pars_d
        
        
        wrkr = self._get_wrkr(Dvuln)
        
        #=======================================================================
        # get data
        #=======================================================================
        #collect inputs for load_expo
        """should be a nicer way to do this"""
        if 'dExpo' in self.data_d:
            df = self.data_d['dExpo']
        else:
            df=None
        if 'dexpo_fp' in self.pars_d:
            fp = self.pars_d['dexpo_fp']
        else:
            fp=None
            
        wrkr.load_expo(fp=fp, df=df)
        
        #fragility functions
        wrkr.load_fragFuncs(os.path.join(self.base_dir, pars_d['dcurves_fp']))
        
        #=======================================================================
        # execute
        #=======================================================================
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        
        pf_df = wrkr.get_failP(**rkwargs)
        wrkr.set_lenfx() #apply length effects
        #=======================================================================
        # write
        #=======================================================================
        if self.write:
            wrkr.output_vdfs()
            
        #=======================================================================
        # wrap
        #=======================================================================
        res_d ={
            'dike_pfail':wrkr.pf_df.copy(),
            'dike_pfail_lfx':wrkr.pfL_df.copy()
            }
        
        self.data_d.update(res_d) #add both for children
        
        return res_d

    def dikes_join(self,
                     pars_d,
                    logger=None,

                    rkwargs=None,
                   ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('dikes_join')
        if pars_d is None: pars_d = self.pars_d
        
        
        wrkr = self._get_wrkr(DikeJoiner)
        
        #=======================================================================
        # get data
        #=======================================================================
        wrkr.load_pfail_df(df = self.data_d['dike_pfail'])
        wrkr.load_ifz_fps(pars_d['eifz_d'], base_dir=self.base_dir)
        
        #=======================================================================
        # execute
        #=======================================================================
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        
        vlay_d = wrkr.join_pfails(**rkwargs)
        
        #=======================================================================
        # output
        #=======================================================================
        if self.write:
            wrkr.output_vlays()
            
        log.debug('finished')
        return {'dike_pfail_d':vlay_d}
        
    #===========================================================================
    # TOOL BOXES-------
    #===========================================================================
    def tb_build(self,  #build tools
              pars_d=None, #single assetModel run for this workflow
              fpoly = True, #whether to build exlikes
              rlay_d=None, #optional rasters to sample
              fpol_d=None, #optional fail polys to sample
              logger=None,
              
              #tool kwargs
              
              finvConstructKwargs = {}, #kwargs for prep_finvConstruct
              rsampPrepKwargs = {}, #kwargs for rsamp_prep
              
              ):
        """"
        todo: improve tool kwarg handling 
            tool boxes were supposed to be for 'typical' runs... 
                but seems more efficient to pass kwargs rather than develop new functions at this level
                
            change _get_kwargs() to be WorkFLow function names? (rather than worker class names)
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = logger.getChild('tb_build')
        if pars_d is None: pars_d = self.pars_d
        log.info('on %i: %s'%(len(pars_d), pars_d.keys()))
        
        res_d = dict()

        #=======================================================================
        # prepare
        #=======================================================================
        cf_fp = self.prep_cf(pars_d, logger=log) #setuip the control file
        
        if len(finvConstructKwargs)>0: #convert data to nest like
            self.prep_finvConstruct(pars_d, **finvConstructKwargs)
        
        res_d['finv'] = self.prep_finv(pars_d, logger=log)
        
        if 'curves_fp' in pars_d:
            res_d['curves'] = self.prep_curves(pars_d, logger=log)
            
        
        #=======================================================================
        # raster sample
        #=======================================================================
        if len(rsampPrepKwargs)>0:
            self.rsamp_prep(pars_d, logger=log, **rsampPrepKwargs)
            
        res_d['expos'] = self.rsamp_haz(pars_d, logger=log, rlay_d=rlay_d)
        
        #=======================================================================
        # dtm sample
        #=======================================================================
        if pars_d['felv']=='ground':
            res_d['gels'] = self.rsamp_dtm(pars_d, logger=log)
            
        #=======================================================================
        # event variables
        #=======================================================================
        """passing to control file in prep_cf()
        loading here for linked runs"""
        
        res_d['evals'] = self.prep_evals(pars_d, logger=log)
        
        #=======================================================================
        # pfail
        #=======================================================================
        if fpoly:
            res_d['exlikes'] = self.lisamp(pars_d, logger=log, fpol_d=fpol_d)
            
        #=======================================================================
        # validate
        #=======================================================================
        """no! were not using the controlf iles
        self.validate(pars_d, logger=log)"""
        """
        self.data_d.keys()
        res_d.keys()
        res_d.values()
        """

        #=======================================================================
        # #setup model runs
        #=======================================================================
        for k,v in res_d.items():
            assert isinstance(v, pd.DataFrame) or isinstance(v, dict), 'bad type on \'%s\': %s'%(k, type(v))
        self.data_d = {**res_d.copy(), **{'finv_vlay':self.data_d['finv_vlay']}}

        #=======================================================================
        # wrap
        #=======================================================================

        
        return res_d #{output name: output object}
    
    def tb_dikes(self,
              pars_d=None, #single assetModel run for this workflow
              logger=None,
                 ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('tb_dikes')
        if pars_d is None: pars_d = self.pars_d
        log.info('on %i: %s'%(len(pars_d), pars_d.keys()))
        

        #=======================================================================
        # tools
        #=======================================================================
        res_d = self.dikes_expo(pars_d, logger=log)
        
        d = self.dikes_vuln(pars_d, logger=log)
        res_d = {**res_d, **d}
        
        d = self.dikes_join(pars_d, logger=log)
        res_d = {**res_d, **d}
        
        log.info('finished w/ %i: \n    %s'%(len(res_d), res_d.keys()))
        
        return res_d
    
    def run(self, **kwargs):
        raise Error('overwrite with your own run method!')
    
    
    def __exit__(self, #destructor
                 *args,**kwargs):
        """
        call this before moving onto the next workflow
        """
        #clear your own
        self.mstore.removeAllMapLayers()
        
        #clear your children
        for cn, wrkr in self.wrkr_d.items():
            wrkr.__exit__(*args,**kwargs)
            
        #del self.wrkr_d
        
        #remove data objects
        del self.data_d
        
        super().__exit__(*args,**kwargs) #initilzie teh baseclass
        gc.collect()





if __name__ == '__main__':
    print('???')
    

    

    
    
    
    
    
    
    
    
    
    
    
    