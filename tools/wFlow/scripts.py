'''
Created on Jan. 23, 2021

@author: cefect


executing a CanFlood workflow froma python console
'''

#===============================================================================
# imports----------
#===============================================================================
import unittest, tempfile, inspect, logging, os, fnmatch, pickle, datetime

from qgis.core import QgsCoordinateReferenceSystem, QgsMapLayerStore, QgsMapLayer
import pandas as pd
import numpy as np


#===============================================================================
# cf helpers
#===============================================================================
from hlpr.logr import basic_logger
 
from hlpr.exceptions import Error
import hlpr.Q
import hlpr.plot

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
#===============================================================================
# methods---------
#===============================================================================

class Session(hlpr.Q.Qcoms, hlpr.plot.Plotr): #handle one test session 
    
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
    # #CanFlood attributes   
    #===========================================================================
    com_hndls = ('absolute_fp', 'overwrite')
    absolute_fp = True

    overwrite=True
    attriMode=False
    
    #===========================================================================
    # program vars
    #===========================================================================



    def __init__(self,
                 base_dir = None, #CanFlood project directory
                 projName = 'proj01',

                 out_dir = None,
                 write=True, #whether to write results to file
                 plot=False, #whether to write plots to file
                 logger=None,
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


    #===========================================================================
    # CHILD HANDLING--------
    #===========================================================================

    def _run_wflow(self, #execute a single workflow 
                   WorkFlow, #workflow object to run
                   **kwargs):
        
        log = self.logger.getChild('r.%s'%WorkFlow.name)
        
        #=======================================================================
        # update crs
        #=======================================================================
        if not WorkFlow.crsid == self.crsid:
            self.set_crs(WorkFlow.crsid)

        #===================================================================
        # # init the flow 
        #===================================================================
        
        #collect pars
        """similar to _get_wrkr().. but less flexible"""
        for k in list(self.com_hndls) + ['init_plt_d', 'init_q_d', 'write', 'base_dir', 'plot']:
            kwargs[k] = getattr(self, k)

        runr = WorkFlow(logger=log, session=self,**kwargs)

        #===================================================================
        # execute the flow
        #===================================================================
        runr.run()
        return runr
        

    
    #==========================================================================
    # RUNNERS----------
    #==========================================================================

    def run(self, #run a set of WorkFlows
            wFLow_l, #set of workflows to run
            **kwargs
            ):
        """
        lets the user define their own methods for batching together workflows
        
        """
        log=self.logger.getChild('r')
 
 
        rlib = dict()
        for fWrkr in wFLow_l:
            rlib[fWrkr.name] = self._run_wflow(fWrkr, **kwargs)
            
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
    tpars_d = None #parameters for passing to tools
    
    
    def __init__(self,
                 session=None,
                 #init_q_d = {},
                 **kwargs):
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(self.name, str), 'must overwrite the \'name\' attribute with a subclass'
        
        #=======================================================================
        # update q handles
        #=======================================================================

        
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
        
        self.cf_tmpl_fp = os.path.join(self.session.base_dir, r'canflood\_pars\CanFlood_control_01.txt')
        assert os.path.exists(self.cf_tmpl_fp), self.cf_tmpl_fp
        
        
        self.com_hndls = list(session.com_hndls) +[
            'out_dir', 'name', 'tag']
        
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
        if logger is None: logger=self.logger
        log = logger.getChild('get_wrkr')
        cn =  Worker.__class__.__name__
        
        #=======================================================================
        # pull previously loaded
        #=======================================================================
        if cn in self.wrkr_d:
            wrkr = self.wrkr_d[cn]
            log.debug('pulled \'%s\' from container'%cn)
        #=======================================================================
        # start your own
        #=======================================================================
        else:
            
            
            #collect common pars
            for k in self.com_hndls:
                kwargs[k] = getattr(self, k)
            
            #colect init pars
            if hasattr(Worker, '_init_plt'): #plotters
                kwargs['init_plt_d'] = self.init_plt_d
            
            if hasattr(Worker, '_init_standalone'): #Qgis
                kwargs['init_q_d'] = self.init_q_d 
                
            if hasattr(Worker, 'init_model'): #models
                kwargs['base_dir'] = self.base_dir
                
            log.debug('building %s w/ %s'%(Worker.__class__.__name__, kwargs))
            wrkr = Worker(logger=logger, **kwargs)


        
        return wrkr
    
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
    # TOOLS-------
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
        cf_fp = wrkr.copy_cf_template() #just copy the default template
        
        
        #=======================================================================
        # #set some basics
        #=======================================================================
        #fix filepaths
        pars_d['evals'] = os.path.join(self.base_dir, pars_d.pop('evals_fp'))
        
        #loop and pull
        new_pars_d =dict()
        for sect, keys in {
            'parameters':['impact_units', 'rtail', 'event_rels', 'felv', 'prec'],
            'dmg_fps':['curves'],
            'plotting':['impactfmt_str'],
            'risk_fps':['evals'],
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

        #=======================================================================
        # execute
        #=======================================================================
        df = wrkr.finv_to_csv(finv_vlay, felv=pars_d['felv'], write=self.write, logger=log)
        if not self.write: wrkr.upd_cf_finv('none')
        
        return df
    
    def rsamp_haz(self, pars_d,  #hazar draster sampler
                  logger=None,
                  dkey = 'rlay_d',
                  ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('prep_cf')
        
        wrkr = self._get_wrkr(Rsamp)
        
        #=======================================================================
        # load the data
        #=======================================================================
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
        
        kwargs = {k:pars_d[k] for k in ['dthresh', 'as_inun'] if k in pars_d}
        res_vlay = wrkr.run(list(rlay_d.values()), finv_vlay, dtm_rlay=dtm_rlay,
                              **kwargs)
        
        #=======================================================================
        # #post
        #=======================================================================
        wrkr.check()
        
        df = wrkr.write_res(res_vlay, write=self.write)
        if not self.write: wrkr.out_fp = 'none' #placeholder
        wrkr.update_cf(self.cf_fp)
        
        return df

    def rsamp_dtm(self, pars_d,  #hazar draster sampler
                  logger=None,
                  dkey = 'dtm_rlay',
                  ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('prep_cf')
        
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
        kwargs = {k:pars_d[k] for k in ['dthresh', 'as_inun'] if k in pars_d}
        res_vlay = wrkr.run([dtm_rlay], finv_vlay, dtm_rlay=dtm_rlay, fname='gels',
                              **kwargs)
        #=======================================================================
        # #post
        #=======================================================================
        wrkr.dtm_check(res_vlay)
        df = wrkr.write_res(res_vlay, write=self.write)
        
        if not self.write: wrkr.out_fp = 'none' #placeholder
        wrkr.upd_cf_dtm()
        
        return df
    
    def lisamp(self, pars_d,  #fail poly sampler
                  logger=None,
                  dkey = 'lpol_d',
                  ):
        
        if logger is None: logger=self.logger
        log = logger.getChild('lisamp')
        
        wrkr = self._get_wrkr(LikeSampler)
        
        #=======================================================================
        # load the data
        #=======================================================================
        fp = os.path.join(self.base_dir, pars_d['lpol_dir'])
        lpol_d = self._retrieve(dkey,
               f = lambda logger=None: wrkr.load_lpols2(fp, logger=logger))

                
        #pull previously loaded
        finv_vlay = self.data_d['finv_vlay']
        
        
        #=======================================================================
        # execute
        #=======================================================================
        
        kwargs = {k:pars_d[k] for k in ['lfield', 'event_rels'] if k in pars_d}
        res_df = wrkr.run(finv_vlay, lpol_d,  **kwargs)
        
        #=======================================================================
        # #post
        #=======================================================================
        wrkr.check()
        if self.write: 
            wrkr.write_res(res_df)
        else:
            wrkr.out_fp = 'none'
        wrkr.update_cf()
        
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
        
        

    def risk1(self,
              pars_d=None,
              logger=None,
              rkwargs = None, #flow control keys for this run
              ): #run risk1
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('risk1')
        if pars_d is None: pars_d = self.pars_d
        
        
        #=======================================================================
        # setup
        #=======================================================================
        wrkr = self._get_wrkr(Risk1)
        
        #get control keys for this tool
        if rkwargs is None: rkwargs = self._get_kwargs(wrkr.__class__.__name__)
        

        wrkr.setup_fromData(self.data_d) #setup w/ the pre-loaded data
        
        #=======================================================================
        # execute
        #=======================================================================
        res_ttl, res_df = wrkr.run(**rkwargs)
            
        #=======================================================================
        # plots
        #=======================================================================
        if self.plot:
            ttl_df = wrkr.prep_ttl(tlRaw_df=res_ttl)
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

    def djoin(self, pars_d=None,
                    logger=None,
                    dkey='finv_vlay',
                    dkey_tab='r_passet'):
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

        jvlay = wrkr.run(finv_vlay, keep_fnl='all')
        
        #=======================================================================
        # write result
        #=======================================================================
        if self.write:
            out_fp = wrkr.vlay_write(jvlay, logger=log)
            

        
        return {'jvlay':jvlay}
    #===========================================================================
    # TOOL BOXES-------
    #===========================================================================
    def tb_build(self,  #workflow for tutorial 1a
              pars_d=None, #single assetModel run for this workflow
              fpoly = True, #whether to build exlikes
              logger=None,
              ):
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
        
        res_d['finv'] = self.prep_finv(pars_d, logger=log)
        
        #=======================================================================
        # raster sample
        #=======================================================================
        res_d['expos'] = self.rsamp_haz(pars_d, logger=log)
        
        #=======================================================================
        # dtm sample
        #=======================================================================
        if pars_d['felv']=='ground':
            res_d['ground'] = self.rsamp_dtm(pars_d, logger=log)
            
        #=======================================================================
        # event variables
        #=======================================================================
        """passing to control file in prep_cf()
        loading here for linked runs"""
        
        res_d['evals'] = pd.read_csv(pars_d['evals'], **Preparor.dtag_d['evals'])
        
        #=======================================================================
        # pfail
        #=======================================================================
        if fpoly:
            res_d['exlikes'] = self.lisamp(pars_d, logger=log)
            
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
            assert isinstance(v, pd.DataFrame), 'bad type on \'%s\': %s'%(k, type(v))
        self.data_d = {**res_d.copy(), **{'finv_vlay':self.data_d['finv_vlay']}}
        #self.mstore.removeAllMapLayers() 
        
        #add some dummies to the control file
        
        #=======================================================================
        # wrap
        #=======================================================================

        
        return res_d #{output name: output object}
    
    def run(self, **kwargs):
        raise Error('overwrite with your own run method!')
    
    
    def __exit__(self, exc_type, exc_value, traceback): #clean up the workflow
        """
        call this before moving onto the next workflow
        """
        self.mstore.removeAllMapLayers()





if __name__ == '__main__':
    print('???')
    

    

    
    
    
    
    
    
    
    
    
    
    
    