'''
Created on Feb. 7, 2020

@author: cefect
'''
#==========================================================================
# logger setup-----------------------
#==========================================================================
import logging, logging.config
#logcfg_file = r'C:\Users\tony.decrescenzo\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\floodiq\_pars\logger.conf'
logger = logging.getLogger() #get the root logger
#logging.config.fileConfig(logcfg_file) #load the configuration file
#logger.info('root logger initiated and configured from file: %s'%(logcfg_file))
    
#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os

import pandas as pd
import numpy as np

from scipy import interpolate, integrate

#custom imports
import hp
from hp import Error, view


from model.scripts_ import Model

#==============================================================================
# functions----------------------
#==============================================================================
class RiskModel(Model):
    
    #==========================================================================
    # parameters from user
    #==========================================================================

    ground_water = False
    felv = 'datum'
    event_probs = 'aep'
    ltail = 'extrapolate'
    rtail = 'extrapolate'
    drop_tails = False
    integrate = 'trapz'
    ead_plot = False
    res_per_asset = False
    
    
    #==========================================================================
    # data containers
    #==========================================================================
    
    dfuncs_d = dict() #container for damage functions
    
    
    #==========================================================================
    # #program vars
    #==========================================================================
    bid = 'bid' #indexer for expanded finv
    datafp_section = 'risk_fps'

    #minimum expectations for parameter file
    exp_pars = {'parameters':list(),
                  'risk_fps':['dmgs','aeps'], #exlikes is optional
                  }
    
    #expected data properties
    exp_dprops = {'dmgs':{'ext':'.csv', 'colns':[]},
                   'exlikes':{'ext':'.csv', 'colns':[]},
                    'aeps':{'ext':'.csv', 'colns':[]},
                    }
    
    

    dirname = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    def __init__(self,
                 par_fp = None,
                 out_dir = None,
                 logger = None
                 ):
        
        #init the baseclass
        super().__init__(par_fp, out_dir, logger) #initilzie teh baseclass
        
        #======================================================================
        # setup funcs
        #======================================================================
        
        
        self.setup_data()
        
        self.logger.debug('finished __init__ on Risk')
        
        
        
    def setup_data(self): #data setups and checks
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('setup_data')
        cid = self.cid
        
        
        #======================================================================
        # setup damages
        #======================================================================
        #get event names from damages
        ddf = self.data_d['dmgs']
        boolcol = ddf.columns.str.endswith('_dmg')
        enm_l = ddf.columns[boolcol].str.replace('_dmg', '').tolist()
        
        #some checks
        assert len(enm_l) > 1, 'failed to identify sufficient damage columns'
        assert cid in ddf.columns, 'missing %s in damages'%cid
        assert ddf[cid].is_unique, 'expected unique %s'%cid
        assert ddf.notna().any().any(), 'got some nulls on dmgs'
        
        #set indexes
        ddf = ddf.set_index(cid, drop=True).sort_index(axis=1).sort_index(axis=0)
        ddf.columns = enm_l
        
        ddf = ddf.round(self.prec)
        
        log.info('prepared ddf w/ %s'%str(ddf.shape))
        
        #set it
        self.data_d['dmgs'] = ddf
        
        #======================================================================
        # aeps
        #======================================================================
        adf = self.data_d['aeps']
        assert len(adf) ==1, 'expected only 1 row on aeps'
        

            
        

        #column names
        miss_l = set(ddf.columns).difference(adf.columns)
        assert len(miss_l) == 0, '%i column mismatch between exlikes and damages: %s'%(
            len(miss_l), miss_l)
        
        #convert to a series
        aep_ser = adf.iloc[0, adf.columns.isin(ddf.columns)].astype(int).sort_values()
        
        #convert to aep
        if self.event_probs == 'ari':
            aep_ser = 1/aep_ser
            log.info('converted %i aris to aeps'%len(aep_ser))
        elif self.event_probs == 'aep': pass
        else: raise Error('unepxected event_probs key %s'%self.event_probs)
        
        #check all aeps are below 1
        boolar = np.logical_and(
            aep_ser < 1,
            aep_ser > 0)
        
        assert np.all(boolar), 'passed aeps out of range'
        
        #check if we have duplicate events and require exposure likelihoods
        if not aep_ser.is_unique:
            assert 'exlikes' in self.data_d, 'duplicate aeps passed but no exlikes data provdied'
            
            log.info('duplicated aeps provided... maximum expected values will be calculated')

        
        
        #wrap
        log.debug('prepared aep_ser w/ %i'%len(aep_ser))
        self.aep_ser = aep_ser.sort_values()
        
        
        
        #======================================================================
        # exlikes
        #======================================================================
        #check against ddf
        if 'exlikes' in self.data_d:
            edf = self.data_d['exlikes']
            
            assert cid in edf.columns, 'exlikes missing %s'%cid
            
            #slice it
            edf = edf.set_index(cid).sort_index(axis=1).sort_index(axis=0)
            
            #replace nulls w/ 1
            """better not to pass any nulls.. but if so.. should treat them as 1
            also best not to apply precision to these values
            """
            edf = edf.fillna(1.0)
            
            
            
            
            #column names
            miss_l = set(ddf.columns).difference(edf.columns)
            assert len(miss_l) == 0, '%i column mismatch between exlikes and damages: %s'%(
                len(miss_l), miss_l)
            
            #xids
            miss_l = set(ddf.index).difference(edf.index)
            assert len(miss_l) == 0, '%i column mismatch between exlikes and damages: %s'%(
                len(miss_l), miss_l)
            
            #slice down to those in teh damages
            """not sure if we'll ever have to deal w/ more data in the edf than in the damages"""
            edf = edf.loc[edf.index.isin(ddf.index), edf.columns.isin(ddf.columns)]
        
            log.info('prepared edf w/ %s'%str(edf.shape))
            
            #set it
            self.data_d['exlikes'] = edf
        

        #======================================================================
        # wrap
        #======================================================================
        self.logger.debug('finished')
        

    def run(self, #main runner fucntion
            ):
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('run')
        ddf, aep_ser, cid = self.data_d['dmgs'], self.aep_ser, self.cid
        
        
        #======================================================================
        # resolve alternate damages (per evemt)
        #======================================================================
        #take maximum expected value at each asset
        if 'exlikes' in self.data_d:
            ddf1 = self.resolve_multis(ddf, self.data_d['exlikes'], aep_ser, log)
            
        #no duplicates. .just rename by aep
        else:
            ddf1 = ddf.rename(columns = aep_ser.to_dict()).sort_index(axis=1)
            
        #======================================================================
        # checks
        #======================================================================
        #check the columns
        assert np.array_equal(ddf1.columns.values, aep_ser.unique()), 'column name problem'
        assert np.all(ddf1.notna()), 'got some nulls'
        
        #check for damage monotonicity
        boolidx = ddf1.apply(lambda x: x.is_monotonic_increasing, axis=1)
        if boolidx.any():
            log.debug(ddf1.loc[boolidx, :])
            raise Error(' %i (of %i)  assets have non-monotonic-increasing damages. see logger'%(
                boolidx.sum(), len(boolidx)))
            
        #======================================================================
        # totals
        #======================================================================        
        res_ser = self.calc_ead(ddf1.sum(axis=0).to_frame().T, logger=logger).iloc[0]
                    
        #======================================================================
        # get ead per asset
        #======================================================================
        if self.res_per_asset:
            res_df = self.calc_ead(ddf1, drop_tails=self.drop_tails, logger=logger)
                        
        else:
            res_df = None
            
        
        
        #======================================================================
        # plot
        #======================================================================
        if self.ead_plot:
            self.risk_plot(res_ser.copy())
            #==================================================================
            # try:
            #     self.risk_plot(res_df)
            # except Exception as e:
            #     log.warning('failed to generate figure \n    %s'%e)
            #==================================================================
        
        #======================================================================
        # output-----------------
        #======================================================================
        log.info('finished on %i assets and %i damage cols'%(len(ddf1), len(res_ser)))
        
        
        """need to create a unique output folder (timestamped) and output:
        log file
        parameter file (copy)
        assets results data (res_df)
        summary data (reserved for future dev)
        risk figure (handled by risk_plot())
        """
        #format resul series
        res = res_ser.to_frame()
        res.index.name = 'aep'
        res.columns = ['$']
        
        #remove tails
        if self.drop_tails:
            res = res.iloc[1:-2,:] #slice of ends 
            res.loc['ead'] = res_ser['ead'] #add ead back
        

        
        self.output(res, '%s_risk_total.csv'%self.name)
        if not res_df is None:
            self.output(res_df, '%s_risk_passet.csv'%self.name)
         
        log.info('finished')
         
        return 
    
    def resolve_multis(self,
                       ddf, edf, aep_ser,
                       logger):
        #======================================================================
        # setup
        #======================================================================
        log = logger.getChild('resolve_multis')
        
        
        #======================================================================
        # get expected values of all damages
        #======================================================================
        """where edf > 0 ddf should also be > 0
        but leave this check for the input validator"""
        evdf = ddf*edf
        
        log.debug('calucated expected values for %i damages'%evdf.size)

        #======================================================================
        # loop by unique aep and resolve
        #======================================================================
        res_df = pd.DataFrame(index=evdf.index, columns = aep_ser.unique().tolist())
        for aep in aep_ser.unique().tolist():
            
            #==================================================================
            # get these events
            #==================================================================
            #find event names at this aep
            boolar = aep_ser == aep
            
            #handle by match count
            if boolar.sum() == 0:
                raise Error('problem with event matching')
            
            #get these event names
            evn_l = aep_ser.index[boolar].tolist()
            
            #==================================================================
            # resolve
            #==================================================================
            #only 1 event.. nothing to resolve
            if len(evn_l) == 1:
                log.warning('only got 1 event \'%s\' for aep %.2e'%(
                    aep_ser.index[boolar], aep))
                
                #use these
                res_df.loc[:, aep] =  evdf.loc[:, evn_l]
            
            #multiple events... take maximum
            else:
                log.info('resolving alternate damages for aep %.2e from %i events: \n    %s'%(
                    aep, len(evn_l), evn_l))
                
                res_df.loc[:, aep] = evdf.loc[:, evn_l].max(axis=1)
                
        #======================================================================
        # warp
        #======================================================================
        assert res_df.notna().all().all(), 'got some nulls'
        
        log.info('resolved to %i unique event damages'%len(res_df.columns))
        
        return res_df.sort_index(axis=1)
           
    
    def calc_ead(self,
                 df_raw, #xid: aep
                 ltail = None,
                 rtail = None,
                 drop_tails = False, #whether to remove the dummy tail values from results
                 logger = None
                 ):      
        
        """
        #======================================================================
        # inputs
        #======================================================================
        ltail: left tail treatment code (low prob high damage)
            flat: extend the max damage to the zero probability event
            extrapolate: extend the fucntion to the zero aep value
            float: extend the function to this damage value (must be greater than max)
            none: don't extend the tail (not recommended)
            
        rtail: right trail treatment (high prob low damage)
            extrapolate: extend the function to the zero damage value
            float: extend the function to this aep
            none: don't extend (not recommended)

        
        """
        #======================================================================
        # setups and defaults
        #======================================================================
        if logger is None: logger = self.logger
        log = logger.getChild('calc_ead')
        if ltail is None: ltail = self.ltail
        if rtail is None: rtail = self.rtail
        
        #format tail values
        
        if not ltail in ['flat', 'extrapolate', 'none']:
            ltail  = float(ltail)
        if not rtail in ['extrapolate', 'none']:
            rtail = float(rtail)
            
        log.info('getting ead on %s w/ ltail=%s and rtail=%s'%(
            str(df_raw.shape), ltail, rtail))
        
        #identify columns to calc ead for
        boolidx = (df_raw > 0).any(axis=1) #only want those with some real damages
        
        #======================================================================
        # setup left tail
        #======================================================================
        df = df_raw.copy()
        #flat projection
        if ltail == 'flat':
            df.loc[:,0] = df.iloc[:,0] 
            
        elif ltail == 'extrapolate':
            df.loc[boolidx,0] = df.loc[boolidx, :].apply(
                self.extrap, axis=1, left=True)

        elif isinstance(ltail, float):
            """this cant be a good idea...."""
            df.loc[boolidx,0] = ltail
        elif ltail == 'none':
            pass
        else:
            raise Error('unexected ltail key'%ltail)
        
        #======================================================================
        # setup right tail
        #======================================================================
        if rtail == 'extrapolate':
            """just using the average for now...
            could extraploate for each asset but need an alternate method"""
            aep_ser = df.loc[boolidx, :].apply(
                self.extrap, axis=1, left=False)
            
            aep_val = round(aep_ser.mean(), 5)
            
            assert aep_val > df.columns.max()
            
            df.loc[boolidx, aep_val] = 0
            
            log.info('using right intersection of aep= %.2e from average extraploation'%(
                aep_val))
        
        elif isinstance(rtail, float):
            aep_val = round(rtail, 5)
            assert aep_val > df.columns.max()
            
            df.loc[boolidx, aep_val] = 0
            
            log.info('using right intersection of aep= %.2e from user val'%(
                aep_val))
            
            
            
        elif rtail == 'none':
            log.warning('passed \'none\' no right tail set!')
        
        else:
            raise Error('unexpected rtail %s'%rtail)
            
        
        
        df = df.sort_index(axis=1)
        
        #======================================================================
        # check monoticiy again
        #======================================================================
        #check for damage monoticyt
        cboolidx = df.apply(lambda x: x.is_monotonic_increasing, axis=1)
        if cboolidx.any():
            log.debug(df.loc[cboolidx, :])
            raise Error(' %i (of %i)  assets have non-monotonic-increasing damages. see logger'%(
                cboolidx.sum(), len(cboolidx)))
            
            
        #======================================================================
        # get ead per row
        #======================================================================
        #get reasonable dx (integrating along damage axis)
        dx = df.max().max()/100
        
        #re-arrange columns so x is ascending
        df = df.sort_index(ascending=False, axis=1)
        
        #apply the ead func
        df.loc[boolidx, 'ead'] = df.loc[boolidx, :].apply(
            self.get_ev, axis=1, dx=dx)
        
        
        df.loc[:, 'ead'] = df['ead'].fillna(0) #fill remander w/ zeros
        
        #======================================================================
        # check it
        #======================================================================
        assert np.all(df['ead'] > 0), 'got negative eads'
        
        #======================================================================
        # clean results
        #======================================================================
        if drop_tails:
            res_df = df_raw.join(df['ead'].round(self.prec))
        else:
            res_df = df
            

        
        
        return res_df
    """
    view(df)
    """
        
        
    def extrap(self, 
               ser, #row of dmages (y values) from big df
               left=True, #whether to extraploate left or gihtt
               ):
        
        #build interpolation function from data
        if left:
            #xvalues = aep
            f = interpolate.interp1d(ser.index.values, ser.values, 
                                     fill_value='extrapolate')
            
        else:
            #xvalues = damages
            f = interpolate.interp1d( ser.values, ser.index.values,
                                     fill_value='extrapolate')
            
        
        #calculate new y value by applying interpolation function
        result = f(0)
        
        return float(result) 
    
    def get_ev(self, 
               ser, #row from damage results
               dx = 0.1,
               ):
        """
        should integrate along the damage axis (0 - infinity)
        """
        
        
        #print('%i.%s    %s'%(self.cnt, ser.name, ser.to_dict()))
        
        x = ser.tolist()
        y = ser.index.tolist()
        
        #======================================================================
        # ser_inv = ser.sort_index(ascending=False)
        # 
        # x = ser_inv.tolist()
        # y = ser_inv.index.tolist()
        # 
        #======================================================================
        if self.integrate == 'trapz':
        
            ead_tot = integrate.trapz(
                y, #yaxis - aeps
                x=x, #xaxis = damages 
                dx = dx)
            
        elif self.integrate == 'simps':
            raise Error('not tested')
            
            ead_tot = integrate.simps(
                y, #yaxis - aeps
                x=x, #xaxis = damages 
                dx = dx)
            
        else:
            raise Error('integration method \'%s\' not recognized'%self.integrate)
            
        
        #======================================================================
        # np.trapz(x, x=y)
        # 
        # np.trapz(y, x=x, dx=4000)
        # 
        # if ead_tot < 0:
        #     raise Error('bad ead tot')
        #======================================================================
        return ead_tot
    
    def risk_plot(self, #generate and save a figure that summarizes the damages 
                  dmg_ser,
                  
                  #labels
                  xlab='ARI', y1lab='$dmg', y2lab='AEP',
                  
                  #format controls
                  grid = True, logx = False, 
                  basev = 1, #base value for dividing damage values
                  dfmt = '${:,.0f}', #formatting of damage values 
                  
                  #output pars
                  out_dir = None, overwrite=None, fmt='svg', 
                  transparent=True, dpi = 150,
                  
                  #figure parametrs
                figsize     = (6.5, 4), 
                    
                #hatch pars
                    hatch =  None,
                    h_color = 'blue',
                    h_alpha = 0.1,
                  ):
        
        """
        TODO: fix the title
        
        """
        
        #======================================================================
        # defaults
        #======================================================================
        log = self.logger.getChild('risk_plot')
        if out_dir is None: out_dir = self.out_dir
        if overwrite is None: overwrite = self.overwrite
        
        #======================================================================
        # setup
        #======================================================================
        
        import matplotlib
        matplotlib.use('SVG') #sets the backend (case sensitive)
        import matplotlib.pyplot as plt
        
        #set teh styles
        plt.style.use('default')
        
        #font
        matplotlib_font = {'family' : 'serif',
                'weight' : 'normal',
                'size'   : 8}
        
        matplotlib.rc('font', **matplotlib_font)
        matplotlib.rcParams['axes.titlesize'] = 10 #set the figure title size
        
        #spacing parameters
        matplotlib.rcParams['figure.autolayout'] = False #use tight layout
        
        #======================================================================
        # data manipulations
        #======================================================================
        #get ead
        ead_tot = dmg_ser['ead']
        del dmg_ser['ead'] #remove it from plotter values
        
        
        #get damage series to plot
        ar = np.array([dmg_ser.index, dmg_ser.values]) #convert to array
        
        #invert aep (w/ zero handling)
        ar[0] = 1/np.where(ar[0]==0, #replaced based on zero value
                           sorted(ar[0])[1]/10, #dummy value for zero (take the second smallest value and divide by 10)
                           ar[0]) 
        
        dmg_ser = pd.Series(ar[1], index=ar[0], dtype=float) #back into series
        dmg_ser.index = dmg_ser.index.astype(int) #format it
                
        
        #get aep series
        aep_ser = dmg_ser.copy()
        aep_ser.loc[:] = 1/dmg_ser.index
        
        
        #======================================================================
        # labels
        #======================================================================
        
        val_str = 'total EAD = ' + dfmt.format(ead_tot/basev)
        
        title = 'CanFlood \'%s\' EAD-%s plot on %i events'%(self.name,xlab, len(dmg_ser))
        
        #======================================================================
        # figure setup
        #======================================================================
        plt.close()
        fig = plt.figure(1)
        fig.set_size_inches(figsize)
        
        #axis setup
        ax1 = fig.add_subplot(111)
        ax2 = ax1.twinx()
        ax1.set_xlim(max(aep_ser.index), 1) #aep limits 
        
        # axis label setup
        fig.suptitle(title)
        ax1.set_ylabel(y1lab)
        ax2.set_ylabel(y2lab)
        ax1.set_xlabel(xlab)
        
        #======================================================================
        # fill the plot
        #======================================================================
        #damage plot
        xar,  yar = dmg_ser.index.values, dmg_ser.values
        pline1 = ax1.semilogx(xar,yar,
                            label       = y1lab,
                            color       = 'black',
                            linestyle   = 'dashdot',
                            linewidth   = 2,
                            alpha       = 0.5,
                            marker      = 'x',
                            markersize  = 2,
                            fillstyle   = 'full', #marker fill style
                            )
        #add a hatch
        polys = ax1.fill_between(xar, yar, y2=0, 
                                color       = h_color, 
                                alpha       = h_alpha,
                                hatch       = hatch)
        
        #aep plot
        xar,  yar = aep_ser.index.values, aep_ser.values
        pline2 = ax2.semilogx(xar,yar,
                            label       = y2lab,
                            color       = 'blue',
                            linestyle   = 'dashed',
                            linewidth   = 1,
                            alpha       = 1,
                            marker      = 'x',
                            markersize  = 0,
                            )
        

        
        #=======================================================================
        # Add text string 'annot' to lower left of plot
        #=======================================================================
        xmin, xmax1 = ax1.get_xlim()
        ymin, ymax1 = ax1.get_ylim()
        
        x_text = xmin + (xmax1 - xmin)*.1 # 1/10 to the right of the left ax1is
        y_text = ymin + (ymax1 - ymin)*.1 #1/10 above the bottom ax1is
        anno_obj = ax1.text(x_text, y_text, val_str)
        
        #=======================================================================
        # format axis labels
        #======================================================= ================
        #damage values (yaxis for ax1)
        old_tick_l = ax1.get_yticks() #get teh old labels
         
        # build the new ticks
        l = [dfmt.format(value/basev) for value in old_tick_l]
              
        #apply the new labels
        ax1.set_yticklabels(l)
        
        
        
        #ARI (xaxis for ax1)
        ax1.get_xaxis().set_major_formatter(
                matplotlib.ticker.FuncFormatter(lambda x, p: format(int(x), ',')))
            
            
        
        
        #=======================================================================
        # post formatting
        #=======================================================================
        if grid: ax1.grid()
        

        #legend
        h1, l1 = ax1.get_legend_handles_labels() #pull legend handles from axis 1
        h2, l2 = ax2.get_legend_handles_labels()
        ax1.legend(h1+h2, l1+l2, loc=2) #turn legend on with combined handles
        
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
            
        
        
        
        
        
        

def main_run(wd, cf):
    print('executing')

    _ = RiskModel(par_fp=cf,
                  out_dir=wd,
                  logger=logger).run()
    
    print('finished')
    

    
    
    