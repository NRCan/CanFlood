import logging, logging.config
logcfg_file = r'C:\Users\tony.decrescenzo\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\floodiq\_pars\logger.conf'
logger = logging.getLogger() #get the root logger
logging.config.fileConfig(logcfg_file) #load the configuration file
logger.info('root logger initiated and configured from file: %s'%(logcfg_file))

