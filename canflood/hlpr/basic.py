'''
Created on Feb. 7, 2020

@author: cefect

helper functions w/o qgis api
'''


#==============================================================================
# dependency check
#==============================================================================



#==============================================================================
# imports------------
#==============================================================================
#python
import os, configparser, logging
import pandas as pd
import numpy as np

mod_logger = logging.getLogger('hp') #creates a child logger of the root

#==============================================================================
# custom
#==============================================================================
#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   

    
#plugin runs
else:
    mod_logger = logging.getLogger('common') #get the root logger

from hlpr.exceptions import QError as Error

#==============================================================================
# functions-------------
#==============================================================================
class ComWrkr(object): #common methods for all classes
    
    progressBar = None
    feedback = None
    
    #mandatory keys for curves
    crv_keys = ('tag', 'exposure')
    
    def __init__(self, tag='session', cid='not_set', cf_fp='',
                 overwrite=True, 
                 out_dir=None, 
                 logger=mod_logger,
                 prec = 4,
                 
                feedback = None, #feed back object
                progressBar = None, #progressBar like object to report progress onto
                LogLevel = None, #logging level for defualt feedbacker
                 ):
        """
        Dialogs don't call this
        
        """
        #======================================================================
        # get defaults
        #======================================================================
        self.logger = logger
        #setup output directory
        if out_dir is None: out_dir = os.getcwd()
        
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            self.logger.info('created requested output directory: \n    %s'%out_dir)

        #======================================================================
        # attach
        #======================================================================
        
        self.tag = tag
        self.cid = cid
        self.overwrite=overwrite
        self.out_dir = out_dir
        self.cf_fp = cf_fp
        self.prec = prec
        
        #=======================================================================
        # feedback
        #=======================================================================
        self.setup_feedback(progressBar=progressBar, feedback=feedback, LogLevel=LogLevel)
        
        
        self.logger.debug('ComWrkr.__init__ finished')
        
    def setup_feedback(self,
                       progressBar = None,
                       feedback=None,
                       LogLevel = None,
                       ):
        """
        feedback setup for all classes
        
        Dialogs:
            using a separate function so Dialog's can call 
            
        Qgis workers
            MyFeedBackQ built during Qcoms.__init__() 
            
        Standard workers
            building dummy MyFeedBack here 
            
            
        Standalone runs
            building dummy progressBar
        Qplugin runs
            expects a QprogressBar widget named progressBar
        """
        
        #progress Bar
        if progressBar is None:
            """
            Dialog runs should have this attached already
                just pull the attribute
            
            other runs we build a dummy progress reporter
            """
            #Dialog runs
            #===================================================================
            # if hasattr(self, 'progressBar'):
            #     progressBar = self.progressBar
            #===================================================================
            if not self.progressBar is None:
                progressBar = self.progressBar
            
            #standalones create a simple reporter
            else:
                progressBar = MyProgressReporter(LogLevel=LogLevel)
        
        
        #=======================================================================
        # #feedback and progresssetup
        #=======================================================================
        if feedback is None:
            """
            build a basic feedbacker for nonQ runs
            Q dependent runs should pass MyFeedBackQ()"""
            feedback = MyFeedBack()
            
        #set feedback's logger
        """becuase Q runs have to build the ffeedbacker before ComWrker can set th elogger
        just forcing it here"""
        feedback.logger=self.logger
        #=======================================================================
        # check the passed objects
        #=======================================================================
        #progressBar
        assert hasattr(progressBar, 'setValue')
        assert callable(progressBar.setValue)
        
        assert hasattr(feedback, 'setProgress')
        assert callable(feedback.setProgress)
        
        #=======================================================================
        # connect feedback to progress bar
        #=======================================================================
        #QgsFeedback like
        if hasattr(feedback, 'progressChanged'):
            feedback.progressChanged.connect(progressBar.setValue)
            
        #dummy feedbacker
        elif hasattr(feedback, 'slots'):
            feedback.slots = [progressBar.setValue]
            
        else:
            raise Error('unrecognized feedback object: %s'%type(feedback))
        
        #=======================================================================
        # attach
        #=======================================================================
        self.feedback = feedback
        self.progressBar = progressBar

        
        
        self.logger.debug('feedback set as \'%s\' and progressBar: %s'%(
            type(feedback).__name__, type(progressBar).__name__))
        
        
        

        
        
    def update_cf(self, #update one parameter  control file 
                  new_pars_d, #new paraemeters {section : {valnm : value }}
                  cf_fp = None):
        
        log = self.logger.getChild('update_cf')
        
        #get defaults
        if cf_fp is None: cf_fp = self.cf_fp
        
        assert os.path.exists(cf_fp), 'bad cf_fp: \n    %s'%cf_fp
        
        #initiliae the parser
        pars = configparser.ConfigParser(allow_no_value=True)
        _ = pars.read(cf_fp) #read it from the new location
        
        #loop and make updates
        for section, val_t in new_pars_d.items():
            assert isinstance(val_t, tuple), '\"%s\' has bad subtype: %s'%(section, type(val_t))
            assert section in pars, 'requested section \'%s\' not in the pars!'%section
            
            for subval in val_t:
                #value key pairs
                if isinstance(subval, dict):
                    for valnm, value in subval.items():
                        assert isinstance(value, str), \
                        'got bad type on %s.%s: \'%s\''%(section, valnm, type(value))
                        
                        pars.set(section, valnm, value)
                        
                #single values    
                elif isinstance(subval, str):
                    pars.set(section, subval)
                    
                else:
                    raise Error('unrecognized value type: %s'%type(subval))
                
        
        #write the config file 
        with open(cf_fp, 'w') as configfile:
            pars.write(configfile)
            
        log.info('updated contyrol file w/ %i pars at :\n    %s'%(
            len(new_pars_d), cf_fp))
        
        return
    
    
    def output_df(self, #dump some outputs
                      df, 
                      out_fn,
                      out_dir = None,
                      overwrite=None,
                      write_index=True,
            ):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.out_dir
        if overwrite is None: overwrite = self.overwrite
        log = self.logger.getChild('output')
        
        #======================================================================
        # prechecks
        #======================================================================
        assert isinstance(out_dir, str), 'unexpected type on out_dir: %s'%type(out_dir)
        assert os.path.exists(out_dir), 'requested output directory doesnot exist: \n    %s'%out_dir
        assert isinstance(df, pd.DataFrame)
        assert len(df) >0, 'no data'
        
        
        #extension check
        if not out_fn.endswith('.csv'):
            out_fn = out_fn+'.csv'
        
        #output file path
        out_fp = os.path.join(out_dir, out_fn)
        
        #======================================================================
        # checeks
        #======================================================================
        if os.path.exists(out_fp):
            log.warning('file exists \n    %s'%out_fp)
            if not overwrite:
                raise Error('file already exists')
            

        #======================================================================
        # writ eit
        #======================================================================
        df.to_csv(out_fp, index=write_index)
        
        log.info('wrote to %s to filezzz: \n    %s'%(str(df.shape), out_fp))
        
        self.out_fp = out_fp #set for other methods
        
        return out_fp
    
    def output_fig(self, fig,
                   out_dir = None, overwrite=None,
                   
                   #figure file controls
                 fmt='svg', 
                  transparent=True, 
                  dpi = 150,):
        #======================================================================
        # defaults
        #======================================================================
        if out_dir is None: out_dir = self.out_dir
        if overwrite is None: overwrite = self.overwrite
        log = self.logger.getChild('output')
        
        #======================================================================
        # output
        #======================================================================
        #file setup
        try:
            fname = fig._suptitle.get_text()
        except:
            fname = self.name
            
        out_fp = os.path.join(out_dir, '%s.%s'%(fname, fmt))
            
        if os.path.exists(out_fp):
            msg = 'passed output file path already esists :\n    %s'%out_fp
            if overwrite: 
                log.warning(msg)
            else: 
                raise Error(msg)
            
        #write the file
        try: 
            fig.savefig(out_fp, dpi = dpi, format = fmt, transparent=transparent)
            log.info('saved figure to file: \n    %s'%out_fp)
        except Exception as e:
            raise Error('failed to write figure to file w/ \n    %s'%e)
        
        return out_fp
    
    def check_curve(self, #validate the passed curve_d  
                    crv_d,
                    logger=None):
        if logger is None: logger=self.logger
        log = logger.getChild('check_curve')
        
        assert isinstance(crv_d, dict)
        
        log.debug('on %i'%len(crv_d))
        
        #srip hitespace
        crv_d1 = dict()
        for k, v in crv_d.items():
            if isinstance(k, str):
                newk = k.strip()
            else:
                newk = k
                
            crv_d1[newk] = v
            
        
        #check keys
        l = set(self.crv_keys).difference(crv_d1.keys())
        assert len(l)==0, 'curve is missing keys: %s'%l

        return True
    
class MyFeedBack(object): #simple custom feedback object
    
    def __init__(self, 
                 logger=mod_logger, 
                 slot=None, #function to pass to feedback signal (must accept 'prog')
                 ):
        
        self.logger = logger.getChild('MyFeedBack')
        self.prog = 0
        
        
        #connect the slot
        """
        For Dialog runs, pass a progress bar updating function
        for standalone, this defaults to printing progress
        
        slots are connected w/ ComWrkr.setup_feedback()
        
        """
        if not slot is None:
            self.slots = [slot] #placeholder
        else:
            self.slots = []
        

        
    def setProgress(self, prog): #basic progress setter. mimics QgsFeedback
        
        #assert len(self.slots)>0
        assert prog <= 100
        self.prog =prog
        
        #call the slot function
        """
        this is supposed to behave like a QgsFeedback object
        
        had to fake it becuase I don't want the model scripts to be Q dependent
        
        This will probably cause issues if we try to multi-thread
        """
        self.__signal()
        
    def progress(self): #mimics QgsFeedback 
        return self.prog
        
    def upd_prog(self, #advanced progress handling
             prog_raw, #pass None to reset
             method='raw', #whether to append value to the progress
             ): 
            
        #=======================================================================
        # defaults
        #=======================================================================
        #get the current progress
        progress = self.progress() 
    
        #===================================================================
        # prechecks
        #===================================================================
        #make sure we have some slots connected
        assert len(self.slots)>0
        
        #=======================================================================
        # reseting
        #=======================================================================
        if prog_raw is None:
            for slot in self.slots:
                slot.reset()
            return
        
        #=======================================================================
        # setting
        #=======================================================================
        if method=='append':
            prog = min(progress + prog_raw, 100)
        elif method=='raw':
            prog = prog_raw
        elif method == 'portion':
            rem_prog = 100-progress
            prog = progress + rem_prog*(prog_raw/100)
            
        assert prog<=100
        
        #===================================================================
        # emit signalling
        #===================================================================
        self.setProgress(prog)
        

        

    def __signal(self): #execut eall the attached slots
        for func in self.slots:
            func(self.prog)

        

class MyProgressReporter(object):   #progressBar like basic progress reporter
                        
                         
    """
    may be an issue for multi-threading
    """
    
    def __init__(self,
                  LogLevel=None, #control outputs
                  ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if LogLevel is None:
            LogLevel= 10
        
        self.level=LogLevel
        self.prog = 0
    
    def reset(self):
        self.prog = 0
        print('    prog reset')
    
    def setValue(self, prog):
        self.prog= prog
        
        """disabling for console runs???
        if self.level<=10:
            print('    prog=%i'%self.prog)"""
    


def view(df):
    if isinstance(df, pd.Series):
        df = pd.DataFrame(df)
        

    
    import webbrowser
    #import pandas as pd
    from tempfile import NamedTemporaryFile

    with NamedTemporaryFile(delete=False, suffix='.html', mode='w') as f:
        #type(f)
        df.to_html(buf=f)
        
    webbrowser.open(f.name)
    
    
def is_null(obj): #check if the object is none

    if obj is None:
        return True
    """might not work for non string multi element objects"""
    if np.any(pd.isnull(obj)):
        return True
    
    #excel checks
    if obj in ('', 0, '0', '0.0'):
        return True
    
    return False

def linr( #fancy check if left elements are in right elements
        ldata_raw, rdata_raw, 
                  lname_raw = 'left',
                  rname_raw = 'right',
                  sort_values = False, #whether to sort the elements prior to checking
                  result_type = 'bool', #format to return result in
                    #missing: return a list of left elements not in the right
                    #matching: list of elements in both
                    #boolar: return boolean where True = left element found in right (np.isin)
                    #bool: return True if all left elements are found on the right
                    #exact: return True if perfect element match
                  invert = False, #flip left and right
                  
                  #expectations
                  dims= 1, #expected dimeions
                  
                  fancy_log = False, #whether to log stuff                  
                  logger=mod_logger
                  ):
    
    #===========================================================================
    # precheck
    #===========================================================================
    if isinstance(ldata_raw, str):
        raise Error('expected array type')
    if isinstance(rdata_raw, str):
        raise Error('expected array type')
    
    #===========================================================================
    # do flipping
    #===========================================================================
    if invert:
        ldata = rdata_raw
        lname = rname_raw
        rdata = ldata_raw
        rname = lname_raw
    else:
        ldata = ldata_raw
        lname = lname_raw
        rdata = rdata_raw
        rname = rname_raw
        
        
    #===========================================================================
    # data conversion
    #===========================================================================
    if not isinstance(ldata, np.ndarray):
        l_ar = np.array(list(ldata))
    else:
        l_ar = ldata
        
    if not isinstance(rdata, np.ndarray):
        r_ar = np.array(list(rdata))
    else:
        r_ar = rdata
        
    #===========================================================================
    # do any sorting
    #===========================================================================
    if sort_values:
        l_ar = np.sort(l_ar)
        r_ar = np.sort(r_ar)
        
        #check logic validty of result type
        if result_type =='boolar':
            raise Error('requested result type does not make sense with sorted=True')

        
    #===========================================================================
    # pre check
    #===========================================================================
    #check for empty containers and uniqueness
    for data, dname in (
        (l_ar, lname),
        (r_ar, rname)
        ):
        #empty container
        if data.size == 0:
            raise Error('got empty container for \'%s\''%dname)
        
        #simensions/shape
        """probably not necessary"""
        if not len(data.shape) == dims:
            raise Error('expected %i dimensions got %s'%(
                dims, str(data.shape)))
            
        
        if not pd.Series(data).is_unique:
            #get detailed print outs
            ser = pd.Series(data)
            boolidx = ser.duplicated(keep=False)            
            
            raise Error('got %i (of %i) non-unique elements for \'%s\' \n    %s'%(
                boolidx.sum(), len(boolidx), dname, ser[boolidx]))
        
        #=======================================================================
        # #uniqueness
        # if not data.size == np.unique(data).size:
        #     raise Error('got non-unique elements for \'%s\' \n    %s'%(dname, data))
        #=======================================================================
        
        """data
        data.shape
        
        """
        

    

    #===========================================================================
    # do the chekcing
    #===========================================================================

    boolar = ~np.isin(l_ar, r_ar) #misses from left to right
    
    if fancy_log:
        
        log = logger.getChild('left_in_right')
        msg = ('%i (of %i) elements in \'%s\'  not found in \'%s\': \n    mismatch: %s \n    \'%s\' %s: %s \n    \'%s\' %s: %s'
                    %(boolar.sum(),len(boolar), lname, rname, 
                      l_ar[boolar].tolist(),
                      lname, str(l_ar.shape), l_ar.tolist(), 
                      rname, str(r_ar.shape), r_ar.tolist()
                      )
                    )
        if np.any(boolar):
            logger.debug(msg)
        elif result_type=='exact' and (not np.array_equal(l_ar, r_ar)):
            logger.debug(msg)
        
    #===========================================================================
    # reformat and return result
    #===========================================================================
    if result_type == 'boolar': #left elements in the right
        return ~boolar
    elif result_type == 'bool': #all left elements in the right
        if np.any(boolar):
            return False
        else:
            return True
        
    elif result_type == 'missing':
        return l_ar[boolar].tolist()
    
    elif result_type == 'matching':
        return l_ar[~boolar].tolist()
    
    elif result_type == 'exact':
        return np.array_equal(l_ar, r_ar)
    
    else:
        raise Error('unrecognized result format')
    
def get_basefn(filepath):
    ftail, fhead = os.path.split(filepath)
    basefn, ext = os.path.splitext(fhead)
    return basefn
    
def force_open_dir(folder_path_raw, logger=mod_logger): #force explorer to open a folder
    logger = logger.getChild('force_open_dir')
    
    if not os.path.exists(folder_path_raw):
        logger.error('passed directory does not exist: \n    %s'%folder_path_raw)
        return False
        
    import subprocess
    
    #===========================================================================
    # convert directory to raw string literal for windows
    #===========================================================================
    try:
        #convert forward to backslashes
        folder_path=  folder_path_raw.replace('/', '\\')
    except:
        logger.error('failed during string conversion')
        return False
    
    try:

        args = r'explorer "' + str(folder_path) + '"'
        subprocess.Popen(args) #spawn process in explorer
        'this doesnt seem to be working'
        logger.info('forced open folder: \n    %s'%folder_path)
        return True
    except:
        logger.error('unable to open directory: \n %s'%dir)
        return False
    
    
if __name__ =="__main__": 
    
    #===========================================================================
    # requirements file
    #===========================================================================
    import pip
  
        
        
       
    