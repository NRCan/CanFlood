'''
Created on Feb. 9, 2020

@author: cefect

Template for worker scripts
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, copy

from weakref import WeakValueDictionary as wdict

#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd




from hlpr.exceptions import QError as Error
    




#===============================================================================
# non-Qgis
#===============================================================================
from hlpr.basic import view
from model.modcom import Model
from results.riskPlot import Plotr

#==============================================================================
# functions-------------------
#==============================================================================
class Cmpr(Plotr):
 
    
    #keys to expect on the sub co ntainers
    exp_pSubKeys = (
        'cf_fp', 
        )

    def __init__(self,
                 cf_fp = '',
                 fps_d = dict(), #control file paths of scenario children to load
                    #not using keys yet
                  *args, **kwargs):
        
        super().__init__(cf_fp=cf_fp, *args, **kwargs)
        
        #=======================================================================
        # attachments
        #=======================================================================
        self.fps_d = fps_d
        
        #=======================================================================
        # setup
        #=======================================================================
        self.init_model() #load the control file (style defaults)
        self._init_plt()
        
        
        self.upd_impStyle() #upldate your group plot style container
        #=======================================================================
        # wrap
        #=======================================================================
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
    
    def _setup(self):
        """even though we only have one setup function... keeping this hear to match other workers"""
        _ = self.load_scenarios()
        return self
        
    def load_scenarios(self,
                 fps_d=None, #container of filepaths 
                 
                 ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_scenarios')
        if fps_d is None: fps_d = self.fps_d
        log.info('on %i scenarios'%len(fps_d))
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(fps_d, dict)
        assert len(fps_d.values())==len(set(fps_d.values())), 'non unique fps!'
        
        for k, fp in fps_d.items():
            assert isinstance(fp, str)
            assert os.path.exists(fp), 'bad filepath: %s'%(fp)
                

            
        #=======================================================================
        # build each scenario----
        #=======================================================================
        """needs to be a strong reference or the workers die!"""
        d = dict() #start a weak reference container
        
        for i, fp in enumerate(fps_d.values()):
            log.debug('loading %i/%i'%(i+1, len(fps_d)))
            # build/load the children
            sWrkr = Scenario(self, cf_fp=fp)


            # add to family
            assert sWrkr.name not in d, 'scenario \'%s\' already loaded!'%sWrkr.name
    
            d[sWrkr.name] = sWrkr
            
            log.debug('loaded \'%s\''%sWrkr.name)
            
        self.sWrkr_d = d
        log.info('compiled %i scenarios: %s'%(len(self.sWrkr_d), list(self.sWrkr_d.keys())))
        
        
        return wdict(self.sWrkr_d)
        
    def riskCurves(self, #plot a risk curve comparing all the scenarios
                   sWrkr_d=None, #container of scenario works to plot curve comparison
                   logger=None,
                   
                   #plot keys
                   y1lab='AEP', #yaxis label and plot type c ontrol
                   
                   #plot formatters
                   val_str='*no',
                   **plotKwargs
                   ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('riskCurves')
        if sWrkr_d is None: sWrkr_d = wdict(self.sWrkr_d)
        
        #=======================================================================
        # collect data from children
        #=======================================================================
        plotPars_d = dict()
        
        #loop through each
        first = True
        for childName, sWrkr in sWrkr_d.items():
            log.debug('preping %s'%childName)
            plotPars_d[childName] = {
                                    'ttl_df':sWrkr.data_d['ttl'],
                                    'ead_tot':sWrkr.ead_tot,
                                    'impStyle_d':sWrkr.impStyle_d.copy(),
                                    }
            
            if first:
                self.impact_name = sWrkr.impact_name
                first = False


        return self.plot_mRiskCurves(plotPars_d,y1lab=y1lab, 
                                     impactFmtFunc=self.impactFmtFunc,
                                     val_str=val_str, 
                                     logger=log,
                                     **plotKwargs)
        
    def cf_compare(self, #compare control file values between Scenarios
                   sWrkr_d=None,
                   logger=None):
        
        
        if logger is None: logger=self.logger
        log = logger.getChild('cf_compare')
        if sWrkr_d is None: sWrkr_d = wdict(self.sWrkr_d)
        
        #=======================================================================
        # collect all the parameters from the children
        #=======================================================================
        first = True
        for childName, sWrkr in sWrkr_d.items():
            log.debug('extracting variables from %s'%childName)
            
            #===================================================================
            # collect values from this child
            #===================================================================
            firstC = True
            for sectName, svars_d in sWrkr.cfPars_d.items():
                
                sdf = pd.DataFrame.from_dict(svars_d, orient='index')
                sdf.columns = [childName]
                
                #collapse the field names
                sdf.index = pd.Series(np.full(len(sdf), sectName)
                                      ).str.cat(pd.Series(sdf.index), sep='.')

                if firstC:
                    cdf = sdf
                    firstC=False
                else:
                    cdf = cdf.append(sdf)
                    
            #add the control file path itself
            cdf.loc['cf_fp', childName] = sWrkr.cf_fp
            #===================================================================
            # update library
            #===================================================================
            if first:
                mdf = cdf
                first = False
            else:
                mdf = mdf.join(cdf)
                
        #=======================================================================
        # compare values
        #=======================================================================
        #determine if all values match by row
        mdf['compare'] = mdf.eq(other=mdf.iloc[:,0], axis=0).all(axis=1)
        
        log.info('finished w/ %i (of %i) parameters matching between %i scenarios'%(
            mdf['compare'].sum(), len(mdf.index), len(mdf.columns)))
        
        return mdf
                    
 
class Scenario(Plotr): #simple class for a scenario
    
    name=None
    
    cfPars_d = None
    
    #plotting variables
    """
    moved to Model
    """

    

    def __init__(self,
                 parent, #not using this yet
                 #nameRaw,
                 #cf_fp=None, #should be picked up in kwargs now
                 **kwargs              
                 ):
        
        
        super().__init__( **kwargs) #initilzie teh baseclass
        #self.logger = parent.logger.getChild(nameRaw)
        log = self.logger
        """we'll set another name from the control file
        TODO: clean this up"""
        #self.nameRaw = nameRaw 
        
        #=======================================================================
        # loaders
        #=======================================================================
        self.init_model()
        self.upd_impStyle() #update plot style dict w/ parameters from control file
        
        """note these also store on the instance"""
        tlRaw_df = self.load_ttl()
        ttl_df = self.prep_ttl(tlRaw_df)
        
        """
        view(self.data_d['ttl'])
        self.
        """
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished _init_')

        
    def xxxload_cf(self, #load the control file
                ):
        """
        this is a simplified version of whats on Model.init_model()
        
        TODO: Consider just using the full function
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_cf')
        
        cf_fp = self.cf_fp
        assert os.path.exists(cf_fp)
        #=======================================================================
        # init the config parser
        #=======================================================================
        cfParsr = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%cfParsr.read(cf_fp))
        
        
        #self.cfParsr=cfParsr
        #=======================================================================
        # check values
        #=======================================================================
        """just for information I guess....
        self.cf_chk_pars(cfParsr, copy.copy(self.exp_pars_md), optional=False)"""
        
        #=======================================================================
        # load/attach parameters
        #=======================================================================
        """this will set a 'name' property"""
        self.cfPars_d = self.cf_attach_pars(cfParsr, setAttr=True)
        assert isinstance(self.name, str)
        

        log.debug('finished w/ %i pars loaded'%len(self.cfPars_d))
        
        return
    

                
    

        
        
        
        
        
        
        
        
        

    
    
    

    

            
        