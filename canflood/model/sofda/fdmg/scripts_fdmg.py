'''
Created on May 16, 2018

@author: cef

significant scripts for calculating damage within the ABMRI framework
    for secondary data loader scripts, see fdmg.datos.py


'''
#===============================================================================
# IMPORT STANDARD MODS -------------------------------------------------------
#===============================================================================
import logging, os,  time, re, math, copy, gc, weakref, random, sys



import pandas as pd
import numpy as np

import scipy.integrate

#===============================================================================
# shortcuts
#===============================================================================
from collections import OrderedDict
from hlpr.exceptions import Error

from weakref import WeakValueDictionary as wdict
from weakref import proxy

from model.sofda.hp.basic import OrderedSet

from model.sofda.hp.pd import view

idx = pd.IndexSlice

#===============================================================================
#  IMPORT CUSTOM MODS ---------------------------------------------------------
#===============================================================================
#import hp.plot
import model.sofda.hp.basic as hp_basic
import model.sofda.hp.pd as hp_pd
import model.sofda.hp.oop as hp_oop
import model.sofda.hp.sim as hp_sim
import model.sofda.hp.data as hp_data
import model.sofda.hp.dyno as hp_dyno
import model.sofda.hp.sel as hp_sel

import model.sofda.fdmg.datos_fdmg as datos




#import matplotlib.pyplot as plt
#import matplotlib
#import matplotlib.animation as animation #load the animation module (with the new search path)



#===============================================================================
# custom shortcuts
#===============================================================================
from model.sofda.fdmg.house import House
#from model.sofda.fdmg.dfunc import Dfunc
from model.sofda.fdmg.dmgfeat import Dmg_feat


# logger setup -----------------------------------------------------------------------
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')
#===============================================================================
#module level defaults ------------------------------------------------------
#===============================================================================
#datapars_cols = [u'dataname', u'desc', u'datafile_tailpath', u'datatplate_tailpath', u'trim_row'] #headers in the data tab

datafile_types_list = ['.csv', '.xls']


class Fdmg( #flood damage model
           hp_sel.Sel_controller, #no init
           hp_dyno.Dyno_wrap, #add some empty containers
           #hp.plot.Plot_o, #build the label
           hp_sim.Sim_model, #Sim_wrap: attach the reset_d. Sim_model: inherit attributes
           hp_oop.Trunk_o, #no init
                            #Parent_cmplx: attach empty kids_sd
                            #Parent: set some defaults
           hp_oop.Child): 
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    pars_path ==> pars_file.xls
        main external parameter spreadsheet.
        See description in file for each column
        
        dataset parameters
        tab = 'data'. expected columns: datapars_cols
        
        session parameters
        tab = 'gen'. expected rows: sessionpars_rows
            
    """
    #===========================================================================
    # program parameters
    #===========================================================================
    name = 'fdmg'

    #list of attribute names to try and inherit from the session
    try_inherit_anl = set(['ca_ltail', 'ca_rtail', 'mind', \
                       'dbg_fld_cnt', 'legacy_binv_f', 'gis_area_max', \
                       'fprob_mult', 'flood_tbl_nm', 'gpwr_aep', 'dmg_rat_f',\
                       'joist_space', 'G_anchor_ht', 'bsmt_opn_ht_code','bsmt_egrd_code', \
                       'damp_func_code', 'cont_val_scale', 'hse_skip_depth', \
                        'area_egrd00', 'area_egrd01', 'area_egrd02',
                        'fhr_nm', 'write_fdmg_sum', 'dfeat_xclud_price', 
                        'write_fdmg_sum_fly',
                        ])
    

    
    fld_aep_spcl = 100 #special flood to try and include in db runs
    bsmt_egrd   = 'wet' #default value for bsmt_egrd
    
    legacy_binv_f = True #flag to indicate that the binv is in legacy format (use indicies rather than column labels)
    
    gis_area_max = 3500
    
    acode_sec_d = dict() #available acodes with dfunc data loaded (to check against binv request) {acode:asector}
    

    
    'consider allowing the user control of these'
    gis_area_min        = 5
    gis_area_max        = 5000
    
    write_fdmg_sum_fly = False
    write_dmg_fly_first = True #start off to signifiy first run
    #===========================================================================
    # debuggers
    #===========================================================================
    write_beg_hist = True #whether to write the beg history or not
    beg_hist_df = None
    #===========================================================================
    # user provided values
    #===========================================================================
    #legacy pars
    floor_ht = 0.0
    
    
    
    mind     = '' #column to match between data sets and name the house objects
    
    #EAD calc
    ca_ltail    ='flat'
    ca_rtail    =2 #aep at which zero value is assumeed. 'none' uses lowest aep in flood set
    
    
    #Floodo controllers
    gpwr_aep    = 100 #default max aep where gridpower_f = TRUE (when the power shuts off)
    
    dbg_fld_cnt = '0' #for slicing the number of floods we want to evaluate
    
    #area exposure
    area_egrd00 = None
    area_egrd01 = None
    area_egrd02 = None
    


    #Dfunc controllers

    place_codes = None
    dmg_types = None
        
    flood_tbl_nm = None #name of the flood table to use  
    
    
    #timeline deltas
    'just keeping this on the fdmg for simplicitly.. no need for flood level heterogenieyt'
    wsl_delta = 0.0
    fprob_mult = 1.0 #needs to be a float for type matching
    
    
    
    dmg_rat_f = False
    
    #Fdmg.House pars
    joist_space = 0.3
    G_anchor_ht = 0.6
    bsmt_egrd_code = 'plpm'
    damp_func_code = 'seep'
    bsmt_opn_ht_code = '*min(2.0)'
    
    hse_skip_depth = -4 #depth to skip house damage calc
    
    fhr_nm = ''
    
    cont_val_scale = .25
    
    write_fdmg_sum = True
    
    dfeat_xclud_price = 0.0

    #===========================================================================
    # calculation parameters
    #===========================================================================
    res_fancy = None
    gpwr_f              = True #placeholder for __init__ calcs

    fld_aep_l = None
    
    dmg_dx_base = None #results frame for writing
    
    plotr_d = None #dictionary of EAD plot workers
    
    dfeats_d = dict() #{tag:dfeats}. see raise_all_dfeats()
    
    fld_pwr_cnt = 0
    seq = 0
    
    
    #damage results/stats
    dmgs_df = None
    dmgs_df_wtail = None #damage summaries with damages for the tail logic included
    ead_tot = 0
    dmg_tot = 0
    
    #===========================================================================
    # calculation data holders
    #===========================================================================
    dmg_dx      = None #container for full run results
    
    bdry_cnt = 0
    bwet_cnt = 0
    bdamp_cnt = 0
    
    def __init__(self,*vars, **kwargs):

        logger = mod_logger.getChild('Fdmg')
        
        #=======================================================================
        # initilize cascade
        #=======================================================================
        super(Fdmg, self).__init__(*vars, **kwargs) #initilzie teh baseclass
        
        #=======================================================================
        # object updates
        #=======================================================================
        self.reset_d.update({'ead_tot':0, 'dmgs_df':None, 'dmg_dx':None,\
                             'wsl_delta':0}) #update the rest attributes
        

        
        #=======================================================================
        # defaults
        #=======================================================================
        if not self.session._write_data:
            self.write_fdmg_sum = False
            
        if not self.dbg_fld_cnt == 'all':
            self.dbg_fld_cnt = int(float(self.dbg_fld_cnt))
            

        #=======================================================================
        # pre checks
        #=======================================================================
        if self.db_f:
            #model assignment
            if not self.model.__repr__() == self.__repr__():
                raise IOError
            
            #check we have all the datos we want
            dname_exp = np.array(('rfda_curve', 'binv','dfeat_tbl', 'fhr_tbl'))
            boolar = np.invert(np.isin(dname_exp, self.session.pars_df_d['datos']))
            if np.any(boolar):
                """allowing this?"""
                logger.warning('missing %i expected datos: %s'%(boolar.sum(), dname_exp[boolar]))
        
        
        #=======================================================================
        #setup functions
        #=======================================================================
        #par cleaners/ special loaders

        logger.debug("load_hse_geo() \n")
        self.load_hse_geo()
        
        logger.info('load and clean dfunc data \n')
        self.load_pars_dfunc(self.session.pars_df_d['dfunc']) #load the data functions to damage type table   
           
        logger.debug('\n')
        self.setup_dmg_dx_cols()
        
        logger.debug('load_submodels() \n')
        self.load_submodels()
        logger.debug('init_dyno() \n')
        self.init_dyno()
        
        #outputting setup
        if self.write_fdmg_sum_fly:
            self.fly_res_fpath = os.path.join(self.session.outpath, '%s fdmg_res_fly.csv'%self.session.tag)
        

            

        logger.info('Fdmg model initialized as \'%s\' \n'%(self.name))
        
        return
        
    
    #===========================================================================
    # def xxxcheck_pars(self): #check your data pars
    #     #pull the datas frame
    #     df_raw = self.session.pars_df_d['datos']
    #     
    #     #=======================================================================
    #     # check mandatory data objects
    #     #=======================================================================
    #     if not 'binv' in df_raw['name'].tolist():
    #         raise Error('missing \'binv\'!')
    #     
    #     #=======================================================================
    #     # check optional data objects
    #     #=======================================================================
    #     fdmg_tab_nl = ['rfda_curve', 'binv','dfeat_tbl', 'fhr_tbl']
    #     boolidx = df_raw['name'].isin(fdmg_tab_nl)
    #     
    #     if not np.all(boolidx):
    #         raise IOError #passed some unexpected data names
    #     
    #     return
    #===========================================================================
    

        
    def load_submodels(self):
        logger = self.logger.getChild('load_submodels')
        self.state = 'load'
        
        #=======================================================================
        # data objects
        #=======================================================================
        'this is the main loader that builds all teh children as specified on the data tab'
        logger.info('loading dat objects from \'fdmg\' tab')
        logger.debug('\n \n')
        
        #build datos from teh data tab
        'todo: hard code these class types (rather than reading from teh control file)'
        self.fdmgo_d = self.raise_children_df(self.session.pars_df_d['datos'], #df to raise on
                                              kid_class = None) #should raise according to df entry
        

        
        self.session.prof(state='load.fdmg.datos')
        'WARNING: fdmgo_d is not set until after ALL the children on this tab are raised'   
        #attach special children
        self.binv           = self.fdmgo_d['binv']
        
        """NO! this wont hold resetting updates
        self.binv_df        = self.binv.childmeta_df"""
        
        
        #=======================================================================
        # flood tables
        #=======================================================================
        self.ftblos_d = self.raise_children_df(self.session.pars_df_d['flood_tbls'], #df to raise on
                                              kid_class = datos.Flood_tbl) #should raise according to df entry
        
        #make sure the one we are loking for is in there
        if not self.session.flood_tbl_nm in list(self.ftblos_d.keys()):
            raise Error('requested flood table name \'%s\' not found in loaded sets'%self.session.flood_tbl_nm)
        
        
        'initial call which only udpates the binv_df'
        self.set_area_prot_lvl()
        
        if 'fhr_tbl' in list(self.fdmgo_d.keys()):
            self.set_fhr()
        

        #=======================================================================
        # dfeats
        #======================================================================
        if self.session.load_dfeats_first_f & self.session.wdfeats_f:
            logger.debug('raise_all_dfeats() \n')
            self.dfeats_d         = self.fdmgo_d['dfeat_tbl'].raise_all_dfeats()
        
        
        #=======================================================================
        # raise houses
        #=======================================================================
        #check we have all the acodes
        self.check_acodes()
        
        logger.info('raising houses')
        logger.debug('\n')
        
        self.binv.raise_houses()
        self.session.prof(state='load.fdmg.houses')
        'calling this here so all of the other datos are raised'
        #self.rfda_curve     = self.fdmgo_d['rfda_curve']
        
        """No! we need to get this in before the binv.reset_d['childmeta_df'] is set
        self.set_area_prot_lvl() #apply the area protectino from teh named flood table"""

        
        logger.info('loading floods')
        logger.debug('\n \n')
        self.load_floods()
        self.session.prof(state='load.fdmg.floods')
        
        
        
        logger.debug("finished with %i kids\n"%len(self.kids_d))
        
        
        return
    
    def setup_dmg_dx_cols(self): #get teh columns to use for fdmg results
        """
        This is setup to generate a unique set of ordered column names with this logic
            take the damage types
            add mandatory fields
            add user provided fields
        """
        logger = self.logger.getChild('setup_dmg_dx_cols')
        
        #=======================================================================
        #build the basic list of column headers
        #=======================================================================
        #damage types at the head
        col_os = OrderedSet(self.dmg_types) #put 
        
        #basic add ons
        _ = col_os.update(['total', 'hse_depth', 'wsl', 'bsmt_egrd', 'anchor_el'])
        

        #=======================================================================
        # special logic
        #=======================================================================
        if self.dmg_rat_f:
            for dmg_type in self.dmg_types:
                _ = col_os.add('%s_rat'%dmg_type)
                
                
        if not self.wsl_delta==0:
            col_os.add('wsl_raw')
            """This doesnt handle runs where we start with a delta of zero and then add some later
            for these, you need to expplicitly call 'wsl_raw' in the dmg_xtra_cols_fat"""
            
        #ground water damage
        if 'dmg_gw' in self.session.outpars_d['Flood']:
            col_os.add('gw_f')
            
        #add the dem if necessary
        if 'gw_f' in col_os:
            col_os.add('dem_el')
                
        
        #=======================================================================
        # set pars based on user provided 
        #=======================================================================
        #s = self.session.outpars_d[self.__class__.__name__]
        
        #extra columns for damage resulst frame
        if self.db_f or self.session.write_fdmg_fancy:
            
            logger.debug('including extra columns in outputs')  
            #clewan the extra cols
            'todo: move this to a helper'
            if hasattr(self.session, 'xtra_cols'):

                try:
                    dc_l = eval(self.session.xtra_cols) #convert to a list
                except:
                    logger.error('failed to convert \'xtra_cols\' to a list. check formatting')
                    raise IOError
            else:
                dc_l = ['wsl_raw', 'gis_area', 'acode_s', 'B_f_height', 'BS_ints','gw_f']
                
            if not isinstance(dc_l, list): raise IOError
            
            col_os.update(dc_l) #add these  

        self.dmg_df_cols = col_os

        logger.debug('set dmg_df_cols as: %s'%self.dmg_df_cols)
        
        return
                  
    def load_pars_dfunc(self, 
                        df_raw=None): #build a df from the dfunc tab
        """
        20190512: upgraded to handle nores and mres types
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('load_pars_dfunc')
        
        #list of columns to expect
        exp_colns = np.array(['acode','asector','place_code','dmg_code','dfunc_type','anchor_ht_code'])
        
        if df_raw is None: 
            df_raw = self.session.pars_df_d['dfunc']
        
        logger.debug('from df %s: \n %s'%(str(df_raw.shape), df_raw))
        #=======================================================================
        # clean
        #=======================================================================
        df1 = df_raw.dropna(axis='columns', how='all').dropna(axis='index', how='all')  #drop rows with all na
        df1 = df1.drop(columns=['note', 'rank'], errors='ignore') #drop some columns we dont need
        
        
        #=======================================================================
        # checking
        #=======================================================================
        #expected columns
        boolar = np.invert(np.isin(exp_colns, df1.columns))
        if np.any(boolar):
            raise Error('missing %i expected columns\n    %s'%(boolar.sum, exp_colns[boolar]))
        
        #rfda garage logic
        boolidx = np.logical_and(df1['place_code'] == 'G', df1['dfunc_type'] == 'rfda')
        if np.any(boolidx):
            raise Error('got dfunc_type = rfda for a garage curve (no such thing)')
        
        #=======================================================================
        # calculated columns
        #=======================================================================
        df2 = df1.copy()
        df2['dmg_type'] = df2['place_code'] + df2['dmg_code']
        
        """as acode whill change, we want to keep the name static
        df2['name'] = df2['acode'] + df2['dmg_type']"""
        df2['name'] = df2['dmg_type']
        


        #=======================================================================
        # data loading
        #=======================================================================
        if 'tailpath' in df2.columns:
            boolidx = ~pd.isnull(df2['tailpath']) #get dfuncs with data requests
            
            self.load_raw_dfunc(df2[boolidx])
            
            df2 = df2.drop(['headpath', 'tailpath'], axis = 1, errors='ignore') #drop these columns
        

        #=======================================================================
        # get special lists
        #=======================================================================
        
        #find total for exclusion
        boolidx = np.invert((df2['place_code']=='total').astype(bool))
        
        """Im not using the total dfunc any more..."""
        if not np.all(boolidx):
            raise Error('i thinkn this has been disabled')
        

        self.dmg_types = tuple(df2.loc[boolidx,'dmg_type'].dropna().unique().tolist())
        self.dmg_codes = tuple(df2.loc[boolidx, 'dmg_code'].dropna().unique().tolist())
        self.place_codes = tuple(df2.loc[boolidx,'place_code'].dropna().unique().tolist())
        #=======================================================================
        # #handle nulls
        #=======================================================================
        df3 = df2.copy()
        for coln in ['dmg_type', 'name']:
            df3.loc[:,coln] = df3[coln].replace(to_replace=np.nan, value='none')
                        
        #=======================================================================
        # set this
        #=======================================================================
        self.session.pars_df_d['dfunc'] = df3
                
        logger.debug('dfunc_df with %s'%str(df3.shape))
        
        #=======================================================================
        # get slice for houses
        #=======================================================================
         
        self.dfunc_mstr_df = df3[boolidx] #get this trim
        
        return
        """
        view(df3)
        """
        
    def load_hse_geo(self): #special loader for hse_geo dxcol (from tab hse_geo)
        logger = self.logger.getChild('load_hse_geo')
        
        #=======================================================================
        # load and clean the pars
        #=======================================================================
        df_raw = hp_pd.load_xls_df(self.session.parspath, 
                               sheetname = 'hse_geo', header = [0,1], logger = logger)
        
        df = df_raw.dropna(how='all', axis = 'index') #drop any rows with all nulls
        

        self.session.pars_df_d['hse_geo'] = df
        
        #=======================================================================
        # build a blank starter for each house to fill
        #=======================================================================
        
        omdex = df.columns #get the original mdex

        'probably a cleaner way of doing this'
        lvl0_values = omdex.get_level_values(0).unique().tolist()
        lvl1_values = omdex.get_level_values(1).unique().tolist()
        lvl1_values.append('t')
        
        newcols = pd.MultiIndex.from_product([lvl0_values, lvl1_values], 
                                             names=['place_code','finish_code'])
        
        """id prefer to use a shortend type (Float32)
        but this makes all the type checking very difficult"""
        
        geo_dxcol = pd.DataFrame(index = df.index, columns = newcols, dtype='Float32') #make the frame
        
        self.geo_dxcol_blank = geo_dxcol
                
        if self.db_f:
            if np.any(pd.isnull(df)):
                raise Error('got %i nulls in the hse_geo tab'%df.isna().sum().sum())
            
            l = geo_dxcol.index.tolist()
            
            if not l == ['area', 'height', 'per', 'inta']:
                raise IOError
            

        
        return
        
    def load_raw_dfunc(self, meta_df_raw): #load raw data for dfuncs
        logger = self.logger.getChild('load_raw_dfunc')
        
        logger.debug('with df \'%s\''%(str(meta_df_raw.shape)))
        
        d = dict() #empty container
        
        meta_df = meta_df_raw.copy()
        
        #=======================================================================
        # loop through each row and load the data
        #=======================================================================
        for indx, row in meta_df.iterrows():
            
            inpath = os.path.join(row['headpath'], row['tailpath'])
            
            df = hp_pd.load_smart_df(inpath,
                                     index_col =None, 
                                     logger = logger)
            
            d[row['name']] = df.dropna(how = 'all', axis = 'index') #store this into the dictionaryu
            
        logger.info('finished loading raw dcurve data on %i dcurves: %s'%(len(d), list(d.keys())))
        
        self.dfunc_raw_d = d
        
        return

    def load_floods(self):
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('load_floods')
        logger.debug('setting floods df \n')
        self.set_floods_df()
        
        df = self.floods_df
        
        logger.debug('raising floods \n')
        d = self.raise_children_df(df,   #build flood children
                                               kid_class = Flood,
                                               dup_sibs_f= True,
                                               container = OrderedDict) #pass attributes from one tot eh next
        
        #=======================================================================
        # ordered by aep
        #=======================================================================
        fld_aep_od = OrderedDict()
        
        for childname, childo in d.items():
            if hasattr(childo, 'ari'):  
                fld_aep_od[childo.ari] = childo
            else: raise IOError
            

        
        logger.info('raised and bundled %i floods by aep'%len(fld_aep_od))
        
        self.fld_aep_od = fld_aep_od
        
        return 
    
    def set_floods_df(self): #build the flood meta data
        
        logger = self.logger.getChild('set_floods_df')
            
        df_raw = self.session.pars_df_d['floods']
        
        df1 = df_raw.sort_values('ari').reset_index(drop=True)
        df1['ari'] = df1['ari'].astype(np.int)
        
        
        
        
        #=======================================================================
        # slice for debug set
        #=======================================================================
        if self.db_f & (not self.dbg_fld_cnt == 'all'):
            """this would be much better with explicit typesetting"""
            #check that we even have enough to do the slicing
            if len(df1) < 2:
                logger.error('too few floods for debug slicing. pass dbg_fld_cnt == all')
                raise IOError
            
            df2 = pd.DataFrame(columns = df1.columns) #make blank starter frame
            

            dbg_fld_cnt = int(float(self.dbg_fld_cnt))
            
            logger.info('db_f=TRUE. selecting %i (of %i) floods'%(dbg_fld_cnt, len(df1)))
            
            #===================================================================
            # try to pull out and add the 100yr
            #===================================================================
            try:
                boolidx = df1.loc[:,'ari'] == self.fld_aep_spcl
                if not boolidx.sum() == 1:
                    logger.debug('failed to locate 1 flood')
                    raise IOError
                
                df2 = df2.append(df1[boolidx])  #add this row to the end
                df1 = df1[~boolidx] #slice out this row
                
                dbg_fld_cnt = max(0, dbg_fld_cnt - 1) #reduce the loop count by 1
                dbg_fld_cnt = min(dbg_fld_cnt, len(df1)) #double check in case we are given a very short set
                
                logger.debug('added the %s year flood to the list with dbg_fld_cnt %i'%(self.fld_aep_spcl, dbg_fld_cnt))
                
            except:
                logger.debug('failed to extract the special %i flood'%self.fld_aep_spcl)
                df2 = df1.copy()
            
            
            #===================================================================
            # build list of extreme (low/high) floods
            #===================================================================
            evn_cnt = 0
            odd_cnt = 0
            

            for cnt in range(0, dbg_fld_cnt, 1): 
                
                if cnt % 2 == 0: #evens.  pull from front
                    idxr = evn_cnt
                    evn_cnt += 1
                    
                else: #odds. pull from end
                    idxr = len(df1) - odd_cnt - 1
                    odd_cnt += 1
                    
                logger.debug('pulling flood with indexer %i'%(idxr))

                ser = df1.iloc[idxr, :] #make thsi slice

                    
                df2 = df2.append(ser) #append this to the end
                
            #clean up
            df = df2.drop_duplicates().sort_values('ari').reset_index(drop=True)
            
            logger.debug('built extremes flood df with %i aeps: %s'%(len(df), df.loc[:,'ari'].values.tolist()))
            
            if not len(df) == int(self.dbg_fld_cnt): 
                raise IOError
                    
        else:
            df = df1.copy()
                    
        if not len(df) > 0: raise IOError
        
        self.floods_df = df
        
        return
    
    def set_area_prot_lvl(self): #assign the area_prot_lvl to the binv based on your tab
        #logger = self.logger.getChild('set_area_prot_lvl')
        """
        TODO: Consider moving this onto the binv and making the binv dynamic...
        
        Calls:
        handles for flood_tbl_nm
        """
        logger = self.logger.getChild('set_area_prot_lvl')
        logger.debug('assigning  \'area_prot_lvl\' for \'%s\''%self.flood_tbl_nm)
        
        #=======================================================================
        # get data
        #=======================================================================
        ftbl_o = self.ftblos_d[self.flood_tbl_nm] #get the activated flood table object
        ftbl_o.apply_on_binv('aprot_df', 'area_prot_lvl')

        return True
    
    def set_fhr(self): #assign the fhz bfe and zone from the fhr_tbl data
        logger = self.logger.getChild('set_fhr')
        logger.debug('assigning for \'fhz\' and \'bfe\'')
        
        
        #get the data for this fhr set
        fhr_tbl_o = self.fdmgo_d['fhr_tbl']
        try:
            df = fhr_tbl_o.d[self.fhr_nm]
        except:
            if not self.fhr_nm in list(fhr_tbl_o.d.keys()):
                logger.error('could not find selected fhr_nm \'%s\' in the loaded rule sets: \n %s'
                             %(self.fhr_nm, list(fhr_tbl_o.d.keys())))
                raise IOError
        
        
        #=======================================================================
        # loop through each series and apply
        #=======================================================================
        """
        not the most generic way of handling this... 
        
        todo:
        add generic method to the binv 
            can take ser or df
            
            updates the childmeta_df if before init
            updates the children if after init
        """
        for hse_attn in ['fhz', 'bfe']:
            ser = df[hse_attn]

        
            if not self.session.state == 'init':
                #=======================================================================
                # tell teh binv to update its houses
                #=======================================================================
                self.binv.set_all_hse_atts(hse_attn, ser = ser)
                
            else:
                logger.debug('set column \'%s\' onto the binv_df'%hse_attn)
                self.binv.childmeta_df.loc[:,hse_attn] = ser #set this column in teh binvdf
        
        """I dont like this
        fhr_tbl_o.apply_on_binv('fhz_df', 'fhz', coln = self.fhr_nm)
        fhr_tbl_o.apply_on_binv('bfe_df', 'bfe', coln = self.fhr_nm)"""
        
        return True
        
    def get_all_aeps_classic(self):   #get the list of flood aeps from the classic flood table format
        'kept this special syntax reader separate in case we want to change th eformat of the flood tables'
        
        flood_pars_df = self.session.pars_df_d['floods'] #load the data from the flood table
        
        fld_aep_l = flood_pars_df.loc[:, 'ari'].values #drop the 2 values and convert to a list 
        
        return fld_aep_l
        
    def run(self, **kwargs): #placeholder for simulation runs
        logger = self.logger.getChild('run')
        logger.debug('on run_cnt %i'%self.run_cnt)
        self.run_cnt += 1
        self.state='run'
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not isinstance(self.outpath, str):
                raise IOError
            
        

        logger.info('\n fdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmgfdmg')
        logger.info('for run_cnt %i'%self.run_cnt)
        
        self.calc_fld_set(**kwargs)
        
        
        return
        
    def setup_res_dxcol(self, #setup the results frame
                        fld_aep_l = None, 
                        #dmg_type_list = 'all', 
                        bid_l = None): 
        
        #=======================================================================
        # defaults
        #=======================================================================
        if bid_l == None:           bid_l = self.binv.bid_l       
        if fld_aep_l is None:       fld_aep_l = list(self.fld_aep_od.keys()) #just get all teh keys from the dictionary
        #if dmg_type_list=='all':    dmg_type_list = self.dmg_types 
        
        
        #=======================================================================
        # setup the dxind for writing
        #=======================================================================        
        lvl0_values = fld_aep_l 

        lvl1_values = self.dmg_df_cols #include extra reporting columns
        
        #fold these into a mdex (each flood_aep has all dmg_types)        
        columns = pd.MultiIndex.from_product([lvl0_values, lvl1_values], 
                                names=['flood_aep','hse_atts'])
        
        dmg_dx = pd.DataFrame(index = bid_l, columns = columns).sort_index() #make the frame
        
        self.dmg_dx_base = dmg_dx.copy()
        
        if self.db_f:
            logger = self.logger.getChild('setup_res_dxcol')
            
            if self.write_beg_hist:
                fld_aep_l.sort()
                columns = pd.MultiIndex.from_product([fld_aep_l, ['egrd', 'cond']], 
                        names=['flood_aep','egrd'])
                        
                
                self.beg_hist_df = pd.DataFrame(index=bid_l, columns = columns)
                logger.info('recording bsmt_egrd history with %s'%str(self.beg_hist_df.shape))
            else:
                self.beg_hist_df = None
        
        """
        dmg_dx.columns
        """
        
        return 
      
    def calc_fld_set(self,  #calc flood damage for the flood set
                    fld_aep_l = None, #list of flood aeps to calcluate
                    #dmg_type_list = 'all',  #list of damage types to calculate
                    bid_l = None, #list of building names ot calculate
                    wsl_delta = None, #delta value to add to all wsl 
                    wtf = None, #optinonal flag to control writing of dmg_dx (otherwise session.write_fdmg_set_dx is used) 
                    **run_fld): #kwargs to send to run_fld 
        
        'we could separate the object creation and the damage calculation'
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        fld_aep_l:    list of floods to calc
            this can be a custom list built by the user
            extracted from the flood table (see session.get_ftbl_aeps)
            loaded from the legacy rfda pars (session.rfda_pars.fld_aep_l)\
            
        bid_l: list of ids (matching the mind varaible set under Fdmg)
        
        #=======================================================================
        # OUTPUTS
        #=======================================================================
        dmg_dx: dxcol of flood damage across all dmg_types and floods
            mdex
                lvl0:    flood aep 
                lvl1:    dmg_type + extra cols
                    I wanted to have this flexible, so the dfunc could pass up extra headers
                    couldnt get it to work. instead used a global list and  acheck
                    new headers must be added to the gloabl list and Dfunc.
                
                
            index
                bldg_id
                
        #=======================================================================
        # TODO:
        #=======================================================================
        setup to calc across binvs as well
        """
        #=======================================================================
        # defaults
        #=======================================================================
        start = time.time()
        logger = self.logger.getChild('calc_fld_set')
        
        
        if wtf is None:       wtf = self.session.write_fdmg_set_dx
        if wsl_delta is None: wsl_delta=  self.wsl_delta
        

        #=======================================================================
        # setup and load the results frame
        #=======================================================================
        #check to see that all of these conditions pass
        if not np.all([bid_l is None, fld_aep_l is None]):
            logger.debug('non default run. rebuild the dmg_dx_base')
            #non default run. rebuild the frame
            self.setup_res_dxcol(   fld_aep_l = fld_aep_l, 
                                    #dmg_type_list = dmg_type_list,
                                    bid_l = bid_l)

        elif self.dmg_dx_base is None:  #probably the first run
            if not self.run_cnt == 1: raise IOError
            logger.debug('self.dmg_dx_base is None. rebuilding')
            self.setup_res_dxcol(fld_aep_l = fld_aep_l, 
                                    #dmg_type_list = dmg_type_list,
                                    bid_l = bid_l) #set it up with the defaults
            
        dmg_dx = self.dmg_dx_base.copy() #just start witha  copy of the base
            
        
        #=======================================================================
        # finish defaults
        #=======================================================================
        'these are all mostly for reporting'
               
        if fld_aep_l is None:       fld_aep_l = list(self.fld_aep_od.keys()) #just get all teh keys from the dictionary
        """ leaving these as empty kwargs and letting floods handle
        if bid_l == None:           bid_l = binv_dato.bid_l
        if dmg_type_list=='all':    dmg_type_list = self.dmg_types """
        
        """
        lvl0_values = dmg_dx.columns.get_level_values(0).unique().tolist()
        lvl1_values = dmg_dx.columns.get_level_values(1).unique().tolist()"""
        
        logger.info('calc flood damage (%i) floods w/ wsl_delta = %.2f'%(len(fld_aep_l), wsl_delta))
        logger.debug('ffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffffff \n')
       
        #=======================================================================
        # loop and calc eacch flood
        #=======================================================================
        fcnt = 0
        first = True
        for flood_aep in fld_aep_l: #lopo through and build each flood
            #self.session.prof(state='%s.fdmg.calc_fld_set.%i'%(self.get_id(), fcnt)) #memory profiling
            
            self.state = flood_aep 
            'useful for keeping track of what the model is doing'
            #get teh flood
            flood_dato = self.fld_aep_od[flood_aep] #pull thsi from the dictionary
            logger.debug('getting dmg_df for %s'%flood_dato.name)
            
            #===================================================================
            # run sequence
            #===================================================================
            #get damage for these depths            
            dmg_df = flood_dato.run_fld(**run_fld)  #add the damage df to this slice
            
            if dmg_df is None: continue #skip this one
            
            #===================================================================
            # wrap up
            #===================================================================
           
            dmg_dx[flood_aep] = dmg_df  #store into the frame
            
            fcnt += 1
            
            logger.debug('for flood_aep \'%s\' on fcnt %i got dmg_df %s \n'%(flood_aep, fcnt, str(dmg_df.shape)))
            
            #===================================================================
            # checking
            #===================================================================
            if self.db_f:
                #check that the floods are increasing
                if first:
                    first = False
                    last_aep = None
                else:
                    if not flood_aep > last_aep:
                        raise IOError
                last_aep = flood_aep

        #=======================================================================
        # wrap up
        #=======================================================================
        self.state = 'na' 
        
        if wtf:
            filetail = '%s %s %s %s res_fld'%(self.session.tag, self.simu_o.name, self.tstep_o.name, self.name)
            filepath = os.path.join(self.outpath, filetail)
            hp_pd.write_to_file(filepath, dmg_dx, overwrite=True, index=True) #send for writing
            
        self.dmg_dx = dmg_dx
        

        
        stop = time.time()
        
        logger.info('in %.4f secs calcd damage on %i of %i floods'%(stop - start, fcnt, len(fld_aep_l)))
        
        
        return 
    
    def get_results(self): #called by Timestep.run_dt()
        
        self.state='wrap'
        logger = self.logger.getChild('get_results')
        
        #=======================================================================
        # optionals
        #=======================================================================
        s = self.session.outpars_d[self.__class__.__name__]
        
        if (self.session.write_fdmg_fancy) or (self.session.write_fdmg_sum):
            logger.debug("calc_summaries \n")
            dmgs_df = self.calc_summaries()
            self.dmgs_df = dmgs_df.copy()
            
        else: dmgs_df = None
            
        if ('ead_tot' in s) or ('dmg_df' in s):
            logger.debug('\n')
            self.calc_annulized(dmgs_df = dmgs_df, plot_f = False)
            'this will also run calc_sumamries if it hasnt happened yet'
            
        if 'dmg_tot' in s:
            #get a cross section of the 'total' column across all flood_aeps and sum for all entries
            self.dmg_tot = self.dmg_dx.xs('total', axis=1, level=1).sum().sum()
            

        if ('bwet_cnt' in s) or ('bdamp_cnt' in s) or ('bdry_cnt' in s):
            logger.debug('get_fld_begrd_cnt')
            self.get_fld_begrd_cnt()
        
        if 'fld_pwr_cnt' in s:
            logger.debug('calc_fld_pwr_cnt \n')
            cnt = 0
            for aep, obj in self.fld_aep_od.items():
                if obj.gpwr_f: cnt +=1
            
            self.fld_pwr_cnt = cnt   
            
        self.binv.calc_binv_stats()
        
        if self.session.write_fdmg_fancy:
            self.write_res_fancy()
        
        if self.write_fdmg_sum_fly: #write the results after each run
            self.write_dmg_fly()
            
        #update the bdmg_dx
        if not self.session.bdmg_dx is None:

           
            #add the timestep
            bdmg_dx = pd.concat([self.dmg_dx], 
                                keys=[self.tstep_o.name],
                                names=['tstep'], 
                                axis=1,verify_integrity=True,copy=False)
            
            bdmg_dx.index.name = self.mind
            
            """trying this as a column so we can append
            #add the sim
            bdmg_dx = pd.concat([bdmg_dx], 
                                keys=[self.simu_o.name],
                                names=['simu'], 
                                axis=1,verify_integrity=True,copy=False)"""
            
            #join to the big
            if len(self.session.bdmg_dx) == 0:
                self.session.bdmg_dx = bdmg_dx.copy() 
            else:
                self.session.bdmg_dx = self.session.bdmg_dx.join(bdmg_dx)
                
                """
                view(self.session.bdmg_dx.join(bdmg_dx))
                view(bdmg_dx)
                view(self.session.bdmg_dx)
                """

            
        #=======================================================================
        # checks
        #=======================================================================
        
        if self.db_f: 
            self.check_dmg_dx()
                        
        logger.debug('finished \n')
        
    def calc_summaries(self, #annualize the damages
                       fsts_l = ['gpwr_f', 'dmg_sw', 'dmg_gw'], #list of additional flood attributes to report in teh summary
                       dmg_dx=None, 
                       plot=False, #flag to execute plot_dmgs() at the end. better to do this explicitly with an outputr 
                       wtf=None): 
        """
        basically dropping dimensions on the outputs and adding annuzlied damages
        #=======================================================================
        # OUTPUTS
        #=======================================================================
        DROP BINV DIMENSIOn
        dmgs_df:    df with 
            columns: raw damage types, and annualized damage types
            index: each flood
            entries: total damage for binv
            
        DROP FLOODS DIMENSIOn
        aad_sum_ser
        
        DROP ALL DIMENSIONS
        ead_tot
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('calc_summaries')
        if dmg_dx is None:  dmg_dx = self.dmg_dx.copy()
        if plot is None:    plot = self.session._write_figs
        if wtf is None:     wtf = self.write_fdmg_sum
        
        
        #=======================================================================
        # #setup frame
        #=======================================================================        
        #get the columns
        dmg_types = list(self.dmg_types) + ['total']
        
        #=======================================================================
        # #build the annualized damage type names
        #=======================================================================
        admg_types = []
        for entry in dmg_types: admg_types.append(entry+'_a')
            
        cols = dmg_types + ['prob', 'prob_raw'] + admg_types + fsts_l
        

        
        dmgs_df = pd.DataFrame(columns = cols)
        dmgs_df['ari'] = dmg_dx.columns.get_level_values(0).unique()
        dmgs_df = dmgs_df.sort_values('ari').reset_index(drop=True)
        
        #=======================================================================
        # loop through and fill out the data
        #=======================================================================
        for index, row in dmgs_df.iterrows(): #loop through an dfill out
            
            dmg_df = dmg_dx[row['ari']] #get the fdmg for this aep
            
            #sum all the damage types
            for dmg_type in dmg_types: 
                row[dmg_type] = dmg_df[dmg_type].sum() #sum them all up
                       
            #calc the probability
            row['prob_raw'] = 1/float(row['ari']) #inverse of aep
            row['prob'] = row['prob_raw'] * self.fprob_mult #apply the multiplier
            
            #calculate the annualized damages
            for admg_type in admg_types: 
                dmg_type  = admg_type[:-2] #drop the a
                row[admg_type] = row[dmg_type] * row['prob']
                
            #===================================================================
            # get stats from the floodo
            #===================================================================
            floodo = self.fld_aep_od[row['ari']]
            
            for attn in fsts_l:
                row[attn] = getattr(floodo, attn)
                
            #===================================================================
            # #add this row backinto the frame
            #===================================================================
            dmgs_df.loc[index,:] = row
            
        #=======================================================================
        # get series totals
        #=======================================================================
        
        dmgs_df = dmgs_df.sort_values('prob').reset_index(drop='true')
        #=======================================================================
        # closeout
        #=======================================================================
        logger.debug('annualized %i damage types for %i floods'%(len(dmg_type), len(dmgs_df)))
        
        if wtf:
            filetail = '%s dmg_sumry'%(self.session.state)
            filepath = os.path.join(self.outpath, filetail)
            hp_pd.write_to_file(filepath, dmgs_df, overwrite=True, index=False) #send for writing
            
        
        logger.debug('set data with %s and cols: %s'%(str(dmgs_df.shape), dmgs_df.columns.tolist()))
        
        if plot: 
            self.plot_dmgs(wtf=wtf)
        
        #=======================================================================
        # post check
        #=======================================================================
        if self.db_f:
                #check for sort logic
            if not dmgs_df.loc[:,'prob'].is_monotonic: 
                raise IOError
            
            if not dmgs_df['total'].iloc[::-1].is_monotonic: #flip the order 
                logger.warning('bigger floods arent causing more damage')
                'some of the flood tables seem bad...'
                #raise IOError
            
            #all probabilities should be larger than zero
            if not np.all(dmgs_df.loc[:,'prob'] > 0): 
                raise IOError 
            
        return dmgs_df
    
    def calc_annulized(self, dmgs_df = None,
                       ltail = None, rtail = None, plot_f=None,
                       dx = 0.001): #get teh area under the damage curve
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        ltail: left tail treatment code (low prob high damage)
            flat: extend the max damage to the zero probability event
            'none': don't extend the tail
            
        rtail: right trail treatment (high prob low damage)
            'none': don't extend
            '2year': extend to zero damage at the 2 year aep

        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('calc_annulized')
        if ltail is None: ltail = self.ca_ltail
        if rtail is None: rtail = self.ca_rtail
        'plotter ignores passed kwargs here'
        
        if plot_f is None: plot_f=  self.session._write_figs
        
        #=======================================================================
        # get data
        #=======================================================================
        if dmgs_df is None:
            dmgs_df = self.calc_summaries()
        #df_raw = self.data.loc[:,('total', 'prob', 'ari')].copy().reset_index(drop=True)
        'only slicing columns for testing'
        
        df = dmgs_df.copy().reset_index(drop=True)
        
        #=======================================================================
        # shortcuts
        #=======================================================================
        if len(df) <2 :
            logger.warning('not enough floods to calculate EAD')
            self.ead_tot = 0
            self.dmgs_df_wtail = df
            return
        
        if df['total'].sum() < 1:
            logger.warning('calculated zero damages!')
            self.ead_tot = 0
            self.dmgs_df_wtail = df
            return

        logger.debug("with ltail = \'%s\', rtail = \'%s\' and df %s"%(ltail, rtail, str(df.shape)))

        #=======================================================================
        # left tail treatment
        #=======================================================================
        if ltail == 'flat':
            #zero probability
            'assume 1000yr flood is the max damage'
            max_dmg = df['total'].max()*1.0001
            
            df.loc[-1, 'prob'] = 0
            df.loc[-1, 'ari'] = 999999
            df.loc[-1, 'total'] = max_dmg
            
            logger.debug('ltail == flat. duplicated danage %.2f at prob 0'%max_dmg)

        elif ltail == 'none':
            pass            
        else: raise IOError
        
        'todo: add option for value multiplier'
        
        #=======================================================================
        # right tail
        #=======================================================================
        if rtail == 'none':
            pass

            
        elif hp_basic.isnum(rtail):
            
            rtail_yr = float(rtail)
            rtail_p = 1.0 / rtail_yr
            
            max_p = df['prob'].max()
            
            #floor check
            if rtail_p < max_p: 
                logger.error('rtail_p (%.2f) < max_p (%.2f)'%(rtail_p, max_p))
                raise IOError
            
            #same
            elif rtail_p == max_p:
                logger.debug("rtail_p == min(xl. no changes made")

            else:
                logger.debug("adding zero damage for aep = %.1f"%rtail_yr)
                #zero damage
                'assume no damage occurs at the passed rtail_yr'

                loc = len(df)
                df.loc[loc, 'prob'] = rtail_p
                df.loc[loc, 'ari'] = 1.0/rtail_p
                df.loc[loc, 'total'] = 0
                
                """
                hp_pd.view_web_df(self.data)
                """
            
        else: raise IOError
        

        #=======================================================================
        # clean up
        #=======================================================================
        df = df.sort_index() #resort the index
        
        if self.db_f:
            'these should still hold'
            if not df.loc[:,'prob'].is_monotonic: 
                raise IOError
            
            """see above
            if not df['total'].iloc[::-1].is_monotonic: 
                raise IOError"""
            
        x, y = df['prob'].values.tolist(), df['total'].values.tolist()
            

        #=======================================================================
        # find area under curve
        #=======================================================================
        try:
            #ead_tot = scipy.integrate.simps(y, x, dx = dx, even = 'avg')
            'this was giving some weird results'
            ead_tot = scipy.integrate.trapz(y, x, dx = dx)
        except:
            raise Error('scipy.integrate.trapz failed')
            
            
        logger.info('found ead_tot = %.2f $/yr from %i points with tail_codes: \'%s\' and \'%s\''
                    %(ead_tot, len(y), ltail, rtail))
        
        self.ead_tot = ead_tot
        #=======================================================================
        # checks
        #=======================================================================
        if self.db_f:
            if pd.isnull(ead_tot):
                raise IOError
            
            if not isinstance(ead_tot, float):
                raise IOError
            
            if ead_tot <=0:
                """
                view(df)
                """
                raise Error('got negative damage! %.2f'%ead_tot)   
        #=======================================================================
        # update data with tails
        #=======================================================================
        self.dmgs_df_wtail = df.sort_index().reset_index(drop=True)
        
        #=======================================================================
        # generate plot
        #=======================================================================
        if plot_f: 
            self.plot_dmgs(self, right_nm = None, xaxis = 'prob', logx = False)
            
        return
    
    def get_fld_begrd_cnt(self): #tabulate the bsmt_egrd counts from each flood
        logger = self.logger.getChild('get_fld_begrd_cnt')
        
        #=======================================================================
        # data setup
        #=======================================================================
        dmg_dx = self.dmg_dx.copy()
        
        #lvl1_values = dmg_dx.columns.get_level_values(0).unique().tolist()
        
        #get all teh basement egrade types
        df1 =  dmg_dx.loc[:,idx[:, 'bsmt_egrd']] #get a slice by level 2 values
        
        #get occurances by value
        d = hp_pd.sum_occurances(df1, logger=logger)
        
        #=======================================================================
        # loop and calc
        #=======================================================================
        logger.debug('looping through %i bsmt_egrds: %s'%(len(d), list(d.keys())))
        for bsmt_egrd, cnt in d.items():
            attn = 'b'+bsmt_egrd +'_cnt'
            
            logger.debug('for \'%s\' got %i'%(attn, cnt))
            
            setattr(self, attn, cnt)
        
        logger.debug('finished \n')
        
    def check_dmg_dx(self): #check logical consistency of the damage results
        logger = self.logger.getChild('check_dmg_dx')
        
        #=======================================================================
        # data setup
        #=======================================================================
        dmg_dx = self.dmg_dx.copy()
        
        mdex = dmg_dx.columns
        
        
        aep_l = mdex.get_level_values(0).astype(int).unique().values.tolist()
        aep_l.sort()
        
        
        #=======================================================================
        # check that each flood increases in damage
        #=======================================================================
        total = None
        aep_last = None
        for aep in aep_l:
            #get this slice
            df = dmg_dx[aep]
            
            if total is None:
                boolcol = np.isin(df.columns, ['MS', 'MC', 'BS', 'BC', 'GS']) #identify damage columns
                total = df.loc[:,boolcol].sum().sum()
                
                
                
                if not aep == min(aep_l):
                    raise IOError
                
            else:
                
                newtot = df.loc[:,boolcol].sum().sum()
                if not newtot >= total: 
                    logger.warning('aep %s tot %.2f < aep %s %.2f'%(aep, newtot, aep_last, total))
                    #raise IOError
                #print 'new tot %.2f > oldtot %.2f'%(newtot, total)
                total = newtot
                
            aep_last = aep
            
            
        
        return
    
    def check_acodes(self, #check you have curves for all the acodes
                     ac_sec_d = None, #set of Loaded acodes {acode: asecotr}
                     ac_req_l = None, #set of requested acodes
                     dfunc_df = None, #contorl file page for the dfunc parameters
                     ):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('check_acodes')
        if ac_sec_d is None: ac_sec_d = self.acode_sec_d
        if ac_req_l is None: ac_req_l = self.binv.acode_l #pull from the binv
        if dfunc_df is None: dfunc_df = self.session.pars_df_d['dfunc']
        
        log.debug('checking acodes requested by binv against %i available'%len(ac_sec_d))
        
        """
        for k, v in ac_sec_d.items():
            print(k, v)
        """
        #=======================================================================
        # conversions
        #=======================================================================
        ava_ar = np.array(list(ac_sec_d.keys())) #convert availables to an array
        req_ar = np.array(ac_req_l)
        
        #get the pars set
        pars_ar_raw = dfunc_df['acode'].dropna().unique()
        pars_ar = pars_ar_raw[pars_ar_raw!='none'] #drop the nones
        
        #=======================================================================
        # check we loaded everything we requested in the pars
        #=======================================================================
        boolar = np.invert(np.isin(pars_ar, ava_ar))
        
        if np.any(boolar):
            raise Error('%i acodes requested  by the pars were not loaded: \n    %s'
                          %(boolar.sum(), req_ar[boolar]))
        
        
        #=======================================================================
        # check the binv doesnt have anything we dont have pars for
        #=======================================================================
        boolar = np.invert(np.isin(req_ar, pars_ar))
        
        if np.any(boolar):
            raise Error('%i binv acodes not found on the \'dfunc\' tab: \n    %s'
                          %(boolar.sum(), req_ar[boolar]))
        

            
        return
        
        

        
            

    def wrap_up(self):
        
        #=======================================================================
        # update asset containers
        #=======================================================================
        """
        #building inventory
        'should be flagged for updating during House.notify()'
        if self.binv.upd_kid_f: 
            self.binv.update()"""
            
        """dont think we need this here any more.. only on udev.
        keeping it just to be save"""
        
            
        self.last_tstep = copy.copy(self.time)
        self.state='close'

    def write_res_fancy(self,  #for saving results in xls per tab. called as a special outputr
                        dmg_dx=None, 
                        include_ins = False,
                        include_raw = False,
                        include_begh = True): 
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        include_ins: whether ot add inputs as tabs.
            ive left this separate from the 'copy_inputs' flag as it is not a true file copy of the inputs
            
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('write_res_fancy')
        if dmg_dx is None: dmg_dx = self.dmg_dx
        if dmg_dx is None: 
            logger.warning('got no dmg_dx. skipping')
            return 
        
        #=======================================================================
        # setup
        #=======================================================================
        od = OrderedDict()
        
        #=======================================================================
        # add the parameters
        #=======================================================================
        #get the blank frame
        df = pd.DataFrame(columns = ['par','value'] )
        df['par'] = list(self.try_inherit_anl)

        for indx, row in df.iterrows():
            df.iloc[indx, 1] = getattr(self, row['par']) #set this value
            
        od['pars'] = df
            
        
        #=======================================================================
        # try and add damage summary
        #=======================================================================
        if not self.dmgs_df is None:
            od['dmg summary'] = self.dmgs_df
        
        #=======================================================================
        # #get theh dmg_dx decomposed        
        #=======================================================================
        od.update(hp_pd.dxcol_to_df_set(dmg_dx, logger=self.logger))
               
        
        #=======================================================================
        # #add dmg_dx as a raw tab
        #=======================================================================
        if include_raw:
            od['raw_res'] = dmg_dx

        #=======================================================================
        # add inputs
        #=======================================================================
        if include_ins:
            for dataname, dato in self.kids_d.items():
                if hasattr(dato, 'data') & hp_pd.isdf(dato.data):
                    od[dataname] = dato.data
                    
                    
        #=======================================================================
        # add debuggers
        #=======================================================================
        if include_begh:
            if not self.beg_hist_df is None:
                od['beg_hist'] = self.beg_hist_df
            

                   
        #=======================================================================
        # #write to excel
        #=======================================================================
        filetail = '%s %s %s %s fancy_res'%(self.session.tag, self.simu_o.name, self.tstep_o.name, self.name)

        filepath = os.path.join(self.outpath, filetail)
        hp_pd.write_dfset_excel(od, filepath, engine='xlsxwriter', logger=self.logger)

        return
    
    def write_dmg_fly(self): #write damage results after each run
        
        logger = self.logger.getChild('write_dmg_fly')
        
        dxcol = self.dmg_dx #results
        
        #=======================================================================
        # build the resuults summary series
        #=======================================================================
        
        #get all the flood aeps
        lvl0vals = dxcol.columns.get_level_values(0).unique().astype(int).tolist()
        
        #blank holder
        res_ser = pd.Series(index = lvl0vals)
        
        #loop and calc sums for each flood
        for aep in lvl0vals:
            res_ser[aep] = dxcol.loc[:,(aep,'total')].sum()
        
        #add extras
        if not self.ead_tot is None:
            res_ser['ead_tot'] = self.ead_tot
                
        
        res_ser['dt'] = self.tstep_o.year
        res_ser['sim'] = self.simu_o.ind
        
        
        lindex = '%s.%s'%(self.simu_o.name, self.tstep_o.name)
        
        
        hp_pd.write_fly_df(self.fly_res_fpath,res_ser,  lindex = lindex,
                   first = self.write_dmg_fly_first, tag = 'fdmg totals', 
                   db_f = self.db_f, logger=logger) #write results on the fly
    
        self.write_dmg_fly_first = False
        
        return

    def get_plot_kids(self): #raise kids for plotting the damage summaries
        logger = self.logger.getChild('get_plot_kids')
        #=======================================================================
        # get slice of aad_fmt_df matching the aad cols
        #=======================================================================
        aad_fmt_df = self.session.pars_df_d['dmg_sumry_plot'] #pull teh formater pars from the tab
      
        dmgs_df = self.dmgs_df
        self.data = dmgs_df
        
        boolidx = aad_fmt_df.loc[:,'name'].isin(dmgs_df.columns) #get just those formaters with data in the aad
        
        aad_fmt_df_slice = aad_fmt_df[boolidx] #get this slice3
        
        """
        hp_pd.view_web_df(self.data)
        hp_pd.view_web_df(df)
        hp_pd.view_web_df(aad_fmt_df_slice)
        aad_fmt_df_slice.columns
        """

        #=======================================================================
        # formatter kids setup
        #=======================================================================
        """need to run this every time so the data is updated
        TODO: allow some updating here so we dont have to reduibl deach time
        if self.plotter_kids_dict is None:"""
        self.plotr_d = self.raise_children_df(aad_fmt_df_slice, kid_class = hp_data.Data_o)
            
        logger.debug('finisehd \n')
                 
#===============================================================================
#     def plot_dmgs(self, wtf=None, right_nm = None, xaxis = 'ari', logx = True,
#                   ylims = None, #tuple of min/max values for the y-axis
#                   ): #plot curve of aad
#         """
#         see tab 'aad_fmt' to control what is plotted and formatting
#         """
#         #=======================================================================
#         # defaults
#         #=======================================================================
#         logger = self.logger.getChild('plot_dmgs')
#         if wtf == None: wtf = self.session._write_figs
#         
#         #=======================================================================
#         # prechecks
#         #=======================================================================
#         if self.db_f:
#             if self.dmgs_df is None:
#                 raise IOError
#             
# 
#         #=======================================================================
#         # setup
#         #=======================================================================
#         if not ylims is None:
#             try:
#                 ylims = eval(ylims)
#             except:
#                 pass
#             
#         #get the plot workers
#         if self.plotr_d is None: 
#             self.get_plot_kids()
#             
#         kids_d = self.plotr_d
#         
#         title = '%s-%s-%s EAD-ARI plot on %i objs'%(self.session.tag, self.simu_o.name, self.name, len(self.binv.childmeta_df))
#         logger.debug('with \'%s\''%title)
#         
#         if not self.tstep_o is None:
#             title = title + ' for %s'%self.tstep_o.name
#         
#         #=======================================================================
#         # update plotters
#         #=======================================================================
#         logger.debug('updating plotters with my data')
# 
#         #get data
#         data_og = self.data.copy() #store this for later
#         
#         if self.dmgs_df_wtail is None:
#             df = self.dmgs_df.copy()
#         else:
#             df = self.dmgs_df_wtail.copy()
#         
#         df = df.sort_values(xaxis, ascending=True)
#   
#         #reformat data
#         df.set_index(xaxis, inplace = True)
#         
#         #re set
#         self.data = df
#         
#         #tell kids to refresh their data from here
#         for gid, obj in kids_d.items(): obj.data = obj.loadr_vir()
#              
#         self.data = data_og #reset the data
#         
#         #=======================================================================
#         # get annotation
#         #=======================================================================
#         val_str = '$' + "{:,.2f}".format(self.ead_tot/1e6)
#         #val_str = "{:,.2f}".format(self.ead_tot)
#         """
#         txt = 'total aad: $%s \n tail kwargs: \'%s\' and \'%s\' \n'%(val_str, self.ca_ltail, self.ca_rtail) +\
#                 'binv.cnt = %i, floods.cnt = %i \n'%(self.binv.cnt, len(self.fld_aep_od))"""
#          
# 
#         txt = 'total EAD = %s'%val_str        
#             
#                 
#         #=======================================================================
#         #plot the workers
#         #=======================================================================
#         #twinx
#         if not right_nm is None:
#             logger.debug('twinning axis with name \'%s\''%right_nm)
#             title = title + '_twin'
#             # sort children into left/right buckets by name to plot on each axis
#             right_pdb_d, left_pdb_d = self.sort_buckets(kids_d, right_nm)
#             
#             if self.db_f:
#                 if len (right_pdb_d) <1: raise IOError
#             
#             #=======================================================================
#             # #send for plotting
#             #=======================================================================
#             'this plots both bundles by their data indexes'
#             ax1, ax2 = self.plot_twinx(left_pdb_d, right_pdb_d, 
#                                        logx=logx, xlab = xaxis, title=title, annot = txt,
#                                        wtf=False)
#             'cant figure out why teh annot is plotting twice'
#             
#             ax2.set_ylim(0, 1) #prob limits
#             legon = False
#         else:
#             logger.debug('single axis')
#             
#             try:
#                 del kids_d['prob']
#             except:
#                 pass
#             
#             pdb = self.get_pdb_dict(list(kids_d.values()))
#             
#             ax1 = self.plot_bundles(pdb,
#                                    logx=logx, xlab = 'ARI', ylab = 'damage ($ 10^6)', title=title, annot = txt,
#                                    wtf=False)
#             
#             legon=True
#         
#         #hatch
#         #=======================================================================
#         # post formatting
#         #=======================================================================
#         #set axis limits
#         if xaxis == 'ari': ax1.set_xlim(1, 1000) #aep limits
#         elif xaxis == 'prob': ax1.set_xlim(0, .6) 
#         
#         if not ylims is None:
#             ax1.set_ylim(ylims[0], ylims[1])
#         
# 
#         #ax1.set_ylim(0, ax1.get_ylim()[1]) #$ limits
#         
#         
#         #=======================================================================
#         # format y axis labels
#         #======================================================= ================
#         old_tick_l = ax1.get_yticks() #get teh old labels
#         
#         # build the new ticks
#         l = []
#         
#         for value in old_tick_l:
#             new_v = '$' + "{:,.0f}".format(value/1e6)
#             l.append(new_v)
#              
#         #apply the new labels
#         ax1.set_yticklabels(l)
#         
#         """
#         #add thousands comma
#         ax1.get_yaxis().set_major_formatter(
#             #matplotlib.ticker.FuncFormatter(lambda x, p: '$' + "{:,.2f}".format(x/1e6)))
# 
#             matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))"""
#         
#         if xaxis == 'ari':
#             ax1.get_xaxis().set_major_formatter(
#                 matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
#         
# 
#         if wtf: 
#             fig = ax1.figure
#             savepath_raw = os.path.join(self.outpath,title)
#             flag = hp.plot.save_fig(self, fig, savepath_raw=savepath_raw, dpi = self.dpi, legon=legon)
#             if not flag: raise IOError 
#             
# 
#         #plt.close()
#         return
#===============================================================================

class Flood( 
                hp_dyno.Dyno_wrap,
                hp_sim.Sim_o, 
                hp_oop.Parent,  #flood object worker
                hp_oop.Child): 
    
    #===========================================================================
    # program pars
    #===========================================================================
    
    gpwr_f          = False #grid power flag palceholder
    #===========================================================================
    # user defineid pars
    #===========================================================================
    ari             = None

    
    #loaded from flood table
    #area exposure grade. control for areas depth decision algorhithim based on the performance of macro structures (e.g. dykes).
    area_egrd00 = ''
    area_egrd01 = ''
    area_egrd02 = ''
    
    area_egrd00_code = None
    area_egrd01_code = None
    area_egrd02_code = None
    #===========================================================================
    # calculated pars
    #===========================================================================
    hdep_avg        = 0 #average house depth
    #damate properties
    total = 0
    BS = 0
    BC = 0
    MS = 0
    MC = 0
    dmg_gw = 0
    dmg_sw = 0
    
    dmg_df_blank =None
    
    wsl_avg = 0
    

    #===========================================================================
    # data containers
    #===========================================================================
    hdmg_cnt        = 0
    dmg_df = None
    dmg_res_df = None

    #bsmt_egrd counters. see get_begrd_cnt()
    bdry_cnt        = 0
    bwet_cnt        = 0
    bdamp_cnt       = 0


    def __init__(self, parent, *vars, **kwargs):
        logger = mod_logger.getChild('Flood')
        logger.debug('start _init_')
        #=======================================================================
        # #attach custom vars
        #=======================================================================
        self.inherit_parent_ans=set(['mind', 'dmg_types'])
        #=======================================================================
        # initilize cascade
        #=======================================================================
        super(Flood, self).__init__(parent, *vars, **kwargs) #initilzie teh baseclass 
        
        #=======================================================================
        # common setup
        #=======================================================================
        if self.sib_cnt == 0:
            #update the resets
            pass

        #=======================================================================
        # unique setup
        #=======================================================================
        """ handled by the outputr
        self.reset_d.update({'hdmg_cnt':0})"""
        self.ari = int(self.ari)
        self.dmg_res_df = pd.DataFrame() #set as an empty frame for output handling
        
        #=======================================================================
        # setup functions
        #=======================================================================
        self.set_gpwr_f()
        
        logger.debug('set_dmg_df_blank()')
        self.set_dmg_df_blank()
        
        logger.debug('get your water levels from the selected wsl table \n')
        self.set_wsl_frm_tbl()
        
        logger.debug('set_area_egrd()')
        self.set_area_egrd()
        
        logger.debug('get_info_from_binv()')
        df = self.get_info_from_binv() #initial run to set blank frame
        
        self.set_wsl_from_egrd(df)

        
        """ moved into set_wsl_frm_tbl()
        logger.debug('\n')
        self.setup_dmg_df()"""
        
        self.init_dyno()
        
        self.logger.debug('__init___ finished \n')
        
    def set_dmg_df_blank(self):
        
        logger = self.logger.getChild('set_dmg_df_blank')
        
        binv_df = self.model.binv.childmeta_df
        
        colns = OrderedSet(self.model.dmg_df_cols.tolist() + ['wsl', 'area_prot_lvl'])
        'wsl should be redundant'
        
        #get boolean
        self.binvboolcol = binv_df.columns.isin(colns) #store this for get_info_from_binv()
        
        #get teh blank frame
        self.dmg_df_blank = pd.DataFrame(columns = colns, index = binv_df.index) #get the blank frame
        'this still needs the wsl levels attached based on your area exposure grade'
        
        logger.debug('set dmg_df_blank with %s'%(str(self.dmg_df_blank.shape)))
        
        return

    def set_gpwr_f(self): #set your power flag
        
        if self.is_frozen('gpwr_f'): return True#shortcut for frozen
        
        logger = self.logger.getChild('set_gpwr_f')
        
        #=======================================================================
        # get based on aep
        #=======================================================================
        min_aep = int(self.model.gpwr_aep)
        
        if self.ari < min_aep:  gpwr_f = True
        else:                   gpwr_f = False
        
        logger.debug('for min_aep = %i, set gpwr_f = %s'%(min_aep, gpwr_f))
        
        #update handler
        self.handle_upd('gpwr_f', gpwr_f, proxy(self), call_func = 'set_gpwr_f')
        
        return True

    def set_wsl_frm_tbl(self, #build the raw wsl data from the passed flood table
                         flood_tbl_nm = None, #name of flood table to pull raw data from
                         #bid_l=None, 
                         ): 
        """
        here we get the raw values
        these are later modified by teh area_egrd with self.get_wsl_from_egrd()
        #=======================================================================
        # INPUTS
        #=======================================================================
        flood_tbl_df_raw:    raw df of the classic flood table
            columns:`    count, aep, aep, aep, aep....\
            real_columns:    bldg_id, bid, depth, depth, depth, etc...
            index:    unique arbitrary
            
        wsl_ser: series of wsl for this flood on each bldg_id
        
        #=======================================================================
        # calls
        #=======================================================================
        dynp handles Fdmg.flood_tbl_nm
                    
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('set_wsl_frm_tbl')
        if flood_tbl_nm is None: flood_tbl_nm = self.model.flood_tbl_nm
        
        #=======================================================================
        # get data
        #=======================================================================
        #pull the raw flood tables
        ftbl_o = self.model.ftblos_d[flood_tbl_nm]
        wsl_d = ftbl_o.wsl_d
        
        df = pd.DataFrame(index = list(wsl_d.values())[0].index) #blank frame from teh first entry
        

        #=======================================================================
        # loop and apply for each flood type
        #=======================================================================
        for ftype, df1 in wsl_d.items():
            
            #=======================================================================
            # data checks
            #=======================================================================
            if self.db_f:
                if not ftype in ['wet', 'dry', 'damp']: 
                    raise IOError
                df_raw =df1.copy()
                
                if not self.ari in df_raw.columns:
                    logger.error('the flood provided on the \'floods\' tab (\'%s\') does not have a match in the flood table: \n %s'%
                                 (self.ari, self.model.ftblos_d[flood_tbl_nm].filepath))
                    raise IOError
                
            #=======================================================================
            # slice for this flood
            #=======================================================================
            boolcol = df1.columns == self.ari #slice for this aep
                
            #get the series for this 
            wsl_ser = df1.loc[:, boolcol].iloc[:,0].astype(float)
    
            #wsl_ser = wsl_ser.rename(ftype) #rename with the aep
            
            'binv slicing moved to Flood_tbl.clean_data()'
            
            #=======================================================================
            # checks
            #=======================================================================
            if self.db_f:
                if len(wsl_ser) <1: 
                    raise IOError
                
                """ allowing
                #check for nuls
                if np.any(pd.isnull(wsl_ser2)):
                    raise IOError"""
                
                
            #=======================================================================
            # wrap up report and attach
            #======================================================================= 
            df[ftype] = wsl_ser
                       
            logger.debug('from \'%s\' for \'%s\' got wsl_ser %s for aep: %i'
                         %(flood_tbl_nm, ftype, str(wsl_ser.shape), self.ari))
            

        self.wsl_df = df #set this
        
        'notusing dy nps'
        if self.session.state == 'init':
            self.reset_d['wsl_df'] = df.copy()
        

        return True

    def set_area_egrd(self): #pull your area exposure grade from somewhere
        """
        #=======================================================================
        # calls
        #=======================================================================
        self.__init__()
        dynp handles: Fdmg.flood_tbl_nm (just in case we are pulling from there
        """
        #=======================================================================
        # dependency check
        #=======================================================================
        if not self.session.state=='init':
                
            dep_l =  [([self.model], ['set_area_prot_lvl'])]
            
            if self.deps_is_dated(dep_l, method = 'reque', caller = 'set_area_egrd'):
                return False
            
        
        logger          = self.logger.getChild('set_area_egrd')
        
        #=======================================================================
        # steal egrd from elsewhere table if asked       
        #=======================================================================
        for cnt in range(0,3,1): #loop through each one
            attn = 'area_egrd%02d'%cnt
            
            area_egrd_code = getattr(self, attn + '_code')
            
            if area_egrd_code in ['dry', 'damp', 'wet']: 
                area_egrd = area_egrd_code

            #===================================================================
            # pull from teh flood table
            #===================================================================
            elif area_egrd_code == '*ftbl':
                ftbl_o = self.model.ftblos_d[self.model.flood_tbl_nm] #get the flood tabl object
                
                area_egrd = getattr(ftbl_o, attn) #get from teh table
                
            #===================================================================
            # pull from teh model
            #===================================================================
            elif area_egrd_code == '*model':
                area_egrd = getattr(self.model, attn) #get from teh table
                
            else:
                logger.error('for \'%s\' got unrecognized area_egrd_code: \'%s\''%(attn, area_egrd_code))
                raise IOError

            #===================================================================
            # set these
            #===================================================================
            self.handle_upd(attn, area_egrd, weakref.proxy(self), call_func = 'set_area_egrd')
            'this should triger generating a new wsl set to teh blank_dmg_df'

            logger.debug('set \'%s\' from \'%s\' as \'%s\''
                         %(attn, area_egrd_code,area_egrd))
            
            if self.db_f:
                if not area_egrd in ['dry', 'damp', 'wet']:
                    raise IOError
            
        return True
                
    def set_wsl_from_egrd(self,  #calculate the wsl based on teh area_egrd
                          df = None): 
        """
        This is a partial results retrival for non damage function results
        
        TODO: 
        consider checking for depednency on House.area_prot_lvl
        
        #=======================================================================
        # calls
        #=======================================================================
        self.__init__
        
        dynp handles for:
            Flood.area_egrd##
            Fdmg.flood_tbl_nm
                if area_egrd_code == *model, this loop isnt really necessary
        
        
        """
        #=======================================================================
        # check dependencies and frozen
        #=========================================================== ============
        if not self.session.state=='init':
                
            dep_l =  [([self], ['set_area_egrd', 'set_wsl_frm_tbl'])]
            
            if self.deps_is_dated(dep_l, method = 'reque', caller = 'set_wsl_from_egrd'):
                return False
                
                
        #=======================================================================
        # defaults
        #=======================================================================
        logger          = self.logger.getChild('set_wsl_from_egrd')
        #if wsl_delta is None: wsl_delta = self.model.wsl_delta
        
        #=======================================================================
        # get data
        #=======================================================================
        if df is None: df = self.get_info_from_binv()
        'need to have updated area_prot_lvls'
        
        #=======================================================================
        # precheck
        #=======================================================================
        if self.db_f:
            if not isinstance(df, pd.DataFrame): raise IOError
            if not len(df) > 0: raise IOError

        #=======================================================================
        # add the wsl for each area_egrd
        #=======================================================================
        for prot_lvl in range(0,3,1): #loop through each one
            #get your  grade fro this prot_lvl
            attn = 'area_egrd%02d'%prot_lvl            
            area_egrd = getattr(self, attn)
            
            #identify the housese for this protection level
            boolidx = df.loc[:,'area_prot_lvl'] == prot_lvl
            
            if boolidx.sum() == 0: continue
            
            #give them the wsl corresponding to this grade
            df.loc[boolidx, 'wsl'] = self.wsl_df.loc[boolidx,area_egrd]
            
            #set a tag for the area_egrd
            if 'area_egrd' in df.columns:
                df.loc[boolidx, 'area_egrd'] = area_egrd
            
            logger.debug('for prot_lvl %i, set %i wsl from \'%s\''%(prot_lvl, boolidx.sum(), area_egrd))
            
        #=======================================================================
        # set this
        #=======================================================================
        self.dmg_df_blank = df
        
        #=======================================================================
        # post check
        #=======================================================================
        logger.debug('set dmg_df_blank with %s'%str(df.shape))
        
        if self.session.state=='init':
            self.reset_d['dmg_df_blank'] = df.copy()
        
            
        if self.db_f:
            if np.any(pd.isnull(df['wsl'])):
                raise Error('got some wsl nulls')
            
        return True
    
        """
        hp_pd.v(df)
        hp_pd.v(self.dmg_df_blank)
        """
 
    def run_fld(self, **kwargs): #shortcut to collect all the functions for a simulation ru n
        
        self.run_cnt += 1
        
        dmg_df_blank = self.get_info_from_binv()
        
        """
        view(dmg_df_blank)
        """
        
        dmg_df = self.get_dmg_set(dmg_df_blank, **kwargs)
        
        if self.db_f: 
            self.check_dmg_df(dmg_df)
        
        'leaving this here for simplicity'
        self.calc_statres_flood(dmg_df)
        
        return dmg_df

    def get_info_from_binv(self):
    
        #=======================================================================
        # defaults
        #=======================================================================
        logger          = self.logger.getChild('get_info_from_binv')

        binv_df = self.model.binv.childmeta_df 
                   
        #pull static values
        binvboolcol = self.binvboolcol       
        df = self.dmg_df_blank.copy()
        'this should have wsl added to it from set_wsl_from_egrd()'
        
        if self.db_f:
            if not len(binvboolcol) == len(binv_df.columns):
                logger.warning('got length mismatch between binvboolcol (%i) and the binv_df columns (%i)'%
                             (len(binvboolcol), len(binv_df.columns)))
                'pandas will handle this mistmatch.. just ignores the end'
                
        
        #=======================================================================
        # #update with values from teh binv       
        #=======================================================================
        df.update(binv_df.loc[:,binvboolcol], overwrite=True) #update from all the values in teh binv

        logger.debug('retreived %i values from the binv_df on: %s'
                     %(binv_df.loc[:,binvboolcol].count().count(), binv_df.loc[:,binvboolcol].columns.tolist()))
        
        #=======================================================================
        # macro calcs
        #=======================================================================
        if 'hse_depth' in df.columns:
            df['hse_depth'] = df['wsl'] - df['anchor_el']
        
        #groudn water damage flag
        if 'gw_f' in df.columns:
            df.loc[:,'gw_f'] = df['dem_el'] > df['wsl'] #water is below grade
            
        if self.db_f:
            if 'bsmt_egrd' in binv_df.columns:
                raise IOError

        
        return df

    def get_dmg_set(self,  #calcluate the damage for each house
                    dmg_df, #pre-filled frame for calculating damage results onto
                    #dmg_type_list='all', 
                    #bid_l = None,
                    #wsl_delta = None,
                    dmg_rat_f =None, #includt eh damage ratio in results
                    ):  
        """
        20190521:
        I dont really like how this is structured with one mega for loop trying to grab everything.
        
        Instead, everything should be handled by Fdmg (which really should be wrapped back into the Session)
        
        Each calculation/value (e.g. damage, static values, etc.) should be calculated in a dedicated loop
            then we can control logic based on each value type
            
        the controller can collect all of these results during wrap up
            rather then trying to pass everything to each loop
        #=======================================================================
        # INPUTS
        #=======================================================================
        depth_ser: series of depths (for this flood) with index = bldg_id
        
        
        
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger          = self.logger.getChild('get_dmg_set(%s)'%self.get_id())

        if dmg_rat_f is None: dmg_rat_f = self.model.dmg_rat_f
        hse_od          = self.model.binv.hse_od  #ordred dictionary by bid: hse_dato
        

        #=======================================================================
        # pre checks
        #=======================================================================
        if self.db_f:
            if not isinstance(dmg_df, pd.DataFrame):
                raise IOError
            
            boolidx = dmg_df.index.isin(list(hse_od.keys()))
            if not np.all(boolidx):
                logger.error('some of the bldg_ids in the wsl_ser were not found in the binv: \n    %s'
                             %dmg_df.index[~boolidx])
                raise IOError
            
            #check the damage columns are empty
            boolcol = np.isin(dmg_df.columns, ['MS', 'MC', 'BS', 'BC', 'GS', 'total']) #identify damage columns
            
            if not np.all(pd.isnull(dmg_df.loc[:,boolcol])):
                raise IOError
        
        #=======================================================================
        # frame setup
        #=======================================================================
        #identify columns containing damage results
        dmgbool = np.logical_or(
            dmg_df.columns.isin(self.model.dmg_types), #damages
            pd.Series(dmg_df.columns).str.contains('_rat').values
            ) #damage ratios

        
        #=======================================================================
        # get teh damage for each house
        #=======================================================================
        logger.debug('getting damage for %s entries'%(str(dmg_df.shape)))

        """generally no memory added during these
        self.session.prof(state='%s.get_dmg_set.loop'%(self.name)) #memory profiling"""
        cnt = 0
        first = True
        for index, row in dmg_df.iterrows(): #loop through each row
            #===================================================================
            # pre-printouts
            #===================================================================
            #self.session.prof(state='%s.get_dmg_set.%i'%(self.name, cnt)) #memory profiling
            cnt +=1
            if cnt%self.session._logstep == 0: logger.info('    (%i/%i)'%(cnt, len(dmg_df)))
            
            #===================================================================
            # retrive info
            #===================================================================
            
            hse_obj = hse_od[index] #get this house object by bldg_id
            hse_obj.floodo = self #let the house know who is flooding it
            logger.debug('on hse \'%s\' '%hse_obj.name)

            #===================================================================
            # add damage results
            #===================================================================

            dmg_ser = hse_obj.run_hse(row['wsl'], dmg_rat_f = dmg_rat_f)
            
            row.update(dmg_ser) #add all these entries


            #===================================================================
            # extract extra attributers from teh house
            #===================================================================    
            #find the entries to skip attribute in filling
            if first:
                boolar = np.invert(np.logical_or( #find entries we dont want to try and get from the house
                    row.index.isin(['total']), #exclude the total column 
                    np.logical_or(
                        np.invert(pd.isnull(row)), #exclude reals
                        dmgbool #exclude damages
                        )))
                
                logger.debug('retrieving %i (of %i) attribute values on each house: \n    %s'
                             %(boolar.sum(),len(boolar), row.index[boolar].values.tolist()))
                
                first = False
            
            #fill thtese
            for attn, v in row[boolar].items(): 
                row[attn] = getattr(hse_obj, attn)
                

            #===================================================================
            # wrap up
            #===================================================================
            dmg_df.loc[index,:] = row #store this row back into the full resulst frame
            
        #=======================================================================
        # extract secondary attributes
        #=======================================================================
            
        """makes more sense to keep nulls as nulls
            as this means something different than a 'zero' damage
        #=======================================================================
        # set null damages to zero
        #=======================================================================
        for coln in ['BC', 'BS']:
            dmg_df.loc[:,coln] = dmg_df[coln].replace(to_replace=np.nan, value=0)"""
        #=======================================================================
        # macro stats
        #=======================================================================
        #total
        boolcol = dmg_df.columns.isin(self.model.dmg_types)
        dmg_df['total'] = dmg_df.iloc[:,boolcol].sum(axis = 1) #get the sum
        
        #=======================================================================
        # closeout and reporting
        #=======================================================================

        #print out summaries
        if not self.db_f:
            logger.info('finished for %i houses'%(len(dmg_df.index)))
        else:
            totdmg = dmg_df['total'].sum()
        
            totdmg_str = '$' + "{:,.2f}".format(totdmg)
            
            logger.info('got totdmg = %s for %i houses'%(totdmg_str,len(dmg_df.index)))
        
            if np.any(pd.isnull(dmg_df)):
                """
                allowing this now
                view(dmg_df[dmg_df.isna().any(axis=1)])
                """
                logger.warning('got %i nulls in the damage results'%dmg_df.isna().sum().sum())
                
            for dmg_type in self.model.dmg_types:
                dmg_tot = dmg_df[dmg_type].sum()
                dmg_tot_str = '$' + "{:,.2f}".format(dmg_tot)
                logger.debug('for dmg_type \'%s\' dmg_tot = %s'%(dmg_type, dmg_tot_str))
            
        return dmg_df
    
    
    def check_dmg_df(self, df):
        logger = self.logger.getChild('check_dmg_df')
        
        #=======================================================================
        # check totals
        #=======================================================================
        boolcol = np.isin(df.columns, ['MS', 'MC', 'BS', 'BC', 'GS']) #identify damage columns
        if not round(df['total'].sum(),2) == round(df.loc[:, boolcol].sum().sum(), 2):
            logger.error('total sum did not match sum from damages')
            raise IOError
        
    def calc_statres_flood(self, df): #calculate your statistics
        'running this always'
        logger = self.logger.getChild('calc_statres_flood')
        s = self.session.outpars_d[self.__class__.__name__]
        
        """needed?
        self.outpath =   os.path.join(self.model.outpath, self.name)"""
        
        #=======================================================================
        # total damage
        #=======================================================================
        for dmg_code in list(self.model.dmg_types) + ['total']:
            
            #loop through and see if the user asked for this output
            'e.g. MC, MS, BC, BS, total'
            if dmg_code in s:
                v = df[dmg_code].sum()
                setattr(self, dmg_code, v)
                
                logger.debug('set \'%s\' to %.2f'%(dmg_code, v))
                
        #=======================================================================
        # by flood type
        #=======================================================================
        if 'dmg_sw' in s:
            self.dmg_sw = df.loc[~df['gw_f'], 'total'].sum() #sum all those with surface water
            
        if 'dmg_gw' in s:
            self.dmg_gw = df.loc[df['gw_f'], 'total'].sum() #sum all those with surface water
                            
        
        #=======================================================================
        # number of houses with damage
        #=======================================================================
        if 'hdmg_cnt' in s:

            boolidx = df.loc[:, 'total'] > 0
        
            self.hdmg_cnt = boolidx.sum()
            
        #=======================================================================
        # average house depth
        #=======================================================================
        if 'hdep_avg' in s:
            
            self.hdep_avg = np.mean(df.loc[:,'hse_depth'])
            
        #=======================================================================
        # wsl average
        #=======================================================================
        if 'wsl_avg' in s:
            self.wsl_avg = np.mean(df.loc[:,'wsl'])
            
            
        #=======================================================================
        # basement exposure grade counts
        #=======================================================================      
        'just calcing all if any of them are requested'  
        boolar = np.isin(np.array(['bwet_cnt', 'bdamp_cnt', 'bdry_cnt']),
                         np.array(s))
        
        if np.any(boolar): self.get_begrd_cnt()
        
        #=======================================================================
        # plots
        #=======================================================================
        if 'dmg_res_df' in s:
            self.dmg_res_df = df
        
        """
        hp_pd.v(df)
        """
        
        return
            
    def get_begrd_cnt(self):
        logger = self.logger.getChild('get_begrd_cnt')
        
        df = self.dmg_res_df
        
        #=======================================================================
        # #get egrades
        # try:
        #     ser = df.loc[:,'bsmt_egrd'] #make the slice of interest
        # except:
        #     df.columns.values.tolist()
        #     raise IOError
        #=======================================================================
        
        ser = df.loc[:,'bsmt_egrd'] #make the slice of interest
        
        begrd_l = ser.unique().tolist()
        
        logger.debug('looping through %i bsmt_egrds: %s'%(len(begrd_l), begrd_l))
        for bsmt_egrd in begrd_l:
            att_n = 'b'+bsmt_egrd+'_cnt'
            
            #count the number of occurances
            boolar = ser == bsmt_egrd
            
            setattr(self, att_n, int(boolar.sum()))
            
            logger.debug('setting \'%s\' = %i'%(att_n, boolar.sum()))
        
        logger.debug('finished \n')
                        
        return
                    
#===============================================================================
#     def plot_dmg_pie(self, dmg_sum_ser_raw = None, 
#                      exp_str = 1, title = None, wtf=None): #generate a pie chart for the damage
#         """
#         #=======================================================================
#         # INPUTS
#         #=======================================================================
#         dmg_sum_ser:    series of damage values (see calc_summary_ser)
#             index: dmg_types
#             values: fdmg totals for each type for this flood
#             
#         exp_main: amoutn to explote structural damage values by
#         """
#         #=======================================================================
#         # set defaults
#         #=======================================================================
#         logger = self.logger.getChild('plot_dmg_pie')
#         if title == None: title = self.session.tag + ' '+self.name+' ' + 'dmgpie_plot'
#         if wtf is None: wtf = self.session._write_figs
#         
#         if dmg_sum_ser_raw == None:  #just calculate
#             dmg_sum_ser_raw = self.dmg_res_df[self.dmg_types].sum()
#             #dmg_sum_ser_raw = self.calc_summary_ser()
#             
#         logger.debug('with dmg_sum_ser_raw: \n %s'%dmg_sum_ser_raw)
#         #=======================================================================
#         # data cleaning
#         #=======================================================================
#         #drop na
#         dmg_sum_ser1 = dmg_sum_ser_raw.dropna()
#         #drop zero values
#         boolidx = dmg_sum_ser1 == 0
#         dmg_sum_ser2 = dmg_sum_ser1[~boolidx]
#         
#         if np.all(boolidx):
#             logger.warning('got zero damages. not pie plot generated')
#             return
#         
#         if boolidx.sum() > 0:
#             logger.warning('dmg_pie dropped %s zero totals'%dmg_sum_ser1.index[boolidx].tolist())
#         
#         dmg_sum_ser = dmg_sum_ser2
#         #=======================================================================
#         # get data
#         #=======================================================================
#         #shortcuts
#         dmg_types = dmg_sum_ser.index.tolist()
#         
#         labels = dmg_types
#         sizes = dmg_sum_ser.values.tolist()
# 
# 
#         #=======================================================================
#         # #get properties list from the dfunc tab
#         #=======================================================================
#         colors = []
#         explode_list = []
#         wed_lab_list = []
#         dfunc_df = self.session.pars_df_d['dfunc']
#         
#         for dmg_type in dmg_types:
#             boolidx = dfunc_df['dmg_type'] == dmg_type #id this dmg_type
#             
#             #color
#             color = dfunc_df.loc[boolidx,'color'].values[0]
#             colors.append(color) #add to the list
#             
#             #explode
#             explode = dfunc_df.loc[boolidx,'explode'].values[0]
#             explode_list.append(explode) #add to the list
#             
#             #wedge_lable
#             wed_lab = '$' + "{:,.2f}".format(dmg_sum_ser[dmg_type])
#             wed_lab_list.append(wed_lab)
#             
#             
#         import matplotlib.pyplot as plt
#         plt.close()
#         fig, ax = plt.subplots()
#         
#         
#         wedges = ax.pie(sizes, explode=explode_list, labels=labels, colors = colors,
#                autopct=hp.plot.autopct_dollars(sizes), 
#                shadow=True, startangle=90)
#         
#         ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
#         
#         ax.set_title(title)
#         
#         if wtf: #write to file
#             filetail = self.session.name + ' '+self.name+' ' + 'dmgpie_plot'
#             filename = os.path.join(self.model.outpath, filetail)
#             hp.plot.save_fig(self, fig, savepath_raw = filename)
#             
#         return ax
#     
#===============================================================================
#===============================================================================
#     def plot_dmg_scatter(self, #scatter plot of damage for each house
#                          dmg_df_raw=None, yvar = 'hse_depth', xvar = 'total', plot_zeros=True,
#                          title=None, wtf=None, ax=None, 
#                          linewidth = 0, markersize = 3, marker = 'x',
#                           **kwargs): 
#         
#         """
#         for complex figures, axes should be passed and returned
#         #=======================================================================
#         # INPUTS
#         #=======================================================================
#         should really leave this for post processing
#         plot_zeros: flag to indicate whether entries with x value = 0 should be included
#         
#         #=======================================================================
#         # TODO
#         #=======================================================================
#         redo this with the plot worker
#         """
#         
#         #=======================================================================
#         # defaults
#         #=======================================================================
#         logger = self.logger.getChild('plot_dmg_scatter')
#         if title == None: title = self.session.tag + ' '+self.name + ' dmg_scatter_plot'
#         if wtf is None: wtf = self.session._write_figs
#         
#             
#         if dmg_df_raw == None: 
#             dmg_res_df_raw = self.dmg_res_df #just use the attached one
#             
#             if not hp_pd.isdf(dmg_res_df_raw): raise IOError
#                 
#         #=======================================================================
#         # manipulate data for plotting
#         #=======================================================================
#         if plot_zeros:
#             dmg_df = dmg_res_df_raw
#         else:
#             #exclude those entries with zero value on the xvar
#             boolidx = dmg_res_df_raw[xvar] == 0
#             dmg_df = dmg_res_df_raw[~boolidx]
#             self.logger.warning('%s values = zero (%i) excluded from plot'%(xvar, boolidx.sum()))
#             
#         #=======================================================================
#         # setup data plot
#         #=======================================================================
#         x_ar = dmg_df[xvar].values.tolist() #damage
#         xlab = 'damage($)' 
#         'could make this more dynamic'
#         
#         if sum(x_ar) <=0:
#             logger.warning('got no damage. no plot generated')
#             return
# 
#         y_ar = dmg_df[yvar].values.tolist() #depth
#         
# 
#         #=======================================================================
#         # SEtup defaults
#         #=======================================================================
#         if ax == None:
#             plt.close('all')
#             fig = plt.figure(2)
#             fig.set_size_inches(9, 6)
#             ax = fig.add_subplot(111)
# 
#             ax.set_title(title)
#             ax.set_ylabel(yvar + '(m)')
#             ax.set_xlabel(xlab)
#             
#             #set limits
#             #ax.set_xlim(min(x_ar), max(x_ar))
#             #ax.set_ylim(min(y_ar), max(y_ar))
#         else:
#             fig = ax.figure
#             
#         label = self.name + ' ' + xvar
#         #=======================================================================
#         # send teh data for plotting
#         #=======================================================================
#         
#         pline = ax.plot(x_ar,y_ar, 
#                         label = label,
#                         linewidth = linewidth, markersize = markersize, marker = marker,
#                         **kwargs)
#         
# 
#         
#         #=======================================================================
#         # post formatting
#         #=======================================================================
#         ax.get_xaxis().set_major_formatter(
#             matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
#         
#         """
# 
#         plt.show()
# 
#         
#         """
# 
#         if wtf: #trigger for saving the fiture
#             filetail = title
#             filename = os.path.join(self.model.outpath, filetail)
#             hp.plot.save_fig(self, fig, savepath_raw = filename, logger=logger)
# 
#         
#         return pline
#     
#===============================================================================
class Binv(     #class object for a building inventory
                hp_data.Data_wrapper,
                #hp.plot.Plot_o,
                hp_sim.Sim_o,
                hp_oop.Parent,
                hp_oop.Child): 
    #===========================================================================
    # program pars
    #===========================================================================
    # legacy index numbers
    legacy_ind_d = {0:'ID',1:'address',2:'CPID',10:'class', 11:'struct_type', 13:'gis_area', 
                    18:'bsmt_f', 19:'ff_height', 20:'xcoord',21:'ycoord', 25:'dem_el'}
    
    #column index where the legacy binv transitions to teh new binv
    legacy_break_ind = 26
    
    #column names expected in the cleaned binv
    """using special types to cut down on the size"""
    exp_coltyp_d = {#'name':str,'anchor_el':float, #calculated (adding these in later)
                    'bid':'uint16', #id for each asset.. generally the mind
                    'gis_area':'Float32', #eventually we should take this off
                     'bsmt_f':bool, 'ff_height':'Float32',
                     'dem_el':'Float32', 
                     'acode_s':str,'acode_c':str, 
                    'parcel_area':'Float32',
                     #'f1area':'Float32','f0area':'Float32','f1a_uf':'Float32','f0a_uf':'Float32',
                     'asector':str,
                     #'lval':'Float32','rval':'Float32' #calculate udev externally
                     } 
    
    #additional column names the binv will accept (but not require reals)
    alwd_coltyp_d = {'bkflowv_f':bool,'sumpump_f':bool, 'genorat_f':bool, 
                     'B_f_height':'Float32',
                     'ayoc':int}
    
    #rounding parameters
    coln_rnd_d = {'dem_el':2, 'B_f_height':2, 'ff_height':2}


    
    #hse_type_list = ['AA', 'AD', 'BA', 'BC', 'BD', 'CA', 'CC', 'CD'] #classification of building types
    
    
    #===========================================================================
    # user provided
    #===========================================================================
    legacy_binv_f       = True


    #===========================================================================
    # calculated pars
    #===========================================================================

    
    #===========================================================================
    # data holders
    #===========================================================================
    #cnt = 0
    hnew_cnt    = 0
    hAD_cnt     = 0


    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Binv')
        logger.debug('start _init_')
        
        
        """Im explicitly attaching the child datobuilder here 
        dont want to change the syntax of the binv
        
        inspect.isclass(self.kid_class)
        """
        self.inherit_parent_ans=set(['mind', 'legacy_binv_f', 'gis_area_max'])
        
        super(Binv, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        
        #=======================================================================
        # special inheritance
        #=======================================================================
        #self.model = self.parent
        self.kid_class = House
        
        self.reset_d.update({'hnew_cnt':0, 'hAD_cnt':0})
        #=======================================================================
        # checks
        #=======================================================================
        if self.db_f:
            if not self.kid_class == House:
                raise IOError
            
            if not isinstance(self.reset_d, dict):
                raise IOError
        
            if self.model is None:
                raise IOError
            
            if not self.model.name == self.parent.name:
                raise IOError
            
        #=======================================================================
        # special inits
        #=======================================================================
        if not self.mind in self.exp_coltyp_d:
            raise Error('requested mind \'%s\' is not a valid binv column'%self.mind)
        """just require this
        self.exepcted_coln = set(self.exepcted_coln + [self.mind]) #expect the mind in the column names as well"""
        
        self.load_data()

        logger.debug('finiished _init_ \n')
        return
        

    def load_data(self): #custom data loader
        #=======================================================================
        # defaults
        #=======================================================================

        log = self.logger.getChild('load_data')
        #test pars
        if self.session._parlo_f: 
            test_trim_row = self.test_trim_row
        else: test_trim_row = None
        
        #=======================================================================
        # load the file
        #=======================================================================
        self.filepath = self.get_filepath()
        
        log.debug('from filepath: %s'%self.filepath)
        
        #load from file
        df_raw = hp_pd.load_xls_df(self.filepath, 
                                   logger=log, 
                                   test_trim_row = test_trim_row, 
                header = 0, index_col = None)
                
        #=======================================================================
        # send for cleaning
        #=======================================================================
        df1 = hp_pd.clean_datapars(df_raw, logger = log)
        """
        hp_pd.v(df3)
        """
        
        #=======================================================================
        # clean per the leagacy binv
        #=======================================================================
        if self.legacy_binv_f:
            df2 = self.legacy_clean_df(df1)
        else:
            df2 = df1
            
        #=======================================================================
        # standard clean   
        #=======================================================================
        df3 = self.clean_inv_df(df2)
        
        
        #=======================================================================
        # macro data manipulations
        #=======================================================================
        df4 = self.pre_calc(df3)
                
        
        #=======================================================================
        # checking
        #=======================================================================
        if self.db_f: 
            self.check_binv_df(df4)
                

        
        #=======================================================================
        # #shortcut lists
        #=======================================================================
        self.bid_l = tuple(df4[self.mind].values.tolist())
        

        self.acode_l = self.get_acodes(df4) #make the resference
        
        
                #=======================================================================
        # wrap up
        #=======================================================================
        self.childmeta_df = df4.copy()
        

        log.info('attached binv_df with %s'%str(df4.shape))
        
        return
    """
    view(df4)
    """
    
    def get_acodes(self, 
                   df,
                   null_val = 'none'): #get the set of requested acodes
        
        log = self.logger.getChild('get_acodes')
        s = set()
        
        #loop through the acode columns
        for coln in ('acode_s', 'acode_c'):
            
            #find null values
            boolidx = df[coln] == null_val

            s.update(df.loc[~boolidx, coln].unique().tolist())#add the contets codes also
            
        log.debug('found %i acodes'%len(s))
        
        return tuple(s)
            

    
    def legacy_clean_df(self, df_raw): #compile data from legacy (rfda) inventory syntax
        """
        pulling column headers from the dictionary of location keys
        
        creating some new headers as combinations of this
        
        """
        #=======================================================================
        # setup
        #=======================================================================
        logger = self.logger.getChild('legacy_clean_df')
        
        d = self.legacy_ind_d
        
        #=======================================================================
        # split the df into legacy and non
        #=======================================================================
        df_leg_raw = df_raw.iloc[:,0:self.legacy_break_ind]
        df_new = df_raw.iloc[:,self.legacy_break_ind+1:]
        
        #=======================================================================
        # clean the legacy frame
        #=======================================================================

        #change all the column names
        df_leg1 = df_leg_raw.copy()
        
        """ couldnt get this to work
        df_leg1.rename(mapper=d, index = 'column')"""

        
        for colind, coln in enumerate(df_leg_raw.columns):
            if not colind in list(d.keys()):continue

            df_leg1.rename(columns = {coln:d[colind]}, inplace=True)
            
            logger.debug('renamed \'%s\' to \'%s\''%(coln,d[colind] ))
            
        #trim down to these useful columns
        boolcol = df_leg1.columns.isin(list(d.values())) #identify columns in the translation dictionary
        df_leg2 = df_leg1.loc[:,boolcol]
        
        logger.debug('trimmed legacy binv from %i to %i cols'%(len(df_leg_raw.columns), boolcol.sum()))
        
        #=======================================================================
        # add back the new frame
        #=======================================================================
        df_merge = df_leg2.join(df_new)

        #=======================================================================
        #  house t ype
        #=======================================================================        
        df_merge.loc[:,'acode_s'] =  df_leg2.loc[:,'class'] + df_leg2.loc[:,'struct_type']
        
        logger.debug('cleaned the binv from %s to %s'%(str(df_raw.shape), str(df_merge.shape)))
        
        if self.db_f:
            if not len(df_merge) == len(df_raw):
                raise IOError
            if np.any(pd.isnull(df_merge['acode_s'])):
                raise IOError
        
        return df_merge
        """
        hp_pd.v(df_leg_raw)
        hp_pd.v(df_merge)
        hp_pd.v(df_raw)
        """
        
    def clean_inv_df(self, #custom binv cleaning
                     df_raw,
                     ): 
        """
        consider using the datos_fdmg wraps
        """
        logger = self.logger.getChild('clean_inv_df')
        #clean with kill_flags
        'this makes it easy to trim the data'
        df1 = hp_pd.clean_kill_flag(df_raw, logger = logger)
        
        #=======================================================================
        # #reindex by a sorted mind (and keep the column)
        #=======================================================================
        df1.loc[:,self.mind] = df1.astype({self.mind:int}) #typeset the index
        df1 = df1.set_index(self.mind, drop=False, verify_integrity=True).sort_index()
        
        #=======================================================================
        # mandatory columns
        #=======================================================================
        #check we got all the columns we require
        exp_coln_ar = np.array(list(self.exp_coltyp_d.keys()))
        
        
        boolar = np.invert(np.isin(exp_coln_ar, df1.columns))
        if np.any(boolar):
            raise Error('missing %i expected columns: \n    %s'%
                          (boolar.sum(), exp_coln_ar[boolar]))
            
        dfm = df1.loc[:, exp_coln_ar]
        
        #null check
        """shouldnt accept any nulls on mandatory data.
        if we do.. why is the data mandatory?
        this isnt data analysis.. this is simulation modeling"""
        hp_pd.fancy_null_chk(dfm, dname='binv1',detect='error')
            
        #=======================================================================
        # optional columns
        #=======================================================================
        #assemble all the columns we allow
        alwd_coln_ar = np.array(list(self.exp_coltyp_d.keys())+list(self.alwd_coltyp_d.keys()))
        
        df2 = df1.loc[:,alwd_coln_ar] #make the slice
        """this may throw a warning if we are missing some columns"""
        
        hp_pd.fancy_null_chk(df2, dname='binv2',detect='error')
        """
        Ideally, we should allow nulls on the 'optional' columns.
        but because of the limitation on excel reading booleans with nulls,
        were not setup to handle this
        
        """

        #=======================================================================
        # #typesetting
        #=======================================================================
       
        df3 = df2.astype(self.exp_coltyp_d)
        
        df3 = df3.astype(self.alwd_coltyp_d)
        
        #=======================================================================
        # rounding
        #=======================================================================
        df4 = df3.copy()
        for coln, places in self.coln_rnd_d.items():
            boolidx = np.invert(df4[coln].isna()) #just the reals
            df4.loc[boolidx, coln] = df4.loc[boolidx, coln].round(places)
        

        return df4
    
    """
    sys.getsizeof(df3)
    df3['dem_el'].astype('Float32')
    view(df3)
    """
        

    def check_binv_df(self, df):  
        logger = self.logger.getChild('check_binv_df')
        'todo: add some template check'
        if not hp_pd.isdf(df):
            raise IOError

        #=======================================================================
        # check area column
        #=======================================================================
        boolidx = df.loc[:,'gis_area']< self.model.gis_area_min
        if np.any(boolidx):
            raise Error('got %i binv entries with area < 5'%boolidx.sum())
        
        boolidx = df.loc[:,'gis_area']> self.model.gis_area_max
        if np.any(boolidx):
            raise Error('got %i binv entries with area > %.2f'%(boolidx.sum(), self.model.gis_area_max))
        
        #=======================================================================
        # check basement
        #=======================================================================
        #basement finish height
        boolidx_fail = np.logical_and(
                        df['B_f_height'] < self.session.bfh_min, #basements below the minimum
                        df['bsmt_f'] #supposed to have a basement
                        ) 
        
        if np.any(boolidx_fail):
            logger.debug('failed entries: \n%s'%df.loc[boolidx_fail, ('bsmt_f','B_f_height')])
            raise Error('binv got %i entries with B_f_height less than the session min %.2f'
                          %(boolidx_fail.sum(), self.session.bfh_min))
            
        #basement finish to floor 1 finish height logic check  (no suspeneded bsasements)
        boolidx_fail = np.logical_and(
                        df['B_f_height'] < df['ff_height'], #basements below the minimum
                        df['bsmt_f'] #supposed to have a basement
                        ) 
        """
        b = df['B_f_height'] < df['ff_height']
        b.sum()
        """
        
        if np.any(boolidx_fail):
            logger.debug('failed entries: \n%s'%df.loc[boolidx_fail, ('ff_height','dem_el','bsmt_f','B_f_height')])
            raise Error('binv got %i entries with B_f_height < ff_height'
                          %(boolidx_fail.sum()))
        
        
        if 'bsmt_egrd' in df:
            raise IOError
            
        return 
    
    def pre_calc(self, #pre calcs on teh binv 
                 df_raw):
        
        log = self.logger.getChild('pre_calc')
        
        df = df_raw.copy()
                        
        #add names column
        if not 'name' in df.columns:
            df['name'] = 'h' + df.loc[:, self.mind].astype(str) #format as strings
        
        
        #add anchor el
        if not 'anchor_el' in df.columns:
            try:
                df['anchor_el'] = df['dem_el'] + df['ff_height']
                df.loc[:, 'anchor_el'] = df['anchor_el'].astype(np.float)
            except Exception as e:
                raise Error('failed to set anchor_el w/ \n    %s'%e)

                
        return df
        

    def raise_houses(self): 
        #=======================================================================
        # setup
        #=======================================================================
        start = time.time()
        logger = self.logger.getChild('raise_houses')
        
        
        df = self.childmeta_df #build the childmeta intelligently
        'we could probably just passt the data directly'
        
        if self.db_f:
            if not hp_pd.isdf(df):
                raise IOError
        
        logger.info('executing with data %s'%str(df.shape))
        
        hse_n_d = self.raise_children_df(df, #run teh generic child raiser
                                         kid_class = self.kid_class,
                                         dup_sibs_f = True) 
        
        """
        view(df)
        """

        #=======================================================================
        # add a custom sorted dictionary by name
        #=======================================================================
        #build a normal dictionary of this
        d = dict() 
        for cname, childo in hse_n_d.items(): 
            d[childo.bldg_id] = weakref.proxy(childo)
            
        #bundle this into a sorted ordered dict
        self.hse_od = OrderedDict(sorted(list(d.items()), key=lambda t: t[0]))
        
        """put this here so the edits made by House are captured"""
        self.reset_d['childmeta_df'] = self.childmeta_df.copy()
        
        logger.debug('calc_binv_stats() \n')
        self.calc_binv_stats()
        
        stop = time.time()
        logger.info('finished with %i hosues in %.4f secs'%(len(d), stop - start))
    
        
        return
            

    
    def set_all_hse_atts(self, #reset an attribute name/value pair to all houses in the binv
                         attn,  
                         attv=None, #single value to apply to each house
                         ser=None, #series to pull data from indexed by the obj_key
                         obj_key = 'dfloc',
                         ): 
        """
        NOTE: oop.attach_att_df() is similar, but doesnt handle the dynamic updating
        udev.set_fhr is also similar
        
        ToDo: consider moving this into dyno
        
        
        """
        logger = self.logger.getChild('set_all_hse_atts')
        #=======================================================================
        # precheck
        #=======================================================================
        if self.db_f:
            if not ser is None:
                if not isinstance(ser, pd.Series):
                    raise IOError
                
            if not len(self.hse_od) > 0:
                raise IOError
            
            if (attv is None) and (ser is None):
                raise IOError #need at least one input

        #=======================================================================
        # loop and add to each house
        #=======================================================================
        logger.debug('dynamically updating %i houses on \'%s\''%(len(self.hse_od), attn))
        
        for k, hse in self.hse_od.items():
            
            if not ser is None:
                attv = ser[getattr(hse, obj_key)]
                
            #haqndle the updates on this house
            hse.handle_upd(attn, attv, proxy(self), call_func = '_set_all_hse_atts') 
            
        return
    
    """
    df = self.childmeta_df
    df.columns
    hp_pd.v(df)
    """

     
    def calc_binv_stats(self): #calculate output stats on the inventory
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        __init__
            raise_children #after raising all the Houses
            
        (Fdmg or Udev).get_restults()

            
        
        #=======================================================================
        # TODO
        #=======================================================================
        fix this so it acts more like a dynp.update with ques triggerd from changes on the HOuse
        
        #=======================================================================
        # TESTING
        #=======================================================================
        hp_pd.v(df)

        df.columns.values.tolist()
        """
        #logger = self.logger.getChild('calc_binv_stats')
        
        s = self.session.outpars_d[self.__class__.__name__]

        
        """using this in some annotations
        if 'cnt' in s:"""
    
        self.cnt = len(self.hse_od) #get the number of houses in the binv
        

            
        if 'hnew_cnt' in s:
        
            #new house counts
            boolidx = self.childmeta_df.loc[:,'ayoc'] > self.session.year0
            self.hnew_cnt = boolidx.sum()
            
        return
        
    def get_bsmt_egrds(self, set_f=False):
        
        logger = self.logger.getChild('get_bsmt_egrds')
        
        df = self.childmeta_df
        
        if not 'bsmt_egrd' in df.columns:
            #self.session.state
            raise IOError
        
        #basement exposure grade
        logger.debug('getting bsmt_egrd stats on %s'%(str(df.shape)))
        
        d = dict()
        
        for grade in ['wet', 'dry', 'damp']: #loop through and count all the finds
            
            #get count
            boolidx = df.loc[:,'bsmt_egrd'] == grade
            
            cnt = boolidx.sum()
            
            d[grade] = cnt
            
            #set as attribute
            if set_f:
                new_an = '%s_cnt'%grade
                
                setattr(self, new_an, cnt)
            
            logger.debug('for bsmt_egrd = \'%s\' found %i'%(grade,cnt))
            
        return d
              
    def write(self): #write the current binv to file
        logger = self.logger.getChild('write')
        
        df = self.childmeta_df
        """
        hp_pd.v(df)
        """
        
        filename = '%s binv'%(self.session.state)
        filehead = self.model.tstep_o.outpath
        
        filepath = os.path.join(filehead, filename)
        
        hp_pd.write_to_file(filepath, df, logger=logger)
                
        return
        

class Dfeat_tbl( #holder/generator fo all the dmg_feats
                 hp_data.Data_wrapper,
                hp_sim.Sim_o,
                hp_oop.Parent,
                hp_oop.Child): 
    """
    holder/generator fo all the dmg_feats
    """
    #===========================================================================
    # progran pars
    #===========================================================================
    extra_hse_types = ['AD'] #always load these house types

    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dfeat_tbl')
        logger.debug('start _init_ ')
        
        self.inherit_parent_ans=set(['mind'])
        
        super(Dfeat_tbl, self).__init__(*vars, **kwargs) #initilzie teh baseclass   
        
        #=======================================================================
        # properties
        #=======================================================================

        self.kid_class      = Dmg_feat #mannually pass/attach this
        
        if self.session.wdfeats_f: #only bother if we're using dfeats
            logger.debug('load_data() \n')
            self.load_data()
            
            self.set_acodes() #get the acodes
            
            
                    
        self.logger.debug('fdmg.Dfeat_tbl initilized') 
        
        #=======================================================================
        # post checks
        #=======================================================================
        
        if self.db_f:
            if self.model is None:
                raise IOError
            
        return
        
    def load_data(self):
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('load_data')
        #test pars
        if self.session._parlo_f: test_trim_row = self.test_trim_row
        else: test_trim_row = None
        
        self.filepath = self.get_filepath()
        
        #load from file
        dfeat_df_d = hp_pd.load_xls_df(self.filepath, logger=logger, test_trim_row = test_trim_row,
                                        skiprows = [1],header = 0, index_col = None, sheetname=None)
                
        
        'wrong function?'
        
        'todo: add some template check'
        
        for tabname, df_raw in dfeat_df_d.items():
            #=======================================================================
            # send for cleaning
            #=======================================================================
            df_clean = self.clean_df(df_raw)
            
            #rewrite this
            dfeat_df_d[tabname] = df_clean
            
            logger.debug('loaded dynamic danage curve table for %s with %s'%(tabname, str(df_clean.shape)))
        
        self.dfeat_df_d = dfeat_df_d 
        self.data = None

        #=======================================================================
        # wrap up
        #=======================================================================
        self.session.ins_copy_fps.add(self.filepath)
        
        logger.debug('attached dfeat_df_d with %i entries'%len(dfeat_df_d))
  
    def clean_df(self, df_raw): #custom cleaner
        logger = self.logger.getChild('clean_df')
        
        df1 = self.generic_clean_df(df_raw)
        
        df2 = df1.dropna(how = 'all', axis='columns') #drop columns where ANY values are na
        
        #drop the 'note' column from the frame
        df3 = df2.drop('note', axis=1, errors='ignore')
        
        
        #=======================================================================
        # exclude small dfeats
        #=======================================================================
        if self.model.dfeat_xclud_price > 0:
            boolidx = df3['base_price'] <= self.model.dfeat_xclud_price
            df4 = df3.loc[~boolidx,:] #trim to just these
            
            if boolidx.sum() > 0:
                logger.warning('trimmed %i (of %i) dfeats below %.2f '%(boolidx.sum(), len(df3), self.model.dfeat_xclud_price))
                
                """
                hp_pd.v(df4.sort_values('base_price'))
                hp_pd.v(df3.sort_values('base_price'))
                """
        else: 
            df4 = df3
        
        
        'todo: drop any columns where name == np.nan'
        
        df_clean = df4.copy()
        
        hp_pd.cleaner_report(df_raw, df_clean, logger = logger)
        
        #=======================================================================
        # #post formatters
        #=======================================================================
        df_clean.loc[:,'depth'] = df_clean['depth_dflt'].values #duplicate this column
        """ This is throwing the SettingWithCopy warning.
        Tried for 20mins to figure this out, but couldnt find any chained indexing.
        """
        
        df_clean.loc[:,'calc_price'] = np.nan #add this as a blank column
        
        return df_clean
    
    def set_acodes(self): #update the fdmg available acodes
        
        log = self.logger.getChild('set_acodes')
        

        #make a list filled with teh acodes
        """eventually, we should detect these from the dfeats"""
        acode_l = np.full(len(self.dfeat_df_d), 'sres').tolist()
        
        #zip together a dictionary 
        d = dict(zip(list(self.dfeat_df_d.keys()),acode_l)) 

        self.parent.acode_sec_d.update(d) #attach these to fdmg
        
        self.acode_sec_d = copy.copy(d)
        
        log.debug('loaded %i acodes: \n    %s'%(len(d), list(d.keys())))

    
    def raise_all_dfeats(self): #construct all of your dfeats
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('raise_all_dfeats')
        
        d = self.dfeat_df_d

        
        dfeats_d = dict() #container of containers
        
        #=======================================================================
        # get the list of house types provided in teh binv
        #=======================================================================
        acode_l = set(self.parent.kids_d['binv'].acode_l) #pull from binv
        acode_l.update(self.extra_hse_types) #add the extras

        #=======================================================================
        # load all the dfeats for this
        #=======================================================================
        logger.debug('on %i house types: %s \n'%(len(d), list(d.keys())))
        
        for acode, df in d.items():
            
            if not acode in acode_l:
                logger.debug(' acode = \'%s\' not found in the binv. skipping'%acode)
                continue
            
            #get all teh place codes
            place_codes_l = df['place_code'].unique().tolist()
            
            #===================================================================
            # raise children on each of these
            #===================================================================
            logger.debug('building set for acode = \'%s\' with %i place_codes \n'%(acode, len(place_codes_l)))
            
            cnt = 0
            for place_code in place_codes_l:
                tag = acode + place_code #unique tag
                
                #slice to this place (on this house dfeat table)
                df_slice = df[df['place_code'] == place_code].reset_index(drop=True)
                'need thsi so the dfloc aligns'
                """
                view(df_slice)
                """

                
                #===============================================================
                # #spawn this subset
                #===============================================================
                logger.debug('for \'%s\' raising children from %s'%(tag, str(df_slice.shape)))
                

                #run teh generic child raiser for all dfeats of this type
                'raise these as shadow children'
                dfeats_d[tag] = self.raise_children_df(df_slice, 
                                                        kid_class = self.kid_class,
                                                        dup_sibs_f = True,
                                                        shadow = True) 
                
                logger.debug('finished with %i dfeats on tag \'%s\''%(len(dfeats_d[tag]), tag))
                cnt += len(dfeats_d[tag])
                #===============================================================
                # checks
                #===============================================================
                if self.db_f:
                    for dfname, dfeat in dfeats_d[tag].items():
                        #model matching
                        if not self.model == dfeat.model:
                            raise Error('model mismatch')
                
                
                #end place code
            logger.debug('finish loop \'%s\' with %i'%(acode, len(dfeats_d)))
            #end acode pars loop
        
        #=======================================================================
        # wrap
        #=======================================================================
        logger.debug("finished with %i dfeats in %i sets raised: %s \n"%(cnt, len(dfeats_d), list(dfeats_d.keys())))
        

        return dfeats_d
    """
    view(df_slice)
    """
 

       
 
  

def annot_builder(dfunc): #special annot builder helper

    annot_str = '%s_type: %s\n'%(dfunc.name, dfunc.dfunc_type) +\
                '    anchor_ht_code: %s\n'%dfunc.anchor_ht_code +\
                '    anchor_el: %.2f\n'%dfunc.anchor_el +\
                '    maxdd = %.2f m, $%.2f\n'%(max(dfunc.dd_ar[0]), max(dfunc.dd_ar[1]))
                
    return annot_str


 
  
        
        
        
        
    
