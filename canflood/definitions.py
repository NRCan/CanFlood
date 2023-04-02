'''
Created on Jun. 26, 2022

@author: cefect
'''
import os

#project base/source directory
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) #C:\LS\09_REPOS\03_TOOLS\CanFlood\_git\
src_dir=base_dir
assert os.path.exists(src_dir)
