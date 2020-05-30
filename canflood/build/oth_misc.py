'''
Created on Mar. 5, 2020

@author: cefect

converting from rfda formats
'''


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging, datetime

import pandas as pd
import numpy as np

from scipy import interpolate, integrate

start, ymd = datetime.datetime.now(), datetime.datetime.now().strftime('%Y%m%d')

#==============================================================================
# pars---
#==============================================================================
l1 = ['False', 'FALSE', 'false', 'NO', 'No', 'no', 'N', 'n']
l2 = ['True','TRUE','true', 'yes','YES','Yes', 'Y', 'y']
truefalse_d = {
    **dict(zip(l1, np.full(len(l1), False))),
    **dict(zip(l2, np.full(len(l2), True)))
    }


#==============================================================================
# custom imports------
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
    
#plugin runs
else:
    mod_logger = logging.getLogger('rfda') #get the root logger

    from hlpr.exceptions import QError as Error

import hlpr.Q as hQ
from hlpr.basic import view
from model.dmg2 import DFunc


mod_name = 'misc'

class Misc(hQ.Qcoms):
    
    # legacy index numbers
    legacy_ind_d = {0:'id1',1:'address',2:'id2',10:'class', 11:'struct_type', 13:'area', 
                    18:'bsmt_f', 19:'ff_height', 20:'lon',21:'lat', 25:'gel'}
    
    ctag_cLibN_d = None #curve tag location
    

    def __init__(self, 

                  **kwargs):
        

        
        mod_logger.info('%s.__init__ start'%mod_name)
        super().__init__(**kwargs) #initilzie teh baseclass
        
    def crv_lib_smry(self,
                     crv_d, #dictionary of curves
                     logger=None,
                     ):
        if logger is None: logger=self.logger
        log = logger.getChild('crv_lib_smry')
        
        raise Error('gave up')
    
    def crv_consol(self, #scan a set of curve librarires and consolidate necessary curves
                   fdf, #inventory data 
                   cLib_all_d, #a set of curve librarires {libName:{ctag:curve_df}}
                   logger=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger=self.logger
        log = logger.getChild('crvCons')
        mdf = pd.DataFrame()
        #=======================================================================
        # collect tags from inventory
        #=======================================================================
        boolcol = np.logical_and(
            fdf.columns.str.contains('_tag'),
            fdf.columns.str.startswith('f'))
            
        assert boolcol.any()
        log.info('collecting tags from %i tagcolumns \n    %s'%(
            boolcol.sum(),  fdf.columns[boolcol].tolist()))
        
        #loop these columns and collect tags
        ftags_d = dict()
        for coln, cser in fdf.loc[:, boolcol].items():
            ftags_d[coln] = cser.dropna().unique().tolist()
            
            #collect tag count meta
            mdf = mdf.join(cser.value_counts(dropna=False), how='outer')
            
        mdf['total'] = mdf.sum(axis=1, skipna=True).astype(np.int)
        log.info('collected %i tags in inventory across all nests \n    %s'%(
                 len(mdf), mdf['total']))
        
        #=======================================================================
        # build index of curve locations
        #=======================================================================
        if self.ctag_cLibN_d is None:
            d = dict()
            for cLname, cLib_d in cLib_all_d.items():
                for ctag, cdf in cLib_d.items():
                    if ctag.startswith('_'):continue #skip these
                    if not ctag in d:
                        d[ctag] = [cLname]
                    else:
                        d[ctag].append(cLname)
            
            log.info('built index of %i curves from %i librarires'%(len(d), len(cLib_d)))
            self.ctag_cLibN_d = d
            """
            view(pd.Series(d))
            """
        
        ctagL_d = self.ctag_cLibN_d

        #=======================================================================
        # collect tags from curve library
        #=======================================================================
        ctags = set(mdf.index.dropna().tolist())
        log.info('collecting %i ctags from %i loaded'%(len(ctags), len(ctagL_d)))
        
        #check coverage
        s = ctags.difference(ctagL_d.keys())
        if len(s)>0:
            log.warning('%i finv tags not found in passed librarries \n    %s'%(len(s), s))
        
        
        
        res_lib = dict() #results container for curves
               
        #loop through each request and collect thre data
        for ctag in ctags:
            
            #===================================================================
            # get the lib names
            #===================================================================
            libNames = ctagL_d[ctag]
            if len(libNames)>1:
                log.warning('%s found in %i librarires... taking first\n    %s'%(
                    ctag, len(libNames), libNames))
                libName = libNames[0]
            elif len(libNames)==1:
                libName = libNames[0]
            else:
                raise Error('bad length')
                
            #===================================================================
            # get the curve data
            #===================================================================
            cdf = cLib_all_d[libName][ctag]
            
            assert isinstance(cdf,  pd.DataFrame)
            assert len(cdf.columns)==2
            
            
            
            res_lib[ctag] = cdf
        
        
        
        
def run2():
    """
    consolidate librarires
    """
    
    #===========================================================================
    # LMRFRA curves
    #===========================================================================
    tag ='%s_LMFRA'%mod_name
    out_dir = r'C:\LS\03_TOOLS\CanFlood\_outs\crv_consol\20200529'
    data_dir = r'C:\LS\03_TOOLS\CanFlood\_ins\20200529'
    
    
    #directory w/ curve librarires
    cLib_dir=r'C:\LS\03_TOOLS\CanFlood\_ins\20200529\curves'
    
    runpars_d={
        #=======================================================================
        # 'sfd':{
        #     'out_dir':os.path.join(out_dir, 'sfd'),
        #     'finv_fp':os.path.join(data_dir, 'finv_tagSFD_01_20200522_pts.gpkg'),
        #     },
        #=======================================================================
        'nrp':{
            'out_dir':os.path.join(out_dir, 'nrp'),
            'finv_fp':os.path.join(data_dir, 'finv_tagNRP_01_20200521_pts.gpkg'),
            },

        }
    
    #==========================================================================
    # setup session------
    #==========================================================================
    Wrkr = Misc(logger=mod_logger, out_dir=out_dir, tag=tag).ini_standalone()
    logger = mod_logger.getChild(tag)
    log = logger
    #===========================================================================
    # load commons------
    #===========================================================================
    #load all curves found in the directory
    assert os.path.exists(cLib_dir)
    
    #get all spreadsheets in the folder
    cLib_fns = [e for e in os.listdir(cLib_dir) if e.endswith('.xls')]
    
    log.info('loading %i curveLibrarires found in %s'%(len(cLib_fns), cLib_dir))
    cLib_all_d = dict()
    for fn in cLib_fns:
        cLib_d = pd.read_excel(os.path.join(cLib_dir, fn), 
                               sheet_name=None, header=None, index=False)
        
        basefn = os.path.splitext(os.path.split(fn)[1])[0].replace('curves_', '')
        log.info('    %s got %i tabs: %s'%(basefn, len(cLib_d), list(cLib_d.keys())))
        cLib_all_d[basefn] = cLib_d
        
        
    #==========================================================================
    # execute----
    #==========================================================================
    log.info('executing %i'%len(runpars_d))
    for fclass, pars_d in runpars_d.items():
        log = logger.getChild(fclass)
        out_dir = pars_d['out_dir']
        fp = pars_d['finv_fp']
        
        #=======================================================================
        # load inventory
        #=======================================================================
        fvlay = Wrkr.load_vlay(fp, logger=log)
        fdf = hQ.vlay_get_fdf(fvlay, logger=log).drop(['fid'], axis=1, errors='ignore')
        
        log.info('loaded %s'%str(fdf.shape))
        
        #=======================================================================
        # consolidate
        #=======================================================================
        
        Wrkr.crv_consol(fdf, cLib_all_d, logger=log)
        
    

def run1():

    
    out_dir = os.path.join(os.getcwd(),'build','other')

    #==========================================================================
    # dev data: curve conversion
    #==========================================================================
    tag ='%s_nrp'%mod_name
    data_dir = r'C:\LS\03_TOOLS\LML\_keeps2\curves\nrp\nrpPer_20200517125446'
    
    runpars_d={
        'inEq':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_inEq.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'inStk':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_inStk.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'outEq':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_outEq.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        'outStk':{
            'out_dir':os.path.join(data_dir, 'figs'),
            'curves_fp':os.path.join(data_dir, 'curves_nrpPer_01_20200517_outStk.xls'),
            #'dfmt':'{0:.0f}', 'y1lab':'impacts',
            },
        }
     
    #==========================================================================
    # setup session------
    #==========================================================================
         
    Wrkr = Misc(logger=mod_logger, out_dir=out_dir, tag=tag)
    log = mod_logger.getChild(tag)
    
    #===========================================================================
    # load------
    #===========================================================================
    crv_lib_d = dict()
    for dname, d in runpars_d.items():
        fp = d['curves_fp']
        assert os.path.exists(fp), '%s got bad fp: %s'%(dname, fp)
        
        crv_lib_d[dname] = pd.read_excel(fp, sheet_name=None, index=None, header=None)
        
        log.info('loaded %i tabs from %s'%(len(crv_lib_d[dname]), fp))
        
    
    #==========================================================================
    # execute
    #==========================================================================
    #collect summary data from each library
    smry_d = dict()
    for dname, crv_d in crv_lib_d.items():
        smry_d = Wrkr.crv_lib_smry(crv_d)
    
    
    return out_dir
     
 
     
    
if __name__ =="__main__": 
    print('start')
    out_dir = run2()
    #force_open_dir(out_dir)
    print('finished')