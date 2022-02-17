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
from qgis.core import QgsPrintLayout, QgsReadWriteContext, QgsLayoutItemHtml, QgsLayoutFrame, \
    QgsLayoutItemMap, QgsVectorLayer, QgsLayoutMultiFrame, QgsLayoutItemPicture, \
    QgsReport, QgsLayout, QgsReportSectionLayout, QgsLayoutItemPage, QgsLayoutItemLabel, \
    QgsTextFormat
 

from PyQt5.QtCore import QRectF, QUrl
from PyQt5 import QtGui

#.QtGui import QFont

#===============================================================================
# customs
#===============================================================================
from hlpr.exceptions import QError as Error
from hlpr.basic import view
 
from hlpr.Q import Qcoms 
 
from results.riskPlot import RiskPlotr
#from model.modcom import Model


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
        
        super().__init__(figsize=figsize, name='report', **kwargs)
        
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
   
    def build_html(self,
                   ofp = None,
                   cf_fp = None, #control fle path
                   svg_fp_d = dict(), #svg filepaths to add to end of html
                   ): #buildt he HTML report
        
        #=======================================================================
        # defaults
        #=======================================================================
        if ofp is None: ofp = os.path.join(self.out_dir, 'report_%s.html'%self.resname)
        if cf_fp is None: cf_fp = self.cf_fp
        log = self.logger.getChild('build_html')
        
        if os.path.exists(ofp):
            os.remove(ofp)

        with open(ofp, "w") as html:
            #=======================================================================
            # #add the control file to the html
            #=======================================================================
        
            with open(cf_fp,"r") as file:
                lines = file.readlines()
                log.info('building report from controlFile w/  %i lines'%len(lines))
 
                for line in lines:
                    html.write(line + "<br>\n")
                    #e.write("<pre>" + line + "</pre> <br>\n")
                    
            #===================================================================
            # add the plots
            #===================================================================
            for name, svg_fp in svg_fp_d.items():
                raise Error('these are not read by QGIS... could try a different format? or just use the layouts native image item')
                assert os.path.exists(svg_fp)
                html.write("<br>\n" + '<object data="{fp}" type="image/svg+xml">\n'.format(fp=svg_fp) + "</object>\n<br>\n<br>\n<br>\n")
        
        #write the html file
        log.info('wrote to %s'%ofp)
        return ofp
        #return r'C:\LS\09_REPOS\03_TOOLS\CanFlood\_git\canflood\_pars\results\reporter\template_01.html'
    
    
    def load_qtemplate(self, #load the layout template onto the project
                       template_fp=None,
                       name=None,
                       logger=None,
                       ):
        
        raise Error('better to use QgsReport')
        #=======================================================================
        # defaults
        #=======================================================================
        if name is None: name='CanFlood_report_%s'%self.resname
        if logger is None: logger=self.logger
        log=logger.getChild('load_qtemplate')
        if template_fp is None: template_fp = self.qrpt_template_fp
        
        #=======================================================================
        # clear the old layout
        #=======================================================================
        layoutManager = self.qproj.layoutManager()
        old_layout = layoutManager.layoutByName(name)
        if not old_layout is None:
            layoutManager.removeLayout(old_layout)
        
        assert os.path.exists(template_fp)
        log.debug('loading from %s'%template_fp)
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
        
        self.layout = qlayout
        
        return qlayout
    
    def add_report(self,
                      
                       name=None,
                       logger=None,
                       ):
        
 
        #=======================================================================
        # defaults
        #=======================================================================
        if name is None: name='CanFlood_%s'%self.resname
        """
        self.name
        """
        if logger is None: logger=self.logger
        log=logger.getChild('add_report')
        
        qproj = self.qproj
        #=======================================================================
        # clear the old layout
        #=======================================================================
        layoutManager = self.qproj.layoutManager()
        old_layout = layoutManager.layoutByName(name)
        if not old_layout is None:
            layoutManager.removeLayout(old_layout)
        

        
        #=======================================================================
        # create the report
        #=======================================================================
        r = QgsReport(qproj)
        r.setName(name)
        
        
        #add to layout
        layoutManager.addLayout(r)
 
        
        log.debug('built report \'%s\''%name)
        
        self.report = r
        
        return r
    
    def add_header(self, #add header from template to the report
                   report=None,
                   template_fp=None,
                   ):
        #=======================================================================
        # defaults
        #=======================================================================
        if report is None: report=self.report
        qproj = self.qproj
        if template_fp is None: template_fp = self.qrpt_template_fp
        log=self.logger.getChild('add_header')
        
        assert os.path.exists(template_fp)
        log.debug('loading from %s'%template_fp)
        #=======================================================================
        # add header
        #=======================================================================
        report.setHeaderEnabled(True)
        report_header = QgsLayout(qproj)
        report_header.initializeDefaults()
        report.setHeader(report_header)
        #=======================================================================
        # load the layout template
        #=======================================================================
        #load the template
        with open(template_fp) as f:
            template_content = f.read()
            doc = QDomDocument()
            doc.setContent(template_content)
        
         
        report_header.loadFromTemplate(doc, QgsReadWriteContext(), True) #set the template 
        
        #=======================================================================
        # add some text
        #=======================================================================
        t = 'report generated on %s'%self.today_str
        self.add_label(qlayout=report_header, text=t,
                       qrect=QRectF(5, 55, 200, 50))
        
        
        log.debug('set header from template file: %s'%template_fp)
    
    def add_section(self, #add a section and layout to the report
                    report=None,
                    ):
        
        if report is None:
            report = self.report
        
        qproj = self.qproj
        
        
            
        sect=QgsReportSectionLayout(report)
        sect.setBodyEnabled(True) #turn the body on
        sect.setParentSection(report)
        report.appendChild(sect)
        
        #add a body to the section
        body = QgsPrintLayout(qproj)
        body.initializeDefaults() #add teh default page
        
        #change the page size
        page_collection = body.pageCollection()
        page1 = page_collection.pages()[0]
        page1.setPageSize('A4', QgsLayoutItemPage.Portrait)
        
        sect.setBody(body)
        
        return body
        
                   
    
    def add_map(self, #add a map to the results report
                report=None,
                qlayout=None,
                vlay=None,
                qrect = None,
                ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None: 
            qlayout = self.add_section(report=report)
            
        if qrect is None: qrect = QRectF(5, 5,200,280)
        log = self.logger.getChild('add_map')
            
        assert isinstance(vlay, QgsVectorLayer)
        
        #=======================================================================
        # #add map
        #=======================================================================
        layItem_map = QgsLayoutItemMap(qlayout)
         
        layItem_map.attemptSetSceneRect(qrect)
        layItem_map.setFrameEnabled(True)
        
        #add extent
 
        layItem_map.setExtent(vlay.extent())
        
        #setting twice seems to be required for the extens to work
        layItem_map.attemptSetSceneRect(qrect)
        
        qlayout.addLayoutItem(layItem_map)
        
        log.debug('added QgsLayoutItemMap')
        
        #=======================================================================
        # add the title
        #=======================================================================
        label = self.add_label(qlayout=qlayout, text='Results Map', text_size=20)
        #label.setFrameEnabled(True)
        

        
        return layItem_map
    
    def add_label(self,
                  qlayout=None,
                  text='text',
                  qrect=QRectF(5, 5, 200, 100),
                  text_size=8,
                  text_bold=True,
                  **kwargs):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None: 
            qlayout = self.add_section(**kwargs)
        
        label = QgsLayoutItemLabel(qlayout)
        label.attemptSetSceneRect(qrect)
        label.setText(text)
        
        #=======================================================================
        # format
        #=======================================================================

        #=======================================================================
        # t = QgsTextFormat()
        # if not text_format is None:
        #     t.setNamedStyle(text_format)
        # if not text_size is None:
        #     t.setSize(text_size)
        # label.setTextFormat(t)
        #=======================================================================
        font = QtGui.QFont()
        font.setPointSize(text_size)
        font.setBold(text_bold)
        label.setFont(font)
        
        
        qlayout.addLayoutItem(label)
        
        return label
    
    def add_html(self, #add content from an html file
                 qlayout=None,
                  html_fp = None,
                  report=None,
                      
                      ):
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None: 
            qlayout = self.add_section(report=report)
        
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
        html_frame.attemptSetSceneRect(QRectF(5, 5, 200, 256.750))
        html_frame.setFrameEnabled(True)
        layItem_html.addFrame(html_frame)
 
        #=======================================================================
        # #populate layout
        #=======================================================================
 
        url = QUrl("file:///" + html_fp)
        log.debug('setUrl from %s'%url)
        layItem_html.setUrl(url) #phantom crashing test mode
        layItem_html.loadHtml()
        # 
        # #change resize mode
        layItem_html.setResizeMode(QgsLayoutMultiFrame.ResizeMode.ExtendToNextPage)
        #=======================================================================

 
        
        log.info('added to %s'%qlayout.name())
        
        return layItem_html
 
            
    def add_picture(self, 
                    fp, #path to svg file to load
                    qlayout=None,
                    report=None,
                    ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None: 
            qlayout = self.add_section(report=report)
 
        log = self.logger.getChild('add_picture')
        
        assert os.path.exists(fp)
        
        layItem_pic = QgsLayoutItemPicture(qlayout)

        layItem_pic.attemptSetSceneRect(QRectF(5, 5,200,280))
        #layItem_pic.setFrameEnabled(True)
        layItem_pic.setPicturePath(fp)
         
        qlayout.addLayoutItem(layItem_pic)
        
        log.debug('added item from %s'%fp)
        
        return layItem_pic
        
        
        
        
        
        
        
        
        
        
        
        