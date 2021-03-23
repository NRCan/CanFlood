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

        
    def convert(self,
                tbl_d,
                meta_df = None,
                sfx = 'DmgFn', #sufix identifying damage functions
                
                #function metadata
                metac_d = {
                      'desc':'HAZUS builtin',
                      'location':'USA',
                      'comment':'', #placeholder to preserve order
                      'desc_asset':'',
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
        # loop and build each grouop----
        #=======================================================================
        rLib_d = dict()
        for gname in gnames:

            #id these
            bx = meta_df.index.str.startswith(gname)
            mdfi = meta_df.loc[bx, :]
            log.debug('on \'%s\' w/ %i tables'%(gname, len(mdfi)))
            
            #get tables
            
            tbli_d = {k:tbl_d[k] for k in mdfi.index} #just these tables
            ddf = tbli_d.pop(gname+sfx)
            """
            view(ddf)
            """
            
            d = None
            if gname == 'flAg':
                """not sure on form"""
                pass
                #d = self._agri(ddf, gname, crve_d.copy(), logger=log)
                
            #buildings
            elif gname.startswith('flBldg') or gname.startswith('flEssntFlty') or gname=='flUtilFlty':
                d = self._bldg(ddf, tbli_d, gname, crve_d.copy(), logger=log)
                pass
            
            #Vehicles
            elif gname == 'flVeh':

                d = self._bldg(
                    ddf.rename(columns={'VehicleType':'Occupancy'}), 
                    tbli_d, gname, crve_d.copy(), logger=log)
            
            elif gname == 'flBridge':
                """not sure on form"""
                pass
                
            else:
                raise Error('unrecognized table: \'%s\''%gname)
                
            if not d is None:
                rLib_d[gname] = d
                
        #=======================================================================
        # re-org by source
        #=======================================================================
        d = dict()
        for gname, l1_d in rLib_d.copy().items():
            
            for srce, l2_d in l1_d.items():
                if not srce in d: d[srce] = dict()
                d[srce][gname] = l2_d
        rLib_d = d
        #=======================================================================
        # convert and build summaries
        #=======================================================================
        smry_d = dict()
        for srce, l1_d in rLib_d.copy().items():
            smry_d[srce] = dict()
            for gname, l2_d in l1_d.items():
                assert isinstance(l2_d, dict), gname
                
                rLib1 = dict()
                
                for k, sd in l2_d.items():
                    assert isinstance(sd, dict), k
                    assert len(sd)>0, k
                    """need this to ensure index is formatted for plotters"""
                    df =  pd.Series(sd).to_frame().reset_index(drop=False)
                    df.columns = range(df.shape[1]) #reset the column names
                    rLib1[k] = df
                
                #get the summary tab first
                smry_df = self._get_smry(l2_d.copy(),
                                         add_colns=['desc_asset'],
                                         logger=self.logger.getChild('%s.%s'%(gname, srce)))
                
                rLib_d[srce][gname] = { **{'_smry':smry_df},
                     **rLib1,
                    }
                smry_d[srce][gname] = smry_df
                
        #=======================================================================
        # collect summaries
        #=======================================================================
        dxind = None
        for gname, srce_d in smry_d.items():

            dxi = pd.concat(list(srce_d.values()), keys=srce_d.keys(), names=['type', 'curveName'])
            dxi = pd.concat([dxi], keys=[gname], names=['source'])
            
            if dxind is None:
                dxind = dxi
            else:
                dxind = dxind.append(dxi)
                
        log.info('finished w/ \n%s'%dxind.index)
        """
        view(dxind)
        """
        #=======================================================================
        # wrap
        #=======================================================================
        """
        view(smry_df)
        """
        #log.info('finished on %i'%len(rLib_d))
        
        return rLib_d, dxind.drop('plot_f', axis=1)

            

            
    def _agri(self,
            df_raw,
            
            gname,
            crve_d,
            sourceCn='FunctionSource',
            assetCn = 'Crop',
            logger=None,
            ):
        
        raise Error('not really sure how these curves work... skipping for now')
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild(gname)
        """
        view(df_raw)
        """
        
        #=======================================================================
        # meta update
        #=======================================================================
        crve_d.update({
            'desc':crve_d['desc'] + ' for Agriculture',
            'scale_var':'building replacement cost',
            'scale_units':'monetary',
            'impact_units':'pct',
            'impact_var':'loss'})
        
        srceLib_d = dict()
        for srce, gdf in df_raw.groupby(sourceCn):
            
            crve_d['source'] = '%s, table=\'%s\' file=%s'%(srce, gname, self.source_str)
            #log.debug('%s w/\n%s'%(srce, gdf['Occupancy'].value_counts()))
            srceLib_d[srce] = dict()
            
            for crop, cdf in gdf.groupby(assetCn):
                """
                view(cdf)
                """
                print(srce, crop)
            
                
        
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

        #=======================================================================
        # precheck
        #=======================================================================

        #=======================================================================
        # meta update
        #=======================================================================
        crve_d.update({
            'desc':crve_d['desc'] + ' for buildings',
            'scale_var':'replacement cost',
            'scale_units':'monetary',
            'impact_units':'pct',
            'impact_var':'loss'})
        #=======================================================================
        # build occupancy metadata
        #=======================================================================
        """no matching keys unique...
        odf = pd.concat([df for k,df in tbl_d.items() if k.endswith('UnionDetails')])
        """
        
        #=======================================================================
        # data prep
        #=======================================================================
        #get index column
        l = [e for e in ddf_raw.columns if e.endswith('Id')]
        assert len(l)==1, gname
        indxColn = l[0]
        
        df = ddf_raw.set_index(indxColn).rename(columns=self.depthc_d)
        """
        view(df)
        """
        log.info('for index \'%s\' got %s'%(indxColn, str(df.shape)))
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
            log.debug('%s w/\n%s'%(srce, gdf['Occupancy'].value_counts()))
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
                #tag
                tag = '%s_%s_%03i'%(gname[2:], row['Occupancy'],fnid)
                for k,v in self.tag_cln_d.items(): #apply typical conversions/cleans
                    tag = tag.replace(k, v)

                assert len(tag)<=30, 'invalid tag name length %i \n    %s'%(len(tag), tag)
                
                
                dcurve_d = crve_d.copy()
                dcurve_d['tag'] = tag
                dcurve_d['desc_asset'] = row['Description']
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
            log.debug('finished source=\'%s\' w/ %i'%(srce, len(srceLib_d[srce])))
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished on %i sources'%len(srceLib_d))
        
        return srceLib_d

        """
        view(pd.Series(dcurve_d))
        view(gdf)
        """
        
    def output_set(self, #output a collection of librarries
                   lib_d,
                   logger=None,
                   out_dir = None,
                   plot=True, #whether to also plot
                   ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('output_set')
        if out_dir is None: out_dir=self.out_dir
        
        #=======================================================================
        # loop and write
        #=======================================================================
        meta_d = dict()
        for srce_raw, l1_d in lib_d.copy().items():
            srce = srce_raw.replace('.', '').replace(' ','')
            od1 = os.path.join(out_dir, 'HAZUS_%s'%srce)
            if not os.path.exists(od1):os.makedirs(od1)
            meta_d[srce] = dict()
 
            for gn1_raw, l2_d in l1_d.items():
                gn1 = gn1_raw[2:]
                meta_d[srce][gn1] = dict()
                #check subtypes
                for k, df in l2_d.items():
                    if not isinstance(df, pd.DataFrame):
                        raise Error('bad type on %s'%gn1)
                
                #setup the filename
                ofn = '%s_%s_%s'%(self.libName, srce, gn1)
                ofn = ofn.replace(' ','')
                ofn = ofn.replace('.','')
                
                #do the write
                meta_d[srce][gn1]['xls_fp'] = self.output(l2_d, 
                                ofn=ofn+'.xls',                    
                                out_dir=od1)
                
                #===========================================================================
                # plots
                #===========================================================================
                if plot:

                    fig = self.plotAll(l2_d, 
                           title='%s_%s_%s'%(self.libName,srce, gn1),
                           lib_as_df=True, xlim = (0, 100),
                           )
                    
                    meta_d[srce][gn1]['fig_fp'] =self.output_fig(fig, 
                                   out_dir=od1, fname = ofn)
    
                
        
        log.info('wrote %i sets'%(len(meta_d)))
        
        return meta_d
    

        


if __name__=='__main__':
    out_dir = r'C:\LS\03_TOOLS\CanFlood\outs\misc\vfunc_conv\hazus'
    
    wrkr = HAZconv(out_dir=out_dir, 
                   figsize = (10, 10),
                   )
    raw_lib_d = wrkr.load()
    cLib_d, meta_dx = wrkr.convert(raw_lib_d)
    
    out_meta = wrkr.output_set(cLib_d, plot=True)
    
    meta_dx.to_csv( 
                 os.path.join(wrkr.out_dir, 'meta_%s_%i.csv'%(wrkr.libName, len(meta_dx)))
                 )

    #===========================================================================
    # wrap
    #===========================================================================
    #force_open_dir(wrkr.out_dir)
    tdelta = datetime.datetime.now() - start
    print('finished in %s'%tdelta)