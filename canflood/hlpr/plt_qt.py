'''
Created on Mar. 1, 2021

@author: cefect
'''
import sys, os


from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvas, NavigationToolbar2QT

from matplotlib.figure import Figure
import matplotlib


class PltWindow(QtWidgets.QMainWindow):
    def __init__(self, 
                 figure, 
                 out_dir=None,
                 ):
        super().__init__()
        
        #=======================================================================
        # defauklts
        #=======================================================================
        if out_dir is None: out_dir = os.getcwd()
        
        
        #update defaults

        if not os.path.exists(out_dir):os.makedirs(out_dir)
        matplotlib.rcParams['savefig.directory'] = out_dir
        
        #styleize window
        self.setWindowTitle('CanFlood %s'%(figure._suptitle.get_text()[:15]))
        
        #=======================================================================
        # setup window
        #=======================================================================
        #add the main widget
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        
        #build a la yout
        layout = QtWidgets.QVBoxLayout(self._main)

        #build/add canvas to layout
        canvas = FigureCanvas(figure)
        layout.addWidget(canvas)
        
        #build/add toolbar
        self._toolbar = NavigationToolbar2QT(canvas, self)
                
        self.addToolBar(self._toolbar)
        

        
        
        
        

