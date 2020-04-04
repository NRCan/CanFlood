'''
Created on Jun 17, 2018

@author: cef

basic commands for data analyis/manipulation

most commands lie in hp_pd
here we mostly are housing the worker object
'''

#===============================================================================
# IMPORT STANDARD MODS
#===============================================================================
import logging, os
#sys, imp, time, re, math, copy, datetime

import pandas as pd
import numpy as np

from collections import OrderedDict

#===============================================================================
#  IMPORT CUSTOM MODS ---------------------------------------------------------
#===============================================================================

import model.sofda.hp.basic as hp_basic
import model.sofda.hp.pd as hp_pd

"""since the workers wrap around the hp_oop.Basic_o, that module must be imported first"""
import model.sofda.hp.oop as hp_oop
#import hp.plot

mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')

class Data_wrapper(object): #wrapper for data type operations


    """
    #===========================================================================
    # USE
    #===========================================================================
    functions for
        loading raw data
        processing and visualizing data
        cleaning
        combining
    """
    #===========================================================================
    # program pars
    #===========================================================================
    filepath        = None
    supported_ext   = ['.csv', '.xls']
    #===========================================================================
    # calculated pars
    #===========================================================================
    datadims        = None #
    """this is the dimensions of the data represented by this object
        0 datadim: single value pair (indx, value)
        1 datadim:  data series
        2 datadim: simple df (matrix)
        3 datadim: mdex 
        4 datadim: a collection of mdexes (typically data files. simulation)
        5 datadim: typically this is the session
        
    this is related to, but not necessarily directly, the branch_level
    """

    #===========================================================================
    # user pars
    #===========================================================================
    index_col       = None #load a synthetic index
    test_trim_row   = 10

    skiprows        = None #for non-virual datos, this dictates which rows to skip when importing the data from file
    """
    #skip teh second line when reading the file
         skiprows =[1]
    #skip the first row (index[0[):
        skiprows=1
    """

    # header translation
    tr_dict_fhead   = None #filehead pointoing to the column translation dictionary
    tr_dict_path    = None #filepath to the translation dictionary
    
    #nlevels = 1 #number of levels tot eh column data
    
    #===========================================================================
    # data containers
    #===========================================================================
    data        = None
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Data_wrapper')
        cn = self.__class__.__name__
        logger.debug('start _init_ on %s'%cn)
        super(Data_wrapper, self).__init__(*vars, **kwargs) #Data_o. initilzie teh baseclass 
        logger.debug('finish _init_ on %s'%cn)
        
    def load_data(self): #place holder for loading data
        """
        #=======================================================================
        # STANDARDS
        #=======================================================================
        the load_data function sould attach (self.data) and return the data
        """
        'this can be overwrriten with custom images. called by raise_children'
        df1 = self.loadr_gen()
        
        #translate headers
        if not self.tr_dict_path is None: 
            df2 = self.translate_heads_df(df1)
        else: df2 = df1.copy(deep=True)
        
        self.data = df2
        
        return df2
    
    def loadr_gen(self, filepath = None): #generic inelligent file loader
        """
        For customized data loading, buid a data object image and create a new data loading function
            generally a call with kwargs to hp.load_csv_df
        
        """
        logger = self.logger.getChild('gen_loadr')
        
        #=======================================================================
        # defaults
        #=======================================================================
        #get the filepath
        if filepath is None: filepath = self.get_filepath()
        
        self.filepath = filepath 
        

        
        logger.debug('from %s'%filepath)
        #=======================================================================
        # Loader by type
        #=======================================================================
        if filepath is None: data = self.loadr_vir()  #virtual
                     
        elif not '.' in filepath: #directories
            logger.debug('directory passed. no data loaded for %s'%filepath)
            data = None 
        
        else: data = self.loadr_real(filepath) #filepaths
        
        logger.debug('found data with type \'%s\''%type(data))
           
        return data
    
    def loadr_vir(self): #load data for virtual datos
        logger = self.logger.getChild('loadr_vir')
        
        df = self.parent.data.copy()
        
        if self.db_f:
            if not hp_pd.isdf(df, logger = logger): 
                logger.error('no filepath and no parent data (%s)'%self.parent.name)
                raise IOError
            """
            add some intelliegent detection based on the branch level
            if not self.name in df.columns.values.tolist():
                logger.error('could not find my name in the parent data: %s'%df.columns.values.tolist()) 
                raise IOError
            """
            if df is None: 
                raise IOError
        
        try:
            data = df[self.name]
        except:
            if self.name == df.index.name:
                data = pd.Series(df.index.values, index = df.index)
                'shadow 2d object'
                
            elif not self.name in df.columns:
                logger.error('my name is not in my parents data')
                """
                hp_pd.view_web_df(df)
                df = df
                
                """
                raise IOError
            else: raise IOError
        
        logger.debug('virtual data branch. data extracted from parent %s'%str(data.shape))
        
        #if data is None: raise IOError
        
        return data
    
    def reload_child_data(self): #reload all the childrens data from teh parent
        logger = self.logger.getChild('reload_children')
        logger.debug('reloading all chidlren data')
        
        if self.kids_d is None: return 0#no children
        
        cnt, ccnt = 0, 0
        
        for gid, childo in self.kids_d.items():
            childo.load_data() #load the data
            ccnt = childo.reload_children() #reload the grand children
            cnt = ccnt + cnt
            
        logger.debug('reloaded data for %i objects'%cnt)
        
        return cnt
    
    def loadr_real(self,  #load data for filepaths
                   filepath, 
                   multi=False, #load tabs from a .xls
                   ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('loadr_real')
        
        #test pars
        if self.session._parlo_f: 
            test_trim_row = self.test_trim_row
        else: test_trim_row = None
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if not os.path.exists(filepath):
            raise IOError('passed filepath does not exist: \n    %s'%filepath)  
                
        #=======================================================================
        # #get the headers
        #=======================================================================
        header = 0 #default
        if not self.datadims is None: #we know how many dimensions there are. load accordingly
            if self.datadims < 3: header = 0
            elif self.datadims == 3: header = [0, 1]
            else: 
                logger.error('got unexpected value for datadims: %s'%self.datadims)
                raise IOError
            
        #=======================================================================
        # #load by filetype
        #=======================================================================
        if filepath.endswith('.csv'):  
            data = hp_pd.load_csv_df(filepath, logger = logger, test_trim_row = test_trim_row, 
                                         header = header, 
                                         skiprows = self.skiprows,
                                         index_col = self.index_col)
        
        elif filepath.endswith('.xls'):  
            if not multi:
                data = hp_pd.load_xls_df(filepath, logger = logger, test_trim_row = test_trim_row, 
                                             header = header, 
                                             skiprows = self.skiprows,
                                             index_col = self.index_col)
            else:
                data = hp_pd.load_xls_d(filepath, logger = logger, test_trim_row = test_trim_row, 
                                             header = header, 
                                             skiprows = self.skiprows,
                                             index_col = self.index_col)
            
        elif filepath.endswith('.par'):
            if not self.skiprows is None: raise IOError
            data = pd.read_table(filepath)
            
        else:
            raise IOError('got unexpected filetype (%s) from filepath: \n    %s'%(filepath[:-4], filepath))
        
        #=======================================================================
        # wrap up
        #=======================================================================
        if data is None: raise IOError
        
        self.session.ins_copy_fps.add(filepath)
        
        return data
    
    def generic_clean_df(self, df_raw): #simple nan cleaning
        """
        TODO: add some reformatting for boolean columns
        """
        logger = self.logger.getChild('clean_df')
        df1 = df_raw.dropna(axis='columns', how='all')
        df2 = df1.dropna(axis='index', how='all') #drop rows with all na
        
        df_clean = df2
        
        if df_clean.columns[0].startswith('?'):
            raise IOError
        
        hp_pd.cleaner_report(df_raw, df_clean,logger=logger)
        
        #=======================================================================
        # #apply data formatting
        #=======================================================================
        if hasattr(self, 'datatplate_path'):
            df_clean = hp_pd.force_dtype_from_tplate(df_clean, self.datatplate_path, logger=self.logger) #apply dtype
        else: 
            self.logger.debug('no data type template provided')
            df_clean = df_clean.copy(deep=True)

        return df_clean
    
    def translate_heads_df(self, df_raw, tr_dict_path = None): #where translation dictoinaries are found, perform the translation

        #=======================================================================
        # defaults$
        #=======================================================================
        logger = self.logger.getChild('translate_df')
        if tr_dict_path is None:
            if self.tr_dict_path is None:
                logger.error('no tr_dict_path provided') 
                raise IOError 
            tr_dict_path = self.tr_dict_path
            

        
        if not hp_pd.isdf(df_raw):
            logger.warning('got unexpected type on passed df (%s). doing nothing'%type(df_raw))
            return df_raw
        
        #=======================================================================
        # load the tr_dict
        #=======================================================================
        Htrans = hp_pd.Head_translator(tr_dict_path, self)  #initilzie the worker
        df_trans = Htrans.translate(df_raw)
        
        return df_trans
                
    def add_data(self, dato=None,right_df = None, #merge the data of passed dato with self
                   on=None, wtf=None, **kwargs): 
        """
        useful for adding more data to existing set
        
        TODO: allow for creating an mdex with level0 being dato name
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('add_data')
        if wtf is None: wtf = self.session._write_data
        right_df_raw = right_df
        del right_df
        
        #get teh data
        left_df = self.data #building inventory data
        
        if right_df_raw is None:
            if dato is None: raise IOError
            right_df_raw = dato.data #damage table data
            
            logger.debug('adding data from %s %s'%(dato.name, str(right_df_raw.shape)))
        else:
            if not dato is None: raise IOError
            logger.debug('adding data from df %s'%(str(right_df_raw.shape)))
                    
        #do the merging
        merge_df = hp_pd.merge_left(left_df, right_df_raw, on=on, logger=logger, **kwargs)
        
        #add this back onto self
        
        if wtf: self.data_writer(data = merge_df, filename = '%s add_data'%self.name)
        
        
         
        self.data = merge_df #re attach teh merged data
                
        return merge_df
    
    def harmonize_data(self,  #harmonize/combine two datasets to 1
                       datonames_list=None, childname = 'harmonized', left_col_keep = False,
                       on=None, wtf=None): 
        
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('harmonize_data')

        if datonames_list is None: gid_l = list(self.kids_d.keys()) #merge everything
        if wtf is None: wtf = self.session._write_data
        
        logger.info('on %i datos'%len(datonames_list))
                
        #=======================================================================
        # loop and merge
        #=======================================================================
        for index, datoname in enumerate(datonames_list):
            dato = self.kids_d[gid] #get the dat
            df1 = dato.data
            df1['dataname'] = dato.name
            
            #===========================================================================
            # check for duplicates in source frames
            #===========================================================================
            flag, boolidx = hp_pd.are_dupes(df1, colname = on, logger=dato.logger)
            if flag: 
                logger.warning('found %i internal duplicates on %s. cleaning these'%(boolidx.sum(), datoname))
                df = df1.drop_duplicates(subset=on, keep='first') #just keep the first entry
            else: df = df1
            

            if index == 0: #start witht he first entry
                merge_df = df                
                logger.debug('starting join loop with %s'%dato.name)
                continue #skip to the next
            
                        
            logger.debug('joining left %s with \'%s\' df %s'%(str(merge_df.shape), dato.name, str(df.shape)))
            
            merge_df = hp_pd.union(merge_df,df, on=on, left_col_keep = left_col_keep, logger=logger)
        
        
        #=======================================================================
        # cleanup
        #=======================================================================
        merge_df1 = hp_pd.move_col_to_front(merge_df, on, logger=logger) #sort columns by search cols
        merge_df2 = merge_df1.reset_index(drop=True)
        
        #=======================================================================
        # create new dato
        #=======================================================================

        harm_dato = self.spawn_child(childdata = merge_df2, childname = childname, Dato_builder = Data_o, 
                                     raise_gkid_f=False, load_data_gkid_f=False)
        
        if wtf: harm_dato.data_writer()
        
        return harm_dato
    
    def all_uq_child_slices(self, search_head, value_head): #make a sliced child for each unique entry in the search_head
        logger = self.logger.getChild('all_uq_child_slices')
        df = self.data
        #=======================================================================
        # prechecks
        #=======================================================================
        if not hp_pd.isdf(df): raise IOError
        if not search_head in df.columns: raise IOError
        
        #=======================================================================
        # setup
        #=======================================================================
        search_values = df[search_head].unique().tolist()
        
        logger.info('with search_head \'%s\' building %i sliced children with values from \'%s\''
                    %(search_head, len(search_values), value_head))
        
        value_dato = self.kids_d[value_head]
        att_ser = value_dato.get_own_att_ser()
        'need to do this so it inerhits properties from the search datao rather than the parent'
        
        #=======================================================================
        # get this data slice
        #=======================================================================
        new_kids_d = dict()
        for srch_val in search_values:
            boolidx = df[search_head] == srch_val #identify where the search value occurs
            boolcol = df.columns == value_head
            #get thsi slice
            df_slice = df.loc[boolidx, boolcol]
            
            #create a child from this slice
            childname = value_head + '_' + srch_val
            childo = self.spawn_child(att_ser = att_ser, childdata=df_slice, childname = childname)
            
            #childo.label = childo.name + '(%s)'%childo.units
            
            logger.debug('spawned child \'%s\' with df %s'%(childo.name, str(df_slice.shape)))
            
            new_kids_d[childname] = childo
            'this is just a helpful slice. the master kids_d should be updated by spawn_child'
            
        logger.debug('finished slicing %i children: %s'%(len(new_kids_d), list(new_kids_d.keys())))
        
        return new_kids_d
    
    def get_slice_stats(self, bool_o, invert=False): #get the stats of slices
        logger = self.logger.getChild('get_slice_stats')
        
        slice_name = bool_o.name
        df_raw = self.data
        
        try:
            bool_o.data = bool_o.data.astype(np.bool) #make sure this is a boollean
        except: 
            logger.error('unable to do type conversion on %s'%bool_o.data.dtype)
        #split the focus dato by trues/falses

        if not invert:
            true_df = df_raw[bool_o.data].dropna() #get teh trues slice
        else:
            true_df = df_raw[~bool_o.data].dropna() #get teh trues slice

        
        #=======================================================================
        # report results
        #=======================================================================
        #true
        stats_l = hp_np.get_stats_str_l(true_df.values)
        if not invert:
            logger.info('for the \'%s\' IN slice got these stats: \n    %s'%(slice_name, stats_l))
        else:
            logger.info('for the \'%s\' OUT slice got these stats: \n    %s'%(slice_name, stats_l))
        
        return stats_l
    
    def select_filepath(self):
        
        title = 'select your datas filepath'
        self.filepath = hp_basic.gui_fileopen(title = title)
        
        return self.filepath
    
    def get_filepath(self): #intellgently set the filepath
        logger = self.logger.getChild('set_filepath')
        
        filepath = None
        
        if hasattr(self, 'headpath') & hasattr(self, 'tailpath'): #concanate to find file
            if not self.headpath is None:
                #absolute 
                if self.session.inspath is None: #
                    filepath = os.path.join(self.headpath, self.tailpath)
                    logger.debug('(absolute) filepath constructed from head and tail')
                
                #relative
                else:
                    filepath = os.path.join(self.session.inspath, self.headpath, self.tailpath)
                    
                    #self.headpath = u'fdmg\\aoi02'
                    if self.headpath.startswith('\\'): raise IOError
                    
                    logger.debug('(relative) filepath constructed from head and tail')
                    
        return filepath
        
class Data_o(hp_oop.Parent, 
             #hp.plot.Plot_o, 
             Data_wrapper,
             hp_oop.Child): #standalone object 
    #===========================================================================
    # program controls
    #===========================================================================
    outpath = None
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Data_o')
        """
        self.inherit_parent_ans
        """
        
        super(Data_o, self).__init__(*vars, **kwargs) #Data_o. initilzie teh baseclass 
        
        # translation dictionary
        if not self.tr_dict_fhead is None: 
            self.tr_dict_path = os.path.join(self.headpath, self.tr_dict_fhead)
            if not os.path.exists(self.tr_dict_path): raise IOError
            
        logger.debug('load_data()')
        _ = self.load_data()
            
        self.logger.debug("finished _init_ \n")
        return
    

        
        
   