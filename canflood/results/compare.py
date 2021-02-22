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
#from model.modcom import Model
from results.riskPlot import RiskPlotr

#==============================================================================
# functions-------------------
#==============================================================================
class Cmpr(RiskPlotr):
 
    
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
        assert len(fps_d)>1, 'passed too few scnearios: %i'%len(fps_d)
        #=======================================================================
        # setup
        #=======================================================================
        self.init_model() #load the control file (style defaults)
        self._init_plt()
        
        
        self.upd_impStyle() #upldate your group plot style container
        self._init_fmtFunc()
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
                 base_dir=None, #base directory to add
                 ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('load_scenarios')
        if fps_d is None: fps_d = self.fps_d
        if base_dir is None: base_dir=self.base_dir
        log.info('on %i scenarios'%len(fps_d))
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert len(fps_d)>=2
        assert isinstance(fps_d, dict)
        assert len(fps_d.values())==len(set(fps_d.values())), 'non unique fps!'
        
        #=======================================================================
        # relatives
        #=======================================================================
        if not self.absolute_fp:
            fps_d = {k:os.path.join(base_dir, v) for k,v in fps_d.items()}
        
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
            sWrkr = Scenario(self, cf_fp=fp, absolute_fp=self.absolute_fp, base_dir=base_dir)


            # add to family
            assert sWrkr.name not in d, 'scenario \'%s\' already loaded!'%sWrkr.name
    
            d[sWrkr.name] = sWrkr
            
            log.debug('loaded \'%s\''%sWrkr.name)
        
        self.sWrkr_d = d
        log.info('compiled %i scenarios: %s'%(len(self.sWrkr_d), list(self.sWrkr_d.keys())))
        
        
        return wdict(self.sWrkr_d)
    
    #===========================================================================
    # comparisons--------
    #===========================================================================
        
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
        assert len(sWrkr_d)>=2
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
    
    #===========================================================================
    # aggregators
    #===========================================================================
    def collect_ttls(self,
                    sWrkr_d=None, #container of scenario works to plot curve comparison
                    ):
        
        log = self.logger.getChild('collect_ttls')
        if sWrkr_d is None: sWrkr_d = wdict(self.sWrkr_d)
       
        #more logicla for single plots
        self.name=self.tag
        
        mdf = None
        ead_d = dict()
        for childName, sWrkr in sWrkr_d.items():
            dfi_raw = sWrkr.data_d['ttl'].copy()
            dfi = dfi_raw.loc[:, 'impacts'].rename(childName).astype(float).to_frame()
            
            ead_d[childName] = sWrkr.ead_tot
            
            if mdf is None:
                self.impact_name = sWrkr.impact_name
                mindex = pd.MultiIndex.from_frame(
                    dfi_raw.loc[:, ['aep', 'ari', 'note', 'plot']])
                
                #dxcol = pd.concat([dfi.T], keys=[childName], names=['childName']).T
                mdf = dfi
                
                
            else:
                mdf = mdf.join(dfi)
                
        
        
        mdf.index = mindex
        log.info('collected %i'%len(mdf.columns))
        self.cdxind = mdf
        self.ead_d = ead_d
        self.ead_tot = sum(ead_d.values())
        return self.cdxind
    
    def plot_rCurveStk_comb(self, #plot a risk curve comparing all the scenarios
                   dxind_raw=None, #container of scenario works to plot curve comparison
                   logger=None,
                   plotTag='',
                   
                   #plot formatters
                   val_str='*no',
                   **plotKwargs
                   ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_rCurveStk_comb')
        if dxind_raw is None: dxind_raw = self.cdxind.copy()
        


        
        dxind = dxind_raw.droplevel(axis=0, level=['note', 'plot'])
        log.info('on %i'%len(dxind))
                    
        return self.plot_stackdRCurves(dxind,
                                       pd.Series(self.ead_d),
                                       val_str=val_str,plotTag=plotTag,
                                       **plotKwargs,)
        
    def plot_rCurve_comb(self, #plot a risk curve comparing all the scenarios
                   dxind_raw=None, #container of scenario works to plot curve comparison
                   logger=None,

                   
                   #plot formatters
                   val_str='*no',
                   **plotKwargs
                   ): 
        log = logger.getChild('plot_rCurve_comb')
        #promomite mindex to columns 
        df = dxind_raw.index.to_frame().join(dxind_raw.sum(axis=1).rename('impacts')
                                ).reset_index(drop=True)

        log.info('on %s'%str(df.shape))
        
        return self.plot_riskCurve(df,
                                   val_str=val_str, plotTag='',
                                     logger=log,
                                     **plotKwargs)
 
class Scenario(RiskPlotr): #simple class for a scenario
    
    name=None
    
    cfPars_d = None
    
    #plotting variables
    """
    plt.show()
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
        assert os.path.exists(self.r_ttl), '%s got bad \'r_ttl\': %s'%(self.name, self.r_ttl)
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



        
        
        
        
        
        
        
        
        

    
    
    

    

            
        