'''
Created on Nov 1, 2017

@author: cef
hp functions for plotting/visualizing data
'''
# standard imports -------------------------------------------------------------
raise IOError
import os, sys, re, logging
from collections import OrderedDict

import pandas as pd
import numpy as np


mod_logger = logging.getLogger(__name__)

#===============================================================================
# setup matplotlib
#===============================================================================
"""There is probably a cleaner way to set this up
For UNIX runs, we need non-interactive backends?
"""
import matplotlib
"""see plot2
"""

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

import matplotlib.pyplot as plt
    
    

    
# import other helpers ---------------------------------------------------------
import model.sofda.hp.pd as hp_pd
import hp.np
import hp.oop
    

def setup_video(logger = mod_logger, basedir = 'G:/My Drive/Programs/ffmpeg/bin'): #setup the ffmpeg codec
    
    codec_path = os.path.join(basedir, 'ffmpeg.exe')
    
    #codec_path = basedir + '\\ffmpeg.exe'
    #check if codec is installed
    if not os.path.exists(codec_path):
        logger.error('ffmpeg codec not found as: \n    %s'%codec_path)
        raise IOError
    
    #reset the default search path to the location of the ffmpeg codec
    plt.rcParams['animation.ffmpeg_path'] =codec_path
    
    import matplotlib.animation as animation #load the animation module (with the new search path)
    
    logger.debug('codec loaded from %s'%codec_path)


    
def clear_fig_lines(fig, logger=mod_logger): #remove all the lines from the plot
    
    axis_list = fig.axes
    
    axis_count = 0
    for ax in axis_list: #loop through each axis
        
        lines_list = ax.lines #get all the lines
        
        
        
        for line in lines_list: #loop through each line
            line.remove() #remove the line

            
        #logger.info('cleared %i lines from axis %i'%(len(lines_list), axis_count))
        axis_count = axis_count + 1
            
    logger.debug('cleared %i axis of lines'%len(axis_list))
    #font=None #remove variable

    
def add_annot(text, ax, location = 'upper_right', logger=mod_logger): # Add text string 'annot' to lower left of plot
    'there may be a built in method for matplotlib to location the text'
        
    xmin, xmax = ax.get_xlim()
    ymin, ymax = ax.get_ylim()
    
    if location == 'upper_right':
        x_text = xmax - (xmax - xmin)/5 # 1/10 to the right of the left axis
        y_text = ymax - (ymax - ymin)/10 #1/10 above the bottom axis
    else:
        logger.error('got unexpected location kwarg: %s'%location)
        raise IOError
    anno_obj = ax.text(x_text, y_text, text)
    
    return anno_obj

def save_fig(obj,  fig, #hp fnction for saving figures
             savepath_raw=True, fmt = 'svg', overwrite=True, legon= True, dpi=300,
             transparent = True,
             logger=mod_logger, **kwargs): 
    """
    plt.show()
    """    
        
    logger = logger.getChild('save_fig')
    #=======================================================================
    # setup
    #=======================================================================
    ext = '.'+fmt
    if legon: plt.legend() #turn teh legend on
    
    #=======================================================================
    # set defaults
    #=======================================================================
    
    if savepath_raw == True: #just write to default
        try:
            title = fig.gca().get_title()
            if title == '': 
                logger.warning('blank title found')
        except: 
            title = fig._suptitle.get_text()
            if title is None: 
                raise ValueError

        if obj.outpath is None:

            raise IOError
        filepath = os.path.join(obj.outpath,title)
        
    elif savepath_raw == False:
        logger.warning('save_path = False')
        return
    else:
        filepath = savepath_raw
    
    if not filepath.endswith(fmt): #add teh file extension
        filepath = filepath + ext
        
    #===========================================================================
    # check for basedir
    #===========================================================================
    head, tail = os.path.split(filepath)
    if not os.path.exists(head): os.makedirs(head) #make this directory

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
                             
    try: 
        fig.savefig(filepath, dpi = dpi, format = fmt, transparent=transparent,
                    **kwargs)
    except:
        logger.error('something went wrong with saving the figure to file:  \n    %s '%filepath)
        raise IOError
        return False
    logger.info('saved figure to file: %s'%(filepath))
    
    plt.close()
    
    return True
        
#===============================================================================
# PIE PLOTS ------------------------------------------------------------------
#===============================================================================

def autopct_dollars(values): #callable function to label wedges with dollar values
    """These are very trickyc
    couldnt figure out how to add percent in also
    """
    def my_autopct(pct):
        total = sum(values)
        val = int(round(pct*total/100.0))

        return '$' + "{:,.2f}".format(val)
    return my_autopct

def make_autopct(values): #label wedges with percent and value
    def my_autopct(pct):
        total = sum(values)
        val = int(round(pct*total/100.0))
        return '{p:.2f}%  ({v:d})'.format(p=pct,v=val)
    return my_autopct

#===============================================================================
# FORMATTING -------------------------------------------------------------------
#===============================================================================

def tick_label_percentage(ax=None, axis='y'):
    
    if ax == None: ax = plt.gca()
    
    if axis == 'y':
        
        vals = ax.get_yticks()
    
        new_ticks = []
        for old_tick in ax.get_yticks():
            tick = '{:1.1f}%'.format(old_tick*100)
            
            new_ticks.append(tick)
            
        ax.set_yticklabels(new_ticks)
        
    else:
        raise IOError #add code for x axis
    
    return ax

class Plotdatabundler(object): #convenience methdos for gneerating plotdatabundles
    """
    in general, this should be handled to convert
        self.data (pandas type)
            into
        plotdatabundle ([self.name, self, data_ar])
        
    these plotdatabundles can then be easily passed tot he PLot_worker
    
    for multiple plots, pass these as ordered dictionaries
    """
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Plotdatabundler')
        logger.debug('start __init__ as \'%s\''%self.__class__.__name__)
        
        super(Plotdatabundler, self).__init__(*vars, **kwargs) #initilzie teh baseclass
        
        self.logger.debug('finish __inti__')
        return
            
    
    def get_plotdatabundle(self, row=0, use_index = False): #basic function for one entry in a plot data bundle
        """
        only setup to handle data on rows at this point
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_plotdatabundle')
        
        if not hasattr(self, 'data'): raise IOError
        if self.data is None: 
            logger.error('self.data is None')
            """
            hp.oop.log_all_attributes(self)
            """
            raise IOError
        
        data_ar = None #presetn
        #===================================================================
        # get teh data from teh object by type
        #===================================================================
        if isinstance(self.data, np.ndarray):
            data_ar_raw = self.data
            
            if use_index: raise IOError
            
            logger.debug('raw format is array')
            
            if len(data_ar_raw.shape) == 1:
                logger.debug('unidimensional array')
                data_ar = np.array(data_ar_raw.tolist())
            
        elif hp_pd.isdf(self.data):
            'todo: add check that this is pandasd type'
            if use_index: data_ar_raw = self.data.index.values
            else: data_ar_raw = self.data.values
            
            
            try:
                data_ar_raw = data_ar_raw.astype(np.number)
            except:
                logger.error('got non numeric data for %s'%self.name)
                logger.debug("%s"%data_ar_raw)
                raise IOError
            
            logger.debug('got array from df type')
            
        elif hp_pd.isser(self.data):
            if use_index: data_ar = self.data.index.values
            
            else: data_ar = self.data.values
            
            logger.debug('got array from series type')
            
        else: raise IOError
            
        #=======================================================================
        # change to single dimension
        #=======================================================================
        if data_ar is None:
            if data_ar_raw.shape[0] < row +1:
                logger.error('got unepxected shape: %s'%str(data_ar_raw.shape))
                
                'todo: add some treatment for data_ars that are flipped'
                raise IOError
            
            elif data_ar_raw.shape[0] > 1: #got a multidimensional array
                logger.debug('dropped dimension')
                data_ar = data_ar_raw[row] #take just this row
                
            else: raise IOError
        
        if not hp.np.isar(data_ar):
            logger.error('expected array. instead got: %s'%type(data_ar))
            raise IOError

        logger.debug('found data_ar (%s): \n    %s'%(str(data_ar.shape), data_ar))
        
        return [self.name, self, data_ar]
    
    def get_pdb_dict(self,  #take a list of datos and get a dictionary of pdbs
                     dato_list, row = 0, use_index = False):
        """
        #=======================================================================
        # OUTPUST
        #=======================================================================
        dato_ar_dict: bundle of datos and their data:
            keys: dato.name
            values: [dato, array of data]
        """
        #=======================================================================
        # setup
        #=======================================================================
        logger = self.logger.getChild('get_pdb_dict')
        logger.debug('on dato_list: %s'%dato_list)
        
        
        #=======================================================================
        # #convert dictioary to list if necessary
        #=======================================================================
        if isinstance(dato_list, dict):
            dato_dict = dato_list
            dato_list = []
            for name, [datoname, dato, data_ar] in dato_dict.items():
                dato_list.append(dato)
                
            logger.debug('got dict. converted back to list %i'%len(dato_list))
            
        if not isinstance(dato_list, list): raise IOError
     
        #=======================================================================
        # build pdb
        #=======================================================================
        pdb_dict = OrderedDict()

        for index, dato in enumerate(dato_list):
            pdb_dict[index] = dato.get_plotdatabundle(row=row, use_index=use_index)
            
            
        logger.debug('bundled %i entries into an od: %s'%(len(pdb_dict), list(pdb_dict.keys())))
        
        return pdb_dict
    
    def plotdatabundle_slice(self, boolidx): #return a sliced list in dato_ar format
        
        df = self.data
        
        if not hp_pd.isdf(df): 
            if not hp_pd.isser(df): raise IOError
        
        df_slice = df[boolidx]
        
        if len(df_slice) == 0: raise IOError
        
        return [self.name, self, df_slice.values]
    
    def get_equil_slice_bundle(self, dep_ar_dict): #return a bundle sliced as in the dep_ar_dict
        logger = self.logger.getChild('get_equil_slice_bundle')
        #=======================================================================
        # setup
        #=======================================================================
        df = self.data
        if not hp_pd.isdf(df): 
            if not hp_pd.isser(df): raise IOError
        
        indp_ar_dict = OrderedDict()
        #=======================================================================
        # loop and fill
        #=======================================================================
        for index,[dep_name, dep_dato, dep_ar] in dep_ar_dict.items(): #loop through each and build the plot
            
            dep_df = dep_dato.data
            if not hp_pd.isdf(dep_df): raise IOError
            
            boolidx = df.index.isin(dep_df.index) #find where they match
            
            indp_ar_dict[index] = self.bundle_as_slice(boolidx) #get teh data bundle on this slice
            
        logger.debug('made %i equilvanet sliced bundles'%len(indp_ar_dict))
        
        return indp_ar_dict
    
    def inspect_pdb(self, pdb): #send pdb to logger
        logger = self.logger.getChild('inspect_pdb')
        
        if isinstance(pdb, dict):
            logger.info('sending %i pdbs to logger'%len(pdb))
            for index,[dep_name, dep_dato, dep_ar] in pdb.items(): #loop through each and build the plot 
                logger.debug('%i, \'%s\' \n    %s'%(index, dep_name, dep_ar.tolist()))
                
    def sort_buckets(self, kids_d, in_search_str): #sort children into buckets witha search string
        logger = self.logger.getChild('sort_buckets')
        in_l = []
        out_l = []
        
        for gid, obj in kids_d.items():
            if gid in in_search_str: 
                in_l.append(obj)
                
            else: 
                out_l.append(obj)

        #assemble these into data bundles
        in_pdb = self.get_pdb_dict(in_l) 
        out_pdb = self.get_pdb_dict(out_l)
        
        logger.debug("got %i objs in and %i objs out"%(len(in_l), len(out_l)))
        
        return in_pdb, out_pdb
        
        
 
class Plot_o(Plotdatabundler): #worker for plotting teh data
    
    units       = ''
    color       = 'black'
    linestyle   = 'solid'
    linewidth   = 1
    alpha       = 1
    marker      = 'x'
    markersize  = 1
    fillstyle   = 'full' #marker fill style
    _figsize     = (6.5, 4) #made this inheritable assuming we never want multiple figsizes per session
    dpi         = 150
    color_cycler = None #plt.rcParams['axes.color_cycle'] #default color indexer
    
    
    #===========================================================================
    # hatch attributes
    #===========================================================================
    hatch_f = False
    hatch =  None
    h_color = 'red'
    h_alpha = 0.5
    
    #===========================================================================
    # historgram vars
    #===========================================================================
    hist_bins = 'auto'
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Plot_o')
        logger.debug('start _init_')
        
        #update the inheritance
        """using session values
        if self.inherit_parent_ans is None: self.inherit_parent_ans = set()
        self.inherit_parent_ans.add('_figsize')"""
            

        super(Plot_o, self).__init__(*vars, **kwargs) #initilzie teh Plotdatabundler 

        #=======================================================================
        # unique inits
        #=======================================================================
        #label
        self.label = self.name + '(%s)'%self.units
        
        #=======================================================================
        # checks
        #=======================================================================
        if self.db_f:
            #figsize
            if not isinstance(self._figsize, tuple):
                raise IOError
        
        logger.debug('finish _init_ as %s'%self.name)
        return
                    
        
        
    
    def plot_twinx(self, dep_pdb_d_left, dep_pdb_d_right, #plot multiple on twinned axis
                        indp1_pdb_dict=None, indp2_pdb_dict=None,
                        logx=False, grid=True, annot = None,
                        ylab1 = None, ylab2 = None, xlab = None,
                        title=None, ax1=None,wtf=None,
                        **kwargs):
        
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        dep_pdb_d_left: dependent pdbs for the left axis (y axis)
        
        """
        
        logger = self.logger.getChild('plot_twinx')
        #=======================================================================
        # defaults
        #=======================================================================
                    
        # formating defaults
        if title == None: title = self.name + ' twinx plot on %i data pairs'%(len(dep_pdb_d_left) + len(dep_pdb_d_right))
        
        #filehandling
        if wtf == None: wtf = self.session._write_figs
        
        #data setup
        if indp1_pdb_dict is None: 
            indp1_pdb_dict = self.get_pdb_dict(dep_pdb_d_left, use_index=True)
            
        if indp2_pdb_dict is None: 
            indp2_pdb_dict = self.get_pdb_dict(dep_pdb_d_right, use_index=True)

        logger.info('getting twinned plot with left %i and right %i data pairs'
                    %(len(dep_pdb_d_left), len(dep_pdb_d_right)))
        
        """
        logger.debug('left axis: \n \n')        
        self.inspect_pdb(dep_pdb_d_left)
        self.inspect_pdb(indp1_pdb_dict)
        
        logger.debug('right axis: \n \n')  
        self.inspect_pdb(dep_pdb_d_right)
        self.inspect_pdb(indp2_pdb_dict)
        
        """

        #=======================================================================
        # setup plot
        #=======================================================================
        if ax1 == None:
            plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(self._figsize)
            ax1 = fig.add_subplot(111)
            ax2 = ax1.twinx()  
            
            #=======================================================================
            # axis label setup
            #=======================================================================
            #left axis
            indp1_dato1 = list(indp1_pdb_dict.values())[0][1]
            dep1_dato1 =  list(dep_pdb_d_left.values())[0][1]
            dep2_dato1 =  list(dep_pdb_d_right.values())[0][1]
                       
            if xlab is None: xlab = indp1_dato1.units 
            if ylab1 is None: ylab1 = dep1_dato1.units
            if ylab2 is None: ylab2 = dep2_dato1.units
        
        
            fig.suptitle(title)
            ax1.set_ylabel(ylab1)
            ax2.set_ylabel(ylab2)
            
            ax1.set_xlabel(xlab)
            
            
                  
        else:
            fig = ax1.figure
            
        #=======================================================================
        # send for plotting
        #=======================================================================
        #left plot
        ax1 = self.plot_bundles(dep_pdb_d_left, indp_pdb_dict=indp1_pdb_dict,
                               logx = logx, grid=False, annot = annot,
                               flip=False, title=title, ax=ax1,wtf=False, ylab=ylab1,
                               **kwargs)
            
        #right plot
        ax2 = self.plot_bundles(dep_pdb_d_right, indp_pdb_dict=indp2_pdb_dict,
                               logx= logx, grid=False, annot = None,
                               flip=False, title=title, ax=ax2,wtf=False, ylab=ylab2,
                               **kwargs)
        
        #=======================================================================
        # post formatting
        #=======================================================================
        if grid: ax1.grid()
        
        #=======================================================================
        # control legend on
        #=======================================================================
        h1, l1 = ax1.get_legend_handles_labels() #pull legend handles from axis 1
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1+h2, l1+l2, loc=2) #turn legend on with combined handles
        

        
        if wtf: 
            flag = save_fig(self, fig, dpi = self.dpi, legon=False)
            if not flag: raise IOError 
        
        return ax1, ax2
            
    
    def plot_bundles(self, dep_pdb_dict, indp_pdb_dict=None, #plot multiple dep_dataos against teh same indp data
                       flip=False, logx = False, grid=True,
                       title=None, ax=None,wtf=None, ylab=None, annot = None, xlab = None,
                       **kwargs):
        
        """
        #=======================================================================
        # INPUTS
        #=======================================================================        
        dep_pdb_dict: dictionary of plot data bundles (see PLotdatabundler.get_pdb_dict) (generally y)
        
        #=======================================================================
        # USE
        #=======================================================================
        I've kep the ylab as an option incase dummy indp_datos were passed
 
        """
        logger = self.logger.getChild('plot_bundles')
        #=======================================================================
        # defaults
        #=======================================================================
                    
        # formating defaults
        if title == None: title = self.name + ' plot %i data pairs'%(len(dep_pdb_dict))
        
        #filehandling
        if wtf == None: wtf = self.session._write_figs
        
        if indp_pdb_dict is None: 
            indp_pdb_dict = self.get_pdb_dict(dep_pdb_dict, use_index=True)

        #=======================================================================
        # pre checks
        #=======================================================================
        if not len(dep_pdb_dict) == len(indp_pdb_dict): raise IOError
        logger.info('generating %s'%(title))
        #=======================================================================
        # data setup/flipping
        #=======================================================================
        #get dummy datos
        indp_dato1 = list(indp_pdb_dict.values())[0][1]
        dep_dato1 =  list(dep_pdb_dict.values())[0][1]
                
        if not flip:
                       
            if xlab is None: xlab = indp_dato1.units 
            if ylab is None: ylab = dep_dato1.units
                        
        else:  #flip the axis            
            if ylab is None: ylab = indp_dato1.units 
            if xlab is None: xlab = dep_dato1.units
            if logx: raise ValueError
        
        #=======================================================================
        # setup plot
        #=======================================================================
        if ax == None:
            plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(self._figsize)
            ax = fig.add_subplot(111)  
            
            ax.set_title(title)
            ax.set_ylabel(ylab)
            ax.set_xlabel(xlab)
                  
        else:
            fig = ax.figure
            
        #=======================================================================
        # build the plot
        #=======================================================================
        logger.debug('looping through %i datos and generating plots'%len(dep_pdb_dict))
        first = True
        for index,[dep_name, dep_dato, dep_ar] in dep_pdb_dict.items(): #loop through each and build the plot

                
            #get indp data
            [indp_name, indp_dato, indp_ar] = indp_pdb_dict[index]
            
            pline = self.plot(dep_dato, indp_dato = indp_dato, dep_ar = dep_ar, indp_ar = indp_ar,
                              flip=flip, logx = logx, grid=False, annot = annot,
                              title=title, ax=ax, wtf=False, **kwargs)
            
            if first:
                annot = None #only want annot on first loop
                first = False
            
        #=======================================================================
        # post formatting
        #=======================================================================
        if grid: ax.grid()
        #=======================================================================
        # closeout        
        #=======================================================================
        logger.debug('finished')
        
        if wtf: 
            flag = save_fig(self, fig, dpi = self.dpi)
            if not flag: raise IOError 
            
        return ax

    
    def plot(self, dep_dato, #generic plotter to plot across data objects
                    indp_dato=None, dep_ar=None, indp_ar=None,
                    annot = None, grid=True,
                    flip=False, logx = False, 
                    title=None, ax=None,wtf=None, legon=False,
                    color = None, linestyle = None, linewidth = None, alpha = None,
                    marker = None, markersize = None, label = None, fillstyle=None,
                    hatch_f = None, h_color = None, h_alpha = None, hatch = None,
                    _figsize = None,**kwargs): 
        """
        TODO: change this so it uses plot data bundles
            add some convienence detection for simple data to plot without setup
        #=======================================================================
        # USE
        #=======================================================================
        generally ran on the session instance
        this usese (most) the formatting from the dep_dato to generate teh plot of dep (y) vs indp (x)
            unless flipped (only flips x and y)
        
        #=======================================================================
        # inputs
        #=======================================================================
        dep_dato: dependent data object (generally y)
            provides all the formatting
        indp_dato: indepdent data object (generally x)
        flip: flag to indicate whether to apply plot formatters from the y or the x name list 
        """
        logger = self.logger.getChild('plot')
        #=======================================================================
        # defaults
        #=======================================================================
        #data defaults
        if indp_dato is None: 
            indp_dato = dep_dato
            indp_ar = dep_dato.data.index.values #just use the index
            
        elif indp_ar is None: 
            'todo: add more sophisicated data extractio'
            try: indp_ar = indp_dato.data.values #just use the values from the indp
            except: indp_ar = indp_dato.data
        else: pass
        
        if dep_ar is None:
            
            #for regresstions/data functions
            if hasattr(dep_dato, 'dfunc'):
                if not dep_dato.dfunc is None:
                    dep_ar = dep_dato.dfunc(indp_ar)
                    
            #for series type
            elif hp_pd.isser(dep_dato.data): 
                dep_ar = dep_dato.data.values #just use the series values
                
            #for array types
            elif hp.np.isar(dep_dato.data):
                dep_ar = dep_dato.data
            else: raise IOError
            
        elif isinstance(dep_ar, list): dep_ar = np.array(dep_ar)
                    
        # formating defaults
        if title is None: title = self.name + ' plot \'%s\' on \'%s\''%(dep_dato.name, indp_dato.name)
        
        #figure size
        if _figsize is None: 
            _figsize = self._figsize

        
        if not hasattr(indp_dato, 'label'): indp_dato.label = indp_dato.name + ' (%s)'%indp_dato.units
        if not hasattr(dep_dato, 'label'): dep_dato.label = dep_dato.name + ' (%s)'%dep_dato.units
        
        #filehandling
        if wtf is None: wtf = self.session._write_figs
        
        #plot handling
        if hatch_f is None: hatch_f = bool(dep_dato.hatch_f)
        #=======================================================================
        # pre checks
        #=======================================================================
        
        
        logger.debug('generating %s on %s'%(indp_dato.label, dep_dato.label))
        #=======================================================================
        # data setup/flipping
        #=======================================================================
        if not flip:
            xar = indp_ar
            yar = dep_ar
                        
            xlab = indp_dato.label #better to provide the full label for the indep data axis label
            ylab = dep_dato.units
                        
        else:  #flip the axis
            xar = dep_ar
            yar = indp_ar
            
            ylab = indp_dato.label
            xlab = dep_dato.units
            if logx: raise ValueError
            
        xar = xar.astype(float)
        yar = yar.astype(float)
                        
        #=======================================================================
        # data checks
        #=======================================================================
        'todo: add null check'
        'todo: add numpy array dtype check'
        if not len(indp_ar) == len(dep_ar): 
            raise IOError
        if len(xar) < 1: raise IOError
        #=======================================================================
        # setup plot
        #=======================================================================
        if ax is None:
            plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(_figsize)
            ax = fig.add_subplot(111)  
            
            ax.set_title(title)
            ax.set_ylabel(ylab)
            ax.set_xlabel(xlab)
            
            if grid: ax.grid()
                  
        else:
            fig = ax.figure
            xmin, xmax = ax.get_xlim()
            
        #=======================================================================
        # #formatting defaults pulled from self
        #=======================================================================
        'these should all be overwritten by any passed **kwargs'
        if color is None:       color       = dep_dato.color
        if linestyle is None:   linestyle   = dep_dato.linestyle
        if linewidth is None:   linewidth   = dep_dato.linewidth
        if alpha is None:       alpha       = dep_dato.alpha
        if marker is None:      marker      = dep_dato.marker
        if markersize is None:  markersize  = dep_dato.markersize
        if label is None:       label       = dep_dato.label
        if fillstyle is None:   fillstyle   = dep_dato.fillstyle
        
        #=======================================================================
        # send teh data for plotting
        #=======================================================================
        """
        plt.show()
        """
        try:
            if logx:
                pline = ax.semilogx(xar, yar, 
                                label       = label,
                                color       = color, 
                                linestyle   = linestyle, 
                                linewidth   = linewidth,
                                alpha       = alpha,
                                marker      = marker,
                                markersize  = markersize,
                                fillstyle   = fillstyle,
                                **kwargs)
            

            else:
                                
                pline = ax.plot(xar, yar, 
                                label = label,
                                color = color, 
                                linestyle = linestyle, 
                                linewidth = linewidth,
                                alpha       = alpha,
                                marker = marker,
                                markersize = markersize,
                                fillstyle = fillstyle,
                                **kwargs)


                
        except:
            raise IOError
        
        #=======================================================================
        # add hatch
        #=======================================================================
        if hatch_f:
            if h_color is None:       h_color       = dep_dato.h_color
            if h_alpha is None:       h_alpha       = dep_dato.h_alpha
            if hatch is None:         hatch         = dep_dato.hatch

            polys = ax.fill_between(xar, yar, y2=0, 
                                    color       = h_color, 
                                    alpha       = h_alpha,
                                    hatch       = hatch)

        
        #=======================================================================
        # post formatting
        #=======================================================================
        
        if not annot is None:
        #=======================================================================
        # Add text string 'annot' to lower left of plot
        #=======================================================================
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            
            x_text = xmin + (xmax - xmin)*.1 # 1/10 to the right of the left axis
            y_text = ymin + (ymax - ymin)*.1 #1/10 above the bottom axis
            anno_obj = ax.text(x_text, y_text, annot)

        
        #=======================================================================
        # closeout        
        #=======================================================================
        if wtf: 
            flag = save_fig(self, fig, dpi = self.dpi, legon=legon)
            if not flag: raise IOError 
            
        return ax
    
    def plot_data_hist(self, data = None, normed = True, bins=None, histtype = 'bar',
                       ax=None, title=None, wtf = None, annot = None, label = None,
                       color = None, alpha = None, rwidth = 0.9): #plot a historgram of the data
        """
        Kept this separate from the main plot function 
         this is quite unique and shouldnt really be combined with much else
         
         2018 06 24
             changed to expect pd.Series data
         
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('plot_data_hist')
        if wtf is None: wtf = self.session._write_figs
        if bins is None: bins = self.hist_bins
        if data is None: data = self.data
        #=======================================================================
        # setup plot
        #=======================================================================
        if ax is None:
            plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(self._figsize)
            ax = fig.add_subplot(111)  
            
            if title is None: title = self.name + ' hist plot'

            ax.set_title(title)
            ax.set_xlabel(self.label)
            
            #y label
            if normed:ylab = 'likelihood'
            else: ylab = 'count'
            ax.set_ylabel(ylab)
            
                  
        else:
            fig = ax.figure
            xmin, xmax = ax.get_xlim()
            
        #=======================================================================
        # data cleaning
        #=======================================================================
        if not hp_pd.isser(data):
            if hp.np.isar(data):
                data = pd.Series(data)
            else: raise IOError
            
        data_clean = data.astype(float) #change typd
        
        data_clean = data.dropna()
            
        #=======================================================================
        # #formatting defaults pulled from self
        #=======================================================================
        'these should all be overwritten by any passed **kwargs'
        if color is None:       color       = self.color
        if alpha is None:       alpha       = self.alpha
        if label is None:       label       = self.label

        """
        normed = False
        color = 'blue'
        alpha = 0.5
        
        data_clean = np.random.random((1,10000))[0]
        
        
        """
            
        n, bin_res, patches = ax.hist(data_clean, density=normed, histtype = histtype, bins = bins,
                                   alpha = alpha, 
                                   color = color,
                                   label = label,
                                   rwidth  = rwidth)
        
        #=======================================================================
        # post formatting
        #=======================================================================
        if not annot is None:
            if annot is True:
                annot = ' n = %i \n bins = %i'%(len(data_clean), len(bin_res))
        #=======================================================================
        # Add text string 'annot' to lower left of plot
        #=======================================================================
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            
            x_text = xmin + (xmax - xmin)*.7 # 1/10 to the right of the left axis
            y_text = ymin + (ymax - ymin)*.6 #1/10 above the bottom axis
            anno_obj = ax.text(x_text, y_text, annot)
            
        #=======================================================================
        # closeout        
        #=======================================================================
        if wtf: 
            flag = save_fig(self, fig, dpi = self.dpi)
            if not flag: raise IOError 
        
        logger.debug('finished')
        """
        plt.show()
        """
        
        return ax
    
       

        