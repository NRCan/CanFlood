'''
Created on Dec. 5, 2020

@author: cefect

web connections
'''


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import configparser, os, logging




from hlpr.Q import *
from hlpr.basic import *
from hlpr.plug import logger as plogger



class WebConnect(ComWrkr):
    
    
    def __init__(self,iface,
                 **kwargs):
        
        self.iface=iface
        self.logger=plogger(self)
        super().__init__(logger=self.logger, **kwargs) #initilzie teh baseclass
    
    
    def addAll(self): #add all connections
        log = self.logger.getChild('addAll')
        
        log.push('addAll executed')
        
        
        