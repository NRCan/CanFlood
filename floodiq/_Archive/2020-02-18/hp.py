'''
Created on Feb. 7, 2020

@author: cefect

common helper functions for use across project
'''

#==============================================================================
# logger----------
#==============================================================================
import logging
mod_logger = logging.getLogger('hp') #creates a child logger of the root


#==============================================================================
# imports------------
#==============================================================================

import pandas as pd

class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, msg):
        mod_logger.error(msg)
        
        

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
    
    
    
  
        
        
       
    