'''
Created on Mar. 5, 2020

@author: cefect

converting from rfda formats
'''


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging, datetime

import pandas as pd
import numpy as np

#from scipy import interpolate, integrate

#qgis
from qgis.core import QgsVectorLayer

#==============================================================================
# custom imports
#==============================================================================
 
from hlpr.exceptions import QError as Error

from hlpr.Q import Qcoms, vlay_get_fdf, vlay_get_fdata, vlay_new_df
#from hlpr.basic import *

from model.modcom import DFunc
#==============================================================================
# parametessr
#==============================================================================
l1 = ['False', 'FALSE', 'false', 'NO', 'No', 'no', 'N', 'n']
l2 = ['True','TRUE','true', 'yes','YES','Yes', 'Y', 'y']
truefalse_d = {
    **dict(zip(l1, np.full(len(l1), False))),
    **dict(zip(l2, np.full(len(l2), True)))
    }




mod_name = 'rfda'

class RFDAconv(DFunc, Qcoms):
    
    # legacy index numbers
    legacy_ind_d = {0:'id1',1:'address',2:'id2',10:'class', 11:'struct_type', 13:'area', 
                    18:'bsmt_f', 19:'ff_height', 20:'lon',21:'lat', 25:'gel'}
    

    def __init__(self, 
                 bsmt_ht = 1.8,
                  **kwargs):
        
        self.bsmt_ht = bsmt_ht
        
        #mod_logger.info('RFDAconv.__init__ start')
        super().__init__(**kwargs) #initilzie teh baseclass
        
    def to_finv(self, #converting rfda inventoryies
                rinv_vlay,
                drop_colns=['ogc_fid', 'fid'], #optional columns to drop from df
                bsmt_ht = None
                ): 
        
        
        if bsmt_ht is None: 
            bsmt_ht = self.bsmt_ht
        
        log = self.logger.getChild('to_finv')
        
        cid = self.cid
        
        assert isinstance(rinv_vlay, QgsVectorLayer)
        assert isinstance(bsmt_ht, float)
        
        dp = rinv_vlay.dataProvider()
        assert dp.featureCount() >0, 'no features'
        
        log.info('on %s w/ %i feats'%(rinv_vlay.name(), dp.featureCount()))
        

        #======================================================================
        # get df
        #======================================================================
        df_raw = vlay_get_fdf(rinv_vlay, logger=log)
        df = df_raw.drop(drop_colns,axis=1, errors='ignore')
        
        assert len(df.columns) >= 26, 'expects at least 26 columns. got %i'%len(df.columns)
        
        log.info('loaded w/ %s'%str(df.shape))
        
        #convert conersion from postiion to loaded labels
        d = self.legacy_ind_d
        lab_d = {df.columns[k]:v for k, v in d.items()}
        
        back_lab_d = dict(zip(lab_d.values(), lab_d.keys()))
        
        #relabel to standardize
        df = df.rename(columns=lab_d)
        
        log.info('converted columns:\n    %s'%lab_d)
        
        #id non-res
        nboolidx = df['struct_type'].str.startswith('S')
        
        log.info('%i (of %i) flagged as NRP'%(nboolidx.sum(), len(nboolidx)))
        """
        view(df)
        """
        #======================================================================
        # build f0-----------
        #======================================================================
        res_df = pd.DataFrame(index=df.index)
        res_df[self.cid] = df['id1'].astype(int)
        
        res_df.loc[:, 'f0_elv'] = df['gel'] + df['ff_height']
        res_df.loc[:,'f0_elv'] = res_df['f0_elv'].round(self.prec)
        res_df['f0_scale'] = df['area'].round(self.prec)
        res_df['f0_cap'] = np.nan
        
        #resi
        res_df['f0_tag'] = df['class'] + df['struct_type'] #suffix addded for main/basement below
        
        #NRP (overwriting any NRPs)
        res_df.loc[nboolidx, 'f0_tag'] = df.loc[nboolidx, 'class']
        
        #======================================================================
        # check
        #======================================================================
        if not res_df[cid].is_unique:
            boolidx = res_df[cid].duplicated(keep=False)
            
            raise Error('invalid indexer. %s column has %i (of %i) duplicated values: \n%s'%(
                back_lab_d['id1'], boolidx.sum(), len(boolidx), 
                res_df.loc[boolidx, cid].sort_values()))
                
                
        assert not res_df['f0_tag'].isna().any(), 'got some nulls on %s and %s'%(
            back_lab_d['class'], back_lab_d['struct_type'])
        
        assert not res_df['f0_elv'].isna().any(), 'got some nulls on %s and %s'%(
            back_lab_d['gel'], back_lab_d['ff_height'])
        
        assert not res_df['f0_scale'].isna().any(), 'got some nulls on %s'%back_lab_d['area']
        
        #======================================================================
        # build f1 (basemments or structural)-----------
        #======================================================================
        #convert/cleean basements
        boolidx = df['bsmt_f'].replace(truefalse_d).astype(bool)
        
        log.info('adding nested curves for %i (of %i) basements'%(boolidx.sum(), len(boolidx)))
        
        #resi basements        
        res_df.loc[boolidx,'f1_tag'] = res_df.loc[boolidx, 'f0_tag'] + '_B'
        res_df.loc[boolidx,'f1_scale'] = res_df.loc[boolidx, 'f0_scale']
        res_df.loc[boolidx,'f1_elv'] = res_df.loc[boolidx, 'f0_elv'] - bsmt_ht
        res_df['f1_cap'] = np.nan
        
        #re-tag main floor
        res_df.loc[:,'f0_tag'] = res_df['f0_tag'] + '_M'
        
        #NRP
        res_df.loc[nboolidx, 'f0_tag'] = df.loc[nboolidx, 'class'] #re-tag
        res_df.loc[nboolidx, 'f1_tag'] = df.loc[nboolidx, 'struct_type']
        res_df.loc[nboolidx, 'f1_elv'] = res_df.loc[nboolidx, 'f0_elv']
        res_df.loc[nboolidx, 'f1_scale'] = res_df.loc[nboolidx, 'f0_scale']
        
        #=======================================================================
        # nrp basements-----------
        #=======================================================================
        NBboolidx = np.logical_and(
            nboolidx, #NRPs 
            boolidx, #basement=Y
            )
        if NBboolidx.any():
            log.info('buildling %i (of %i) NRP basments'%(NBboolidx.sum(), len(boolidx)))
            
            nb = NBboolidx
            res_df.loc[nb, 'f2_tag'] = 'nrpUgPark'
            res_df.loc[nb, 'f2_scale'] = res_df.loc[nb, 'f0_scale']
            res_df.loc[nb, 'f2_elv'] = res_df.loc[nb, 'f0_elv'] - bsmt_ht
            res_df.loc[nb, 'f2_cap'] = np.nan
        
        #======================================================================
        # add in everything else
        #======================================================================
        res_df = res_df.join(df)
        
        """
        view(res_df)
        """
        
        #======================================================================
        # generate vlay
        #======================================================================
        geo_d = vlay_get_fdata(rinv_vlay, geo_obj=True, logger=log)
        finv_vlay = vlay_new_df(res_df, rinv_vlay.crs(), geo_d=geo_d,
                                logger=log,
                                layname = '%s_finv'%rinv_vlay.name())
        
        
        
        fcnt = finv_vlay.dataProvider().featureCount()
        assert fcnt == dp.featureCount()
        
        log.info('finished w/ \'%s\' w/ %i feats'%(finv_vlay.name(), fcnt))
        
        return finv_vlay
    
    def to_curveset(self,
                    df_raw,
                    bsmt_ht =None, #for combination curves,
                    nrpParkAD = 215.0, #default $/m2 for NRP uderground parking
                    
                    
                    #metatdata default
                    metac_d = {
                        'desc':'rfda format converted to CanFlood format',
                        'location':'Calgary and Edmonton, AB',
                        'date': 2014,
                        },
                    
                    logger=None,
                    ):
        """
        converting rfda style residential + nrp curves into CanFlood
        
        TODO: add for displacement stlye?
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        if bsmt_ht is None: bsmt_ht = self.bsmt_ht
        
        log = logger.getChild('to_curveset')
        

        

        
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(df_raw, pd.DataFrame)
        assert isinstance(bsmt_ht, float)
        
        log.debug('on %s'%str(df_raw.shape))
        
        
        #=======================================================================
        # update the defaults
        #=======================================================================
        crve_d = self.crve_d.copy() #start with a copy
        for k,v in {**{ 
            'source':'CanFlood.%s_%s_%s'%(mod_name, self.tag, datetime.datetime.today().strftime('%Y%m%d')),
            #'bsmt_ht':bsmt_ht,
            }, **metac_d}.items():
            crve_d[k] = v
        #==============================================================================
        # load
        #==============================================================================
        

        #drop the counts
        df = df_raw.drop(0, axis=0)
        
        #set the index
        df = df.set_index(0)
        df.index.name = 'cname'
        
        
        #get the curve name prefix
        df['cnp'] = df.index.str.slice(start=0, stop=2)
        
        
        #set the dcount columns
        df = df.rename(columns = {1:'dcount'})
        
        #re-order the columns
        boolcol = df.columns.isin(['dcount', 'cnp'])
        df = df.loc[:, ~boolcol].join(df.loc[:, boolcol])
        
        
        #==============================================================================
        # convert residential tags
        #==============================================================================
        #identify the residentials
        rboolidx = df.loc[:, 24].isin(['MC', 'MS', 'BC', 'BS'])
        
        #build new index
        df['nindex'] = df.loc[rboolidx, 'cnp'] + '_' + df.loc[rboolidx,24]
        
        df.loc[~rboolidx, 'nindex'] = df[~rboolidx].index
        df['oindex'] = df.index
        df = df.set_index('nindex', drop=True)
        
        #ctype = df.loc[boolidx,24].to_dict() #get all the types
        
        #==============================================================================
        # create individuals--------------------
        #==============================================================================
        res_d = dict() #container for CanFlood function tabs
        dd_set_d = dict() #container for all the depth damages
        dd_set_d2 = dict()
        
        boolar = df.columns.isin(['dcount', 'cnp', 'oindex'])
        
        
        for cname, row in df.iterrows():
            
            #==========================================================================
            # set meta info
            #==========================================================================
            dcurve_d = crve_d.copy()
            dcurve_d['tag']=cname
        
            
            #==========================================================================
            # depth damage info
            #==========================================================================
            #get just depth damage
            dd_ser = row[~boolar].dropna()
            
            #identify depths (evens) 
            bool_dep = dd_ser.index.values % 2 == 0
            
            #identiy damages
            bool_dmg = np.invert(bool_dep)
            
            #bundle depth:damage
            dd_d = dict(zip(dd_ser[bool_dep].tolist(),dd_ser[bool_dmg].tolist() ))
            
            
            #check for validty
            if max(dd_d.values()) == 0:
                print('%s has no damages! skipping'%cname)
            
            #add it in
            res_d[cname] = {**dcurve_d, **dd_d}
            dd_set_d[cname] = dd_d  #used below  B+M
            dd_set_d2[cname] = dd_d  #used below S+C
            print('added %s'%dcurve_d['tag'])
        

        #==============================================================================
        # create combined basement+mf----------------
        #==============================================================================
        #slice to this
        boolidx = df.loc[:, 24].isin(['MC', 'MS', 'BC', 'BS'])
        
        assert boolidx.any(), 'unable to find expected curve type keys in column 24'
        
        df_res = df.loc[boolidx,:].dropna(axis=1, how='all')
        
        df_res = df_res.rename(columns = {24:'ctype'})
        
        
        cnp_l = df_res.loc[:, 'cnp'].unique().tolist()
        
        #loop and collect
        res_bm_C_d = dict() #collect just these
        res_bm_S_d = dict() #collect just these
        
        for cnp in cnp_l:
            #loop on structural and contents
            for ctype in ('S', 'C'):
                #get this
                boolidx1 = np.logical_and(
                    df_res['cnp'] == cnp, #this class
                    df_res['ctype'].str.contains(ctype), #this ctype
                    )
                
                #check it
                if not boolidx1.sum() == 2:
                    raise IOError('unexpected count')
                
                #======================================================================
                # #collect by floor
                #======================================================================
                fdd_d = dict()
                for floor in ('M', 'B'):
        
                    boolidx2 = np.logical_and(boolidx1,
                                              df_res['ctype'].str.contains(floor))
                    
                    if not boolidx2.sum() == 1:
                        raise IOError('unexpected count')
                    
                    #get this dict
                    cname = df_res.index[boolidx2][0]
                    fdd_d[floor] = dd_set_d.pop(cname)
                    
                #======================================================================
                # adjust basement
                #======================================================================
                #add bsmt_ht to all the basement
        
                res_serf = pd.Series(fdd_d['B'])
                
                if bsmt_ht > max(res_serf.index):
                    raise IOError('requested basement height %.2f out of range'%bsmt_ht)
                
                res_serf.index = res_serf.index - bsmt_ht
                res_serf.index = res_serf.index.values.round(2)
                
                #get max value
                dmgmax = max(res_serf)
                
                
                #drop all positives (basement cant have posiitive depths)
                res_ser = res_serf[res_serf.index <= 0].sort_index(ascending=True)
                
                #set highest value to max
                res_ser.loc[0] = dmgmax
                
                #======================================================================
                # assemble
                #======================================================================
                mf_ser = pd.Series(fdd_d['M']) + dmgmax
                
                res_ser = res_ser.append(mf_ser, ignore_index=False).sort_index(ascending=True)
                
                #only take positive values
                res_ser = res_ser[res_ser > 0]
                #======================================================================
                # set meta
                #======================================================================
                tag = '%s_%s'%(cnp, ctype)
                
                dcurve_d = crve_d.copy()
                dcurve_d['tag']=tag
                dcurve_d['desc']=' %s \nrfda converted and combined w/ bsmt_ht = %.2f, M+B '%(dcurve_d['desc'], bsmt_ht)
                
                #add it in
                res_d[tag] = {**dcurve_d, **res_ser.to_dict()}
                
                if ctype == 'S':
                    res_bm_S_d[cnp] = res_ser
                elif ctype == 'C':
                    res_bm_C_d[cnp] = res_ser
                else:raise Error('bad ctype')
                
                
                print('added %s'%tag)
                
        #======================================================================
        # create combined mf+bsmt+S+C----------
        #======================================================================
        for cnp, Sser in res_bm_S_d.items():
            Cser = res_bm_C_d[cnp]
            
            assert np.array_equal(Sser.index, Cser.index), 'index mismatch'
            assert not cnp in res_d, 'tag already taken'
            
            #==================================================================
            # cpombine
            #==================================================================
            res_ser = Cser + Sser
            
            dcurve_d = crve_d.copy()
            dcurve_d['tag']=cnp
            dcurve_d['desc']=' %s \nrfda converted and combined w/ bsmt_ht = %.2f, BC+BS+MC+MS'%(dcurve_d['desc'], bsmt_ht)
            
            res_d[cnp] = {**dcurve_d, **res_ser.to_dict()}
            
        #======================================================================
        # combine Contes + Struc
        #======================================================================
        for cnp in cnp_l:
            for floor in ('B', 'M'):
                dd_C_ser =  dd_set_d2['%s_%sC'%(cnp, floor)]
                dd_S_ser =  dd_set_d2['%s_%sS'%(cnp, floor)]
                
                res_ser = pd.Series(dd_C_ser) + pd.Series(dd_S_ser)
                
                tag = '%s_%s'%(cnp, floor)
                
                assert not tag in res_d

                
                dcurve_d = crve_d.copy()
                dcurve_d['tag']=tag
                dcurve_d['desc']=' %s \nrfda converted and combined w/ bsmt_ht = %.2f, C+S'%(dcurve_d['desc'], bsmt_ht)
                
                res_d[tag] = {**dcurve_d, **res_ser.to_dict()}
                
            
            
        #=======================================================================
        # NRP underground parking------------
        #=======================================================================
        tag = 'nrpUgPark'
        
        dcurve_d = crve_d.copy()
        dcurve_d['tag']=tag
        dcurve_d['desc']=' %s \nrfda underground parking fixed %.2f $/m2'%(dcurve_d['desc'], nrpParkAD)
        
        
        res_d[tag] = {**dcurve_d,
                        **{
                        0:nrpParkAD,
                        10:nrpParkAD,
                            
                            }}
        
        #==============================================================================
        # convert and check
        #==============================================================================
        df_d = dict()
        for cname, d in res_d.items():
            self.check_crvd(d)
            df_d[cname] = pd.Series(d).to_frame()
            
        #======================================================================
        # wrap
        #======================================================================
        log.info('finished w/ %i'%len(df_d))
        return df_d
    
    def output(self, df_d,
               basefn = 'curves',
               out_dir = None,
               logger=None):
        if logger is None: logger = self.logger
            
        log = logger.getChild('output')
        
        if out_dir is None: out_dir = self.out_dir
        
        
        ofp = os.path.join(out_dir, '%s_%s_cset.xls'%(self.tag, basefn))
        
        
        #write to multiple tabs
        writer = pd.ExcelWriter(ofp, engine='xlsxwriter')
        for tabnm, df in df_d.items():
            df.to_excel(writer, sheet_name=tabnm, index=True, header=False)
        writer.save()
        
        log.info('wrote %i sheets to file: \n    %s'%(len(df_d), ofp))
        
        return ofp
        
