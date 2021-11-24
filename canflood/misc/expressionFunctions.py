'''
Created on Nov. 23, 2021

@author: cefect

all expression functions usd by the plugin
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
    <p>Add a fixed value to the fX_elv field (by nestID)</p>
    <p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; background-color:#f6f6f6;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; font-size:medium; font-weight:600; color:#93b023; background-color:#f6f6f6;">Syntax</span></p>
    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; font-weight:600; color:#0a6099;">finv_elv_add</span><span style=" font-family:'Courier New'; color:#000000;">(</span><span style=" font-family:'monospace'; font-style:italic; color:#bf0c0c;">delta, nestID</span><span style=" font-family:'Courier New'; color:#000000;">)</span></p>
    <p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; background-color:#f6f6f6;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; font-size:medium; font-weight:600; color:#93b023; background-color:#f6f6f6;">Arguments</span></p>
    <table border="0" cellpadding="0" cellspacing="2" style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px;">
        <tbody>
            <tr>
                <td style=" padding-right:10;">
                    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'monospace'; font-style:italic; color:#bf0c0c;">nestID</span></p>
                </td>
                <td>
                    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; color:#000000;">field nest index</span></p>
                </td>
            </tr>
            <tr>
                <td style=" padding-right:10;">
                    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'monospace'; font-style:italic; color:#bf0c0c;">delta</span></p>
                </td>
                <td>value to add</td>
            </tr>
        </tbody>
    </table>
    <p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; background-color:#f6f6f6;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; font-size:medium; font-weight:600; color:#93b023; background-color:#f6f6f6;">Examples</span></p>
    <ul style="margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 1;">
        <li style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; color:#000000;"><span style=" font-family:'Courier New';">finv_elv_add(1.0, 1)</span> &rarr; feat[f1_elv] +1</li>
    </ul>
    """
    
    return value1 + feat['f%i_elv'%nestID]

@qgsfunction(args="auto", group=groupName)
def finv_scale_add(value1, nestID, feat, parent):
    """
    <p>Add a fixed value to the fX_scale field (by nestID)</p>
    <p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; background-color:#f6f6f6;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; font-size:medium; font-weight:600; color:#93b023; background-color:#f6f6f6;">Syntax</span></p>
    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; font-weight:600; color:#0a6099;">finv_elv_add</span><span style=" font-family:'Courier New'; color:#000000;">(</span><span style=" font-family:'monospace'; font-style:italic; color:#bf0c0c;">delta, nestID</span><span style=" font-family:'Courier New'; color:#000000;">)</span></p>
    <p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; background-color:#f6f6f6;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; font-size:medium; font-weight:600; color:#93b023; background-color:#f6f6f6;">Arguments</span></p>
    <table border="0" cellpadding="0" cellspacing="2" style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px;">
        <tbody>
            <tr>
                <td style=" padding-right:10;">
                    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'monospace'; font-style:italic; color:#bf0c0c;">nestID</span></p>
                </td>
                <td>
                    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; color:#000000;">field nest index</span></p>
                </td>
            </tr>
            <tr>
                <td style=" padding-right:10;">
                    <p style=" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;"><span style=" font-family:'monospace'; font-style:italic; color:#bf0c0c;">delta</span></p>
                </td>
                <td>value to add</td>
            </tr>
        </tbody>
    </table>
    <p style=" margin-top:12px; margin-bottom:12px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px; background-color:#f6f6f6;"><span style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; font-size:medium; font-weight:600; color:#93b023; background-color:#f6f6f6;">Examples</span></p>
    <ul style="margin-top: 0px; margin-bottom: 0px; margin-left: 0px; margin-right: 0px; -qt-list-indent: 1;">
        <li style=" font-family:'Lato,Open Sans,Lucida Grande,Segoe UI,Arial,sans-serif'; color:#000000;"><span style=" font-family:'Courier New';">finv_scale_add(1.0, 1)</span> &rarr; feat[f1_scale] +1</li>
    </ul>
    """
    
    return value1 + feat['f%i_scale'%nestID]


#===============================================================================
# interface control
#===============================================================================
"""called by CanFlood.unload"""
all_funcs_l =  [
        finv_elv_add
        ]

def addToInterface(funcs_l=None):
    if funcs_l is None:
        funcs_l=all_funcs_l
    for func in funcs_l:
        QgsExpression.registerFunction(func) 
        
def unloadFromInterface():
    for func in all_funcs_l:
        QgsExpression.unregisterFunction(func.name())