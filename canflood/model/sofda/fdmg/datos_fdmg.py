'''
Created on Aug 28, 2018

@author: cef

object handlers for the fdmg tab
'''

#===============================================================================
# IMPORT STANDARD MODS -------------------------------------------------------
#===============================================================================
import logging, re #os, sys, imp, time, re, math, copy, inspect


import pandas as pd
import numpy as np

from hlpr.exceptions import Error

#import scipy.integrate


#from collections import OrderedDict

#===============================================================================
#  IMPORT CUSTOM MODS ---------------------------------------------------------
#===============================================================================

import model.sofda.hp.pd as hp_pd
import model.sofda.hp.oop as hp_oop
import model.sofda.hp.data as hp_data

#===============================================================================
# IMPORT SPECIFIC FUNCS ------------------------------------------------------
#===============================================================================
from model.sofda.hp.pd import view

# LOGGER SETUP -----------------------------------------------------------------
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')

#Befin Definitions ------------------------------------------------------------

class Fdmgo_data_wrap(object): #generic methods for Fdmg data objects
    
    exp_coltyp_d = None #place holder for column/type expectations {coln: type}
    
    """dont want to mess with this
    def __init__(self,  *vars, **kwargs):
        logger = mod_logger.getChild('Fdmgo_data_wrap')
        cn = self.__class__.__name__
        logger.debug('start _init_ on %s'%cn)
        
        super(Fdmgo_data_wrap, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        
        #append the mind to the expected column names
        if isinstance(self.exp_coltyp_d, dict):          
            self.exp_coltyp_d[self.mind] = int
            
        self.logger.debug('finished __init__ on %s'%self.__class__.__name__)"""
        
    
    def clean_binv_data(self, df_raw): #generic cleaning for binv style data
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('clean_binv_data')
        df = df_raw.copy()
        binv_df = self.parent.kids_d['binv'].childmeta_df
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not isinstance(binv_df, pd.DataFrame):
                raise IOError
            if not len(binv_df)  > 0:
                raise IOError
            
        #=======================================================================
        # slice columns by the expected columns
        #=======================================================================
        if isinstance(self.exp_coltyp_d, dict):  
            
            #add the indexer
            self.exp_coltyp_d[self.mind] = int
            
            #check we got all the columns we require
            exp_coln_ar = np.array(list(self.exp_coltyp_d.keys()))
            
            
            boolar = np.invert(np.isin(exp_coln_ar, df.columns))
            if np.any(boolar):
                raise Error('missing %i expected columns: \n    %s'%
                              (boolar.sum(), exp_coln_ar[boolar]))
                
            #make the slice
            df1 = df.loc[:, exp_coln_ar]
            
            #remove the indexer
            del self.exp_coltyp_d[self.mind]
        else:
            df1 = df
            
        if not self.mind in df1.columns:
            raise Error('%s is missing \'%s\''%(self.name, self.mind))
        #=======================================================================
        # reindex
        #=======================================================================
        if np.any(df1[self.mind].isna()):
            raise IOError
        
        
        df1.loc[:,self.mind] = df1.loc[:,self.mind].astype(int)  #change the type
        df2 = df1.set_index(self.mind, 
                           drop=True, #would be better to keep this... but looks like much of our cleaning requires it be gone 
                           verify_integrity=True).sort_index()
        

        #===================================================================
        # slice for the binv
        #===================================================================       
        boolind = np.isin(df2.index, binv_df.index)
        df3 = df2[boolind]
        
        if self.db_f:
            if not boolind.sum() == len(binv_df):
                boolind2 = np.isin(binv_df.index, df2.index)
                logger.error('failed to find %i entries specified in the binv: \n %s'
                             %(len(binv_df) - boolind.sum(),binv_df.index[~boolind2].values.tolist()))
                raise IOError #check data trimming?
        
        logger.debug('dropped %i (of %i) not found in teh binv to get %s'%
                     (len(df2) - len(df3), len(df2), str(df3.shape)))

        #=======================================================================
        # typeset
        #=======================================================================
        """leave this to individuals as we have different null handling strategies"""
        
        
        
        return df3

    def check_binv_data(self, df):
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('check_binv_data')
        
        binv_df = self.parent.kids_d['binv'].childmeta_df
        
        #null check
        hp_pd.fancy_null_chk(df, detect='error', dname=self.name, logger=logger)

        

        
        #length check
        if not len(df) == len(binv_df):
            raise Error('my data length (%i) does not match the binv length (%i)'%(len(df), len(binv_df)))
        
        #check for index match
        if not np.all(df.index == binv_df.index):
            raise IOError
        
    def apply_on_binv(self, #apply the passed key data to the binv
                      data_attn, #name of data set to apply toth ebinv
                      hse_attn, 
                      coln = None, #optional column name in data set (if different than hse_attn)
                      ): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('apply_on_binv')
        
        if coln is None: coln = hse_attn #assume this is how the data is labeld
        
        df = getattr(self, data_attn)
        binv = self.model.binv
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not isinstance(df, pd.DataFrame):
                raise IOError
            
            if not coln in df.columns:
                raise IOError
            
            if not self.session.state == 'init':
                #check the indexes match
                if not np.all(binv.childmeta_df.index == df.index):
                    raise IOError
        
        #pull the requested series from the data set
        ser = df.loc[:, coln]
        
        """
        type(ser)
        """
        logger.debug('from \'%s\' with %s applied to \'%s\''%
                     (data_attn, str(df.shape), hse_attn))
        #=======================================================================
        # mid session dynamic update to the objects
        #=======================================================================
        if not self.session.state == 'init':

            # tell teh binv to update its houses
            binv.set_all_hse_atts(hse_attn, ser = ser)
            
        #=======================================================================
        # pre run just update the binv_df
        #=======================================================================
        else:
            #binv_df = binv.childmeta_df.copy()
            binv.childmeta_df.loc[:,hse_attn] = ser
            logger.debug('merged %i entries for \'%s\' onto the binv_df %s'
                         %(len(ser), hse_attn, str(binv.childmeta_df.shape)))
            
        return

        
class Rfda_curve_data(#class object for rfda legacy pars
            hp_data.Data_wrapper,
            hp_oop.Child): 
    'made this a class for easy tracking/nesting of parameters'
    
    acode_sec_d =  {'AA1': 'sres', 'AA2': 'sres', 'AA3': 'sres', 'AA4': 'sres', 'AD1': 'sres', 'AD2': 'sres', 'AD3': 'sres', 'AD4': 'sres', 
                    'BA1': 'sres', 'BA2': 'sres', 'BA3': 'sres', 'BA4': 'sres', 'BC1': 'sres', 'BC2': 'sres', 'BC3': 'sres', 'BC4': 'sres', 'BD1': 'sres', 'BD2': 'sres', 'BD3': 'sres', 'BD4': 'sres', 
                    'CA1': 'sres', 'CA2': 'sres', 'CA3': 'sres', 'CA4': 'sres', 'CC1': 'sres', 'CC2': 'sres', 'CC3': 'sres', 'CC4': 'sres', 
                    'CD1': 'sres', 'CD2': 'sres', 'CD3': 'sres', 'CD4': 'sres', 
                    'DA1': 'sres', 'DA2': 'sres', 'DA3': 'sres', 'DA4': 'sres', 
                    'ME1': 'mres', 'ME2': 'mres', 'ME3': 'mres', 'ME4': 'mres', 
                    'NF1': 'mres', 'NF2': 'mres', 'NF3': 'mres', 'NF4': 'mres', 
                    'S1': 'nores', 'S2': 'nores', 'S3': 'nores', 'S4': 'nores', 'S5': 'nores', 
                    'A1': 'nores', 'B1': 'nores', 
                    'C1': 'nores', 'C2': 'nores', 'C3': 'nores', 'C4': 'nores', 'C5': 'nores', 'C6': 'nores', 'C7': 'nores', 
                    'D1': 'nores', 'E1': 'nores', 'F1': 'nores', 'G1': 'nores', 'H1': 'nores', 'I1': 'nores', 'J1': 'nores', 'K1': 'nores', 'L1': 'nores', 'M1': 'nores', 'N1': 'nores', 'N2': 'nores'}
    
    
    
    def __init__(self, *vars, **kwargs):
        super(Rfda_curve_data, self).__init__(*vars, **kwargs) #initilzie teh baseclass   
        
        self.load_data()
        self.data = self.pre_calcs()
        
        #pass your pars off tot he session
        self.session.acode_sec_d = self.acode_sec_d
        
        self.logger.debug('fdmg.Rfda_curve_data initilized')
        
        return
    
    """
    view(self.data)
    """
        
    def load_data(self): #load legacy pars from the df
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('load_data')


        
        self.filepath = self.get_filepath()
        
        #load from file
        df_raw = hp_pd.load_xls_df(self.filepath, logger=logger, 
                header = 0, index_col = None)
                
        
        self.data = df_raw 
        logger.debug('attached rfda_curve with %s'%str(self.data.shape))
        
    def pre_calcs(self,
                  df_raw = None): #df level manpiulations
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('pre_calcs')
        if df_raw is None: df_raw = self.data.copy()
        
        df = df_raw.copy()
        
        #=======================================================================
        # clean it up
        #=======================================================================
        df = df.rename(columns={ df.columns[0]: "acode1" }) #rename the first column
        #=======================================================================
        # add the asector column5
        #=======================================================================
        ser = pd.Series(self.acode_sec_d, name='asector')
        df = df.join(ser, on='acode1') #add the column
        
        
        #=======================================================================
        # get the list of acodes
        #=======================================================================
        """
        view(df)
        """
        acode_sec_d = dict() #{acode: asector}
        
        #add teh commericial
        boolidx_nr = df['asector']=='nores' #identify
        
        nores_df = df.loc[boolidx_nr, ('acode1', 'asector')] #slice to this
        
        #drop to reindexed series and get a dict from this
        nores_d = nores_df.set_index('acode1', verify_integrity=True).iloc[:,0].to_dict() 
        
        acode_sec_d.update(nores_d) #add thse in 
        
        
        #add the residential
        res_df = df.loc[~boolidx_nr, ('acode1', 'asector')] #slice to this
        
        res_df.loc[:, 'acode1'] = res_df['acode1'].str.slice(stop=2) #drop all the trailing numerals
        
        res_df = res_df.drop_duplicates(subset='acode1').reset_index(drop=True) #drop down to just hte unique acodes
        
        #drop to reindexed series and get a dict from this
        res_d = res_df.set_index('acode1', verify_integrity=True).iloc[:,0].to_dict() 
        
        acode_sec_d.update(res_d) #add thse in 
        
        logger.debug('found %i acodes'%len(acode_sec_d))
        
        self.parent.acode_sec_d.update(acode_sec_d) #attach these to fdmg
        
        
        return df
        
                        
        
class Flood_tbl(     #flood table worker
                     hp_data.Data_wrapper,
                     hp_oop.Child,
                     Fdmgo_data_wrap): 
    
    #===========================================================================
    # program
    #===========================================================================
    expected_tabn = ['wet', 'dry', 'aprot']
    #===========================================================================
    # from user
    #===========================================================================
    na_value = None #extra value to consider as null
    
    min_chk = 800 #minimum value to pass through checking
    max_chk = 2000 #maximumv alue to allow through checking
    
    wetnull_code = 'take_wet'
    
    wetdry_tol = 0.1
    
    damp_build_code = 'average'
    
    #area exposure grade
    area_egrd00 = None
    area_egrd01 = None
    area_egrd02 = None

    
    #===========================================================================
    # calculated
    #===========================================================================
    
    aprot_df = None
    
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Flood_tbl')
        logger.debug('start _init_')
        super(Flood_tbl, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        

        #=======================================================================
        # custom atts
        #=======================================================================
        self.mind = self.parent.mind
        self.model = self.parent
        
        self.wsl_d = dict()

        
        logger.debug('load_data() \n')
        self.load_data() #execute the standard data loader
        
        self.treat_wetnull()
        
        self.wetdry_logic_fix()
        
        self.build_damp()
        
        if self.db_f:  self.check_data()
        
        """ NO! only want the named flood table to set this
        self.set_area_prot_lvl()"""
        
        logger.debug('finish _init_ \n')
        
        return
    
    def load_data(self):
        logger = self.logger.getChild('load_data')
        
        self.filepath = self.get_filepath()
        
        d = self.loadr_real(self.filepath, multi = True)
        
        #=======================================================================
        # sort and attach
        #=======================================================================
        for k, v in d.items():
            logger.debug('sending \'%s\' for cleaning'%k)
            df1 = self.clean_binv_data(v)
            
            #cleaning for wsl
            if k in ['dry', 'wet']: 
                df2 = self.wsl_clean(df1, tag=k)

                self.wsl_d[k] = df2
                
            #cleaning for area protection
            elif k == 'aprot': 
                self.aprot_df = df1.astype(np.int)
                
            else: 
                raise Error('got unexpected tab name \'%s\''%k)
        
        return
    
    def wsl_clean(self, df_raw, tag='?'):
        logger = self.logger.getChild('wsl_clean')
        df = df_raw.copy()
        
        #=======================================================================
        # drop columns
        #=======================================================================
        """not implemented"""
        #any flagged columns
        boolcol = df.columns.astype(str).str.startswith('~')
        
        if np.any(boolcol):
            logger.warning('dropping %i \'%s\' columns with \'~\' flag'%( boolcol.sum(), tag))
            df1 = df.loc[:,~boolcol]
        else:
            df1 = df
            
        #drop any coordinate columns
        df1 = df1.drop(labels=['X','x','Y','y'], axis=1, errors='ignore')
        
        
        #===================================================================
        # headers
        #===================================================================
        #reformat columns
        try:
            df1.columns = df1.columns.astype(int) #reformat the aeps as ints
        except:
            raise Error('failed to recast columns as int: \n %s'%(df1.columns.tolist()))
        
        
        #sort the columns
        df2 = df1.reindex(columns = sorted(df1.columns))

        
        #reformat values
        df2 = df2.astype('float32')
        
        
        #=======================================================================
        # clean the user provided null
        #=======================================================================
        if not self.na_value is None:
            boolar = df2.values == self.na_value
            df2[boolar] = np.nan
            
            logger.warning('for set %i user identified values to null with \'%s\''%
                           (boolar.sum().sum(), self.na_value))
        
        """not working for some reason
        hp_pd.cleaner_report(df, df2)"""
        
        logger.debug('cleaned to %s'%str(df2.shape))
        
        return df2
        
    def treat_wetnull(self): #apply the wetnull_code algorhitim to the dry
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('treat_wetnull')
                
        dfwet = self.wsl_d['wet']
        dfdry = self.wsl_d['dry']
        
        dfwet_raw = dfwet.copy()
        dfdry_raw = dfdry.copy()
        
        #=======================================================================
        # precheck
        #=======================================================================
        if self.db_f:
            if np.any(pd.isnull(dfdry)):
                logger.debug('nulls per column: \n%s'%pd.isnull(dfdry).sum(axis=0))
                logger.debug('nulls per row: \n%s'%pd.isnull(dfdry).sum(axis=1))
                raise Error('got %i null values for dfdry'%pd.isnull(dfdry).sum().sum()) 
        
        
        #=======================================================================
        # take _wet
        #=======================================================================
        if self.wetnull_code == 'take_dry':
            
            #identify location of null values in the dry frame
            boolar = pd.isnull(dfwet.values)
            
            #replace all the null values with the value from dfwet
            dfwet = dfwet.where(~boolar, other=dfdry)
            
            logger.info('set %i values from the wet flood to the dry flood'%boolar.sum())
            
        else: raise IOError
        
        
        #=======================================================================
        # reset into dict
        #=======================================================================
        self.wsl_d['wet'] = dfwet
        self.wsl_d['dry'] = dfdry
        
        return 
 
    def wetdry_logic_fix(self, tol = None): #fix the dry depths
        'makes sure our dry depths are at elast as high as our wet depths'
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('wetdry_logic_fix')
        
        if tol is None: tol = self.wetdry_tol
        
        dfwet = self.wsl_d['wet']
        dfdry = self.wsl_d['dry']
        
        #=======================================================================
        # find logical inconsistencies
        #=======================================================================

        delta = dfwet - dfdry 
        """
        hp_pd.v(delta)
        """
        
        boolar = delta < 0 #identify all inconsistencies
        
        if not np.any(boolar):
            logger.debug('no inconsistencies found. skipping')
            """
            hp_pd.v(boolar)
            hp_pd.v(delta)
            """
            return
        
        #=======================================================================
        # check we are within tolerance
        #=======================================================================
        delta2 = delta.where(boolar, other=0) #replace all positive deltas with zero
        boolar1 = abs(delta2) > tol #find where these are out of tolerance
        
        if np.any(boolar1):
            logger.error('dry<wet: \n%s'%
                         (delta2[boolar1].dropna(axis=0, how='all').dropna(axis=1, how='all')))
            
            raise Error('found %i entries out of tolerance = %.2f'%(boolar1.sum().sum(), tol))
        
        """
        hp_pd.v(abs(delta2))
        hp_pd.v(delta[boolar])
        hp_pd.v(boolar)
        
        hp_pd.v(delta)
        hp_pd.v(delta2)
        """
        #=======================================================================
        # replace bad dry values with the wet values
        #=======================================================================
        logger.warning('resolving %i dry > wet depth inconsistencies on the wet'%boolar.sum().sum())
        
        
        dfwet1 = dfwet.where(~boolar, other=dfdry) #set these
        
        self.wsl_d['wet'] = dfwet1 #reset this
        
        if self.db_f:
            delta2 = dfwet1 - dfdry
            
            if np.any(delta2 < 0):
                raise IOError
            
        
        return
        
    def check_data(self):
        logger = self.logger.getChild('check_data')
        
        #combine all your data for quicker checking
        d = self.wsl_d.copy()
        d['aprot'] = self.aprot_df
        #=======================================================================
        # check the tabs
        #=======================================================================
        if not np.all(np.isin(self.expected_tabn, list(d.keys()))):
            logger.error("expected tabs %sin the flood table"%self.expected_tabn)
            raise IOError
        
        #=======================================================================
        # check the data
        #=======================================================================\
        shape = None
        cols = None

        for k, df in d.items():
            logger.debug('checking \'%s\''%k)
            self.check_binv_data(df)
            
            #===================================================================
            # check wsl
            #===================================================================
            if k in ['wet', 'dry', 'damp']:
            
                if np.any(df.dropna().values > float(self.max_chk)):
                    raise IOError
                
                if np.any(df.dropna().values < float(self.min_chk)):
                    raise IOError
                
                #check the shape between the set
                if shape is None: #set the first to check later
                    shape = df.shape
                    
                else: #check against last time
                    if not shape == df.shape:
                        raise Error('got shape mistmatch for \'%s\' flood table (%s != %s)'
                                      %(k, shape, df.shape))

                #check the columns match from tab to tab
                cols = df.columns.tolist()
                
                if not cols is None:
                    if not cols == df.columns.tolist():
                        raise IOError
                    
                
                #check that the depths vary with the aep
                col_last = None
                for coln, col in df.items():
                    
                    #set first
                    if col_last is None:
                        col_last = col
                        coln_last = coln
                        continue
                    
                    #aep should increase monotonically
                    if not coln > coln_last:
                        raise IOError
                    
                    #see that all of our depths are greater than last years
                    boolar = col <= col_last
                    
                    if np.any(boolar):
                        logger.warning('for \'%s\' found %i (of %i) entries from \'%s\' <= \'%s\''
                                     %(k, boolar.sum().sum(), boolar.count().sum(), coln, coln_last))
                        
                        logger.debug('\n %s'%df.loc[boolar, (coln, coln_last)])
                        
                        
                        """
                        structural protections can prevent flood waters from rising for more extreme floods
                        
                        for small floods, wet== dry
                        """
                    coln_last = coln
                        

                    
                logger.debug('finished check on wsl data for \"%s\''%k)
             
            #===================================================================
            # check aprot   
            #===================================================================
            else:
                if not 'area_prot_lvl' in df.columns:
                    logger.error('expected area_prot_lvl as a colmn name on tab \'%s\''%k)
                    raise IOError
                
                
                
                
        #=======================================================================
        # wet dry logic
        #=======================================================================
        dfwet = d['wet']
        dfdry = d['dry']
        
        #look for bad values where the dry depth is higher than the wet depth
        boolar = dfdry > dfwet
        
        if np.any(boolar):
            logger.error('got %i (of %i) dry depths greater than wet depths'%(boolar.sum(), dfdry.count().sum()))
            """
            delta = dfdry - dfwet
            hp_pd.v(delta)
            hp_pd.v(dfdry)
            hp_pd.v(dfwet)
            hp_pd.v
            """
            raise IOError
        
        boolar = d['damp'] > dfwet
        
        if np.any(boolar):
            raise IOError
        
        boolar = dfdry > d['damp']
        
        if np.any(boolar):
            raise IOError
        
            
        return
    
    def build_damp(self): #build the damp levels
        logger = self.logger.getChild('build_damp')
        
        dfwet = self.wsl_d['wet']
        dfdry = self.wsl_d['dry']
        
        if self.damp_build_code == 'average':
            delta = dfwet - dfdry
            """
            hp_pd.v(delta)
            
            hp_pd.v(delta/0.5)
            """
            
            dfdamp = dfdry + delta/2.0
            
        elif self.damp_build_code.startswith('random'):
            
            #===================================================================
            # randmoly set some of these to the wet value
            #===================================================================
            #pull the ratio out of the kwarg 
            str1 = self.damp_build_code[7:]
            frac = float(re.sub('\)',"",str1)) #fraction of damp that should come from wet
            
            #generate random selection
            rand100 = np.random.randint(0,high=101, size=dfdry.shape, dtype=np.int) #randomly 0 - 100
            randbool = rand100 <= frac*100 #select those less then the passed fraction
            
            #set based on this selection
            dfdamp = dfdry.where(~randbool, other = dfwet) #replace with wet
            
            logger.info('generated dfdamp by setting %i (of %i) entries from wet onto dry'%(randbool.sum().sum(), dfdamp.count().count()))
            
            if self.db_f:
                if not np.all(dfdamp[randbool] == dfwet[randbool]):
                    raise IOError
                
                if not np.all(dfdamp[~randbool]==dfdry[~randbool]):
                    raise IOError
                       
            
            
        else:
            raise IOError
        
        logger.info('with damp_build_code = \'%s\', generated damp wsl with %s'%(self.damp_build_code, str(dfdamp.shape)))
        
        self.wsl_d['damp'] = dfdamp
        
        if self.db_f:
            deltaw = dfwet - dfdamp
            
            if np.any(deltaw<0):
                boolar = deltaw<0
                logger.error('got %i (of %i) damp levels greater than wet levels'%(boolar.sum().sum(), dfwet.count().sum()))
                """
                hp_pd.v(deltaw)
                hp_pd.v(delta)
                hp_pd.v(dfwet)
                hp_pd.v(dfdamp)
                
                hp_pd.v(dfdry)
                """
                raise IOError
            
            deltad = dfdamp - dfdry
            
            if np.any(deltad <0):
                raise IOError
        
        return
    

    
    """
    dfpull = self.model.binv.childmeta_df
    dfpull.columns
    binv_df.columns
    hp_pd.v(df3)
    """
    
    
class Fhr_tbl( #flood table worker
        Fdmgo_data_wrap,    
        hp_data.Data_wrapper,
        hp_oop.Child, #must be at the bottom of the cascade
                     ): 
    
    exp_coltyp_d = {'fhz':int, 'bfe':float}
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Fhr_tbl')
        logger.debug('start Fhr_tbl._init_')
        super(Fhr_tbl, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        

        #=======================================================================
        # custom atts
        #=======================================================================
        self.mind = self.parent.mind
        self.model = self.parent
        
        

        

        logger.debug('load_data() \n')
        self.load_data() #execute the standard data loader
        
        logger.debug('finish _init_')
        
        return
    """
    for k, df in self.d.items():
        print(k, str(df.shape))
    view(df)
    """
    
    def load_data(self):
        logger = self.logger.getChild('load_data')
        
        self.filepath = self.get_filepath()
        
        d = self.loadr_real(self.filepath, multi = True)
        
        #=======================================================================
        # clean and assign
        #======================================================================='
        """
        d.keys()
        """
        self.d = dict()

        for k, v in d.items():
            logger.debug('on \'%s\' with %s'%(k, str(v.shape)))
            #clean
            df = hp_pd.clean_datapars(v, logger=logger)
            df1 = self.clean_binv_data(df)#adds the mind, slices to the expected columns, makes sure we have them
            
            #check the data
            """ nothing very useful here
            self.check_data(df1)"""
            
            #===================================================================
            # check for nulls
            #===================================================================
            #check the fhz for nulls (allowing nulls on the bfe)
            hp_pd.fancy_null_chk(df1['fhz'], detect='error', dname=self.name, logger=logger)
            
            
            #tyepsetting
            df2 = df1.astype(self.exp_coltyp_d)
            
            

            
            #add this cleaned frame into the collection
            self.d[k] = df2
            
            logger.debug('loaded adn added \'%s\' with %s'%(k, str(df1.shape)))
            
        logger.info('finished with %i fhrs loaded: %s'%(len(self.d), list(self.d.keys())))
            

            
        return
    
#===============================================================================
#     def check_data(self, df):
#         
#         self.check_binv_data(df)
# 
#         return
#===============================================================================

        
        
                

                
        
        
            
            
        
    
        
        
          