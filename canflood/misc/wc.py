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


from qgis.core import QgsApplication
#==============================================================================
# custom imports
#==============================================================================

#standalone runs
if __name__ =="__main__": 
    from hlpr.logr import basic_logger
    mod_logger = basic_logger()   
    
    from hlpr.exceptions import Error
#plugin runs
else:
    #base_class = object
    from hlpr.exceptions import QError as Error


#from hlpr.Q import *
from hlpr.basic import ComWrkr

from hlpr.plug import logger as plogger


class WebConnect(ComWrkr):
    
    
    def __init__(self,
                 iface=None,
                 qini_fp = None, #path to user's QGIS.ini file
                 
                 **kwargs):
        
        self.iface=iface
        
        #Qgis run
        if iface is None:
            self.logger = mod_logger
            
        #Standalone run 
        else:
            self.logger= plogger(self)
        
        
        super().__init__(logger=self.logger, **kwargs) #initilzie teh baseclass
        
        #setup
        
        #qini_fp = os.path.abspath(__file__)[:-59]+"QGIS\QGIS3.ini" # The path to the configuration file for QGIS
        if qini_fp is None:
            qini_fp = os.path.join(QgsApplication.qgisSettingsDirPath(), r'QGIS\QGIS3.ini')
            
        assert os.path.exists(qini_fp), 'bad qini_fp: %s'%qini_fp
        self.qini_fp = qini_fp
        
        self.logger.info('found config file: %s'%qini_fp)
        
        #=======================================================================
        # load connection info file
        #=======================================================================
        #get filepath
        dirname = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        con_fp = os.path.join(dirname, '_pars','WebConnections.ini')
        
        self.serv_d = self.retrieve_fromFile(con_fp)
        
        
    def retrieve_fromFile(self,
                          con_fp):
        
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
        serv_d = dict()
        for name, sect_d in pars.items():
            if  'DEFAULT' in name: continue #skip the default section
            serv_d[name] = sect_d
            
            #check it
            for ele in ('serverType', 'url'):
                assert ele in sect_d.keys(), '%s missing \'%s\''%(name, ele)

    
        log.info('finished loading %i connections \n    %s'%(len(serv_d), list(serv_d.keys())))
        
        return serv_d
    
    
    def addAll(self, #add all connections
               serv_d = None, #connections to load
               ): 
        
        log = self.logger.getChild('addAll')
        if serv_d is None:
            serv_d = self.serv_d
        
        log.debug('addAll executed')
        
        
        #=======================================================================
        # serv_d =  {#title: {serverType, url}}
        #     'NRPI':('arcgisfeatureserver','https://maps-cartes.ec.gc.ca/arcgis/rest/services/NPRI_INRP/NPRI_INRP/MapServer')
        #     }
        #=======================================================================
        
        #=======================================================================
        # loop and add
        #=======================================================================
        res_d = dict() #results container
        for title, sect_d in serv_d.items():
            result = self.saveLayer(title, sect_d['url'], sect_d['serverType'])
            if not result:
                log.info('failed to add \'%s\''%title)
            else:
                log.info('added \'%s\''%title)
            res_d[title] = result

        
        cnt = np.array(list(res_d.values())).sum() #total the TRUEs
        
        log.info('added %i (of %i) connections'%(cnt, len(serv_d)))
            
        return cnt, serv_d
        
            
    
    def get_settings(self, serverType, title, url):
        
        """check out 'QGIS3.ini' for syntax
        
        seems like this could be written much cleaner....
        """
        
        if (serverType == "WMS"): 
            base_settings = "connections-wms\\"+title+"\\"
            base_security_settings = "WMS\\"+title+"\\"
            
            settings = [base_settings+"url",base_settings+"ignoreAxisOrientation",base_settings+"invertAxisOrientation",
                        base_settings+"ignoreGetMapURI",base_settings+"smoothPixmapTransform",base_settings+"dpimode",base_settings+"referer",
                        base_settings+"ignoreGetFeatureInfoURI",base_security_settings+"username",base_security_settings+"password",base_security_settings+"authcfg"]
            
            settings_ans = [url,"false","false","false","false","7","","false","","",""]
            
        elif (serverType == "WFS"):
            base_settings = "connections-wfs\\"+title+"\\"
            base_security_settings = "WFS\\"+title+"\\"
            settings = [base_settings+"url",base_settings+"ignoreAxisOrientation",base_settings+"invertAxisOrientation",
            base_settings+"version",base_settings+"maxnumfeatures",base_security_settings+"username",
            base_security_settings+"password",base_security_settings+"authcfg"]
            
            settings_ans = [url,"false","false","auto","","","",""]
        
        elif (serverType == "arcgismapserver"):
            base_settings = "connections-arcgismapserver\\"+title+"\\"
            base_security_settings = "arcgismapserver\\"+title+"\\"
            settings = [base_settings+"url",base_security_settings+"username",base_security_settings+"password",
            base_security_settings+"authcfg"]
            
            settings_ans = [url,"","",""]
            
        elif (serverType == "arcgisfeatureserver"):
            base_settings = "connections-arcgisfeatureserver\\"+title+"\\"
            base_security_settings = "arcgisfeatureserver\\"+title+"\\"
            settings = [base_settings+"url",base_security_settings+"username",base_security_settings+"password",
            base_security_settings+"authcfg"]
            
            settings_ans = [url,"","",""]
            
        elif (serverType=='WCS'):
            
            """using pythonic code here"""
            #===================================================================
            # #default parmaeters:settings
            #===================================================================
            
            
            conBase_d = { #ocnnections
                'url':'???',
                'ignoreAxisOrientation':'false',
                'invertAxisOrientation':'false',
                'ignoreReportedLayerExtents':'false',
                'ignoreGetMapURI':'false',
                'smoothPixmapTransform':'false',
                'dpiMode':'7',
                'referer':''}
                
            secBase_d = { #security settings 
                'username':'',
                'password':'',
                'authcfg':'',
                }
                
               
            #===================================================================
            # #populate
            #===================================================================
            
            #add passed parameters
            conBase_d['url'] = url
            
            

            
            
            #===================================================================
            # #add base values
            #===================================================================
            con_d, sec_d = copy.copy(conBase_d), copy.copy(secBase_d) #start with defaults
            base_settings = "connections-wcs\\"+title+"\\"
            base_security_settings = "WCS\\"+title+"\\"
            
            con_d = {base_settings+k:v for k,v in con_d.items()}
            sec_d = {base_security_settings+k:v for k,v in sec_d.items()}
            
  
            
            #===================================================================
            # revert
            #===================================================================
            """todo: restructure this whole class to be more pythonic"""
            settings = list(con_d.keys()) + list(sec_d.keys())
            settings_ans = list(con_d.values()) + list(sec_d.values())
                     
            
            
        else:
            raise Error('unrecognized serverType: %s'%serverType)
            
        return settings, settings_ans, base_settings
        
        
        
    def saveLayer(self, #add entry to the ini file
                   title,url,serverType):
        """taken from canadian_web_services
        
        is there an api method to do this?
        
        https://gis.stackexchange.com/questions/307325/how-to-open-and-add-sqlite-connection-to-browser-with-pyqgis
        
        
        """
        
        '''
        Standalone function that saves services into the registry 
        @param title - The title of the service
        @param url - the url of the service
        @param serverType - the serverType of service (ie WMS,WFS,ESRI MapServer)
        '''
        
        log = self.logger.getChild('saveLayer')
        
        log.debug('on %s'%title)
        filepath =  self.qini_fp
        #=======================================================================
        # open up the ini file
        #=======================================================================
        config = ConfigParser()
        config.optionxform =str
        _ = config.read(self.qini_fp)

        
        #=======================================================================
        # calculate the settings
        #=======================================================================
        settings, settings_ans, base_settings = self.get_settings(serverType, title, url)

            
        #=======================================================================
        # see if its been written
        #=======================================================================

        try: # try block checks if the service has been added
            """bad way to do this...."""
            check = config["qgis"][base_settings+"url"] # Checks if the service has already been added
            already_added = config["qgis"][base_settings+"url"] == url # checks to see if the urls match (Used since we might encounter services with the same name but different urls)
            
            
            
        except: # If it hasn't add it 
            for i in range (len(settings)):
                """loop through setting variables and set values"""
                config["qgis"][settings[i]] = settings_ans[i]

            
            with open(filepath,"w") as configfile:
                """
                some protocols were not loading when the spaces aroudn the equal signs were included
                """
                config.write(EqualsSpaceRemover(configfile))
                
            already_added = True
            
            log.info('added \'%s\' with type: \'%s\' and url: \n    %s'%(title, serverType, url))
            
            return True
            
            
        
        #=======================================================================
        # 
        # if not already_added: # If the service has still not been added (most common reason to be here is if there are multiple services with the same name (title))
        #     already_added,title = self.name_finder(title,config,serverType,url,0)
        #     if(not(already_added)): # If the service has not already been added 
        #         return False# Do nothing
        #     
        #     else: # Otherwise add it to the configuration file
        #         
        #         settings, settings_ans, base_settings = self.get_settings(serverType, title, url)
        #         
        #         for i in range (len(settings)): # Sets information into config
        #             config["qgis"][settings[i]] = settings_ans[i]
        #         
        #         with open(filepath,"w") as configfile: # writes into file 
        #             config.write(EqualsSpaceRemover(configfile))
        #             
        #         return True    
        # else:
        #     return False
        #=======================================================================
              

    
    
    def name_finder(self,
                        title,config,serverType,url,counter):
        
        '''
        Helper function for method saveLayers that obtains how we should name our service (Created to counter-act the fact that many services in the plugin have the same name)
        
        @param title - title of the service
        @param config - ConfigParser that contains a dictionary like structure that contains the configuration settings of QGIS
        @param serverType - the serverType of service (ie WMS, WFS, ESRI MapServer)
        @param counter - Amount of times we have run this helper function for the given service
        
        @return bool - that is false if a write is not necessary, and true if it is
        @return title - the new title we should be using when writing to the configuration settings file.  
        '''
        
        try:# Checks if the service exists
            counter += 1
            
            if (serverType == "WMS"): # If block checks what serverType of service we are given and does the appropriate url check
                check = config["qgis"]["connections-wms\\"+title+"\\url"] == url
            elif (serverType == "WFS"):
                check = config["qgis"]["connections-wfs\\"+title+"\\url"] == url
            elif (serverType == "arcgismapserver"):
                check = config["qgis"]["connections-arcgismapserver\\"+title+"\\url"] == url
            elif (serverType == "arcgisfeatureserver"):
                check = config["qgis"]["connections-arcgisfeatureserver\\"+title+"\\url"] == url
            elif serverType == 'WCS':
                check = config["qgis"]["connections-wcs\\"+title+"\\url"] == url
            else:
                raise Error('unrecognized serverType: %s'%serverType)
            
            if(check): # If we found the service 
                return False,title 
            else: # Otherwise 
            
                if (counter == 1): # If block that deals with naming conventions, if this is the first time we ran the function 
                    title += "_"+str(counter) 
                else: # For every subsequent run of the function, remove what was previously added, and then add the new version Ex: Given title_1, strips the 1 and add 2 leaving us with : title_2  
                    title = title[:-(len(str(counter - 1)))]
                    title += str(counter)
                return self.name_finder(title,config,serverType,url,counter)
        except: # If the service doesn't exist, that means we can now write to the configuration settings file without error
            return True,title 
        
class EqualsSpaceRemover:
    output_file = None
    def __init__( self, new_output_file ):
        self.output_file = new_output_file

    def write( self, what ):
        self.output_file.write( what.replace( " = ", "=", 1 ) )
        
if __name__ =="__main__":
    
    
    wrkr = WebConnect(
        qini_fp = r'C:\Users\cefect\AppData\Roaming\QGIS\QGIS3\profiles\dev\QGIS\QGIS3.ini') #setup worker
    
    
    wrkr.addAll() #add everything
    
        