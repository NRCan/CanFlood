'''
Created on Feb. 9, 2020

@author: cefect

plotting damage curves from the library
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
#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
    

#plugin runs
else:
    #base_class = object
    from hlpr.exceptions import QError as Error
    

from hlpr.basic import ComWrkr
import hlpr.basic


#==============================================================================
# functions-------------------
#==============================================================================
class CurvePlotr(ComWrkr):
    
    
    def __init__(self,
                 name='Results',
                 **kwargs
                 ):
        
        """inherited by the dialog.
        init is not called during the plugin"""
        mod_logger.info('simple wrapper inits')
        

        
        super().__init__(**kwargs) #initilzie teh baseclass
        
        self.name = name
        
        self.logger.info('init finished')
        
    def load_data(self, fp):
        log = self.logger.getChild('load_data')
        #precheck
        assert os.path.exists(fp)
        data_d = pd.read_excel(fp, sheet_name=None, index=None, header=None)
        
        log.info('loaded %i tabs'%len(data_d))
        
        return data_d
    
    
    def plotGroup(self, #plot a group of figures w/ handles
                  curves_d,
                  ):
        
        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('plotGroup')
        

        
        #results container
        res_d = dict()
        #=======================================================================
        # #pull out the handles
        #=======================================================================
        if '_smry' in curves_d:
            hndl_df =curves_d.pop('_smry')
            
            #re-tag the columns
            colns = hndl_df.iloc[0,:].values
            colns[0] = 'cName'
            hndl_df.columns = colns
            
            hndl_df = hndl_df.set_index('cName', drop=False).drop('cName') 

            
   
            
            #see if the expected columns are there
            boolcol = hndl_df.columns.isin(['plot_group', 'plot'])
            
            if not boolcol.any():
                log.warning('loaded a _smry tab.. but no handle columns provided')
                hndl_df = None
                
            else:
                hndl_df = hndl_df.loc[:, boolcol]
            
            
        else:

            hndl_df = None
            
        #=======================================================================
        # precheck
        #=======================================================================
        """dev"""
        hndl_df = None
        #=======================================================================
        # no handles
        #=======================================================================
        if hndl_df is None:
            log.info('no handles provided. plotting %i individual curves'%len(curves_d))
            for cName, curve_df in curves_d.items():
                crv_d = curve_df.set_index(0, drop=True).iloc[:,0].to_dict()
                res_d[cName] = self.plotCurve(crv_d)
            
        #=======================================================================
        # with handles    
        #=======================================================================
        else:
            log.info('handles %s provided. plotting %i individual curves'%(
                str(hndl_df.shape), len(curves_d)))
            
                
        
                
        
                
                
    def plotCurve(self,
                  crv_d,
                  tag='Curve',
                  logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        assert 'tag' in crv_d
        log = logger.getChild('plot%s'%crv_d['tag'])
        
        #=======================================================================
        # precheck
        #=======================================================================
        self.check_curve(crv_d, logger=log)
        
        #=======================================================================
        # extract data
        #=======================================================================
        dd_f = False
        dd_d = dict()
        for k, v in crv_d.items():
            #set the flag
            if k == 'exposure':
                dd_f = True
                continue
            
            if dd_f:
                dd_d[k]=v
                
        log.info('collected %i dd vals: \n    %s'%(len(dd_d), dd_d))
                
            
            
        
        
        
        
            
        
        
    def run(self, #generate and save a figure that summarizes the damages 
                  curves_d,
                  
                  #labels
                  xlab='ARI', y1lab=None, y2lab='AEP',
                  
                  #format controls
                  grid = True, logx = False, 
                  basev = 1, #base value for dividing damage values
                  dfmt = '{0:.0f}', #formatting of damage values 
                  
                  
                  #figure parametrs
                figsize     = (6.5, 4), 
                    
                #hatch pars
                    hatch =  None,
                    h_color = 'blue',
                    h_alpha = 0.1,
                  ):
        
        """
        summary risk results plotter
        
        This is duplicated on modcom.risk_plot()
        
        """
        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        



        if y1lab is None: y1lab = self.y1lab
        #======================================================================
        # precheck
        #======================================================================
        assert isinstance(dmg_ser, pd.Series)
        assert 'ead' in dmg_ser.index, 'dmg_ser missing ead index'
        #======================================================================
        # setup
        #======================================================================
        
        import matplotlib
        matplotlib.use('SVG') #sets the backend (case sensitive)
        import matplotlib.pyplot as plt
        
        #set teh styles
        plt.style.use('default')
        
        #font
        matplotlib_font = {'family' : 'serif',
                'weight' : 'normal',
                'size'   : 8}
        
        matplotlib.rc('font', **matplotlib_font)
        matplotlib.rcParams['axes.titlesize'] = 10 #set the figure title size
        
        #spacing parameters
        matplotlib.rcParams['figure.autolayout'] = False #use tight layout
        
        #======================================================================
        # data manipulations
        #======================================================================
        #get ead
        ead_tot = dmg_ser['ead']
        del dmg_ser['ead'] #remove it from plotter values
        
        #typeset index
        dmg_ser.index = dmg_ser.index.astype(np.float64)
        
        
        #get damage series to plot
        ar = np.array([dmg_ser.index, dmg_ser.values]) #convert to array
        
        #invert aep (w/ zero handling)
        ar[0] = 1/np.where(ar[0]==0, #replaced based on zero value
                           sorted(ar[0])[1]/10, #dummy value for zero (take the second smallest value and divide by 10)
                           ar[0]) 
        
        dmg_ser = pd.Series(ar[1], index=ar[0], dtype=float) #back into series
        dmg_ser.index = dmg_ser.index.astype(int) #format it
                
        
        #get aep series
        aep_ser = dmg_ser.copy()
        aep_ser.loc[:] = 1/dmg_ser.index
        
        
        #======================================================================
        # labels
        #======================================================================
        
        val_str = 'total Annualized = ' + dfmt.format(ead_tot/basev)
        
        title = 'CanFlood \'%s\' Annualized-%s plot on %i events'%(self.tag, xlab, len(dmg_ser))
        
        #======================================================================
        # figure setup
        #======================================================================
        plt.close()
        fig = plt.figure(1)
        fig.set_size_inches(figsize)
        
        #axis setup
        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx()
        ax1.set_xlim(max(aep_ser.index), 1) #aep limits 
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_ylabel(y1lab)
        ax2.set_ylabel(y2lab)
        ax1.set_xlabel(xlab)
        
        #======================================================================
        # fill the plot
        #======================================================================
        #damage plot
        xar,  yar = dmg_ser.index.values, dmg_ser.values
        pline1 = ax1.semilogx(xar,yar,
                            label       = y1lab,
                            color       = 'black',
                            linestyle   = 'dashdot',
                            linewidth   = 2,
                            alpha       = 0.5,
                            marker      = 'x',
                            markersize  = 2,
                            fillstyle   = 'full', #marker fill style
                            )
        #add a hatch
        polys = ax1.fill_between(xar, yar, y2=0, 
                                color       = h_color, 
                                alpha       = h_alpha,
                                hatch       = hatch)
        
        #aep plot
        xar,  yar = aep_ser.index.values, aep_ser.values
        pline2 = ax2.semilogx(xar,yar,
                            label       = y2lab,
                            color       = 'blue',
                            linestyle   = 'dashed',
                            linewidth   = 1,
                            alpha       = 1,
                            marker      = 'x',
                            markersize  = 0,
                            )
        

        
        #=======================================================================
        # Add text string 'annot' to lower left of plot
        #=======================================================================
        xmin, xmax1 = ax1.get_xlim()
        ymin, ymax1 = ax1.get_ylim()
        
        x_text = xmin + (xmax1 - xmin)*.1 # 1/10 to the right of the left ax1is
        y_text = ymin + (ymax1 - ymin)*.1 #1/10 above the bottom ax1is
        anno_obj = ax1.text(x_text, y_text, val_str)
        
        #=======================================================================
        # format axis labels
        #======================================================= ================
        #damage values (yaxis for ax1)
        old_tick_l = ax1.get_yticks() #get teh old labels
         
        # build the new ticks
        l = [dfmt.format(value/basev) for value in old_tick_l]
              
        #apply the new labels
        ax1.set_yticklabels(l)
        
        
        
        #ARI (xaxis for ax1)
        ax1.get_xaxis().set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
        
        #=======================================================================
        # post formatting
        #=======================================================================
        if grid: ax1.grid()
        

        #legend
        h1, l1 = ax1.get_legend_handles_labels() #pull legend handles from axis 1
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1+h2, l1+l2, loc=2) #turn legend on with combined handles
        
        return fig
    
    

if __name__ =="__main__": 
    print('start')

    
    #===========================================================================
    # tutorials
    #===========================================================================
    runpars_d={
        'Tut1a':{
            'out_dir':os.path.join(os.getcwd(),'riskPlot', 'Tut1a'),
            'curves_fp':r'C:\LS\03_TOOLS\LML\_keeps\mbc\mbc_20200409130224\curves_mbc.compile_dev_161.xls',
            'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },

        }
    
    for tag, pars in runpars_d.items():
        #=======================================================================
        # defaults
        #=======================================================================
        log = logging.getLogger(tag)
        out_dir, curves_fp, dfmt, y1lab = pars['out_dir'], pars['curves_fp'], pars['dfmt'], pars['y1lab']
        #=======================================================================
        # precheck
        #=======================================================================



        #=======================================================================
        # execute
        #=======================================================================
        wrkr = CurvePlotr(out_dir=out_dir, logger=log, tag=tag)
        
        #load data
        curves_d = wrkr.load_data(curves_fp)
        
        wrkr.plotGroup(curves_d)
        
        for fig in wrkr.res_figs:
            wrkr.output_fig(fig)


        
        log.info('finished')

   
        
        
    
    hlpr.basic.force_open_dir(out_dir)
    
    print('finished')
    

    
    
       


        