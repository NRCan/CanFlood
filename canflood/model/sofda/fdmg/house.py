'''
Created on May 12, 2019

@author: cef
'''


#===============================================================================
# IMPORT STANDARD MODS -------------------------------------------------------
#===============================================================================
import logging, os,  time, re, math, copy, gc, weakref, random


import pandas as pd
import numpy as np




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

import model.sofda.hp.dyno as hp_dyno
#import model.sofda.hp.data as hp_data

from model.sofda.fdmg.dfunc import Dfunc
import model.sofda.udev.scripts as udev_scripts

# logger setup -----------------------------------------------------------------------
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')


class House(
            udev_scripts.House_udev,
            #hp.plot.Plot_o, 
            hp_dyno.Dyno_wrap,
            hp_sim.Sim_o,  
            hp_oop.Parent, #building/asset objects 
            hp_oop.Child): 
    
    #===========================================================================
    # program pars
    #==========================================================================
    geocode_list        = ['area', 'per', 'height', 'inta'] #sufficxs of geometry attributes to search for (see set_geo)
    finish_code_list    = ['f', 'u', 't'] #code for finished or unfinished
    

    #===========================================================================
    # debugging
    #===========================================================================
    last_floodo = None
    
    #===========================================================================
    # user provided pars
    #===========================================================================
    dem_el      = np.nan    
    """changed to acode
    hse_type    = '' # Class + Type categorizing the house"""
    acode_s     = ''
    acode_c     = ''
    anchor_el   = np.nan # anchor elevation for house relative to datum (generally main floor el)   
    gis_area    = np.nan #foot print area (generally from teh binv)
    B_f_height  = np.nan
    bsmt_f   = True
    area_prot_lvl = 0 #level of area protection
    asector     =''
    
    f1area =np.nan
    f0area = np.nan
    f1a_uf =np.nan
    f0a_uf =np.nan

    
    #needed for udev
    parcel_area = np.nan
    
    #defaults passed from model
    """While the ICS for these are typically uniform and broadcast down by the model,
    these need to exist on the House, so we can spatially limit our changes"""
    G_anchor_ht   = None   #default garage anchor height (chosen aribtrarily by IBI (2015)
    joist_space   = None   #space between basement and mainfloor. used to set the 
    
    
    #set of expected attributes (and their types) for validty checking
    exp_atts_d = {'parcel_area':float, 'acode_s':str, 'acode_c':str, 'anchor_el':float, 'gis_area':float,
                  'B_f_height':float, 'dem_el':float, 'asector':str}
    #===========================================================================
    # calculated pars
    #===========================================================================
    floodo      = None  #flood object flooding the house

    # #geometry placeholders
    #geo_dxcol_blank = None #blank dxcol for houes geometry
    geo_dxcol = None

    
    
    'keeping just this one for reporting and dynp'
    
    
    boh_max_val = None #basement open height minimum value
    
    
        
    # #anchoring
    """
    Im keeping anchor heights separate from geometry attributes as these could still apply
    even for static dmg_feats
    """
    
    bsmt_opn_ht   = 0.0   #height of lowest basement opening
    damp_spill_ht = 0.0
    
    vuln_el       = 9999.0   #starter value

    # personal property protection
    bkflowv_f       = False #flag indicating the presence of a backflow  valve on this property
    sumpump_f       = False
    genorat_f       = False
    
    bsmt_egrd   = ''
    
    #statistics
    BS_ints     = 0.0 #some statistic of the weighted depth/damage of the BS dfunc
    max_dmg     = 0.0 #max damage possible for this house 
    dummy_cnt   = 0 #number of dummy dfuncs
    kid_nm_t    = tuple()
    beg_hist    = ''
    #===========================================================================
    # data containers
    #===========================================================================
    dd_df       = None #df results of total depth damage 


    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('House')
        logger.debug('start _init_')
        #=======================================================================
        # attach pre init atts
        #=======================================================================
        #self.model              = self.parent.model #pass the Fdmg model down
        'put this here just to keep the order nice and avoid the unresolved import error'
        
        self.inherit_parent_ans=set(['mind', 'model'])

        #=======================================================================
        # #initilzie teh baseclass
        #=======================================================================
        super(House, self).__init__(*vars, **kwargs) 
        
        if self.db_f:
            if self.model is None: raise IOError
        

        #=======================================================================
        #common setup
        #=======================================================================
        if self.sib_cnt == 0:
            logger.debug("sib_cnt=0. setting atts")
            self.kid_class          = Dfunc
            
            """noved this out to set_dfunc_df
            self.childmeta_df       = self.model.house_childmeta_df #dfunc meta data"""
            
            self.joist_space        = self.model.joist_space
            self.G_anchor_ht        = self.model.G_anchor_ht
            
        #=======================================================================
        # unique se5tup
        #=======================================================================
        self.bldg_id            = int(getattr(self, self.mind ))

        self.bsmt_f            = hp_basic.str_to_bool(self.bsmt_f, logger=self.logger)

        
        if not 'B' in self.model.place_codes:
            raise Error('not sure about this')
            self.bsmt_f = False
        
        'these need to be unique. calculated during init_dyno()'
        self.post_upd_func_s = set([self.calc_statres_hse])
        
        
        logger.debug('building the house \n')
        self.build_house()
        logger.debug('raising my dfuncs \n')
        self.raise_dfuncs()
        logger.debug('init_dyno \n')
        self.init_dyno()
        
        #=======================================================================
        # cheking
        #=======================================================================
        if self.db_f: self.check_house()
        
        logger.debug('_init_ finished as %i \n'%self.bldg_id)
        
        return


    
    def check_house(self):
        logger = self.logger.getChild('check_house')
        
        #check the proxy objects
        if not self.model.__repr__() == self.parent.parent.__repr__(): 
            raise IOError


        #=======================================================================
        # check attribute validity
        #=======================================================================
        self.check_atts()
        
        #=======================================================================
        # check the basement logic
        #=======================================================================
        if self.bsmt_f:
            if self.B_f_height < self.session.bfh_min:
                raise Error('%s basement finish height (%.2f) is lower than the session minimum %.2f)'
                              %(self.name,self.B_f_height, self.session.bfh_min ))
        
        #=======================================================================
        # check your children
        #=======================================================================
        for name, dfunc in self.kids_d.items():
            dfunc.check_dfunc()
            

        
        return
    
    def build_house(self): #buidl yourself from the building inventory
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        binv.raise_children()
            spawn_child()
        
        """
        logger = self.logger.getChild('build_house')
    
        #=======================================================================
        # custom loader functions
        #=======================================================================
        #self.set_binv_legacy_atts() #compile data from legacy (rfda) inventory syntax
        logger.debug('set_geo_dxcol \n')
        self.set_geo_dxcol() #calculate the geometry (defaults) of each floor
        logger.debug('set_hse_anchor \n')
        self.set_hse_anchor()
                        
        """ a bit redundant, but we need to set the bsmt egrade regardless for reporting consistency
        'these should be accessible regardless of dfeats as they only influence the depth calc'"""
        self.set_bsmt_egrd()
        
        if self.bsmt_f:
            logger.debug('set_bsmt_opn_ht \n')
            self.set_bsmt_opn_ht()
            logger.debug('set_damp_spill_ht \n')
            self.set_damp_spill_ht()
            
            
        #=======================================================================
        # value
        #=======================================================================
        'need a better way to do this'
        """contents value scaling
        self.cont_val = self.value * self.model.cont_val_scale"""
            
        if self.db_f:    
            
            if self.gis_area < self.model.gis_area_min:
                raise IOError
            if self.gis_area > self.model.gis_area_max: raise IOError
                        
        logger.debug('finished')
        
        return

        
    def raise_dfuncs(self): #build dictionary with damage functions for each dmg_type
        """
        
        called by spawn_child and passing childmeta_df (from dfunc tab. see above)
        this allows each dfunc object to be called form the dictionary by dmg_type
        
        dfunc_df is sent as the childmeta_df (attached during __init__)
        #=======================================================================
        # INPUTS
        #=======================================================================
        dfunc_df:    df with headers:

        these are typically assigned from the 'dfunc' tab on the pars.xls

        """
        #=======================================================================
        # #defautls
        #=======================================================================
        logger = self.logger.getChild('raise_dfuncs')
        

        
        'this is a slice from the dfunc tab made by Fdmg.load_pars_dfunc'
        
        #=======================================================================
        # get your dfunc pars
        #=======================================================================      
        dfunc_pars_df = self.get_dfunc_df()
        
        #set this as yoru childmeta
        self.childmeta_df = dfunc_pars_df.copy()
        
        logger.debug('from %s'%str(dfunc_pars_df.shape))
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not self.session.state=='init':
                raise Error('should only build these once')
            if not isinstance(dfunc_pars_df, pd.DataFrame): 
                raise IOError
            if len(dfunc_pars_df) == 0:  
                raise Error('%s got no dfunc_pars_df!'%self.name)
            if not self.kid_class == Dfunc:
                raise IOError
            if len(self.kids_d) > 0: 
                raise IOError
            
        #=======================================================================
        # clean the dfunc pars
        #=======================================================================
        
        """I think we need placeholder dfuncs incase we rebuild this house with a basement later
        #drop basements
        if not self.bsmt_f:
            dfunc_pars_df = dfunc_pars_df_raw[dfunc_pars_df_raw['place_code']!='B']
        else:
            dfunc_pars_df = dfunc_pars_df_raw"""
            
        #slice out all the nones
        dfunc_pars_df1 = dfunc_pars_df[dfunc_pars_df['acode'] != 'none']
        #=======================================================================
        # compile for each damage type
        #=======================================================================
        #shortcut for ALL nones
        if len(dfunc_pars_df1) == 0:
            logger.debug('no real dfuncs. skipping construction')
            self.dfunc_d = dict()
        else:
            self.dfunc_d = self.raise_children_df(dfunc_pars_df1,
                                   kid_class = self.kid_class,
                                   dup_sibs_f = True)
 
        #=======================================================================
        # closeout and wrap up
        #=======================================================================
        logger.debug('built %i dfunc children: %s'%(len(self.dfunc_d), list(self.dfunc_d.keys())))
        
        #=======================================================================
        # post check
        #=======================================================================
        if self.db_f:
            
            self.check_house()
            

        
        return 
    


    def set_hse_anchor(self):
        'pulled this out so updates can be made to dem_el'
        if self.is_frozen('anchor_el'): return True
        
        anchor_el = self.dem_el + float(self.ff_height) #height + surface elevation
        
        #set the update
        self.handle_upd('anchor_el', anchor_el, proxy(self), call_func = 'set_hse_anchor')
        
        return True
    
    
            
    def set_bsmt_opn_ht(self): #set the basement openning height (from teh basement floor)
        """
        bsmt_open_ht is used by dfuncs with bsmt_e_grd == 'damp' and damp_func_code == 'spill' 
            for low water floods
        """
        #=======================================================================
        # shortcuts
        #=======================================================================
        if not self.bsmt_f: 
            return True
        
        #=======================================================================
        # check dependencies and frozen
        #=========================================================== ============
        if not self.session.state=='init':

            if self.is_frozen('bsmt_opn_ht'): 
                return True
            
            dep_l =  [([self], ['set_hse_anchor', 'set_geo_dxcol'])]
            
            if self.deps_is_dated(dep_l, method = 'reque', caller = 'set_bsmt_opn_ht'):
                return False
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('set_bsmt_opn_ht')
        
        #=======================================================================
        # from user provided minimum
        #=======================================================================
        if self.model.bsmt_opn_ht_code.startswith('*max'):
            
            #===================================================================
            # prechecks
            #===================================================================
            if self.db_f:
                bfh_chk = float(self.geo_dxcol.loc['height',('B','f')])
                if not round(self.B_f_height, 2) ==  round(bfh_chk, 2):
                    raise Error('B_f_height mismatch attribute (%.2f) geo_dxcol (%.2f)'
                                  %(self.B_f_height, bfh_chk))
                
                """lets let the basement be above grade"""
                if self.ff_height > (bfh_chk + self.joist_space):
                    logger.warning('basement is above grade!')
            
            #get the minimum value
            if self.boh_max_val is None: #calculate and set
                'this means we are non dynamic'
                s_raw = self.model.bsmt_opn_ht_code
                s = re.sub('\)', '',s_raw[5:])
                self.boh_max_val = float(s) #pull the number out of the brackets
                
            max_val = self.boh_max_val

            # get the basement anchor el
            B_f_height = float(self.geo_dxcol.loc['height',('B','t')]) #pull from frame
        
            bsmt_anchor_el = self.anchor_el - B_f_height - self.joist_space #basement curve
        

            #get the distance to grade
            bsmt_to_dem = self.dem_el - bsmt_anchor_el
                
            
            if bsmt_to_dem <0: #floating basements
                bsmt_opn_ht = 0
            else:
                
                #take the min of all three
                bsmt_opn_ht = min(B_f_height, bsmt_to_dem, max_val)
            
            #===================================================================
            # wrap 
            #===================================================================
            if self.db_f:
                #check basement anchor elevation logic
                if bsmt_anchor_el > self.anchor_el:
                    raise Error('%s basement anchor el (%.2f) is above the main anchor el (%.2f)'
                                  %(self.name, bsmt_anchor_el, self.anchor_el))
                    
                
                """letting this happen for now"""
                if bsmt_to_dem < 0:
                    logger.debug('\n dem_el=%.2f, bsmt_anchor_el=%.2f, B_f_heigh=%.2f, anchor_el=%.2f'
                             %(self.dem_el, bsmt_anchor_el, B_f_height, self.anchor_el))
                                    
                    logger.warning('%s bassement is above grade! bsmt_anchor_el(%.2f) > dem _el (%.2f) '
                                  %(self.name, bsmt_anchor_el, self.dem_el))
                
                
                #detailed output
                boolar = np.array([B_f_height, bsmt_to_dem, max_val, 0]) == bsmt_opn_ht #identify which one you pulled from
                selected = np.array(['B_f_height', 'bsmt_to_dem', 'max_val', 'zero'])[boolar]
                
                logger.debug('got bsmt_opn_ht = %.2f from \'%s\''%(bsmt_opn_ht, selected[0]))
                
            else:
                logger.debug('got bsmt_opn_ht = %.2f ')
            
        #=======================================================================
        # from user provided float
        #=======================================================================
        else:
            bsmt_opn_ht = float(self.model.bsmt_opn_ht_code)
            
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not bsmt_opn_ht >= 0:
                logger.error('\n dem_el=%.2f, bsmt_anchor_el=%.2f, B_f_heigh=%.2f, anchor_el=%.2f'
                             %(self.dem_el, bsmt_anchor_el, B_f_height, self.anchor_el))
                raise Error('%s got a negative bsmt_opn_ht (%.2f)'%(self.name, bsmt_opn_ht))
        
        #=======================================================================
        # wrap up
        #=======================================================================
        self.handle_upd('bsmt_opn_ht', bsmt_opn_ht, proxy(self), call_func = 'set_bsmt_opn_ht')
        

        
        return True
    
    def set_damp_spill_ht(self):

        damp_spill_ht = self.bsmt_opn_ht / 2.0
        
        self.handle_upd('damp_spill_ht', damp_spill_ht, proxy(self), call_func = 'set_damp_spill_ht')   

        return True
              
    
    def set_bsmt_egrd(self): #calculate the basement exposure grade
        """
        bkflowv_f    sumpump_f    genorat_f

        There is also a globabl flag to indicate whether bsmt_egrd should be considered or not
        
        for the implementation of the bsmt_egrd in determining damages, see Dfunc.get_dmg_wsl()
        
        #=======================================================================
        # CALLS
        #=======================================================================
        this is now called during every get_dmgs_wsls()... as gpwr_f is a function of the Flood object
        
        consider only calling w
        """
        #=======================================================================
        # shortcuts
        #=======================================================================
        if self.is_frozen('bsmt_egrd'):
            return 'frozen'

        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('set_bsmt_egrd')
        
        if self.bsmt_f:
            #=======================================================================
            # from plpms
            #=======================================================================
            if self.model.bsmt_egrd_code == 'plpm':
                
                
                #store the plpm status into the cond string
                if self.db_f:
                    cond = 'plpm.'
                    for tag, flag in {'s':self.sumpump_f, 'g':self.genorat_f, 'b':self.bkflowv_f}.items():
                        if flag:
                            cond = '%s%s'%(cond, tag)

                            
                else:
                    cond = 'plpm'
                
                
                #=======================================================================
                # get the grid power state
                #=======================================================================
                if self.session.state == 'init':
                    gpwr_f = self.model.gpwr_f
                    cond = cond + '.init'
                else:
                    gpwr_f = self.floodo.gpwr_f
                    cond = '%s.%s'%(cond, self.floodo.ari)
            
                #=======================================================================
                # grid power is on
                #=======================================================================
                if gpwr_f:
                    cond = cond + '.on'
                    if self.bkflowv_f and self.sumpump_f:
                        bsmt_egrd = 'dry'
                        
                    elif self.bkflowv_f or self.sumpump_f:
                        bsmt_egrd = 'damp'
                        
                    else: 
                        bsmt_egrd = 'wet'
                    
                #=======================================================================
                # grid power is off
                #=======================================================================
                else:
                    cond = cond + '.off'
                    if self.bkflowv_f and self.sumpump_f and self.genorat_f:
                        bsmt_egrd = 'dry'
                        
                    elif self.bkflowv_f or (self.sumpump_f and self.genorat_f):
                        bsmt_egrd = 'damp'
                        
                    else: bsmt_egrd = 'wet'
                
                
                logger.debug('set bsmt_egrd = %s (from \'%s\') with grid_power_f = %s'%(bsmt_egrd,self.bsmt_egrd, gpwr_f))
                
            #=======================================================================
            # ignore bsmt_egrd
            #=======================================================================
            elif self.model.bsmt_egrd_code == 'none':
                cond = 'none'
                bsmt_egrd = 'wet'
                gpwr_f = self.model.gpwr_f
            
            #=======================================================================
            # allow the user to override all
            #=======================================================================
            elif self.model.bsmt_egrd_code in ['wet', 'damp', 'dry']:
                cond = 'global'
                bsmt_egrd = self.model.bsmt_egrd_code
                gpwr_f = self.model.gpwr_f
            
            else:
                raise IOError
            
        else:
            gpwr_f = self.model.gpwr_f
            cond = 'nobsmt'
            bsmt_egrd = 'nobsmt'
        
        #=======================================================================
        # wrap up
        #=======================================================================
        self.bsmt_egrd = bsmt_egrd
        self.gpwr_f = gpwr_f #set this
        
        """report/collect on the flood
        self.parent.childmeta_df.loc[self.dfloc,'bsmt_egrd'] = bsmt_egrd"""
        

        return cond

        
    def set_geo_dxcol(self): #calculate the geometry of each floor based on the geo_build_code
        """
        builds a dxcol with all the geometry attributes of this house

        
        called by load_data when self.session.wdfeats_f = True
        
        #=======================================================================
        # KEY VARS
        #=======================================================================
        geo_build_code: code to indicate what geometry to use for the house. see the dfunc tab
            'defaults': see House.get_default_geo()
            'from_self': expect all geo atts from the binv.
            'any': take what you can from the binv, everything else use defaults.
            'legacy': use gis area for everything
            
        gbc_override: used to override the geo_build_code
        
        geo_dxcol: house geometry
        
        #=======================================================================
        # UDPATES
        #=======================================================================
        when a specific geometry attribute of the house is updated (i.e. B_f_height)
        this dxcol needs to be rebuilt
        and all the dfuncs need to run build_dd_ar()
        
        #=======================================================================
        # TODO
        #=======================================================================
        add some isolated updating?
            for when we only change one floor
        need to add some kwargs to the dynp_handles
                    

        """
        logger = self.logger.getChild('set_geo_dxcol')
        
        if self.is_frozen('geo_dxcol', logger=logger): 
            return True
        
        pars_dxcol = self.session.pars_df_d['hse_geo'] #pull the pars frame
        
        #=======================================================================
        # get default geometry for this house
        #=======================================================================
        self.defa = self.gis_area #default area
        
        
        if self.defa <=0:
            logger.error('got negative area = %.2f'%self.defa)
            raise IOError
        
        self.defp = 4*math.sqrt(self.defa)

        #=======================================================================
        # setup the geo_dxcol
        #=======================================================================   
        dxcol = self.model.geo_dxcol_blank.copy() #get a copy of the blank one\
        
        'I need to place the reference herer so that geometry attributes have access to each other'
        #self.geo_dxcol = dxcol
            
        place_codes     = dxcol.columns.get_level_values(0).unique().tolist()
        #finish_codes    = dxcol.columns.get_level_values(1).unique().tolist()
        #geo_codes       = dxcol.index
        
        
                
        logger.debug("from geo_dxcol_blank %s filling:"%(str(dxcol.shape)))
        #=======================================================================
        # #loop through each place code and compile the appropriate geometry
        #=======================================================================
        for place_code in place_codes:
            geo_df = dxcol[place_code] #geometry for just this place           
            pars_df = pars_dxcol[place_code]
            
            #logger.debug('filling geo_df for place_code: \'%s\' '%(place_code))        
            #===================================================================
            # #loop through and build the geometry by each geocode
            #===================================================================
            for geo_code, row in geo_df.iterrows():
                
                for finish_code, value in row.items():
                    
                    #===========================================================
                    # total column
                    #===========================================================
                    if finish_code == 't':
                        uval = dxcol.loc[geo_code, (place_code, 'u')]
                        fval = dxcol.loc[geo_code, (place_code, 'f')]
                        
                        if self.db_f:
                            if np.any(pd.isnull([uval, fval])):
                                raise IOError
                        
                        
                        if geo_code == 'height': #for height, take the maximum
                            att_val = max(uval, fval)
                                                        
                        else: #for other geometry, take the total
                            att_val = uval + fval
                    
                    #===========================================================
                    # finish/unfinished                       
                    #===========================================================
                    else:
                        #get the user passed par for this
                        gbc = pars_df.loc[geo_code, finish_code]
                        
                        try:gbc = float(gbc)
                        except: pass

                        #===========================================================
                        # #assemble per the geo_build_code
                        #===========================================================
                        #user specified code
                        if isinstance(gbc, str):
                            gbc = str(gbc)
                            if gbc == '*binv':
                                att_name = place_code +'_'+finish_code+'_'+ geo_code #get the att name for this
                                att_val = getattr(self, att_name) #get this attribute from self
                                """"
                                mostly using this key for the B_f_height
                                """
                                
                            elif gbc == '*geo':
                                att_val = self.calc_secondary_geo(place_code, finish_code, geo_code, dxcol=dxcol) #calculate the default value
                                
                            elif gbc.startswith('*tab'):
                                #get the pars
                                tabn = re.sub('\)',"",gbc[5:]) #remove the end parentheisis
                                df = self.session.pars_df_d[tabn]
                                
                                att_name = place_code +'_'+finish_code+'_'+ geo_code #get the att name for this
                                
                                att_val = self.get_geo_from_other(df, att_name)
                                
                            else:
                                att_val = getattr(self, gbc)
                            
                        #user speciifed value
                        elif isinstance(gbc, float): #just use the default value provided in the pars
                            att_val = gbc
                            
                        else: raise IOError
                        
                        logger.debug('set %s.%s.%s = %.2f with gbc \'%s\''%(place_code,finish_code,geo_code, att_val, gbc))
                    
                    #===========================================================
                    # value checks
                    #===========================================================
                    if self.db_f:
                        att_name = place_code +'_'+finish_code+'_'+ geo_code 
                        if not 'float' in type(att_val).__name__:
                            raise Error('got unexpected type for \"%s\': %s'%(att_name, type(att_val)))
                        if pd.isnull(att_val): 
                            raise IOError
                        if att_val < 0: 
                            raise IOError


                        
                    #===========================================================
                    # set the value
                    #===========================================================
                    dxcol.loc[geo_code, (place_code, finish_code)] = att_val
                    
                    #row[finish_code] = att_val #update the ser
                    #logger.debug('set \'%s\' as \'%s\''%(att_name, att_val))
                    
        #=======================================================================
        # rounding
        #=======================================================================
        dxcol = dxcol.round(decimals=2)
                  
        #=======================================================================
        # special attribute setting 
        #=======================================================================
        'need this as an attribute for reporting'
        B_f_height = float(dxcol.loc['height', ('B', 'f')]) #to set the type
        #===============================================================
        # POST
        #===============================================================
        """todo:
        add some checking that we are not changing any geometry attributes with a dynp
            that would be overwritten here
        
        """
        #logger.debug('built house_geo_dxcol %s'%str(dxcol.shape))
        
        self.handle_upd('geo_dxcol', dxcol, weakref.proxy(self), call_func = 'set_geo_dxcol')
        self.handle_upd('B_f_height', B_f_height, weakref.proxy(self), call_func = 'set_geo_dxcol')
                        
        return True
    
    def set_bfh(self):#set the basement finish height into the geo_dxcol 
        
        #shortcutting for those without basements
        if not self.bsmt_f:
            return True
        
        #updat ethe geo_dxcol
        return self.update_geo_dxcol(self.B_f_height, 'height', 'B', 'f')
    
    def xxxset_ffh(self): #set the ff_height (from the anchor_el and the dem_el
        """not sure I want to do this, because we generally get the anchor_el from the ff_height"""
        self.ff_height = self.anchor_el - self.dem_el
        
        
        return True
    
    def update_geo_dxcol(self,
                         nval_raw, #new value
                         geo_code, place_code, finish_code, #locations
                         ):
        

        log = self.logger.getChild('update_geo_dxcol')
        #=======================================================================
        # frozen check
        #=======================================================================
        if self.is_frozen('geo_dxcol', logger=log): 
            return True
        
        #=======================================================================
        # defaults
        #=======================================================================
        nval = round(nval_raw, 2)
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if finish_code == 't':
            raise Error('not implemented')
                
        
        
        
        
        dxcol = self.geo_dxcol.copy() #get a copy of the original
        
        #=======================================================================
        # check if we had a change
        #=======================================================================
        oldv = float(dxcol.loc[geo_code, (place_code, finish_code)])
        if nval == round(oldv, 2):
            log.debug('for %s.%s.%s nval= %.2f has no change... skipping'%(geo_code, place_code, finish_code, nval))
            return True
        
        #=======================================================================
        # #set the new value
        #=======================================================================
        dxcol.loc[geo_code, (place_code, finish_code)] = nval
        
        if self.db_f:
            if not nval == round(float(dxcol.loc[geo_code, (place_code, finish_code)]), 2):
                raise Error('value didnt set')
        
        
        """
        dxcol.loc[geo_code, (place_code, finish_code)] = 99.9
        
        """
        
        log.debug('for %s.%s.%s set %.2f'%(geo_code, place_code, finish_code, nval))
        
        #=======================================================================
        # set the total value
        #=======================================================================
        dxcol.loc[geo_code, (place_code, 't')] = dxcol.loc[geo_code, idx[[place_code], ['u','f']]].sum()
        
        
    
        #=======================================================================
        # #handle the update
        #=======================================================================
        self.handle_upd('geo_dxcol', dxcol, weakref.proxy(self), call_func = 'update_geo_dxcol')
        """
        for just hte basement, would be nice to only force updates on those that have changed
        """
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not nval == round(float(self.geo_dxcol.loc[geo_code, (place_code, finish_code)]), 2):
                raise Error('value didnt set')
        
        return True
        
        
    
    def get_dfunc_df(self): #pull your dfunc_df
        """
        20190512: added this to provide for dfunc handling on all the different acodes
        
        the dfuncs should use this new
        
        
        killing dfuncs and spawning new ones?
            way more complicated...
            this is what we're doing with dfeats
        
        
        how do we tell the dfuncs about their new pars?
            added a loop to the front of build_dfunc() 
        
        simulation reseting?
            as all these pars are in teh dynp_handles (which get loaded into the reset_d automatically
            changes here should be reset
        
        #=======================================================================
        # callers
        #=======================================================================
        dynp_handles (for acode_s and acode_c changes)
        
        
        """
        
        log = self.logger.getChild('set_dfunc_df')
        
        df_raw = self.model.dfunc_mstr_df.copy() #pull from teh session
        """this is configured by scripts_fdmg.Fdmg.load_pars_dfunc()"""
        
        
        #get your slice
        boolidx = np.logical_or(
            df_raw['acode']==self.acode_s, #matching your structural dfuncs
            df_raw['acode']==self.acode_c, #matching contents
            )
        
        df = df_raw[boolidx].copy() #set this
                
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            
            #length check
            """want to allow adding garage curves and removeing some dfuncs"""
            if len(df) > 6:
                raise Error('%s dfunc_df too long (%i) with acode_s=%s and acode_c=%s'
                              %(self.name, len(df), self.acode_s, self.acode_c))
                
        return df
    


    
    def calc_secondary_geo(self,  #aset the default geometry for this attribute
                           place_code, finish_code, geo_code,
                           dxcol = None): 
        
        logger = self.logger.getChild('get_default_geo')
        
        #=======================================================================
        # get primary geometrty from frame
        #=======================================================================
        if dxcol is None: dxcol = self.geo_dxcol
        
        area = dxcol.loc['area',(place_code, finish_code)]
        height = dxcol.loc['height',(place_code, finish_code)]
        
        #=======================================================================
        # calculate the geometris
        #=======================================================================
    
        if geo_code == 'inta':
            per = dxcol.loc['per',(place_code, finish_code)]
            
            att_value = float(area + height * per)
        
        elif geo_code == 'per':
            
            per = 4*math.sqrt(area)
            att_value = float(per)
            
            
        else: raise IOError
        
        logger.debug(" for \'%s\' found %.2f"%(geo_code, att_value))
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            for v in [area, height, per, att_value]:
                if not 'float' in type(v).__name__: 
                    raise IOError
                if pd.isnull(v): 
                    raise IOError
                
                if not v >= 0: 
                    raise IOError
        
        
        return att_value
    
    def xxxrun_bsmt_egrd(self):
        logger = self.logger.getChild('run_bsmt_egrd')

    

    def get_geo_from_other(self, #set the garage area 
                           df_raw, attn_search): 
        """
        we need this here to replicate the scaling done by the legacy curves on teh garage dmg_feats
        
        assuming column 1 is the cross refereence data
        """
        logger = self.logger.getChild('get_geo_from_other')


        #=======================================================================
        # find the cross reference row
        #=======================================================================
        cross_attn = df_raw.columns[0]
        cross_v = getattr(self, cross_attn)  #get our value for this
        
        boolidx = df_raw.iloc[:,0] == cross_v #locate our cross reference
        
        
        #=======================================================================
        # find the search column
        #=======================================================================
        boolcol = df_raw.columns == attn_search
        
        value_fnd = df_raw.loc[boolidx, boolcol].iloc[0,0] #just take the first
        
        if self.db_f:
            if not boolidx.sum() == 1:
                raise IOError
            if not boolidx.sum() == 1:
                raise IOError
        

        return value_fnd
 
 
    def run_hse(self, wsl, **kwargs):
        'TODO: compile the total dfunc and use that instead?'
        logger = self.logger.getChild('run_hse')
        hse_depth = wsl - self.anchor_el
        
        self.run_cnt += 1
        
        #=======================================================================
        # precheck
        #=======================================================================
        """todo: check that floods are increasing
        if self.db_f:
            if self.last_floodo is None:
                pass"""
                
        if self.db_f:
            #full check
            self.check_house()
            #make sure you dont have any updates qued
            if len(self.upd_cmd_od) > 0:
                raise IOError

        #=======================================================================
        # basement egrade reset check
        #=======================================================================
        """because the grid power changes on each flood, we need to re-calc this"""
        if self.model.bsmt_egrd_code == 'plpm':
            #always calc on the first time
            if self.run_cnt ==1:
                cond = self.set_bsmt_egrd()
                
            elif not self.bsmt_f:
                cond='nobsmt'
            
            #some change! re-run the calc
            elif not self.gpwr_f == self.floodo.gpwr_f:
                cond = self.set_bsmt_egrd()
                
            else:
                cond = 'nochng'
                logger.debug('no change in gpwr_f. keeping bsmt egrd = %s'%self.bsmt_egrd)
        else:
            cond = 'no_plpm'
                
        #===============================================================
        # write the beg histor y
        #===============================================================
        if not self.model.beg_hist_df is None:                
            self.model.beg_hist_df.loc[self.dfloc, (self.floodo.ari, 'egrd')] = self.bsmt_egrd
            self.model.beg_hist_df.loc[self.dfloc, (self.floodo.ari, 'cond')] = cond
            

        #=======================================================================
        # calculate the results
        #=======================================================================
        #check for tiny depths
        if hse_depth < self.model.hse_skip_depth:
            logger.debug('depth below hse_obj.vuln_el  setting fdmg=0')
            dmg_ser = pd.Series(name = self.name, index = list(self.dfunc_d.keys()))
            dmg_ser.loc[:] = 0.0

        else:
                
            logger.debug('returning get_dmgs_wsls  \n')
            
            dmg_ser = self.get_dmgs_wsls(wsl, **kwargs)

        #=======================================================================
        # wrap up
        #=======================================================================
        self.floodo = None #clear this
        

        return dmg_ser

    def get_dmgs_wsls(self,  #get damage at this depth from each Dfunc
                    wsl, 
                    dmg_rat_f = False, #flat to include damage ratios in the outputs

                    ): 
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        res_ser: shortcut so that damage are added to this series
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_dmgs_wsls')
        id_str = self.get_id()
        
        #=======================================================================
        # precheck
        #=======================================================================

            

        #=======================================================================
        # fast calc
        #=======================================================================
        if not dmg_rat_f:
            dmg_ser = pd.Series(name = self.name, index = list(self.dfunc_d.keys()))
            
            """
            logger.debug('\'%s\' at wsl= %.4f anchor_el = %.4f for %i dfuncs bsmt_egrd \'%s\'\n'
                     %(id_str, wsl, self.anchor_el, len(dmg_ser), self.bsmt_egrd))"""

            for dmg_type, dfunc in self.kids_d.items():
    
                logger.debug('getting damages for \'%s\' \n'%dmg_type)
        
                #get the damge
                _, dmg_ser[dmg_type], _ = dfunc.run_dfunc(wsl)
                
                dfunc.get_results() #store these outputs if told
                

        #=======================================================================
        # full calc
        #=======================================================================
        else:
            raise IOError #check this
            dmg_df = pd.DataFrame(index = list(self.dfunc_d.keys()), columns = ['depth', 'dmg', 'dmg_raw'])
            dmg_ser = pd.Series()
            
            logger.debug('\'%s\' at wsl= %.4f anchor_el = %.4f for %i dfuncs bsmt_egrd \'%s\''
                     %(id_str, wsl, self.anchor_el, len(dmg_df), self.bsmt_egrd))
            
            for indx, row in dmg_df.iterrows():
                dfunc = self.kids_d[indx]
                
                row['depth'], row['dmg'], row['dmg_raw'] = dfunc.run_dfunc(wsl)
                
                dfunc.get_results() #store these outputs if told
                
                #enter into series
                dmg_ser[indx] = row['dmg']
                dmg_ser['%s_rat'%indx] = row['dmg_raw']
                
        #=======================================================================
        # post chekcs
        #=======================================================================
                
        #=======================================================================
        # wrap up
        #=======================================================================
        logger.debug('at %s finished with %i dfuncs queried and res_ser: \n %s \n'
                     %(self.model.tstep_o.name, len(self.kids_d), dmg_ser.values.tolist()))

        
           

        return dmg_ser
    

                
    def raise_total_dfunc(self, #compile the total dd_df and raise it as a child
                          dmg_codes = None, place_codes = None): 
        """ this is mostly used for debugging and comparing of curves form differnet methods
        
        #=======================================================================
        # todo
        #=======================================================================
        allow totaling by 
        possible performance improvement;
            compile the total for all objects, then have Flood.get_dmg_set only run the totals
            
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('raise_total_dfunc')
        tot_name = self.get_tot_name(dmg_codes)
        
        if dmg_codes is None:  dmg_codes = self.model.dmg_codes
        if place_codes is None: place_codes = self.model.place_codes
        
        #=======================================================================
        # get the metadata for the child
        #=======================================================================
        df_raw = self.session.pars_df_d['dfunc'] #start with the raw tab data
        
        #search by placecode
        boolidx1 = df_raw['place_code'] == 'total' #identify all the entries except total
        
        #search by dmg_code where all strings in the list are a match
        boolidx2 = hp_pd.search_str_fr_list(df_raw['dmg_code'], dmg_codes, all_any='any') #find 
        
        if boolidx2.sum() <1:
            logger.warning('unable to find a match in the dfunc tab for %s. using default'%tot_name)
            boolidx2 = pd.Series(index = boolidx2.index, dtype = np.bool) #all true 


        'todo: add some logic for only finding one of the damage codes'
        
        #get this slice
        boolidx = np.logical_and(boolidx1, boolidx2)
        
        if not boolidx.sum() == 1: 
            logger.error('childmeta search boolidx.sum() = %i'%boolidx.sum())
            raise IOError
        
        att_ser = df_raw[boolidx].iloc[0]

        'need ot add the name here as were not using the childname override'
                
        logger.debug('for place_code: \'total\' and dmg_code: \'%s\' found child meta from dfunc_df'%(dmg_codes))
        #=======================================================================
        # raise the child
        #=======================================================================
        #set the name        
        child = self.spawn_child(att_ser = att_ser, childname = tot_name)
        
        #=======================================================================
        # #do custom edits for total
        #=======================================================================
        child.anchor_el = self.anchor_el
        
        #set the dd_ar
        dd_df = self.get_total_dd_df(dmg_codes, place_codes)
        depths = dd_df['depth'].values - child.anchor_el #convert back to no datum
        
        child.dd_ar     = np.array([depths, dd_df['damage'].values])
        
        #add this to thedictionary
        self.kids_d[child.name] = child
        
        logger.debug('copied and edited a child for %s'%child.name)
        
        return child
    
    def get_total_dd_df(self, dmg_codes, place_codes): #get the total dd_df (across all dmg_types)
        logger = self.logger.getChild('get_total_dd_df')
        
        #=======================================================================
        # compile al lthe depth_damage entries
        #=======================================================================
        df_full = pd.DataFrame(columns = ['depth', 'damage_cum', 'source'])
        
        # loop through and fill the df
        cnt = 0
        for datoname, dato in self.kids_d.items():
            if not dato.dmg_code in dmg_codes: continue #skip this one
            if not dato.place_code in place_codes: continue
            
            cnt+=1
            #===================================================================
            # get the adjusted dd
            #===================================================================
            df_dato = pd.DataFrame() #blank frame
            
            df_dato['depth'] =  dato.dd_ar[0]+ dato.anchor_el  #adjust the dd to the datum
            df_dato['damage_cum'] = dato.dd_ar[1]
            """the native format of the dmg_ar is cumulative damages
            to sum these, we need to back compute to incremental
            """
            df_dato['damage_inc'] = hp_pd.get_incremental(df_dato['damage_cum'], logger=logger)
            df_dato['source'] = datoname
            
            #append these to the full
            df_full = df_full.append(df_dato, ignore_index=True)
            
        logger.debug('compiled all dd entries %s from %i dfuncs with dmg_clodes: %s'
                     %(str(df_full.shape), cnt, dmg_codes))
        
        df_full = df_full.sort_values('depth').reset_index(drop=True)
        
        #=======================================================================
        # harmonize this into a dd_ar
        #=======================================================================
        #get depths
        
        depths_list = df_full['depth'].sort_values().unique().tolist()
        
        #get starter frame
        dd_df = pd.DataFrame(columns = ['depth', 'damage'])
        dd_df['depth'] = depths_list #add in the depths
        
        for index, row in dd_df.iterrows(): #sort through and sum by depth
            
            boolidx = df_full['depth'] <= row['depth'] #identify all those entries in the full 
            
            row['damage'] = df_full.loc[boolidx, 'damage_inc'].sum() #add these as the sum
            
            dd_df.iloc[index,:] = row #update the master
            
        logger.debug('harmonized and compiled dd_df %s'%str(dd_df.shape))
        
        self.dd_df = dd_df
        
        return dd_df
      
    def get_tot_name(self, dmg_codes): #return the equilvanet tot name
        'not sure whats going on here'
        new_str = 'total_'
        for dmg_code in dmg_codes: new_str = new_str + dmg_code
        
        return new_str
    
    def calc_statres_hse(self): #calculate statistics for the house (outside of a run)
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        this is always called with mypost_update() executing each command in self.post_upd_func_s()
        
        mypost_update() is called:
            init_dyno()    #first call before setting the OG values
            session.post_update() #called at the end of all the update loops
            
        
        """
        logger = self.logger.getChild('calc_statres_hse')
        
        if self.acode_s == 'none':
            """
            ToDo:
            need to fix how we handle null assets:
            
            acode_s='none':
                this should be a place holder asset
                only parcel attributs are read from the binv (parcel_area, asector)
                
                all output attributes should be NULL
                
                When we transition a 'none' to a real,
                    we should have some check to make sure we have all hte attributes we need?
                    
            acode_c='none'
                fine... only calc structural damages (empty asset).
                
            
            """
            raise Error('not sure how this manifests on the outputers')
        
        s = self.session.outpars_d[self.__class__.__name__]
        #=======================================================================
        # BS_ints
        #=======================================================================
        if 'BS_ints' in s:
            'I dont like this as it requires updating the child as well'
            """rfda curves also have this stat
            if self.dfunc_type == 'dfeats':"""
            
            #updat eht ekid
            if not self.kids_d['BS'].calc_intg_stat(): 
                raise IOError
            
            self.BS_ints = self.kids_d['BS'].intg_stat
            
            """this is handled by set_og_vals()
            if self.session.state == 'init':
                self.reset_d['BS_ints'] = self.BS_ints"""
                
            logger.debug('set BS_ints as %.4f'%self.BS_ints)
                
        if 'vuln_el' in s:
            self.set_vuln_el()
            
        
        if 'max_dmg' in s:
            self.max_dmg = self.get_max_dmg()
            self.parent.childmeta_df.loc[self.dfloc, 'max_dmg'] = self.max_dmg #set into the binv_df
            
        if 'dummy_cnt' in s:
            cnt = 0
            for dfunc in self.kids_d.values():
                if dfunc.dummy_f:
                    cnt+=1
            self.dummy_cnt = cnt 
            
        if 'kid_nm_t' in s:
            self.kid_nm_t = tuple([kid.get_tag() for kid in self.kids_d.values()])

        if 'max_dmg_nm' in s:
            d = dict()
            for name, dfunc in self.kids_d.items():
                if dfunc.dummy_f:
                    d[dfunc.get_tag()] = 'dummy'
                else:
                    d[dfunc.get_tag()] = "{:,.1f}".format(max(dfunc.dd_ar[1]))
            self.max_dmg_nm = str(d)
            
        if 'beg_hist' in s and (not self.model.beg_hist_df is None):
            """view(self.model.beg_hist_df)"""
            self.beg_hist = str(self.model.beg_hist_df.loc[self.dfloc,:].dropna().to_dict())
            

        return True
    

    
    def set_vuln_el(self): #calcualte the minimum vulnerability elevation
        """
        #=======================================================================
        # CALLS
        #=======================================================================

        TODO: consider including some logic for bsmt_egrade and spill type
        """
        #=======================================================================
        # check frozen and dependenceis
        #=======================================================================
        logger = self.logger.getChild('set_vuln_el')
        
        """this is a stat, not a dynamic par
        if self.is_frozen('vuln_el', logger=logger): return True"""
        
        vuln_el = 99999 #starter value
        
        for dmg_type, dfunc in self.kids_d.items():
            if dfunc.dummy_f: 
                continue #skip these
            else:
                vuln_el = min(dfunc.anchor_el, vuln_el) #update with new minimum
            

        logger.debug('set vuln_el = %.2f from %i dfuncs'%(vuln_el, len(self.kids_d)))
        
        if vuln_el == 99999:
            vuln_el = np.nan
            
        self.vuln_el = vuln_el
            
        return True
    
    
 
    def get_max_dmg(self): #calculate the maximum damage for this house
        #logger = self.logger.getChild('get_max_dmg')
        
        #=======================================================================
        # precheck
        #=======================================================================
        if self.db_f:
            #loop and check dummies
            for dmg_type, dfunc in self.kids_d.items():
                if not dfunc.dummy_f:
                    if not len(dfunc.dd_ar)==2:
                        raise Error('%s.%s is real but got unexpected dd_ar length: %i'
                                      %(self.name, dfunc.name, len(dfunc.dd_ar)))
        
        #=======================================================================
        # calcs
        #=======================================================================
        
        max_dmg = 0
        for  dfunc in self.kids_d.values():
            if not dfunc.dummy_f:
                max_dmg+= dfunc.dd_ar[1].max()
                
        return max_dmg
        
        """sped this up
        ser = pd.Series(index = list(self.kids_d.keys()))
        
        #=======================================================================
        # collect from each dfunc
        #=======================================================================
        for dmg_type, dfunc in self.kids_d.items():
            try:
                ser[dmg_type] = dfunc.dd_ar[1].max()
            except: #should only trip for unreal baseements
                ser[dmg_type] = 0.0
                
                
                if self.db_f:
                    if self.bsmt_f:
                        raise Error('failed to get max damage and I have a basement')
            
        return ser.sum()"""

        
        
    def plot_dd_ars(self,   #plot each dfunc on a single axis
                    datum='house', place_codes = None, dmg_codes = None, plot_tot = False, 
                    annot=True, wtf=None, title=None, legon=False,
                    ax=None, 
                    transparent = True, #flag to indicate whether the figure should have a transparent background
                    **kwargs):
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        datum: code to indicate what datum to plot the depth series of each dd_ar
            None: raw depths (all start at zero)
            real: depths relative to the project datum
            house: depths relative to the hse_obj anchor (generally Main = 0)
            
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('plot_dd_ars')
        if wtf==None:           wtf= self.session._write_figs
        if dmg_codes is None:   dmg_codes = self.model.dmg_codes
        if place_codes is None: place_codes = self.model.place_codes
            
        if title is None:
            title = 'plot_dd_ars on %s for %s and %s'%(self.name, dmg_codes, place_codes)
            if plot_tot: title = title + 'and T'
        
        'this should let the first plotter setup the axis '

        logger.debug('for \n    dmg_codes: %s \n    place_codes: %s'%(dmg_codes, place_codes))
        #=======================================================================
        # plot the dfuncs that fit the criteria
        #=======================================================================
        dfunc_nl = [] #list of dfunc names fitting criteria
        for datoname, dato in self.dfunc_d.items():
            if not dato.dmg_code in dmg_codes: continue
            if not dato.place_code in place_codes: continue
            ax = dato.plot_dd_ar(ax=ax, datum = datum, wtf=False, title = title, **kwargs)
            
            dfunc_nl.append(dato.name)
            
        #=======================================================================
        # add the total plot
        #=======================================================================
        if plot_tot:
            #get the dato
            tot_name = self.get_tot_name(dmg_codes)
            if not tot_name in list(self.kids_d.keys()): #build it
                'name searches should still work'
                
                tot_dato = self.raise_total_dfunc(dmg_codes, place_codes)
            else:
                tot_dato = self.kids_d[tot_name]
            
            #plot the dato
            ax = tot_dato.plot_dd_ar(ax=ax, datum = datum, wtf=False, title = title, **kwargs)
            
        #=======================================================================
        # add annotation
        #=======================================================================
        if not annot is None:
            if annot:
                """WARNING: not all attributes are generated for the differnt dfunc types
                """               
                B_f_height = float(self.geo_dxcol.loc['height',('B','f')]) #pull from frame
                
                
                annot_str = 'acode = %s\n'%self.acode +\
                            '    gis_area = %.2f m2\n'%self.gis_area +\
                            '    anchor_el = %.2f \n'%self.anchor_el +\
                            '    dem_el = %.2f\n'%self.dem_el +\
                            '    B_f_height = %.2f\n'%B_f_height +\
                            '    bsmt_egrd = %s\n'%self.bsmt_egrd +\
                            '    AYOC = %i\n \n'%self.ayoc
                            
                #add info for each dfunc
                
                for dname in dfunc_nl:
                    dfunc = self.dfunc_d[dname]
                    annot_str = annot_str + annot_builder(dfunc)
    
            else: annot_str = annot
            #=======================================================================
            # Add text string 'annot' to lower left of plot
            #=======================================================================
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            
            x_text = xmin + (xmax - xmin)*.7 # 1/10 to the right of the left axis
            y_text = ymin + (ymax - ymin)*.01 #1/10 above the bottom axis
            anno_obj = ax.text(x_text, y_text, annot_str)
                
        #=======================================================================
        # save figure
        #=======================================================================
        if wtf: 
            """
            self.outpath
            """
            fig = ax.figure
            flag = hp.plot.save_fig(self, fig, dpi = self.dpi, legon=legon, transparent = transparent)
            if not flag: raise IOError 
            
        logger.debug('finished as %s'%title)
        
        return ax
    
    def write_all_dd_dfs(self, tailpath = None): #write all tehchildrens dd_dfs
        
        if tailpath is None: tailpath = os.path.join(self.outpath, self.name)
        
        if not os.path.exists(tailpath): os.makedirs(tailpath)
        
        for gid, childo in self.kids_d.items():
            
            if not childo.dfunc_type == 'dfeats': continue #skip this one\
            
            filename = os.path.join(tailpath, childo.name + ' dd_df.csv')
            
            childo.recompile_dd_df(outpath = filename)
            
    