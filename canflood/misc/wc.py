'''
Created on Dec. 5, 2020

@author: cefect

web connections
'''


#==============================================================================
# imports---------------------------
#==============================================================================
#python standards
import os, logging, copy

from configparser import ConfigParser, RawConfigParser
import numpy as np


from qgis.core import QgsApplication, QgsSettings
from PyQt5.QtCore import QSettings
#==============================================================================
# custom imports
#==============================================================================


from hlpr.exceptions import QError as Error


#from hlpr.Q import *
from hlpr.basic import ComWrkr

from hlpr.plug import logger as plogger


class WebConnect(ComWrkr):
    """
    constructed by CanFlood.py from the drop-down menu button
        not sure if this is setup to run standalone any more
    """
    allGroups = None
    
    def __init__(self,
                 iface=None,
                 newSettings_fp = None,
                 qini_fp = None, #path to user's QGIS.ini file
                 
                 **kwargs):
        
        self.iface=iface
        
        
        
        
        super().__init__(logger=plogger(self), **kwargs) #initilzie teh baseclass
        
        #setup
        
        #=======================================================================
        # get the users settings file
        #=======================================================================
        #qini_fp = os.path.abspath(__file__)[:-59]+"QGIS\QGIS3.ini" # The path to the configuration file for QGIS
        if qini_fp is None:
            qini_fp = os.path.join(QgsApplication.qgisSettingsDirPath(), r'QGIS\QGIS3.ini')
            
        assert os.path.exists(qini_fp), 'bad qini_fp: %s'%qini_fp
        self.qini_fp = qini_fp
        
        self.logger.info('found config file: %s'%qini_fp)
        
        #=======================================================================
        # load CanFlood's parameters info file
        #=======================================================================
        #get filepath
        if newSettings_fp is None:
            dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            newSettings_fp = os.path.join(dirname, '_pars','WebConnections.ini')
        
        self.newCons_d = self.retrieve_fromFile(newSettings_fp)
        
        
    def retrieve_fromFile(self, #pull parameters from CanFlood's file
                          con_fp,
                          expected_keys = ['group', 'url'], #keys expected under each group
                          ):
        
        log = self.logger.getChild('retrieve_fromFile')
        assert os.path.exists(con_fp)
        
        log.info('reading connection info fron \n    %s'%con_fp)
        pars = ConfigParser(allow_no_value=True)
        pars.optionxform=str
        _ = pars.read(con_fp) #read it from the new location

        #=======================================================================
        # loop through each seciton and load
        #=======================================================================
        log.debug('got %i sections'%len(pars.sections()))
        newCons_d = dict()
        for name, sect_d in pars.items():
            if  'DEFAULT' in name: continue #skip the default section
            newCons_d[name] = dict(sect_d)
            
            miss_l = set(expected_keys).difference(newCons_d[name].keys())
            assert len(miss_l) == 0, 'parameter file missing some keys: %s'%miss_l
            


    
        log.info('retrieved %i connection parameters from file \n    %s'%(len(newCons_d), list(newCons_d.keys())))
        
        return newCons_d
    
    
    def addAll(self, #add all connections
               qini_fp = None, #users settings path
               newCons_d = None, #connections to load
               ): 
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('addAll')
        if newCons_d is None: newCons_d = self.newCons_d
        if qini_fp is None: qini_fp = self.qini_fp
        
        log.debug('addAll on %i'%len(newCons_d))
        
        #=======================================================================
        # initilize settings
        #=======================================================================
        assert os.path.exists(qini_fp), 'bad settings filepath: %s'%qini_fp
        usets = QgsSettings(qini_fp, QSettings.IniFormat) 
        
        #navigate to group1
        """all connectins are in the qgis group"""
        usets.beginGroup('qgis') 
        
        #=======================================================================
        # loop and add each connection
        #=======================================================================
        for cname, newPars_d in copy.copy(newCons_d).items():
            #navigate to this group within the settings
            usets.beginGroup(newPars_d['group'])
            
            """TODO: add checks:
            warn if this group already exists
            check if connection is valid
            """
            
            log.debug('setting %i parameters to group \"%s\' \n    %s'%(
                len(newPars_d), usets.group(), newPars_d))
            #loop and add each setting to this group
            for k, v in newPars_d.items():
                if k=='group': continue 
                usets.setValue(k, v)
                
            #return to the parent group
            usets.endGroup()


        usets.sync() #write unsaved changes to file
        
        log.info('added %i connections: \n    %s'%( len(newCons_d), list(newCons_d.keys())))
        #=======================================================================
        # check result
        #=======================================================================
        result, chk_d = self.checkSettingsGroup(newCons_d, logger=log)
        assert result, 'failed to set some values \n    %s'%chk_d
                
                
        
            
        return newCons_d
    
    
    def checkSettingsGroup(self, #check a group of settings
                           cons_d,
                           qini_fp = None,
                           logger=None,
                           parent_group = 'qgis',
                           ):
        """there's probably some builtin functions for this"""
        
        #=======================================================================
        # defaults
        #=======================================================================
        if qini_fp is None: qini_fp = self.qini_fp
        if logger is None: logger = self.logger
        log = logger.getChild('checkSettingsGroup')
        
        #=======================================================================
        # init the settings
        #=======================================================================
        """would be nice to not re-init each time.. but not sure how to reset the group cleanly
        """
        assert os.path.exists(qini_fp), 'bad settings filepath: %s'%qini_fp
        usets = QgsSettings(qini_fp, QSettings.IniFormat) 
        #usets.beginGroup(parent_group) #all checks are done within the 1qgis group

        allGroups = self.getAllGroups(usets)
        log.debug('found %i groups'%len(allGroups))
            
        #=======================================================================
        # loop and check
        #=======================================================================
        log.debug('checking %i connectin settings in fp: \n    %s'%(len(cons_d), qini_fp))
        res_d = dict() #macro results contqainer
        for cname, newPars_d in cons_d.items():
            res_d1 = dict()
            group = '/qgis/%s'%newPars_d['group'].replace('\\', '/') #group to check
            for k, v in newPars_d.items():
                if k=='group': continue 
                result, msg = self.checkSettings(group, k, v, usets, allGroups)
                log.debug('\"%s\' %s =%s'%(group,result, msg))
                res_d1[k] = result #add result
                
            usets.endGroup() #revert group
            
            #===================================================================
            # #report
            #===================================================================
            ar = np.array(list(res_d1.values()))
            log.debug('group=\'%s\' %i (of %i) settings match'%(group, ar.sum(), len(ar)))

            
            res_d[cname] = ar.all()
            
        return np.array(list(res_d.values())).all(), res_d
    
    def getAllGroups(self, usets):
        """couldnt find a nice builtin for this
        
        pulls all groups on the QgsSettings"""
        assert isinstance(usets, QgsSettings)
        
        l = list()
        for k in usets.allKeys():
            k_all = k.split(r'/') #split all the entries
            if len(k_all)>1:
                l.append('/'.join(k_all[:-1]))
            else:
                l.append(k_all[0])
                
        #add the leading slash
        l = ['/'+e for e in l]
        
        return l
        
    
    def checkSettings(self,
                      group,
                      key,
                      value,
                      usets,
                      allGroups
                      ):
        


                
        
        #=======================================================================
        # run checks
        #=======================================================================
        result, msg = True, 'match'
        

        
        
        #see if the group exists
        if not group in allGroups:
            msg = 'group \'%s\' does not exist'%group
            result = False
        
        #=======================================================================
        # see if the key exists
        #=======================================================================
        if result:
            #move to the group
            usets.beginGroup(group)
            assert usets.group() in group
            
            if not key in usets.childKeys():
                msg='group \"%s\' does not have key \'%s\''%(group, key)
                result = False
            else:
                #===============================================================
                # see if the value matches
                #===============================================================
                if not value == usets.value(key):
                    msg = '%s.%s=%s does not match \'%s\''%(
                        group, key, usets.value(key), value)
                    result = False
                
            #revert gruop
            usets.endGroup()
            
        
        return result, msg
            

    

        
    
        
if __name__ =="__main__":
    
    
    wrkr = WebConnect(
        newSettings_fp = r'C:\LS\03_TOOLS\CanFlood\_git\canflood\_pars\WebConnections1.ini',
        qini_fp = r'C:\Users\cefect\AppData\Roaming\QGIS\QGIS3\profiles\dev\QGIS\QGIS3.ini') #setup worker
    
    
    wrkr.addAll() #add everything
    
        