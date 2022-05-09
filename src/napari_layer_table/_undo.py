"""
"""

from pprint import pprint
#from tkinter.messagebox import showinfo

import numpy as np
import pandas as pd

from qtpy import QtCore

from napari_layer_table._my_logger import logger
#from napari_layer_table._my_layer import mmLayer

class mmUndo(QtCore.QObject):
    #def __init__(self, layer : mmLayer):
    def __init__(self, layer):
        super().__init__()
        
        self._layer = layer

        self._undoList = []
        self._redoList = []

        self._layer.signalDataChanged.connect(self.slot_change)

    def numUndo(self):
        return len(self._undoList)
    
    def _addUndo(self, theDict):
        self._undoList.append(theDict)
    
    def doUndo(self):
        if self.numUndo() == 0:
            logger.info('nothing to undo')
            return
        
        logger.info('')
        
        theDict = self._undoList[-1]
        action = theDict['action']
        if action == 'add':
            # do delete
            logger.info(' do delete')
            print('  selected_data:', theDict['selected_data'])
            print('  data:', theDict['data'])
            #print('  df:', theDict['df'])
        if action == 'delete':
            # do delete
            logger.info(' do add')
            print('  selected_data:', theDict['selected_data'])
            print('  data:', theDict['data'])
            #print('  df:', theDict['df'])
        elif action =='change':
            # action should be called 'move'
            logger.info(' do move')
            print('  selected_data:', theDict['selected_data'])
            print('  data:', theDict['data'])


    def _getUndoDict(self, action : str, selected_data : set, selected_data2 : np.ndarray, df : pd.DataFrame):
        theDict = {
            'action': action,
            'selected_data': selected_data,
            'data': selected_data2,
            'df': df,
        }
        return theDict.copy()
    
    #def slot_change(self, action : str, selected_data : set, data : np.ndarray, df : pd.DataFrame):
    def slot_change(self, action, selected_data, selected_data2, df):
        logger.info('')
        theDict = self._getUndoDict(action, selected_data, selected_data2, df)
        self._addUndo(theDict)