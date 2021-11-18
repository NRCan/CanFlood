'''
Created on Nov. 18, 2021

@author: cefect

execute a sensivitiy analysis bundle


'''


#===============================================================================
# imports
#===============================================================================
from hlpr.basic import ComWrkr, view
import pandas as pd

from wFlow.scripts import WorkFlow, Session


class SensiRunner(Session):
    
    def rbatch(self, #run a batch of sensitivity 
            ):
 
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('r')



class CandidateModel(WorkFlow):
    pass