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
from hlpr.basic import get_valid_filename, view

from model.modcom import Model #for data checks

#==============================================================================
# functions-------------------
#==============================================================================
class Preparor(Model, Qcoms):


    def __init__(self,**kwargs):
        
        
        super().__init__(**kwargs)

        self.logger.debug('Preparor.__init__ w/ feedback \'%s\''%type(self.feedback).__name__)
        
        
    def copy_cf_template(self, #start a new control file by copying the template
                  wdir=None, #optional build path to copy to
                  cf_fp=None, #path to copy to
                  
                  cf_src = None, #template fiilepath
                  logger=None
                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('copy_cf_template')


        
        
        #=======================================================================
        # #get the default template from the program files
        #=======================================================================
        if cf_src is None:
            cf_src = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     '_pars/CanFlood_control_01.txt')
        
        assert os.path.exists(cf_src)
        
        
        #=======================================================================
        # #get new file name
        #=======================================================================
        if cf_fp is None: 
            if wdir is None: 
                wdir=self.out_dir
            assert os.path.exists(wdir)
            cf_fp = os.path.join(wdir, 'CanFlood_%s.txt'%self.tag)
            
        if os.path.exists(cf_fp):assert self.overwrite
            
        #=======================================================================
        # copy control file template
        #=======================================================================
        #copy over the default template
        shutil.copyfile(cf_src, cf_fp)
        
        log.debug('copied control file from\n    %s to \n    %s'%(
            cf_src, cf_fp))
        
        self.cf_fp = cf_fp
        
        return cf_fp

    def upd_cf_first(self, #seting initial values to the control file
                     scenarioName=None,
                     curves_fp=None,
                     **kwargs
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
        
        
        new_pars_d = {'parameters':(
            dict(**{'name':scenarioName}, **kwargs),note_str)}
        
        #add curves
        if isinstance(curves_fp, str):
            new_pars_d['dmg_fps'] = ({'curves':curves_fp},)
            

            
        
        
        return self.set_cf_pars(new_pars_d)
        
    def finv_to_csv(self, #convert the finv to csv
                    vlay,
                    felv='datum', #should probabl just leave this if none
                    cid=None, tag=None,
                    logger=None, write=True,
                    ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('finv_to_csv')
        
        if cid is None: cid=self.cid
        if tag is None: tag=self.tag
        self.felv = felv
        
        log.debug('on %s'%vlay.name())
        #=======================================================================
        # prechecks
        #=======================================================================
        
        assert vlay.crs()==self.qproj.crs(), 'finv CRS (%s) does not match projects (%s)'%(
            vlay.crs(), self.qproj.crs())
        
        
        #check cid
        assert isinstance(cid, str)
        if cid == '':
            raise Error('must specify a cid') 
        if cid in self.invalid_cids:
            raise Error('user selected invalid cid \'%s\''%cid)  
        
        
        assert cid in [field.name() for field in vlay.fields()], '%s missing cid \'%s\''%(vlay.name(), cid)
        
         
        
        #label checks
        assert isinstance(tag, str)

        #=======================================================================
        # #extract data
        #=======================================================================
        
        log.info('extracting data on \'%s\' w/ %i feats'%(
            vlay.name(), vlay.dataProvider().featureCount()))
                
        df = vlay_get_fdf(vlay, feedback=self.feedback)
        
        """
        view(df.dtypes)
        """
        #check index nulls
        bx = df[cid].isna()
        assert not bx.any(), '%s got %i (of %i) nulls on %s'%(vlay.name(), bx.sum(), len(bx), cid)
          
        #drop geometery indexes (e.g., fid)
        for gindx in self.invalid_cids:   
            df = df.drop(gindx, axis=1, errors='ignore')
            
        #force type on index
        try:
            df.loc[:, cid] = df[cid].astype(np.int32)
        except Exception as e:
            raise Error('failed to typeset cid index  \'%s\' w/ int32 \n%s'%(cid, e))
        df = df.set_index(cid, drop=True)
        
        """
        df.index
        """
        
        #drop empty columns
        boolcol = df.isna().all(axis=0)
        if boolcol.any():
            df = df.loc[:, ~boolcol]
            log.warning('%s dropping %i (of %i) empty fields'%(tag, boolcol.sum(), len(boolcol)))
            
        
            
        #=======================================================================
        # post checks
        #=======================================================================
        self.check_finv(df, cid=cid, logger=log)
        self.feedback.upd_prog(50)
        
        if not write: 
            """mostly a skip for testing"""

            return df
        
        #=======================================================================
        # #write to file
        #=======================================================================
        out_fp = os.path.join(self.out_dir, 
                              get_valid_filename('finv_%s_%i_%s.csv'%(tag, len(df), vlay.name().replace('finv_', ''))))
        
        #see if this exists
        if os.path.exists(out_fp):
            msg = 'generated finv.csv already exists. overwrite=%s \n     %s'%(
                self.overwrite, out_fp)
            if self.overwrite:
                log.warning(msg)
            else:
                raise Error(msg)
            
            
        df.to_csv(out_fp, index=True)  
        
        log.info("inventory csv written to file:\n    %s"%out_fp)
        assert os.path.exists(out_fp)
        self.feedback.upd_prog(80)
        #=======================================================================
        # write to control file
        #=======================================================================
        self.upd_cf_finv(out_fp)
        
        self.feedback.upd_prog(99)
        
        
        return df
    
    def upd_cf_finv(self, out_fp):
        
        assert os.path.exists(self.cf_fp), 'bad cf_fp: %s'%self.cf_fp
        
        #=======================================================================
        # """
        # writing the filepath to the vector layer wont work...
        #     often we're working with memory layers
        #     the transition from spatial to non-spatial and back to spatial losses these connections
        # """
        # 
        #=======================================================================
        self.set_cf_pars(
            {
            'dmg_fps':(
                {'finv':out_fp}, 
                '#\'finv\' file path set from prepr.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                ),
            'parameters':(
                {'cid':self.cid,
                 'felv':self.felv},
                ),

             },

            )
    
 
            
    
    def to_finv(self, #clean a raw vlay an add some finv colums
                in_vlay,
                drop_colns=['ogc_fid', 'fid'], #optional columns to drop from df
                new_data = {},
                newLayname = None,
                logger=None,
                ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('to_finv')
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
        res_df = df2.join(pd.DataFrame(index=df_raw.index, data=new_data))


        self.feedback.upd_prog(70)
        
        #=======================================================================
        # chekc data
        #=======================================================================
        """" no? not for this intermediate function?
        self.check_finv()
        
        """
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
                        logger=None,
                        ):
        
        if len(d_raw)==0: return dict()
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(nestID, int)
        
        miss_l = set(d_raw.keys()).difference(['scale', 'elv', 'tag', 'cap'])
        assert len(miss_l)==0, 'got some unrecognzied'
        
        
        #chekc mandatory keys
        miss_l = set(['scale', 'elv']).difference(d_raw.keys())
        assert len(miss_l)==0, 'missing mandatory inventory columns: %s'%miss_l
        
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
 













                

 
    
    
    

    

            
        