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

#standalone runs
 
from hlpr.exceptions import QError as Error
    

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata
from hlpr.basic import get_valid_filename

#==============================================================================
# functions-------------------
#==============================================================================
class Preparor(Qcoms):
    """

    
    each time the user performs an action, 
        a new instance of this should be spawned
        this way all the user variables can be freshley pulled
    """
    
    

    def __init__(self,

                  *args, **kwargs):
        
        super().__init__(*args, **kwargs)
        

        
        self.logger.debug('Preparor.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def copy_cf_template(self, #start a new control file by copying the template
                  wdir,
                  cf_fp=None,
                  logger=None
                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('copy_cf_template')
        
        if cf_fp is None: cf_fp = os.path.join(wdir, 'CanFlood_%s.txt'%self.tag)
        #=======================================================================
        # copy control file template
        #=======================================================================
        
        
        #get the default template from the program files
        cf_src = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 '_pars/CanFlood_control_01.txt')
        
        assert os.path.exists(cf_src)
        
        
        #get new file name
        
        
        #see if this exists
        if os.path.exists(cf_fp):
            msg = 'generated control file already exists. overwrite=%s \n     %s'%(
                self.overwrite, cf_fp)
            if self.overwrite:
                log.warning(msg)
            else:
                raise Error(msg)
            
            
        #copy over the default template
        shutil.copyfile(cf_src, cf_fp)
        
        log.debug('copied control file from\n    %s to \n    %s'%(
            cf_src, cf_fp))
        
        self.cf_fp = cf_fp
        
        return cf_fp

    def upd_cf_first(self, #seting initial values to the control file
                     scenarioName=None,
                     curves_fp=None,
                     ):
        """
        todo: change this to accept kwargs
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if scenarioName is None: scenarioName=self.tag
        
        #get new parameters
        note_str = '#control file template created from \'upd_cf_first\' on  %s'%(
            datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S'))
        
        
        new_pars_d = {'parameters':({'name':scenarioName},note_str)}
        
        #add curves
        if isinstance(curves_fp, str):
            new_pars_d['dmg_fps'] = ({'curves':curves_fp},)
        
        
        return self.update_cf(new_pars_d)
        
    def finv_to_csv(self, #convert the finv to csv
                    vlay,
                    felv='datum', #should probabl just leave this if none
                    cid=None, tag=None,
                    logger=None,
                    ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('finv_to_csv')
        
        if cid is None: cid=self.cid
        if tag is None: tag=self.tag
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert os.path.exists(self.cf_fp), 'bad cf_fp: %s'%self.cf_fp
        assert vlay.crs()==self.qproj.crs(), 'finv CRS (%s) does not match projects (%s)'%(
            vlay.crs(), self.qproj.crs())
        
        
        #check cid
        assert isinstance(cid, str)
        if cid == '':
            raise Error('must specify a cid') 
        if cid in self.invalid_cids:
            raise Error('user selected invalid cid \'%s\''%cid)  
        
        
        assert cid in [field.name() for field in vlay.fields()]

        #=======================================================================
        # #extract data
        #=======================================================================
        
        log.info('extracting data on \'%s\' w/ %i feats'%(
            vlay.name(), vlay.dataProvider().featureCount()))
                
        df = vlay_get_fdf(vlay, feedback=self.feedback)
          
        #drop geometery indexes
        for gindx in self.invalid_cids:   
            df = df.drop(gindx, axis=1, errors='ignore')
            
        #more cid checks
        if not cid in df.columns:
            raise Error('cid not found in finv_df')
        
        assert df[cid].is_unique
        assert 'int' in df[cid].dtypes.name, 'cid \'%s\' bad type'%cid
        
        self.feedback.upd_prog(50)
        
        #=======================================================================
        # #write to file
        #=======================================================================
        out_fp = os.path.join(self.out_dir, get_valid_filename('finv_%s_%s.csv'%(self.tag, vlay.name())))
        
        #see if this exists
        if os.path.exists(out_fp):
            msg = 'generated finv.csv already exists. overwrite=%s \n     %s'%(
                self.overwrite, out_fp)
            if self.overwrite:
                log.warning(msg)
            else:
                raise Error(msg)
            
            
        df.to_csv(out_fp, index=False)  
        
        log.info("inventory csv written to file:\n    %s"%out_fp)
        
        self.feedback.upd_prog(80)
        #=======================================================================
        # write to control file
        #=======================================================================
        assert os.path.exists(out_fp)
        
        self.update_cf(
            {
            'dmg_fps':(
                {'finv':out_fp}, 
                '#\'finv\' file path set from BuildDialog.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                ),
            'parameters':(
                {'cid':str(cid),
                 'felv':felv},
                )
             },

            )
        
        self.feedback.upd_prog(99)
        
        return out_fp
            
    
    def to_finv(self, #clean a raw vlay an add some finv colums
                in_vlay,
                drop_colns=['ogc_fid', 'fid'], #optional columns to drop from df
                new_data = {},
                newLayname = None,
                ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('to_finv')
        if newLayname is None: newLayname = 'finv_%s'%in_vlay.name()
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(in_vlay, QgsVectorLayer)

 
        dp = in_vlay.dataProvider()
        
        log.info('on %s w/ %i feats and %i new colums'%(in_vlay.name(), dp.featureCount(), len(new_data)))
        
        self.feedback.upd_prog(20)
        #=======================================================================
        # extract data
        #=======================================================================
        df_raw = vlay_get_fdf(in_vlay, logger=log)
        geo_d = vlay_get_fdata(in_vlay, geo_obj=True, logger=log)
        
        self.feedback.upd_prog(50)
        
        #=======================================================================
        # clean
        #=======================================================================
        #drop specified columns
        df0 = df_raw.drop(drop_colns,axis=1, errors='ignore')
        
        #convert empty strings to null
        df1 = df0.replace(to_replace='', value=np.nan)
        log.info('replaced %i (of %i) null values'%(df1.isna().sum().sum(), df1.size))

        #drop empty fields
        df2 = df1.dropna(axis=1, how='all')
        log.info('dropped %i empty columns'%(len(df1.columns) - len(df2.columns)))
        
        self.feedback.upd_prog(60)

        #=======================================================================
        # add fields
        #=======================================================================
        #build the new data
        log.info('adding field data:\n    %s'%new_data)

        #join the two
        res_df = pd.DataFrame(index=df_raw.index, data=new_data).join(df2)


        self.feedback.upd_prog(70)
        #=======================================================================
        # reconstruct layer
        #=======================================================================
        finv_vlay = self.vlay_new_df2(res_df,  geo_d=geo_d, crs=in_vlay.crs(),
                                logger=log,
                                layname = newLayname)
        
        #=======================================================================
        # wrap
        #=======================================================================
        fcnt = finv_vlay.dataProvider().featureCount()
        assert fcnt == dp.featureCount()
        
        log.info('finished w/ \'%s\' w/ %i feats'%(finv_vlay.name(), fcnt))
        
        self.feedback.upd_prog(99)
        return  finv_vlay
    
    def build_nest_data(self, #convert data to nest like
                        nestID = 0, 
                        d_raw = {'scale':1.0, 'elv':0.0, 'tag':None, 'cap':None},
                        ):
        
        if len(d_raw)==0: return dict()
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(nestID, int)
        
        miss_l = set(d_raw.keys()).difference(['scale', 'elv', 'tag', 'cap'])
        assert len(miss_l)==0, 'got some unrecognzied'
        
        
        #=======================================================================
        # prep input data
        #=======================================================================
        d = dict()
        for kRaw, vRaw in d_raw.items():
            if vRaw is None:
                if kRaw == 'tag':
                    v = '' #get the right data type for empty tag fields?
                else:
                    v = np.nan
            else:
                v = vRaw
                
            d['f%i_%s'%(nestID, kRaw)] = v
            
        return d
 













                

 
    
    
    

    

            
        