'''
Created on Feb. 9, 2020

@author: cefect
'''
import os
from qgis.core import QgsWkbTypes
from hp import Error

import pandas as pd

class LiSamp(object):
    
    def run(self,
            lpol_vlay_l, #set of likelihood polygons to sample.
            enames_d, # {lpol_vlay_l.name(): event name} from user
            finv, #inventory layer
            control_fp = '', #control file path
            cid = 'xid', #index field name on finv
            ):
        
        """
        #======================================================================
        # dev inputs
        #======================================================================
        
        lpol_vlay_l
             exposure_likes_10e2_cT1_20200209.gpkg, exposure_likes_20e1_cT1_20200209.gpkg
             
        enames_d
             {'exposure_likes_10e2_cT1_20200209':'Gld_10e2_fail_cT1', 'exposure_likes_20e1_cT1_20200209':'Gld_20e1_fail_cT1'}
             
        finv:
            finv_icomp_cT1.gpkg
        
        """
        
        
        
        #======================================================================
        # #load the data
        #======================================================================
                
        #get index from finv
        findex
        
        
        
        #======================================================================
        # #check the data
        #======================================================================
        for vlay in lpol_vlay_l:
            assert 'Polygon' in QgsWkbTypes().displayString(vlay.wkbType())
            
            #ask user what field ot use for likelihood values
            
            
            #check if layer has requested field
            
            #check if 0<fval<1
            
            
        #======================================================================
        # slice data by project aoi
        #======================================================================
        
        
        #======================================================================
        # sample values
        #======================================================================
        #sample raster value at each inventory point (one-to-many)
        
        raw_samp_d = dict() #container for samples {event name: sample data}
        for vlay in lpol_vlay_l:
            raw_samp_d[enames_d[vlay.name()]] = self.sample(vlay, finv)
        
            
        #======================================================================
        # resolve union events
        #======================================================================
        res_df = pd.DataFrame(index = findex, columns = enames_d.keys())
        for ename, sdf in raw_samp_d.items():
            #identify cids w/ single 'unitary' sample value
            
                     
            #collect sample values by cid for cids /w multiple samples
            """groupby or apply?"""
            
            #calc union probability for multi predictions
            """apply wuold be faster"""
            res_d = dict()
            for cid, probs in cid_sample_d.items():
                res_d[cid] = self.union_probabilities(probs)
                
            
            #add union resolved predictions back w/ unitaries
            
            #add series to results
            res_df.join(pd.Series(res_d, name=ename))
            
        #======================================================================
        # check outpust
        #======================================================================
        
        
        #======================================================================
        # wrap
        #======================================================================
        
        
        #save reuslts to file
        out_fp = self.output(res_df)
        
        if not os.path.exists(control_fp): pass
            #create control file template
            
        #update control file: exlikes = out_fp
        
        
        
        
        
        
    
    def union_probabilities(self,
                            probs,
                            ):
        """
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
        log = self.logger.getChild('union_probabilities')
        #===========================================================================
        # do some checks
        #===========================================================================
        
        assert (len(probs) < 20), "list too long"
        assert (all(map(lambda x: x <= 1 and x >= 0, probs))), 'probabilities out of range'
        
        #===========================================================================
        # loop and add (or subtract) joint probabliities
        #===========================================================================
        total_prob = 0
        for r in range(1, len(probs) + 1):
            log.debug('for r %i total_prob = %.2f'%(r, total_prob))
            combs = itertools.combinations(probs, r)
            total_prob += ((-1) ** (r + 1)) * sum([np.prod(items) for items in combs])
            
        log.debug('finished in %i loops '%len(probs))
    
    return total_prob