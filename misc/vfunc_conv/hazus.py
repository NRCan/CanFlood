'''
Created on Feb. 16, 2021

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
from hlpr.exceptions import Error

from vfunc_conv.vcoms import VfConv
#import pandas_access as mdb
import pyodbc
#from model.modcom import DFunc

mod_name = 'hazus'
today_str = datetime.datetime.today().strftime('%Y%m%d')

class HAZconv(VfConv):
    def __init__(self,
                 libName = 'HAZUS',
                 prec=5, #precision
                 **kwargs):
        
        self.libName = libName
        
        
        super().__init__(
                 prec=prec,
                 **kwargs) #initilzie teh baseclass
    
    def load(self,
                 fp = r'C:\LS\03_TOOLS\CanFlood\ins\vfunc\hazus\flDmRsFn.mdb',
                 
                ):
        log = self.logger.getChild('load')
        assert os.path.exists(fp)
        
        #print driver info
        [x for x in pyodbc.drivers() if x.startswith('Microsoft Access Driver')]
        
        
        #=======================================================================
        # build connection
        #=======================================================================
        conn_str = (
            r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'
            r'DBQ=%s;'%fp
                    )
        cnxn = pyodbc.connect(conn_str)
        crsr = cnxn.cursor()
        
        #=======================================================================
        # #print tables
        #=======================================================================
        tables = [table_info.table_name for table_info in crsr.tables(tableType='TABLE')]

            
        #=======================================================================
        # for t in crsr.description:
        #     print(t)
        #=======================================================================
        tbl_d = dict()
        meta_d = dict()
        for tableName in tables:
            sql = "Select * From %s"%tableName
            df = pd.read_sql(sql,cnxn)
            log.info('from \'%s\' got %s'%(tableName, str(df.shape)))
            tbl_d[tableName] = df

            meta_d[tableName] = {
                'shape':str(df.shape),
                #'dtypes':df.dtypes,
                'cols_str':str(df.columns.tolist()),               
                }
        #=======================================================================
        # wrap
        #=======================================================================
        
        self.meta_df = pd.DataFrame.from_dict(meta_d, orient='index')
        
        self.source_str = '%s received 2020-12-11'%os.path.basename(fp)

        return tbl_d
    
    def convert(self,
                tbl_d,
                meta_df = None,
                sfx = 'DmgFn', #sufix identifying damage functions
                
                #function metadata
                metac_d = {
                      'desc':'HAZUS builtin',
                      'location':'USA',
                      'comment':'', #placeholder to preserve order
                      #'date':'2010',
                      #'source':'(Huizinga et al. 2017)',
                      #'impact_var':'loss',
                      #'impact_units':'pct',
                      #'exposure_var':'flood depth',
                      #'exposure_units':'m',
                      #'scale_var':'maximum damage (national average)',
                      #'scale_units':'pct',
                          }, 
                                
                ):
        
        """
        #=======================================================================
        # mirroring structure in mdb
        #=======================================================================
        type (e.g. building structural)
            source (e.g. FIA)
                tags or curves
        """
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('convert')
        if meta_df is None: meta_df=self.meta_df.copy()
        
        #set the depth conversion dictionary
        self._set_depth_conv(
            [e for e in tbl_d['flBldgStructDmgFn'].columns if e.startswith('ft')])
        
        #=======================================================================
        # setup meta
        #=======================================================================
        crve_d = self.crve_d.copy() #start with a copy
        crve_d['file_conversion']='CanFlood.%s_%s'%(mod_name, today_str)
        crve_d['exposure_units']=self.exposure_units
        
        
        
        #check keys
        miss_l = set(metac_d.keys()).difference(crve_d.keys())
        #assert len(miss_l)==0, 'requesting new keys: %s'%miss_l

        #crve_d = {**metac_d, **crve_d}
        crve_d.update(metac_d) #preserves order
        """
        crve_d.keys()
        """
        #fix order
        del crve_d['exposure']
        crve_d['exposure'] = 'impact'
        
        #check it
        assert list(crve_d.keys())[-1]=='exposure', 'need last entry to be eexposure'
        
        #=======================================================================
        # identify function groups
        #=======================================================================
        bx = meta_df.index.str.endswith(sfx)
        
        gnames = meta_df.index[bx].str.replace(sfx, '').tolist()
        
        log.info('on %i damage tables \n    %s'%(len(gnames), gnames))
        
        #=======================================================================
        # loop and build each grouop
        #=======================================================================
        rLib_d = dict()
        for gname in gnames:

            #id these
            bx = meta_df.index.str.startswith(gname)
            mdfi = meta_df.loc[bx, :]
            log.info('on \'%s\' w/ %i tables'%(gname, len(mdfi)))
            
            #get tables
            
            tbli_d = {k:tbl_d[k] for k in mdfi.index} #just these tables
            ddf = tbli_d.pop(gname+sfx)
            
            if gname == 'flAg':
                d = self._ag(ddf)
                
            elif gname.startswith('flBldg'):
                d = self._bldg(ddf, tbli_d, gname, crve_d.copy(),
                                      logger=log)
                
            else:
                print(gname)
                
            rLib_d[gname] = d
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished on %i'%len(rLib_d))
            """
            view(ddf)
            """
            
    def _set_depth_conv(self, #get conversion dictionary form hazus labels
                        raw_l,  #example depths ['ft04m', 'ft03m', 'ft02m', 'ft01m', 'ft00', 'ft01', 'ft02', 'ft03'
                        exposure_units =None, #for changing units
                        ):
        log = self.logger.getChild('get_depth_conv')
        assert isinstance(raw_l, list)
        if exposure_units is None: exposure_units=self.exposure_units
        #=======================================================================
        # get scale
        #=======================================================================
        if exposure_units=='meters':
            scale = self.ft_m
        elif exposure_units =='ft':
            scale = 1
        else:
            raise Error('unrecognized exposure_units: %s'%exposure_units)
        
        #=======================================================================
        # get conversions
        #=======================================================================
        d = dict()
        for raw in raw_l:
            assert raw.startswith('ft'), raw
            
            val = raw.replace('ft', '')
            
            if raw.endswith('m'):
                iscale = scale*-1 #invert scale for negatives
                val = val[:-1]
            else:
                iscale = scale
                
            try:
                d[raw] = round(float(val)*iscale, self.prec)
            except Exception as e:
                raise Error('failed to float %s=\'%s\' \n    %s'%(raw, val, e))
            
        #=======================================================================
        # wrap
        #=======================================================================
        assert np.all(np.diff(pd.Series(d))>0), 'non-monotonic'
        
        log.info('finished w/ %i'%len(d))
        """
        d.keys()
        view(pd.Series(d))
        """
        self.depthc_d = d
        
        return 

        
            
    def _ag(self,
            df_raw):
        return dict()
    
    def _bldg(self,
              ddf_raw,
              tbl_d,
              gname,
              crve_d,
              logger=None,
              ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild(gname)
        """
        view(ddf_raw)
        
        tbl_d.keys()
        k = 'flBldgContDmgXRef'
        view(tbl_d[k])
        view(pd.Series(crve_d))
        """
        
        #=======================================================================
        # meta update
        #=======================================================================
        crve_d.update({
            'desc':crve_d['desc'] + ' for buildings',
            'scale_var':'building replacement cost',
            'scale_units':'monetary',
            'impact_units':'pct',
            'impact_var':'loss'})
        #=======================================================================
        # build occupancy metadata
        #=======================================================================
        
        odf = pd.concat([df for k,df in tbl_d.items() if k.endswith('UnionDetails')])
        
        #=======================================================================
        # data prep
        #=======================================================================
        df = ddf_raw.set_index('ContDmgFnId').rename(columns=self.depthc_d)
        """
        view(df)
        """
        #depth-damage data
        dboolidx = df.columns.isin(self.depthc_d.values()) #locate depth values
        
        assert df.loc[:, dboolidx].max().max()<=100, 'max dmg percent violated'
        assert df.loc[:, dboolidx].max().max()>=0, 'min dmg percent violated'
        #=======================================================================
        # loop and build curves
        #=======================================================================
        log.info('w/ \n%s'%df['Source'].value_counts())
        
        srceLib_d = dict()
        for srce, gdf in df.groupby('Source'):
            crve_d['source'] = '%s, table=\'%s\' file=%s'%(srce, gname, self.source_str)
            log.info('%s w/\n%s'%(srce, gdf['Occupancy'].value_counts()))
            srceLib_d[srce] = dict()
            
            #build a tab for each curve
            for fnid, row in gdf.iterrows():
                #===============================================================
                # depth-damage
                #===============================================================
                dd_d = row[dboolidx].to_dict()

                #===================================================================
                # meta
                #===================================================================
                tag = '%s_%s_%s_%03i'%(gname[2:], row['Occupancy'], srce, fnid)
                dcurve_d = crve_d.copy()
                dcurve_d['tag'] = tag
                dcurve_d['desc'] = '%s \n%s'%(row['Description'], dcurve_d['desc'])
                dcurve_d['comment'] = row['Comment']
                
                """
                view(pd.Series(dcurve_d))
                view(row[~dboolidx])
                """
                
                #assemble
                dcurve_d = {**dcurve_d, **dd_d}
    
                self.check_crvd(dcurve_d)
                
                srceLib_d[srce][tag] = dcurve_d
            #===================================================================
            # wrap source
            #===================================================================
            log.info('finished source=\'%s\' w/ %i'%(srce, len(srceLib_d[srce])))
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished on %i sources'%len(srceLib_d))
        
        return srceLib_d

            """
            view(pd.Series(dcurve_d))
            view(gdf)
            """
            

    
        



if __name__=='__main__':
    out_dir = r'C:\LS\03_TOOLS\CanFlood\outs\misc\vfunc_conv\hazus'
    
    wrkr = HAZconv(out_dir=out_dir, figsize = (10,10))
    raw_lib_d = wrkr.load()
    cLib_d = wrkr.convert(raw_lib_d)
    
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