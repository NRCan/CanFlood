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
    
    def __init__(self, tag='session', cid='not_set', cf_fp='',
                 overwrite=True, 
                 out_dir=None, 
                 logger=mod_logger,
                 prec = 4,
                 
                feedback = None, #feed back object
                progressBar = None, #progressBar like object to report progress onto

                 ):
        """
        Dialogs don't call this
        
        """
        #======================================================================
        # get defaults
        #======================================================================
        self.logger = logger.getChild('ComWrkr')
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
        self.setup_feedback(progressBar=progressBar, feedback=feedback)
        
        
        self.logger.info('ComWrkr.__init__ finished')
        
    def setup_feedback(self,
                       progressBar = None,
                       feedback=None):
        """
        feedback setup for all classes
        
        Dialogs:
        
            using a separate function so Dialog's can call 
        """
        
        #progress Bar
        if progressBar is None:
            #Dialog runs should have this attached already
            if hasattr(self, 'progressBar'):
                progressBar = self.progressBar
            
            #standalones create a simple reporter
            else:
                progressBar = MyProgressReporter()
        
        
        #=======================================================================
        # #feedback and progresssetup
        #=======================================================================
        if feedback is None:
            """Q dependent runs should pass QgsProcessingFeedback()"""
            feedback = MyFeedBack(logger=self.logger)
            
        assert callable(progressBar)
        assert callable(feedback)
        
        #=======================================================================
        # connect feedback to progress bar
        #=======================================================================

        
        self.feedback = feedback
        self.progressBar = progressBar
        self.prog = 0 # progress counter ranges from 0 to 100
        
        
        self.logger.info('feedback set as \'%s\' and progressBar: %s'%(
            type(feedback).__name__, type(progressBar).__name__))
        
        
        
    def upd_prog(self, #feedback handling
                 prog_raw, #pass None to reset
                 method='raw', #whether to append value to the progress
                 ): 
        """
        fancy method to push to feedback
        
        object's feeedback should be connected to the status bar
        
        for children functions, connect their feedback tothe parent's
        
        if your QProgressBar is not named 'progressBar', you'll need to set this attribute somewhere
        """
        assert callable(self.progressBar)
        #=======================================================================
        # reseting
        #=======================================================================
        if prog_raw is None:
            self.progressBar.reset()
            return
        
        #=======================================================================
        # setting
        #=======================================================================
        if method=='append':
            prog = min(self.progress + prog_raw, 100)
        elif method=='raw':
            prog = prog_raw
        elif method == 'portion':
            rem_prog = 100-self.progress
            prog = self.progress + rem_prog*(prog_raw/100)
            
        assert prog<=100
        
        #update the feedback worker
        """
        for standalones, this should be a MyFeedBack object
        for Dialog, this will just be a QgsFeedback object
        """
        self.feedback.setValue(prog)
        
        self.progress=prog #set for later
        
        
    def update_cf(self, #update one parameter  control file 
                  new_pars_d, #new paraemeters {section : {valnm : value }}
                  cf_fp = None):
        
        log = self.logger.getChild('update_cf')
        
        #get defaults
        if cf_fp is None: cf_fp = self.cf_fp
        
        assert os.path.exists(cf_fp), 'bad cf_fp: %s'%cf_fp
        
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
        out_fp = os.path.join(out_dir, '%s_smry_plot.%s'%(self.name, fmt))
            
        if os.path.exists(out_fp):
            msg = 'passed output file path already esists :\n    %s'%out_fp
            if overwrite: 
                log.warning(msg)
            else: 
                raise Error(msg)
            
        #write the file
        try: 
            fig.savefig(out_fp, dpi = dpi, format = fmt, transparent=transparent)
            log.info('saved figure to file: %s'%out_fp)
        except Exception as e:
            raise Error('failed to write figure to file w/ \n    %s'%e)
        
        return out_fp
    
class MyFeedBack(object): #simple custom feedback object
    
    def __init__(self, logger=mod_logger, slot=None):
        
        self.logger = logger.getChild('MyFeedBack')
        self.prog = 0
        
        
        #connect the slot
        """
        For Dialog runs, pass a progress bar updating function
        for standalone, this defaults to printing progress
        
        """
        
        if slot is None:
            slot = MyProgressReporter()
            
        assert callable(slot), 'passed bad slot: %s'%slot

        self.logger.debug('connected to slot: %s'%slot.__name__)
        self.slot = slot #placeholder
        

        
    def setProgress(self, prog):
        assert prog + self.prog < 100
        self.prog +=prog
        
        #call the slot function
        """
        this is supposed to behave like a QgsFeedback object
        
        had to fake it becuase I don't want the model scripts to be Q dependent
        
        This will probably cause issues if we try to multi-thread
        """
        self.__signal()
        
        
        
        
    def __signal(self):
        if not self.slot is None:
            self.slot(self.prog)
        

def MyProgressReporter(object): #progressBar like basic progress reporter
    
    def __init__(self):
        self.prog = 0
    
    def reset(self):
        self.prog = 0
        print('    prog=%i'%self.prog)
    
    def setValue(self, prog):
        self.prog= prog
        
        print('    prog=%i'%self.prog)
    


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
    
    
    
  
        
        
       
    