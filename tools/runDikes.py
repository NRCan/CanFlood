'''
Created on Feb. 24, 2021

@author: cefect

scripted dike runs
'''


import os, datetime
#from qgis.core import QgsCoordinateReferenceSystem, QgsRasterLayer
import pandas as pd
import numpy as np

from hlpr.logr import basic_logger
mod_logger = basic_logger() 
    
    
from hlpr.Q import view
from hlpr.exceptions import Error

from runComs import Runner

class DikeRunner(Runner):
    
    #dummy hanles for 'run_all' to get sequence from
    hndl_lib = {'expo':{}, 
                'vuln':{'dexpo_fp':{'filepath':True}},
                'rjoin':{'pfail_fp':{'filepath':True}}
                }
    
    meta_lib = dict()

    def __init__(self,
                 pars_d,
                 meta_fp = None,
                 control_fp=None, #parameters for  individual tool runs
                 **kwargs):
        
        super().__init__(pars_d, **kwargs)
        
        
        #=======================================================================
        # meta results filepaths
        #=======================================================================
        if meta_fp is None:
            self.meta_fp = os.path.join(self.out_dir, 
                          'cf_dikeSummary_%s_%s.xls'%(self.projName, self.scenarioName))
            
            
        
        #=======================================================================
        # control file paths
        #=======================================================================
        if control_fp is None:
            control_fp = os.path.join(self.out_dir, 
                          'cf_batchPars_%s_%s.csv'%(self.projName, self.scenarioName))
            
        self.control_fp = control_fp
        
        
        
        
    def tools_expo(self,
        pars_d,
        
        #exposure pars
        dist_dike = 40, #distance along dike to draw perpindicular profiles
        dist_trans = 200, #length (from dike cl) of transect 
        
        #output control
        breach_pts = False , #write the breach points
        write_tr = False, #write th etransecft template
        write_vlay = None,
        plot = None,

        
        logger=None,
        **kwargs
        ):
        """
        no need to loop... not batching dike segements.. just one r un
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('expo')
        
        if write_vlay is None: write_vlay = self.write_vlay
        if plot is None: plot = self.plot

        #=======================================================================
        # prechecks
        #=======================================================================
        assert not 'dexpo_fp' in pars_d, 'output parameter already set!'
        assert self.toolName == 'expo'
        #=======================================================================
        # setup the tool
        #=======================================================================
        from misc.dikes.expo import Dexpo
        
        wrkr = Dexpo(logger=log,  out_dir=os.path.join(self.out_dir, self.toolName),   
                          segID=pars_d['segID'], dikeID=pars_d['dikeID'],tag=self.scenarioName,
                          **kwargs
                         )

        self._init_child_q(wrkr) #setup Q
        self._init_child_pars(wrkr) #pass standard attributies 
                         

        #==========================================================================
        # load the data
        #==========================================================================
        #mandatory
        noFailr_d = wrkr.load_rlays(pars_d['noFailr_d'], basedir = pars_d['data_dir'])
        
        dike_vlay = wrkr.load_vlay(os.path.join(pars_d['data_dir'], pars_d['dikes']))
        
        _ = wrkr.prep_dike(dike_vlay)
        _ = wrkr.load_dtm(pars_d['dtm'])

        
        #==========================================================================
        # execute
        #==========================================================================

        dxcol, vlay_d = wrkr.get_dike_expo(noFailr_d, write_tr=write_tr,
                                           dist_dike=dist_dike, dist_trans=dist_trans)
        expo_df = wrkr.get_fb_smry()
        
        #get just the breach points
        if breach_pts:
            breach_vlay_d = wrkr.get_breach_vlays()
        
        #=======================================================================
        # plots
        #=======================================================================
        if plot:
            """
            should we take this over for our children also?
            """
            wrkr._init_plt()
            for sidVal in wrkr.sid_vals:
                fig = wrkr.plot_seg_prof(sidVal)
                wrkr.output_fig(fig)
        #=======================================================================
        # outputs
        #=======================================================================
        
        wrkr.output_expo_dxcol()
        self.pars_d['dexpo_fp'] = wrkr.output_expo_df()
        
        if write_vlay: 
            wrkr.output_vlays()
            if breach_pts:
                wrkr.output_breaches()
                
        #=======================================================================
        # meta
        #=======================================================================
        self.meta_d = {'dexpo_fp': self.pars_d['dexpo_fp']} #run_all reporting
        """
        indexing by dike segment
        """
        expoV_df = expo_df.loc[:, wrkr._get_etags(expo_df)] #just the exposure values

        meta_df = expo_df.join(expoV_df.max(axis=1).rename('max_expo'))
        
                

        return wrkr.out_dir, meta_df
    
    
    def tools_vuln(self,
            pars_d,
            
            logger=None,
            **kwargs

            ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        assert self.toolName=='vuln'
        log = logger.getChild('vuln')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        #assert 'dexpo_fp' in pars_d, 'vuln requires the dexpo_fp.. did you run expo yet?'
        #assert not 'pfail_fp' in pars_d, 'output parameter already set!'
        
        from misc.dikes.vuln import Dvuln
 
        #===========================================================================
        #run--------
        #===========================================================================
        wrkr = Dvuln(logger=log,  out_dir=os.path.join(self.out_dir, self.toolName),   
                          segID=pars_d['segID'], dikeID=pars_d['dikeID'],tag=self.scenarioName,
                          **kwargs
                         )
        
        self._init_child_pars(wrkr) #pass standard attributies 
        
        #==========================================================================
        # load the data
        #==========================================================================
        """bundles the two loader functions"""
        wrkr._setup(dexpo_fp = pars_d['dexpo_fp'],
                    dcurves_fp = pars_d['dcurves_fp'],
                    )
        
        #==========================================================================
        # execute
        #==========================================================================
        pf_df = wrkr.get_failP()
        """
        view(pf_df)
        """
        
        """consider making thise a separate tool?"""
        #wrkr.set_lenfx() #apply length effects
                    
        #=======================================================================
        # outputs
        #=======================================================================
        self.pars_d['pfail_fp'] = wrkr.output_vdfs()
        
        #=======================================================================
        # meta
        #=======================================================================
        pfails_df = pf_df.loc[:, pf_df.columns.isin(wrkr.etag_l)] #just the failure values
        
        meta_df = pf_df.join(pfails_df.max(axis=1).rename('pfail_max'))

        self.meta_d = {'pfail_fp': self.pars_d['pfail_fp']} #run_all reporting
                

        return wrkr.out_dir, meta_df
    
    def tools_rjoin(self, #join vulnerability results onto dike exposure polygons
            pars_d,
            
            write_vlay = True,
            logger=None,
            **kwargs

            ):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        assert self.toolName=='rjoin'
        log = logger.getChild('rjoin')
        if write_vlay is None: write_vlay=self.write_vlay
        #=======================================================================
        # prechecks
        #=======================================================================
        #assert 'pfail_fp' in pars_d, '%s requires the pfail_fp.. did you run vuln yet?'%self.toolName
        
        from misc.dikes.rjoin import DikeJoiner
 
        #===========================================================================
        #setup the worker
        #===========================================================================
        wrkr = DikeJoiner(logger=log,  out_dir=os.path.join(self.out_dir, self.toolName),   
                          segID=pars_d['segID'], dikeID=pars_d['dikeID'], tag=self.scenarioName,
                          **kwargs
                         )
        
        self._init_child_pars(wrkr) #pass standard attributies 
        self._init_child_q(wrkr) #setup Q

        #==========================================================================
        # load the data
        #==========================================================================
        #mandatory
        wrkr.load_pfail_df(pars_d['pfail_fp'])
        wrkr.load_ifz_fps(pars_d['eifz_d'])
        
        #==========================================================================
        # execute
        #==========================================================================
        vlay_d = wrkr.join_pfails()
 
        #=======================================================================
        # outputs
        #=======================================================================
        if write_vlay:
            vlay_fp_d = wrkr.output_vlays()
        else:
            vlay_fp_d = dict()
            
        #=======================================================================
        # meta
        #=======================================================================
        self.meta_d = vlay_fp_d #run_all reporting
            
           
        return wrkr.out_dir, pd.Series(vlay_fp_d).rename('ifz_fp')
    
    #===========================================================================
    # SINGLE TOOL HANDLER-------
    #===========================================================================
    def run_toolbox(self,
                    toolName, #run a specific tool group (other than build)
                        #build, dmg2, risk1, risk2, djoin
            pars_d=None, #common parameters for build toolbox

            writePars = True, #whether to save the control parameters to file

            control_df=None, #not using this here.. but passeed by run_all()
            logger=None,
            **kwargs, #passed to 'tools_xxx()' function
            ):
    
        #===========================================================================
        # defaults
        #===========================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('rT')
    
        self.toolName=toolName
        if pars_d is None: pars_d =self.pars_d
        
        assert toolName in self.hndl_lib
        phndl_d = self.hndl_lib[toolName] #handles for this tool
        
        #=======================================================================
        # precheck
        #=======================================================================
        
        fName = 'tools_%s'%toolName
        assert hasattr(self, fName)
        
        #=======================================================================
        # augment parameters from csv
        #=======================================================================
        miss_l = set(phndl_d.keys()).difference(pars_d)
        if len(miss_l)>0:
            assert not toolName=='expo', 'missing parameters on expo run: %s'%miss_l
            assert os.path.exists(self.control_fp), '%s is missing %i and no batchPars provided!\n    %s'%(
                toolName, len(miss_l), miss_l)
            bpars_d = pd.read_csv(self.control_fp, index_col=0, header=0).iloc[:, 0].to_dict()
            
            #get just the ones we're missing
            bp_d = {k:v for k,v in bpars_d.items() if k in miss_l}
            pars_d.update(bp_d) #update the parameters
            
            log.info('%s missing %i required pars... collected from batchPars.csv\n    %s'%(
                toolName, len(miss_l), bp_d))
        
        #=======================================================================
        # check parameters
        #=======================================================================
        for k, hndl_d in phndl_d.items():
            assert k in pars_d, '%s missing %s'%(toolName, k)
            
            for hndl, v in hndl_d.items():
                if hndl=='filepath':
                    assert v, 'should be True...'
                    assert os.path.exists(pars_d[k]), '%s got bad filepath: %s'%(k, pars_d[k])
                    
                else:
                    raise Error('unrecognized handle: %s'%hndl)
                    
                
        
        
        #=======================================================================
        # run the tools---------
        #=======================================================================
        #get the runner
        f = getattr(self, fName)            
        tool_od, meta_df = f(pars_d, logger=log, **kwargs)
    
        #===========================================================================
        # run summary data --------
        #===========================================================================
        self.meta_lib[toolName] = meta_df
        
        if writePars: #for single runs, just write now... othwerwise, let run_all write
            self.write_pars()
            self.write_parsd()

    
        log.info('finished on %s'%toolName)
        return tool_od, meta_df
    
    #===========================================================================
    # OUTPUTTERS----
    #===========================================================================
    def write_pars(self, #write batch control file
                  df=None, #dummy catch for run_all
                  meta_lib = None, #library fo data to write
                  meta_fp = None,
                  logger=None,
                  ):
        
        """
        updating a tab on a spreadsheet
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log=logger.getChild('write_pars')
        if meta_lib is None: meta_lib = self.meta_lib
        if meta_fp is None: meta_fp = self.meta_fp
        
        if len(meta_lib)==0: 
            log.warning('no meta_lib data! skipping')
            return meta_fp
        #=======================================================================
        # load the old results
        #=======================================================================
        d = dict()
        if not meta_fp is None:
            if os.path.exists(meta_fp):
                d = pd.read_excel(meta_fp, sheet_name=None)
                
        if meta_fp is None:
            meta_fp = os.path.join(self.out_dir, 'dikes_meta.xls')
                
        assert isinstance(meta_fp, str)
        assert meta_fp.endswith('.xls')
            
        #=======================================================================
        # reconcile
        #=======================================================================
        d.update(meta_lib) #should overwrite and add any new
        
        
        #=======================================================================
        # write ammended resulst
        #=======================================================================
        with pd.ExcelWriter(meta_fp) as writer:
            for tabnm, data in d.items():
                if len(data)==0: continue 
                
                #type conversion
                if isinstance(data, pd.DataFrame):
                    df = data
                else:
                    df = pd.Series(data)
                
                
                df.to_excel(writer, sheet_name=tabnm, index=True, header=True)

        log.info('wrote %i tabs to file: %s'%(len(d), meta_fp))
        return meta_fp
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    