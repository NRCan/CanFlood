'''
Created on Mar. 8, 2021

@author: cefect
'''

from wFlow.scripts import WorkFlow, Session
        
class Tut1a(WorkFlow): #tutorial 1a
    name='tut1a'
    crsid ='EPSG:3005'
    pars_d = {
            
            #data files
            'finv_fp':r'tutorials\1\finv_tut1a.gpkg',
            'raster_dir':r'tutorials\1\haz_rast',
            'evals_fp':r'tests\_data\all2\evals_4_tut1a.csv',
            #'fpol_dir':r'tutorials\1\haz_fpoly',
            
            #run controls
            'felv':'datum', 'validate':'risk1'
                    }
    
    tpars_d = { #kwargs for individual tools
        'Risk1':{
            'res_per_asset':True,
            }
        }
    
    
    
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
        
        """
        self.res_d.keys()
        self.data_d.keys()
        """
        
class Tut2(WorkFlow): #tutorial 1a
    
    crsid ='EPSG:3005'
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'finv_fp':r'tutorials\2\finv_tut2.gpkg',
                'raster_dir':r'tutorials\2\haz_rast',
                'evals_fp':r'tests\_data\all2\evals_4_tut2a.csv',
                'curves_fp':r'tests\_data\all2\IBI2015_DamageCurves.xls',
                'dtm_fp':r'tutorials\2\dtm_tut2.tif',
                'fpol_dir':r'tutorials\2\haz_fpoly',
                
                #run controls
                'felv':'ground', 'validate':'dmg2', 'prec':6,
                
                #plot controls
                'impactfmt_str':',.0f',
                'color':'red'
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
            'evals_fp':r'tests\_data\all2\evals_4_tut2b.csv',
            'event_rels':'mutEx', #for RiskModel.. nto likeSamp
            })
        
        #=======================================================================
        # self.tpars_d['LikeSampler'].update({
        #     'event_rels':'mutEx'})
        #=======================================================================
        
    

    
    
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
        d= self.risk2(logger=log, plot=False, prep_kwargs={'event_slice':True})
        self.res_d = {**self.res_d, **d}
        
        #extra risk plots
        self.plot_risk_ttl(logger=log)


#===============================================================================
# executeors------------
#===============================================================================
wFlow_l = [Tut2b] #used below and by test scripts to bundle workflows

if __name__ == '__main__':
    
    wrkr = Session(write=True, plot=True)
    #===========================================================================
    # build test pickesl
    #===========================================================================
    rlib = wrkr.run(wFlow_l)
    

    