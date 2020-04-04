'''
Created on Sep 29, 2018

@author: cef

Helper functions for graphical user interface
'''
import os, copy, sys, logging
import tkinter, tkinter.filedialog 


mod_logger = logging.getLogger(__name__)






class Selection():
    
    pick = None
    
    def __init__(self, pick_l, title = 'select',logger = mod_logger):
        
        self.pick_l = pick_l
        self.title = title
        self.logger = logger.getChild('Buttons')
        
        
        #===========================================================================
        # initilize gui
        #===========================================================================
        self.root = tkinter.Tk()
        self.root.title(self.title) #add the title
        self.root.wm_attributes('-topmost', 1)  #push it to the top
               
        return 
    
    def dropdown(self): #give the user a drop down menu to pick from
        """
        user needs to close the menu to continue
        """
        logger= self.logger.getChild('dropdown')
    
        variable = tkinter.StringVar(self.root)
        variable.set(self.pick_l[0]) # default value
        
        class Sel():
            def __init__(self, parent):
                self.parent = parent
            def get(self, pick):
                self.parent.pick = pick
                self.parent.root.destroy() #kill the tkinter windoww
                print('user picked %s'%pick)
                return
        
        #===========================================================================
        # add the options menu
        #===========================================================================
        w = tkinter.OptionMenu(self.root, variable, *self.pick_l, command=Sel(self).get).pack()
    
  
        
        print(('%s'%self.title))
        
        tkinter.mainloop()
        
        logger.info('user selected \'%s\''%self.pick)
        
        return self.pick
        
    def buttons(self):

        #=======================================================================
        # build selector workers
        #=======================================================================
        class Sel():
            def __init__(self, pick, parent):
                self.pick = pick
                self.parent = parent
            def get(self):
                self.parent.pick = self.pick
                self.parent.root.destroy() #kill the tkinter windoww
                print('user picked %s'%self.pick)
                return self.pick
                
                
        #===========================================================================
        # loop through and add all these buttons
        #===========================================================================
        for option in self.pick_l:
            
            #pack the button
            tkinter.Button(self.root, text=option, command=Sel(option, self).get).pack()
            
        #pause foer the user
        print('Waiting for user to make selection.....')
        self.root.mainloop()
        
        
        
        if self.pick is None:
            self.logger.error('got no pick')
            raise IOError
        else:
            self.logger.info('user selected \'%s\''%self.pick)
        
        return self.pick

    

def DropDownMenu(options_list, prompt=None, count=1,  title = "Select"): #gui for selecting an item from a list
    import easygui
    """TESTING
    list = ['choice1', 'choice2','chioce3']
    choice = DropDownMenu(list, prompt = 'pick me!')
    """
    

    if prompt == None: prompt = 'select option'

    if not isinstance(count, int):
        try: count = int(count)
        except:
            logger.error('got unexpected type for count kwd: \n %s'%type(count))
            raise TypeError
            
    if not isinstance(options_list, list):
        try: options_list = list(options_list)
        except:
            logger.error('got unexpected type for kwarg options_list: %s'%type(options_list))
            raise TypeError
    
    if count == 1:
    
        choice = easygui.choicebox(prompt ,title, options_list)
        
    elif count >1:
        
        choice = easygui.multchoicebox(prompt , title, options_list) 
        
    else:
        logger.error('got unexpected value for kwarg count: %s'%count)
        raise IOError
    
    return choice

#===============================================================================
# Directory Functions
#===============================================================================

def gui_fileopen(title = None, 
                 indir = None, #initial directory to spawn gui
                 filetypes = None, 
                 logger=mod_logger): #gui to select and return filename
    
    logger=logger.getChild('file_open_gui')
    
    if indir == None:
        indir = __file__
    if title == None:
        title = 'pick your file'
        
    #configure the file types        
    if filetypes == None:
        filetypes = [("all files","*.*")]

    elif filetypes == 'csv':
        filetypes = [('comma separated', '.csv')]
        
    elif filetypes == 'xls':
        filetypes = [('excel files', '.xls')]
        'doesnt seem to be working'
    else: raise IOError
        
        
    root = tkinter.Tk()
    root.withdraw() 
    root.wm_attributes('-topmost', 1)  #push it to the top
    
    print('waiting on user to select file....')
    
    filename = tkinter.filedialog.askopenfilename(title=title, 
                                   initialdir=indir,
                                   filetypes=filetypes)
    
    logger.info('user selected file:\n    %s'%filename)
    
    return filename



def get_dir(title = None, 
                 indir = None, #initial directory to spawn gui
                 logger=mod_logger): #gui to select and return filename
    
    logger=logger.getChild('get_dir')
    
    if indir == None:
        indir = __file__
    if title == None:
        title = 'pick directory'
                
    root = tkinter.Tk()
    root.withdraw() 
    root.wm_attributes('-topmost', 1)  #push it to the top
    
    print('waiting on user to select file....')
    
    dir = tkinter.filedialog.askdirectory(title=title, 
                                   initialdir=indir,)
    
    logger.info('user selected dir:\n    %s'%dir)
    
    return dir

def GetfileSave(title=None, initialdir=None, logger = mod_logger): #gui to pick a filename to save as
    logger=logger.getChild('GetfileSave')
    root = tkinter.Tk()
    root.withdraw()
    if title == None: title = 'Select Data Folder'
    
    if initialdir == None: initialdir = 'C:\\Users\cef\Google Drive\School\\UofA\Thesis\02_MODEL\ABM_py_TESTs'
    filename = tkinter.filedialog.asksaveasfilename(title=title, initialdir=initialdir)
    logger.debug('Directory selected: \n %s'%filename)
    return filename       
    
def OutDir():
    'show an "Open" dialog box with title in the header and return the path to the selected'
    root = tkinter.Tk()
    root.withdraw()
    
    title = 'Select Directory to dump outputs'
    initialdir = 'C:\\Users\cef\qgis_base\outputs'
    directory = tkinter.filedialog.askdirectory(title=title, initialdir=initialdir)
    #root.mainloop()
    #raw_input()
    
    return directory  

def WorkingDir():
    'show an "Open" dialog box with title in the header and return the path to the selected'
    root = tkinter.Tk()
    root.withdraw()
    
    title = 'Working Directory'
    initialdir = 'C:\\Users\cef\qgis_base'
    directory = tkinter.filedialog.askdirectory(title=title, initialdir=initialdir)
    #root.mainloop()
    #raw_input()
    
    return directory

def file_saveas(title = None, indir = None, defaultextension = None, logger=mod_logger): #gui to select file save as
    logger=logger.getChild('file_saveas')
    
    
    if indir == None:
        indir = __file__
    if title == None:
        title = 'Save file as'
        
    filename = tkinter.filedialog.asksaveasfilename(title=title, 
                                   initialdir=indir,
                                   defaultextension = defaultextension)
    
    
    logger.debug('user selected \'%s\''%filename)
    
    return filename    