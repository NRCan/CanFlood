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
            #'lpol_dir':r'tutorials\1\haz_fpoly',
            
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
    name='tut1a'
    crsid ='EPSG:3005'
    pars_d = {
            
            #data files
            'finv_fp':r'tutorials\1\finv_cT2b.gpkg',
            'raster_dir':r'tutorials\1\haz_rast',
            'evals_fp':r'tests\_data\all2\evals_4_tut1a.csv',
            'lpol_dir':r'tutorials\1\haz_fpoly',
            
            #run controls
            'felv':'datum', 'validate':'risk1'
                    }
    
    tpars_d = {#kwargs for individual tools
        'Risk1':{
            'res_per_asset':True,
            }
        }
    
    def run(self,  #workflow for tutorial 1a

              ):
        log = self.logger.getChild('r')
        
        #build
        self.res_d = self.tb_build(logger=log, fpoly=True)


#===============================================================================
# executeors------------
#===============================================================================
wFlow_l = [Tut1a] #used below and by test scripts to bundle workflows

if __name__ == '__main__':
    
    wrkr = Session(write=False)
    #===========================================================================
    # build test pickesl
    #===========================================================================
    rlib = wrkr.run(wFlow_l)
    

    