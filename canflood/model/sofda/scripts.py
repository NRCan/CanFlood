'''
Created on Jun 11, 2018

@author: cef
'''
#===============================================================================
# HIERARCHY and RUN LOOPS --------------------------------------------------------------
#===============================================================================
'''
see discussion in hp_sim.py
KEY RUN LOOPS
*Session.run_all():                10,000x              controls a single scenario
    *Simulation.run_timeline():    50x       controls one simulation of a scenario (a set of stochastic parameters)
        *Tstep.run_dt():                4x:    runs all the user specified models (and their submodels)
            *Udev.run()             2x : runs all the Actions specified on the timeline
                Action.run()
                    Action.run()    5x: we allow chaining of actions
                        Dynamic_par.run() 5x
                    Dynamic_par.run() 5x
                    
            *Fdmg.run()             10x:     bundles the flood damage tasks
                Flood.run()      1000x        calcluate the damage for each house
                    House.run()    4x        get damage at this depth from each Dfunc
                        Dfunc.run()  1x       main damage call. get the damage from the wsl

*5 special top-level objects PARENT/POINTERS                    
'''




#===============================================================================
# IMPORT STANDARD MODS -------------------------------------------------------
#===============================================================================
import os, time, logging, gc, weakref, datetime


import pandas as pd
import numpy as np


from collections import OrderedDict as od
from weakref import WeakValueDictionary as wdict
from hlpr.exceptions import Error
#from weakref import proxy

#===============================================================================
#  IMPORT CUSTOM MODS ---------------------------------------------------------
#===============================================================================
#import hp.plot #need to call this first so thet matplotlib backend configures correctly
import model.sofda.hp.basic as basic

#from .. import model.sofda.hp.pd as hp_pd
import model.sofda.hp.pd as hp_pd 
import model.sofda.hp.oop as hp_oop

import model.sofda.hp.sim as hp_sim
import model.sofda.hp.dynp as hp_dynp

import model.sofda.hp.dyno as hp_dyno
import model.sofda.hp.sel as hp_sel
import model.sofda.hp.outs as hp_outs
import model.sofda.hp.dict as hp_dict #wasnt added before for some reason...
import model.sofda.hp.data as hp_data

from model.sofda.hp.pd import view

#===============================================================================
# import in project mods
#===============================================================================
import model.sofda.fdmg.scripts_fdmg as fscripts
import model.sofda.udev.scripts as udev_scripts

#===============================================================================
# mod_logger
#===============================================================================
mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')


#===============================================================================
# module parameter file setup
#===============================================================================
'reserved for parameter files of this module hidden from the user'
_mod_dir = os.path.dirname(__file__)


"""this is super gross"""
class Session( #main session handler. runs many simulations for stochastic modelling
               
        hp_sim.Sim_session,
        hp_dyno.Dyno_controller,
        hp_oop.Session_o,  
        hp_sel.Sel_controller, 
        hp_dynp.Dynp_session,
        hp_outs.Out_controller,
        hp_data.Data_wrapper,
        #hp.plot.Plot_o,
        hp_oop.Child): 
   
    #===========================================================================
    # program parametser
    #===========================================================================
    mod_n_l = ['udev', 'fdmg'] #list of model names recognized by the simulation
    
    color = 'blue'
    
    bfh_min = 1.0 #minimum acceptable basement finish height
    
    #===========================================================================
    # calculated pars
    #===========================================================================
    #session style flags
    wdfeats_f             = False #flag whether dfeats are used in teh session

    'not sure about this'
    dyn_haza_f      = False #flag to indicate whether the hazard is dynamic (changes through time)
    dyn_vuln_f      = False #dynamic vulnerability (i.e. udev model has some actions)
    load_dfeats_first_f = True
    
    bdmg_dx = None 
    #===========================================================================
    # user pars
    #===========================================================================
    
    transp_f = False
    
    #output flags
    """not sure where all the other ones are..."""
    write_fly_bdmg_dx = False
    
    

    def __init__(self, dynp_hnd_file = None, *vars, **kwargs):
        logger = mod_logger.getChild('Session') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
        #=======================================================================
        # set defaults
        #=======================================================================
        if dynp_hnd_file is None:
            dynp_hnd_file = os.path.join(os.path.dirname(__file__), '_pars', 'dynp_handles_20190512.xls')
            
        assert os.path.exists(dynp_hnd_file)
            
        self.dynp_hnd_file = dynp_hnd_file
        
        #initilzie the first baseclass
        super(Session, self).__init__(*vars, **kwargs) 
        

        
        #=======================================================================
        # debug inits  
        #=======================================================================
        #resource profiler
        if self._prof_mem>0:
            import model.sofda.hp.prof_mem as hp_profMem
            self.resc_prof = hp_profMem.Resource_profiler(logger = self.logger,
                                                     _wtf = self.session._write_data,
                                                     name = self.tag,
                                                     session = self)
            
            self.prof(state='0.%s'%self.session.state) #make the first write to the frame
            
        #=======================================================================
        # special loader funcs
        #=======================================================================
        logger.debug('set_flags () \n')
        self.set_flags()
        
        #fly results
        if self.write_fly_f:
            #basic results 
            self.fly_res_fpath = os.path.join(self.outpath, '%s fly_res.csv'%self.tag)
            
            #dx results
            if self.output_dx_f:
                self.fly_resx_fpath = os.path.join(self.outpath, '%s fly_res_dx.csv'%self.tag)
                
            #bdmg results
            if self.write_fly_bdmg_dx:
                self.fly_bdmg_fpath = os.path.join(self.outpath, '%s bdmg_fly_res.csv'%self.tag)
                self.bdmg_dx = pd.DataFrame() #set the empty container
            

        self.logger.info('SOFDA simulation initialized as \'%s\' with %i runs (_dbgmstr=%s) \n \n'
                         %(self.name, self.run_cnt, self._dbgmstr))
        

        
        return
    
    def set_flags(self): #set the calculation session style flags
        """need to load all of these up front so the other models can initilize properly"""
        logger = self.logger.getChild('set_flags')

        if self._parlo_f:
            logger.warning('_parlo_f = TRUE!!!')
        else:
            logger.info('_parlo_f = FALSE')

        if not self.glbl_stoch_f:
            logger.warning('Dynamic Pars disabled!!!!')
            #time.sleep(3)
        #=======================================================================
        # dynamic  hazard and udev
        #=======================================================================
        self.dyn_vuln_f = True
        self.dyn_haza_f = True
            
        """this doesn't really work
        if self.glbl_stoch_f:
            self.dyn_vuln_f = True
            self.dyn_haza_f = True
            
            todo: come up wtih better exclusions

            df = self.session.pars_df_d['timeline']
            
            for ind, run_seq_d in df.loc[:,'run_seq_d'].iteritems():
                d = OrderedDict(eval(run_seq_d))
                
                for modn, run_seq_l in d.iteritems():
                    #drop normal runs
                    try:
                        run_seq_l.remove('*run')
                    except:
                        logger.debug('no \'*run\' in run_seq')
                        
                    if len(run_seq_l) > 0: #if there are any left we have a dynamic run
                        if modn == 'Udev': self.dyn_vuln_f = True
                        elif modn == 'Fdmg': self.dyn_haza_f = True 
                        
            run_seq_l.remove('xx')
            if np.any(df.loc[:,'Fdmg.wsl_delta'] !=0):
                self.dyn_haza_f = True #flag to indicate whether the hazard is dynamic (changes through time)
                
            if np.any(df.loc[:,'Fdmg.fprob_mult'] !=1):
                self.dyn_haza_f = True #flag to indicate whether the hazard is dynamic (changes through time)"""

                
        logger.info('dyn_haza_f = %s and dyn_vuln_f = %s'%(self.dyn_haza_f, self.dyn_vuln_f))


        #=======================================================================
        # damage functions
        #=======================================================================
        df = self.session.pars_df_d['dfunc']
        boolidx = df.loc[:,'dfunc_type'] == 'dfeats'
        if boolidx.sum() > 0: 
            self.wdfeats_f = True


        else:
            self.wdfeats_f = False
            
        logger.info('wdfeats_f = %s'%self.wdfeats_f)

            
        #=======================================================================
        # dynamic vulnerability
        #=======================================================================
        """
        #dynamic vulnerability (i.e. udev model has some actions)
        if self.glbl_stoch_f:   
            df = self.session.pars_df_d['timeline']
            boolcol = df['01udev'] == 'no'
            if boolcol.sum() < len(df): #timeline has some udev runs loaded onto it
                self.dyn_vuln_f = True
                
            logger.info('dyn_vuln_f = %s'%self.dyn_vuln_f)"""
        
        #=======================================================================
        # determine all the outpars
        #=======================================================================
        self.build_outpars_d()

            
        return
        
    def load_models(self):
        logger = self.logger.getChild('load_models')
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        have main.py call this
        
        #=======================================================================
        # DEPENDENCIES
        #=======================================================================
        order matters.
        timeline
            Fdmg
            Udev
            
        Udev
            Selectors
            Dynp
        
        
        setup_outs_library (out_lib_od)
            needs all the children to be loaded
            
        self._parlo_f
        
        """
        #=======================================================================
        # fdmg model
        #=======================================================================
        logger.info('loading damage submodel')
        logger.debug('\n ')
        
        self.fdmg = self.spawn_child(childname = 'fdmg', kid_class = fscripts.Fdmg)
        self.prof(state='load.fdmg')
        self.model = self.fdmg #this avoids alot of error flags during inheritance
        
        #=======================================================================
        # udev model
        #=======================================================================
        logger.debug('\n \n')
        logger.info('loading udev submodel')
        logger.debug('\n \n')
        
        self.udev = self.spawn_child(childname = 'udev', kid_class = udev_scripts.Udev)
        self.prof(state='load.udev')
        self.fdmg.udev = self.udev
        
        self.models_d = {'Fdmg':self.fdmg,'Udev':self.udev}
        #self.udev.load_data()
        """
        seperated this out so that the buildinv inventory special attributes are loaded
        before the Selelectors run for the first time.
        
        self.inherit_parent_ans
        
        """
        


        #=======================================================================
        # #selectors
        #=======================================================================
        logger.debug('\n \n')
        logger.info('loading object selectors')
        logger.debug("\n \n")
        
        self.raise_selectors(self.pars_df_d['selectors'])
        self.prof(state='load.sels')
                
        #=======================================================================
        # #dynamic parameters
        #=======================================================================
        logger.debug('\n \n')
        logger.info('loading dynps')
        logger.debug('\n \n')
        
        self.raise_dynps(self.pars_df_d['dynp'])
        self.prof(state='load.dynps')
            
        #=======================================================================
        # udev Actions (steal Selectors and Dynps)
        #=======================================================================
        logger.debug('\n \n')
        logger.info('raising Udev')
        logger.debug('\n \n')
        'seperated this out so the dynamic pars are accessible'
        
        self.udev.raise_children()
        self.prof(state='load.Actions')
        
        #=======================================================================
        # #Actions
        #=======================================================================
        logger.info('loading agent Actions')
        logger.debug('\n \n')
        self.acts_d = self.raise_children_df(self.session.pars_df_d['actions'], 
                                             kid_class = Action)
        
        #=======================================================================
        # timeline
        #=======================================================================
        logger.debug('\n \n')
        logger.info('loading timeline')
        logger.debug('\n \n')
        
        self.load_timeline()
        self.prof(state='load.Tsteps')

            
        #=======================================================================
        # load the simulations
        #=======================================================================
        logger.debug('\n \n')
        logger.info('loading sims for sensi_f = %s'%self.session.sensi_f)
        logger.debug("\n \n")
        
        if self.session.sensi_f:    self.load_sensi_sims()
        else:               
            self.load_sims() #spawn all the simulation children
        self.prof(state='load.Sims')
        
        
        #=======================================================================
        # Outputrs        
        #=======================================================================
        logger.debug('\n \n')
        logger.info('loading Outputrs')
        logger.debug("\n \n")
        
        self.raise_outputrs()
        self.prof(state='load.Outputrs')
        
        if self.session.sensi_f: self.check_sensi_delta_outrs()
        
        #=======================================================================
        # Dynp handles
        #=======================================================================
        logger.debug('\n')
        """ movd to Dynp_controller.__init__
        'not actually children'
        self.load_dynp_hnd_file(_dynp_hnd_file)"""
        """ having each object do this itself
        self.init_dynos() #secondary initilization on all dyno kids"""
        
        
        #self.check_family_refs(max_cnt = 3)
        
        logger.debug('finished with %i children (gc = %i) \n'%(len(self.kids_d), gc.collect()))
       
        return
          
    def load_timeline(self):
        logger = self.logger.getChild('load_timeline')
        #=======================================================================
        # #get the list of mod heads on the timeline with values entered
        #=======================================================================
        df = self.pars_df_d['timeline'].sort_values('rank')
        
        logger.debug('on timeline with \'%s\''%str(df.shape))
        
        'the Tstep needs this..'
        df_clean = df.dropna(axis='columns',how='all')
        #search_ser = pd.Series(df_clean.columns)
        
        l = []
        for e in df_clean.columns.tolist():
            if basic.isnum(e[:2]):
                l.append(e)
        
        l.sort()
        
        self.tl_mod_head_n_l = l

        #=======================================================================
        # spawn the timeline
        #=======================================================================
        logger.debug('raise_children_df() \n')
        self.timeline_d = self.raise_children_df(df, kid_class = Tstep, 
                                   dup_sibs_f=False,
                                   container = od)
        
        #self.timeline_d = OrderedDict(sorted(d.items(), key=lambda t: t[0])) #sort it
        
        #=======================================================================
        # secondary
        #=======================================================================
        self.year0 = list(self.timeline_d.values())[0].year #take the year from the first time step object
               
        logger.debug('finished with year0 = %i \n'%self.year0)
        
    def load_sims(self): #load sims
        logger = self.logger.getChild('load_sims')
        
        df = self.get_sim_metadf(self.run_cnt) #build a dummy frame with the sim meta data
        
        self.sims_meta_df = df
        #=======================================================================
        # raise all thse
        #=======================================================================
        self.sims_od = self.raise_children_df(df, kid_class = Simulation, 
                                              dup_sibs_f=True,
                                              container = wdict)
        
        logger.debug('loaded %i Simulations \n'%len(self.sims_od))
        
        return

    def load_sensi_sims(self, sims_per_var = None): #load simulations for sensitivity analysis
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('load_sensi_sims')
        
        #if sims_per_var is None: sims_per_var = self.sims_per_var
    
        df = self.get_sensi_metadf(wtf=False)
        
        self.run_cnt = min(len(df), self.run_cnt)
        
        """NO! We always want to allow partial run cnt
        
        if self._parlo_f: 
            self.run_cnt = min(len(df), self.run_cnt)
            logger.warning('trimming sensitivity simulations for testing')
        else: self.run_cnt = len(df)"""
        
        logger.info('set run_cnt to %i'%self.run_cnt)
        
        """
        we cannot precoimpile the simulations with set dynps 
        cant do a complete copy of the dynp_d
        
        self.sims_od.keys()
        
        hp_pd.v(df)
        """
        #=======================================================================
        # load the sims
        #=======================================================================
        self.load_sims()
        
        #=======================================================================
        # attach the sensi_ser
        #=======================================================================
        sim_l = self.sims_meta_df['name'].values.tolist()
        for sim_key in sim_l:

            sim = self.sims_od[sim_key]
            sim_ind = sim.ind
            
        
            sensi_ser = df.loc[sim_ind, :]
            
            sim.sensi_ser = sensi_ser.copy()
            
        logger.debug('finished and attached sensi_ser to %i simulations'%len(self.sims_od))
        
        return
        
    def run_session(self, wtf=None): #run each simulation
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        main.py
        """
        logger = self.logger.getChild('run_session')
        
        if wtf is None: wtf = self.session._write_data
        
        #=======================================================================
        # setup the run
        #=======================================================================
        logger.debug('\n \n \n ')
        
        logger.debug('\n~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        logger.info('setting up run')
        """
        Unlike other sim objects, the Session needs to setup its own run
        not sure how to differentiate between this and the .__init__ commands
        """
        """happens during selector __init__?
        self.run_selectors()"""
        # set the initial sample values
        self.run_dynps() #first call. set all 'Session' values

        # setup the results frame
        df = pd.DataFrame()
        dxcol = pd.DataFrame() #multi dimensional outputs
        
        
        logger.debug('~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~')
        logger.info('running %i simulations'%len(self.sims_od))
        #=======================================================================
        # loop through each simulation and run
        #=======================================================================
        
        first = True
        ldf_cnt = None #for testing
        
        'workaround for ordered dict and weakref'
        sim_l = self.sims_meta_df['name'].values.tolist()
        for sim_key in sim_l:
            self.state = 'run.%s'%sim_key
            
            self.prof(state = '0.%s.start'%self.state) #profiling
            'state needs to start with zero so the profiler runs for _prof_mem = 0'
            #===================================================================
            # setup vals
            #===================================================================
            start = time.time()
            sim = self.sims_od[sim_key]
            sim_ind = sim.ind
            self.hs_stamp = (sim.upd_sim_lvl, sim.ind)
         
            #===================================================================
            # runs
            #===================================================================
            logger.info('\n (%i/%i)*************************************************************** \n \n'%(sim_ind+1, len(sim_l)))
            logger.debug('run_selectors() \n')
            sim.run_selectors() #update all the selectors
            
            #sensitivity
            if self.session.sensi_f:
                logger.debug('sensi_f=TRUE. raise_dynps_sensi() \n') 
                sim.raise_dynps_sensi() #re calibrate the dynps for this sensitivity analysis
                            
            logger.debug('run_dynps() \n')
            sim.run_dynps() #second call. set all dynp 'Simulation' values
            
            logger.debug('run_timeline() \n')
            sim.run_sim()
            #===================================================================
            # #get/write the results
            #===================================================================
            self.session.state = 'getres.%s'%sim_key
            logger.debug('get_results() \n')
            res_ser, res_dx = sim.get_res_sim(wtf = self.write_sim_res_f) #get teh stats results summary
            
            df = df.append(res_ser, ignore_index = False) #add these
            
            if self.output_dx_f:
                dxcol = dxcol.append(res_dx)
            
            #fly writers
            if self.write_fly_f: 
                hp_pd.write_fly_df(self.fly_res_fpath,res_ser,  lindex=sim_key,
                                   first = first, tag = self.tag, 
                                   db_f = self.db_f, logger=self.logger) #write results on the fly
                
                if self.output_dx_f:
                    hp_pd.write_fly_df(self.fly_resx_fpath,res_dx,  sim_key,
                                   first = first, tag = self.tag,
                                    db_f = self.db_f, logger=self.logger) #write results on the fly
                    
                    
                if not self.bdmg_dx is None:
                    self.write_bdmg_dx(sim.name, first)


                    
            
            #===================================================================
            # #clean up
            #===================================================================
            if not len(sim_l) -1 == sim_ind: #skip the last sim
                self.session.state = 'clean.%s'%sim_key
                logger.debug('reset_all() \n')
                self.reset_all()
            
                #===================================================================
                # clean out previous
                #===================================================================
                if first:
                    first = False
                else:
                    self.kill_obj(sim)
                    del self.sims_od[sim_key]
                    del sim
                    logger.debug('killed sim \'%s\''%sim_key)
                    #gc.collect()

                #===============================================================
                # testing
                #===============================================================
                if self.db_f:
                    if 'Dmg_feat' in self.family_d:
                        df_cnt = len(self.family_d['Dmg_feat'])
                    else:
                        df_cnt = 0
                        
                    if not ldf_cnt is None:
                        if not df_cnt == df_cnt:
                            raise IOError
                    
                    ldf_cnt = df_cnt #set for next time
                

            
            stop = time.time()
            logger.info('finished in %.2f mins sim %s'%((stop - start)/60.0, sim_key))
            self.prof(state = sim_key + '.end') #profiling

        #=======================================================================
        # wrap up
        #=======================================================================
        self.state = 'run.wrap'
        self.prof(state='0.run_session.post')
        
        logger.info('finished with res_df %s \n'%str(df.shape))
        
        #attach to the session
        self.res_df = df.dropna(axis='columns', how='all')
        self.res_dxcol = dxcol.dropna(axis='columns', how='all')
        self.data = df.dropna(axis='columns', how='all')
        
        return
    
    def write_results(self):
        #logger = self.logger.getChild('write_results')
        
        if self._write_data and self.write_fancy_outs: 
            #session.write_summary_df()
            self.write_fancy_res()
            
            self.prof(state='write_fancy_res')
    
        if self.session._write_figs: 
            self.plot_hists() #plot histograms as directed by the 'outputs' - ses_plot tab
            self.prof(state='plot_hists')
  
    def write_fancy_res(self):
        logger = self.logger.getChild('write_results_fancy')
        logger.debug('executing')
        res_d = od() #start empty
        
        #=======================================================================
        # inputs tab
        #=======================================================================
        df_raw = self.pars_df_d['gen']
        df1 = df_raw.drop('rank',axis=1)
        
        df2 = pd.DataFrame(columns = df1.columns)

        #add extra details
        for attn in ['outpath', 'pars_filename', 'time']:
            desc = None
            if attn == 'pars_filename':
                _, v = os.path.split(self.parspath)
            elif attn == 'time':
                v = datetime.datetime.now()
                desc = 'session close time'
            else:
                v = getattr(self, attn)
                
            ser = pd.Series([attn,desc,v], index = df2.columns)
 
            df2 = df2.append(ser, ignore_index = True) #add this tot he end
            
        #add the rest to the end
        df2 = df2.append(df1, ignore_index = True)

        
        res_d['ins'] = df2
        
        
        #=======================================================================
        # summaruy rseults
        #=======================================================================
        res_d['res_summary'] = self.res_df #store thsi into the dict
        logger.debug(" on res_df %s"%str(self.res_df.shape))
        
        """
        hp_pd.v(self.res_df)
        hp_pd.v(df2)
        hp_pd.v(self.pars_df_d['gen'].drop('rank',axis=1))
        """
        
        #=======================================================================
        # output meta data
        #=======================================================================
        #make the blank frame
        outmeta_df = pd.DataFrame(index = ['sim_stats_exe', 'sel_n', 'desc'], columns = self.res_df.columns)
         
        for k, v in self.outs_od.items():
            boolcol = outmeta_df.columns == v.codename
            
            if boolcol.sum() == 0 : continue 
            
            ar = np.array([[v.sim_stats_exe, v.sel_n, v.desc]]).T
            
            outmeta_df.iloc[:,boolcol] = ar.tolist()
            
        res_d['outmeta'] = outmeta_df
        

        #=======================================================================
        # sensi results
        #=======================================================================
        if self.sensi_f: 
            'I dont like passing the d here...'
            res_d = self.get_sensi_results(res_d)
            
        #=======================================================================
        # mdex results
        #=======================================================================
        if self.output_dx_f:
            res_d['summary_dxcol'] = self.res_dxcol

        #=======================================================================
        # #write to excel
        #=======================================================================
        filetail = '%s fancy_res'%(self.tag)

        filepath = os.path.join(self.outpath, filetail)
        hp_pd.write_dfset_excel(res_d, filepath, engine='xlsxwriter', logger=self.logger)
        
        logger.debug('finished \n')
        
        return
    
    def write_bdmg_dx(self, tag, first):
        logger = self.logger.getChild('write_bdmg_dx')

        """using the builtin to_csv with an append method
        this adds the df as a new set of rows each time"""
        #get data (and add the sim to the index)
        dxcol = pd.concat([self.bdmg_dx], keys=[tag], names=['sim'])
        
        """
        view(dxcol)
        """
        
        dxcol.to_csv(self.fly_bdmg_fpath ,
                    header = first, #writ eht eheaders the ifrst time through
                    mode = 'a', #appending
                    )
        
        logger.debug('appendded bdmg_dx %s to file \n    %s'%
                     (str(dxcol.shape), self.fly_bdmg_fpath))
        
        #clear it
        self.bdmg_dx = pd.DataFrame()
        
        return
        
        

    def get_sensi_results(self, res_d):
        
        logger = self.logger.getChild('get_sensi_results')
        
        df2 = self.sensi_df.copy()
        
        #=======================================================================
        # #reforat the headers to codenae
        #=======================================================================
        l = []
        for old_col in df2.columns:
            if old_col == 'focus': l.append(old_col)
            else:
                dynpo = self.dynp_d[old_col]
                l.append(dynpo.codename)
            
        df2.columns = l
        
        df3 = df2.reindex(sorted(df2.columns), axis=1)
        
        #=======================================================================
        # #move focus to front
        #=======================================================================
        df3 = hp_pd.move_col_to_front(df3, 'focus', logger = logger)
        
        res_d['sensi_mat'] = df3
        
        #=======================================================================
        # #do the merging
        #=======================================================================
        res_df = res_d['res_summary'].copy()
        res_df = res_df.reset_index(drop=True)
                    
        merge_df = pd.merge(res_df, df3, 
                on = None,
                how = 'left',
                left_index = True,
                right_index = True, 
                left_on = None,
                right_on = None,
                sort = False,
                indicator = False)
        
        if not hp_pd.isdf(merge_df):
            raise IOError
        
        #=======================================================================
        # #get the comparison columns
        #=======================================================================
        
        l = self.delta_compare_col_nl
        logger.debug('generating %i comparison columns: %s'%(len(l), l))
        merge_df1 = merge_df.copy()
        
        for cmpre_coln in l:
            merge_df1 = self.get_sensi_base_delta(merge_df1, cmpre_coln)
            
        merge_df2 = hp_pd.move_col_to_front(merge_df1, 'focus', logger = logger)

        res_d['sensi_merge'] = merge_df2
        
        """
        res_d.keys()
        hp_pd.view_web_df(res_d['res_summary'])
        """
        
        return res_d
            
    def get_sensi_base_delta(self, df, cmpre_coln):
        
        logger = self.logger.getChild('get_sensi_base_delta')
        #=======================================================================
        # get baseline delta
        #=======================================================================
        
        boolcol = df.columns.str.contains(cmpre_coln) #get the delta column
        boolidx = df.loc[:,'focus'] == 'baseline' #get the baseline row
        
        if not boolcol.sum() == 1:
            if boolcol.sum() == 0:
                logger.warning('no \'%s\' Outputr loaded'%cmpre_coln)
                return
            else:raise IOError
        if not boolidx.sum() == 1:raise IOError
        
        
        base_ead = float(df.loc[boolidx, boolcol].values) #what we are comparing to
        
        #=======================================================================
        # add a delta column
        #=======================================================================

        #get 
        new_coln = '%s_dlt'%cmpre_coln
        new_ar = df.loc[:, boolcol].values - base_ead
        
        #set these
        df.loc[:,new_coln] = new_ar #sim minus baseline
        df1 = hp_pd.move_col_to_front(df, new_coln, logger=logger)
        logger.debug('for base_ead = %.2f made delta column\'%s\''%(base_ead, new_coln))
        #=======================================================================
        # add a relative change column 
        #=======================================================================
        """
        for nm in df1.columns:
            print nm
        type(df1.loc[:,new_coln2])
        """
        new_coln2 = '%s_rdlt'%cmpre_coln
        new_ar2 = new_ar/float(base_ead)
        
        df1.loc[:,new_coln2] =  new_ar2 #delta over baseline
        df2 = hp_pd.move_col_to_front(df1, new_coln2, logger=logger)

        
        
        return df2
    
    def wrap_up(self): #shut down and write
        if self.session._write_data:
            
            if self._prof_mem>0:
                self.resc_prof.write()
            
               
class Simulation( #a single simulation within the session
        hp_sim.Sim_simulation, 
        hp_sel.Sel_controller, 
        hp_dynp.Dynp_controller,
        hp_outs.Out_controller,
        hp_oop.Child):
    
    'todo: move this to hp_sim and make generic'

    #===========================================================================
    # object handling overrides
    #===========================================================================
    #load_data_f     = False    
    last_tstep      = None
    db_f            = True
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Simulation')
        logger.debug('start _init_')
        
        self.inherit_parent_ans = set()
        
        super(Simulation, self).__init__(*vars, **kwargs) #initilzie teh baseclass
    
        self.ind = int(self.ind)
        #=======================================================================
        # commons
        #=======================================================================
        'each simulation should have these in commmon'
        if self.sib_cnt == 0:
            self.timeline_d = self.parent.timeline_d
            
            self.udev = self.session.udev
            self.fdmg = self.session.fdmg 
        

        
        self.logger.debug('finish _init_ as %s\n'%self.name)
        
        return
        
    def run_sim(self): #run the full timeline
        """
        #=======================================================================
        # FUNCTION
        #=======================================================================
        loops through each timestep
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('run_sim')
                
        logger.info('with %i Tsteps: %s'%(len(self.timeline_d), (list(self.timeline_d.keys()))))

        #=======================================================================
        # loop and run
        #=======================================================================
        cnt = 0
        for time_str, tstep_o in self.timeline_d.items():
            #===================================================================
            # setup
            #===================================================================
            logger.info('\n %s (%i of %i) dtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdtdt'%
                        (time_str, cnt+1, len(self.timeline_d)))

            logger.debug('\n')
            self.session.hs_stamp = (tstep_o.upd_sim_lvl, cnt) #update the hierarchy/sequence stamp
            self.session.state = 'run.%s.%s'%(self.name, tstep_o.name)
            #===================================================================
            # execute
            #===================================================================
            self.init_tstep(tstep_o)  #initilize teh time step
            tstep_o.run_dt() #run the timestep
            #===================================================================
            # wrap
            #===================================================================
            self.last_tstep = tstep_o.time
            
            self.session.prof(state = '%s.run_sim.%s.end'%(self.name, time_str)) #profiling
            
            logger.debug('finished for %s \n'%time_str)
            cnt +=1
            
        logger.debug('ended on %s \n'%self.last_tstep)
        
    def init_tstep(self, tstep_o): #initilize teh tstep for this simulation
        logger = self.logger.getChild('init_tstep')
        
        logger.debug('on \'%s\''%tstep_o.name)
        self.time = tstep_o.time
        self.tstep_o = tstep_o
        
        tstep_o.inherit(self)
        'this should trigger Tstep.inherit()'
        
        if self.db_f:
            if tstep_o.parent is None:
                raise IOError
        """
        op = tstep_o.parent
        op.name
        """
        return
        
    def get_res_sim(self, wtf=None): #calculat ethe summary of outputs from the timeline
        #=======================================================================
        # defaults
        #=======================================================================        
        logger = self.logger.getChild('get_res_sim')
        if wtf is None: wtf = self.session._write_data
        
        xtra_d = od() #for collection extra outputs
        
        logger.debug('start')
        
        #outs_od = self.session.outs_od
        
        """no.. running these only on timesteps
        self.run_outputrs() #final run on the outputrs"""
        
        #=======================================================================
        # single line results
        #=======================================================================
        logger.debug('\n')
        res_ser = self.get_outputs_summary()
        
        xtra_d['res_ser'] = res_ser
        
        #=======================================================================
        # multi line results
        #=======================================================================
        if self.session.output_dx_f:
            res_dx = self.get_outputs_summary_dx()
            xtra_d['res_dx']=res_dx
            
        else: res_dx = None

        #write this to file
        if wtf: 
            logger.debug('write_full_outputs ()\n')
            self.write_full_outputs(xtra_d = xtra_d)
            
        logger.debug('finished with res_ser: \n %s'%res_ser)
        
        return res_ser, res_dx
    
class Tstep( #a timestep from teh simulation timeline
            hp_oop.Parent,
            hp_sim.Sim_o, 
            hp_sel.Sel_controller, 
            hp_outs.Out_controller, 
            hp_dynp.Dynp_controller,
            hp_oop.Child): 
    
    
    #===========================================================================
    # submodel handling
    #===========================================================================
    mod_runs_od = None #dictionary of model call sequences
    #===========================================================================
    # #pars from timeline tab
    #===========================================================================
    date = None

    run_seq_d = None #dictionary of model:run_seq_l
    
    
    #===========================================================================
    # simulation states
    #===========================================================================
    #re_reset_anl_Tstep = ['']
    'mod_runs_od: shouldnt change between simulations'
    
    sim_lvl = 2
    
    #===========================================================================
    # Object Handling
    #===========================================================================
    """
    raise_kids_f = False #tell the generic raise kids to also raise the grand kids here
    load_data_flag = False"""
        
    def __init__(self, *args, **kwargs):
        logger = mod_logger.getChild('Tstep')
        logger.debug('start _init_')
        super(Tstep, self).__init__(*args, **kwargs) #initilzie teh baseclass
        """
        NOTE on Simulation __init__
        
        everything here will only happen once
            (When teh session initilizes the timeline)
        commands in the self.inherit() will run for each Simulation
        
        self.name
        self.time
        datetime.datetime(2000)
        """
        #=======================================================================
        # attach custom atts
        #=======================================================================
        'using a string name and a sepearate column for date seems to keep things nice'
        self.dt_cnt = int(self.rank)
        self.year = int(self.date.strftime('%Y'))
        #hp_oop.clean_l_atts(self, logger = self.logger)
        #=======================================================================
        # cleaning/formatting
        #=======================================================================
        self.tstep_o    = self
        
        #=======================================================================
        # commons
        #=======================================================================
        if self.sib_cnt == 0:    
            self.timeline_df = self.session.pars_df_d['timeline']
        

        #=======================================================================
        # custom loader funcs
        #=======================================================================
        if not self.run_seq_d is None:
            try:
                d = od(eval(self.run_seq_d))
            except:
                if not isinstance(eval(self.run_seq_d), tuple):
                    logger.error('failed to evaluate a tuple from \'%s\''%self.run_seq_d)

                raise IOError
            
            self.run_seq_d = d

        else:
            self.run_seq_d = dict() #empty dic

        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f: self.check_tstep()

            
        self.logger.debug("_init_ finished \n")
        
        return
    
    def check_tstep(self):
        if not isinstance(self.date, pd.Timestamp): 
            raise IOError
        
        if self.parent is None:
            raise IOError
        
        #check the run sequence
        if not isinstance(self.run_seq_d, dict):
            raise IOError
        
        for k, v in self.run_seq_d.items():
            
            if not k in list(self.session.models_d.keys()):
                raise IOError
            
            if not isinstance(v, list):
                raise IOError
                    
    def inherit(self, parent): #inherit custom attributes from the parent

        """
        #=======================================================================
        # calls
        #=======================================================================
        this is called during session _init_
        
        as well as during Simulation.init_tstep
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        pcn = parent.__class__.__name__
       
        #=======================================================================
        # common inherits
        #=======================================================================
        #shortcut for single time step simulations
        if len(self.session.timeline_d) == 1:
            self.outpath = parent.outpath 
        else:
            self.outpath = os.path.join(parent.outpath, self.name)
        
        #=======================================================================
        # parent based
        #=======================================================================
        if pcn == 'Session':
            if not parent.state == 'init': raise IOError

            logger = self.logger.getChild('inherit')
            
        #=======================================================================
        # inheritance based on whether were actually simulating
        #=======================================================================
        elif pcn == 'Simulation':
            """note this is triggerd multiple times for the same Tstep object
            as Tstep objects are recycled between simulations"""
            self.inherit_logr(parent)
            logger = self.logger.getChild('inherit')
            logger.debug('assigning inheritance from sim \'%s\''%parent.name)
            
            self.simu_o          = parent
              
            """id rather keep the tstep out of the family 
            self.inherit_family(parent)"""
            
            self.session.tstep_o = self #tell the session what the tstep is
            self.session.year = self.year
                          
                    
        else: raise IOError
            
        logger.debug('finished from %s'%parent.name)
        
        if self.db_f:
            if self.parent is None:
                raise IOError
        
        return
    
    def run_dt(self): #loop through the model dictionary and run each one

        #=======================================================================
        # defaults
        #=======================================================================
        start = time.time()
        logger = self.logger.getChild('run_dt')
        
        #=======================================================================
        # pre runs
        #=======================================================================
        self.session.update_all(loc = self.name) #run udpates on everything in the que
        
        self.run_selectors() #update all the selectors with update_ste = 'Tstep'
        
        self.run_dynps() #apply all dynp with sample_step = 'Tstep'
            
        d = self.run_seq_d
        
        logger.debug('running %i models: %s'%(len(d), list(d.keys())))
        #=======================================================================
        # execute each assigned model
        #=======================================================================
        cnt = 1
        for model_name, run_seq_l in d.items(): #loop through 
            """this mcode_l has the flag, and the model in the first 2 entries
            Should only do one run for a string of commands
            """
            #===================================================================
            # set parameters for this run
            #===================================================================
            logger.debug("%02d executing \'%s,%s\'"%(cnt, model_name, run_seq_l))
            modloc = '%s.%s.%s'%(self.simu_o.name, self.name, model_name)
            self.session.state = '%s.run'%modloc
            
            #get model
            model = self.session.models_d[model_name]
            
            #state assignments
            self.session.model = model
            model.assign_handler(self)  
            self.session.hs_stamp = (model.upd_sim_lvl, cnt) #update the hierarchy/sequence stamp

            #===================================================================
            # pre run commands
            #===================================================================
            model.run_selectors()
            'shouldnt we execute the dynps as well for the model level?'
            
            #===================================================================
            # exceute run sequence
            #===================================================================
            seq_cnt = 1
            for seq in run_seq_l:
                logger.debug('%02d executing \'%s.%s\''%(seq_cnt, model_name, seq))
                seqloc = '%s.%s'%(modloc, seq)
                self.session.hs_stamp = (model.upd_sim_lvl +1, seq_cnt) #update the hierarchy/sequence stamp
                self.session.state = '%s.run'%seqloc
                #===============================================================
                # pre run commands
                #===============================================================
                self.session.prof(state = seqloc) #profiling
                
                self.session.update_all(loc = seqloc) #update all the objects
                
                #===============================================================
                # run by key
                #===============================================================
                #special 
                if seq == '*run':
                    model.run()
                    
                #model commands
                elif seq.startswith('*model'):
                    raise IOError #should strip this and execute it as a method
                    eval(seq)
                    
                #action run
                else:
                    acto = self.session.acts_d[seq] #retrieve the action object
                    acto.model = model #set the model
                    acto.run() #run the action
                    acto.model = None
                    
                seq_cnt += 1
                logger.debug('finished sequence \'%s\' \n'%seq)
                
            #===================================================================
            # get results
            #===================================================================
            self.session.state = 'run.%s.post'%modloc
            self.session.prof() #profiling
            model.get_results()

            #===================================================================
            # wrap up this loop piece
            #===================================================================
            self.session.state = 'run.%s.wrap'%modloc
            model.wrap_up()
            self.session.prof() #profiling
            cnt +=1
                              
        #=======================================================================
        # wrap up
        #=======================================================================\
        self.session.state = 'run.%s.%s.wrap'%(self.simu_o.name, self.name)
        self.get_res_tstep()
        
        stop = time.time()
        logger.info('finished in %.4f secs'%(stop - start))

        return
                    

    def get_res_tstep(self):
        
        #=======================================================================
        # final updating
        #=======================================================================
        """
        usually, this doesnt do anything as the last model run is fdmg
        but we want to make sure everything is up to date before outputting
        """
        self.session.update_all(loc = '%s_wrap'%(self.name)) #update all the objects
        
        'only care about these right before outputting'
        self.session.post_update()
        
        self.session.run_outputrs() #tell all the object writers to run
        
        return

class Action(    #collection of modifications of the objects in the Fdmg
                hp_sel.Sel_usr_wrap,
                hp_sim.Sim_o,
                hp_oop.Parent,
                hp_oop.Child): 
    '''
    #===========================================================================
    # DEPENDENCIES
    #===========================================================================
    Dynps
    
    inherited actions (make sure the order of hte 'actions' tab is correct
    
    '''
    #===========================================================================
    # program pars
    #===========================================================================
    
    # object handling overrides
    """
    load_data_f         = False
    raise_kids_f        = True
    raise_in_spawn_f    = False #load all the children before moving on to the next sibling"""
    'this has to be false so we can chain actions'
    
    #===========================================================================
    # user pars
    #===========================================================================
    dynp_n_l    = None #list of modifications for this
    act_n_l     = None #list of chained actions

    mark_f      = False #adds a flag to this object 
    #===========================================================================
    # calculated pars
    #===========================================================================
    acts_d = None #nested actionss
    obj_cnt = 0 #number of objects directly influenced by teh action
    
    upd_all_d = None #container of all objects this Action has been applied to. useful for get_results()
    
    upd_sim_lvl = 3
    
    dynp_wd = None 
    
    def __init__(self, *args, **kwargs):
        logger = mod_logger.getChild('Action')
        logger.debug('start _init_')
        super(Action, self).__init__(*args, **kwargs) #initilzie teh baseclass
        #=======================================================================
        #unique setup
        #=======================================================================
        'todo: convert these to sets'
        self.dynp_n_l = basic.excel_str_to_py(self.dynp_n_l, logger = self.logger)
        
        self.act_n_l = basic.excel_str_to_py(self.act_n_l, logger = self.logger)
        
        logger.debug('setup_action() \n')
        self.setup_action()
        
        """handled by outputrs
        self.reset_d.update({'obj_cnt': 0})"""
        
        #=======================================================================
        # checks
        #=======================================================================
        if self.db_f: self.check_action()

        
        logger.debug('_init_ finished \n')
        
    def check_action(self):
        """allowing now
        if self.model is None:
            raise IOError"""
            
        logger = self.logger.getChild('check_action')
        
        if not self.act_n_l is None:
            if not isinstance(self.act_n_l, list):
                raise IOError
            
        if self.pclass_n is None:
            logger.error('no pclass_n provided')
            raise IOError
        
        
    def setup_action(self, #special child raising per the mod_n_l
                     container=wdict): 
        logger = self.logger.getChild('setup_action')
        """
        self.name
        
        """

        #=======================================================================
        # get the dynamic pars by trype
        #=======================================================================
        if not self.dynp_n_l is None:
            logger.debug('setting up dynps with \'%s\''%self.dynp_n_l)
            
            #===================================================================
            # precheck
            #===================================================================
            if self.db_f:
                #check we have all the reuqested dynps
                boolar = np.invert(np.isin(
                    np.array(self.dynp_n_l), 
                    np.array(list(self.session.dynp_d.keys()))
                                           ))
                if np.any(boolar):
                    raise IOError('Action %s cant find %i requested dynps: %s'
                                  %(self.name, boolar.sum(), np.array(self.dynp_n_l)[boolar]))
                
            #===================================================================
            # get the set of requested dynps by name
            #===================================================================
            try:
                #extract with some fancy searching
                self.dynp_wd = hp_dict.subset(self.session.dynp_d, #container to pull values from
                                              self.dynp_n_l,#list of keys to search from from the dynp_d
                                             container = container, logger = logger)
            except:
                raise IOError("dict subset failed for some reason")
        else:
            logger.debug('no \'dynp_n_l\'. setting \'dynp_wd\' as an empty container')
                
    
        if self.dynp_wd is None: 
            self.dynp_wd = container()
        

        'todo: check if this dynp has been loaded '
        #=======================================================================
        # get teh child actions by type
        #=======================================================================
        
        if not self.act_n_l is None:
            logger.debug('setting up child actions with \'%s\''%self.act_n_l)
            #global pulls
            class_d = self.session.family_d['Action']
            self.acts_d = od()
            
            #loop and collect
            for actn in self.act_n_l:
                
                #upll this action object from teh class_d
                acto = hp_dict.value_by_ksearch(actn, class_d, logger = logger)
                
                if acto is None: 
                    logger.error('got None for \'%s\'. check the order??'%actn)
                    raise IOError
                
                self.acts_d[actn] = acto
                
                
            logger.debug('finished with %i sub actions collected: %s'%(len(self.acts_d), list(self.acts_d.keys())))
                
            
            
            
            """
            boolar = basic.bool_list_in_list(self.model.kids_d.keys(), self.act_n_l)
            
            if not np.all(boolar):
                logger.error('some chained actions have not been loaded yet. make sure the order is correct')
                raise IOError
            
            self.acts_d = hp_dict.subset(self.model.kids_d, self.act_n_l, 
                                         container = container, logger = logger)"""
        'have to use kids_d here because the model.acts_d hasnt finished yet'

        #=======================================================================
        # get the selector
        #=======================================================================
        if not self.sel_n is None:
            """why?
            logger.error("must provide a selector (even for Actions with a single dynp)")
            raise IOError #todo.. just pull the selector from the single dynp"""
        
            self.sel_o = weakref.proxy(self.session.sels_d[self.sel_n]) #attach your selector
        else:
            self.sel_o = None
        #=======================================================================
        # wrap up
        #=======================================================================
        logger.debug('finished\n')
        
    def run(self, actk_d = None , container=wdict): #execute the chained Actions and all my dynp
        'models and submodels must have the simple run name'
        
        """
        #===========================================================================
        # CALLS
        #===========================================================================

        
        """
        logger = self.logger.getChild('run(%s)'%self.get_id())
        #=======================================================================
        # setup
        #=======================================================================

        upd_all_s = set() #set of gids        
        self.run_cnt += 1
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            pass
        
        #=======================================================================
        # defaults
        #=======================================================================
        if actk_d is None: k = 'empty'
        else: k = list(actk_d.keys())

        logger.debug('executing with\n    actk_d: %s \n    acts_d: %s \n    dynp_wd.keys(): %s'%
                     (k, self.acts_d, list(self.dynp_wd.keys())))
        
        #=======================================================================
        # build set
        #=======================================================================
        
        actk_d1 = self.make_pick(big_d = actk_d)
        'I guess Actions make fresh picks each time?'
        #shortcut
        if len(actk_d1) == 0: 
            logger.debug("no objects passed by selector. doing nothing")
            return container()
        
        
        #=======================================================================
        # run the chained actions
        #=======================================================================
        if not self.acts_d is None:
            sub_act_cnt = len(self.acts_d)
            
            #run the nested actions agaisnt your set
            'workaround for wdict order limitation' 
            for act_n in self.act_n_l:
                act_o = self.acts_d[act_n] #retrieve the action

                logger.debug('on my pick (%i) running nested act_n: \'%s\' and their dynp_wd: %s \n '
                             %(len(actk_d1), act_n, list(act_o.dynp_wd.keys())))
                
                upd_s = act_o.run(actk_d = actk_d1) #use my subset when you run
                
                #warp up
                upd_all_s.update(upd_s)
                logger.debug('finished nested act_n \'%s\' with %i updates'%(act_n, len(upd_s)))

        else: sub_act_cnt = 0
            
        #=======================================================================
        # loop through each mod/dynp associated with this action and set the new value
        #=======================================================================
        if len(self.dynp_wd) > 0:
            logger.debug('running my dynps: %s'%list(self.dynp_wd.keys()))
            
            'workaround for wdict order limitation'            
            for dynp_n in self.dynp_n_l:
                dynp_o = self.dynp_wd[dynp_n] #get this dynp

                logger.debug('running dynp \'%s\' with \'%s\' on my set (%i) of \'%s\' \n'
                             %(dynp_n, dynp_o.value_assign_str, len(actk_d1), list(actk_d1.values())[0].__class__.__name__))
                #===================================================================
                # set the values on the intersection of the two
                #===================================================================         
                upd_s = dynp_o.run_dynp(big_d = actk_d1)
                
                upd_all_s.update(upd_s) #add these items to the list

        #=======================================================================
        # wrap up
        #=======================================================================   
        if self.mark_f: self.mark_set(actk_d1)
        
        self.get_results(upd_all_s)
             
        logger.info('changed %i objects with %i sub-Actions and %i prime-dynps: %s'
                    %(len(upd_all_s), sub_act_cnt, len(list(self.dynp_wd.keys())),list(self.dynp_wd.keys())))
        
        
        return upd_all_s
        
    def mark_set(self, d): #add an entry to the parents childmeta_df marking that this Action has been applied
        logger = self.logger.getChild('mark_set')
        #=======================================================================
        # setup
        #=======================================================================
        obj1 = list(d.values())[0] #just take the first
        df = obj1.parent.childmeta_df.copy()
        
        logger.debug('on %i objects with childmeta_df %s'%(len(d), str(df.shape)))
        
        #find the attributes column
        if not self.name in df.columns.values.tolist():
            df[self.name] = np.nan #add an empty column
            logger.debug('added a column \'%s\' to the \'%s\'s childmeta_df'%(self.name, obj1.parent.name))
        
        boolcol = df.columns == self.name
        
        new_val = self.model.tstep_o.name
        #=======================================================================
        # update the df
        #=======================================================================
        for obj_n, obj in d.items():
            
            boolidx = df.loc[:,'name'] == obj.name #find yourself
            
            df.loc[boolidx, boolcol] =  new_val#set the timestamp

            logger.debug('marked object \'%s\'s childmeta_df entry with \'%s\''%(obj_n, new_val))
            
        #=======================================================================
        # update the parents frame
        #=======================================================================
        obj1.parent.childmeta_df = df
        logger.debug('finished marking %i objects and udpating the parents frame'%len(d))
    
    def get_results(self, upd_all_s):

        s = self.session.outpars_d[self.__class__.__name__]
        
        if 'obj_cnt' in s:
            'needs to be cumulative as some actions are chained'
            self.obj_cnt = self.obj_cnt =+ len(upd_all_s)
            
        return
        


       
            

        
        

                
