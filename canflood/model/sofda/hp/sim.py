'''
Created on Jun 15, 2018

@author: cef

basic simulation programming
'''
#===============================================================================
# STYLES AND STANDARDS -------------------------------------------------------
#===============================================================================
'''
#===========================================================================
# special top-level objects PARENT/POINTERS
#===========================================================================
*Session
    *Simulation
        *Tstep
            Model
            
* represent the 3 main phases of the model where we trigger 'top down comands'
    see 'Run Loops' note below


#===============================================================================
# Run Loops 
#===============================================================================
model runs should be triggered at the highest level.
these should start a cascade of runs to each relevant child Sim_o

these should all be called 'run' for easy identification/standardization
     often times the self.run() will just have a link to one other command
     
only the commands necessary to execute the run (and trigger the children to run) should be included int eh command
    any output handling, initilization, or setting up for subsequent runs, should be in separate functions
    the parent should call these separate child functions within its own run
    
    
EXAMPLE

Model.run()
    
    #setup the run
    
    #start the childs run
    for child in my_children:
        child.recompile 

        *child.inherit(self)
        
        *child.set_smpval_dp_all() #set all teh dynamic parameters for thsi level
        
        *child.update_selectors() #update all the selectors for this level
        
        child.run()
        
        *child.get_results() #generally just store the attributes
        
        *child.wrap_up() 
        
    #log the results and NOTHING ELSE
    
NOTE: the session needs to do all setup within its own run commaned
* These are exclusive to the 3 top level handlers (Session, Simulation, Tstep)
    
#===============================================================================
# Key Functions
#===============================================================================
__init__
inherit:    see below
recompile:    see below
run:        see above
        

'''
#===============================================================================
# RESTART, REINIT, INHERIT, RECOMPILE ------------------------------------------------
#===============================================================================
'''

naturally, everything was first scripted to run from a cold start (initilize)
    loads parameters/inputs from file system
    saves outputs to file system
    loops through and builds every elemennt

however, now that a session has 10,000x simulations each with 50x timesteps
    performance could be improved by limiting some fo the tasks between each
    ie carrying some information between steps
    choosing selectively what to respawn/recreate 
    
    
#===============================================================================
# Recompile -- Updating per simulation
#===============================================================================
OBJECTIVE: recompile each object so it is ready for the next simulation (no memory)
    withouth aving to fully reiniilzie the object
    
ACTIONS:
    Sim_o's
        reset key attributes (re_reset_anl) to None
    Model_o's
        
    


calls:

Session.run_all()
    Simulation.recompile():
        Tstep.recompile(): deletes key attributes (from teh previous simulation)
        Fdmg.recompile(): 
            delete key atts
            recompile_kids(): loops through all the children and triggers their recompile()
            
        Udev.recompile():
            self.recompile_genr()
            self.recompile_kids()  #trigger recompile on all the children
        
NOTE: This triggers a cascade of recompilation down the full hierarchy
i.e. erases memory between simulations ('resets' the simulation for the next run)

CUSTOM RECOMPILE()
user must go object by object and define custom recompiles() for the key objects with memory
    generally, this just involves 
        deleting key attributes
        re-running setup functions
        in some cases, rebuilding children
        
CONCERNS:
I'm a bit worried this will amake it difficult to track what is updating and what is not between runs
        

        
#===============================================================================
# inherit -- Updates per timestep (and __init__)
#===============================================================================
mostly just assigns some key attributes (parent, model, etc.) to the new reference


calls:                        

Basic_o.__init__: initilize teh base class
    inherit(): 
        generic_inherit(): 
            inherit_sim():
                set_sample_value()
        

Simulation.run_timeline()
    Tstep.inherit(Simulation)
        Models.inherit(Tstep)
            self.inherit_model(parent)
                self.generic_inherit(parent) #reassign all my vars
        
        
NOTE: This does not trigger a cascade as Recompile does
    did this because there needs to be memory from time step to timestep
    (also saves resources)
    therefore, dynamic attributes should be called from one of the 5 special top-level objects
    


'''
#===============================================================================
# OUTPUTS --------------------------------------------------------------------
#===============================================================================
'see hp_outs'
#===============================================================================
# DYNAMIC PARAMETERS --------------------------------------------------------------------
#===============================================================================
'see hp_dynp'

# IMPORTS ----------------------------------------------------------------------
import logging
import os, sys, copy, re, gc, weakref
from collections import OrderedDict


import pandas as pd
import numpy as np
#import scipy.stats

import model.sofda.hp.basic as hp_basic
#import model.sofda.hp.pd as hp_pd
#import model.sofda.hp.dynp as hp_dynp
import model.sofda.hp.oop as hp_oop
#import model.sofda.hp.outs as hp_outs


mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')


class Sim_wrap(object): #worker for simulation handing
    """
    #===========================================================================
    # USE
    #===========================================================================
    For tasks that involve changing proeprties and executing functions iteratively
    supports outputs at different steps
    
    #===========================================================================
    # 5 special top-level objects PARENT/POINTERS
    #===========================================================================
    This uses three special parents to point to
    
    generic parents
        session: ctop of the hierarchy
        parent: whatever the object right above me is in the hierarchy
        
    simulation special
        model: the main bundler that gets passed from tstep to tstep
        
        simu_o: the simulation object that runs all the timesteps 
        tstep_o: executes commands for one timestep 
        
    to save resources, Im only having the model reinherit from the tstep each time
    """
    #===========================================================================
    # program pars
    #===========================================================================
    reset_f     = True #this object should run the reset routine
    sim_lvl     = 4 #phase of the simulation on which this object is relevant. mostly for outputs

    perm_f = True #this is a permanent object
    
    #===========================================================================
    # user provided pars
    #===========================================================================
    sensi_f     = False
    mind = ''
    outpath = ''
    #===========================================================================
    # calculated pars
    #===========================================================================
    model       = None #model object
    
    #simulation state
    tstep_o     = None #Tstep objecty
    simu_o      = None #reference to the simualtion object
    time        = None #datetime object indicating the current simulated time
    dt_cnt      = None #timestep count for this object (starting from 0) 
    
    """ moved to dynp.Dynp_wrap
    upd_f   = False #flag indicating whether the object needs to be updated or not"""
    reset_d = None # d[att_name] = original value: attributes to reset
    reset_func_od = None #od of commands to run during reset
    
    #===========================================================================
    # data holders  
    #===========================================================================
    run_cnt     = 0 #how many times this object has been run triggered
    
    #===========================================================================
    # Updates
    #===========================================================================
    'not sure everyone needs this...'
    upd_sim_lvl = 1 #default to update for each simulation


    def __init__(self, 
                 *vars, **kwargs): #these are need to pass onto the Child
        
        logger = mod_logger.getChild('Sim_wrap')
        logger.debug('start _init_ as \'%s\''%self.__class__.__name__)
        #=======================================================================
        # pre base init
        #=======================================================================
        """ using session values
        if self.inherit_parent_ans is None: self.inherit_parent_ans = set()
        self.inherit_parent_ans.update(['sensi_f'])"""
        
        super(Sim_wrap, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        #=======================================================================
        # common setup
        #=======================================================================
        
        #reset_d
        'making a hard set here to clear any duplicates from children.. thsi means we need to be at the bottom'
        self.reset_d = dict()
        self.reset_d.update({'outpath':None, 'run_cnt':0, 'dt_cnt':None})
        
        self.reset_func_od = OrderedDict()
        
        #=======================================================================
        # unique setup
        #=======================================================================
        if self.sib_cnt == 0:
            
            if self.db_f:
                if not isinstance(self.reset_d, dict):
                    raise IOError

        logger.debug("finishe __init__ on \'%s\' as  \'%s\'"%(self.name, self.__class__.__name__))
        return
        
    def set_upd_sim_lvl(self, max = 2): #set/format the sim_lvl and report
        logger = self.logger.getChild('set_upd_sim_lvl')
        
        #=======================================================================
        # type detection
        #=======================================================================
        #numeric
        if hp_basic.isnum(self.upd_sim_lvl): 
            self.upd_sim_lvl = int(self.upd_sim_lvl)
            
            if self.upd_sim_lvl == 0:
                logger.debug('upd_sim_lvl == 0. STATIC object ')
            elif self.upd_sim_lvl >max: 
                logger.error('maximum allowed upd_sim_lvl = 2')
                raise IOError
            
            else: logger.debug('set as PERIODIC with upd_sim_lvl = %i'%self.upd_sim_lvl)
            
        #None
        elif re.search('none', self.upd_sim_lvl, re.IGNORECASE): 
            logger.debug('set as EXPLICIT with upd_sim_lvl = none')
            self.upd_sim_lvl = 'none'
            
        else:
            logger.error('got unexpected type for upd_sim_lvl: %s'%type(self.upd_sim_lvl))
            raise IOError
        
    def get_dt_n(self, kwd): #intelligent timeline setting
        logger = self.logger.getChild('set_dt')
        #=======================================================================
        # setup
        #=======================================================================
        if not isinstance(kwd, str): raise IOError
        
        df_raw = self.session.pars_df_d['timeline']
        
        df = df_raw.sort_values('date')
        
        dt_l = df.loc[:,'name'].values.tolist() #get list of names
        
        kwd = str(kwd) #format the search keword
        
        #=======================================================================
        # logic pull
        #=======================================================================
        if kwd in dt_l:
            logger.debug('passed kwd \'%s\' in timeline'%kwd)
            return kwd
        
        elif kwd.startswith('*'):
            
            if re.search('first', kwd, re.IGNORECASE): dtn = dt_l[0]
            
            elif re.search('last', kwd, re.IGNORECASE): dtn = dt_l[-1]

            else: raise IOError
            
        else:
            logger.error('passed kwd \'%s\' not found in the timeline'%kwd)
            raise IOError
        
        logger.debug('found dt = \'%s\' from kwd \'%s\''%(dtn, kwd))
        
        return dtn
                

    def get_results(self): #placeholder

        'disabled outputting here. its now handled by the session'
        
        'moved outpath updating to the hp_outs.Outputr_base.store_all()'
        #self.outpath = self.model.outpath 
        return
        
    
    def reset_simo(self): #reset attribute values to those found in teh reset_d
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        reset_d: d['att_name'] = base_value.
            dictionary of base values to restore
            
        self.session.reset_d.keys()
        """
        'should be called at the start of each simulation (other than the first)'
        logger = self.logger.getChild('reset_simo')
        #=======================================================================
        # basic reset from dictionary
        #=======================================================================
        logger.debug('on %i attributes in reset_d: %s'%(len(self.reset_d), list(self.reset_d.keys())))
        cnt = 0
        for attn, attv in self.reset_d.items():
            #===================================================================
            # print out
            #===================================================================
            if self.db_f:
                if (hasattr(attv, 'shape')) & (not isinstance(attv, float)): 
                    logger.debug('on \'%s\' with og val shape %s'%(attn, str(attv.shape)))
                else:
                    logger.debug('on \'%s\' with og val = \'%s\''%(attn, attv)) 
                    
                if not hasattr(self, attn):  
                    logger.warning('I dont have \'%s\' attribute. skipping'%attn)
                    raise IOError    
            

            new_attv = copy.copy(attv)
            'deep copy doesnt work for child objects'
            setattr(self, attn, new_attv)

            cnt +=1

                
        logger.debug('finished with %i attributes reset'%cnt)
        
        'we are not deleting the reset_d. letting it roll over from sim to sim'
        
        #=======================================================================
        # reset commands
        #=======================================================================
        if len(self.reset_func_od) > 0:
            logger.debug('running %i reseter functions'%len(self.reset_func_od))
            for func, caller in self.reset_func_od.items():
                logger.debug('running \'%s\' queued by \'%s\''%(func, caller))
                func()
            
            logger.debug("finihsed")
            
        logger.debug('finished \n')
        return  
        
          
    def get_id(self): #return an id string
        
        return self.session.state
        if self.session.state == 'init':
            str = 'init'
        else:
            try:
                mod = self.session.model
                str = '%s.%s.%s'%(self.model.simu_o.name, self.model.tstep_o.name, self.model.state)
            except:
                str = '?'
        
        return str

    
class Sim_o(Sim_wrap): #standalone sim object
    """
    dont want Sim_model and Sim_o to share all attributes/inits
    """
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Sim_o') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__ on \"%s\''%self.__class__.__name__)
        
        if self.inherit_parent_ans is None: self.inherit_parent_ans = set()
        self.inherit_parent_ans.update(['model'])
        
        super(Sim_o, self).__init__(*vars, **kwargs) #initilzie teh baseclass
        
        
        logger.debug("finish __init__ on %s"%self.__class__.__name__)
           
class Sim_model(Sim_wrap):#, hp_outs.Out_controller):#, hp_dynp.Dynp_basic): #wrapper for model instances3
    """
    special object for the top level simulation objects
    """
    #===========================================================================
    # program pars
    #===========================================================================
    try_inherit_anl = None
    sim_lvl = 3 #phase of the simulation on which this object is relevant. mostly for outputs
    
    #===========================================================================
    # calculation pars
    #===========================================================================
    last_tstep = None #attribute to mark the last timestep

    
    year = 0
    
    #===========================================================================
    # user provided pars
    #===========================================================================
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Sim_model') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__ as \"%s\''%self.__class__.__name__)
        
        #=======================================================================
        # base init
        #=======================================================================
        super(Sim_model, self).__init__(*vars, **kwargs) #initilzie teh baseclass
        
        if not self.parent.__class__.__name__ == 'Session': 
            raise IOError
        
        self.model = weakref.proxy(self)
        
        """todo: make a separate tab for this
        
        20190504: This is super gross
        much better to specify a separate tab (similar to the sessions tab) 
            from which all pars can be loaded/passed to this child object
        
        """
        
        logger.debug('attempt to pull attributes from the Session')
        #check we have all the attributes we want to inherit
        atnar = np.array(list(self.try_inherit_anl))
        boolar = np.invert(np.isin(atnar, 
                                   np.array(dir(self))
                                   ))
        if np.any(boolar):
            raise IOError('object \"%s\' is missing %i attributes it wants to inherit: \n %s'%
                          (self.__class__.__name__, boolar.sum(), atnar[boolar]))

        for attn in self.try_inherit_anl:
            _ = hp_oop.mirror_att(self, attn, logger = logger)
        
        logger.debug("finish __init__ \n")
        
        return
        
    def assign_handler(self, handler): #quasi inheritance
        logger = self.logger.getChild('assign_handler')
        
        hcn = handler.__class__.__name__
        
        logger.debug('from \'%s\' handler'%hcn)
        
        if hcn == 'Tstep':
            self.tstep_o        = handler
            
            for attn in ['simu_o', 'time', 'dt_cnt', 'year', 'outpath']:
                new_val = getattr(handler, attn)
                setattr(self, attn, new_val)
                                        
            self.inherit_logr(handler)
            
    
        elif hcn == 'Simulation': raise IOError #not setup for this
        else: raise IOError
     
class Sim_simulation(Sim_o):#wrapper for simulation objects
    
    #===========================================================================
    # program pars
    #===========================================================================
    write_sim_res_f = True #flag whether to write results of each simulation
    sim_lvl = 1 #phase of the simulation on which this object is relevant. mostly for outputs
    
    reset_f = False #this object should run the reset routine
    
    #===========================================================================
    # calcualted pars
    #===========================================================================
    ind = None #indicies for thsi sim
    
    def __init__(self, *args, **kwargs):
        logger = mod_logger.getChild('Sim_simulation')
        logger.debug('start _init_')
        
        super(Sim_simulation, self).__init__(*args, **kwargs) #initilzie teh baseclass
        
        #=======================================================================
        # common setup
        #=======================================================================

        #=======================================================================
        # unique setup
        #=======================================================================
        #outpath
        self.outpath = os.path.join(self.parent.outpath, self.name)
        
        if self.session._write_data:
            """ better to make on demand...
            if not os.path.exists(self.outpath): 
                os.makedirs(self.outpath)"""
                
            if self.session.log_separate_f: 
                self.build_custom_logger(logname = self.name)
        
        self.simu_o   = weakref.proxy(self)

        self.logger.debug("__init__ finished \n")
        

class Sim_session( #wrapper for Session instances, top level session handler for a simulation objects
        Sim_wrap):

    #===========================================================================
    # program pars
    #===========================================================================
    
    # reseting
    reset_f = False #this object should run the reset routine
    
    sim_lvl = 0 #phase of the simulation on which this object is relevant. mostly for outputs
    
    log_separate_f = False #flag indicating whether a separate logger should be created for each simulation
    
    #===========================================================================
    # calculation pars
    #===========================================================================
    year0 = 2000 #default first year
    'are we using this?'
    
    
    year = 0 #placeholder
    sims_od = OrderedDict() #collection os simulations
    mod_run_nl = [] #contain a list of models we are running
    state = 'init'
    run_cnt = 1 #number of simulations to run
    
    hs_stamp = (0,0) #tuple to tag the hierarchy/runs tate of the session
    'this is useful to for objects to compare previous states tot he current one'
    
    #===========================================================================
    # user provided pars
    #===========================================================================
    write_sim_res_f = True
    output_dx_f = False #
    

    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Sim_session') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
        #=======================================================================
        # empty containers
        #=======================================================================
        'as there is only one session we dont need to worry about this'
        
        #initilzie teh first baseclass
        super(Sim_session, self).__init__(*vars, **kwargs) 
                
        #=======================================================================
        # post child init
        #=======================================================================
        
        """
        for k, v in kwargs.iteritems(): 
            print k
        """
         
                
        logger.debug('finished __init__ \n')
        
    def get_sim_metadf(self, sim_cnt = None): #build a dummy frame for the sims
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_sim_metadf')
        if sim_cnt is None: sim_cnt = self.run_cnt
        
        
        #=======================================================================
        # build frame
        #=======================================================================
        logger.debug('for %i sims'%sim_cnt)
        df = pd.DataFrame(index = list(range(0, int(sim_cnt), 1)),
                          columns = ['name', 'ind']) #get dummy blank
        
        df['ind'] = df.index #build the indicies as a copy of th eindex
        #=======================================================================
        # loop and fill name
        #=======================================================================
        logger.debug('looping and building name on %s'%str(df.shape))
        for index, row in df.iterrows():
            df.loc[index, 'name'] = 'sim_%i'%row['ind']
            
        return df

    def reset_all(self): #reset all objects in the family to their base state
        
        logger = self.logger.getChild('reset_all')
        
        logger.debug('on %i books in the family library: %s'%(len(self.family_d), list(self.family_d.keys())))
        
        cnt =0
        for cn, book in self.family_d.items():
            logger.debug('on \'%s\' book with %i objects~~~~~~~~~~~~~~~~~~~~~~~~~~~~~'%(cn, len(book)))
            
            ocnt = 0
            for gid, obj in book.items():
                if hasattr(obj, 'reset_simo'):
                    if (obj.reset_f) &(obj.upd_sim_lvl !=0):
                        
                        if obj.perm_f: #permanent object. reset me
                            logger.debug('perm_f = TRUE. reseting \'%s.%s\''%(obj.__class__.__name__, obj.gid))
                            obj.reset_simo()
                            ocnt += 1
                        else:
                            logger.debug('perm_f = FALSE. skipping all \'%s\''%(cn))
                            break
                            """handling child death with parents now
                            this makes swapping out new kids easier
                            self.kill_obj(obj)"""
                            

                            
                    else: logger.debug('reset_f = %s and upd_sim_lvl = %s. skipping'%(obj.reset_f, obj.upd_sim_lvl))
                    
                else:
                    logger.debug('this object class has no reset. skipping all')
                    break
            
            logger.debug('reset %i \'%s\' objects \n'%(ocnt, cn))
            cnt += ocnt
        logger.debug('reset a total of %i objects'%cnt)
        
        return

    def delete_sim(self, sim_id): #fully clear/delete a sim
        logger = self.logger.getChild('delete_sim')
        
        logger.debug('deleting sim_ind \"%s\''%sim_id)
        
        old_sim = self.sims_od[sim_id]
        
        del self.sims_od[sim_id] #clear the reference                
         
        #=======================================================================
        # flear from teh familyi
        #=======================================================================
        if not self.kill_obj(old_sim):
            if self.db_f:
                raise IOError
            
        #=======================================================================
        # clean up
        #=======================================================================
        #gc.collect() #force garbage collection
        
        logger.debug('finished \n')
        
    
        
    

                     
        
class Sim_handler(Sim_o): #wrapper with extra functions for simulation handelers
    """
    TODO: Ipelment this
    
    Users: Selector, Dynps, Outputtrs
    
    These are objects taht sit outside of the main simulation
        dont belong to a model
    """
    
    def __init__(self):
        return
    

            

