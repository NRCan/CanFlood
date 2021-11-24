'''
Created on Nov. 23, 2021

@author: cefect
'''

from qgis.utils import qgsfunction
from qgis.core import QgsExpression

groupName= 'CanFlood'
#===============================================================================
# define functions
#===============================================================================

@qgsfunction(args="auto", group=groupName)
def finv_elv_add(value1, nestID, feat, parent):
    """
    Add a fixed value to a finv's fX_elv field
    
    <h2>Example usage:</h2>
    <ul>
      <li>finv_elv_add(1.2, 2) -> feat[f2_elv] + 1.2</li>

    </ul>
    """
    
    return value1.toFloat()[0] + feat['f%i_elv'%nestID]


#===============================================================================
# interface control
#===============================================================================
funcs_l =  [
        finv_elv_add
        ]

def addToInterface():
    for func in funcs_l:
        QgsExpression.registerFunction(func) 
        
def unloadFromInterface():
    for func in funcs_l:
        QgsExpression.unregisterFunction(func.name())