'''
Created on Jun 20, 2018

@author: cef
'''

#===============================================================================
#DYNAMIC PARAMETERS ---------------------------------------------------------
#===============================================================================
"""
This allows stochastic and dynamic overriding of object attributes

#===============================================================================
# PHILOSOPHY
#===============================================================================
Top Down:
    let the parent loop through the dynp_d and run set_sample_value()
    provide each dynp with a classo_d (dict of class objects flagged for dynamic parameters)
    
    I like this better as it gives more explicit control as to when the newp arameters are set
        ensures we don't have some rogue object resting its prameters mid simulation
    also makes setting up the sensitivy run easier?
    
    
    ALSO! we can combine this with the udev mods

Bottom Down:
    let each object run through its own collection of dynps and set_sample_value()
    2018 06 20: originally coded this way with build_master_dp_d()

#===============================================================================
# key workers
#===============================================================================
Dynp_controller: inherited by the Session
    build_master_dp_d():
Kid: wrapper for objects on which dynamic parameters will apply 
"""   
#===============================================================================
# CHANGING PARAMETER VALUES --------------------------------------------------------------------
#===============================================================================
"""
#===============================================================================
# SETUP
#===============================================================================
Session.raise_dynps()
    raises all the dynps into dynp_d from the 'dynp' pars.xls tab
    
        
#===============================================================================
# Application of the parameter
#===============================================================================
PERIODIC: upd_sim_lvl = int
    (Session, Simulation, or Tstep).run_dynps(): called at the beginning of the respective run loops 
        dynp_o.run_dynp()

    
EXPLICIT: upd_sim_lvl = None
    Tstep.run()
        udev.run()
            udev.Action.run(): 
                dynp_o.run_dynp()
                
"""
#===============================================================================
#UPDATES ----------------------------------------------------------------
# #=============================================================================== 
"""
storing original values: old values are stored into the reset_d (see hp_sim.Sim_o.reste_genr())

update_obj_f = TRUE
    secondary update commands: custom commands are qued on the object based on the handle pars (dynp_hnd_d) 
    (see dynp.Kid.handle_upd)

obj.upd_df = TRUE
    update parents childmetad_df

"""

#===============================================================================
# # IMPORTS --------------------------------------------------------------------
#===============================================================================
import os, sys, copy, random, logging, weakref, time, re
#re
from collections import OrderedDict

from weakref import WeakValueDictionary as wdict

import pandas as pd
import numpy as np
import scipy.stats  #need this for exec calls

import model.sofda.hp.pd as hp_pd 
import model.sofda.hp.basic as hp_basic
import model.sofda.hp.oop as hp_oop
import model.sofda.hp.sim as hp_sim
import model.sofda.hp.sel as hp_sel

mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')

           
 

'this has to be basic because hp_sim needs to inherit the dynps'
class Dynamic_par(hp_sel.Sel_usr_wrap,
                  hp_sim.Sim_o,
                  hp_oop.Child): #generic object fo handling stochastic assignemtns on a single parametre
    #===========================================================================
    # program vars
    #===========================================================================
    two_par_dists_nl = ['norm', 'logistic'] #recognized scipy sdistribution
    three_par_dists_nl = ['lognorm']
    
    """
    # simulation overrides
    run_upd_f       = False #dummy to get the update handle to work properly"""
             
    #===========================================================================
    # user provided
    #===========================================================================
    #pclass_n    = None #applicable class name for this dynamic parameter
    #sel_n           = None #name of selector
    dist_pars_l     = None #list of distribution parameters
    correlate_an    = None #correlated object attribute name
    att_name        = 'none'
    
    change_type     = None #control how the dynp changes teh value
    min             = None
    max             = None
    
    freeze_att_f    = False #flag to freeze this attribute for the full sim whenever modified by this dynp
    
    #sensitivty analysis pars
    sensi1          = None #sensi toggle value 
    sensi2          = None
    sensi3          = None
    """ moved to the handles file and the dyno
    upd_df          = False #control whether your object needs to update its parent.childmeta_df"""
    
    #plotting pars
    plot_f          = False
    color           = 'blue'
    
    value_assign_str    = None
    
    stoch_f = True #flag to override stochastity on this par
    
    write_hist_f = False
    
    #===========================================================================
    # calculated pars
    #===========================================================================
    #sensitivty analyss
    sensi_vals      = None #list of value_assign_str to sue for sensitivy analysis

    value   = None #spawned value for this
    val_f   = None #function for spawning the value
    
    
    contained = False #whether to apply min/max values to numeric dynps
    
    skip_f = False #flag to skip this dynp during run loops
    obj_cnt = 0 #number of objects affected by this dyno per sim
    
    upd_d = None #container for objects updated
    #===========================================================================
    # data containers
    #===========================================================================


        
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dynamic_par') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        #=======================================================================
        # inherit special attributes 
        #=======================================================================
        
        #initilzie teh baseclass
        super(Dynamic_par, self).__init__(*vars, **kwargs) 
                
        #=======================================================================
        # common attributes
        #=======================================================================
        if self.sib_cnt == 0:
            self.outpath = os.path.join(self.outpath, 'dynps')
            
        #=======================================================================
        # unique attributes
        #=======================================================================
        #list of calibration parametrs for statistical distributions
        if not self.dist_pars_l is None: #format toa  list
            self.dist_pars_l = hp_basic.str_to_list(self.dist_pars_l, new_type=float,logger=self.logger)
            
        #strip leading/trailing whitespace
        self.att_name       = self.att_name.strip() 
        
        
        #codenae
        self.codename = str('%s-%s-%s'%(str(self.rank).zfill(2), self.name, self.pclass_n))
        if not self.att_name is None: self.codename = self.codename + '-%s'%self.att_name
        logger.debug('set codename \'%s\''%self.codename)

        
        self.plot_f = bool(self.plot_f)     
        
        self.freeze_att_f = bool(self.freeze_att_f)   
        
        self.reset_d.update({'obj_cnt':0, 'upd_d':None})    
        #=======================================================================
        # custom setup funcs
        #=======================================================================
        
        
        #upd_sim_lvl
        self.set_upd_sim_lvl()
        logger.debug('\n')
        #calibrate your value function
        self.calibrate_valf() #for normal simulations
        logger.debug('\n')
        
        #for senstivity analysis
        if self.session.sensi_f:    
            self.set_sensi_vals() 
            logger.debug('\n')
         

            
        #collec the objects which you apply to
        #self.get_selection() 
        if not self.upd_sim_lvl == 'none':
            logger.debug("for PERIODIC (%i), make_pick() \n"%self.upd_sim_lvl)
            self.pick_d = self.make_pick()
        
        """Class default is 'none'. disables updates when this input is blank. assumes some custom function"""
        #if self.att_name == 'none': self.update_obj_f = False
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not self.sel_o is None:
                if not self.sel_o.upd_sim_lvl == 'none':
                    logger.error('dynps only allow explicit selectors. fix \'%s\''%self.sel_o.name)
                    raise IOError
                
            
            self.hist_df = pd.DataFrame()
            
            self.reset_d['hist_df'] = self.hist_df.copy()

        logger.debug('__init__ finished \n')
        return

    def calibrate_valf(self): #calibrate value function generator
        """"should only be run once during __init__
        
        assign the val_f to be a callable functio nof a standard form based on the value_assign_str
        
        #=======================================================================
        # NOTE
        #=======================================================================
        all of these callable value functions are run on the passed object
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('calibrate_valf')
        
        vstr = self.value_assign_str
        self.skip_f = False #need to reset this
        
        logger.debug("on value_assign_str = \'%s\'"%vstr)
        
        #=======================================================================
        # constant value assignment
        #=======================================================================
        if hp_basic.isnum(vstr): #numerics
            'this will pick numbers posing as strings as well'
            
            #check for boolean formatting
            if self.att_name.endswith('_f'):
                value = bool(vstr)
            else:
                value = float(vstr) #just use the number
                
            val_f = self.valf_constant
            
            msg = 'calibrated as a constant %.2f'%value
            
        elif isinstance(vstr, str): #everything else (String type)
            
            vstr_py = vstr.replace(" ", "") #drop all the whitespace
            vstr_py = hp_basic.excel_str_to_py(vstr_py, logger = logger) #make pythonic
            
            #=======================================================================
            # boolean
            #=======================================================================
            if isinstance(vstr_py, bool):
                value = vstr_py
                val_f = self.valf_constant  
                msg = 'as a boolean %s'%value
                
            #===================================================================
            # string calls
            #===================================================================
            elif isinstance(vstr_py, str): #still a string
                
                #special calls
                if vstr_py.startswith('*'):
                    
                    if vstr_py == '*skip':
                        value = '*skip'
                        val_f = self.valf_skip
                        self.skip_f = True #set the skip flag. see run_dynp()
                        msg = 'special call \'%s\''%vstr_py
                        
                    else: raise IOError
                    
                #simple funcs
                elif vstr_py.startswith('new_val='):
                    val_f = self.valf_simpl
                    msg = 'simple function \'%s\''%vstr_py
                    
                    #get base value
                    if hp_basic.isnum(self.min): 
                        value = self.min
                    else: 
                        value = vstr_py
                    
                #custom callabe class functions
                elif vstr_py.startswith('obj.'):
                    'TODO: check if this is callable'
                    val_f = self.valf_set_exec
                    value = vstr_py
                    
                    msg = 'custom function %s'%val_f
                    
                #scipy functions    
                elif vstr_py.startswith('scipy'):
                    val_f, dname, value = self.calibrate_scipy(vstr_py)
                    msg = 'scipy function %s'%dname
                    #value = 'scipy'
                    
                    # static override
                    if (not self.session.glbl_stoch_f) or (not self.stoch_f): 
                        logger.warning("Overriding scipy dynp to constant (static) with value \'%s\'"%self.value)
                        val_f = self.valf_constant

                elif vstr_py.startswith('sklearn'):
                    'couldnt get this to work'
                    raise IOError #TODO this
                
                else:
                    value = vstr_py
                    val_f = self.valf_constant
                    msg = 'constant string \'%s\''%value
                    
            elif vstr_py is None:
                value = 'none'
                val_f = self.valf_constant
                msg = 'none string string \'%s\''%value
                
            
            else: #only setup for single values here
                logger.error('got unexpected type for value_assign_str: %s'%type(vstr_py))
                raise IOError
            
            """dont seem to be using this anymore
        elif vstr is None:
            'need this for passing none to some attributes'
            val_f = self.valf_constant
            value = 'none'
            
            msg = 'none string'"""
                
        else:
            logger.error('got unexpected type for value_assign_str: %s'%type(vstr))
            raise IOError
        

        
        #=======================================================================
        # wrap up
        #=======================================================================
        logger.debug("finished for pclass_n \'%s\' and att_name \'%s\' with code \'%s\' \n"
                     %(self.pclass_n, self.att_name, msg))
        

        #attach these values
        self.val_f = val_f #use the logic from above
        self.value = value
        
        return msg
        
    def calibrate_scipy(self, vstr):
        """TESTING
        rand_samp = self.rv.rvs() #get a random sample from teh scipy function
        """
        
        #=======================================================================
        # setup
        #=======================================================================
        logger = self.logger.getChild('calibrate_scipy')
        base_val = None #placeholder for the base value (for sensitivity analysis)
                
        #=======================================================================
        # setup the random variable distribution
        #=======================================================================
        rv = eval(vstr) #evalute the string
        
        """ not sure how to nicely pass the parameters list"""
        #=======================================================================
        # # freeze the rv
        #=======================================================================
        #extrac the loc and scale from the dist
        self.loc = self.dist_pars_l[0]
        self.scale = self.dist_pars_l[1]
        
        #two pars
        if  rv.name in self.two_par_dists_nl: #freeze for recobnized distributions
            
            self.rv = rv(loc = self.loc, scale = self.scale)
            
        #3 pars
        elif rv.name in self.three_par_dists_nl:
            
            self.shape = self.dist_pars_l[2] #get the shape par
            
            self.rv = rv(self.shape, loc = self.loc, scale = self.scale)
            
        #===================================================================
        # assign function based on what was provided in the min column 
        #===================================================================
        #simple numerical models. CONSTRAINED
        if hp_basic.isnum(self.min):
            val_f = self.valf_rsample
            self.contained = True
            
            if not self.min < self.max:
                logger.error('min must be less than max')
                raise IOError
            
        #simple numerical models. UNCONSTRAINED
        elif (self.min is None) or pd.isnull(self.min):
            
            val_f = self.valf_rsample
            self.contained = False

        #binary label based
        elif isinstance(self.min, str):
        
            self.binary_low = hp_basic.str_to_bool(self.min)
            self.binary_high = hp_basic.str_to_bool(self.max)
            
            base_val = self.binary_low
            """pretty arbitrary, but we have to pick sometyhing"""
            
            #with a correlation attribute
            if not self.correlate_an is None:
            
                val_f = self.valf_binary_coran #set teh value seek function
                
                #set the binary labels
                
            else:
                
                val_f = self.valf_binary 
                

        else: raise IOError
        
        #===================================================================
        # plotter
        #===================================================================
        """
        self.rv.ppf(0.01)
        
        self.rv.loc
        
        self.rv.dist.name
        """
        
        if self.plot_f: 
            if self.session._write_figs:
                self.plot_valf()
        

        
        #report
        mean, var, skew, kurt = self.rv.stats(moments='mvsk')
        
        logger.debug('distrubtion frozen as \'%s\' with mean = %.2f and var = %.2f'%(self.rv.dist.name, mean, var))
        
        if base_val is None: base_val = mean
        
        return val_f, rv.name, base_val
            
    def valf_constant(self, obj): #set the constant
        logger = self.logger.getChild('valf_constant')
        
        logger.debug('for \'%s\' on \'%s\' got  \'%s\''%(obj.name, self.att_name, self.value))
        
        return self.value
        
    def valf_set_exec(self, obj): #set from a callable function on the object
        logger = self.logger.getChild('valf_set_exec')
        #=======================================================================
        # expose some variables for the function
        #=======================================================================
        """ shouldnt need ac cess to these
        att_name = self.att_name
        
        try:
            old_att_val = getattr(obj, att_name)
        except:
            logger.debug('unable to get \'%s\' from obj'%att_name)"""

        'thse strings should make calls to to obj'
        exec(self.value_assign_str)
        
        #=======================================================================
        # try:
        #     exec(self.value_assign_str)
        # except:
        #     logger.error('failed to execute \'%s\''%self.value_assign_str)
        #     raise IOError
        #=======================================================================
        
        """
        obj.set_new_depth(obj.hse_o.fhzlvl_ser[100])
        """
        
        logger.debug("finished with exe_str = %s"%self.value_assign_str)
        
        return np.nan
        
    def valf_simpl(self, #allow simple math on the object
                   obj): 
        
        logger = self.logger.getChild('valf_simpl')
        


        #=======================================================================
        # get local variables
        #=======================================================================
        att_name = self.att_name
        old_att_val = getattr(obj, self.att_name)
        session = self.session
        
        #add some more kwarg options for the user
        old_att_value = old_att_val
        old_value = old_att_val
        old_val = old_att_val
        
        
        
        new_val = None #the exe_str should overwrite this
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            """better to do this before hand"""
            if not 'new_val' in self.value_assign_str:
                raise IOError('missint \'new_val\' from exe_str')
            
        """this broke in py3 for some reason
        #=======================================================================
        # execute
        #=======================================================================

        
        try:
            exec(exe_str)
        except:
            raise IOError('failed to exec \'%s\' on \'%s\''%(exe_str, obj.name))"""
         
        #=======================================================================
        # eval
        #=======================================================================
        #clean the string
        exe_str = re.sub('new_val=','',self.value_assign_str.replace(" ",""))

        #do the eval
        new_val = eval(exe_str)
        
        
        #=======================================================================
        # checker
        #=======================================================================
        if new_val is None: 
            #new_val = 'dummy' #just to trick the code reader for scripts below
            raise IOError('failed to set any new_val for %s'%exe_str)
        
        #=======================================================================
        # formater
        #=======================================================================
        if hp_basic.isnum(new_val):
            new_val1 = float(new_val)
        else: 
            new_val1 = new_val
        
        
        logger.debug('with exec \'%s\' on \'%s\' got %s = \'%s\' (vs %s)'
                     %(exe_str, obj.name, att_name, new_val1, old_val))
        
        
        return new_val1
        
    def get_rsamp(self): #get a contained random sample
        
        rand_samp = self.rv.rvs() #get a random sample from teh scipy function
        
        'todo: add other samples by call'
        
        #=======================================================================
        # check for min/max
        #=======================================================================
        if rand_samp > self.max:
            value = self.max
        elif rand_samp < self.min:
            value = self.min
        else:
            value = rand_samp
            
        return value
        
    def valf_rsample(self, obj): #get a sample value
        'this gets called by the Dynp_controller.set_sample_values()'
        logger = self.logger.getChild('valf_rsample')
        #=======================================================================
        # prechecks
        #=======================================================================
        if not obj.__class__.__name__ == self.pclass_n: raise IOError
        if not hasattr(obj, self.att_name):                 raise IOError
        if getattr(obj, self.att_name) is None:             raise IOError
        #=======================================================================
        # get the contained arndom sample
        #=======================================================================
        if self.contained:
            value = self.get_rsamp() #get it contained
        else:
            value = self.rv.rvs() #get a random sample from teh scipy function
            
        logger.debug('applied on \'%s\' set \'%s\' to \'%s\''%(obj.name, self.att_name, value))
            
        return value
    
    def valf_binary(self, obj):  #binary label based
        
        logger = self.logger.getChild('valf_binary')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        'TODO: move these checks to __init__'
        if self.db_f:
            if not obj.__class__.__name__ == self.pclass_n: 
                raise IOError
            if not hasattr(obj, self.att_name):
                logger.error('\'%s\' does not have the expected attritube \'%s\''%(obj.name, self.att_name))                 
                raise IOError
            if getattr(obj, self.att_name) is None:             
                raise IOError
            
            
        #=======================================================================
        # get the break point
        #=======================================================================
        break_point = self.rv.rvs()
        #=======================================================================
        # apply the prediction
        #=======================================================================
        
        if     break_point <= 0.5: prediction = False
        else:                      prediction = True
        
        #=======================================================================
        # set this prediction on the object
        #=======================================================================
        
        logger.debug('finished for \'%s\' with break_point = %.2f. set \'%s\' to \'%s\''
                     %(obj.name,break_point, self.att_name, prediction))
        
        if self.db_f:
            #store debugging info
            hist_ser = pd.Series(name = obj.gid)

            hist_ser['break_pt'] = break_point

            
            self.hist_df = self.hist_df.append(hist_ser)
            
            self.hist_df.loc[obj.gid, 'prediction'] = prediction
            self.hist_df.loc[obj.gid, 'binary_low'] = self.binary_low
            self.hist_df.loc[obj.gid, 'binary_high'] = self.binary_high
            self.hist_df.loc[obj.gid, self.session.mind] = getattr(obj,  self.session.mind)
        
        return prediction
    
    def valf_binary_coran(self, obj): #binary label based with a correlation attribute
        'this gets called by the Dynp_controller.set_sample_values()'
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('valf_binary_coran')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        'TODO: move these checks to __init__'
        if self.db_f:
            if not obj.__class__.__name__ == self.pclass_n: 
                raise IOError
            if not hasattr(obj, self.att_name):
                logger.error('\'%s\' does not have the expected attritube \'%s\''%(obj.name, self.att_name))                 
                raise IOError
            if getattr(obj, self.att_name) is None:             
                raise IOError
            if not self.correlate_an is None:
                if not hasattr(obj, self.correlate_an):  
                    logger.error('\'%s\' does not have the expected correlation attritube \'%s\''%(obj.name, self.correlate_an))            
                    raise IOError
            
        #=======================================================================
        # get correlation
        #=======================================================================
        if self.correlate_an is None:
            lookup_val = None
        else:
            
            lookup_val = getattr(obj, self.correlate_an)
        """
        obj.value
        """
        
        #=======================================================================
        # Get the break point
        #=======================================================================
        'simple guess based on the realtion of a random sample and the break point'

        if lookup_val is None: 
            logger.warning('\'%s\' has no \'%s\'. setting thebreakpoint to 50/50'%(obj.name, self.correlate_an))
            break_point = 0.50
        
        elif hp_basic.isnum(lookup_val):
            break_point = self.rv.cdf(lookup_val)
            
        else: raise IOError
        
        #=======================================================================
        # apply the prediction
        #=======================================================================
        rand_samp = random.random() #get a random value from 0 to 1
        
        if     rand_samp <= break_point: prediction = self.binary_low
        else:                            prediction = self.binary_high
        
        #=======================================================================
        # set this prediction on the object
        #=======================================================================
        
        logger.debug('finished for \'%s\' with break_point = %.2f. set \'%s\' to \'%s\''
                     %(obj.name,break_point, self.att_name, prediction))
        
        if self.db_f:
            #store debugging info
            hist_ser = pd.Series(name = obj.gid)
            if not self.correlate_an is None:
                hist_ser[self.correlate_an] = lookup_val
            hist_ser['break_pt'] = break_point
            hist_ser['rand_samp'] = rand_samp
            
            self.hist_df = self.hist_df.append(hist_ser)
            
            self.hist_df.loc[obj.gid, 'prediction'] = prediction
            self.hist_df.loc[obj.gid, 'binary_low'] = self.binary_low
            self.hist_df.loc[obj.gid, 'binary_high'] = self.binary_high
            self.hist_df.loc[obj.gid, self.session.mind] = getattr(obj, self.session.mind)
        
        return prediction
    
    def valf_skip(self):
        raise IOError #this dynp should just be skipped
    
    def pick_from_dict(self, d): #select an attribute value from a liklihood dictionary
        logger = self.logger.getChild('pick_from_dict')
        
        roll = random.random()
        
        cuml = 0
        for k, v in d.items(): #loop through each option and see if the roll falls within the band
             
            cuml = cuml + v #add your liklihood to the pile
            #print k, v, cuml
            
            if roll < cuml:
                pick = k
                break
            
        logger.debug('got \'%s\' with roll = %.2f'%(pick, roll))
        
        return pick
            
            
    
    def set_sensi_vals(self):
        
        #=======================================================================
        # setup
        #=======================================================================
        logger = self.logger.getChild('set_sensi_vals')
        vstr = str(self.value_assign_str) #need this for some special cases
        
        #=======================================================================
        # set base values
        #=======================================================================
        base = self.value
        logger.debug('pulled base from \'self.value\' as \'%s\''%base)
        #=======================================================================
        # set sensi toggle values
        #=======================================================================
        logger.debug('calculating sensi values from passed pars \n')
        
        sensi_l=[]
        
        for sensi_an in ['sensi1', 'sensi2', 'sensi3']: #looping through each one
            sv_str = getattr(self, sensi_an) #pull the attribute
                        
            if sv_str is None: 
                continue #skip this one
            
            
            logger.debug('setting value from \'%s\' passed with \'%s\''%(sensi_an, sv_str))
            #specials
            if hp_basic.isnum(sv_str):
                sensi_l.append(sv_str)
                logger.debug("appending \'%s\' to sensi_l"%sv_str)
                continue
                
            sv_str = str(sv_str).strip() 
            if sv_str.startswith('*'):
                
                if sv_str == '*min/max':
                    
                    #unbounded scipy function
                    if self.min is None:
                        if not vstr.startswith('scipy'): raise IOError
                        
                        base = self.dist_pars_l[0]
                        delta = self.dist_pars_l[1]*3 #3 std devs is about 99%
                        min = base - delta
                        max = base + delta
                        
                        logger.debug('unbound scipy function with 3std dev') 
                            
                    #normal min/max
                    else:
                        min = self.min
                        max = self.max
                            
                    sensi_l = [min, max]
                    logger.debug('just using min/max values')
                    
                elif sv_str == '*skip':
                    sensi_l = [sv_str]                 
                   
                else:
                    logger.error("got unrecognized kwg \'%s\'"%sv_str) 
                    raise IOError #unrecognized kwd
                
                """why?
                break #only considering the first entry for special functions""" 
                
            #normals
            else: 
                sensi_l.append(sv_str)
                logger.debug("appending \'%s\' to sensi_l"%sv_str)
                
        
        #=======================================================================
        # closeout
        #=======================================================================
        if self.db_f:
            if base is None: 
                raise IOError
            if not isinstance(sensi_l, list): raise IOError
            if isinstance(base, list): raise IOError
            
            for v in sensi_l:
                if v is None: raise IOError
        
        
        self.sensi_base = base
        self.sensi_vals = sensi_l
        
        logger.debug('attached \'base\' and \'sensi_l\' %i'%(len(sensi_l)))
        
        return
        
        
    

    def run_dynp(self, big_d = None):
        """
        The challenge here is the Selector may have been modified
            but we dont want to re-run find_children() each time
        """

        #=======================================================================
        # shortcuts
        #=======================================================================
        if self.skip_f: #shortcut for dummies
            #logger.debug('skip_f=True. skipping')
            self.upd_d = set()
            return self.upd_d 

        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('run_dynp')
        self.run_cnt += 1

        
        #=======================================================================
        # object selection
        #=======================================================================
        logger.debug('making pick \n')
        pick_d = self.decide_pick(big_d = big_d)
        'this handles complex picks w/ and w/o selectors.. and whether to pull a fresh pick'
        #=======================================================================
        # #run the updates
        #=======================================================================
        logger.debug('applying to set \n')
        self.upd_s = self.apply_to_set(pick_d)
        
        #=======================================================================
        # #get the results
        #=======================================================================
        self.obj_cnt = len(self.upd_s)
        #self.get_results()
            
        return self.upd_s
    
    
    def apply_to_set(self,  #set teh sample value on all the objects in your class_D
                     dynk_d,  #set of objects to apply updates on
                     container = wdict, #results container
                     **kwargs): 
        
        """
        #=======================================================================
        # Calls
        #=======================================================================
        Action.run() Calls me exlicitly, often passing a subset of object names
        
        Dynp_controller.run_dynps()
        
        dynk_d: d[obj name] = object you apply to
        
        #=======================================================================
        # object update handling
        #=======================================================================
        see note at top
        
        2018 08 21: made major changes. all update handling should be done by the Kid now
            

        
        #=======================================================================
        # INPUTS
        #=======================================================================
        mark:    attribute name on which to apply a time stamp
        """
        
        
        #=======================================================================
        # shortcuts
        #=======================================================================
        #shortcut for no objects on this dynp
        if len(dynk_d) == 0: 

            return container() #shortcut
        
        #=======================================================================
        # setup
        #=======================================================================
        logger = self.logger.getChild('apply_to_set(%s)'%self.get_id())
        upd_s = set() #dictionary of objects with updates aplied to them
        
        #=======================================================================
        # pre checks
        #=======================================================================
        if self.db_f:
            if not callable(self.val_f): 
                raise IOError('%s something is wrong with the value setting function'%self.name)
            
            #class check
            obj1 = list(dynk_d.values())[0]
            if not self.pclass_n == obj1.__class__.__name__:
                raise IOError
            
            #freeze logic
            if self.freeze_att_f & (self.att_name is None): raise IOError
                
        """ switched to slicing beforehand
        if subset_n_l is None:
            logger.debug('for %i dynk_d: %s'%(len(self.dynk_d), self.dynk_d.keys()))
        else:
            logger.debug('intersect of %i dynk_d and passed subset of %i'%(len(subset_n_l), len(self.dynk_d)))"""
        
        #=======================================================================
        # loop and apply yourself to your children
        #=======================================================================
        logger.debug('on dynk_d (%i) of \'%s\' as \'%s\''
                     %(len(dynk_d), list(dynk_d.values())[0].__class__.__name__, self.value_assign_str))
        cnt = 0
        for k, obj in dynk_d.items():
            """WARNING: this dictionary may not be keyed with the objects native name"""

            #===================================================================
            # pre process    
            #===================================================================
            cnt +=1
            #if cnt%self.session._logstep ==0: logger.info('on %i of %i'%(cnt, len(dynk_d)))
            
            #logger.debug('changing \'%s\' \n'%(k))

            upd_s.update([obj.spawn_cnt]) #update the results container
            #===================================================================
            # get the new value
            #===================================================================
            if self.change_type == 'replace':
                logger.debug("for \'%s\' change_type == \'replace\'"%k)
                new_val = self.val_f(obj) #run the precompiled modification function on the object
                old_val = getattr(obj, self.att_name)
                                
            elif self.change_type == 'delta':
                logger.debug("for \'%s\' change_type == \'delta\'"%k)
                old_val = getattr(obj, self.att_name)
                new_val = old_val + self.val_f(obj)
                
            elif self.change_type is None:
                logger.debug("for \'%s\' change_type == 'NONE' (\'%s\')"%(k, self.value_assign_str))
                new_val = self.val_f(obj)
                old_val = None
                
            else: 
                raise IOError
            
            #===================================================================
            # type fixing
            #===================================================================
            #new_val = hp_basic.match_type(old_val, new_val, db_f = self.db_f)
            
            if not hasattr(old_val, 'shape'):
                new_val = type(old_val)(new_val)
            
            #===================================================================
            # update the object
            #===================================================================
            if not self.change_type is None: 
                obj.handle_upd(self.att_name, new_val, weakref.proxy(self), call_func='_%s.apply_to_set'%self.name)
            
            #===================================================================
            # freeze the att
            #===================================================================
            if self.freeze_att_f:
                
                if self.db_f:
                    if obj.is_frozen(self.att_name): 
                        raise IOError('change attempted on frozen \'%s.%s\''%(obj.gid, self.att_name))
                
                obj.fzn_an_d[self.att_name] = [self, 'freeze_att_f'] #freeze it
                
                logger.debug('freeze_att_f=TRUE. freezing attribute \'%s\''%self.att_name)
                
            #===================================================================
            # in loop checks
            #===================================================================
            if self.db_f:
                if not isinstance(new_val, type(old_val)):
                    raise IOError('%s failed to match old/new types'%self.name)
                
        #=======================================================================
        # post checker
        #=======================================================================
        if self.db_f:
            if not len(upd_s) == len(dynk_d):
                raise IOError
            

            
            if self.write_hist_f:
                try:
                    self.write_hist_df()
                except:
                    logger.warning('failed to execute write_hist_df')
        #===================================================================
        # wrap up
        #===================================================================
            
        logger.debug('finished on %i objects'%(cnt))
                    
        return upd_s
    
   
    #===========================================================================
    # def plot_valf(self, wtf=True): #plot the distribution
    #     
    #     logger = self.logger.getChild('plot_valf')
    #     
    #     import hp.sci
    #     import matplotlib.pyplot as plt
    #     import hp.plot
    #     
    #     #=======================================================================
    #     # create distrubtion worker
    #     #=======================================================================
    #     wrkr = hp.sci.Continuous_1D(self, self.session, name = self.name + '_plotr')
    #     
    #     #pass downa ll attributes
    #     wrkr.rv = self.rv #set the random variable parameters
    #     wrkr.fit_name = self.rv.dist.name
    #     wrkr.color = self.color
    #     wrkr.outpath = self.outpath
    #     
    #     wrkr.label = self.pclass_n + '.' + self.att_name
    #     
    #     if self.change_type == 'delta': wrkr.label = wrkr.label +  ' delta'
    #     
    #     title = self.name + ' '+ wrkr.fit_name + '_pdf plot'
    #     
    #     
    #     _ = wrkr.plot_pdf(title=title, wtf=wtf, annot_f=True)
    #     
    #         
    #     del wrkr #delete teh worker
    #     
    #     return
    #===========================================================================
    
    def write_hist_df(self):
        
        filetail = '%s %s %s hist_df'%(self.session.tag, self.session.state, self.name)

        if self.outpath is None:
            filepath = os.path.join(self.session.outpath, filetail)
        else:
            filepath = os.path.join(self.outpath, filetail)
            
        hp_pd.write_to_file(filepath, self.hist_df, index=True, overwrite=False, logger=self.logger)
        
        self.hist_df = pd.DataFrame() #clear it
        
    

           
class Dynp_controller(object): #controlling dynamic pars
    #===========================================================================
    # calcluated pars
    #===========================================================================
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dynp_controller') #have to use this as our own logger hasnt loaded yet
        logger.debug('\'%s\' start __init__'%self.__class__.__name__)
        super(Dynp_controller, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        logger.debug('\'%s\' finish __init__'%self.__class__.__name__)

    def run_dynps(self): #set apply all applicable dynp_os for this upd_sim_lvl
        """
        For periodic dynps
        #=======================================================================
        # CALLS
        #=======================================================================
        Should be called after updating the selectors, and before the main run loop
        
        
        Session.run_all() 
            self.run_dynps()    #called during Session. __init__. sim_lvl = 0  
            sim.run_dynps()    #called during Sessions run loop. sim_lvl = 1
            
            Simulation.run_timeline()
                tstep_o.run_dynps().     #sim_lvl = 2
                
                
        #=======================================================================
        # sim_lvl
        #=======================================================================
        upd_sim_lvl: sets the lowest sim_lvl at which the dynp will be activated
        
        sim_lvl: simulation level of the object calling run_dynps
        
        only set up for Session (0) Simulation (1), and Tstep (2)
                
                    
        """
        #=======================================================================
        # shortcuts
        #=======================================================================
        
        if not self.session.glbl_stoch_f: return #no dynamic pars this sessjion
        start = time.time()
        
        od = self.session.dynp_d
        #=======================================================================
        # setup
        #======================================================================= 
        logger = self.logger.getChild('run_dynps')
        setnl = []
        cnt = 0
        
        logger.info('\n dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp-dynp')
        logger.info('at sim_lvl %i on %i dynps'%(self.sim_lvl, len(od)))
        logger.debug('\n')

        #=======================================================================
        # loop and apply where told       
        #=======================================================================
        for dynp_n, dynp_o in od.items():
            
            #===================================================================
            # #short cuts
            #===================================================================
            if dynp_o.upd_sim_lvl == 'none': 
                logger.debug('%s is explicit. skipping'%dynp_n)
                continue #this dynp must be called explicitly
            'only applying dynps at a finer sim_lvl than whoever called this updater'
            
            if not dynp_o.upd_sim_lvl == self.sim_lvl: 
                logger.debug('%s upd_sim_lvl (%i) != my sim_lvl (%i). skipping'%(dynp_n, dynp_o.upd_sim_lvl, self.sim_lvl))
                continue #doesnt trigger for this step
            
            """ had ot move this into the run_dynp as some dynps are called explicitly
            if dynp_o.value == 'skip':
                logger.debug('\'%s\' is a dummy dynp. skipping'%dynp_n)
                continue"""

            logger.debug('running \'%s (%s.%s) \' with upd_sim_lvl = %i\n'
                         %(dynp_n, dynp_o.pclass_n, dynp_o.att_name, dynp_o.upd_sim_lvl))
            #===================================================================
            # run the dynp
            #===================================================================
            #run the valf on each object beloonging to the dynp
            upd_s = dynp_o.run_dynp()
            
            cnt += len(upd_s)
            
            setnl.append(dynp_n)
            
        stop = time.time()
        if len(setnl) > 0:
            logger.info('FINISHED in %.4f secs at sim_lvl %i, made %i updates with %i dynps: %s'
                         %(stop - start, self.sim_lvl, cnt, len(setnl), setnl))
            logger.debug('\n')
            
        else: logger.info('FINISHED at sim_lvl %i made no updates \n'%self.sim_lvl)
        
        return
    
    def raise_dynps_sensi(self): #special raiser for sensitity runs
        """
        #=======================================================================
        # INPUTS 
        #=======================================================================
        sensi_ser: series of parameter values for a simulations sensitivity run
        """
        sensi_ser = self.sensi_ser
        d = self.session.dynp_d
        logger = self.logger.getChild('raise_dynps_sensi')
        
        logger.debug('sensi_dynp-sensi_dynp-sensi_dynp-sensi_dynp-sensi_dynp-sensi_dynp-sensi_dynp-sensi_dynp-')
        logger.debug('setting the valf on a sensitivty analysis for %i dynps \n'%len(d))
        logger.debug('sensi_ser: \n%s \n \n'%sensi_ser)
        types = []
        for name, dynp in d.items():
            logger.debug('for dynp \'%s\' setting value_assign_str to \'%s\''%(name,sensi_ser[name] ))
            dynp.value_assign_str = sensi_ser[name]
            
            type = dynp.calibrate_valf() #assign teh valf b ased on this
            types.append('%s (%s)'%(name, type))
            
        
        #for entry in types: logger.debug(entry)
        
        logger.info('finished setting %i valfs'%len(types))
        logger.debug('\n')
        
        return



class Dynp_session(Dynp_controller): #handling of th edynamic pars
    """
    generally inherited by the Session
    
    mostyl handles dynps
    also does some handling of dynos
    """
    #===========================================================================
    # global pars
    #===========================================================================
    sensi_f = False  #sensitivity run flag

    glbl_stoch_f = False #placeholder session level flag to  disable dynps
    #===========================================================================
    # handle pars
    #===========================================================================
    dynp_hnd_file = None #filepath for handle file
    
    


    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dynp_controller') #have to use this as our own logger hasnt loaded yet
        logger.debug('\'%s\' start __init__'%self.__class__.__name__)
 
        super(Dynp_session, self).__init__(*vars, **kwargs) #initilzie teh baseclass 

        #=======================================================================
        # set pars
        #=======================================================================
        """ initilizing directly now
        self.dyno_d = OrderedDict() #container for all dynamic objects (Dyno_wrap)"""
        
        logger.debug('load_dynp_hnd_file \n')
        'set by sim.scripts'
        self.load_dynp_hnd_file(self.dynp_hnd_file)
        
        self.build_dyno_pars_d()
        
        self.logger.debug("__init__ finished \n ")
        return
                  
    def raise_dynps(self, df):
        """
        Using this just to keep all the dynp functions in one place
        """
        logger = self.logger.getChild('raise_dynps')
        #=======================================================================
        # raise the children
        #=======================================================================
        self.dynp_d = self.raise_children_df(df, kid_class = Dynamic_par)
        
        #=======================================================================
        # get the shortcutting lists
        #=======================================================================
        dp_smpstp_l = df.loc[:,'upd_sim_lvl'].unique().tolist()
        
        'dont think we are using this'
        dp_cn_l = df.loc[:,'pclass_n'].unique().tolist()
             
        logger.debug('finished with dp_smpstp_l = %i and dp_cn_l = %i'%(len(dp_smpstp_l), len(dp_cn_l)))
        
        logger.info("raised %i dynps"%len(self.dynp_d))
        
        self.dp_smpstp_l = dp_smpstp_l
        self.dp_cn_l = dp_cn_l
        
    def load_dynp_hnd_file(self, filepath): #load the xls full of dynp handles  
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('load_dynp_hnd_file')
        exp_coln = np.array(('att_name', 'self_upd', 'dynk_hndl', 'upd_df', 'lock_f'))
        
        #=======================================================================
        # prechecks
        #=======================================================================
        
        if not self.__class__.__name__ == 'Session': 
            raise IOError
        if filepath is None: 
            raise IOError
        
        
        #=======================================================================
        # load the file
        #=======================================================================
        #hnd_d = hp_pd.load_xls_d(filepath, logger = logger, index_col = None)
        hnd_d = self.load_par_tabs(filepath)

        #=======================================================================
        #checks
        #=======================================================================
        logger.debug('looping through %i loaded object handles: %s'%(len(hnd_d), list(hnd_d.keys())))
        for k, df_raw in hnd_d.items():
            logger.debug('cleaning \'%s\' handles: %s'%(k, str(df_raw.shape)))
            


            #===================================================================
            # clean and check
            #===================================================================
            
            df1 = df_raw.drop(columns = ['desc']).dropna(how='all', axis=0)
            
            #header check
            boolar = np.invert(np.isin(exp_coln, df1.columns))
            if np.any(boolar):
                raise IOError('missing %i expected columns: %s'%(boolar.sum(), exp_coln[boolar]))
            
            df2 = df1.loc[:, exp_coln] #get this slice
            
            if np.any(pd.isnull(df2)): 
                raise IOError('found some nulls on \'%s\' in teh dynp file: \n    %s'%(k, filepath))

            #===================================================================
            # tupleize
            #===================================================================
            df3 = df2.copy()
            for coln in ['self_upd', 'dynk_hndl']:
                df3.loc[:,coln] = df3[coln].replace(to_replace='none', value=np.nan)
                """NO! se have dictionayrs on teh dynk_hndl
                df3.loc[:,coln] = hp_pd.tlike_ser_clean(df3[coln].replace(to_replace='none', value=np.nan), 
                                                        leave_singletons=False, #make everything a tuple
                                                        sub_dtype=str,
                                                        logger=logger
                                                        )"""
                        
            #reset thid frame
            hnd_d[k] = df3.copy()

        logger.debug('finished and attached dynp_hnd_d %i from file \n'%len(hnd_d)) 
        
        self.dynp_hnd_d = hnd_d #attach this
        
        return
    
    """
    for k, df in hnd_d.items():
        print(k)
        
    df = hnd_d['House']
    
    df.loc[3,'self_upd]
    """
        
    def build_dyno_pars_d(self): #build the parameters shared by each dyno
        """
        here we explode each tab of the handle file into more usable set of containers
        
        To reduce memory footpring, we're storing all of this onto the session
        """
        
        logger = self.logger.getChild('build_dyno_pars_d')
        
        #=======================================================================
        # loop and build handles container
        #=======================================================================
        dyno_pars_d = dict() #dictionary of pars per cn
        
        for cn, df in self.dynp_hnd_d.items():
            logger.debug('building handles for \'%s\''%cn)
            d = dict() #pars holder for this cn {data name: data}
            
            #just a straight copy of the df
            d['hndl_df'] = df 
            
            #dynamic attribute names
            d['dyn_anl'] = df['att_name'].values.tolist() 
            
            #set of dynamic attributes that should trigger an update tot he parents metadf
            d['upd_df'] = tuple(df.loc[df['upd_df'],'att_name'].values.tolist())
            
            #locked attributes
            d['lock_anl']= df.loc[df['lock_f'], 'att_name'].values.tolist()
            
            #commands for ourselves
            d['self_upd'] = hp_pd.tlike_to_valt_d(
                                df.set_index('att_name')['self_upd'].dropna(), 
                                  leave_singletons=False, sub_dtype=str,
                                  leave_nulls=False)
            
            #commans for our children
            d['dynk_hndl'], d['dynk_ns'] = self.build_dynk_hndl(df)
            
            
            
            logger.debug('loaded dyno pars for \'%s\': %s'%(cn, list(d.keys())))
            
            dyno_pars_d[cn] = copy.copy(d) #set this
            
        logger.debug('finished loading dyno pars on %i dyno classes:%s'%(len(dyno_pars_d), list(dyno_pars_d.keys())))
        
        self.dyno_pars_d = dyno_pars_d #ste this
        
        """
        self.session.dyno_pars_d[self.__class__.__name__]
        
        for k, v in d.items():
            print(k, v)
        
        
        for k, v in dyno_pars_d.iteritems():
            print ('\'%s\': %s'%(k, v.keys()))
        """
            
    
    def build_dynk_hndl(self, df): #build handles from the handle frame
        """TODO: move this back up
        """
        #=======================================================================
        # buidl the self handle dictionary
        #=======================================================================

        
        
        
        hd = dict()
        dynk_ns = set() #set of dynk class names
        
        #raw_hnd_l = df.loc[:,'dynk_upd_raw'].unique().tolist()
        
        for ind, row in df[~df['dynk_hndl'].isna()].iterrows():
            #if row['dynk_hndl'] == 'none': continue #no handles for this att
            
            #convert these handles to a dictionary
            d1 = hp_basic.str_to_dict(row['dynk_hndl'])
            
            #convert these all to tuples
            d2 = {key:tuple(vals) for key, vals in d1.items()}
            
            dynk_ns.update(list(d2.keys())) #udpate the dynk_cn set
            
            #add this dictionary to the handle library
            hd[row['att_name']] = d2
            
            
        return hd, dynk_ns

            
            
        

        

        
    def check_dyno_cn(self, obj_cn): #check that this object type is a dyno
        logger = self.logger.getChild('check_dyno_cn')
        
        if not obj_cn in list(self.family_d.keys()):
            logger.warning('passed obj_cn \'%s\' not found in the family dictionary'%obj_cn)
            return
        
        mybook = self.family_d[obj_cn]
        obj1 = list(mybook.values())[0] #just take the first object
        
        if not hasattr(obj1, 'run_upd_f'):
            logger.error('\'%s\' objects are not a dynp.kids'%obj_cn)
            raise IOError
        else: logger.debug('\'%s\' is a dynp.kid'%obj_cn)
        
                            
    def get_sensi_metadf(self, sims_per_var = None, wtf = None): #get the metadata for sensitivity analysis runs
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_sensi_metadf')
        
        #if sims_per_var is None:    sims_per_var = self.sims_per_var
        if wtf is None:             wtf  = self.session._write_data
        
        #=======================================================================
        # get the baseline values
        #=======================================================================
        baseline_ser = pd.Series(index = list(self.dynp_d.keys())) #row to add each time
        
        logger.debug('finding baseline values for %i dynps'%len(self.dynp_d))
        
        for dn, dynp in self.dynp_d.items(): #loop through each dynp and enter the value
            bval = dynp.sensi_base
            
            
            #checks
            if self.db_f:
                if bval is None: raise IOError
                if str(bval).startswith('scipy'):
                    raise IOError #dont allow stochastic 
                
            baseline_ser[dn] = bval
            
        logger.debug('got baseline values: \n %s'%baseline_ser)
        
        #=======================================================================
        # convert the comparison columns
        #=======================================================================
        try: self.delta_compare_col_nl = eval(self.delta_compare_col_nl)
        except:
            logger.error('failed to convert the delta_compare_col_nl')
            raise IOError
            
        if not isinstance(self.delta_compare_col_nl, list):
            raise IOError
        
        #=======================================================================
        # get teh simulations metadata matrix
        #=======================================================================
        #add teh focus col
        baseline_ser['focus'] = 'baseline'
        baseline_ser['rank'] = 0
        
        
        df = pd.DataFrame(columns = baseline_ser.index) #build the matrix with this index
        df = df.append(baseline_ser, ignore_index = True) #add teh first row

        
        logger.debug('building sensi metadf from %i dynps \n'%len(self.dynp_d))

        for dn, dynp in self.dynp_d.items(): #loop through by classname
            logger.debug('updating df with \'%s\'s sensi_vals (%i)'%(dn, len(dynp.sensi_vals)))
            #===================================================================
            # prechecks
            #===================================================================
            """not sure about this..."""
            if dynp.upd_sim_lvl == 0: raise IOError #this is Session level and wont be captured
            
            """leeting the dyn_pars descide how many runs there should ber
            as we loop through , we fill the mdex_d so that we can make an mdex of this
            """            
            new_ser = baseline_ser.copy() #start witha  cop y

            logger.debug('for dynp \'%s\' adding %i sensi_vals to the analysis: sensi_val_l: %s'
                         %(dn, len(dynp.sensi_vals), dynp.sensi_vals))
            
            new_ser['focus'] = dn
            new_ser['rank'] = dynp.rank
            
            #add a row to the df for each of these
            for value in dynp.sensi_vals: 
                
                new_ser[dn] = value #change this value
                df = df.append(new_ser, ignore_index = True) #add teh modified row
                    
                
        """
        hp_pd.v(df)
        """
        
        df = df.sort_values('rank').reset_index(drop=True) #sort by rank
        df = df.drop(columns=['rank']) #drop the rank
            
        logger.debug("got sensi metadf with %s"%str(df.shape))
        
        if wtf:
            filepath = os.path.join(self.outpath, 'Session \'%s\' sensi_mat.csv'%self.name)
            hp_pd.write_to_file(filepath, df, index=True, logger=logger)
            
        
        self.sensi_df = df
        
        return df
        

