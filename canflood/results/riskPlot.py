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
from model.modcom import Model


#==============================================================================
# functions-------------------
#==============================================================================
class Plotr(Model):
    
    #===========================================================================
    # parameters from control file
    #===========================================================================
    #[plotting]

    color = 'black'
    linestyle = 'dashdot'
    linewidth = 2.0
    alpha =     0.75        #0=transparent 1=opaque
    marker =    'o'
    markersize = 4.0
    fillstyle = 'none'    #marker fill style
    impactfmt_str = '.2e'
        #',.0f' #Thousands separator
    #===========================================================================
    # expectations from parameter file
    #===========================================================================
    exp_pars_md = {
        'results_fps':{
             'r2_ttl':{'ext':('.csv',)},
             }
        }
    
    exp_pars_op={
        'results_fps':{
             'r2_passet':{'ext':('.csv',)},
             }
        }
    
    #===========================================================================
    # controls
    #===========================================================================
    exp_ttl_colns = ('note', 'plot', 'aep')
    
    valid_par='risk2'  #TODO: fix this
    
    #===========================================================================
    # defaults
    #===========================================================================
    val_str='*default'
    ead_tot=''
    impact_name=''
    
    """values are dummies.. upd_impStyle will reset form attributes"""
    impStyle_d = {
            'color': 'black',
            'linestyle': 'dashdot',
            'linewidth': 2.0,
            'alpha':0.75 , # 0=transparent, 1=opaque
            'marker':'o',
            'markersize':  4.0,
            'fillstyle': 'none' #marker fill style
                            }
    

    
    
    def __init__(self,
                 cf_fp='',
                 name='Results',
                 impStyle_d=None,
                   #labels
 
                  #format controls
                  grid = True, logx = False, 
                  
                  
                  #figure parametrs
                figsize     = (6.5, 4), 
                    
                #hatch pars
                    hatch =  None,
                    h_color = 'blue',
                    h_alpha = 0.1,
                    
                    impactFmtFunc=None, #function for formatting the impact results
                        #lambda x:'{:,.0f}'.format(x)   #(thousands separator)

                 **kwargs
                 ):
        
        """inherited by the dialog.
        init is not called during the plugin"""

        

        
        super().__init__(cf_fp, **kwargs) #initilzie teh baseclass

        #=======================================================================
        # attached passed        
        #=======================================================================
        self.name = name #where are we using this?
        self.plotTag = self.tag #easier to store in methods this way
 
        self.grid    =grid
        self.logx    =logx
 
        self.figsize    =figsize
        self.hatch    =hatch
        self.h_color    =h_color
        self.h_alpha    =h_alpha
        
        """get the style handles
            setup to load from control file or passed explicitly"""
        if impStyle_d is None:
            self.upd_impStyle()
        else:
            self.impStyle_d=impStyle_d
            

        self.impactFmtFunc=impactFmtFunc
        
        self.logger.info('init finished')
        
        """call explicitly... sometimes we want lots of children who shouldnt call this
        self._init_plt()"""
        
    def _setup(self):
        """attribution has its own _setup function which will overwrite this"""
        log = self.logger.getChild('setup')
        
        
        self.init_model() #load the control file
        self._init_plt()
        
        #upldate your group plot style container
        self.upd_impStyle()
        
        #load and prep the total results
        _ = self.load_ttl(logger=log)
        _ = self.prep_ttl(logger=log)
        
        #set default plot text
        try:
            self.val_str =  'annualized impacts = %s \nltail=\'%s\',  rtail=\'%s\''%(
                self.impactFmtFunc(self.ead_tot), self.ltail, self.rtail) + \
                '\naevent_rels = \'%s\', prec = %i'%(self.event_rels, self.prec)
        except Exception as e:
            log.warning('failed to set default plot string w/ \n    %s'%e)
            
   
        
        return self
    
    def _init_plt(self,  #initilize matplotlib
                **kwargs
                  ):
        """
        calling this here so we get clean parameters each time the class is instanced
        """

        
        #=======================================================================
        # imports
        #=======================================================================
        import matplotlib
        matplotlib.use('Qt5Agg') #sets the backend (case sensitive)
        import matplotlib.pyplot as plt
        
        #set teh styles
        plt.style.use('default')
        
        #font
        matplotlib_font = {
                'family' : 'serif',
                'weight' : 'normal',
                'size'   : 8}
        
        matplotlib.rc('font', **matplotlib_font)
        matplotlib.rcParams['axes.titlesize'] = 10 #set the figure title size
        
        #spacing parameters
        matplotlib.rcParams['figure.autolayout'] = False #use tight layout
        
        self.plt, self.matplotlib = plt, matplotlib
        
        #=======================================================================
        # #value formatter
        #=======================================================================
        self._init_fmtFunc(**kwargs)

        

        
        return self
    
    def _init_fmtFunc(self,
                    impactFmtFunc=None,
                  impactfmt_str=None, #used for building impactFmtFunc (if not passed)
                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        """whatever was passed during construction.. usually None"""
        if impactFmtFunc is None: impactFmtFunc=self.impactFmtFunc
        if impactfmt_str is  None: impactfmt_str=self.impactfmt_str
        
        assert isinstance(impactfmt_str, str)
        if not callable(impactFmtFunc):
            
            impactFmtFunc = lambda x, fmt=impactfmt_str:'{:>{fmt}}'.format(x, fmt=fmt)
            
        self.impactFmtFunc=impactFmtFunc
        
        #check it
        try:
            impactFmtFunc(1.2)
        except Exception as e:
            self.logger.warning('bad formatter: %s w/ \n    %s'%(impactfmt_str, e))
        
        return
            
        
    def upd_impStyle(self): #update the plotting pars based on your attributes
        """
        taking instance variables (rather than parser's section) because these are already typset
        
        usually called twice
            1) before loading the control file, to build a default
            2) after, to update values
        """
        #assert not self.cfPars_d is None, 'load the control file first!'
        impStyle_d = dict()
        
        
        #loop through the default values
        
        for k, v in self.impStyle_d.items():
            if hasattr(self, k):
                impStyle_d[k] = getattr(self, k)
            else: #just use default
                impStyle_d[k] = v
                
        self.impStyle_d = impStyle_d
        
        
        
    def load_ttl(self,  #load a single raw ttl dataset
                 fp=None, 
                 logger=None): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('load_data')
        if fp is None: fp=self.r2_ttl
        
        #=======================================================================
        # #precheck
        #=======================================================================
        assert isinstance(fp, str)
        assert os.path.exists(fp), 'bad fp: %s'%fp
        
        #=======================================================================
        # load
        #=======================================================================
        tlRaw_df = pd.read_csv(fp, index_col=None)
        
        #=======================================================================
        # check
        #=======================================================================
        assert isinstance(tlRaw_df, pd.DataFrame)
        
        #check the column expectations
        miss_l = set(self.exp_ttl_colns).difference(tlRaw_df.columns)
        assert len(miss_l)==0

        assert 'ead' in tlRaw_df.iloc[:,0].values, 'dmg_ser missing ead entry'
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('loaded %s from %s'%(str(tlRaw_df.shape), fp))
        
        self.tlRaw_df=tlRaw_df
        
        return tlRaw_df
    
    def prep_ttl(self, # prep the raw results for plotting
                 tlRaw_df=None, #raw total results info
                 logger=None,
                 ):
        """
        when ttl is output, we add the EAD data, drop ARI, and add plotting handles
            which is not great for data manipulation
        here we clean it up and only take those for plotting
        
        see also Artr.get_ttl()
        """
        
        if tlRaw_df is None: tlRaw_df = self.tlRaw_df
        if logger is None: logger=self.logger
        log = logger.getChild('prep_ttl')
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(tlRaw_df, pd.DataFrame)
        
        #=======================================================================
        # column labling
        #=======================================================================
        """letting the user pass whatever label for the impacts
            then reverting"""
        df1 = tlRaw_df.copy()
        
        self.impact_name = list(df1.columns)[1] #get the label for the impacts
        
        newColNames = list(df1.columns)
        newColNames[1] = 'impacts'
        
        df1.columns = newColNames

        #=======================================================================
        # #get ead
        #=======================================================================
        bx = df1['aep'] == 'ead' #locate the ead row
        assert bx.sum()==1

        self.ead_tot = df1.loc[bx, 'impacts'].values[0]
        
        assert not pd.isna(self.ead_tot)
        assert isinstance(self.ead_tot, float)
        
        #=======================================================================
        # #get plot values
        #=======================================================================
        df2 = df1.loc[df1['plot'], :].copy() #drop those not flagged for plotting
        
        #typeset aeps
        df2.loc[:, 'aep'] = df2['aep'].astype(np.float64).round(self.prec)

        #=======================================================================
        # #invert aep (w/ zero handling)
        #=======================================================================
        self._get_ttl_ari(df2)

        #=======================================================================
        # re-order
        #=======================================================================
        log.info('finished w/ %s'%str(df2.shape))
        
        ttl_df = df2.loc[:, sorted(df2.columns)].sort_values('ari', ascending=True)
        self.data_d['ttl'] = ttl_df.copy()
        
        #shortcut for datachecks
        df1 = ttl_df.loc[:, ('aep', 'note')]
        df1['extrap']= df1['note']=='extrap'

        self.aep_df = df1.drop('note', axis=1)  #for checking
        
        
        return ttl_df
        
        
    def plot_riskCurve(self, #risk plot
                  res_ttl=None,
                  y1lab='AEP', #yaxis label and plot type c ontrol
                    #'impacts': impacts vs. ARI (use self.impact_name)
                    #'AEP': AEP vs. impacts 
                    
                    impactFmtFunc=None, #tick label format function for impact values
                    #lambda x:'{:,.0f}'.format(x) #thousands comma
                    
                    val_str=None, #text to write on plot. see _get_val_str()
                    figsize=None, logger=None,  plotTag=None,                
                  ):
        
        """
        summary risk results plotter
        
        This is similar to what's  on modcom.risk_plot()
        
        """
        
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_riskCurve')
        plt, matplotlib = self.plt, self.matplotlib
        if figsize is None: figsize    =    self.figsize

        if y1lab =='impacts':
            y1lab = self.impact_name
            
        if impactFmtFunc is None:
            impactFmtFunc=self.impactFmtFunc
            
        if res_ttl is None: res_ttl = self.data_d['ttl']
        if plotTag is None: plotTag=self.tag
        #=======================================================================
        # prechecks
        #=======================================================================
        assert isinstance(res_ttl, pd.DataFrame)
        miss_l = set(['aep', 'ari', 'impacts']).difference(res_ttl.columns)
        assert len(miss_l)==0, miss_l
        

        #======================================================================
        # labels
        #======================================================================
        val_str = self._get_val_str(val_str, impactFmtFunc)
        
        
        if y1lab == 'AEP':
            title = '%s %s AEP-Impacts plot for %i events'%(self.name, plotTag, len(res_ttl))
            xlab=self.impact_name
        elif y1lab == self.impact_name:
            title = '%s %s Impacts-ARI plot for %i events'%(self.name, plotTag, len(res_ttl))
            xlab='ARI'
        else:
            raise Error('bad y1lab: %s'%y1lab)
            
 
        #=======================================================================
        # figure setup
        #=======================================================================
        """
        plt.show()
        """
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
        # add the line
        #=======================================================================
        self._lineToAx(res_ttl, y1lab, ax1)
        
        #set limits
        if y1lab == 'AEP':
            ax1.set_xlim(0, max(res_ttl['impacts'])) #aep limits 
            ax1.set_ylim(0, max(res_ttl['aep'])*1.1)
        elif y1lab == self.impact_name:
            ax1.set_xlim(max(res_ttl['ari']), 1) #aep limits 
        
        #=======================================================================
        # post format
        #=======================================================================
        self._postFmt(ax1, val_str=val_str)
        
        #assign tick formatter functions
        if y1lab == 'AEP':
            xfmtFunc = impactFmtFunc
            yfmtFunc=lambda x:'%.4f'%x
        elif y1lab==self.impact_name:
            xfmtFunc = lambda x:'{:,.0f}'.format(x) #thousands separatro
            yfmtFunc=impactFmtFunc
            
        self._tickSet(ax1, xfmtFunc=xfmtFunc, yfmtFunc=yfmtFunc)
        
        return fig
    
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
            title = '%s %s AEP-Impacts plot for %i stacks'%(self.tag, plotTag, len(dxind.columns))
            xlab=self.impact_name
        elif y1lab == self.impact_name:
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
        """
        plt.show()
        """
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

        

    def _lineToAx(self, #add a line to the axis
              res_ttl,
              y1lab,
              ax,
              lineLabel=None,
              impStyle_d=None,
              hatch_f=True,
              h_color=None, h_alpha=None, hatch=None,
              ): #add a line to an axis
        
        #=======================================================================
        # defaults
        #=======================================================================
        plt, matplotlib = self.plt, self.matplotlib
        if impStyle_d is None: impStyle_d = self.impStyle_d
        
        if h_color is None: h_color=self.h_color
        if h_alpha is None: h_alpha=self.h_alpha
        if hatch is None: hatch=self.hatch
        if lineLabel is  None: lineLabel=self.tag

        """
        plt.show()
        """
        #======================================================================
        # fill the plot
        #======================================================================
        if y1lab == self.impact_name:
            xar,  yar = res_ttl['ari'].values, res_ttl['impacts'].values
            pline1 = ax.semilogx(xar,yar,
                                label       = lineLabel,
                                **impStyle_d
                                )
            #add a hatch
            if hatch_f:
                polys = ax.fill_between(xar, yar, y2=0, 
                                        color       = h_color, 
                                        alpha       = h_alpha,
                                        hatch       = hatch)
        
        elif y1lab == 'AEP':
            xar,  yar = res_ttl['impacts'].values, res_ttl['aep'].values
            pline1 = ax.plot(xar,yar,
                            label       = lineLabel,
                            **impStyle_d
                            )
                    
            if hatch_f:
                polys = ax.fill_betweenx(yar.astype(np.float), x1=xar, x2=0, 
                                    color       = h_color, 
                                    alpha       = h_alpha,
                                    hatch       = hatch)
        else:
            raise Error('bad yl1ab: %s'%y1lab)
            
        
        return ax
            
        
    def _postFmt(self, #text, grid, leend
                 ax, 

                 
                 grid=None,
                 
                 #plot text
                 val_str=None,
                 xLocScale=0.1, yLocScale=0.1,
                 
                 #legend kwargs
                 legendLoc = 1,
                 
                 legendHandles=None, 
                 legendTitle=None,
                 ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        plt, matplotlib = self.plt, self.matplotlib
        if grid is None: grid=self.grid
        
        #=======================================================================
        # Add text string 'annot' to lower left of plot
        #=======================================================================
        if isinstance(val_str, str):
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            
            x_text = xmin + (xmax - xmin)*xLocScale # 1/10 to the right of the left axis
            y_text = ymin + (ymax - ymin)*yLocScale #1/10 above the bottom axis
            anno_obj = ax.text(x_text, y_text, val_str)
        
        #=======================================================================
        # grid
        #=======================================================================
        if grid: ax.grid()
        

        #=======================================================================
        # #legend
        #=======================================================================
        if legendHandles is None:
            h1, l1 = ax.get_legend_handles_labels() #pull legend handles from axis 1
        else:
            assert isinstance(legendHandles, tuple)
            assert len(legendHandles)==2
            h1, l1 = legendHandles
        #h2, l2 = ax2.get_legend_handles_labels()
        #ax.legend(h1+h2, l1+l2, loc=2) #turn legend on with combined handles
        ax.legend(h1, l1, loc=legendLoc, title=legendTitle) #turn legend on with combined handles
        
        return ax
    
    def _tickSet(self,
                 ax,
                 xfmtFunc=None, #function that returns a formatted string for x labels
                 xlrot=0,
                 
                 yfmtFunc=None,
                 ylrot=0):
        

        #=======================================================================
        # xaxis
        #=======================================================================
        if not xfmtFunc is None:
            # build the new ticks
            l = [xfmtFunc(value) for value in ax.get_xticks()]
                  
            #apply the new labels
            ax.set_xticklabels(l, rotation=xlrot)
        
        
        #=======================================================================
        # yaxis
        #=======================================================================
        if not yfmtFunc is None:
            # build the new ticks
            l = [yfmtFunc(value) for value in ax.get_yticks()]
                  
            #apply the new labels
            ax.set_yticklabels(l, rotation=ylrot)
        
    def _get_val_str(self, #helper to get value string for writing text on the plot
                     val_str, #cant be a kwarg.. allowing None
                     impactFmtFunc=None,
                     ):
        #=======================================================================
        # defaults
        #=======================================================================
        if impactFmtFunc is None: impactFmtFunc=self.impactFmtFunc
        if val_str is None:
            val_str = self.val_str
        
        #=======================================================================
        # special keys
        #=======================================================================
        if isinstance(val_str, str):
            if val_str=='*default':
                assert isinstance(self.ead_tot, float)
                val_str='total annualized impacts = ' + impactFmtFunc(self.ead_tot)
            elif val_str=='*no':
                val_str=None
            elif val_str.startswith('*'):
                raise Error('unrecognized val_str: %s'%val_str)
                
        return val_str
    

        

    

 

    
    
       


        