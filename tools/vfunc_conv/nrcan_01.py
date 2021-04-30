'''
Created on Feb. 8, 2021

@author: cefect

converting 'Depth Damage Functions.xlsx' to CanFlood format 
    from NIcky's spreadsheet
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
from hlpr.exceptions import Error

from vfunc_conv.vcoms import VfConv
#from model.modcom import DFunc

mod_name = 'misc.nrcan_01'
today_str = datetime.datetime.today().strftime('%Y%m%d')


class NRconv(VfConv):
    

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
    od_dmg_pct = 'Damage Total (% of Assessed Value)'
    
    

    
    
    def __init__(self,
                 logger=None,
                 out_dir=None,
                 prec=5, #precision

                 **kwargs
                 ):
        
        
        if logger is None: logger=mod_logger
        
        super().__init__(logger=logger, out_dir=out_dir,
                         prec=prec,
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


    def _get_tag(self, btag, ltype):
        if ltype == 'total':
            tag = btag
        else:
            tag = '%s_%s' % (btag, ltype)
            
            
        #standard cleans
        for k,v in self.tag_cln_d.items():
            tag = tag.replace(k, v)
            
            
        return tag.strip()

    def convert(self, #get CanFlood format curve from Nickys spreadsheet
                
                      #search data
                      srch_str = 'Acres Ltd., Guidelines for analysis',
                      libName = 'Acres_1968', #name prefix for library
                      
                      #data handles
                      as_pct = False, #whether curve is percent or absolute damages
                      df_raw = None,
                      
                      #meta info
                      noMeta_colns = set(), #depth-damage also excluded
                      metac_d = {
                          'desc':'depth-damage curves for Residential, Commericial, and Inudstrial buildings in 1968 Galt, ON',
                          }, 
                      
                      lt_impactVal_d = {
                            'cont':'contents depreciated or repair value and some cleaning',
                            'strc':'building repair and restoration costs',
                            }
                              
                      ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild(libName)
        if df_raw is None: df_raw= self.df
        
        dcoln = self.dcoln
        #those we are NOT including in the meta reporting
        dd_colns = [self.od_typer, self.od_type2]
        
        if as_pct:
            dd_colns = dd_colns + [self.od_dmg_pct]
            subGroup_d = {'total':self.od_dmg_pct} #main divisor for curve librarries
        else:
            dd_colns = dd_colns + [self.od_dmgS, self.od_dmgC]
            subGroup_d = {'cont':self.od_dmgC,'strc':self.od_dmgS}
        
        
        #=======================================================================
        # clean1
        #=======================================================================
        df = self._get_source(srch_str, df_raw, logger=log).dropna(how='all', axis=1)
    
        #clean columns
        df.columns = df.columns.str.strip()
        #=======================================================================
        # precheck
        #=======================================================================
        miss_l = set(dd_colns).difference(df.columns)
        assert len(miss_l)==0, 'missing requested data colns: %s'%miss_l
        
        #impact descriptors matches subgruops
        miss_l = set(lt_impactVal_d.keys()).symmetric_difference(subGroup_d.keys())
        assert len(miss_l)==0, 'subgroup key mismatch: %s'%miss_l
        
        #meta columns
        miss_l = set(noMeta_colns).difference(df.columns)
        assert len(miss_l)==0, 'requested noMeta cols not in df: %s'%miss_l
        
        #=======================================================================
        # conversions
        #=======================================================================
        #to meteres
        
        df[dcoln] = df[self.od_depthFt]*self.ft_m
        df = df.drop(self.od_depthFt, axis=1) #remove for reporting
        dd_colns.append(dcoln)
        
        #year
        df.loc[:, self.od_year] = df[self.od_year].astype(int)
        
        #=======================================================================
        # get default meta----
        #=======================================================================
        noMeta_colns.update(dd_colns)
        
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
            if mcoln in metac_d: continue #skip these... take users value
            
            #check its unique
            assert len(df[rcoln].unique())==1, '%s not unique: %s'%(rcoln, df[rcoln].duplicated(keep=False))
            crve_d[mcoln] = df[rcoln].unique()[0]
            
            noMeta_colns.add(rcoln) #make sure we dont report this one
        
        #=======================================================================
        # get remainders
        #=======================================================================
        self.noMeta_colns = noMeta_colns.copy() #set for smry
        """some of these are redundant... but including for completeness"""
        cols = df.columns[~df.columns.isin(noMeta_colns)]
        log.info('collecting metadat from %i cols: %s'%(len(cols), cols.tolist()))
        
        for coln, cser in df.loc[:, ~df.columns.isin(noMeta_colns)].items():
            
            """not bothing with unique check"""
            crve_d[coln.strip()] = cser.unique()[0]
            
        #fix order
        del crve_d['exposure']
        crve_d['exposure'] = 'impact'

        #=======================================================================
        # assemble curves----
        #=======================================================================
        #=======================================================================
        # prep
        #=======================================================================
        rlib = dict() #contents curves
        
        df.loc[:,self.od_type2] = df[self.od_type2].fillna(' ') #need this to pickup gruops
        """
        view(df)
        """

                     
        #=======================================================================
        # #group loop
        #=======================================================================
        for (coln1, coln2), gdf in df.loc[:, dd_colns].groupby(by = [self.od_typer, self.od_type2]):
            #get tag (with dummy value handling)
            if coln2==' ':
                btag = coln1
            else:
                btag = '%s_%s'%(coln1, coln2)
            
            
            #build for each
            for ltype, coln in subGroup_d.items():
                assert coln in gdf.columns, coln
                if not ltype in rlib: rlib[ltype]=dict() #add the page

                # meta
                tag = self._get_tag(btag, ltype)
                    
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
                    
                """
                view(gdf1)
                """
                
                #sort and convert
                gdf2 = gdf1.loc[:, [dcoln, coln]].dropna(
                    ).sort_values(dcoln, ascending=True
                    ).round(self.prec).dropna(how='any', axis=0).astype(float)
                    
                """precision of indexes behaving unexpectedly"""

                dd_d = {round(e[0], self.prec):e[1] for e in gdf2.values}
                
                #check first value
                if not dd_d[list(dd_d.keys())[0]]==0.0:
                    raise Error('bad zero value: %s'%dd_d[0])
                
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
            
            log.info('wrote %i sheets to file: \n    %s'%(len(d), ofp))
        
        return out_dir
        

def run(set_d,
        plot=True,
        out_dir=r'C:\LS\03_TOOLS\CanFlood\outs\misc\vfunc_conv',
        ):
    
    #===========================================================================
    # setup
    #===========================================================================
    wrkr = NRconv(out_dir=out_dir, figsize = (10,10))
    wrkr.load()
    
    #===========================================================================
    # loop each set
    #===========================================================================
    for libName, d in set_d.items():
        
        #get kwargs
        kwargs = {k:v for k,v in d.items() if k in ['srch_str','as_pct', 'lt_impactVal_d', 'metac_d', 'noMeta_colns']}
                
        #run conversion
        wrkr.convert(libName=libName,**kwargs)
 
        #=======================================================================
        # plots       
        #=======================================================================
        if plot:
            fig_d = wrkr.plot_res()
     
            for k,v in fig_d.items():
                wrkr.output_fig(v)
                
        #=======================================================================
        # outputs
        #=======================================================================
            
        out_dir = wrkr.output()
        
    return out_dir
        
        
        

if __name__=='__main__':
    
    
    out_dir = run(
        {
        #=======================================================================
        # 'Acres_1968':{
        #     'srch_str':'Acres Ltd., Guidelines for analysis',
        #     'as_pct':False,
        #     'metac_d':{
        #                   'desc':'depth-damage functions for Residential, Commericial, and Inudstrial buildings in 1968 Galt, ON',
        #             },
        #             },
        #=======================================================================
        
          'KGS_2000':{
              'srch_str':'KGS Group, Red River',
              'as_pct':True,
              'metac_d':{
                          'desc':'depth-damage functions for buildings and basements in 1997 Southern Manitoba',
                          'location':'Red River Basin, MB',
                          'scale_var':'total market value',
                          'scale_units':'$CAD',
                          'impact_units':'pct',
                          'exposure_var':'flood depth above main floor',
                          'empirical_synthetic':'semi-empirical',
                          'cost_year':'1997',
                    },
              'lt_impactVal_d':{'total':'total foundation, structure components, and moveable losses'},
              'noMeta_colns':{'Type', 'Notes on Depths', 'Notes2', '$ Year', 'Region/Floodplain', 'Coverage of Report'}
             },
        }
        )

    


    #===========================================================================
    # wrap
    #===========================================================================
    #force_open_dir(wrkr.out_dir)
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)