# -*- coding: utf-8 -*-
"""
ui class for the vfunction selection dialog
"""
#==============================================================================
# imports-----------
#==============================================================================
#python
import sys, os, datetime, time, configparser

from shutil import copyfile

"""see __init__.py for dependency check"""
import pandas as pd
import numpy as np #assuming if pandas is fine, numpy will be fine

#PyQt
from PyQt5 import uic, QtWidgets
from PyQt5.QtWidgets import QFileSystemModel, QListView, QHeaderView
from PyQt5.QtCore import QStringListModel, QAbstractTableModel
from PyQt5 import QtGui

#qgis

#from qgis.core import *


#==============================================================================
# custom imports
#==============================================================================


from hlpr.basic import get_valid_filename, force_open_dir, ComWrkr
from hlpr.exceptions import QError as Error
from hlpr.plug import MyFeedBackQ, QprojPlug, pandasModel
from misc.curvePlot import CurvePlotr


#===============================================================================
# logger
#===============================================================================


#===============================================================================
# load UI file
#===============================================================================
# This loads your .ui file so that PyQt can populate your plugin with the elements from Qt Designer
ui_fp = os.path.join(os.path.dirname(__file__), 'vfunc_select.ui')
assert os.path.exists(ui_fp), 'failed to find the ui file: \n    %s'%ui_fp
FORM_CLASS, _ = uic.loadUiType(ui_fp)


#===============================================================================
# class objects-------
#===============================================================================

class vDialog(QtWidgets.QDialog, FORM_CLASS, QprojPlug):
    """
    constructed by  BuildDialog
    """
    vdata_d = dict()
    dfModel3 = None
    fsModel = None
    
    linEdit_ScenTag = 'scenario'
    lineEdit_wd = None

    def __init__(self, 
                 iface, 
                 parent=None,
                 plogger=None):
        """these will only ini tthe first baseclass (QtWidgets.QDialog)
        
        required"""
        super(vDialog, self).__init__(parent) #only calls QtWidgets.QDialog
        

        #=======================================================================
        # attachments
        #=======================================================================
        self.iface = iface
        
        #=======================================================================
        # setup funcs
        #=======================================================================

        self.setupUi(self)
        
        # Set up the user interface from Designer through FORM_CLASS.
        # After self.setupUi() you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect


        #=======================================================================
        # qproj_setup 
        #=======================================================================
        """setup to run outside qgis
        self.qproj_setup() #basic dialog worker setup"""
        
        if plogger is None: plogger = hlpr.plug.logger(self) 
        self.logger=plogger
        

        self.setup_feedback(progressBar = self.progressBar,
                            feedback = MyFeedBackQ())
        
        self.pars_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), '_pars')
        
        self.vfunc_dir = os.path.join(self.pars_dir, 'vfunc')
        
        assert os.path.exists(self.vfunc_dir), 'got bad function directory: %s'%self.vfunc_dir
        
        #=======================================================================
        # connect the slots
        #=======================================================================        
        #self.connect_slots()
        
        
        
        self.logger.debug('rDialog initilized')
        
    def _setup(self):
        _ = self.get_libData()
        self.connect_slots()
        return self

    def connect_slots(self):
        log = self.logger.getChild('connect_slots')

        #======================================================================
        # pull project data
        #======================================================================

                
        #=======================================================================
        # general----------------
        #=======================================================================

        #ok/cancel buttons
        self.buttonBox.accepted.connect(self.reject) #back out of the dialog
        self.buttonBox.rejected.connect(self.reject)
        
        
        
        self.logger.statusQlab=self.progressText #connect to the progress text
        #=======================================================================
        # library meta table------
        #=======================================================================
        #=======================================================================
        # build model
        #=======================================================================
        vdata_d = self.vdata_d
        assert len(vdata_d)>0
        
        #build a df of what we want to display
        df = pd.DataFrame.from_dict({k: v['meta.d'] for k,v in vdata_d.items()}
                                    ).T.reset_index()
        
        #lModel = QStringListModel(list(vdata_d.keys()))
        self.dfModel = pandasModel(df)
        
        #=======================================================================
        # setup  view
        #=======================================================================
        self.tableView.setModel(self.dfModel)
        
        #adjust columns
        header = self.tableView.horizontalHeader()
        for lindex in [0, 1]: #resize specific columns to contents
            header.setSectionResizeMode(lindex, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        
        #=======================================================================
        # connections
        #=======================================================================
        #connect selection
        self.tableView.selectionModel().selectionChanged.connect(self.displayDetails)
        self.tableView.selectionModel().selectionChanged.connect(self.displayFiles)
        
        #=======================================================================
        # connect buttons------
        #=======================================================================
        self.pushButton_copy.clicked.connect(self.copy_vfuncs)
        self.pushButton_PlotSet.clicked.connect(self.plot_set)
        
        #=======================================================================
        # wrap
        #=======================================================================
        

    
    def displayDetails(self): #display details on the selected library
        #log = self.logger.getChild('displayDetails')
        
        #=======================================================================
        # retrieve selection
        #=======================================================================
        #check we have a selection
        if len(self.tableView.selectionModel().selectedRows())==0:
            return 
        
        #get the selection index
        """should only allow 1 row.. but taking the first regardless"""
        sindex = self.tableView.selectionModel().selectedRows()[0]
        row = sindex.row()
        
        #get this value
        libName = self.dfModel.data(self.dfModel.index(row, 0))
        #log.debug('user selected \'%s\''%libName)
        self.libName = libName #set for retrieving curve details
        #=======================================================================
        # build data for this
        #=======================================================================
        df = self.vdetails_d[libName]
        self.dfModel2 = pandasModel(df)
        
        
        #=======================================================================
        # send to the widget
        #=======================================================================
        self.tableView_right.setModel(self.dfModel2)
        
    def displayFiles(self): #show the xls files on the treeview for the selected library
        """
        called when a library is selected
        """
        #check we have a selection
        if len(self.tableView.selectionModel().selectedRows())==0:
            return 
        log = self.logger.getChild('displayFiles')
        #=======================================================================
        # retrieve selection
        #=======================================================================
        #get the selection index
        """should only allow 1 row.. but taking the first regardless"""
        sindex = self.tableView.selectionModel().selectedRows()[0]
        row = sindex.row()
        
        #get this value
        libName = self.dfModel.data(self.dfModel.index(row, 0))
        #log.debug('user selected \'%s\''%libName)
        
        #=======================================================================
        # data setup
        #=======================================================================
        focus_dir = self.vdata_d[libName]['basedir']
        #focus_dir = r'C:\LS\03_TOOLS\CanFlood\_git\canflood\_pars\vfunc'

        #=======================================================================
        # #build the model
        #=======================================================================
        assert os.path.exists(focus_dir)
        fsModel = QFileSystemModel()
        fsModel.setRootPath(focus_dir)
        fsModel.setNameFilters(['*.xls'])
        self.fsModel = fsModel
        
        #=======================================================================
        # #tree view
        #=======================================================================
        self.treeView.setModel(fsModel)
        self.treeView.setRootIndex(fsModel.index(focus_dir))
        log.debug('connected treeView to QFileSystemModel w/: \n    %s'%focus_dir)
        
        #adjust columns
        header = self.treeView.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setStretchLastSection(False)
        #self.treeView.resizeColumnToContents(0)
        
        #=======================================================================
        # connect it
        #=======================================================================
        self.treeView.selectionModel().selectionChanged.connect(self.dislpayCsDetails)
        
        """
        if not self.dfModel3 is None:
            self.dfModel3.clear()
        #self.tableView_bottomRight.clearSpans() #clear the table view until next trigger
        
        """

        
        try: #cleanup the model
            self.tableView_bottomRight.setModel(pandasModel(pd.DataFrame())) #set a dummy model
            del self.dfModel3
        except:pass
        
    def _get_cset_selection(self): #pull the selected file information from the Tree
        if self.fsModel is None:
            return None, None
        
        selModel = self.treeView.selectionModel() #get the selection model
        index = selModel.currentIndex()
        
        #get the model index from this
        indexItem = self.fsModel.index(index.row(), 0, index.parent())
        
        fp = self.fsModel.filePath(indexItem)
        fn = self.fsModel.fileName(indexItem)
        
        #wrap
        assert os.path.exists(fp), fp
        

        return fn, fp 

        
        
    def dislpayCsDetails(self): #display the selected curve set details
        """called when a curve set is selected"""

        
        #=======================================================================
        # #get the selection
        #=======================================================================
        fileName, filePath = self._get_cset_selection()
        
        #=======================================================================
        # build data for this
        #=======================================================================
        df = pd.Series(self.vdata_d[self.libName]['curves_d'][fileName], name='values'
                  ).to_frame().reset_index().rename(columns={'index':'var'})


        self.dfModel3 = pandasModel(df)
        
        
        #=======================================================================
        # send to the widget
        #=======================================================================
        self.tableView_bottomRight.setModel(self.dfModel3)
        
        #adjust columns
        header = self.tableView_bottomRight.horizontalHeader()
        for lindex in [0]: #resize specific columns to contents
            header.setSectionResizeMode(lindex, QHeaderView.ResizeToContents)
        header.setStretchLastSection(True)
        
        
    def _get_buildPars(self): #helper to retrieve info off the parent class
        
        #=======================================================================
        # disconntected sessions
        #=======================================================================
        if isinstance(self.linEdit_ScenTag, str):
            return self.linEdit_ScenTag, os.getcwd()
        else:
            return self.linEdit_ScenTag.text(), self.lineEdit_wd.text()

        
    def plot_set(self):
        #=======================================================================
        # defaults
        #=======================================================================
        log = self.logger.getChild('plot_set')
        
        #=======================================================================
        # retrieve
        #=======================================================================
        tag, out_dir = self._get_buildPars()
        fileName, filePath = self._get_cset_selection()
        if filePath is None: 
            log.warning('no file selected!')
            return
        #=======================================================================
        # execute
        #=======================================================================
    
        wrkr = CurvePlotr(out_dir=out_dir, logger=self.logger, tag=tag)
        
        #load data
        cLib_d = wrkr.load_data(filePath)
        
        #plot
        fig = wrkr.plotAll(cLib_d)
        
        #output
        ofp = wrkr.output_fig(fig)
        
        try:
            force_open_dir(os.path.split(ofp)[0])
        except Exception as e:
            log.warning('failed to open dir')
        
        return
        
        
    def get_libData(self,
                    vfunc_dir=None):
        
        #=======================================================================
        # defaults
        #=======================================================================
        if vfunc_dir is None: vfunc_dir = self.vfunc_dir
        log = self.logger.getChild('get_libData')
    
        #=======================================================================
        # collect the meta files
        #=======================================================================
        meta_fps = set()
        for dirpath, dirnames, fns in os.walk(vfunc_dir):
            meta_fps.update([os.path.join(dirpath, e) for e in fns if e.endswith('metadata.txt')])
             
        assert len(meta_fps)>0
        log.info('got %i vfunc libs'%len(meta_fps))
        
        #=======================================================================
        # #load data in each collection
        #=======================================================================
        vdata_d = dict()
        for fp in meta_fps:
            assert os.path.exists(fp), fp
            #get filepath info
            basedir = os.path.split(fp)[0]
            parentName = os.path.split(basedir)[1] #get parent name from the containing folder
            
            d = dict() #start the page
            d['basedir'] = basedir #add the data directory
            
    
            #=======================================================================
            # from meta  file
            #=======================================================================
            #open the file
            log.debug('loading from %s'%fp)
            cPars = configparser.ConfigParser(inline_comment_prefixes='#')
            _ = cPars.read(fp)
            
            #check it
            miss_l = set(['description', 'variables']).difference(cPars.sections())
            assert len(miss_l)==0, '%s meta file missing sections: %s'%(parentName, miss_l)
            
            
            #pull out the data
            d['meta.d'] = {k:v for k,v in cPars['description'].items()}
            d['meta.v'] = {k:v for k,v in cPars['variables'].items()}
                
            #=======================================================================
            # data contents
            #=======================================================================
            fns = [e for e in os.listdir(basedir) if e.endswith('.xls')]
            d['curveSet_fns'] = fns
            d['curveSet_cnt'] = len(fns)
            
            #===================================================================
            # #curve set values
            #===================================================================
            """
            display these on 
            """
            curves_d = dict()
            for fn in fns:
                fp = os.path.join(basedir, fn)
                assert os.path.exists(fp), fp
                
                cs_d = dict()
                
                
                df_d_raw = pd.read_excel(fp, sheet_name=None, header=None, index_col=None)
                
                df_d = {k:v for k,v in df_d_raw.items() if not k.startswith('_')} #drop dummy tabs
                
                cs_d['cnt'] = len(df_d)
                cs_d['tags'] = list(df_d.keys())
                curves_d[fn] = cs_d
                
            #summarize
            d['curves_d'] = curves_d

            
            """no.. just give details on each .xls
            d['curve_cnt'] = pd.DataFrame.from_dict(curves_d).T['cnt'].sum()
            
            l1 = [v['tags'] for v in curves_d.values()]
            d['curve_tags'] = set([e for subl in l1 for e in subl])
            d['curve_tags_cnt'] = len(d['curve_tags'])"""
            #===================================================================
            # wrap this library
            #===================================================================
            vdata_d[parentName] = d
            log.info('finished on %s'%parentName)
            
        #=======================================================================
        # clean up details
        #=======================================================================
        """not adding anything any more"""
        detailKeys = []
        #detailKeys = ['curve_tags', 'curve_tags_cnt'] #top level tags to pull out and add to the details
        #store the details for displayDetails()
        d = {k: v['meta.v'] for k,v in vdata_d.items()}
        
        d2 = dict()
        for libName, sub_d in d.copy().items():
            #add some info
            sub_d2 = {**sub_d, **{k:v for k,v in vdata_d[libName].items() if k in detailKeys}}
            
            #add this as a data frame
            d2[libName] = pd.Series(sub_d2, name='value').to_frame().reset_index().rename(columns={'index':'vars'})
        self.vdetails_d = d2
        
        #=======================================================================
        # wrap
        #=======================================================================
        log.info('finished collecting on %i librarires'%len(vdata_d))
        self.vdata_d = vdata_d.copy()
        return vdata_d
        
        
        
    def copy_vfuncs(self): #copy the selected vfuncs into the users working directory
        log = self.logger.getChild('copy_vfuncs')
        #get the output directory
        """should be assigned by BuildDialog"""
        tag, out_dir = self._get_buildPars()
        
        #=======================================================================
        # #get the selection
        #=======================================================================
        fileName, filePath = self._get_cset_selection()
        log.debug('user selected %s'%filePath)
        
        
        #=======================================================================
        # copy it over
        #=======================================================================
        ofp = os.path.join(out_dir, fileName)
        copyfile(filePath, ofp)
        log.info('copied over %s'%ofp)
        
        #=======================================================================
        # fill in the text box
        #=======================================================================
        try:
            self.lineEdit_curve.setText(ofp)
        except Exception as e:
            log.warning('failed ot fill lineEdit w/ %s'%e)
                
            
        
if __name__=='__main__':
    print('yay')

    

        
        
        
                
  
 

           
            
                    
            