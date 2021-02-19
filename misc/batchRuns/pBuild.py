'''
Created on Feb. 17, 2021

@author: cefect

helpful definitions for CanFlood 'build' tools ran from scripts
'''
#===============================================================================
# standard imports
#===============================================================================
import os, datetime, configparser
from qgis.core import QgsCoordinateReferenceSystem


#===============================================================================
# CanFlood plugin imports
#===============================================================================

from hlpr.logr import basic_logger
mod_logger = basic_logger() 


from build.prepr import Preparor
from build.rsamp import Rsamp
from build.lisamp import LikeSampler
from build.validator import Vali

#===============================================================================
# definitions
#===============================================================================

class MasterBuilder(#combine all the build workers for a single run
        Preparor, Rsamp, LikeSampler, Vali):
    """
    needed to avoid reinitilziing qgis each time
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        self.baseClassConv_d = self.get_baseClassConv_d()
        
    def get_baseClassConv_d(self):
        
        baseClassConv_d = dict()
        first=True
        last=None
        for baseClass in self.__class__.__mro__:
            bcName = baseClass.__name__
            if first:
                first=False
            else:
                baseClassConv_d[bcName]=last
            
            last = baseClass
            
        return baseClassConv_d
    
    
def build_models( #generic runner for the risk1 model
            pars, #common running parameters
            tag_d, #assetModel parameters {tag:am_d}}
            plot=True, 
            logger=None,
            ):
    if logger is None: logger=mod_logger
    #===========================================================================
    # #pull form parameters
    #===========================================================================
    base_dir =  pars['base_dir']
    out_dir = pars['out_dir']

    #=======================================================================
    # start worker
    #=======================================================================
    kwargs = {k:pars[k] for k in ['out_dir', 'figsize'] if k in pars}
    wrkr = MasterBuilder(**kwargs,
                    ).ini_standalone(
                        crs=QgsCoordinateReferenceSystem(pars['crs_id']))
                            
    
    #==========================================================================
    # build/execute
    #==========================================================================
    #containers
    rlay_d, dtm_rlay, lpol_d = None, None, None
    cf_d = dict()

    #loop and build each asset model
    for tag, am_d in tag_d.items():
        cf_d[tag] = dict() #add the page
        log = logger.getChild(tag)
        
        #=======================================================================
        # #variables for this asset model
        #=======================================================================
        od1 = os.path.join(out_dir, tag)
        if not os.path.exists(od1):os.makedirs(od1)
        
        wrkr.out_dir = od1
        wrkr.tag = tag
        wrkr.cid = am_d['cid']
        wrkr.logger=log
        #=======================================================================
        # prepare----
        #=======================================================================
        wrkrPR = super(wrkr.baseClassConv_d['Preparor'], wrkr) #get a special worker
        #copy the template
        cf_fp = wrkrPR.copy_cf_template(cf_src=os.path.join(base_dir, pars['cf_tmpl_fn']))
        
        
        #set some basics
        new_pars_d =dict()
        for sect, keys in {
            'parameters':['impact_units', 'rtail', 'event_rels', 'felv'],
            'dmg_fps':['curves'],
            'plotting':['impactfmt_str']
            }.items():
            d = {k:am_d[k] for k in keys if k in am_d} #get these keys where present
            
            if sect == 'parameters':
                d['name']=tag
            
            if len(d)>0:
                new_pars_d[sect] = tuple([d, '#set by build_all.py on %s'%wrkr.today_str])

        wrkrPR.set_cf_pars(new_pars_d)

        log.info('control file created: %s'%cf_fp)
        #=======================================================================
        # convert_finv
        #=======================================================================
        #load the aoi
        if 'aoi_fp' in pars:
            aoi_vlay = wrkrPR.load_vlay(pars['aoi_fp'])
        else:
            aoi_vlay=None
            
        #load the finv
        finv_vlay = wrkrPR.load_vlay(am_d['finv_fp'], aoi_vlay=aoi_vlay)
        
        #convert
        wrkrPR.finv_to_csv(finv_vlay, felv=am_d['felv'])
        del wrkrPR
        
        #=======================================================================
        # sample hazard rasters----
        #=======================================================================
        wrkrHR = super(wrkr.baseClassConv_d['Rsamp'], wrkr) #get a special worker
        
        #=======================================================================
        # #load rasters
        #=======================================================================
        if rlay_d is None:
            rlay_d = wrkrHR.load_rlays(os.path.join(base_dir, pars['raster_dir']),
                                       aoi_vlay=aoi_vlay)
            
        if 'dtm_fp' in pars:
            if dtm_rlay is None:
                dtm_rlay = wrkrHR.load_rlay(pars['dtm_fp'])
                            
        #=======================================================================
        # #run samples
        #=======================================================================
        kwargs = {k:am_d[k] for k in ['dthresh', 'as_inun'] if k in am_d}
        res_vlay = wrkrHR.run(list(rlay_d.values()), finv_vlay, dtm_rlay=dtm_rlay,
                              **kwargs)
    
        #=======================================================================
        # #post
        #=======================================================================
        wrkrHR.check()
        wrkrHR.write_res(res_vlay) #save csv results to file
        wrkrHR.update_cf(cf_fp) #update ocntrol file
        
        if plot:
            fig = wrkrHR.plot_boxes()
            wrkrHR.output_fig(fig)
            
            fig = wrkrHR.plot_hist()
            wrkrHR.output_fig(fig)
        #=======================================================================
        # DTM----
        #=======================================================================
        if am_d['felv']=='ground':
            res_vlay = wrkrHR.run([dtm_rlay], finv_vlay, fname='gels')
            wrkrHR.dtm_check(res_vlay)
            wrkrHR.write_res(res_vlay)
            wrkrHR.upd_cf_dtm()
        
        del wrkrHR
         
        #=======================================================================
        # event variables----
        #=======================================================================
        if 'evals_fn' in pars:
            evals_fp = os.path.join(base_dir, pars['evals_fn'])
            assert os.path.exists(evals_fp), evals_fp
            wrkr.set_cf_pars(
                {
                    'parameters':({'event_probs':'ari'},),
                    'risk_fps':({'evals':evals_fp},)                          
                 }
                )
        
        #=======================================================================
        # pFail----- 
        #=======================================================================
        if 'lpol_fn_d' in pars:
            wrkrLS = super(wrkr.baseClassConv_d['LikeSampler'], wrkr) #get a special worker
              
            #load lpols
            if lpol_d is None:
                lpol_d = wrkrLS.load_lpols(pars['lpol_fn_d'], basedir=pars['lpol_basedir'])
              
            #run it      

            res_df = wrkrLS.run(finv_vlay, lpol_d, 
                                lfield=pars['lfield'], 
                                event_rels=am_d['Levent_rels'])          
            #post
            wrkrLS.check()
            wrkrLS.write_res(res_df)
            wrkrLS.update_cf(cf_fp)
            
            #plot
            if plot:
                fig = wrkrLS.plot_hist()
                wrkrLS.output_fig(fig)
                
                fig = wrkrLS.plot_boxes()
                wrkrLS.output_fig(fig)
            del wrkrLS
            
        #=======================================================================
        # validator----
        #=======================================================================
        wrkrVA =  super(wrkr.baseClassConv_d['Vali'], wrkr) #get a special worker
        from model.risk1 import Risk1
        #from model.risk2 import Risk2
        from model.dmg2 import Dmg2
        
        wrkrVA.config_cf() #initlize the parser
        
        #loop and check each model
        for vtag, modObj in {
            'risk1':Risk1, 
            'dmg2':Dmg2,
            }.items():
            
            if vtag in am_d['validate']:
            
                errors = wrkrVA.cf_check(modObj)
                if not len(errors)==0:
                    """letting those that fail to validate pass"""
                    log.warning('\'%s\' got some errors \n    %s'%(vtag, errors))

                #update control file
                wrkr.cf_mark()
            
        del wrkrVA
        
        #=======================================================================
        # meta----
        #=======================================================================
        cf_d[tag].update({
            'cf_fp':cf_fp,
            'finv_fp':am_d['finv_fp'],
            
            #'use':True,
            })

        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished building')
        wrkr.out_dir = out_dir #reset
    
    log.info('wrap w/ %s'%wrkr.out_dir)
 
    return wrkr.out_dir, cf_d