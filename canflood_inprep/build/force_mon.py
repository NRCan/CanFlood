'''
Created on Mar. 4, 2020

@author: cefect


force monotonocity onto an exposure set
'''
import configparser, os, inspect, logging


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
    
from hlpr.basic import *

from model.modcom import Model


class ForceWorker(Model):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) #initilzie teh baseclass
        

    def run(self, df, adf, logger=None):
        if logger is None: logger=self.logger
        
        log =logger
    
        aep_ser = adf.iloc[0, adf.columns.isin(df.columns)].astype(int).sort_values().copy()
        
        assert len(aep_ser) == len(df.columns)
        
        res_df = self.force_monot(df, aep_ser = aep_ser, event_probs='ari', logger=log)
        
        return res_df



if __name__ =="__main__":
    #==========================================================================
    # dev data
    #==========================================================================
    #==========================================================================
    # out_dir = os.path.join(os.getcwd(), 'modcoms')
    # cf_fp = r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\CanFlood_scenario1.txt' 
    # tag='dev'
    #==========================================================================
    
    #==========================================================================
    # exp_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk1\wex\expos_test.csv'
    # aep_fp = r'C:\LS\03_TOOLS\_git\CanFlood\Test_Data\model\risk1\wex\aeps_test.csv'
    #==========================================================================
    #==========================================================================
    # 20200304 data
    #==========================================================================
    runpars_d = {
        'TDDnrp':{
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDDnrp\risk1',
            'cf_fp': r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDDnrp\CanFlood_TDDnrp.txt',
             },
        'TDDres':{
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDD_res\risk1',
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\TDD_res\CanFlood_TDDres.txt',            
            },
        'ICIrec':{
            'out_dir':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\risk1',
            'cf_fp':r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\CanFlood_ICIrec.txt',
            }
        }
    
    
    cid = 'xid'
    #==========================================================================
    # exp_fp = r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\expos_scenario1_16_855.csv'
    # aep_fp = r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\aeps_16_scenario1.csv'
    # exl_fp = r'C:\LS\03_TOOLS\CanFlood\_wdirs\20200304\ICI_rec\exlikes_ICI_rec.csv'
    #==========================================================================
    
    for dtag, pars in runpars_d.items():
        cf_fp, out_dir = pars['cf_fp'], pars['out_dir']
        log = mod_logger.getChild(dtag)
        #======================================================================
        # load from pars
        #======================================================================
        cf_pars = configparser.ConfigParser(inline_comment_prefixes='#')
        log.info('reading parameters from \n     %s'%cf_pars.read(cf_fp))
        
        aep_fp = cf_pars['risk_fps']['aeps']
        exl_fp = cf_pars['risk_fps']['exlikes']
        exp_fp = cf_pars['dmg_fps']['expos']
        #======================================================================
        # load common data
        #======================================================================
        adf = pd.read_csv(aep_fp)
        
        #==========================================================================
        # setup
        #==========================================================================
        wrkr = ForceWorker(cf_fp, out_dir=out_dir, logger=log)
        #==========================================================================
        # exlikes-------------
        #==========================================================================
            
        tag, fp = 'exlikes', exl_fp

    
        # load exposure data
    
        ddf_raw = pd.read_csv(fp).set_index(cid)
        
        # force monotoncity
        res_df = wrkr.run(ddf_raw, adf)
        
        #==========================================================================
        # output
        #==========================================================================
        basefn = os.path.splitext(os.path.split(fp)[1])[0]
        ofp = os.path.join(out_dir, '%s_forceM.csv'%basefn)
        res_df.to_csv(ofp, index=True)
        
        log.info('wrote %s to \n    %s'%(str(res_df.shape), ofp))
        
        
        #==========================================================================
        # wsl.fail-------------
        #==========================================================================
            
        tag, fp = 'expo', exp_fp
        log = mod_logger.getChild(tag)
    
    
        # load exposure data
        ddf_raw = pd.read_csv(fp).set_index(cid)
        
        #==========================================================================
        # divide
        #==========================================================================
        boolcol = ddf_raw.columns.str.contains('fail')
        ddf = ddf_raw.loc[:, boolcol]
    
        res_df1 = wrkr.run(ddf, adf)
    
        
        #==========================================================================
        # wsl.good------------
        #==========================================================================
        ddf = ddf_raw.loc[:, ~boolcol]
    
        res_df2= wrkr.run(ddf, adf)
        
        #==========================================================================
        # recombine
        #==========================================================================
        res_df =res_df1.join(res_df2)
        
        """
        view(res_df)
        """
        
        #==========================================================================
        # output
        #==========================================================================
        basefn = os.path.splitext(os.path.split(fp)[1])[0]
        ofp = os.path.join(out_dir, '%s_forceM.csv'%basefn)
        res_df.to_csv(ofp, index=True)
        
        log.info('wrote %s to \n    %s'%(str(res_df.shape), ofp))
    
    
    force_open_dir(out_dir)

    print('finished')
    
    