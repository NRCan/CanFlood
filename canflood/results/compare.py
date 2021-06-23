'''
Created on Feb. 9, 2020

@author: cefect

Template for worker scripts
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, copy, shutil

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
        # wrap
        #=======================================================================
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
    
    def setup(self):
        """even though we only have one setup function... keeping this hear to match other workers"""
        self.init_model() #attach control file
        
        self.prep_model() 
        
        return self
    
    def prep_model(self, **kwargs):
        _ = self.load_scenarios(**kwargs)
        
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
        assert len(fps_d.values())==len(set(fps_d.values())), 'must specify unique Control filepaths'
        
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
        
        for i,(tag, fp) in enumerate(fps_d.items()):
            log.debug('loading %i/%i'%(i+1, len(fps_d)))

            # build/load the children
            sWrkr = Scenario(self, cf_fp=fp, absolute_fp=self.absolute_fp, 
                             base_dir=os.path.dirname(fp), tag=tag).setup()


            # add to family
            assert sWrkr.name not in d, 'scenario \'%s\' already loaded!...\'name\' must be unique'%sWrkr.name
    
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
                                    'ttl_df':sWrkr.data_d['r_ttl'],
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
                if len(svars_d)==0: continue #skip blank sections
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
    def build_composite(self, #merge data from a collection of asset models
                    sWrkr_d=None, #container of scenario works to plot curve comparison
                    new_wrkr=True, #whether to build a new worker
                    ):
        
        log = self.logger.getChild('build_composite')
        if sWrkr_d is None: sWrkr_d = wdict(self.sWrkr_d)
       
        #more logicla for single plots
        self.name=self.tag
        log.debug('on %i'%len(sWrkr_d))
        #=======================================================================
        # collect data
        #=======================================================================
        mdf = None
        ead_d = dict()
        for childName, sWrkr in sWrkr_d.items():
            dfi_raw = sWrkr.data_d['r_ttl'].copy()  #set by prep_ttl() 
            """
            view(dfi_raw)
            """
            dfi = dfi_raw.loc[:, 'impacts'].rename(childName).astype(float).to_frame()
            
            ead_d[childName] = sWrkr.ead_tot
            
            if mdf is None:
                #pull some from the first
                self.impact_name = sWrkr.impact_name
                self.rtail, self.ltail = sWrkr.rtail, sWrkr.ltail
                
                
                mindex = pd.MultiIndex.from_frame(
                    dfi_raw.loc[:, ['aep', 'ari', 'note', 'plot']])
                mdf = dfi
                
                
            else:
                mdf = mdf.join(dfi)
        
        
        #=======================================================================
        # build new worker
        #=======================================================================
        if new_wrkr:
            cWrkr = sWrkr.copy(name='%s_%i_composite'%(self.tag, len(sWrkr_d))) #start with a copy
            
            #===================================================================
            # convert the data to standard ttl format
            #===================================================================
            cttl_df = dfi_raw.drop(['impacts', 'ari'], axis=1).copy()
            cttl_df[self.impact_name] = mdf.sum(axis=1)
            
            #fix order
            """
            prep_ttl() is column location senstigvite
            """
            l = cttl_df.columns.to_list()
            l.remove(self.impact_name)
            l = [l[0], self.impact_name]+l[1:]
            cttl_df = cttl_df.loc[:, l]
            
            #add the ead row at the bottom
            cWrkr.data_d['r_ttl'] = cttl_df.append(pd.Series({
                'aep':'ead', 'note':'integration', 'plot':False, self.impact_name:sum(ead_d.values())
                }), ignore_index=True)
            
            
            
            
            """this function isnt set up very well.. easier to do it ourselves here
            #get just the combined impacts (drop tails)
            bx = dfi_raw['note']=='impact_sum'
            cttl_df = dfi_raw.loc[bx, 'aep'].to_frame().join(pd.Series(mdf[bx].sum(axis=1), name='impacts'))
            
            cWrkr.data_d['r_ttl'] = dfi_raw #set this for pulling handles
            cWrkr.data_d['r_ttl'], ead_tot = cWrkr.get_ttl(cttl_df, logger=log,
                                                 cols_include=['note', 'plot'])"""
            

            

        #=======================================================================
        # wrap
        #=======================================================================
        mdf.index = mindex
        """
        view(mdf)
        """
        log.info('collected %i'%len(mdf.columns))
        self.cdxind = mdf
        self.ead_d = ead_d
        self.ead_tot = sum(ead_d.values())
        
        return self.cdxind, cWrkr
    

    
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
    
    out_funcs_d = { #data tag:function that outputs it
        'r_ttl':'output_ttl'
        }

    

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
        self.parent=parent
        log.info('finished _init_')
        
#===============================================================================
#     def prep_model(self):
# 
#         
#         """note these also store on the instance"""
#         assert os.path.exists(self.r_ttl), '%s got bad \'r_ttl\': %s'%(self.name, self.r_ttl)
#         tlRaw_df = self.load_ttl()
#         ttl_df = self.prep_ttl(tlRaw_df)
#  
#         #=======================================================================
#         # wrap
#         #=======================================================================
#===============================================================================
        
        
    def copy(self,
             name = None,
             clear_data = True,):
        
        cWrkr = copy.copy(self)
        
        #clear all the data
        if clear_data:
            cWrkr.data_d = dict()
        #change the name
        if not name is None:
            cWrkr.name = name
        else:
            cWrkr.name = '%s_copy'%self.name
        
        return cWrkr
        
        
    def write(self,#store this scenario to file
              
              #filepaths
              out_dir = None,
              logger=None,
              
              ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('write')
        if out_dir is None: 
            out_dir = os.path.join(self.parent.out_dir, self.name)
            
        if not os.path.exists(out_dir):os.makedirs(out_dir)
        
        self.out_dir=out_dir #set this
        self.resname = self.name #normally set by risk models
        log.info('set out_dir to: %s'%out_dir)
        
        #=======================================================================
        #set the new control file
        #=======================================================================
        #=======================================================================
        # #duplicate
        # cf_fp = os.path.join(out_dir, 'cf_controlFile_%s.txt'%self.name)
        # shutil.copy2(self.cf_fp,cf_fp)
        #=======================================================================
        
        #open the copy
        cpars_raw = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%cpars_raw.read(self.cf_fp))
        
        #cleaqr filepath sections
        for sectName in cpars_raw.sections():
            
            if sectName.endswith('_fps'):
                log.info('clearing  section \"%s\''%sectName)
                assert cpars_raw.remove_section(sectName) #remove it
                cpars_raw.add_section(sectName) #add it back empty
                
        #write the config file 
        cf_fp = os.path.join(out_dir, 'cf_controlFile_%s.txt'%self.name)
        with open(cf_fp, 'w') as configfile:
            cpars_raw.write(configfile)
            
        self.cf_fp = cf_fp
        
        #=======================================================================
        # #add new data
        #=======================================================================
        """each of these makes a new call to set_cf_pars"""
        self.set_cf_pars({
            'parameters':({'name':self.name}, '#copy')
            })
        
        #update 
        """each of these should write using intelligent name/path/index and update the control file"""
        meta_d = dict()
        for dtag, data in self.data_d.items():
            assert dtag in self.out_funcs_d, 'missing function key on %s'%dtag
            
            #retrieve the outputter function
            assert hasattr(self, self.out_funcs_d[dtag]), self.out_funcs_d[dtag]
            f = getattr(self, self.out_funcs_d[dtag]) 
            
            #output the data using the function
            meta_d[dtag] = f(df=data, upd_cf=True, logger=log)
            
        log.info('finished on %i \n    %s'%(len(meta_d), meta_d))
        
        return meta_d
            
                



        
        
        
        
        
        
        
        
        

    
    
    

    

            
        