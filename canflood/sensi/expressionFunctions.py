'''
Created on Nov. 23, 2021

@author: cefect
'''

from qgis.utils import qgsfunction

groupName= 'CanFlood'
#===============================================================================
# define functions
#===============================================================================

@qgsfunction(args="auto", group=groupName)
def finv_elv_add(value1, value2, feature, parent):
    return value1.toInt()[0] & value2.toInt()[0]


#===============================================================================
# add to interface
#===============================================================================

def addToInterface():
    from qgis.core import QgsExpression
    
    for func in [
        ]:
    
        QgsExpression.registerFunction(finv_elv_add) 