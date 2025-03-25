'''
Created on Mar 25, 2025

@author: cef
'''
import os, tempfile


#===============================================================================
# directories and files-------
#===============================================================================
src_dir = os.path.dirname(os.path.dirname(__file__))
plugin_dir = os.path.dirname(__file__)
home_dir = os.path.join(os.path.expanduser('~'), 'CanFlood')
os.makedirs(home_dir, exist_ok=True)

temp_dir = os.path.join(tempfile.mkdtemp(), 'CanFlood')
os.makedirs(temp_dir, exist_ok=True)