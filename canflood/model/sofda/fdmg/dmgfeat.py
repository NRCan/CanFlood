'''
Created on May 12, 2019

@author: cef
'''

#===============================================================================
# IMPORT STANDARD MODS -------------------------------------------------------
#===============================================================================
import logging
#, os,  time, re, math, copy, gc, weakref, random


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

#import model.sofda.hp.basic as hp_basic
#import model.sofda.hp.pd as hp_pd
import model.sofda.hp.oop as hp_oop

import model.sofda.hp.dyno as hp_dyno
import model.sofda.hp.sim as hp_sim


# logger setup -----------------------------------------------------------------------
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')


class Dmg_feat( #single damage feature of a complex damage function
                hp_dyno.Dyno_wrap,
                hp_sim.Sim_o,  
                hp_oop.Child):

    #===========================================================================
    # program pars
    #===========================================================================
    # object handling overrides
    """
    raise_kids_f        = True
    db_f                = False
    post_cmd_str_l      = ['build_dfeat']"""
    """not worth it
    spc_inherit_ans     = set(['hse_o', 'place_code'])""" 
    
    """
    # dynp overrides
    run_upd_f = False #teh parent uses a complied damage function during run.""" 
    
    
    # Simulation object overrides
    perm_f              = False #not a permanent object
    
    """
    #===========================================================================
    # OBJECT PERMANENCE (shadow handling)
    #===========================================================================
    because we are temporary, we need a way to reset after each sim (if modified)
    this must completely replace our parents old kids with the new kids
    
    create a deepcopy of the original kids_d during _init_
    integrate shadow_kids into all simulation containers
        update all selections
    
    
    #===========================================================================
    # replacement flagging
    #===========================================================================
    all dynp changes should trigger self.flag_parent_shdw_kids()
    this notifes the parent to reset ALL children
        todo: consider using a container instead, and only replacing select children
        
    #===========================================================================
    # replacement handling
    #===========================================================================
    during Dfunc.reset_simo() (custom version) the old kids are relaced with the shadow
    
    #===========================================================================
    # container updating
    #===========================================================================
    Parent.kids_d and kids_sd: 
        generic_inherit()
    
    Selectors update at given intervals
        todo: add check on interval logic with perm_f=False
        
    Outputrs
    
    Dynp

    """

    #===========================================================================
    #user provided pars
    #===========================================================================
    acode = '' #do I need this?
    place_code = None
    dmg_code = None
    cat_code = None
    base_area = None
    base_per = None
    base_height = None
    base_inta = None
    raw_index = None
    depth_dflt = None
    desc = None
    quantity = None
    unit = None
    unit_price = None
    base_price = None
    price_calc_str = None
    
    tag = None 
    #===========================================================================
    # calculated pars
    #===========================================================================
    #geometry placeholders
    'use geometry directly from parent'
    
    calc_price = None
    hse_o = None

    #===========================================================================
    # data containers
    #===========================================================================
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dmg_feat')
        logger.debug('start _init_')
        self.inherit_parent_ans=set(['mind', 'model'])
        
        super(Dmg_feat, self).__init__(*vars, **kwargs) #initilzie teh baseclass  
        

        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not isinstance(self.gid, str):
                raise IOError
            
            if self.place_code is None:
                raise IOError
        
        #=======================================================================
        # setup funcs
        #=======================================================================
        """ 
        dont want to activate this until the dfeat is on its proper parent
        NO. need this separate
        just bringing this all back
        logger.debug('build_dfeat \n')
        self.build_dfeat() """
        
        """ needs to be unique
        if self.sib_cnt == 0:
            logger.debug('getting dyno kids \n')"""
            
        'as we are non-permanent, this doesnt really do much'
        self.init_dyno()
                
        if self.db_f:
            logger.debug('check_dynh \n')
            self.check_dynh()
            
        logger.debug('initilized as \'%s\''%self.name)

        return
    
    def check_dfeat(self): #standard checking fcommands
        
        if not self.mind == self.model.mind: 
            raise IOError
        
        #=======================================================================
        # check hierarchy
        #=======================================================================
        if self.parent is None: 
            raise IOError

        if not self.hse_o == self.parent.parent: 
            raise IOError
        
        #check acode
        if 'run' in self.session.state:
            hp_oop.check_match(self, self.hse_o, attn='acode')
            
            if not self.acode == self.parent.get_acode():
                raise Error('acode mismiatch with parent')
        

        gp = self.parent.parent
        if not self.model == gp.model: 
            raise Error('\"%s\' model (%s) \n does not match their grandparents \'%s\' (%s)'
                          %(self.name, self.model, gp.name,gp.model ))
        
        if self.hse_o.geo_dxcol is None:
            raise IOError
        
        if not self.parent.__class__.__name__ == 'Dfunc':
            raise IOError
        
        #=======================================================================
        # check meta_df
        #=======================================================================
        
        if not self.dfloc in self.parent.childmeta_df.index.tolist():
            raise Error('could not find my dfloc \'%s\' in my parents \'%s\' index'%(self.dfloc, self.parent.name))
        
        if not self.name in self.parent.childmeta_df.loc[:,'name'].values.tolist():
            raise IOError
        

        
    
    def birth_dfeat(self, parent): #setup the dfeat under this parent
        """here we use a special inheritance 
        as we are spawning the dfeat with a different object than the real parent
        
        see datos.Dfeat_tbl.raise_all_dfeats()
        """
        #=======================================================================
        # defaults
        #=======================================================================
        #logger = self.logger.getChild('birth_dfeat')
        
        """handled by init_clone
        self.parent = weakref.proxy(parent)"""
        self.state = 'birth'
        #=======================================================================
        # clear all your updates
        #=======================================================================
        self.halt_update()
        
        #=======================================================================
        # inherit all the attributes from your parent
        #=======================================================================
        self.hse_o = self.parent.parent

        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            self.check_dfeat()
        
        #=======================================================================
        # build the dfeat
        #=======================================================================
        #logger.debug("build_dfeat()")
        self.build_dfeat()
        #logger.debug('finished \n')
        self.state = 'ready'
        return
    
    def build_dfeat(self):
        'need this as standalone for  dyno handle calls'
        """fien to run on an outdated parent
        if self.depend_outdated(halt=True): return"""
        logger = self.logger.getChild('build_dfeat')
        
        #=======================================================================
        # check dependencies
        #=======================================================================
        if self.depend_outdated(    depend = self.hse_o,
                                    search_key_l = ['set_geo_dxcol()'], #see if the parent has these
                                    reque = False,
                                    force_upd = False, #force the parent to update if found
                                    halt = False): #clear all of my updates (except this func)
            
            raise IOError #should not be built if the parent is this outdated
        
        #=======================================================================
        # garage area override
        #=======================================================================
                
        #logger.debug('eval_price_calc \n')
        self.eval_price_calc_str()
        """ to speed things up, just pulling out the useful bits
        logger.debug('init_dyno \n')
        self.init_dyno()"""
        #logger.debug('finished \n')
        
        self.halt_update()
        """using halt command
        self.upd_cmd_od = OrderedDict() #empty the dictionary""" 
        
        return
                      

             
    def eval_price_calc_str(self): #get the calc price by evaluating the string in teh table
        """
        evalutes the price_calc_str provided on the dyn_dmg_tble colum for this bldg type
        #=======================================================================
        # CALLS
        #=======================================================================
        load_data()
        update.run()
        """
        #=======================================================================
        # defaults
        #=======================================================================
        
        
        #=======================================================================
        # check dependneciies
        #=======================================================================
        dep_p = [([self.hse_o], ['set_geo_dxcol']),\
                 ([self.parent], ['build_dfunc'])]
        
        if self.deps_is_dated(dep_p, caller='eval_price_calc_str'):
            return False
            

        #=======================================================================
        # #make all the variables local
        #=======================================================================
        df = self.hse_o.geo_dxcol[self.place_code] #eference to the houses geometry dxcol a slice for just this place
        """ so the price_calc_str has the right vars to work with"""
        height      = df.loc['height', 'f'] #        standing height
        
        t_area      = df.loc['area', 't'] #         total area for this floor
        f_area      = df.loc['area', 'f']#    finished area for this floor
        u_area      = df.loc['area', 'u'] #   unifnished area for this floor
        
        t_per       = df.loc['per', 't']  # total perimeter for this floor
        f_per       = df.loc['per', 'f']  # finished area perimenter
        u_per       = df.loc['per', 'u'] # unfinisehd perimeter
        
        f_inta      = df.loc['inta', 'f']
        u_inta      = df.loc['inta', 'u']
        

        base_area   = float(self.base_area)
        base_per    = float(self.base_per)
        base_inta   = float(self.base_inta)
        
        #attributes passed form the dfeat tabler
        base_price  = float(self.base_price)
        unit_price  = float(self.unit_price)
        quantity    = int(self.quantity)
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f: 
            if pd.isnull(t_area): 
                raise IOError
            if t_area is None: 
                raise IOError
            if t_area < 5: 
                raise IOError
            
            self.check_dfeat()
        
        """
        hp_oop.log_all_attributes(self, logger = logger)
        """
        #=======================================================================
        # execute hte price calc string
        #=======================================================================
        try:        
            calc_price = eval(self.price_calc_str)
        except:
            raise Error('unable to evaluate price_calc_str: \'%s\''%self.price_calc_str)
        
        #=======================================================================
        # postchecks
        #=======================================================================
        if self.db_f: 
            logger = self.logger.getChild('eval_price_calc_str')
            logger.debug('calc_price = %.2f on eval: %s'%(calc_price, self.price_calc_str))
        
            if pd.isnull(calc_price): 
                raise IOError
            if calc_price == 0: 
                logger.debug('got zero price')
            elif not calc_price >= 0: 
                logger.warning('not calc_price (%.2f) > 0 with \'%s\''%(calc_price, self.price_calc_str))
                raise IOError
            
            #make sure your parent is qued for resetting
            if not self.session.state == 'init':
                if self.session.dyn_vuln_f:
                    if not self.parent.reset_dfunc in list(self.parent.reset_func_od.keys()): 
                        raise IOError
            

            
        #=======================================================================
        # update handling
        #=======================================================================
        #set the att
        self.calc_price = calc_price
        
        #update parents df
        self.parent.childmeta_df.loc[self.dfloc, 'calc_price'] = calc_price
        
        if not self.session.state == 'init':
            #flag parent
            'this is redundant as recomplie_dyn() should also flag this'
            self.parent.reset_shdw_kids_f = True
            

            if not self.state == 'birth':
                'dont want to recompile during the original compiling!'
                self.parent.que_upd_skinny('recompile_ddar', 'calc_price',proxy(self),'eval_price_calc_str')
                
                'during birth we call a full halt'
                self.del_upd_cmd(cmd_str = 'eval_price_calc_str')

        return True
    
    
    
    def depth_check(self, #check that you are on the floor youre supposed to be
                    depth = None, 
                    tol = 0.1, 
                    dep_check = True): 
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('depth_check')

        if depth is None: depth = self.depth
        swap = False
        #=======================================================================
        # check dependneciies
        #=======================================================================
        if dep_check: #letting callers skip thsi for speed
            if self.is_frozen('depth', logger = logger): raise IOError
            
            #dependency pairing
            dep_l =  [([self.hse_o], ['set_hse_anchor', 'set_geo_dxcol']),\
                      ([self.parent], ['set_dfunc_anchor', 'build_dfunc'])]
            
            if self.deps_is_dated(dep_l, caller='depth_check'):
                return False
        
                
        #=======================================================================
        # get floro height
        #=======================================================================
        if self.place_code == 'B':
            height = self.hse_o.anchor_el - self.parent.anchor_el
            'this allows for multiple anchor_ht_code methods. means the set_anchor has to be updated'
        else:
            height = self.hse_o.geo_dxcol.loc['height',(self.place_code,'f')]
            
        #=======================================================================
        # check depth
        #=======================================================================
        if depth > height: #too big for my floor
            newd = depth - height #take all the depth above the height 
            logger.debug('weve outgrowh our parent by %.2f'%newd)
            
            if self.place_code == 'B': 
                self.change_dfunc('M') #check and change parents 
                swap = True
            else:
                logger.debug('already on teh main floor... nothing to do')
                
        else: #still fit in my floor
            newd = depth
            
        #=======================================================================
        # handle new depth
        #=======================================================================
        if (newd > self.depth + tol) or (newd < self.depth - tol) or swap:
            logger.debug('with height=%.2f found significant depth change (%.2f to %.2f)'%(height, self.depth, newd))
            self.handle_upd('depth', newd, proxy(self), call_func = 'depth_check') #change my attribute
            self.parent.reset_shdw_kids_f = True
        else:
            logger.debug('insignificant depth change')

            
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not self.place_code == self.parent.place_code: 
                raise IOError
            
            if self.dmg_code == 'S':
                if not self.acode == self.hse_o.acode_s:
                    raise Error('damage code mismatch with house')
            elif self.dmg_code == 'C':
                if not self.acode == self.hse_o.acode_c:
                    raise Error('damage code mismatch with house')
            else:
                raise Error('unrecognized damage code')
            
            if newd < 0: 
                raise IOError
        
        return True
            
    def set_new_depth(self, new_el_raw, #elevate the selected dfeats to the new elevation
                      min_max = 'max', tol = 0.1): 
        """
        need a special function for modifying dfeat depths from elevations
        this converts elevations to depths using some logic and the dfunc's anchor_el
        #=======================================================================
        # INPUTS
        #=======================================================================
        new_el_raw:    new elevation for this feature
        min_max: logic to set new elevation relative to old elevation
        
        
        #=======================================================================
        # FUTURE THOUHGTS
        #=======================================================================
        perhaps we should have combined all dfuncs into 1?
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('set_new_depth')
        """decided to be more explicit
        if self.depend_outdated(): return"""
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not self.parent.parent == self.hse_o:
                raise IOError
            
            if self.dmg_code == 'S':
                if not self.acode == self.hse_o.acode_s:
                    raise Error('damage code mismatch with house')
            elif self.dmg_code == 'C':
                if not self.acode == self.hse_o.acode_c:
                    raise Error('damage code mismatch with house')
            else:
                raise Error('unrecognized damage code')
            
        #=======================================================================
        # frozen and dependneces
        #=======================================================================
        if self.is_frozen('depth', logger = logger): return
        
        dep_l =  [([self.hse_o], ['set_hse_anchor', 'set_geo_dxcol']),\
                  ([self.parent], ['set_dfunc_anchor', 'build_dfunc'])]
        
        if self.deps_is_dated(dep_l, method = 'force', caller = 'set_new_depth'):
            raise IOError
        """
        problem with this shortcut is the parents dependencies may also be out of date
        if 'set_dfunc_anchor()' in self.parent.upd_cmd_od.keys():
            self.parent.set_dfunc_anchor()
            'this is the only dependency I care about. avoids ahving to add all the dfeats'"""
            

        old_el = self.parent.anchor_el + self.depth #should be the updated anchor)el
        #=======================================================================
        # get the new elevation
        #=======================================================================

        # raw elevation
        if min_max is None:
            logger.debug('using raw new_el %.2f'%new_el_raw)
            new_el = new_el_raw
            
        # logical elevation
        else:
            logger.debug('with new_el = %.2f using logic from old_el = %.2f and min_max code \'%s\''
                         %(new_el_raw, old_el, min_max))
            #===================================================================
            # by min/max flag
            #===================================================================
            if min_max == 'min': 
                new_el = min(new_el_raw, old_el)
            elif min_max == 'max': 
                new_el = max(new_el_raw, old_el)
            else: raise IOError
            
        #=======================================================================
        # depth handling
        #=======================================================================
        #shortcut out for non change
        'because we are setting the depth directly with this func, if there is no change, no need to check'
        if (old_el< new_el +tol) & (old_el > new_el - tol):
            logger.debug('old_el = new_el (%.2f). doing nothing'%new_el)
        else:
            #===================================================================
            # significant change
            #===================================================================
            
            new_depth = new_el - self.parent.anchor_el
            
            logger.debug('from parent.anchor_el = %.2f and new_el_raw = %.2f got new depth = %.2f'
                         %(self.parent.anchor_el, new_el, new_depth))
            
            #=======================================================================
            # send this for checking/handling
            #=======================================================================
            if not self.depth_check(depth = new_depth, tol = tol, dep_check = False): 
                raise IOError #we have the same dependencies so there is no reason this should fail

        #=======================================================================
        # updates
        #=======================================================================
        'depth_check sets the value'
        self.del_upd_cmd('set_new_depth') #no need to ru nthis check
        #=======================================================================
        # post check
        #=======================================================================
        if self.db_f:
            if self.depth < 0 : raise IOError
            
            if not self.parent.reset_dfunc in list(self.parent.reset_func_od.keys()): raise IOError
        
        #logger.debug('finished \n')
        
        return True

    
    def change_dfunc(self, new_pc): #move from one Dfunc to another
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('change_dfunc')
        parent_old = self.parent
        
        
        #=======================================================================
        # get the new parent
        #=======================================================================
        #get the new parents name
        'assumes the damage code/type stays the same... only changing place code'
        new_p_n = new_pc + self.parent.dmg_code 
        
        try:
            parent_new = self.hse_o.dfunc_d[new_p_n]
        except:
            if not new_p_n in list(self.hse_o.dfunc_d.keys()):
                logger.error('passed dfunc name \'%s\' not loaded'%new_pc)
            
            raise IOError
        
        logger.debug('moving from \'%s\' to \'%s\''%(parent_old.name, parent_new.name))
        
        self.place_code = new_pc #set the new place_code
        #=======================================================================
        # swap out
        #=======================================================================
        """handled by update_childmeta() now
        parent_old.upd_dd_df(self.name, method = 'delete') #remove yourself from teh dd_df"""
        
        self.session.parent_swap(self, parent_new) #inherit, add to family lib, initilze logger, set new gid

        
        #=======================================================================
        # calcluate/apply changes
        #=======================================================================
        """price_calc wont change by just moving floors
        none of the birth_dfeat() cmds are necesary for a floor change
        #update your price calc
        self.eval_price_calc_str()"""
        
        """ handled by updaet_childmeta()
        parent_new.upd_dd_df(self.name, method = 'add') #remove yourself from teh dd_df"""
        #=======================================================================
        # updates
        #=======================================================================
        """this is covered by set_new_depth handle_upd
        parent_new.reset_shdw_kids_f = True #parent needs to swap out all its kids"""
        
        parent_old.reset_shdw_kids_f = True #tell your old parent to reset everyone next time
        
        #que the update commands on the parents
        'this is probably redundant '
        parent_old.que_upd_skinny('recompile_ddar', 'depth',proxy(self),'change_dfunc')
        """ hte new parent should receive the update command from set_new_depth()
        """

        if self.db_f:
            
            if self.name in parent_old.childmeta_df.loc[:,'name'].tolist(): raise IOError
            if not self.name in parent_new.childmeta_df.loc[:,'name'].tolist(): raise IOError
            if not self.dfloc in parent_new.childmeta_df.index.tolist(): raise IOError
            
            if not self.parent.__repr__() == parent_new.__repr__():
                raise IOError
            
            if not self.parent.hse_o == self.hse_o: raise IOError
            
            if self.dmg_code == 'S':
                if not self.acode == self.hse_o.acode_s:
                    raise Error('damage code mismatch with house')
            elif self.dmg_code == 'C':
                if not self.acode == self.hse_o.acode_c:
                    raise Error('damage code mismatch with house')
            else:
                raise Error('unrecognized damage code')
            
            if not parent_old.reset_dfunc in list(parent_old.reset_func_od.keys()): raise IOError
            
            if not parent_new.reset_dfunc in list(parent_new.reset_func_od.keys()): raise IOError
            
            """
            self.parent.name
            df = parent_new.childmeta_df
            
            """
        return
  