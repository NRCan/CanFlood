'''
Created on Nov. 20, 2021

@author: cefect

constructing sensitivity analysis model candidates
'''

#===============================================================================
# imports----------
#===============================================================================
import os, datetime, pickle, copy, shutil, configparser
import pandas as pd
import numpy as np
 

from hlpr.basic import view

        
                     
from sensi.coms import Shared

    
    

class CandidateModel(Shared):
    def __init__(self,
             mtag='candidateTag',
             logger=None,
             **kwargs):
        
        

        
        super().__init__( logger=logger,
                     **kwargs) #Qcoms -> ComWrkr
        
        #reset the logger
        self.mtag=mtag
 
        self.logger=logger.getChild(mtag)
        
    def upd_cfPars(self, #update the control file parameters with some new values
                   ncfPars_d,
                   cfPars_d = None,
                   logger=None
                   ):
        
        if cfPars_d is None: cfPars_d=self.cfPars_d
        cfPars_d = copy.deepcopy(cfPars_d)
        #=======================================================================
        # loop and update
        #=======================================================================
        
        pars_lib = dict()
        for section, val_d in ncfPars_d.items():
            cfPars_d[section].update(val_d)
            
        self.cfPars_d = cfPars_d
        
        return self.cfPars_d
        
        
    def copy_datafiles(self, #copy over data files and update some parameters
                       cfPars_d=None, #{section:{valnm:value}}
                       out_dir=None, 
                       logger=None):
        """
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('copy_datafiles')
        if out_dir is None: out_dir=self.out_dir
        if cfPars_d is None: cfPars_d=self.cfPars_d
        
        
        log.debug('on %i'%len(cfPars_d))
        
        #=======================================================================
        # loop and copy
        #=======================================================================
        meta_d = dict()
        pars_lib = copy.deepcopy(cfPars_d)
        for section, val_d in cfPars_d.items():
            #none data files
            if not section.endswith('_fps'): 
                pars_lib[section] = copy.deepcopy(val_d)
                
            #datafile sections
            else:
                pars_lib[section] = dict()
                for valnm, fp in val_d.items():
                    #check for blanks
                    if fp == '':
                        pars_lib[section][valnm] = fp
                    else:
                        assert os.path.exists(fp), 'got bad filepath for \"%s\': %s'%(valnm, fp)
                        new_fp = os.path.join(out_dir, os.path.basename(fp))
                        
                        if os.path.exists(new_fp): assert self.overwrite
                        
                        #copy it over
                        pars_lib[section][valnm] = shutil.copyfile(fp, new_fp)
                        
                        meta_d[valnm] = pars_lib[section][valnm] 
                    
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('copied %i data files to %s'%(
            len(meta_d), out_dir))
    
        return pars_lib
                
            
    


class SensiConstructor(Shared):
    
 
    

    def build_candidates(self, #build all the candidate models
                         df_raw, #frame with parameters
                         base_cf_fp = None, #base control file
                         base_cf_fn = None, #ase control file name
                         logger=None,
                         basedir = None,
                         copyDataFiles=True, #whether to copy over all datafiles
                         ):
        
        """
        view(df_raw)
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('bcan')
        
        if base_cf_fp is None: base_cf_fp=self.cf_fp
        if basedir is None: basedir = self.out_dir
        
        if base_cf_fn is None:
            base_cf_fn = os.path.splitext(os.path.basename(base_cf_fp))[0]
        
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(df_raw, pd.DataFrame)
        assert 'name' in df_raw.index, 'must specify a name row'
        assert df_raw.loc['name', :].iloc[0] == self.name, 'base name does not match'
        

        #=======================================================================
        # #check base pars
        #=======================================================================
        pars_d = df_raw.iloc[:,0].to_dict()
        for k,v in pars_d.items():
            assert hasattr(self, k)
            if not getattr(self, k) == str(v):
                """this gets too complicated for parameters w/ variable types"""   
                log.warning('mismatch \'%s\''%k)
        
        df = df_raw.iloc[:,1:] #drop the base
 
        #=======================================================================
        # get sections
        #=======================================================================
        attn_sect_d = self.get_sections(df.index.tolist(), logger=log)
        #=======================================================================
        # loop and create each candidate
        #=======================================================================
        log.info('creating %i candidate models'%len(df.T))
        meta_lib = dict()
        for mtag, col in df.items():
            log.debug('on %s'%mtag)
            
            #setup the new directory
            out_dir = os.path.join(basedir, mtag)
            if os.path.exists(out_dir):
                assert self.overwrite
            else:
                os.makedirs(out_dir)
            
            #copy over the base cf_fp
            cf_fp = os.path.join(out_dir,'%s_%s.txt'%(base_cf_fn, mtag)) 
            _ = shutil.copyfile(base_cf_fp, cf_fp)
            log.info('copied cf to %s'%cf_fp)
            
            #append sections and restructure
            pars_d1 = dict()
            for section, gdf in col.to_frame().join(pd.Series(attn_sect_d, name='section')
                                                    ).groupby('section'):
                att_d = gdf[mtag].to_dict()
                att_d = {k:str(v) for k,v in att_d.items()} #convert to all strings
                pars_d1[section] = att_d
 
            
            
            #update the control file w/ the new paramters
            with CandidateModel(out_dir=out_dir, cf_fp=cf_fp, logger=log, 
                                mtag=mtag, name=col['name']) as wrkr:
                
                #load the base control file
                wrkr.init_model()
                
                #update base control file with new values
                pars_d2 = wrkr.upd_cfPars(pars_d1)
                
                #copy over all the data files
                if copyDataFiles:
                    pars_d3 = wrkr.copy_datafiles(cfPars_d=pars_d2)
                else:
                    pars_d3 = pars_d2
                

                #convert to strings again
                pars_d3 = {sect:{k:str(v) for k,v in att_d.items()} for sect, att_d in pars_d3.items()}
                
                #add notes
                txt = '#generated sensitivity analysis candidate %s.%s'%(mtag, self.resname)

                #save to file (this should overwrite everthing)
                wrkr.set_cf_pars({k:tuple([att_d,txt]) for k,att_d in pars_d3.items()})
            
 
 
            meta_lib[mtag] = {'cf_fp':cf_fp, 'name':col['name'], 'new_pars':len(col)-1}
            
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished building  %i to \n    %s'%(len(meta_lib), basedir))
        
        kstr = '\n'
        for mtag, d in meta_lib.items():
            kstr = kstr + '    \'%s\':r\'%s\',\n'%(mtag, d['cf_fp'])
        
        log.info(kstr)
        
        return meta_lib
            
            
        
        """
        add random color to each cf
        """
        
                         
 