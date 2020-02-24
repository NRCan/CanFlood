'''
Created on 2019 04 01

@author: cef


pyqgis3

converting columns

'''
#===============================================================================
# GLOBALS --------------------------------------------------------------------
#===============================================================================
__version__ = '0.0.1'

import logging, logging.config, os, sys, datetime, gc, copy

start = datetime.datetime.now() #start the clock

#module directory
mod_dir = os.path.dirname(__file__)

normal_dir = r'C:\LS\03_TOOLS\LML\_ins\icomp'

profile = False #wheter to execute as a profile run

def run(
    #===========================================================================
    # VARS and KWARGS ------------------------------------------------------------
    #===========================================================================
            #main directory and control file setup
            pars_fp            = os.path.join(normal_dir,'icomp_01.xls'), 
            #control file name.    '*gui' = use gui (default).
            work_dir            = '*pauto', #control for working directory. 'auto'=one directory up from this file.
            out_dir             = '*auto', #control for the out_dir. 'auto': generate out_dir in the working directory; 'gui' let user select.
            
            #logger handling
            _log_cfg_fn         = 'logger.conf', #filetail of root logging configuration file (relative to mod_dir)
            
            #file write handling
            _write_data         = True, #write outputs to file
            _write_gis          = True, #write gis layer results
            _write_figs         = False, #flag whether to write the generated pyplots to file
            _write_ins          = True, #flag whether to writ eht einputs to file
            
            #debug handling
            db_f                = False, #flag to run in debug mode (extra tests)
            _parlo_f            = False,  #flag to run in test mode (partial ddata loading) (ignores _dbg)
            
            force_open          = True #force open the outputs folder
            ):
    
    #===============================================================================
    # SETUP.logger ----------------------------------------------------------
    #===============================================================================
    logcfg_file = os.path.join(os.path.dirname(mod_dir), '_pars',_log_cfg_fn)
    
    if not os.path.exists(logcfg_file):  
        print('No logger Config File found at: \n   %s'%logcfg_file)
        raise IOError
    
    logger = logging.getLogger() #get the root logger
    logging.config.fileConfig(logcfg_file) #load the configuration file
    'this should create a logger in the modules directory /root.log'
    logger.info('root logger initiated and configured from file at %s: %s'%(datetime.datetime.now(), logcfg_file))
    
    #===============================================================================
    # SETUP.dirs ------------------------------------------------------
    #===============================================================================
    import hp.qt5
    #assign
    if work_dir == '*pauto': 
        'for python runs. doesnt work for freezing'
        work_dir = os.path.dirname(os.path.dirname(mod_dir)) #default to 2 directories up
        
    
    elif work_dir == '*auto':
        work_dir = os.getcwd()
        
    elif work_dir == '*gui':
        work_dir = hp.qt5.FileDialog(title='select working directory', indir = os.getcwd()).getdir()

        
    elif work_dir == '*home':
        from os.path import expanduser
        usr_dir = expanduser("~") #get the users windows folder
        
        work_dir = os.path.join(usr_dir, 'SOFDA')
        
        if not os.path.exists(work_dir): os.makedirs(work_dir)
        

    #check it
    if not os.path.exists(work_dir): 
        print('passed work_dir does not exist: \'%s\''%work_dir)
        raise IOError #passed working directory does nto exist
        
    os.chdir(work_dir) #set this to the working directory
    logger.debug('working directory set to \"%s\''%os.getcwd())
    #===========================================================================
    # SETUP.control file -----------------------------------------------------------
    #===========================================================================
    if pars_fp == '*gui':
        pars_fp = hp.qt5.FileDialog(title='select control file', 
                                    indir =work_dir,
                                    filter = "CSVs (*.csv)",
                                    logger=logger).openfile()

    if not os.path.exists(pars_fp):
        print('passed parfile \'%s\' does not exist'%pars_fp)
        raise IOError
    
    _, pars_fn = os.path.split(pars_fp) #get the conrol file name

    #===========================================================================
    # SETUP.out_dir --------------------------------------------------------
    #===========================================================================
    
    import hp.basic
    import icomp.scripts_icomp as scripts #special scripts for this analysis
    from hp.exceptions import Error
    
    if _write_data or _write_figs or _write_ins:
        if out_dir == '*auto':
            'defaulting to a _outs sub directory'
            outparent_path =  os.path.join(work_dir, '_outs')
            if not os.path.exists(outparent_path):
                logger.warning('default outs path does not exist. building')
                os.makedirs(outparent_path)
                
            out_dir = hp.basic.build_out_dir(outparent_path, basename = pars_fn[:-4])
            
        elif out_dir == '*gui':
            raise IOError
            #out_dir = hp.qt5.FileDialog(title='select working directory', indir = os.getcwd()).getdir()
            
        #check and build
        if not os.path.exists(out_dir):
            logger.warning('selected out_dir exists (%s)'%out_dir)
            raise IOError


        #=======================================================================
        # #setup the ins copy
        #=======================================================================
        inscopy_dir = os.path.join(out_dir, '_inscopy')
        if _write_ins: 
            os.makedirs(inscopy_dir)
            for obj in (pars_fp, __file__, scripts.__file__):
                if not hp.basic.copy_file(obj, inscopy_dir, logger=logger): 
                    raise Error('failed to copy file: \n %s'%obj)

        
        
        #===============================================================================
        # # Load duplicate log file
        #===============================================================================
        logger_file_path = os.path.join(out_dir, '%s.log'%__name__)
        handler = logging.FileHandler(logger_file_path) #Create a file handler at the passed filename 
        handler.setLevel(logging.INFO) #set the level of the handler
        logger.addHandler(handler) #attach teh hasndler to the logger
        logger.info('session info logger made in: %s'%logger_file_path)
        

        
    else:
        logger.info('output flags set to false. out_dir and inscopy_dir set to _none')
        out_dir, inscopy_dir = '_none', '_none'
        
    
    
    #=======================================================================
    # IMPORTS ----------------------------------------------------------------
    #=======================================================================
    


    import pandas as pd
    import numpy as np
    
    from qgis.core import QgsFeatureRequest, QgsWkbTypes, QgsVectorLayer, QgsGeometry
    
    from PyQt5.QtCore import QVariant, QMetaType 
    
    
    import hp.pd, hp.np
    import hp.Q.core 
    
    from hp.pd import df_check
    
    from hp.np import left_in_right as linr
    
    from hp.Q.core import log_all, view, vlay_check
    
    from hp.Q.algos import Alg


    #===============================================================================
    # INITILIZING ------------------------------------------------------------
    #===============================================================================
    #build the session
    Ses = scripts.Session(  #initilize the session
                            pars_fp = pars_fp,
                            out_dir = out_dir,
                            _write_data=_write_data,
                            _write_figs=_write_figs,
                            _write_ins=_write_ins,
                            _write_gis = _write_gis,
                            db_f = db_f,
                            _parlo_f = _parlo_f
                            ) 
    
    Ses.load_pars_xls(mixed_colns_d=None) #load the parameter file
    Ses.set_crs(authid = Ses.crs_id) #sett the coordinate reference system
    Ses.load_aoi()
    mstore = Ses.mstore 
    
    #===========================================================================
    # RUN. common layers setup-----------
    #===========================================================================
   
    #===========================================================================
    # common layer pars
    #===========================================================================
    coms_df = Ses.psetup('coms_df', 
                                  ptag = 'coms_df',
                                  exp_colns = ['dtag', 'fn',  'exp_fieldns', 'fkey', 'scl_fieldns'],
                                  #exp_tags = ('inv',),#let teh user pass w/e
                                  fp_coln = 'fn', #column with filenames/paths
                                  base_dir = Ses.coms_dir,
                                  )

    #get tuple data pars
    exp_fieldns_d = hp.pd.tlike_to_valt_d(coms_df['exp_fieldns'], logger=logger)
    scl_fieldns_d = hp.pd.tlike_to_valt_d(coms_df['scl_fieldns'], logger=logger)
    
    #combine
    for dtag, efnl in copy.copy(exp_fieldns_d).items():
        exp_fieldns_d[dtag] = list(set(efnl).union(scl_fieldns_d[dtag]))
        
        
    #===========================================================================
    # #set some locals
    #===========================================================================
    xid = 'xid'
    zid = 'zid'

    #set these on the session
    Ses.zid = zid
    Ses.xid = xid   
    db_f = Ses.db_f
    


    #===========================================================================
    # loop and asesmble -------------------------
    #===========================================================================
    res_df = None #all results
    mbucket_df = None #bucket results
    for dtag, par_ser in coms_df.iterrows():
        """
        lets add a bunch of new columns, then clean out the raw columns at the end
        """
        log = logger.getChild(dtag)
        scl_fieldns = list(scl_fieldns_d[dtag])
        
        #start field names to keep
        keep_fieldns =['zid', 'xid', 'fclass', 'x', 'y', 'gel', 'fscale', 'fcap', 'felv']
        

        #=======================================================================
        # get this data---------------
        #=======================================================================
        #load the vlay
        fvlay_raw = Ses.load_layer(par_ser,
                                   data_dir = Ses.coms_dir,
                                   mstore=True, 
                                   as_mlay=False, 
                                   as_centroids=False, #helps w/ overlap
                                   allow_none = True, logger=logger, aoi_vlay='project', update_meta=False)
        
        #none check
        if fvlay_raw is None:
            log.warning('got nothing for \'%s\'... skipping'%(dtag))
            continue
        
        #get the data
        df_raw = hp.Q.core.vlay_get_fdf(fvlay_raw, logger=log).drop('ogc_fid', axis=1, errors='ignore')
        #df_raw['fid'] = df_raw.index
        
        
        log.info('assembling for \'%s\' w/ %s'%(
            dtag, str(df_raw.shape)))
        
        

        #=======================================================================
        # check it
        #=======================================================================
        if db_f:
            df_check(df_raw, exp_colns=exp_fieldns_d[dtag], exp_real_colns=scl_fieldns, key=xid, logger=log)

        
        df = df_raw.copy()
        
        #=======================================================================
        # nasty typesetting
        #=======================================================================
        if dtag == 'sfd':
            df.loc[:, 'stor'] = df['stor'].astype(int).astype(str) +'sty'
        
        #=======================================================================
        # coalesce sub_class
        #=======================================================================
        df.loc[:, 'sclass'] = df[scl_fieldns.pop(0)] #start w/ the first
        
        df.loc[:, 'sclass'] = df['sclass'].str.cat(
            others=df.loc[:, scl_fieldns], sep='.')
        
        keep_fieldns.append('sclass')
        
        #=======================================================================
        # add sub-class bucket nbumber
        #=======================================================================
        #build the bucket frame
        bucket_df = df['sclass'].value_counts().to_frame().reset_index().rename(columns={'sclass':'counts'})
        bucket_df = bucket_df.rename(columns={'index':'sclass'}).reset_index().rename(columns={'index':'buck_id'})
        bucket_df.loc[:, 'buck_id'] = bucket_df['buck_id']+1 #advanc the indexer so we dont have zeros
        bucket_df['fclass'] = dtag
        
        #vlookup in the bucket id
        df = df.merge(bucket_df.loc[:, ['sclass', 'buck_id']], 
                 on='sclass', how='left', validate='m:1')
        
        keep_fieldns.append('buck_id')
        #=======================================================================
        # rename nesters
        #=======================================================================
        #get all the nested field names
        nest_fieldns = sorted(list(set(df.columns.tolist()).difference(keep_fieldns).difference(scl_fieldns_d[dtag])))
        
        #make sure these all have underscores
        boolcol = pd.Series(nest_fieldns, index=nest_fieldns).str.contains('_')
        
        if not boolcol.all():
            raise Error('%i nestinf fields missing an underscore'%np.invert(boolcol).sum())
        
        #assemble the rename paramters
        valid_l = ['cap', 'scale', 'tag', 'elv']
        counter = 1
        first = True
        oprefix = None
        rename_d = dict() #container for re-mapping
        for coln in nest_fieldns:
            prefix, body = coln[:2], coln[2:]
            
            if not body in valid_l:
                raise Error('got invalid nested coln: %s'%body)
            
            if first:
                first = False
            else:
                #see if we should advance the counter
                if not prefix == oprefix:
                    counter +=1 

            rename_d[coln] = 'f%i_%s'%(counter, body)
            
            oprefix = prefix
            
            
        #do some checks
        #make sure its dividisuble by 4
        if not len(rename_d)%4 == 0:
            raise Error('got the wrong number of nested paramters... requires 4 of each \n    %s'%rename_d)
            
        #apply the renaming
        df = df.rename(columns=rename_d)
        
        log.info('renamed %i nested columns \n    %s'%(len(rename_d), rename_d))
        
        keep_fieldns = keep_fieldns + list(rename_d.values())
        
        
        #=======================================================================
        # ftag
        #=======================================================================
        df.loc[:,'ftag'] = df['fclass'].str.cat(others = df['sclass'], sep='.')
        
        keep_fieldns.append('ftag')
        
        #=======================================================================
        # combine
        #=======================================================================
        
        df1 = df.loc[:, keep_fieldns].set_index(xid, drop=False)
        if res_df is None:
            res_df = df1
            mbucket_df = bucket_df
        else:
            res_df = pd.concat([res_df, df1], sort=False)
            mbucket_df = pd.concat([mbucket_df, bucket_df], sort=False, ignore_index=True)
            """
            view(res_df)
            """
    log = logger
    #===========================================================================
    # meta------------------------
    #===========================================================================
    
    
    
    #=======================================================================
    # write-------------
    #=======================================================================
    #re-order some columns
    res_df = hp.pd.reorder_coln(res_df, [ zid, 'fclass', 'sclass','gel', 'buck_id'], logger=log, first=False )
    res_df = hp.pd.reorder_coln(res_df, [xid, 'ftag', 'fscale', 'fcap', 'felv'], logger=log )
    #===========================================================================
    # write csv results
    #===========================================================================
    #collapsed data
    log.info('writing %s to file'%str(res_df.shape))
    out_fp = os.path.join(out_dir, 'csv', Ses.new_nm)
    hp.pd.write_to_csv(out_fp, res_df)
    

    #=======================================================================
    # re-assemble layer
    #=======================================================================

    if Ses.write_vlay:
        #=======================================================================
        # main
        #=======================================================================
        logger.info('building results as a layer from %s'%(str(res_df.shape)))
        
        
        #collect into layer 
        """using the xy values rather than the polygons here"""
        res_vlay = Ses.vlay_new_df(res_df, geo_fn_tup=('x', 'y'), layname =  Ses.new_nm,
                                   logger=log, db_f=db_f)
        
        _ = Ses.write_layer(res_vlay, update_meta=False, db_f=db_f)
        
        
    #===========================================================================
    # report
    #===========================================================================
    if Ses.report:
        hp.pd.data_report(res_df, logger=log,
                          out_filepath = os.path.join(out_dir, '%s_rpt'%Ses.new_nm))


    #=======================================================================
    # METADATA-----------------------------------------------------------------
    #=======================================================================
    log = logger
    
    #===========================================================================
    # counts
    #===========================================================================
    bkt_cnt_df = mbucket_df['fclass'].value_counts().to_frame().reset_index(
        ).rename(columns={'fclass':'counts'}).rename(columns={'index':'fclass'})

    #===========================================================================
    # assemble and write spreadsheet
    #===========================================================================
    meta_d = {
              'data smry':Ses.meta_df.sort_index(),
              'buckets': mbucket_df,
              'bucket_cnts':bkt_cnt_df,
              'pars':Ses.ses_df, 
              }
    
    if db_f:
        meta_d['res_df'] = res_df

            
    outpath = os.path.join(out_dir, 'icomp_%s_meta'%(Ses.tag))
    hp.pd.write_to_xls(outpath, meta_d, logger=logger)

    #===========================================================================
    # WRAP-----------------------------------------------------------------
    #===========================================================================
    
    stop = datetime.datetime.now()
    logger.info('finished in %s'%(stop - start))
    
    if force_open and (not out_dir is '_none'): hp.basic.force_open_dir(out_dir)


    return
    


if __name__ =="__main__":    
    
    exe_str = 'run(work_dir=\'*pauto\', out_dir=\'*auto\')'
    
    if profile: 
        import hp.prof
        
        hp.prof.profile_run_skinny(exe_str)
        
    else:
        exec(exe_str)
    
    #for standalone runs
    print('finished')
















