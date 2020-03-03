'''
Created on Feb. 9, 2020

@author: cefect

likelihood sampler
sampling overlapping polygons at inventory points to calculate combined likelihoods
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


#Qgis imports
from qgis.core import QgsVectorLayer, QgsRasterLayer, QgsFeatureRequest, QgsProject

#==============================================================================
# custom imports
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
    
    from hlpr.plug import QprojPlug as base_class

#plugin runs
else:

    from hlpr.exceptions import QError as Error

from hlpr.Q import *
from hlpr.basic import *

#==============================================================================
# classes-------------
#==============================================================================
class LikeSampler(Qcoms):
    """
    sampling failure likelihood polygons with the inventory
    """
    cid = 'not_set'
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.resname = 'exlikes_%s'%self.tag
        
    def load_layers(self, #load data to project (for standalone runs)
                    lpol_fp_d, finv_fp,
                    providerLib='ogr'
                    ):
        
        """
        special input loader for standalone runs
        Im assuming for the plugin these layers will be loaded already
        
        finv_fp, lpol_fp_d
        
        """
        log = self.logger.getChild('load_layers')
        #======================================================================
        # load rasters
        #======================================================================
        lpol_d = dict()
        
        for ename, fp in lpol_fp_d.items():
            
            vlay = self.load_vlay(fp, logger=log, providerLib=providerLib)
            
            #add it in
            lpol_d[ename] = vlay
            
        #======================================================================
        # load finv vector layer
        #======================================================================
        finv_vlay = self.load_vlay(finv_fp, logger=log, providerLib=providerLib)

        #======================================================================
        # wrap
        #======================================================================
        log.info('finished')
        return lpol_d, finv_vlay
            
    def run(self,
            finv, #inventory layer
            lpol_d, #{event name: likelihood polygon layer}
            cid = 'xid', #index field name on finv
            lfield = 'p_fail', #field with likelihhood value
            ):
        
        log = self.logger.getChild('run')

        self.cid = cid #set for other methods
        #======================================================================
        # #check/load the data
        #======================================================================
        #check lpols
        for ename, vlay in lpol_d.items():
            if not isinstance(vlay, QgsVectorLayer):
                raise Error('bad type on %s layer: %s'%(ename, type(vlay)))
            assert 'Polygon' in QgsWkbTypes().displayString(vlay.wkbType())
            assert lfield in [field.name() for field in vlay.fields()]
            assert vlay.isValid()
            
            #==================================================================
            # #check values
            #==================================================================
            
            chk_df = vlay_get_fdf(vlay, logger=log)
            chk_ser = chk_df.loc[:, lfield]
            #check fo rnulls
            boolidx = chk_ser.isna()
            assert not boolidx.any(), 'got nulls on %s'%ename
        
            #if 0<fval<1
            boolidx = np.logical_and( #checking for fails
                chk_ser <0,
                chk_ser >1,)
            
            if boolidx.any():
                raise Error('%s.%s got %i (of %i) values out of range: \n%s'%(
                    ename,lfield, boolidx.sum(), len(boolidx), chk_ser[boolidx]))
            
        #check vlay
        assert isinstance(finv, QgsVectorLayer), 'bad type on finv'
        assert finv.isValid(), 'invalid finv'
        assert cid in  [field.name() for field in finv.fields()], 'missing cid %s'%cid
        
            
        #======================================================================
        # slice data by project aoi
        #======================================================================
        
        
        #======================================================================
        # prep finv
        #======================================================================
        #clean out finv
        fc_vlay = self.deletecolumn(finv, [cid], invert=True, layname='fclean')
        
        self.fc_vlay = fc_vlay #set this for vectorize()
        #get cid list
        fdf = vlay_get_fdf(fc_vlay, logger=log)
        cid_l = fdf[cid].tolist()
        
        
        #======================================================================
        # sample values
        #======================================================================
        log.info('sampling %i lpols w/ %i finvs'%(len(lpol_d), len(cid_l)))
        en_c_sval_d = dict() #container for samples {event name: sample data}
        for ename, lp_vlay in lpol_d.items():
            log = self.logger.getChild('run.%s'%ename)
            
            """
            todo: remove any features w/ zero value
            """
            svlay, new_fns, jcnt = self.joinattributesbylocation(fc_vlay, lp_vlay, [lfield],
                                                  method=0, #one-to-many
                                                  expect_j_overlap=True,
                                                  )
            #extract raw sampling data
            sdf = vlay_get_fdf(svlay, logger=log)
            
            #==================================================================
            # #do some checks
            #=================================================================
            #check columns
            miss_l = set(sdf.columns).symmetric_difference([lfield, cid])
            assert len(miss_l) == 0, 'bad columns on the reuslts'
            #make sure all the cids made it
            miss_l = set(cid_l).difference(sdf[cid].unique().tolist())
            assert len(miss_l) == 0, 'failed to get %i assets in the smaple'%len(miss_l)
            

            #==================================================================
            # #pivot this out to unique cids
            #==================================================================
            """
            #this works only when all the failure probabilities are unique
            lp_vlay.dataProvider().featureCount()
            sdf.pivot(index=cid, columns=lfield, values=lfield)"""
            
            #loop and build for each cid
            """not very efficient... but cant think of a better way"""
            cid_samp_d = dict() #container for sampling results
            for cval in cid_l:
                #get this data
                boolidx = sdf[cid] == cval
                cid_samp_d[cval] = sdf.drop(cid, axis=1)[boolidx].iloc[:, 0].dropna().tolist()
                
            #wrap event loop
            en_c_sval_d[ename] = cid_samp_d #add to reuslts
            log.debug('collected sample values on %i assets'%len(cid_samp_d))
        
        
        
        #======================================================================
        # resolve union events
        #======================================================================
        log = self.logger.getChild('run')
        log.info('collected sample values for %i events and %i assets'%(
            len(en_c_sval_d), len(cid_l)))
        
        #build results contqainer
        #res_df = pd.DataFrame(index = fdf[cid], columns = en_c_sval_d.keys())
        res_df = None

        
        #loop and resolve
        log.debug('resolving %i events'%len(en_c_sval_d))
        for ename, cid_samp_d in en_c_sval_d.items():
            log.debug('resolving \"%s\''%ename)
            
            #loop through each asset and resolve sample values
            cid_res_d = dict() #harmonized likelihood results
            for cval, pvals in cid_samp_d.items():
                #log = self.logger.getChild('run.%s.%s'%(ename, cval))
                #simple unitaries
                if len(pvals) == 1:
                    cid_res_d[cval] = pvals[0]
                    
                #multi value
                else:
                    
                    #calc union probability for multi predictions
                    cid_res_d[cval] = self.union_probabilities(pvals, logger=log)
                    
                #wrap union loop
                #log.debug('%s.%s got p_unioin = %.2f'%(ename, cval, cid_res_d[cval]))
            
                
            #update results
            res_ser = pd.Series(cid_res_d, name=ename)
            if res_df is None:
                res_df = res_ser.to_frame()
                res_df.index.name = cid
            else:
                assert np.array_equal(res_df.index, res_ser.index), 'index mmismatch'
                res_df = res_df.join(res_ser)
            

        #======================================================================
        # post checks
        #======================================================================
        log = self.logger.getChild('run')
        miss_l = set(lpol_d.keys()).symmetric_difference(res_df.columns)
        assert len(miss_l) == 0, 'failed to match columns to events'
        
        assert res_df.max().max() <=1.0, 'bad max'
        assert res_df.min().min() >= 0.0, 'bad min'
        #======================================================================
        # wrap
        #======================================================================
        
        log.info('finished w/ %s'%str(res_df.shape))
        
        return res_df
    
    def union_probabilities(self,
                            probs,
                            logger = None,
                            ):
        """
        calculating the union probability of multiple events using the exclusion principle
        
        https://en.wikipedia.org/wiki/Inclusion%E2%80%93exclusion_principle#In_probability
        
        from Walter
    
        Parameters
        ----------
        probs_list : Python 1d list
            A list of probabilities between 0 and 1 with len() less than 23
            After 23, the memory consumption gets huge. 23 items uses ~1.2gb of ram. 
    
        Returns
        -------
        total_prob : float64
            Total probability 
            
        """
        if logger is None: logger=self.logger
        #log = self.logger.getChild('union_probabilities')
        #======================================================================
        # prefilter
        #======================================================================
        #guranteed
        if max(probs) == 1.0:
            #log.debug('passed a probability with 1.0... returning this')
            return 1.0
        
        #clean out zeros
        if 0.0 in probs:
            probs = [x for x in probs if not x==0]
        
        
        #===========================================================================
        # do some checks
        #===========================================================================
        
        assert (len(probs) < 20), "list too long"
        assert (all(map(lambda x: x < 1 and x > 0, probs))), 'probabilities out of range'
        
        #===========================================================================
        # loop and add (or subtract) joint probabliities
        #===========================================================================
        #log.debug('calc total_prob for %i probs: %s'%(len(probs), probs))
        total_prob = 0
        for r in range(1, len(probs) + 1):
            #log.debug('for r %i total_prob = %.2f'%(r, total_prob))
            combs = itertools.combinations(probs, r)
            total_prob += ((-1) ** (r + 1)) * sum([np.prod(items) for items in combs])
            
        #log.debug('finished in %i loops '%len(probs))
        
        assert total_prob <1 and total_prob > 0, 'bad result'
    
        return total_prob
    
    def vectorize(self, #map results back onto the finv geometry 
                  res_df):
        
        log = self.logger.getChild('vectorize')
        
        #======================================================================
        # extract data from finv
        #======================================================================
        vlay = self.fc_vlay
        
        #get geometry
        geo_d = vlay_get_fdata(vlay, geo_obj=True)
        
        #get key conversion
        fid_cid_d = vlay_get_fdata(vlay, fieldn=self.cid, logger=log)
        
        #convert geo
        cid_geo_d = {fid_cid_d[k]:v for k, v in geo_d.items()}
        
        #======================================================================
        # build the layer
        #======================================================================
        assert res_df.index.name == self.cid, 'bad index on res_df'
        
        
        res_vlay = vlay_new_df(res_df, vlay.crs(), geo_d = cid_geo_d, 
                               layname = self.resname,
                                logger=log)
        
        return res_vlay
    
    def check(self):
        pass #placeholder
    
    def write_res(self, res_df,**kwargs):
        return self.output_df(res_df, self.resname,**kwargs)
    
    def upd_cf(self, cf_fp): #configured control file updater
        return self.update_cf(
            {'risk_fps':(
                {'exlikes':self.out_fp}, 
                '#\'exlikes\' file path set from lisamp.py at %s'%(datetime.datetime.now().strftime('%Y-%m-%d %H.%M.%S')),
                )
             },
            cf_fp = cf_fp
            )
        


if __name__ =="__main__": 
    
    out_dir = os.path.join(os.getcwd(), 'lisamp')
    
    """
    l = [0.0, 0.0, 1.0]
    
    l.remove(0.0)
    """

    #==========================================================================
    # dev data
    #==========================================================================
    data_dir = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\build\lisamp'
    
    finv_fp = os.path.join(data_dir, r'finv_cT2.gpkg')
    
    lpol_fn_d = {'Gld_10e2_fail_cT1':r'exposure_likes_10e2_cT1_20200209.gpkg', 
              'Gld_20e1_fail_cT1':r'exposure_likes_20e1_cT1_20200209.gpkg'}
    
    
    lpol_fp_d = {k:os.path.join(data_dir, v) for k, v in lpol_fn_d.items()}
    
    #==========================================================================
    # load the data
    #==========================================================================
    
    wrkr = LikeSampler(mod_logger, tag='lisamp_testr', feedback=QgsProcessingFeedback())
    wrkr.ini_standalone(out_dir=out_dir) #setup for a standalone run
    
    lpol_d, finv_vlay = wrkr.load_layers(lpol_fp_d, finv_fp)
    
    #==========================================================================
    # execute
    #==========================================================================
    res_df = wrkr.run(finv_vlay, lpol_d)
    
    #convet to a vector
    res_vlay = wrkr.vectorize(res_df)
    
    
    wrkr.check()
    
    #==========================================================================
    # save results
    #==========================================================================
    vlay_write(res_vlay, 
               os.path.join(wrkr.out_dir, '%s.gpkg'%wrkr.resname),
               overwrite=True, logger=mod_logger)
    
    outfp = wrkr.write_res(res_df)
    
    wrkr.upd_cf(os.path.join(data_dir, 'CanFlood_scenario1.txt'))

    force_open_dir(os.getcwd())

    print('finished')
    
    
    
    
    

