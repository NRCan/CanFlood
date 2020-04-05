'''
Created on Jul 5, 2018

@author: cef
'''
import os, sys, copy, logging, time
#weakref
from collections import OrderedDict
from weakref import WeakValueDictionary as wdict

import pandas as pd
import numpy as np


import model.sofda.hp.basic as hp_basic
import model.sofda.hp.pd as hp_pd
#import hp.plot
import model.sofda.hp.oop as hp_oop
import model.sofda.hp.sim as hp_sim
import model.sofda.hp.sel as hp_sel

from model.sofda.hp.pd import view

mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')

"""doesnt seem worth it
class Outputme_wrap(object): #wrapper for object on which Outputrs are applied
    pass """

class Outputr(hp_sel.Sel_usr_wrap,
              hp_sim.Sim_o,
              hp_oop.Child): #Standalone outputr worker
    
    #===========================================================================
    # program pars
    #===========================================================================
    'changed this so outputrs run every time step'
    upd_sim_lvl     = 2 #control when this is run

    # object handling overrides
    """
    raise_kids_f    = False
    load_data_f     = False"""
    db_f            = True        #override to perform db_f on writer (False could improve speed)
    
    #===========================================================================
    # user provided pars
    #===========================================================================
    #sel_n           = None  #selector name
    custom_exe      = None #custom outputter string
    sim_stats_exe   = None #numpy stats to perform for each siulation
    dt_n            = None #Tstep name for time slice outputrs
    out_attn        = None #attribute name selected for outputting
    #pclass_n        = None  #oject class name selected for outputting
    post_exe        = None
    ses_plot        = None #type of plot to generate for simulation summary data
    #out_attn_sfx    = None
    desc            = None
    
    #===========================================================================
    # calculation pars
    #===========================================================================
    #pick_d     = None
    otype       = None #type of outputer

    data        = None #holds the data for this outputr
    dtype       = None #data type for outputr data detected from out_attn suffix
    
    
    def __init__(self, *args, **kwargs):
        logger = mod_logger.getChild('Outputr') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
        super(Outputr, self).__init__(*args, **kwargs) 


        #=======================================================================
        #unique setup
        #=======================================================================
        self.codename = self.get_codename()

        if not self.dt_n is None: 
            self.dt_n = self.get_dt_n(self.dt_n)
            logger.debug('\n')

        
        logger.debug('set_dtype \n')
        self.set_dtype()
        
        logger.debug('make_pick \n')
        self.pick_d = self.make_pick()
        
        logger.debug('set_otype()')
        self.set_otype()
        
    
        
        logger.debug('set_dimensions \n')        
        self.set_dimensions()
        
        logger.debug('set_outf \n')
        self.set_outf()
        
        #=======================================================================
        # checking
        #=======================================================================
        if self.db_f:
            logger.debug('db_f=TRUE \n') 
            self.check_outputr()
        

        logger.debug('__init__ finished with pclass_n = \'%s\' \n'%self.pclass_n)
        
        return
    
    def get_codename(self): #generate a codename from the attribute values
        logger = self.logger.getChild('get_codename')
        codename = '%s'%self.name
        
        for attn in ['pclass_n', 'out_attn', 'sel_n', 'dt_n']:
            v = getattr(self, attn) #should have all of these
            
            if not v is None:
                codename = codename +'.%s'%v 
                
        logger.debug('got codename \'%s\''%codename)
        

        return codename
    
    def check_outputr(self):
        logger = self.logger.getChild('check_outputr')
        timeline_df = self.session.pars_df_d['timeline']
        
        if not self.dt_n is None:
            
            if not self.dt_n in timeline_df.loc[:,'name'].values.tolist():
                
                logger.error('my dt_n \'%s\' is not in the timeline'%self.dt_n)
                raise IOError
            
            if len(timeline_df) < 2:
                logger.error('can not provide time sliced data when there is only 1 time step')
                raise IOError
            
        #=======================================================================
        # selector checks
        #=======================================================================
        if not self.sel_n is None:
            
            #check the validity of this Selecto
            if not self.sel_o.pclass_n == self.pclass_n:
                logger.error('the Selelctors (%s) pclass_n (%s) must match the Outputrs  pclass_n (%s)'
                             %(self.sel_o.name, self.sel_o.pclass_n, self.pclass_n ))
                raise IOError
            
            """
            if not self.sel_o.upd_sim_lvl == 0:
                'see note in headers'
                logger.error('passed Selector \'%s\' has mid-Session updates (%s)'
                             %(self.sel_o.name, self.sel_o.upd_sim_lvl))
                raise IOError"""
                
        if not self.picko_p_f:
            raise IOError #not allowing this... too complicated with data structure
        

                
    
    def set_dtype(self): #detect teh data type by the out_attn suffix
        if not self.out_attn is None:
            if self.out_attn.endswith('_f'): 
                self.dtype = np.bool
            else: 
                self.dtype = np.dtype(object)
                
    def set_otype(self): #determine the outputer type
        logger = self.logger.getChild('set_otype')
        if (self.custom_exe is None) & (self.post_exe is None):
            self.otype = 'simple'
        elif (self.custom_exe is None) & (not self.post_exe is None):
            self.otype = 'post'
        elif (not self.custom_exe is None) & (self.post_exe is None):
            self.otype = 'obj'
        else:
            raise IOError
            
        logger.debug('set as \'%s\''%self.otype)
            
        return

    def set_dimensions(self): #set the outputtr function
        logger = self.logger.getChild('set_dimensions')
        #=======================================================================
        # logic by outputter type
        #=======================================================================
        #post exes
        if self.otype == 'post_exe': 
            'todo: allow multiple dimensions'
            time_d, space_d = 0, 0

        else:
            #=======================================================================
            #set time dimension            
            #=======================================================================
            
            #time slices
            'todo: allow lists'
            if not self.dt_n is None:
                time_d = 0
            else:
                time_d = 1
                
            #===================================================================
            # set space dimension
            #===================================================================
            space_d = 1
    
        #=======================================================================
        # wrap up
        #=======================================================================            
        if (time_d + space_d) >3: raise IOError
            

        self.total_d = space_d + time_d
        self.space_d, self.time_d = space_d, time_d
        
        logger.debug('got space_d = %s, time_d = %s'%(space_d, time_d))
    
    def set_outf(self): #assign the approriate writer function
        """
        TODO: add pandas functionality so the user can returns tats on the childmeta_df
        """
        logger = self.logger.getChild('set_outf')
        #===================================================================
        # get shortcuts
        #===================================================================
        ce_str = self.custom_exe
        pick_d = self.pick_d
        
        if self.db_f:
            if pick_d is None: raise IOError
            """allowign this now
            if len(pick_d) == 0: 
                raise IOError"""
        #===================================================================
        # data based writers
        #=================================================================== 
        if self.otype == 'simple':
            #===================================================================
            # snap shots
            #===================================================================
            if self.time_d == 0:
                
                if self.space_d == 0:    #one value for the simulation
                    data = np.nan
                    outf = self.time0_space0
    
                elif self.space_d == 1:   #a list of  attributes constant for the simulation (or at th eend)              
                    data = pd.Series(name = self.codename, index = list(pick_d.keys()), dtype = np.object).sort_index()
                    outf = self.time0_space1
                    

    
                else: 
                    raise IOError
                
            #=======================================================================
            # time series    
            #=======================================================================
            elif self.time_d == 1:
                
                #get the time series
                dt_l = self.session.pars_df_d['timeline'].loc[:,'name'].tolist()
                
                if self.space_d == 0:    #one object attribute with a time series
                    data = pd.Series(name = self.codename, index = dt_l, dtype = np.object).sort_index()
                    outf = self.time1_space0
    
                elif self.space_d == 1:   #an array of attributes recorded at each time           
                    """just add new entries?
                    data = pd.DataFrame(columns = dt_l, index = pick_d.keys(), dtype = np.object)"""
                    data = pd.DataFrame(columns = dt_l, dtype = np.object).sort_index()
                    outf = self.time1_space1
                    
                    
            else: raise IOError
    
      
        #===================================================================
        # custom outputr commands
        #===================================================================
        elif self.otype == 'obj':
            'todo: allow a list of commands'
            #===============================================================
            # pre checks
            #===============================================================
            """no?
            if not self.out_attn is None:
                logger.error('out_attn must be blank for custom_exes (got \'%s\''%self.out_attn)
                raise IOError"""
                

            """no! allow some stats for custom funcs
            if not self.sim_stats_exe is None:  
                logger.error('expected something for ')
                raise IOError"""
            
            """ OK with this now
            if not ce_str.endswith(')'):        
                logger.error('for custom_exe calls, the string must end with \')\'')
                raise IOError"""

            logger.debug('user provided custom output functions \'%s\''%(ce_str))
            
            outf = self.custom_exe_call #attach this as the writer func
            #data = np.nan
            
            #===================================================================
            # set data container
            #===================================================================
            if not self.time_d == 1: raise IOError
            dt_l = self.session.pars_df_d['timeline'].loc[:,'name'].tolist()
            if self.space_d == 0:    #one object attribute with a time series
                data = pd.Series(name = self.codename, index = dt_l, dtype = np.object).sort_index()

            elif self.space_d == 1:   #an array of attributes recorded at each time           
                data = pd.DataFrame(columns = dt_l, dtype = np.object).sort_index()
            else: raise IOError

            
        #=======================================================================
        # post_exe s
        #=======================================================================
        elif self.otype == 'post':
            
            outf = self.post_exe_call
            data = np.nan
            
            logger.debug('post_exe provided: \'%s\''%self.post_exe)
            
            
        else: raise IOError
            
        self.outf = outf
        self.data = data
        
        self.reset_d['data'] = copy.copy(data) #set blank data container for reseting
        
        logger.debug('finished with outf: \'%s\' and data: \'%s\''%(outf, data))
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not self.session.state == 'init': 
                raise IOError
            
            if data is None:
                raise IOError
            
            if not callable(outf):
                raise IOError
                         
        return
                        
    def time0_space0(self, obj, att_value):
        logger = self.logger.getChild('time0_space0')
        self.data = att_value
        
        logger.debug('for %s updated with \'%s\' = %s'%(obj.name, self.out_attn, att_value))
        
        return
    
    def time0_space1(self, obj, att_value):
        """
        This type could be a series from a single object
        or a string of object scould be passed
        """
        
        logger = self.logger.getChild('time0_space1')
        
        if not hp_pd.isser(self.data): raise IOError
        
        #=======================================================================
        # for data series
        #=======================================================================
        if hp_pd.isser(att_value):
            'just make a reference ot this series'
            self.data = att_value.copy()
            
        #=======================================================================
        # for a gorup of objects, passed one at a time
        #=======================================================================
        else:
            if not obj.gid in self.data.index: raise IOError
                
            self.data[obj.gid] = att_value
            
        logger.debug('for %s updated ser %i with \'%s\' = %s'%
                    (obj.name, len(self.data), self.out_attn, att_value))
        
        return
        

                
    def time1_space0(self, obj, att_value):
        logger = self.logger.getChild('time1_space0')
        
        ser = self.data
        time = self.session.tstep_o.name
        logger.debug('for obj.name \'%s\' time \'%s\' out_attn \'%s\''%(obj.name, time, self.out_attn))
        
        #=======================================================================
        # checsk
        #=======================================================================
        if self.db_f: 
            if not hp_pd.isser(ser):raise IOError
            if not time in ser.index: raise IOError
            if hasattr(att_value, 'values'): 
                """
                type(att_value)
                att_value.shape
                """
                raise IOError
            if not self.chk_old_val(ser[time], att_value):
                raise IOError
            
        self.data[time] = att_value
        
        logger.debug('for %s updated ser %i with \'%s\' = %s'%
            (obj.name, len(self.data), self.out_attn, att_value))
        
        return
        
    def time1_space1(self, obj, att_value):
        'TODO: evaluate the boolean again'
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('time1_space1')
        
        time = self.session.tstep_o.name
   
        logger.debug('for obj.name \'%s\' time \'%s\' out_attn \'%s\''%(obj.name, time, self.out_attn))
        
        #=======================================================================
        # check that this entry hasnt been written yet
        #=======================================================================
        if self.db_f:
            df = self.data
            if not hp_pd.isdf(df):          raise IOError
            
            if not time in df.columns:      raise IOError
            """allowing d ynamic selection
            if not obj.gid in df.index:    raise IOError
            if not self.chk_old_val(df.loc[obj.gid, time], att_value):
                raise IOError""" 
                
            #if this object is in already, is the value blank?
            if obj.gid in df.index:
                if not self.chk_old_val(df.loc[obj.gid, time], att_value):
                    raise IOError
                
        #=======================================================================
        # do the updating
        #=======================================================================
        #write this value by name and time
        self.data.loc[obj.gid, time] = att_value
        
        
        
        logger.debug('for %s updated df %s with \'%s\' = %s'%
                    (obj.gid, str(self.data.shape), self.out_attn, att_value))
        
        return
        
    def custom_exe_call(self, obj, att_value): #object method call
    
        logger = self.logger.getChild('custom_exe_call')
               
        logger.debug("for eval_str: \'%s\'"%self.custom_exe)
        
        try:
            result = eval(self.custom_exe)
        except:
            raise IOError
        
        #=======================================================================
        # store the result
        #=======================================================================
        if not result is None:
        
            time = self.session.tstep_o.name
            
            if self.space_d == 0:
                self.data[time] = result
            elif self.space_d == 1:
                self.data.loc[obj.gid, time] = result
            else: raise IOError
        
        return 
            

    def post_exe_call(self, obj, att_value):
        logger = self.logger.getChild('post_exe_call')
        
        #=======================================================================
        # make variables local
        #=======================================================================
        outs_od = self.session.outs_od
        'only setup for uni-dimensional data types'
        
        try:
            data = eval(self.post_exe)
        except:
            logger.error('failed to evaluate \'%s\''%self.post_exe)
            raise IOError
        
        try: 
            self.data = float(data)
        except:
            logger.error('got unexpected type on data: \'%s\': %s'%(type(data), data))
            raise IOError
        
        logger.debug('got post_exe result: %.2f from cmd \'%s\''%(self.data, self.post_exe))
        
        if self.db_f:
            if np.any(pd.isnull(self.data)):
                logger.warning('got null')
                #raise IOError
            
            """

            self.session.outs_od.keys()
            """
        
    def run_outp(self): #store outputs for each of my userse
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        called by Out_controller.run_outputrs()
        
        this ensure teh approriate sim_lvl is applied
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('run_outp')
        logger.debug('starting with run_cnt %i'%self.run_cnt)
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if self.data is None:
                raise IOError
            
            if self.pick_d is None:
                raise IOError
        
        #self.modified_f = True #flag for recompiling
        self.run_cnt += 1
        
        #=======================================================================
        # get userse
        #=======================================================================
        #data = self.data
        d = self.decide_pick()
        '''upgrading to dynamic
        only setup for static selection'''

        logger.debug('for %i \'%s\' users \n'%(len(d), self.pclass_n))


        #=======================================================================
        # loop and store
        #=======================================================================
        for gid, obj in d.items(): #loop through all of your users and store the data page
            logger.debug('outputing %s'%gid)
            
                        
            #===================================================================
            # get the attribute value
            #===================================================================
            if not self.out_attn is None:
                att_value = getattr(obj, self.out_attn) #get this attribute value
                if self.dtype == np.bool: att_value = bool(att_value)

            else:
                att_value = None #custom calls wont have an att value 
            
            #===================================================================
            # execute the outputr func
            #===================================================================
            _ = self.outf(obj, att_value) #data bbased
            
        logger.debug('finished outputting for %i objects \n'%len(d))
        
        
        return
        
        
    def chk_old_val(self, old_val, new_val):
        
        logger = self.logger.getChild('chk_old_val')
        
        if np.all(pd.isnull(old_val)):
            'the value should be cleared and null' 
            return True
        
        elif old_val == new_val: 
            logger.error('my value  was already in teh output page (%s)'%old_val)
            return False
        else: 
            logger.error('att_v_old = %s while att_value = %s'%(old_val, new_val))
            return False
        
    def get_stat(self, data=None): #get the passed stats for this data set
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_stat')
        if data is None: data = self.data
        
        logger.debug('on data \'%s\''%(type(data)))
        
        if data is None: 
            logger.error('got None for data')
            raise IOError
        #===================================================================
        #  time slices
        #===================================================================


        #===================================================================
        # get the stat method
        #===================================================================
        exe_str = self.sim_stats_exe
        
        #use raw data
        if exe_str == '*none':
            logger.debug('got \'*none\' kwarg. returning None')
            return None
        
        elif (exe_str == '*raw') or (exe_str == '*dxraw'): 
            cond = 'raw'
            
            if hasattr(data, 'values'): #for 1d arrays
                cond = cond + '%s'%str(data.shape)
                
                if data.shape == (1,1):
                    stat = data.values[0,0]
                elif data.shape == (1,):
                    stat = data.values[0]
                else:
                    logger.error('got unexpected shape %s for sim_stats_exe = \'*raw\''%str(data.shape))
                    raise IOError
                
            else:
                stat = data
                
        #numpy stats command
        else: 
            #===================================================================
            # get stat by dimension
            #===================================================================
            #non matrix data
            if not hasattr(data, 'values'):
                
                'were getting series passing through, so this just pulls the value'
                if hp_basic.isnum(data):            
                    stat = float(data)
                    cond = 'float'
                elif isinstance(data, str):  
                    stat = str(data)
                    cond = 'str'
                else: raise IOError
                
            #matrix type data
            else:
                logger.debug('with data shape %s'%str(data.shape))
                    
                if len(data) == 0:
                    logger.warning('got no data!')    
                    """allowing this now
                    raise IOError"""
                    stat = np.nan
                    cond = 'empty'
                
                else:
                    cond = 'matrix xD'

                    ar = data.values
                    
                    'just dropping everything down to an array'
                    data = ar
                    
                    try:  
                        stat = eval(self.sim_stats_exe) #bundle this with the numpy object
                    except:
                        logger.warning('data: \n%s'%data)
                        raise IOError('failed to evaluate \'%s\' '%(self.sim_stats_exe))
                    
                    
        logger.debug('finished with stat = \'%s\' under cond: \'%s\''%(stat, cond))
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not isinstance(exe_str, str):
                raise IOError
            
            if hasattr(stat, 'values'):
                logger.error('improper stats compression for \'%s\''%self.sim_stats_exe)
                raise IOError
            
            if not exe_str.startswith('*'):
                if not hp_basic.isnum(stat): 
                    logger.error("got non numeric stat")
                    raise IOError
        
        return stat
    


class Out_controller(object): #thin wrapper of output commands for high level simulation controllers
    
    outpars_d = None #container of each class and the att_n we've selected for outputting
    
    #===========================================================================
    # user pars
    #===========================================================================
    write_fly_f = False #flag to write results on the fly
    #===========================================================================
    # object handling overrides
    #===========================================================================
    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Out_controller') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__')
        
        super(Out_controller, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        logger.debug("_init__ finished \n")
    
    
    def raise_outputrs(self):
        'should be called by  the session'
        self.outs_od = self.raise_children_df(self.pars_df_d['outputs'], 
                                             kid_class = Outputr, 
                                             container = OrderedDict,
                                             attn_skip_l = None,
                                             dup_sibs_f = False) #this has some issues with blank entries
        
        """
        hp_pd.v(self.pars_df_d['outputs'])
        """
        #=======================================================================
        # get codenames list
        #=======================================================================
                #get codename list
        l = []
        for k, v in self.outs_od.items():
            l.append(v.codename)
        self.outs_codenames_l = l
        #=======================================================================
        # build dxcol
        #=======================================================================
        if self.output_dx_f:

            dt_l = self.session.pars_df_d['timeline'].loc[:,'name'].tolist()
            
            mdex = pd.MultiIndex.from_product([l, dt_l],
                                 names=['codenames', 'dt_n'])
            
            self.outputrs_dxcol = pd.DataFrame(columns = mdex)
        
        """need to execute this earlier
        self.build_outpars_d()
        hp_pd.v(dxcol)
        
        v.desc
        
        """
        #=======================================================================
        # post checks
        #=======================================================================
        for k, v in self.outs_od.items():
            if not v.__class__.__name__ == 'Outputr':
                raise IOError
        
        
        return
    

    def build_outpars_d(self): #build a dictionary of the parameters selected for output for each pclass_n
        """
        This allows us to tell whats being output,
            so we know whether to calc it or not
            
        #=======================================================================
        # Reseting (simulation handling)
        #=======================================================================
        see dyno.set_og_vals()
            these are collected (for dynamic objects) and added to the reset_d
        """
        logger = self.logger.getChild('build_outpars_d')
        
        
        d = dict()
        
        df = self.pars_df_d['outputs']
        
        for ind, row in df.iterrows():
            if row['out_attn'] is None: continue
            if row['out_attn'] == 'none': continue #we shoudl change all these blanks to explicit
            if pd.isnull(row['out_attn']):
                continue
            
            cn = row['pclass_n'] #get the classs name for this
            
            
            if cn in list(d.keys()): #update
                d[cn].update([row['out_attn']]) #add this attribute name to the set
                
            else: #start a new one
                d[cn] = set([row['out_attn']])
        
        """need to load from the frame, not the outputrs
        for outn, outo in self.outs_od.iteritems():
            
            if outo.out_attn is None: continue
            if outo.out_attn == 'none': continue #we shoudl change all these blanks to explicit
            
            cn = outo.pclass_n #get the classs name for this
            
            
            if cn in d.keys(): #update
                d[cn].update([outo.out_attn]) #add this attribute name to the set
                
            else: #start a new one
                d[cn] = set([outo.out_attn])"""

        
        logger.debug('buitl outpars_d for %i classes'%len(d))
        
        #=======================================================================
        # add any blanks
        #=======================================================================
        
        """run too early for the family_d
        for cn in self.family_d.keys():
            if not cn in d.keys():
                d[cn] = [] #empty list"""
                
        for cn in self.pars_df_d['obj_test'].loc[:,'name'].values.tolist(): #pull from the test tab
            if not cn in list(d.keys()):
                d[cn] = [] #empty list
                
        
        self.outpars_d = d
        
        return
        
        
        
    def check_sensi_delta_outrs(self):
        logger = self.logger.getChild('check_sensi_delta_outrs')
        #=======================================================================
        # check outputrs
        #=======================================================================
        l = self.delta_compare_col_nl
        
        for oname in l:
            if not oname in list(self.outs_od.keys()):
                logger.error('passed delta compare outputer name \'%s\' not found in the loaded outputers '%oname)
                raise IOError
        

    def run_outputrs(self, outs_od=None): #tell each writter to store its  data to the library
        
        """
        triggered by
        Simulation.run_timeline():
            Tstep.get_results()
        
        this creates a problem for classes higher than this
        
        for now, ive just disabled writing to the high_cns, bu tleft the decision code here
        """
        
        logger = self.logger.getChild('run_outputrs')
        
        
        if outs_od is None: 
            outs_od = self.session.outs_od
        
        logger.debug('\n \n')
        logger.info('on %i outputrs at %s'%(len(outs_od), self.session.state))
        logger.debug('\n')
        start = time.time()
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not self.__class__.__name__ == 'Session':
                raise IOError
            
            l1 = len(self.outs_od)
            
            for k, v in outs_od.items():
                if self.model is None: 
                    raise IOError
                if not v.__class__.__name__ == 'Outputr':
                    raise IOError
                
                
        #=======================================================================
        # loop the outputrs
        #=======================================================================\
        cnt = 0
        for oname, outputr in outs_od.items():
            #===================================================================
            # #check by model time slice
            #===================================================================
            'todo, allow a list of dt_ns'
            if not outputr.dt_n is None:
                if not outputr.dt_n == self.model.tstep_o.name:
                    logger.debug('\'%s\' time sliced by \'%s\' not ready. skipping'%(oname, outputr.dt_n))
                    continue
                
            #===================================================================
            # run the Outputr
            #===================================================================
            logger.debug('on %s with upd_sim_lvl = %s \n'%(oname, outputr.upd_sim_lvl))
                            
            outputr.run_outp() 
            cnt +=1
            
        stop = time.time()
        logger.info('finished on %i in %.4f secs \n'%(cnt, stop - start))
        
        if self.db_f:
            if not l1 == len(self.outs_od):
                raise IOError
        
        return
        
        
    def get_outputs_summary(self, od = None): #calculate the stats across the timeline for each output
        """
        'run by the simulation during get_results()'
        basically dropping the time dimension with a statistic
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_outputs_summary')
        if od is None: od = self.session.outs_od
        #=======================================================================
        # data setup
        #=======================================================================
        df = pd.DataFrame(index = [self.name]) #series for putting stats in

        'needs to be a df to handle mixed types. , columns = od.keys()'
                
        logger.info('for %i pages in the outputs library'%len(od))
        
        #=======================================================================
        # loop and calc stats
        #=======================================================================
        for name, outo in od.items(): #loop through each page and calculate stats
            #===================================================================
            # drop to single stat
            #===================================================================
            logger.debug('summarizing for \'%s\' '%(name))
            if outo.sim_stats_exe == '*none': continue #skip me
            if outo.sim_stats_exe == '*dxraw': continue
            
            df.loc[self.name,outo.codename] = outo.get_stat() #plug this in

        
        logger.debug('finished calculating %i statistics'%len(df))

        return df
    
    def get_outputs_summary_dx(self, od = None):
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('get_outputs_summary_dx')
        if od is None: od = self.session.outs_od
        
        #=======================================================================
        # data setup
        #=======================================================================
        dxcol = self.session.outputrs_dxcol.copy() #set this during raise_outputrs
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            for name, outo in od.items(): #loop through each page and calculate stats
                if outo.sim_stats_exe == '*none': continue #skip me
                if outo.time_d == 0: continue #exclude these 
                if not isinstance(outo.data, pd.DataFrame): 
                    raise IOError
                """
                type(outo.data)
                """
                
        
        
        #=======================================================================
        # loop and calc stats
        #=======================================================================
        logger.info('for %i pages in the outputs library:'%len(od))
        for name, outo in od.items(): #loop through each page and calculate stats
            
            #shortcuts/exclusions
            if outo.sim_stats_exe == '*none': continue #skip me
            if outo.time_d == 0: continue #exclude these 
            'seems better to exclude any time sliced data'
            
            
            #enter the data
            data = outo.data
            
            logger.debug('collecting time stats on \'%s\''%(name))
            for dt_n in data.columns: #loop through and summarize for each time step
                
                
                'single row with 2d colums'
                df_slice = data[dt_n] #get the time slice
                dxcol.loc[self.name, (outo.codename, dt_n)] = outo.get_stat(df_slice)
                    
                    
        logger.debug('finished with dxcol %s'%str(dxcol.shape))
        return dxcol
    
    def write_full_outputs(self,  #write the attributes to file
                          outs_od = None, #dictionary of outputrs to write
                          xtra_d = dict(), ##bonus name:data pairs to include int he outputs
                          filehead = None, filetail = None, wtf = None): 

        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('write_full_outputs')
        
        if outs_od is None: outs_od = self.session.outs_od
        if wtf is None: wtf = self.session._write_data
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not hasattr(outs_od, 'keys'):
                raise IOError
        
        #=======================================================================
        # collect all the outputs
        #=======================================================================
        d = OrderedDict() #start empty
        for tag, outo in outs_od.items(): 
            if outo.data is None: 
                logger.warning('%s has no data. skipping'%tag)
                continue #skip this one
            
            #add teh label
            outo.data.index.name = outo.desc
            
            d[tag] = outo.data
            
        #=======================================================================
        # add the extras
        #=======================================================================
        for tag, data in xtra_d.items():
            d[tag] = data
        

        logger.debug('on d with %i entries'%len(d))
        
        #=======================================================================
        # write to file
        #=======================================================================
        if wtf: 
            if filehead is None: filehead = self.outpath
            if filetail is None: filetail = '%s %s sim_res'%(self.session.tag, self.name)
        
            filepath = os.path.join(filehead, filetail)
            
            hp_pd.write_dfset_excel(d, filepath, logger=logger)
                            
        return
    

    def plot_hists(self, wtf=None): #plot hisograms on the flagged outputr codenames
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('plot_hists')
        

        if wtf is None: wtf = self.session._write_figs
        outs_od = self.outs_od
        
        #=======================================================================
        # shortcuts
        #=======================================================================
        if self.session.sensi_f: 
            logger.info('sensi_f=TRUE. skipping histograms')
            return
        

        logger.debug('on outs_od %i'%len(outs_od))
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not self.__class__.__name__ == 'Session': 
                raise IOError
            
            """ not sure why this was here....
            if self.state == 'post':
                raise IOError"""
                
        #=======================================================================
        # loop the outputrs
        #=======================================================================
        logger.debug('looping outputrs and generating histograms')
        ptype = []
        for codename, outputr in outs_od.items():
            if outputr.ses_plot == 'hist': 
                self.plot_simout_hist(outputr.name, wtf=wtf)
                ptype.append('%s_hist'%outputr.name)
            
            elif outputr.ses_plot is None: 
                pass
            else: raise IOError
                
        logger.debug('finished and generated %i plots: %s'%(len(ptype), ptype))
        
        return
                
            
    def plot_simout_hist(self, search_str, wtf=None): #plot the histogram of all the aad results
        """
        NOTE: This does not plot outputr data, but the Session summary
        #=======================================================================
        # INPUTS
        #=======================================================================
        search_str: string found in the outputr codename
        
        #=======================================================================
        # TODO
        #=======================================================================
        revise this to work on the outputr not the session
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('run_all')
        if wtf is None: wtf = self.session._write_figs
        
        df = self.data
        
        #=======================================================================
        # formatters
        #=======================================================================
        self.color = 'blue'
        self.alpha = 0.5
        self.label = search_str
        self.fig_size = (4,4)
        
        self.hist_bins = 'auto'
        
        title = 'Session \'%s\' with %i sims - \'%s\' histogram'%(self.name, self.run_cnt, search_str)
        #=======================================================================
        # find the results colmun
        #=======================================================================
        boolcol = pd.Series(df.columns).astype(str).str.contains(search_str).values
        
        try:
            data = df.loc[:,boolcol].T.iloc[0].astype(float)
        except:
            
            if boolcol.sum() == 0:
                logger.warning('found no column with \'%s\' in the simulation summary. skipping'%search_str)
                return

            raise IOError
        

        
        #=======================================================================
        # plot the historgram
        #=======================================================================
        ax = self.plot_data_hist(data = data, title = title, annot = True, normed = False,
                                 wtf = wtf)
    
        return

   