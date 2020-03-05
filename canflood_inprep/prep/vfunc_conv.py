'''
Created on Feb. 18, 2020

@author: cefect

convert rfda damage functions to CanFlood format
'''

#==============================================================================
# imports
#==============================================================================
import os
import pandas as pd
import numpy as np

from hp import view

#==============================================================================
# inputs
#==============================================================================
#filepath to rfda damage curves (to be converted)
rfda_fp = r'C:\LS\03_TOOLS\CanFlood\_ins\prep\vfunc_conv\Calgary2016_rfda_curves.csv'


bsmt_ht = 1.8 #for combination curves

#==============================================================================
# load
#==============================================================================

df_raw = pd.read_csv(rfda_fp, header=None)

#drop the counts
df = df_raw.drop(0, axis=0)

#set the index
df = df.set_index(0)
df.index.name = 'cname'


#get the curve name prefix
df['cnp'] = df.index.str.slice(start=0, stop=2)


#set the dcount columns
df = df.rename(columns = {1:'dcount'})

#re-order the columns
boolcol = df.columns.isin(['dcount', 'cnp'])
df = df.loc[:, ~boolcol].join(df.loc[:, boolcol])


#==============================================================================
# convert residential tags
#==============================================================================
#identify the residentials
rboolidx = df.loc[:, 24].isin(['MC', 'MS', 'BC', 'BS'])

#build new index
df['nindex'] = df.loc[rboolidx, 'cnp'] + '_' + df.loc[rboolidx,24]

df.loc[~rboolidx, 'nindex'] = df[~rboolidx].index
df['oindex'] = df.index
df = df.set_index('nindex', drop=True)

#ctype = df.loc[boolidx,24].to_dict() #get all the types

#==============================================================================
# create individuals
#==============================================================================
res_d = dict() #container for CanFlood function tabs
dd_set_d = dict() #container for all the depth damages

boolar = df.columns.isin(['dcount', 'cnp', 'oindex'])




for cname, row in df.iterrows():
    
    #==========================================================================
    # set meta info
    #==========================================================================

    
    
    
    dcurve_d = {'tag':cname,
                'desc':'rfda converted',
                'source':'Alberta (2014)',
                'location':'Alberta',
                'date':2014,
                'vuln_units':'$CAD/m2',
                'dep_units':'m',
                'scale':'occupied space area',
                'ftype':'depth-damage',
                'depth':'damage'}

    
    #==========================================================================
    # depth damage info
    #==========================================================================
    #get just depth damage
    dd_ser = row[~boolar].dropna()
    
    #identify depths (evens) 
    bool_dep = dd_ser.index.values % 2 == 0
    
    #identiy damages
    bool_dmg = np.invert(bool_dep)
    
    #bundle depth:damage
    dd_d = dict(zip(dd_ser[bool_dep].tolist(),dd_ser[bool_dmg].tolist() ))
    
    
    #check for validty
    if max(dd_d.values()) == 0:
        print('%s has no damages! skipping'%cname)
    
    #add it in
    res_d[cname] = {**dcurve_d, **dd_d}
    dd_set_d[cname] = dd_d #used below
    print('added %s'%dcurve_d['tag'])




#==============================================================================
# create combined basement+mf
#==============================================================================


#slice to this
boolidx = df.loc[:, 24].isin(['MC', 'MS', 'BC', 'BS'])
df_res = df.loc[boolidx,:].dropna(axis=1, how='all')

df_res = df_res.rename(columns = {24:'ctype'})


cnp_l = df_res.loc[:, 'cnp'].unique().tolist()



#loop and collect
for cnp in cnp_l:
    #loop on structural and contents
    for ctype in ('S', 'C'):
        #get this
        boolidx1 = np.logical_and(
            df_res['cnp'] == cnp, #this class
            df_res['ctype'].str.contains(ctype), #this ctype
            )
        
        #check it
        if not boolidx1.sum() == 2:
            raise IOError('unexpected count')
        
        #======================================================================
        # #collect by floor
        #======================================================================
        fdd_d = dict()
        for floor in ('M', 'B'):

            boolidx2 = np.logical_and(boolidx1,
                                      df_res['ctype'].str.contains(floor))
            
            if not boolidx2.sum() == 1:
                raise IOError('unexpected count')
            
            #get this dict
            cname = df_res.index[boolidx2][0]
            fdd_d[floor] = dd_set_d.pop(cname)
            
        #======================================================================
        # adjust basement
        #======================================================================
        #add bsmt_ht to all the basement

        res_serf = pd.Series(fdd_d['B'])
        
        if bsmt_ht > max(res_serf.index):
            raise IOError('requested basement height %.2f out of range'%bsmt_ht)
        
        res_serf.index = res_serf.index - bsmt_ht
        res_serf.index = res_serf.index.values.round(2)
        
        #get max value
        dmgmax = max(res_serf)
        
        
        #drop all positives (basement cant have posiitive depths)
        res_ser = res_serf[res_serf.index <= 0].sort_index(ascending=True)
        
        #set highest value to max
        res_ser.loc[0] = dmgmax
        
        #======================================================================
        # assemble
        #======================================================================
        mf_ser = pd.Series(fdd_d['M']) + dmgmax
        
        res_ser = res_ser.append(mf_ser, ignore_index=False).sort_index(ascending=True)
        
        #only take positive values
        res_ser = res_ser[res_ser > 0]
        #======================================================================
        # set meta
        #======================================================================
        tag = '%s_%s'%(cnp, ctype)
        dcurve_d = {'tag':tag,
                'desc':'rfda converted and combined w/ bsmt_ht = %.2f'%bsmt_ht,
                'source':'Alberta (2014)',
                'location':'Alberta',
                'date':2014,
                'vuln_units':'$CAD/m2',
                'dep_units':'m',
                'scale':'occupied space area',
                'ftype':'depth-damage',
                'depth':'damage'}
        
        #add it in
        res_d[tag] = {**dcurve_d, **res_ser.to_dict()}
        
        print('added %s'%tag)
        
        
        

        
    



#==============================================================================
# convert
#==============================================================================
df_d = dict()
for cname, d in res_d.items():
    df_d[cname] = pd.Series(d).to_frame()

#==============================================================================
# write results
#==============================================================================
out_fp = os.path.join(r'C:\LS\03_TOOLS\CanFlood\_outs\vfunc_conv',
                      'rfda_conv.xls')
print('writing set of %i to file: \n    %s'%(len(res_d), out_fp))
#write to multiple tabs
writer = pd.ExcelWriter(out_fp, engine='xlsxwriter')
for tabnm, df in df_d.items():
    df.to_excel(writer, sheet_name=tabnm, index=True, header=False)
writer.save()


