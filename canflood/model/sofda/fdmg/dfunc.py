'''
Created on May 12, 2019

@author: cef
'''

#===============================================================================
# IMPORT STANDARD MODS -------------------------------------------------------
#===============================================================================
import logging, os,  time, re, math, copy, gc, weakref, random, scipy


import pandas as pd
import numpy as np
import scipy.integrate

from model.sofda.fdmg.dmgfeat import Dmg_feat

#===============================================================================
# shortcuts
#===============================================================================


from weakref import WeakValueDictionary as wdict
from weakref import proxy



idx = pd.IndexSlice

#===============================================================================
#  IMPORT CUSTOM MODS ---------------------------------------------------------
#===============================================================================
#import hp.plot
#import model.sofda.hp.basic as hp_basic
import model.sofda.hp.pd as hp_pd
import model.sofda.hp.oop as hp_oop
#import model.sofda.hp.data as hp_data

import model.sofda.hp.dyno as hp_dyno
import model.sofda.hp.sim as hp_sim

from hlpr.exceptions import Error
from model.sofda.hp.pd import view

# logger setup -----------------------------------------------------------------------
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')


class Dfunc(
            #hp.plot.Plot_o,
            hp_dyno.Dyno_wrap,
            hp_sim.Sim_o, #damage function of a speciic type. to be attached to a house
            hp_oop.Parent,
            hp_oop.Child): 
    '''
    #===========================================================================
    # architecture
    #===========================================================================
    rfda per house predicts 4 damage types (MS, MC, BS, BC)\
    
    do we want these damage types comtained under one Dfunc class object? or separate?
    
        lets keep them separate. any combining can be handled in the House class
        
    #===========================================================================
    # main vars
    #===========================================================================
    dd_ar:    main damage array (np.array([depth_list, dmg_list])) data
        using np.array for efficiency
        this is compiled based on dfunc_type see:
            legacy: get_ddar_rfda 
            abmri: get_ddar_dfeats (this requires some intermittent steps)

    '''
    #===========================================================================
    # program pars
    #===========================================================================
    
    """post_cmd_str_l      = ['build_dfunc']
    
    # object handling overrides
    load_data_f         = True
    raise_kids_f        = True #called explicilly in load_data()"""
    #raise_in_spawn_f    = True #load all the children before moving on to the next sibling
    db_f                = False
    
    #set of expected attributes (and their types) for validty checking
    exp_atts_d = {'dmg_code':str, 'dfunc_type':str, 
                  #'bsmt_egrd_code':str, #we build this later
                  'anchor_el':float, 'dmg_type':str}
        
    
    """
    #===========================================================================
    # #shadow kids
    #===========================================================================
    see note under Dfeats
    """
    reset_shdw_kids_f = False #flag to install the shadow_kids_d during reset 
    shdw_kids_d   = None #placeholder for the shadow kids
    
    kid_cnt         = 0 #number of kids you have
    
    #===========================================================================
    # passed pars from user
    #===========================================================================
    """I dont think the Dfunc should have this
    acode           =''"""
    place_code      = None 
    dmg_code        = ''  #contets vs structural
    dfunc_type      =''
    bsmt_egrd_code = ''
    anchor_ht_code = None 
    geo_build_code = None 
    rat_attn       = '*none' #attribute name  to scale by for relative damage functions

    #===========================================================================
    # calculation pars
    #===========================================================================
    dd_ar           = None #2d array of depth (dd_ar[0])vs total damage (dd_ar[1]) values
    dmg_type        = ''  #type of damage predicted by this function (MC, MS, BC, etc.)
    
    anchor_el       = 0.0 #height from project datum to the start of the dd_ar (depth = 0)

    
    #headers to keep in the dyn_dmg_df
    dd_df_cols = ['name', 'base_price', 'depth', 'calc_price']
    
    depth_allow_max = 10 #maximum depth to allow without raising an error with dg_f = True. 
    '10m seems reasonable for a 12ft basement and 1000 yr flood' 
    
    tag             = '' #type of dfeats curve (acode + place_code)
    
    dummy_f         = False #whether this dfunc is just a placeholder

    
    intg_stat       = None #placeholder for this stat
     

    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dfunc')
        logger.debug('start _init_')
        #=======================================================================
        # update program handlers
        #=======================================================================
        self.inherit_parent_ans=set(['mind', 'model'])
        
        
        super(Dfunc, self).__init__(*vars, **kwargs) #initilzie teh baseclass   
        
        #=======================================================================
        #common setup
        #=======================================================================

        if self.sib_cnt == 0:
            logger.debug('sib_cnt = 0. setting complex atts')
            self.kid_class      = Dmg_feat #mannually pass/attach this
            self.hse_o          = self.parent 
            'this should be a proxy'
        
                    
        #=======================================================================
        # #unique
        #=======================================================================
        'for now, only using this on BS curves'
        if self.dmg_type == 'BS':
            self.post_upd_func_s = set([self.calc_statres_dfunc])
        
        """for plotting
        #misc
        self.label = self.name + ' (%s) (%s)'%(self.dfunc_type, self.units)"""
        
            
        if not self.place_code == 'total':
            """NO! dfunc shouldnt care about its acode
            #set acode
            if self.dmg_code == 'C': #contents
                self.acode = self.parent.acode_c
            elif self.dmg_code == 'S': #structural
                self.acode = self.parent.acode_s"""
                
            #loaders
            logger.debug('build_dfunc \n')
            self.build_dfunc()
            logger.debug('init_dyno \n')
            self.init_dyno()
        
        #=======================================================================
        # checks
        #=======================================================================
        if self.db_f: 
            logger.debug("checking myself \n")
            self.check_dfunc()
            
            if hasattr(self, 'kids_sd'):
                raise IOError

        self.logger.debug('finished _init_ as \'%s\' \n'%(self.name))
        
        return
    
    def check_dfunc(self):
        logger = self.logger.getChild('check_dfunc')

        #attribute check
        self.check_atts()
        #=======================================================================
        # hierarchy
        #=======================================================================
        """could standardize this somewhere"""
        if not self.model == self.parent.model:
            raise IOError('\"%s\' model (%s) does not match parents \'%s\' = %s'
                          %(self.__class__.__name__,
                            self.model,
                            self.parent.__class__.__name__,
                            self.parent.model))

        #=======================================================================
        # parameter logic
        #=======================================================================
        if self.dfunc_type == 'rfda':
            #no garages allowed
            if self.place_code == 'G':
                raise IOError('rfda curves can not have garages')
            
            #area ratio type
            if not self.rat_attn == 'self.parent.gis_area':
                raise IOError('for RFDA, expected \'gis_area\' for rat_attn')
            
        elif self.dfunc_type == 'dfeats':
            if not self.dummy_f:
                if len(self.kids_d) == 0:
                    raise IOError('no kids!')
            
            
            #area ratio type
            if not self.rat_attn =='*none':
                raise IOError('expected \'*none\' for rat_attn on dfeats')
            
            #check the reseting
            if not self.reset_dfunc in self.reset_func_od:
                raise IOError('dfunc reset function missing from the reset que')
            
            #check that all the dfeats have the right acode
            """moved this into check_dfeat"""

            
            #check your dfeats
            for name, dfeat in self.kids_d.items():
                dfeat.check_dfeat()
        
        if not self.rat_attn =='*none':
            
            try:
                _ = eval(self.rat_attn)
            except:
                logger.error('failed to execute passed \'%s\''%self.rat_attn)
                raise IOError
            
        #=======================================================================
        # total checks
        #=======================================================================
        if self.place_code == 'total':
            if self.anchor_ht_code == '*hse':
                raise IOError #hse not allowed for total curve
            
            
        #=======================================================================
        # built checks
        #=======================================================================
        if not self.session.state == 'init':
            
            if not 'dd_ar' in list(self.reset_d.keys()):
                raise IOError
            
            ar = self.dd_ar
            #check unreal basement dfuncs
            if self.dummy_f:
                if not len(ar) == 0:
                    raise IOError('%s is unreal and has an unrecognized dd_ar'%self.name)
            else:
                if len(ar) == 0:
                    raise IOError('%s.%s is real but got no dd_ar'%(self.parent.name, self.tag))
                
                if not ar.shape[0] == 2 and ar.shape[1] > 4:
                    raise IOError('bad shape on real dfunc (%s) dd_ar (%s)'%(self.name, str(ar.shape))) 
            
        logger.debug('finished check')
        return

    def build_dfunc(self):  #build from scratch
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        _init_
        handles
        
        """
        'todo: move these commands elsewhere'
        logger = self.logger.getChild('build_dfunc(%s)'%self.get_id())
        
        #=======================================================================
        # precheck
        #=======================================================================
        """NO! WE shouldnt have an acode
        #check the acode
        check_match(self, self.parent, attn='acode')"""
    
        """leaving this to more specific functions
        #=======================================================================
        # dependency check
        #=======================================================================
        if not self.session.state == 'init':
            dep_p = [([self.parent],['set_geo_dxcol()'] )] #dependency paring
            if self.deps_is_dated(dep_p, method = 'force', caller = 'build_dfunc'):
                raise IOError #because we are forcing this should alwys return FALSE"""
            
        'need to clear this so the children will update'
        self.del_upd_cmd(cmd_str = 'build_dfunc')
        self.del_upd_cmd(cmd_str = 'recompile_ddar')
        
        #=======================================================================
        # new pars
        #=======================================================================
        if not self.session.state == 'init':
            if not self.reload_pars():
                raise IOError()
            

        #=======================================================================
        # sett dummy status
        #=======================================================================
        self.set_dummyf()

        #=======================================================================
        # custom loader funcs
        #=======================================================================
        logger.debug('setting tag')
        self.tag = self.get_tag() #added dmg_code to this
        logger.debug('set_dfunc_anchor() \n')
        res1 = self.set_dfunc_anchor() #calculate my anchor elevation
        
        logger.debug('build_dd_ar() \n')
        res2 = self.build_dd_ar()
        

        if self.session.state == 'init':
            
            if self.dummy_f:
                pass #no meta_df to use
            elif self.dfunc_type == 'dfeats':
                'add this here so the children have a chance to fill it out during load'
                self.reset_d['childmeta_df'] = self.childmeta_df.copy()
                
        else:
            pass
            """some comands (constrain_dd_ar) we want to leave in the que
            self.halt_update()"""
            
            """cleared this at the beginning
            if len(self.upd_cmd_od) > 0:
                self.del_upd_cmd(cmd_str = 'recompile_ddar()')"""

        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if len(self.upd_cmd_od) > 0:
                logger.warning('still have updates queud: \n %s'%list(self.upd_cmd_od.keys()))

        logger.debug('finished \n')
        
        return True #never want to re-que this
        

               
            
    def build_dd_ar(self): #buidl the damage curve from codes passed on the 'dfunc' tab
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        build_dfunc
        
        (this could be used by some handles...but not a great case)

        """
        #=======================================================================
        # setups
        #=======================================================================
        logger = self.logger.getChild('build_dd_ar')
        
        #=======================================================================
        # dependencies and frozen
        #=========================================================== ============
        if not self.session.state=='init':
            """shouldnt really need this"""

            if self.is_frozen('dfunc_type', logger = logger): 
                raise IOError #why was this frozen?
            
            dep_l =  [([self], ['reload_pars'])]
            
            if self.deps_is_dated(dep_l, method = 'force', caller = 'build_dd_ar'):
                raise IOError('should have forced the update')
                             

        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            #per dfunc_type
            if self.dfunc_type == 'rfda':
                """switched to hse_geo tab
                if not self.geo_build_code == 'defaults':
                    logger.error('dfunc_type=rfda only uses gis_area. therefore geo_build_code must = defaults') 
                    raise IOError"""
                
                if not self.anchor_ht_code == '*rfda':
                    logger.debug('dfunc_type=rfda got  anchor_ht_code != rfda_par.')
                    'as were keeping the contents rfda, need to allow cross anchoring types'
                    
            elif self.dfunc_type == 'dfeats':                
                if self.dmg_code == 'C':
                    logger.error('Contents damage not setup for dfunc_type = dfeats')
                    raise IOError
                
            elif self.dfunc_type == 'depdmg':
                pass #not impoxing any restrictions?
                
            elif pd.isnull(self.dfunc_type):
                pass
            
            elif self.dfunc_type == '':
                """for 'none' passed on the dfunc tab"""
                pass
                
            else: 
                raise IOError('got unrecognized dfunc_type: \'%s\''%self.dfunc_type)
            
        #=======================================================================
        # build the children
        #=======================================================================                        
        if self.dfunc_type == 'dfeats':
            logger.debug('dfunc_type = dfeats. raising children')
            self.raise_dfeats()  #grow all the damage features
        else:
            self.kids_d = wdict() #set an empty container

        
        #=======================================================================
        # complile teh curve
        #=======================================================================
        if self.dummy_f:
            dd_ar = np.array([])
        elif self.dfunc_type == 'rfda':#leagacy
            dd_ar = self.get_ddar_rfda() #build the dfunc from this house type

        elif self.dfunc_type == 'dfeats':
            dd_ar = self.get_ddar_dfeats() #compile the damage array
            
        elif self.dfunc_type == 'depdmg':
            dd_ar = self.get_ddar_depdmg()

        else: 
            raise IOError('unrecognized dfunc_type \'%s\''%self.dfunc_type)
        
        #=======================================================================
        # wrap up
        #=======================================================================
        'constrain will set another copy onto this'
        self.dd_ar = dd_ar

        #=======================================================================
        # constrain_dd_ar
        #=======================================================================
        """even thourgh we may receive multiple ques, this should be called everytime. 
            build_dfunc() will clear the que"""

        constrain_result = self.constrain_dd_ar()
        
        """cosntrain_dd_ar will execute this
        self.handle_upd('dd_ar', dd_ar, proxy(self), call_func = 'build_dd_ar')
        'this will que constrain_dd_ar for non init runs'"""
        
        #=======================================================================
        # get stats
        #=======================================================================
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if 'build_dd_ar()' in list(self.upd_cmd_od.keys()): 
                raise IOError
            if constrain_result:
                if 'constrain_dd_ar()' in list(self.upd_cmd_od.keys()): 
                    raise IOError
            
            """
            see note. not a strong case for queuing this command directly (with handles)
            'because we are not using the update handler, just calling this'
            self.del_upd_cmd(cmd_str = 'build_dd_ar') #delete yourself from the update command list"""
            
        
        logger.debug('finished for dfunc_type \'%s\' and dd_ar %s \n'%(self.dfunc_type, str(self.dd_ar.shape)))
        
        return True
    
    def reload_pars(self,
                    attns = ['dfunc_type','rat_attn','anchor_ht_code'],
                    ): #re acquiring pars from the parents meta_df
        """
        because we are only calling this with the buidl_dfunc,
            Ive left it out of hte handles
            
        However, we could add it into the head of the list
        """
        #=======================================================================
        # setups and defaults
        #=======================================================================
        logger = self.logger.getChild('reload_pars')
        df = self.model.dfunc_mstr_df
        acode = self.get_acode()
        tag = self.get_tag()
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if tag == self.tag:
                """this could trip if we redevelop onto the same type"""
                logger.warning('%s.%s tag \'%s\' has not changed'%(self.parent.name, self.name, self.tag))
        
        #=======================================================================
        # find yourself
        #=======================================================================
        boolidx = np.logical_and(
            df['name']==self.name,
            df['acode']==acode
            )
        

        if self.db_f:
            if not boolidx.sum() == 1:
                raise IOError
                    
        #=======================================================================
        # get the static atts
        #=======================================================================
        self.del_upd_cmd(cmd_str = 'reload_pars')
        
        #loop through the simple attributes which can be changed by changes in the House's acode
        """this will overwrite any Class level defaults (where the original df passed nans)"""
        for attn in attns:
            
            nattv = df.loc[boolidx, attn] #get the new value       
            self.handle_upd(attn, nattv, proxy(self), call_func = 'reload_pars') #set the new value
            
        logger.debug('finished reloading %i pars from the \'model.dfunc_mstr_df\': \n     %s'%(len(attns), attns))
        return True
        
    
    def get_ddar_rfda(self): #build a specific curve from rfda classic
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        raw_dcurve_df: raw df from the standard rfda damage curve file
            Ive left the sorting/cleaning to here'
            may be slightly more efficient (although more confusing) to clean this in the session
            
        #=======================================================================
        # OUTPUTS
        #=======================================================================
        dd_ar: depth damage per m2 
            NOTE: this is different than the dd_ar for the dyn_ddars
            reasoning for this is I want the parent calls to all be in the run loop
                (rather than multiplying the rfda $/m2 by the parents m2 during _init_)
                
        #=======================================================================
        # TODO:
        #=======================================================================
        consider precompiling all of these and making pulls to a shadow set instead
            
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_ddar_rfda')
        
        self.dfunc_type     = 'rfda' #set the dfunc type
        """do we need this??"""
        
        
        dmg_type            = self.dmg_type
        raw_dcurve_df       = self.model.kids_d['rfda_curve'].data
        'need this goofy reference as the fdmg_o has not fully loaded'
        
        acode_sec_d         =self.session.acode_sec_d #{acode: asector}
        
        #get the correct acode
        acode               = self.get_acode()


        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not hp_pd.isdf(raw_dcurve_df):
                raise IOError
            
            if acode == '':
                raise IOError('acode not set yet')
            
            if dmg_type == '':
                raise IOError('%s has no dmg_type'%self.name)
            
            """for new houses we should run this mid session
            if not self.session.state == 'init': 
                raise IOError"""
        
        logger.debug('for dmg_type = %s, acode = %s and raw_dcurve_df %s'%(dmg_type, acode, str(raw_dcurve_df.shape)))
        
        #=======================================================================
        # preclean
        #=======================================================================
        df1 =   raw_dcurve_df.dropna(how = 'all', axis='index').dropna(how = 'all', axis='columns') #drop columns where ANY values are na
        
        #=======================================================================
        # #identify the sector
        #=======================================================================
        #complex, (sres) search
        if not acode in acode_sec_d:
            #do a search for this
            asector = None
            for acode_srch, asec in acode_sec_d.items():
                
                if acode in acode_srch: #found
                    asector = asec
                    break
                
            if asector is None:
                raise IOError('failed to find \'%s\' in teh acdoes'%acode)
        
        #simple
        else:   
            asector = acode_sec_d[acode]
            
            
        #identify those rwos for this sector
        boolidx_sec = df1['asector'] == asector
        #=======================================================================
        # get the raw data by acode_srch
        #=======================================================================
        #find the rows for this acode
        """these have prefixes attached"""
        if asector == 'sres' or asector == 'mres':
            boolidx_code = df1.iloc[:,0].astype(str).str.contains(acode) #
            
            if not boolidx_code.sum()==4:
                raise IOError('too many hits for sres acode \'%s\''%acode)

        elif asector == 'nores':
            boolidx_code = df1.iloc[:,0].astype(str)== acode#
        else:
            raise IOError
        

        #=======================================================================
        # by sector
        #======================================================================= 
        #column dropp/cleaning       
        df2 = df1.drop(columns=['asector']) #drop this one
        boolcol = df2.columns.isin(df2.columns[:2])#those other than the first 2
        
        #single and multi
        if asector == 'sres' or asector == 'mres':
            #slice to just the residential
            df_res = df2[boolidx_sec].dropna(axis=1, how='any')
            srch_coln = df_res.columns[-1] #column name to search on
        
            #damage types are in the last column
            boolidx_dmg = df2[srch_coln].astype(str).str.contains(dmg_type)
            
            """
            view(df2.loc[boolidx_d,:].dropna(axis=1, how='all'))
            """
            
            #append dropper columns
            boolcol = np.logical_or(
                boolcol, # first 2
                df2.columns.isin([srch_coln]) #last (of the residential)
                )
            """others are dropped below"""
            
            #identfy the row we want
            boolidx = np.logical_and(boolidx_dmg, boolidx_code)

        #non residential
        elif asector == 'nores':
            boolidx = boolidx_code

        
        

        #slice onto this row with extra data droped
        dc_raw_ser = df2.loc[boolidx,np.invert(boolcol)].iloc[0].dropna().astype('float32').reset_index(drop=True)
        #=======================================================================
        # checks
        #=======================================================================
        if self.db_f:
            
            if not np.any(boolidx_code):
                raise IOError('failed to find acode \'%s\' in the rfda damage curves'%acode)
            
            if not len(df1.loc[boolidx_code, 'asector'].unique())==1:
                raise IOError('rfda curve lookup got multiple asectors (%s) for acode \'%s\''
                              %(df1.loc[boolidx_code, 'asector'].unique().tolist(), acode))
                       

            if not boolidx.sum()==1:
                raise IOError('expected 1 hit for nores')
            
            if not 'float' in dc_raw_ser.dtype.name:
                raise IOError
            
            #check we got he expected length
            if asector == 'nores':
                if acode[0] == 'S': #structural curves
                    exp_len = 24
                else:
                    exp_len = 30
            else:
                exp_len = 22
                
            if not len(dc_raw_ser) == exp_len:
                raise IOError('acode \'%s\' (asector %s) got unnexpected length of damage curve %i'
                              %(acode, asector,len(dc_raw_ser)))
            
            
        #=======================================================================
        # for this row, extract teh damage curve
        #=======================================================================

        
        boolidx_e = dc_raw_ser.index%2 == 0 #events
        depths = dc_raw_ser[boolidx_e].values
        dmgs = dc_raw_ser[~boolidx_e].round(2).values
        
        #zip into an array
        dd_ar = np.sort(np.array([depths, dmgs], dtype='float32'), axis=1)
        
#===============================================================================
#         depth_list = []
#         dmg_list = []
#         #loop through each entry and assemble by position
#         for indxr, entry in dc_raw_ser: #loop through each entry
# 
#             #===================================================================
#             # 'the syntax of these curves is very strange'
#             # #===================================================================
#             # # logic for non depth/damage entries
#             # #===================================================================
#             # if index <=1:                   continue #skip the first 2
#             # if not hp_basic.isnum(entry):   continue #skip non number
#             #===================================================================
# 
#             if indxr%2 == 0:    #evens
#                 depth_list.append(float(entry))
#             else:  #odds             
#                 dmg_list.append(float(entry))
#                 
#         
#         """ thsi even/odd index selectio may not work for non house type damage curves        
#         """
#===============================================================================

#===============================================================================
#         #=======================================================================
#         # Build array
#         #=======================================================================
#         
# 
#         
#         """ moved this to make parent reference more accessible
#         dd_ar[1] = dd_ar1[1] * self.parent.gis_area"""
#===============================================================================
        
        #=======================================================================
        # #post checks
        #=======================================================================
        if self.db_f:
            if not dd_ar.shape[0] == 2:
                'getting 3.208 at the end of the depth list somehow'
                raise IOError('got unexpected shape on damage array: %s'%str(dd_ar.shape))
        
        #=======================================================================
        # closeout============================================
        #self.dd_ar = dd_ar
        
        
        logger.debug('built damage array from rfda for acode \'%s\' and dmg_type \'%s\' as %s'
                          %(acode, dmg_type, str(dd_ar.shape)))

        return dd_ar
    
    def get_ddar_depdmg(self): #build the dd_ar from standard format depth damage tables
        logger = self.logger.getChild('get_ddar_depdmg')
        
        #=======================================================================
        # get your data from the session
        #=======================================================================
        df = self.model.dfunc_raw_d[self.name]
        
        dd_ar = np.sort(df.values, axis=1)
        
        logger.debug('build dd_ar from passed file for with %s'%(str(dd_ar.shape)))
        
        return dd_ar
        
        
    
    def get_ddar_dfeats(self): #build the dd_ar from the dmg_feats
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        build_dd_ar (for dfeats)
        recompile_ddar (called by handles)
        
        never directly called by handles
        #=======================================================================
        # OUTPUTS
        #=======================================================================
        dd_ar: depth/damage (total)
            NOTE: This is different then the dd_ar for rfda curves
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_ddar_dfeats')
        
        dd_df = self.childmeta_df #ge tthe dynamic depth damage frame 
        """
        dfeat.eval_price_calc_str() will make updates to this
        
        """
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not hp_pd.isdf(dd_df): 
                raise IOError
            
            if np.any(pd.isnull(dd_df['calc_price'])):
                logger.error('got %i null entries on teh dd_df'%pd.isnull(dd_df['calc_price']).sum())
                raise IOError

            #check the acode matches
            acode = self.get_acode()
            for k, v in self.kids_d.items():
                if not v.acode == acode:
                    raise IOError('dfeat \'%s\' acode \'%s\' does not match \'%s\''
                                 %(k, v.acode, acode))
                    
            #basement logic
            if self.dummy_f:
                raise IOError('Im unreal!')
            
            if not isinstance(self.dd_ar, np.ndarray):
                raise IOError('unexpected type on dd_ar')

            #=======================================================================
            # dependencies/frozen
            #=======================================================================
            'only using this as a check'
            #if not self.session.state == 'init':
            dep_p = [([self.parent], ['set_geo_dxcol']),\
                     (list(self.kids_d.values()), ['eval_price_calc_str', 'set_new_depth'])]#,\
            
                    #the dfeats que this'
                    #([self],['recompile_ddar()'])]
            
            if self.deps_is_dated(dep_p, caller = 'get_ddar_dfeats'):
                'this func is never called directly by the handles'
                raise IOError #because we are forcing this should alwys return FALSE
            
            #===================================================================
            # frame checks
            #===================================================================
            if dd_df['depth'].min() < 0: 
                raise IOError

        #=======================================================================
        # setup
        #=======================================================================
        logger.debug('compiling dd_ar from dd_df %s'%str(dd_df.shape))
        #get list of depths
        depth_list = dd_df['depth'].astype(np.float).sort_values().unique().tolist()
         
        #=======================================================================
        # calc dmg_list for these depths
        #=======================================================================
        dmg_list = []
        
        #loop through depths 
        for depth in depth_list:
            """shrotened
            #find all the depths less then this
            boolidx = dd_df['depth'] <= depth
            dd_df_slice = dd_df[boolidx] #get this slice
            
            #check this
            #if len(dd_df_slice) <1: raise IOError
            
            #calc the damage for this slice
            dmg = dd_df_slice['calc_price'].sum()"""
            
            dmg = dd_df.loc[dd_df['depth'] <= depth, 'calc_price'].sum()
            
            """these are calculated by each Dmg_feat.get_calc_price
             and entered into the dyn_dmg_df"""
             

            dmg_list.append(dmg)

        #=======================================================================
        # constrain the depths
        #=======================================================================
        """ moved this
        dd_ar = self.constrain_dd_ar(depth_list, dmg_list)"""
         
        #=======================================================================
        # closeout
        #=======================================================================
        
        dd_ar = np.sort(np.array([depth_list, dmg_list]), axis=1)
        
        """moved this to build_dd_ar() and recompile_dd_ar()
        self.handle_upd('dd_ar', dd_ar, proxy(self), call_func = 'get_ddar_dfeats')"""
        'this will add constrain_dd_ar to the queue, but generally this should remove itself shortly'
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not max(dd_ar[1]) == dd_df['calc_price'].sum():
                raise IOError('complied curve maximum (%.2f) != dyn_df total (%.2f)'
                              %(max(dd_ar[1]), dd_df['calc_price'].sum()))
                
        logger.debug('built dd_ar %s'%str(dd_ar.shape))
        
        return dd_ar


    def set_childmetadf(self): #get teh childmetadata for the dyn dmg_feats
        logger = self.logger.getChild('set_childmetadf')
        
        #=======================================================================
        # setup
        #=======================================================================
        #pull the data for this curve from globals
        dyn_dc_dato = self.model.kids_d['dfeat_tbl']
        
        #get the correct acode
        acode = self.get_acode()

        #check that its there
        if not acode in list(dyn_dc_dato.dfeat_df_d.keys()):
            """
            self.asector
            """
            raise IOError('my acode type (%s) isnt in teh dfeat_tbl'%acode)
        
        df_raw = dyn_dc_dato.dfeat_df_d[acode] #for just this house type
        
        logger.debug('got data from file for %s with %s'%(acode, str(df_raw.shape)))
        
        #=======================================================================
        # clean/set this
        #=======================================================================
        self.childmeta_df = df_raw[
            df_raw['place_code'] == self.place_code
            ].reset_index(drop=True).drop(columns = ['desc', 'unit'])
        
        #=======================================================================
        # attach base geometry
        #=======================================================================
        'todo: add check that all these are the same'

        #=======================================================================
        # close out/wrap up
        #=======================================================================
        """ not ready to store this yet... wait till teh children load and insert their initial values
        placed in build_dfunc() 
        self.reset_d['childmeta_df'] = self.childmeta_df.copy() #add this for reseting"""

        logger.debug('finisehd with %s'%str(self.childmeta_df.shape))      
        
        #=======================================================================
        # post checker
        #=======================================================================
        if self.db_f:
            if not 'calc_price' in self.childmeta_df.columns.tolist():
                raise IOError
    
        return 
    
    def raise_dfeats(self): #raise the dmg_feats children

        #=======================================================================
        # defautls
        #=======================================================================
        if self.db_f: start = time.time()
        logger = self.logger.getChild('raise_dfeats')
        id_str = self.get_id()
        acode = self.get_acode()

        
        """see below
        #=======================================================================
        # dependency check
        #======================================================================="""
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            
            if not self.dmg_code == 'S':    
                raise IOError('got unexpected dmg_code == %s'%self.dmg_code)

            if not self.dfunc_type == 'dfeats':
                raise IOError
            
            if hasattr(self, 'kids_sd'): 
                raise IOError
            
            if not self.session.state == 'init': 
                if not self.dummy_f:
                    if len(self.kids_d) == 0: 
                        logger.warning('%s.%s is raising dfeats outside of startup'%(self.parent.name, self.name))
                        """this could trip if we redevelop onto a dummy
                        raise IOError"""
                    
                    #get set of old kid gids for post checking
                    old_kgid_s = set()
                    for k, v in self.kids_d.items(): 
                        old_kgid_s.update([v.gid])
                        
                    #need to relase the last one from this space
                    try:del v 
                    except: pass
                    
                else:
                    if not len(self.kids_d) == 0:
                        raise IOError
                
                

                
        """
        'only bothering if we are outside of the update scan'
        state = self.session.state != 'update' #a boolean of whether the session is upating
        _ = self.depend_outdated(search_key_l = ['set_geo_dxcol()'], #see if the parent has these
                             force_upd = state, #force the parent to update if found
                             halt = False) #clear all of my updates (except this func)"""
                             
        #=======================================================================
        # shortcut for dummies
        #=======================================================================
        if self.dummy_f:
            self.kids_d =  wdict()#empty placeholder
            #need to store these empty kids for reseting
            if self.session.state == 'init' and self.session.dyn_vuln_f:

                """we use these shadow kids to reset our children at the start of a simulation
                        see reset_dfunc()"""
                
                self.shdw_kids_d = dict() #set an empty container (needs to be rea)
                self.reset_func_od[self.reset_dfunc]='Dfunc' #que the updater func
                logger.debug('set an empty container for teh shadow kids on this dummy dfunc')
                
            else:
                logger.debug('dummy.. skipping')
                
            return
            
        #=======================================================================
        # dynamic vuln. mid simulation changes
        #=======================================================================
        if not self.session.state == 'init': 
            
            #=======================================================================
            # dependecy check
            #=======================================================================
            dep_p = [([self.parent],['set_geo_dxcol'] )] #dependency paring
            if self.deps_is_dated(dep_p, method = 'force', caller = 'raise_dfeats'):
                raise IOError #because we are forcing this should alwys return FALSE

            #===================================================================
            # clear out old kids
            #===================================================================
            logger.debug('at \'%s\' session.state != init. killing kids \n'%id_str)
            
            self.kill_kids() # run kill() on all your children
            
            #add this reseting function
            """just adding this to everyone
            self.reset_func_od[self.reset_dfunc]='Dfunc'"""
            self.reset_shdw_kids_f = True #???
        

            
        #=======================================================================
        # post kill checks
        #=======================================================================
        if self.db_f:
            if not self.session.state == 'init': 
                if len(self.kids_d) > 0:
                    gc.collect()
                    if len(self.kids_d) > 0:
                        '1 child seems to hang'
                        logger.warning('sill have %i children left: %s'%(len(self.kids_d), list(self.kids_d.keys())))
                        raise IOError

                if not self.session.dyn_vuln_f: 
                    raise IOError
                
                if not isinstance(self.shdw_kids_d, dict): 
                    raise IOError('%s.%s doesnt have any shadow kids')
        

        #=======================================================================
        # set the childmeta data
        #=======================================================================
        logger.debug('at \'%s\' running set_childmetadf \n'%id_str)
        self.set_childmetadf()
        'this container is always needed for holding all the meta data and curve building'
            

        #=======================================================================
        # Initilize.CLONE
        #=======================================================================
        if self.tag in self.model.dfeats_d.keys(): #see if a clone of myself has been spawned yuet
            logger.debug("found my dfeats \'%s\' in the preloads. pulling them from there"%self.tag)
            dfeat_d_mstr = self.model.dfeats_d[self.tag] #get the base dfeats
            """
            for k, v in d_pull.items():
                print(k, v)
            """
            #make a copy of these guys for yourself
            dfeat_d = hp_oop.deepcopy_objs(dfeat_d_mstr, container = dict, 
                                           db_f = self.db_f, logger=logger) 
            
            #===================================================================
            # #birth the clones
            #===================================================================
            logger.debug('initilizing %i dfeat clones: %s'%(len(dfeat_d), list(dfeat_d.keys())))
            for dname, dfeat in dfeat_d.items():                 
                dfeat.init_clone(self) #add this to the family (as your child)
                dfeat.inherit_logr(parent = self) #setup the logger


            #post birth checks
            if self.db_f:
                for dname, dfeat in dfeat_d.items():
                    if not dfeat.model == self.model:
                        raise IOError('model mismatch on dfeat against myself')
                    
                    if not dfeat.model == self.parent.model:
                        raise IOError('model mismatch with my parent')

            """ init_clone does this   
            self.kids_d = wdict(d)"""
            
        #=======================================================================
        # INIT. UNIQUE. spawn your own
        #=======================================================================
        else:
            df =  self.childmeta_df
            logger.debug('raising children from df %s\n'%str(df.shape))
            #=======================================================================
            # load the children
            #=======================================================================
            'probably a better way to deal witht hese falgs'
            dfeat_d = self.raise_children_df(df, 
                                       kid_class = self.kid_class,
                                       dup_sibs_f = True) #adding the kwarg speeds it up a bit
        
            
        #=======================================================================
        # Activate the dfeats
        #=======================================================================
        logger.debug("birth_dfeat on %i dfeats \n"%len(dfeat_d))
        for dfeat in dfeat_d.values():
            dfeat.birth_dfeat(self) #tell the dfeat your're the parent and inherit
        #=======================================================================
        # reset handling
        #=======================================================================
        
        #save teh recompile state
        if self.session.state == 'init':
            if self.session.dyn_vuln_f:
                
                #add the shadow kids and their handler
                logger.debug('deep copying over to shdw_kids_d')
                self.shdw_kids_d = hp_oop.deepcopy_objs(dfeat_d, container = dict, logger=logger)
                
                """we use these shadow kids to reset our children at the start of a simulation
                        see reset_dfunc()
                        
                    CAN NOT be a wdict because this is the only place they live"""
                
                self.reset_func_od[self.reset_dfunc]='Dfunc'

        else:
            pass
            """never called directly by the handler"""

        #=======================================================================
        # post checking
        #=======================================================================
        if self.db_f:
            if len(dfeat_d) > 0:
                self.check_family(dfeat_d)
                
            if not len(dfeat_d) == len(self.kids_d):
                raise IOError
            

            if not self.session.state == 'init': 
                #make sure all the old kids are dead
                book = self.session.family_d['Dmg_feat'] #get the book containing all these
                for gid in old_kgid_s:
                    if gid in list(book.keys()): 
                        raise IOError
                    
            #check the childmeta_df
            if np.any(pd.isnull(self.childmeta_df)):
                raise IOError
            
            """not ready
            self.check_dfunc()"""
            
            stop = time.time()
            logger.debug('in %.4f secs finished on %i Dmg_feats: %s \n'
                         %(stop - start, len(dfeat_d), list(dfeat_d.keys())))
        else:
            logger.debug('finished on %i Dmg_feats: %s \n'%(len(dfeat_d), list(dfeat_d.keys())))
            
        return


    
    def set_dfunc_anchor(self): #calculate my anchor_el from place code
        """
        This is a special type of geometry that needs to be determined regardles of whether the curves are dynanmic
        therefore kept seperate from teh geo calcs
        """       
        logger = self.logger.getChild('set_dfunc_anchor')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not isinstance(self.parent.geo_dxcol, pd.DataFrame): 
                raise IOError
            if not len(self.parent.geo_dxcol) > 0: 
                raise IOError
            if self.place_code == 'total': 
                raise IOError
            
        
            
        #=======================================================================
        # dependencies and frozen
        #=========================================================== ============
        if not self.session.state=='init':

            if self.is_frozen('anchor_el', logger = logger): 
                return True
            
            dep_l =  [([self.parent], ['set_hse_anchor', 'set_geo_dxcol'])]
            
            if self.deps_is_dated(dep_l, method = 'reque', caller = 'set_dfunc_anchor'):
                return False

        
        #=======================================================================
        # shortcut assignments
        #=======================================================================
        pa_el   = self.parent.anchor_el


        #=======================================================================
        # #unreal basements shortcut
        #=======================================================================
        if self.dummy_f:
            self.anchor_ht = np.nan 
            return True #dont bother with handles?
            #anchor_el = np.nan 
                
        #=======================================================================
        # #use legacy anchor heights
        #=======================================================================
        elif self.anchor_ht_code == '*rfda_pars': 
            ' we could exclude this from updates as it shouldnt change'
            if self.place_code == 'B': 
                try: 
                    rfda_anch_ht = self.model.fdmgo_d['rfda_pars'].floor_ht #use the floor height from the par file
            
                except:
                    raise Error('failed to load rfda_pars')


                anchor_el = pa_el - rfda_anch_ht #basement curve
                'rfda_anch_ht is defined positive down'
                
            #main floor
            elif self.place_code == 'M':  
                anchor_el = pa_el #main floor, curve datum = house datum

            #garage
            elif self.place_code == 'G': 
                anchor_el = pa_el -.6 #use default for garage
                'the garage anchor was hard coded into the rfda curves'
                            
            else: raise IOError

        #=======================================================================
        # #pull elevations from parent
        #=======================================================================
        elif self.anchor_ht_code == '*hse': 

            #real basements
            if self.place_code == 'B':
                jh = self.parent.joist_space
                
                B_f_height = float(self.parent.geo_dxcol.loc['height',('B','f')]) #pull from frame
                
                anchor_el = pa_el - B_f_height - jh#basement curve
                logger.debug('binv.B got B_f_height = %.4f, jh = %.4f'%(B_f_height, jh))
            #main floor
            elif self.place_code == 'M': 
                anchor_el = self.parent.anchor_el #main floor, curve datum = house datum
            
            #Garage
            elif self.place_code == 'G': 
                anchor_el = pa_el + self.parent.G_anchor_ht #use default for garage
                'parents anchor heights are defined positive up'
            
            else: raise IOError
            
        #=======================================================================
        # straight from dem
        #=======================================================================
        elif self.anchor_ht_code =='*dem':
            anchor_el = self.parent.dem_el
        
        #=======================================================================
        # striaght from parent
        #=======================================================================
        elif self.anchor_ht_code == '*parent':
            anchor_el = self.parent.anchor_el 
            
        else: 
            raise IOError
            

        #=======================================================================
        # wrap up
        #=======================================================================
        logger.debug('for anchor_ht_code: \'%s\' and place_code \'%s\' found %.4f'
                     %(self.anchor_ht_code, self.place_code, anchor_el))
        
        #updates
        self.handle_upd('anchor_el', anchor_el, proxy(self), call_func = 'set_dfunc_anchor')
        self.anchor_ht = anchor_el - pa_el
        
        
        """done by teh handler
        #update the dd_ar
        'this needs to happen after the anchor_el update has been set'
        #logger.debug('running constrain_dd_ar \n')
        self.constrain_dd_ar()"""
        
        return True
    
    def constrain_dd_ar(self, #adjust the depth damage arrays to fit within the anchor
                        tol = 0.01): 
        """
        TODO: switch to sets
        """

        logger = self.logger.getChild('constrain_dd_ar')


        #=======================================================================
        # dependency checks
        #=======================================================================
        if not self.session.state == 'init':
            dep_p = [([self.parent], ['set_geo_dxcol', 'set_hse_anchor']),\
                     ([self], ['set_dfunc_anchor', 'build_dd_ar', 'recompile_ddar']),\
                     (list(self.kids_d.values()), ['set_new_depth'])]#,\

            
            if self.deps_is_dated(dep_p, caller='constrain_dd_ar'):
                return False

            
        #=======================================================================
        # shortcuts
        #=======================================================================
        if self.dummy_f:
            self.handle_upd('dd_ar', self.dd_ar, proxy(self), call_func = 'constrain_dd_ar')
            
            if self.db_f:
                if self.hse_o.bsmt_f:
                    raise IOError('expected the parent not to have a basement')
            
            return True
            
        #=======================================================================
        # defaults
        #=======================================================================
        depth_list  = self.dd_ar[0].tolist()
        dmg_list    = self.dd_ar[1].tolist()
        
        max_d = max(depth_list)
        #logger.debug('with place_code = \'%s\' and max_d = %.2f'%(self.place_code, max_d))
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if self.anchor_el is None: 
                raise IOError
            if min(depth_list) < 0: 
                raise IOError
            if min(dmg_list) < 0: 
                raise IOError
            
            old_max_dmg = max(dmg_list) #set for post check
            
        #=======================================================================
        # get the expected height
        #=======================================================================
        
        if self.place_code == 'B':#for basements
            height = self.parent.anchor_el - self.anchor_el
            'this allows for multiple anchor_ht_code methods. means the set_anchor has to be updated'
        else: #for mainfloor and garges
            height = self.parent.geo_dxcol.loc['height',(self.place_code,'t')]
            
        
        logger.debug('for place_code = \'%s\' got height = %.2f'%(self.place_code, height))
        
        if self.db_f:
            if not height > 1: 
                raise IOError('got non-positive height = %.2f'%height)
            
        #=======================================================================
        # collapse based on relative
        #=======================================================================
        #too short. raise it up. add a dummy value up
        if max_d <= height - tol: #check if the curve extents to teh ceiling
            depth_list.append(height) 
            dmg_list.append(max(dmg_list)) #add a max value
            
            logger.debug('dd_ar too short (%.2f). added dummy entry for height= %.2f'%(max_d, height))
            
        #too high. collapse. change the last height depth value to match the height
        elif max_d > height+tol:
            dar = np.array(depth_list) 
            boolind =   dar > height #identify all of th evalues greater than the height
            
            dar[boolind] = height #set all these to the height
            
            depth_list = dar.tolist() #convert back to  list
            
            logger.debug('max(depth %.4f)> height (%.4f) collapsing %i'
                           %(max_d, height, boolind.sum()))
            
        else:
            logger.debug('dd_ar (%.2f) within tolerance (%.2f) of height (%.2f). no mods made'%(max_d, tol, height))

            
        if not min(depth_list) == 0: #add a zero here
            """why is this needed?"""
            depth_list.append(0.0)
            dmg_list.append(0.0)
            logger.debug('added zero entry')
            
        #bundle this        
        dd_ar = np.sort(np.array([depth_list, dmg_list]), axis=1)

        #=======================================================================
        # wrap up
        #=======================================================================
        #update handling
        """
        ive just locked this... dont need to send to the update handler
        actually... we want the upd_cmd to be cleared of this function
        """
        logger.debug('finished with dd_ar[0]: %s \n'%dd_ar[0].tolist())
               
        self.handle_upd('dd_ar', dd_ar, proxy(self), call_func = 'constrain_dd_ar')
        'this shouldnt que any updates. removes yourself from the que'
        
        """mvoed to post updating
        self.calc_statres_dfunc()"""
        
        if self.db_f:
            if not min(self.dd_ar[0].tolist()) == 0:
                raise IOError
            
            if not max(self.dd_ar[1]) == old_max_dmg:
                raise IOError('maximum damages changed!')
        

        return True
    
    def recompile_ddar(self,  #update the dd_ar (for small changes to dfeats)
                        #childn_l = None, 
                        outpath = None): 
        
        """
        this loops through each dmg_feat, and updates the dyn_dmg_df with price and depth
        then we recompile the depth damage array
        
        to improve efficiency, when were only changing a few dmg_feats, 
            pass a subset of child names
            
        
        Why not just call build_dfunc??
            This kills all the dfeat children
        
        #=======================================================================
        # CALLS
        #=======================================================================
        this should be called by the dynp handles for any changes to:
            house.geometry (geo_dxcol)
            Dmg_feat price/depth
        """
        #=======================================================================
        # shortcuts
        #=======================================================================
        logger = self.logger.getChild('recompile_ddar')
        'this gets called by teh dyno handles regardles of the dfunc type'
        if self.dfunc_type == 'dfeats': 
            #=======================================================================
            # check dependneciies
            #=======================================================================
            #dependency pairing
            dep_p = [([self.parent], ['set_geo_dxcol']), #house has updated the geometry
                     (list(self.kids_d.values()), ['eval_price_calc_str', 'set_new_depth'])] #dfeats have updated
            
            if self.deps_is_dated(dep_p, caller='recompile_ddar'):
                return False
        
            #=======================================================================
            # prechecks
            #=======================================================================
            if self.db_f:
                cn = self.__class__.__name__
                if self.session.state == 'init': 
                    raise IOError

                #make sure my custom reseter function is loaded
                if not self.reset_dfunc in self.reset_func_od: 
                    raise IOError('%s resetter function has not been qued'%cn)
                
                if self.dd_ar is None:
                    raise IOError
                
                
                #check your kids
                for name, dfeat in self.kids_d.items():
                    """this is done below
                    dfeat.check_dfeat()"""
                    
                    """do we use the upd_cmd_od on dfeats?"""
                    if 'eval_price_calc_str' in list(dfeat.upd_cmd_od.keys()): 
                        raise IOError
                    
                self.check_dfunc()

            #=======================================================================
            # rebuild the depth damage array
            #=======================================================================
            id_str = self.get_id()
            logger.debug('at %s get_ddar_dfeats() \n'%id_str)
            
            if self.dummy_f: #for unreal baseemnts
                logger.debug('unreal. skipping')
            else:
                self.dd_ar = self.get_ddar_dfeats() #recomplie the full curve
            'constrain sets a new copy'
                   

            #clear myself from the update que
            'need to remove this here so that contrain_dd_ars dependencies arent tripped'
            self.del_upd_cmd(cmd_str = 'recompile_ddar')
            
            #constrain this
            res = self.constrain_dd_ar()
            
            """letting constrain_dd_ar deal with the handles
            #===================================================================
            # updates
            #===================================================================
            self.handle_upd('dd_ar', dd_ar, proxy(self), call_func = 'recompile_ddar')"""
        
            #=======================================================================
            # wrap up
            #=======================================================================
            """ this should only be run by upd_cmd (which executes del_upd_cmd
            'not using the update handler so we need to do the delete manually'
            self.del_upd_cmd() """
            
            self.reset_shdw_kids_f = True #flag the children for reseting
            'because we dont reset our children, this just swaps them all out for the shadow set'
            'todo: only swap changed ones?'
        
        else:
            logger.debug('dfunc_type \'%s\' does not recomplie... skipping'%self.dfunc_type)
        #=======================================================================
        # post checks
        #=======================================================================

        if self.db_f:
            'this shouldnt be called during __init__. see raise_chidlren()'
            
            #check unreal basements
            if self.dummy_f:
                if not len(self.dd_ar) == 0:
                    raise IOError
            else:
                if not isinstance(self.dd_ar, np.ndarray):
                    raise IOError('unepxected type on dd_ar')
            
            #=======================================================================
            # writiing
            #=======================================================================
            if not outpath is None:
                if outpath == True:
                    filename = os.path.join(self.outpath, 'dd_df.csv')
                else:
                    filename = outpath
                    
                hp_pd.write_to_file(filename, self.dd_df, logger=logger)
        
        return True
    

    def run_dfunc(self, *vars, **kwargs):
        self.run_cnt += 1
        
        if self.db_f:
            
            #===================================================================
            # checks
            #===================================================================
            logger = self.logger.getChild('run_dfunc')
            
            """no.. call this on the house
            self.check_dfunc()"""

                
            if len(self.upd_cmd_od) > 0:
                raise IOError

            logger.debug('for %s returning get_dmg_wsl'%self.get_id())
            

        return self.get_dmg_wsl(*vars, **kwargs)
    
    def get_dmg_wsl(self, wsl): #main damage call. get the damage from the wsl
        #logger = self.logger.getChild('get_dmg_wsl')
                    
        #convert this wsl to depth
        if self.dummy_f: #unreal basem,ents
            depth    = np.nan
        else:
            depth    = self.get_depth(wsl) 
        
        #get damage (scaled and unscaled) for this depth
        if depth < 0 or np.isnan(depth): 
            dmg, dmg_raw = 0.0, 0.0
        else:           
            dmg, dmg_raw = self.get_dmg(depth)

        #=======================================================================
        # reporting
        #=======================================================================
        #=======================================================================
        # msg = 'depth = %.2f (%s) fdmg = %.2f (%s)'%(depth, condition_dep, dmg, condition_dmg)        
        # logger.debug(msg)
        #=======================================================================
        
        return depth, dmg, dmg_raw
    
    def get_depth(self, wsl):
        """
        This converts wsl to depth based on teh wsl and the bsmt_egrd
        this modified depth is sent to self.get_dmg_depth for interpolation from teh data array

        """       
        logger = self.logger.getChild('get_depth')
        depth_raw = wsl - self.anchor_el #get relative water level (depth)
        
        #=======================================================================
        # #sanity check
        #=======================================================================
        if self.db_f:
            if depth_raw > self.depth_allow_max:
                logger.error('\n got depth_raw (%.2f) > depth_allow_max (%.2f) for state: %s '
                             %(depth_raw, self.depth_allow_max, self.model.state))
                
                #get your height
                df      = self.hse_o.geo_dxcol[self.place_code] #make a slice for just this place
                height  = df.loc['height', 'f'] #        standing height
        

                logger.error('\n with anchor_el: %.2f wsl: %.2f, place_code: \'%s\' and height = %.2f'%
                             (self.anchor_el, wsl, self.place_code, height))
                
                raise IOError
            

        #=======================================================================
        # short cuts
        #=======================================================================
            
        if depth_raw < 0: #shortcut for water is too low to generate damage
            logger.debug('wsl (%.2f) < anchor_El (%.2f).skipping'%(wsl, self.anchor_el))
            return depth_raw
        
        #=======================================================================
        # set depth by floor
        #=======================================================================       
        if not self.dmg_type.startswith('B'): 
            depth = depth_raw
            condition = 'non-basement'
            
        else:  #basement
            #check if the flood depth is above the main floor
            if wsl > self.parent.anchor_el: 
                depth = depth_raw
                condition = 'high wsl'
                
            else: #apply the exposure grade
                if self.parent.bsmt_egrd == 'wet':
                    depth = depth_raw
                    condition = 'bsmt_egrd = WET'
                    
                elif self.parent.bsmt_egrd == 'damp':
                    
                    if self.model.damp_func_code == 'spill':
                        if depth_raw < self.parent.damp_spill_ht:
                            depth = 0
                            condition = 'bsmt_egrd = DAMP. spill. DRY. damp_spill_ht = %.2f'%self.parent.damp_spill_ht
                        else:
                            depth = depth_raw
                            condition = 'bsmt_egrd = DAMP. spill. WET damp_spill_ht = %.2f'%self.parent.damp_spill_ht
                        
                    elif self.model.damp_func_code == 'seep':
                        depth = depth_raw*0.5 #take half
                        condition = 'bsmt_egrd = DAMP. seep'
                        
                    else: raise IOError

                elif self.parent.bsmt_egrd == 'dry':
                    if depth_raw > self.parent.bsmt_opn_ht:
                        depth = depth_raw
                        condition = 'bsmt_egrd = DRY. above bsmt_opn_ht = %.2f'%self.parent.bsmt_opn_ht
                    else:
                        depth = 0
                        condition = 'bsmt_egrd = DRY. below bsmt_opn_ht = %.2f'%self.parent.bsmt_opn_ht
                    
                else:
                    logger.error('got unexpected code for bsmt_egrd = %s'%self.parent.bsmt_egrd )
                    raise IOError
                
                
        logger.debug('found depth = %.4f with \'%s\' from anchor_el = %.4f'%(depth, condition, self.anchor_el))
                
        return depth
                
    def get_dmg(self, depth): #basic depth from fdmg
        """
        for depth manipulations, see 'self.get_dmg_wsl'
        this dd_ar should be precompiled (based on dfunc_type) by one of the compiler functions
        """
        logger = self.logger.getChild('get_dmg')
        
        depth_list = self.dd_ar[0] #first row
        dmg_list = self.dd_ar[1]
        
        if self.db_f:
            if not min(depth_list)==0:
                logger.error('min(depth_list) (%.4f)!=0'%min(depth_list))
                'constrain_dd_ar should have been run to fix this'
                raise IOError
            
            
        
        #check for depth outside bounds
        if depth < min(depth_list):
            dmg_raw = 0 #below curve
            condition = 'below'
            
        elif depth > max(depth_list):
            dmg_raw = max(dmg_list) #above curve
            condition = 'above'
        else:
            dmg_raw = np.interp(depth, depth_list, dmg_list)
            condition = 'interp'
            
        #=======================================================================
        # scale with ratios
        #=======================================================================
        if not self.rat_attn =='*none':
            scale = eval(self.rat_attn)
        else:
            scale = 1.0
            
        dmg= dmg_raw * scale
            
        logger.debug('for \'%s\' type dmg = %.4f with \'%s\' from dd_ar %s min(%.4f) max(%.4f) scale(%.2f)'
                     %(self.dfunc_type, dmg, condition, str(self.dd_ar.shape),  min(depth_list),  max(depth_list), scale))
        
        return dmg, dmg_raw
    
    def reset_dfunc(self, *vars, **kwargs): #reset routine
        """
        keeping this command inthe func_od to make it easier for children to flag for a reset
        del self.reset_func_od['reset_dfunc']
        """
        logger = self.logger.getChild('reset_dfunc(%s)'%self.get_id())
        
        #=======================================================================
        # precheck
        #=======================================================================
        """if self.db_f:
            should have already been reset
            old_max_dmg = max(self.dd_ar[1])"""
        
        #=======================================================================
        # reset your kids
        #=======================================================================
        if self.reset_shdw_kids_f:
            
            logger.debug('reset_shdw_kids_f=TRUE. swapping kids \n')
            #===================================================================
            # precheck
            #===================================================================
            if self.db_f:
                if not isinstance(self.shdw_kids_d, dict):
                    raise IOError
            
                #check kid container length
                if len(self.kids_d) == 0 or len(self.shdw_kids_d) == 0: 
                    logger.debug('empty kids_d!') 
                    if not self.dummy_f:
                        """this dummy_f should have been reset to the original state
                        so for mid-session dummy flagging, this would trip
                        but I dont think were allowign that yet"""
                        raise IOError('%s.%s has no kids and is real'%(self.parent.name, self.name))
                
                #store this generations names for post checking
                gen1_gid_l = list(self.kids_d.keys())
                
            #===================================================================
            # shortcuts
            #===================================================================
            
                
                
            #===================================================================
            # kid swapping
            #===================================================================
            if len(self.shdw_kids_d) == 0:
                #just set an empty container
                self.kids_d = wdict()
            else:
                #swaps kids_d with shdw_kids_d
                self.swap_kids(self.shdw_kids_d)

            self.reset_shdw_kids_f = False #turn teh flag off
            
            #===================================================================
            # post check
            #===================================================================
            if self.db_f:
                if not isinstance(self.kids_d, wdict): 
                    raise IOError
                if not len(self.kids_d) == len(self.shdw_kids_d): 
                    raise IOError
                
                #check that the old kid is not in teh family_d
                for gid in gen1_gid_l:
                    if gid in list(self.session.family_d['Dmg_feat'].keys()):
                        raise IOError
                    
        else: #simulation never made changes to the kids.. no need to reset
            pass
            #logger.warning("reset_shdw_kids_f=FALSE")
            
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            self.check_dfunc()
            if not self.dummy_f:
                self.check_family()
                

                

        return 
    
    def calc_statres_dfunc(self): #clacluated a statistic for the dd_ar
        #logger = self.logger.getChild('calc_statres_dfunc')
        s = self.session.outpars_d[self.__class__.__name__]
        #=======================================================================
        # BS_ints
        #=======================================================================
        if 'intg_stat' in s: 
            res = self.calc_intg_stat()
            
        if 'kid_cnt' in s:
            self.kid_cnt = len(self.kids_d)
            

        
        """ using handler
        self.parent.BS_ints = intg_stat
        just setting this directly for now as we're only doing this on one child
        #=======================================================================
        # updates
        #=======================================================================
        
        self.parent.que_upd_skinny('calc_statres_hse()', 'intg_stat', proxy(self), 'calc_statres_dfunc')"""
        
        return True
    
    def calc_intg_stat(self, dx = 0.001):
        #=======================================================================
        # shortcuts
        #=======================================================================
        if not self.name == 'BS': 
            return False#only care about the basement
        if self.dummy_f:
            return False 
        
        logger = self.logger.getChild('calc_intg_stat')
        
        depth_list  = self.dd_ar[0].tolist()
        dmg_list    = self.dd_ar[1].tolist()
            
        intg_stat = scipy.integrate.trapz(dmg_list, depth_list, dx = dx)
        
        logger.debug('got intg_state = %.4f'%intg_stat)
        
        self.intg_stat = intg_stat
            
        return True
    
    def get_acode(self):    #quick acode getter
    
        if self.dmg_code == 'S':
            return self.hse_o.acode_s
        elif self.dmg_code == 'C':
            return self.hse_o.acode_c
        elif self.hse_o.acode_c == 'none' or self.hse_o.acode_s == 'none':
            return 'none'
        else:
            raise IOError('unrecognized damage code \'%s\''%self.dmg_code)
        
    def get_tag(self):
        return self.get_acode() + self.place_code + self.dmg_code
    
    def set_dummyf(self): #set your dummy status
        
        if np.any(np.array([
            self.get_acode() == 'none',
            self.place_code == 'B' and not self.hse_o.bsmt_f
            ])):
            self.dummy_f = True

        else:
            self.dummy_f = False
            
        #=======================================================================
        # save in the reset_d
        #=======================================================================
        if self.session.state=='init':
            self.reset_d['dummy_f'] = self.dummy_f
            
        return
                
#===============================================================================
#     def plot_dd_ar(self, #plot the depth damage array
#                    datum = None, ax=None, wtf=None, title=None, annot=None, **kwargs):
#         
#         #=======================================================================
#         # defaults
#         #=======================================================================
#         logger = self.logger.getChild('plot_dd_ar')
#         if wtf == None: wtf = self.session._write_figs
#         if title is None: title = self.parent.name +' ' + self.name + ' depth-damage plot'
#         
#         #=======================================================================
#         # depth data setup 
#         #=======================================================================
#         
#         #plot formatting
#         depth_dato = copy.copy(self) #start with a copy of self
#         
#         
#         #data transforms
#         if datum is None:  #plot raw values
#             delta = 0.0
#             depth_dato.units = 'depth raw(m)'
#             
#         elif datum == 'real': #plot relative to elevation/anchor
#             delta = self.anchor_el
#             depth_dato.units = 'elevation (m)'
# 
#         elif datum == 'house': #plot relative to the house anchor
#             delta = self.anchor_el - self.parent.anchor_el
#             depth_dato.units = 'depth (m)'
#             
#         depth_ar = self.dd_ar[0] + delta
#         depth_dato.label = depth_dato.units
#         
#         logger.debug('added %.2f to all depth values for datum: \'%s\''%(delta, datum))
# 
#         #=======================================================================
#         # damage data setup 
#         #=======================================================================
#         dmg_ar = self.dd_ar[1] 
#         
#         #scale up for rfda
#         if self.dfunc_type == 'rfda': dmg_ar= dmg_ar * self.parent.gis_area
#         
#         #annotation
#         if not annot is None:
#             if annot == True:
#                 annot = 'acode = %s\n'%self.acode +\
#                                 'dfunc_type: %s\n'%self.dfunc_type
#                 
#                 raise IOError
#                 'this may be broken'
#                 if hasattr(self, 'f_area'):
#                                 annot = annot +\
#                                 'f_area = %.2f m2\n'%self.f_area +\
#                                 'f_per = %.2f m\n'%self.f_per +\
#                                 'f_inta = %.2f m2\n'%self.f_inta +\
#                                 'base_area = %.2f m2\n'%self.base_area +\
#                                 'base_per = %.2f m\n'%self.base_per +\
#                                 'base_inta = %.2f m2\n'%self.base_inta 
#                 else:
#                     annot = annot +\
#                     'gis_area = %.2f m2\n'%self.parent.gis_area
# 
#         #=======================================================================
#         # send for  plotting
#         #=======================================================================
#         """
#         dep_dato: dependent data object (generally y)
#         indp_dato: indepdent data object (generally x)
#         flip: flag to indicate whether to apply plot formatters from the y or the x name list 
#         """
#         ax = self.model.plot(self, indp_dato = depth_dato, dep_ar = dmg_ar, indp_ar = depth_ar,
#                        annot = annot, flip = True, 
#                        ax=ax, wtf=False, title=title, **kwargs)
#         
#         #=======================================================================
#         # post formatting
#         #=======================================================================
#         #add thousands comma
#         ax.get_xaxis().set_major_formatter(
#             matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
#         
#             
#         #=======================================================================
#         # wrap up
#         #=======================================================================
#         if wtf: 
#             fig = ax.figure
#             flag = hp.plot.save_fig(self, fig, dpi = self.dpi)
#             if not flag: raise IOError 
#                             
#         
#         logger.debug('finished as %s'%title)
#         
#         return ax
#         
#===============================================================================
    def write_dd_ar(self, filepath = None): #save teh dd_ar to file
        logger = self.logger.getChild('write_dd_ar')
        
        if filepath is None: 
            filename = self.parent.name + ' ' + self.name +'dd_ar.csv'
            filepath = os.path.join(self.outpath, filename)
        
        np.savetxt(filepath, self.dd_ar, delimiter = ',')
        
        logger.info('saved dd_ar to %s'%filepath)
        
        return filepath
   