'''
Created on Aug 30, 2018

@author: cef

scripts for handling dynamic objects

'''
#===============================================================================
#IMOPRTS --------------------------------------------------------------------
#===============================================================================
import os, sys, copy, random, re, logging, weakref, time, inspect



from collections import OrderedDict


from weakref import WeakValueDictionary as wdict
from hlpr.exceptions import Error

import pandas as pd
import numpy as np
import scipy.stats 

#import model.sofda.hp.basic as hp_basic
import model.sofda.hp.oop as hp_oop
#import model.sofda.hp.sim as hp_sim
#import model.sofda.hp.sel as hp_sel

mod_logger = logging.getLogger(__name__)
mod_logger.debug('initilized')

class Dyno_wrap(object): #wraspper for objects which will ahve dynpamic pars applied to them
    

    
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dyno_wrap')
        logger.debug('start __init__ on %s'%self.__class__.__name__)
        
        #=======================================================================
        # defaults
        #=======================================================================
        # user provided handles
        'all of these are now stored on the Session'

        # calculated pars
        self.upd_cmd_od       = None #dictionary of functions queued for update. upd_cmd_od[str(upd_cmd)] = [att_name, req_o, req_str]
        self.fzn_an_d        = None #dictinoary of frozen attribute names. d[att_name] = [req_o, req_str]
        self.dynk_lib        = None #library of dynk dictionaries
        
        self.dynk_perm_f     = True #flag that your dynks are permanent       
        
        self.post_upd_func_s     = None #common container of post upd functions per object

        # data containers
        self.upd_cnt = 0 #counter for number of update() runs
        
        
        
        #=======================================================================
        # _init_ cascade
        #=======================================================================
        
        super(Dyno_wrap, self).__init__(*vars, **kwargs) #initilzie teh baseclass 
        
        #=======================================================================
        # unique attributes
        #=======================================================================
        
        'put thsi here so each object gets a unique empty dictionary'
        self.upd_cmd_od      = OrderedDict()  #dictionary of functions queued for update
        self.fzn_an_d       = dict() #d['att_nme':'controller'] of frozen attribute names. see apply_to_set(). should clear each sim
        
        self.reset_d.update({'upd_cnt':0, 'fzn_an_d':dict()})
        
        if not isinstance(self.gid, str):
            raise IOError
        
        #=======================================================================
        # common attributes
        #=======================================================================
        if self.sib_cnt == 0:
            self.dynk_ns        = set() #set of (dynamically wrapped) kid names specified in your handles (other classes you update)
            'I think we ar eOK with this being shared'
            logger.debug('setting handles \n')
        
        #=======================================================================
        # unique
        #=======================================================================
        'todo: make sure cascade is in the proper order so we can update this if necessary'
        self.post_upd_func_s = set()
        
        if self.db_f: 
            pass
            """called during _init_dyno
            logger.debug('check_dynh \n')
            self.check_dynh()"""
            
            
        """unfortunately, the originating caller has not completed its __init__
            (setup function shave not completed
        self.init_dyno()"""
        
        logger.debug('__init__ finished on %s'%self.__class__.__name__)
        
        return

    def get_hndl(self, par): #shortcut to pull the passed handle from the session
        
        return self.session.dyno_pars_d[self.__class__.__name__][par]
        
 
    def init_dyno(self): #initizlie my dynamic par attributes
        """
        because this requries the full library to be initilized, ive pulled all these commands out
        
        generally, this needs to be explicitly called (generally at the end)of the callers __init__
        
        called for all siblings
        """
        logger = self.logger.getChild('init_dyno')
        if self.perm_f:
            
            #===================================================================
            # handle post updating
            #===================================================================
            if len(self.post_upd_func_s) > 0:
                
                #see if any of your stats are being output
                if not self.__class__.__name__ in list(self.session.outpars_d.keys()):
                    logger.warning('I have no outputers loaded on myself. clearing self.post_upd_func_s')
                    self.post_upd_func_s = set()
                    
                else:
                    #calc all these before setting the og
                    if not self.mypost_update():
                        raise IOError
                
                    #add yourself to the post updating que
                    self.session.post_updaters_wd[self.gid] = self
                
            
            logger.debug('set_og_vals \n')
            self.set_og_vals()

        
            """NO! each sibling has a unique set of dynk
            if self.sib_cnt == 0:
                logger.debug('getting dyno kids \n')"""
        
        #=======================================================================
        # setup your dependents
        #=======================================================================
        'for non-permanents this sets an empty dict'
        self.set_dynk_lib()  
                
        if self.db_f:
            logger.debug('check_dynh \n')
            self.check_dynh()
            
        logger.debug('finished \n')
        return
            
            
    def check_dynh(self): #check that the obj and its parent have the passed handels
        """
        checking hte handles under set_dyno_handles
        #=======================================================================
        # CALLS
        #=======================================================================
        init_dyno()
        """
        logger = self.logger.getChild('check_dynh')
        df = self.session.dynp_hnd_d[self.__class__.__name__] #get your handle pars
        logger.debug('on dynp_hnd_df %s'%str(df.shape))
        #=======================================================================
        # check yourself
        #=======================================================================
        #self_upd_cmds = df.loc[:,'self_upd'].iloc[0]
        self_upd_cmds = self.session.dyno_pars_d[self.__class__.__name__]['self_upd']
        
        self.check_upd_cmds(self_upd_cmds)
        
        """ not using real children, should perform full check
        if not self.perm_f:
            logger.debug('perm_f = FALSE. skipping children check')"""
            
        if self.dynk_lib is None:
            raise IOError
        
        for attn in self.get_hndl('dyn_anl'):
            if not hasattr(self, attn):
                raise Error('%s missing attribute \'%s\''%(self, attn))
            
        return
        
        
    def check_upd_cmds(self, upd_cmds_d): #check the updating command
        
        #=======================================================================
        # precheck
        #=======================================================================
        if not isinstance(upd_cmds_d, dict):
            raise IOError

        #=======================================================================
        # checker
        #=======================================================================
        for attn, meth_t in upd_cmds_d.items():
            if not isinstance(meth_t, tuple):
                raise IOError
            #loop each method and make sure we have it
            for meth_raw in meth_t:
                #check for special methods
                if meth_raw.startswith('*'):
                    meth = meth_raw[1:] #drop the flag
                else:
                    meth = meth_raw
                
                
                #now checck we ahve this method                
                if not hasattr(self, meth):
                    raise Error('%s is missing a method requested in the handles: %s'
                                  %(self.__class__.__name__, meth))
                    
        return

        
    def set_dynk_lib(self, container=wdict): #build your subscription list
        """
        The goal here  is to build a library of subscriber dictionaries during __init__
            so we dont have to make additional calls to this
        
        """
        #=======================================================================
        # shortcuts
        #=======================================================================
        if len(self.dynk_ns) == 0: 
            self.dynk_lib = container() #just set an empty container
            return
        
        if not self.perm_f:
            self.dynk_lib = container() #just set an empty container
            return
            
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('set_dynk_lib')
        s = self.dynk_ns
        d = dict() #a library of wdicts
        
        #=======================================================================
        # prechecks
        #=======================================================================
        #if not self.session.state == 'init':
        if self.db_f:
            if not self.perm_f: raise IOError
            
        #=======================================================================
        # build the dictionary
        #=======================================================================
        logger.debug('on %i subscriber types: %s \n'%(len(s), s))
        for dynk_cn in s:
            logger.debug('building for dynk_cn \'%s\''%dynk_cn)
            
            book = self.get_dyn_kids_nd(dynk_cn, container=container)
            
            obj1 = list(book.values())[0]
            
            if obj1.perm_f:
            
                d[dynk_cn] = book
                
            else:
                logger.debug('this dynk \'%s\' is non-permanent. excluding from dynk_lib'%obj1.__class__.__name__)
                continue
            
            #if not isinstance(book, container): raise IOError
            
        logger.debug('setting dynk_lib with %i entries'%len(d))
        self.dynk_lib = copy.copy(d)
        
        return
        
        
    def get_dyn_kids_nd(self,  #get the child objects you apply updates to
                        dynk_cn,  #class name to build set of
                        container=wdict,
                        logger = None,
                        **report_kwargs):
        """
        This is a hierarchical simple object selection (does not use Selectors)
        
        #=======================================================================
        # TODO
        #=======================================================================
        consider making this more explicit 
            user should specify if they expect a descendant object returned o
        """
        #=======================================================================
        # defaults
        #=======================================================================
        if logger is None: logger = self.logger
        logger = logger.getChild('get_dyn_kids_nd')
        
        'using update commands so weak references are set'
        
        
        logger.debug('building container of \'%s\''%dynk_cn)
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            cn = self.__class__.__name__
            #check special keys
            if dynk_cn.startswith('*'):
                pass
            
            elif dynk_cn.startswith('+'):
                dynk_cn1 = dynk_cn[1:]#drop the prefix
                #check this cn is in the library
                if not dynk_cn1 in list(self.session.family_d.keys()):
                    logger.error('requested cn \'%s\' not fo und in the family_d.. load order?'%(dynk_cn))
                    raise IOError
            else:
                pass
            
            #===================================================================
            # #check dummy requests
            # """allowing these now"""
            # if dynk_cn == 'Dmg_feat' and cn == 'House':
            #     logger.debug('checking a House looking for a Dmg_feat')
            #     #loop through your kids
            #     gk_d = dict()
            #     for name, kid in self.kids_d.items():
            #         if not kid.__class__.__name__ == 'Dfunc':
            #             raise IOError
            #         
            #         """dont want to check yet because were still makign changes
            #         kid.check_dfunc()"""
            #         
            #         
            #         gk_d.update(kid.kids_d) #add the grand kids
            #         
            #         if kid.dummy_f:
            #             logger.debug('%s is a dummy'%name)
            #     
            #     if len(gk_d) == 0:
            #         logger.debug('no dfeats!')
            #===================================================================
                
        #=======================================================================
        # perform the search
        #=======================================================================
        dynk_nd = container()
        

        
        """not using these anymore
        #=======================================================================
        # special vars
        #=======================================================================
        if dynk_cn.startswith('*'):
            dynk_cn1 = dynk_cn[1:]#drop flag
            
            if re.search(dynk_cn1, 'parent', re.IGNORECASE):
                dynk_nd.update({self.parent.name:self.parent.get_self()})

                logger.debug('got \'%s\'. setting to parent \'%s\''%(dynk_cn, self.parent.name))
            
            else:
                raise IOError #add more vars
            
        #=======================================================================
        # pull all objects of that type
        #=======================================================================
        elif dynk_cn.startswith('+'):
            dynk_cn1 = dynk_cn[1:]#drop the prefix
            dynk_nd.update(self.session.family_d[dynk_cn1]) #get subset of this generation
            logger.debug('pulled all %i  objects of type \'%s\' from teh family_d)'%(len(dynk_nd), dynk_cn))

                
        #=======================================================================
        # normal code of a class name
        #=======================================================================
        else:"""
        #=======================================================================
        # complex parent
        #=======================================================================
        if hasattr(self, 'kids_sd'):
            dynk_nd.update(self.kids_sd[dynk_cn])
            logger.debug('complex parent. pulled %i kids from page \'%s\' in teh kids_sd'%(len(dynk_nd), dynk_cn))
           
        #=======================================================================
        # simple parent
        #=======================================================================
        elif len(self.kids_d) > 0: #excluding parents with out kids (Flood)
            #===============================================================
            # direct children request
            #===============================================================
            if dynk_cn == list(self.kids_d.values())[0].__class__.__name__: #see if we match the first obj
                dynk_nd.update(self.kids_d)
                logger.debug('simple parent. pulled all \'%s\' children from kids_d (%i)'%(dynk_cn, len(dynk_nd)))
                
            #===============================================================
            # grand children request
            #===============================================================
            else:
                """not all of our users have this wrap.. easier to just copy/paste commands
                'using the Sel_usr_wrap command '
                dynk_nd.update(self.drop_subset(self.kids_d, pclass_n = dynk_cn)) #look for grandchildren as well"""
                logger.debug('simple parent. grand child request')

                # run condenser to get pick correct level set
                gk_d = hp_oop.Kid_condenser(self.kids_d, 
                                               dynk_cn, 
                                               db_f = self.db_f, 
                                               key_att = 'gid', #object attribte on which to key the result container
                                               container = container,
                                               logger = logger).drop_all()
                     
                dynk_nd.update(gk_d)
                
                #===========================================================
                # checks
                #===========================================================
                if self.db_f:
                    #make sure these grand kids know me
                    for k, v in dynk_nd.items(): 
                        if not v.parent.parent.__repr__() == self.__repr__(): 
                            raise IOError
        #=======================================================================
        # not a parent
        #=======================================================================
        else:
            pass 
            """allowing this now"""
            #===================================================================
            # """would be better to return an empty container here... 
            #     but we are setup to avoid calling this function if we dont have any kids"""
            # logger.error('report_kwargs \n    %s'%report_kwargs)
            # raise Error('%s is not a parent'%self.name)
            #===================================================================


        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if not len(dynk_nd) == 0: 
                #raise Error('%s failed to collect any dynk_nd of %s'%(self.name, dynk_cn))
        
                self.dyn_kid_check(dynk_nd) #check the consistency of all these

                
        #=======================================================================
        # set update flag
        #=======================================================================
        if self.session.state == 'init':
            if self.dynk_perm_f:
                if len(dynk_nd) == 0: 
                    raise IOError
                
                
                'setting this as a global flag (least common denominator of all kids'
                self.dynk_perm_f = list(dynk_nd.values())[0].perm_f #just steal from the first kid
                logger.debug('during init took perm_f = \'%s\' from first dynk'%(self.dynk_perm_f))


        return dynk_nd
        
    def set_og_vals(self): #set the reset vals for all the dynp kids
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('set_og_vals')
        
        #check if this is a permeanet object
        if not self.perm_f:
            logger.debug('perm_f=FALSE. no need to set ogs. skipping')
            return
        
        #=======================================================================
        # get atts on which to store
        #=======================================================================
        #pull dynamic pars
        attn_s = set(self.get_hndl('dyn_anl'))
        
        #pull stat pars from ou tputrs
        cn = self.__class__.__name__
        if cn in list(self.session.outpars_d.keys()):
            attn_s.update(self.session.outpars_d[cn])

        'this will probably overwrite a lot of the attns because we often output dyanmic atts'
        
        if self.db_f:
            #===================================================================
            # check for valid outputr request
            #===================================================================
            s = self.session.outpars_d[cn]
            for attn in s:
                if not hasattr(self, attn):
                    raise Error('got invalid output attribute request \'%s\''%attn)
                
            s = set(self.get_hndl('dyn_anl'))
            
            for attn in s:
                if not hasattr(self, attn):
                    raise Error('got invalid dynp handle attribute request \'%s\''%attn)
            
            

        #=======================================================================
        # pull values and store
        #=======================================================================
        logger.debug('from the dynp file, collecting og att vals on %i attributes: %s \n'%(len(attn_s), attn_s))
        cnt = 0
        for attn in attn_s:
            
            #get the og
            try:
                attv = getattr(self, attn)
            except:

                raise Error('attribute \'%s\' not found. check the handle file?. bad output attn request?'%(attn))
                    
            #store the og
            if attv is None:
                logger.warning('\'%s\' not loaded yet. skipping'%(attn))
                'some Dfuncs dont use all the attributes'
                'outputrs with selectors'
                #raise IOError
            
            else:
                self.reset_d[attn] = copy.copy(attv)
                
                if hasattr(attv, 'shape'): 
                    logger.debug('in reset_d added \'%s\' with shape %s'%(attn, str(attv.shape)))
                else: 
                    logger.debug('in reset_d added \'%s\' = \'%s\''%(attn, attv))
                
                cnt +=1
            

        logger.debug('finished with %i total entries colected and stored into the reset_d (%i)'%(cnt, len(self.reset_d)))
        

    def handle_upd(self, #apply the approriate updates to this object based on what att was modified
                        att_name, #attribute name we are changng
                        new_val, #new value to set
                        req_o, #object making the update request
                        call_func=None):
        """
        adds all the commands listed in the handle pars for this attribute (and its children)
        
        2018 08 21
        reworked this so it should accept updates from dynps or functions
        #=======================================================================
        # CALLS
        #=======================================================================
        Dynamic_par.apply_to_set() #dynamic parameter changes
        
        Dyn_wrapper.some_func() #object driven changes
           
        
        #=======================================================================
        # INPUTS
        #=======================================================================
        run_upd_f = TRUE:
            more efficients. allows each dynp to make its changes
                then updates are applied only to the objects once they are run
        
        run_upd_f = False:
            applies the update during each dynp
            necessary for those objects which do not have a run routine
        

        """
        #=======================================================================
        # shrotcuts
        #=======================================================================
        """NO! we us the updaters and the setters during init
        if self.session.state == 'init': return"""
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('handle_upd')
        if call_func is None: 
            raise Error("call explicitly")
            #call_func = inspect.stack()[1][3] #get the caller function
        
        old_val = getattr(self, att_name)
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            cn = self.__class__.__name__
            if not hasattr(new_val, '__len__'):
                logger.debug('on att_name=%s, new_val=%s, old_val=%s, req_o=%s'%(att_name, new_val, old_val, req_o))
            else:
                logger.debug('on att_name=%s req_o=%s'%(att_name, req_o))

            cn = self.__class__.__name__
            if req_o.__class__.__name__ == 'Dynamic_par':
                if att_name in self.get_hndl('lock_anl'):
                    raise Error('change attemnpted on locked attribute \'%s\''%att_name)
            
            if not att_name in self.get_hndl('dyn_anl'):
                raise Error('%s attempted update to attribute not in handles \n     \'%s\''
                              %(self.name, att_name))
            
            if not hasattr(self, att_name): 
                raise IOError
            
            if not isinstance(req_o, weakref.ProxyType):
                raise IOError
            
            #special checker for non residential code changes
            if cn == 'House' and att_name == 'acode_c':
                if not self.asector == 'sres':
                    raise Error('acode updates for \'%s\' not implemented'%self.asector)
                
            
            #type ch ecker
            if not old_val is None:
                if not type(old_val) == type(new_val):
                    """allowing this now, because sometimes were just flipping numpy types"""
                    logger.warning('\'%s.%s\' type mismatch %s !=%s'%(cn, att_name, type(old_val), type(new_val)))
        
        #=======================================================================
        # clear the caller
        #=======================================================================
        #try and remove the calling function from teh updates
        """
        want to do this in all cases as the caller has just executed
        for object.somefunc custom calls, this makes sure we havent requed the command
        
        for some complex updates, we may still be added back by some later, larger update function string"""
        
        if not call_func.startswith('_'):
            self.del_upd_cmd(cmd_str = call_func) #try and remove the caller from the queue
            
        #=======================================================================
        # shrotcuts
        #=======================================================================
        """because we take array, lists, and singletons, we cant do much fancy type checking"""
        if not old_val is None:
            
            #array type check
            if np.array(new_val == old_val).all():
                logger.debug('for \'%s\' new_val == old_val (array) ...skipping'%att_name)
                return
            
            #special float checker
            if isinstance(new_val, float):
                if round(new_val, 2) == round(old_val, 2):
                    logger.debug('for \'%s\' (floats %.2f = %.2f)... skipping'%(att_name, new_val, old_val))
                    return
                
            #regular singleton checker
            elif not hasattr(new_val, '__len__'):
                if new_val == old_val:
                    logger.debug('for \'%s\' (%s=%s) singleton %s... skipping'%(att_name, new_val, old_val, type(new_val)))
                    return
                

            
            
        
        #=======================================================================
        # Freeze check
        #=======================================================================
        if att_name in list(self.fzn_an_d.keys()):
        
            logger.debug('change on \'%s\' requested by \'%s\' is frozen by \'%s.%s\'. skipping'
                         %(att_name, req_o.name, self.fzn_an_d[att_name][0].name, self.fzn_an_d[att_name][1]))
            
            if self.fzn_an_d[att_name].name == req_o.name:
                raise Error('The requested froze this attribute and am trying to change it again')
            
            return
        
        """ we only want to allow dynps to freeze attributes"""
        #=======================================================================
        # PRIMARY update (set the new value)
        #=======================================================================
        if not pd.isnull(np.array(new_val)).all():

            setattr(self, att_name, new_val)
            logger.debug('set attribute \'%s\' with \'%s\''%(att_name, type(new_val)))
            
            
            if self.db_f:
                #tyep checking
                if not isinstance(new_val, type(old_val)) and not old_val is None:
                    if not isinstance(new_val, str): #ignore unicode/str fli9ps
                        logger.warning('for \'%s\' got type mismatch from old \'%s\' to new \'%s\''%
                                       (att_name, type(old_val), type(new_val)))
            
            
        else: 
            raise Error('why are we passing nulls here?')
            if self.db_f: 
                logger.warning('got null new_value for \'%s\'. skipping'%att_name)
        
        #=======================================================================
        # SECONDARY UPDATE HANDLING
        #=======================================================================

        #=======================================================================
        # get handles
        #=======================================================================
        #df = self.session.dynp_hnd_d[self.__class__.__name__] #get your handle pars
        
        hndl_d = self.session.dyno_pars_d[self.__class__.__name__]
        
        #=======================================================================
        # pass teh commands
        #=======================================================================
        if not self.session.state == 'init':
            #self.handle_upd_funcs(att_name, ser, req_o, call_func)
            
            #===================================================================
            # #self upd5ates
            #===================================================================
            if att_name in hndl_d['self_upd']:
                supd_meth_t = hndl_d['self_upd'][att_name] #pull from teh handles
                logger.debug('from \'%s\' handling self_upd with \'%s\''%(att_name, supd_meth_t))
                
                #pass this set to the full updater
                self.que_upd_full(supd_meth_t, att_name, req_o, call_func = call_func)
                
            else:
                logger.debug('no self updates handles for \"%s\'... skipping'%att_name)

                
            #===================================================================
            # #childrens updates
            #===================================================================
            if att_name in hndl_d['dynk_hndl']: #see if this caller attribute has any handles it needs to apply
                
                kupd_meth_d = hndl_d['dynk_hndl'][att_name] #pull from teh handles
                self.handle_kid_upd(kupd_meth_d, att_name, req_o, call_func=call_func)
                
            else:
                logger.debug('no child updates for \"%s\''%att_name)
                
        else:
            pass
                        
        #update the parents df
        if att_name in hndl_d['upd_df']: #see if this attribute has been flagged as one that should update the parents metadf 
            #logger.debug('updating parents df')
            self.parent_df_upd(att_name, new_val)


        return
        
        
      
    def handle_kid_upd(self,  #handle updates on a single type of kid
                       upd_cmd_d,
                       att_name, 
                       req_o, 
                       call_func = None, #additiona pars to pass onto upd_que
                       method ='add',
                       **que_upd_kwargs):  #kwargs to pass onto que_upd
        """
        type(upd_cmd_t)
        upd_cmd_d = upd_cmd_t
        #=======================================================================
        # kids set handling ()
        #=======================================================================
        if the dynk_cn is not found in teh kids_sd, 
            updates are passed to all objects of that cn (family_od)
        #=======================================================================
        # CALLS
        #=======================================================================
        self.handle_upd
        
        #=======================================================================
        # key vargs
        #=======================================================================
        raw_cmd_str: this could be a list of commands or a single command
        
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('handle_kid_upd')  
        
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not isinstance(upd_cmd_d, dict):
                raise TypeError
        
        #=======================================================================
        # get handles
        #=======================================================================
        #hnd = self.get_hndl('dynk_hndl')[att_name]
        
        logger.debug('from handles for \'%s\' on dynk_cn: %s \n'%(att_name, list(upd_cmd_d.keys())))
        
        #loop through each dynk_cn: cmnd  and handel updates
        for indxr0, (dynk_cn, upd_cmd_t) in enumerate(upd_cmd_d.items()):
            
            logger.debug('for dynk_cn \'%s\' %i (of %i)  with cmd_str \'%s\' '%(dynk_cn, indxr0+1, len(upd_cmd_d), upd_cmd_t))

            #=======================================================================
            # get theses dynkids
            #=======================================================================
            #dynk_nd = self.get_dyn_dynk_nd(dynk_cn)
            if dynk_cn == '*parent':  #parent shortcut
                dynk_nd = {self.parent.name: self.parent}
                
            else: 
                #===============================================================
                # #normal pull
                #===============================================================
                if dynk_cn in self.dynk_lib:
                    dynk_nd = self.dynk_lib[dynk_cn]
                    'set_dynk_lib excludes non-permanents from this'

                #===============================================================
                # no entry. (non-permanent dynkids?)
                #===============================================================
                else:
                    logger.debug("passed dynk_cn \'%s\' not in my dynk_lib. getting new pick \n "%dynk_cn)
                    dynk_nd = self.get_dyn_kids_nd(dynk_cn, logger=logger, 
                                                   att_name=att_name, 
                                                   req_o=req_o, 
                                                   call_func=call_func)#for reporting
                        

            #=======================================================================
            # prechecks with the dynkids
            #=======================================================================
            if self.db_f: 

                #check the update commands
                if not isinstance(upd_cmd_t, tuple):
                    raise TypeError
                

                #check the container we got back
                if not len(dynk_nd) == 0:
                    if dynk_cn.startswith('+'):  #???
                        dynk_cn1 = dynk_cn[1:] #drop the prefix
                    else: 
                        dynk_cn1 = dynk_cn
                    
                    obj1 = list(dynk_nd.values())[0]
                    
                    if not obj1.perm_f:
                        if dynk_cn1 in list(self.dynk_lib.keys()): 
                            raise IOError
                        
                    if not dynk_cn.startswith('*'): #exclude specials
    
                        if not obj1.__class__.__name__ == dynk_cn1: 
                            raise IOError
                    
                    if self.__class__.__name__ == 'House':
                        if dynk_cn == 'Dfunc':
                            for k, v in dynk_nd.items():
                                if not v.parent.__repr__ == self.__repr__:
                                    raise IOError
    
            #=======================================================================
            # loop and handle updates
            #=======================================================================
            if len(dynk_nd) > 1: logger.debug('on dynk_nd for \'%s\' with %i  \n'%(dynk_cn, len(dynk_nd)))

            """if dynk_nd is empty.. this will just skip"""
            indxr1 = 0
            for indxr1, (name, obj) in enumerate(dynk_nd.items()):

                logger.debug('%i (of %i) \'%s\' cmd_str \'%s\' on \'%s\' \n'%(indxr1+1, len(dynk_nd), method, upd_cmd_t, name ))
                
                if method == 'add':
                    obj.que_upd_full(upd_cmd_t,att_name, req_o, call_func = call_func, **que_upd_kwargs)
                elif method == 'delete':
                    raise Error('why are we doing this?')
                    #obj.del_upd_cmd(cmd_str = upd_cmd_t)
                else: 
                    raise IOError
                
            if indxr1 > 1:
                logger.debug('by \'%s\' handled \'%s\' on %i dependents '%(method, upd_cmd_t, indxr1))

        return

    def que_upd_full(self, #que a set of update commands on myself (from teh handler)
                    upd_cmd_t, 
                    att_name, 
                    req_o, 
                    call_func = None,
                    allow_self_que = False): 
        """
        #=======================================================================
        # USE
        #=======================================================================       
        
        #=======================================================================
        # INPUTS
        #=======================================================================
        upd_cmd: update command sent for queing by the controller
        controller: object requesting the update command
        
        upd_ovr: update override flag. forces  update here (instead of during computational run0
        
        self.run_upd_f #flag controlling whether updates are applied during a run or during each dynp.
        
        #=======================================================================
        # OUTPUTS
        #=======================================================================
        upd_cmd_od: dictionary of update commands and meta data
            keys: update command
            values: [controller requesting update, att_name controller's att name triggering this]
            
        made this a dictionary with metadata for better tracking of where the updates come from
        
        """
        #=======================================================================
        # shortcuts
        #=======================================================================
        #no updates requested
        if upd_cmd_t is None: 
            return
        
        if self.session.state == 'init': 
            """ some chidlren may que changes to the parent during __init__
            but the parents init functions shoudl trigger in such an order as to capture this
            """
            return #never que updates during init
        
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('que_upd_full') 
        
        if call_func is None: 
            raise Error('why didnt you pass this?')
            call_func = inspect.stack()[1][3]
            
        force_upd = False #set teh default force update flag.
        """if we find a * prefix, we force an update after queing all the commands
            if we find a *update.. we force the update immiedately"""
        
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not isinstance(req_o, weakref.ProxyType):
                raise IOError
            if not isinstance(upd_cmd_t, tuple):
                raise IOError
            
            #loop checks
            for ucmd_str_raw in upd_cmd_t:
                #clean the marker
                if ucmd_str_raw.startswith('*'):
                    ucmd_str = ucmd_str_raw[1:] #drop the marker
                else:
                    ucmd_str = ucmd_str_raw
                    
                    if ucmd_str == 'update':
                        raise Error('why?')
                    
                #method check
                if not hasattr(self, ucmd_str):
                    raise Error('%s doesnt have the reuqested method \"%s\''
                                  %(self.__class__.__name__, ucmd_str))
        
        #=======================================================================
        # loop and handle
        #=======================================================================
        logger.debug('handling %i update commands: %s'%(len(upd_cmd_t), upd_cmd_t))
        for indxr, ucmd_str_raw in enumerate(upd_cmd_t):
            
            if ucmd_str_raw.startswith('*'):
                ucmd_str = ucmd_str_raw[1:] #drop the marker
                force_upd = True
                position = 'head'
            else:
                ucmd_str = ucmd_str_raw
                position = 'tail'
        
        
            #===================================================================
            # SHORTCUT.already queued
            #===================================================================
            if ucmd_str in self.upd_cmd_od: 
                continue

            #===================================================================
            # SHORTCUT.reque
            #===================================================================
            if not allow_self_que:            
                if re.search(call_func, ucmd_str, re.IGNORECASE):
                    logger.debug('self request by \'%s.%s\'. doing nothing'%(req_o.name, call_func))
                    self.del_upd_cmd(cmd_str = ucmd_str) #try and remove it
                    continue
                
            #===================================================================
            # SHORTCUT.update
            #===================================================================
            if ucmd_str == 'update':
                #logger.debug('received \'*%s\'. forcing update now \n'%ucmd_str)
                
                #add yourself to the update que
                self.session.update_upd_que(self)
                
                #check to make sure we didnt miss anything
                if self.db_f:
                    if not force_upd:
                        raise Error('why wasnt this triggered yet')
                    
                continue

            #===================================================================
            # QUE this
            #===================================================================
            logger.debug('with upd_cmd \'%s\' %i (of %i), controller \'%s\' and att_name \'%s\''%
                         (ucmd_str_raw,indxr+1, len(upd_cmd_t), req_o.name, att_name))
            self.que_upd_skinny(ucmd_str, att_name, req_o, call_func, position = position)
            
            #end the upd_cmd loop
            
            
                
        #=======================================================================
        # #perform update now   
        #=======================================================================
        if force_upd:
            logger.debug('got a special update forcer. executing update() now \n')
            self.update() #force the update now

            
        return
    
    def que_upd_skinny(self, #que an update on myself (direct. withouth andles)
                       ucmd_str, 
                       att_name, 
                       req_o, 
                       call_func,
                       position='tail'): #where in teh que to add the command
        

        logger = self.logger.getChild('que_upd_skinny')
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            cn = self.__class__.__name__
            if not isinstance(ucmd_str, str):
                raise IOError
            
            if '(' in ucmd_str or ')' in ucmd_str:
                raise Error('unrecognized charachters in cmd_str: %s'%ucmd_str)
            
            if not hasattr(self, ucmd_str):
                raise Error('obj %s does not have the requested command %s'%(cn, ucmd_str))
            
            if ucmd_str in self.upd_cmd_od: 
                que_check(self)
                
            """taking either here
            if not isinstance(req_o, weakref.ProxyType):
                raise Error('%s passed a proxy object of %s'%(cn, req_o.__class__.__name__))"""
        
        #=======================================================================
        # shortcuts
        #=======================================================================
        if ucmd_str in self.upd_cmd_od: 
            logger.debug('\'%s\' already qued. skipping'%ucmd_str)
            return
        
        if ucmd_str is None: 
            return
        
        if self.session.state == 'init': 
            return
        
        #=======================================================================
        # proxy the requester
        #=======================================================================
        if not isinstance(req_o, weakref.ProxyType):
            req_o = weakref.proxy(req_o)
        
        #=======================================================================
        # add to the que
        #=======================================================================
        
        
        #add yourself to the update que
        self.session.update_upd_que(self)
        
        #add this command to your list
        self.upd_cmd_od[ucmd_str] = [att_name,req_o , call_func] 

        #adjust the position
        if position == 'head':
            self.upd_cmd_od.move_to_end(ucmd_str, last=False)

        
        logger.debug('added \'%s\' to \'%s\' of upd_cmd_od: %s'
                     %(ucmd_str, position, list(self.upd_cmd_od.keys())))
        

        return
        
    
    
    def del_upd_cmd(self, #remove the command from your que then cleanup the global que
                    cmd_str = None, #command to remove
                    logger=None): 
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        handle_upd()
            when an custom object.somefunc() calls the handle_upd
            
        needs to be called as
            self.del_upd_cmd()
        
        """
        
        #=======================================================================
        # shortcuts
        #=======================================================================
        if self.session.state == '_init_': 
            return
        
        
        #=======================================================================
        # defaults
        #=======================================================================
        #if logger is None: logger = self.logger
        
        'this is very slow!'
        if cmd_str is None: 
            raise Error('add this directly!')
            cmd_str = inspect.stack()[1][3] #just pull from the last caller
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if '(' in cmd_str or ')' in cmd_str:
                raise Error('got a command with unrecognized charageters: %s'%cmd_str)
            
            if not hasattr(self, cmd_str):
                raise Error('%s does not have requested method \'%s\''%
                            (self.__class__.__name__, cmd_str))


        #=======================================================================
        # remove command from your set
        #=======================================================================
        
        if cmd_str in self.upd_cmd_od: #check fi were even in there
            del self.upd_cmd_od[cmd_str]

        #=======================================================================
        # cleanup global que
        #=======================================================================
        'if we couldnt even remove the command from teh que.. thenw e probably dont need to remove the obj'
        if len(self.upd_cmd_od) == 0:
            self.session.update_upd_que(self, method='delete') #remvoe yourself from the que
                

        return
                
    def parent_df_upd(self, att_name, new_val): #make updates to the parents df
        logger = self.logger.getChild('parent_df_upd')
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            df = self.parent.childmeta_df
            if not self.name in df.loc[:,'name'].tolist(): 
                raise IOError
            
            if not self.dfloc in df.index.tolist():
                raise IOError
            
            if not att_name in df.columns.tolist(): 
                logger.warning('passed \'%s\' not in \'%s\'s childmeta_df columns.\n %s'%
                             (att_name, self.parent.name, df.columns.tolist()))
                """ allowing now
                raise IOError"""
            """
            
            hp_pd.v(df)
            """
            
            if pd.isnull(new_val):
                raise Error('got a null new_val')
        
        #=======================================================================
        # execute df write
        #=======================================================================
        try:
            logger.debug('updating parent \'%s\' with \'%s\' at %i'%(self.parent.name, new_val, self.dfloc))
            self.parent.childmeta_df.loc[self.dfloc, att_name] = new_val
        except:
            #===================================================================
            # error handling
            #===================================================================

            try:
                df = self.parent.childmeta_df
                if not att_name in df.columns:
                    logger.error('passed att_name \'%s\' not in the columns')
            except: 
                logger.error('something wrong with parent')
                
            if not hasattr(self, 'dfloc'):
                logger.error('I dont have a dfloc attribute')
                
            raise IOError
        
        
        
    def update(self, propagate=False):
        """ 
        #=======================================================================
        # CALLS
        #=======================================================================
        dynp.Kid.que_upd()
            run_upd_f==FALSE: this can happen during the pres session state
            
        Udev.wrap_up()
            for all objects stored during run loopd in the upd_all_d
            
        fdmg.House.run_hse()
            upd_f == TRUE
            
        fdmg.Dfunc.run_dfunc()
            upd_f == TRUE
        #=======================================================================
        # INPUTS
        #=======================================================================
        upd_cmd_od: dictionary of update commands and metadata. see Kid.que_upd
        propagate: flag to propagate your update onto your children
        
        #=======================================================================
        # TESTING
        #=======================================================================
        self.upd_cmd_od.keys()
        self.upd_cmd_od.values()
        """
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('update(%s)'%self.get_id())
        self.upd_cnt += 1
        d = copy.copy(self.upd_cmd_od) #set teh copy (as this may change throughout the loop)
        cnt = 0
        #=======================================================================
        # precheck
        #=======================================================================
        if self.db_f:
            if self.upd_cmd_od is None: raise IOError
            if len(self.upd_cmd_od) == 0: 
                logger.error('I have no commands in upd_cmd_od')
                raise IOError

            #check format of the dictionary
            if not len(list(self.upd_cmd_od.values())[0]) == 3:
                raise IOError
            
            que_check(self)
        
        #=======================================================================
        # loop and execute the LIVE updating commands
        #=======================================================================
        #id_str = self.get_id()
        logger.debug('uuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuuu')
        logger.debug('upd_cnt = %i state \'%s\' with %i cmds: \n    %s'
                     %(self.upd_cnt, self.session.state, len(self.upd_cmd_od), list(self.upd_cmd_od.keys())))

                
        for cmd_raw, v in d.items():
            att_name, req_o, req_str = v
            

            """ clearing upd_cmd_od alone (with some command) does not break this loop
                python seems to continue with the initial call to the dictionary"""
                
            if not cmd_raw in list(self.upd_cmd_od.keys()):
                logger.debug('cmd \'%s\' removed from dictionary. skipping'%cmd_raw)
            else:
                cnt +=1
                logger.debug('executing upd_cmd() %i (of %i) with cmd_raw \'%s\' \n'%(cnt, len(d), cmd_raw))
                self.execute_upd_cmd(cmd_raw, att_name=att_name, req_o=req_o, req_str=req_str)

        logger.debug('finished %i upd_cmds (%i remain: %s)'%(cnt,len(self.upd_cmd_od),  list(self.upd_cmd_od.keys())))
        
        
        #=======================================================================
        # recursive udpating
        #=======================================================================
        if not len(self.upd_cmd_od) == 0: 
            pass
            #logger.debug('some items remain in the upd_cmd_od: %s'%self.upd_cmd_od.keys())
        else:
            try:
                del self.session.update_upd_que_d[self.gid] #try and remove yourself from teh update que
                logger.debug('upd_cmd_od empty. removed myself from the update_upd_que_d')
            except:
                pass
            
        
        #=======================================================================
        # post checking
        #=======================================================================
        if self.db_f: 
            #the updates dict should have been cleared
            if not len(self.upd_cmd_od) == 0: 
                if not self.gid in list(self.session.update_upd_que_d.keys()): 
                    raise IOError
          
        """I dont want to clear this.. what if children requeud on me?  
        self.halt_updates(req_o = self)"""
        
        if cnt > 0: 
            return True
        else: 
            return False

    
    def halt_update(self): #force an update halt on me
        logger = self.logger.getChild('halt_update')
        self.upd_cmd_od = OrderedDict() #empty the dictionary
        try:
            self.session.update_upd_que(self, method='delete')
        except: pass
        logger.debug('cleared my upd_cmd_od and removed myself from the que \n')
        
        if self.db_f:
            if is_dated(self, '*any'): raise IOError
        
        
    def execute_upd_cmd(self, #execute the passed command on yourself
                cmd_str, #command to execute
                **ref_kwargs):  #reference kwargs (for display only)
        
        """
        broke this out so we can run individual update commands
        """
        logger = self.logger.getChild('execute_upd_cmd')
        

        #=======================================================================
        # pre checks
        #=======================================================================
        if self.db_f:
            cn = self.__class__.__name__
            if '(' in cmd_str or ')' in cmd_str:
                raise Error('got unrecognized charagerts in cmd_str: %s'%cmd_str)
            
            if not hasattr(self, cmd_str):
                raise Error('obj %s does not have an attribute %s'%(cn, cmd_str))
            
            if not callable(getattr(self, cmd_str)):
                raise Error('requested method \'%s.%s\' is not callable'%(cn, cmd_str))


        #=======================================================================
        # execute update
        #=======================================================================
        logger.debug('executing  cmd_str \'%s\' with kwargs: \n    %s'
                     %(cmd_str, ref_kwargs))
        
        
        func = getattr(self, cmd_str) #get the method
        result = func() #execute the method
        
        #=======================================================================
        # clean out the que
        #=======================================================================
        if result:
            self.del_upd_cmd(cmd_str = cmd_str, logger=logger)
        
        else:
            logger.debug('%s.%s returned false. leaving qued'%(self.__class__.__name__, cmd_str))

                
                
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if result is None:
                raise IOError
            if not result:
                que_check(self)
            
        return
    
    def mypost_update(self): #esecute post updater functions
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        init_dyno()    #first call before setting the OG values
        session.post_update() #called at the end of all the update loops
        
        """
        if self.post_upd_func_s is None: 
            return False
        logger = self.logger.getChild('mypost_update')
        for func in self.post_upd_func_s:
            logger.debug('executing \'%s\''%(func))
            func() #execute the fu nction
            
        return True

        
    def dyn_kid_check(self, kids_nd):
        
        logger = self.logger.getChild('dyn_kid_check')
        
        kid1 = list(kids_nd.values())[0] #first kid
        #logger.debug('on %i kids with cn \'%s\''%(len(kids_nd), kid1.__class__.__name__))
    
                #unique kid check
        l = []
        for name, obj in kids_nd.items():
            cn = obj.__class__.__name__
            
            if not cn in l: l.append(cn)
            
            """ not using this any more
            #check for unique run_upd_f
            if not hasattr(obj, 'run_upd_f'):
                logger.error('passed kid type \'%s\' is not a sim obj'%cn)
                raise IOError
            
            if not obj.run_upd_f == kid1.run_upd_f:
                logger.error('got non-unique run_upd_f on \'%s\''%obj.name)
                raise IOError"""
            
        if len(l) > 1:
            logger.error('got multiple kid types in passed kids_nd: %s'%l)
            raise IOError
        
        #logger.debug('cleared all')
        return
        
    def is_frozen(self, att_name, logger=None): #check if this attribute is frozen. with printouts
        """
        #=======================================================================
        # CALLS
        #=======================================================================
        custom calls should check at the beginning:
            if self.is_frozen('anchor_el', logger = logger): return
        
        dynp calls a similar function during apply_to_set()
        """
        if logger is None: logger = self.logger
        logger = logger.getChild('is_frozen')
        
        if att_name in list(self.fzn_an_d.keys()):
                        
            req_o, req_str = self.fzn_an_d[att_name]
            
            logger.debug('attribute \'%s\' was frozen by \'%s.%s\''%(att_name, req_o.name, req_str))
            
            if self.db_f:
                if self.session.state == 'init': raise IOError
            
            return True
        else: 
            #logger.debug('\'%s\' not frozen'%att_name)
            return False
        
    
        
    def deps_is_dated(self,
                      dep_l, #list of [(dependency container, commands to search for)]
                      method = 'reque', #what to do if your dependencies are outdated
                      caller = None): #caller function
        
        """
        #=======================================================================
        # INPUTS
        #=======================================================================
        dep_l: 
            this canot be a dictionary because we are keyeing (first entry) but a group of objects sometimes
        """
        
        if self.session.state == 'init': return False
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('deps_is_dated')
        if caller is None: 
            caller = inspect.stack()[1][3]
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if not isinstance(dep_l, list): 
                raise IOError
            
            #check contents
            for dep_container, cmd_l in dep_l:
                #tyep chekc
                for obj in [dep_container, cmd_l]:
                    if not (isinstance(obj, list) or isinstance(obj, tuple)): 
                        raise Error('unexpected type')
                    
                for obj in dep_container:
                    if not hasattr(obj, '__class__'):
                        raise Error('%s tried to check an unrecognize object type: %s'
                                      %(self.name, type(obj)))
                                      
                
                for cmd in cmd_l:
                    if not isinstance(cmd, str):
                        raise IOError
                    
                    if ')' in cmd or '(' in cmd:
                        raise Error('got unrecognized charachters in command str: %s'%cmd)


        
        logger.debug('\'%s\' is looking on %i dependency pairs: \n    %s'%(caller, len(dep_l), dep_l))
        
        #=======================================================================
        # container cmd_l pairing
        #=======================================================================
        for dep_container, cmd_l in dep_l:
            #===================================================================
            # check each dependent provided
            #===================================================================
            for depend in dep_container:
                #===================================================================
                # check each command provided
                #===================================================================\
                for cmd in cmd_l:           
                    #===========================================================
                    # handle dated commands     
                    #===========================================================
                    if is_dated(depend, cmd):
                        
                        #=======================================================
                        # prechecks
                        #=======================================================
                        if self.db_f:
                            que_check(depend)
                            
                        logger.debug('FOUND \'%s\' queued for \'%s\''%(cmd, depend.gid))
                        #===============================================================
                        # reque the caller
                        #===============================================================
                        if method == 'reque':                            
                            logger.debug('re-queing caller \'%s\' in my upd_cmd_od'%caller)
                            self.que_upd_skinny(caller, 'na', self, caller)  
                            return True
                        
                        elif method == 'pass':
                            logger.debug('dependency \'%s\' is outdated... but we are just passing'%depend.gid)
                            return True
                            
                        elif method == 'halt':
                            logger.debug("passed halt=TRUE. clearing the upd_cmd_od") 
                            self.upd_cmd_od = OrderedDict() #empty the dictionary 
                            return True
                            
                        elif method == 'force':
                            logger.debug('forcing update on depdendnt')
                            depend.update()
                            continue
                            
                        elif method == 'cascade':
                            raise Error('I dont think were using this')
                            self.session.update_all()
                            return False
                            
                        else: raise IOError
                    #end command loop. this command is not dated
                #end dependency loop
                
            else:
                pass 
                #logger.debug('no \'%s\' queud for \'%s\''%(cmd, depend.gid))
            
        logger.debug('all passed dependency pairs (%i) up to date'%len(dep_l))
        return False
                    

    def depend_outdated(self,  #handle outdated dependencies
                        depend = None, #dependency to check
                        search_key_l = None, #list of keys to search for (of update commands)
                        halt=False, #whether to clean out my own update commands
                        reque = True, #whether to re-que the caller
                        force_upd = False,  #flag to force an update on the depdende
                        caller = None):  
        """
        looks like we only used this once.
        consider deps_is_dated() instead
        """
        #=======================================================================
        # shortcuts
        #=======================================================================
        if self.session.state == 'init': return False
        
        #=======================================================================
        # defaults
        #=======================================================================
        if depend is None: depend = self.parent
        
        logger = self.logger.getChild('depend_outdated')
        outdated = False
        
        if self.db_f:
            if not search_key_l is None:
                if not isinstance(search_key_l, list): raise IOError
        #=======================================================================
        #prove it out dated
        #=======================================================================
        if len(depend.upd_cmd_od) >0:
            if not search_key_l is None: #some commands with a subset provided
                 
                for k in search_key_l:
                    if k in list(depend.upd_cmd_od.keys()):
                        outdated = True
                        break #stop the loop
            else:
                outdated = True #some commands with no subset provided
        
        
        #=======================================================================
        # handle the outdated dependent
        #=======================================================================
        if outdated:
            logger.debug('depdendnet \"%s\' is outdated with %i upd_cmds: %s'
                         %(depend.name,  len(depend.upd_cmd_od), list(depend.upd_cmd_od.keys())))
            
            #===================================================================
            # reque the caller
            #===================================================================
            if reque: #add this command back intot he que
                'TODO: see execute_upd_cmd(). consider returning flags rather tahn delete/add cycles '
                if caller is None: caller = inspect.stack()[1][3]
                logger.debug('re-queing caller \'%s\' in my upd_cmd_od'%caller)
                
                self.que_upd_skinny(caller, 'na', self, caller)
                
                """NO! need to handle yourself in the que as well
                'just placing a direct entry'           
                self.upd_cmd_od[caller+'()'] = ['na', weakref.proxy(self), caller]"""

                
            
            #===================================================================
            # #halt overrid
            #===================================================================
            if halt:
                logger.debug("passed halt=TRUE. clearing the upd_cmd_od") 
                self.upd_cmd_od = OrderedDict() #empty the dictionary 
                
            #===================================================================
            # forced udpate
            #===================================================================
            if force_upd:
                logger.debug("passed force_Upd =TRUE. forcing update on depdendnt \'%s\' \n"%depend)
                depend.update()
                
            #===================================================================
            # checks
            #===================================================================
            if self.db_f:
                if self.session.state == 'init': raise IOError
                if reque:
                    if not self.gid in list(self.session.update_upd_que_d.keys()): 
                        logger.error('\n I was instructed to reque if my depend \'%s\' is out of date, but Im not in the update_upd_que_d'
                                     %depend.gid)
                        raise IOError
                if not force_upd:
                    if not depend.gid in list(self.session.update_upd_que_d.keys()): raise IOError
                #if not 'build_dfunc()' in self.upd_cmd_od.keys(): raise IOError
            
            """better to use the recursive update que
            just let the que keep looping until the depend is fully updated
            
            logger.debug('forcing update on depend \'%s\''%depend.name)
            depend.update()
            logger.debug('finished updating depend \n')
            depend.upd_cmd_od.keys()
            
            """
        
        return outdated

class Dyno_controller(object): #wrapper for controlling dynamic objects
    
    #===========================================================================
    # calcluated pars
    #===========================================================================
    update_upd_que_d = None    #container for objects needing updating
    upd_iter_cnt = 0
    
    post_updaters_wd = wdict()      #container of gids that received updates
    
    def __init__(self, *vars, **kwargs):
        logger = mod_logger.getChild('Dyno_controller') #have to use this as our own logger hasnt loaded yet
        logger.debug('start __init__ as \'%s\''%self.__class__.__name__)
        super(Dyno_controller, self).__init__(*vars, **kwargs) 
        
        self.update_upd_que_d = OrderedDict() #container for objects needing updating
        
        #=======================================================================
        # resetting
        #=======================================================================
        """ dont need these for the session
        self.reset_d.update({'update_upd_que_d':OrderedDict(), 'upd_iter_cnt':0})"""
        
        logger.debug('finished _init_ \n')
        return
    
    def update_all(self, loc='?'): #update all objects in the queue
        """
        old_state = self.state
        self.state = '%s.update'%old_state"""

        start = time.time()
        #=======================================================================
        # shortcuts
        #=======================================================================
        if len(self.update_upd_que_d) == 0: return
        #=======================================================================
        # defaults
        #=======================================================================
        logger = self.logger.getChild('update_all')
        
        logger.info("\n uauauauauauauauauauauauauauauauauauauauauauauauauauauauauauauauuauauauauauauauauauauauauauauauauauauauau")
        logger.info('at \'%s\' with %i objects in que'%(loc, len(self.update_upd_que_d )))
        
        self.update_iter()
        
        """using static wd
        if len(self.post_updaters_wd) > 0:
            'we often dont update any objects with post update commands'"""
            
        """moved this to get_res_tstep()
            then we are only calling it after model changes, but before running the outputrs
        logger.debug("executing post_update()")
        self.post_update()"""
        
        #=======================================================================
        # wrap up
        #=======================================================================
        stop = time.time()
        logger.info('finished in %.4f secs with %i scans'%(stop - start, self.upd_iter_cnt))
        logger.debug('\n')
        
        self.upd_iter_cnt = 0 #reset this
        """
        self.state = old_state #return the state"""
        
        #=======================================================================
        # post checks
        #=======================================================================
        if self.db_f:
            if len(self.update_upd_que_d) > 0: raise IOError
        

        return
        
    def update_iter(self): # a single update iteration
            
        logger = self.logger.getChild('update_iter')
        self.upd_iter_cnt +=1
        this_cnt = int(self.upd_iter_cnt)
        #logger.info('upd_iter_cnt: %i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i%i')
        logger.debug('for upd_iter_cnt %i executing on %i objects in que \n'
                     %(self.upd_iter_cnt, len(self.update_upd_que_d)))
        
        
        
        d_copy = copy.copy(OrderedDict(sorted(list(self.update_upd_que_d.items()), key=lambda t: t[0])))
        """setting a sorted copy here 
            so no changes made druing the update commands affect the original que
            this update top down (low branch_level -> high) to the lowest"""
        
        #if self.db_f:
        if self.upd_iter_cnt > 10: 
            logger.error('stuck in a loop with %i objs queued \n %s'%(len(d_copy), list(d_copy.keys())))
            
            raise IOError
        #=======================================================================
        # loop and update
        #=======================================================================
        cnt = 0
        for k, obj in d_copy.items():
            cnt+=1
            if cnt%self.session._logstep == 0: logger.info('    (%i/%i)'%(cnt, len(d_copy)))
            
            if not obj.gid in list(self.update_upd_que_d.keys()):
                'some siblings can pull each other out of the que'
                logger.debug('\'%s\' has been removed from teh que. skipping'%obj.gid)
                continue
            
            logger.debug('updating \'%s\''%(k))
            
            _ = obj.update()
            """using a static update_wd
            if obj.update():
                if not obj.post_upd_func_s is None: #only que those objects with post funcs
                    self.post_updaters_wd[obj.gid] = obj #append this gid to the list of objects updated"""
            
            
            """ objects update() should do this
            del self.update_upd_que_d[k] #remove this from teh que"""
            
        logger.debug('finished iteration on %i objects \n'%cnt)
        
        if len(self.update_upd_que_d) > 0:
            logger.info('after scan %i, %i remain in que (vs original %i). repeating'
                         %(self.upd_iter_cnt, len(self.update_upd_que_d), len(d_copy)))
            self.update_iter()
            
            logger.debug('closing loop %i'%(this_cnt +1))
            
        else:
            logger.debug('update_upd_que_d emptied after %i iters'%self.upd_iter_cnt)
            
        return
    
    def post_update(self): #run through all updated objects and execute any post/stats commands
        """
        only statistic commands should be executed here
            those that only outputers rely on... do not influence the simulation model
        
        these are excueted on all those objects with receved update() = TRUE during the update iteration
        
        
        
        #=======================================================================
        # PURPOSE
        #=======================================================================
        This allows for only a subset of objects to run some post stats calc functions
            where objects can add/remove themselves to this que based on their own properties
        
        Allows for stats to be calcualted on objects NOT in run loops
        
        #=======================================================================
        # Calls
        #=======================================================================
        Tstep.run_dt()
            Tstep.get_res_tstep() #during wrap up
        
        """
        logger = self.logger.getChild('post_update')
        
        """objects are added to this during __init_dyno_ if they have any post_upd_func_s"""
        d = self.post_updaters_wd
        
        #=======================================================================
        # prechecks
        #=======================================================================
        if self.db_f:
            if len(d) == 0:
                raise IOError
            
        #=======================================================================
        # loop and update all the objects
        #=======================================================================
        logger.debug('executing on %i objects in the post_updaters_wd \n'%len(d))
        for gid, obj in d.items(): 
            if not obj.mypost_update(): raise IOError

                
        #=======================================================================
        # wrap up
        #=======================================================================
        logger.debug('finished \n')
        
        """letting this carry over
        self.post_updaters_wd = wdict() #clear this"""
        
        return
        """
        d.keys()
        """
        
        
    def update_upd_que(self, obj, method='add'): #add the object to the que
        """ should be able to update dictionary directly
        """
        logger = self.logger.getChild('update_upd_que')
        #=======================================================================
        # addition to the library
        #=======================================================================
        if method == 'add':
            self.update_upd_que_d[obj.gid] = weakref.proxy(obj)
            logger.debug('added \'%s\' to the \'update_upd_que_d\' (%i)'%(obj.gid, len(self.update_upd_que_d)))
            
        #=======================================================================
        # deletions from the library
        #=======================================================================
        elif not obj.gid in  self.update_upd_que_d: 
            return #nothing to do here
        
        elif method == 'delete':
            del self.update_upd_que_d[obj.gid]
            logger.debug('deleted \'%s\' from the \'update_upd_que_d\' (%i)'%(obj.gid, len(self.update_upd_que_d)))
                
        else: 
            raise IOError
        
        return
                     
                     
def is_dated(obj, cmd):
        """
        match = hp_basic.list_search(obj.upd_cmd_d.keys(), cmd)"""
        #=======================================================================
        # any updates
        #=======================================================================
        if cmd == '*any':
            if len(obj.upd_cmd_od) > 0: return True
            
        #=======================================================================
        # specific updates
        #=======================================================================
        for e in list(obj.upd_cmd_od.keys()):
            if re.search(cmd, e, re.IGNORECASE):                
                return True
            
        return False
        
def que_check(obj, logger = mod_logger): #raise errors if this object is not properly queued
    if not len(obj.upd_cmd_od) >0:
        logger = logger.getChild('que_check') 
        logger.error('\'%s\' doesnt have any commands queud on itself'%obj.gid)
        raise IOError
    
    if not obj.gid in list(obj.session.update_upd_que_d.keys()): 
        logger = logger.getChild('que_check') 
        logger.error('\'%s\' is not in the update que'%obj.gid)
        raise IOError
    
    
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        
        