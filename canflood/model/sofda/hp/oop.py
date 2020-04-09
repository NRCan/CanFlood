'''
Created on May 30, 2018

@author: cef

hp functiosn for basic object oriented programming in Pythong
'''
#===============================================================================
# PHILOSOPHIES ---------------------------------------------------------------
#===============================================================================
'''
#===============================================================================
# ATTRIBUTES
#===============================================================================
a child's attribute calculations should done by the child (NOT THE PARENT)

INHERITED 
only attributes with _SOMENAME will be passed down automatically to the children

#===============================================================================
# OBJECT PERMANENCE
#===============================================================================
all object references should be weak dictionaires
    or where ORderedDicts (or 1 offs) are erquired.. use proxies
    
family_d contains the only hard reference

This makes object deleteion/cleanup much simpler
    only need to remove reference in family_d (and close the frame)
    then gc.collect() will release the object from memory
    and all the wdicts will be updated

#===============================================================================
# WARNING
#===============================================================================
since there are some embedments of hte Basic_o, the import order now matters

this module must be imported before
    hp_data
    hp.plot
'''
# IMPORTS ----------------------------------------------------------------------
import logging
import os, sys, copy, gc, time, weakref, inspect
from collections import OrderedDict

from weakref import WeakValueDictionary as wdict
from hlpr.exceptions import Error




import pandas as pd
import numpy as np


import model.sofda.hp.basic as hp_basic
import model.sofda.hp.pd as hp_pd

import model.sofda.hp.prof_mem as hp_profMem






mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')

# FUNCTIONS --------------------------------------------------------------------

def att_delete(obj, att): #delte the passed attribute
    
    flag = None
    if hasattr(obj, att):
        
        try:
            delattr(obj, att)
            note = 'deleted attribute: %s'%att

        except:
            flag = 'FAILED to del attribute: %s'%att

    else:
        note = 'asset does not have attribute: %s'%att

    return flag, note
        
def att_list_delete(obj, att_list):
    flags, notes = [], []
    for att in att_list:
        flag, note = att_delete(obj,att)
    
        if not flag == None: flags.append(flag)
        if not note == None: notes.append(note)
        
    return flags, notes
        
def attach_att_df( #attacha df as attributes to an object
        obj, #object to attach attributes from the df to
        df,  #data to attach to the attribute
                  db_f = False,  #debugger flag
                  match_old = False,
                  logger=mod_logger): #attach parameters to object from passed df
    
    'this coould be simplified'
    """
    #===========================================================================
    # function
    #===========================================================================
    attach each value from teh secondc olumn of the df to the object
    has some format detection for lists and file paths
    """
    logger = logger.getChild("attach_att_df")
    
    l = []

    for _, row in df.iterrows(): #loop through each entry and attach it to the class object
        #=======================================================================
        # defaults
        #=======================================================================
        var_name = row[0]
        value_raw = row[2]
        
        #=======================================================================
        # pre check
        #=======================================================================
        if db_f:
            if not isinstance(var_name, str):
                raise Error('unexpected type')

        #=======================================================================
        # input  conversions            
        #check for false booleans
        if var_name.endswith('_f'): 
            if value_raw == 1.0 or value_raw == 0.0:
                """value_raw = 0.0"""
                value = np.bool(value_raw)
                
        else: 
            value = value_raw
            
        #=======================================================================
        # match old type
        #=======================================================================
        if match_old:
            oldval = getattr(obj, var_name)
            value = hp_basic.match_type(oldval, value_raw, logger=logger,  db_f = db_f)
        
        #=======================================================================
        # checks
        #=======================================================================
        if db_f:
            try:
                oldval = getattr(obj, var_name)
                
                if not isinstance(value, type(oldval)):
                    """
                    2019 05 04
                    getting a mismatch on ''delta_compare_col_nl''"""
                    logger.warning('for variable \'%s\' got type mismatch from old \'%s\' to new \'%s\''
                                   %(var_name, type(oldval), type(value)))
            except:
                logger.warning('\'%s\' object does not have attribute \'%s\''
                               %(obj.__class__.__name__, var_name))
                
            #===================================================================
            # unique ch eck
            #===================================================================
            if var_name in l:
                logger.warning('\'%s\' attached twice'%var_name)
                
            l.append(var_name)
            
        #=======================================================================
        # set the new value
        #=======================================================================

        setattr(obj, var_name, value)
        
        logger.debug('attaching parameter \'%s\' with value \'%s\' as %s'%(var_name, value, type(value)))
        
        
    
    logger.debug('general parameter values attached to object')
    
    return
    
def get_atts(obj, logger = mod_logger): #intelligently build dictionaries for the different attriburtes by type
    
    logger = logger.getChild('get_atts')
    
    att_call = dict() #dictionary of callable attributes (name; value)
    att_def = dict() #dictionary of default attributes
    att_std = dict() #standard attributes
    
    for att_name in dir(obj):
        att_value = getattr(obj, att_name)
        if att_name.startswith('__'): #make sure its not a default attribute
            att_def[att_name] = att_value

        elif callable(att_value):
            att_call[att_name] = att_value
            
        else:
            att_std[att_name] = att_value
            
    return att_std, att_call, att_def

def has_att_l(obj, att_nl, prfx_skip = '*', logger = mod_logger):
    logger = logger.getChild('has_att_l')
    
    for att_n_raw in att_nl:
        #prefix fix
        if att_n_raw[0] == prfx_skip: 
            att_n = att_n_raw[1:]
            
        else: att_n = att_n_raw
        
        if hasattr(obj, att_n): 
            continue
        else:
            #check for command style
            if att_n.endswith(')'):
                
                pos = att_n.index('(') #get the start of the command
                
                att_n = att_n[:pos] #get everything up to this
                
                if hasattr(obj, att_n): continue
            
            else: att_n = att_n_raw
            
            logger.debug('could not find att_n \'%s\' on obj \'%s\''%(att_n, obj.__class__.__name__))
            return False
        
    return True
         
        
        
        
         
     
     
     
def log_all_attributes(obj, log_callable = False, log_def = False, logger=mod_logger): #log each attribute

    logger = logger.getChild('log_all_attributes')

    #get teh attributes in buckets
    att_std, att_call, att_def  = get_atts(obj, logger = logger)
    
    for att_name, att_value in att_std.items():
        logger.debug('\'%s\' = \'%s\' (std)'%(att_name, att_value))
    
    if log_callable:
        for att_name, att_value in att_call.items():
            logger.debug('\'%s\' = \'%s\' (callable)'%(att_name, att_value))
            
    if log_def:
        for att_name, att_value in att_def.items():
            logger.debug('\'%s\' = \'%s\' (default)'%(att_name, att_value))
            
def attr_default_val(obj, att_name, dflt_val = 0, logger=mod_logger): #intelligent nan detection and overwrite with default value
    'this probably only works when dflt_val is numeric'
    logger = logger.getChild('attr_default_val')
    if hasattr(obj, att_name): #check if we have this
        att = getattr(obj, att_name) #get the attribute
        #if not att.isnumeric(): continue #
        if pd.isnull(att): #check if its nan
            setattr(obj, att_name, dflt_val) #set default
            logger.debug('set attribute \'%s\' to default value = %s'%(att_name, dflt_val))
            
def clean_l_atts(obj, search_sfx = '_l', logger=mod_logger): #clean all the attributes with '_l' suffix
    
    logger = logger.getChild('clean_l_atts')
    att_std, att_call, att_def = get_atts(obj, logger=logger) #get all the attributes
    
    cnt = 0
    
    for att_name, att_value in att_std.items():
        
        if isinstance(att_value, str):
            if att_name.endswith(search_sfx):
                value_l = hp_basic.str_to_list(att_value, logger=logger) #get the formatted value
                setattr(obj, att_name, value_l) #reset this value
                
                cnt += 1
                logger.debug('set \'%s\' to list with %i entries'%(att_name, len(value_l)))
                
    logger.debug("finished with %i mods"%cnt)
    
def copy_container_d(d, logger = mod_logger): #a semi deep copy of a container of objects
    'workaround for problems with deepcopy'
    logger = logger.getChild('copy_container_d')
    new_d = dict()
    
    logger.debug('on d with %i entries: %s'%(len(d), list(d.keys())))
    for k, v in d.items():
        
        if not hasattr(v, '__class__'): raise IOError
        
        copy_o = copy.copy(v)
        
        new_d[k] = copy_o
    
    logger.debug('finished')
    
    return new_d

def deepcopy_objs(#semi deep copy of a dictionary of objects
        d, #dictionary with objects to copy
        container = dict, 
        db_f = False,
        logger=mod_logger):
    """
    it looks like weakrefrecnging/proxies changed a bit in 3.7. 
        so i had to make some  tweaks here
    """
    #===========================================================================
    # setups and defaults
    #===========================================================================
    logger = logger.getChild('deepcopy_objs')
    
    #=======================================================================
    # prechecks
    #=======================================================================
    if db_f:
        for k, obj in d.items():
            if isinstance(obj, weakref.ProxyType):
                raise Error('trying to make a copy of a proxy!')
    
    #===========================================================================
    # loop and copy
    #===========================================================================
    new_d = container() #new container
    
    logger.debug("on %i objects"%len(d))
    for key, obj in d.items():
        obj_copy = copy.copy(obj) #set teh initial copy
        """this does a good job for everything other than comp ound objects
            dicts, lists, dfs, etc...
            which we need to make a deep copy of for simulation objects
            so we have true copies rather than just pointers
            so we can make changes to one object's compound attribute without changing the other"""
        
        
        #=======================================================================
        # loop over and make deep copies for compound objects
        #=======================================================================
        logger.debug('    setting copies of \"%s\'s (type %s) %i attributes'%(obj.__class__.__name__,type(obj), len(obj.__dict__)))
        for n, v in obj.__dict__.items():

            #weakref... no need to copy
            if isinstance(v, weakref.ProxyType):
                """what about weakvalue dictionaries ??.. setting deepcopys now"""
                #logger.debug('        ProxyType \'%s\'=\'%s\'   with type \'%s\'. skipping'%(n, v, type(v)))
                
            #deepcopy for compound objects
            elif hasattr(v, '__len__') and not isinstance(v, str):
                #logger.debug('        COMPOUND \'%s\'=\'%s\'   with type \'%s\'. setting deepcopy'%(n, v, type(v)))
                setattr(obj_copy, n, copy.deepcopy(v))
                
            #anything else.. no need to deepcopy
            else:
                pass
                #logger.debug('        SIMPLE \'%s\'=\'%s\'   with type \'%s\'. skipping'%(n, v, type(v)))
            

            
        new_d[key] = obj_copy #set this in teh dictionary
    
    #logger.debug("finished \n")
    return new_d

"""
for k, v in obj.dynk_lib.items():
    print(k, v, type(v))

len(obj.dynk_lib)

new_d = copy.deepcopy(obj.dynk_lib)

for k, v in new_d.items():
    print(k, v)

obj.dynk_lib['new'] = obj

copy2 = copy.copy(obj)

del copy2

obj.unit='not a window!'
obj_copy.unit

newd = dict()

for e in dir(newd):
    print(e)
obj_copy.session
#===============================================================================
# TESTING COPY BEHAVIOR
#===============================================================================
for attn, attv in obj.__dict__.items():
    cattv = getattr(obj_copy, attn) #pull the copyies attribut ehere
    mod_logger.info('\'%s\' \n     orig: %s (%s)\n     copy: %s (%s)'%(attn, attv,type(attv), cattv, type(cattv)))
    
    
obj.reset_func_od['newk']= 'newv'

attn = 'reset_func_od'
attv = getattr(obj, attn)

obj.reset_func_od.clear()


attn = 'depth'
setattr(obj, attn, 99)

obj_copy = copy.deepcopy(obj) #set teh initial copy



type(obj.session)

'%s'%getattr(obj, 'session')


obj.session
obj_copy.session

for k, v in d.items():
    print(k, v)
"""

        

def mirror_att( #attach an attribute (by name) from the parent onto the child (with some type logic)
                child, #object to pass new attribute to (from their .parent)
                att_n, #attribute name to pass
                parent=None,  #optional parent object
                match_self_type_f = True, #match the type of the attribute as it is now (on the child)
                db_f = None,
                logger=mod_logger):
    #===========================================================================
    # defaults
    #===========================================================================
    logger = logger.getChild('mirror_att')
    if parent is None: parent =child.parent
    if db_f is None: db_f = child.db_f
    cn = child.__class__.__name__
    #===========================================================================
    # precheck
    #===========================================================================
    if db_f:
        if match_self_type_f:
            if not hasattr(child, att_n):
                logger.error('match_self_type_f=TRUE but child \'%s\' doesnt have an attribute \'%s\''%
                             (child.name, att_n))
                
                raise IOError
            
            """ugly.. but for now were just going to ignore the type setting for None objects
            if getattr(child, att_n) is None:
                raise Error('match_self_type_f=True, but child \'%s\'s current \'%s\'attribute is None'%
                              (child.__class__.__name__, att_n))"""
            
        if not hasattr(parent, att_n): 
            logger.error('inherit failed. \'%s\' does not have attn \'%s\''%(parent.name, att_n))
            raise IOError
    
    
    #===========================================================================
    # pull value from parent
    #===========================================================================
    new_v_raw = getattr(parent, att_n)
    
    #=======================================================================
    # type matching
    #=======================================================================
    if match_self_type_f and (not getattr(child, att_n) is None): #skip for none old types
        #extract the old value
        old_v = getattr(child, att_n)
        
        #set its type onto the new_v
        try:
            new_v = type(old_v)(new_v_raw)
        except:
            raise Error('for \'%s.%s\' failed to set old value type \'%s\' \n     onto \'%s\' (current type=%s)'
                          %(cn, att_n, type(old_v), new_v_raw, type(new_v_raw)))
    else:
        new_v = new_v_raw
        

        

    setattr(child, att_n, new_v)
    logger.debug('\'%s\' inherited \'%s\' = \'%s\' from \'%s\' as %s'%(child.name, att_n, new_v, parent.name, type(new_v)))
    
    #===========================================================================
    # post check
    #===========================================================================
    if db_f:
        if new_v is None:
            logger.warning('for \'%s\' set None'%att_n)
    
    return True

        

def convert_keys(d, key_att, container = dict, logger=mod_logger): #take a dictionary and replace its keys with some object attirute
    
    new_d = container()
    
    for k, v in d.items():
        new_d[getattr(v, key_att)] = v
        
    return new_d
        
def log_referrers(obj, logger=mod_logger):
    logger=logger.getChild('log_referrers')
    gc.collect()
    cn = obj.__class__.__name__
    logger.info('passed object \'%s\' has %i refs'%(cn, sys.getrefcount(obj)))
    
    refs_l = gc.get_referrers(obj)

    for i, ref in enumerate(refs_l):
        logger.info('%i ref \'%s\''%(i, type(ref)))
        
        if hasattr(ref, 'keys'):
            for k, v in ref.items():
                logger.info('    %s:%s'%(k, v))
                
def get_slots(obj): #workaround to get all slots
    
    if not hasattr(obj, '__slots__'): return None
    
    fnd = OrderedDict() #best way to get a unique ordered list
    
    'skipping the last one as its always an object type'
    for cls in obj.__class__.__mro__[:-1]: #loop through all the baseclasses
        """these dont seem to be working
        if not isclass(cls): continue #skip the base object
        if isinstance(cls): continue"""
        try:
            v = getattr(cls, '__slots__')
            fnd[cls.__name__] = v
            #fnd.append(v)
        except:
            print(('fail on \'%s\''%cls))

        
        #print('from \'%s\' got these slots: %s'%(cls, att))
        
    return fnd

def get_slots_d(obj, logger = mod_logger): #get a dictionary filled with the slots and their values
    logger=logger.getChild('get_slots_d')
    d = dict()
    
    
    if not hasattr(obj, '__slots__'): return d
    
    'skipping the last one as its always an object type'
    for cls in obj.__class__.__mro__[:-1]: #loop through all the baseclasses
        """these dont seem to be working
        if not isclass(cls): continue #skip the base object
        if isinstance(cls): continue"""
        try:
            slots = getattr(cls, '__slots__')
            
            for attn in slots:
                d[attn] =  getattr(obj, attn) #store this in the dictionary
                

        except:
            logger.debug('failed to retrieve slots on \'%s\''%cls)
            
            
    return d
    
    
def check_match( #check attribute matching for hierarchical objects
        obj1, obj2, attn = 'acode'):
    
    #===========================================================================
    # special checkers
    #===========================================================================
    #acode comparison against a house
    if attn == 'acode' and obj2.__class__.__name__=='House':
        
        #get the house code
        if obj1.dmg_code == 'S':
            o2_av = obj2.acode_s
        elif obj1.dmg_code == 'C':
            o2_av = obj2.acode_c
        else:
            raise Error('unrecognized damage code')

    else:
        o2_av = getattr(obj2, attn)
        
    #===========================================================================
    # do the check
    #===========================================================================
    if not getattr(obj1, attn) == o2_av:
        raise Error('attv mismatch for \'%s\'  bettween \'%s\' (%s) and \'%s\' (%s)'
                      %(attn, obj1.name, getattr(obj1, attn), obj2.name, o2_av))
        
     
        
    
class Kid_condenser(): #collect all children in the tree matchin gthe pick_cn 
    """
    scans through the full hierarchy to collect any objects which match the class name
    """
    drop_loop_cnt = 0
    
    def __init__(self, 
                 d, #container of objects to scan {obj name: obj}
                 pick_cn, 
                 db_f = False, 
                 container = wdict,
                 key_att = 'gid', #attribute on which to key the picks
                 logger=mod_logger):

        
        self.logger = logger.getChild('Kcol')
        
        #=======================================================================
        # attach everything
        #=======================================================================
        self.d = copy.copy(d)
        self.pick_cn = pick_cn
        self.top_cn = list(self.d.values())[0].__class__.__name__ #class name of top level objects
        self.res_d = dict() #results dictionary
        self.db_f = db_f
        self.container = container
        self.key_att = key_att
        
        return
    
    def drop_all(self): #start the drop cascade
        logger = self.logger.getChild('drop_all')
        
        logger.debug('collecting all \'%s\' from  %i \'%s\' objs: \n    %s'
                     %(self.pick_cn, len(self.d), self.top_cn,  list(self.d.keys())))
        

        
        'need this to start the drop with self'
        self.drop(self.d) #start hte cascade with the original
        
        logger.debug('finished with res_d (%i) on \'%s\''%(len(self.res_d), self.pick_cn))
        
        return self.container(self.res_d)
        
    def drop(self,d): #callabel for each level of the hierarchy
        logger = self.logger.getChild('drop')
        
        logger.debug("drop_loop_cnt = %i with d (%i) of \'%s\'"
                     %( self.drop_loop_cnt, len(d),list(d.values())[0].__class__.__name__))
        self.drop_loop_cnt += 1
        
        if self.db_f:
            if len(d) == 0:
                raise IOError
        
        #loop through each object and see if we are at the right level
        for _, obj in d.items():
            cn = obj.__class__.__name__
            if cn == self.pick_cn:
                self.res_d[getattr(obj, self.key_att)] = obj #add this object to the dictionary with the new name
                """
                logger.debug('added \'%s.%s\' bl %i object to res_d as \'%s\''
                             %(obj.parent.name, obj.name, obj.branch_level, getattr(obj, self.key_att)))"""
                #we are at the correct level just return the d
             
            else: #wrong level. need to drop again
                if len(obj.kids_d) > 0:
                    logger.debug('\'%s.%s\' bl %i too high. dropping down with %i kids \n'
                                 %(cn, obj.gid, obj.branch_level, len(obj.kids_d)))
                    
                    #trigger the update cascade on this objects children
                    self.drop(obj.kids_d)
                    
                else:
                    logger.debug('obj \'%s.%s\' has no kids. skipping'%(cn, obj.gid))
                    
                    #childless object logic check
                    if self.db_f:
                        if cn == 'Dfunc': 
                            if obj.dfunc_type == 'dfeats' and not obj.dummy_f: 
                                raise Error('dfunc \'%s.%s\' is a dfeat type but has no kids!'%(obj.parent.name, obj.name))
                
        logger.debug('finished  at %i on \'%s\' \n'%(self.drop_loop_cnt, cn))
        
        
        return

    
"""
import resource



"""
            
    
#===============================================================================
# starter class objects ------------------------------------------------------
#===============================================================================
#hp_profMem.Profile_wrapper
    
class Child(hp_profMem.Profile_wrapper):#foundational object 
    
    
    
    inherit_parent_ans = None  #list of attribute names to inherit
    """this one is a bit unique because for some instances we add to this BEFORE we execute this _init_"""
    db_f = False
    sib_cnt = 0
    
    def __init__(self,
                 parent,  
                 session, 
                 name = None,  #default name
                 att_d = None, #attribute dictionary to replace __dict__ with
                 att_ser = None, #attribute series to apply
                 shadow = False): #whether to raise this as a shadow child
        """there should be no spill over... Child is the end of the cascade
                 *vars, 
                 **kwargs):"""
                 
        #=======================================================================
        # defaults
        #=======================================================================
        logger = mod_logger.getChild('Child') #have to use this as our own logger hasnt loaded yet
        cn = self.__class__.__name__
        logger.debug('start Child.__init__ as \"%s.%s\''%(cn, name))
        
        self.sib_cnt    = 0
        
        """NO! if we are making deep copies, these attributes will remain constant
        while the objects are different
        self.rchk = random.random() #random checker value"""
        #=======================================================================
        # shrotcuts
        #=======================================================================
        if self.__class__.__name__ == 'Session':
            """ a better way to handle thsi would be to make a wrapper
                (for things need by teh Session and the Child obj)
                separate from the actual child obj"""
            'we dont treat the session as a normal object'
            #super(Child, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
            
            """need the pars to be loaded for thsi to work on the session any way
            self.set_debugger_mode()"""
            return
        

        #=======================================================================
        # clone setup
        #=======================================================================
        if not att_d is None:
            'WARNING: this erases all previous attributes'
            logger.debug('overwriting __dict__ from att_d (%i): %s'%(len(att_d), list(att_d.keys())))
            self.__dict__ = copy.copy(att_d) #shallow copy
            
            self.outpath             = os.getcwd() #should be overwritten thorugh inheritance
        
        #=======================================================================
        # non-clone setup
        #=======================================================================
        else: 
            self.session    = session  #should be a proxy already
            
            
            self.parent     = weakref.proxy(parent)
            
            self.set_debugger_mode()
            
            self.branch_level = self.parent.branch_level +1

        #=======================================================================
        # unique setup
        #=======================================================================
        """just use session values for these.
        keeping this in fo rnow"""
        try:
            if self.inherit_parent_ans is None: 
                self.inherit_parent_ans = set()
        except:
            self.inherit_parent_ans = set()

        self.inherit_parent_ans.update(['outpath'])
        
        
        self.shdw_f = shadow
        
        """its ok if this is shared by all
        self.inherit_parent_ans = set()"""
        
        #name setup
        if name is None:
            self.set_name(att_ser = att_ser)
        else: 
            logger.debug('using passed name \'%s\''%name)
            self.name = name
        
 
        # standard inherits
        logger.debug('inherit_logr() from \'%s\' to \'%s\''%(parent.name, self.name))
        self.inherit_logr(parent)
        """ having parents handle this 
        logger.debug('inherit_family() \n')
        self.inherit_family(parent)"""
        logger.debug("init_clone")
        self.init_clone(parent, shadow=shadow)
        #=======================================================================
        # att_ser
        #=======================================================================
        if not att_ser is None:
            logger.debug('got an att_ser with %i. executing attach_att_ser() \n'%len(att_ser))
            self.attach_att_ser(att_ser) #attach/load all the attributes from the passed series
            self.dfloc = att_ser.name
            
        #=======================================================================
        # customizeable inherits
        #=======================================================================
        """ keep everythign explicit
        #inheritance commands
        if self.inher_func_s is None: self.inher_func_s = set()
        'classes should '"""
        #=======================================================================
        # uniques
        #=======================================================================
        if self.sib_cnt == 0: #skippinga ll these for siblings
            self.inherit_from_pset()
            """ keep everything explicit
            self.inher_func_s.add(self.inherit_from_pset)
            self.inher_func_s.add('self.parent.delete_kids_d(self)')"""
            
        """ keep everything explicit?
        logger.debug('executing inherit()\n')
        if len(self.inher_func_s) > 0: self.inherit()"""
        
        
        if self.db_f:
            if self.parent is None: raise IOError
            if self.session is None: raise IOError

        logger.debug('finish Child.__init__ as \"%s.%s\''%(cn, name))
        """
        #=======================================================================
        # WARNING
        #=======================================================================
        Make sure this _init_ is the last in the cascade
        """
        return

    def init_clone(self, #birthing of a clone (or original)
                   parent, 
                   shadow=False): 
        """
        because when we clone an object, we only want certain functions re-triggered (to activate)
        this should also be run on the first time an object is initilzied
        
        new parent ref, new gid, added to family_lib, add yourself to parent.kids_d and execute any post commands
        """
        
        self.parent     = weakref.proxy(parent)
        
        #update the session
        self.session.spawn_cnt += 1
        self.spawn_cnt = int(self.session.spawn_cnt) #low memory unique ID
        
        #=======================================================================
        # set unique ID
        #=======================================================================
        self.gid = str('%02d_%05d_%s.%s'
                       %(self.branch_level, self.session.spawn_cnt, self.parent.name, self.name))
        

        
        #=======================================================================
        # #update the family _d with yourself
        #=======================================================================
        self.session.upd_family_d(self, shadow=shadow)
        
        parent.adopt_child(self) #add yourself to parent.kids_d and execute any post commands

        #=======================================================================
        # halt any updates
        #=======================================================================
        if not self.session.state == 'init':
            if hasattr(self, 'halt_update'): 
                self.halt_update()
        

        return

        
    def set_debugger_mode(self): #load debugger flag from pars file
        
        """not doing this for the session
        
        not very elegant....
        """
        cn = self.__class__.__name__
        logger = mod_logger.getChild('%s.set_debugger_mode'%cn) #have to use this as our own logger hasnt loaded yet
        #=======================================================================
        # load from the obj par tab
        #=======================================================================
        try:
            df = self.session.pars_df_d['obj_test']
            try: 
                boolidx = df.loc[:, 'name'] == cn
                if boolidx.sum() == 1:
                    self.db_f = bool(df.loc[boolidx, 'db_f'].values) #pull yourself out
                else: 
                    raise IOError
                
            except: 
                logger.warning('failed to load \'%s\' from the obj_test pars'%cn)
                raise IOError #bump it to the except statement
        except:
            if not cn in df['name'].values:
                logger.warning('\'%s\' is not specified on the \'obj_test\' tab'%cn) 
            else:
                raise Error('failed to get the obj_test pars')
            #raise IOError

        #=======================================================================
        # conntrol by sessions master flag
        #=======================================================================
        'this has to go very early for the flags lower down to set properly'
        if self.session._dbgmstr == 'any':      pass #leave itas is
        elif self.session._dbgmstr == 'all':    self.db_f = True
        elif self.session._dbgmstr == 'none':    self.db_f = False
        else: 
            raise IOError
        
        logger.debug('set db_f as \'%s\''%self.db_f)
        
        return
        
        
    def set_name(self, #set the name logic
                 att_ser = None, default_name = 'somename', parent=None):
        """
        Ive split this out to keep all the name logic in once place... and the special logger
        #=======================================================================
        # LOGGER
        #=======================================================================
        WARNING: normal has not been initilzied yet (need the name for this)
        
        WARNING: parent and logger has not been inherited yet
        """
        
        
        #=======================================================================
        # get the object from teh passed kwargs
        #=======================================================================
        """this seems unecessarily complicated. the name is applied with the following priority
            att_ser
            name kwarg
            default 
        """
        logger = mod_logger.getChild('set_name') #have to use this as our own logger hasnt loaded yet
        
        #=======================================================================
        # pull from self
        #=======================================================================
        if att_ser is None:
            logger.debug("no att_ser passed. using class default \'%s\'"%self.name)
            name = self.name
        
        #=======================================================================
        # pull from att_ser
        #=======================================================================
        else:
            try:
                name = att_ser['name']
                logger.debug("using name from passed att_ser")
            except:
                #get from the att_ser
                if not hp_pd.isser(att_ser): #quick type check
                    logger.error('got unepxected type on att_ser: %s'%type(att_ser))
                    raise IOError
            
                if not 'name' in att_ser.index.values: 
                    logger.debug('could not find \'name\' in the series index: %s'%att_ser.index.values)

          
        #get from teh kwarg
        if name is None:  
            default_name = 'somename'
            logger.debug('just using default name \'%s\''%default_name)

        #=======================================================================
        # name checks
        #=======================================================================
        if self.db_f:
            
            if name is None: raise IOError
            
            'might be able to move these to Data_o to speed things up'
            if hp_basic.isnum(name): 
                logger.error('got numeric type for name %s'%att_ser['name'])
                raise IOError
            
            if not isinstance(name, str): raise IOError
            
            if '.' in name:
                logger.warning('found . in \'%s\'. this may be a dx col. check the datadims in teh pars'%att_ser['name'])
                raise IOError
            
            #===================================================================
            # parent checks
            #===================================================================
            if parent is None: parent = self.parent
                
            if name == parent.name:
                raise IOError
            
            if name in list(parent.kids_d.keys()):
                logger.error('found my name \'%s\' in parent \'%s\' kids_d'%(name, parent.name))
            
        self.name = str(name)

        return 

            

        
    
    def inherit_logr(self, parent=None):
        if parent is None: parent = self.parent
        self.logger         = parent.logger.getChild(self.name)
        #=======================================================================
        # logger and debugging
        #=======================================================================
        if self.db_f:
            self.logger.setLevel(logging.DEBUG) #set the base level for the logger
        else:
            'this should stop log entries made with logger.debug'
            self.logger.setLevel(logging.INFO) #set the base level for the logger
           
        logger = self.logger.getChild('inherit_logr') 
        logger.debug('from parent \'%s\''%parent.name)
        
        return
        

        

        
    def inherit_from_pset(self, parent=None, inher_set = None):
        
        #=======================================================================
        # setups and defaults
        #=======================================================================
        if parent is None: parent = self.parent
        
        logger = self.logger.getChild('inherit_from_pset')
        """ moved this to the family_d update
        self.branch_level  = parent.branch_level +1""" 

        #get the set
        if inher_set is None:  inher_set = self.inherit_parent_ans


        #===================================================================
        # loop through and inherit each
        #===================================================================
        'inher_set is combined with spc_s by __init__'
        logger.debug('from \'%s\' on %i entries in the s: %s'
                     %(parent.name, len(inher_set), list(inher_set)))

        
        sucs = True
        for attn in inher_set:
            
            #===================================================================
            # pull and set
            #===================================================================
            try:
                setattr(self, attn, getattr(parent, attn))

            except:
                if not hasattr(parent, attn):
                    logger.warning('parent \'%s\' does not have attn \'%s\''%(parent.name, attn))
                    sucs = False
                else:
                    raise IOError
                
            #===================================================================
            # post check
            #===================================================================
            if self.db_f:
                oldval = getattr(self, attn)
                v = getattr(parent, attn)
                logger.debug('    from parent \'%s\' set \'%s\' = \'%s\''%(parent.name, attn, v))
                if v is None:
                    logger.warning('    for \'%s\' set None'%attn)
                    
                if not isinstance(v, type(oldval)):
                    if not hasattr(v, '__class__'): #ignore setting of objects
                        logger.warning('    got type mismatch from old \'%s\' to new \'%s\''%(type(oldval), type(v)))
                    
                

                
        return sucs
                
                
            
                    
    def attach_att_ser(self,  #attach the passed series as attributes
                       att_ser_raw, 
                       #att_ser_skip_anl = None,
                       ):
        """
        This is the generic attribute builder
        for compiling custom attributes from this series, 
            create a custom function under the real child ('attach_atts')
            and add some post operations after calling this generic one
        """
        logger = self.logger.getChild('attach_att_ser')
        #=======================================================================
        # precheck
        #=======================================================================
        
        att_ser = att_ser_raw.dropna()
        
        #=======================================================================
        # loop and apply
        #=======================================================================
        for att_name, att_value in att_ser.items():

            #===================================================================
            # special value cleaning
            #===================================================================
            'consider adding the generic py string converter here'
            #if isinstance(att_value, basestring):
            """ removed this as id like to keep string none calls explicit
            if (att_value == 'None') or (att_value == 'none'): att_value = None
            
            """
            #===================================================================
            # else:
            #     
            #===================================================================
            try:
                setattr(self, att_name, att_value)
            except:

                raise Error('setting  \'%s\' =  %s failed'%(att_name, type(att_value)))
            
            
        
        
        #=======================================================================
        # small att_ser mods
        #=======================================================================
        """ custom attributes should go under load_data
        here we are only doing standard filepath concanations"""
        
        #=======================================================================
        # wrap up
        #=======================================================================
        logger.debug('attached %i attributes to \'%s\': %s'%(len(att_ser), self.name, att_ser.index.tolist()))
        return
    

 

    
    def write_named_atts(self, #extract and write these attributes from teh child (one file per attribute)
                      att_name_l, wtf = None): 
        """
        TODO: combine this with the above
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if att_name_l is None: return None
        if wtf is None: wtf = self.session._write_data
        if not isinstance(att_name_l, list): att_name_l = [att_name_l]
        logger = self.logger.getChild('write_named_atts')
        logger.debug('writing a datafile for %i attributes: %s'%(len(att_name_l), att_name_l))
        #get teh child        
        att_d = dict() #starter dict for writing
    
        for att_name in att_name_l:
            #===================================================================
            # checks
            #===================================================================
            if not isinstance(att_name, str): 
                raise IOError
            if not hasattr(self, att_name): 
                logger.error('\'%s\' does not have att \'%s\''%(self.name, att_name))
                raise IOError
            
            #===================================================================
            # get store and write hte attribute
            #===================================================================
            att_value = getattr(self, att_name)
            
            att_d[att_name] = copy.deepcopy(att_value) #attach a copy of this to the dinctionary
            
            if wtf: self.data_writer(data = att_value, filename = att_name) #write this
        
        logger.debug('bundled and wrote %i attributes'%len(list(att_d.keys())))
        
        return att_d

    def get_self(self): return self #useful for proxies
    
    
    def check_atts(self, #check the validity of some expected attributes 
                   exp_atts_d = None, #container of expected attributes {att name : py type}
                   ):
        
        log = self.logger.getChild('check_atts')
        
        if exp_atts_d is None:
            exp_atts_d = self.exp_atts_d
            
        if not isinstance(exp_atts_d, dict):
            raise Error('expected attributes container is not a dict')
        
        log.debug('checking %i attributes \n    %s'%(len(exp_atts_d), list(exp_atts_d.keys())))
        
        for attn, exp_ptype in exp_atts_d.items():
            if not hasattr(self, attn):
                raise Error('I dont have the expected attribute \'%s\''%attn)
            
            attv = getattr(self, attn)
            
            if not isinstance(attv, exp_ptype):
                raise Error('attribute \'%s\' expected \'%s\', instead got \'%s\''%
                              (attn, exp_ptype, type(attv)))
                
            #check the set value validity (by type)
            if attv is None:
                raise Error('att \"%s\' is still none'%attn)
            
            if isinstance(attv, float):
                if pd.isnull(attv):
                    raise Error('att \"%s\' loaded as null'%(attn))
                
            elif isinstance(attv, str):
                if attv == '':
                    raise Error('att \"%s\' is blank'%attn)
                
            elif isinstance(attv, int):
                if pd.isnull(attv):
                    raise Error('att \"%s\' loaded as null'%(attn))
                
            elif isinstance(attv, bool):
                pass #dont really have a check here...
            
        return
                
                
        
    

        
        
class Parent(object): #wrapper for raising child
    
    """ 
    #===========================================================================
    # kids_d
    #===========================================================================
    Each data object has a unique copy of this
        key: dataname of child object
        value: child data object
    """
    att_ser_skip_anl = None
    #===========================================================================
    # Program Pars
    #===========================================================================
    """
    raise_kids_f        = True #flag whether to spawn a child. queried on self.
    raise_in_spawn_f    = False #spawn the next generation during spawn_child (vs raise_chidlren)"""
    #===========================================================================
    # user pars
    #===========================================================================
    kid_class       = None #class object for the child of this
    childmeta_df    = None #dataframe of metadata for the children. see raise_children_df()
    
    
    """
    Dato_builder is a unique attribute:
        when passed in a pars .xls, it is intended to be applied to that object 
            (when loaded from teh data)
        when assigned to a py script, it is intended to be applied to that objects CHILDREN
    """
    
    #===========================================================================
    # calculated pars
    #===========================================================================
    kids_d          = None #dictionary to house child objects
    post_init_func_od   = None #ordered dictionary of command sto execute during spawn_child (after _init_)
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Parent')
        logger.debug('start _init_ on \'%s\''%self.__class__.__name__)

        super(Parent, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        

        #=======================================================================
        # unique attributes
        #=======================================================================
        
        self.kids_d = wdict()
        self.post_init_func_od = OrderedDict()
        'we need to be at the bottom of the cascade to avoid overwriting on this'
        """calling this every tiem in spawn_child
        self.post_init_func_od[self.update_kids_d] =  'Parent'"""
        
        #=======================================================================
        # common atts
        #=======================================================================
        if self.sib_cnt == 0:
            if self.kid_class is None:
                self.kid_class = Child #set the default
                logger.debug('setting kid_class = \'%s\''%self.kid_class)
                
            #set defaults for skipping attributes to loadf rom data
            if self.att_ser_skip_anl is None: 
                self.att_ser_skip_anl = set(['desc', 'Dato_builder', 'import_str'])

        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not inspect.isclass(self.kid_class): 
                raise IOError

        self.logger.debug("finished __init__ as \'%s\'"%self.__class__.__name__)
        return
        

    def update_childmeta(self, obj, method = 'add'): #add the passed object to your metadata
        logger = self.logger.getChild('add_childmeta')
        
        df_raw = self.childmeta_df.copy()
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not obj.name in list(self.kids_d.keys()): 
                raise IOError
            """
            for e in self.kids_d.keys():
                print e
            """
            if method == 'delete':
                if not len(df_raw) == len(self.kids_d): 
                    raise IOError
        
        if method == 'add':
            #=======================================================================
            # fill the series
            #=======================================================================
            ser = pd.Series(index = df_raw.columns) #empty series with matching index
            
            for ind, entry in ser.items():
                #get from teh child
                v = getattr(obj, ind)
                
                #add to the series
                ser[ind] = v
                
            #=======================================================================
            # append to the frame
            #=======================================================================
            df = df_raw.append(ser, ignore_index=True)
            
            #=======================================================================
            # set the dfloc
            #=======================================================================
            boolidx = df.loc[:,'name'] == obj.name
            obj.dfloc = int(df.index[boolidx].values)
            
            #=======================================================================
            # wraup up
            #=======================================================================
            self.childmeta_df = df #set the copy
            
            logger.debug('for \'%s\' appended series (%i) to end of my childmeta_df %s'%
                         (obj.name, len(ser), str(df.shape)))
            
            """
            hp_pd.v(df)
            hp_pd.v(df_raw)
            """
        elif method == 'delete':
            self.childmeta_df.drop(index=obj.dfloc, inplace=True)
            
            logger.debug("dropped \'%s\' from my metadata"%obj.dfloc)
            
        
        
        
        return
        
        
        
    
    def raise_children(self): #raise the children intelligently
        raise IOError
        """
        this is really just a wrapper around the raise_children_df
        
        this can be overwritten by custom images for custom child raising routines
        we should probably combine raise_children and grow_tree better
        
        #=======================================================================
        # USE
        #=======================================================================
        This should be the default for a generic Dato spawned with raise_kids_f = True
        
        If you already have your childmeta_df, just run raise_children_df() directly
        
        For special loading functions, define a new raise_children() within the custom image
            then when raise_chidlren_df runs it will trigger that custom function
        
        #=======================================================================
        # KNOWN ISSUES
        #=======================================================================
        some custom images require data from other trees to initilzie
        
        workaround: place the binv at the bottom of the data tab
            
        better solution:
            add 'rank' column to the data tab
            rather than propagate one tree completely, then move to the next
                propagate one level (across all trees) then move tot he next
                

        """
        #=======================================================================
        # setup
        #=======================================================================
        logger = self.logger.getChild('raise_children')
        child_blvl = self.branch_level +1 #level of the child
        'i think this has to be a string to be read from teh excel tabs'
        logger.debug("raising children with raise_kids_f = %s and child blvl = %s"%(self.raise_kids_f, child_blvl))
        condition = []
        #=======================================================================
        # pre checks
        #=======================================================================
        if not self.raise_kids_f: 
            logger.debug("raise_kids_f = FALSE. doing nothing")
            return
        
        #=======================================================================
        # load the pars from the tree map
        #=======================================================================
        if not self.tree_map_filetail is None: #this object must be a trunk. make a new tree map
            logger.info('growing tree from map: %s'%self.tree_map_filetail)
            condition.append('loaded tree_map')
            self.treem_df_d = self.load_tree_map()
            
        #=======================================================================
        # load the childmeta data
        #=======================================================================
        if hp_pd.isdf(self.childmeta_df):
            logger.debug('already have childmet_df %s'%str(self.childmeta_df.shape))
            condition.append('using loaded childmeta_df')
        
        #check if you are in the tree map
        elif isinstance(self.treem_df_d, dict):
            if child_blvl in list(self.treem_df_d.keys()):
                logger.debug('child_blvl (%i) found in treem_df_d. extracting childmetadf from there'%child_blvl)
                condition.append('loaded childmeta_df from tree map')
                self.childmeta_df = self.treem_df_d[child_blvl]
            
        #automatic metadata for children
        else:
            logger.debug('no pars provided for this child (bl = %s). building from data'%child_blvl)
            self.childmeta_df = self.get_childmetadf()
            condition.append('build childmeta from data')
                    
        #===================================================================
        # raise the childeren
        #===================================================================
        if self.childmeta_df is None: raise IOError 
        new_kids_dict = self.raise_children_df(self.childmeta_df) #raise all the children according to this tree_map
        
        if self.db_f: 
            logger.debug('finished with %i new kids: %s'%(len(new_kids_dict), list(new_kids_dict.keys())))
            for msg in condition: logger.debug('    ' + msg)
        
        return new_kids_dict
    
    def raise_gkids_group(self, kid_colname, childmeta_df, #makes a slice of the meta_df and raises achild with that group
                               kid_class = None):
        
        """
        this is a lazy way to create a second generation from one frame
        identifies a slice from the childmetadf (by kid_colname), 
        and makes a dummy kid with data of tha tslice (no atts for that kid)
        then raises gkids under that kid using its data (each row is the grandkids atts)
        
        #=======================================================================
        # OUTPUTS
        #=======================================================================
        outputs a special dictionary
        
        twogen_gkids_d
            keys: child names
            values: that childs kids_d (a dictionary of grand children)
        """
        raise IOError
        logger = self.logger.getChild('raise_gkids_group')
        
        #=======================================================================
        # setup
        #=======================================================================
        twogen_gkids_d = dict()
        new_kids_d = dict()
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if len(childmeta_df) == 0:
            logger.warning('got empty childmeta_df')
            return new_kids_d
        
        if not kid_colname in childmeta_df.columns:
            raise IOError
        
        #get a list of the children
        kid_names = childmeta_df[kid_colname].unique()
        
        if np.any(pd.isnull(kid_names)): 
            raise IOError

        
        logger.debug('building %i kids and their (grand) kids: %s'%(len(kid_names), kid_names))
        
        for childname in kid_names: #loop through and build the dynamic pars for each class name
            # get a slice of the pars for this name
            boolidx = childmeta_df[kid_colname] == childname
            df_slice = childmeta_df[boolidx]
            logger.debug('loading \'%s\' with df %s'%(childname, str(df_slice.shape)))
            
            #spawn this child
            'remember this also stores the kid in the kids_d'
            child = self.spawn_child(att_ser = None, childdata=df_slice, 
                                     childname = childname, kid_class = kid_class)
            
            'by teh nature of this function, we want to raise grand kids'
            child.raise_kids_f = True
            
            gkids_d = child.raise_children_df(df_slice) #raise the grand kids from this slice
            
            twogen_gkids_d[childname] = gkids_d
            new_kids_d[childname] = child
            
            
        logger.debug('finished with %i twogen_gkids_d: %s'%(len(twogen_gkids_d), list(twogen_gkids_d.keys())))
        
        return new_kids_d
 
    def raise_children_df(self, #raise all the children from teh metadf and put them in the kids_d
                          df_raw,  #data set on which to rase a child for each line
                          kid_class = None, #class to spawn each child with
                          dup_sibs_f = False, #flag to duplicate attributes on siblings (improves efficenci
                          shadow = False, #whether to raise these children in the shadows
                          container = wdict, #container object to fill
                          attn_skip_l = 'inherit', #list of attribute names to slice out of the df and not pass to the child
                          **init_kwargs): 
        """
        This is the most common way to raise children: from a frame (one kid per row)
        
        This should be called by the __init__ of each object to trigger the cascade
                
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if self.db_f: start = time.time()
        logger = self.logger.getChild('raise_children_df')
        new_kids_d = container()
        logger.debug('with container \'%s\''%new_kids_d)
        #=======================================================================
        # pull sibling passing defaults from kid_class
        #=======================================================================
        """ do this in loop to get updated lists
        if not kid_class is None:
            if pass_anl is None:
                logger.debug('from passed kid_class \'%s\'. using spc_inherit_anl for pass_anl: %s'
                             %(kid_class, kid_class.inherit_sib_ans ))
                
                pass_anl = kid_class.inherit_sib_ans"""
            
        """ dont want to use this.. use __init__ insteadl
            if post_cmd_str_l is None:
                
                logger.debug('from passed kid_class \'%s\'. using spost_cmd_str_l: %s'
                             %(kid_class, kid_class.post_cmd_str_l ))
                
                post_cmd_str_l = kid_class.post_cmd_str_l"""
                
        #=======================================================================
        # df cleaning
        #=======================================================================
        df1 = df_raw.copy()
        #set sib_cnt
        if dup_sibs_f:
            logger.debug('dup_sibs_f = TRUE. setting sib_cnt as index')
            df1['sib_cnt'] = df_raw.reset_index(drop=True).index.astype(int) #integer ranking
        else:
            logger.debug('dup_sibs_f = FALSE. setting all sib_cnt = 0')
            df1['sib_cnt'] = 0 
            
        df2 = df1
        
        """moved to spawn child because we need some atts from teh df to spawn certain children
        #slice out exclusions
        if attn_skip_l == 'inherit':
            'probably not the best way to handle this'
            attn_skip_l = self.att_ser_skip_anl 
            
        if not attn_skip_l is None:
            boolcol = ~df1.columns.isin(attn_skip_l)
            df2 = df1.iloc[:,boolcol]
        else:
            df2 = df1
            """


        #=======================================================================
        # pre-checks
        #=======================================================================
        if self.db_f:
            start = time.time()

            if self.branch_level > 4: raise IOError
            
            if not hp_pd.isdf(df2):  raise IOError
            
            if not 'name' in df2.columns.values: 
                raise Error('passed df does not have a \'name\' column: %s'%df2.columns.values)
            
            if not hp_basic.isnum(self.branch_level): raise IOError
        
        #report
        logger.debug('from branch_lvl = %i with df %s \n'%(self.branch_level, str(df2.shape)))
        #=======================================================================
        # loop and build
        #======================================================================= 
        #setup counters
        pass_d = None
        first = True  
        cnt = 1
        
        for index, row in df2.iterrows(): #loop through the df
            #===================================================================
            # messaging
            #===================================================================
            if not first:
                if cnt%self.session._logstep ==0: logger.info('for \'%s\' on %i of %i'%(row['name'], cnt, len(df2)))
                
            logger.debug('spawning \'%s\' with sib_cnt=%i \n'%(row['name'], row['sib_cnt']))

            #===================================================================
            # #build the object
            #===================================================================
            'passing an att_d will erase all attributes. but anything in att_ser will override'
            child = self.spawn_child(att_ser = row, #series of attribute values to assign tot he child
                                        att_d = pass_d, #dictionary to set on child.__dict__
                                        childname = row['name'], #name to pass on to the child
                                        kid_class = kid_class, #class object to load teh child on
                                        shadow = shadow,
                                        attn_skip_l = attn_skip_l,
                                        **init_kwargs)
            #child.sib_cnt = cnt #tell the child where it lies amongst its siblings
            'this is useful for custom inherit calls'
            
            'self.kids_d is updated by generic_inherit'

            #===================================================================
            # special attribute handling for first chidl
            #===================================================================
            if first:
                self.kid_cn_s = child.__class__.__name__ #set this attribute
                if dup_sibs_f:
                    #get atts in the dict
                    pass_d = copy.copy(child.__dict__)
                    
                    """this is too tricky
                    #add slots
                    if hasattr(child, '__slots__'):
                        pass_d.update(get_slots_d(child, logger=logger))"""

                    logger.debug('passing on %i attributes to the next sibiling'%(len(pass_d)))
                    first = False

 
            #===================================================================
            # wrap up loop
            #===================================================================
            new_kids_d[child.name] = child #add thsi to teh dictionary
            cnt += 1
            
        #=======================================================================
        # spawn the grand children
        #=======================================================================
            
        #=======================================================================
        # wrap up/ post check
        #=======================================================================
        if self.db_f:
            stop = time.time()
            logger.debug('finish %.4f s (%.4f/obj) built %i from df:\n %s'
                         %(stop - start, float((stop-start) / float(cnt)), len(new_kids_d), list(new_kids_d.keys())))
            #logger.debug('\n') 
            
            #===================================================================
            # checks
            #===================================================================
            if not len(new_kids_d) == len(df2): 
                raise IOError
            'in some cases, we may use thsi to raise multiple chidl sets'
            if not len(self.kids_d) >= len(df2):
                raise IOError
            
        else:
            logger.debug('built %i child objects from the df \n'%(len(new_kids_d))) 

              
        return new_kids_d
    
    def spawn_child(self,  #create a child from teh passed data
                    att_ser = None, #series of attribute values to assign tot he child
                    att_d = None, #dictionary to set on child.__dict__
                    childname = None, #name to pass on to the child
                    kid_class = None, #class object to load teh child on
                    shadow = False, #whether to raise this as a shadow child or not
                    attn_skip_l = 'inherit', #list of attribute names to not pass down to the child
                    #post_cmd_str_l = None, #list of commands to execute on the child after __init__
                    **init_kwargs): #special kwargs to pass to the childs __init__
        
        """
        this is hte main function for spawning a child
        #=======================================================================
        # USE
        #=======================================================================

        #=======================================================================
        # WARNING
        #=======================================================================
        This is a frequently called function, try to make as skinny as possible
        
        att_ser is always created and passed to the Dato
        """
         
        #=======================================================================
        # defaults
        #=======================================================================
        """ kids_d is updated by generic_inherit
        if self.kids_d is None: self.kids_d = dict()"""
        start = time.time()
        logger = self.logger.getChild('spawn_child')
                
        logger.debug('with att_ser %s, childname \'%s\', kid_class \'%s\''
                     %(type(att_ser), childname, kid_class))
        #=======================================================================
        # get the class with which to raise the child
        #=======================================================================
        if not kid_class is None: #intelligent load
            logger.debug('loading from passed kid_class (%s). executing __init__ \n'%kid_class.__name__) #passed loader

        else:
            #laod from pars
            """2019 05 04: this is super gross"""
            if not att_ser is None: #there is an att_ser
                if 'Dato_builder' in att_ser.index.values: 
                    if not pd.isnull(att_ser['Dato_builder']):
                        try:
                            exec(att_ser['import_str'])
                        except:
                            raise Error('user requested module \'%s\' not recognized'%att_ser['import_str'])
                            
                            
                        kid_class = eval(att_ser['Dato_builder']) #use custom 
                        logger.debug('kid_class from df Dato_builder \'%s\'. executing __init__ \n'%kid_class)
        
        
            #load from parent                
            if kid_class is None: 
                'this should just pull the default'
                kid_class = self.kid_class   
                logger.debug('loaded kid_class from self (%s). executing __init__ \n'%kid_class.__name__)

        #final check
        if self.db_f:
            if not inspect.isclass(kid_class): 
                logger.error('passed kid_class is not a class')
                raise IOError 
            
            if not isinstance(self.session, weakref.ProxyType):
                raise Error('Session is not a proxy!')
            
        #=======================================================================
        # clean the att_ser
        #=======================================================================     
        if isinstance(att_ser, pd.Series):
            if attn_skip_l == 'inherit':
                'probably not the best way to handle this'
                attn_skip_l = self.att_ser_skip_anl 
            
            if not attn_skip_l is None:
                att_ser = att_ser.drop(attn_skip_l, errors='ignore')

        #=======================================================================
        # spawn the chidl
        #=======================================================================
        """
        logger.debug('_init_ on \'%s\' with name \'%s\' att_ser \'%s\', data\'%s\', \n'
                     %(kid_class, childname, type(att_ser), type(childdata)))"""
                     
        """
        type(self.session.__repr__())
        """
        
        child = kid_class(self, 
                          self.session,  #should be a proxy already
                          name = childname, 
                          att_d = att_d, 
                          att_ser = att_ser,
                          shadow = shadow, 
                          **init_kwargs)
        #child = kid_class(self, self.session, att_ser = att_ser, data = childdata, name = childname, **kwargs)
        """"leave all special attributes and loaders to __ini__ or raise_children()
        this child is added tot he kids_d by self.generic_inherit()
            this allows the child to be reassigned to a different parent
        """
        
        
        #=======================================================================
        # wrap up
        #=======================================================================  
        stop = time.time()  
        logger.debug('finished in  %.4f secs \n'%(stop - start))  
                
        return child
    
    def adopt_child(self, #activates the child under this parent (and all post_init commands)
                    child): 
        """moved this out so we can activate children without spawning them"""
        #logger = self.logger.getChild('adopt_child')
        #basic family structure
        #logger.debug('appending \'%s\' to kids_d (%i)'%(child.name, len(self.kids_d)))
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if self.kids_d is None:
                raise IOError #hast eh parent __init__ been executed?
        
            if not isinstance(self.kids_d, weakref.WeakValueDictionary):
                raise TypeError('local kids_d is not a weakref!. %s'%type(self.kids_d))
        
        #=======================================================================
        # add the kid to your local family tree
        #=======================================================================
        self.kids_d[child.name] = child
        """should the children be weakrefs?"""
        #=======================================================================
        # execute secondary init functions
        #=======================================================================
        if len(self.post_init_func_od)> 0:
            #logger.debug('executing %i funcs from post_init_func_od \n'%len(self.post_init_func_od))
            for func, caller in self.post_init_func_od.items():
                #logger.debug('executing \'%s\' queued by \'%s\' \n'%(func, caller))
                result = func(child, method='add')
                

            
        return
    
    def set_child_atts_df(self, #attach a df by key to each child
                      df_raw, #data with obj_key to attach to kids
                      kids_d = None, #container of kidss to attach data to
                      df_key = None, 
                      obj_key = 'name', 
                      ser_nm=None,  #if None: attach each entry individually.  otherwise, attach as a series with this name
                      **kwargs): 
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        ser_nm:
            None: attach each data item in the df_raw as individual items
            somename: attach the row from teh df as single attribute (series type with this name_)
        """
        
        #=======================================================================
        # defauilts
        #=======================================================================
        logger = self.logger.getChild('attach_att_df')
        
        if kids_d is None: kids_d = self.kids_d
        
        df = df_raw.copy(deep=True)
                
        logger.debug('on df with %s and kids_d %i \n'%(str(df.shape), len(kids_d)))
        
        #=======================================================================
        # setup
        #=======================================================================
        #find where teh bid column is for slicing later
        if not df_key is None: boolcol = df.columns != df_key #everything but the search
        else: boolcol = ~pd.Series(index = df.columns,dtype = bool) #all Trues
        
        #=======================================================================
        # prechecks
        #=======================================================================
        'todo: check for unique entires in the dictionary'
        
        #=======================================================================
        # loop and update
        #=======================================================================
        for oname, obj in kids_d.items(): #loop through each hosue and apply the new atts
            logger.debug('on \'%s\''%oname)
            #===================================================================
            # #data search
            #===================================================================
            #set the object indexer
            if obj_key == 'name': id_o = oname
            else: id_o = getattr(obj, obj_key) #pull the custom indexser
            
            #find your data from here
            if df_key is None: boolidx = df.index == id_o #index search
            else: boolidx = df.loc[:,df_key] == id_o #column search
            
            if self.db_f:
                if boolidx.sum()>1:
                    logger.error('for kid \'%s\' found multitiple (%i) matches'%(oname, boolidx.sum())) 
                    raise IOError
                
                elif boolidx.sum() == 0:
                    logger.error('for kid \'%s\' found NO matches'%oname)
                    raise IOError
            

            ser = df.loc[boolidx, boolcol].iloc[0] #get this data slice
            ser.name = id_o
            
               
            #===================================================================
            # data attach
            #===================================================================
            #attach each item individually
            if ser_nm is None: 
                obj.attach_att_ser(ser, **kwargs)
                
            #attach as a series
            else:
                setattr(obj, ser_nm, ser)
                logger.debug('attached series with %i entries to obj as \'%s\''%(len(ser), ser_nm))

            
            
        logger.debug('added data to %i children'%len(kids_d))
       
        return
    
    def get_kids_byname(self, search_name): #find the children in the kids_d with names matching
        
        found_d = dict()
        for childname, dato in self.kids_d.items():
            
            if search_name in childname: found_d[childname] = dato #append this
            
        return found_d
    
    def swap_kids(self, shdw_kids_d): #replace current kids with a shadow set
        
        """
        this is useful for makeing pure replacements during simualtion resets
            rather tahn updating a big group of children
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('swap_kids')
        """make more explicit
        if shdw_kids_d is None: shdw_kids_d = self.shdw_kids_d"""
        
        #=======================================================================
        # shortcuts
        #=======================================================================

            
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not len(shdw_kids_d) >0: 
                """if you dont have  shadows, dont call this
                otherwise, we miss catching errors on objects whwere we have forgotten to se the shdw_kids"""
                raise Error('no shadow kids!')
            if not len(self.kids_d) >0:
                """for dfuncs which are turned dummy mid simulation, we could allow this.
                but I dont think were doing that right now"""
                raise IOError
            

            
        logger.debug('from kids_d (%i) to shdw_kids_d (%i) \n'%(len(self.kids_d), len(shdw_kids_d)))
        #=======================================================================
        #make the swap
        #=======================================================================
        #logger.debug('kill_kids() \n')
        self.kill_kids()
        
        #clone the shadows
        'we want to preserve the shadow copy for future use'
        clones_d = copy_container_d(shdw_kids_d)
        
        logger.debug('activating %i clones \n'%(len(clones_d)))
        self.activate_kids(clones_d) #reintigrate the clones into the family
        
        #=======================================================================
        # wrap up;
        #=======================================================================
        if self.db_f:
            'alternatively we could sort things'
            #perform key check using array
            nk_ar = np.array(list(self.kids_d.keys()))
            sk_ar = np.array(list(shdw_kids_d.keys()))
            
            if not np.all(np.isin(nk_ar, sk_ar)):
                raise IOError
            
            if not len(self.kids_d) == len(clones_d):
                raise IOError                             

            
        logger.debug('finished with a new set of kids (%i): %s \n'%(len(self.kids_d), list(self.kids_d.keys())))
        
        return
    
    def activate_kids(self, new_kids_d): #bring a set of shadow children into the family structure
        logger = self.logger.getChild('activate_kids')
        
        logger.debug('on new_kids_d %i: %s'%(len(new_kids_d), list(new_kids_d.keys())))
                
        #=======================================================================
        # bring the new kids in
        #=======================================================================
        for key, child in new_kids_d.items():
            logger.debug('bringing in child \'%s\' as \'%s\''%(child.name, child.__class__.__name__))
            child.init_clone(self)
            """init_clone executes adopt_child
            self.adopt_child(child)"""

        #=======================================================================
        # wrap up
        #=======================================================================
        if self.db_f:
            
            #check that we have at least as many kids as we requested
            if not len(new_kids_d) <= len(self.kids_d):
                'some of the old kids seem to be holding on'
                raise IOError
            
            if not child.parent.__repr__() == self.__repr__(): raise IOError

        logger.debug('finished on (%i)/%i kids \n'%(len(new_kids_d), len(self.kids_d)))
        """
        self.kids_d.keys()
        for e in gc.get_referrers(self.kids_d['ADBS18']): 
            print e
        new_kids_d.keys()
        """
        
    def update_kids_d(self, obj, method='add'):
        """
        should not need to call this during _init_
        kids_d = WeakValueDictionary
            keys: using names. 
            a parents kids should not have duplicated child names
        
        """
        logger = self.logger.getChild('update_kids_d')
        
        if method == 'add':
            logger.debug('adding \'%s\' to my kids_d (%i)'%(obj.name, len(self.kids_d)))
            
            if self.db_f:
                if obj.name in list(self.kids_d.keys()): raise IOError
                
            #add to the container
            self.kids_d[obj.name] = obj
            
            """ shouldnt need this with proxies 
            #queue the kill command
            obj.kill_funcs_od[self.update_kids_d] = 'Parent'
           
            
        elif method == 'delete':
            logger.debug('deleteing \'%s\' from my kids_d (%i)'%(obj.name, len(self.kids_d)))
            try:
                del self.kids_d[obj.name]
            except:
                logger.error('failed to delete \"%s\' from my kids_d (%i)'%(obj.name, len(self.kids_d)))
                raise IOError"""
            
        else: raise IOError
        
        if self.db_f:
            if self.session.state == 'init': raise IOError
            
        return
  
    def kill_kids(self): #erase your kids_d
        """ setup for proxies"""
        logger = self.logger.getChild('kill_kids')
        """ why not do by names?
        d = copy.copy(self.kids_d) #get a copy to iterate over"""
        
        
        if not self.kids_d is None:
            kn_l = list(self.kids_d.keys())
            logger.debug('killing %i kids and resetting kids_d and kids_sd'%len(kn_l))
            
            #delete the object and its reference in the family _lib
            for kn in kn_l:  
                self.session.kill_obj(self.kids_d[kn])
                
            """objects probably not released yet
            if self.db_f:
                if len(self.kids_d) > 0: raise IOError
                if hasattr(self, 'kids_sd'):
                    if len(self.kids_d) >0 : raise IOError"""
            """this should be redundant
            #reset the containers
            self.kids_d = dict()
            if hasattr(self, 'kids_sd'): self.kids_sd = dict()
            
            for k, v in self.kids_d.items():
                print(k, v)
            
            
            """
            #gc.collect() #force garbage collection
            #===================================================================
            # post checks  
            #===================================================================
            if self.db_f:
                logger.debug('finished murdering kids')
                if len(self.kids_d) > 0:
                    raise Error('failed to kill %i kids'%len(self.kids_d))
                

            
        else:
            logger.debug('no kids to kill')
        
        return
    
    def check_family(self, #check each object in passed for consistency against your children
                     kids_d = None, #container of objects to check
                     d_is_all = True, #flag whether the passed container is ALL of your children
                     ): 
        """
        I dont really like this
        """
        cn = self.__class__.__name__
        #=======================================================================
        # defaults
        #=======================================================================
        if kids_d is None: 
            kids_d = self.kids_d
            d_is_all = False #no nseed to check
            
        #=======================================================================
        # parent checks
        #=======================================================================
        if not len(self.kids_d) >0 :
            raise Error('%s.%s has no kids!'%(cn, self.name))
    
        if not isinstance(self.childmeta_df, pd.DataFrame):
            raise IOError
        
        if not len(self.kids_d) == len(self.childmeta_df):
            raise IOError
        
        
            
        #=======================================================================
        # kid checks
        #=======================================================================
        for k, v in kids_d.items():
            
            if not v.parent.__repr__() == self.__repr__(): 
                raise IOError
            if not v.name in list(self.kids_d.keys()):
                raise IOError
            if not v.name in self.childmeta_df.loc[:,'name'].tolist(): 
                raise IOError
            if not v.dfloc in self.childmeta_df.index.tolist(): 
                raise IOError
            
        #=======================================================================
        # check matches between dicts
        #=======================================================================
        if d_is_all:
            dar = np.array(list(kids_d.keys()))
            kar = np.array(list(self.kids_d.keys()))
            
            boolar = np.isin(dar, kar)
            
            if not np.all(boolar):
                raise IOError
            

        return
            
            

        
class Parent_cmplx(Parent): #wrapper for parents with multiple child types
    
    kids_sd = None #structured kids dictionary {class_name: {obj.name : obj} }
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Parent_cmplx')
        logger.debug('start _init_ as \'%s\''%self.__class__.__name__)
        #=======================================================================
        # empty containers
        #=======================================================================
        self.kids_sd = dict() #the library is a dictionary. books are weak
        
        super(Parent_cmplx, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        self.post_init_func_od[self.update_kids_sd] =  'Parent_cmplx'
        #=======================================================================
        # continue the initilize cascade
        #=======================================================================
        self.logger.debug('finished _init_ as \'%s\' \n'%self.__class__.__name__)
        
        return
    
    def update_kids_sd(self, obj, method='add'): #add the object to your structured kids_d
        """
        structuerd by class name
        
        kids_sd
            d[kids class name] = kids_name_dict
                d[kid name] = child object
        
        this only contains objects you own (unlike the family_d)
        
        """
        logger = self.logger.getChild('update_kids_sd')

        cn = obj.__class__.__name__
        
        if method == 'add':
            
            do = wdict({obj.name:obj}) #new entry to be added
            
            logger.debug('adding \'%s\' as \'%s\' to kids_sd with %i books: %s'
                         %(obj.name, cn, len(self.kids_sd), list(self.kids_sd.keys())))
    
            if cn in list(self.kids_sd.keys()): #append
            
                d_old = self.kids_sd[cn]
                
                if obj.name in list(d_old.keys()): 
                    logger.error('found \'%s\' already in the kids_sd book  \'%s\''%(obj.name, cn))
                    raise IOError
                
                d_old.update(do)
                
                self.kids_sd[cn] = d_old #reset this (probably not needed)
                
                logger.debug('appending to d_old of \'%s\' with %i'%(cn, len(d_old)))
                
            else:  #new
                self.kids_sd[cn] = do
            
        
        else: raise IOError
        
        return
    
    def remove_kids_sd(self, obj): #try and remove the object from your kids_sd
        
        
        cn = obj.__class__.__name__
        
        if cn in self.kids_sd:

            d_old = self.kids_sd[cn]
            
            try: 
                del d_old[obj.name]
                
                self.kids_sd[cn] = d_old #reset this
                return
            except:
                if not obj.name in list(d_old.keys()): 
                    pass
                else:
                    logger = self.logger.getChild('remove_kids_sd')
                    logger.error('failed to remove for some reason')
                    raise IOError
                

class Trunk_o(Parent_cmplx): #advanced hierarchy functions
    """
    #===========================================================================
    # USE
    #===========================================================================
    made this separate from Basic_o to simplify it
    this supports advanced tree building, inspection, and child handling
    
    often used for top level handlers
    
    For session handlers, see Session_o
    """

    
    def __init__(self, *vars, **kwargs):
                
        super(Trunk_o, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        self.logger.debug('Trunk_o initilized')
        
        return
            
    def build_custom_logger(self,  #create a custom logger. outputs to the out_path
                            logger = None,
                            logname = None, 
                            lg_lvl = None,
                            warn_logr = False, #include a separat logger for warnings
                            ): 
        """
        for storing a custom logger in the output folder
            good for recording model run details
        
        WARNING: this does not configure a consoleHandler (only a separate filehandler)
            typically, the consolehandler is configured by main.py with the root logger (config file)
                    
        """
        #=======================================================================
        # setup defaults
        #=======================================================================
        if logname == None: logname = self.__class__.__name__
        
        if isinstance(lg_lvl, int):
            pass #already passed level
        elif lg_lvl is None: lg_lvl = logging.DEBUG
        elif lg_lvl == 'DEBUG': lg_lvl = logging.DEBUG
        elif lg_lvl == 'INFO': lg_lvl = logging.INFO
        elif lg_lvl == 'WARNING': lg_lvl = logging.WARNING
        else: raise IOError
        """cant pass python objects via the argparser"""
    
        
        #=======================================================================
        # build the new logger
        #=======================================================================
        if logger is None:
            logger = logging.getLogger(logname) #get/create a child of the root logger
        logger.setLevel(lg_lvl) #set the base level for the logger
        
        
        if self.session._write_data:
            #===================================================================
            #configure the abasic file handler
            #===================================================================
            filename = '%s.log'%(logname)
            logger_file_path = os.path.join(self.outpath, filename)
            handler = logging.FileHandler(logger_file_path) #Create a file handler at the passed filename 
            
            formatter = logging.Formatter('%(asctime)s.%(levelname)s.%(name)s:  %(message)s')
                    
            handler.setFormatter(formatter) #attach teh formater object
            handler.setLevel(lg_lvl) #set the level of the handler
            'this should only display the lowest of the logger'
            logger.addHandler(handler) #attach teh handler to the logger
            
            logger.info('standalone file logger created in :%s'%logger_file_path)
            #logger.info('custom logger loaded as %s from \'%s\''%(logname, os.path.basename(self.parspath)))
            
            #===================================================================
            # configure the warning logger
            #===================================================================
            if warn_logr:
                filename = ' %s_WARN.log'%(logname)
                logger_file_path = os.path.join(self.outpath, filename)
                handler = logging.FileHandler(logger_file_path) #Create a file handler at the passed filename 
                

                handler.setFormatter(formatter) #attach teh formater object
                'use same as above'
                handler.setLevel(logging.WARNING) #set the level of the handler

                logger.addHandler(handler) #attach teh handler to the logger
                
                logger.warning('standalone warning file logger created in : %s'%logger_file_path)
                
            
        else:
            logger.warning('_write_data = FALSE. no standalone logger')
            

        #===================================================================
        # wrap up
        #===================================================================
        self.logger = logger
        
        
        return
        
    
#===============================================================================
#     def write_child_atts(self, datao_dict): #save all the dataobjects and their attributes to a csv
# 
#         'this file can be copy/pasted back into the pars file for future formatting'
#         
#         #get the old pars frame
#         old_pars_df = self.session.pars_vars_df #get the pars df as loaded for this session
#         
#         
#         #=======================================================================
#         # build list of synthetic variables            
#         #=======================================================================
#         syn_dnames_list = []
#         for dataname, data_obj in self.dataset_dict.iteritems(): #loop through eacn one
#             
#             if not dataname in old_pars_df.loc[:, 'var_name'].values.tolist(): #exclude original vars
#                 syn_dnames_list.append(dataname) #add this one
#                 
#         #=======================================================================
#         # build the new pars frame
#         #=======================================================================
#         new_pars_df = pd.DataFrame(columns =old_pars_df.columns)
#         
#         new_pars_df['var_name'] =   ['blank']+ syn_dnames_list #store the new datanames
#         'adding the blank entry here to match pars frame formatting'
#         
#         #=======================================================================
#         # fill the new par frame     
#         #=======================================================================
#         for index, row in new_pars_df.iterrows(): #loop through and fill
#             if index == 0: continue #do nothing for the first row
#             #get this data object
#             data_obj = self.dataset_dict[row['var_name']]
#             
#             #fill with the attributes from this data_obj
#             for rindex, entry in row.iteritems():
#                 'we are not copy values from teh pars_df, but from teh data_obj attribute'
#                 if hasattr(data_obj, rindex): #see if this dataobj has this att
#                     att_val = getattr(data_obj, rindex) 
#                     row[rindex] = att_val#store this attribute value onto the row
#                     self.logger.debug('for %s setting \'%s\' = %s'%(data_obj.name, entry, att_val))
#                 else:
#                     self.logger.debug('data_obj %s does not have attribute \'%s\'. leaving blank'%(data_obj.name, rindex))
#                     
#             #add this back into the df
#             new_pars_df[index] = row
#             
#         #=======================================================================
#         # wrap up
#         #=======================================================================     
#         if self.write_outs:
#             filetail = self.sim_name + ' syn_datapars'
#             filename = os.path.join(self.out_path, filetail)
#             hp_pd.write_to_file(filename, new_pars_df, index=False) 
#             
#===============================================================================
    def load_par_tabs(self, #load data from a spreadsheet of parameters
                      parspath= None, #load the pars_df_d from the parfile
                      header = 0, 
                      index_col = None, 
                      skiprows=[1], 
                      **kwargs): 
        
        '''
        Called by the session
        20190504:
            I really dont like this.. very difficult to follow.
            much better to switch to the new style (everything is specified on the first tab)
        #===========================================================================
        # INPUTS
        #===========================================================================
        parfile_path:    filepath to the .xls with the data parameters tab
        datapar_tab:    spreadsheet like data on wich to load parameters
            row1:    parameter names
            row2: ignored (notes)
            col1=dataname    dataset names
            subsequent rows:    parameter values for each dataset
            
        kill_flag:    value (foundd in dataname) on which to stop loading subsequent rows
            this allows the user to keep all the data and parameters on the tab, but copy/paste to choose which are loaded
            
        rank:    the order of each entry determines the data rank (for conflict resolution)
        
        #=======================================================================
        # SPECIAL TABS
        #=======================================================================
        this generic loader has treats the loading of certain tabs differently:
        
        gen:    these are attached to the session directly as attributes
        
        pars: these are loaded by parent name into the obj_dyn_par_d (see hp_sim.Dyn_par_dato)
        
        '''
        #=======================================================================
        # load defaults
        #=======================================================================
        logger = self.logger.getChild('load_par_tabs')
        if parspath is None: parspath = self.parspath
         

        
        logger.info('from filepath: %s'%parspath)
        #=======================================================================
        # load all the frames
        #=======================================================================
        'the dtype kwarg with np.object blocks the data converter'
        df_d_raw = hp_pd.load_xls_d(parspath, header = header, index_col = index_col, skiprows = skiprows,                                    
                                    logger = logger, 
                                    **kwargs)
        
        
        #===================================================================
        # post formatting
        #===================================================================
        pars_df_d = OrderedDict()
        for sheetname, df_raw in df_d_raw.items(): #looop through each sheet/frame
            if sheetname.startswith('~'): continue #skip these
            
            #logger = logger.getChild('load_par_tabs.%s'%sheetname) #so we can tell what sheet the subfunctions are working on 
            df_clean = hp_pd.clean_datapars(df_raw, logger=logger) #special cleaning for datapars
            
            #===================================================================
            # special tabs
            #===================================================================
            if sheetname == 'gen': 
                logger.debug('attaching parameters from the \'gen\' tab to the Session \n')
                attach_att_df(self, df_clean, logger = logger, db_f = self.db_f) #attach all these

            #===================================================================
            # wrap up
            #===================================================================
            pars_df_d[sheetname] = df_clean
        

        #=======================================================================
        # #attacha nd closeout
        #=======================================================================
        logger = self.logger.getChild('load_par_tabs') #reset the logger
        logger.debug("pars_df_d %i dfs from files: %s"%(len(pars_df_d), list(pars_df_d.keys())))
        
        return pars_df_d
     
class Session_o(Trunk_o,#generic class for a program session
                hp_profMem.Profile_session_wrapper): 
    """
    This is a special wrapper around Basic_o for the session insstance)
    there should only be one of these per package
    """
    #===========================================================================
    # program pars
    #===========================================================================
    branch_level    = 0         #branch_level within the object hierarchy for thsi object
    name    = 'ses' #lets keep this
    #===========================================================================
    # user provided pars
    #===========================================================================
    raise_kids_f    = True      #flag whether to raise children or not
    'generally, the session uses a custom raise_children() call'
    _parlo_f        = False
    
    tag = ''
    mind = None
    delta_compare_col_nl = []
          
    #===========================================================================
    # calculation containers
    #===========================================================================
    family_d = dict() #d[class name] = d[obj name] = obj
    family_shdw_d = dict() #for holding shadow copies (non-simulation objects)
    'duplicate names will overrite here'
    #family_lib = dict() #d[class name] = d[unique gen cnt] = ojb

    spawn_cnt = 0 #counter for spawn number
    
    usage_file = None
    
    ltime = None #placeholder for tracking the last time recorded
    
    state = 'init'
    
    ins_copy_fps = set()
    
    def __init__(self, 
                 parspath = None,
                 outpath = None,
                 inscopy_path = None, 
                 
                 _logstep = 50,
                 lg_lvl = None,

                 _write_data = True, 
                 _write_figs = True, 
                 _write_ins = False,
                 
                 
                 _dbgmstr = 'any',  #amster debug control state
                 _parlo_f = False,  #partial data loading flag
                 
                 
                 _prof_time = False,
                 _prof_mem = 0,
                 
                 logger = None,
                 
                 *vars, **kwargs):
        

        log = mod_logger.getChild('Session_o') #have to use this as our own logger hasnt loaded yet
        log.debug('start __init__')

        #=======================================================================
        # inherit passed attributes
        #=======================================================================
        self.parspath       = parspath
        self.outpath        = outpath
        self.inscopy_path   = inscopy_path
        
        self._logstep       = _logstep

        self._write_data     = _write_data
        self._write_figs     = _write_figs
        self._write_ins      = _write_ins
        
        self._dbgmstr       = _dbgmstr
        self._parlo_f        = _parlo_f
        
        self._prof_time      = _prof_time #whether to profile cpu/memory stats during key run loops
        self._prof_mem      = _prof_mem
        
        
        'load from control file'
        #self.inspath        = inspath #for relative path references
        #=======================================================================
        # defaults
        #=======================================================================
        self.ltime          = time.time()
        
        """made a proxy"""
        self.session        = weakref.proxy(self) #this helps the raise_children get started
        
        #=======================================================================
        # debugger mode
        #=======================================================================
        if self._dbgmstr == 'any':      self.db_f = True #leave itas is
        elif self._dbgmstr == 'all':    self.db_f = True
        elif self._dbgmstr == 'none':    self.db_f = False

        #=======================================================================
        # generic loader functions
        #=======================================================================
        if logger is None:
            self.build_custom_logger(lg_lvl = lg_lvl, logname = 'S', warn_logr=True)      #build a custom logger
        else:
            self.logger = logger
        
        #logger = self.logger.getChild('Session_o')
        log.debug("loading pars \n")
        self.pars_df_d = self.load_par_tabs(parspath)            #load all the pars from the file
        
        self.set_inspath()

        super(Session_o, self).__init__(self, self, *vars, **kwargs) #initilzie teh baseclass
        """ not setup very well
        these kwargs, vars are only used to pass onto the Child...
        but we dont even use the _init_ of the child
        'passing self, self as parent, session' 
        'just doing this to pickup all teh handles off Child'"""
        
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not isinstance(self._prof_mem, int):
                raise IOError
            
        log.debug('__init_ finished \n')

        return
    
    def set_inspath(self): #apply logic for assigning the inspath
        logger = self.logger.getChild('get_inspath')
        
        if not hasattr(self, 'inspath'):
            raise IOError #no attribute inspath
        
        if self.inspath is None:
            raise IOError
        
        elif self.inspath == 'abs': 
            logger.info('using absolute file referneces')
            return
            
        elif self.inspath == 'auto':
            logger.info('setting inspath automatically from contol file location')
            self.inspath,_ = os.path.split(self.parspath)
            
        
        #using relatives
        if not os.path.exists(self.inspath): 
            raise IOError 
        logger.info('using file references relative to \'%s\''%self.inspath)
        
        return
    
    def upd_family_d(self, obj, shadow=False):
        """ I considered moving this to the model
            therefore allowing full duplication of the model structure on reset
            
        hoever, this makes reseting all of the pointers very difficult (relative vs absolute)
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('upd_family_d')
        #get your classes dictionary as it is
        
        cn  = obj.__class__.__name__
        
        #shadow handling
        if shadow:
            logger.debug('shadow=TRUE. storing in the shadow dict')
            d = self.family_shdw_d
        else:
            d = self.family_d
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not obj.session == self: 
                raise IOError
            if not hasattr(obj, '__class__'):
                raise IOError
            
            """ for plotting, we sometimes spawn new data objects mid run """
            if not self.state == 'init':
                if not cn in list(d.keys()): 
                    logger.warning('outside of warmup, could not find class name \'%s\' in the family_d'%cn)


        #=======================================================================
        # pull book from the library
        #=======================================================================
        #logger.debug('adding \'%s\' object to the family library'%cn)
        
        if cn in list(d.keys()): #see if you have a book already
            #family dictionary
            class_d = d[cn] #get your class_d
            
        else: #add a new book
            class_d = OrderedDict()
            

            logger.debug('created a new book for \'%s\''%cn)
            

        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not isinstance(obj.branch_level, int):
                raise IOError
            
            #check if this object is a proxy
            if isinstance(obj, weakref.ProxyType):
                raise IOError
            
            if obj.gid in list(class_d.keys()): 
                raise Error('there is already a copy in book \'%s\' of \'%s\''%(cn, obj.gid))
            
            """ shadow objects may have a high sib_cnt once they are brought back into the family
            #cehck if this object has siblings and is still the first
            if len(class_d) == 0:
                if obj.sib_cnt >0:
                    raise IOError"""
            
        """ moved back to init
        obj.gid = str('%02d_%s_%03d_%s'%(obj.branch_level, obj.parent.name,  obj.gen_cnt, obj.name,))"""
        
        #=======================================================================
        # #udpate global containers
        #=======================================================================
        logger.debug('adding \'%s\' to family_d  as \'%s\''%(obj.name, obj.gid))

        class_d[obj.gid] = obj
        
        #shadow handling
        if shadow:
            self.family_shdw_d[cn] = class_d
        else:
            self.family_d[cn] = class_d
            
        del logger
        
        return
    
    def parent_swap(self, obj, parent_new): #swap parents
        logger = self.logger.getChild('parent_swap')
        parent_old = obj.parent
        
        
        logger.debug('on \'%s\' from \'%s\' to \'%s\''%(obj.name, parent_old.name, parent_new.name))
        
        if self.db_f:
            old_gid = obj.gid
            if not inspect.isclass(type(parent_old)):
                raise IOError
            
            if not parent_old.__class__ == parent_new.__class__:
                raise IOError
        
        """want to keep working with the original
        #=======================================================================
        # get clone
        #=======================================================================
        clone = copy.copy(obj)"""
        
               
        #=======================================================================
        # clean from old parent
        #=======================================================================
        parent_old.update_childmeta(obj, method='delete') #update the childmeta
        
        self.kill_obj(obj) #remove your entry from teh family_d and the upd_cmd_que

        """ these should all die
            NOPE. we are not killing ourselves. jsut renaming/moving"""
        #basic parent
        del parent_old.kids_d[obj.name]
        
        #complex parent
        if hasattr(parent_old, 'kids_sd'):
            parent_old.remove_kids_sd(obj)
        
        
        #=======================================================================
        # add to the new parent
        #=======================================================================
        obj.inherit_logr(parent_new)
        
        'I dont think this is usually necessary, but more robust to include'
        obj.inherit_from_pset(parent_new)
        
        'new parent ref, new gid, added to family_lib, add yourself to parent.kids_d and execute any post commands'
        obj.init_clone(parent_new)
        
        parent_new.update_childmeta(obj, method='add') #update the childmeta
        #=======================================================================
        # setup dfloc
        #=======================================================================
        
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if obj.name in list(parent_old.kids_d.keys()): raise IOError
            if not obj.name in list(obj.parent.kids_d.keys()): raise IOError
            
            if obj.gid == old_gid: raise IOError
            
            if not obj.parent.__repr__() == parent_new.__repr__():
                raise IOError
            
            """if hasattr(obj, 'hse_type'):
                if not obj.hse_type == obj.hse_o.hse_type:
                    raise IOError"""

        
        logger.debug('finished \n')
    
    def family_cnt(self): #get the total count of objects in the family_d
        
        cnt = 0
        for cn, book in self.family_d.items(): cnt += len(book)
        
        return cnt
    
    def print_family_cnt(self):
        logger = self.logger.getChild('print_family_cnt')
        for cn, book in self.family_d.items():
            logger.info('%i in \'%s\''%(len(book), cn))
    
    
    def kill_obj(self, #kill the passed object
                  proxy): 
        
        """this should not be necessary when using WeakValueDictionary

        setup for proxies"""
        logger = self.logger.getChild('kill_obj')
        
        cn = proxy.__class__.__name__
        logger.debug('on proxy for object \'%s.%s\''%(cn, proxy.gid))
        
        #if self.db_f:

        
        #=======================================================================
        # retrieve the real object from teh family library
        #=======================================================================
        gid = proxy.gid
        
        obj = self.family_d[cn][gid] 
        
        #=======================================================================
        # updates que
        #=======================================================================
        if proxy.gid in list(self.update_upd_que_d.keys()):
            logger.debug('attempting to kill an object \'%s\' that has some updates qued on it: %s'
                         %(proxy.gid, list(self.update_upd_que_d[proxy.gid].upd_cmd_od.keys())))
            
            """
            This happens when we que up a bunch of updates on the house, then reset the type
            """
            
            del self.update_upd_que_d[gid] #remove the ques on this
            
        
        #=======================================================================
        # permanent holders
        #=======================================================================
        
        'this is probably still alive in the calling frame'
        del obj #delete the object
        
        del self.family_d[cn][gid] #delete the reference from teh family lib
        
        return
    
    def shadow_objs(self, wd): #duplicate container of objects
        """setup to handle weak references
        creates a container holding full referneces of hte passed object
        """
        logger = self.logger.getChild('shadow_objs')
        
        shdw_d = dict() #msut be a real dict
        
        logger.debug('on container with %i entries of type \'%s\''%(len(wd), type(wd)))
        
        
        
        for k, obj in wd.items():

            shdw_d[k] = copy.copy(obj) #plant a real reference
            

            if self.db_f:
                if not inspect.isclass(obj): raise IOError
                if not isinstance(wd, wdict): raise IOError
                'todo: check that this isnt a proxy'
                
        logger.debug('built a shadow copy with %i \n'%len(shdw_d))
        
        return shdw_d
    
    def check_family_refs(self,#check the reference count of all objects
                           max_cnt = 0,  #maximum number of allowable reference counts
                           excl_ns = set(['Udev', 'Fdmg'])):  #book names to exclude
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        max_cnt: number of counts on which to raise flags
            seem to be getting inconcisisnte counts
        """
        logger = self.logger.getChild('check_family_refs')
        #gc.collect()
        
        fails = set()
        cnt = 0
        #=======================================================================
        # loop and check
        #=======================================================================
        logger.debug("checking %i books for max_cnt %i: %s \n"%( len(self.family_d),max_cnt, list(self.family_d.keys())))
        for bookname, book_wd in self.family_d.items():
            if bookname in excl_ns: continue
            logger.debug('checking book \'%s.%s\' with %i entries\n'%(bookname, type( book_wd), len(book_wd)))
            
            """this is the family library... anything goes
            if not isinstance(book_wd, wdict): 
                logger.error('for book \'%s\' got unexpected type \'%s\''%(bookname, type(book_wd)))
                raise IOError"""
            
            for k, obj in book_wd.items():
                
                cnt +=1
                gc.collect()
                if sys.getrefcount(obj) > max_cnt:
                    logger.debug('\'%s.%s\' failled with getrefcount = %i'
                                 %(bookname,k, sys.getrefcount(obj)))
                    fails.add(obj)
                    
                    
        #=======================================================================
        # report
        #=======================================================================
        if len(fails) == 0:
            logger.debug('all passed')
            return True
        else:
            logger.debug(' %i/%i failed'%(len(fails), cnt))
            return False
        
    def check_permanence(self, obj):

        logger = self.logger.getChild('check_permanence')
        logger.info('on \'%s\' named \'%s\''%(obj, obj.name))
        o2 = copy.copy(obj)
        
        gc.collect()
        parent = o2.parent
        cnt1 = len(parent.kids_d)
        refs = sys.getrefcount(obj)
        

        
        self.kill_obj(obj)
        
        l = []
        
        gc.collect()
        for e in gc.get_referrers(obj): l.append(str(e))
        
        del obj
        
        
        cnt2 = len(parent.kids_d)
        
        if len(l) > 1:
            logger.error('failed with %i referrers'%len(l))
            for e in l: logger.info(e)
            return False
        else:
            return True
        

        




            

    
        
        
        
        

        
            
            
    


