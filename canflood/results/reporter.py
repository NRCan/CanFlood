'''
Created on Feb. 11, 2022

@author: cefect

generating report template
'''
#==============================================================================
# imports------------
#==============================================================================
import logging, configparser, datetime, copy, shutil


import os
import numpy as np
import pandas as pd

#Q imports
from PyQt5.QtXml import QDomDocument
from qgis.core import QgsPrintLayout, QgsReadWriteContext, QgsLayoutItemHtml, QgsLayoutFrame
 
 
from PyQt5.QtCore import QRectF, QUrl

#===============================================================================
# customs
#===============================================================================
from hlpr.exceptions import QError as Error
from hlpr.basic import view
from hlpr.Q import Qcoms
 
from results.riskPlot import RiskPlotr


#==============================================================================
# functions-------------------
#==============================================================================
class ReportGenerator(RiskPlotr, Qcoms):
 
 
    #===========================================================================
    # expectations from parameter file
    #===========================================================================
    exp_pars_md = {
        'results_fps':{
             'r_ttl':{'ext':('.csv',)},
             }
        }
    
    exp_pars_op={
 
        }
    
    def __init__(self,
                figsize=(10,6),
                 **kwargs):
        
        super().__init__(figsize=figsize, **kwargs)
        
        self.dtag_d={**self.dtag_d,**{
            'r_ttl':{'index_col':None}}}
        
        #=======================================================================
        # paramters directory
        #=======================================================================
        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars', 'results', 'reporter')
        
        #=======================================================================
        # get the temlpate files
        #=======================================================================
        
        self.qrpt_template_fp = os.path.join(self.pars_dir,  'CanFlood_report_template_01.qpt')

        assert os.path.exists(self.qrpt_template_fp), 'passed template_fp is bad: \'%s\''%self.qrpt_template_fp
        
        
        #self.html_template_fp = os.path.join(self.pars_dir,  'template_01.html')
        #assert os.path.exists(self.html_template_fp)
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
    def prep_model(self):

        
        self.set_ttl() #load and prep the total results

        
        return 
   
    def build_html(self): #buildt he HTML report
        
        #add some info to the html template
        
        #write the html file
        
        
        return r'C:\LS\09_REPOS\03_TOOLS\CanFlood\_git\canflood\_pars\results\reporter\template_01.html'
    
    
    def load_qtemplate(self, #load the layout template onto the project
                       template_fp=None,
                       name=None,
                       logger=None,
                       ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if name is None: name='CanFlood_report_%s'%self.resname
        if logger is None: logger=self.logger
        log=logger.getChild('load_qtemplate')
        if template_fp is None: template_fp = self.qrpt_template_fp
        
        
        assert os.path.exists(template_fp)
        #=======================================================================
        # load the layout template
        #=======================================================================
        #load the template
        with open(template_fp) as f:
            template_content = f.read()
            doc = QDomDocument()
            doc.setContent(template_content)
        
         
        #build a normal layout
        qlayout = QgsPrintLayout(self.qproj)
        
        #load the template 
        qlayout.loadFromTemplate(doc, QgsReadWriteContext(), True)
        

        #rename
        qlayout.setName(name)

        
        log.debug('loaded layout from template file: %s'%template_fp)
        
        
        return qlayout
    
    def add_html(self, #add content from an html file
                 qlayout=None,
                  html_fp = None,
                      
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        
        
        log = self.logger.getChild('add_html')
        
        log.info('from %s'%html_fp)
        assert os.path.exists(html_fp)
 
        #=======================================================================
        # #build the layouts 
        #=======================================================================
 
        layItem_html = QgsLayoutItemHtml(qlayout)
        
        #=======================================================================
        # #add the frame
        #=======================================================================
        html_frame = QgsLayoutFrame(qlayout, layItem_html)
        html_frame.attemptSetSceneRect(QRectF(0, 40, 209.500, 256.750))
        html_frame.setFrameEnabled(True)
        layItem_html.addFrame(html_frame)
         
        
        #=======================================================================
        # #populate layout
        #=======================================================================
        #layItem_html.setContentMode(QgsLayoutItemHtml.ManualHtml)
        #layItem_html.setHtml('test<br><b>test</b>')
        
        
        url = QUrl("file:///" + html_fp)
        layItem_html.setUrl(url)
        layItem_html.loadHtml()
        
        layItem_html.loadHtml()

 
        
        log.info('finished')
        
    def __exit__(self, #destructor
                 *args,**kwargs):
        pass
    
        
        
        
        
        
        
        
        
        
        
        
        