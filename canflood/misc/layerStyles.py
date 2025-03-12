'''
Created on Nov. 24, 2021

@author: cefect

worker to add styles to the menu
'''
import os
from canflood.hlpr.plug import QMenuAction

from qgis.core import  QgsStyle

class StylesAction(QMenuAction):
    
    #action parameters
    icon_fn = 'paint-palette.png'
    icon_name = 'Add Layer Styles'
    icon_location = 'menu'
    
    def launch(self):
        log = self.logger.getChild('l')
        pars_dir = self.session.pars_dir
        #=======================================================================
        # filepath
        #=======================================================================
        
        fp = os.path.join(pars_dir, 'CanFlood.xml')
        assert os.path.exists(fp), 'requested xml filepath does not exist: %s'%fp
        
        #=======================================================================
        # add the sylte
        #=======================================================================
        style = QgsStyle.defaultStyle() #get the users style database

        if style.importXml(fp):
            log.push('imported styles from %s'%fp)
        else:
            log.error('failed to import styles')