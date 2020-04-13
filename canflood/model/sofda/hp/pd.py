'''
Created on Oct 25, 2017

@author: cef
'''

import logging, copy, os, time, inspect
import numpy as np
import pandas as pd
import xlrd #this is here to test the optional dependency

#import matplotlib.pyplot as plt
from collections import OrderedDict

#===============================================================================
# other helpers
#===============================================================================
import model.sofda.hp.basic as basic


mod_logger = logging.getLogger(__name__) #creates a child logger of the root

#===============================================================================
# pandas styling 
#===============================================================================
pd.set_option("display.max_columns", 7)
pd.set_option('display.width', 150)


def view_web_df(df):
    import webbrowser
    #import pandas as pd
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
        #type(f)
        df.to_html(buf=f)
        
    webbrowser.open(f.name)
    
def view(df):
    view_web_df(df)
    
#===============================================================================
# # SIMPLE MATH ------------------------------------------------------------------ 
#===============================================================================
def sum_occurances(df_raw, logger=mod_logger): #return a dictionary of counts per occurance
    """
    try value_counts()?
    """
    logger = logger.getChild('sum_occurances')
    df = df_raw.copy()
    l = np.unique(df).tolist()
    d = dict()
    #=======================================================================
    # loop and calc
    #=======================================================================
    logger.debug('looping through %i unique values: %s'%(len(l), l))
    for val in l:
        d[val] = (df == val).sum().sum()

    
    return d
        
        
    
    
#===============================================================================
# INTERPOLATION and SEARCH --------------------------------------------------------------
#===============================================================================
def Get_interp_header_dx2ser(df_raw, header_search, value_ask_raw, logger=mod_logger): # Vlookup. return row (series) at [value_ask, header_search]
    """"
    Most robust interpolator
    #===========================================================================
    # USE
    #===========================================================================
    interp_ser = hp_pd.Get_interp_header_dx2ser(df_raw, header_search, value_ask_raw)
    
    interp_value = interp_ser[header_desire]
    #===========================================================================
    # FUNCTION
    #===========================================================================
    add a row and interpolate all values. return row (series) at [value_ask, header_search]'
    'returns the whole row, which has been interpolated by the axis passed in the header_search
    allows for non-index interpolation (useful for aribtrary indexes)
    for time series (or other non-aribitrary indexes), see Get_interp_index_df2ser
    
    #===========================================================================
    # INPUTS
    #===========================================================================\
    df_raw:        data set (with header_search in columns)
    header_search = the header name from which to search for the value_ask
    value_ask_raw:    numeric value (on the header_search's column) from which to interoplate the other rows
    #===========================================================================
    # TESTING:
    #===========================================================================
    
    import sim.debug

    df = sim.debug.Get_curve_df()

    """
    'TODO: convert df index to float'
    'TODO: check if the passed header is in the columns'
    
    #===========================================================================
    # check inputs
    #===========================================================================
    if not isinstance(df_raw, pd.core.frame.DataFrame):
        logger.error('got undexpected type on df_raw: %s'%type(df_raw))
        raise TypeError
    
    #drop nan values
    df_raw =   df_raw.dropna(axis='index')
    
    value_ask = round(value_ask_raw, 2)
    
    #check if thsi value is outside of the passed column
    
    df = df_raw.astype(np.float) #convert the index to floats
    'there seems to be some problem with importing commas from excel'

    df_sort = df_raw.sort_values(by=header_search).reset_index(drop='true')
    
    if value_ask < df_sort.loc[0,header_search]:
        logger.error('asked value is outside the domain')
        return df_sort.loc[0,:]
    
    last_index = len(df_sort.index) -1
    if value_ask > df_sort.loc[last_index, header_search]:
        logger.error('asked value is greater than the serach domain: %.2f'%value_ask)
        return df_sort.iloc[last_index,:] #return the last row
    
    
    #check if interpolation is even needed 
    bool_row = df_raw.loc[:,header_search] == value_ask #search for value
    if sum(bool_row) == 1: #found one match
        results_ser = df_raw.loc[bool_row,:].iloc[0] #get this row
        return results_ser
    
    elif sum(bool_row) >1: #found multiple matches
        df_trim = df_raw.loc[bool_row,header_search]
        logger.error('found too many existing matches in search: \n %s'%df_trim)
        raise ValueError
    
    #builda  new df with the header_search as the index 
    'I think there is a better command for this'
    index = list(df_raw.loc[:,header_search])

    
    bool_col = df_raw.columns != header_search #get the remaining 
    col = df_raw.columns[bool_col]
    
    data = df_raw.loc[:,bool_col].values #get all this data

    df = pd.DataFrame(data = data, index = index, columns = col )
    
    ser = pd.Series(data=None, index= col) #dummy row for adding
    df.loc[value_ask,:] = ser #add this in at teh requested row
    
    #resort the frame
    df_interp = df.sort_index() 
    
    #convert each value to numeric
    for col in df_interp: df_interp[col] = pd.to_numeric(df_interp[col], errors='coerce')
        
    #interpolate the missing values
    'WARNING: all methods (except linear) interpolate based on the index'
    df_new = df_interp.interpolate(method='values')
    
    #Extract interpolated row    
    results_ser = df_new.ix[value_ask] #get the results row
    results_ser.loc[header_search] = value_ask #add teh search value/header back
    
    return results_ser

def Get_interp_ser(ser_raw, index_ask_raw, logger=mod_logger): #get the corresponding value for the passed index using the series
    """TESTING
    index_ask = 52
    
    """
    logger.debug('performing interpolation for index_ask: %.2f'%index_ask_raw)
    #===========================================================================
    # check inputs
    #===========================================================================
    if not isinstance(ser_raw, pd.core.series.Series):
        logger.error('got undexpected type on ser_raw: %s'%type(ser_raw))
        raise TypeError
    
    'todo: check that the index is numeric'
    
    index_ask = float(round(index_ask_raw, 2)) #round/convert ask
    ser = ser_raw.copy(deep=True)
    ser.index = ser_raw.index.astype(np.float) #convert the index to floats

    #===========================================================================
    #check if interpolation is even needed 
    #===========================================================================
    bool = ser.index == index_ask #search for value
    if sum(bool) == 1: #found one match
        value = float(ser[index_ask]) #get this row
        return value
    
    elif sum(bool) >1: #found multiple matches
        logger.error('found too many existing matches in search: \n %s'%ser)
        raise ValueError
    
    #===========================================================================
    # perform inerpolation
    #===========================================================================
    ser = ser.set_value(index_ask, np.nan) #add the dummy search value
    
    #resort the frame
    ser = ser.sort_index() 
    
    #convert each value to numeric
    #for value in df_interp: df_interp[col] = pd.to_numeric(df_interp[col], errors='coerce')
    
    ser_interp = ser.interpolate(method='values')
    
    #get the requested value
    
    value = float(ser_interp[index_ask])
    
    return value

def Get_interp_index_df2ser(df_raw, index_ask_raw, logger=mod_logger): #get the corresponding value for the passed index using the series
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    df_raw:    dataframe with numeric or time series index
    index_ask_raw: new index value where you want a row to be interpolated on
    
    #===========================================================================
    # LIMITATION
    #===========================================================================
    I believe the linear interpolater just splits the difference between the bounding rows
    
    TESTING
    index_ask = 52
    type(df_raw)
    """
    logger.debug('performing interpolation for index_ask: %s'%index_ask_raw)
    #===========================================================================
    # check inputs
    #===========================================================================
    if not isinstance(df_raw, pd.core.frame.DataFrame):
        logger.error('got undexpected type on df_raw: %s'%type(df_raw))
        raise TypeError
    
    if index_ask_raw < df_raw.index[0]:
        logger.error('got an index outside the bounds of the passed frame: \n %s'%df_raw.index)
        raise IOError
    

    index_ask = index_ask_raw

    #===========================================================================
    # # check if interpolation is even needed 
    #===========================================================================
    bool = df_raw.index == index_ask #search for value
    if sum(bool) == 1: #found one match
        ser = df_raw.loc[bool].iloc[0] #get this row
        return ser
    
    elif sum(bool) >1: #found multiple matches
        logger.error('found too many existing matches in search: \n %s'%index_ask)
        raise ValueError
    
    #===========================================================================
    # perform inerpolation
    #===========================================================================

 
    new_row = pd.DataFrame(index = [index_ask], columns = df_raw.columns)
    
    df = df_raw.append(new_row).sort_index()
    
    df_interp = df.interpolate(method='linear')
    
    #get the requested value
    
    ser = df_interp.loc[index_ask, :]
    
    return ser
  
def gen_ser_keyvalue(keys_ser, kv_df, value_head = 'rank', logger=mod_logger): #generate a response series
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    keys_ser:    series of values on which to generate a response from the kv mapping
    kv_df:        dictionary like frame where 
            col1_values = keys (found in keys_ser)
            col2_values = values corresponding to the keys
            
    search_header:    header defining the values column
    
    """
    
    logger = logger.getChild('gen_ser_keyvalue')
     
    #===========================================================================
    # build the dictionary
    #===========================================================================
    key_head = keys_ser.name #header of keys

    if not header_check(kv_df, [key_head,value_head ]): raise IOError
    
    #efficietnly build a dictionary from two columns
    keys = kv_df.loc[:,key_head].values
    values =  kv_df.loc[:,value_head].values
    dictionary = pd.Series(values,index=keys).to_dict()
    
    #===========================================================================
    # get the values
    #===========================================================================
    df = pd.DataFrame(keys_ser)
    df[value_head] = df.iloc[:,0] #create a second column and fill it with the key entries

    df1 = df.replace({value_head: dictionary }) #replace the entries with the dictionary
    
    return df1[value_head]

def search_str_fr_list(ser, #find where items have all the items in the search_str_list
                       search_str_list, case=False, all_any = 'all',
                       logger=mod_logger):  
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    all_any: flag denoting how to to treat the combined conditional
        all: find rows where every string in the list is there
        any: find rows where ANY string in the list is there
    """
    
    logger = logger.getChild('search_str_fr_list')
    
    if not isser(ser): raise IOError
    
    #starter boolidx series
    df_bool = pd.DataFrame(index = search_str_list, columns = ser.index)
    
    #loop through and find search results for each string
    for index, row in df_bool.iterrows():
        boolcol = ser.astype(str).str.contains(index, case=case)
        
        df_bool.loc[index,:] = boolcol.values.T
        
    #find the result of all rows
    if all_any == 'all':
        boolidx = df_bool.all()
    elif all_any == 'any':
        boolidx = df_bool.any()
    else: 
        logger.error('got unexpected kwarg for all_any: \'%s\''%all_any)
        raise IOError
    logger.debug('found %i series match from string_l (%i): %s'
                 %(boolidx.sum(), len(search_str_list), search_str_list))
    
    if boolidx.sum() == 0: 
        logger.warning('no matches found')


            
    return boolidx
            
    

#===============================================================================
#  IMPORTS --------------------------------------------------------------------
#===============================================================================

def slice_df_from_file(df_raw, slicefile_path, #slice a df with values found in an external slicefile
                       spcl_srch = '*', drop_omits=True, logger=mod_logger): 
    """
    #===========================================================================
    # ARCHITECTURE
    #===========================================================================
    The external slicefile contains the logic on which to slice:
        slicing columns: any columns NOT found in the slicefile will be sliced OUT
        slicing rows: if only a header is provided in the slice file, no data will be sliced
            if values are provided under a header in the slice file, data not matching this will be sliced OUT
            
        values ending in * will be searched for any strings containing the value
    #===========================================================================
    # INPUTS
    #===========================================================================  
    slicefile_path:    file path to csv with headers and values on which to slice
    
        
    df_raw:        df to slice with slicefile data
    
    drop_omits: flag for header omission treatment
        True:    if the header is missing, the column is dropped
        False:    do nothing on missing headers
    
    #===========================================================================
    # TESTING
    #===========================================================================
    view_df(df_raw)
    """
    logger = logger.getChild('slice_df_from_file')
    logger.debug('on df_raw  (%i cols x %i indx) from slice_file:\n    %s'
                 %(len(df_raw.columns), len(df_raw.index), slicefile_path))
    
    #===========================================================================
    # #check and attach slice file
    #===========================================================================
    if not os.path.exists(slicefile_path):
        if slicefile_path is None: 
            logger.error('no slicefile entered')
            raise IOError
        logger.error('passed slicefile does not exist: \n     %s'%slicefile_path)
        raise IOError
        
    #load the slice file
    'imports without headers. headers are kept on row 0 for manipulation as data'
    slicefile_df_raw = pd.read_csv(slicefile_path,
                     header = None,
                     index_col=False,
                     skipinitialspace=True)
    
    #===========================================================================
    # clean the slice file
    #===========================================================================
    #strip leading/trailing zeros from the first row
    slicefile_df_clean0 = slicefile_df_raw.copy(deep=True)
    slicefile_df_clean0.iloc[0,:] = slicefile_df_raw.iloc[0,:].str.strip()
    
    #drop any rows with all nan
    slicefile_df_clean1 = slicefile_df_clean0.dropna(axis='index', how='all')
    slicefile_df_clean2 = slicefile_df_clean1.dropna(axis='columns', how='all').reset_index(drop='true') #drop any columns with all na
    
    #strip trailing zerios
    slicefile_df_clean = slicefile_df_clean2
        
    if len(slicefile_df_clean) == 0:
        logger.info('no values selected for slicing. returning raw frame')
        return df_raw
    
    #===========================================================================
    # slice columns
    #===========================================================================
    slice_head_list = slicefile_df_clean.iloc[0,:].values.tolist() #use the first row
    
    #make sure all these passed headers are found in the data
    if not header_check(df_raw, slice_head_list, logger = logger): 
        os.startfile(slicefile_path)
        raise IOError
    
    if drop_omits:
        boolhead = df_raw.columns.isin(slice_head_list)
        
        df_head_slice = df_raw.loc[:,boolhead] #get just the headers found in the first row of the slicer
    else:
        df_head_slice = df_raw.copy(deep=True)
    
    #===========================================================================
    # #manipulate the slice df to match header dtype as expected
    #===========================================================================
    #boolcol_indata = slicefile_df_clean.columns.isin(df_raw.columns)
    
    slicefile_df2_clean = slicefile_df_clean.copy(deep=True)
    slicefile_df2_clean.columns = slicefile_df2_clean.iloc[0,:] #reset teh columns
    slicefile_df2_clean = slicefile_df2_clean.iloc[1:,:] #drop the first row
    
    if len(slicefile_df2_clean) == 0:
        logger.warning('no slicing values provided')
        
    
    #=======================================================================
    # build the boolidx from teh slicefile_df
    #=======================================================================
    #start with bool of all trues
    boolidx_master = pd.DataFrame(~df_raw.loc[:,slicefile_df2_clean.columns[0]].isin(df_head_slice.columns))
    
    
    for header, col in slicefile_df2_clean.items(): #loop through each column and update the logical df
        
        slice_list = list(col.dropna())
        
        if len(slice_list) == 0: #check that we even want to slice this
            logger.debug('no slicing values given for header %s'%header)
            continue
        
        boolcol = df_head_slice.columns == header #select just this column
        
        #=======================================================================
        # build the slice boolidx
        #=======================================================================
        if spcl_srch in str(slice_list): #check for the special search flag
            #===================================================================
            # special search
            #===================================================================
            boolidx = ~boolidx_master.iloc[:,0]
            for search_value in slice_list:
                boolidx_new = df_head_slice[header].astype(str) == search_value
                if isinstance(search_value, str):
                    if search_value.endswith('*'): #special search
                        new_sv = search_value[:-1] #drop the asterisk
                        
                        #overwrite the boolidx
                        boolidx_new = df_head_slice[header].astype(str).str.contains(new_sv)
                        
                        logger.debug("contains search found %i entries on header %s"%
                                          (boolidx.sum(), header))
                    else: pass
                else: pass #just leave the original boolidx
            
                boolidx = np.logical_or(boolidx, boolidx_new) #get the logical cmululation of all these
            logger.info('special search on \'%s\' found %i entries'%(header, boolidx.sum()))
            boolidx = pd.DataFrame(boolidx)
        else: #normal search
            boolidx = df_head_slice.loc[:,boolcol].astype(str).isin(slice_list) #find the rows where (on this column) the values are contained in the list
                
        '''
        df_head_slice.loc[:,boolcol]
        '''
        #check that we havent sliced all the data

        if not boolidx.any(axis=0)[0]:
            logger.debug('slicefile_path: \n    %s'%slicefile_path)
            logger.warning('slicing col \'%s\' found no rows with values \n    %s'%(header, slice_list))

        
        boolidx_master = np.logical_and(boolidx_master, boolidx) #get df of logical AND combination of two child dfs
        
        logger.debug('on header: %s slicing found %i entries matching: \n %s'%(header, len(boolidx), slice_list))
    
    #=======================================================================
    # get final slice
    #=======================================================================
    df_slice = df_head_slice.loc[boolidx_master.iloc[:,0],:]
    
    if len(df_slice.index) < 1:
        logger.error('sliced out all rows')
        raise IOError
    
    if len(df_slice.columns) <1:
        logger.error('sliced out all columns')
        raise IOError
    
    cleaner_report(df_raw, df_slice, cleaner_name ='slice', logger= logger)
    
    return df_slice


def load_smart_df(filepath, logger = mod_logger, **kwargs):
    
    if filepath.endswith('.csv'):
        return load_csv_df(filepath, logger = logger, **kwargs)
    
    if filepath.endswith('.xls'):
        return load_xls_df(filepath, logger = logger, **kwargs)
    
    else:
        raise IOError

def load_csv_df(filepath,  
                test_trim_row = None, #for partial loading, stop at this line
                header = 0,  #Row number(s) to use as the column names, and the start of the data. 
                                #fofor dxcol, pass a list of the column names
                index_col = 0, #for 
                skip_blank_lines = True, 
                skipinitialspace = True, 
                skiprows = None,
                parse_dates=True, 
                sep = ',', 
                logger=mod_logger,
                **kwargs):
    
    #===========================================================================
    # defaults
    #===========================================================================
    logger = logger.getChild('load_csv_df')
    if not test_trim_row is None: test_trim_row = int(test_trim_row)
    
    #===========================================================================
    # prechecks
    #===========================================================================
    if not os.path.exists(filepath): 
        logger.error('passed filepath does not exist: %s'%filepath)
        raise IOError
    
    if not filepath.endswith('.csv'): 
        raise IOError
    
    if (not isinstance(header, int)) and (not header is None): #normal state
        if not isinstance(header, list):
            raise IOError
        else:
            for v in header:
                if not isinstance(v, int): 
                    raise IOError
    
    """
    header = [0,1]
    
    hp_pd.v(df_raw)
    """
    
    try: #default engine
        df_raw = pd.read_csv(filepath,
                             header = header, index_col=index_col, skip_blank_lines = skip_blank_lines,
                                    skipinitialspace=skipinitialspace, skiprows = skiprows, 
                                    parse_dates=parse_dates,sep = sep,
                                    **kwargs)
        
    except: 
        try: #using the python engine
            df_raw = pd.read_csv(open(filepath,'rU'), encoding='utf-8', engine='python',
                             header = header, index_col=index_col,skip_blank_lines = skip_blank_lines,
                                    skipinitialspace=skipinitialspace, skiprows = skiprows,
                                    parse_dates=parse_dates,sep = sep,
                                    **kwargs)
            
            logger.debug('loaded successfully using python engine')
            
        except:
            logger.error('failed to load data from %s'%filepath)
            raise IOError
        
    logger.debug('loaded df %s from file: \n    %s'%(df_raw.shape, filepath))
    

    #=======================================================================
    # trim for testing flag
    #=======================================================================
    if not test_trim_row is None: 
        df = df_raw.iloc[0:test_trim_row,:] #for testing, just take the first 100 rows
        logger.warning('TEST FLAG=TRUE. only loading the first %i rows'%test_trim_row)
    else:
        df = df_raw.copy(deep=True)
        
    #===========================================================================
    # format index
    #===========================================================================
    df1 = df.copy(deep=True)
    try:
        df1.index = df.index.astype(np.int)
    except:
        logger.warning('failed to convert index to numeric')
    
       
    return df1

def load_xls_df(filepath, logger=mod_logger, 
                test_trim_row = None,  
                sheetname = 0,
                header = 0,  #Row number(s) to use as the column names, and the start of the data. 
                index_col = 0,
                parse_dates=False, 
                skiprows = None,
                convert_float = False, 
                **kwargs):
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    sheetname: None returns a dictionary of frames
        0 returns the first tab
        
    #===========================================================================
    # KNOWN ISSUES
    #===========================================================================
    converting TRUE/FALSE to 1.0/0.0 for partial columns (see pandas. read_excel)
    
    """
    #===========================================================================
    # defaults
    #===========================================================================
    logger = logger.getChild('load_xls_df')
    if not test_trim_row is None: test_trim_row = int(test_trim_row)
    
    #===========================================================================
    # prechecks
    #===========================================================================
    if not filepath.endswith('.xls'): raise IOError('got unexpected file extension: \'%s\''%filepath[:-4])
    if not isinstance(filepath, str): raise IOError
    'todo: add some convenience methods to append xls and try again'
    if not os.path.exists(filepath): 
        raise IOError('passed filepath not found: \n    %s'%filepath)
    
    if parse_dates: raise IOError #not impelmented apparently..
    

        
    #===========================================================================
    # loader
    #===========================================================================
    try:
        df_raw = pd.read_excel(filepath,
                sheet_name = sheetname,
                header = header,
                index_col = index_col, 
                skiprows = skiprows,
                parse_dates = parse_dates,
                convert_float = convert_float,
                engine = None,
                formatting_info = False,
                verbose= False,
                **kwargs)
    except:
        raise IOError('unable to read xls from: \n    %s'%filepath)
    
    #===========================================================================
    # post checks
    #===========================================================================
    if not isdf(df_raw):
        if not sheetname is None: raise IOError
        if not isinstance(df_raw, dict): raise IOError 
        logger.debug('sheetname = None passed. loaded as dictionary of frames')
        
        df_dict = df_raw
        
        for tabname, df_raw in df_dict.items():
            #=======================================================================
            # trim for testing flag
            #=======================================================================
            df = None
            if not test_trim_row is None: 
                if test_trim_row < len(df_raw):
                    df = df_raw.iloc[0:test_trim_row,:] #for testing, just take the first 100 rows
                    logger.warning('TEST FLAG=TRUE. only loading the first %i rows'%test_trim_row)
        
            if df is None:
                df = df_raw
                
            df_dict[tabname] = df #update the dictionary
            
        return df_dict
        
    logger.debug('loaded df %s from sheet \'%s\' and file: \n    %s'%(df_raw.shape, sheetname, filepath))
    #=======================================================================
    # trim for testing flag
    #=======================================================================
    df = None
    if not test_trim_row is None: 
        if test_trim_row < len(df_raw):
            df = df_raw.iloc[0:test_trim_row,:] #for testing, just take the first 100 rows
            logger.warning('TEST FLAG=TRUE. only loading the first %i rows'%test_trim_row)

    if df is None:
        df = df_raw
    
       
    return df

def load_xls_d(filepath, #load a xls collection of tabs to spreadsheet
               logger=mod_logger, **kwargs):
    
    #===========================================================================
    # defaults
    #===========================================================================
    logger = logger.getChild('load_xls_d')    
    
    #===========================================================================
    # setup
    #===========================================================================
    df_d = OrderedDict() #creat ehte dictionary for writing
    
    #get sheet list name
    xls = xlrd.open_workbook(filepath, on_demand=True)
    sheetnames_list =  xls.sheet_names()
            
    logger.debug('with %i sheets from %s: %s'%(len(sheetnames_list),filepath, sheetnames_list))
    
    for sheetname in sheetnames_list:
        logger.debug('on sheet: \'%s\' \n'%sheetname)
        #pull the df from the file and do the custom parameter formatting/trimming
        df_raw  = load_xls_df(filepath, sheetname = sheetname, 
                                                logger = logger,
                                                **kwargs)
        
        if len(df_raw) < 1: 
            logger.error('got no data from tab \'%s\' in %s '%(sheetname, filepath))
            raise IOError
        
        df_d[sheetname] = df_raw #update the dictionary
        
    logger.debug('loaded %i dfs from xls sheets: %s'%(len(list(df_d.keys())), list(df_d.keys())))
        
    return df_d
    

            
    
            

#===============================================================================
# CONVERSIONS ----------------------------------------------------------------
#===============================================================================
def force_dtype_from_tplate(df_raw, templatefile_path, logger=mod_logger): #force the df column dtype to match that provided in the template
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    templatefile_path:    filepath to a csv with row0: header, row1: dtype (str, float, int, datetime, None)
    df:    dataframe on which to map the passed type
    
    #===========================================================================
    # TESTING
    #===========================================================================
    view_df(df_raw)
    """
    logger=logger.getChild('dtype_tplate')
    logger.debug('force_dtype_from_tplate from template file:\n    %s'%templatefile_path)
    #===========================================================================
    # checks
    #===========================================================================
    if not os.path.exists(templatefile_path): raise IOError
    if not isdf(df_raw): raise IOError
    
    #load the template file
    template_df = pd.read_csv(templatefile_path,
                    header = 0,
                    index_col=False)
    
    template_ser = pd.Series(template_df.iloc[0,:])
       
    """ Im leaving this out for testing as Im using the large data format template 
    #check that the headers match
    DFColumnCheck(template_df,df.columns)
    """
    df = df_raw.copy(deep=True)
    
    for header, col in df_raw.items(): #loop through each column
        
        if not header in template_ser.index:
            logger.warning('could not find \' %s \' in teh template file'%header)
            continue
            
        dtype_str = template_ser[header]
        
        if pd.isnull(dtype_str):
            logger.debug('no dtype found in template for %s'%header)
            continue
        
        elif dtype_str == 'datetime':
            df.loc[:,header] = pd.to_datetime(col) #send this back to the df as a datetime
            
        elif dtype_str == 'float':
            try:
                df.loc[:,header] = col.astype(np.float64, copy=False)
            except:
                logger.error('failed to convert header %s to float'%header)
                raise IOError
            
        elif dtype_str == 'int':
            try:
                df.loc[:,header] = col.astype(np.dtype(int), copy=False)
            except:
                logger.error('failed to convert header %s to integer from tplate file: \n %s'%(header,templatefile_path ))
                raise IOError
                
        elif dtype_str == 'str':
            df.loc[:,header] = col.astype(np.dtype(str), copy=False)
        
        else:
            logger.warning('got unexpected value for dtype = %s on %s' %(dtype_str, header))
            raise IOError
                           
        logger.debug('changed dtype on %s to %s'%(header, dtype_str))
        
    #===========================================================================
    # check
    #===========================================================================
    df_check = df.dropna(axis='columns', how='all')
    df_raw_chk = df_raw.dropna(axis='columns', how='all')
    logger.debug('dropped nas and checking if we lost any columns')
    
    if not len(df_check.columns) == len(df_raw_chk.columns):
        cleaner_report(df_check, df_raw, cleaner_name = 'clean_df_frmt ERROR', logger = logger)
        logger.error('some columns were lost in teh formatting')
        raise IOError
    
    return df

def df_to_1line_dict(df_raw, convert_none=True, logger=mod_logger): #convert the first two rows of a df into a dictionary
    'builtin to_dict doesnt handle single entry dictionaries'
    
    keys_list = []
    values_list = []
    
    if not len(df_raw.index) == 1:
        logger.error('got unepxected shape of df')
        raise IOError
    
    for header, col in df_raw.items():
        if header.startswith('Unnamed'):
            if convert_none:
                keys_list.append(None)
            else:
                logger.warning('found Unnamed header: \'%s\' but convert_none flag =False'%header)
        else:
            keys_list.append(header)
        
        value = col[0]
        
        values_list.append(value)
        
    dictionary = dict(list(zip(keys_list, values_list))) #zip these into a dcit
    
    return dictionary

def convert_headers_frm_dict(df_raw, old_new_d, logger=mod_logger): #converts the passed header names to those in the dictionary and reorders
    logger = logger.getChild('convert_headers_frm_dict')
    df = df_raw.copy(deep=True)
    
    new_headers = [] #headers from the passed dictionary
    focus_headers = [] #renamed headers in the dataset
    extra_headers = []
    
    for header in df.columns:
        if header in old_new_d: #convert me
            conv_head = old_new_d[header]
            
            if conv_head is None: raise IOError
            if pd.isnull(conv_head): raise IOError
            
            new_headers.append(conv_head)
            focus_headers.append(conv_head)
            logger.debug('converting \'%s\' to \'%s\''%(header, conv_head))
        else: #no conversion here
            extra_headers.append(header)
            new_headers.append(header)
            
    #apply the new headers
    df.columns = new_headers
    
    logger.debug('renamed %i headers: \n    %s'%(len(focus_headers), focus_headers))
    

    #===========================================================================
    # reorder the columns
    #===========================================================================
    new_head_ordr = sorted(focus_headers) + extra_headers
    df_ordr = df[new_head_ordr]
     
    if not len(df_ordr.columns) == len(df_raw.columns):
        logger.error('lost some columns')
        raise IOError
    
    logger.debug('reordered headers')
     
    return df_ordr

def dict_to_ser(key_ser, dictionary): #generates a series from the dictionary keys
    
    new_ser = pd.Series(index=key_ser.index, dtype = key_ser.dtype)
    
    for index, entry in key_ser.items():
        
        new_ser[index] = dictionary[entry]
        
    return new_ser

def ser_fill_df(ser, rows, logger = mod_logger): #fill a dataframe with this series
    """
    #===========================================================================
    # INPUT
    #===========================================================================
    rows: count of row length for dummy df 
    """
    if not isser(ser): raise IOError
    
    #buidl blank frame for writing
    df = pd.DataFrame(index = list(range(0, rows)), columns = ser.index.values)
    
    #loop through and fill
    for index, row in df.iterrows(): df.iloc[index,:] = ser.values.tolist()
        
    return df

def right_fill_df_atts(obj, att_names_list, df_raw, logger=mod_logger): #add a dummy block of attribute values to the df_raw
    logger = logger.getChild('right_fill_df_atts')
    #=======================================================================
    #pull values from self
    #=======================================================================
    def_ser = pd.Series(index = att_names_list)
    
    for att_name in att_names_list:
        if not hasattr(obj, att_name):
            logger.error('passed obj does not have an attribute \'%s\''%att_name)
            raise IOError
        
        att_value = getattr(obj, att_name) #get this attribute
        def_ser[att_name] = att_value #fill it out
        
    #fill the frame
    dummy_df = ser_fill_df(def_ser, len(df_raw), logger = logger)
    
    #append these
    df_merge = pd.merge(df_raw, dummy_df, how = 'left', right_index=True, left_index=True)
    
    if not len(df_merge) == len(df_raw): raise IOError
    
    logger.debug('added %i new columns to make df_merge %s: %s'
                 %(len(att_names_list), str(df_merge.shape), att_names_list))
    
    
    return df_merge

def right_fill_df_dict(right_dict, df_raw, logger=mod_logger): #add a dummy block of attribute values to the df_raw
    logger = logger.getChild('right_fill_df_dict')
    #=======================================================================
    #pull values from self
    #=======================================================================
    def_ser = pd.Series(right_dict)

    #fill the frame
    dummy_df = ser_fill_df(def_ser, len(df_raw), logger = logger)
    
    #append these
    df_merge = pd.merge(df_raw, dummy_df, how = 'left', right_index=True, left_index=True)
    
    if not len(df_merge) == len(df_raw): raise IOError
    
    logger.debug('added %i new columns to make df_merge %s: %s'
                 %(len(right_dict), str(df_merge.shape), list(right_dict.keys())))
    
    
    return df_merge

def concat_many_heads(df_raw, heads_list, concat_name = 'concat', sep = ' ', #combine many columns into one string 
                      logger=mod_logger): 
    
    #=======================================================================
    # concat the columns of interest 
    #=======================================================================
    df1 = df_raw.copy(deep=True)
    
    for index, col in enumerate(heads_list):
        if index ==0:
            df1[concat_name] = df_raw[col].map(str)
            continue
        
        ser = df_raw[col].map(str)
        
        df1[concat_name] = df1[concat_name].str.cat(ser, sep= sep)
        
    return df1
            
            
    
class Head_translator(): #object for translating headers
    def __init__(self, filepath, Parent):
        
        self.Parent  = Parent
        self.logger  = Parent.logger.getChild('tr')
        self.filepath = filepath
        self.name   = 'Head_translator'
        
        if not os.path.exists(filepath): raise IOError
        
        self.load_dict(filepath)
        
        self.logger.debug('initilzied')
        
    def load_dict(self, filepath,  #load the tr_dict from file
                  header = 0, index_col = False, skip_blank_lines=True, skipinitialspace=True,
                  **kwargs):
        
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        tr_filepath: filepath to csvcontaining tr_dict
            row1:    header name foundin raw data
            row2:    header name to map onto frame (new harmonized name
                BLANK of omitted = no translation done
        
        tr_dict: header translation is performed with external translation dictionaries
            key: raw header
            value: new header

        """
        
         
        logger = self.logger.getChild('load_dict')
        
        logger.debug("loding dictionary from:\n     %s"%filepath)

        df_raw = pd.read_csv(filepath,
                         header = header,
                         index_col=index_col,
                         skip_blank_lines=skip_blank_lines,
                         skipinitialspace=skipinitialspace, **kwargs)
        
        df = clean_dropna(df_raw, logger=self.logger)
        
        self.tr_dict = df_to_1line_dict(df, convert_none=True, logger=self.logger)
                
        return self.tr_dict
    
    def translate(self, df_raw, expect_heads = None):
        logger = self.logger.getChild('translate')
        
        logger.debug('performing on df_raw %s'%str(df_raw.shape))
        
        #=======================================================================
        # #make the translation
        #=======================================================================
        df1    = convert_headers_frm_dict(df_raw, self.tr_dict, logger=logger)
        
        return df1
#===============================================================================
# OUTPUTS --------------------------------------------------------------------
#===============================================================================
def write_to_file(filename, data, #write the df to a csv. intelligent
                  overwrite=False,
                  float_format=None, 
                  index=False, #write the index?
                  logger=mod_logger, **kwargs ): 
    
    logger=logger.getChild('write_to_file')

    # checks
    if not isdf(data):
        if not isser(data): 
            raise TypeError
    
    #===========================================================================
    # defaults
    #===========================================================================
    if not filename.endswith('.csv'): filename = filename + '.csv'
        
    if overwrite == False: #don't overwrite
        if os.path.isfile(filename): #Check whether file exists 
            logger.warning('File exists already: \n %s'%filename)
            raise IOError
        
    #=======================================================================
    # root folder setup
    #=======================================================================
    head, tail = os.path.split(filename)
    if not os.path.exists(head): os.makedirs(head) #make this directory

    #===========================================================================
    # writing
    #===========================================================================
    try:
        data.to_csv(filename, float_format = float_format, index=index, **kwargs)
        logger.info('df %s written to file: \n     %s'%(str(data.shape), filename))
    except:
        logger.warning('WriteDF Failed for filename: \n %s'%filename)
        logger.debug('df: \n %s'%data)
        raise IOError
    
    return 

def df_to_logger(df_raw, logger = mod_logger, row_print_count = 10): #log large dfs

    if not isinstance(df_raw, pd.core.frame.DataFrame):
        logger.error('got unexpected type for passed df: %s'%type(df_raw))
        raise IOError
    
   
    df = df_raw.copy(deep=True)
    
    #change the display options
    with pd.option_context('display.max_rows', None, 
                           'display.max_columns', None,
                           'display.height',1000,
                           'display.width',1000):
        
        logger.debug('\n %s \n \n \n \n'%df)
        
def write_dfset_excel(df_set_dict, filepath, #write a dictionary of frames to excel
                      engine='xlsxwriter', logger=mod_logger, **kwargs): 
    
    
    #===========================================================================
    # setup defaults
    #===========================================================================
    logger=logger.getChild('write_dfset_excel')
    if not filepath.endswith('.xls'): filepath = filepath + '.xls'
    
    #===========================================================================
    # make the root folder
    #===========================================================================
    head, tail = os.path.split(filepath)
    if not os.path.exists(head): os.makedirs(head)
        
    #===========================================================================
    # data setup
    #===========================================================================
    """NO! use the provided order
    #sort the dictionary by key
    od = OrderedDict(sorted(df_set_dict.items(), key=lambda t: t[0]))"""
    #===========================================================================
    # #write to multiple tabs
    #===========================================================================
    writer = pd.ExcelWriter(filepath, engine=engine)
    
    for df_name, df in df_set_dict.items():
        logger.debug("on \'%s\'"%df_name)
        if not isdf(df):
            if not isser(df):
                logger.debug('got unexpected type on bundled data: \'%s\'. attempting to convert'%type(df))
                try: df = pd.DataFrame([df])
                except:
                    raise IOError

        if len(df) == 0: continue #skip empty frames
        try:
            df.to_excel(writer, sheet_name=str(df_name), **kwargs)
        except:
            logger.error('failed to write df %s'%df_name)
            raise IOError
        
    writer.save()
    logger.info('wrote %i frames/tab to:  %s'%(len(list(df_set_dict.keys())), filepath))
    
def sort_workbook(filename): #sort xls by tab name
    'not working'
    import xlsxwriter


    workbook = xlsxwriter.Workbook(filename)
    
    # sort sheets based on name
    workbook.worksheets_objs.sort(key=lambda x: x.name)
    workbook.close()
    
def val_to_str(val): #intelligently generate a value string by type
    
    if isinstance(val, float): return '%.4f'%val
    
    if hasattr(val, 'shape'): return str(val.shape)
    
    return str(val)

def write_fly_df( #write the first row of the df 
        filepath, 
        data, 
                lindex = None, #how to start this line in the file
                 first=False, #indicator for the first call
                 tag='',
                 db_f = False,
                 logger=mod_logger): #
    
    """
    setup to handle series, df, or dxcol
    """
    logger = logger.getChild('write_fly_df')
    
    if len(data) == 0:
        logger.warning('got empty data. skipping')
        return
    
    #===========================================================================
    # defaults
    #===========================================================================
    if isinstance(data, pd.Series):
        headers = data.index
        data_ar = data.values
        if lindex is None: lindex = data.name
        
    elif isinstance(data, pd.DataFrame):
        headers = data.columns
        data_ar = data.iloc[0].values
        if lindex is None: lindex = data.index[0]
    else:
        logger.error('got unexpected type for data %s'%type(data))
        raise IOError
    
    #===========================================================================
    # prechecks
    #===========================================================================
    if db_f:
        if not os.path.exists( os.path.dirname(filepath)):
            raise IOError

        


    #===========================================================================
    # make writes
    #===========================================================================
    with open(filepath, 'a') as f: #re open and append to the file
        #=======================================================================
        # headers
        #=======================================================================
        if first:
            logger.debug('first file write. setting up %i headers of t ype \'%s\''%(len(headers), type(headers)))
            f.write('%s,'%tag)
            
            #===============================================================
            # normal 1Dcolumns
            #===============================================================
            if not isinstance(headers, pd.MultiIndex):
                for k in headers:
                    #print k, v
                    f.write('%s,'%k)
                    
                f.write('\n') #start a new line
            #===============================================================
            # mdex columns
            #===============================================================
            else:
                mdex = headers
                first = True
                for name in mdex.names: #loop through each level
                    l = mdex.get_level_values(name).values.tolist() #get all the values at this level
                    
                    #lindex
                    if first: first = False
                    else:
                        'for the first line this slot is taken up by the session tag'
                        f.write('%s,'%name)
                    
                    
                    #write each of these
                    for k in l:
                        f.write('%s,'%k)
                    f.write('\n') #start a new line
                
                logger.debug('stored mdex headers with %i levels: %s'%(mdex.nlevels, mdex.names))

        #=======================================================================
        # write the indexer
        #=======================================================================
        f.write('%s,'%lindex)

        #======           =================================================================
        # write the values
        #=======================================================================
        for v in data_ar: #just taking the values from the first row. SHOULD ONLY HAVE 1 ROW!
            f.write('%s,'%v) #write ht evalues
        
        f.write('\n') #start a new line   
        
    logger.debug('appended %i entries under \'%s\' to file %s'%
                 (len(data_ar), lindex, filepath))
    
    return 
    




# CHECKING --------------------------------------------------------------------- 
def is_multi(obj):
    
    if isinstance(obj, float): return False
    #check if its numpy
    if type(obj).__module__ == np.__name__: return True
    
    #check if its pandas
    if type(obj).__module__ == pd.__name__: return True
    
    return False
    
def isdf(df, logger=mod_logger): #check if this is a df
    
    
    if df is None: return False

    if not isinstance(df, pd.core.frame.DataFrame):
        #logger.debug('got undexpected type on passed obj: %s'%type(df))
        return False
    
    return True
    

    
def isser(ser, logger=mod_logger):
    
    logger=logger.getChild('isser')
    
    if not isinstance(ser, pd.core.series.Series):
        #logger.error('got unexpected dtype: %s'%type(ser))
        return False
    else: return True
    
def ismdex(mdex, logger=mod_logger): #check if this is an mdex
    
    logger = logger.getChild('ismdex')
    
    
    if not isinstance(mdex, pd.core.indexes.multi.MultiIndex):
        #logger.debug('got unexpected dtype: %s'%type(mdex))
        return False
    else: return True
    
def isdxcol(df, logger=mod_logger):
    
    if isdf(df):
        if ismdex(df.columns, logger=logger):
            return True
        
    logger.debug('passed df is not a dxcol')
    return False

def isdxind(df, logger=mod_logger):
    
    if isdf(df):
        if ismdex(df.index, logger=logger):
            return True
        
    logger.debug('passed df is not a dxind')
    return False

def smart_isdx(df, logger=mod_logger): #intelligent dx checking
    logger = logger.getChild('smart_isdx')
    #===========================================================================
    # basic checks
    #===========================================================================
    if isdxcol(df, logger=logger): return True
    if isdxind(df, logger=logger): return True
    
    #check the index
    boolidx = pd.isnull(df.index)
    if boolidx.sum() > 0:
        logger.warning('got nan entries on the index. may be a dx col')
        return 'maybe'
    
    #check if the index is an integer
    """
    int_cnt = 0
    for entry in df.index:
        try:
            _ = int(entry)
            int_cnt = int_cnt +1
        except: pass
            
    if not int_cnt == len(df.index):
        logger.warning('found mismatacfh on type count. may be a dx col')
        return 'maybe'
    """
    
    return False

        
                        
    
        

    
def header_check(obj, expected_headers, return_list = False, logger = mod_logger): #check that all the expected headers are found in teh df
    """
    #===========================================================================
    # INPUTS
    #===========================================================================
    return_list: flag whether to return the list of headers not found in the data set (as second output)
    expected_headers:    list of headers to check against the passed dataset
    
    """
    'todo: allow for index checking as well'
    #===========================================================================
    # build logger
    #===========================================================================
    logger = logger.getChild('header_check')
      
    #===========================================================================
    # check for data type  and assign axis for checking
    #===========================================================================
    'takes either a series or a dataframe'
    if isinstance(obj, pd.core.frame.DataFrame): #check for df
        data_labels = list(obj.columns)
        
    elif isinstance(obj, pd.core.series.Series): #check for series
        data_labels = list(obj.index)
    else:
        logger.error('Expected type: df. found type: %s'%type(obj))
        raise TypeError
    
    #===========================================================================
    # check for header match
    #===========================================================================
    flag = []
    unfound_headers = []
    for header in expected_headers: #loop thorugh each header and see if it exists
    
        if not header in data_labels: #check that each manditory header is found in the inventory
            msg = 'expected header: \'%s\' not found in headers: \n     %s'%(header, data_labels)
            flag.append(msg)
            unfound_headers.append(header)
            
    #===========================================================================
    # print out all the flags
    #===========================================================================
    if len(flag) > 0:
        for msg in flag: logger.warning(msg)
        
        if return_list: 
            return False, unfound_headers
            
        return False
    
    else:
        if return_list:
            return True, unfound_headers
        return True  
    
def get_entries_missing(ser, ve_list, logger=mod_logger): #get entries on ve_list not foundin df_raw
    
    logger = logger.getChild('get_entries_missing')
    if not isser(ser): raise IOError
    
    ve_ser = pd.Series(ve_list)
    
    excluded_ser = ve_ser[~ve_ser.isin(ser)]
    
    return list(excluded_ser.values)
    
def are_dupes(df_raw, colname = None, logger=mod_logger, keep=False, #check if theer are any duplicates
              **kwargs): 
    """
    colname = None: check for duplicates on all rows
    colname = 'index': check for duplicates on the index
    """
    
    logger = logger.getChild('are_dupes')
        
    if not isinstance(colname, list): #normal single column check
        
        if colname == 'index':
            boolidx = df_raw.index.duplicated(keep=keep)
        else:
            boolidx = df_raw.duplicated(subset = colname, keep=keep) #identify every entry and its twin
        

    else:
        """
        Here we want to find duplicate PAIRS
            this is different from identifying rows with values duplicated internally
            we want coupled duplictaes
            
        """
        
        #merge the columsn to check on
        chk_colnm = 'checker'
        df1 = concat_many_heads(df_raw, colname, concat_name = chk_colnm, logger=logger)
        
        #find where there are internal duplicates on thsi merged column
        boolidx = df1.duplicated(subset = chk_colnm, keep=keep) #identify every entry and its twin
         
        """
        df1.columns.tolist()
        view_df(df1[boolidx])
        df2 = df1[colname + [chk_colnm]]
        df2.loc[:,'chk'] = boolidx.values
        view_df(df2)
        
        df3 = df2[boolidx]
        view_df(df3)
        """
   #===========================================================================
    # closeout and report
    #=========================================================================== 
    if np.any(boolidx):
        logger.debug('found %i (of %i) duplicates on \'%s\' '%(boolidx.sum(),len(df_raw), colname))
        return True, boolidx
    else:
        return False, boolidx


def get_conflicts_bool(df_raw, header='head', logger=mod_logger):
    
    logger = logger.getChild('get_conflicts_bool')
    
        
    #get a unique frame
    df_uq = df_raw.drop_duplicates(header)
    
    #identify those entires that were dropped
    boolidx = ~df_raw.index.isin(df_uq.index)
    
    #get a frame of the dropped entries
    df_nuq = df_raw[boolidx]
    
    #get a list of the header values that were in teh dropped entries
    head_nuq_list = df_nuq[header].values
    
    #identify all the entries that share these values
    con_boolidx = df_raw[header].isin(head_nuq_list)
    
    logger.debug('identified %i of %i conflict entries'%(con_boolidx.sum(), len(df_raw)))
    
    return con_boolidx

def Get_bool_list(series, check, logger=mod_logger): #return bool of whether check is in value_list (of each cell)
    'checking if list format entries have a match to the passed check (single or list)'
    'see Series.isin for series to list checking'
    
    bool_list = []
    check = str(check)

    #if not type(check) == type('a'): raise TypeError

    for index, value in series.items():
        
        try: #for values in list form
            value_list = value.split(',')
            value_list = list(map(str, value_list))
            if check in value_list: bool_list.append(True)
            else: bool_list.append(False)
        except: #for integer values
            if np.isnan(value): bool_list.append(True) #postive treatment of empty cells
            elif str(value) == check: bool_list.append(True)
            else: bool_list.append(False)
             
    bool = np.array(bool_list)
    
    return bool    

def check_false_boolcol(df_raw, convert=True, logger=mod_logger): #trys to detect booleans
    """
    #===========================================================================
    # USEr
    #===========================================================================
    Here were checking for imprpoerly inputed user information (incomplete bool columns)
    
    make sure the whole raw frame is passed here (not a slice)
    """ 
    if len(df_raw) < 2: return False, []
    logger = logger.getChild('check_false_boolcol')
    found = []
    
    #===========================================================================
    # initial cleaning
    #===========================================================================
    df1 = df_raw.dropna(axis='columns', how='all') #drop all the columns
    'need to make su re the whole row isnt empty'
    
    
    for colname, col in df1.items():
        
        if col.dtype == np.bool: 
            continue
        
        elif np.any(pd.isnull(col)): #must contain some null
            
            logger.debug("on \'%s\' found %i nulls"%(colname, pd.isnull(col).sum()))
            
            """
            df1[pd.isnull(col)]
            """
            
            col1 = col.dropna()
            
            if len(col1) == 0: continue #ignore columns with all nans
            
            #find entries that look like missed booleans
            bool1 = col1.values == 1.0
            bool2 = col1.values == 0.0
            bool3 = col1.values == 1
            bool4 = col1.values == 0
            
            #identify all non NAN entries that may be booleans
            bool_cmb = np.logical_or(np.logical_or(bool1, bool2), np.logical_or(bool3, bool4))
            
            if bool_cmb.sum() == len(col1):  #every non-NAN is a boolean... something is wrong
                found.append(colname)
                
    
    if len(found) >0:        
    
        logger.warning('found %i columns which may be incomplete boolcols: %s'%(len(found), found))
        return True, found
    
    else:
        logger.debug('found no false booleans')
        
        return False, []
    


def log_full_df(df, logger=mod_logger): #override display defaults and log the full frame
    return #need to revisit this with the new pandas version
    #log the full data set
    with pd.option_context('display.max_rows', None, 
                           'display.max_columns', None,
                           'display.height',1000,
                           'display.width',1000):

        
        logger.debug('\n %s'%df)
        
def fancy_null_chk(df,
                   detect='boolean', #what to do if nulls are detected
                   dname='?', #data name
                   logger=mod_logger,):
    
    #===========================================================================
    # see if we have any nulls
    #===========================================================================
    if np.any(pd.isnull(df)):
        boolidx = df.isna().any(axis=1)
        boolcol = df.isna().any(axis=0)
        logger.warning('\'%s\' found %i entries (and %i cols) with nulls \n%s'%
                     (dname, boolidx.sum(), boolcol.sum(), df.loc[boolidx, boolcol]))
        
        if detect == 'boolean':
            return True
        elif detect=='error':
            raise IOError('cleaning \'%s\' got %i nulls. check log'%(dname, pd.isnull(df).sum().sum()))
        else:
            raise IOError('unrecognized detect kwarg: %s'%detect)
    
    #===========================================================================
    # wrap
    #===========================================================================
    if detect=='error':
        return #no need to return booleans in this case
    else: 
        return False
        

    
#===============================================================================
# SET OPERATIONS -------------------------------------------------------------
#===============================================================================
def merge_left(left_df_raw, right_df_raw, #intelligently add the right_df to the left with the 'on' colname
          on=None,  #column name to link between the two frames
          left_index=True, 
          right_name = 'right', 
          allow_partial = False, 
          trim_dupes = True, 
          allow_new_cols = False, 
          outpath = None,  #outpath for saving results to file
          logger = mod_logger,
          db_f = True): 
    """
    #===========================================================================
    # USe
    #===========================================================================
    This is useful for taking a frame (left_df) with some data and a keys column
    then adding a bunch more data per those keys (from the right_df)
    
    for example:
        survey results for each 
        and attaching all the assessment records for those
    """
    #===========================================================================
    # setup
    #===========================================================================
    logger = logger.getChild('merge_left')
    if on is None: left_index = True
    else:
        if not on in right_df_raw.columns: raise IOError
        if not on in left_df_raw.columns: raise IOError
        
    #===========================================================================
    # pre clean
    #===========================================================================
    right_df1 = right_df_raw.dropna(axis='columns', how='all')
    left_df = left_df_raw.dropna(axis='columns', how='all')
    
    if 'dataname' in right_df1.columns: 
        right_df2 = right_df1.drop('dataname', axis=1)
    else:
        right_df2 = right_df1
            
    #=======================================================================
    # prechecks
    #=======================================================================
    if db_f:
        if not isdf(left_df_raw): raise IOError
        if not isdf(right_df_raw): raise IOError
        if not len(left_df_raw) > 0: raise IOError
        if not len(right_df_raw) > 0: raise IOError
        
    
        #check for nulls on the left linking columns
        if np.any(pd.isnull(left_df_raw.loc[:,on])): 
            boolidx = pd.isnull(left_df_raw.loc[:,on])
            logger.error('found %i entries on left search col \'%s\' with null value'%(boolidx.sum(), on))
            log_full_df(left_df_raw[boolidx], logger=logger)
            raise IOError
        
        if on is None: 
            raise IOError #todo: add this
        
        if not on in right_df2.columns:
            logger.error('\'%s\' column was dropped during cleaning'%on) 
            raise IOError
        
        if not on in left_df.columns: 
            raise IOError
    
    logger.debug('joining left_df (%s) to right_df (%s)'%(str(left_df_raw.shape), str(right_df_raw.shape)))
    
    
    
    #=======================================================================
    # data cleaning
    #=======================================================================   
    #trim the right to just those values from the left
    boolidx = right_df2.loc[:,on].isin(left_df.loc[:,on])
    right_df21 = right_df2.loc[boolidx,:]
    
    #check for a match
    if not boolidx.sum() == len(left_df):
        logger.warning('only found %i matches (of %s)'%(boolidx.sum(), str(left_df.shape)))
        if not allow_partial: 
            raise IOError
        
    #===========================================================================
    # check for duplicates in source frames
    #===========================================================================
    #search col in teh elft
    flag, boolidx = are_dupes(left_df, colname = on, logger=logger)
    if flag: 
        logger.error('found  %i internal duplicates on passed left_df %s'%(boolidx.sum(), str(left_df.shape)))
        if boolidx.sum() < 100: log_full_df(left_df[boolidx], logger=logger) 
        raise IOError
    
    #check for duplicated index
    flag, boolidx = are_dupes(left_df, colname = 'index')
    if flag: 
        logger.error('found %i duplicated indicies on left_df'%boolidx.sum())
        raise IOError
    
    #check the right frame
    flag, boolidx = are_dupes(right_df2, colname = on, logger=logger)
    if flag: 
        logger.warning('found  %i internal duplicates on passed right_df %s. taking first'%(boolidx.sum(), str(right_df1.shape)))
        if boolidx.sum() < 100: log_full_df(right_df_raw[boolidx], logger=logger)
        if not trim_dupes: raise IOError
        else: right_df3 = right_df21.drop_duplicates(on)
        
    else: right_df3 = right_df21
    
    #===========================================================================
    # check for unexpected column matching
    #===========================================================================
    boolcol = left_df.columns.isin(right_df3.columns)
    if not boolcol.sum() ==1:
        logger.warning('found %i extra column matches between frames: %s'%(boolcol.sum(), left_df.columns[boolcol]))
        if not allow_new_cols: raise IOError
    
    #===========================================================================
    # #check if we need to upgrade to an mdex
    #===========================================================================
    if isdxcol(left_df):
        logger.debug('merging with a dxcol. upgrading right_df')
        if isdxcol(right_df1): raise IOError
        
        #get teh data from the left
        old_mdex = left_df.columns
        lvl0_vals = old_mdex.get_level_values(0).unique() 
        names = [old_mdex.names[0], right_name]
        
        #make the dummpy dxcol
        right_df4 = fill_dx_col(right_df3, lvl0_vals, names, logger=logger) #get this
        
        #perform teh merge
        merge_df = merge_dxcol(left_df, right_df4, on = on, logger=logger)
        
    else: 
        #=======================================================================
        # perform merge
        #=======================================================================
        merge_df = pd.merge(left_df, right_df3, 
                            on = on,
                            how = 'left',
                            left_index = False,
                            right_index = False, 
                            left_on = None,
                            right_on = None,
                            sort = False,
                            indicator = False)
    
    #=======================================================================
    # post checks
    #=======================================================================
    if db_f:
        if not len(merge_df) == len(left_df): 
            raise IOError
        
        if not np.all(merge_df.index.isin(left_df.index)): 
            raise IOError
        
        #check for duplicated index
        flag, boolidx = are_dupes(merge_df, colname = 'index')
        if flag: 
            logger.error('found %i duplicated indicies in merge_df: '%(boolidx.sum()))
            log_full_df(merge_df[boolidx])
            raise IOError
    
    
    logger.debug('to left %s filled %s to make merge_df %s. attached as data'
             %(str(left_df.shape), str(right_df3.shape), str(merge_df.shape)))
    
    #===========================================================================
    # file write
    #===========================================================================
    if not outpath is None:
        """
        v(merge_df)
        """
        filename = os.path.join(outpath, 'merge.csv')
        write_to_file(filename, merge_df)
    
    return merge_df

def fillna_fancy(left_df_raw, fill_df_raw, #fill the holes in the left_df_raw with the right
                 on = None, #cross section column name
                 supress = None, 
                 sysout_f = True, 
                 logger = mod_logger): 
    """
    try using pd.where instead
    #===========================================================================
    # USE
    #===========================================================================
    This is useful for taking a dataset with holes in it (na values) (left_df)
    and filling those holes with data from another data set (fill_df_raw) matching they keys (on)
    
    for example:
        a set of partial assessment records for each 
        filing in teh missing records from an older data set
        
    To run this against a string of datasets with filling of new columns, see merge_rnk_choice()
    #===========================================================================
    # TODO
    #===========================================================================
    add support for on= None (index matching)
    """
    #===========================================================================
    # setup
    #===========================================================================
    logger = logger.getChild('fillna_fancy')
    
    if supress is None: 
        if len(left_df_raw) > 100: supress = True
    
    """
    view_df(left_df_raw)
    view_df(fill_df_raw)
    
    view_df(fill_df_raw[boolidx]).
    
    view_web_df(fill_df_raw[boolidx])
    
    """
    #===========================================================================
    # cleaning
    #===========================================================================
    left_df = left_df_raw.copy(deep=True)
    left_df.index
    #===========================================================================
    # prechecks
    #===========================================================================
    flag, boolidx = are_dupes(fill_df_raw, colname = on)
    if flag: 
        logger.error('found %i duplicates in the fill_df'%boolidx.sum())
        raise IOError
    
    flag, boolidx = are_dupes(left_df_raw, colname = on)
    if flag: raise IOError
    
    flag, boolidx = are_dupes(left_df_raw, colname = 'index')
    if flag: 
        logger.error('found %i duplicated indicies on left_df'%boolidx.sum())
        raise IOError
    
    boolidx = pd.isnull(left_df_raw.loc[:,on])
    if boolidx.sum() > 0: 
        logger.error('found %i entries on left search col \'%s\' with null value'%(boolidx.sum(), on))
        log_full_df(left_df_raw[boolidx], logger=logger)
        raise IOError
    
    #===========================================================================
    # columns
    #===========================================================================
    #only use those columns from teh fill that are also in the left
    boolcol = fill_df_raw.columns.isin(left_df.columns)
    fill_df1 = fill_df_raw.loc[:,boolcol]
    
    delta = len(fill_df_raw.columns) - boolcol.sum()
    if delta > 0:
        logger.debug('%i columns from the fill do not match the left. dropping: %s'%(delta, fill_df_raw.columns[boolcol]))
    
    #===========================================================================
    # indicies
    #===========================================================================
    boolind = fill_df1.loc[:,on].isin(left_df.loc[:,on]) #find where the search values match
    fill_df2 = fill_df1[boolind]
    
    delta = len(fill_df_raw) - boolind.sum()
    if delta > 0:
        logger.debug('%i rows from the fill_df dont match. dropping'%delta)
                                 

    #===========================================================================
    # loop through and fill by row
    #===========================================================================
    oldna_cnt = pd.isnull(left_df).sum().sum()
    logger.debug('filling %s (%i nulls) with %s row by row'%(str(left_df.shape),oldna_cnt, str(fill_df2.shape)))
    

    for index, row in left_df.iterrows():
        
        match_val = row[on] #get the matching value
        
        #get the row with this matching value
        boolidx = fill_df2.loc[:,on] == match_val
        if boolidx.sum() == 0:
            msg = 'for \'%s\' = %s, found no matches in the fill data. skipping'%(on, match_val)
            if not supress: logger.warning(msg)
            else: logger.debug(msg)
            continue
        if not boolidx.sum() == 1: 
            raise IOError
        fill_ser = fill_df2.loc[boolidx,:].iloc[0]

        try:
            left_df.loc[index,:] = row.fillna(fill_ser) #update the df with this
        except:
            pass
        #=======================================================================
        # report
        #=======================================================================
        oldna_bool = pd.isnull(row)
        newna_bool = pd.isnull(left_df.loc[index,:])
        
        delta = oldna_bool.sum() - newna_bool.sum()
        
        logger.debug('for index %i. filled %i nulls with %i values'%(index, oldna_bool.sum(), delta))
        
        #=======================================================================
        # if sysout_f: 
        #     basic.stdout_status(index, len(left_df), sfx = 'fillna_fancy')
        #=======================================================================

        
    newna_cnt = pd.isnull(left_df).sum().sum()
    delta = oldna_cnt - newna_cnt
    
    logger.debug('filled %i nas (of %i) for %s'%(delta, oldna_cnt, str(left_df.shape)))
    
    return left_df
                
def merge_rnk_choice(left_df_raw, right_df_raw, ranking_col, ranked_l, #fill the left with the right using the rnk_d to rank entries
          on=None, left_index=True, right_name = 'right', 
          allow_partial = False, trim_dupes = True, logger = mod_logger):
    
    
    """
    #===========================================================================
    # USE
    #===========================================================================
    Takes an iniital frame with records for each key (on) )(left_df)
    and fills it with data from the right frame (with duplicate entrires for some keys)
    duplicates are resolved by ranking the values found in the ranking_col
    
    for example:
        a skinny data set on  field responses
        attaching a huge dataset of assessment records (with multiple years)
        but using only the most recent assessment records
        unless those records are missing, then take the next oldest year
        
    basically, this combines
        step1: merge_left
        step2,3,4... fillna_fancy (with a slice of each value in ranked_l)
    
    """
    
    #===========================================================================
    # setup
    #===========================================================================
    logger = logger.getChild('merge_rnk_choice')
    
    if on is None: raise IOError
    else:
        if not on in right_df_raw.columns: raise IOError
        if not on in left_df_raw.columns: 
            logger.debug('passed on = \'%s\' not found in the left_df columns'%on)
            raise IOError
    
    #=======================================================================
    # prechecks
    #=======================================================================
    if not isdf(left_df_raw): raise IOError
    if not isdf(right_df_raw): raise IOError
    if not len(left_df_raw) > 0: raise IOError
    if not len(right_df_raw) > 0: raise IOError
    
    logger.debug('joining left_df (%s) to right_df (%s) using %i ranked search values on right_col \'%s\''
                 %(str(left_df_raw.shape), str(right_df_raw.shape), len(ranked_l), ranking_col))
    
    #=======================================================================
    # data cleaning
    #=======================================================================
    #drop nulls
    right_df1 = right_df_raw.dropna(axis='columns', how='all')
    left_df = left_df_raw.dropna(axis='columns', how='all')
    
    #drop the datanames
    if 'dataname' in right_df1.columns:  right_df2 = right_df1.drop('dataname', axis=1)
    else: right_df2 = right_df1
    
    #post cleaning check
    if on is None: raise IOError #todo: add this
    if not on in right_df2.columns: raise IOError         
    if not on in left_df.columns: raise IOError
    
    #trim the right to just those values from the left
    boolidx = right_df2.loc[:,on].isin(left_df.loc[:,on])
    right_df21 = right_df2.loc[boolidx,:]
    
    if not boolidx.sum() == len(left_df):
        logger.warning('only found %i matches (of %s)'%(boolidx.sum(), str(left_df.shape)))
        if not allow_partial: raise IOError
        
    #check for duplicates
    flag, boolidx = are_dupes(left_df, colname = 'index')
    if flag: 
        logger.error('found %i duplicated indicies on left_df'%boolidx.sum())
        raise IOError
        
    #===========================================================================
    # rank choice filling
    #===========================================================================
    for index, value in enumerate(ranked_l):
        
        #get this slice from the right
        boolidx = right_df21.loc[:,ranking_col] == value #find the matching values
        r_df_slice = right_df21[boolidx]
        
        #=======================================================================
        # iprechecks
        #=======================================================================
        if not len(r_df_slice)>0: raise IOError
        
        #duplicates on the source frame
        flag, boolidx = are_dupes(r_df_slice, colname = on) #check for duplicates here
        if flag:
            
            logger.warning('found %i dupes in the source slice %s when \'%s\' = %s, dropping'
                           %(boolidx.sum(), str(r_df_slice.shape), ranking_col, value))
            
            if not trim_dupes: raise IOError
            'todo: consider moving this into the fill_na_fancy'
            
            r_df_slice2 = r_df_slice.drop_duplicates(subset=on, keep='first')
        else:
            r_df_slice2 = r_df_slice.copy()
        #=======================================================================
        # simple merge for first run
        #=======================================================================
        if index == 0: #start with a simple merge
            logger.debug('merging with %s slice from col \'%s\' = %s'%(str(r_df_slice2.shape), ranking_col, value))
            
            #fill with this slice
            merge_df = merge_left(left_df, r_df_slice2, 
                  on=on, left_index=left_index, right_name = right_name, 
                  allow_partial = allow_partial, trim_dupes = trim_dupes, logger = logger)
            

        #=======================================================================
        # for the rest, fill in the blanks
        #=======================================================================
        else: #do a fancy fill for the other ones
            logger.debug('filling with %s slice from col \'%s\' = %s'%(str(r_df_slice2.shape), ranking_col, value))
            
            merge_df = fillna_fancy(merge_df, r_df_slice2, on, logger = logger)
        
    logger.debug('finished with merge_df %s'%str(merge_df.shape))
    return merge_df
    

    

def union(left_df_raw, right_df_raw, #combine unique entries from both frames and duplicate entries from left
          on=None, left_col_keep = False, right_index = False, 
          logger = mod_logger):
    """
    finds the union on
        columns: inner union (columsn shared by both)
        index: outer union (all left values and unique right values) (per 'on' colname)
        
    #===========================================================================
    # IUNPUTS    
    #===========================================================================
    on:    None: check for duplicates on index
        list of colnames to check for duplicates on
        
    left_col_keep: whether to ensure all the columns from teh left frame are preserved
        rather tahn doing a true column union (only cols found in both)
    """

    logger = logger.getChild('union')

    
    #=======================================================================
    # prechecks
    #=======================================================================
    if not isdf(left_df_raw):raise IOError
    if not isdf(left_df_raw):raise IOError
    #===========================================================================
    # preclean
    #===========================================================================
    left_df1 = clean_dropna(left_df_raw)
    right_df1 = clean_dropna(right_df_raw)
    
    #===========================================================================
    # check for duplicates in source frames
    #===========================================================================
    flag, boolidx = are_dupes(left_df1, colname = on, logger=logger)
    if flag: 
        logger.error('found internal duplicates on passed left_df')
        raise IOError
    
    flag, boolidx = are_dupes(right_df1, colname = on, logger=logger)
    if flag: 
        raise IOError
        
    
    
    #===========================================================================
    # column unions
    #===========================================================================
    
    left_boolcol = left_df1.columns.isin(right_df1.columns)
    
    logger.debug('cols: left (%i) shares %i with right (%i)'
                 %(len(left_df1.columns), left_boolcol.sum(), len(right_df1.columns)))
    
    if not left_boolcol.sum() == len(left_df1.columns):
        if left_col_keep:
            logger.warning('some columns from left not fou nd in right. keeping left')
            left_df2 = left_df1.copy()
        else:
            logger.warning('some columns from left not fou nd in right. trimming left')
            left_df2 = left_df1.loc[:,left_boolcol] #only take matching ones
            
    else: left_df2 = left_df1.copy()
    
    
    
    #trim right
    right_boolcol = right_df1.columns.isin(left_df1.columns)
    right_df2 = right_df1.loc[:,right_boolcol]
    
    #===========================================================================
    # index unions
    #===========================================================================

    if on is None: #perform merge on index
        
        left_boolind = left_df2.index.isin(right_df2.index)
        right_boolind = right_df2.index.isin(left_df2.index)
         
    else: #perform merge on some header
        if not isinstance(on, list): on = list(on) #convert this to a list
        
        if not np.any(left_df2.columns.isin(on)): raise IOError
        if not np.any(right_df2.columns.isin(on)): raise IOError

        #find where the values match
        try: #for multiple on
            left_boolind = left_df2.loc[:,on].isin(right_df2.loc[:,on]).any(axis=1)
            right_boolind = right_df2.loc[:,on].isin(left_df2.loc[:,on]).any(axis=1)
        except: #for single on
            'thsis houldnt trigger even if on is a single entry list'
            left_boolind = left_df2.loc[:,on].isin(right_df2.loc[:,on])
            right_boolind = right_df2.loc[:,on].isin(left_df2.loc[:,on])
    #===========================================================================
    # get uniques
    #===========================================================================
    if right_boolind.sum() > 0:
        logger.debug('found %i non-unique entries in right from \'%s\''%(right_boolind.sum(), on))
        
    right_df_uq1 = right_df2.loc[~right_boolind,:] #get all teh unique entries from the right
        
                
    #===========================================================================
    # perform merge
    #===========================================================================
    """
    here we just lump all the entries from the left with the unique e ntries from teh right
    """    
    merge_df = left_df2.append(right_df_uq1, ignore_index = True)
    
    logger.debug('merged left %s with right %s to get %s'
                 %(str(left_df2.shape), str(right_df_uq1.shape), str(merge_df.shape)))
    
    """
    right_df_uq1.columns
    view_web_df(merge_df)
    """
    #===========================================================================
    # post checks
    #===========================================================================
    #check the index length

        
    expected_ind_cnt = len(left_df1) + len(right_df1) - left_boolind.sum()
    if not len(merge_df) == expected_ind_cnt: 
        raise IOError
    
    #check columns
    if left_col_keep:
        expected_col_cnt = len(left_df1.columns)
    else:
        expected_col_cnt =  left_boolcol.sum()
        
    if not len(merge_df.columns) == expected_col_cnt:
        raise IOError
    
    return merge_df
    
#===============================================================================
#CLEANING and FORMATTING---------------------------------------------------------------------
#===============================================================================
def clean_dropna(df_raw, logger=mod_logger): #drop all na values
    logger=logger.getChild('dropna')
    
    df_clean1 = df_raw.dropna(axis='columns', how='all') #drop any columns with all na values
    
    df_clean2 = df_clean1.dropna(axis='index', how='all') #drop any rows with all na values
    
    df_clean = df_clean2
    
    rows_delta = len(df_raw.index) - len(df_clean.index)
    if rows_delta < 0 : raise IOError
    
    if len(df_clean) == 0:
        logger.warning('dropped all rows')
        
    cleaner_report(df_raw, df_clean, logger = logger)
    
    return df_clean

def clean_datapars(df_raw,  #typical formatting for cleaning a datapars df
                   kill_flags = ['stop'], #row indexer to exclude all entries below
                   ignore_flags = ['~'],  #row indexer to exclude THIS entry
                   logger=mod_logger): 
    """
    not really data pars... using this for user data files also
    #===========================================================================
    # INPUTS
    #===========================================================================
    kill_flags: all rows below and columns to the right of this are dropped (inclusive)
    ignore_flag: drops all rows containing this flag
    
    """
    logger=logger.getChild('clean_datapars')
    
    #===========================================================================
    # prechecks
    #===========================================================================
    if len(df_raw) == 0:
        raise IOError
    #===========================================================================
    # cleaning
    #===========================================================================
    #by kill_flag
    df1 = df_raw.copy()
    for kill_flag in kill_flags: #loop through and trim for each kill_flag
        df1 = clean_kill_flag(df1, kill_flag = kill_flag, logger = logger)
    
    #drop by ignore_flag
    df2 = df1.copy()
    for ignore_flag in ignore_flags:
        df2 = clean_ignore_flag(df2, ignore_flag = ignore_flag, logger = logger)
        
    # drop empty rows
    df2 = df2.dropna(axis=0, how='all') #drop any rows with all na values

    # drop 'unnamed' columns
    boolcol = df2.columns.str.contains('Unnamed:')
    df3 = df2.loc[:, ~boolcol]
    
    #strip leading/trailing whitespace from column names
    df3.columns = df3.columns.str.strip()
    
    """
    hp_pd.v(df3)
    I dont want to lose the headers even if the columns are empty
    df2 = clean_dropna(df1)"""
    
    #===========================================================================
    # #formating
    #===========================================================================
    #the names column
    df4 = df3.copy()
    'this has to go after the drop na otherwise it convers the nans to strings'

    if 'name' in df4.columns:
        try: 
            df4['name'] = df4['name'].astype(str)
        except:
            raise IOError('failed to convert a names column to string')
        
        if np.any(df4.duplicated(subset = 'name')):
            logger.debug('%s'%df4['name'].values.tolist())
            raise IOError('got some duplicates on the names column: %s'
                          %df4.loc[df4.duplicated(subset = 'name'), 'name'].values.tolist())
       
        
    

    #=======================================================================
    # special datapars formatting
    #=======================================================================
    df5 = df4.copy()
    #rank column
    df5['rank'] = df5.index
    
    
    #===========================================================================
    # post checks
    #===========================================================================
    if len(df5) <1: 
        logger.warning('got len <1, returning')
        return df5
    
    
    #for missed boolean columns
    flag, found = check_false_boolcol(df5, logger = logger)
    if flag:
        for entry in found: #only run check on those columns with the _f suffix
            if entry.endswith('_f'): 
                """excel reads dont seem to handle TRUE/FALSE with nulls"""
                raise IOError('false boolean on \'%s\''%entry)

    return df5
"""
view(df5)
"""

def clean_kill_flag(df_raw, #clean the data frame with kill_flags
                    kill_flag = 'stop', logger=mod_logger, case = False):
    
    'useful for quick trims of large data by inserting STOP into the spreadsheet'
    logger = logger.getChild('clean_kill_flag')
    if len(df_raw) == 0: 
        raise IOError
    #===========================================================================
    # trim rows with kill_flag
    #===========================================================================
    df1 = df_raw.copy()
    
    """
    ser = df1.iloc[:,0].astype(str)
    
    ser.str.contains('~', case = False)
    
    """
    
    if np.any(df1.iloc[:,0].astype(str).str.contains(kill_flag, case = case)):
        
        boolidx = df1.iloc[:,0] == kill_flag  #identify locations with the kill_flag
        
        kf_loc = boolidx.values.argmax() #get location of first occurance
            
        df1 = df1.iloc[:kf_loc,:] #make this trim
        logger.debug('found kill_flag = \'%s\' at rank %i'%(kill_flag, kf_loc))
        
    #===========================================================================
    # trim columns with kill_flag
    #===========================================================================
    df2 = df1.copy()
    ser = pd.Series(df2.columns, dtype = str)
    if np.any(ser.str.contains(kill_flag, case = case)):
        
        boolidx = ser == kill_flag  #identify locations with the kill_flag
        
        kf_loc = boolidx.values.argmax() #get location of first occurance
            
        df2 = df2.iloc[:,:kf_loc] #make this trim
        logger.debug('found kill_flag = \'%s\' at rank %i'%(kill_flag, kf_loc))
        
    """
    v(df2)
    v(pd.DataFrame(boolidx))
    v(df1)
    """
    if len(df2) == 0: 
        logger.warning('cleaned to empty frame')
        #time.sleep(1)
        """allow this
        raise IOError"""
    #===========================================================================
    # wrap up
    #===========================================================================
    cleaner_report(df_raw, df2, logger = logger)
    
    return df2

def clean_ignore_flag(df_raw, #clean the data frame with ignore_flags
                    ignore_flag = '~', logger=mod_logger, case = False):
    
    'useful for quick trims of large data by inserting STOP into the spreadsheet'
    if len(df_raw) == 0: return df_raw 
        #raise IOError
    #===========================================================================
    # trim rows with ignore_flag
    #===========================================================================
    df1 = df_raw.copy()
    
    boolidx = df1.iloc[:,0].astype(str).str.contains(ignore_flag, case = case)
    if boolidx.sum() > 0:
            
        df1 = df1[~boolidx]
        
        logger.debug('dropped %i rows'%boolidx.sum())

        
    #===========================================================================
    # trim columns with ignore_flag
    #===========================================================================
    df2 = df1.copy()
    ser = pd.Series(df2.columns, dtype = str)
    
    boolcol = ser.str.contains(ignore_flag, case = case).values.T
    'transform and convert to an array'
    
    if boolcol.sum() > 0:
        
        df2 = df2.loc[:, ~boolcol] #make this trim
        
        logger.debug('dropped %i columns'%boolcol.sum())

    if len(df2) == 0: 
        logger.warning('got empty frame')
    #===========================================================================
    # wrap up
    #===========================================================================
    cleaner_report(df_raw, df2, logger = logger)
    
    return df2

def format_bool_cols(df_raw, sfx='_f', logger=mod_logger): #format boolean colmns as such
    logger = logger.getChild('format_bool_cols')
    
    df = df_raw.copy()
    
    logger.debug('on %s'%str(df.shape))
    
    #===========================================================================
    # identify boolcols
    #===========================================================================
    boolcol = df.columns.str.endswith(sfx)
    
    df1 = df.copy()
    df1.loc[:,boolcol] = df1.loc[:,boolcol].astype(bool)
    
    logger.debug('formatted %i columns to boolean'%boolcol.sum())
    
    return df1
    


def cleaner_report(df_raw, df_clean,logger=mod_logger):
    """
    #===========================================================================
    # TESTING
    #===========================================================================
    view_df(df_raw)
    
    len(df_raw.index)
    """
    logger = logger.getChild('report')
        
    #get deltas
    rows_delta = len(df_raw.index) - len(df_clean.index)
    cols_delta = len(df_raw.columns) - len(df_clean.columns)
    
    if rows_delta < 0 or cols_delta <0:
        logger.error('cleaning ADDED rows?! switch inputs?')
        raise IOError
    
    #===========================================================================
    # #get list of headers not in df_clean
    #===========================================================================
    
    cleaned_boolhead = ~df_raw.columns.isin(df_clean.columns)
    
    removed_headers = list(df_raw.columns[cleaned_boolhead])
    
    #===========================================================================
    # identify cleaned indicies
    #===========================================================================
    cleaned_boolidx = ~df_raw.index.isin(df_clean.index)
    
    removed_ids = list(df_raw.index[cleaned_boolidx])
    
    #===========================================================================
    # check if the numbers match
    #===========================================================================
    if not rows_delta == len(removed_ids):
        logger.error('got length mismatch')
        raise IOError
    if not cols_delta == len(removed_headers):
        logger.error('got length mismatch')
        raise IOError
    
    #===========================================================================
    # reporting
    #===========================================================================
    if rows_delta + cols_delta == 0:
        logger.debug('did no cleaning')
        return
    else:
        if cols_delta > 0:
            logger.debug('cleaned %i headers:  %s '%(len(removed_headers), removed_headers))
        
        if rows_delta > 0:
            logger.debug('cleaned %i idx:  %s '%(len(removed_ids), removed_ids))
            
    return    

def strip_whitespace_df(df_raw, logger=mod_logger): #strip whitespace from all string columns in the passed frame
    
    logger=logger.getChild('strip_whitespace_df')
    logger.debug('passed df_raw (rows: %i, cols: %i)'%(len(df_raw.index), len(df_raw.columns)))
    
    for header, col in df_raw.items():
        print(header)
        
def move_col_to_front(df_raw, colname, logger=mod_logger): #reorder teh cheaders
    
    
    if not isdf(df_raw):
        raise IOError
    
    #check if we were given a list
    if isinstance(colname, list):
        df1 = df_raw.copy(deep=True)
        reversed_list = reversed(colname)
        for cn in reversed_list: 
            df1 = move_col_to_front(df1, cn, logger=logger)
        return df1.copy()
    
    if not colname in df_raw.columns.values.tolist():
        logger=logger.getChild('move_col_to_front')
        logger.warning('\'%s\' not found in columns'%colname) 
        return df_raw.copy()
    
    
    ocols = df_raw.columns.values.tolist()
    
    newcols = copy.deepcopy(ocols)
    
    newcols.remove(colname)
    
    newcols = [colname] + newcols #add it back to the front
    
    df = df_raw[newcols] #get a reordered slice
    
    if not df.shape == df_raw.shape: raise IOError
    
    return df.copy()
        
def unique_byrank(df_raw, #make unique on uq_colname pulling data based on the ranked dictionary 
                  uq_colname, colval_rnk_d, logger=mod_logger):
    
    pass

def typeset_wnull( #typesetting with some null handling
        df_raw, 
        coln_type_d,
        logger=mod_logger):
    
    raise IOError('this workaround doesnt do much...')
    
    log = logger.getChild('typeset_wnull')
    
    log.debug('typesetting %s with %i cols: %s'%(str(df_raw.shape), len(coln_type_d), coln_type_d.keys()))
    df = df_raw.copy()
    #===========================================================================
    # loop through each column and typeset reals
    #===========================================================================
    for coln, typeset in coln_type_d.items():
        
        if not coln in df.columns:
            raise IOError('missing column %s'%coln)
        
        #split into nulls and reals
        boolidx_r = np.invert(df[coln].isna())
        
        #handle reals
        log.debug('setting %s onto col \'%s\' with %i (of %i) reals'%(typeset, coln, boolidx_r.sum(), len(boolidx_r)))
        ser_r = df.loc[boolidx_r, coln].astype(typeset)
        
        #reset nulls
        ser_n = df.loc[~boolidx_r, coln] 
        
        #re assemble
        df.loc[:,coln] = pd.concat([ser_r, ser_n], axis=0).sort_index()
    
    log.debug('finisehd')
    
    return df

"""
view(df)
"""

# TUPLE LIKE -------------------------------------------------------------------

def tlike_ser_clean( #clean a set of tlike data (into a cleaner tlike set)
        ser_raw,
        leave_singletons = True, #whether to leave single tons (vs dump them into a tuple)
        sub_dtype = None, #for mixed_type=True, what sub_dtype to place on the unitary values
        logger=mod_logger):
    
    #===========================================================================
    # defaults
    #===========================================================================
    log = logger.getChild('tlike_ser_clean')
    
    #activate the sub_dtype (incase it was passed as a string)
    if isinstance(sub_dtype, str):
        sub_dtype = eval(sub_dtype)
    
    #===========================================================================
    # shortcuts
    #===========================================================================
    #see if we are the correct unitary already (sub_dtype already matches)
    if sub_dtype.__name__ in ser_raw.dtype.name:
        log.debug('series \'%s\' is already unitary (type: %s). skipping'
                  %(ser_raw.name, ser_raw.dtype.name))
        
        #double check were not a string type
        if ser_raw.dtype.char == 'O':
            raise IOError('Object type!')
        
        return ser_raw.astype(sub_dtype)

    #===========================================================================
    # poorly formated with nulls
    #===========================================================================
    if not ser_raw.dtype.char == 'O':
        ser = ser_raw.astype(str) #reset type
        ser[ser_raw.isna()] = np.nan #remove all the nulls again
    else:
        ser = ser_raw
    
    
    if not ser.dtype.char == 'O':
        raise TypeError('unexpected type on tlike column \'%s\': %s'%(ser.name, ser.dtype.char))
    
    
    #===========================================================================
    # extract and clean
    #===========================================================================
    log.debug('cleaing tlike series \'%s\' with %i and sub_dtype: \'%s\''%
              (ser_raw.name, len(ser), sub_dtype))
       

    #extract everything into a dict witht eh formatting
    valt_d = tlike_to_valt_d(ser, 
                            leave_singletons = leave_singletons, 
                            sub_dtype = sub_dtype, 
                            leave_nulls = True,
                            logger=log)
    
    ser = pd.Series(valt_d, name=ser_raw.name)
    
    #===========================================================================
    # do some checks
    #===========================================================================
    if not len(ser) == len(ser_raw):
        raise IOError
    
    if not np.all(ser_raw.sort_index().index == ser.sort_index().index):
        raise IOError('index mismatch')
    
    if not ser.count() == ser_raw.count():
        raise IOError('value mismatch')

    return ser.loc[ser_raw.index] #return with the index in the same order

def tlike_to_valt_d( #convert a series (or array) of tuple like values into a dictionary of tuples
        tlike_raw, #series or array
        leave_singletons = True, #whether to leave single tons (vs dump them into a tuple)
        sub_dtype = None, #for mixed_type=True, what sub_dtype to place on the unitary values
        leave_nulls = False, #whether to leave the null values in
        logger=mod_logger):
    """
    Couldnt get pandas to work with tuples, 
    so this is a workaround by dumping everything into a dictionary
    
    dictionary result is keyed with the series index
    
    TODO: consider forcing sub_dtype on the tuple/list elements
    """
    #===========================================================================
    # setups
    #===========================================================================
    log = logger.getChild('tlike_to_valt_d')
    
    if isinstance(sub_dtype, str):
        sub_dtype = eval(sub_dtype)
        
    if not inspect.isclass(sub_dtype):
        raise IOError('got unexpected type on sub_dtype: \"%s\''%type(sub_dtype))
    
    if sub_dtype == int:
        def smart_int(v):
            return int(float(v))
        sub_dtype  = smart_int
        
        """
        smart_int('123.0')
        
        """
    #===========================================================================
    # prechecks
    #===========================================================================
    if len(tlike_raw) == 0:
        log.warning('got an empty container... returning an empty dict')
        return dict()
    #type checking
    if not tlike_raw.dtype.char == 'O':
        raise IOError('unepxected type: %s'%(tlike_raw.dtype))
        
    #===========================================================================
    # type conversion
    #===========================================================================
    if isinstance(tlike_raw, pd.Series):
        ser = tlike_raw
        log.debug('extracting tuple dictionary from series \'%s\' with %i elements'%(tlike_raw.name, len(tlike_raw)))

    elif isinstance(tlike_raw, np.ndarray):
        ser = pd.Series(tlike_raw) #leave as is

    else:
        raise TypeError('unexpected type') #shouldnt hit from above

    #=======================================================================
    # reals. extraction (pulls all singletons too)
    #=======================================================================
    #id nulls
    boolidx = np.invert(pd.isnull(ser))
    
    #loop and set
    d2 = dict()
    for key, val in ser[boolidx].items():

        if isinstance(val, str):
            if "(" in val or "[" in val:
                """ if were dealing with tuple like + singleton strings, we dont want to evaluate single tons w/o this"""
                try:
                    d2[key] = eval(val) #extract it
                except:
                    raise IOError('valued to eval ser \'%s\' key %s = \'%s\''%(ser.name, key, val))
            else:
                d2[key] = val #just leave it
        else:
            d2[key] = val
        
    #=======================================================================
    # tupleize
    #=======================================================================
    if not leave_singletons:
        d3 = dict()
        for key, val in d2.items():
            #handle by type
            if isinstance(val, tuple): #already a tuple. just leave it
                nval = val 
            elif isinstance(val, list): #list like. convert it to a tuple
                nval = tuple(val)
            else: #try and convert it
                nval = tuple([val])
            
            #set it
            d3[key] = nval
            
        log.debug('tupleizing all elements')

    else:
        d3 = d2
        
    #===========================================================================
    # sub_dtyping
    #===========================================================================
    if not sub_dtype is None:
        log.debug('setting sub_dtype \'%s\' on %i entries'%(sub_dtype, len(d3)))
        d4 = dict()
        for k, val_t in d3.items():
            try:
                if isinstance(val_t, tuple) or isinstance(val_t, list):#loop and format each
                    #dump and convert (wouldnt work in line)
                    l1 = []
                    for val in val_t:
                        l1.append(sub_dtype(val))
                    
                    d4[k] = tuple(l1)

                else: #singleton. just type it
                    d4[k] = sub_dtype(val_t)
            except:
                raise TypeError('failed to set \'%s\' on key \'%s\' val \'%s\''%(sub_dtype, k, val_t))
            """
            sub_dtype(val_t)
            """
        #log.debug('finished typesetting')
                
    else:
        d4 = d3

    #=======================================================================
    # add the nulls back in
    #=======================================================================
    if leave_nulls and np.any(~boolidx):
        log.debug('re-inserting placeholder keys for %i nulls'%(pd.isnull(ser).sum()))
        for key, val in ser[~boolidx].items():
            d4[key] = np.nan
    else:
        log.debug('omitting keys for %i nulls'%(pd.isnull(ser).sum()))
            

    return d4


 
#===============================================================================
# PLOTTERS --------------------------------------------------------------------
#===============================================================================

#===============================================================================
# def Plot_split_on_y(df, ax=None, title = None, savepath = None, x_label = None, logger=mod_logger): #plot the first two columns agains the index
#     
#     #===========================================================================
#     # Set Defaults
#     #===========================================================================
#     
#     if ax == None:
#         fig = plt.figure(5)
#         fig.set_size_inches(6, 4.5)
#         ax = fig.add_subplot(111)
#     else:
#         fig = plt.gcf()
#         
#     #===========================================================================
#     # Get the data
#     #===========================================================================
#     x_list = list(df.index)
#     y1_list = list(df.iloc[:,0])
#     y2_list = list(df.iloc[:,1])
#     
#     
#     y1_lab = df.columns[0]
#     y2_lab = df.columns[1]
#     
#     #===========================================================================
#     # PLot the first axis
#     #===========================================================================
#     color = 'green'
# 
#     y1_pline = ax.plot(x_list, y1_list, color = color)
#     
#     y1_pline[0].set_label(y1_lab)
#     
#     #===========================================================================
#     # Plot the second axis
#     #===========================================================================
#     ax2 = ax.twinx()
#     color = 'blue'
#     y2_pline = ax2.plot(x_list, y2_list, color = color)
#     y2_pline[0].set_label(y2_lab)
#            
#     #===========================================================================
#     # Label the plot
#     #===========================================================================
#     type(df.index)
#     ax.set_title(title)
#     ax.set_xlabel(x_label) 
#     ax.set_ylabel(y1_lab)
#     ax2.set_ylabel(y2_lab)
#     
#     #===========================================================================
#     # configure the legend
#     #===========================================================================
#     h1, l1 = ax.get_legend_handles_labels() #pull legend handles from axis 1
#     h2, l2 = ax2.get_legend_handles_labels()
#     ax.legend(h1+h2, l1+l2) #turn legend on with combined handles
#     
#     #===========================================================================
#     # Save teh figure
#     #===========================================================================
#     if not savepath == None: #trigger for saving the fiture
#         fig.savefig(savepath, dpi = 300)
#         
#     return ax, ax2
#===============================================================================

    
#===============================================================================
# MISC -----------------------------------------------------------------------
#===============================================================================
def insert_row_value(df_raw, index, value, logger=mod_logger ): #insert a row with the passed value on teh passed index
    
    #===========================================================================
    # precheck
    #===========================================================================
    if not isdf(df_raw): raise IOError
    if len(df_raw) == 0: raise IOError
    #===========================================================================
    # setup
    #===========================================================================
    logger = logger.getChild('insert_row_value')
    
    data = np.full((1, len(df_raw.columns)), value).tolist()[0] #new row to add data
    data_ser = pd.Series(data, index = df_raw.columns)
    
    
    df1 = df_raw.iloc[:index, :] #first half
        
    df2 = df_raw.iloc[index:, :] #second half
    
    
    #===========================================================================
    # bundle them all
    #===========================================================================
    df3 = df1.append(data_ser, ignore_index=True)
    df4 = df3.append(df2, ignore_index=True)
    
    logger.debug('on index %i with fill value %s for result %s'%(index, value, str(df4.shape)))
    
    if not len(df4)  == len(df_raw)+1: raise IOError
    
    return df4

def get_incremental(ser_raw, logger=mod_logger): #get the incremental (delta) values 
    
    if not isser(ser_raw): raise IOError
    
    ser_inc = pd.Series(index = ser_raw.index) #starter index
    
    for index, cum_val in ser_raw.items(): #loop through and claculate
        if index == 0: inc_val = cum_val
        else:
            inc_val = cum_val - ser_raw[index - 1] #get from the last
            
        ser_inc[index] = inc_val #set this
        
    return ser_inc 
    
    
#===============================================================================
# MULTINDEX FRAMES ------------------------------------------------------------ 
#===============================================================================
"""
#===============================================================================
# A note on nomenclature
#===============================================================================
dx    = multindex dataframe
dxcol = column (header)based
dxind = index (row) based multindex

mdex        = multindex object
level        = rank sensitive labels
"""
def dxind_append_df(dx_raw, lvl0_val, df, logger=mod_logger): #add the df under the lvl0 header
    
    if len(df.index) == 0:
        logger.debug('passed frame was empty: \n %s'%df)
        return dx_raw
    
    mdex = dx_raw.index #get the mdex
    
    #===========================================================================
    # check that the lvl1 headers match the new headers
    #===========================================================================
    if not df.index in mdex.get_level_values(0).unique():
        logger.warning('not all the new headers were found in the mdex')
        raise IOError
    
    dx_raw[lvl0_val] = df #add this new df under the lvl0 value
        
    '''
    #===========================================================================
    # build the new mdex 
    #===========================================================================
    lvl0_values = mdex.get_level_values(0).append(lvl0_val)
    lvl1_values = mdex.get_level_values(1)
    
    tuples = list(zip(lvl0_values,lvl1_values))
        
    new_mdex = pd.MultiIndex.from_tuples(tuples, names=mdex.names)
    '''
        
        

    

def DxCol_append_dframe(dx, level1_value, df, logger=mod_logger): #add the df values to the dxcol_2lvl along the dx sliced by level1_value
    
    if len(df.index) == 0:
        logger.debug('passed frame was empty: \n %s'%df)
        return dx
    
    mdex = dx.columns #get the mdex
    #get the concanted index (old + new) unique values
    new_index = dx[level1_value].append(df, ignore_index=False).index.unique()
    
    #build a new frame with this updated index and the old values
    dx = pd.DataFrame(data=dx, columns = mdex, index=new_index)
    
    #add data from this years frame to the proper slice
    dx[level1_value]= df
    
    return dx
    
def DxCol_xs_append_df(dx_raw, lvl_rank_dict, df, logger=mod_logger): #add the df values to the dxcol_3lvl along the dx sliced by the levels
    """INPUTS:
    
    lvl_rank_dict = {[rank1, rank2, rank3,...],[lvl1_value, lvl2_value, lvl3_value,...]}
    """
    
    if len(df.index) == 0:
        logger.debug('passed frame was empty: \n %s'%df)
        return dx_raw
    'TODO: check data type of inputs'
    
    mdex = dx_raw.columns #get the mdex
    
    # check dimensions of passed variables 
    
    if not len(mdex.names) - 1 == len(lvl_rank_dict):
        logger.error('dimensions of mdex dont match dimensions of slice passed: \n %s'%lvl_rank_dict)
        
    if len(lvl_rank_dict) == 2:
    
        #get the xs at this spot
        dx_trim = dx_raw[lvl_rank_dict[0], lvl_rank_dict[1]]
        
        #get the concanted index (old + new) unique values
        new_index = dx_trim.append(df, ignore_index=False).index.unique()
        
        #build a new frame with this updated index and the old values
        dx = pd.DataFrame(data=dx_raw, columns = mdex, index=new_index)
        dx.sort_index(axis=0, inplace=True) #sort the index
        
        #add data from this years frame to the proper slice
        dx[lvl_rank_dict[0], lvl_rank_dict[1]] = df
        
    if len(lvl_rank_dict) == 1:
        
        #get the xs at this spot
        dx_trim = dx_raw[lvl_rank_dict[0]]
        
        #get the concanted index (old + new) unique values
        new_index = dx_trim.append(df, ignore_index=False).index.unique()
        
        #build a new frame with this updated index and the old values
        dx = pd.DataFrame(data=dx_raw, columns = mdex, index=new_index)
        dx.sort_index(axis=0, inplace=True) #sort the index
        
        #add data from this years frame to the proper slice
        dx[lvl_rank_dict[0]] = df
    
    return dx

def fill_dx_col(df, lvl0_vals, names, logger=mod_logger): #take a df and make a fake upgrade to a dxcol
    
    logger = logger.getChild('fill_dx_col')
    #build the new mdex            
    mdex = pd.MultiIndex.from_product([lvl0_vals, df.columns], names=names)
                     
    
    dxcol = pd.DataFrame(index = df.index, columns = mdex)
    
    #===========================================================================
    # fill the frame
    #===========================================================================
    for lvl0val in lvl0_vals: dxcol[lvl0val] = df
    
    logger.debug('filled the dxcol %s from df %s'%(str(dxcol.shape), str(df.shape)))
    
    return dxcol

def merge_dxcol(left_dxcol, right_dxcol, 
                on=None, left_index=True,how = 'left', right_index = True, 
                left_on = None, right_on = None,sort = False, indicator = True,
                logger=mod_logger, **kwargs): #merge two dxcols with eh same lvl0 values
    
    
    import model.sofda.hp.np as hp_np
    left_lvl0_vals = left_dxcol.columns.get_level_values(0).unique() 
    right_lvl0_vals = right_dxcol.columns.get_level_values(0).unique()
    
    #===========================================================================
    # prechecks
    #===========================================================================
    if not np.any(hp_np.np_isin_workaround(left_lvl0_vals, right_lvl0_vals)): raise IOError
    
    
    
    #===========================================================================
    # ssetup mdex
    #===========================================================================

    left_lvl1_vals = left_dxcol.columns.get_level_values(1).unique() 
    right_lvl1_vals = right_dxcol.columns.get_level_values(1).unique() 
    'todo: check if there is overlap'
    'todo: check if on is in here'
    
    #check that the search value is in teh lvl1 of both
    if not on is None:
        if not on in left_lvl1_vals.tolist(): raise IOError
        if not on in right_lvl1_vals.tolist(): raise IOError
    
    lvl1_vals = left_lvl1_vals.tolist() + right_lvl1_vals.tolist()
    
    names = [left_dxcol.columns.names[0], 'merge']
    
    mdex = pd.MultiIndex.from_product([left_lvl0_vals, lvl1_vals], names=names)
        
    
    
    #===========================================================================
    # loop and fill
    #===========================================================================
    for index, lvl0_val in enumerate(left_lvl0_vals): 
        
        #get the slices
        left_df_slice = left_dxcol[lvl0_val]
        right_df_slice = right_dxcol[lvl0_val]
        
        #set teh slice
        merge_df = pd.merge(left_df_slice, right_df_slice, 
                                on = on,
                                how = how,
                                left_index = left_index,
                                right_index = right_index, 
                                left_on = left_on,
                                right_on = right_on,
                                sort = sort,
                                indicator = indicator, **kwargs)
        
        
        if index == 0: #do the setup
            merge_dxcol = pd.DataFrame(index = merge_df.index, columns = mdex) #build the empty frame
                    
        merge_dxcol[lvl0_val] = merge_df
        
        """
        hp_pd.view_df(merge_df)
        left_df.columns
        right_df2.columns
        """
    logger.debug('merged left_df %s with right_df %s to make merge_df %s. attached as data'
                 %(str(left_dxcol.shape), str(right_dxcol.shape), str(merge_dxcol.shape)))
    
    #===========================================================================
    # checks
    #===========================================================================
    if not len(merge_dxcol) >= len(left_dxcol): raise IOError
    if not len(merge_dxcol) >= len(right_dxcol): raise IOError
    
    return merge_dxcol
    
    
            
    
def Get_mdex_lvl_ranks(mdex, lvl_names, logger=mod_logger): #workaround to get the rank of different level names
    
    lvl_ranks = []
    
    for name in lvl_names: #loop through the passed names and get th eir rank
        rank = mdex.names.index(name)
        lvl_ranks.append(rank)
        
    return lvl_ranks

def Get_mdex_xs_lvl_rank_dict(mdex, lvl_values, lvl_names, logger=mod_logger): #build a dictionary of the passed indexer xs
    'this only works for a cross section (one lvl_value per lvl_rank/name'
    'builds a dictionary of this xs keyed by lvl_rank'
    
    lvl_ranks = Get_mdex_lvl_ranks(mdex, lvl_names) #get teh corresponding ranks
    
    lvl_rank_dict = dict(list(zip(lvl_ranks, lvl_values)))
    
    return lvl_rank_dict

def Get_spatial_dxcol(x_values,y_values,time_ser, data_raw, logger=mod_logger):  #build a dxcol of x,y,z over time data

    """here we build a quasi 2D mdex of time vs location.
    location however is defined with 2 dimensions (x, y)
    
    #===========================================================================
    # INPUTS
    #===========================================================================
    data = an array of arrays in the same order as the time series
    
    """
    #check inputs
    if not len(x_values) == len(y_values):
        logger.error('x value and y value pair lengths do not match: \n %s \n %s'%(x_values, y_values))
        
    #check the data_raw dimensions 
    if not len(data_raw.shape) == 2:
        logger.error('expected 2 dims for data, instead got: %s'%data_raw.shape)
        raise IOError
    
    #check that the xy values match the number of data entries
    if not int(data_raw.shape[1]) == len(x_values):
        #logger.error('dimension mismatch. data: %s and x_values: %i'%(lvl_data_trim.shape, len(x_values)))
        raise IOError
    

    #check the time series match
    if not int(data_raw.shape[0]) == len(time_ser):
        logger.error('time series of raw data (%i) did not match time_ser (%i)'%(int(data_raw.shape[0]),len(time_ser) ))
        raise IOError
    
    #check that the x and y values are list
    if not isinstance(x_values, list) & isinstance(y_values, list):
        logger.error('got unexpected type of x and y values: %s'%type(x_values))
        raise IOError
        
        
    lvl0_values = x_values
    lvl1_values = y_values
    
    tup = list(zip(lvl0_values, lvl1_values))
    
    mdex = pd.MultiIndex.from_tuples(tup,  sortorder=None, names = ['x', 'y'])
    
    dxcol = pd.DataFrame(index = time_ser, columns = mdex )
    
    logger.debug('mdex built with %i xy pairs: '%len(x_values))
    
    #loop through each time series and add the values 
    for i, time in enumerate(dxcol.index):
        dxcol.loc[time] = data_raw[i]
        
         
    return dxcol

def dxcol_to_df_set(dxcol, 
                    container = OrderedDict,
                    logger=mod_logger): #breaks a 2 level dxcol into a set of dictionaries
    """
    #===========================================================================
    # OUTPUTS
    #===========================================================================
    df_set_dict
        keys:    list of unique lvl0_values from the dxcol
        values:   list of dfs with headers from lvl1_values. corresponds to the lvl0values
    """
    
    if not isdxcol(dxcol): 
        raise IOError
    
    mdex = dxcol.columns

    
    lvl0_values = list(mdex.get_level_values(0).unique())
    
    try:
        lvl0_values.sort()
    except:
        logger.warning('failed to sort lvl0values: %s'%lvl0_values)

    
    df_list = []
    dfname_list = []
    
    for lvl0_val in lvl0_values:
        df = dxcol[lvl0_val] #get a df slice for just this lvl0val
        
        df_list.append(df)
        dfname_list.append(lvl0_val)
        
    #wrap into dictionary
    df_set_dict = container(list(zip(dfname_list, df_list)))
    
    logger.debug('broke then wrapped %i frames into a dictionary'%(len(dfname_list)))
    
    return df_set_dict



# MULTIPROCESSING --------------------------------------------------------------

#===============================================================================
# def mp(df_raw, #perform the func on the frame using threading
#        func,  
#        threads = 4, logger=mod_logger, **kwargs): 
#     
#     import math
#     
#     logger = logger.getChild('pd.mp')
#     
#     block_len = math.ceil(len(df_raw)/float(threads)) #number of blocks
#     
#     logger.info('multiprocessing %s in %i blocks on %i threads')
#     
#     #===========================================================================
#     # split the frame into blocks
#     #===========================================================================
#     
#     #last row of each block
#     block_end_list = range(block_len, len(df_raw), block_len) + [len(df_raw)] #get the last entry of each block
#     
#     #for block_end in block_end_list:3
#     
# def parallelize(df, func, threads = 4, logger=mod_logger, **kwargs):
#     """ from: http://www.racketracer.com/2016/07/06/pandas-in-parallel/
#     
#     """
#     #if __name__ == '__main__':
#     from multiprocessing import Pool
#     split_dfs = np.array_split(df, threads) #split the df into threads dfs
#     
#     pool = Pool(threads) #create the process pool
#     df = pd.concat(pool.map(func, split_dfs))
#     pool.close()
#     pool.join()
#     return df
#     
#     #else: return False
#     
# class Parallel():
#     def __init__(self, threads=4):
#         
#         self.threads = threads
#         
#         print 'initizlied on %i threads'%threads
#         
#     def ize(self, df, func, **kwargs):
#         threads = self.threads
#         from multiprocessing import Pool
#         split_dfs = np.array_split(df, threads) #split the df into threads dfs
#         
#         pool = Pool(threads) #create the process pool
#         df = pd.concat(pool.map(func, split_dfs))
#         pool.close()
#         pool.join()
#         return df
#         
#===============================================================================

        
        
        
        
    

    





    
        
     
    