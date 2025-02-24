'''
Created on Feb. 11, 2022

@author: cefect

generating report template
'''
#==============================================================================
# imports------------
#==============================================================================
import os
import numpy as np
import pandas as pd

#Q imports
from PyQt5.QtXml import QDomDocument
from qgis.core import (
    QgsPrintLayout, QgsReadWriteContext, QgsLayoutItemHtml, QgsLayoutFrame, 
    QgsLayoutItemMap, QgsVectorLayer, QgsLayoutMultiFrame, QgsLayoutItemPicture, 
    QgsReport, QgsLayout, QgsReportSectionLayout, QgsLayoutItemPage, QgsLayoutItemLabel, 
    QgsLayoutItemAttributeTable, QgsVectorLayer, QgsField, QgsFeature, QgsProject,
    QgsTextFormat,
    )
 

from PyQt5.QtCore import QRectF, QUrl, Qt, QVariant
from PyQt5.QtGui import QFont
from PyQt5 import QtGui


#===============================================================================
# customs
#===============================================================================
from canflood.hlpr.exceptions import QError as Error
from canflood.hlpr.basic import view
 
from canflood.hlpr.Q import Qcoms 
 
from canflood.results.riskPlot import RiskPlotr


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

    section_count = 1
    
    def __init__(self,
                figsize=(10,6),
                 **kwargs):
        
        super().__init__(figsize=figsize, name='report', **kwargs)
        
        self.dtag_d={**self.dtag_d,**{
            'r_ttl':{'index_col':None}}}
        
        #=======================================================================
        # parameters directory
        #=======================================================================
        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars', 'results', 'reporter')
        
        #=======================================================================
        # get the template files
        #=======================================================================
        
        self.qrpt_template_fp = os.path.join(self.pars_dir,  'CanFlood_report_template_01.qpt')

        assert os.path.exists(self.qrpt_template_fp), 'passed template_fp is bad: \'%s\''%self.qrpt_template_fp
        
        
        self.logger.debug('%s.__init__ w/ feedback \'%s\''%(
            self.__class__.__name__, type(self.feedback).__name__))
        
    def prep_model(self):
        self.set_ttl() #load and prep the total results

 
   
    def build_html(self,
                   ofp = None,
                   cf_fp = None, #control file path
 
                   ): #build the HTML report
        
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
            # add the control file to the html
            #=======================================================================
            with open(cf_fp,"r") as file:
                lines = file.readlines()
                log.debug('building report from controlFile w/  %i lines'%len(lines))
 
                for line in lines:
                    html.write(line + "<br>\n")
 
        #write the html file
        log.debug('wrote to %s'%ofp)
        return ofp
    
    def add_report(self,
                      
                       name=None,
                       logger=None,
                       ):
        """add a report to the project"""
        
 
        #=======================================================================
        # defaults
        #=======================================================================
        if name is None: name='CanFlood_%s'%self.resname
 
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
    
    def add_header(self, #
                   report=None,
                   template_fp=None,
                   ):
        """add header from template to the report"""
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

        #=======================================================================
        # add the page number
        #=======================================================================
        self.add_page_number(qlayout=report_header)     
        
        
        log.debug('set header from template file: %s'%template_fp)
    
    def add_section(self, #add a section and layout to the report
                    report=None,
                    tag=None,
                    
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
        body.initializeDefaults() #add the default page

        #add page number to section
        self.add_page_number(qlayout=body)

        #add page header to section
        self.add_page_header(qlayout=body, text='CanFlood Model Report: %s'%self.name)
                
        #change the page size
        page_collection = body.pageCollection()
        page1 = page_collection.pages()[0]
        page1.setPageSize('A4', QgsLayoutItemPage.Portrait)
        
        sect.setBody(body)
        
        #tag it (mainly for debugging)
        if not tag is None:
            sect.tag=tag
        
        return body

    def add_page_number(self, qlayout=None, qrect=QRectF(190, 290, 14, 4), **kwargs):
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None: 
            qlayout = self.add_section(**kwargs)

        #=======================================================================
        # add page number label
        #=======================================================================
        page_label = QgsLayoutItemLabel(qlayout)
        text = "Page " + str(self.section_count)

        #setting label styling options
        page_label.setText(text)
 
        page_label.setTextFormat(QgsTextFormat().fromQFont(QFont("Ms Shell Dlg 2", 10)))
        page_label.attemptSetSceneRect(qrect)

        #add page number label to body
        qlayout.addLayoutItem(page_label)

        #increment the section count
        self.section_count += 1

    def add_page_header(self, qlayout=None, qrect=QRectF(5, 5, 150, 10), 
                        text='CanFlood Model Report', **kwargs):
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None: 
            qlayout = self.add_section(**kwargs)

        #=======================================================================
        # add page header
        #=======================================================================
        label = self.add_label(qlayout=qlayout, text=text, text_size=22, 
                               qrect=qrect, text_bold=True)
 
        
    def add_map(self, #
                report=None,
                qlayout=None,
                vlay=None,
                qrect = None,
                ):
        """add a map to the results report"""
        #=======================================================================
        # defaults
        #=======================================================================
        if qrect is None: qrect = QRectF(5, 20, 200, 265)
        log = self.logger.getChild('add_map')
        
        
        if qlayout is None: 
            qlayout = self.add_section(report=report, tag='map')
 
        #=======================================================================
        # precheck
        #=======================================================================
        assert isinstance(vlay, QgsVectorLayer), type(QgsVectorLayer).__name__
        assert vlay.extent().area()>0.0
        assert vlay.dataProvider().featureCount()>0, 'selected finv (%i) has no features'%vlay.name()
        #=======================================================================
        # add map
        #=======================================================================
        layItem_map = QgsLayoutItemMap(qlayout)
         
        layItem_map.attemptSetSceneRect(qrect)
        layItem_map.setFrameEnabled(True)
        
 
        #add extent
        layItem_map.setExtent(vlay.extent())
        assert layItem_map.extent().area()>0.0
        
        #setting twice seems to be required for the extens to work
        layItem_map.attemptSetSceneRect(qrect)
        
        #add to the layout
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
                  qrect=QRectF(5, 20, 200, 10),
                  text_size=8,
                  text_bold=True,
                  text_underline=False,
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

        font = QtGui.QFont()
        font.setPointSize(text_size)
        font.setBold(text_bold)
        font.setUnderline(text_underline)
 
        label.setTextFormat(QgsTextFormat().fromQFont(font))
        
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
        # build the layouts 
        #=======================================================================
 
        layItem_html = QgsLayoutItemHtml(qlayout)
        
        #=======================================================================
        # add the frame
        #=======================================================================
        html_frame = QgsLayoutFrame(qlayout, layItem_html)
        html_frame.attemptSetSceneRect(QRectF(5, 20, 200, 260))
        html_frame.setFrameEnabled(True)
        layItem_html.addFrame(html_frame)
 
        #=======================================================================
        # populate layout
        #=======================================================================
 
        url = QUrl("file:///" + html_fp)
        log.debug('setUrl from %s'%url)
        layItem_html.setUrl(url) #phantom crashing test mode
        layItem_html.loadHtml()

        # change resize mode
        layItem_html.setResizeMode(QgsLayoutMultiFrame.ResizeMode.ExtendToNextPage)
        #=======================================================================

 
        
        log.info('added to %s'%qlayout.name())
        
        return layItem_html
 
            
    def add_picture(self, 
                    fp, #path to svg file to load
                    df=None, #dataframe to use for the event summary table
                    qlayout=None,
                    report=None,
                    title=None,
                    ):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None: 
            qlayout = self.add_section(report=report)
 
        log = self.logger.getChild('add_picture')
        
        assert os.path.exists(fp)
        
        layItem_pic = QgsLayoutItemPicture(qlayout)

        layItem_pic.attemptSetSceneRect(QRectF(5, 30, 200, 265))
        layItem_pic.setPicturePath(fp)
         
        qlayout.addLayoutItem(layItem_pic)

        # Check that event summary table is present
        if df is not None:
            #format table
            df.columns = map(str.upper, df.columns)
            df.iloc[:, 1] = df.iloc[:, 1].map(lambda impact_val: self.impactFmtFunc(impact_val)) #FutureWarning: Setting an item of incompatible dtype is deprecated and will raise in a future error of pandas. Value '0    0.00e+00
            
            #convert to layer
            df_layer = self.vlay_new_df2(df, layname='event_summary_table',
                                       logger=log)
            # Add table header
            self.add_label(qlayout=qlayout, text='Event Summary Table', qrect=QRectF(5, 150, 100, 100), 
                                                                            text_size=16, text_bold=False, text_underline=True)
            # Add the table under the picture                       
            self.add_table(df_layer, qlayout=qlayout, 
                            qrect=QRectF(25, 160, 160, 49.050), column_width=34)
        
        log.debug('added item from %s'%fp)
        
        #=======================================================================
        # add title
        #=======================================================================
        if not title is None:
            label = self.add_label(qlayout=qlayout, text=title, text_size=20)
        
        return layItem_pic

    #===========================================================================
    # Param 'finv_df_raw': Inventory file DataFrame object
    #===========================================================================
    def add_finv_smry(self, finv_df_raw, qlayout=None, report=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None: 
            qlayout = self.add_section(report=report)

        log = self.logger.getChild('add_finv_smry')
 
        #project = self.qproj
        
        #=======================================================================
        # prep data
        #=======================================================================
        finv_df = finv_df_raw.head(10).iloc[:,:3]

        #=======================================================================
        # # Create layout and vector layer with finv file path
        #=======================================================================
        finv_layer = self.vlay_new_df2(finv_df.reset_index(), layname='finv_summary_table',
                                       logger=log)

        self.add_table(df_layer=finv_layer, qrect=QRectF(25, 40, 160, 67.050),
                        qlayout=qlayout, report=report)
        
        #=======================================================================
        # add title
        #=======================================================================
        label = self.add_label(qlayout=qlayout, text='Inventory Summary', text_size=20)
        
        #=======================================================================
        # wrap
        #=======================================================================

        log.debug('added table from %s'%str(finv_df.shape))

    #===========================================================================
    # Param 'df_layer': QgsVectorLayer object derived from DataFrame
    # Param 'qrect': QRectF object to specify size and placement of table
    # Param 'qlayout': QgsLayout object to add table to
    # Param 'report': QgsReport object to add layout to
    #===========================================================================
    def add_table(self, df_layer, qrect=None, column_width=35, qlayout=None, report=None):
        #=======================================================================
        # defaults
        #=======================================================================
        if qlayout is None:
            qlayout = self.add_section(report=report)

        if qrect is None: 
            qrect = QRectF(25, 20, 160, 67.050)

        log = self.logger.getChild('add_table')

        project = self.qproj

        # Needs to be added to project instance as a temporary file to prevent data loss
        project.addMapLayer(df_layer)

        #=======================================================================
        # Set table layer
        #=======================================================================
        table = QgsLayoutItemAttributeTable.create(qlayout)
        table.setVectorLayer(df_layer)

         # Resize columns and set alignment to centre
        columns = table.columns()
        for column in columns:
            column.setHAlignment(Qt.AlignHCenter)
            column.setWidth(column_width)
        
        # Set table column styling and refresh table to display with new styling
        table.setColumns(columns)
        table.refresh()

        #=======================================================================
        # Add the frame
        #=======================================================================
        frame = QgsLayoutFrame(qlayout, table)
        frame.attemptSetSceneRect(qrect)
        frame.setFrameEnabled(True)
        table.addFrame(frame)

        # Add the frame to the layout
        qlayout.addMultiFrame(table)

        return table