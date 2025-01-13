'''
Created on Feb. 9, 2020

@author: cefect

plotting damage curves from the library

not implemented in GUI yet


TODO: Consolidate w/ riskPlot
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, itertools



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd
from hlpr.basic import force_open_dir, view, get_valid_filename

mod_name='curvePlot'
#==============================================================================
# # custom
#==============================================================================

from hlpr.exceptions import QError as Error
    
#===============================================================================
# setup matplotlib
#===============================================================================
 
    

#from hlpr.basic import ComWrkr
#import hlpr.basic
from model.modcom import DFunc, view
from hlpr.plot import Plotr


#==============================================================================
# functions-------------------
#==============================================================================
class CurvePlotr(DFunc, Plotr):
    subplot=111
    
    def __init__(self,
                 name='Results',
                 
                #===============================================================
                #  
                # figsize = (6,4), #6,4 seems good for documnets
                # subplot = 111,
                # 
                # #writefig
                # fmt = 'svg' ,#format for figure saving
                # dpi = 300,
                # transparent = False,
                #===============================================================


                 **kwargs
                 ):
        
 
 
        
        super().__init__(name=name, **kwargs) #initilzie teh baseclass
        
        #=======================================================================
        # attachments
        #=======================================================================
        

        
        #self.figsize, self.subplot, self.fmt, self.dpi, self.transparent = figsize, subplot, fmt, dpi, transparent
        self._init_plt()
        self.logger.info('init finished')
        
    def load_data(self, fp, 
                    index=None, header=None
                    ): #load a curve set
        
        log = self.logger.getChild('load_data')
        #precheck
        assert os.path.exists(fp)
        data_d = pd.read_excel(fp, sheet_name=None,index_col=index, header=header )
        
        #=======================================================================
        # summary tab
        #=======================================================================
        if '_smry' in data_d:
            log.info('found smry tab... co nfiguring')
            hndl_df =pd.read_excel(fp, 
                                   sheet_name='_smry',index_col=0, header=0 
                                   ).dropna(axis=1, how='all')
            
            data_d['_smry'] = hndl_df
 
        
        log.info('loaded %i tabs from \n    %s\n    %s'%(
            len(data_d), fp, list(data_d.keys())))
        
        return data_d
    
    def plotAll(self, #plot everything in a single group
                cLib_d, #container of functions
                lib_as_df = True, #indicator for format of passed lib
                title=None,
                logger=None,
                **lineKwargs
                ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger

        
        log = logger.getChild('plotAll')
        log.info('plotting w/ %i'%len(cLib_d))
        
        if title is None: title='%s vFunc plot of %i curves'%(self.tag, len(cLib_d))
        self.plt.close()
        #=======================================================================
        # convert clib
        #=======================================================================
        if lib_as_df:
            assert isinstance(cLib_d[list(cLib_d.keys())[0]], pd.DataFrame), 'expected frames'
            cLib_d = {k:df.set_index(df.columns[0], drop=True).iloc[:,0].to_dict() for k, df in cLib_d.items()}
            
            """
            for k,v in cLib_d.items():
                print(k, type(v))
            """

        
        #===============================================================
        # loop and plot
        #===============================================================
        ax = None
        marker = itertools.cycle(('+', '1', 'o', '2', 'x', '3', '4'))
                                 
        for cName, crv_d in cLib_d.items():
            if cName.startswith('_'): continue #skip these

            
            ax = self.plotCurve(crv_d, ax=ax,
                                marker=next(marker),
                                **lineKwargs)
            
        #post format
        fig = ax.figure
        fig.suptitle(title)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.20),
                                fancybox=True, shadow=True, ncol=6)
        ax.grid()
        
        return fig
            

    
    
    def plotGroup(self, #plot a group of figures w/ handles
                  cLib_d, #container of data to plot {cName: crv_d}
                  pgCn='plot_group', #group plots
                  pfCn='plot_f', #plot flag
                  
                  title=None,
                  grid=None,
                
                  lib_as_df = False, #indicator for format of passed lib
                  logger=None,
                  
                  **lineKwargs #kwargs for self.line
                  ):
        
        
        #======================================================================
        # defaults
        #======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plotGroup')
        
        if title is None: title='%s vFunc plot'%(self.tag)
        if grid is None: grid=self.grid

        
        #results container
        res_d = dict()
        #=======================================================================
        # #pull out the handles----------
        #=======================================================================
        if '_smry' in cLib_d:
            hndl_df =cLib_d.pop('_smry')
 
            
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
        if lib_as_df:
            for cName, data in cLib_d.copy().items():
                if isinstance(data, pd.DataFrame):
                    cLib_d[cName] = data.set_index(0, drop=True).iloc[:,0].to_dict()

        
        #=======================================================================
        # check
        #=======================================================================
        for cName, crv_d in cLib_d.items():
            assert self.check_crvd(crv_d), '%s failed'%cName
 
        #=======================================================================
        # PLOT no handles-----------
        #=======================================================================
        if hndl_df is None:
            log.info('no handles provided. plotting %i individual curves'%len(cLib_d))
            
            indxr=0
            for cName, crv_d in cLib_d.items():
                assert 'tag' in crv_d, 'failed to get \'tag\' field on \'%s\''%cName
                ax = self.plotCurve(crv_d, title=crv_d['tag'], **lineKwargs)
                
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
                marker = itertools.cycle(('+', '1', 'o', '2', 'x', '3', '4'))
                
                for cName, row in pdf.iterrows():
                    #get this curve
                    crv_d = cLib_d[cName]
                    log.debug('plotting %s'%cName)
                    ax = self.plotCurve(crv_d, ax=ax,marker=next(marker),**lineKwargs)
                    
                #post format
                fig = ax.figure
                fig.suptitle(pgroup + ' ' + title)
                ax.legend()
                if grid:
                    ax.grid()
                #===============================================================
                # group loop
                #===============================================================
                if indxr>20: 
                    log.warning('to omany curves.. breaking')
                    break
                
                
                
                #add results
                res_d[pgroup] = fig
                
                #wrap
                indxr +=1


                
        #=======================================================================
        # wrap--------
        #=======================================================================
        
        log.info('finished generating %i figures'%len(res_d))
        return res_d
                
        
                
                
    def plotCurve(self, #plot a single CanFlood curve definition
                  crv_d,

                  logger=None,
                  **lineKwargs):
        """
        TODO: allow plotting with curve_deviation
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        assert 'tag' in crv_d, 'missing tag in \n    %s'%crv_d
        log = logger.getChild('plot%s'%crv_d['tag'])
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert self.check_crvd(crv_d, logger=log)
        
        #=======================================================================
        # extract data
        #=======================================================================
        dd_f = False
        dd_d = dict()
        for k, v in crv_d.items():
            #set the flag that we've reached the depth-damage values
            if k == 'exposure':
                dd_f = True
                continue
            
            if dd_f:
                dd_d[k]=v
                
        log.debug('collected %i dd vals: \n    %s'%(len(dd_d), dd_d))
        dser = pd.Series(dd_d, name=crv_d['tag'])
        
        #=======================================================================
        # assemble parameters
        #=======================================================================
        pars_d = dict()
 
        
        #add fillers
        cd1 = crv_d.copy()
        for k in ['exposure_var', 'exposure_units', 'impact_var', 'impact_units', 'color']:
            if not k in cd1:
                cd1[k] = None
        
        #labels
        pars_d['ylab'] = '%s (%s)'%(cd1['exposure_var'], cd1['exposure_units'])
        pars_d['xlab'] = '%s (%s/%s)'%(cd1['impact_var'], cd1['impact_units'], cd1['scale_units'])
        #pars_d['color'] = cd1['color']
                          
        #return the axis
        return self.line(dser.values, dser.index.values,
                         
                         ylab=pars_d['ylab'],
                         xlab=pars_d['xlab'],
                         #color=pars_d['color'],
                         label=crv_d['tag'],
                          **lineKwargs)
        
    def line(self, #add a vfunc to the axis
                #values to plot
                xvals, yvals,
                
                #figure controls
                constrained_layout=None,
                tight_layout=None,
                
                #plot controls
                ax = None,
                title = None,
                ylab=None,
                xlab=None,
                
                xlim=None,

                **kwargs, #splill over kwargs
                ):
        """
        for plotting risk curves
            see: RiskModel._lineToAx
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        plt= self.plt
        figsize=self.figsize
        subplot=self.subplot
        
        if constrained_layout is None:
            constrained_layout=self.constrained_layout
        if tight_layout is None: tight_layout=self.tight_layout
        
        """
        plt.show()
        """
        #=======================================================================
        # setup axis
        #=======================================================================
        if ax is None:

            fig = plt.figure(figsize=figsize,tight_layout=tight_layout,
                     constrained_layout = constrained_layout)

            ax = fig.add_subplot(subplot)  
            
            if not xlim is None:
                ax.set_xlim(xlim)
            
            #set the suptitle
            if isinstance(title, str):
                ftitle=title
            else:
                ftitle='figure' #needed for filepath?
                
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
        
    
        #==========================================================================
        # plot it
        #==========================================================================
        #log.debug('plotting \"%s\' w/ \n    %s \n    %s'%( title, xvals, yvals))
        
        ax.plot(xvals, yvals, 
                #markerfacecolor='black',
                #markersize=markersize, 
                #fillstyle='full',

                **kwargs)
 
    
        return ax
                
    def output(self,
               d,
               ofn = None,
               out_dir = None,
               ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('output')
        if out_dir is None: out_dir=self.out_dir
        if not os.path.exists(out_dir):os.makedirs(out_dir)
        if ofn is None:
            ofn = 'cLib_%s_%s.xls'%(self.tag, self.today_str)
        
        ofn = get_valid_filename(ofn)
        assert os.path.splitext(ofn)[1]=='.xls', ofn
        #=======================================================================
        # precheck
        #=======================================================================

        
        #=======================================================================
        # patsh
        #=======================================================================
        ofp = os.path.join(out_dir, ofn)
        assert len(d)>0
        if os.path.exists(ofp): assert self.overwrite
        
        #write to multiple tabs
        #ofp = ofp.replace('.xls', '.xlsx') #no.. force the user to pass xlsx 
        with pd.ExcelWriter(ofp) as writer:
            for i, (tabnm, data) in enumerate(d.items()):
                #write handles
                if tabnm=='_smry':
                    index, header = True, True
                else:
                    index, header = False, False
                    
                #tab check
                
                if len(tabnm)>30:
                    log.warning('changing tab name! this can break tagging')
                    tabnm = tabnm.replace(' ','')
                    
                if len(tabnm)>30:
                    tabnm = tabnm[:29]+'%s'%i
                    
                #data format
                if isinstance(data, dict):
                    df = pd.Series(data).to_frame()
                elif isinstance(data,  pd.DataFrame):
                    df = data
                else:
                    raise Error('bad')
                    
                df.to_excel(writer, sheet_name=tabnm, index=index, header=header)
            
            
        print('wrote %i sheets to %s'%(len(d), ofp))
            
        return ofp
       


        