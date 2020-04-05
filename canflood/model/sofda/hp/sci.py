'''
Created on Jun 13, 2018

@author: cef

hp functions for the scipy and sklearn modulew
'''
#===============================================================================
# # IMPORTS --------------------------------------------------------------------
#===============================================================================
import logging, os, sys, imp, time, math, re, copy

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import scipy.stats 

from collections import OrderedDict
from weakref import proxy

#===============================================================================
# import other helpers
#===============================================================================
import hp.plot2
import model.sofda.hp.basic as hp_basic
import model.sofda.hp.np as hp_np
import model.sofda.hp.oop as hp_oop
import model.sofda.hp.data as hp_data


mod_logger = logging.getLogger(__name__)


#class Fit_func(hp_data.Data_o): #thin wrapper for regressions
     

class Data_func(hp_data.Data_wrapper, 
                hp.plot2.Plotr,
                hp_oop.Child): #for analysis by data type
    
    #===========================================================================
    # regressions
    #===========================================================================
    dfunc   = None #placeholder for callable function that takes a set of indepdent values and returns depdendent
    fits_od = OrderedDict() #dictionary of regression fit children
    
    #===========================================================================
    # fit plotting formatters
    #===========================================================================
    fit_color = 'red'
    fit_alpha = 0.6
    fit_lw = 3
    fit_linestyle = 'solid'
    fit_markersize = 0
    
    units = 'none'
    
    #===========================================================================
    # object handling overrides
    #===========================================================================
    
    def __init__(self, parent = None, session = None, name = 'datafunc'):
        
        self.name = name 
        self.parent = parent
        self.session = session
        
        #initilzie teh baseclass
        self.label = self.name + '(%s)'%self.units
        
        if not parent is None:
            self.inherit_logr(parent)
        else:
            self.logger = mod_logger
        

 
    def clean_data(self, raw_data):
        'placeholder'
        return raw_data
        
        
    def calc_stats(self): #update teh stats from teh data
        
        data = self.data
        
        self.min = data.min()
        self.max = data.max()
        self.mean = data.mean()
        self.var = data.var()
        
        self.stat_str = 'min: %.2f, max = %.2f, mean = %.2f, var = %.2f'\
            %(self.min, self.max, self.mean, self.var)
        
        self.logger.debug(self.stat_str)
        
    def spawn_fit(self, kid_class=None, childname = None, **kwargs):
        
        #=======================================================================
        # defautls
        #=======================================================================
        if kid_class is None: kid_class = hp.plot.Plot_o
        if childname is None: childname = '%s %s fit'%(self.name, self.fit_name)
        
        #spawn the child
        
        child = self.spawn_child(childname = childname,
                         kid_class = kid_class, **kwargs)
        
        
        #give it the datat function
        child.dfunc = self.dfunc
        
        
        #pass down the correct attributes
        child.units =           self.units
        
        #give it the formatters
        child.color  =          self.fit_color
        child.alpha =           self.fit_alpha 
        child.lineweight =      self.fit_lw 
        child.linestype =       self.fit_linestyle
        child.markersize =      self.fit_markersize 
        
        self.fits_od[child.name] = child
        
        return child
        
class Continuous_1D(Data_func): #set of 1d discrete data
    rv = None #scipy random variable placeholder
    fit_name = None #placeholder for the type of fit applied
    
    def clean_data(self, ar_raw): #clean the data
        logger = self.logger.getChild('clean_data')
        
        if not hp_np.isar(ar_raw):
            try:
                ar1 = ar_raw.values
                if not hp_np.isar(ar1): raise ValueError
            except:
                self.logger.error('failed to convert to array')
                raise IOError 
            
        else: ar1 = copy.deepcopy(ar_raw) #just get a copy
        
        #dimensional check
        ar2 = hp_np.make_1D(ar1, logger = self.logger)
        
        ar3 = hp_np.dropna(ar2, logger = self.logger)
        
        ar_clean = ar3
        
        logger.debug('cleaned %s to %s'%(str(ar_raw.shape), str(ar_clean.shape)))
        
        return ar_clean


        
    def fit_norm(self): #fit and freeze a normal distribution to this
        logger = self.logger.getChild('fit_norm')
        self.fit_name = 'norm'
        
        logger.debug('fitting a normal disribution to data')
        
        #get the noral dist paramters for this data
        pars = scipy.stats.norm.fit(self.data)
        
        #=======================================================================
        # check the parameters
        #=======================================================================
        if np.isnan(pars[0]): raise IOError
        if not len(pars) == 2: raise IOError #normal distribution should only return 2 pars
        
        #freeze a distribution with these paramters
        self.rv = scipy.stats.norm(loc = pars[0], scale = pars[1])
        
        logger.info('froze dist with pars: %s '%str(pars))
        
        self.pars = pars
        
        return
    
    def fit_lognorm(self):
        
        logger = self.logger.getChild('fit_norm')
        
    def plot_pdf(self, ax=None, title = None,wtf=None, annot_f=False,
                 color = 'red', alpha = 0.6, lw = 3, label = None,
                 outpath = None): #cretate a plot of the pdf
        """
        Ive createdd a separate plot frunctio n(from hp.plot) as this is a curve fit to the data... not the data
        """
        #=======================================================================
        # defautls
        #=======================================================================
        if self.rv is None: raise IOError
        if wtf is None: wtf = self.session._write_figs
        if label is None: label = self.fit_name + ' pdf'
        
        rv = self.rv
        
        logger = self.logger.getChild('plot_pdf')
        logger.debug('plotting with ax = \'%s\''%ax)
        #=======================================================================
        # setup plot
        #=======================================================================
        if ax is None:
            plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(self.figsize)
            ax = fig.add_subplot(111)  
            
            if title is None: title = self.name + ' '+ self.fit_name + ' pdf plot'

            ax.set_title(title)
            ax.set_ylabel('likelihood')
            ax.set_xlabel(self.label)
                  
        else:
            fig = ax.figure
            xmin, xmax = ax.get_xlim()

        #=======================================================================
        # data setup
        #=======================================================================
        x = np.linspace(rv.ppf(0.001), rv.ppf(0.999), 200) #dummy x values for plotting
        
        #=======================================================================
        # plot
        #=======================================================================
        pline = ax.plot(x, rv.pdf(x), 
                        lw = lw, alpha = alpha, label = label, color=color)
        
    
        if annot_f:
            max1ind = np.argmax(rv.pdf(x)) #indicies of first occurance of the max value
            max_x = x[max1ind]
            """
            boolmax = max(rv.pdf(x)) == rv.pdf(x)
            boolmax = x[np.argmax(rv.pdf(x))]
            try:
                max_x = float(x[boolmax])
            except:
                max_x = 0.00"""
                
            annot = '%s dist \n'%self.rv.dist.name +\
                    r'$\mu=%.2f,\ \sigma=%.2f$, max=%.2f'%(self.rv.kwds['loc'], self.rv.kwds['scale'], max_x)
                    
            #add the shape parameter for 3 par functions
            if len(self.rv.args) > 0:
                annot = annot + '\n shape = %.2f'%self.rv.args[0]
            
            
            
            #=======================================================================
            # Add text string 'annot' to lower left of plot
            #=======================================================================
            xmin, xmax = ax.get_xlim()
            ymin, ymax = ax.get_ylim()
            
            x_text = xmin + (xmax - xmin)*.5 # 1/10 to the right of the left axis
            y_text = ymin + (ymax - ymin)*.5 #1/10 above the bottom axis
            anno_obj = ax.text(x_text, y_text, annot)
        
        logger.debug('finished')
        
        if wtf: 
            try:
                self.save_fig(fig, outpath=outpath)
            except:
                logger.warning('failed to safe figure')

            
        """
        plt.show()
        """
            
        
        return ax
    
    def plot_fit(self, bins = None, #plot the fit curve adn the data
                 ax = None, title=None, wtf=None,
                 **kwargs): 

        #=======================================================================
        # defautls
        #=======================================================================
        if self.rv is None: raise IOError
        if wtf is None: wtf = self.session._write_figs
        rv = self.rv
        
        logger = self.logger.getChild('plot_fit')

        
        #=======================================================================
        # setup plot
        #=======================================================================
        if ax is None:
            plt.close()
            fig = plt.figure(1)
            fig.set_size_inches(self._figsize)
            ax = fig.add_subplot(111)  
            
            if title is None: title = self.name + ' '+ self.fit_name + ' fit plot'

            ax.set_title(title)
            ax.set_ylabel('likelihood')
            ax.set_xlabel(self.label)
                  
        else:
            fig = ax.figure
            xmin, xmax = ax.get_xlim()
            
        #=======================================================================
        # setup annotation
        #=======================================================================
        annot =  r'n = %i, $\mu=%.2f,\ \sigma=%.2f$'%(len(self.data), self.mean, self.var)
            
        #=======================================================================
        # plot the data
        #=======================================================================
        ax = self.plot_data_hist(normed=True, bins = bins, 
                                 ax=ax, title=title, wtf=False, annot = annot,
                                 **kwargs)
        
        ax = self.plot_pdf(ax=ax, title = title, wtf=False)
        
        #=======================================================================
        # post formatting
        #=======================================================================

        
        if wtf: 
            flag = hp.plot.save_fig(self, fig, dpi = self.dpi, legon = True)
            if not flag: raise IOError 
        
        logger.info('finished')

class Boolean_1D(Data_func): #set of 1d discrete data
    reg = None #LogisticRegression from sklearn
    fit_name = None #placeholder for the type of fit applied
    
    data2_o = None #partenr data to compare against
    
    data_int = None #boolean data converted to integers
    
    logit_solvers = ['newton-cg', 'lbfgs', 'liblinear', 'sag', 'saga']
    
    def data_setup(self, data2_o): #basic cleaning adn data setup
        
        if data2_o is None: data2_o = self.data2_o
        if data2_o is None: raise IOError
        
        self.data2_o = data2_o
        
        if self.data_int is None: self.bool_to_num()
        
        #=======================================================================
        # combine data into frame
        #=======================================================================
        df1 = pd.DataFrame(index = self.data_int.index)
        
        df1['bool'] = self.data
        df1['int'] = self.data_int.values
        df1['data2'] = data2_o.data
        
        
        self.df_raw = df1 #attach this
        
        #=======================================================================
        # clean
        #=======================================================================
        df2 = df1.dropna(axis='index', how='any')
        
        self.df_clean = df2
        #=======================================================================
        # data setup
        #=======================================================================
        
        
        self.dep_ar = df2.loc[:,'int'].astype(np.int).values
        self.ind_ar = df2.loc[:,'data2'].astype(np.int).values
        
        return 
            
    def bool_to_num(self): #convert the boolean data to numeric
        
        if not hp_pd.isser(self.data): raise IOError
        
        self.data = self.data.astype(np.bool) #convert the original data to boolean
        
        self.data_int = self.data.astype(np.int)
        
    def fit_LogisticRegression(self, data2_o=None, target = 'int',
                   solver = 'newton-cg', verbose=2): #fit the data to a logit model
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        target: what header in the clean_df to use as the target array
        """
    
        #=======================================================================
        # set defaults
        #=======================================================================
        logger = self.logger.getChild('fit_LogisticRegression')
        
        
        self.data_setup(data2_o)
        #if not dep_ar.shape == ind_ar.shape: raise IOError
        df = self.df_clean
        
        #=======================================================================
        # build the model
        #=======================================================================
        import sklearn.linear_model
        
        #get teh train/target data from the clean frame
        train_ar = df['data2'].values.reshape(-1,1)
        target_ar = df[target].values.reshape(-1,1)
        
        #initilze teh model
        reg = sklearn.linear_model.LogisticRegression(solver = solver , verbose=verbose)
        
        #fit to the data
        reg = reg.fit(train_ar, target_ar)
        
        self.reg = reg
        self.fit_name = 'LogisticRegression'
        #=======================================================================
        # get equilvanet pars
        #=======================================================================
        'doin gthis here for plotting annot'
        self.loc = self.data2_o.data.min() #this looks good. closest yet
        self.scale = 1.0/float(self.reg.coef_) #looks pretty good
        
        #=======================================================================
        # create a new child for this
        #=======================================================================
        child = self.spawn_fit()
        
        child.reg   = self.reg #give it the regression
        
        child.data2_o = self.data2_o #give it the indepdendnet dato
        
        #=======================================================================
        # wrap up and report
        #=======================================================================
        logger.info('finished with coef_  = %.2f,  intercept_  = %.2f, n_iter_  = %.2f' 
                    %(reg.coef_ , reg.intercept_ , reg.n_iter_ ))
        

        
        return child
        
    def try_all_logit_solvers(self): #plot results for all solver methods
        logger = self.logger.getChild('plot_asnum')
        
        success = []
        
        for solver in self.logit_solvers:
            try:
                reg = self.fit_LogisticRegression(solver = solver, verbose=0)
                
                title = self.name + ' logit on \'%s\' with \'%s\''%(self.data2_o.name, solver)
                
                ax = self.plot_fit(title = title) #make the plot
                
                success.append(solver)
                
            except:
                logger.error('failed on \'%s\''%solver)
                
        
        logger.info('finished with %i (of %i) successful solvers: %s'%(len(success), len(self.logit_solvers), success))
        
    def dfunc(self, x):
        
        y = self.reg.predict_proba(x.reshape(-1,1))[:,1]
        
        if not x.shape == y.shape:
            raise IOError
        
        return y
    
    def build_scipy_equil(self, type = 'cdf'): #build an equilvalent scipy logistic (or Sech-squared) continuous random variable.
        """
        because we need a more sophisiticated LinearMOdel to fit to the boolean data
            we use Sklearn to train the model
            
        However, there doesn't seem to be a good way to incorporate a simply parametersized Sklearn model into ABMRI
        
        SOLUTION:
            use the coefficents from teh Sklearn training to paramterize a simple scipy logistc curve
            
        
        
        """
        logger = self.logger.getChild('plot_asnum')
        
        if self.reg is None: raise IOError
        
        #=======================================================================
        # get teh equilvanet parameters
        #=======================================================================
        #=======================================================================
        # loc = self.data2_o.data.min() #this looks good. closest yet
        # scale = 1.0/float(self.reg.coef_) #looks pretty good
        #=======================================================================
        
        'pull from teh fit_LogisticRegression'
        loc, scale = self.loc, self.scale #attach these
        
        #get a frozen func
        self.rv = scipy.stats.logistic(loc = loc, scale = scale)
        
        logger.info('parameterized a scipy.stats.logistic with loc = %.2f and scale = %.2f'%(loc, scale))

        #=======================================================================
        # create a new child for this
        #=======================================================================
        childname = '%s %s fit'%(self.name, 'scipy.stats.logistic')
        child = self.spawn_fit(childname = childname)
        
        #attach the attributes
        child.data2_o = self.data2_o #give it the indepdendnet dato
        child.rv = self.rv #attach teh frozen curve
        #=======================================================================
        # child.loc   = self.loc
        # child.scale = self.scale
        #=======================================================================
        
        #=======================================================================
        # attach the function
        #=======================================================================
        
        def cdf(x):
            'no need to pass loc and scale as the curve is frozen'
            return self.rv.cdf(x)
        
        def pdf(x):
            return self.rv.pdf(x)
        
        if type == 'cdf': child.dfunc = cdf
        elif type == 'pdf': child.dfunc = pdf
        
        #=======================================================================
        # attach the formatter overrides 
        #=======================================================================
        'most the formatters are applied during spawn_fit'
        child.linestyle = 'dashed'
        
        return child
                
        
    def plot_asnum(self, data2_o=None, 
                   title = None,
                   ax=None, wtf=None, **kwargs): #plot the raw data converting bools to integers
        
        logger = self.logger.getChild('plot_asnum')
        
        if data2_o is None: data2_o = self.data2_o
        if data2_o is None: raise IOError
        
        #=======================================================================
        # data setup
        #=======================================================================
        if self.data_int is None: self.bool_to_num()
        dep_ar = self.data_int
        
        #=======================================================================
        # formatting
        #=======================================================================
        if title is None: title ='%s vs %s plot'%(self.name, data2_o.name)
        
        #=======================================================================
        # send for plotting
        #=======================================================================
        
        ax = self.parent.plot(self, indp_dato = data2_o, dep_ar = dep_ar,
                         linewidth = 0,
                         title = title, ax = ax, wtf=wtf, **kwargs)
        
        """
        data2_o.name
        plt.show()
        """
        
        return ax
    
    def plot_probs(self, data2_o=None, fit_o = None,
                    title = None, ax=None, wtf=None, **kwargs): #plot the raw data converting bools to integers
        
        logger = self.logger.getChild('plot_probs')
        
        if data2_o is None: data2_o = self.data2_o
        if data2_o is None: raise IOError
        
        #get the fitter child
        if fit_o is None: 
            if not len(self.fits_od) == 1: 
                logger.warning('found more than one fit. taking first')
            fit_o = list(self.fits_od.values())[0]
        
        #=======================================================================
        # data setup
        #=======================================================================
        x = np.linspace(data2_o.data.min(), data2_o.data.max(), 100) #dummy x values for plotting
        
        #=======================================================================
        # formatting
        #=======================================================================
        if title is None: title ='%s %s prob plot'%(self.name, self.fit_name)
        
        logger.debug('%s with x: %s'%(title, x.shape))
        
        ax = self.plot(fit_o, indp_dato = data2_o, indp_ar = x,
                        title = title,
                        ax = ax, wtf=wtf, **kwargs)
        
        return ax
        
    def plot_fit(self, title = None, wtf=None,ax = None):
        
        #=======================================================================
        # defauilts
        #=======================================================================
        logger = self.logger.getChild('fit_LogisticRegression')
        if wtf is None: wtf = self.session._write_figs

        
        #=======================================================================
        # formatters
        #=======================================================================
        if title is None: title = 'plot %s fit of \'%s\'  to \'%s\''%(self.fit_name, self.name,self.data2_o.name)
        
        annot = 'LogisticRegression coefs: \nn_iter_ = %i, coef_ = %.2e, intercept_ = %.2f, xmin = %.2f \n' \
            %(self.reg.n_iter_, self.reg.coef_, self.reg.intercept_, self.data2_o.data.min()) \
            + 'loc = %.2f, scale = %.2f'%(self.loc, self.scale)
                
        #=======================================================================
        # plot the raw data
        #=======================================================================
        ax = self.plot_asnum(ax = None, wtf = False, title = title, annot = annot)
        ax = self.plot_probs(ax = ax, wtf = False)
        
        #=======================================================================
        # setup the synthetic data
        #=======================================================================
        plt.legend() #turn teh legend on

        
        """
        plt.show()
        
        
        reg = self.reg
        from scipy.stats import logistic
        x = np.linspace(self.data2_o.data.min(), self.data2_o.data.max(), 100) #dummy x values for plotting
        
        import math.exp
        
        for value in [reg.n_iter_, reg.coef_, reg.intercept_]:
            value = float(value)
            #print value
            print 1.0/value
            
            print math.exp(value)
            print 1.0/math.exp(value)
             
            print math.exp(-value)
            print 1.0/math.exp(-value)
            
            print math.exp(1.0/value)
            print math.exp(-1.0/value)
            
            try:
                1/print math.log(value)
                1/print math.log(1/value)

            except:
                print ('failed on %.2f'%value)
            pass
        
        int() 
        1.0/int(reg.n_iter_)
        
        loc = 
        scale = float(self.reg.coef_) #way too low
        
        reg.get_params() #nothing useful
        
        scale = -float(self.reg.intercept_) #bad
        
        float(self.reg.intercept_) #bad
        
        

        
        ax.plot(x,ylogistic ,'b-', lw=1, alpha=0.6, label='logistic pdf')
        
        
        self.reg.coef_
        self.reg.intercept_
        
                logger.info('finished with coef_  = %.2f,  intercept_  = %.2f, n_iter_  = %.2f' 
                    %(reg ,  , reg.n_iter_ ))
        
        """
        
        if wtf: 
            fig = ax.figure
            flag = hp.plot.save_fig(self, fig, dpi = self.dpi)
            if not flag: raise IOError 
            
        return ax
    

        
        