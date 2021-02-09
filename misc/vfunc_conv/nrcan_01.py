'''
Created on Feb. 8, 2021

@author: cefect

converting 'Depth Damage Functions.xlsx' to CanFlood format
'''
#===============================================================================
# imports---------
#===============================================================================
import os, datetime
start =  datetime.datetime.now()
print('start at %s'%start)

import pandas as pd
import numpy as np


from hlpr.logr import basic_logger
mod_logger = basic_logger() 
from hlpr.basic import force_open_dir, view

from misc.curvePlot import CurvePlotr
#from model.modcom import DFunc

mod_name = 'misc.nrcan_01'
today_str = datetime.datetime.today().strftime('%Y%m%d')


class NRconv(CurvePlotr):
    
    #===========================================================================
    # program pars
    #===========================================================================
    ft_m = 0.3048
    
    res_d = dict() #container of each library created
    #===========================================================================
    # data labels
    #===========================================================================
    #original Data
    od_source = 'Source'
    
    #meta
    od_year = 'Year'
    od_fplain = 'Region/Floodplain'
    
    
    #function
    od_typer = 'ResType'
    od_type2 = 'Type2'
    od_depthFt = 'Depth ft'
    od_dmgS = 'Damage St $'
    od_dmgC = 'Damage Cont $'
    
    
    def __init__(self,
                 logger=None,
                 out_dir=r'C:\LS\03_TOOLS\CanFlood\outs\misc\vfunc_conv',
                 **kwargs
                 ):
        
        
        if logger is None: logger=mod_logger
        
        super().__init__(logger=logger, out_dir=out_dir,
                         **kwargs) #initilzie teh baseclass
        

        #=======================================================================
        # containers
        #=======================================================================
        self.exp_colns = [self.od_typer, self.od_type2, self.od_depthFt, self.od_dmgS, 
                          self.od_dmgC,
                          self.od_year, self.od_fplain]
        

    def load(self,
            fp=r'C:\LS\03_TOOLS\CanFlood\ins\misc\vfunc_conv\Depth Damage Functions.xlsx',
            ):
        
            
        log = self.logger.getChild('load')
        log.info('loading from %s'%fp)
        #===========================================================================
        # load
        #===========================================================================
        df_raw = pd.read_excel(fp, sheet_name='Original Data', index_col=None)
        
        df = df_raw.dropna(axis=1, how='all').dropna(axis=0, how='all')
        
        log.info('got %s'%str(df.shape))
        
        #=======================================================================
        # check
        #=======================================================================
        miss_l = set(self.exp_colns).difference(df.columns)
        assert len(miss_l)==0, 'missing columsn: %s'%miss_l
        
        self.df_raw = df_raw
        self.df = df
        
        return df

    def convert(self, #get CanFlood format on Acres group
                      srch_str = 'Acres Ltd., Guidelines for analysis',
                      libName = 'Acres_1968', #name prefix for library
                      df_raw = None,
                      metac_d = {
                          'desc':'depth-damage curves for Residential, Commericial, and Inudstrial buildings in 1968 Galt, ON',
                          'scale_units':'none',
                          'impact_units':'$CAD',
                          'exposure_units':'m'
                          
                          }, #function level defaults
                      
                      lt_impactVal_d = {
                            'cont':'contents depreciated or repair value and some cleaning',
                            'strc':'building repair and restoration costs',
                            }
                              
                      ):
        
        log = self.logger.getChild('acres1968')
        if df_raw is None: df_raw= self.df
        
        


        
        #=======================================================================
        # clean1
        #=======================================================================
        df = self._get_source(srch_str, df_raw, logger=log).dropna(how='all', axis=1)
        
        
        #=======================================================================
        # conversions
        #=======================================================================
        #to meteres
        dcoln = 'depth_m'
        df[dcoln] = df[self.od_depthFt]*self.ft_m
        df = df.drop(self.od_depthFt, axis=1) #remove for reporting
        
        
        df.loc[:, self.od_year] = df[self.od_year].astype(int)
        
        #=======================================================================
        # get default meta----
        #=======================================================================
        #those we are NOT including in the meta reporting
        dd_colns = [self.od_typer, self.od_type2, dcoln,
                            self.od_dmgS, self.od_dmgC]
        noMeta_colns = set(dd_colns)
        
        crve_d = self.crve_d.copy() #start with a copy
        
        #=======================================================================
        # basics
        #=======================================================================
        crve_d['file_conversion']='CanFlood.%s_%s'%(mod_name, today_str)

        #crve_d = {**metac_d, **crve_d}
        crve_d.update(metac_d) #preserves order
        
        """
        crve_d.keys()
        """
        
        #=======================================================================
        # #get unique data from frame (renamed)
        #=======================================================================
        for mcoln, rcoln in {
            'date':self.od_year,
            'location':self.od_fplain,
            'source':self.od_source,
            }.items():
            
            #check its unique
            assert len(df[rcoln].unique())==1, '%s not unique: %s'%(rcoln, df[rcoln].duplicated(keep=False))
            
            
            crve_d[mcoln] = df[rcoln].unique()[0]
            
            noMeta_colns.add(rcoln) #make sure we dont report this one
        
        #=======================================================================
        # get remainders
        #=======================================================================
        self.noMeta_colns = noMeta_colns.copy() #set for smry
        """some of these are redundant... but including for completeness"""
        
        for coln, cser in df.loc[:, ~df.columns.isin(noMeta_colns)].items():
            
            """not bothing with unique check"""
            crve_d[coln.strip()] = cser.unique()[0]
            
        #fix order
        del crve_d['exposure']
        crve_d['exposure'] = 'impact'

        #=======================================================================
        # assemble curves----
        #=======================================================================
        rlib = dict() #contents curves


                     
        #group loop
        for (coln1, coln2), gdf in df.loc[:, dd_colns].groupby(by = [self.od_typer, self.od_type2]):
            btag = '%s_%s'%(coln1, coln2)
            
            
            #build for each
            for ltype, coln in {
                'cont':self.od_dmgC,
                'strc':self.od_dmgS,
                }.items():
                if not ltype in rlib: rlib[ltype]=dict() #add the page

                # meta
                tag = '%s_%s'%(btag, ltype)
                dcurve_d = crve_d.copy()
                dcurve_d['tag']=tag
                dcurve_d['impact_var'] = lt_impactVal_d[ltype]
                
                
                
                log.info('added %s w/ %s'%(tag, dcurve_d))
                #===============================================================
                # #depth damage data
                #===============================================================

                #add zero
                if not min(gdf[dcoln])<=0:
                    zser = gdf.iloc[0, :].copy() #start with first
                    zser[dcoln] = 0
                    zser[coln] = 0
                    gdf1 = gdf.append(zser, ignore_index=True)
                else:
                    gdf1 = gdf.copy() #dont want to cary over the value from last loop
                
                #sort and convert
                dd_d = gdf1.loc[:, [dcoln, coln]].dropna(
                    ).sort_values(dcoln, ascending=True
                    ).set_index(dcoln, drop=True).dropna().iloc[:, 0].to_dict()
                
                
                assert dd_d[0]==0.0, 'bad zero value: %s'%dd_d[0]
                #assemble
                dcurve_d = {**dcurve_d, **dd_d}

                self.check_crvd(dcurve_d, logger=log)
                
                #add result
                rlib[ltype][tag] = dcurve_d
                

        log.info('finished w/ %i contents and structural curves'%(len(rlib[ltype])))
        #==============================================================================
        # convert and add to results
        #==============================================================================
        new_libs = set()
        for ltype, d in rlib.items():
            


            
            rd = dict()
            for k, sd in d.items():
                """need this to ensure index is formatted for plotters"""
                df =  pd.Series(sd).to_frame().reset_index(drop=False)
                df.columns = range(df.shape[1]) #reset the column names
                rd[k] = df
            
            #get the summary tab first
            rd = { **{'_smry':self._get_smry(d.copy(), logger=log)},
                 **rd,
                }
            
            
            lName = '%s_%s'%(libName, ltype)
            self.res_d[lName] = rd
            new_libs.add(lName)
            
        log.info('added %i new librarires to result: \n    %s'%(len(new_libs), new_libs))
        
        return rlib
        
        
    def _get_source(self, #pull data out by source tag
                    srch_str,
                    df_raw=None,
                    logger=None,
                    srch_coln = None,
                    ):
        
        if logger is None: logger=self.logger
        if df_raw is None: df_raw = self.df
        if srch_coln is None: srch_coln = self.od_source
        log = logger.getChild('_get_srch_str')
        
        #=======================================================================
        # locate entreis w/ match
        #=======================================================================
        boolidx = df_raw[srch_coln].str.contains(srch_str)
        
        assert boolidx.any(), 'failed to get a match on %s'%srch_str
        
        log.info('for \'%s\'=\'%s\' got %i (of %i) matches'%(
            srch_coln, srch_str, boolidx.sum(), len(boolidx)) )
        
        return df_raw.loc[boolidx, :]
    

        """
        view(df)
        view(df_raw)
        """
        
    
    #===========================================================================
    # ploters--------
    #===========================================================================
    def plot_res(self, #plot all the libraries
                 logger=None,
                 **kwargs
                 ):
        
        res_d = self.res_d
        
        
        fig_d = dict()
        for libName, lib_d in res_d.items():
            """
            for k,v in lib_d.items():
            
                print(k)
            """
            
            
            fig_d[libName] = self.plotAll(lib_d, title=libName, lib_as_df=True, 
                                          logger=logger, **kwargs)
            
        return fig_d
        
         
    #===========================================================================
    # outputers----------
    #===========================================================================
    def output(self,
               overwrite=None,
               ): #writ ethe results container
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('output')
        res_d = self.res_d
        out_dir = self.out_dir
        if overwrite is None: overwrite=self.overwrite
        
        #=======================================================================
        # loop and write
        #=======================================================================
        
        
        for libName, d in res_d.items():
            ofn = '%s_%s.xls'%(libName, today_str)
            ofp = os.path.join(out_dir, ofn)
            
            if os.path.exists(ofp): assert overwrite
            
            #write to multiple tabs
            writer = pd.ExcelWriter(ofp, engine='xlsxwriter')
            for tabnm, df in d.items():
                if tabnm=='_smry':
                    index, header = True, True
                else:
                    index, header = False, False
                    
                df.to_excel(writer, sheet_name=tabnm, index=index, header=header)
            writer.save()
            
            log.info('wrote %i sheets to file: \n    %s'%(len(d), ofn))
        
        return out_dir
        
        
        
        
        

if __name__=='__main__':
    
    
    
    
    wrkr = NRconv()
    wrkr.load()
    
    for libName, srch_str in {
                              'Acres_1968':'Acres Ltd., Guidelines for analysis',
                            }.items():
    
        wrkr.convert(libName=libName, srch_str=srch_str)
    
#===============================================================================
#     #plots
#     fig_d = wrkr.plot_res()
# 
#     
#     #outputs
#     for k,v in fig_d.items():
#         wrkr.output_fig(v)
#===============================================================================
        
    out_dir = wrkr.output()

    #===========================================================================
    # wrap
    #===========================================================================
    #force_open_dir(wrkr.out_dir)
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)