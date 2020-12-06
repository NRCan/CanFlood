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



class WebConnect(ComWrkr):
    
    
    def __init__(self,
                 **kwargs):
        
        super().__init__(**kwargs) #initilzie teh baseclass
    
    
    def addAll(self): #add all connections
        log = self.logger.getChild('addAll')
        
        log.info('pushed')
        
        
        