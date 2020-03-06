'''
Created on Mar. 5, 2020

@author: cefect

converting from rfda formats
'''


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging

import pandas as pd
import numpy as np

from scipy import interpolate, integrate

#==============================================================================
# parametessr
#==============================================================================
l1 = ['False', 'FALSE', 'false', 'NO', 'No', 'no', 'N', 'n']
l2 = ['True','TRUE','true', 'yes','YES','Yes', 'Y', 'y']
truefalse_d = {
    **dict(zip(l1, np.full(len(l1), True))),
    **dict(zip(l2, np.full(len(l2), False)))
    }


#==============================================================================
# custom imports
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
    
#plugin runs
else:
    mod_logger = logging.getLogger('risk1') #get the root logger

    from hlpr.exceptions import QError as Error

from hlpr.Q import *
from hlpr.basic import *



class RFDAconv(Qcoms):
    
    # legacy index numbers
    legacy_ind_d = {0:'id1',1:'address',2:'id2',10:'class', 11:'struct_type', 13:'area', 
                    18:'bsmt_f', 19:'ff_height', 20:'lon',21:'lat', 25:'gel'}
    
    

    
    def __init__(self, 
                 bsmt_ht = 1.8,
                  **kwargs):
        
        self.bsmt_ht = bsmt_ht
        
        mod_logger.info('RFDAconv.__init__ start')
        super().__init__(**kwargs) #initilzie teh baseclass
        
    def to_finv(self, #convert an .xls to a .gpkg
                rinv_vlay,
                drop_colns=['ogc_fid', 'fid'], #optional columns to drop from df
                bsmt_ht = None
                ): 
        if bsmt_ht is None: bsmt_ht = self.bsmt_ht
        
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
        
        assert len(df.columns) == 26, 'expects 26 columns'
        
        log.info('loaded w/ %s'%str(df.shape))
        
        #convert conersion from postiion to loaded labels
        d = self.legacy_ind_d
        lab_d = {df.columns[k]:v for k, v in d.items()}
        
        back_lab_d = dict(zip(lab_d.values(), lab_d.keys()))
        
        #relabel to standardize
        df = df.rename(columns=lab_d)
        
        log.info('converted columns:\n    %s'%lab_d)
        
        
        #======================================================================
        # convert
        #======================================================================
        res_df = pd.DataFrame(index=df.index)
        res_df[self.cid] = df['id1'].astype(int)
        res_df['f0_tag'] = df['class'] + df['struct_type'] #suffix addded for main/basement below
        res_df['f0_elv'] = df['gel'] + df['ff_height']
        res_df.loc[:,'f0_elv'] = res_df['f0_elv'].round(self.prec)
        res_df['f0_scale'] = df['area'].round(self.prec)
        res_df['f0_cap'] = np.nan
        
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
        # basements
        #======================================================================
        #convert/cleean basements
        boolidx = df['bsmt_f'].replace(truefalse_d).astype(bool)
        
        log.info('adding nested curves for %i (of %i) basements'%(boolidx.sum(), len(boolidx)))
        
        #basements        
        res_df.loc[boolidx,'f1_tag'] = res_df.loc[boolidx, 'f0_tag'] + '_B'
        res_df.loc[boolidx,'f1_scale'] = res_df.loc[boolidx, 'f0_scale']
        res_df.loc[boolidx,'f1_elv'] = res_df.loc[boolidx, 'f0_elv'] - bsmt_ht
        res_df['f1_cap'] = np.nan
        
        """
        view(res_df)
        """
        
        
        
        
        #re-tag main floor
        res_df.loc[:,'f0_tag'] = res_df['f0_tag'] + '_M'
        
        
        
        
        
        #======================================================================
        # add in everything else
        #======================================================================
        res_df = res_df.join(df)
        
        #======================================================================
        # generate vlay
        #======================================================================
        geo_d = vlay_get_fdata(rinv_vlay, geo_obj=True, logger=log)
        finv_vlay = vlay_new_df(res_df, rinv_vlay.crs(), geo_d=geo_d,
                                logger=log,
                                layname = '%s_finv.gpkg'%rinv_vlay.name())
        
        
        
        fcnt = finv_vlay.dataProvider().featureCount()
        assert fcnt == dp.featureCount()
        
        log.info('finished w/ \'%s\' w/ %i feats'%(finv_vlay.name(), fcnt))
        
        return finv_vlay
    
    def to_curveset(self,
                    df_raw,
                    bsmt_ht =None, #for combination curves,
                    logger=None,
                    ):
        if logger is None: logger = self.logger
        if bsmt_ht is None: bsmt_ht = self.bsmt_ht
        
        log = logger.getChild('to_curveset')
        assert isinstance(bsmt_ht, float)
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
            
            dcurve_d = {'tag':cname,
                        'desc':'rfda converted',
                        'source':'Alberta (2014)',
                        'location':'Alberta',
                        'date':2014,
                        'vuln_units':'$CAD/m2',
                        'dep_units':'m',
                        'scale':'occupied space area',
                        'ftype':'depth-damage',
                        'depth':'damage'}
        
            
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
                dcurve_d = {'tag':tag,
                        'desc':'rfda converted and combined w/ bsmt_ht = %.2f, M+B '%bsmt_ht,
                        'source':'Alberta (2014)',
                        'location':'Alberta',
                        'date':2014,
                        'vuln_units':'$CAD/m2',
                        'dep_units':'m',
                        'scale':'occupied space area',
                        'ftype':'depth-damage',
                        'depth':'damage'}
                
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
            
            dcurve_d = {'tag':cnp,
                        'desc':'rfda converted and combined w/ bsmt_ht = %.2f, BC+BS+MC+MS'%bsmt_ht,
                        'source':'Alberta (2014)',
                        'location':'Alberta',
                        'date':2014,
                        'vuln_units':'$CAD/m2',
                        'dep_units':'m',
                        'scale':'occupied space area',
                        'ftype':'depth-damage',
                        'depth':'damage'}
            
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
                
                dcurve_d = {'tag':tag,
                        'desc':'rfda converted and combined w/ bsmt_ht = %.2f, C+S'%bsmt_ht,
                        'source':'Alberta (2014)',
                        'location':'Alberta',
                        'date':2014,
                        'vuln_units':'$CAD/m2',
                        'dep_units':'m',
                        'scale':'occupied space area',
                        'ftype':'depth-damage',
                        'depth':'damage'}
                
                res_d[tag] = {**dcurve_d, **res_ser.to_dict()}
                
            
            
        
        #==============================================================================
        # convert
        #==============================================================================
        df_d = dict()
        for cname, d in res_d.items():
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
        
        
        ofp = os.path.join(out_dir, '%s_cset.xls'%basefn)
        
        
        #write to multiple tabs
        writer = pd.ExcelWriter(ofp, engine='xlsxwriter')
        for tabnm, df in df_d.items():
            df.to_excel(writer, sheet_name=tabnm, index=True, header=False)
        writer.save()
        
        log.info('wrote %i sheets to file: \n    %s'%(len(df_d), ofp))
        
        return ofp
        
        


if __name__ =="__main__": 
    overwrite=True
    

#==============================================================================
#     #==========================================================================
#     # dev data: curve conversion
#     #==========================================================================
#     out_dir = os.path.join(os.getcwd(), 'rfda')
#     crv_fp = r'C:\LS\03_TOOLS\CanFlood\_ins\rfda\HighRiver\20200305\DamageCurves.xls'
#     tag = 'dev'
#     
#     
#     #==========================================================================
#     # load
#     #==========================================================================
#     assert os.path.exists(crv_fp)
#     df_raw = pd.read_excel(crv_fp, header=None)
#         
#     wrkr = RFDAconv(logger=mod_logger, out_dir=out_dir, tag=tag)
#     #==========================================================================
#     # execute
#     #==========================================================================
#     log = mod_logger.getChild(tag)
#     
# 
#     
#     
#     df_d = wrkr.to_curveset(df_raw, bsmt_ht=1.8, logger=log)
#     
#     #==========================================================================
#     # output
#     #==========================================================================
#     basefn = os.path.splitext(os.path.split(crv_fp)[1])[0]
#     ofp = wrkr.output(df_d, basefn=basefn)
#==============================================================================

    
     
    #==========================================================================
    # inventory conversion
    #==========================================================================
    #==========================================================================
    # dev data
    #==========================================================================
    out_dir = os.path.join(os.getcwd(), 'rfda')
    inv_fp = r'C:\LS\03_TOOLS\CanFlood\_ins\rfda\HighRiver\20200305\HighRiverResDirect_rinv.gpkg'
    tag = 'dev'
    cid = 'xid'
     
     
     
    #==========================================================================
    # load data
    #==========================================================================
    assert os.path.exists(inv_fp)
    rinv_vlay = load_vlay(inv_fp)
    #==========================================================================
    # execute
    #==========================================================================
    log = mod_logger.getChild(tag)
    wrkr = RFDAconv(logger=mod_logger, out_dir=out_dir, tag=tag, cid=cid)
     
    finv_vlay = wrkr.to_finv(rinv_vlay)
     
     
    #==========================================================================
    # ouput
    #==========================================================================
     
    vlay_write(finv_vlay, os.path.join(out_dir, finv_vlay.name()), logger=log, overwrite=overwrite)

     
    
    force_open_dir(out_dir)

    print('finished')