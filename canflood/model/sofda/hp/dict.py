'''
Created on Mar 6, 2018

@author: cef

hp functions for workign with dictionaries
'''
import logging, os, sys, math, copy, inspect

from collections import OrderedDict
from weakref import WeakValueDictionary as wdict

import numpy as np
import model.sofda.hp.basic as hp_basic




mod_logger = logging.getLogger(__name__) #creates a child logger of the root 


def dict_2_logr(dict, logger= mod_logger): #log each value of the dictionary to fille
    logger = logger.getChild('dict_2_logr')

    msg = '\n'
    for key, value in dict.items():
        
        msg = msg + '    key: %s\n    value: %s \n'%(key, value)
        
    logger.debug(msg)
    
def key_list(d,  #return the intersection of the dict.keys() and the key_list
             key_list, logger = mod_logger):
    logger = logger.getChild('key_list')
    #===========================================================================
    # pre check
    #===========================================================================
    bool_list = hp_basic.bool_list_in_list(list(d.keys()), key_list)
    if not bool_list.any(): raise IOError #check if any are not found

    
    #===========================================================================
    # build the found values
    #===========================================================================
    values_fnd_list = []
    
    for key, value in d.items():
        if key in key_list: values_fnd_list.append(value)
        
        
    return values_fnd_list

def build_nones_dict(key_list, logger=mod_logger): #add 'None' values to the passed keys
    
    val_list = np.full((1, len(key_list)), None)
    dict = dict(list(zip(key_list, val_list)))
    
    return dict

def merge_two_dicts(x, y):
    if x is None: return y
    if y is None: return x
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z

def value_by_ksearch(ksearch_str, d, #get the entry that matches the search str
                     logger=mod_logger, *search_args):
    
    
    #===========================================================================
    # take a shot at a perfect match
    #===========================================================================
    try:
        return d[ksearch_str]
    except:
    
        #find a match for this key
        k_fnd = hp_basic.list_search(list(d.keys()), ksearch_str, *search_args)
        
        if k_fnd is None: 
            logger = logger.getChild('value_by_ksearch')
            logger.debug('could not find \'%s\' in %i dict keys. returning None'%(ksearch_str, len(d)))
            return None
        else: 

            return d[k_fnd]

def merge(dl, dr, #intelligent dictionary merging
          set_type = 'intersect', 
          method = 'exact',
          container = dict(),
          logger = mod_logger, *search_args):
    
        if set_type == 'union':
            if method == 'exact':
                d_merge = merge_two_dicts(dl, dr, logger=logger)
            else:
                raise IOError #todo
        
        elif set_type == 'intersect':
            d_merge = subset(dl, list(dr.keys()), set_type = set_type, 
                             method=method, container=container, logger=logger, *search_args)
            
        else: raise IOError
        
        logger.debug('got d_merge %i'%len(d_merge))
        
        return container(d_merge)
                
def subset_pfx(d_big, prefix, logger=mod_logger):
    #===========================================================================
    # shortcuts
    #===========================================================================
    if len(d_big) == 0: return dict()
    #===========================================================================
    # defaults
    #===========================================================================
    logger = logger.getChild('subset_pfx')
    
    d = copy.copy(d_big)
    
    fnd_d = dict()
    for k, v in d.items():
        if k.startswith(prefix):
            fnd_d[k] = v
            
    logger.debug('found %i entries with prefix \'%s\' \n'%(len(fnd_d), prefix))
            
    return fnd_d
    

def subset(d_big, l,  #get a dictionary subset using standard user inputs
           #ordered = False,  using containers instead
           set_type = 'sub', 
           method = 'exact',
           container = dict,
           logger = mod_logger, 
           *search_args):
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    l: list of keys (within d_big) on which to erturn the sutset
    
    set_type: how to treat the set
        intersect: returna  dictionary with only the common keys
        sub:    raise a flag if not every item in 'l' is found in d_big.keys()
        
    method: what type of key search to perform (re.function)
        search: look for a key in the dictionary that contains the list entry.
                returned d is keyed by the list
    """
    logger = logger.getChild('subset')

    
    #===========================================================================
    # setup[]
    #==========================================================================
    d = container()
    """
    #dictionary setup
    if ordered: d = OrderedDict()
    else:       d = dict()"""
    
    #input list setup
    if isinstance(l, list):         pass
    elif isinstance(l, str): l = [l]
    elif l is None:                 return d
    else:                           raise IOError
    
    nofnd_l = [] 
    #===========================================================================
    # determine subset by kwarg
    #===========================================================================
    for k in l:
        
        try: #attempt teh direct match
            d[k] = d_big[k]
            
        except:
            #===================================================================
            # try again using search functions
            #===================================================================
            try:
                if method == 'search':
                    #search and return this value
                    v = value_by_ksearch(k, d_big, logger=logger, *search_args)

                    if not v is None:
                        d[k] = v
                        continue #not sure this is needed
                    
                    else: raise ValueError                   
                else: raise ValueError

            #===================================================================
            # nothing found. proceed based on set_type
            #===================================================================
            except:
                logger.debug('unable to find \'%s\' in the dict with method \'%s\''%(k, method))
                
                if set_type == 'sub':
                    
                    boolar = hp_basic.bool_list_in_list(list(d_big.keys()), l)
            
                    if not np.all(boolar):
                        logger.error('%i entries in list not found in big_d'%(len(l) - boolar.sum()))
                        
                    raise IOError
                
                elif set_type == 'intersect': nofnd_l.append(k)
                else: raise IOError
                    
                
                
    #===========================================================================
    # wrap up
    #===========================================================================     
    if len(nofnd_l) >0:        
        logger.debug('%i of %i list entries DO NOT intersect: %s'%(len(nofnd_l), len(l), nofnd_l))
        if set_type == 'sub': raise IOError
        
    #===========================================================================
    # check
    #===========================================================================
    if len(d) == 0: 
        logger.warning('0 common values between d(%i) and l(%i)'%(len(d), len(l)))
        
    logger.debug('returning d with %i entries: %s \n'%(len(d), list(d.keys())))

    return container(d)

 

class deepcopier():
    tries = 0 #keep track of the loop
 
    def __init__(self,obj, logger=mod_logger):
                
        self.logger = logger.getChild('deepcopier')
        self.copy_o = obj
        
    def tryit(self, obj=None): #make as deep a copy as possible
        if obj is None: obj = self.copy_o
        #===========================================================================
        # simple try
        #===========================================================================
        try:
            copy_o = copy.deepcopy(obj)
            return copy_o
        except:
            self.logger.debug('failed first attempt')
            self.tries += 1
            
        #=======================================================================
        # sophisiticated try
        #=======================================================================
        self.logger.debug('copy attempt %i'%self.tries)
        
        if self.tries > 10: return self.copy_o
            
        #try for each element of the dict
        if isinstance(obj, dict):
            new_d = dict()
            for key, value in obj.items():
                
                try:
                    new_d[key] = self.tryit(obj = value)
                except:
                    new_d[key] = copy.copy(obj)
                    
            self.logger.debug('returning new_d with %i entries: %s'%(len(new_d), list(new_d.keys())))
        
        else: raise IOError
        
        return new_d
    
    
#===============================================================================
# 
# from collections import OrderedDict
# 
# class MyOrderedDict(OrderedDict):
#     """
#     as there is no builtin method to add to the head of an ordered dict,
#         here we add a method
#     https://stackoverflow.com/questions/16664874/how-can-i-add-an-element-at-the-top-of-an-ordereddict-in-python
#     """
# 
#     def prepend(self, #add entry to the front of myself
#                 key, value, 
#                 dict_setitem=dict.__setitem__, #??
#                 ):
#         """
#         Im not sure if there is a clean way to do this to the 3.7+ dict
#         """
#         raise IOError('outdated. use \'move_to_end\'')
#     
#     
#         d = {'1':1,'99':99,'2':2}
#         
#         for k in iter(sorted(d)):
#             print(k)
#             
# 
#             
#         dict(sorted(d.items()))
#             
#         d.sort()
# 
#         """
#         
#         
#         import sys
#         sys.version
#                 for e in dir(self):
#             print(e)
#         """
#         root = self._OrderedDict__root
#         first = root[1]
# 
#         if key in self:
#             link = self._OrderedDict__map[key]
#             link_prev, link_next, _ = link
#             link_prev[1] = link_next
#             link_next[0] = link_prev
#             link[0] = root
#             link[1] = first
#             root[1] = first[0] = link
#         else:
#             root[1] = first[0] = self._OrderedDict__map[key] = [root, first, key]
#             dict_setitem(self, key, value)
#             
# 
#         
#===============================================================================
