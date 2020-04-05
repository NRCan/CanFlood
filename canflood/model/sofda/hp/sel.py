'''
Created on Jun 21, 2018

@author: cef

object selectors
'''
                     

#===============================================================================
# PERIODIC vs EXPLICIT Selectors ---------------------------------------------
#===============================================================================\
"""
EXPLICIT Selectors
    Those selectors with upd_sim_lvl = None. selector not run by run_selectors()
    Only Actions and Dynps are setup to handle Explicit selectors
    
PERIODIC
    Those selectors with upd_sim_lvl == 0, 1, or 2. triggered durin run_selectors()

"""
#===============================================================================
#OUPUTS ---------------------------------------------------------------------
#===============================================================================
"""
As selectors are foundational to the OUtputrs, we use a special function to output attributes of the selector
"""
#===============================================================================
#pick_d KEYS ------------------------------------------------------------------
#===============================================================================
"""
these should be by gid to handle selections across parents
"""

# IMPORTS ----------------------------------------------------------------------
import logging
import os, sys, copy, weakref, time, random
from collections import OrderedDict
from weakref import WeakValueDictionary as wdict
from weakref import proxy

#import pandas as pd
import numpy as np
import pandas as pd
#import scipy.stats 

#import model.sofda.hp.basic as hp_basic
import model.sofda.hp.pd as hp_pd
import model.sofda.hp.oop as hp_oop
import model.sofda.hp.sim as hp_sim
import model.sofda.hp.data as hp_data
import model.sofda.hp.dict as hp_dict
'because we want our selectors to be sim objects, cant let anything in hp_sim use this mod'


mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')

class Sel_usr_wrap(object): #functions for objects that want to use Selectors
    """ WARNING: This is used on objects that need Selector capabilities
        but the user did not want a selector for that particular instance
    
    #===========================================================================
    # classes inheriting this
    #===========================================================================
    udev_scripts.Action
    
    hp_dynp.Dynamic_par
    
    hp_outs.Outputr
    
    hp_sel.Selector
        
    """
    #===========================================================================
    # program pars
    #===========================================================================

    #===========================================================================
    # user provided
    #===========================================================================
    sel_n       = None #name of selector subscribed to
    
    #===========================================================================
    # calculated
    #===========================================================================
    pick_d      = None #objects picked 
    pick_k_ar = None #array of keys (for faster selection)
    
    sel_o       = None #selector object associated with this dynp

    picko_bl    = None #branch level of picked object
    picko_p_f   = False #object permanence of selected objects
    #updated_pick_f = False #flag  on whether our pick is up to date
    
    pclass_n = None #class name of objects you select
    
    
    #===========================================================================
    # data containers
    #===========================================================================
    sel_cnt     = 0
    
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Sel_usr_wrap') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')

        #=======================================================================
        # #initilzie teh baseclass
        #=======================================================================
        super(Sel_usr_wrap, self).__init__(*vars, **kwargs) 

        logger = self.logger.getChild('__init__')
        #=======================================================================
        # unique 
        #=======================================================================
        logger.debug('continuing unique init')
        """ keeping this as none
        self.pick_d = wdict()"""
        self.pick_hs_stamp = (0,0) #stamp indicating when your pick was made (sim_lvl, sequence)
        
        #reset_d
        if self.reset_d is None: self.reset_d = dict()
        'pick_d is added here for redundancy'
        self.reset_d.update({'pick_d':None, 'sel_cnt':0, 'pick_hs_stamp':(0,0)})
        
        self.reset_func_od.update({self.reset_selusr:'Sel_usr_wrap'})

        self.pclass_n = self.pclass_n.strip()
        #=======================================================================
        # inherit the selector
        #=======================================================================
        if not self.sel_n is None: 
            if not self.sel_n in self.session.sels_d:
                raise IOError('passed selector \'%s\' not found in set'%self.sel_n)
            else: 
                self.sel_o = weakref.proxy(self.session.sels_d[self.sel_n]) #attach your selector
                logger.debug('attached selector \'%s\''%self.sel_o.name)

                
            
        #=======================================================================
        # set handles for this pclass_n
        #=======================================================================
        if not self.pclass_n in self.session.family_d:
            """maybe youre looking for dfeats but havent loaded any acodes that use dfeats?"""
            raise IOError('Selector %s pclass \'%s\' is not in the family_d!'%(self.name, self.pclass_n))
        
        
        k1 = list(self.session.family_d[self.pclass_n].values())[0] #just get the first kid
        self.picko_bl = k1.branch_level
        self.picko_p_f = k1.perm_f
        logger.debug('for pclass_n \'%s\' set picko_bl = %i and picko_p_f =\'%s\''
                     %(self.pclass_n, self.picko_bl, self.picko_p_f))
            
        #=======================================================================
        # perform first selection
        #=======================================================================
        """ let the base objects do this
        self.get_selection()"""
            
        #=======================================================================
        # checks
        #=======================================================================
        if self.db_f: 
            self.sel_usr_chk()

                    
        logger.debug('finished __init__ \n')
        return
    
    
    def sel_usr_chk(self):
        
        logger = self.logger.getChild('__init__checks')
        if not hasattr(self,'reset_f'): raise IOError #needs to be a sim object
        if not self.pclass_n in list(self.session.family_d.keys()): raise IOError #this object needs to be loaded
        
        #selector logic checks
        if not self.sel_n is None:
            
            #periodic selector logic check
            if isinstance(self.sel_o.upd_sim_lvl, int):
                if not self.upd_sim_lvl >= self.sel_o.upd_sim_lvl: 
                    logger.error('my upd_sim_lvl (%s) needs to be >= my selectors \'%s\''
                                 %(self.upd_sim_lvl, self.sel_o.name))
                    raise IOError
                
            elif self.sel_o.upd_sim_lvl == 'none': 
                logger.debug('got explicit selector')
            else: raise IOError
            
        #object permanence logic check
        if not self.picko_p_f:
            if not self.upd_sim_lvl == 'none':
                if not self.upd_sim_lvl > 0: 
                    logger.error('selection workers, whose picked objects are non-permanent, need upd_sim_lvl >0')
                    raise IOError
        
    def decide_pick(self, big_d=None, container=wdict): #decides whether to make the selection
        logger = self.logger.getChild('decide_pick')
        
        pick_d = None
        
        """
        Standard: Consider NOT making a new pick?
        """
        
        if not self.pick_d is None: #EXPLICIT, nothign picked yet
        
            if big_d is None: #no subset passed
                
                if self.sel_o is None: #no selector
                    logger.debug('no selector. no need to re-run')
                    pick_d = self.pick_d
                  
                    """
                    elif not self.sel_o.upd_sim_lvl == 'none': #with periodic selectors
                    
                    couldnt figure out a nice qay to get the (sim_lvl, sequence) tags to work
                    #get stamps
                    opick_sim_lvl, opick_seq = self.pick_hs_stamp
                    sel_opick_lvl, sel_opick_seq = self.sel_o.pick_hs_stamp
                    
                    sim_lvl, seq = self.session.hs_stamp
                    
                    #compare stamps    
                    'finer resolution objects (tsteps) have HIGHER sim_lvls'                
                    if (opick_sim_lvl <= self.sel_o.upd_sim_lvl) & (opick_seq <= seq):
                        logger.debug('using fresh pick last_sim_lvl (%i)  <= sim_lvl (%i) &  last_seq (%i) <= seq(%i)'
                                     %(opick_sim_lvl, sim_lvl, opick_seq, seq))
                        pick_d = self.pick_d
                        
                    else:
                        logger.debug('stale pick.. need to re run')
                    """
                    """
                    self.sel_o.upd_sim_lvl
                    
                    if self.sel_o.upd_sim_lvl == 0: #STATIC selectors
                        logger.debug('static selector. no need to re-run')
                        pick_d = self.pick_d
                    
                    I dont like this... lets just run the pick again every time
                    elif self.sel_o.upd_sim_lvl <= self.upd_sim_lvl: #coarse period selectors
                        logger.debug('selector updates LESS frequently than I')
                        
                        if self.updated_pick_f: #fresh pick
                            logger.debug('updated_pick_f =TRUE. (fresh pick) using my pick')
                            pick_d = self.pick_d
                            
                    else:
                        logger.debug('selector updates MORE frequently than I. rerun')"""
                            
                else:
                    logger.debug('selector. runing')
                    
            else:
                logger.debug('got a big_d.. need to slice it')
                
        else:
            logger.debug('I dont have a self.pick_d. running')
        
        
        if self.db_f:
            if self.upd_sim_lvl == 'none':
                if not self.pick_d is None: 
                    logger.error('explicit object has pick_d')
                    raise IOError
                
            if self.__class__.__name__ == 'Selector': raise IOError
                
            
        

        if pick_d is None:
            logger.debug('no criteria satisfied. running make_pick \n')
            
            pick_d =  self.make_pick(big_d=big_d, container=container)
        
        """doing this in make_pick()
        #=======================================================================
        # store this pick
        #=======================================================================
        if not self.upd_sim_lvl == 'none':
            self.pick_d = copy.copy(pick_d)""" 

        return container(pick_d)


    def make_pick(self, #makes the selection from selector,  owner logic, and passed set
                  big_d=None, container=wdict): 
        
        """
        should not be called by teh selsector
        #=======================================================================
        # INPUTS
        #=======================================================================
        big_d: collection of objects to perform a sub selection of
            this may have a higher or equal branch_level to my pick objects 
        
        20180728
        modified so that selectors passed on the dynp tab are only called when teh dynp is run
        must be explicit
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('make_pick')
        #big_d1 = container() #doesnt matter.. not carrying
        #pick_d = container()
        pick_d = None #placeholder

        logger.debug('with passed big_d \'%s\' and my upd_sim_lvl = %s'%(type(big_d), self.upd_sim_lvl))
        
        if self.db_f:
            big_d_raw = copy.copy(big_d)
            if self.__class__.__name__ == 'Selector': raise IOError
            
        #=======================================================================
        # simple selector mathces
        #=======================================================================
        'for selector users without a subset and the same child level as the selector'
        if (big_d is None) & (not self.sel_o is None):
            if self.sel_o.pclass_n == self.pclass_n:
                pick_d = self.simple_pick()

            
        #=======================================================================
        # complex pick
        #=======================================================================
        if pick_d is None:
            if big_d is None:
                
                big_d1 = container(self.session.family_d[self.pclass_n])
                
                #===================================================================
                # try:
                #     big_d1 = container(self.session.family_d[self.pclass_n])
                # except:
                #     if not self.pclass_n in self.session.family_d.keys():
                #         logger.error('dynp_class \'%s\' not found in family_d (%i): %s'
                #                      %(self.pclass_n, len(self.session.family_d), self.session.family_d.keys() ))
                #         raise IOError
                #     raise IOError
                #===================================================================
                    
                logger.debug("took all \'%s\' objects from family_d %i "%(self.pclass_n, len(big_d1)))
            
            else:
                logger.debug('checking for correct level with drop_subset() for \'%s\''%self.pclass_n)
                big_d1 = self.drop_subset(big_d, container=container)
                
            if self.db_f:
                if len(big_d1) == 0:
                    raise IOError
            #=======================================================================
            # make secondary selection by selector
            #=======================================================================        
            if not self.sel_o is None:
                #===================================================================
                # logger.debug('performing secondary selection with \'%s\' whose upd_sim_lvl = \'%s\''
                #              %(self.sel_o.name, self.sel_o.upd_sim_lvl))
                #===================================================================
                
                #===================================================================
                # explicit selectors
                #===================================================================
                if self.sel_o.upd_sim_lvl == 'none':
                    logger.debug('executing explicit selector \n')
                    self.sel_o.handler = proxy(self) #re assign the handler
                    pick_d = self.sel_o.run_sel(big_d = big_d1, container = container)
                    'this selects from within the passed set'
                #===================================================================
                # periodic 
                #===================================================================
                else:
                    logger.debug('getting slice of my big_d %i from \'%s\' with upd_sim_lvl = %i'
                                 %(len(big_d1), self.sel_o.name, self.sel_o.upd_sim_lvl))
                    
                    pick_d = self.sel_o.slice_handler(big_d1, container = container)
                    
            else: # no selector
                #logger.debug('I dont have a selector. no secondary selection')
                pick_d = big_d1
            
        #=======================================================================
        # wrap up        
        #=======================================================================
        if not len(pick_d)> 0:  
            logger.warning('got empty pick')
            #return container()
        else:
            if self.db_f: 
                self.check_pick(pick_d)
            logger.debug('made pick_d %i of \'%s\''%(len(pick_d), list(pick_d.values())[0].__class__.__name__))
            
            
        #=======================================================================
        # storage
        #=======================================================================
        if (not self.upd_sim_lvl == 'none'):
            self.pick_hs_stamp = copy.copy(self.session.hs_stamp) #set the stamp of when you updated your pick
            'allowing non permanents.. these should be removed from teh pick and reset'
            logger.debug('with upd_sim_lvl = %i. setting self.pick_d (%i)'%(self.upd_sim_lvl, len(pick_d)))
            self.pick_d = copy.copy(pick_d)
            self.pick_k_ar = np.array(list(pick_d.keys()))
            #===================================================================
            # reseting
            #===================================================================
            """ putting this here because make_pick() is not mandatory in the __init__
            leaving some flexibility for user objects to call this when needed"""
        
            if self.session.state == 'init':
                if self.picko_p_f:
                    logger.debug('session.state = init with permanent objects. updating reset_d')
                    self.reset_d['pick_d'] = copy.copy(pick_d)
                    self.reset_d['pick_k_ar'] = copy.copy(self.pick_k_ar)
                
                
            
        'this reference may change otherwise...'
        return pick_d
    
    def simple_pick(self,
                    container = wdict):
        logger = self.logger.getChild('simple_pick')
        
        if self.db_f:
            if self.sel_o is None: raise IOError
            if not self.sel_o.pclass_n == self.pclass_n: raise IOError
        
        logger.debug("simple pick of \'%s\' from \'%s\'"%(self.pclass_n, self.sel_o.name))
        
        if self.sel_o.upd_sim_lvl == 'none':
            logger.debug('explicit selector. executing selection')
            self.sel_o.handler = proxy(self) #re assign the handler
            pick_d = self.sel_o.run_sel(container = container)
            
        else:
            
            pick_d = self.sel_o.pick_d
        
        
        return pick_d
        
        
    def check_pick(self, pick_d):
        logger = self.logger.getChild('check_pick')
        
        if len(pick_d) == 0:
            logger.error('got no pick')
            raise IOError
        
        
        #=======================================================================
        # loop and check consistency
        #=======================================================================
        first = True
        for key, kid in pick_d.items():
            cni = kid.__class__.__name__
            if first:
                cn1 = cni
                
                #check against my own
                if not cn1 == self.pclass_n: raise IOError
                
                first = False
                continue
            
            #class name check
            if not cn1 == cni: raise IOError
            
            #object pernanence
            if not kid.perm_f == self.picko_p_f: raise IOError
            
    def slice_handler(self, #find the interescection of a passed d with your own pick (accounts for hierarchy)
                      big_d,  #see below
                      container=wdict): #type of container to return 
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        big_d: some set of objects to take a slice of
            these may be higher branch_levels than my pick objects
            these may include more objects than my selection
            
        self.name
        
        """
        #=======================================================================
        # shortcuts
        #=======================================================================
        if big_d == self.pick_d: return container(big_d) #no slicing, return everything
        if len(big_d) ==0: return container() #nothing passed!
        
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('slice_handler')
        
        if len(self.pick_d) == 0:
            logger.debug('I have no pick to find the intersect on! returning empty')
            return container()

        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if big_d is None: raise IOError
            if self.upd_sim_lvl== 'none': raise IOError #should only be doing this for periodic
        
        d_og = self.pick_d #get the pick as it exists now

        #=======================================================================
        # depth handling/ branch level
        #=======================================================================
        #boolean array of matches
        bool_ar = np.isin(self.pick_k_ar, list(big_d.keys()))
        
        if not np.any(bool_ar): #no matches
            logger.debug('on big_d %i checking/getting subset for \'%s\' \n'%(len(big_d), self.pclass_n))
            vert_d = self.drop_subset(big_d)
            
            #get a new boolean
            bool_ar = np.isin(self.pick_k_ar, list(vert_d.keys()))
            
            if self.db_f:
                #check for class name match
                k1 = list(d_og.values())[0]
                k2 = list(vert_d.values())[0]
                
                if not k1.__class__.__name__ == k2.__class__.__name__: raise IOError
                if not k1.__class__.__name__ == self.pclass_n: raise IOError
            
        if self.db_f:
            if not np.all(np.isin(self.pick_k_ar, list(d_og.keys()))): raise IOError
        
        #=======================================================================
        # sibling handling/ lateral selection
        #=======================================================================
        """
        logger.debug('slicing vert_d (%i) of \'%s\' against my original pick (%i)'%(len(vert_d),self.pclass_n, len(d_og)))
        d2 = hp_dict.merge(d_og, vert_d, set_type = 'intersect', container = container, logger = logger)"""
        
        keys_match = self.pick_k_ar[bool_ar].tolist() #get the matching subset
        logger.debug("found %i/%i matching keys. getting intersect: %s"%(len(keys_match), len(self.pick_d), keys_match))
        
        d2 = container({k: d_og[k] for k in keys_match})#get the intersection between matching keys and original pick
        #=======================================================================
        # wrap up
        #=======================================================================
        if d2 is None:raise IOError
        elif len(d2)== 0: 
        
            logger.warning('got no intersect on passed big_d %i with my pick %i'%(len(big_d), len(d_og)))
            return d2
        else:
            logger.debug('got intersect with %i/(%i) \'%s\' objs'
                         %(len(d2), len(self.session.family_d[self.pclass_n]), self.pclass_n))
            
            return d2
        """
        d2.keys()
        
        """
  
            
    def drop_subset(self, big_d, pclass_n = None, container=wdict): #get the children at the correct level
        
        if self.db_f:
            if not big_d is None:
                if len(big_d) == 0:
                    raise IOError
        #=======================================================================
        # shortcut for correct level
        #=======================================================================
        obj1 = list(big_d.values())[0]
        big_cn = obj1.__class__.__name__ 
        
        if pclass_n is None: pclass_n = self.pclass_n
        
        if big_cn == pclass_n: 
            #logger.debug('passed big_d \'%s\' is already the correct level. doing nothing'%big_cn)
            return big_d #already the correct level
        
        
        logger = self.logger.getChild('drop_subset')

        
        #=======================================================================
        # run condenser to get pick correct level set
        #=======================================================================
        kcond_o = hp_oop.Kid_condenser(big_d, 
                                       pclass_n, 
                                       db_f = self.db_f, 
                                       key_att = 'gid', #object attribte on which to key the result container
                                       container = container,
                                       logger = logger)
             
        class_d = kcond_o.drop_all()
             
        logger.debug('condensed dictionary %i of \'%s\' to %i of \'%s\''
                     %(len(big_d), big_cn, len(class_d), pclass_n))
        
        #del kcond_o
        
        return container(class_d)
    
    def reset_selusr(self): 
        """
        need this to ensure the pick doesnt contain references to dead objects
        """
        logger = self.logger.getChild('reset_selusr')
        
        #=======================================================================
        # selection updating
        #=======================================================================
        if not self.picko_p_f:
            'some workers may not store their pick_d... no need to reset then'
            if not self.pick_d is None:
                logger.debug('my selection of \'%s\'s is non-permanent. re-running make_pick \n'%self.pclass_n)
                
                self.make_pick()
                'stores self.pick_d and self.pick_k_ar'
                
                #=======================================================================
                # checks
                #=======================================================================
                if self.db_f:
                    if 'pick_d' in list(self.reset_d.keys()): 
                        raise IOError #should not be reseting for non-permanents
                    if self.upd_sim_lvl == 'none': raise IOError #pick_d should be none
                    
                    if self.picko_p_f: raise IOError #check for a wrong re-flag

        return 
            
class Selector( Sel_usr_wrap,
               hp_data.Data_wrapper, 
               hp_sim.Sim_o,
               hp_oop.Child): #generic object selector #, 
    """
    #===========================================================================
    # OWNERSHIP
    #===========================================================================
    As I want to be able to output selectorsa s submodels, I'm having udev own them
    
    however, as udev.Actions need the selectors to be loaded first, 
        I'm going this ownership loop within udev
    """
    #===========================================================================
    # Program vars
    #===========================================================================
    # file writing
    write_pick_f    = False #flag to write hte pick names to a file
    pick_file   = None #file to write ipck in
    handler     = 'nobody'
    
    # object handling overrides
    db_f            = True
    #load_data_f     = False #calling explicitly 
    key_att         ='gid' #object attribute name on which to key selection containers
    
    #===========================================================================
    # user defined vars
    #===========================================================================
    pclass_n        = None #object name on which this is applicable
    spcl_f_exe_str  = None #string for executing a special selctor fucntion
    metadf_bool_exe = None # simple boolean to pick youself based on the classname's parent's childmeta_df.
    obj_bool_exe    = None #pick set based on object booleans e.g. 'obj.name == 'myname'
    headpath        = None #headpath to the bid_list.csv
    tailpath        = None
    upd_sim_lvl     = None #class name of step on which to update hte selector
    
    #===========================================================================
    # data containers
    #===========================================================================
    pick_cnt    = 0
    pick_nl     = None #used for writing pick to file
    
    #===========================================================================
    # calculation pars
    #===========================================================================
    #pick_d      = None #d[picked object name] = [picked object]
    ranked_l    = None #ranked list of object names. for ranked choice


    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Selector')
        logger.debug('start _init_')
        
        
        super(Selector, self).__init__(*vars, **kwargs) #initilzie teh baseclass  
        
        #=======================================================================
        # unique setup
        #=======================================================================
        self.pick_nl = []
        """done by the wrapper
        self.pick_d = dict()"""
        self.reset_d.update({'pick_nl':[], 'pick_cnt':0})
        
        #self.reset_func_od.update({self.reset_selector:'Selector'})
        
        #=======================================================================
        # common setup
        #=======================================================================
        if self.sib_cnt == 0:
            self.model = None
            self.handler = self.session #initial set
            'see note in udev.Udev.raise_chidlren()'
        
        'this is getting reset somewhere'
        self.outpath = os.path.join(self.session.outpath, '_sels')
            
        #=======================================================================
        # prechecsk
        #=======================================================================
        if self.pclass_n is None:
            self.logger.error('need to provide a pclass_n')
            raise IOError
        
        #=======================================================================
        # formatting
        #=======================================================================
        self.write_pick_f = bool(self.write_pick_f)

        
        #=======================================================================
        # custom setup functions
        #=======================================================================
        logger.debug('\n')
        self.set_upd_sim_lvl()
        
        if not self.headpath is None: 
            logger.debug('load_data() \n')
            self.load_data()
        
        #initial selection
        if self.upd_sim_lvl =='none':
            logger.debug('raised as EXPLICIT selector. no inital selection')
        else: 
            logger.debug('upd_sim_lvl = %i. making first pick \n'%self.upd_sim_lvl)
            self.handler = self
            self.pick_d = self.run_sel() #run the first selection
            
            #===================================================================
            # reseting
            #===================================================================
            if self.picko_p_f:
                logger.debug('picko_p_f=TRUE. updating the rest dictionary with pick_d %i'%len(self.pick_d))
                self.reset_d['pick_d'] = copy.copy(self.pick_d)
                self.reset_d['pick_k_ar'] = copy.copy(self.pick_k_ar)
                
            else:
                'the pick should be reset by Sel_usr_wrap.reset_simo() override'
                pass
        
        logger.debug('finished _init_ as \'%s\' \n'%self.name)
        
        return
  
    

    def load_data(self): #load the data passed for this Selector on the 'selectors' tab
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        __init__
        
        #=======================================================================
        # TODO
        #=======================================================================
        Change this so it selects  by the model index ("bid") rather than name
        
        well... we don't have the model index in the GID...
        """

        logger = self.logger.getChild('load_data') 
        
        #=======================================================================
        # precheck
        #=======================================================================
        if self.db_f:
            if not self.data is  None:  raise IOError 
            if self.headpath is None: raise IOError
        #=======================================================================
        # get the filepath
        #=======================================================================
        filepath = self.get_filepath()
        self.filepath = filepath
        #=======================================================================
        # laod the selection list
        #=======================================================================
        """
        we expect a list of object n ames
        hp_pd.v(df_raw)
        """
        df_raw = hp_pd.load_csv_df(filepath, index_col = None, header=None, logger=logger)
        
        if not df_raw.shape[1] == 1:
            logger.error('expected shape (x, 1) and got %s'%str(df_raw.shape))
            raise IOError
        
        data = df_raw.astype(str).iloc[:,0].values.tolist()
        
        if self.db_f: 
            self.check_data(data)
        
        #=======================================================================
        # wrap up
        #=======================================================================
        logger.debug('finished with %i entries loaded'%len(data))
        
        self.data = data
        
        self.reset_d['data'] = copy.copy(data) #add this for restoring
        
        
        self.session.ins_copy_fps.add(self.filepath)
        #if self.session._write_ins: _ = hp_basic.copy_file(self.filepath,self.session.inscopy_path)
        
        return 
    
    def check_data(self, objn_l):
        logger = self.logger.getChild('check_data')
        class_d = self.session.family_d[self.pclass_n] #get your class_d
        
        if self.session.bucket_size > len(objn_l):
            raise IOError
        
        #=======================================================================
        # check that each item in the pick list is in the binv
        #=======================================================================
        if not self.session._parlo_f: 
            
            #check that the names seection list is at least as large as the number of class items in there
            if not len(objn_l) <= len(class_d):
                raise IOError('got a pick list shorter than all the loaded \'%s\' objects'%self.pclass_n)
            
            
            #check that we can find all of these
            err = []
            for name in objn_l:
                obj = hp_dict.value_by_ksearch(name, class_d, logger=logger)
                
                if obj is None:
                    err.append('unable to find \'%s\' in the binv'%name)

                if not obj.__class__.__name__ == self.pclass_n:
                    err.append('for \'%s\' found object cn \'%s\' does not match my pick \'%s\''
                               %(name, obj.__class__.__name__, self.pclass_n))
                    
            #check and print out the errors
            if len(err) >0:
                for msg in err: logger.error(msg)
                raise IOError('got %i errors when scanning the passed selection list'%len(err))
            
            
        
        """doesn't work with names vs gid
        #check that all items in the binv are in the list
        bool_l = hp_basic.bool_list_in_list(class_d.keys(), objn_l , method='search')
        
        if not bool_l.sum() == len(class_d):
             #==================================================================
             # this is a counterintuitive inclusion test
             #    setup more for debugging.
             #    we are assuming that all entries in the loaded binv are included in the picker list
             #==================================================================
            logger.error('of the %i file objects, could not find %i in the class_d (%i)'
                         %(len(objn_l), np.count_nonzero(~bool_l), len(class_d)))
            
            logger.error('loaded objects: %s'%class_d.keys())
            logger.error('file objects:   %s'%objn_l)
            logger.error('%s'%self.filepath)
            
            raise IOError #should probably take this out"""
        #=======================================================================
        # check that all these object names are in the class d
        #=======================================================================

    
    def run_sel(self, **kwargs): #simulation placeholder
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        see ntoe at top
        Explicit: udev.Action.run

        """
        self.run_cnt += 1
        
        pick_d = self.calc_selection(**kwargs)
        
        self.get_results()

        return  pick_d
    
    def calc_selection(self, big_d = None, container=wdict): #perform the selection calculation based on the pars passed in the 'selectors' tab
        """
        #=======================================================================
        # EXPLICIT vs PERIODIC
        #=======================================================================
        Explicit: this can perform slicing autmoatically
        Periodic
            perofrms pick at given times across the whole set
            to pull slices from this, use slice_handler()
            
        #=======================================================================
        # INPUTS
        #=======================================================================
        big_d: larger set on which to perform the selection
            big_d = None: perform your selection on all session objects with your class name
        #=======================================================================
        # OUTPUTS
        #=======================================================================
        pick_d: d[obj.gid] = [picked object]
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('calc_selection')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not self.pclass_n in list(self.session.family_d.keys()): 
                logger.error('cound not find the picking class (%s) in the family library'%self.pclass_n)
                'TODO: figure out how to use selectors in outputters for pclass_n = an object with a Selector depednency'
                if self.pclass_n == 'Dmg_feat': 
                    logger.warning('check that the dmg_feats are enabled on the dfunc tab')
                raise IOError
            
            if not big_d is None:
                if len(big_d) == 0:
                    raise IOError
            
        #=======================================================================
        # setup
        #=======================================================================
        pick_d = container()
        
        #get the relevant class book
        if big_d is None:
            #logger.debug('no big_d passed. pulling straight from family_d for \'%s\''%self.pclass_n) 
            class_d = self.session.family_d[self.pclass_n] #get your class_d
        else:
            logger.debug('big_d passed with %i. checking for subset'%len(big_d))
            class_d = self.drop_subset(big_d) #make sure you have the right level from this subset
            
        """
        WARNING: class_d = d[obj.gid] = obj
        class_d.keys()
        """
        
        logger.debug('with class_d \'%s\': %i : %s'%(self.pclass_n, len(class_d), list(class_d.keys())))
    
        #=======================================================================
        # make selection by passed selector col
        #=======================================================================
        #=======================================================================
        # metadf_bool_exe by parents childmeta_df    
        #=======================================================================
        if not self.metadf_bool_exe is None:
            """ allowing dynmic now. see Dynamic_par.set_upddf_f()
            if not self.upd_sim_lvl == 0:
                logger.error("selection by metadf_bool is static. upd_sim_lvl must = 0")
                raise IOError"""
            
            #setup
            exe_str = str(self.metadf_bool_exe.replace(" ", "")) #make sure all the spaces are dropped
            method = 'metadf_bool'
            
            #get the parents childmeta_df
            'this assumes all of the children have the same parent'
            pparent_o = list(class_d.values())[0].parent
            
            if pparent_o.childmeta_df is None: raise IOError
            
            df = pparent_o.childmeta_df #get the frame
            
            #perform the selection
            try:
                boolidx = eval(exe_str) #evaluate the object
            except:
                logger.error('failed to eval \'%s\' from parent \'%s\''%(exe_str, pparent_o.name))
                raise IOError
            
            """
            np.logical_or(df.loc[:,'cat_code']=='M',df.loc[:,'cat_code']=='E')
            
            hp_pd.view_web_df(df)
            hp_pd.df_to_logger(df)
            """
            
            #get this slice (list of names)
            try: 
                pnames_l = df.loc[boolidx, 'name'].values.tolist()
            except:
                logger.debug('%s'%boolidx)
                logger.error('failed to apply boolidx')
                raise IOError
            
            #make a slice of the dictionary from this
            """the challenge here is we have a list of names but a dict of gids"""
            sub_d = hp_dict.subset(class_d, pnames_l, set_type = 'sub', method='search')
            
            #re key this 
            pick_d.update(hp_oop.convert_keys(sub_d, self.key_att, container=container, logger=logger))
            
            logger.debug('%s with \'%s\''%(method, exe_str))
                        
        #=======================================================================
        # obj_bool_exe--by object attribute selection
        #=======================================================================
        elif not self.obj_bool_exe is None:
            #expose local variables
            session = self.session
            
            #setup
            exe_str = self.obj_bool_exe
            method = 'obj_bool_exe \'%s\''%self.obj_bool_exe
            logger.debug('obj_bool_exe with \'%s\''%(exe_str))
            
            for gid, obj in class_d.items(): #loop through each object and ccheck
                #check if this fits the boolean
                try:
                    if eval(exe_str): 
                        pick_d[gid]= obj
                except:
                    raise IOError('failed to evaluate \'%s\''%exe_str)
                
                """
                for gid, obj in class_d.items():
                    print(gid, obj.fhz)
                obj.fhz
                """
                
            logger.debug('finished with %i picks'%len(pick_d))
            
        #=======================================================================
        # #pick by custom function (spcl_f_exe_str)
        #=======================================================================
        elif not self.spcl_f_exe_str is None:
            exe_str = self.spcl_f_exe_str
 
            method = 'spcl_f_exe_str'
            
            logger.debug('executing %s with \'%s\' \n'%(method, exe_str))
            
            pick_d.update(eval(self.spcl_f_exe_str))
            
        elif not self.headpath is None:
            logger.debug('from headpath: %s'%self.headpath)
            
            method = 'from file'
            
        #=======================================================================
        # no pars provided. pick everything
        #=======================================================================
        else: 
            pick_d.update(class_d.copy()) #
            method = 'everything'
            
        """messages from above
        logger.debug('during \'%s\' for calc_cnt %i found pick_d with %i entries by %s: %s'
                     %(self.session.state, self.run_cnt, len(pick_d), method, pick_d.keys()))"""
        
        #=======================================================================
        # checks
        #=======================================================================
        if self.db_f:

            if not isinstance(pick_d, container): 
                raise IOError
            
            if len(pick_d) == 0:
                
                #===============================================================
                # fancy search fail reporting
                #===============================================================
                if not self.obj_bool_exe is None:
                    #loop through some common search attributes and collec tthe data
                    d = dict()
                    for attn in ['fhz', 'cat_code', 'asector', 'acode_s', 'ayoc']:
                        #see if this obj_bool_exe is making some calcs on this att
                        if attn in self.obj_bool_exe:
                            d = dict()
                            for gid, obj in class_d.items(): #loop through each object and ccheck
                                d[gid] = getattr(obj, attn)

                            #report the results
                            logger.warning('failed search stats: \n%s'%pd.Series(d, name=attn).value_counts())

                logger.warning('at \'%s\' picked no \'%s\' objects with method \'%s\''%(self.get_id(), self.pclass_n, method))

            else:
                #check for teh approriate keying
                k1 = list(pick_d.values())[0]
                if not getattr(k1, self.key_att) == list(pick_d.keys())[0]:
                    raise IOError

        #=======================================================================
        # # wrap up
        #=======================================================================
        self.pick_d = copy.copy(container(pick_d)) #attach
        self.pick_k_ar = np.array(list(pick_d.keys()), dtype=object)

        return pick_d

    
    def ranked_choice(self, #selection from some ranked list
                      pick_cnt='udev', #number of entries to select from list
                      update=True, #whether to update the master list (remove recent picks)
                      stoch_f=None, #flag to allow stochastic bucket picking
                      obj_bool = 'obj.asector==\'sres\'', #extra filter boolean string to execute 
                      #pretty bad workaround to add an additional filter...
                      #would be better to support chain selectors
                      ): 
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        ranked_l: this should be a ranked list of object names loaded from file
            each call with update=True should update this list
            
            the list is reset to None during recompile
            while self.data is restored to Og during recompile
        
        """
        #=======================================================================
        # Defaaults
        #=======================================================================
        logger = self.logger.getChild('ranked_choice')
        
        """dont think we are using this any more
        if update: 
            
            ''
            self.modified_f = True #need to flag my self for recompiling to reset the list"""
        
        #count    
        if pick_cnt == 'udev':
            
            pick_cnt = self.session.udev.infil_cnt + self.session.udev.infil_cnt_delta
            'not really using the infil cnt delta, but this would allow for changes in pick size over time'
            logger.debug('n=udev. pulling from session.udev.infil_cnt %s'%pick_cnt)
            
        
        
        #stochastity
        if stoch_f is None: stoch_f = self.session.glbl_stoch_f

        #=======================================================================
        # precheck
        #=======================================================================
        if self.db_f:
            if self.session.state == 'init': 
                raise IOError #can only be called expliclity
            else:
                #l_og = copy.copy(self.ranked_l)
                pass
            
            if not self.upd_sim_lvl == 'none':
                logger.error('expected None for upd_sim_lvl yet got %s'%self.upd_sim_lvl)
                raise IOError
            
            if self.data is None: 
                raise IOError
            
            if not isinstance(pick_cnt, int):
                raise IOError
            
            if pick_cnt < 1: 
                logger.error('got n<1')
                raise IOError
            
            if self.ranked_l is None: #must be the first run
                if not self.run_cnt == 1: 
                    raise IOError
                
            #check the obj bool caller
            if not obj_bool is None:
                if not isinstance(obj_bool, str):
                    raise IOError
                if not 'obj' in obj_bool:
                    raise IOError

        #=======================================================================
        # data setup
        #=======================================================================
        #ranked list of object names
        if self.ranked_l is None: #must be the first run            
            self.ranked_l = self.data #pull fron teh data
            
            self.reset_d['ranked_l'] = copy.copy(self.ranked_l) #set the initial
            
            logger.debug('for calc_cnt %i pulled teh ranked_l from data with %i entries'%(self.run_cnt, len(self.ranked_l)))
        
        #=======================================================================
        # data checks
        #=======================================================================
        if self.db_f:
            """20190504: had to fix this for some reason"""
            if pick_cnt > len(self.ranked_l):
                raise IOError('trying to pick more than we have in the list! (%i)'%len(self.ranked_l))
        #=======================================================================
        # list type
        #=======================================================================
        'could make this handle more selection types'
        #just use the list
        if self.model.bucket_size == 0:
            srch_l = self.ranked_l[:pick_cnt] #get a static copy of the ranked_l
            
            'shouldnt run out of picks...'

        #get a random pick from a bucket    
        elif self.model.bucket_size > 0:
            srch_l = self.get_random_pick_from_bucket(
                            self.ranked_l, 
                            pick_cnt + self.model.bucket_size, 
                            pick_cnt, 
                            stoch_f = stoch_f)
                        
        else: 
            raise IOError #unexpected KWARG for Udev.pick_type
        'otherwise were looping and updating'
            
        #dictionary of your class objects
        class_d = self.session.family_d[self.pclass_n] #get your class_d
        
        
        pick_d = wdict()
        #=======================================================================
        # sort through the rank andpick
        #=======================================================================
        for index, obj_n in enumerate(srch_l): #loop through the ranking
            #logger.debug('sorting for index=%i and n=%i'%(index, n))\
            #===================================================================
            # get this object from the class)d
            #===================================================================
            obj = hp_dict.value_by_ksearch(obj_n, class_d, logger=logger)
            
            if obj is None:
                logger.error('class_d keys: \n    %s'%list(class_d.keys()))
                'did you load enough houses?'
                raise IOError('\'%s\' no \'%s\' in %s_d (%i) (run_cnt=%i loop=%i pick_cnt=%i, pick_d=%i, bucket=%i)\n    did you load enough?'
                               % (self.name, obj_n, self.pclass_n, len(class_d), len(pick_d),self.model.bucket_size,
                                  self.run_cnt, index,pick_cnt,
                                  ))
                
            #===================================================================
            # check the secondary filter
            #===================================================================
            if not obj_bool is None:
                if not eval(obj_bool):
                    continue #dont add this one
                    
                
            #===================================================================
            # update hte pick
            #===================================================================
            pick_d[obj.gid] = obj
            #update the list
            if update: 
                self.ranked_l.remove(obj_n) #take this one out of the list
        
        #=======================================================================
        # wrap up
        #=======================================================================
        if self.db_f:
            if len(pick_d) == 0:
                logger.warning('made no picks')
                raise IOError
            
            #check we got as many as we wanted
            if obj_bool is None:
                if not len(pick_d) == pick_cnt:
                    raise IOError
            
            pick_nl = []
            for gid, obj in pick_d.items():
                pick_nl.append(obj.name)
                #print obj.name
                #for objec ttype
                if not obj.__class__.__name__ == self.pclass_n: 
                    logger.error('object \'%s\' class \'%s\' does not match my pclass \'%s\''
                                 %(gid,obj.__class__.__name__, self.pclass_n ))
                    raise IOError
                
                if obj.name in self.ranked_l:
                    raise IOError #check that the selected objects were removed from the list
                
            #check that all of our pickis ahve been remvoed from the ranked list
            if update:
                
                if np.any(np.isin(pick_nl, self.ranked_l)):
                    bool_l = np.isin(list(pick_d.keys()), self.ranked_l)
                    logger.error('failed to remove %i entries from teh ranked_l'%bool_l.sum())
                    raise IOError
                
            """
            pick_d.keys()
            self.model.reset_d.keys()
            self.model.reset_d['bucket_size']
            """


        logger.info('finished w/ pick_d (%i), bucket_size = %i, update = %s, and pclass_n = \'%s\''
                     %(len(pick_d), self.model.bucket_size, update, self.pclass_n))
        
        #self.ranked_l = l #re attach the updated list
                
        return pick_d
        
    
    def get_random_pick_from_bucket(self, #generate a random sample from a bucket built from a passed list
                             full_l, #ranked list of objects used to construct bucket from
                             bucket_size, #int for size of bucket to build from full_l
                             pick_cnt,  #int for count to randomly select from bucket
                             stoch_f = True, #flag to allow stochastic bucket picks
                             ): 
          
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_random_pick_from_bucket')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if pick_cnt > len(full_l): raise IOError
            if pick_cnt > bucket_size: raise IOError
            
        #=======================================================================
        # shortcuts
        #=======================================================================
        """while this works in some sense, its nice to randomize the order
        this keeps it consistent with bucket picking as the user would expect
        #if pick_cnt == bucket_size: return full_l[:bucket_size]"""
        
        #=======================================================================
        # build bucket
        #=======================================================================
        if bucket_size >= len(full_l):
            bucket_l = full_l
        else:
            bucket_l = full_l[:bucket_size]
        
        #=======================================================================
        # deterministic pick
        #=======================================================================
        if self.session.sensi_f or (not stoch_f):
            'todo, handle the sensi_f better'
            """
            really, buckets are meant for random picking.
            but when testing, we want a bigger sample then just the top
            so we take half (+1) from teh top and half from the bottom of the bucket
            """
            logger.debug('making DETERMINSITIC pick of %i from bucket of %i'%(pick_cnt, bucket_size))
            
            if pick_cnt == 1:
                pick_l = bucket_l[:pick_cnt]
            else:
                #top of the bucket
                pick_lt = bucket_l[:(pick_cnt/2 + pick_cnt%2)]
                
                #bottom of the bucket
                pick_lb = bucket_l[-(pick_cnt/2):]
                
                pick_l = pick_lt + pick_lb
            

        #=======================================================================
        # random pick
        #=======================================================================5
        else:

            logger.debug('making random pick of %i from bucket of %i'%(pick_cnt, bucket_size))
         
            pick_l = random.sample(bucket_l, pick_cnt)
            
        if self.db_f:
            
            if not len(pick_l) == pick_cnt: 
                logger.error('FAIL len(pick_l) (%i) == pick_cnt (%i)'%(len(pick_l) , pick_cnt))
                raise IOError
        
        """
        self.session.lg_lvl
        
        logger.handlers
        logger.info('test')
        """

        return pick_l
              
    def reset_selector(self):
        raise IOError
        if self.write_pick_f:
            if not self.pick_file is None:
                self.pick_file.close()
                self.pick_file = None
            
        return 
            
    def get_results(self):
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        run_sel()
        """
        logger = self.logger.getChild('get_results')
        self.pick_cnt = len(self.pick_d)
        #self.pick_nl = self.pick_d.keys()
        
        
        if self.write_pick_f and self.session._write_data: 
            try:
                self.write_pick()
            except:
                logger.warning('failed to write_pick')
        
        """ moved this to the calc_selection
        self.pick_cnt = len(self.pick_d)"""
        
    def write_pick(self, 
                   out_prop = 'name', #what object property to write to file
                   ):
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        get_results
        
        #=======================================================================
        # TODO
        #=======================================================================
        'todo: make this more generic'
        consider dumping all picks into a spreadsheet at the end
        
        """
        
        logger = self.logger.getChild('write_pick')
        logger.debug('on pick_file \'%s\''%self.pick_file)
        first = False
        #=======================================================================
        # setup the file for the first time
        #=======================================================================
        if self.pick_file is None:
            self.outpath = os.path.join(self.session.outpath, '_sels')
            'not sure where this is getting dropped'
            #Periodic
            if not self.session.state == 'run':
                #get nice looking ty pe
                if self.upd_sim_lvl == 'none': type = 'exp'
                else: type = self.upd_sim_lvl
            #EXPLICIT
            else:
                type = self.session.state

                
            filename = '%s.%s.%s picks.csv'%(self.session.tag, self.name, type)
            self.pick_file = os.path.join(self.outpath, filename)
            
            #make the container folder
            if not os.path.exists(os.path.dirname(self.pick_file)):
                os.makedirs(os.path.dirname(self.pick_file))

                
            #self.pick_file =  open(filepath, 'a')
            logger.debug('pick_file is None. opened file at \'%s\''%self.pick_file)
            
            if self.db_f:
                if not os.path.exists(os.path.dirname(self.pick_file)):
                    logger.error('base dir does not exist: \'%s\''%self.pick_file)
                    raise IOError
            
            first = True
        
        #=======================================================================
        #append to the file
        #=======================================================================
        with open(self.pick_file, 'a') as f:
            if first:
                f.write('run_id, handler,')
                
                #add some numbers to the headers
                for cnt in range(0,len(self.pick_d),1):
                    f.write('%i,'%cnt)
                    
                f.write('\n') #star tteh next line
                    
            
            
            
            f.write('%s,'%self.get_id())
            #line indexer
            if not self.session.state == 'run': #Periodoic
                lindxer = '%s,'%self.handler.name
                
            else: #explicit
                lindxer = '%s,'%self.model.tstep_o.name
                
            f.write(lindxer)  
                
            #===================================================================
            # write hte data
            #===================================================================
            #standard gid
            if out_prop == 'gid':
                'this is the default method for Selectors to ensure unique entries'
                for gid in sorted(self.pick_d.keys()): #write the sorted list of pick keys
                    f.write('%s,'%gid)
                    
            #custom attribute
            else: 
                'allows writing name or bid'
                for gid, obj in self.pick_d.items():
                    v = getattr(obj, out_prop)
                    f.write('%s,'%v)
                    
                
            f.write('\n') #start a new li ne
        

        logger.debug('wrote pick to file for \'%s\''%lindxer)
        
        return           

        
        
        
        

class Sel_controller(object): #control functions for Selsector objects
    
    sels_d = None #collection of selector objects
    'generally belongs only to the Session'
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Sel_controller') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        super(Sel_controller, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        logger.debug("finish __init__")
        
    def raise_selectors(self, df):
        'usually only ran by the session'
        self.sels_d = self.raise_children_df(df, 
                                             kid_class = Selector)
        
    def run_selectors(self): #run teh recalc routine on all the selectors if flagged as so
        'see note at top'
        logger = self.logger.getChild('run_selectors')
        start = time.time()
        logger.info('\n at sim_lvl %i on sels_d (%i) sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel-sel'%
                     (self.sim_lvl, len(self.session.sels_d)))

        #=======================================================================
        # precheck
        #=======================================================================        
        if self.db_f:
            if self.session.sels_d is None:
                logger.error('no sels_d loaded')
                raise IOError
            
            if self.__class__.__name__ == 'Session':
                raise IOError #teh session should never call this... let the update happen during __init__
            
        
        upd_nl = [] #list of selector names that ahve updated
        for sel_n, sel_o in self.session.sels_d.items():
            
            if sel_o.upd_sim_lvl == 'none': continue #no updates for these
            
            """
            changed this so we only update at our level.. exclude those lower
            """
            if sel_o.upd_sim_lvl == self.sim_lvl:  #check by byat level of the session called you
                logger.debug('Selector \'%s\' is within the sim_lvl. running with old pick_d: %s \n'
                             %(sel_n, sel_o.pick_d))
                
                
                """
                unable to only update those SElectors whose selection changes
                    (does'nt capture objects changing outside the selection)
                    
                TODO: Consider a Session level dictionary that flags updates based on Object.__Class__.__name__
                    (copy fo the family_d)
                then teh selector can check to see if any objects of its selected class have changed before recalcing everything
                    
                
                
                changed my mind on this... wasn't really working.
                and seems like there will be lots of swapping between selections between timesteps
                if sel_o.upd_Simo_f: #check and see if anything you've subscribed to has changed
                    'WARNING: our updating is only INCLUSIVE. see note at top'"""
                    
                sel_o.handler = proxy(self) #tell teh selector who its handler is   
                sel_o.run_sel()
                
                """ moved this to within the run_sel to handle explicit selectors
                sel_o.get_results()"""
                
                upd_nl.append(sel_n)
                """ not flagging new selections for recompile as these are updated automiatically
                sel_o.modified_f = True"""
            else: logger.debug('Selector \'%s\' is outside the sim_lvl. not run'%sel_n)
                    
        stop = time.time()
        logger.info('finished in %.4f secs with %i (of %i) selectors updated: %s \n'
                     %(stop - start, len(upd_nl), len(self.session.sels_d), upd_nl))
        
        return 
            
            
            
            