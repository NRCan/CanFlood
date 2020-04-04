'''
main launching script for SOFDA model execution.

#===============================================================================
# Calling this script
#=============================================================================
via windows command line (see main_cmd)
via IDE/interactive/debugging (run this script)

#===============================================================================
# Variable handling philosophy
#===============================================================================
vars that define the model
    should be wholely contained in the pars file
    
vars that determine file handling and setup
    this script
    
vars that control debugging
    this script (with some in the pars file where necessary)
    

'''

__version__ = '3.0.3'


import logging, logging.config, os, sys, time, datetime


start = time.time() #start the clock

#module directory
mod_dir = os.path.dirname(__file__)

#===============================================================================
# #highest level debuggers
#===============================================================================
_prof_time = False

#===============================================================================
# define the main function ---------------------------------------------------
#===============================================================================
#===============================================================================
# from memory_profiler import profile
# 
# @profile
#===============================================================================
def run(    
        # run vars -------------------------------------------------------------
        #main directory and control file setup
        parspath            = r'C:\LocalStore\03_TOOLS\SOFDA\_ins\_sample\3.0.3\sample_303.xls', 
        #control file name.    'gui' = use gui (default).
        work_dir            = 'cur', #control for working directory. 'auto'=one directory up from this file.
        outs_dir             = 'auto', #control for the outs_dir. 'auto': generate outpath in the working directory; 'gui' let user select.
        
        dynp_hnd_file       = 'auto', #control for locating the dynp handle file
        
        #logger handling
        _log_cfg_fn         = 'logger.conf', #filetail of root logging configuration file (relative to mod_dir)
        lg_lvl              = None, #logging level of the sim logger. None = DEBUG
        _lg_stp             = 20, #for key iterations, interval on which to log
        
        #file write handling
        _write_data         = True, #write outputs to file
        _write_figs         = True, #flag whether to write the generated pyplots to file
        _write_ins          = True, #flag whether to writ eht einputs to file
        
        #debug handling
        _dbgmstr            = 'all', #master debug code ('any', 'all (see 'obj_test' tab)', 'none'). 
        _parlo_f            = True,  #flag to run in test mode (partial ddata loading)
        #"""this gets really tricky with the selection lists"""
        
        #profiling
        _prof_time          = _prof_time, #run while profile the program stats
        _prof_mem           = 0, #0, 1, 2, 3 memory profile level
        
        force_open          = True #force open the outputs folder
                                        ):

    print('Welcome to SOFDA %s !!!'%__version__)
    #===============================================================================
    # Working directory ------------------------------------------------------
    #===============================================================================
    import hp.gui
    #assign
    if work_dir == 'pauto': 
        'for python runs. doesnt work for freezing'
        work_dir = os.path.dirname(os.path.dirname(__file__)) #default to 1 directories up
    
    elif work_dir == 'cur':
        work_dir = os.getcwd()
        
    elif work_dir == 'gui':
        work_dir = hp.gui.get_dir(title='select working directory', indir = os.getcwd())
        
    elif work_dir == 'home':
        from os.path import expanduser
        usr_dir = expanduser("~") #get the users windows folder
        work_dir = os.path.join(usr_dir, 'SOFDA')
        if not os.path.exists(work_dir): os.makedirs(work_dir)
        

    #check it
    if not os.path.exists(work_dir): 
        raise IOError('passed work_dir does not exist: \'%s\''%work_dir)
        

    #===============================================================================
    # Setup root log file ----------------------------------------------------------
    #===============================================================================
    logcfg_file = os.path.join(mod_dir, '_pars',_log_cfg_fn)
    
    if not os.path.exists(logcfg_file):  
        raise IOError('No logger Config File found at: \n   %s'%logcfg_file)
    
    logger = logging.getLogger() #get the root logger
    logging.config.fileConfig(logcfg_file) #load the configuration file
    'this should create a logger in the current directory'
    logger.info('%s root.log configured from file at %s: \n    %s'%(__version__, datetime.datetime.now(), logcfg_file))
    
    #move to the working directory
    os.chdir(work_dir) #set this to the working directory
    logger.debug('working directory set to \n    \"%s\''%os.getcwd())
    
    #load the custom exceptions
    from exceptions import Error

    #===========================================================================
    # Control file -----------------------------------------------------------
    #===========================================================================
    if parspath == 'gui':
        parspath = hp.gui.gui_fileopen(title='Select SOFDA your control file.xls', indir = work_dir,
                                       filetypes = 'xls', logger=logger)
        
    if not os.path.exists(parspath):
        raise Error('passed parfile  does not exist \n    %s'%parspath)
    
    _, pars_fn = os.path.split(parspath) #get the conrol file name

    #===========================================================================
    # outputs folder --------------------------------------------------------
    #===========================================================================
    import hp.basic
    
    if _write_data:
        if outs_dir == 'gui':
            outpath = hp.gui.file_saveas(title='enter output folder name/location', indir = work_dir, logger=logger)
        else: #from some parent directory
            
            if outs_dir == 'auto':
                'defaulting to a _outs sub directory'
                outparent_path =  os.path.join(work_dir, '_outs')
                
            elif os.path.exists(outs_dir):
                outparent_path =  outs_dir
            else:
                raise Error('unrecognized outs_dir: %s'%outs_dir)
            
            if not os.path.exists(outparent_path):
                logger.warning('default outparent_path does not exist. building \n    %s'%outparent_path)
                os.makedirs(outparent_path)
                
            outpath = hp.basic.setup_workdir(outparent_path, basename = pars_fn[:-4])
            

        #check and build
        if os.path.exists(outpath):
            logger.debug('selected outpath exists\n    %s'%outpath)
        else:
            os.makedirs(outpath)

        #setup the ins copy
        inscopy_path = os.path.join(outpath, '_inscopy')
        if _write_ins: 
            os.makedirs(inscopy_path)
        
    else:
        _write_ins = False
        _write_figs = False
        outpath, inscopy_path = '_none', '_none'
        
    #===========================================================================
    # handle files -----------------------------------------------------------
    #===========================================================================
    if dynp_hnd_file == 'auto':
        dynp_hnd_file = os.path.join(mod_dir, '_pars', 'dynp_handles_20190512.xls')
        
    if not os.path.exists(dynp_hnd_file):
        raise Error('')
       

    #===============================================================================
    # INIT -----------------------------------------------------------
    #===============================================================================
    import scripts
    
    session = scripts.Session(parspath = parspath, 
                              outpath = outpath, 
                              inscopy_path = inscopy_path,
                              dynp_hnd_file = dynp_hnd_file,
                              
                              _logstep = _lg_stp, 
                              lg_lvl = lg_lvl, 
                              
                              _write_data = _write_data, 
                              _write_figs = _write_figs, 
                              _write_ins = _write_ins, 
                              
                              _dbgmstr = _dbgmstr, 
                              _parlo_f = _parlo_f,

                              _prof_time = _prof_time, 
                              _prof_mem = _prof_mem)
    
    # LOAD ---------------------------------------------------------------------
    session.load_models()
    
    # RUN --------------------------------------------------------------------
    session.run_session()
    
    #===========================================================================
    # WRITE RESULTS
    #===========================================================================
    session.write_results()
    #===============================================================================
    # WRAP UP ----------------------------------------------------------------
    #===============================================================================
    session.wrap_up()
    
    #===============================================================================
    # copy input files
    #===============================================================================
    #copy pyscripts
    if _write_ins: 
        sfx = '_%s'%datetime.datetime.now().strftime('%Y%m%d') #file suffix
        
        session.ins_copy_fps.update([__file__, scripts.__file__, parspath]) #add some to the writer list
        
        for fn in session.ins_copy_fps: #loop and write these
            _ = hp.basic.copy_file(fn,inscopy_path, sfx=sfx) #copy this script

    
    if force_open: 
        hp.basic.force_open_dir(outpath)
    
    stop = time.time()
    logger.info('\n \n    in %.4f mins \'%s.%s\' finished at %s on \n    %s\n    %s\n'
                %((stop-start)/60.0, __name__,__version__, datetime.datetime.now(), pars_fn[:-4], outpath))



#===============================================================================
# IDE/standalone runs runs
#===============================================================================
if __name__ =="__main__": 
    
    if _prof_time: #profile the run
        import hp.basic
        
        #=======================================================================
        # file setup
        #=======================================================================
        work_dir = os.path.dirname(os.path.dirname(__file__)) #default to 1 directories up
        out_fldr = '_outs'

        outparent_path =  os.path.join(work_dir, out_fldr)
        master_out, inscopy_path = hp.basic.setup_workdir(outparent_path)

        
        run_str = 'run(outpath = master_out)'
        


        import hp.prof
        hp.prof.profile_run_skinny(run_str, outpath = master_out, localz = locals())

    else:
        run(work_dir='pauto') #for standalone runs


        
