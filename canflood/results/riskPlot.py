'''
Created on Feb. 9, 2020

@author: cefect

plotting risk curve from results
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd




#==============================================================================
# # custom
#==============================================================================

from hlpr.exceptions import QError as Error

from hlpr.basic import view
from model.riskcom import RiskModel
#from hlpr.plot import Plotr

#==============================================================================
# functions-------------------
#==============================================================================
class RiskPlotr(RiskModel): #expanded plotting for risk models
    """
    inherited by 
        results.compare.Cmpr
        results.attribution.Attr
    """

    #===========================================================================
    # expectations from parameter file
    #===========================================================================
    exp_pars_md = {
        'results_fps':{
             'r_ttl':{'ext':('.csv',)},
             }
        }
    
    exp_pars_op={
        'results_fps':{
             'r_passet':{'ext':('.csv',)},
             }
        }
    
    #===========================================================================
    # controls
    #===========================================================================

    
    #===========================================================================
    # defaults
    #===========================================================================

    def __init__(self,**kwargs):
 
 
        super().__init__(**kwargs) #initilzie teh baseclass
        
        self.dtag_d={**self.dtag_d,**{
            'r_ttl':{'index_col':None}}}
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))

        
    def prep_model(self):

        
        self.set_ttl() #load and prep the total results
        
        #set default plot text
        self._set_valstr()
        
        return 

    def plot_mRiskCurves(self, #single plot w/ risk curves from multiple scenarios
       
                  parsG_d, #container of data and plot handles
                    #{cName:{
                            #ttl_df:df to plot
                            #ead_tot:total ead value (for label)
                            #impStyle_d: kwargs for semilogx
                            
                  y1lab='AEP', #yaxis label and plot type c ontrol
                    #'impacts': impacts vs. ARI (use self.impact_name)
                    #'AEP': AEP vs. impacts 
                    
                    impactFmtFunc=None, #tick label format function for impact values
                    #lambda x:'{:,.0f}'.format(x)
                    
                    legendTitle=None,
                    val_str='*no', #text to write on plot. see _get_val_str()
 


                  figsize=None, logger=None, plotTag=None,
                  ):
        
        """
        called by
            Attr.plot_slice() #a data slice against the total
            Cmpr.riskCurves() #a set of totals (scenarios)
        """
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('multi')
        plt, matplotlib = self.plt, self.matplotlib
        
        if figsize is None: figsize=self.figsize
        
        if y1lab =='impacts':
            y1lab = self.impact_name
            
        if impactFmtFunc is None:
            impactFmtFunc=self.impactFmtFunc
        assert callable(impactFmtFunc)
        if plotTag is None: plotTag=self.tag
        
        
        #=======================================================================
        # pre-data manip: collect all the impacts ari data into one
        #=======================================================================
        """makes it easier for some operations
        still plot on each individually"""

        first = True
        for cName, cPars_d in parsG_d.items():
            #check keys
            miss_l = set(['ttl_df', 'impStyle_d']).difference(cPars_d.keys())
            assert len(miss_l)==0, '\'%s\' missing keys: %s'%(cName, miss_l)
            
            #check data
            cdf = cPars_d['ttl_df'].copy()
            
            #check columns
            miss_l = set(['aep', 'impacts', 'ari', 'plot']).difference(cdf.columns)
            assert len(miss_l)==0, '\'%s\' missing columns: %s'%(cName, miss_l)
            
            #drop to just the data (and rename)
            cdf = cdf.loc[cdf['plot'],:].loc[:,('ari','impacts')].rename(columns={'impacts':cName})

            #get index columns from first
            if first:
                all_df = cdf.copy()
                first = False
            else:
                #add data
                all_df = all_df.merge(cdf, how='outer', on='ari')

        #add back in aep
        all_df['aep'] = 1/all_df['ari']
        
        #move these to the index for quicker operations
        all_df = all_df.set_index(['aep', 'ari'], drop=True)
        

        #======================================================================
        # labels
        #======================================================================
        if y1lab == 'AEP':
            title = '%s AEP-Impacts plot for %i scenarios'%(plotTag, len(parsG_d))
            xlab=self.impact_name
        elif y1lab == self.impact_name:
            title = '%s Impacts-ARI plot for %i scenarios'%(plotTag, len(parsG_d))
            xlab='ARI'
        else:
            raise Error('bad y1lab: %s'%y1lab)
        
        #======================================================================
        # figure setup
        #======================================================================
        """
        plt.show()
        """
        plt.close()
        fig = plt.figure(figsize=figsize, constrained_layout = True)
        
        #axis setup
        ax1 = fig.add_subplot(111)

        # axis label setup
        fig.suptitle(title)
        ax1.set_ylabel(y1lab)
        #ax2.set_ylabel(y2lab)
        ax1.set_xlabel(xlab)
        

        
        #======================================================================
        # fill the plot----
        #======================================================================
        first = True
        #ead_d=dict()
        for cName, cPars_d in parsG_d.items():
            
            #pull values from container
            cdf = cPars_d['ttl_df'].copy()
            cdf = cdf.loc[cdf['plot'], :] #drop from handles
            
            #hatching
            if 'hatch_f' in cPars_d:
                hatch_f=cPars_d['hatch_f']
            else:
                hatch_f=False
                
            #labels
            if 'label' in cPars_d:
                label = cPars_d['label']
            else:
                if 'ead_tot' in cPars_d:
                    label = '\'%s\' annualized = '%cName + impactFmtFunc(float(cPars_d['ead_tot']))
                else:
                    label = cName
                
            
            #add the line
            self._lineToAx(cdf, y1lab, ax1, impStyle_d=cPars_d['impStyle_d'],
                           hatch_f=hatch_f, lineLabel=label)
            
            #ead_d[label] = float(cPars_d['ead_tot']) #add this for constructing the 



        #set limits
        if  y1lab==self.impact_name:
            ax1.set_xlim(max(all_df.index.get_level_values('ari')), 1) #ARI x-axis limits
        else:
            ax1.set_xlim(0, all_df.max().max())
            ax1.set_ylim(0, max(all_df.index.get_level_values('aep'))*1.1)
            
        #=======================================================================
        # post format
        #=======================================================================
        
        #legend
        h1, l1 = ax1.get_legend_handles_labels()
        #legLab_d = {e:'\'%s\' annualized = '%e + impactFmtFunc(ead_d[e]) for e in l1}
        val_str = self._get_val_str(val_str)
        #legendTitle = self._get_val_str('*default')
        
        self._postFmt(ax1, 
                      val_str=val_str, #putting in legend ittle 
                      legendHandles=(h1, l1),
                      #xLocScale=0.8, yLocScale=0.1,
                      legendTitle=legendTitle,
                      )
        
        
        #=======================================================================
        # val_str = self._get_val_str(val_str, impactFmtFunc)
        # self._postFmt(ax1, val_str=val_str)
        #=======================================================================
        
        #assign tick formatter functions
        if y1lab == 'AEP':
            xfmtFunc = impactFmtFunc
            yfmtFunc=lambda x:'%.4f'%x
        elif y1lab==self.impact_name:
            xfmtFunc = lambda x:'{:,.0f}'.format(x) #thousands separatro
            yfmtFunc=impactFmtFunc
            
        self._tickSet(ax1, xfmtFunc=xfmtFunc, yfmtFunc=yfmtFunc)
        
        return fig
    
    def plot_stackdRCurves(self, #single plot with stacks of risk components for single scenario
                   dxind, #mindex(aep, ari), columns: one stack or component
                   sEAD_ser, #series with EAD data for labels
                   y1lab='AEP',
                   
                   #hatch format
                   h_alpha = 0.9,
                   
                   #figure config
                   title=None, #None: generate from data
                   figsize=None, impactFmtFunc=None, plotTag=None,
                   val_str=None,
                   logger=None,):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_stack')
        

        plt, matplotlib = self.plt, self.matplotlib
        
        if figsize is None: figsize=self.figsize
        
        if y1lab =='impacts':
            y1lab = self.impact_name
            
        if impactFmtFunc is None:
            impactFmtFunc=self.impactFmtFunc
            
        if h_alpha is None: h_alpha=self.h_alpha
        if plotTag is None: plotTag=self.plotTag
        
        if val_str is None:
            val_str =  'ltail=\'%s\',  rtail=\'%s\''%(self.ltail, self.rtail) + \
                        '\naevent_rels = \'%s\', prec = %i'%(self.event_rels, self.prec)
                        
 
        #=======================================================================
        # prechecks
        #=======================================================================
        #expectations on stacked data
        mindex=dxind.index
        assert isinstance(mindex, pd.MultiIndex)
        assert np.array_equal(np.array(['aep', 'ari']), mindex.names)
        

        nameRank_d= {lvlName:i for i, lvlName in enumerate(mindex.names)}
        
        if isinstance(sEAD_ser, pd.Series):
            miss_l = set(sEAD_ser.index).symmetric_difference(dxind.columns)
            assert len(miss_l)==0, 'mismatch on plot group names'
        
        #======================================================================
        # labels
        #======================================================================
        val_str = self._get_val_str(val_str, impactFmtFunc)
         
         
        if y1lab == 'AEP':
            if title is None:
                title = '%s %s AEP-Impacts plot for %i stacks'%(self.tag, plotTag, len(dxind.columns))
            xlab=self.impact_name
        elif y1lab == self.impact_name:
            if title is None:
                title = '%s %s Impacts-ARI plot for %i stacks'%(self.tag, plotTag, len(dxind.columns))
            xlab='ARI'
        else:
            raise Error('bad y1lab: %s'%y1lab)
            
        #=======================================================================
        # data prep
        #=======================================================================
        dxind = dxind.sort_index(axis=0, level=0)
        mindex = dxind.index
        #=======================================================================
        # figure setup
        #=======================================================================
        plt.close()
        fig = plt.figure(figsize=figsize, constrained_layout = True)
        
        #axis setup
        ax1 = fig.add_subplot(111)
        #ax2 = ax1.twinx()
        
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_ylabel(y1lab)

        ax1.set_xlabel(xlab)
 
        #=======================================================================
        # plot line
        #=======================================================================

        if y1lab == 'AEP':
            """I dont see any native support for x axis stacks"""
            
            yar = mindex.levels[nameRank_d['aep']].values
            assert len(yar)==len(mindex), 'check the mindex doesnt have phantom labels'
            xCum_ar = 0
            for colName, cser in dxind.items():
                ax1.fill_betweenx(yar, xCum_ar, xCum_ar+cser.values, label=colName, 
                                  lw=0, alpha=h_alpha)
                xCum_ar +=cser.values

        elif y1lab == self.impact_name:
            
            #ARI values  (ascending?)
            xar = np.sort(mindex.levels[nameRank_d['ari']].values)
            #transpose, and ensure sorted
            yar = dxind.T.sort_index(axis=1, level='ari', ascending=True).values
            
            #plot the stack
            ax1.stackplot(xar, yar, baseline='zero', labels=dxind.columns,
                          alpha=h_alpha, lw=0)
            
            ax1.set_xscale('log')
            
        #set limits
        if y1lab == 'AEP':
            ax1.set_xlim(0, max(xCum_ar)) #aep limits 
            ax1.set_ylim(0, max(yar)*1.1)
        elif y1lab == self.impact_name:
            ax1.set_xlim(max(xar), 1) #ari limits
        
        #=======================================================================
        # post format
        #=======================================================================
        #legend
        h1, l1 = ax1.get_legend_handles_labels()
        legLab_d = {e:'\'%s\' annualized = '%e + impactFmtFunc(sEAD_ser[e]) for e in l1}
        legendTitle = self._get_val_str('*default')
        
        self._postFmt(ax1, 
                      val_str=val_str, #putting in legend ittle 
                      legendHandles=(h1, list(legLab_d.values())),
                      #xLocScale=0.8, yLocScale=0.1,
                      legendTitle=legendTitle)
        
        #assign tick formatter functions
        if y1lab == 'AEP':
            xfmtFunc = impactFmtFunc
            yfmtFunc=lambda x:'%.4f'%x
        elif y1lab==self.impact_name:
            xfmtFunc = lambda x:'{:,.0f}'.format(x) #thousands separatro
            yfmtFunc=impactFmtFunc
            
        self._tickSet(ax1, xfmtFunc=xfmtFunc, yfmtFunc=yfmtFunc)
        
        return fig
    
    def _set_valstr(self): 
        """"
        similar to whats on modcom.RiskModel
            but removing some attributes set during run loops
        """
        
        #plotting string
        self.val_str =  'annualized impacts = %s %s \nltail=\'%s\' \nrtail=\'%s\''%(
            self.impactFmtFunc(self.ead_tot), self.impact_units, self.ltail, self.rtail) +\
            '\nnevent_rels = \'%s\'\nprec = %i\ndate=%s'%(
                self.event_rels, self.prec, self.today_str)



       


        