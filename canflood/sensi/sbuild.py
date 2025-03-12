'''
Created on Nov. 20, 2021

@author: cefect

constructing sensitivity analysis model candidates
'''

#===============================================================================
# imports----------
#===============================================================================
import os, datetime, pickle, copy, shutil, configparser, warnings
import pandas as pd
import numpy as np
 

from canflood.hlpr.basic import view

        
                     
from canflood.sensi.coms import SensiShared

    
    

class CandidateModel(SensiShared):
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
                        if os.path.normpath(new_fp)==os.path.normpath(fp):
                        
                        #if os.path.sameopenfile(new_fp, fp):
                            pars_lib[section][valnm] = fp #this can happen on repeat clicks of compile
                        else:
                            pars_lib[section][valnm] = shutil.copyfile(fp, new_fp)
                        
                        meta_d[valnm] = pars_lib[section][valnm] 
                    
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('copied %i data files to %s'%(
            len(meta_d), out_dir))
    
        return pars_lib
                
            
    


class SensiConstructor(SensiShared):
    
 
    def typeset_df(self, #typeset and prepthe prameter frame usig handles
                   df_raw, #parameters: candidates
                   logger=None,
                   ):
        """
        we transpose the frame to preserve types on columns
        """
        
        if logger is None: logger=self.logger
        log=logger.getChild('typeset_df')
        
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(df_raw, pd.DataFrame)
        assert 'name' in df_raw.columns, 'must specify a name row'
        assert df_raw['name'].iloc[0] == self.name, 'base name does not match'
        
        log.info('on %s'%str(df_raw.shape))

        #=======================================================================
        # typeset
        #=======================================================================
        #loop and collect as typeset series
        d = dict( )
        for colName, col in df_raw.copy().items():
            assert hasattr(self, colName), colName
            
            #retrieve default from class
            classVal = getattr(self, colName)
            
            #special for booleans
            if classVal.__class__.__name__=='bool':
                d[colName] = col.str.lower().replace({'true':True,'false':False}).astype(classVal.__class__)
            
            else:            
                d[colName] = col.astype(classVal.__class__)
            
            
            
        df = pd.concat(list(d.values()), axis=1, keys=d.keys())

        log.debug('finished w/ %i typeset: \n    %s'%(len(df), df.dtypes.to_dict()))
        return df #{candidates: paraeters}
            
        
 
            

    def build_candidates(self, #build all the candidate models
                         df_raw, #frame with parameters {par:candidate} (always absolute filepaths)
                         base_cf_fp = None, #base control file
                         base_cf_fn = None, #ase control file name
                         logger=None,
                         out_basedir = None, #directory where all the candidate models will be saved
 
                         copyDataFiles=True, #whether to copy over all datafiles
                         absolute_fp=None, #status of the base control file (df_raw is always absolute)
                         ):
        
        """
        WARNING: this reads candidates from a datarame, not the control file
 
        """
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('bcan')
        
        if base_cf_fp is None: base_cf_fp=self.cf_fp
        if out_basedir is None: out_basedir = self.out_dir
 
        if absolute_fp is None: absolute_fp=self.absolute_fp
        
        if base_cf_fn is None:
            base_cf_fn = os.path.splitext(os.path.basename(base_cf_fp))[0]
        
        
        log.info('on %s'%base_cf_fp)
 
        #=======================================================================
        # prep the data
        #=======================================================================
        
        df1 = self.typeset_df(df_raw, logger=log)
        
        
        #=======================================================================
        # #check base pars
        #=======================================================================
        """checking whats on the compile tab (first row) 
        against what weve loaded from the cf on the setup tab"""
        pars_d = df1.iloc[0,:].to_dict()
        for k,v in pars_d.items():
            assert hasattr(self, k), 'worker missing requested attribute \'%s\''%k
            #classVal = getattr(self, k)
            #assert v == classVal, 'mismatch on \'%s\': %s != %s'%(k, classVal, v)

 
        
        #df = df1.iloc[1:,:] #drop the base
        
 
        df = df1.copy()
        #=======================================================================
        # remove results from main
        #=======================================================================
        """never using results from the main
        moved to Load"""

        #=======================================================================
        # get sections
        #=======================================================================
        attn_sect_d = self.get_sections(df1.columns.tolist(), logger=log)
        
 

        #=======================================================================
        # loop and create each candidate
        #=======================================================================
        log.info('creating %i candidate models'%len(df.T))
        meta_lib = dict()
        
        #collect init kwargs for candidates
        kwargs = {attn:getattr(self,attn) for attn in [
            #'absolute_fp', #need to convert everything to absolute 
            'feedback']}
        
        #loop on rows bur presever types
        first=True
        for i, (mtag, pars_d) in enumerate(df.to_dict(orient='index').items()):
            log = logger.getChild('bcan.%i'%i)
            log.debug('on %s'%mtag)
 
            
            #===================================================================
            # #setup the new directory
            #===================================================================
            out_dir = os.path.join(out_basedir, mtag)
            if os.path.exists(out_dir):
                assert self.overwrite
            else:
                os.makedirs(out_dir)
                

            
            #===================================================================
            # prep the control file
            #===================================================================
            #copy over the base cf_fp
            cf_fp = os.path.join(out_dir,'%s_%s.txt'%(base_cf_fn, mtag)) 
            _ = shutil.copyfile(base_cf_fp, cf_fp)
            log.info('copied cf to %s'%cf_fp)
            
            
            #===================================================================
            # prep the base control file
            #===================================================================
            if first:
                #handle relatives
                if not self.absolute_fp:
                    #change everything to absolute
                    self._cfFile_relative(cf_fp=cf_fp, logger=log)
                    
                #tell subsequent siblings to use this one
                base_cf_fp = cf_fp
                
                first=False
            
 
            
            #===================================================================
            # prep the parameters
            #===================================================================
            pars_d1 = dict()
            for attn, attv in pars_d.items():
                sectName = attn_sect_d[attn]
                if not sectName in pars_d1:
                    pars_d1[sectName]=dict()
                
                pars_d1[sectName][attn] = attv
                
            
            #===================================================================
            # #update the control file w/ the new paramters
            #===================================================================
            log.debug('building %s'%pars_d['name'])
            with CandidateModel(out_dir=out_dir, cf_fp=cf_fp, logger=log, mtag=mtag, name=pars_d['name'], **kwargs) as wrkr:
                
                #load the base control file
                """
                wrkr.absolute_fp
                wrkr.base_dir
                """
                wrkr.init_model()
                
                #update base control file with new values
                pars_d2 = wrkr.upd_cfPars(pars_d1)
                
                #copy over all the data files
                if copyDataFiles:
                    pars_d3 = wrkr.copy_datafiles(cfPars_d=pars_d2)
                else:
                    pars_d3 = pars_d2
                
                #special fix for colors
                if 'color' in pars_d3['plotting']:
                    pars_d3['plotting']['color'] = pars_d3['plotting']['color'].replace('#','?')
                    
                
                #convert to strings again
                pars_d3 = {sect:{k:str(v) for k,v in att_d.items()} for sect, att_d in pars_d3.items()}
                
                #add notes
                txt = '#generated sensitivity analysis candidate %s.%s'%(mtag, self.resname)

                #save to file (this should overwrite everthing)
                wrkr.set_cf_pars({k:tuple([att_d,txt]) for k,att_d in pars_d3.items()})
                
                log.debug('finished on %s'%wrkr.name)
            
 
 
            meta_lib[mtag] = {'cf_fp':cf_fp, 'name':pars_d['name'], 'new_pars':len(pars_d)-1, 'pars_d':pars_d3}
            
        #=======================================================================
        # wrap
        #=======================================================================
        
        kstr = 'finished building  %i to \n    %s'%(len(meta_lib), out_basedir) + '\n'
        for mtag, d in meta_lib.items():
            kstr = kstr + '    \'%s\':r\'%s\',\n'%(mtag, d['cf_fp'])
        
        log.info(kstr)
        
        return meta_lib
    
    
    def cf_append_subdir(self, #adding a subdir to relative filepaths

                         subdir,
                              cf_fp=None,
                          sections=['dmg_fps', 'risk_fps'], #parameter sections to manipulate
                         logger=None):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        if cf_fp is None: cf_fp=self.cf_fp
        log=logger.getChild('cf_append_subdir')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        assert not self.absolute_fp
        
        #=======================================================================
        # load the control file
        #=======================================================================
        pars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.debug('reading parameters from \n     %s'%pars.read(cf_fp))
            
        pars = self._cf_relative(pars, base_dir=subdir, sections=sections, warn=False)
        
                #write the config file 
        with open(cf_fp, 'w') as configfile:
            pars.write(configfile)
            
        log.info('updated control file at :    %s'%(cf_fp))
        
        return cf_fp
        
 
        
                         
 