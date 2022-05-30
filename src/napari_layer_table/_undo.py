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
        
        self._layer = layer  # mmLayer

        # TODO (cudmore) keep adding (push) but pop oldest
        self._maxNumUndo = 20
        
        self._undoList = []
        self._redoList = []

        self._ignoreNewAction = False  # set to stop adding undo on actual undo

        self._layer.signalDataChanged.connect(self.slot_change)

    def numUndo(self):
        return len(self._undoList)
    
    def _addUndo(self, theDict):
        """Append to the list and keep it within max elements.
        """
        self._undoList.append(theDict)
        # limit list to last _maxNumUndo 
        self._undoList = self._undoList[-self._maxNumUndo:] 

    def _print(self):
        logger.info('  == undo stack is:')
        for item in self._undoList:
            print(f'    layer "{self._layer.getName()}" original undo action:', item['action'], item['selected_data'])
    
    def doUndo(self):
        """Pop the last action and perform undo.
        """
        if self.numUndo() == 0:
            logger.info('nothing to undo')
            return
                
        self._print()
        
        # pop from list
        theDict = self._undoList.pop(-1)
        action = theDict['action']
        if action == 'add':
            _selected_data = theDict['selected_data']
            logger.info(f'undo add with delete _selected_data:{_selected_data}')
            
            # TODO (cudmore) fix this, our _layer is a mmLAyer which has a napari _layer
            # Two steps (i) select and (ii) remove selected
            self._ignoreNewAction = True
            self._layer._layer.selected_data = _selected_data
            self._layer._layer.remove_selected()

            self._ignoreNewAction = False

        if action == 'delete':
            _selected_data = theDict['selected_data']
            logger.info(f' undo delete with add _selected_data:{_selected_data}')
            
            self._ignoreNewAction = True
            self._layer._paste_data(theDict['layerSelectionCopy'])
            self._ignoreNewAction = False

        elif action =='change':
            # action should be called 'move'
            logger.info(' do move by updating layer data')
            _selected_data_list = list(theDict['selected_data'])
            
            # TODO (cudmore) for shapes these are not ndarray but [shapes] !!!!
            _data = theDict['layerSelectionCopy']['data']

            print('    _selected_data_list:', _selected_data_list)  # the data to be moved
            print('    type(self._layer._layer.data):', type(self._layer._layer.data))
            print('    type(_data):', type(_data))
            print('    _data:', _data)
            print('    -->> not refreshing properly ???')
            
            # todo (cudmore) the viewer is not refreshing ???

            self._ignoreNewAction = True
            if isinstance(self._layer._layer.data, list):
                # shapes layer data is a list
                for oneIdx, oneItem in enumerate(_selected_data_list):
                    self._layer._layer.data[oneItem] = _data[oneIdx]  # property setter of napari layer
            else:
                # assuming np.ndarray
                self._layer._layer.data[_selected_data_list] = _data  # property setter of napari layer
            self._ignoreNewAction = False

            # the above is not refreshing the viewer
            self._layer._layer.refresh()

    def _getUndoDict(self, action : str,
                    selected_data : set,
                    #selected_data2 : np.ndarray,
                    layerSelectionCopy : dict,
                    df : pd.DataFrame):
        """
        Args:
            action (Str)
            select_data (Set)
            layerSelectionCopy (dict) Full copy of all selected layer info
            df (pd.DataFrame) DataFrame of all layer features.
        """
        theDict = {
            'action': action,
            'selected_data': selected_data,
            'layerSelectionCopy': layerSelectionCopy,
            'df': df,
        }
        return theDict.copy()
    
    #def slot_change(self, action : str, selected_data : set, data : np.ndarray, df : pd.DataFrame):
    def slot_change(self, action :str,
                    selected_data : set,
                    layerSelectionCopy : dict,
                    df : pd.DataFrame):
        # don't update undo if no selection
        # could also use selected_data
        if self._ignoreNewAction:
            # ignore new actions when actually doing undo
            return
        
        if action == 'select':
            # no undo action for selection
            return
        
        # debug (Cudmore) put this back in
        #if action == 'change':
        #    return
        
        if layerSelectionCopy:
            logger.info(f'action:{action} selected_data:{selected_data}')
            theDict = self._getUndoDict(action, selected_data, layerSelectionCopy, df)
            self._addUndo(theDict)