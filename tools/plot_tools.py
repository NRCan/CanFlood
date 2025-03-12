'''
@author: cefect

refining risk curves

2021-11-03: copied from Kent
 
'''
#===============================================================================
# IMPORTS-----------
#===============================================================================

#===============================================================================
# python basics
#===============================================================================
import os, datetime

 


import pandas as pd
import numpy as np

#===============================================================================
# CanFlood generals
#===============================================================================
from canflood.hlpr.basic import force_open_dir, view

from canflood.hlpr.exceptions import Error

from canflood.results.compare import Cmpr

def plot_fixr(
        cf_fp_xls=r'C:\LS\03_TOOLS\_jobs\202012_kent\_ins\risk_curve\kent_risk_curves_01.xls',
        name='Kent',
        tag='',
        ylabs = ['AEP', 'impacts'], #types of plots_custom to generate
        out_dir=None,
        ):
    """
    standalone of LMLses.plot_combine()
    """
 
    #===========================================================================
    # #collect control file paths
    #===========================================================================
    df = pd.read_excel(cf_fp_xls, index_col=0)
    cf_fp_d = df.iloc[:,0].to_dict()
    
    #check it
    for tag, fp in cf_fp_d.items():
        assert os.path.exists(fp), 'bad fp on %s: \n    %s'%(tag, fp)
    
    
    
    
    #===========================================================================
    # setup the worker
    #===========================================================================
    
    wrkr=Cmpr(fps_d=cf_fp_d, tag=tag, out_dir=out_dir)
    plt, matplotlib = wrkr.plt, wrkr.matplotlib
    
    _ = wrkr.load_scenarios()
    #=======================================================================
    # get data
    #=======================================================================
    cdxind_raw, cWrkr = wrkr.build_composite()
    
    #trim
    """
    view(cdxind)
    cdxind.index
    cdxind.index.levels[1]
    cdxind_raw.index
    """
    #cdxind = cdxind_raw.drop(labels=[10000], axis=0, level=1)
    
    #cdxind.index = cdxind.index.remove_unused_levels()
    
    cdxind=cdxind_raw


    #===========================================================================
    # generate plo9ts
    #===========================================================================
    d = dict()
    for ylab in ylabs:

        
        #=======================================================================
        # default figure
        #=======================================================================
        fig = wrkr.plot_rCurveStk_comb(dxind_raw=cdxind, y1lab=ylab, plotTag=name,
                                       impactFmtFunc=lambda x:'{:,.0f}'.format(x/1000),
                                       title='',
                                       )
        
        #=======================================================================
        # #custom legend
        #=======================================================================
        #get data
        #sEAD_ser = pd.Series(wrkr.ead_d)
        
        #retireve the axis
        ax1= fig.axes[0]
        
        """
        plt.show()
        """
        
        h1, l1 = ax1.get_legend_handles_labels() #get the default handles/labels
        #legend = ax1.legend()
        
        #convert tags to lables
        l2 = [df.loc[tag, 'label'] for tag in l1]
        
        #set new handles
        ax1.legend(h1, l2)
        
        #reset label
        ax1.set_xlabel('$CAD (\'000)')
        #=======================================================================
        # legends = [c for c in ax1.get_children() if isinstance(c, matplotlib.legend.Legend)]
        # assert len(legends)==1
        # legend=legends[0]
        #=======================================================================
        #=======================================================================
        # output
        #=======================================================================
        d[ylab] = wrkr.output_fig(fig, fname='riskCurves_%s_%s_%s'%(
            name, ylab, datetime.datetime.now().strftime('%Y%m%d')))
        
    
    #===========================================================================
    # output data
    #===========================================================================
    ofp = os.path.join(wrkr.out_dir, 'values_%s_%s.xls'%(name, datetime.datetime.now().strftime('%Y%m%d')))
    with pd.ExcelWriter(ofp) as writer:       
        cdxind.to_excel(writer, sheet_name='smry', index=True, header=True)
        
    print('finished on %i at %s'%(len(d), wrkr.out_dir))
    return out_dir
        
    


 
    