'''
Created on Sep 7, 2018

@author: cef
'''

import os, copy, sys, time, logging, weakref, gc
import cProfile, pstats, objgraph

from collections import OrderedDict, Mapping, Container


from datetime import datetime
from sys import getsizeof

import pandas as pd
import hp.plot #need to call this first so matplotlib handles are set properly
import model.sofda.hp.pd as hp_pd

#===============================================================================
# # module globals -------------------------------------------------------------
#===============================================================================
prof_subfolder = '_prof'

mod_logger = logging.getLogger(__name__)

mod_logger.debug('initialized')


def profile_run(exe_str, outpath, sort_key = 'ncalls', logger = mod_logger, 
                localz = None, globalz = None): #profile run
    
    logger = logger.getChild('spawn_child')
    
    #exe_str = str(cmd) + '()'
    
    logger.info('profile run on \'%s\''%exe_str)
    
    #===========================================================================
    # file setup
    #===========================================================================
    stats_raw_file = os.path.join(outpath, 'cprofile_stats_raw')
    stats_file = os.path.join(outpath, 'cprofile_stats.txt')
    
    #===========================================================================
    # namespace setup
    #===========================================================================
    if locals is None: localz = locals()
    if globals is None: globalz = globals()
    
    #===========================================================================
    # run the profile
    #===========================================================================
    cProfile.runctx(exe_str, globalz, localz, stats_raw_file)
    """
    cProfile.run(cmd.__code__, stats_raw_file)
    cProfile.run(cmd, stats_raw_file)
    localz['session']
    """
     
    #===========================================================================
    # process the stats
    #===========================================================================
    
    #setup streams
    stream_l = [open(stats_file, 'w')] 
    'streaming to a file and to the root logger'
    'cant get this to p'
    
    logger.debug('generating stats on %i streams'%len(stream_l))
    for stream in stream_l: 
        logger.debug('calcing stats on stream \'%s\''%stream)
        #initilzie the stats
        stats = pstats.Stats(stats_raw_file, stream = stream)
        'not sure how to pull directly from teh profile class'
        
        #format
        stats.strip_dirs() #drop the file heads
        stats.sort_stats(sort_key) 

        #send to teh stream
        stats.print_stats()
        
        if not stream is None: logger.info('sent Cprofile stats to %s'%stream.name)
        
    logger.debug('finished')
    
    """
    stream.name
    import model.sofda.hp.oop as hp_oop
    att_std, att_call, att_def  = hp_oop.get_atts(stream)
    
    att_std.keys()
    """


def profile_run_skinny( #profile run
                        exe_str,  #program command string to execute the profile run on
                        outpath=None, 
                        sort_key = 'ncalls', 
                        localz = None, 
                        globalz = None,
                        print_frac = 0.1): #fraction of profile stats to print 

    
    print(('profile run on \'%s\''%exe_str))
    
    if outpath is None: outpath = os.getcwd()
    
    #===========================================================================
    # setup the file dump
    #===========================================================================
    from datetime import datetime
    time = datetime.now().strftime('%Y%m%d-%H-%M-%S')
    outdir = os.path.join(outpath, prof_subfolder)
    os.makedirs(outdir)
    
    #===========================================================================
    # file setup
    #===========================================================================
    stats_raw_file = os.path.join(outdir, 'cprofstats_raw.txt')
    stats_file = os.path.join(outdir, 'cprofstats.txt')
    
    #===========================================================================
    # namespace setup
    #===========================================================================
    if locals is None: localz = locals()
    if globals is None: globalz = globals()
    
    #===========================================================================
    # run the profile
    #===========================================================================
    cProfile.runctx(exe_str, globalz, localz, stats_raw_file)
    """
    cProfile.run(cmd.__code__, stats_raw_file)
    cProfile.run(cmd, stats_raw_file)
    localz['session']
    """
     
    #===========================================================================
    # process the stats
    #===========================================================================
    
    #setup streams
    stream_l = [open(stats_file, 'w')] 
    'streaming to a file and to the root logger'
    'cant get this to p'
    
    
    for stream in stream_l: 
        #logger.debug('calcing stats on stream \'%s\''%stream)
        #initilzie the stats
        stats = pstats.Stats(stats_raw_file, stream = stream)
        'not sure how to pull directly from teh profile class'
        
        #format
        stats.strip_dirs() #drop the file heads
        stats.sort_stats(sort_key) 

        #send to teh stream
        stats.print_stats(print_frac)
        
        
        if not stream is None: print(('sent Cprofile stats to %s'%stream.name))
        
        stats_to_csv(stats_raw_file) #save these to csv
        
    
        
    print('finished')
    
    """
    stream.name
    import model.sofda.hp.oop as hp_oop
    att_std, att_call, att_def  = hp_oop.get_atts(stream)
    
    att_std.keys()
    """
    
def stats_to_csv(stats_raw_file, outpath = None): #save the stats file in a more friendly format
    """
        
    help(StatsViewer)
    hp_pd.v(df)
    df.index
    """
    
    #imports
    from pstatsviewer import StatsViewer
    import model.sofda.hp.pd as hp_pd

    
    if not os.path.exists(stats_raw_file):
        print(('passed stats_raw_file does not exist: %s'%stats_raw_file))

    #initilzie teh stats viewer object on the raw stats
    sv = StatsViewer(stats_raw_file)
    
    #extract the frame from this
    df = sv.callers
    """
    time.time()
    sv.__dict__.keys()
    
    sv.name
    hp_pd.v(sv.callers)

    """
    
    #===========================================================================
    # #write to file
    #===========================================================================
    if outpath is None:
        outpath = os.path.join(os.path.dirname(stats_raw_file), '%s_friendly.csv'%sv.name)
        
    hp_pd.write_to_file(outpath, df, index=True, overwrite=True)
    
    print('saved friendly stats to file')
    
    return

