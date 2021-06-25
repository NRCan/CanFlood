'''
Created on Feb. 15, 2021

@author: cefect
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
from hlpr.basic import ComWrkr, view


class Plotr(ComWrkr):
    
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
        
    impactFmtFunc = None
    
    #===========================================================================
    # controls
    #===========================================================================
    set_cnt_max = 10 #maximum number of datasets to allow on a plot
    
    #===========================================================================
    # defaults
    #===========================================================================
    val_str='*default'
        
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


                 impStyle_d=None,
                 
                 #init controls
                 init_plt_d = {}, #container of initilzied objects
 
                  #format controls
                  grid = True, logx = False, 
                  
                  
                  #figure parametrs
                figsize     = (6.5, 4), 
                    
                #hatch pars
                    hatch =  None,
                    h_color = 'blue',
                    h_alpha = 0.1,
                    
                    impactFmtFunc=None, #function for formatting the impact results
                        
                        #Option1: pass a raw function here
                        #Option2: pass function to init_fmtFunc
                        #Option3: use 'impactfmt_str' kwarg to have init_fmtFunc build
                            #default for 'Model' classes (see init_model)


                 **kwargs
                 ):
        


        
        super().__init__( **kwargs) #initilzie teh baseclass

        #=======================================================================
        # attached passed        
        #=======================================================================

        self.plotTag = self.tag #easier to store in methods this way
 
        self.grid    =grid
        self.logx    =logx
 
        self.figsize    =figsize
        self.hatch    =hatch
        self.h_color    =h_color
        self.h_alpha    =h_alpha
        
        #init matplotlib
        if len(init_plt_d)==0:
            self.init_plt_d = self._init_plt() #setup matplotlib
        else:
            for k,v in init_plt_d.items():
                setattr(self, k, v)
                
            self.init_plt_d = init_plt_d
        
        #impact formatting

        self._init_fmtFunc(impactFmtFunc=impactFmtFunc)

        
        """get the style handles
            setup to load from control file or passed explicitly"""
        if impStyle_d is None:
            self.upd_impStyle()
        else:
            self.impStyle_d=impStyle_d
            

        
        
        self.logger.debug('init finished')
        
        """call explicitly... sometimes we want lots of children who shouldnt call this
        self._init_plt()"""
        

    
    def _init_plt(self,  #initilize matplotlib
                #**kwargs
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
        
        #legends
        matplotlib.rcParams['legend.title_fontsize'] = 'large'
        
        self.plt, self.matplotlib = plt, matplotlib
        

        return {'plt':plt, 'matplotlib':matplotlib}
    
    def _init_fmtFunc(self, #setup impact formatting from two options
                    impactFmtFunc=None, #raw function
                  impactfmt_str=None, #ALTERNATIVE: python formatting string for building function
                  ):
        """
        called during init with a callable
        generally overwritten by init_model() (with impactfmt_str)
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        """whatever was passed during construction.. usually None"""

        
        
        
        
        #get from string
        if impactFmtFunc is None: 
            if impactfmt_str is  None: impactfmt_str=self.impactfmt_str
            assert isinstance(impactfmt_str, str)
            
            impactFmtFunc = lambda x, fmt=impactfmt_str:'{:>{fmt}}'.format(x, fmt=fmt)
            
        
        self.impactFmtFunc=impactFmtFunc
        
        #check it
        assert callable(self.impactFmtFunc)
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
        
        

    def plot_impact_boxes(self, #box plots for each event 
                   df,  #frame with columns to turn into box plots
                      
                    #labelling
                    title = None,
                    xlab=None,  ylab=None, val_str=None,
                    impactFmtFunc=None, #tick label format function for impact values
                    smry_method = 'sum', #series method for summary providedin labels
                    
                    #figure parametrs
                    figsize=None,
                    grid=False,        
                    ylims_t = None, #tuple of yaxis limits
                    
                    logger=None, 
                    pkwargs = {},
                      ): 
        
        """
        todo: migrate these generic plotters to a more logical module

        """
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_impact_boxes')
        plt, matplotlib = self.plt, self.matplotlib
        

        if figsize is None: figsize    =    self.figsize
        
        
        if impactFmtFunc is None: impactFmtFunc=self.impactFmtFunc
        
        if title is None:
            title = 'Boxplots on %i events'%len(df.columns)
        
        log.debug('on %s'%str(df.shape))
        #=======================================================================
        # check
        #=======================================================================
        assert callable(impactFmtFunc)
        #=======================================================================
        # manipulate data
        #=======================================================================
        #get a collectio nof arrays from a dataframe's columns
        data = [ser.dropna().values for _, ser in df.items()]
        log.debug('on %i'%len(data))
        
        #======================================================================
        # figure setup
        #======================================================================
        plt.close()
        fig = plt.figure(figsize=figsize, constrained_layout = True)
        
        #check for max
        if len(data) > self.set_cnt_max:
            log.warning('data set count exceeds max: %i... skipping'%len(data))
            return fig
        
        #axis setup
        ax1 = fig.add_subplot(111)
        
        #aep units
        if not ylims_t is None:
            ax1.set_ylim(ylims_t[0], ylims_t[1])
 
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_xlabel(xlab)
        ax1.set_ylabel(ylab)
 

        
        #=======================================================================
        # plot thie histogram
        #=======================================================================
        boxRes_d = ax1.boxplot(data, whis=1.5, **pkwargs)
        #=======================================================================
        # format axis labels
        #======================================================= ================
        #build new lables
        f = lambda idx: getattr(df.iloc[:, idx-1], smry_method)()
        xfmtFunc = lambda idx:'%s (%i): %s=%s'%(
            df.columns[idx-1], len(df.iloc[:, idx-1].dropna()), smry_method, impactFmtFunc(f(idx)))
        l = [xfmtFunc(value) for value in ax1.get_xticks()]
        
        #adjust locations
        og_locs = ax1.get_xticks()
        ax1.set_xticks(og_locs-0.3) 
        
        #apply new lables
        Text_l = ax1.set_xticklabels(l, rotation=90, va='center', y=.5, color='red',)
        self._tickSet(ax1, yfmtFunc=impactFmtFunc)

        #=======================================================================
        # post
        #=======================================================================
        self._postFmt(ax1, grid=grid, val_str=val_str,
                      xLocScale=.2, yLocScale=.8,
                      legendLoc=None, #boxplots do nt have legends
                      )

        
        
        return fig
            
            
    def plot_impact_hist(self, #stacked histograms for each column series
                   df,  
                      
                    #labelling
                    title = None,
                    xlab=None,  ylab='asset count', val_str=None,
                    impactFmtFunc=None, #tick label format function for impact values

                    
                    #figure parametrs
                    figsize=None,
                    grid=True,        
                    xlims_t = None, #tuple of yaxis limits
                    
                    logger=None, 
                    pkwargs = {},
                      ): 
        
        """
        todo: migrate these generic plotters to a more logical module

        """
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_impact_boxes')
        plt, matplotlib = self.plt, self.matplotlib
        

        if figsize is None: figsize    =    self.figsize
        
        
        if impactFmtFunc is None: impactFmtFunc=self.impactFmtFunc
        
        if title is None:
            title = 'Histogram on %i Events'%len(df.columns)
        
        log.debug('on %s'%str(df.shape))
        #=======================================================================
        # manipulate data
        #=======================================================================
        #get a collectio nof arrays from a dataframe's columns
        data = [ser.dropna().values for _, ser in df.items()]

        
        #======================================================================
        # figure setup
        #======================================================================
        plt.close()
        fig = plt.figure(figsize=figsize, constrained_layout = True)
        
        #check for max
        if len(data) > self.set_cnt_max:
            log.warning('data set count exceeds max: %i... skipping'%len(data))
            return fig
        
        #axis setup
        ax1 = fig.add_subplot(111)
        
        #aep units
        if not xlims_t is None:
            ax1.set_xlim(xlims_t[0], xlims_t[1])
 
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_xlabel(xlab)
        ax1.set_ylabel(ylab)


        #=======================================================================
        # plot thie histogram
        #=======================================================================
        histVals_ar, bins_ar, patches = ax1.hist(
            data, bins='auto', stacked=False, label=df.columns.to_list(),
            alpha=0.9,
            **pkwargs)

        #=======================================================================
        # post
        #=======================================================================
        self._tickSet(ax1, xfmtFunc=impactFmtFunc)
        
        self._postFmt(ax1, grid=grid, val_str=val_str,
                      xLocScale=.3, yLocScale=.8,
                      )

        
        
        return fig
            

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
        if isinstance(legendLoc, int):
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
        """
        generally just returns the val_str
            but also provides some special handles
        """
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
    
    #===========================================================================
    # OUTPUTTRS------
    #===========================================================================
    def output_fig(self, fig,
                   
                   #file controls
                   out_dir = None, overwrite=None,
                   fname = None, #filename
                   
                   #figure write controls
                  fmt='svg', 
                  transparent=True, 
                  dpi = 150,
                  logger=None,
                  ):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.out_dir
        if overwrite is None: overwrite = self.overwrite
        if logger is None: logger=self.logger
        log = logger.getChild('output_fig')
        
        #=======================================================================
        # precheck
        #=======================================================================
        """
        self.plt.show()
        """
        
        assert isinstance(fig, self.matplotlib.figure.Figure)
        if not len(fig.axes) >0:
            log.warning('passed empty figure... skipping')
            return 'no'
        
        log.debug('on %s'%fig)
        #======================================================================
        # output
        #======================================================================
        #file setup
        if fname is None:
            try:
                fname = fig._suptitle.get_text()
            except:
                fname = self.name
            
        out_fp = os.path.join(out_dir, '%s.%s'%(fname, fmt))
            
        if os.path.exists(out_fp): assert overwrite

            
        #write the file
        try: 
            fig.savefig(out_fp, dpi = dpi, format = fmt, transparent=transparent)
            log.info('saved figure to file:   %s'%out_fp)
        except Exception as e:
            raise Error('failed to write figure to file w/ \n    %s'%e)
        
        return out_fp
    