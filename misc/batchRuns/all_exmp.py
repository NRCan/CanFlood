'''
Created on Feb. 14, 2021

@author: cefect

example script to run the batch models.

#===============================================================================
# INSTRUCTIONS
#===============================================================================
create 1 local function for each pXXX tool script (e.g., run_build, run_dmg, run_risk2, run_risk1)
    usually I give each of these functions their own script file for easy management/running
    these functions should havea all the filepaths/parameters for your run
    
each of these should run a 'tool' of the CanFlood modelling process independently

to link them all together:
    create an 'all' script like what's shown below
    

now you can run the linked version, or each piece  independently.
'''

out_dir=r'C:\LS\03_TOOLS\_jobs\202102_lang\_outs\cf'
#===============================================================================
# build
#===============================================================================
from cf import buildL
_ = buildL.run(out_dir=out_dir)
print('finished mBuild')
 
#===============================================================================
# r1 models
#===============================================================================
from cf import risk1L
_ = risk1L.run(out_dir=out_dir)
 

#===============================================================================
# r2 models
#===============================================================================

from cf import dmgL
_ = dmgL.run(out_dir=out_dir)
print('finished mDmg')

from cf import risk2L
_ = risk2L.run(out_dir=out_dir)
print('finished mRisk2')


 
from cf.res import joinL
_ = joinL.run(out_dir=out_dir)
