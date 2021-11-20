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
        
didn't make much use of other workers here

'''


#===============================================================================
# imports----------
#===============================================================================
import os, datetime, pickle
import pandas as pd
import numpy as np

from hlpr.logr import basic_logger

from hlpr.basic import view
import hlpr.plot


#import model.riskcom
import results.riskPlot

from model.risk1 import Risk1
from model.risk2 import Risk2
from model.dmg2 import Dmg2

from results.compare import Cmpr


#===============================================================================
# workers-------
#===============================================================================
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
            ead_tot = wrkr.ead_tot
            
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
            'ofp':ofp, 'ead_tot':ead_tot
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
            
            cres_df = wrkr.run(**rkwarks_d['Dmg2'])
            
            
            
        
            if write:
                
                out_fp = wrkr.output_cdmg()
                wrkr.update_cf(out_fp=out_fp, cf_fp=cf_fp)
                
        #=======================================================================
        # run risk worker
        #=======================================================================
        with Risk2(cf_fp=cf_fp, logger=log, **initkwargs) as wrkr:
            wrkr.setup()
            res_ttl, res_df = wrkr.run(**rkwarks_d['Risk2'])
            
            eventType_df = wrkr.eventType_df
            ead_tot = wrkr.ead_tot
            
            ofp=None
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
            'tdelta':datetime.datetime.now() - start,
            'ofp':ofp, 'ead_tot':ead_tot
            
            }
        
class SensiSessionComs(Shared):
    """similar to wFlow.scripts.Session
    
        but opted not to share anything as that scrip tis way more complex"""
        
        
    def __init__(self,
                 logger=None,
                 baseName='base',
                 name='sensi',
                 **kwargs):
        
        if logger is None: logger = basic_logger()
        
        
        super().__init__(logger = logger,  name=name,
                         inher_d = {},
                         **kwargs) #Qcoms -> ComWrkr
        
        """overwrite the ComWrkr default"""
        self.logger = logger 
        self.logger.debug('SensiRunner.__init__ finished \n')
        
        self.baseName=baseName
        
        
        self.resname = '%s_%s_%s'%(self.name, self.tag,  datetime.datetime.now().strftime('%m%d'))
    
class SensiSessRunner(SensiSessionComs): #running a sensitivity session
    
 
    def run_batch(self, #run a batch of sensitivity 
               cf_d, #{mtag, controlfile}
               modLevel='L1', #type of model being executed
               rkwargs={}, #OPTIONAL model runner kwargs
               out_dir=None,
               baseName=None, #for checks and some reeporting
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
        if baseName is None: baseName=self.baseName
        log = self.logger.getChild('r')
        log.info('on %i: %s'%(len(cf_d), list(cf_d.keys())))
        start =  datetime.datetime.now()
        
        assert baseName in cf_d.keys()
        #=======================================================================
        # loop and execute
        #=======================================================================
        initKwargs = self._get_inher_atts()
        res_lib = dict()
        for mtag, cf_fp in cf_d.items():
            log.info('on %s from %s'%(mtag, os.path.basename(cf_fp)))
            
            
            with CandidateModel(name=mtag, logger=log, cf_fp=cf_fp,
                                write=self.write, #sometimes we pass this to children.. sometimes no
                                out_dir = os.path.join(out_dir, mtag), 
                                **initKwargs) as cmod:
                
                f = getattr(cmod, modLevel)
                
                res_lib[mtag] = f(**rkwargs)
                res_lib[mtag]['cf_fp']=cf_fp
                
            #wrap
            log.debug('finished %s'%mtag)
            

        
        #=======================================================================
        # get basic stats
        #=======================================================================
        d = {mtag:d['ead_tot'] for mtag, d in res_lib.items()}
        rser = pd.Series(d, name='ead_tot', dtype=np.float32)
        
        meta_d = {'len':len(rser), 
                         'max':round(rser.max(),2), 
                         'min':round(rser.min(), 2),
                         'mean':round(rser.mean(),2),
                         'base':round(rser[baseName],2)}
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info("finished on %i in %s output to  %s \n    %s"%(
            len(res_lib), datetime.datetime.now() - start, out_dir, meta_d))
        
        return res_lib, meta_d
    
    def write_pick(self, #write the results to a pickel for later
                   res_lib,
                   out_fp=None,
                   logger=None,
                   ):
        
        #======================================================================
        # defaults
        #======================================================================
        if out_fp is None: out_fp=os.path.join(self.out_dir, self.resname + '.pickle')
        if logger is None: logger=self.logger
        log = logger.getChild('write_pick')
        
        
        with open(out_fp, 'wb') as f:
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(res_lib, f, pickle.HIGHEST_PROTOCOL)
            
        log.info('wrote %i to %s'%(len(res_lib), out_fp))
        return out_fp
    
    def analy_evalTot(self, #get analysis values for ead_tot on all the candidates
                      res_lib,
                      dname='ead_tot',
                      baseName=None,
                      logger=None,
                      ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if baseName is  None: baseName=self.baseName
        if logger is None: logger=self.logger
        log=logger.getChild('analy_evalTot')
        log.info('on %i: %s'%(len(res_lib), list(res_lib.keys())))
        
        assert baseName in res_lib
        #=======================================================================
        # extract the total data
        #=======================================================================
        d = {mtag:d[dname] for mtag, d in res_lib.items()}
        res_df = pd.Series(d, name=dname, dtype=np.float32).to_frame()
        
        bval = d[baseName] #base value for comparison
        
        #=======================================================================
        # get comparisoni stats
        #=======================================================================
        res_df['delta'] = res_df[dname] - bval
        res_df['delta_rel'] = res_df['delta']/bval
        
        res_df['rank'] = res_df['delta_rel'].abs().rank(
            ascending=False, #want the largest variance to have the highest rank
            method='dense', # rank always increases by 1 between groups.
            ).astype(np.int)
            
        log.info('finished w/ %s'%str(res_df.shape))
        
        return res_df
    



class SensiSessResults( #analyzing results of a sensi session
        SensiSessionComs, results.riskPlot.RiskPlotr):
    
    #===========================================================================
    # #expectations from parameter file
    #===========================================================================
    #control file expectation handles: MANDATORY
    #{section : {variable {check handle type: check values}
    exp_pars_md = {
        'parameters' :
            {
             'name':        {'type':str},
             
             },
            

                }
    
    exp_pars_op = {#optional expectations
        'parameters':{
            'impact_units': {'type':str}
            },
        'risk_fps':{
            'exlikes':{'ext':('.csv',)},
                    },
        
        'results_fps':{
             'attrimat02':{'ext':('.csv',)},
                    }
                }
    
    
    def __init__(self,
                 cf_fp=None, #base control file for configuring plots
                 **kwargs):
        
 
        super().__init__( cf_fp=cf_fp,
                         **kwargs) #Qcoms -> ComWrkr
        
        self.setup()

        
    def load_pick(self,
                  fp = '', #filepath to a pickle with res_lib from SensiSessRunner
                  logger=None,
                  baseName=None,
                  ):
                  
        #=======================================================================
        # defaults
        #=======================================================================
        if baseName is None: baseName=self.baseName
        if logger is None: logger=self.logger
        log = logger.getChild('load_pick')
        
        
        assert os.path.exists(fp), fp
        
        
        log.info('from %s w/ %.2f kb'%(fp, os.stat(fp).st_size/1024))
        
        #=======================================================================
        # load
        #=======================================================================
        
        with open(fp, 'rb') as f:
            data = pickle.load(f)
            
        #=======================================================================
        # checks
        #=======================================================================
        assert isinstance(data, dict)
        assert len(data)>0
        assert baseName in data
        
        log.info('loaded w/ %i model candidates'%len(data))
        
        return data
                  
    
    
    def plot_riskCurves(self, #plot all the selected risk curves (on a single axis)
                        
                        #data and controls
                         mtags_l = None, #list of candidates to include in the plot
                         res_lib = None, 
                         
                        #plot control
                        y1labs = ['impacts', 'AEP'], #what types of plot to generate
                        base_cfp = None, #control file for plot defaults
                   
                    #generic
                    write=None,
                      baseName=None,
                      logger=None,
                      ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if baseName is  None: baseName=self.baseName
        if logger is None: logger=self.logger
        if mtags_l is None: mtags_l = list(res_lib.keys()) #just take all
        if write is None: write=self.write 
        if base_cfp is None: base_cfp=self.cf_fp
        
        log=logger.getChild('plot_riskCurves')
        log.info('on %i: %s'%(len(mtags_l), mtags_l))
        
        #=======================================================================
        # check keys
        #=======================================================================
        assert baseName in mtags_l
        
        miss_l = set(mtags_l).difference(res_lib.keys())
        assert len(miss_l)==0, miss_l
        
        #=======================================================================
        # get filepaths
        #=======================================================================
        fps_d = {mtag:d['cf_fp'] for mtag, d in res_lib.items()}
        
        
        #=======================================================================
        # build curves
        #=======================================================================
        res_d = dict()
        initKwargs = self._get_inher_atts()
        with Cmpr(fps_d = fps_d, cf_fp=base_cfp, logger=self.logger, **initKwargs) as wrkr:
            wrkr.setup() #loads a scenario from each control file
            
            for y1lab in y1labs:
                fig = wrkr.riskCurves(y1lab=y1lab)
                
                if write:
                    res_d[y1lab] = self.output_fig(fig)
                    
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished on %i'%len(res_d))
        return res_d
    
    def plot_box(self,
                 #data and controls
                 mtags_l = None, #list of candidates to include in the plot
                 res_lib = None, 
                 dname='ead_tot',
                 #plot control
                 base_cfp = None, #control file for plot defaults
                 ylab=None,
                 
                 #generic
                    write=None,
                      baseName=None,
                      logger=None,
                      ):
                 
        #=======================================================================
        # defaults
        #=======================================================================
        if baseName is  None: baseName=self.baseName
        if logger is None: logger=self.logger
        if mtags_l is None: mtags_l = list(res_lib.keys()) #just take all
        if write is None: write=self.write 
        if base_cfp is None: base_cfp=self.cf_fp
        if ylab is None: ylab=self.impact_name
        
        log=logger.getChild('plot_box')
        log.info('on %i: %s'%(len(mtags_l), mtags_l))
        
        #=======================================================================
        # check keys
        #=======================================================================
        assert baseName in mtags_l
        
        miss_l = set(mtags_l).difference(res_lib.keys())
        assert len(miss_l)==0, miss_l
        
        #=======================================================================
        # get data
        #=======================================================================
        
        
        d = {mtag:d[dname] for mtag, d in res_lib.items()}
        rser = pd.Series(d, name=dname, dtype=np.float32)
        
        #=======================================================================
        # get plot
        #=======================================================================
        fig = self.plot_impact_boxes(rser.to_frame(), logger=log, ylab=ylab,
                                     title='%s %i candidate \'%s\' boxplot'%(self.tag, len(rser), dname))
        
        #=======================================================================
        # output
        #=======================================================================
        if write:
            ofp = self.output_fig(fig)
            
            
            
        return ofp
        
            
