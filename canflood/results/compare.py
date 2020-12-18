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





#==============================================================================
# Logger
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
#plugin runs
else:
    #base_class = object
    from hlpr.exceptions import QError as Error
    




#===============================================================================
# non-Qgis
#===============================================================================
from hlpr.basic import ComWrkr
from model.modcom import Model
from results.riskPlot import Plotr as riskPlotr

#==============================================================================
# functions-------------------
#==============================================================================
class Cmpr(riskPlotr):
    """
    general methods to be called by the Dialog class
    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """
    
    #keys to expect on the sub co ntainers
    exp_pSubKeys = (
        'cf_fp', 
        )

    def __init__(self,

                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        

        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
        
    def load_scenarios(self,
                 parsG_d, #container of filepaths 
                 
                 ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_scenarios')
        
        log.info('on %i scenarios'%len(parsG_d))
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        for sName, parsN_d in parsG_d.items():
            assert isinstance(sName, str)
            assert isinstance(parsN_d, dict)
            
            #check all the keys match
            miss_l = set(self.exp_pSubKeys).difference(parsN_d.keys())
            assert len(miss_l)==0, 'bad keys: %s'%miss_l
            
            #check all the filepaths are good
            for pName, fp in parsN_d.items():
                assert os.path.exists(fp), 'bad filepath for \'%s.%s\': %s'%(
                    sName, pName, fp)
                
            log.debug('checked scenario \'%s\''%sName)
            
        #=======================================================================
        # build each scenario
        #=======================================================================
        """needs to be a strong reference or the workers die!"""
        self.sWrkr_d = dict() #start a weak reference container
        
        """we dont know the scenario name until its loaded"""
        self.nameConv_d = dict() #name conversion keys
        
        for sName, parsN_d in parsG_d.items():
            
            #===================================================================
            # build/load the children
            #===================================================================
            sWrkr = Scenario(self, sName)
            
             
            #load total results file
            if 'ttl_fp' in parsN_d:
                """these are riskPlot methods"""
                sWrkr.load_ttl(parsN_d['ttl_fp'])
                sWrkr.prep_dtl(logger=log)
                
                
            #load control file
            """setting this last incase we want to overwrite with control file values"""
            sWrkr.load_cf(parsN_d['cf_fp'])
            
            #populate the plotting parameters
            sWrkr.get_plot_pars() 
                
            #===================================================================
            # add to family
            #===================================================================
            assert sWrkr.name not in self.sWrkr_d, 'scenario \'%s\' already loaded!'
                
            self.sWrkr_d[sWrkr.name] = sWrkr
            self.nameConv_d[sName] = sWrkr.name
            
            log.debug('loaded \'%s\''%sWrkr.name)
            
        log.info('compiled %i scenarios: %s'%(len(self.sWrkr_d), list(self.sWrkr_d.keys())))
        
        
        return wdict(self.sWrkr_d)
        
    def riskCurves(self,
                   sWrkr_d, #container of scenario works to plot curve comparison
                   logger=None
                   ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('riskCurves')
        
        
        #=======================================================================
        # collect data from children
        #=======================================================================
        plotPars_d = dict()
        
        #loop through each
        first = True
        for childName, sWrkr in sWrkr_d.items():
            log.debug('preping %s'%childName)
            plotPars_d[childName] = {
                                    'ttl_df':sWrkr.ttl_df,
                                    'ead_tot':sWrkr.ead_tot,
                                    'impStyle_d':sWrkr.impStyle_d.copy(),

                                    }
            
            if first:
                self.y1lab = sWrkr.impact_name
                first = False
            
        
        #=======================================================================
        # plot
        #=======================================================================
        """NOTE: each child is also a riskPlotr.. but here we make a separate
        
        consider making the parent a risk plotter also?
        """

        return self.multi(plotPars_d)
        
        
         
    
    def cf_compare(self, #compare control file values between Scenarios
                   sWrkr_d,
                   logger=None):
        
        
        if logger is None: logger=self.logger
        log = logger.getChild('cf_compare')
        
        
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
                    


        
    
class Scenario(Model, riskPlotr): #simple class for a scenario
    
    name=None
    
    cfPars_d = None
    
    #plotting variables
    color = 'black'
    linestyle = 'dashdot'
    linewidth = 2.0
    alpha =     0.75        #0=transparent 1=opaque
    marker =    'o'
    markersize = 4.0
    fillstyle = 'none'    #marker fill style
    

    def __init__(self,
                 parent,
                 nameRaw,              
                 ):
        
        self.logger = parent.logger.getChild(nameRaw)
        
        """we'll set another name from the control file"""
        self.nameRaw = nameRaw 
        
        """no need to init baseclases"""
        
    def load_cf(self, #load the control file
                cf_fp):
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_cf')
        assert os.path.exists(cf_fp)
        self.cf_fp = cf_fp
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
    
    def get_plot_pars(self): #get a set of plotting handles based on your variables
        """
        taking instance variables (rather than parser's section) because these are already typset
        """
        assert not self.cfPars_d is None, 'load the control file first!'
        impStyle_d = dict()
        
        
        #loop through the default values
        
        for k, v in self.impStyle_d.items():
            if hasattr(self, k):
                impStyle_d[k] = getattr(self, k)
            else: #just use default
                impStyle_d[k] = v
                
        self.impStyle_d = impStyle_d
                
    

        
        
        
        
        
        
        
        
        

    
    
    

    

            
        