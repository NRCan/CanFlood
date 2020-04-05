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

__version__ = '3.0.4'


import logging, logging.config, os, sys, time, datetime


start = time.time() #start the clock

#module directory
mod_dir = os.path.dirname(__file__)

#===============================================================================
# custom imports
#===============================================================================
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    logger = basic_logger()   
    
    from hlpr.exceptions import Error
    
#plugin runs
else:
    logger = logging.getLogger('sofda') #get the root logger

    from hlpr.exceptions import QError as Error



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

        out_dir             = None, #control for the outs_dir. 'auto': generate outpath in the working directory; 'gui' let user select.
        
        dynp_hnd_file       = None, #control for locating the dynp handle file
        
        #logger handling

        _lg_stp             = 20, #for key iterations, interval on which to log
        lg_lvl              = None, #logging level of the sim logger. None = DEBUG
        
        #file write handling
        _write_data         = True, #write outputs to file
        _write_figs         = True, #flag whether to write the generated pyplots to file
        _write_ins          = True, #flag whether to writ eht einputs to file
        
        #debug handling
        _dbgmstr            = 'all', #master debug code ('any', 'all (see 'obj_test' tab)', 'none'). 
        _parlo_f            = True,  #flag to run in test mode (partial ddata loading)
        #"""this gets really tricky with the selection lists"""
        
        #profiling
        _prof_time          = False, #run while profile the program stats
        _prof_mem           = 0, #0, 1, 2, 3 memory profile level
        
        force_open          = True #force open the outputs folder
                                        ):

    print('Welcome to SOFDA %s !!!'%__version__)
    #===============================================================================
    # defaults------------------------------------------------------
    #===============================================================================
        
    #output directory
    if out_dir is None: 
        out_dir = os.path.join(os.getcwd(), 'sofda', 
                               datetime.datetime.now().strftime('%Y%m%d_%H%M%S'))
                
    if not os.path.exists(out_dir):
        logger.info('buildilng out_dir: %s'%out_dir)
        os.makedirs(out_dir)
        
    assert os.path.exists(out_dir)
    
    inscopy_path = os.path.join(out_dir, '_ins')
    if not os.path.exists(inscopy_path):
        os.makedirs(inscopy_path)
    #===========================================================================
    # contorl file       
    #===========================================================================
    assert os.path.exists(parspath), 'passed parfile  does not exist \n    %s'%parspath
    
    _, pars_fn = os.path.split(parspath) #get the conrol file name

        
    #===========================================================================
    # handle files  
    #===========================================================================
    if dynp_hnd_file is None:
        dynp_hnd_file = os.path.join(mod_dir, '_pars', 'dynp_handles_20190512.xls')
        
    assert os.path.exists(dynp_hnd_file), 'passed invalid \'dynp_hnd_file\': %s'%dynp_hnd_file
       

    #===============================================================================
    # INIT -----------------------------------------------------------
    #===============================================================================
    import model.sofda.scripts as scripts
    
    session = scripts.Session(parspath = parspath, 
                              outpath = out_dir, 

                              dynp_hnd_file = dynp_hnd_file,
                              
                              _logstep = _lg_stp, 
                              lg_lvl = lg_lvl, 
                              
                              _write_data = _write_data, 
                              _write_figs = _write_figs, 
                              _write_ins = _write_ins, 
                              
                              _dbgmstr = _dbgmstr, 
                              _parlo_f = _parlo_f,

                              _prof_time = _prof_time, 
                              _prof_mem = _prof_mem,
                              
                              logger=None)
    
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
    import model.sofda.hp.basic as basic
    #copy pyscripts
    if _write_ins: 
        
        sfx = '_%s'%datetime.datetime.now().strftime('%Y%m%d') #file suffix
        
        session.ins_copy_fps.update([__file__, scripts.__file__, parspath]) #add some to the writer list
        
        for fn in session.ins_copy_fps: #loop and write these
            _ = basic.copy_file(fn,inscopy_path, sfx=sfx) #copy this script

    
    if force_open: 
        basic.force_open_dir(out_dir)
    
    stop = time.time()
    logger.info('\n \n    in %.4f mins \'%s.%s\' finished at %s on \n    %s\n    %s\n'
                %((stop-start)/60.0, __name__,__version__, datetime.datetime.now(), pars_fn[:-4], out_dir))



#===============================================================================
# IDE/standalone runs runs
#===============================================================================
if __name__ =="__main__": 
    
    #===========================================================================
    # tutorial 3
    #===========================================================================
    parspath    = r'C:\LS\03_TOOLS\_git\CanFlood\tutorials\3\sample_304.xls'
    out_dir     = None #use the default
    
    run(parspath=parspath, out_dir=out_dir) #for standalone runs


        
