'''
Created on Nov. 18, 2021

@author: cefect

execute a sensivitiy analysis bundle


flow
1) pass values from dialog
2) construct set of independent model packages
3) execute the group of packages
4) write summary results and display in gui


#===============================================================================
# objects
#===============================================================================
Session            handles each workflow
    workflow        a single model package
        workers    e.g., dmg2, risk2
        
because we're only using model workers, no need for fancy init handling
    except for Plotr (pass init_plt_d)
        


'''


#===============================================================================
# imports
#===============================================================================
import os, datetime

from hlpr.basic import ComWrkr, view
from hlpr.wf import WorkFlow, Session
import pandas as pd

 


class SensiRunner(Session):
    
    def build_batch_cfs(self, #build the set of model packages specified in the gui
                        df, #matrix of variables read from the diailog
                         
                      ):
        pass
    
    def rbatch(self, #run a batch of sensitivity 
               cf_d, #{mtag, controlfile}
            ):
        """
        only model rountes (e.g., dmg, risk)
            all build routines should be handled by the UI
            
        run a set of control files?
        """
 
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('r')
        log.info('on %i: %s'%(len(cf_d), list(cf_d.keys())))
        
        #=======================================================================
        # loop and execute
        #=======================================================================
        for mtag, cf in cf_d.items():
            log.info('on %s from %s'%(mtag, os.path.basename(cf)))



class CandidateModel(WorkFlow):
    pass