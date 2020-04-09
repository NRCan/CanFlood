'''
Created on Sep 15, 2018

@author: cef

generic plotting functions
'''

#===============================================================================
# # IMPORTS --------------------------------------------------------------------
#===============================================================================
import os,  logging, gc, weakref, copy, sys, re
import pandas as pd
import numpy as np

from collections import OrderedDict
from weakref import WeakValueDictionary as wdict
from weakref import proxy


import model.sofda.hp.pd as hp_pd
import model.sofda.hp.oop as hp_oop
import model.sofda.hp.dict as hp_dict
import model.sofda.hp.data as hp_data2

#import da.pscripts2 as pscripts2

idx = pd.IndexSlice
#===============================================================================
# mod_logger
#===============================================================================
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')

#===============================================================================
# setup matplotlib
#===============================================================================

import matplotlib

#set the backend
interactive = True

if interactive:
    matplotlib.use('TkAgg')
else:
    matplotlib.use('SVG') #sets the backend (case sensitive)




#===============================================================================
#  formatting defaults
#===============================================================================
import matplotlib.pyplot as plt
#set teh styles
plt.style.use('default')

#font
matplotlib_font = {'family' : 'serif',
        'weight' : 'normal',
        'size'   : 8}

matplotlib.rc('font', **matplotlib_font)

matplotlib.rcParams['axes.titlesize'] = 10 #set the figure title size

#spacing parameters
matplotlib.rcParams['figure.autolayout'] = True #use tight layout
"""

matplotlib.rcParams['figure.subplot.left'] = 0.125 #the left side of the subplots of the figure. 0.125
matplotlib.rcParams['figure.subplot.right'] = 0.1 # 0.9
matplotlib.rcParams['figure.subplot.bottom'] = 0.1 # 0.1
matplotlib.rcParams['figure.subplot.top'] = 0.9 #0.9
"""

#===============================================================================
# Classes ----------------------------------------------------------------------
#===============================================================================
class Plotpar_wrap(object): #for single data plotting variables shared between Plotrs and Pairs
    """
    The Plotr's value, if provided, should propegate th rough tot he plot
    otherwise, the pairs value should be used
    
    WARNING! 
    That means all of these need to be None.
    If you want to set default values, repeat these pars under the PAIR
    """
    #===========================================================================
    # plot parameters
    #===========================================================================
    #generic plot formatting
    xlab = None
    ylab = None
    title = None
    
    fmt_func_str = None  #eval str to reformat the tick labels
    
    
    #data styling
    units       = None
    color       = None
    linestyle   = None
    linewidth   = None
    alpha       = None
    marker      = None
    markersize  = None
    markerfacecolor = None
    markeredgecolor = None
    markeredgewidth = None
    fillstyle   = None #marker fill style
    
    label = None
    
    
    #annotation
    annot = None #string to add as an annotation
    anno_tup = None #tuple for locating the annotation
    xycoords = None
    anno_arrow_tup = None #tuple for annotation arrow
    textcoords = None #coordinate system for arrow tails
    annot_kwargs = None #additional kwargs to pass to ax.annotate
    arrowprops = None
    
    #box plots
    box_notch = None
    box_whis = None
    box_meanline = None
    box_widths = None
    
    #histogram special
    hist_bins = None
    hist_density = None
    histtype = None 
    hist_rwidth = None
    
    
    #hatching    
    hatch_f = None
    hatch =  None
    h_color = None
    h_alpha = None
    
    
    #===========================================================================
    # overrides
    #===========================================================================
    outpath = 'none'
    
    def __init__(self, *vars, **kwargs):
        """
        logger = mod_logger.getChild('Plotpar_wrap') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')"""
        
        #initilzie the first baseclass
        super(Plotpar_wrap, self).__init__(*vars, **kwargs) 
        logger = self.logger.getChild('_init_')
        #=======================================================================
        # custom atts
        #=======================================================================

        
        #hist bins
        if not self.hist_bins is None:
            if not self.hist_bins == 'auto':
                try:
                    self.hist_bins = int(self.hist_bins)
                except:
                    'need to eval this later'
                    self.hist_bins = str(self.hist_bins).strip()
            
        #annotation
        #arrow
        if not self.anno_arrow_tup is None:
            self.anno_arrow_tup = eval(self.anno_arrow_tup)
        else:
            self.textcoords = None
            
        if not self.annot_kwargs is None:
            self.annot_kwargs = eval(self.annot_kwargs)
            
            if not isinstance(self.annot_kwargs, dict): raise IOError
            
        if not self.anno_tup is None:
            self.anno_tup = eval(self.anno_tup)
            
            if not isinstance(self.anno_tup, tuple): raise IOError
            
        if not self.arrowprops is None:
            self.arrowprops = eval(self.arrowprops)
            
            if not isinstance(self.arrowprops, dict): 
                raise IOError
            
        #=======================================================================
        # custom atts
        #=======================================================================
        #eval pars
        
        self.chk_eval_par('fmt_func_str')
        self.chk_eval_par('label', post=True)
        
        
        #hist bins
        if not self.hist_bins is None:
            if not self.hist_bins == 'auto':
                self.hist_bins = int(self.hist_bins)
        
        
        
        logger.debug('finished _init_ as %s'%self.name)
            
        return
    
    def chk_eval_par(self,  #handling for mandatory eval pars
                     attn, 
                     post=True, #post atts MUST be evaluatable, and are activated during the plot
                     ):
        logger = self.logger.getChild('chk_eval_par')
        v = getattr(self, attn) #pull the attribute
        
        if not v is None: #refrmat as a string
            new_v = str(v)

            if post:
                #needs to start with a quote
                if not new_v.startswith('\''):
                    
                    logger.warning('\'%s\' didnt start with an apostrophe... adding'%attn)
                    
                    """this is adding weird apostraphes
                    new_v1 = '\'%s'%new_v"""
                    new_v1 = new_v
                    
                else: 
                    new_v1 = new_v
                    
                    
                #should not end with a quote
                if new_v1.endswith('\''):
                    logger.warning('\'%s\' ends with an apostrophe! removing it for you')
                    new_v1 = new_v1[:-1]
                    
            
            else: #pre eval pars. allow for non eval
                if new_v.startswith('\''):
                    new_v1 = eval(new_v)
                    
                else: new_v1 = new_v
                
            try:
                new_v1 = eval(new_v1)
            except:
                logger.warning('failed to evaluate %s'%attn)
                
            #reset this attribute
            setattr(self, attn, new_v1)
    
    def check_plotpars(self):
        logger = self.logger.getChild('check_plotpars')
        
        if not self.fmt_func_str is None:
            if not isinstance(self.fmt_func_str, str):
                raise IOError
            
        if not self.anno_tup is None:
            if not isinstance(self.anno_tup, tuple): 
                raise IOError
        
    
    def get_value_formatted(self, value): #format a single value with your formatter eval
        
        if self.fmt_func_str is None:
            return str(value)
        else:
            try:
                return eval(self.fmt_func_str)
            except:
                logger = self.logger.getChild('get_value_formatted') #have to use this as our own logger hasnt loaded yet
                logger.error('failed to eavlaute \'%s\' on \'%s\''%(self.fmt_func_str, value))
                raise IOError
            
            
            
        """
        '$' + "{:,.2f}".format(value/1e6)
        """

            
            

class Variable_wrap(hp_data2.Dataset): #variable methods to be shared between synthetic and raw
    allow_null_f = False
    sceno = None
    syn_eval = None
    boolidx_str = None
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Variable') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
                #initilzie the first baseclass
        super(Variable_wrap, self).__init__(*vars, **kwargs) 
        
        
        if self.label is None:
            self.label = self.name + ' (%s)'%self.units
            
        
        return
    
    def index_slicer(self):
        
        if not self.boolidx_str is None:
            logger = self.logger.getChild('index_slicer')
            df = self.parent.data
            
            try:
                boolidx = eval(self.boolidx_str)
            except:
                logger.error('failed to evaluate \'%s\' on dataset \'%s\''%(self.boolidx_str, self.parent.name))
                raise IOError
            """
            hp_pd.v(df)
            """
            
            self.boolidx = boolidx.values
            
            logger.debug('built index slicer with %i (of %i) entries selected'%(self.boolidx.sum(), len(df)))
            
            
            
    
    def apply_syn_eval(self):
        logger = self.logger.getChild('apply_syn_eval')
 
        if self.data is None:
            df = self.parent.data
        elif isinstance(self.data, pd.DataFrame):
            df = self.data
        elif isinstance(self.data, pd.Series):
            ser = self.data
            df = None
        else:
            logger.error('got unexpected data type')
            raise IOError

        full_df = self.parent.data
        
        """
        self.name
        hp_pd.v(df)
        
        df.mean(axis=1)
        
        full_df.loc[:,('od5.Flood.dmg_gw','dt_2046')] / full_df.loc[:,('od6.Flood.dmg_sw','dt_2046')]
        
        df.columns
        """
        
        self.data = eval(self.syn_eval)
        """
        df.loc[:,idx['2016','10':'8']].reset_index(drop=True)
        df1 = df.loc[:,idx[:,'10':'8']].reset_index(drop=True)
        hp_pd.v(df1)
        hp_pd.v(self.data)
        df1
        
        full_df.columns.get_level_values(0).unique()
        df.loc[:,
        
        try:
            self.data = eval(self.syn_eval)
        except:
            logger.error('failed on \'%s\''%self.syn_eval)
            raise IOError"""

         
        if not df is None:
            logger.debug('from parent data (%s) applied \"%s\' and got %s'%
                         (str(df.shape), self.syn_eval, str(self.data.shape)))
         
        return

    
    def check_var(self):
        logger = self.logger.getChild('check_var')
        if self.data is None:
            logger.error('got NONE for data')
            raise IOError
        
        if (not isinstance(self.data, pd.Series)) and (not isinstance(self.data, pd.DataFrame)):
            logger.error('got unexpected type')
            raise IOError
        
        if not len(self.data) > 0:
            logger.error('got bad data length')
            raise IOError
        
        #check for nulls
        if not self.allow_null_f:
            if np.any(pd.isnull(self.data)):
                raise IOError
            
            
        #check label
        if not isinstance(self.label, str):
            logger.error('got uenxpected value for lable \'%s\''%type(self.label))
            raise IOError
        
        return
    

        
class Var_raw( #raw variable object
               Plotpar_wrap, #plotting parameters
              Variable_wrap,  #singel variable specific parameters
              ):
    
    post_load_eval = None
    
    lvl0val = None
    lvl1val = None
    lvl2val = None
    
    def __init__(self, *vars, **kwargs):
        
        
        #initilzie the first baseclass
        super(Var_raw, self).__init__(*vars, **kwargs) 
        logger = self.logger.getChild('init') #have to use this as our own logger hasnt loaded yet
        #=======================================================================
        # custom atts
        #=======================================================================
        #hierarchy
        self.sceno = self.parent
               
        #=======================================================================
        # loader funcs
        #=======================================================================
        
        """
        I want to let these fail
        """
        self.index_slicer()
        
        #primary data loading
        try: self.load_data_from_scen()
        except: logger.warning('failed to execute load_data_from_scen')
            
        #secondary custom scripts
        if not self.syn_eval is None:
            try: 
                self.apply_syn_eval()
            except: 
                logger.warning('failed to execute apply_syn_eval')
                
                
        try: self.check_var()
        except: logger.warning('check failed for \'%s\''%self.name)
            
        logger.debug("finished")
        
        return

        
    def load_data_from_scen(self): #pull your data from your parent
        """
        setup for dxcols and df
        
        self.lvl1val = str(10)
        
        df.columns
        
        hp_pd.v(df)
        
        df.loc[:,
        """
        logger = self.logger.getChild('load_data_from_scen')
        df = self.parent.data
        
        if isinstance(df.columns, pd.MultiIndex):
            logger.debug('loading from dxcol with \'%s\' and \'%s\''%(self.lvl0val, self.lvl1val))
            
            if not self.lvl2val is None:
                

                self.data= df.loc[:, (self.lvl0val, self.lvl1val, self.lvl2val)]
            
            #series type
            elif not self.lvl1val is None:
                'todo: add nlevels check'
            
                self.data = df.loc[:, (self.lvl0val, self.lvl1val)]
                
            elif not self.lvl0val is None:
                
                self.data = df.loc[:, self.lvl0val]
                
                
            #df type
            else:
                logger.warning('no lvl values passed. using full data')
                
                self.data = df.copy()
            
            
        elif isinstance(df.columns, pd.Index):
            #pull a series from the column
            if not self.name in df.columns:
                logger.warning('could not find myself in \'%s\' columns'%self.parent.name)
                #raw_input('\n \n      press any key to load data as None....')
                self.data = None
                
            else:
                
                self.data = df[self.name]
                
        
        else:
            raise IOError
        
        """
        hp_pd.v(df)
        type(data)
        """
        return

    #===========================================================================
    # def post_load(self):
    #     """
    #     not really using this any more, vars are only series type
    #     """
    #     logger = self.logger.getChild('post_load')
    #     
    #     df = self.data
    #     
    #     df2 = eval(self.post_load_eval)
    #     
    #     logger.debug('from %s applied \'%s\' to get %s'%
    #                  (str(self.data.shape), self.post_load_eval, str(df2.shape)))
    #     
    #     self.data = df2
    #     
    #     return
    #===========================================================================
      
#===============================================================================
# class Var_syn( #synthetic post/processed variable
#                pscripts2.Fdmg_da,
#                Plotpar_wrap,
#                Variable_wrap, #needs to be at the bottom
#                
#               ):
#     
#     syn_eval = None
#     raw_df_nm = None
#     raw_df = None
#     
#     try_inher_s = []
#     """dont like this
#     try_inher_s = ['color',  'marker', 'linewidth', 'linestyle', 'fillstyle', 'allow_null_f', 'hatch', 'units',\
#       'markersize', 'fmt_func_str',  'alpha', 'h_alpha', 'label', 'hatch_f', 'h_color']"""
#     
#     def __init__(self, *vars, **kwargs):
#         logger = mod_logger.getChild('Var_syn') #have to use this as our own logger hasnt loaded yet
#         logger.debug('start __init__')
#         
#         #initilzie the first baseclass
#         super(Var_syn, self).__init__(*vars, **kwargs)
#         
#         logger = self.logger.getChild('_init_') #have to use this as our own logger hasnt loaded yet
#         
#         #=======================================================================
#         # custom atts
#         #=======================================================================
#         self.sceno = self.parent
#         
#         #attach teh raw data if provided
#         if not self.raw_df_nm is None:
#             try: self.load_from_raw()
#             except: logger.warning('failed to execute load_from_raw()')
#             
#         #apply secondary custom evals
#         try: 
#             self.apply_syn_eval()
#         except:  
#             logger.warning('failed to execute self.apply_syn_eval()')
#             
#         self.sceno.vars_d[self.name] = self #add yourself to your parents vars
#         'dont want to wait for this to happen after everything is loaded'
#         
#     def load_from_raw(self):
#         self.data = self.parent.kids_d[self.raw_df_nm].data.copy()
#         
#         self.index_slicer()
# 
# 
#     
#     def check_syn(self):
#         
#         self.check_var()
#         
#         if not isinstance(self.data, pd.Series):
#             raise IOError
#         
# class Var_syn_x( #synthetic post/processed variable crossing scenarios
#                pscripts2.Fdmg_da,
#                Plotpar_wrap,
#                Variable_wrap, #needs to be at the bottom
#               ):
#     
#     syn_eval = None
#     scen_nm_l = None
#     var_nm = None
# 
#     
#     
#     def __init__(self, *vars, **kwargs):
#         logger = mod_logger.getChild('Var_syn_x') #have to use this as our own logger hasnt loaded yet
#         logger.debug('start __init__')
#         
#         #initilzie the first baseclass
#         super(Var_syn_x, self).__init__(*vars, **kwargs)
#         
#         #=======================================================================
#         # custom atts
#         #=======================================================================
#         self.scen_nm_l = eval(self.scen_nm_l)
#         
#         if not isinstance(self.scen_nm_l, list):
#             raise IOError
# 
#         
#         self.load_from_xsec()
#         
#         if not self.syn_eval is None:
#             self.apply_syn_eval()
#         
#         logger.debug("finished")
#         
#     def load_from_xsec(self): #load your scenario cross section data
#         
#         logger = self.logger.getChild('load_from_xsec')
#                
#         
#         #=======================================================================
#         # loop through each scenario
#         #=======================================================================
#         first = True
#         for sceno_n in self.scen_nm_l:
#             #get this scenario
#             sceno= self.session.scen_d[sceno_n]
#             
#             #get your variable from the sceno
#             vari = sceno.vars_d[self.var_nm]
#             
#             data = vari.data.copy() #get this variables data
#             
#             #setup the main data container
#             if first:
#                 if isinstance(data, pd.Series):
#                     main_data = pd.Series(name = self.var_nm, dtype = data.dtype)
#                 elif isinstance(data, pd.DataFrame):
#                     main_data = pd.DataFrame(columns = data.columns)
#                     
#                 first = False
#                 
#             #fill the container
#             main_data = main_data.append(data, ignore_index = True)
#             
#             logger.debug('added %s  from \'%s.%s\''%(str(data.shape),sceno_n, self.var_nm ))
#         
#         #=======================================================================
#         # wraup up
#         #=======================================================================
#             
#         logger.info('built data cross section from %i scenarios with %s'%(len(self.scen_nm_l), str(main_data.shape)))
#         
#         self.data = main_data
#         
#         return      
#     
#===============================================================================

                    
        
      
class Pair( #pair of variables
        Plotpar_wrap,
           hp_oop.Child, 
           ): 
    
    var1_nm = None
    var2_nm = None
    var3_nm = None
    
    vars_d = None
    
    trim_f = False
    
    #===========================================================================
    # Plot par defaults
    #===========================================================================
    
    
    
    fillstyle = 'none' #marker fill style
    'these are the defaults if the user leaves the par blank'
    
    anno_tup = '(\'mean\', \'mean\')' #tuple for locating the annotation
    xycoords = 'data'
    #arrowprops see below for default
    
    hist_bins = 'auto'
    hist_density = True
    histtype = 'bar' 
    hist_rwidth = 0.9
    
    
    box_notch = False
    box_whis = 1.0
    box_meanline = True
    

    
    

    #===========================================================================
    # object handling
    #===========================================================================
    sceno = None
    
    var_inher_s = set()
    
    """make the user pick each of these. dont like inheritance going on behind the scenes
    var_inher_s = set(['units','color','linestyle','linewidth','alpha','marker', \
                       'markersize', 'fillstyle', 'hatch_f', 'h_color', 'h_alpha',\
                        'hist_bins', 'hist_norm_f', 'histtype'])"""
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Pair') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
        #initilzie the first baseclass
        super(Pair, self).__init__(*vars, **kwargs) 
        

            
        if self.arrowprops is None:
            self.arrowprops = dict(arrowstyle="->", connectionstyle="arc3")
        #=======================================================================
        # custom setup funcs
        #=======================================================================
        self.collect_vars()
        
        self.set_atts_from_var() #set your attributes from the data pairs
        
        self.set_label()

        self.check_pair()
        
        logger.debug('finished _init_ ')
        
        return
        
    def collect_vars(self):
        logger = self.logger.getChild('collect_vars')
        
        #=======================================================================
        # cross section pairs
        #=======================================================================

        if self.scenario == '*x': 
            all_vars_d = self.session.varx_d
        
        #=======================================================================
        # pairs from scenarios
        #=======================================================================
        else:
            #=======================================================================
            # get your scenarios variables
            #=======================================================================
            class_d = self.session.family_d['Scenario']
            self.sceno = hp_dict.value_by_ksearch(self.scenario, class_d)
            
            #=======================================================================
            # pre checks
            #=======================================================================
            if self.sceno is None:
                logger.error('could not find \'%s\' in the loaded scenarios'%self.scenario)
                """
                class_d.keys()
                """
                raise IOError
            
            if not self.sceno.name == self.scenario:
                logger.error('scenario name mismatch')
                raise IOError
            
            all_vars_d = self.sceno.vars_d

        #=======================================================================
        # loop through this container and pull out the ones you want
        #=======================================================================
        d = OrderedDict()
        
            
        for attn in ['var1_nm', 'var2_nm', 'var3_nm']:
            v = getattr(self, attn)

            if not v is None:
                try:
                    d[v] = all_vars_d[v] #get this subset
                except:
                    if not v in list(all_vars_d.keys()):
                        logger.error('could not find \'%s\' in the scenario variables'%v )
                    raise IOError
        

            
        logger.debug('finished with %i pairs collected: %s'%(len(d), list(d.keys())))
        
        self.vars_d = d
        
        if len(d) == 0:
            logger.warning('failed to collect any variables')

        
        return
    
    def trim_to_union(self): #trim vars to common index
        """
        unfortuantely we're not setup to trim variables like this
        because we call data from the variable during plotting (not from the pair) any changes we make 
        woudl affect other pairs
        """
        raise IOError
        
        #=======================================================================
        # setup
        #=======================================================================
        logger = self.logger.getChild('trim_to_union')
        
        #build blank frame
        df = pd.DataFrame()
        
        #=======================================================================
        # trim down 
        #=======================================================================
        #fill the frame with data from each variable
        for name, varo in self.vars_d.items():
            
            df[name] = varo.data
            
        df =  df.dropna(axis='index')
        
    def set_label(self):
        
        if self.label is None:
            self.label = self.name + '(%s)'%self.units
            
        elif self.label == '*scen':
            self.label = self.sceno.label
        elif self.label.startswith('\''):
            self.label = eval(self.label)
        

    def set_atts_from_var(self):
        logger = self.logger.getChild('set_atts_from_var')
        

        key_var = list(self.vars_d.values())[0] 


        for attn in self.var_inher_s:
            ov = getattr(self, attn)
            if ov is None: #only overwrite blank attributes on the pairs tab
                v = getattr(key_var, attn)
                setattr(self, attn, v)
            
        logger.debug('inherited %i attributes from variable \'%s\''%(len(self.var_inher_s), key_var.name))
        

        
        
        #=======================================================================
        # build the title
        #=======================================================================
        first = True
        for k, v in self.vars_d.items():
            if first:
                title = '%s %s'%(self.scenario, k)
                first = False
            else:
                title = title + ' on %s'%k
            
        self.title = title
        return 
    
    def check_pair(self):
        logger = self.logger.getChild('check_pair')
        var_data_len = None
        var_data_shp = None
        var_index = None
        
        
        if not self.anno_arrow_tup is None:
            if not isinstance(self.anno_arrow_tup, tuple):
                logger.error('got unepxected type for anno_arrow_tup: %s'%type(self.anno_arrow_tup))
                raise IOError
        
        for name, varo in self.vars_d.items():
            
            if varo.data is None:
                logger.warning('no data loaded. skipping check')
                return
            
            if not len(varo.data.shape) == 1:
                'all paired data should be 1D'
                logger.error("got unexpected shape %s on \'%s\'. All paired data should be 1D"
                             %(str(varo.data.shape), varo.name))
                raise IOError
            #===================================================================
            # set from the first
            #===================================================================
            if var_data_len is None:
                var_data_len = len(varo.data)
                var_index = varo.data.index
                var_data_shp = varo.data.shape
                #null_boolidx = pd.isnull(varo.data)
                continue
            
            #===================================================================
            # check subsequen
            #===================================================================
            if not var_data_len == len(varo.data):
                logger.error('variable lengths do not match')
                raise IOError
            
            if not np.all(var_index == varo.data.index):
                logger.error('indexes do not match')
                raise IOError
            
            #===================================================================
            # check hierarchy
            #===================================================================
            if not varo.sceno.name == self.scenario:
                logger.error('scenario mismatch with \'%s\': \'%s\''%(varo.name, varo.sceno.name))
                raise IOError
            
            #===================================================================
            # check dimensiosn
            #===================================================================
            if not var_data_shp == varo.data.shape:
                raise IOError
            
        if self.label is None:
            logger.warning('got no label!')
            
            

        return
    
    """
    self.vars_d.values()[0].data
    self.vars_d.keys()
    """
                 
class Plotr( #collection of pairs for plotting
            Plotpar_wrap, 
            hp_oop.Child,): 
    
    #===========================================================================
    # default pars
    #===========================================================================
    fmt = 'svg' #format for figure saving
    dpi = 300
    #transp_f = True #transparent figure saving
    #===========================================================================
    # user pars
    #===========================================================================
    pairs_nl = None #list of pairs associated with this plot
    plot_func = 'basic()' #plot command to generate from this
    
    figsize = (6,4)
    subplot = 111
    grid_f  = False #flag to turn teh grid on
    logx_f = False #flag to make a log plot on the xaxis
    
    flip_f = False
    
    yfmt_func_str = None#histograms generally have an integer format on the y axis
    
    post_funcs_l = None
    
    #===========================================================================
    # possible user pars
    #===========================================================================
    xticklabrot = 45
    
    
    #===========================================================================
    # calculated pars
    #===========================================================================
    pairs_d     = None #dictionary of data pair objects
    
    
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Plotr') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
        #initilzie the first baseclass
        super(Plotr, self).__init__(*vars, **kwargs) 
        
        #=======================================================================
        # custom atts
        #=======================================================================
        self.arrow_tips = set()
        self.pairs_nl = eval(self.pairs_nl)#hp_basic.str_to_list(self.pairs_nl)
        
        if isinstance(self.figsize, str):
            self.figsize = eval(self.figsize)
            
            
        self.chk_eval_par('yfmt_func_str')
        
        
        if not self.post_funcs_l is None:
            self.post_funcs_l = eval(self.post_funcs_l)
            

            
            
        #=======================================================================
        # loader funcs
        #=======================================================================
        
        
        self.collect_pairs()
        
        self.check_plotr()
        
        logger.debug('finished _init_ ')
        
        return
        
            
    def check_plotr(self):
        logger = self.logger.getChild('check_plotr')
        if not isinstance(self.pairs_nl, list):
            raise IOError
        
        if not isinstance(self.figsize, tuple):
            raise IOError
        
        if not self.title is None:
            if not self.title.startswith('\''): #exclude recognized pyevals
                if '%s' in self.title: #shouldn't have any of these then
                    logger.error('custom pyeval title names must begin with \'')
                    raise IOError
                
        if not self.post_funcs_l is None:
            if not isinstance(self.post_funcs_l, list):
                raise IOError
            
            for v in self.post_funcs_l:
                if not isinstance(v, str):
                    raise IOError
                
        #check for pair duplicates
        nm_l = []
        
        for k, v in self.pairs_d.items():
            if v.name in nm_l:
                logger.error('got repeat variable name \'%s\''%v.name)
                raise IOError
            
            nm_l.append(v.name)
            
        return
        
    def collect_pairs(self):
        logger = self.logger.getChild('collect_pairs')
        class_d = self.session.family_d['Pair']
        d = OrderedDict()
        
        sceno_s = set() #place holder for scenario obj

        #scen_style_f = False
        
        lasto = None
        for onm in self.pairs_nl:
            obj = hp_dict.value_by_ksearch(onm, class_d) #pull the pair from the family
            
            
            if obj is None:
                logger.error('unable to find \'%s\''%onm) #missing quotes?
                raise IOError
            
            d[onm] = obj
                
            #add thsi scenario
            if not obj.sceno is None:
                sceno_s.update([obj.sceno])

            
        #=======================================================================
        # wrap up
        #=======================================================================
        if not len(sceno_s) == 0:
            self.sceno = list(sceno_s)[0]
            
            #get the sceno name string
            first = True
            last = False
            for indx, sceno in enumerate(sceno_s):
                if first:
                    sceno_str = '%s'%sceno.name
                    first = False
                elif last:
                    sceno_str = sceno_str + ' and %s'%sceno.name
                    
                else:
                    sceno_str = sceno_str + ', %s'%sceno.name
                    
                if indx == len(sceno_s)-2:
                    last = True
            
            self.sceno_nm_str = sceno_str
            'attaching this for single scene plots'

            
        
        logger.debug('finished with %i pairs collected: %s'%(len(d), list(d.keys())))
        
        self.pairs_d = d
        #self.scen_style_f = scen_style_f
        
            
        
        return
        
        
    def plot(self, wtf=None, outpath=None):
        
        if wtf is None: wtf = self.session._write_figs
        
        #=======================================================================
        # execute the plotter
        #=======================================================================
        ax =  eval('self.' + self.plot_func)
        
        #=======================================================================
        # execute post evals
        #=======================================================================
        self.post()
        
        #=======================================================================
        # save the figure
        #=======================================================================
        if wtf:
            self.save_fig(ax.figure, outpath = outpath)
    """
    plt.show()
    """



    
    def basic(self,
              pairs_d   = None, #dictionary of plot variable pairs to generate plot on
              ax        = None, #axis object to add plotting to
              outpath = None, #outpath for file writing
              wtf = False, #file writing flag
              **plot_kwargs
              ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('basic')
        
        if pairs_d is None: pairs_d = self.pairs_d


        
        #=======================================================================
        # setup plot
        #=======================================================================
        if ax is None:
            plt.close()
            #get first objects for default formatting
            pair1 = list(pairs_d.values())[0] #using for default formatting
            
            if not pair1.flip_f:
                xo1 = list(pair1.vars_d.values())[1]
                yo1 = list(pair1.vars_d.values())[0]
            else: #flipped axis
                xo1 = list(pair1.vars_d.values())[0]
                yo1 = list(pair1.vars_d.values())[1]
                
            
            #title
            if self.title is None: #just take from first
                title = 'basic %s'%pair1.title
            elif self.title.startswith('\''): #dynamic ty tle
                try:
                    title = eval(self.title)
                except:
                    logger.error('unable to eval \"%s\''%self.title)
                    raise IOError
                """
                'New houses for %s'%self.sceno_nm_str
                """
                
            else: title = self.title
                
            #axis labels
            if self.xlab is None:
                xlab = xo1.label
            else:
                xlab = self.xlab
                
                
            if self.ylab is None:
                ylab = yo1.label
            else:
                ylab = self.ylab
            
            
            #plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(self.figsize)
            ax = fig.add_subplot(self.subplot)  
            
            ax.set_title(title)
            ax.set_ylabel(ylab)
            ax.set_xlabel(xlab)
            
            if self.grid_f: ax.grid()
                  
        else:
            fig = ax.figure
            xmin, xmax = ax.get_xlim()
            
        #get the plotting func
        if not self.logx_f:
            plot_func = ax.plot
        else:
            plot_func = ax.semilogx
            
            
        #=======================================================================
        # add all the pairs to the plot
        #=======================================================================
        annos_d = OrderedDict()
        
        logger.debug('adding %i pairs to plot: %s'%(len(pairs_d), list(pairs_d.keys())))
        for pn, pair in pairs_d.items():
            logger.debug("adding \'%s\' to plot"%pn)
            
            #===================================================================
            # #get vars
            #===================================================================
            if not pair.flip_f:
                xvar = list(pair.vars_d.values())[1]
                yvar = list(pair.vars_d.values())[0]
            else:
                xvar = list(pair.vars_d.values())[0]
                yvar = list(pair.vars_d.values())[1]
                
            if xvar.data is None:
                logger.error('failed to load the xvar for \'%s.%s\''%(pn, xvar.name))
                raise IOError
            if yvar.data is None:
                logger.error('failed to load the yvar for \'%s.%s\''%(pn, yvar.name))
                raise IOError
            #get data arrays
            xar = xvar.data.values
            yar = yvar.data.values
            'all the checking should be done on the pair'
            
            #===================================================================
            # data checks
            #===================================================================
            if not (len(xar.shape) == 1) & (len(yar.shape) == 1):
                raise IOError
            

            #===================================================================
            # collect styles
            #===================================================================
            """NO! make the user set the pair how they like in the pars
            if self.scen_style_f: #style based on the scenario
                raise IOError #not using
                styo = pair.parent
                logger.debug('styling from scen \'%s\''%styo.name)
            else: #style based on the pair
                styo = pair
                logger.debug('styling from pair \'%s\''%styo.name)"""
                
            kw_l = ['label', 'color', 'linestyle', 'linewidth','alpha', 'marker', 'markersize', 'fillstyle']
            sty_d =  get_stykwargs_from_obs(self, pair, kw_l,logger=self.logger)
     
            #merge with kwargs
            sty_d.update(plot_kwargs)
            
            #kwarg check
            if sty_d['label'] is None:
                raise IOError

            
            pline = plot_func(xar, yar, **sty_d)
            """
            plt.show()
            pairs_d.keys()
            """
            #=======================================================================
            # add hatch
            #=======================================================================
            if self.hatch_f or pair.hatch_f:
                #collect style kwargs
                kw_l2 = ['hatch_color, hatch_alpha, hatch']
                hsty_d =get_stykwargs_from_obs(self, pair, kw_l2,key_substr = 'hatch_',logger=self.logger)

                #set the hatching
                polys = ax.fill_between(xar, yar, y2=0,**hsty_d)
                
            #===================================================================
            # annotation
            #===================================================================
            if self.annot is None:
                annot = pair.annot
            else:
                annot = self.annot
            
            #get the default annotation
            if annot == '*default':
                xmean = xvar.get_value_formatted(xar.mean())
                ymean = yvar.get_value_formatted(yar.mean())
                annot = '%s \ncnt = %i \nxmean = %s \nymean = %s'\
                    %(pair.label, len(xar), xmean, ymean)

            #build the que
            if not annot is None:
                annos_d[pn] = self.get_annot_que(annot, pair, xar, yar,ax, color = sty_d['color'])
                
            #===================================================================
            # reformat the axis tick labels
            #===================================================================
            if not xvar.fmt_func_str is None:
                self.reformat_tick_label(xvar, ax =ax, axis = 'x')
                
            if not yvar.fmt_func_str is None:
                self.reformat_tick_label(yvar, ax =ax, axis = 'y')
                
            logger.debug("finished on \'%s\'"%pn)
            
        #=======================================================================
        # add annotation
        #=======================================================================
        logger.debug("adding %i annotation commands to the plot"%len(annos_d))
        for pn, (func, vars, annkwargs) in annos_d.items():
            logger.debug('executing annotation from \'%s\''%pn)
            _ = func(vars, **annkwargs) #execute this

        #=======================================================================
        # legend
        #=======================================================================
        plt.legend()
        #=======================================================================
        # saving        
        #=======================================================================
        if wtf: 
            self.save_fig(fig, outpath = outpath)
            

        return ax
    

    
    def callouts(self, #scatter plot with callouts
              pairs_d   = None, #dictionary of plot variable pairs: indp, dep, labels
              ax        = None, #axis object to add plotting to
              outpath = None, #outpath for file writing
              **kwargs
              ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('callouts')
        if pairs_d is None: pairs_d = self.pairs_d
        
        #=======================================================================
        # prechecks
        #=======================================================================
        pair1 = list(pairs_d.values())[0] #using for default formatting
        if not len(pair1.vars_d) == 3:
            raise IOError #expects a collectio nof 3
        
        
        #=======================================================================
        # make basic plot
        #=======================================================================
        ax = self.basic(pairs_d, ax = ax, wtf = False, outpath = outpath)
        
        #=======================================================================
        # add the labels
        #=======================================================================
        for pnm, pair in pairs_d.items():
            if not len(pair.vars_d) == 3: raise IOError
            #===================================================================
            # #get vars
            #===================================================================
            if not pair.flip_f:
                xvar = list(pair.vars_d.values())[1]
                yvar = list(pair.vars_d.values())[0]
            else:
                xvar = list(pair.vars_d.values())[0]
                yvar = list(pair.vars_d.values())[1]
                
            #get data arrays
            xar = xvar.data.values
            yar = yvar.data.values
            'all the checking should be done on the pair'
            
            #get label
            labvar = list(pair.vars_d.values())[2]
            labar = labvar.data.values
            
            """
            plt.show()
            """
            
            #===================================================================
            # loo pthrough and add each label
            #===================================================================
            for lb, x, y in zip(labar, xar, yar):
                ax.annotate(lb, xy=(x,y))
                
    def hist(self, #scatter plot with callouts
              pairs_d   = None, #dictionary of plot variable pairs: indp, dep, labels
              ax        = None, #axis object to add plotting to
              outpath = None, #outpath for file writing
              wtf = False, #file writing flag
              **histkwargs
              ):
        
        #===================================================================
        # defaults
        #===================================================================
        logger = self.logger.getChild('hist')
        
        if pairs_d is None: pairs_d = self.pairs_d
        

        #get objects
        pair1 = list(pairs_d.values())[0] #using for default formatting
        

        #===================================================================
        # build the axis
        #===================================================================

        if ax is None:
            plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(self.figsize)
            ax = fig.add_subplot(self.subplot)  
            
            
            
            #title
            if self.title is None: #just take from first
                title = 'hist %s'%pair1.title
            else:
                if self.title.startswith('\''): #must be an eval
                    title = eval(self.title)
                else: 
                    title = self.title
                
            #axis labels
            if self.xlab is None:
                xlab = list(pair1.vars_d.values())[0].label #pull from teh first variable of the pair
            else:
                xlab = self.xlab

            #y label
            if self.ylab is None:
                if pair1.hist_norm_f:
                    ylab = 'likelihood'
                else: 
                    ylab = 'count'
            else:
                ylab = self.ylab
                
            #set all these
            ax.set_ylabel(ylab) 
            ax.set_xlabel(xlab)
            ax.set_title(title)
            

        else:
            fig = ax.figure
            xmin, xmax = ax.get_xlim()
            
        #===================================================================
        # build the figures
        #===================================================================
        annos_d = OrderedDict()
        bin_res = None
        
        for pnm, pair in pairs_d.items():
            logger.debug('generating historgram for \'%s\''%pnm)
            
            if not len(pair.vars_d) == 1:
                raise IOError #expects only 1 var
            
            #get the data/objects
            vari = list(pair.vars_d.values())[0]
            var_ar = vari.data.values #get data from var
            
            """
            vari.name
            pnm
            pair.color
            """
            
            #setup the bins
            if  (not pair.hist_bins == 'auto') and (not isinstance(pair.hist_bins, int)):
                #raise IOError #cant get the single bin to show up
                if not bin_res is None: delta = bin_res[1] - bin_res[0] #pull from last hist
                pair.hist_bins = eval(pair.hist_bins)
            
            #collect the syles
            kw_l = ['hist_density', 'histtype', 'hist_bins', 'alpha', 'color', 'label', 'hist_rwidth']
            sty_d = get_stykwargs_from_obs(self, pair, kw_l,key_substr = 'hist_',logger=self.logger)
            
            #add the passed kwargs
            sty_d.update(histkwargs)
            
            #make the plot            
            n, bin_res, patches = ax.hist(var_ar,**sty_d)
            """
            n:  values of the histogram bins
            """
            
            #=======================================================================
            # Add text string 'annot' to lower left of plot
            #=======================================================================
            if self.annot is None:
                annot = pair.annot
            else:
                annot = self.annot
            
            #get the text
            if annot == '*default':
                mean_str = vari.get_value_formatted(var_ar.mean())
                spread_str = vari.get_value_formatted(var_ar.max() - var_ar.min())
                annot = ' %s \n n = %i \n bins = %i \n mean = %s \n spread = %s'\
                    %(pair.label, len(var_ar), len(bin_res)-1, mean_str, spread_str)

            
            if not annot is None:
                annos_d[pnm] = self.get_annot_que(annot, pair, var_ar, n,ax)
                
            #=======================================================================
            # reformat tick labels
            #=======================================================================
            if not vari.fmt_func_str is None:
                self.reformat_tick_label(vari, ax =ax, axis = 'x')
                
            if not self.yfmt_func_str is None:
                self.reformat_tick_label(self, ax =ax, axis = 'y', fmt_func_str =self.yfmt_func_str  )
        
            logger.debug('plot generated')

        #=======================================================================
        # add annotation
        #=======================================================================
        logger.debug("adding %i annotation commands to the plot"%len(annos_d))
        for pn, (func, vars, annkwargs) in annos_d.items():
            logger.debug('executing annotation from \'%s\''%pn)
            _ = func(vars, **annkwargs) #execute this
            
        #=======================================================================
        # saving        
        #=======================================================================
        plt.legend()
            
        if wtf: 
            self.save_fig(fig, outpath = outpath)
            """
            plt.show()
            """
            
        return ax
     
    def box(self, #generate a box plot
              pairs_d   = None, #dictionary of plot variable pairs to generate plot on
              ax        = None, #axis object to add plotting to
              outpath = None, #outpath for file writing
              wtf = False, #file writing flag
              **boxkwargs): 
        
        """
        While Id rather plot one at a time
        
        NO!
        boxplot is generally used to plot all data dimenions at once
        however, for the way we've set up styling, its easier to loop and add one at a time
        """
        
        #===================================================================
        # defaults
        #===================================================================
        logger = self.logger.getChild('box')
        if wtf is None: wtf = self.session._write_figs
        if pairs_d is None: pairs_d = self.pairs_d
        
        pos_l = list(range(0, len(pairs_d), 1)) #get the set of positions
        

        #get objects
        pair1 = list(pairs_d.values())[0] #using for default formatting
        
        #=======================================================================
        # setup axis
        #=======================================================================
        if ax is None:
            plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(self.figsize)
            ax = fig.add_subplot(self.subplot)  

            #title
            if self.title is None: #just take from first
                title = 'box plot %s'%pair1.title
            else:
                if self.title.startswith('\''): #must be an eval
                    title = eval(self.title)
                else: 
                    title = self.title
                
            #x axis labels
            if self.xlab is None:
                xlab = None
            else:
                xlab = self.xlab #generally scenario

            #y label
            if self.ylab is None:
                ylab = list(pair1.vars_d.values())[0].label #pull from teh first variable of the pair
            else:
                ylab = self.ylab
                
            #set all these
            _ = ax.set_ylabel(ylab) 
            _ = ax.set_xlabel(xlab)
            _ = ax.set_title(title)
            


        else:
            fig = ax.figure
            
        #=======================================================================
        # loop through each data set and add the plot
        #=======================================================================
        
        #setup ICs
        annos_d = OrderedDict()
        bin_res = None
        xticklabs = [] #need a blank starter entry?
        
        
        cnt = 0
        
        
        for pnm, pair in pairs_d.items():
            logger.debug('generating historgram for \'%s\''%pnm)
            
            #precheck
            if not len(pair.vars_d) == 1:
                raise IOError #expects only 1 var
            
            #get the data/objects
            vari = list(pair.vars_d.values())[0]
            var_l = vari.data.values.tolist() #get data from var
            
            
            #===================================================================
            # #get plotting values
            #===================================================================
            positions = [pos_l[cnt]]
            pkw_l = ['box_notch', 'box_whis', 'box_meanline', 'box_widths']
            boxplt_d = get_stykwargs_from_obs(self, pair, pkw_l, key_substr = 'box_',logger=self.logger)
            
            boxplt_d.update(boxkwargs) #add the custom key s
            
            #===================================================================
            # get formatters
            #===================================================================
            fkw_l = ['marker', 'markersize', 'fillstyle', 'markerfacecolor', 'color', 'markeredgecolor']
            flierprops = get_stykwargs_from_obs(self, pair, fkw_l,logger=self.logger)
            
            bkw_l = ['linestyle', 'linewidth', 'color']
            boxprops = get_stykwargs_from_obs(self, pair, bkw_l,logger=self.logger)
            
            whiskerprops = boxprops #ust using the same as the box
            capprops = boxprops
            medianprops = boxprops

            #===================================================================
            # #get the plot
            #===================================================================
            res_d = ax.boxplot(var_l, 
                               positions = positions, #get the position for this plot
                               manage_xticks = False, #dont update the x axis 
                               boxprops = boxprops,
                               flierprops = flierprops, #properties for fliers
                               whiskerprops = whiskerprops , #props dict for the whiskers
                               capprops = capprops,
                               medianprops = medianprops,
                               **boxplt_d)
            
            #collect formatters
            xticklabs.append(pair.label)
            
            #=======================================================================
            # Que the Annotation
            #=======================================================================
            if self.annot is None:
                annot = pair.annot
            else:
                annot = self.annot
            
            #default annotation
            if annot == '*default':
                
                #get quartiles
                'wont work for horizontal boxes'
                botw_l2d, topw_l2d = res_d['whiskers'] #get teh whisker lines
                qlow = min(botw_l2d._y) 
                qhigh = max(topw_l2d._y)
                
                qlow_str = vari.get_value_formatted(qlow) 
                qhigh_str = vari.get_value_formatted(qhigh)
                
                #get mean
                var_ar = vari.data.values
                mean_str = vari.get_value_formatted(var_ar.mean())

                annot = ' %s \n n = %i \n  qhigh = %s \n mean = %s \n qlow = %s'\
                    %(pair.label, len(var_ar),  qhigh_str, mean_str, qlow_str)
                    
            elif annot == '*none': annot = None

            
            if not annot is None:
                annos_d[pnm] = self.get_annot_que(annot, pair, np.array(positions), var_ar,ax)
                
            
            cnt +=1
            
            """
            plt.show()
            """
            
        #=======================================================================
        # post formatting
        #=======================================================================
        """not needed if 
        #set teh axis limits manage_xticks = False
        ax.set_xlim(min(pos_l)-1, max(pos_l)+1)"""
        

        
        #reformat the y axis
        if not vari.fmt_func_str is None:
            self.reformat_tick_label(vari, ax =ax, axis = 'y')
            
        #set the x axis labels with some rotation
        #ax.set_xticklabels(xticklabs, rotation = 45)
        plt.xticks(pos_l, xticklabs)
        """

        """
        
        #=======================================================================
        # add annotation
        #=======================================================================
        logger.debug("adding %i annotation commands to the plot"%len(annos_d))
        for pn, (func, vars, annkwargs) in annos_d.items():
            logger.debug('executing annotation from \'%s\''%pn)
            _ = func(vars, **annkwargs) #execute this

        
        if wtf: 
            self.save_fig(fig, outpath = outpath)
            
        return ax
            
    def post(self):
        if self.post_funcs_l is None: return
        logger = self.logger.getChild('post')
        #=======================================================================
        # loop through each post func and evaluate
        #=======================================================================
        l = self.post_funcs_l
        logger.info('executing %i post functions'%len(l))
        for pfunc in l:
            logger.debug('evaluating \'%s\''%pfunc)
            try: eval(pfunc)
            except:
                logger.warning('failed to eavluate \'%s\''%pfunc)
            
        
        return
             

        

        
        
    
    def get_annot_que(self, #get a dictionary for this annotation
                    annot,
                    pair,
                    xar,
                    yar,
                    ax, color = None): #data pair to generate annotation for
        """
        #=======================================================================
        # TODO
        #=======================================================================
        switch this so we are just passing all the pairs to an annotation plot loop
        """
        
        logger = self.logger.getChild('get_annot_que')
        #=======================================================================
        # #get defaults
        #=======================================================================
        if self.anno_tup is None: 
            anno_tup = pair.anno_tup
        else:
            anno_tup = self.anno_tup
            
        annotx_pos = anno_tup[0]
        annoty_pos = anno_tup[1]
        
        if color is None: color = pair.color
        
        #=======================================================================
        # arrow head
        #=======================================================================
        # set the coord system

        xycoords = pair.xycoords
        
        #mean data override   
        if (annotx_pos == 'mean') or (annoty_pos == 'mean'):
            if not xycoords == 'data':
                logger.error('did not got xycoords=\'data\' for \'mean\' anno_tup')
                raise IOError
            
            

        # #getx the location       
        if annotx_pos == 'mean':
            if not xycoords == 'data': raise IOError #need to be relative to data
            an_x = xar.mean() #x location at the mean
            
        elif xycoords == 'data':
            an_x = xar.max()*annotx_pos #scale it
            
        elif xycoords == 'axes fraction': #must be a relative
            an_x = annotx_pos
        
        else: raise IOError
        

        # #get the y location
        if annoty_pos == 'mean':
            if not xycoords == 'data': raise IOError #need to be relative to data
            an_y = yar.mean() #x location at the mean
            
        elif xycoords == 'data':
            an_y = yar.max()*annoty_pos #scale it
            
        elif xycoords == 'axes fraction':
            an_y = annoty_pos
            
        else: raise IOError
            
        #=======================================================================
        # #get the arrow props
        #=======================================================================
        if not pair.anno_arrow_tup is None:

                
            arrow_tail = pair.anno_arrow_tup
            
            arrowprops = pair.arrowprops
            
        else: arrow_tail, arrowprops = None, None
                
        #que this annotation for execution after all the plots are built
        'this makes it easier to scale relative to the final plot'

        annkwargs = {'ax':ax, \
                     'arrow_tip':(an_x, an_y),\
                     'xycoords':xycoords,\
                     'color':color,\
                     'arrow_tail':arrow_tail,
                     'arrowprops':arrowprops,
                     'textcoords':pair.textcoords}
        
        if not pair.annot_kwargs is None:
            annkwargs.update(pair.annot_kwargs)
        
        return [self.set_annot, annot, annkwargs]
    """
    pair.name
    """

            
 
    def set_annot(self, annot_str,              
              ax        = None, #axis object to add plotting to
              arrow_tip = (0.1, 0.1), #x,y for arrow tip
              xycoords = 'axes fraction', #kwarg for xy's coordinate system,
              
              #arrow kwargs
              arrow_tail = None, #xy tup for arrow tail
              arrowprops = None, #dict(facecolor='black', shrink=0.05),
              textcoords = None,
              #bbox_props = dict(boxstyle="round,pad=0.3", fc="cyan", ec="b", lw=2),
              #final formatters
              color = 'black',
              **kwargs):
    
        logger = self.logger.getChild('set_annot')
        #=======================================================================
        # defaults
        #=======================================================================
        if ax == None: ax = plt.gca()
        
        #=======================================================================
        # ensure no duplicate annotations
        #=======================================================================
        
        if arrow_tip in self.arrow_tips: #see if this arrow tip has been used before
            logger.warning('arrow_tips may overlap')
            """make the user fix this
            for x in range(0,1,.1):
                old_x = arrow_tip[0]
                
                #get the new x value
                new_x = old_x + x
                if new_x > 1:
                    new_x = old_x - x
                    
                at = (x, arrow_tip[1]) #get the new tip to try
                
                if at in self.arrow_tips: 
                    continue #try another
                else: #chose this one
                    arrow_tip = at
                    break"""
            
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if xycoords == 'axes fraction':
            for scale in arrow_tip:
                if scale > 0.9: 
                    raise IOError
                if scale < 0.1: 
                    raise IOError
        
        
        #=======================================================================
        # apply the annot
        #=======================================================================
        anno_obj = ax.annotate(annot_str, 
                               xy = arrow_tip,  #Length 2 sequence specifying the (x,y) point to annotate
                               xycoords = xycoords,
                               xytext  = arrow_tail,
                               textcoords = textcoords, 
                               arrowprops= arrowprops,
                               color = color,
                               
                               #bbox = bbox_props,
                               **kwargs
                               )
        
        
        """
        anno_obj = ax.text(x_text, y_text, annot_str, color = color, **kwargs)
        
        arrow_tail = (30, 1)
        anno_obj.remove()
        
        plt.show()
        """
        #=======================================================================
        # wrap up
        #=======================================================================
        self.arrow_tips.update([arrow_tip]) #set this for next time
        
        return anno_obj
    
    def reformat_tick_label(self, #reformat the tick labels
                            obj, #some callable str to apply to the new tick list ('tick' exposed)
                        ax= None, axis = 'y',
                        fmt_func_str =None, #override to apply this eval rather than teh objects
                         ):
    
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('reformat_tick_label')
        if ax == None: ax = plt.gca()
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if fmt_func_str is None:
            if not isinstance(obj.fmt_func_str, str): 
                raise IOError
            
        logger.debug('formatting axis \'%s\' by \'%s\''%(axis, obj.name))
        #===========================================================================
        # get the old ticks
        #===========================================================================
        if axis == 'y':
            old_tick_l = ax.get_yticks()
            
        elif axis == 'x':
            old_tick_l = ax.get_xticks()
            
        else: raise IOError
        
        #===========================================================================
        # build the new ticks
        #===========================================================================
        l = []
        
        #default, build from the object
        if fmt_func_str is None:
            for value in old_tick_l:
                new_v = obj.get_value_formatted(value)
                l.append(new_v)
                
        else: #used passed eval string
            for value in old_tick_l:
                try:
                    new_v = eval(fmt_func_str)
                    l.append(new_v)
                except:
                    logger.warning('failed to eval \'%s\' on \"%s\'. using raw value'%(fmt_func_str, value))
                    l.append(value)
            
            
        #===========================================================================
        # apply the new labels
        #===========================================================================
        if axis == 'y':
            ax.set_yticklabels(l)
            
        elif axis == 'x':
            ax.set_xticklabels(l)
            
        logger.debug('formated the \'%s\' axis ticks with: \'%s\' \n %s'%(axis, obj.name, l))
            
        return
   

            
    def save_fig(self,  fig, #hp fnction for saving figures
             filename = None,
             outpath = None, 
             overwrite  = True, 
             legon= False, 
              **kwargs): 
        """
        plt.show()
        """    
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('save_fig')

        
        ext = '.'+self.fmt
        if legon: plt.legend() #turn teh legend on
        if outpath is None: outpath = self.outpath
        #=======================================================================
        # file name/path
        #=======================================================================
        if filename is None:
            #try and get the name from the figure title
            try:
                title = fig.gca().get_title()
            except: 
                title = title = fig._suptitle.get_text()
                if title is None: 
                    raise ValueError
                
            filename = '%s %s'%(self.name, title)
            
        filepath = os.path.join(self.outpath, filename)

        if not filepath.endswith(ext): #add teh file extension
            filepath = filepath + ext
            
        #===========================================================================
        # check for basedir
        #===========================================================================
        if not os.path.exists(os.path.dirname(filepath)): 
            os.makedirs(os.path.dirname(filepath)) #make this directory
    
        #=======================================================================
        # check for overwrite
        #=======================================================================
        if os.path.exists(filepath): 
            logger.debug('filepath already exists:\n    %s'%filepath)
            
            if not overwrite: raise IOError 
                   
            for sfx in range(0,100, 1):
                newsavefile = re.sub(ext, '', filepath) + '_%i'%sfx + ext
                logger.debug("trying %s"%newsavefile)
                if os.path.exists(newsavefile): 
                    logger.debug('this attempt exists also:    \n %s'%newsavefile)
                    continue #try again
                else:
                    filepath = newsavefile
                    break
                
            logger.warning('savefile_path exists. added sfx: \'%s\''%sfx)
            
        if os.path.exists(filepath):
            logger.error('STILL EXISTS!')
            raise IOError
                                 
        
        fig.savefig(filepath, dpi = self.dpi, format = self.fmt, transparent=self.session.transp_f,
                    **kwargs)


        logger.info('saved figure to file: %s'%(filepath))
        
        
        
        return 
    
    def modify_tick_labs(self, axis='x', **kwargs): #helper func to pass kwargs to plt.xticks
        
        if axis == 'x':
            #retrieve the current values
            oldlocs, oldlabs =  plt.xticks() 
            
            #set teh new values
            plt.xticks(oldlocs, oldlabs, **kwargs)
        
        else:
            raise IOError #todo
        
        return
                
class Plot_handler(object): #wrapper for complex data objects to handle plotting
    
    label = None
    
    hatch_f = False
    hatch =  None
    hatch_color = None
    hatch_alpha = None
    
    outpath = 'none'
    
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Plot_handler') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
        #initilzie the first baseclass
        super(Plot_handler, self).__init__(*vars, **kwargs) 
        
        #=======================================================================
        # custom atts
        #=======================================================================
        if self.label is None:
            self.label = self.name

        logger.debug('finished _init_ ')
        
        return
    
    def load_vars(self):
        logger = self.logger.getChild('load_vars')
        
        #=======================================================================
        # raw variables
        #=======================================================================
        #get teh data
        df = self.session.pars_df_d['vars']
        
        self.vars_d = self.raise_children_df(df, kid_class = Var_raw)
        
        
        #=======================================================================
        # synthetic variables
        #=======================================================================
        """ switched back to loading independently
        #loop througha nd collect all the synthetic vars
        d = dict() #need this so we are not looping over a changing container
        for k, obj in self.vars_d.iteritems():
            if not obj.kids_d is None:
                d.update(obj.kids_d)
                
        
        if len(d) > 0:
            self.vars_d.update(d) #udpate with all these
            logger.debug('loaded %i synthetic vars'%len(d))"""
        
        
        #get teh data
        df = self.session.pars_df_d['vars_syn']
        'just combining witht he raw variables'
        self.vars_d.update(self.raise_children_df(df, kid_class = Var_syn))
        
    def load_pairs(self):
        logger = self.logger.getChild('load_pairs')
        #=======================================================================
        # pairs
        #=======================================================================
        #get the data
        df_raw = self.session.pars_df_d['pairs']
        
        #find your slices
        """
        hp_pd.v(df_raw)
        
        self.pairs_d.keys()
        """
        boolidx = df_raw.loc[:,'scenario'] == self.name
        
        #load from this
        if boolidx.sum() > 0:
            df = df_raw[boolidx]
            self.pairs_d =  self.raise_children_df(df, kid_class = Pair)
        
        else:
            logger.warning('I have no data pairs loaded')
            #time.sleep(3)
            
        return
    
    def load_plotrs(self):
        
        df = self.pars_df_d['plotrs']
        self.plotrs_d =  self.raise_children_df(df, kid_class = Plotr, container = OrderedDict)
    
    def run_all_plots(self):
        logger = self.logger.getChild('run_all_plots')
        for nm, plotr in self.plotrs_d.items():
            plotr.plot()

                
        

    
        
def tick_label_percentage(ax=None, axis='y'):
    
    if ax == None: ax = plt.gca()
    
    if axis == 'y':
        
        #vals = ax.get_yticks()
    
        new_ticks = []
        for old_tick in ax.get_yticks():
            tick = '{:1.1f}%'.format(old_tick*100)
            
            new_ticks.append(tick)
            
        ax.set_yticklabels(new_ticks)
        
    else:
        raise IOError #add code for x axis
    
    return ax

def get_stykwargs_from_obs(
        obj1, #first object to try and get style parameters from
        obj2, 
        kw_l, #list of style parameters
        key_substr = None,
        logger=mod_logger):
    
    logger = logger.getChild('get_stykwargs_from_obs')
    
    d = dict()
    
    #===========================================================================
    # loop through and take att
    #===========================================================================
    for k in kw_l:
        
        if not getattr(obj1, k) is None: #pull from teh Plotr first
            v = getattr(obj1, k)
        else:  #then pull from the pair
            v = getattr(obj2, k)
            
        if not key_substr is None: #remvoe the sub string from teh key
            k1 = re.sub(key_substr, "",k)
        else:
            k1 = k #just use this
            
        d[k1] = v #set into the dict
            
    logger.debug('collected %i entries in dictionary'%len(d))
    
    return d



    
