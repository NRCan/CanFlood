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


#Qgis imports
from qgis.core import QgsVectorLayer, QgsWkbTypes

#==============================================================================
# custom imports
#==============================================================================
from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, view
from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class Diker(Qcoms):
    """

    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """

    def __init__(self,

                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        
        self.logger.debug('Diker.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def load_rlays(self,
                   layfp_d,
                   logger=None,
                   **kwargs):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('load_rlays')
        
        log.info('on %i layers'%len(layfp_d))
        
        #=======================================================================
        # load it
        #=======================================================================
        d = dict()
        
        for layTag, fp in layfp_d.items():
            d[layTag] = self.load_rlay(fp, logger=log, **kwargs)
            
        log.info('loaded %i layers'%len(d))
        
        return d
    
    def load_dike(self, fp,
                  dikeID = 'dikeID', #dike identifier field
                  segID = 'segID', #segment identifier field
                   logger=None, **kwargs):
        
        if logger is None: logger=self.logger
        log = logger.getChild('load_dikes')
        
        vlay = self.load_vlay(fp, **kwargs)
        

        df = vlay_get_fdf(vlay, logger=log)
        
        

        
        #=======================================================================
        # checks
        #=======================================================================
        
        
        
        miss_l = set([dikeID, segID]).difference(df.columns)
        assert len(miss_l)==0, 'missing expected columns on dike layer: %s'%miss_l
        
        """try forcing
        assert 'int' in df[segID].dtype.name, 'bad dtype on dike layer %s'%segID
        assert 'int' in df[dikeID].dtype.name, 'bad dtype on dike layer %s'%dikeID"""
        
        #geometry
        assert 'Line' in QgsWkbTypes().displayString(vlay.wkbType()), 'bad vector type on dike'
        
        dp = vlay.dataProvider()
        
        #=======================================================================
        # build global segment ids
        #=======================================================================
        #type forcing
        for coln in [dikeID, segID]:
            try:
                df[coln] = df[coln].astype(int)
            except Exception as e:
                raise Error('failed to type set dike column \'%s\' w/ \n%s'%(coln, e))
        
        
        s1 = df[dikeID].astype(str).str.pad(width=3, side='left', fillchar='0')
        s2 = df[segID].astype(str).str.pad(width=2, side='left', fillchar='0')
        
        df['sid'] = s1.str.cat(others=s2).astype(int)
        

        # bundle back into vectorlayer
        geo_d = vlay_get_fdata(vlay, geo_obj=True, logger=log)
        res_vlay = self.vlay_new_df2(df, geo_d=geo_d, logger=log,
                               layname=vlay.name())
        
        
        #=======================================================================
        # wrap
        #=======================================================================

        log.info('loaded dike layer \'%s\'  w/ %i segments'%(vlay.name(), dp.featureCount()))

        self.dike_vlay = res_vlay
        
        """
        view(vlay)
        
        """
        
        return self.dike_vlay
    
    def load_fcurves(self):
        pass
    
    def run_breachP(self, #get location and probability of breach using fragility curves
                    noFailr_d,
                    dike_vlay = None,
                    dtm_rlay = None,
                    
                    logger=None,
                    ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('run_breachP')
        if dike_vlay is None: dike_vlay = self.dike_vlay
        if dtm_rlay is None: dtm_rlay = self.dtm_rlay
        
        #=======================================================================
        # prechecks
        #=======================================================================
        
        
        #=======================================================================
        # crossProfiles
        #=======================================================================
        
        
        







                

 
    
    
    

    

            
        