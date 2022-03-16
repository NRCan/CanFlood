'''
Created on Mar. 16, 2022

@author: cefect

re-creating 

https://github.com/NRCan/CanFlood/issues/31
'''

from wFlow.tutorials import WorkFlow, Session


class Tut2(WorkFlow): #tutorial 1a
    
    name='issue31'
    crsid ='EPSG:26910'
    res_d = dict()
    def __init__(self, **kwargs):
        self.pars_d = {
                
                #data files
                'finv_fp':r'C:\LS\02_WORK\IBI\202011_CanFlood\01_GEN\01_INOUT\2022 03 10 - Ben - store inv error\finv_tagSFD_20200608_pts_c.gpkg',
                #===============================================================
                # 'raster_dir':r'tutorials\2\haz_rast',
                # 'evals_fp':r'tests\_data\tuts\evals_4_tut2a.csv',
                # 'curves_fp':r'tests\_data\tuts\IBI2015_DamageCurves.xls',
                # 'dtm_fp':r'tutorials\2\dtm_tut2.tif',
                # 'fpol_dir':r'tutorials\2\haz_fpoly',
                #===============================================================
                
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
        super().__init__(cid='zid2', **kwargs)
        
        
    def run(self,  #workflow for tutorial 1a
            pars_d=None,
              ):
        log = self.logger.getChild('r')
        
        if pars_d is None: pars_d = self.pars_d
        res_d = self.res_d
        
        cf_fp = self.prep_cf(pars_d, logger=log) #setuip the control file
        
        res_d['finv'] = self.prep_finv(pars_d, logger=log)
        
        if 'curves_fp' in pars_d:
            res_d['curves'] = self.prep_curves(pars_d, logger=log)
        
        #=======================================================================
        # #model.dmg2
        # d = self.dmg2(logger=log, bdmg_smry=False, dmgs_expnd=True)
        # self.res_d = {**self.res_d, **d}
        # 
        # #model.risk2
        # d= self.risk2(logger=log, plot=False)
        # self.res_d = {**self.res_d, **d}
        # 
        # #extra risk plots
        # self.plot_risk_ttl(logger=log)
        #=======================================================================
        
        
#===============================================================================
# executeors------------
#===============================================================================
wFlow_l = [Tut2] #used below and by test scripts to bundle workflows

if __name__ == '__main__':
    
    wrkr = Session(projName='tuts', write=True, plot=False)
    rlib = wrkr.run(wFlow_l)