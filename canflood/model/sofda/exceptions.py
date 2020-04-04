'''
Created on May 18, 2019

@author: cef

custom exceptions and errors
'''

import logging
mod_logger = logging.getLogger('exceptions') #creates a child logger of the root


class Error(Exception):
    """Base class for exceptions in this module."""
    def __init__(self, msg):
        mod_logger.error(msg)
