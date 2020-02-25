'''
Created on Feb. 25, 2020

@author: cefect
'''

import os, logging.config, logging


class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, msg):
        import logging
        mod_logger = logging.getLogger('exceptions') #creates a child logger of the root

        mod_logger.error(msg)

def basic_logger(): #for logging outside the plugin
    
    
    
    base_dir = os.path.dirname(os.path.dirname(__file__)) #canflood
    logcfg_file = os.path.join(base_dir, '_pars', 'logger.conf')
    
    if not os.path.exists(logcfg_file):
        raise Error('logger config file does not exist:\n    %s'%logcfg_file)
    
    #change path to users directory
    new_wdir = os.path.join(os.path.expanduser('~'), 'CanFlood')
    
    if not os.path.exists(new_wdir):
        os.makedirs(new_wdir)
        print('default working directory didnt exist. made it:\n    %s'%new_wdir)
    
    os.chdir(new_wdir)
    
    print('changed current directory to: \n    %s'%os.getcwd())
    
    
    logger = logging.getLogger() #get the root logger
    logging.config.fileConfig(logcfg_file) #load the configuration file
    logger.info('root logger initiated and configured from file: %s'%(logcfg_file))
    
    return logger
    