'''
Created on Feb. 9, 2021

@author: cefect
'''


from io import BytesIO

import requests, os
import pandas as pd
from hlpr.basic import view

"""couldnt get this to work
r = requests.get('https://docs.google.com/spreadsheets/d/1CwoGkVlY6YPF3zb67BlJTKjeNr09Mez0f6c7EjPOmNg/edit?usp=sharing')
data = r.content


df = pd.read_csv(BytesIO(data), index_col=0)"""
#===============================================================================
# inputs
#===============================================================================
fp = r'C:\LS\03_TOOLS\CanFlood\ins\misc\vfunc_conv\CanFlood - Vulnerability Functions - libraries.csv'

out_dir = r'C:\LS\03_TOOLS\CanFlood\ins\misc\vfunc_conv'

#===============================================================================
# load
#===============================================================================
df_raw = pd.read_csv(fp, header=1, index_col=None)


df = df_raw.dropna(subset=['name'], how='any', axis=0).set_index('name', drop=False)

df = df.dropna(axis=1, how='all')

#description (main display)
colnh_d = {
    'description':[
        'creation_date', 'location','name'],
    'variables':[
             'reference', 'asset_types1', 'asset_types2', 'reference_2', 'original_platform',
               'classification_scheme', 'flood_type', 'impact_units', 'cost_base',
               'cost_year', 'empirical_synthetic'
               ]
       }
#===============================================================================
# prechecks
#===============================================================================
for sname, l in colnh_d.items():
    miss_l = set(l).difference(df.columns)
    assert len(miss_l)==0, '%s columns not found: %s'%(sname, miss_l)
    
if not os.path.exists(out_dir):os.makedirs(out_dir)
#===============================================================================
# loop and build
#===============================================================================
print('on %s'%str(df.shape))
for name, row in df.iterrows():
    print('building \'%s\''%name)
    #setup the container
    od = os.path.join(out_dir, name)
    os.makedirs(od)
    
    
    


"""
view(df)

df.columns
"""