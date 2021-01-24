'''
Created on Jan. 23, 2021

@author: cefect

common model testing methods
'''
import unittest, tempfile, inspect, logging, os, fnmatch


class tModel(unittest.TestCase): #common model level testing methods
    
    def __init__(self, *args, 
                 Model=None, #model object to test
                 tdata_d = None, #container of data to test against

                 **kwargs):

        #=======================================================================
        # attach
        #=======================================================================
        self.Model=Model
        self.tdata_d = tdata_d
        self.name=Model.tag

        assert inspect.isclass(type(Model))
        
        print('init \'%s\' w/ \'%s\' \n    args: %s'%(
            self.__class__.__name__, self.Model.tag,   args))
        

        super().__init__(*args, **kwargs) #initilzie the baseclass cascade
        
    #===========================================================================
    # expected handler methods---------
    #===========================================================================
        
    def setUp(self):
        print('setting up %s (%s) %s'%(self.__class__.__name__, self.Model.tag, self._testMethodName))
    def tearDown(self):
        print('tearing down %s (%s) %s \n'%(self.__class__.__name__, self.Model.tag, self._testMethodName))
        
        
    #===========================================================================
    # test methods---------
    #===========================================================================

