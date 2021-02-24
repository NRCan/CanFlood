'''
Created on Feb. 24, 2021

@author: cefect

scripted dike runs
'''


import os, datetime
from qgis.core import QgsCoordinateReferenceSystem, QgsRasterLayer
import pandas as pd
import numpy as np

from hlpr.logr import basic_logger
mod_logger = basic_logger() 
    
    
from hlpr.Q import  vlay_write

from runComs import Runner

class DikeRunner(Runner):
    
    #dummy hanles for 'run_all' to get sequence from
    hndl_lib = {'expo':{}, 'vuln':{}, 'results':{}}
    
    meta_lib = dict()

    def __init__(self,
                 pars_d,
                 meta_fp = None,
                 **kwargs):
        
        super().__init__(pars_d, **kwargs)
        
        
        #=======================================================================
        # meta results filepaths
        #=======================================================================
        if meta_fp is None:
            meta_fp = os.path.join(self.out_dir, 
                          'cf_dikeRunner_%s_%s.xls'%(self.projName, self.scenarioName))
        
        
        
        
    def tools_expo(self,
        setPars_d,
        
        #exposure pars
        dist_dike = 40, #distance along dike to draw perpindicular profiles
        dist_trans = 200, #length (from dike cl) of transect 
        
        #output control
        breach_pts = True,
        write_tr = False, #write th etransecft template
        write_vlays=True,

        #plotting
        plots = True,
        figsize     = (14, 4),
        
        #flow control
        link_vuln = False,
        ):
    
        from misc.dikes.expo import Dexpo
        for tag, pars_d in setPars_d.copy().items():
            log = mod_logger.getChild(tag)
            #===========================================================================
            # build directories
            #===========================================================================
            out_dir = pars_d['out_dir']
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            #===========================================================================
            #expo--------
            #===========================================================================
    
            wrkr = Dexpo(logger=log, tag=tag, out_dir=out_dir,  LogLevel=20,
                          segID=pars_d['segID'], dikeID=pars_d['dikeID'],
                          figsize     = figsize,
                         ).ini_standalone(
                             crs = QgsCoordinateReferenceSystem(pars_d['crs']))
            
            #==========================================================================
            # load the data
            #==========================================================================
            #mandatory
            noFailr_d = wrkr.load_rlays(pars_d['noFailr_d'], basedir = pars_d['data_dir'])
            
            _ = wrkr.load_dike(pars_d['dikes'], basedir = pars_d['data_dir'])
            _ = wrkr.load_dtm(pars_d['dtm'])
    
            
            #==========================================================================
            # execute
            #==========================================================================
    
            dxcol, vlay_d = wrkr.get_dike_expo(noFailr_d, write_tr=write_tr,
                                               dist_dike=dist_dike, dist_trans=dist_trans)
            df = wrkr.get_fb_smry()
            
            #get just the breach points
            if breach_pts:
                breach_vlay_d = wrkr.get_breach_vlays()
            
            #=======================================================================
            # plots
            #=======================================================================
            if plots:
                wrkr._init_plt()
                for sidVal in wrkr.sid_vals:
                    fig = wrkr.plot_seg_prof(sidVal)
                    wrkr.output_fig(fig)
            #=======================================================================
            # outputs
            #=======================================================================
            
            wrkr.output_expo_dxcol()
            pars_d['dexpo_fp'] = wrkr.output_expo_df(as_vlay=write_vlays)
            if write_vlays: 
                wrkr.output_vlays()
                if breach_pts:
                    wrkr.output_breaches()
                    
            #=======================================================================
            # update for linked runs
            #=======================================================================
    
            setPars_d[tag] = pars_d
        #=======================================================================
        # vulnerability
        #=======================================================================
        if link_vuln:
            run_vuln(setPars_d, tag=tag)
           
        return out_dir
    
    
    def tools_vuln(self,
            setPars_d,
            tag='vuln',
            link_res = False
            ):
        
        from misc.dikes.vuln import Dvuln
        
        for tag, pars_d in setPars_d.copy().items():
            log = mod_logger.getChild(tag)
            #===========================================================================
            # build directories
            #===========================================================================
            out_dir = os.path.join(pars_d['out_dir'], 'vuln')
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            #===========================================================================
            #run--------
            #===========================================================================
            wrkr = Dvuln(logger=log, tag=tag, out_dir=out_dir,  LogLevel=20,
                         segID=pars_d['segID'], dikeID=pars_d['dikeID'],
                         )
            
            #==========================================================================
            # load the data
            #==========================================================================
            #mandatory
            wrkr._setup(dexpo_fp = pars_d['dexpo_fp'],
                        dcurves_fp = pars_d['dcurves_fp'],
                        )
            
            #==========================================================================
            # execute
            #==========================================================================
            wrkr.get_failP()
            
            wrkr.set_lenfx() #apply length effects
                        
            #=======================================================================
            # outputs
            #=======================================================================
            pars_d['pfail_fp'] = wrkr.output_vdfs()
            
            #=======================================================================
            # update
            #=======================================================================
            setPars_d[tag] = pars_d
            
        if link_res:
            run_res(setPars_d)
            
        return out_dir
    
    def tools_results(self,
            setPars_d,
            write_vlays=True,
            ):
        from misc.dikes.dRes import DRes
        for tag, pars_d in setPars_d.items():
            log = mod_logger.getChild(tag)
            #===========================================================================
            # build directories
            #===========================================================================
            out_dir = os.path.join(pars_d['out_dir'], 'vuln', 'res')
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)
            #===========================================================================
            #run--------
            #===========================================================================
    
            wrkr = DRes(logger=log, tag=tag, out_dir=out_dir,  LogLevel=20,
                         segID=pars_d['segID'], dikeID=pars_d['dikeID'],
                         ridN=pars_d['ridN'], ifidN=pars_d['ifidN'],
                         ).ini_standalone(
                             crs = QgsCoordinateReferenceSystem(pars_d['crs']))
            
            #==========================================================================
            # load the data
            #==========================================================================
            #mandatory
            wrkr.load_pfail_df(pars_d['pfail_fp'])
            wrkr.load_ifz_fps(pars_d['eifz_lib'])
            
            #==========================================================================
            # execute
            #==========================================================================
            vlay_d = wrkr.join_pfails()
     
            #=======================================================================
            # outputs
            #=======================================================================
            if write_vlays:
                wrkr.output_vlays()
            
           
        return out_dir
    
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
        
        #=======================================================================
        # precheck
        #=======================================================================
        
        fName = 'tools_%s'%toolName
        assert hasattr(self, fName)
        
        #=======================================================================
        # run the tools---------
        #=======================================================================
        #get the runner
        f = getattr(self, fName)            
        tool_od, meta_d = f(pars_d, logger=log, **kwargs)
    
        #===========================================================================
        # run summary data --------
        #===========================================================================
        self.meta_lib[toolName] = meta_d
        
        if writePars: #for single runs, just write now... othwerwise, let run_all write
            self.write_pars()

    
        log.info('finished on %s'%toolName)
        return tool_od, None
    
    #===========================================================================
    # OUTPUTTERS----
    #===========================================================================
    def write_pars(self, #write batch control file
                  df=None, #dummy catch for run_all
                  meta_lib = None, #library fo data to write
                  meta_fp = None,
                  
                  ):
        """
        updating a tab on a spreadsheet
        """
        if meta_lib is None: meta_lib = self.meta_lib
        
        #=======================================================================
        # load the old results
        #=======================================================================
        if os.path.exists(meta_fp):
            d = pd.read_excel(meta_fp, sheet_name=None)
            
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
                    df = pd.dataFrame.from_dict(data)
                
                
                df.to_excel(writer, sheet_name=tabnm, index=True, header=True)

            
        return meta_fp
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    