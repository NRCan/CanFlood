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


mod_name='curvePlot'
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
    
#===============================================================================
# setup matplotlib
#===============================================================================

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
    

from hlpr.basic import ComWrkr
import hlpr.basic




#==============================================================================
# functions-------------------
#==============================================================================
class CurvePlotr(ComWrkr):
    
    
    def __init__(self,
                 name='Results',
                 
                 
                 figsize = (6,4), #6,4 seems good for documnets
                subplot = 111,
                
                #writefig
                fmt = 'svg' ,#format for figure saving
                dpi = 300,
                transparent = False,


                 **kwargs
                 ):
        
        """inherited by the dialog.
        init is not called during the plugin"""
        mod_logger.info('simple wrapper inits')
        
        super().__init__(**kwargs) #initilzie teh baseclass
        
        #=======================================================================
        # attachments
        #=======================================================================
        
        self.name = name
        
        self.figsize, self.subplot, self.fmt, self.dpi, self.transparent = figsize, subplot, fmt, dpi, transparent
        
        self.logger.info('init finished')
        
    def load_data(self, fp):
        log = self.logger.getChild('load_data')
        #precheck
        assert os.path.exists(fp)
        data_d = pd.read_excel(fp, sheet_name=None, index=None, header=None)
        
        log.info('loaded %i tabs'%len(data_d))
        
        return data_d
    
    
    def plotGroup(self, #plot a group of figures w/ handles
                  cLib_d,
                  pgCn='plot_group',
                  pfCn='plot_f',
                  
                  marker='o', markersize=3,
                  
                  logger=None,
                  ):
        
        
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plotGroup')
        

        
        #results container
        res_d = dict()
        #=======================================================================
        # #pull out the handles----------
        #=======================================================================
        if '_smry' in cLib_d:
            hndl_df =cLib_d.pop('_smry')
            
            #re-tag the columns
            colns = hndl_df.iloc[0,:].values
            colns[0] = 'cName'
            hndl_df.columns = colns
            
            hndl_df = hndl_df.set_index('cName', drop=False).drop('cName') 

            
   
            
            #see if the expected columns are there
            boolcol = hndl_df.columns.isin([pgCn, pfCn])
            
            if not boolcol.any():
                log.warning('loaded a _smry tab.. but no handle columns provided')
                hndl_df = None
                
            else:
                hndl_df = hndl_df.loc[:, boolcol]
            
            
        else:

            hndl_df = None
            
        #=======================================================================
        # convert clib
        #=======================================================================
        d = dict()
        for cName, curve_df in cLib_d.items():
            d[cName] = curve_df.set_index(0, drop=True).iloc[:,0].to_dict()
            
        cLib_d = d
            
        #=======================================================================
        # precheck
        #=======================================================================

        #=======================================================================
        # PLOT no handles-----------
        #=======================================================================
        if hndl_df is None:
            log.info('no handles provided. plotting %i individual curves'%len(cLib_d))
            
            indxr=0
            for cName, crv_d in cLib_d.items():
                ax = self.plotCurve(crv_d, title=crv_d['tag'])
                
                res_d[cName] =ax.figure
                
                indxr+=1
                
                if indxr>50:
                    log.warning('too many curves.. breaking loop')
                    break
                

        #=======================================================================
        # PLOT with handles-----------    
        #=======================================================================
        else:
            log.info('handles %s provided. plotting %i individual curves'%(
                str(hndl_df.shape), len(cLib_d)))
            
            #check the handles match the lib
            l = set(hndl_df.index).difference(cLib_d.keys())
            assert len(l)==0, 'library meta mismatch: %s'%l
            
            #add d ummy plot group if missing
            if not pgCn in hndl_df.columns:
                hndl_df[pgCn]='group1'
                
            if not pfCn in hndl_df.columns:
                hndl_df[pfCn]=True
                
            #===================================================================
            # preclean
            #===================================================================
            hndl_df = hndl_df.loc[hndl_df[pfCn], :]
                
            #===================================================================
            # loop and plot by groups
            #===================================================================
            grps = hndl_df[pgCn].unique().tolist()
            log.info('generating plots on %i groups: \n    %s'%(
                len(grps), grps))
            
            indxr=0
            for pgroup, pdf in hndl_df.groupby(pgCn):
                log = logger.getChild('plotGroup.%s'%pgroup)
                log.info('plotting w/ %s'%str(pdf.shape))

                
                #===============================================================
                # loop and plot
                #===============================================================
                ax = None
                
                for cName, row in pdf.iterrows():
                    #get this curve
                    crv_d = cLib_d[cName]
                    
                    ax = self.plotCurve(crv_d, ax=ax,
                                        marker=marker, markersize=markersize)
                    
                #post format
                fig = ax.figure
                fig.suptitle(pgroup)
                fig.legend()
                    
                #===============================================================
                # group loop
                #===============================================================
                if indxr>50: 
                    log.warning('to omany curves.. breaking')
                    break
                indxr +=1
                
                #add results
                res_d[cName] = fig

                
        #=======================================================================
        # wrap--------
        #=======================================================================
        
        log.info('finished generating %i figures'%len(res_d))
        return res_d
                
        
                
                
    def plotCurve(self, #plot a single CanFlood curve definition
                  crv_d,

                  logger=None,
                  **lineKwargs):
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
        dser = pd.Series(dd_d, name=crv_d['tag'])
        
        #=======================================================================
        # assemble parameters
        #=======================================================================
        pars_d = dict()
        for par, cpar in {'ylab':'exposure_var', 
                          'xlab':'impact_var',
                          'color':'color'}.items():
            
            if cpar in crv_d:
                pars_d[par]=crv_d[cpar]
            else:
                pars_d[par]=None
                          
        
        return self.line(dser.values, dser.index.values,
                         
                         ylab=pars_d['ylab'],
                         xlab=pars_d['xlab'],
                         color=pars_d['color'],
                         label=crv_d['tag'],
                          **lineKwargs)
        
    def line(self,
                #values to plot
                xvals, yvals,
                
                #plot controls
                ax = None,
                title = None,
                ylab=None,
                xlab=None,
                **kwargs):
        
        #=======================================================================
        # defaults
        #=======================================================================
        
        figsize=self.figsize
        subplot=self.subplot
        
        #=======================================================================
        # setup axis
        #=======================================================================
        if ax is None:

            fig = plt.figure()
            fig.set_size_inches(figsize)
            ax = fig.add_subplot(subplot)  
            
            #set the suptitle
            if isinstance(title, str):
                ftitle=title
            else:
                ftitle='figure'
                
            fig.suptitle(ftitle)
            
        else:
            fig = plt.gcf()
        
        
        #set labels
        if isinstance(ylab,str):
            _ = ax.set_ylabel(ylab) 
        if isinstance(xlab, str):
            _ = ax.set_xlabel(xlab)
        if isinstance(title, str):
            _ = ax.set_title(title)
        
        """
        plt.show()
        """
                
        #==========================================================================
        # plot it
        #==========================================================================
        #log.debug('plotting \"%s\' w/ \n    %s \n    %s'%( title, xvals, yvals))
        
        ax.plot(xvals, yvals, **kwargs)
        
        """
        plt.show()
        """
        
    
        return ax
                

if __name__ =="__main__": 
    print('start')

    
    #===========================================================================
    #nrp curves
    #===========================================================================
    data_dir = r'C:\LS\03_TOOLS\LML\_keeps2\nrp\nrpPer_20200517125446'
    
    runpars_d={
        'inEq':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_inEq.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'inStk':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_inStk.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'outEq':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_outEq.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'outStk':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_outStk.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        }
    
    #===========================================================================
    #mbc curves
    #===========================================================================
    data_dir = r'C:\LS\03_TOOLS\LML\_keeps2\curves\mbc\curving\mbcC_20200519145845'
    
    runpars_d={
        'f0':{
            'out_dir':os.path.join(data_dir,'figs', 'f0'),
            'curves_fp':os.path.join(data_dir, 'curves_mbcC_03_20200519_f0_29.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'f1':{
            'out_dir':os.path.join(data_dir,'figs', 'f1'),
            'curves_fp':os.path.join(data_dir, 'curves_mbcC_03_20200519_f1_54.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'gar':{
            'out_dir':os.path.join(data_dir,'figs', 'gar'),
            'curves_fp':os.path.join(data_dir, 'curves_mbcC_03_20200519_gar_17.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'gen':{
            'out_dir':os.path.join(data_dir, 'figs','gen'),
            'curves_fp':os.path.join(data_dir, 'curves_mbcC_03_20200519_gen_52.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'f1gen':{
            'out_dir':os.path.join(data_dir, 'figs','f1gen'),
            'curves_fp':os.path.join(data_dir, 'curves_mbcC_03_20200519_f1gen_54.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        }
    
    #===========================================================================
    # rfda curves
    #===========================================================================
    data_dir = r'C:\LS\02_WORK\IBI\201909_FBC\04_CALC\curves\rfda'
    
    runpars_d={
        'cont':{
            'out_dir':os.path.join(data_dir,'figs'),
            'curves_fp':os.path.join(data_dir, 'CanFlood_curves_rfda_20200218.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        }
    
    for tag, pars in runpars_d.items():
        #=======================================================================
        # defaults
        #=======================================================================
        log = logging.getLogger(tag)
        out_dir, curves_fp = pars['out_dir'], pars['curves_fp']
        #=======================================================================
        # precheck
        #=======================================================================
        
        #=======================================================================
        # execute
        #=======================================================================
        wrkr = CurvePlotr(out_dir=out_dir, logger=log, tag=tag)
        
        #load data
        curves_d = wrkr.load_data(curves_fp)
        
        """expects 'plot_f'  and 'plot_group' columns"""
        res_d = wrkr.plotGroup(curves_d) 
        
        for cname, fig in res_d.items():
            wrkr.output_fig(fig)


        
        log.info('finished')

   
        
        
    
    hlpr.basic.force_open_dir(out_dir)
    
    print('finished')
    

    
    
       


        