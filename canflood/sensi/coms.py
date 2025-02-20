'''
Created on Nov. 20, 2021

@author: cefect

common methods for sensitivity analylsis
'''
#===============================================================================
# imports----------
#===============================================================================
import os, datetime, pickle, copy, shutil, configparser

from canflood.model.modcom import Model
 

from canflood.model.risk1 import Risk1
from canflood.model.risk2 import Risk2
from canflood.model.dmg2 import Dmg2





#===============================================================================
# classes-----
#===============================================================================

class SensiShared(Model):
    
    
    #sub model class objects to collect attributes from
    modelTypes_d = {
        'L1':[Risk1],
        'L2':[Risk2, Dmg2]
        }
    
    collect_attns = [ #attribute names to collect from submodels
        'exp_pars_md', 'exp_pars_op'
        ]
    
    
    def __init__(self,
                 modLevel='L1',
                 **kwargs):
         
        #=======================================================================
        # collect attributes from submodels
        #=======================================================================
        
        

        self.merge_expectations(modLevel)

                   
         
        super().__init__( 
                         **kwargs) #Qcoms -> ComWrkr
        
    
    def setup(self):
        """even though were not really a model... stil using this for consistency"""
        self.init_model()
        
        #overwrite
        self.resname = '%s_%s_%s'%(self.name, self.tag,  datetime.datetime.now().strftime('%m%d'))
        
    def merge_expectations(self, #merge expectation containers
                            modLevel
                            ):
        """
        because we're merging Risk and Impact model classes, need to combine the expectation pars
        """
        assert modLevel in self.modelTypes_d
        
        #loop through each of your sibilings
        for ModObj in self.modelTypes_d[modLevel]:
            #print('collecting from %s'%ModObj.__name__)
            
            #===================================================================
            # loop each expectation container
            #===================================================================
            for attn in self.collect_attns:
                
                #get from the sibling
                sib_att_d = copy.deepcopy(getattr(ModObj, attn))
                        
                if not hasattr(self, attn):
                    new_att_d = sib_att_d
                
                #=======================================================================
                # merge
                #=======================================================================
                else:
                    #start with a copy of th eold
                    new_att_d = copy.deepcopy(getattr(self, attn))
         
                    
                    for k, sub_d in sib_att_d.items():
                        if k in new_att_d:
                            new_att_d[k] = {**new_att_d[k], **sub_d}
                        else:
                            new_att_d[k] = sub_d
                    
        
                #set it
                setattr(self, attn, new_att_d)
                
        #===================================================================
        # special fixes
        #===================================================================
        """need to remove the dmgs from the mandatory expectations"""
        if 'dmgs' in self.exp_pars_md['risk_fps']:
 
            del self.exp_pars_md['risk_fps']['dmgs']
        else:
            assert modLevel=='L1'
                
    def get_sections(self, #retrieving sections for each attn from the check_d's
                     attn_l,
                     master_pars=None, #{section: {attn:type}}
                     logger=None,
                     ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('get_sections')
        if master_pars is None: master_pars=self.master_pars
        
        #=======================================================================
        # pivot pars
        #=======================================================================
        all_attn_sect_d = dict()
        for sectName, pars_d in master_pars.items():
            all_attn_sect_d.update({k:sectName for k in pars_d.keys()})
            
        
 
                
        log.debug('got %i'%len(all_attn_sect_d))
        
        #=======================================================================
        # chekc we got everything
        #=======================================================================
        miss_l = set(attn_l).difference(all_attn_sect_d.keys())
        assert len(miss_l)==0, miss_l
        
        
        return {k:all_attn_sect_d[k] for k in attn_l}
    
    def get_attns_from_sections(self,
                                sections_l,
                             master_pars=None, #{section: {attn:type}}
                     logger=None,
                     ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('get_sections')
        if master_pars is None: master_pars=self.master_pars
        
        
        attn_d = dict()
        for sectName in sections_l:
            attn_d.update({k:sectName for k in master_pars[sectName].keys()})
            
        return attn_d
                                
    
    
 