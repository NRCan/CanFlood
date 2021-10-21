'''
Created on Mar. 8, 2021

@author: cefect
'''

from wFlow.scripts import WorkFlow, Session
#===============================================================================
# TUTORIAL 1------
#===============================================================================
class Tut1a(WorkFlow): #tutorial 1a
    name='tut1a'
    crsid ='EPSG:3005'
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'finv_fp':r'tutorials\1\finv_tut1a.gpkg',
                'raster_dir':r'tutorials\1\haz_rast',
                'evals_fp':r'tests\_data\tuts\evals_4_tut1a.csv',
                #'fpol_dir':r'tutorials\1\haz_fpoly',
                
                #run controls
                'felv':'datum', 'validate':'risk1'
                        }
        
        self.tpars_d = { #kwargs for individual tools
            'Risk1':{
                'res_per_asset':True,
                }
            }
        super().__init__(**kwargs)
    
    
    
    def run(self,  #workflow for tutorial 1a

              ):
        log = self.logger.getChild('r')
        
        #build
        self.res_d = self.tb_build(logger=log, fpoly=False)
        
        #model.risk1
        d= self.risk1(logger=log)
        self.res_d = {**self.res_d, **d}
        
        #results.djoin
        d = self.djoin(logger=log)
        self.res_d = {**self.res_d, **d}
        
        
        log.info('finished w/ %i: %s'%(len(self.res_d),  list(self.res_d.keys())))
        

#===============================================================================
# Tutorial 2-------------
#===============================================================================
class Tut2(WorkFlow): #tutorial 1a
    
    crsid ='EPSG:3005'
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'finv_fp':r'tutorials\2\finv_tut2.gpkg',
                'raster_dir':r'tutorials\2\haz_rast',
                'evals_fp':r'tests\_data\tuts\evals_4_tut2a.csv',
                'curves_fp':r'tests\_data\tuts\IBI2015_DamageCurves.xls',
                'dtm_fp':r'tutorials\2\dtm_tut2.tif',
                'fpol_dir':r'tutorials\2\haz_fpoly',
                
                #run controls
                'felv':'ground', 'validate':'dmg2', 'prec':6,
                
                #plot controls
                'impactfmt_str':',.0f',
                
                        }
        
        self.tpars_d = {#kwargs for individual tools
           'Risk2':{
                'res_per_asset':True,
                },
            'LikeSampler':{
                'lfield':'p_fail',
                'event_rels':'mutEx'
                }
    
            }
        super().__init__(**kwargs)
    
class Tut2a(Tut2): #tutorial 1a
    name='tut2a'
    attriMode = False
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.pars_d.update({
            'color':'red'
            })

        
    def run(self,  #workflow for tutorial 1a

              ):
        log = self.logger.getChild('r')
        
        #build
        self.res_d = self.tb_build(logger=log, fpoly=False)
        
        #model.dmg2
        d = self.dmg2(logger=log, bdmg_smry=False, dmgs_expnd=True)
        self.res_d = {**self.res_d, **d}
        
        #model.risk2
        d= self.risk2(logger=log, plot=False)
        self.res_d = {**self.res_d, **d}
        
        #extra risk plots
        self.plot_risk_ttl(logger=log)

class Tut2b(Tut2): #tutorial 1a
    name='tut2b'
    attriMode = True
    
    rlay_fps = [
        r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\haz_frast\haz_1000_fail_A_tut2.tif',
        r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\haz_rast\haz_0050_tut2.tif',
        r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\haz_rast\haz_0100_tut2.tif',
        r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\haz_rast\haz_0200_tut2.tif',
        r'C:\LS\03_TOOLS\CanFlood\_git\tutorials\2\haz_rast\haz_1000_tut2.tif',        
        ]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        

        self.pars_d.update({
            'evals_fp':r'tests\_data\tuts\evals_4_tut2b.csv',
            'event_rels':'mutEx', #for RiskModel.. nto likeSamp
            })
        
        self.tpars_d['Risk2'].update({
            'prep_kwargs':{'event_slice':True},
            })
        

    def run(self,  #workflow for tutorial 1a

              ):
        log = self.logger.getChild('r')
        
        #load teh rasters
        """cant use directory loaders becuase we are only using some of the layers"""
        rlay_d = self.load_layers(self.rlay_fps)
        
        """no.. wana use the name matcher
        fpol_d = self.load_layers(self.fpol_fps, layType = 'vector')"""
        
        #build
        self.res_d = self.tb_build(logger=log, fpoly=True, rlay_d=rlay_d)
        
        #model.dmg2
        d = self.dmg2(logger=log, bdmg_smry=False, dmgs_expnd=True)
        self.res_d = {**self.res_d, **d}
        
        #model.risk2
        d= self.risk2(logger=log, plot=False)
        self.res_d = {**self.res_d, **d}
        
        #extra risk plots
        d = self.plot_failSplit(logger=log)
        self.res_d = {**self.res_d, **d}

class Tut2c(Tut2): #tutorial 1a
    name='tut2c'
    attriMode = True
    
    """layers are in two directores"""
    rlay_dirs = [
        r'tutorials\2\haz_frast',
        r'tutorials\2\haz_rast',
        ]
    

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        

        self.pars_d.update({
            'evals_fp':r'tests\_data\tuts\evals_4_tut2c.csv',
            })
        

    def run(self, 
              ):
        log = self.logger.getChild('r')
        
        #=======================================================================
        # load rasters
        #=======================================================================
        rlay_d = self.load_layers_dirs(self.rlay_dirs, base_dir=self.base_dir)
        
        
        #build
        self.res_d = self.tb_build(logger=log, fpoly=True, rlay_d=rlay_d)
        
        #model.dmg2
        d = self.dmg2(logger=log, bdmg_smry=False, dmgs_expnd=True)
        self.res_d = {**self.res_d, **d}
        
        #model.risk2
        d= self.risk2(logger=log, plot=True)
        self.res_d = {**self.res_d, **d}
        
class Tut2c_mutex(Tut2c): #tutorial 1a
    name='Tut2c_mutex'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        

        self.pars_d.update({
            'event_rels':'mutEx', #for RiskModel.. nto likeSamp

            })
        
    def run(self):
        log = self.logger.getChild('r')
        #do the base execution
        super(Tut2c_mutex, self).run()
        
        """added the unique tools from tutorial 2a and 2b 
            to make the full test suite more efficient"""
        #results. risk plots (from tutorial 2a)
        self.plot_risk_ttl(logger=log)
        
        #results. fail plots (from tutorial 2b)
        d = self.plot_failSplit(logger=log)
        self.res_d = {**self.res_d, **d}
        
        #set your cf_fp for your sibling
        self.session.data_d[self.name] = {'cf_fp':self.cf_fp}

        
class Tut2c_max(Tut2c): #tutorial 1a
    name='Tut2c_max'
    sibName = 'Tut2c_mutex'
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        

        self.pars_d.update({
            'event_rels':'max', #for RiskModel.. nto likeSamp
            'color':'red',
            'linestyle':'solid'
            })
        
    def run(self):
        log = self.logger.getChild('r')
        assert self.sibName in self.session.data_d, 'missing siblings result'
        
        #do the base execution
        super(Tut2c_max, self).run()
        

        
        #results.compare
        cf_fp_sib = self.session.data_d[self.sibName]['cf_fp']
        
        d = self.compare({self.name:self.cf_fp, self.sibName:cf_fp_sib},
                     logger=log)
        self.res_d = {**self.res_d, **d}
        
#===============================================================================
# Tutrorial 4-----------
#===============================================================================
class Tut4(WorkFlow): #tutorial 1a
    
    crsid ='EPSG:3005'
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'raster_dir':r'tutorials\4\haz_rast',
                'evals_fp':r'tests\_data\tuts\evals_4_tut4a.csv',
                'dtm_fp':r'tutorials\4\dtm_ct2.tif',

                
                #run controls
                'felv':'datum', 'validate':'dmg2', 'prec':6,
                
                        }
        
        self.tpars_d = { #kwargs for individual tools
            'Risk1':{
                'res_per_asset':True,
                }
            }
        super().__init__(**kwargs)
        
        
    def run(self,  #workflow for tutorial 1a

              ):
        log = self.logger.getChild('r')
        
        #build
        self.res_d = self.tb_build(logger=log, fpoly=False)
        
        #model.risk1
        d= self.risk1(logger=log)
        self.res_d = {**self.res_d, **d}
        
        #results.djoin
        d = self.djoin(logger=log)
        self.res_d = {**self.res_d, **d}
        
        
        log.info('finished w/ %i: %s'%(len(self.res_d),  list(self.res_d.keys())))
    
class Tut4a(Tut4):
    name = 'tut4a'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.pars_d.update({
            'finv_fp':r'tutorials\4\finv_tut4a_polygons.gpkg',
            'as_inun':True, 'dthresh':0.5,
            })

class Tut4b(Tut4):
    name = 'tut4b'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.pars_d.update({
            'finv_fp':r'tutorials\4\finv_tut4b_lines.gpkg',
            'as_inun':True, 'dthresh':0.5,
            })



        
        
#===============================================================================
# Tutorial 5-------------
#===============================================================================
class Tut5a(WorkFlow): #tutorial 1a
    name = 'tut5a'
    crsid ='EPSG:3978'
    prec = 6
    
    
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'raster_dir':r'tests\_data\tuts\5a', #using local data instead of web data for the test
                'finv_fp':r'tests\_data\tuts\5a\NPRI_lay3_3978.gpkg',
                'aoi_fp':r'tutorials\5\tut5_aoi_3978.gpkg',
                #'evals_fp':r'tests\_data\tuts\evals_5_tut5a.csv',
                
                #run controls
                'felv':'datum', 'validate':'risk1', 
                }
        
        self.finvConstructKwargs = {
            'nest_data':{
                'scale':1.0, 'elv':0.0
                },
            'nestID':0,
            }
        
        self.rsampPrepKwargs = {
            'clip_rlays':True, 'allow_rproj':True, 'allow_download':False, 
            'scaleFactor':0.01,
            }
        

                
        super().__init__(cid ='OBJECTID',
                         **kwargs)
        
    def run(self,  #workflow for tutorial 1a

              ):
        log = self.logger.getChild('r')
        
        #build
        """using custom build routine for shortened tutorial"""
        #=======================================================================
        # self.res_d = self.tb_build(logger=log, fpoly=False, 
        #                            finvConstructKwargs=self.finvConstructKwargs,
        #                            rsampPrepKwargs=self.rsampPrepKwargs)
        #=======================================================================
        pars_d = self.pars_d
        res_d = dict()
        #=======================================================================
        # prepare
        #=======================================================================
        cf_fp = self.prep_cf(pars_d, logger=log) #setuip the control file
        

        self.prep_finvConstruct(pars_d, **self.finvConstructKwargs)
        
        res_d['finv'] = self.prep_finv(pars_d, logger=log)
        

        #=======================================================================
        # raster sample
        #=======================================================================

        self.rsamp_prep(pars_d, logger=log, **self.rsampPrepKwargs)
        res_d['expos'] = self.rsamp_haz(pars_d, logger=log)
        
        #=======================================================================
        # collect some data for the tests
        #=======================================================================
        
        #raster layer crs
        res_d['rlay_crs_d'] = {k:lay.crs().authid() for k, lay in self.data_d['rlay_d'].items()}
            
        

        self.res_d = res_d
        log.info('finished w/ %i: %s'%(len(self.res_d),  list(self.res_d.keys())))
        
        
        
        
        
        
#===============================================================================
#Tutorial 6---------
#===============================================================================
ifz_fp = r'tutorials\6\dike_influence_zones.gpkg'
class Tut6a(WorkFlow): #tutorial 1a
    name = 'tut6a'
    crsid ='EPSG:3005'
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'raster_dir':r'tutorials\6\haz_rast',
                'evals_fp':r'tests\_data\tuts\evals_4_tut4a.csv',
                'dtm_fp':r'tutorials\6\dtm.tif',
                'dikes_fp':r'tutorials\6\dikes.gpkg',
                'dcurves_fp':r'tutorials\6\dike_fragility_20210201.xls',

                'eifz_d':{
                    '0010_noFail':ifz_fp,
                    '0050_noFail':ifz_fp,
                    '0200_noFail':ifz_fp,
                    '1000_noFail':ifz_fp,
                    }
                
                #run controls

                        }
        
        self.tpars_d = { #kwargs for individual tools

            }
        

        super().__init__(dikeID='ID', 
                         **kwargs)
        
        
    def run(self,  #workflow for tutorial 1a

              ):
        log = self.logger.getChild('r')
        
        self.res_d = self.tb_dikes()
        
#===============================================================================
#Tutorial 7---------
#===============================================================================
"""value sampling types"""
class Tut7(WorkFlow): #tutorial 1a
    
    crsid ='EPSG:3005'
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'raster_dir':r'tutorials\7\haz_rast',
                'evals_fp':r'tests\_data\tuts\evals_4_tut7.csv',
                'dtm_fp':r'tutorials\7\dtm_ct2.tif',

                
                #run controls
                'felv':'ground', 'validate':'dmg2', 'prec':3,
                
                        }
        
        self.tpars_d = { #kwargs for individual tools
            'Risk1':{
                'res_per_asset':True,
                }
            }
        super().__init__(**kwargs)
        
        
    def run(self,  #workflow for tutorial 1a

              ):
        log = self.logger.getChild('r')
        
        #build
        self.res_d = self.tb_build(logger=log, fpoly=False)
        
        #model.risk1
        d= self.risk1(logger=log)
        self.res_d = {**self.res_d, **d}
        
        #results.djoin
        d = self.djoin(logger=log)
        self.res_d = {**self.res_d, **d}
        
        
        log.info('finished w/ %i: %s'%(len(self.res_d),  list(self.res_d.keys())))
        
class Tut7a(Tut7):
    name = 'Tut7a'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
        self.pars_d.update({
            'finv_fp':r'tutorials\7\finv_tut7_polys.gpkg', #setup for R2.. but just using R1

            })
        
        self.tpars_d.update({
             'Rsamp':{'psmp_fieldName':'sample_stat'}
            })
        
        
#===============================================================================
# executeors------------
#===============================================================================
wFlow_l = [Tut7a] #used below and by test scripts to bundle workflows

if __name__ == '__main__':
    
    wrkr = Session(projName='tuts', write=True, plot=False)
    rlib = wrkr.run(wFlow_l)
    

    