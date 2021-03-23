'''
Created on Feb. 9, 2020

@author: cefect

simple build routines
'''

#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, configparser, datetime, shutil



#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd
from pandas import IndexSlice as idx

#Qgis imports
from qgis.core import QgsVectorLayer, QgsWkbTypes, QgsMapLayerStore, QgsFeatureRequest, QgsProcessingParameterExpression,\
    QgsExpression
import processing
#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, view, stat_pars_d, \
    vlay_rename_fields
    
 
from .dcoms import Dcoms
    
#from hlpr.basic import get_valid_filename

from hlpr.plot import Plotr

#==============================================================================
# functions-------------------
#==============================================================================
class DPlotr(Dcoms, Plotr):
    """

    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """


    def __init__(self,
                 figsize     = (10, 4),                  
                  *args,  **kwargs):
        
        super().__init__(*args, figsize=figsize,**kwargs)
        

        
        self.logger.debug('Diker.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
    def plot_seg_prof(self, #get a plot for a single segment 
                      sidVal,
                      dxcol_raw = None,
                      
                      sid = None,
                      logger=None,
                      
                      #plot handles
                      figsize=None,
                      
                      **kwargs
                      ):
        
        plt, matplotlib = self.plt, self.matplotlib
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('plot_seg_prof')
        if dxcol_raw is None: dxcol_raw = self.expo_dxcol.copy()
        if sid is None: sid=self.sid
        if figsize is None: figsize    =    self.figsize
        
        #=======================================================================
        # precheck
        #=======================================================================

        assert sidVal in dxcol_raw.loc[:, idx[:, sid]].values, 'requested %s not found: %s'%(sid, sidVal)
        
        miss_l = set([sid, self.sdistn,self.celn,self.wsln]).difference(dxcol_raw.columns.levels[1])
        assert len(miss_l)==0, 'missing some expected columns: %s'%miss_l
        
        #=======================================================================
        # data slice----
        #=======================================================================\
        boolidx = dxcol_raw.loc[:, idx[:, sid]].iloc[:, 0]==sidVal
        dxcol = dxcol_raw.loc[boolidx, :]
        
        
        #=======================================================================
        # common data
        #=======================================================================
        
        #extracting common info from first set
        """ assuming the sid column is the same on all levels"""
        dike_df = dxcol.loc[:, 'common']
                            
        
        
        #get labels
        segIDVal = dike_df[self.segID].unique()[0]
        dikeIDVal = dike_df[self.dikeID].unique()[0]
        
        dike_df = dike_df.drop([self.segID, self.dikeID], axis=1)
        log.info('getting plot from %s'%str(dike_df.shape))
        

        
        
        #======================================================================
        # labels
        #======================================================================
        y1lab = 'elv (datum m)'
        xlab = 'profile distance (m)'
        title = '%s dike %s-%s profiles'%(self.tag, dikeIDVal, segIDVal)


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
        # add  wsl profiles
        #=======================================================================
        """
        view(dxcol.columns.to_frame())
        """
        
        #get the data slice and sort it
        dxcol1 = dxcol.drop('common', axis=1, level=0).sort_index(
            axis=1, level=None, ascending=False)
        
        #loop over lvl0 values/subframes
        for l0val, edxcol in dxcol1.groupby(level=0, axis=1):
            edf =  edxcol.droplevel(level=0, axis=1).join(dike_df[self.sdistn])
            self._wsl_toAx(ax1,edf, label = '%s_%s'%(l0val, self.wsln))
            
        log.info('added %i \'%s\' plots'%(
            len(dxcol.columns.levels[0])-1, self.wsln))
        
        ymin, ymax = ax1.get_ylim()
        #=======================================================================
        # add crest
        #=======================================================================
        
        self._crest_toAx(ax1, dike_df)
            
        #=======================================================================
        # limits
        #=======================================================================
        ax1.set_xlim(dike_df[self.sdistn].min(), dike_df[self.sdistn].max())
        
        ax1.set_ylim(ymin-1, ymax+1)
        
        
        #=======================================================================
        # post format
        #=======================================================================
        if self.grid: ax1.grid()
        ax1.legend()
        

        
        
        
        return fig

        
    def _wsl_toAx(self,
                 ax, df, style_d = {
                             #'color':'blue',

                              'marker':'v',
                              'markeredgecolor':'blue',
                              'linewidth':.75,
                              'fillstyle':'none',
                              },
                 label = None,
                 ):
        if label is None: label = self.wsln
        
        xar,  yar = df[self.sdistn].values, df[self.wsln].values
        return ax.plot(xar,yar, label= label,
                        **style_d)
        
        
        
    def _crest_toAx(self, #add the two lines to the plot
                     ax, df, 
                     style_d = {
                         'color':'brown',
                          'marker':'+',
                          'linewidth':1.5
                          },
                     
                     #hatch pars
                     hatch_f = True,
                     hstyle_d = {
                         'color':'orange',
                         'alpha':0.1,
                         'hatch':None,
                         }
                         ):
        
        xar,  yar = df[self.sdistn].values, df[self.celn].values
        lines =  ax.plot(xar,yar, label= self.celn,
                        **style_d)
        
        if hatch_f:
            polys = ax.fill_between(xar, yar, y2=0,**hstyle_d)
        
        return lines
        
    

 
    
    
    

    

            
        