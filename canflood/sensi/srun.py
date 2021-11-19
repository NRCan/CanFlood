'''
Created on Nov. 18, 2021

@author: cefect

execute a sensivitiy analysis bundle


flow
1) pass values from dialog
2) construct set of independent model packages
3) execute the group of packages
4) write summary results and display in gui


#===============================================================================
# objects
#===============================================================================
Session            handles each workflow
    workflow        a single model package
        workers    e.g., dmg2, risk2
        
because we're only using model workers, no need for fancy init handling
    except for Plotr (pass init_plt_d)
        


'''


#===============================================================================
# imports
#===============================================================================
import os, datetime
import pandas as pd

from hlpr.logr import basic_logger

from hlpr.basic import ComWrkr, view
import hlpr.plot
 



from model.risk1 import Risk1
from model.risk2 import Risk2
from model.dmg2 import Dmg2

 
class Shared(hlpr.plot.Plotr): #shared methods
    """
    we want both model and session to have some exclusive init/methods AND some shared
    """
    def __init__(self,
                 write=True, #whether to write outputs
                inher_d = {},

                 **kwargs):
        
 
        
        super().__init__( 
                         **kwargs) #Qcoms -> ComWrkr
        
        #=======================================================================
        # attachments
        #=======================================================================
        """this should be the bottom of the cascade dealing w/ inheritance"""
        self.inher_d = {**inher_d, #add all thosefrom parents 
                        **{'Shared':['init_plt_d','tag', 'absolute_fp', 'overwrite']}
                        }
        
        self.write=write
        #=======================================================================
        # checks
        #=======================================================================
                
        for className, attn_l in self.inher_d.items():
            for attn in attn_l:
                assert hasattr(self, attn), attn
        
        self.logger.debug('inher_d: %s'%self.inher_d)
        #=======================================================================
        # wrap
        #=======================================================================
        self.logger.debug('Shared__init__ finished \n')
        
                
                
    def _get_inher_atts(self, #return a container with the attribute values from your inher_d
                       inher_d=None,
                       logger=None,
                       ):
        """used by parents to retrieve kwargs to pass to children"""
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('get_inher_atts')
        if inher_d is None:
            inher_d = self.inher_d
            
        #=======================================================================
        # retrieve
        #=======================================================================
        att_d = dict()
 
        
        for className, attn_l in inher_d.items():
            d = dict()
            for attn in attn_l:
                attv = getattr(self, attn)
                #assert not attv is None, attn #allowing Nones to pass
                
                att_d[attn] = attv
                d[attn] = attv
                
            log.debug('got %i atts from \'%s\'\n    %s'%(
                len(d), className, d))
        
        return att_d
        
 
class CandidateModel(Shared):
    
 
    def __init__(self,

                inher_d = {},
                cf_fp='',
                logger=None,
                 **kwargs):
        
        
        inher_d = {**inher_d, #add all thosefrom parents 
                        **{'CandidateModel':['out_dir']}, 
                        }

        super().__init__(inher_d=inher_d,logger=logger,
                         **kwargs) #Qcoms -> ComWrkr
        
        """ComWrkr assignes by class name... but we want something more uique"""
        self.logger = logger.getChild(self.name)
        #=======================================================================
        # checks
        #=======================================================================
        assert os.path.exists(cf_fp)
        self.cf_fp=cf_fp
        
        self.logger.debug('CandidateModel.__init__ finished')

                
                
    def L1(self,
              cf_fp=None,
              logger=None,
              write=None,
              rkwarks_d = {'Risk1':{}},
              ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        if write is None: write=self.write
        if cf_fp is None: cf_fp=self.cf_fp
 
        log=logger.getChild('L1')
        start =  datetime.datetime.now()
        
        #=======================================================================
        # run worker
        #=======================================================================
        initkwargs = self._get_inher_atts()
        with Risk1(cf_fp=cf_fp, logger=log, **initkwargs) as wrkr:
            
            #run
            res_ttl, res_df = wrkr.run(**rkwarks_d['Risk1'])
            
            #collect
            eventType_df = wrkr.eventType_df
            
            #===================================================================
            # #write
            #===================================================================
            ofp = None
            if write:
                if len(res_ttl)>0: 
                    ofp = wrkr.output_ttl()
 
                    
                    
                wrkr.output_etype()
                if not res_df is None: 
                    wrkr.output_passet()
                
            
        return {
            'r_ttl':res_ttl,
            'eventypes':eventType_df,
            'r_passet':res_df,
            'tdelta':datetime.datetime.now() - start,
            'ofp':ofp
            }
        
    def L2(self,
            cf_fp=None,
            logger=None,
              write=None,
   
              rkwarks_d = {'Dmg2':{}, 'Risk2':{}},
              ):
        """combine this w/ risk1?"""
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        if write is None: write=self.write
        if cf_fp is None: cf_fp=self.cf_fp
 
        log=logger.getChild('L2')
        
        start =  datetime.datetime.now()
        log.debug('on %s'%(cf_fp))
        #=======================================================================
        # run damage worker
        #=======================================================================
        initkwargs = self._get_inher_atts()
        with Dmg2(cf_fp=cf_fp, logger=log,  **initkwargs) as wrkr:
            wrkr.setup()
            #run
            cres_df = wrkr.run(rkwarks_d['Dmg2'])
            
        
        
            if write:
                wrkr.output_cdmg()
                
        #=======================================================================
        # run risk worker
        #=======================================================================
        with Risk2(cf_fp=cf_fp, logger=log, **initkwargs) as wrkr:
            
            res_ttl, res_df = wrkr.run(rkwarks_d['Risk2'])
            
            eventType_df = wrkr.eventType_df
            
            if write:
                ofp = wrkr.output_ttl()
                wrkr.output_etype()
                if not res_df is None: 
                    wrkr.output_passet()
            
 
 
            
        return {
            'dmgs':cres_df,
            'r_ttl':res_ttl,
            'eventypes':eventType_df,
            'r_passet':res_df,
            'tdelta':datetime.datetime.now() - start
            }
        
 
class SensiRunner(Shared):
    """similar to wFlow.scripts.Session
    
    but opted not to share anything as that scrip tis way more complex"""
    
 
    def __init__(self,
                 logger=None,
                 **kwargs):
        
        if logger is None: logger = basic_logger()
        
        
        super().__init__(logger = logger,  
                         inher_d = {'SensiRunner':['write']},
                         **kwargs) #Qcoms -> ComWrkr
        
        """overwrite the ComWrkr default"""
        self.logger = logger 
        self.logger.debug('SensiRunner.__init__ finished \n')
    
    
    def build_batch_cfs(self, #build the set of model packages specified in the gui
                        df, #matrix of variables read from the diailog
                         
                      ):
        pass
    
    def rbatch(self, #run a batch of sensitivity 
               cf_d, #{mtag, controlfile}
               modelMode='L1', #type of model being executed
               rkwargs={}, #OPTIONAL model runner kwargs
               out_dir=None,
            ):
        """
        only model rountes (e.g., dmg, risk)
            all build routines should be handled by the UI
            
        run a set of control files?
        """
 
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir=self.out_dir
        log = self.logger.getChild('r')
        log.info('on %i: %s'%(len(cf_d), list(cf_d.keys())))
        
        #=======================================================================
        # loop and execute
        #=======================================================================
        initKwargs = self._get_inher_atts()
        res_lib = dict()
        for mtag, cf_fp in cf_d.items():
            log.info('on %s from %s'%(mtag, os.path.basename(cf_fp)))
            
            
            with CandidateModel(name=mtag, logger=log, cf_fp=cf_fp,
                                out_dir = os.path.join(out_dir, mtag), 
                                **initKwargs) as cmod:
                
                f = getattr(cmod, modelMode)
                
                res_lib[mtag] = f(**rkwargs)
                
            #wrap
            log.debug('finished %s'%mtag)
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.info("finished on %i")
        
        
            



