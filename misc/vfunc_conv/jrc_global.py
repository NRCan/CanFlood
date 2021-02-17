'''
Created on Feb. 9, 2021

@author: cefect
'''
#===============================================================================
# imports
#===============================================================================
import os, datetime
start =  datetime.datetime.now()
import pandas as pd
import numpy as np
from pandas import IndexSlice as idx
from hlpr.basic import view, force_open_dir

from vfunc_conv.vcoms import VfConv
#from model.modcom import DFunc

mod_name = 'misc.jrc_global'
today_str = datetime.datetime.today().strftime('%Y%m%d')

class JRConv(VfConv):
    
    def __init__(self,
                 libName = 'Huzinga_2017',
                 prec=5, #precision
                 **kwargs):
        
        self.libName = libName
        
        
        super().__init__(
                 prec=prec,
                 **kwargs) #initilzie teh baseclass
    
    def load(self,
                 fp = r'C:\LS\02_WORK\IBI\202011_CanFlood\04_CALC\vfunc\lib\Huzinga_2017\copy_of_global_flood_depth-damage_functions__30102017.xlsx',
                 
                ):
    
        #===============================================================================
        # inputs
        #===============================================================================
        dx_raw = pd.read_excel(fp, sheet_name = 'Damage functions', header=[1,2], index_col=[0,1])
        
        
        
        #clean it
        df = dx_raw.drop('Standard deviation', axis=1, level=0)
        dxind = df.droplevel(level=0, axis=1)
        dxind.index = dxind.index.set_names(['cat', 'depth_m'])
        
        #get our series
        boolcol = dxind.columns.str.contains('North AMERICA')
        """
        no Transport or Infrastructure curves for North America
        """
        dxind = dxind.loc[:, boolcol]
        #handle nulls
        
        dxind = dxind.replace({'-':np.nan}).dropna(axis=0, how='any')
        
        
        self.dxind = dxind
        
        
        
        return self.dxind
    
    
    def convert(self,
                dxind=None,
                
                metac_d = {
                      'desc':'JRC Global curves',
                      'location':'USA',
                      'date':'2010',
                      'source':'(Huizinga et al. 2017)',
                      'impact_var':'loss',
                      'impact_units':'pct',
                      'exposure_var':'flood depth',
                      'exposure_units':'m',
                      'scale_var':'maximum damage (national average)',
                      'scale_units':'pct',
                          }, 
                                      
                ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if dxind is None: dxind=self.dxind
        
        #=======================================================================
        # setup meta
        #=======================================================================
        crve_d = self.crve_d.copy() #start with a copy
        
        
        crve_d['file_conversion']='CanFlood.%s_%s'%(mod_name, today_str)
        
        #check keys
        miss_l = set(metac_d.keys()).difference(crve_d.keys())
        assert len(miss_l)==0, 'requesting new keys: %s'%miss_l

        #crve_d = {**metac_d, **crve_d}
        crve_d.update(metac_d) #preserves order
        """
        crve_d.keys()
        """
        
        #check it
        assert list(crve_d.keys())[-1]=='exposure', 'need last entry to be eexposure'
        #=======================================================================
        # curve loop
        #=======================================================================
        cLib_d = dict()
        #loop and collect
        for cval, cdf_raw in dxind.groupby('cat', axis=0, level=0):
            #===================================================================
            # get the tag
            #===================================================================
            tag = cval.strip().replace(' ','')
            
            for k,v in self.tag_cln_d.items():
                tag = tag.replace(k, v).strip()
            
            #===================================================================
            # depth-damage
            #===================================================================
            ddf = cdf_raw.droplevel(level=0, axis=0).astype(np.float).round(self.prec)
            dd_d = ddf.iloc[:,0].to_dict()
            
            #===================================================================
            # meta
            #===================================================================
            dcurve_d = crve_d.copy()
            dcurve_d['tag'] = tag
            
            #assemble
            dcurve_d = {**dcurve_d, **dd_d}

            self.check_crvd(dcurve_d)
            
            cLib_d[tag] = dcurve_d
            
        #=======================================================================
        # convert and summarize
        #=======================================================================
        rd = dict()
        for k, sd in cLib_d.items():
            """need this to ensure index is formatted for plotters"""
            df =  pd.Series(sd).to_frame().reset_index(drop=False)
            df.columns = range(df.shape[1]) #reset the column names
            rd[k] = df
        
        #get the summary tab first
        smry_df = self._get_smry(cLib_d.copy())
        rd = { **{'_smry':smry_df},
             **rd,
            }
        
        self.res_d = rd.copy()
        
        return self.res_d
 


                


"""
view(dxind)
view(dx_raw)
"""




if __name__=='__main__':
    out_dir = r'C:\LS\03_TOOLS\CanFlood\outs\misc\vfunc_conv'
    
    wrkr = JRConv(out_dir=out_dir, figsize = (10,10))
    wrkr.load()
    cLib_d = wrkr.convert()
    
    wrkr.output(cLib_d)
    
    #===========================================================================
    # plots
    #===========================================================================

    fig = wrkr.plotAll(cLib_d, title=wrkr.libName,lib_as_df=True)
    wrkr.output_fig(fig)
    
    #===========================================================================
    # wrap
    #===========================================================================
    force_open_dir(wrkr.out_dir)
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)