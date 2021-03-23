'''
Created on Feb. 9, 2021

@author: cefect
'''


from io import BytesIO

import requests, os, configparser, sys, locale
import pandas as pd
from hlpr.basic import view, force_open_dir
from hlpr.exceptions import Error

"""couldnt get this to work
r = requests.get('https://docs.google.com/spreadsheets/d/1CwoGkVlY6YPF3zb67BlJTKjeNr09Mez0f6c7EjPOmNg/edit?usp=sharing')
data = r.content


df = pd.read_csv(BytesIO(data), index_col=0)"""
#===============================================================================
# inputs
#===============================================================================
fp = r'C:\LS\03_TOOLS\CanFlood\ins\misc\vfunc_conv\CanFlood - Vulnerability Functions - libraries.csv'

out_dir = r'C:\LS\03_TOOLS\CanFlood\outs\misc\vfunc_conv\meta'

#description (main display)
colnh_d = {
    'description':[
        'creation_date', 'location','name'],
    'variables':[
             'reference', 'asset_types1', 'asset_types2', 'reference_2', 'native_platform',
               'classification_scheme', 'flood_type', 'impact_units', 'cost_base',
               'cost_year', 'empirical_synthetic'
               ]
       }

#===============================================================================
# load
#===============================================================================
df_raw = pd.read_csv(fp, header=1, index_col=None)


#===============================================================================
# clean
#===============================================================================
df = df_raw.dropna(subset=['name'], how='any', axis=0).set_index('name', drop=False)

df = df.dropna(axis=1, how='all')

#get just those in the library
df.loc[:, 'vlib'] = df['vlib'].fillna(False)
boolidx = df['vlib']

print('%i of %i vlib=True'%(boolidx.sum(), len(boolidx)))
df = df.loc[boolidx, :].drop('vlib', axis=1)

"""
df.columns
"""
#===============================================================================
# prechecks
#===============================================================================
for sname, l in colnh_d.items():
    miss_l = set(l).difference(df.columns)
    assert len(miss_l)==0, '%s columns not found: %s'%(sname, miss_l)
    
if not os.path.exists(out_dir):os.makedirs(out_dir)

#===============================================================================
# formatters
#===============================================================================
#df.loc[:,'creation_date'] =df['creation_date'].astype(int) 
"""
view(df)
"""

encoding = locale.getpreferredencoding()


"""this makes the references ugly... but should stop the errors"""
for coln in ['Source', 'reference']:
    """
    view(df[coln].str.encode('ascii'))
    """
    try:
        df.loc[:, coln] = df[coln].str.encode('utf-8')
    except Exception as e:
        raise Error('\'%s\' has some bad character: \n    %s'%(coln, e))
    #print(coln)

#===============================================================================
# loop and build
#===============================================================================

print('on %s'%str(df.shape))

for name, r_raw in df.iterrows():
    print('building \'%s\''%name)

    
    #setup the container
    od = os.path.join(out_dir, name)
    if not os.path.exists(od):os.makedirs(od)
    
    #===========================================================================
    # prep data
    #===========================================================================
    row = r_raw.dropna()
    
    #format dates
    for coln in ['cost_year', 'creation_date']:
        if coln in row:
            row[coln] = int(row[coln])
    
    #===========================================================================
    # collect data
    #===========================================================================
    
    lib_d = dict() #results container
    
    for sname, cols in colnh_d.items():
        lib_d[sname] = row[row.index.isin(cols)].to_dict()
        
    #===========================================================================
    # config file
    #===========================================================================
    
    cPars = configparser.ConfigParser()
    cPars.read_dict(lib_d)
    
    #write it
    cfp = os.path.join(od, 'metadata.txt')
    with open(cfp, 'w') as configFile:
        cPars.write(configFile)
        
    print('    wrote to %s'%cfp)
    
    
force_open_dir(out_dir)



"""
view(df)

df.columns
"""