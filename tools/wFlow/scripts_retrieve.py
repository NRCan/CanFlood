'''
Created on Jan. 10, 2022

@author: cefect

separate scripts for gen3 retrival functions
'''

import inspect, logging, os,  datetime, shutil, gc, weakref

 
import pandas as pd
import numpy as np

from hlpr.Q import view


class WF_retriev(object):
    
 
    def __init__(self, 
                  bk_lib=dict(), #kwargs for builder calls {dkey:kwargs}
                 compiled_fp_d = dict(), #container for compiled (intermediate) results {dkey:filepath}
                 data_retrieve_hndls=None,

                **kwargs):
        
        
        super().__init__(**kwargs)
        
        
        #=======================================================================
        # construction handles---------
        #=======================================================================
        if data_retrieve_hndls is None:
            
            #default handles for building data sets {dkey: {'compiled':callable, 'build':callable}}
            #all callables are of the form func(**kwargs)
            #see self._retrieve2()
                
            data_retrieve_hndls = { 

                'rsamp_vlay':{
                    'compiled':lambda fp=None:self.load_vlay(fp, allow_none=False),
                    'build':lambda **kwargs:self.get_WSLsamp_vlay(**kwargs)
                    },
                'dtmsamp_vlay':{
                    'compiled':lambda fp=None:self.load_vlay(fp, allow_none=False),
                    'build':lambda **kwargs:self.get_DTMsamp_vlay(**kwargs)
                    },
                }
            
            
            
            
        self.data_retrieve_hndls=data_retrieve_hndls
        
        
        keys = self.data_retrieve_hndls.keys()
        if len(keys)>0:
            l = set(bk_lib.keys()).difference(keys)
            assert len(l)==0, 'keymismatch on bk_lib \n    %s'%l
            
            l = set(compiled_fp_d.keys()).difference(keys)
            assert len(l)==0, 'keymismatch on compiled_fp_d \n    %s'%l
            
            
                
        self.bk_lib=bk_lib
        self.compiled_fp_d = compiled_fp_d
        self.ofp_d = dict() #container for output files
    
    def _retrieve2(self, #flexible 3 source data retrival
                 dkey,
                 *args,
                 logger=None,
                 **kwargs
                 ):
        """
        WARNING: be careful with parameters that are meant to live in the control file
            in general, 'bk_lib' should be for keys used by build tools
        """
        
        if logger is None: logger=self.logger
        log = logger.getChild('_retrieve2')
        

        
        #=======================================================================
        # 1.alredy loaded
        #=======================================================================
        if dkey in self.data_d:
            return self.data_d[dkey]
        
        #=======================================================================
        # retrieve handles
        #=======================================================================
        log.info('loading %s'%dkey)
                
        assert dkey in self.data_retrieve_hndls, dkey
        
        hndl_d = self.data_retrieve_hndls[dkey]
        
        #=======================================================================
        # 2.compiled provided
        #=======================================================================
        if dkey in self.compiled_fp_d and 'compiled' in hndl_d:
            data = hndl_d['compiled'](fp=self.compiled_fp_d[dkey])
 
        #=======================================================================
        # 3.build from scratch
        #=======================================================================
        else:
            assert 'build' in hndl_d, 'no build handles for %s'%dkey
            if dkey in self.bk_lib:
                bkwargs=self.bk_lib[dkey].copy()
                bkwargs.update(kwargs) #function kwargs take precident
                kwargs = bkwargs
                """
                clearer to the user
                also gives us more control for calls within calls
                """
                
            
            
            data = hndl_d['build'](*args, dkey=dkey, **kwargs)
            
        #=======================================================================
        # store
        #=======================================================================
        self.data_d[dkey] = data
            
        log.info('finished on \'%s\' w/ %i'%(dkey, len(data)))
        
        return data
    
    
    def get_WSLsamp_vlay(self,
                     wrkr=None, #Rsamp
                  pars_d=dict(),  #hazar draster sampler
                  logger=None,
                  
                  rlay_d = None, #optional container of raster layers
                  
                  #
                  **kwargs
                  ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('get_WSLsamp_vlay')
        
 
        #=======================================================================
        # load the data
        #=======================================================================
        if rlay_d is None:
            fp = os.path.join(self.base_dir, pars_d['raster_dir'])
            rlay_d = self._retrieve('rlay_d',
                   f = lambda logger=None: wrkr.load_rlays(fp, logger=log))

        assert len(rlay_d)>0
        
        #dtm layer
        if 'dtm_fp' in pars_d:
            fp = os.path.join(self.base_dir, pars_d['dtm_fp'])
            dtm_rlay = self._retrieve('dtm_rlay',
                   f = lambda logger=None: wrkr.load_rlay(fp, logger=log))
        else:
            dtm_rlay=None
            
        #=======================================================================
        # execute
        #=======================================================================
        return self.get_rsamp_vlay(list(rlay_d.values()),
                                   wrkr=wrkr, log=log, pars_d=pars_d, dtm_rlay=dtm_rlay,
                                    **kwargs)

    def get_DTMsamp_vlay(self,
                     wrkr=None, #Rsamp
                  pars_d=dict(),  #hazar draster sampler
                  logger=None,
 
 
                  **kwargs
                  ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('get_DTMsamp_vlay')
        
        
 
        
        #=======================================================================
        # load the data
        #=======================================================================
        fp = os.path.join(self.base_dir, pars_d['dtm_fp'])
        dtm_rlay = self._retrieve('dtm_rlay',
               f = lambda logger=None: wrkr.load_rlay(fp, logger=log))
        
 
            
        #=======================================================================
        # execute
        #=======================================================================
        return self.get_rsamp_vlay([dtm_rlay],
                                   wrkr=wrkr, log=log, pars_d=pars_d,  
                                    **kwargs)
        
    def get_rsamp_vlay(self, #commons for running rsamp
                       rlay_l,
                       
                       #passtthrough
                       dkey = '',
                       wrkr=None, #Rsamp
                       #dtm_rlay=None,
                       log=None,
                       
                       #model control
                       pars_d=None, 

                       

                       #function control
                                              
                       write=None,                       
                       **kwargs):
                
        #=======================================================================
        # defaults
        #=======================================================================
        if write is  None: write=self.write
        assert dkey in ['rsamp_vlay', 'dtmsamp_vlay']
        
        
        
        
        #pull previously loaded
        finv_vlay = self.data_d['finv_vlay']
        
        
        #=======================================================================
        # collect the three kinds of kwargs
        #=======================================================================
        """
        TODO: harmonize this to at most 2 types
        """

            
        #kwargs from control file
        pkwargs = {k:pars_d[k] for k in ['dthresh', 'as_inun', 'psmp_stat'] if k in pars_d}
        
        
        #check overlap      
        l = set(pkwargs.keys()).intersection(kwargs.keys())
        assert len(l)==0, 'got some overlapping keys: %s'%l
        
        #combine
        kwargs = {**kwargs, **pkwargs}
        #=======================================================================
        # execute
        #=======================================================================
        
        res_vlay = wrkr.run(rlay_l, finv_vlay,  
                              **kwargs)
        
        wrkr.check()
        
        wrkr.rlay_inun_lib
        #=======================================================================
        # write
        #=======================================================================
        if write:
            """
            view(res_vlay)
            """
            ofp = os.path.join(self.out_dir, 'data', '%s_%s.gpkg'%(dkey, res_vlay.name()))
            self.ofp_d[dkey] = self.vlay_write(res_vlay, ofp, logger=log)
            
        
        return res_vlay
 
    
    
    def __exit__(self, #destructor
                 *args, **kwargs):
        
        print('WF_retriev.__exit__ on \'%s\''%self.__class__.__name__)
        
        #=======================================================================
        # log major containers
        #=======================================================================
        print('__exit__ w/ data_d.keys(): %s'%(list(self.data_d.keys())))
        
        if len(self.ofp_d)>0:
            print('__exit__ with %i ofp_d:'%len(self.ofp_d))
            for k,v in self.ofp_d.items():
                print('    \'%s\':r\'%s\','%(k,v))
              
              
        
        
        super().__exit__(*args, **kwargs)
    
    
    
    
    
    
    
    
    
    