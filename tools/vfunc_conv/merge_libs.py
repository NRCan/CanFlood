'''
Created on Jun. 8, 2021

@author: cefect

merge vfunc .xls into one
'''

#==============================================================================
# imports------------
#==============================================================================
import os, datetime
start =  datetime.datetime.now()
import numpy as np
import pandas as pd

from hlpr.basic import view, force_open_dir
from hlpr.exceptions import Error

from vfunc_conv.vcoms import VfConv

class VfMerge(VfConv):
    
    def load_all(self,
                 fp_l, #list of filepaths to load
                 base_dir=None,
                 ):
        log = self.logger.getChild('load_all')
        lib_d = dict()
        
        for fp in fp_l:
            if not base_dir is  None: fp = os.path.join(base_dir, fp)
            lib_d[os.path.basename(fp)] = self.load_data(fp)
            
        log.info('loaded %i'%len(lib_d))
        
        return lib_d
    
    def run(self, #merge a set of curve libraries
            lib_raw, #{libraryName:curveLibrary}
            overlaps='raise', #how to handle overlaps in libraries
            ): 
        log = self.logger.getChild('run')
        
        keys_d = {k:list(v.keys()) for k,v in lib_raw.items()}
        for k,v in keys_d.items():
            print('%s    %i:%s'%(k, len(v), v))
            
        cnt_d = {k:len(v) for k,v in keys_d.items()}
        
        #=======================================================================
        # remove summary sheets
        #=======================================================================
        lib = dict()
        curve_keys =  set()
        for k,clib_raw in lib_raw.items():
            lib[k] = {k:v for k,v in clib_raw.items() if not k.startswith('_')} #remove summary sheet
            
            #check there are no duplicates
            l = set(lib[k].keys()).intersection(curve_keys)
            if not len(l)==0:
                log.warning('got %i overlaps on %s: \n    %s'%(len(l), k, l))
                if overlaps=='warn':
                    continue
                elif overlaps=='raise':
                    raise IOError()
                else:
                    raise Error('unrecognized overlaps key')
 
            
            #append
            curve_keys.update(set(lib[k].keys()))
        
            
        #=======================================================================
        # compress into 1
        #=======================================================================
        mlib = dict()
        for k,clib_raw in lib.items():
            mlib.update({k:v for k,v in clib_raw.items() if not k.startswith('_')}) #remove summary sheet
            
        log.info('merged to %i from \n    %s'%(len(mlib), cnt_d))
        
        #=======================================================================
        # fix some issues
        #=======================================================================
        mlib1 = dict()
        for k, df_raw in mlib.items():
            dd_d, meta_d = self._get_split(df_raw)
            
            #remove key row
            del meta_d['exposure']
            
            #impact_units
            if not 'impact_units' in meta_d.keys():
                meta_d['impact_units'] = {'$/m2':'$CAD'}[meta_d['impact_var']]
                
                
            #ressemble
            meta_d['exposure']='impact' #replace key row
            crv_d = {**meta_d, **dd_d}
            
            """
            for k,v in crv_d.items():
                print(k,v)
            """
                
            self.check_crvd(crv_d)

            mlib1[k] = crv_d
            
        #=======================================================================
        # convert
        #=======================================================================
        rd = dict()
        for k, sd in mlib1.items():
            """need this to ensure index is formatted for plotters"""
            df =  pd.Series(sd).to_frame().reset_index(drop=False)
            df.columns = range(df.shape[1]) #reset the column names
            rd[k] = df
        
        #=======================================================================
        # add summary
        #=======================================================================
        #get the summary tab first
        try:
            smry_df = self._get_smry(mlib1.copy(), clib_fmt_df=False, set_index=True)
            mlib = { **{'_smry':smry_df},
                 **mlib,
                }
        except Exception as e:
            log.warning('failed to get sumary tab w/ \n    %s'%e)
         
        return rd
            
            

    

if __name__=='__main__':
    
    wrkr = VfMerge(out_dir=r'C:\LS\02_WORK\NHC\202012_Kent\03_SOFT\_py\_out\cf\vf_merge')
    
    lib_d = wrkr.load_all(
        fp_l=['curves_CFcc_20200608_nrp.xls','curves_CFcc_20200608_ag.xls'],
        base_dir=r'C:\LS\02_WORK\NHC\202012_Kent\04_CALC\risk\curves')
    
    mlib = wrkr.run(lib_d, overlaps='warn')
    
    wrkr.output(mlib, ofn='curves_merge_%s.xls'%datetime.datetime.now().strftime('%Y-%m-%d'))
    
    #===========================================================================
    # wrap
    #===========================================================================
    #force_open_dir(wrkr.out_dir)
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)
    