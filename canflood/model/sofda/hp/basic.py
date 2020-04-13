'''
Created on Jun 24, 2017

@author: cef

Library of custom hp functions for pythons builtin librarires

#===============================================================================
# # PHILOSOPHY ---------------------------------------------------------------
#===============================================================================

functions less than a few lines should be put directly into parent code

functions that work mostly with custom python modules (pandas, numpy, etc.) should have their own hp librarires
    any of these basic functions that require custom py mods shoud import within the function
'''


# Import Python LIbraries 
import os, copy, sys, time, re, logging, random, shutil

from datetime import datetime

#import pandas as pd

import numpy as np
import logging.config



mod_logger = logging.getLogger(__name__)
"""NOTE ON LOGGING
In general, logging should go to the 'main' logger called above
WARNING: this requires the main logger be initialized prior to loading this script
see main.py for details

 """          

mod_logger.debug('hp_basic initialized')




#FOLDER operations------------------------------------------------------------- 


    
def force_open_dir(folder_path_raw, logger=mod_logger): #force explorer to open a folder
    logger = logger.getChild('force_open_dir')
    
    if not os.path.exists(folder_path_raw):
        logger.error('passed directory does not exist: \n    %s'%folder_path_raw)
        return False
        
    import subprocess
    
    #===========================================================================
    # convert directory to raw string literal for windows
    #===========================================================================
    try:
        #convert forward to backslashes
        folder_path=  folder_path_raw.replace('/', '\\')
    except:
        logger.error('failed during string conversion')
        return False
    
    try:
        """
        folder_path = folder_path_raw
        dir = 'C:\\Users\cef\Google Drive\Programs\Sobek 3\Python\Plotting'
        """
        args = r'explorer "' + str(folder_path) + '"'
        subprocess.Popen(args) #spawn process in explorer
        'this doesnt seem to be working'
        logger.info('forced open folder: \n    %s'%folder_path)
        return True
    except:
        logger.error('unable to open directory: \n %s'%dir)
        return False
    
def copy_file(filetocopy_path,  #copy file to a directory
              dest_base_dir, 
              overwrite = True, 
              new_fn = None,
              sfx = None,
              logger=mod_logger): 
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    
    """
    #===========================================================================
    # setups and defaults
    #===========================================================================
    logger = logger.getChild('copy_file')
    tail, filename = os.path.split(filetocopy_path)
    if new_fn is None: new_fn = filename
    
    
    #===========================================================================
    # get new filepath
    #===========================================================================
    if not sfx is None:
        new_fn1, ext = os.path.splitext(new_fn)
        new_fn = '%s%s%s'%(new_fn1, sfx, ext)
    
    
    dest_file_path = os.path.join(dest_base_dir, new_fn)
    
    #===========================================================================
    # checks and sub folder creation
    #===========================================================================
    if not os.path.exists(filetocopy_path):
        logger.error('passed file does not exist: \"%s\''%filetocopy_path)
        raise IOError
    
    if os.path.exists(dest_file_path):
        logger.warning('destination file already exists. no copy made. \n    %s'%dest_file_path)
        return False
    
    if not os.path.exists(dest_base_dir): #check if the base directory exists
        logger.warning('passed base directory does not exist. creating:\n    %s'%dest_base_dir)
        os.makedirs(dest_base_dir) #create the folder

    try:    
        shutil.copyfile(filetocopy_path,dest_file_path)
    except:
        logger.error('failed to copy \'%s\' to \'%s\''%(filetocopy_path,dest_file_path))
        raise IOError
    
    logger.debug('copied file to \n    %s'%dest_file_path)
    
    return True
    

def setup_workdir(workpath, basename='out', ins_basename = '_inscopy', logger=mod_logger): #Create and return output directory based on time
    
    logger=logger.getChild('setup_workdir')
        
    
 
    if not os.path.exists(workpath): 
        raise IOError('passed workpath does not exists: \'%s\''%workpath)
    
    outpath = None
    #===========================================================================
    # loop and find unique name
    #===========================================================================
    for ind in range(0,100,1):
        tnow = datetime.now().strftime('%Y%m%d%H%M%S') #convenience time string
    
        outpath = os.path.join(workpath,basename+'_'+ tnow)
    
    
        if os.path.exists(outpath): #check to see if it exists
            logger.warning('time generated output folder already exists at: %s'%outpath)
            time.sleep(1)
            continue #wait a second and try anoth reloop
        else:
            break
         
        
    if outpath is None: raise IOError #loop didnt find a good path
    

    
    logger.info('outpath built: \n    %s'%outpath)
    
    #===========================================================================
    # make the directories
    #===========================================================================
    os.makedirs(outpath) #create the folder
       
        
    return outpath

                 
                 
        
#===============================================================================
# OBJECT Based -----------------------------------------------------------------
#===============================================================================
'see oop.py'


#===============================================================================
# LIST FUNCTIONS ---------------------------------------------------------------
#===============================================================================

        
    
def str_to_list(list_str, strip = True, list_pfx = '[', cmd_sfx = ')',
                new_type = 'auto', logger=mod_logger): #convert a string to a list
    
    """
    This got pretty complicated because I want to control what gets interpreted as a lis
        startswith('['): by default treat as a list

        
    #===========================================================================
    # INPUTS
    #===========================================================================
    strip:     flag wither to strip teh whitespaces between entries
    new_type:    new type to map onto each entry
        'auto': detect type from first entry
        
    """
    if isinstance(list_str, list): return list_str #do nothing. already a list
    

    #===========================================================================
    # defaults
    #===========================================================================
    logger = logger.getChild('str_to_list')
    
    #check if this isa list type
    if not is_str_list(list_str, list_pfx = list_pfx, logger=logger): 
        logger.error('got non list type: \'%s\''%list_str)
        raise IOError
    
    
    #logger.debug('converting to list type: %s'%list_str)
    #===========================================================================
    # convert
    #===========================================================================
    list_str1 = list_str[1:-1] #drop the brackets
    
    list1 = None
    #single entrys
    if list_str1.find(',') == 0: 
        list1 =  [list_str1] #no commans. just a single entry
        'could still be a single entry list. list of commands with kwrags'
    
    #with command strings
    elif not cmd_sfx is None:
        'because we need to accept kwargs with commas and apostraphes, we instaed split by the cmd_sfx'
        if list_str1.endswith(cmd_sfx): #may be a list of commands
            
            #===================================================================
            # precheck
            #===================================================================
            if not np.any((new_type == 'str', new_type == 'auto')): 
                raise IOError #commands have to be strings
                
                
            'try splitting by the command suffixes as tehse should end each entry'
            
            #===================================================================
            # intelligent search
            #===================================================================
            command_cnt = list_str1.count(cmd_sfx) #guess at how many commands there are
            
            list1 = []
            old_str = copy.copy(list_str1) #start with the original
            for i in range(0, command_cnt, 1): #loop through and make each of these
                
                pos = old_str.index(cmd_sfx) #find th elocation of the break
                
                this_str = old_str[:pos+1].strip() #get everything up to this
            
                list1.append(this_str) #add to the list
                
                old_str = old_str[pos+2:] #chop this out of ht eold list
                
            #logger.debug('found string of %i custom commands'%command_cnt)
            
            """
            list1[1].strip()
            
            """
            
                    
    #no embeded commas        
    if list1 is None: list1 = str(list_str1).split(',') #try and convert a string with comas to a list
                
    #===========================================================================
    # stip whitespace
    #===========================================================================
    if strip:
        list2 = []
        for raw_str in list1: list2.append( raw_str.strip())
    else: list2 = copy.copy(list1)

            
    #===========================================================================
    # type mapping
    #===========================================================================
    #none
    if new_type is None: list3 = copy.copy(list2) #no conversion
    
    #automatic
    elif new_type == 'auto': 
        
        #see if the first entry is a number
        if isnum(list2[0]): 
            list3 = list(map(float, list2))
        else: list3 = copy.copy(list2) #no c onversion
        
    elif new_type == 'str':
        
        list3 = []
        for entry in list2:
            list3.append(entry.replace("'", ""))
        
    #explicit
    else: list3 = list(map(new_type, list2))
    
    #===========================================================================
    # wrap up
    #===========================================================================
    new_l = list3
    
    #logger.debug('converted string to list with %i entries'%len(new_l))
        
    return new_l



#===============================================================================
# def list2str(list1, logger=mod_logger): #take a list and convert it to a string
#     """
#     this is useful for taking a list, and convertin git to
#         items entered as a list of strings in excel (C, S, E, etc...)
#     and converting them to a pythonic type list
#     """
#     logger = logger.getChild('list2str')
#     
#     new_str = ''
#     for entry in list1:
#         new_str = new_str + str(entry) + ','
#         
#     return new_str[:-1] #exclude the last comma
#===============================================================================
    

    
#===============================================================================
# def list_cleaner(list_raw, delim=' ', logger=mod_logger): #take a messy list and clean it
#     """
#     #===========================================================================
#     # INPUTS
#     #===========================================================================
#     delim:     entry to look for on which to split the list
#     """
#     
#     logger = logger.getChild('list_cleaner')
#     #logger.debug('cleaning list with %i entries: \n    %s'%(len(list_raw), list_raw))
#     
#     list_clean = []
#     
#     for entry in list_raw:
#         if isinstance(entry, str): #only convert string like entries 
#             if delim in entry: #see if the delimintaor is in the string
#                 new_list = str(entry).split(delim) #split on the delim
#                 
#                 list_clean = list_clean + new_list
#                 
#                 
#             else: list_clean.append(entry)
#                 
#         else:list_clean.append(entry)
#         
#     return list_clean
#===============================================================================

def bool_list_in_list(list_outer, list_inner,  #check that each entry of the inner list is in the outer list
                      method='exact', *search_args):
    """
    #===========================================================================
    # OUTPUTS
    #===========================================================================
    bool_list:    boolean list (same length as list_inner) returning TRUE for inner entries found in outter
    """
    
        
    
    bool_list = []
    
    for entry in list_inner:
        if method == 'search':
            entry = list_search(list_outer, entry,  *search_args)
            'this will return None if the entry was not found in the list_outer'
            bool_list.append(not entry is None)
        elif method == 'exact':
            bool_list.append(entry in list_outer)
        else: raise IOError

            
        
    return np.array(bool_list)

#===============================================================================
# def get_list_mismatch(left_l, right_l, logger=mod_logger): #log the inner values not found in outer
#     
#     logger = logger.getChild('get_list_mismatch')
#     
#     right_lost_l = []
#     
#     for entry in right_l:
#         if not entry in left_l: right_lost_l.append(entry) 
#         
#     left_lost_l = []
#     
#     for entry in left_l:
#         if not entry in right_l: left_lost_l.append(entry) 
#         
#     #===========================================================================
#     # reporting
#     #===========================================================================
#     if len(right_lost_l)>0:
#         logger.debug('INNEr list is missing %i values: \n    %s'%(len(right_lost_l), right_lost_l))
#     if len(left_lost_l)>0:
#         logger.debug('OUTER list is missing %i values: \n    %s'%(len(left_lost_l), left_lost_l))
#         
#     return right_lost_l, left_lost_l
#===============================================================================

def list_search(l, search_str, #return the list item that matches the search_str
                method ='search', logger=mod_logger, *args): 
    
    logger = logger.getChild('list_search')
    
    if method == 'search':
        if args is None: args = re.IGNORECASE
        
        for entry in l:
            if re.search(search_str, entry, *args):
                
                logger.debug('found match of \'%s\' in l as \'%s\''%(search_str, entry))
                return entry
            
        #logger.debug('found no match for \'%s\' in list (%i): %s'%(search_str, len(l), l))
        return None
    
    elif method == 'prefix':
        fnd_l = []
        for entry in l:
            try:
                if entry.beginswith(search_str):
                    fnd_l.append(entry)
            except:
                logger.error('failed to do prefix search')
                raise IOError
        
        logger.debug('found %i entries matching the passed prefix \'%s\''%(len(fnd_l), search_str))
        return fnd_l

    else: raise IOError

#===============================================================================
# def list_intersect(l1, l2): #find the intersection of both lists
#     
#     lu = [val for val in l1 if val in l2]
#     
#     return lu
#===============================================================================

#===============================================================================
# def takeClosest(myList, myNumber): #Returns closest value to myNumber
#     """
#     Assumes myList is sorted. .
# 
#     If two numbers are equally close, return the smallest number.
#     https://stackoverflow.com/questions/12141150/from-list-of-integers-get-number-closest-to-a-given-value/12141511#12141511
#      has a running time of O(log n) as opposed to the O(n) running time of the highest voted answer
#     """
#     from bisect import bisect_left
#     myList.sort()
#     
#     pos = bisect_left(myList, myNumber) #find the position of the number in the list
#     
#     # ends condition 
#     if pos == 0: #first spot
#         return myList[0]
#     
#     if pos == len(myList):
#         return myList[-1]
#     
#     # Stuff in between 
#     before = myList[pos - 1]
#     after = myList[pos]
#     
#     if after - myNumber < myNumber - before:
#        return after
#     else:
#        return before
#===============================================================================
   
#===============================================================================
# def fancy_l_combine(l1, l2):
#     
#     if l2 is None: l = l1
#     elif l1 is None: l = l2
#     
#     
#     elif not (isinstance(l1, list) and isinstance(l2, list)): 
#         raise IOError
#     
#     else: l = l1 + l2
#     
#     return l
#===============================================================================
       
#===============================================================================
# # TUPLE FUNCTIONS ------------------------------------------------------------
#===============================================================================
#===============================================================================
# def str_to_tup(raw_str, logger = mod_logger): #convert a string to a tuple
#     if isinstance(raw_str, tuple): return raw_str #already a tuple
#     if not is_str_tup(raw_str, logger = logger): raise IOError #not a tuple type 
#     
#     logger = logger.getChild('str_to_tup')
#     
#     #===========================================================================
#     # get a list of the entries
#     #===========================================================================
#     list1 = str_to_list(raw_str, strip = True, list_pfx = '(', cmd_sfx = None,
#                         logger=logger) #convert a string to a list
#     
#     
#     return tuple(list1)
#===============================================================================

            
#===============================================================================
# CHECKING  -----------------------------------------------------------
#===============================================================================
def isnum(entry): #checks if the entry si numeric or not

    try:
        float(entry)
        return True
    except:
        return False
    
def is_str_list(chk_str, list_pfx = '[', logger = mod_logger): #check if  a strin gmay be a list
    
    if isinstance(chk_str, list): return True #do nothing. already a list
    if not isinstance(chk_str, str): raise IOError
    else: chk_str = str(chk_str) #conversion 
    
    logger = logger.getChild('is_str_list')
    
    if not list_pfx is None:
        if chk_str.startswith(list_pfx):
            return True
        else:
            return False #doesn't start wit the prefix
        
    else: 
        'I want to make list detection explicit'
        raise IOError
    
def is_str_tup(chk_str, tup_pfx = '(', logger = mod_logger): #check if  a strin gmay be a list
    'may be able to combine this with is_str_list'
    if isinstance(chk_str, tuple): return True #do nothing. already a list
    if not isinstance(chk_str, str): raise IOError
    else: chk_str = str(chk_str) #conversion 
    
    logger = logger.getChild('is_str_tup')
    
    if not tup_pfx is None:
        if chk_str.startswith(tup_pfx):
            return True
        else:
            return False #doesn't start wit the prefix
        
    else: 
        'I want to make list detection explicit'
        raise IOError
    
def str_is_bool(chk_str):
    
    trues = ['True','TRUE','true', 'yes','YES','Yes', 'Y', 'y']
    falses = ['False', 'FALSE', 'false', 'NO', 'No', 'no', 'N', 'n']
    
    if chk_str in trues: return True
    elif chk_str in falses: return True
    else: return False
    
def str_is_none(raw_str, logger=mod_logger): #detect whether teh passed string is probably noen
    #type checking
    if raw_str is None:                     return True
    if not isinstance(raw_str, str): return False
    else: raw_str = str(raw_str)
    
    #contents checking
    nones = ['none', 'None', 'NONE', 'nothing']
    
    if raw_str in nones: return True
    else: return False
    
def str_is_dict(raw_str, logger=mod_logger):
    if raw_str is None:                     return False
    if hasattr(raw_str, 'keys'):            return True
    if not isinstance(raw_str, str): return False
    if raw_str.startswith('{') & raw_str.endswith('}'): return True
    else: return False
        


    


#===============================================================================
# FORMATING,  TYpes, and COnversions ------------------------------------------------------------------
#===============================================================================


#===============================================================================
# def String2ptype(text_str, logger=mod_logger): #convert a text string to its obvious python type
#     """TESTING:
#     text_str = 'str'
#     type = String2dtype(text_str)
#     """
#     if text_str == 'str':
#         return str
#     elif text_str == 'int':
#         return int
#     elif text_str == 'float':
#         return float
#     else:
#         logger.warning('No dtype match for: %s'%text_str)
#         raise IOError
#===============================================================================
      
def str_to_bool(bool_string, logger=mod_logger): #convert a string to a boolean
    logger = logger.getChild('str_to_bool')
    #check if bool_)string is a string
    if isinstance(bool_string, bool): #check if its already formatted proeprly
        return bool_string
    #===========================================================================
    # elif not isinstance(bool_string, str):
    #     logger.error('got unexpected type: %s'%type(bool_string))
    #     raise IOError
    #===========================================================================
    else: #convert
    
        trues = ['True','TRUE','true', 'yes','YES','Yes', 1, 'Y', 'y']
        falses = ['False', 'FALSE', 'false', 'NO', 'No', 'no', 'N', 'n', 0]
        
        if bool_string in trues:
            return True
        
        elif bool_string in falses:
            return False
        

def str_to_dict(raw_str, container = dict, logger=mod_logger):
    
    if not str_is_dict(raw_str): 
        raise IOError('got unexpceted type \'%s\''%type(raw_str))
    
    
    
    try:
        d = eval(raw_str.strip())
    except:
        logger = logger.getChild('str_to_dict')
        logger.error("failed to convert \'%s\' to py thonic"%raw_str)
        raise IOError
    
    if not isinstance(d, dict): raise IOError
    
    return container(d)


        
def excel_str_to_py(raw_str, logger = mod_logger): #convert user input excel strings to pythonic
    if not isinstance(raw_str, str): return raw_str #short cut out

    raw_str = str(raw_str)
    #logger = logger.getChild('excel_str_to_py')
    
    #number
    if isnum(raw_str):
        new_value = float(raw_str)
        
    #list checking
    elif is_str_list(raw_str, logger = logger):
        new_value =  str_to_list(raw_str, logger = logger) #intelligently convert to a list
        'this always returns a list, we want to preserve non-list type entries'  
        
    #tuples
    elif is_str_tup(raw_str, logger = logger):
        new_value = str_to_tup(raw_str, logger = logger)
        
    #booleans
    elif str_is_bool(raw_str):
        new_value = str_to_bool(raw_str)
    
    #dictionaries
    elif raw_str.startswith('{'): #must be a dictionary
        raise IOError #todo this
    
    #nones
    elif str_is_none(raw_str): 
        new_value =  None
    
    #jsut a string                
    else:  
        new_value = str(raw_str) #non list string
        
    
    return new_value
    
    
def match_type( #attempt to return a new_obj matching the type of the old object
        old_obj, 
        new_raw,  
        logger=mod_logger, 
        db_f = False): 
    """
    this is very gross.. just typeset directly!
    """
    
    if old_obj is None: return new_raw
    if new_raw is None: return new_raw
    
    if db_f: 
        logger = logger.getChild('match_type')
    
    if isinstance(old_obj, float): 
        new_obj =  float(new_raw)
        
    elif hasattr(old_obj, 'shape'): 
        new_obj = new_raw
        
    elif isinstance(old_obj, bool): 
        new_obj =  bool(new_raw)
    
    elif isinstance(old_obj, int): 
        try:
            new_obj = int(new_raw)
        except:
            logger.warning('failed to typeset \'int\' onto \'%s\'. keeping type as %s'
                           %(new_raw, type(new_raw)))
            return new_raw

    elif isinstance(old_obj, str): 
        new_obj = str(new_raw)
        
    else:
        if db_f:
            logger.warning('no type match found for \'%s\''%type(old_obj))
            
    if db_f:
        if not isinstance(new_obj, type(old_obj)):
            if not isinstance(old_obj, str):
                logger.error('failed to match type from \'%s\' to \'%s\''%(type(old_obj), type(new_obj)))
                raise IOError

        
    return new_obj
    
    
    
#===============================================================================
# USER INTERFACE -------------------------------------------------------------
#===============================================================================
'for file operations with user interface, see above'



#===============================================================================
# def stdout_status(cnt, length, sfx = 'progress', prints = 10):
#     cnt = int(cnt)
#     if cnt%(length/prints) == 0:  #only output on the interval
#         sys.stdout.write("\r%s at %.1f%%" %(sfx, 100*cnt/float(length)))
#         sys.stdout.flush()
#         
#     elif cnt == length-1: 
#         sys.stdout.write("\r%s at %.1f%% \n" %(sfx, 100*cnt/float(length)))
#===============================================================================
    
    
# INSPECTION -----------------------------------------------------------------
#===============================================================================
# def log_curframe(logger=mod_logger):
#     import inspect
#     cframe = inspect.currentframe()
#     filename, lineno, function, code_context, index = inspect.getframeinfo(cframe)
#      
#     logger.debug('filename \'%s\', lineno \'%s\', function \'%s\', code_context \'%s\', index \'%s\''%
#                  (filename, lineno, function, code_context, index))
#===============================================================================
 
import collections

class OrderedSet(collections.MutableSet):

    def __init__(self, iterable=None):
        self.end = end = [] 
        end += [None, end, end]         # sentinel node for doubly linked list
        self.map = {}                   # key --> [key, prev, next]
        if iterable is not None:
            self |= iterable

    def __len__(self):
        return len(self.map)

    def __contains__(self, key):
        return key in self.map

    def add(self, key):
        if key not in self.map:
            end = self.end
            curr = end[1]
            curr[2] = end[1] = self.map[key] = [key, curr, end]

    def discard(self, key):
        if key in self.map:        
            key, prev, next = self.map.pop(key)
            prev[2] = next
            next[1] = prev
            
    def update(self, l):
        
        for item in l:
            self.add(item)
            
        return self
        

    def __iter__(self):
        end = self.end
        curr = end[2]
        while curr is not end:
            yield curr[0]
            curr = curr[2]

    def __reversed__(self):
        end = self.end
        curr = end[1]
        while curr is not end:
            yield curr[0]
            curr = curr[1]

    def pop(self, last=True):
        if not self:
            raise KeyError('set is empty')
        key = self.end[1][0] if last else self.end[2][0]
        self.discard(key)
        return key

    def __repr__(self):
        if not self:
            return '%s()' % (self.__class__.__name__,)
        return '%s(%r)' % (self.__class__.__name__, list(self))

    def __eq__(self, other):
        if isinstance(other, OrderedSet):
            return len(self) == len(other) and list(self) == list(other)
        return set(self) == set(other)

    def tolist(self):
        return list(self)

   
    
    