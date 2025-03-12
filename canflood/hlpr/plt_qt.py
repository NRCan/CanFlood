'''
Created on Mar. 1, 2021

@author: cefect
'''
import sys, os


from PyQt5 import QtCore, QtWidgets

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg , NavigationToolbar2QT

#from matplotlib.figure import Figure
import matplotlib


class PltWindow(QtWidgets.QMainWindow):
    def __init__(self, figure, out_dir=None, parent=None):
        # Pass parent to the QMainWindow constructor
        super().__init__(parent)
        
        #=======================================================================
        # defaults
        #=======================================================================
        if out_dir is None:
            out_dir = os.getcwd()
        
        # Ensure the output directory exists and update matplotlib defaults
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
        matplotlib.rcParams['savefig.directory'] = out_dir
        
        # Set window title (be cautious accessing _suptitle as it is somewhat internal)
        self.setWindowTitle('CanFlood %s' % (figure._suptitle.get_text()[:15]))
        
        #=======================================================================
        # setup window
        #=======================================================================
        # Create the main widget and set it as the central widget
        self._main = QtWidgets.QWidget()
        self.setCentralWidget(self._main)
        
        # Create layout for the main widget
        layout = QtWidgets.QVBoxLayout(self._main)
        
        # Create and add the canvas
        canvas = FigureCanvasQTAgg(figure)
        layout.addWidget(canvas)
        
        # Create and add the navigation toolbar
        self._toolbar = NavigationToolbar2QT(canvas, self)
        self.addToolBar(self._toolbar)
        

        
        
        
        

