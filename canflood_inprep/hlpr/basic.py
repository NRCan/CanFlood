'''
Created on Feb. 7, 2020

@author: cefect

helper functions w/o qgis api
'''


#==============================================================================
# dependency check
#==============================================================================



#==============================================================================
# imports------------
#==============================================================================
#python
import os, configparser, logging
import pandas as pd
import numpy as np

mod_logger = logging.getLogger('hp') #creates a child logger of the root

# custom imports
if __name__ =="__main__": 
    from hlpr.exceptions import Error
else:
    from hlpr.exceptions import QError as Error

     

#==============================================================================
# functions-------------
#==============================================================================


def view(df):
    if isinstance(df, pd.Series):
        df = pd.DataFrame(df)
    import webbrowser
    #import pandas as pd
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
        #type(f)
        df.to_html(buf=f)
        
    webbrowser.open(f.name)
    
    
def is_null(obj): #check if the object is none

    if obj is None:
        return True
    """might not work for non string multi element objects"""
    if np.any(pd.isnull(obj)):
        return True
    
    #excel checks
    if obj in ('', 0, '0', '0.0'):
        return True
    
    return False

def linr( #fancy check if left elements are in right elements
        ldata_raw, rdata_raw, 
                  lname_raw = 'left',
                  rname_raw = 'right',
                  sort_values = False, #whether to sort the elements prior to checking
                  result_type = 'bool', #format to return result in
                    #missing: return a list of left elements not in the right
                    #matching: list of elements in both
                    #boolar: return boolean where True = left element found in right (np.isin)
                    #bool: return True if all left elements are found on the right
                    #exact: return True if perfect element match
                  invert = False, #flip left and right
                  
                  #expectations
                  dims= 1, #expected dimeions
                  
                  fancy_log = False, #whether to log stuff                  
                  logger=mod_logger
                  ):
    
    #===========================================================================
    # precheck
    #===========================================================================
    if isinstance(ldata_raw, str):
        raise Error('expected array type')
    if isinstance(rdata_raw, str):
        raise Error('expected array type')
    
    #===========================================================================
    # do flipping
    #===========================================================================
    if invert:
        ldata = rdata_raw
        lname = rname_raw
        rdata = ldata_raw
        rname = lname_raw
    else:
        ldata = ldata_raw
        lname = lname_raw
        rdata = rdata_raw
        rname = rname_raw
        
        
    #===========================================================================
    # data conversion
    #===========================================================================
    if not isinstance(ldata, np.ndarray):
        l_ar = np.array(list(ldata))
    else:
        l_ar = ldata
        
    if not isinstance(rdata, np.ndarray):
        r_ar = np.array(list(rdata))
    else:
        r_ar = rdata
        
    #===========================================================================
    # do any sorting
    #===========================================================================
    if sort_values:
        l_ar = np.sort(l_ar)
        r_ar = np.sort(r_ar)
        
        #check logic validty of result type
        if result_type =='boolar':
            raise Error('requested result type does not make sense with sorted=True')

        
    #===========================================================================
    # pre check
    #===========================================================================
    #check for empty containers and uniqueness
    for data, dname in (
        (l_ar, lname),
        (r_ar, rname)
        ):
        #empty container
        if data.size == 0:
            raise Error('got empty container for \'%s\''%dname)
        
        #simensions/shape
        """probably not necessary"""
        if not len(data.shape) == dims:
            raise Error('expected %i dimensions got %s'%(
                dims, str(data.shape)))
            
        
        if not pd.Series(data).is_unique:
            #get detailed print outs
            ser = pd.Series(data)
            boolidx = ser.duplicated(keep=False)            
            
            raise Error('got %i (of %i) non-unique elements for \'%s\' \n    %s'%(
                boolidx.sum(), len(boolidx), dname, ser[boolidx]))
        
        #=======================================================================
        # #uniqueness
        # if not data.size == np.unique(data).size:
        #     raise Error('got non-unique elements for \'%s\' \n    %s'%(dname, data))
        #=======================================================================
        
        """data
        data.shape
        
        """
        

    

    #===========================================================================
    # do the chekcing
    #===========================================================================

    boolar = ~np.isin(l_ar, r_ar) #misses from left to right
    
    if fancy_log:
        
        log = logger.getChild('left_in_right')
        msg = ('%i (of %i) elements in \'%s\'  not found in \'%s\': \n    mismatch: %s \n    \'%s\' %s: %s \n    \'%s\' %s: %s'
                    %(boolar.sum(),len(boolar), lname, rname, 
                      l_ar[boolar].tolist(),
                      lname, str(l_ar.shape), l_ar.tolist(), 
                      rname, str(r_ar.shape), r_ar.tolist()
                      )
                    )
        if np.any(boolar):
            logger.debug(msg)
        elif result_type=='exact' and (not np.array_equal(l_ar, r_ar)):
            logger.debug(msg)
        
    #===========================================================================
    # reformat and return result
    #===========================================================================
    if result_type == 'boolar': #left elements in the right
        return ~boolar
    elif result_type == 'bool': #all left elements in the right
        if np.any(boolar):
            return False
        else:
            return True
        
    elif result_type == 'missing':
        return l_ar[boolar].tolist()
    
    elif result_type == 'matching':
        return l_ar[~boolar].tolist()
    
    elif result_type == 'exact':
        return np.array_equal(l_ar, r_ar)
    
    else:
        raise Error('unrecognized result format')
    
def get_basefn(filepath):
    ftail, fhead = os.path.split(filepath)
    basefn, ext = os.path.splitext(fhead)
    return basefn
    
    

    
    
    
  
        
        
       
    