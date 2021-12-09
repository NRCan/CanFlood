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

from hlpr.basic import view, Error
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
    
    not using sensi.coms
    """
    def __init__(self,
                 write=True, #whether to write outputs
                inher_d = {},
                modLevel='L1',
                 **kwargs):
        
 
        
        super().__init__( 
                         **kwargs) #Qcoms -> ComWrkr
        
        #=======================================================================
        # attachments
        #=======================================================================
        """this should be the bottom of the cascade dealing w/ inheritance"""
        self.inher_d = {**inher_d, #add all thosefrom parents 
                        **{'Shared':['init_plt_d','tag', 'absolute_fp', 'overwrite',]}
                        }
        
        self.write=write
        self.modLevel=modLevel
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
              plot=True,
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
        log.info('Dmg2')
        with Dmg2(cf_fp=cf_fp, logger=log,  **initkwargs) as wrkr:
            wrkr.setup()
            
            cres_df = wrkr.run(**rkwarks_d['Dmg2'])
            
            if write:
                out_fp = wrkr.output_cdmg()
                wrkr.update_cf(out_fp=out_fp, cf_fp=cf_fp)
                
        #=======================================================================
        # run risk worker
        #=======================================================================
        log.info('Risk2')
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
                    
            if plot:
                wrkr.set_ttl(tlRaw_df = res_ttl)
                fig = wrkr.plot_riskCurve()
                try:
                    wrkr.output_fig(fig)
                except Exception as e:
                    raise Error('%s plot fail w/ \n    %s'%(self.name, e))
            
 
 
            
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
        
    res_keys = ['meta_d', 'res_lib']
    
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
               modLevel=None, #type of model being executed
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
        if modLevel is None: modLevel=self.modLevel
        log = self.logger.getChild('r')
        log.info('on %i: %s'%(len(cf_d), list(cf_d.keys())))
        start =  datetime.datetime.now()
        
        assert len(cf_d)>0, 'got empty control file suite'
        assert baseName in cf_d.keys(), 'expected baseName \'%s\' in the run cf'%baseName
        #=======================================================================
        # loop and execute
        #=======================================================================
        initKwargs = self._get_inher_atts()
        res_lib = dict()
        self.feedback.upd_prog(10)
        for i, (mtag, cf_fp) in enumerate(cf_d.items()):
            log.info('%i/%i on %s from %s'%(i+1, len(cf_d), mtag, os.path.basename(cf_fp)))
            
            
            with CandidateModel(name=mtag, logger=log.getChild(str(i)), cf_fp=cf_fp,
                                write=self.write, #sometimes we pass this to children.. sometimes no
                                out_dir = os.path.join(out_dir, mtag), 
                                **initKwargs) as cmod:
                
                f = getattr(cmod, modLevel)
                log.info('running \'%s.%s\' \n\n'%(mtag, modLevel))
                res_lib[mtag] = f(**rkwargs)
                res_lib[mtag]['cf_fp']=cf_fp
                
            #wrap
            log.debug('finished %s'%mtag)
            self.feedback.upd_prog(10+80*(i/len(cf_d)))
            

        
        #=======================================================================
        # get basic stats
        #=======================================================================
        d = {mtag:d['ead_tot'] for mtag, d in res_lib.items()}
        rser = pd.Series(d, name='ead_tot', dtype=float)
 
        
        meta_d = {      'len':len(rser), 
                         'max':round(rser.max(),2), 
                         'min':round(rser.min(), 2),
                         'mean':round(rser.mean(),2),
                         'var':round(rser.var(),2),
                         'base':round(rser[baseName],2),
                         'runTag':self.tag,
                         'runDate':self.today_str,
                         'runTime':datetime.datetime.now() - start,
                         }
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info("finished on %i in %s output to  %s \n    %s"%(
            len(res_lib), datetime.datetime.now() - start, out_dir, meta_d))
        
        self.res_lib, self.meta_d = res_lib.copy(), meta_d.copy()
        
        return res_lib, meta_d
    
    def write_pick(self, #write the results to a pickel for later
                   res_lib=None,
                   meta_d=None,
                   out_fp=None,
                   logger=None,
                   ):
        
        #======================================================================
        # defaults
        #======================================================================
        if out_fp is None: out_fp=os.path.join(self.out_dir, self.resname + '.pickle')
        if logger is None: logger=self.logger
        if res_lib is None: res_lib=self.res_lib
        if meta_d is None: meta_d = self.meta_d
        log = logger.getChild('write_pick')
        
        #=======================================================================
        # prep
        #=======================================================================
        out_d = {'res_lib':res_lib,'meta_d':meta_d}
        
        #check
        for k, sub_d in out_d.items():
            assert isinstance(sub_d, dict), k
            assert len(sub_d)>0, k
        
        #=======================================================================
        # write
        #=======================================================================
        with open(out_fp, 'wb') as f:
            # Pickle the 'data' dictionary using the highest protocol available.
            pickle.dump(out_d, f, pickle.HIGHEST_PROTOCOL)
            
        log.info('wrote %i to %s'%(len(res_lib), out_fp))
        return out_fp
    

    



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
        
    def setup(self):
        self.init_model() #attach control file

        
    def load_pick(self,
                  fp = '', #filepath to a pickle with res_lib from SensiSessRunner
                  logger=None,
                  baseName=None,
                  res_keys = None,
                  ):
                  
        #=======================================================================
        # defaults
        #=======================================================================
        if baseName is None: baseName=self.baseName
        if logger is None: logger=self.logger
        if res_keys is None: res_keys = self.res_keys
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
        
        miss_l = set(res_keys).symmetric_difference(data.keys())
        assert len(miss_l)==0, miss_l
        
        assert baseName in data['res_lib']
        
        for k in res_keys:
            d = data[k]
            assert isinstance(d, dict)
            assert len(d)>0
            setattr(self, k, d)
            log.debug('set \'%s\' as %s'%(k, type(d)))
        
        log.info('loaded w/ %i model candidates'%len(data['res_lib']))
        
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
        
        if write is None: write=self.write 
        if base_cfp is None: base_cfp=self.cf_fp
        if res_lib is None: res_lib=self.res_lib
        
        if mtags_l is None: mtags_l = list(res_lib.keys()) #just take all
        
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
                res_d[y1lab] = wrkr.riskCurves(y1lab=y1lab)
                
                #===============================================================
                # if write:
                #     res_d[y1lab] = self.output_fig(fig)
                #===============================================================
                    
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished on %i'%len(res_d))
        return res_d
    
    def analy_evalTot(self, #get analysis values for ead_tot on all the candidates
                      res_lib=None,
                      dname='ead_tot',
                      baseName=None,
                      logger=None,
                      ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if baseName is  None: baseName=self.baseName
        if logger is None: logger=self.logger
        if res_lib is None: res_lib=self.res_lib.copy()
        log=logger.getChild('analy_evalTot')
        log.info('on %i: %s'%(len(res_lib), list(res_lib.keys())))
        
        assert baseName in res_lib
        #=======================================================================
        # extract the total data
        #=======================================================================
        d = {mtag:d[dname] for mtag, d in res_lib.items()}
        res_df = pd.Series(d, name=dname, dtype=float).to_frame()
        
        bval = d[baseName] #base value for comparison
        
        #=======================================================================
        # get comparisoni stats
        #=======================================================================
        res_df['delta'] = res_df[dname] - bval
        res_df['delta_rel'] = (res_df['delta']/bval).round(3)
        
        res_df['rank'] = res_df['delta_rel'].abs().rank(
            ascending=False, #want the largest variance to have the highest rank
            method='dense', # rank always increases by 1 between groups.
            ).astype(int)
            
        log.info('finished w/ %s'%str(res_df.shape))
        
        return res_df
    
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
        
        """
        TODO: add some special mark for the base
        """
                 
        #=======================================================================
        # defaults
        #=======================================================================
        if baseName is  None: baseName=self.baseName
        if logger is None: logger=self.logger
        if res_lib is None: res_lib=self.res_lib
        if mtags_l is None: mtags_l = list(res_lib.keys()) #just take all
        if write is None: write=self.write 
        if base_cfp is None: base_cfp=self.cf_fp
        if ylab is None: ylab=self.impact_units 
        
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
        rser = pd.Series(d, name=dname, dtype=float)
        
        #=======================================================================
        # get plot
        #=======================================================================
        fig = self.plot_impact_boxes(rser.to_frame(), logger=log, ylab=ylab,
                                     title='%s \'%s\' boxplot for %i candidates'%(self.tag,  dname, len(rser)))
        
 
            
            
            
        return fig
        
            
