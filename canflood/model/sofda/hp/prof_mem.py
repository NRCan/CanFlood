'''
Created on Jul 13, 2018

@author: cef

memory profiling
'''
#===============================================================================
# # IMPORTS ----------------------------------------------------------------------
#===============================================================================
#import hp.plot #need to call this first so matplotlib handles are set properly
import os, copy, sys, time, logging, weakref, gc
#import cProfile, pstats, 
#import objgraph

#from pympler import asizeof

from collections import OrderedDict


from datetime import datetime
from sys import getsizeof

import pandas as pd

import model.sofda.hp.pd as hp_pd
#import model.sofda.hp.basic as hp_basic

#===============================================================================
# # module globals -------------------------------------------------------------
#===============================================================================
prof_subfolder = '_prof'

mod_logger = logging.getLogger(__name__)

mod_logger.debug('initialized')



def deep_getsizeof(o, ids):
    """Find the memory footprint of a Python object
    This is a recursive function that rills down a Python object graph
    like a dictionary holding nested ditionaries with lists of lists
    and tuples and sets.
    The sys.getsizeof function does a shallow size of only. It counts each
    object inside a container as pointer only regardless of how big it
    really is.
    :param o: the object
    :param ids:
    :return:
    
    https://github.com/the-gigi/deep/blob/master/deeper.py#L80
    
    
    """
    d = deep_getsizeof
    if id(o) in ids:
        return 0

    r = getsizeof(o)
    ids.add(id(o))

    if isinstance(o, str) or isinstance(0, str):
        return r

    if isinstance(o, Mapping):
        return r + sum(d(k, ids) + d(v, ids) for k, v in o.items())
    
    if isinstance(o, weakref.ProxyType):
        return r + getsizeof(o)

    if isinstance(o, Container):
        return r + sum(d(x, ids) for x in o)

    return r

def fill_in_ocnt(ser): #fill in the object counts in the passed series
    
    for type_name in ser.index.tolist():
        if not pd.isnull(ser[type_name]): continue
        try:
            ser[type_name] = objgraph.count(type_name)
        except:
            print('fail on %s'%type_name)
            raise IOError
    
    return ser

def profile_obj_mem(obj, logger = mod_logger, outpath = None): #get data on objects memory footprint
    logger = logger.getChild('profile_obj_mem')
    
    cols = ['att_name', 'att_type', 'vtype', 'shallow_mem', 'deep_mem']
    df = pd.DataFrame(columns = cols)
    ser_blank = pd.Series(index = cols)
    
    #===========================================================================
    # get objects attributes
    #===========================================================================
    
    att_std, att_call, att_def = hp_oop.get_atts(obj, logger = logger)
    
    #===========================================================================
    # get data from each
    #===========================================================================
    
    for att_type, d in [('other', att_std), ('callable', att_call), ('default',att_def)]:
        
        for att_name, v in d.items(): #loop through each type
            #get blank series
            ser = ser_blank.copy()
            
            #===================================================================
            # get data
            #===================================================================
            ser['att_name'] = att_name
            if att_name in list(obj.__dict__.keys()): att_type = '__dict__' #re label these
            
            ser['att_type'] = att_type
            
            ser['vtype'] = type(v)
            
            ser['shallow_mem'] = getsizeof(v)
            
            ser['deep_mem'] = deep_getsizeof(v, set())
            
            #update set
            
            df = df.append(ser, ignore_index = True)
            
            logger.debug('got: %s'%ser.values.tolist())
            
    
    if not outpath is None:
        if not os.path.exists(outpath): raise IOError
        
        filename = '\'%s\' profile_obj_mem'%(obj.name) 
        filepath = os.path.join(outpath, filename)
                
        hp_pd.write_to_file(filepath,df, logger = logger)
        
    return df

    """
    hp_pd.v(df)
    """
            
            
    
    
    
class Profile_wrapper(object): #wrapper for profiling oops
    
    def __objsize__(self):
        #=======================================================================
        # defaults
        #=======================================================================

        
        #=======================================================================
        # build dictionary of objects ot check
        #=======================================================================
        d = dict()
        try:
            d.update(self.__dict__) #add the live atts
        except:
            pass
        
        try:
            for k in self.__slots__: #ge tall teh slots
                
                d[k] = getattr(self, k)
        except: pass
            
        #=======================================================================
        # calcluate the size of all these
        #=======================================================================
        ts = getsizeof(self) #flat size
            
        for k, v in d.items():
            try:
                vs =  deep_getsizeof(v, set())
            except:
                vs = getsizeof(v)
            ts += vs

            
        return ts
    
class Profile_session_wrapper(object):
    
    def prof(self, state=None):
        """ switched to a graduated profile level"""
        
        if state is None: state = self.session.state
        
        if self._prof_mem >0: #only profile sim runs
            if state.startswith('0'):
                self.resc_prof.store_run_state(state = state)
                
            if self._prof_mem >1: 
                self.resc_prof.store_run_state(state = state)
                
                if self._prof_mem >2: 
                    self.resc_prof.store_obj_size(state = state) #size of all objects in teh family_d
        
                    
                    if self._prof_mem >3:
                        self.resc_prof.store_obj_cnt(state = state)
                        gc.collect() #need to clear up these expensive profiling processes
                        
        else:
            self.logger.debug('no profiling for _prof_mem = %i'%self._prof_mem)
            
        return
     
class Resource_profiler(object): #worker for profiling resource usage
    

    fly_res_fd = None #contianer fo fly results file names for each data type

    def __init__(self, 
                 logger     = mod_logger, 
                 _wtf       = True,
                 fly_res_f  = True,
                 name       = 'none',
                 session    = None):

        #=======================================================================
        # passed
        #=======================================================================
        self.logger = logger.getChild('resc_prof')
        self._wtf = _wtf
        self.name = name
        self.session = session
        self.fly_res_f = fly_res_f
        self.db_f = session.db_f
        
        #=======================================================================
        # defaults
        #=======================================================================
        self.outpath = os.path.join(self.session.outpath,prof_subfolder)
        self.time_fmt = '%Y%m%d-%H-%M-%S'
        self.ltime =  time.time()
        self.headers = ['state','time', 'tdelta', 'family_d cnt', 'spawn_cnt', 'rss', 'vss', 'cpu']
        self.state_df = pd.DataFrame(columns = self.headers)
        self.ocnt_df = pd.DataFrame(columns = ['state', 'time']) #empty data frame to start with
        self.osize_df = self.ocnt_df.copy()
        self.ogrow_df = self.ocnt_df.copy()
        self.ocnt2_df = self.ocnt_df.copy()
        
        #=======================================================================
        # setup funcs
        #=======================================================================
        #if self._wtf: self.file_setup()
        
        if self.fly_res_f and self._wtf:
            self.fly_res_fd = dict()
            
        if self._wtf:
            os.makedirs(self.outpath)

                 
        
        self.logger.debug("finished _init_ with headers: %s"%(self.headers))
        
        return

        
    def store_run_state(self, state = None): #add an entry to the frame
        #=======================================================================
        # defait;s
        #=======================================================================
        
        logger = self.logger.getChild('store_run_state')
        if state is None: state = self.session.state
        df = self.state_df
        #=======================================================================
        # setup and initials
        #=======================================================================
        #build the blank series for writing
        ser = pd.Series(index = df.columns)

        ctime = time.time()
        
        import psutil
        process = psutil.Process(os.getpid())
        with process.oneshot():
        
            #=======================================================================
            # loop and fill
            #=======================================================================
            
            for indx, entry in ser.items():
                if indx == 'state': v = state
                if indx == 'time': v = datetime.now().strftime(self.time_fmt)
                if indx == 'tdelta': v =  (ctime - self.ltime)
                if indx == 'family_d cnt': v = self.session.family_cnt()
                if indx == 'spawn_cnt': v = self.session.spawn_cnt
                if indx == 'rss': v = process.memory_info()[0]/1e6
                if indx == 'vss': v = process.memory_info()[1]/1e6
                if indx == 'cpu': v = process.cpu_percent(interval=None)
                
                #store into the series
                ser[indx] = v
        
        #=======================================================================
        # add deltas
        #=======================================================================
        for indx in ['rss']:
            if len(df) > 0:
                try:
                    v = ser[indx] - float(df.tail(1)[indx])
                except:
                    print('fail on %s'%df.tail(1)[indx])
                    raise IOError
                
            else: v = 0
                
            ser['%s_d'%indx] = v #store this
            
            
        #=======================================================================
        # wrap up
        #=======================================================================
        self.state_df = df.append(ser, ignore_index=True) #add this to the end
        self.ltime = ctime #set this for tnext time
        
        logger.info('\'%s\' rss= %.2f Mb, rss_d= %.4f Mb'%(ser['state'], ser['rss'], ser['rss_d']))
        logger.debug('finished with: \n %s'%ser)
        
        #=======================================================================
        # write fly results
        #=======================================================================
        if not self.fly_res_fd is None: 
            
            #first time. setup the file
            if not 'run_state' in list(self.fly_res_fd.keys()):
                self.fly_res_fd['run_state'] = os.path.join(self.outpath, '%s fly_run_state.csv'%self.session.tag)
                first = True
            else:
                first = False
            
            #write hte data
            hp_pd.write_fly_df(self.fly_res_fd['run_state'], ser, lindex = ser['state'], 
                               first = first, tag = self.session.tag,
                               logger = self.logger, db_f = self.db_f)



        
        return
    
    def store_obj_size(self, state = None): #calcluate the size of all objects in teh family_d
        
        #=======================================================================
        # defait;s
        #=======================================================================
        lib = self.session.family_d
        
        if len(lib) == 0: return
        
        logger = self.logger.getChild('store_obj_size')
        if state is None: state = self.session.state
        
        
        df = self.osize_df
        
        #=======================================================================
        # data setup
        #=======================================================================
        ser = pd.Series(index = ['state'])
        ser['state'] = state
        ser['time'] = datetime.now().strftime(self.time_fmt)
        
        #special writers
        ser['Session'] = getsizeof(self.session)/1e6
        

        
        #=======================================================================
        # loop and calculate for each cn
        #=======================================================================
        logger.debug('looping through %i books'%len(lib))
        for cn, d in lib.items():
            size = 0
            for gid, obj in d.items(): #sum each object
                
                
                size2 = obj.__objsize__() #size attributes deep size
                
                """
                size3 = asizeof.asizeof(obj) #size of the object plus the sizes of any referents
                

                size1 = getsizeof(obj) #shallow/flat size
                logger.info('\'%s\' size1=%.0f, size2=%.0f, size3=%.0f'%(gid, size1, size2, size3)) """
                
                size += size2
                
            ser[cn] = size/1e6 #set this into the series
        
        #=======================================================================
        # get the total size
        #=======================================================================
        boolcol = ser.index.isin(['state', 'time'])
        ser['TOTAL'] = ser[~boolcol].sum()
        #=======================================================================
        # wrap up
        #=======================================================================
        self.osize_df = df.append(ser, ignore_index = True)
        
        logger.debug('finished with df %s and new ser: \n %s'%(str(self.osize_df.shape), ser))

        
        """only writes to file
        objgraph.show_growth(file = logger)
        
        hp_pd.v(self.osize_df)
        
        obj.__sizeof__()
        
        obj.__sizeof__ = oop_getsizeof
        
        ts = oop_getsizeof(obj)
        

            
        def oop_getsizeof(obj):
            ts = 0
            for k, v in obj.__dict__.iteritems():
                try:
                    vs =  deep_getsizeof(v, set())
                except:
                    vs = getsizeof(v)
                ts += vs
                print('for \"%s\' got size = %.0f'%(k, vs))
                
            return ts
            
        
        """
        
        
        return
    
    
    def store_obj_cnt(self, state = None, limit = 5): #log the growth of objects at different intervals
        """ this is a variable column frame"""
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('store_obj_cnt')
        if state is None: state = self.session.state
        
            
        df = self.ocnt_df
        df2 = self.ogrow_df
        df3 = self.ocnt2_df
        
        #=======================================================================
        # data setup
        #=======================================================================
        #get the object list

        ser = pd.Series(index = df.columns.tolist())

        
        ser2 = pd.Series()

        
        indx_s3 = set(df3.columns.tolist())
        indx_s3.update(list(self.session.family_d.keys())) #add all the fmaily objects
        ser3 = pd.Series(index = indx_s3)

        
        #=======================================================================
        # set commons
        #=======================================================================
        d = {'state':state,
             'time':datetime.now().strftime('%Y%m%d-%H-%M-%S')}
        
        for k ,v in d.items():
            ser[k] = v
            ser2[k] = v
            ser3[k] = v
        
        """
        objgraph.show_growth()
        """
        
        if not state == 'init': #first call is not useful
            #=======================================================================
            # add the growth
            #=======================================================================
            for type_name, total_count, increase_delta in objgraph.growth(limit = limit):
                ser[type_name] = int(total_count) #add this entry
                ser2[type_name] = int(increase_delta)
                
            #=======================================================================
            # add the maxes
            #=======================================================================
            for type_name, count in objgraph.most_common_types(limit = limit):
                ser[type_name] = int(count) #add this entry
                
            #=======================================================================
            # fill in the blanks
            #=======================================================================
            ser = fill_in_ocnt(ser)
            ser3 = fill_in_ocnt(ser3)
           
        
        self.ocnt_df = df.append(ser, ignore_index = True) #add dthis to the end
        self.ogrow_df = df2.append(ser2, ignore_index = True)
        self.ocnt2_df = df3.append(ser3, ignore_index = True)
        
        logger.debug('finished with df %s and new ser: \n %s'%(str(self.ocnt_df.shape), ser))
        
        return
            
        
    
    def write(self): #write all your stats frames to file
        logger = self.logger.getChild('write')
        """
        hp_pd.v(df)
        """
        #=======================================================================
        # build the data for each tab
        #=======================================================================
        d = dict()
        for attn in ['state_df', 'ocnt_df', 'ogrow_df','osize_df', 'ocnt2_df']:
            df = getattr(self, attn)
            
            if len(df) >0: d[attn] = df

                
        filename = '%s prof_result'%(self.name) 
        filepath = os.path.join(self.outpath, filename)
                
        hp_pd.write_dfset_excel(d,filepath, logger = logger)
        
        return

        
    
    
    
   