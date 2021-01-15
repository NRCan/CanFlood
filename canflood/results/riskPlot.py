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

from hlpr.basic import ComWrkr, view


#==============================================================================
# functions-------------------
#==============================================================================
class Plotr(ComWrkr):

    #===========================================================================
    # controls
    #===========================================================================
    exp_ttl_colns = ('note', 'plot', 'aep')
    
    #===========================================================================
    # defaults
    #===========================================================================
    val_str='*defalut'
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

        

        
        super().__init__(**kwargs) #initilzie teh baseclass

        #=======================================================================
        # attached passed        
        #=======================================================================
        self.name = name
 
        self.grid    =grid
        self.logx    =logx
 
        self.figsize    =figsize
        self.hatch    =hatch
        self.h_color    =h_color
        self.h_alpha    =h_alpha
        
        if impStyle_d is None:
            self.upd_impStyle()
        else:
            self.impStyle_d=impStyle_d
            
        if impactFmtFunc is None:
            impactFmtFunc = lambda x:'%.2e'%x #default to scientific notation
        self.impactFmtFunc=impactFmtFunc
        
        self.logger.info('init finished')
        
        """call explicitly... sometimes we want lots of children who shouldnt call this
        self._init_plt()"""
        
        
    def _init_plt(self): #initilize matplotlib
        """
        calling this here so we get clean parameters each time the class is instanced
        """
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
        return self
        
    def upd_impStyle(self): #update the plotting pars based on your attributes
        """
        taking instance variables (rather than parser's section) because these are already typset
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
        assert os.path.exists(fp)
        
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
    
    def prep_dtl(self, # prep the raw results for plotting
                 tlRaw_df=None, #raw total results info
                 logger=None,
                 ):
        """
        when ttl is output, we add the EAD data, drop ARI, and add plotting handles
            which is not great for data manipulation
        here we clean it up and only take those for plotting
        """
        
        if tlRaw_df is None: tlRaw_df = self.tlRaw_df
        if logger is None: logger=self.logger
        log = logger.getChild('prep_dtl')
        
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
        
        #=======================================================================
        # #get plot values
        #=======================================================================
        df2 = df1.loc[df1['plot'], :].copy()
        
        #typeset aeps
        df2.loc[:, 'aep'] = df2['aep'].astype(np.float64).round(self.prec)
        """
        df2.dtypes
        """

        #=======================================================================
        # #invert aep (w/ zero handling)
        #=======================================================================
        ar = df2.loc[:,'aep'].T.values
        
        ar_ari = 1/np.where(ar==0, #replaced based on zero value
                           sorted(ar)[1]/10, #dummy value for zero (take the second smallest value and divide by 10)
                           ar) 
        
        df2['ari'] = ar_ari.astype(np.int32)
        
        #=======================================================================
        # re-order
        #=======================================================================
        log.info('finished w/ %s'%str(df2.shape))
        
        ttl_df = df2.loc[:, sorted(df2.columns)].sort_values('ari', ascending=True)
        self.data_d['ttl'] = ttl_df.copy()
        
        #shortcut for datachecks
        df1 = ttl_df.loc[:, ('aep', 'note')]
        df1['extrap']= df1['note']=='extrap'
        """
        df1.dtypes
        
        #non-extraploated events
        self.aep_df.loc[~self.aep_df['extrap'], 'aep']
        """
        self.aep_df = df1.drop('note', axis=1)  #for checking
        
        
        return ttl_df
        
        
    def plot_riskCurve(self, #risk plot
                  res_ttl,
                  y1lab='AEP', #yaxis label and plot type c ontrol
                    #'impacts': impacts vs. ARI (use self.impact_name)
                    #'AEP': AEP vs. impacts 
                    
                    impactFmtFunc=None, #tick label format function for impact values
                    #lambda x:'{:,.0f}'.format(x) #thousands comma
                    
                    val_str=None, #text to write on plot. see _get_val_str()
                    figsize=None, logger=None,                  
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
            title = '%s AEP-Impacts plot for %i events'%(self.tag, len(res_ttl))
            xlab=self.impact_name
        elif y1lab == self.impact_name:
            title = '%s Impacts-ARI plot for %i events'%(self.tag, len(res_ttl))
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
                    
                    val_str=None, #text to write on plot. see _get_val_str()

                  figsize=None, logger=None,
                  ):
        

        
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
        
        
        
        #=======================================================================
        # pre-data manip: collect all the impacts ari data into one
        #=======================================================================
        """makes it easier for some operations
        still plot on each individually"""

        first = True
        for cName, cPars_d in parsG_d.items():
            #check keys
            miss_l = set(['ttl_df', 'ead_tot', 'impStyle_d']).difference(cPars_d.keys())
            assert len(miss_l)==0, '\'%s\' missing keys: %s'%(cName, miss_l)
            
            #check data
            cdf = cPars_d['ttl_df'].copy()
            
            #check columns
            miss_l = set(['aep', 'impacts', 'ari', 'plot']).difference(cdf.columns)
            assert len(miss_l)==0, '%s missing columns: %s'%(cName, miss_l)
            
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
            title = '%s AEP-Impacts plot for %i scenarios'%(self.tag, len(parsG_d))
            xlab=self.impact_name
        elif y1lab == self.impact_name:
            title = '%s Impacts-ARI plot for %i scenarios'%(self.tag, len(parsG_d))
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
        #ax2 = ax1.twinx()
        
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_ylabel(y1lab)
        #ax2.set_ylabel(y2lab)
        ax1.set_xlabel(xlab)
        

        
        #======================================================================
        # fill the plot----
        #======================================================================
        first = True
        for cName, cPars_d in parsG_d.items():
            
            
            #pull values from container
            cdf = cPars_d['ttl_df'].copy()
            cdf = cdf.loc[cdf['plot'], :] #drop from handles
            ead_tot = cPars_d['ead_tot']
            
            #defaults
            if 'hatch_f' in cPars_d:
                hatch_f=cPars_d['hatch_f']
            else:
                hatch_f=False
            
            #add the line
            self._lineToAx(cdf, y1lab, ax1, impStyle_d=cPars_d['impStyle_d'],
                           hatch_f=hatch_f, lineLabel=cName)
            


            #build labels
            val_str = '%s = '%cName + impactFmtFunc(ead_tot)
            
            if first:
                vMaster_str = val_str
                first = False
            else:
                vMaster_str= '%s\n%s'%(vMaster_str, val_str)

        #set limits
        if  y1lab==self.impact_name:
            ax1.set_xlim(max(all_df.index.get_level_values('ari')), 1) #ARI x-axis limits
        else:
            ax1.set_xlim(0, all_df.max().max())
            ax1.set_ylim(0, max(all_df.index.get_level_values('aep'))*1.1)
            
        #=======================================================================
        # post format
        #=======================================================================
        self._postFmt(ax1, val_str=vMaster_str)
        
        #assign tick formatter functions
        if y1lab == 'AEP':
            xfmtFunc = impactFmtFunc
            yfmtFunc=lambda x:'%.4f'%x
        elif y1lab==self.impact_name:
            xfmtFunc = lambda x:'{:,.0f}'.format(x) #thousands separatro
            yfmtFunc=impactFmtFunc
            
        self._tickSet(ax1, xfmtFunc=xfmtFunc, yfmtFunc=yfmtFunc)
        
        return fig
    
    def plot_stackdRCurves(self,
                   dxind,
                   y1lab='AEP',
                   figsize=None, impactFmtFunc=None, val_str=None,
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
        
        #=======================================================================
        # prechecks
        #=======================================================================
        #expectations on stacked data
        mindex=dxind.index
        assert isinstance(mindex, pd.MultiIndex)
        assert np.array_equal(np.array(['aeps', 'ari']), mindex.names)
        

        nameRank_d= {lvlName:i for i, lvlName in enumerate(mindex.names)}
        
        #======================================================================
        # labels
        #======================================================================
        #val_str = self._get_val_str(val_str, impactFmtFunc)
         
         
        if y1lab == 'AEP':
            title = '%s AEP-Impacts plot for %i stacks'%(self.tag, len(dxind.columns))
            xlab=self.impact_name
        elif y1lab == self.impact_name:
            title = '%s Impacts-ARI plot for %i stacks'%(self.tag, len(dxind.columns))
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
        # plot line
        #=======================================================================
        if y1lab == 'AEP':
            """I dont see any native support for x axis stacks"""
            
            yar = mindex.levels[nameRank_d['eads']].values #ARI values 
            for colName, cser in dxind.items():
                ax1.fill_betweenx()
                print(colName)

        
        
        
        elif y1lab == self.impact_name:
            
            #ARI values  (ascending?)
            xar = np.sort(mindex.levels[nameRank_d['ari']].values)
            #transpose, and ensure sorted
            yar = dxind.T.sort_index(axis=1, level='ari', ascending=True).values
            
            #plot the stack
            ax1.stackplot(xar, yar, baseline='zero', labels=dxind.columns,
                          alpha=0.9)
            ax1.set_xscale('log')
            
            """
            view(dxind)
            ax1.legend()
            """
        #set limits
        if y1lab == 'AEP':
            ax1.set_xlim(0, max(res_ttl['impacts'])) #aep limits 
            ax1.set_ylim(0, max(res_ttl['aep'])*1.1)
        elif y1lab == self.impact_name:
            ax1.set_xlim(max(xar), 1) #ari limits
        
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

                 val_str=None,
                 grid=None,
                 legendLoc = 1,
                 xLocScale=0.1, yLocScale=0.1,
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
        h1, l1 = ax.get_legend_handles_labels() #pull legend handles from axis 1
        #h2, l2 = ax2.get_legend_handles_labels()
        #ax.legend(h1+h2, l1+l2, loc=2) #turn legend on with combined handles
        ax.legend(h1, l1, loc=legendLoc) #turn legend on with combined handles
        
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
                     val_str,impactFmtFunc
                     ):
        
        if val_str is None:
            val_str = self.val_str
        
        if isinstance(val_str, str):
            if val_str=='*defalut':
                val_str='annualized impacts = ' + impactFmtFunc(self.ead_tot)
            elif val_str=='*no':
                val_str=None
                
        return val_str
        

    

 

    
    
       


        