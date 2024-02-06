"""
"""
from copy import copy, deepcopy
import time

from typing import Union #Callable, TypeVar

from pprint import pprint

import numpy as np
import pandas as pd

from napari.qt import get_app  # for flash on selection, see snapToItem()

from skimage.measure import regionprops, regionprops_table  # for labeled layer

# turn off pandas warning
# no longer needed, in general all pandas 'cells' have to be scalar
# this was needed when we were assigning a list for (r,g,b,a), now using #RRGGBBAA
# see: https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
# for a way to temporarily turn it off using 'with'
# pd.options.mode.chained_assignment = None

from qtpy import QtCore

#from napari.layers.points import _points_mouse_bindings  # import add, highlight, select

# oct 17, was this
#from napari.layers.shapes import _shapes_mouse_bindings  #vertex_insert

#from napari.layers.utils.layer_utils import features_to_pandas_dataframe

# oct 17, was this
from napari.layers.utils.layer_utils import _features_to_properties  # , _FeatureTable

from napari.utils.colormaps.standardize_color import (
    rgb_to_hex,
)

from napari_layer_table._my_logger import logger
from napari_layer_table._undo import mmUndo

#
# see here for searching unicode symbols
# https://unicode-search.net/unicode-namesearch.pl
# here, we map napari shape names to unicode characters we can print
SYMBOL_ALIAS = {
    'arrow': '\u02C3',
    'clobber': '\u2663',  # no corresponding unicode ?
    # 'cross': '\u271A', # abb remove 202402
    'diamond': '\u25C6',
    'disc': '\u26AB',
    'hbar': '\u2501',
    'ring': '\u20DD',
    'square': '\u25A0',  # or '\u2B1B'    
    'star': '\u2605',
    'tailed_arrow': '\u2B95',
    'triangle_down': '\u25BC',
    'triangle_up': '\u25B2',
    'vbar': '\u2759',
    'cross': '\u002B',  # abb 202402
    'x': '\u2716',    
    }

# TODO (cudmore) put this in a _utils.py file (used by miltiple files)
def setsAreEqual(a, b):
    """Convenience function. Return true if sets (a, b) are equal.
    """
    if len(a) != len(b):
        return False
    for x in a:
        if x not in b:
            return False
    return True

class mmLayer(QtCore.QObject):
    # Note: these have to be kept in sync with labelLayer signals
    signalDataChanged = QtCore.Signal(str,  # action
                            set,            # selected set
                            dict,           # _layerSelectionCopy
                            pd.DataFrame)   # properties DataFrame
    
    signalLayerNameChange = QtCore.Signal(str)

    def __init__(self, viewer, layer,
                    onAddCallback=None,
                    onDeleteCallback=None,
                    ):
        """
        Args:
            onAddCallback (func) params(set, pd.DataFrame) return Union[None, dict]
        """
        super().__init__()
        
        self._viewer = viewer
        self._layer = layer

        self._shift_click_for_new = False
        self._onAddCallback = onAddCallback  # callback to accept/reject/modify add
        self.newOnShiftClick(onAddCallback is not None)
        
        # not sure how to use bind_key
        self._deleteOnDeleteKey = False
        self._onDeleteCallback = onDeleteCallback  # callback to accept/reject/modify add
        self.deleteOnDeleteKey(onDeleteCallback is not None)
        #self._layer.bind_key(self.xxx)
        
        self._flashTimer = None
        # flash on point selection

        self._undo = None  # creat undo object in derived classes

        self._onlyOneLayer = True

        self._blockOnAdd = False

        self._layerSelectionCopy = None  # a copy of all selected layer data

        self._selected_data = layer.selected_data.copy()
        
        # replaced by full copy of table in _layerSelectionCopy
        '''if list(self._selected_data):
            self._selected_data2 = layer.data[self._selected_data]
        else:
            # TODO (cudmore) can we initialize with None ???
            self._selected_data2 = np.ndarray([])
        '''

        self._numItems = len(layer.data)

        self._connectLayer()

        # slots to detect a change in layer selection
        self._viewer.layers.events.inserting.connect(self.slot_insert_layer)
        self._viewer.layers.events.inserted.connect(self.slot_insert_layer)
        self._viewer.layers.events.removed.connect(self.slot_remove_layer)
        self._viewer.layers.events.removing.connect(self.slot_remove_layer)

        self._viewer.layers.selection.events.changed.connect(self.slot_select_layer)

        # todo (cudmore) for now, experiment with this in the mmPoints layer
        #self._undo = mmUndo(self)  # undo connect to self.signalDataChanged

    '''
    def keyPressEvent(self, event):
        logger.info('')
        if event.key() == QtCore.Qt.Key_Q:
            pass
        elif event.key() == QtCore.Qt.Key_Enter:
            pass
        event.accept()
    '''

    @property
    def properties(self):
        return self._layer.properties
    
    def old_on_delete_key_callback(self):
        """Intercept del keystroke and decide if we really want to delete.
        
        Notes:
            not implemented.
        """
        logger.info('')

    def _copy_data(self):
        """Make a complete copy of a layer selection.

        Implement in derived classes.
        """
        pass

    def doUndo(self):
        if self._undo is not None:
            self._undo.doUndo()

    def addFeature(self, featureName : str, columnName : Union[str, None] = None):
        """Add a feature to layer.
        
        Args:
            featureName: The key name of the feature to add to layer
            columnName: Specify if column name in table is different from feature name.
        
        Notes:
            We don't want our features (like 'x') to contaminate
            an existing layer features. User may already have a feature 'x'
            we don't want to over-wrte it.
            
            Thus, use
                featureName = 'ltp_x'
                columnName = 'x'
        """
        if columnName is None:
            columnName = featureName
        features = self._layer.features # get existing
        # check if column exists
        if featureName in features.columns:
            logger.warning('Feature already exists')
            return
        features[featureName] = None  # need to be len(layer)

    def snapToItem(self, selectedRow : int, isAlt : bool =False):
        """Visually snap the viewer to selected item.
        """
        pass

    def bringToFront(self):
        """Bring the underlying layer to the front.
        """
        if self._viewer.layers.selection.active != self._layer:
            self._viewer.layers.selection.active = self._layer

    def getName(self):
        """Get the name from underlying layer.
        """
        return self._layer.name
    
    def numItems(self):
        """Get the current number of items.

        Used to determine if we have add/delete in slot_user_edit_highlight().
        """
        return self._numItems
        
    def selectItems(self, selectedRowSet : set):
        """Set the selected items in layer.
        
        Called from _my_widget on user selectnig row(s) in table
        
        TODO:
            not used.
        """
        self._layer.selected_data = selectedRowSet

    @property
    def selected_data(self):
        return self._selected_data

    def _connectLayer(self, layer=None):
        
        self._layer.events.name.connect(self.slot_user_edit_name)
        self._layer.events.highlight.connect(self.slot_user_edit_highlight)
        self._layer.events.data.connect(self.slot_user_edit_data)

        # no longer available in PyPi napari
        # self._layer.events.features.connect(self.slot_user_edit_features)

        # we want to receive an event when user sets the face color of (points, shapes)
        # this does not trigger?
        self._layer.events.face_color.connect(self.slot_user_edit_face_color)
        # this triggers but only for points layer
        #self._layer._face.events.current_color.connect(self.slot_user_edit_face_color)
        
        # want to use this, only triggers for shapes layer
        #self._layer.events.current_face_color.connect(self.slot_user_edit_face_color)

        # this is never called, not sure if it even triggers
        self._layer.events.properties.connect(self.slot_user_edit_properties)

    def newOnShiftClick(self, on = None):
        """Enable/disable shift+click for new points.
        """
        if on is not None:
            self._shift_click_for_new = on
        
        if self._shift_click_for_new:
            logger.info(f'{self._derivedClassName()} enabling newOnShiftClick')
            self._layer.mouse_drag_callbacks.append(self._on_mouse_drag)
        else:
            try:
                logger.info(f'{self._derivedClassName()} disabling newOnShiftClick')
                self._layer.mouse_drag_callbacks.remove(self._on_mouse_drag)
            except (ValueError) as e:
                # not in list
                pass
            
    def deleteOnDeleteKey(self, on = None):
        self._deleteOnDeleteKey = on

    def _on_mouse_drag(self, layer, event):
        """Handle user mouse-clicks. Intercept shift+click to make a new point.

        Will only be called when install with newOnShiftClick().
        """
        if 'Shift' in event.modifiers:
            # make a new point at cursor position
            onAddReturn = {}
            if self._onAddCallback is not None:
                logger.info(f'checking with _onAddCallback ...')
                # onAddCallback should determine (i) if we want to actually add
                # (ii) if add is ok, return a dict of values for selected row
                onAddReturn = self._onAddCallback(self._selected_data, self.getDataFrame())
                if onAddReturn is None:
                    print('    shift+clik was rejected -->> no new point')
                    return
                else:
                    print('  on add return returned dict:')
                    pprint(onAddReturn)

            data_coordinates = self._layer.world_to_data(event.position)
            # always add as integer pixels (not fractional/float pixels)
            cords = np.round(data_coordinates).astype(int)
            
            # add to layer, only for points layer?
            # for shape layer type 'path', use add_paths()
            # self._layer.add(cords)
            self.addAnnotation(cords, event, features=onAddReturn)

            # set features from onAddReturn

    '''
    def on_mouse_wheel(self, layer, event):
        """Mouse wheel callback.
        
        Over-ride default behavior to become
        
            mouse-wheel: scroll through image planes (need a 3d image)
            mouse-wheel + ctrl: zoom in/out on mouse position
        """        
        # used to find what data the event has
        pprint(vars(event))
        
        isShift = 'Shift' in event.modifiers
        isControl = 'Control' in event.modifiers

        #xDelta = event.delta[0]  # ignore
        yDelta = event.delta[1]  # +1 is 'up', -1 is 'down'

        logger.info(f'handled:{event.handled} isShift:{isShift} isControl:{isControl} yDelta:{yDelta}')

        #self.dims._increment_dims_left()
        if isControl:            
            zoomScale = 0.1
            _start_zoom = self._viewer.camera.zoom
            self._viewer.camera.zoom = _start_zoom * (zoomScale + yDelta)
            #event.handled = True
    '''

    def addAnnotation(self, coords, event = None, features:dict = None):
        """Add an annotation to a layer.
        
        Define when deriving. For points layer use 'self._layer.add(cords)'
       
        Args:
            coords:
            event: napari mouse down event
        """
        pass

    def getDataFrame(self, getFull=False) -> pd.DataFrame:
        """Get a dataframe from layer.
        
        Args:
            getFull: get full dataframe
                otherwise, get datafram for _selectedData
        """

        # self._layer.features gives us a (features, properties) pandas dataframe !!!        
        # can be empty !!!
        dfFeatures = self._layer.features  # all features

        # not neccessary, alreay a pd.DataFrame (I think)
        # dfFeatures = features_to_pandas_dataframe(dfFeatures)

        if getFull:
            selectedList = list(range(len(self._layer.data)))
        else:
            selectedList = list(self._selected_data)

        # reduce by selection
        df = dfFeatures.loc[selectedList]

        if len(df) == 0:
            df = pd.DataFrame(index=selectedList)

        #
        # This is impossibly hard to get working
        # I just want to assign a column named 'Face Color'
        # Bottom line, all cells in a pd.DataFrame need to be scalars
        # TODO (cudmore) use hex values rather than rgba

        # SettingWithCopyWarning
        # A value is trying to be set on a copy of a slice from a DataFrame.
        # Try using .loc[row_indexer,col_indexer] = value instead
        #print('=== SettingWithCopyWarning:', self._derivedClassName())
        #print('selectedList:', selectedList)
        #pprint(df)
        # ValueError: cannot set a frame with no defined index and a scalar
        # df.loc[selectedList, 'Face Color'] = ''


        if selectedList:
            # TODO (cudmore) rgb_to_hex() returns an np.array with  dtype of unicode '|U9''
            #    we want it as a string ???
            tmpColor = [str(rgb_to_hex(oneColor)[0])
                        for oneColor in self._layer.face_color[selectedList]]        

            df.loc[selectedList, 'Face Color'] = tmpColor
        
        return df

    def _derivedClassName(self):
        return self.__class__.__name__

    def slot_user_edit_highlight(self, event):
        """Called repeatedly on mouse hover.

        Error:
            mm_env/lib/python3.9/site-packages/numpy/core/fromnumeric.py:43:
            VisibleDeprecationWarning:
            Creating an ndarray from ragged nested sequences
            (which is a list-or-tuple of lists-or-tuples-or ndarrays with different lengths or shapes)
            is deprecated.
            If you meant to do this, you must specify 'dtype=object' when creating the ndarray.!

        """
        newSelection = not setsAreEqual(event.source.selected_data, self._selected_data)
            
        action = 'none'
        if len(event.source.data) > self.numItems():
            # add an item: for points layer is point, for shapes layer is shape
            # event.source.selected_data gives us the added points
            # for shape layer, *this is called multiple times without the added items selected
            if newSelection:
                action = 'add'
            else:
                # this happens on add in shapes layer
                # for shapes, need to add
                print('    ==== data length changed but selection did not...')
                print('     event.source.selected_data:', event.source.selected_data)
                print('     self._selected_data:', self._selected_data)
                '''
                _newSelectionStart = self.numItems()
                _newSelectionStop = len(event.source.data)
                _newSelectionRange = np.arange(_newSelectionStart, _newSelectionStop)
                event.source.selected_data = set(_newSelectionRange)
                print(f'     tweeked event.source.selected_data: {event.source.selected_data}')
                action = 'add'
                '''
        elif len(event.source.data) < self.numItems():
            # event.source.selected_data tells us the rows
            # THEY NO LONGER EXIST
            # our current self._selected_data tells us the rows
            action = 'delete'
        elif newSelection:
            action = 'select'

        '''
        if newSelection and self._blockOnAdd and not event.source.selected_data:
            # after shapes add, we re-enter here but event.source.selected_data is empty set()
            # should be the newly added shape(s), e.g. self._selected_data
            print('        ================')
            print('        action:', action)
            print('        convert to action: select')
            event.source.selected_data = self._selected_data
            self._blockOnAdd = False
        '''

        if action != 'none':
            logger.info(f'{self._derivedClassName()}')
            print('    newSelection:', newSelection)
            print('    event.source.selected_data:', event.source.selected_data)
            print('    self._selected_data:', self._selected_data)
            print('    len(event.source.data):', len(event.source.data))
            print('    self.numItems():', self.numItems())
            print('    action:', action)

        # signal what changed
        if action == 'add':
            # for shapes layer, when we get called again selected_data == set()
            self._blockOnAdd = True
            
            # on add we have new items and they are selected
            self._selected_data = event.source.selected_data.copy()
            self._numItems = len(event.source.data)

            # trying to figure out shapes layer
            # after add shapes layer trigger selection with set(), not with what was added
            #if not self._selected_data:
            #    print(f'    ERROR in {self._derivedClassName()} ... new shapes are not selected')
            _selected_data_set = set(self._selected_data)  # abb 202402
            self._copy_data()  # copy all selected points to _layerSelectionCopy
            self._updateFeatures(self._selected_data)
            dfFeatures = self.getDataFrame()
            print(f'  -->> signalDataChanged.emit "add" with _selected_data:{self._selected_data}')
            self.signalDataChanged.emit('add',
                                _selected_data_set,
                                # self._selected_data,
                                self._layerSelectionCopy,
                                dfFeatures)

        elif action == 'delete':
            # on delete, data indices were deleted_selected_data
            delete_selected_data = self._selected_data.copy()
            delete_selected_data_set = set(delete_selected_data)  # abb 202402
            self._selected_data = set()
            self._numItems = len(event.source.data)
            
            # here we are reusing previous _layerSelectionCopy
            # from action ('add', 'select')
            logger.info(f'  -->> signalDataChanged.emit "delete" with delete_selected_data:{delete_selected_data}')
            self.signalDataChanged.emit('delete',
                            delete_selected_data_set,  # abb 202402
                            # delete_selected_data,
                            self._layerSelectionCopy,
                            pd.DataFrame())
        
        elif action == 'select':
            self._selected_data = event.source.selected_data.copy()

            selectedDataSet = set(self._selected_data)
            self._copy_data()  # copy all selected points to _layerSelectionCopy
            dfProperties = self.getDataFrame()

            logger.info(f'action:{action}')
            print(f'  -->> signalDataChanged.emit "select" with _selected_data:{self._selected_data}')
            pprint(dfProperties)
            print('')
            self.signalDataChanged.emit('select',
                                selectedDataSet,  # abb 202402
                                # self._selected_data,
                                self._layerSelectionCopy,
                                dfProperties)

    def slot_user_edit_data(self, event):
        """User edited a point in the current layer.
        
        This is generated when user finishes a click+drag.
                
        Notes:
            On key-press (like delete), we need to ignore event.source.mode
        """

        # if there is no selection, there is never a change
        # this does not work for shapes layer
        if not self._selected_data:
            # no data changes when no selection
            logger.info(f'NO CHANGE BECAUSE _selected_data is {self._selected_data}')
            return

        # we usually show x/y/z in table
        # update our internal fatures
        self._updateFeatures(self._selected_data)

        # copy the selection
        self._copy_data()

        dfFeatures = self.getDataFrame()

        logger.info('')
        logger.info(f'  -->> signalDataChanged.emit "change" with _selected_data:{self._selected_data}')
        logger.info('    features:')
        pprint(dfFeatures)

        selectedDataSet = set(self._selected_data)
        self.signalDataChanged.emit('change', 
                        selectedDataSet,  # abb 202402
                        # self._selected_data, 
                        self._layerSelectionCopy, 
                        dfFeatures)

    def slot_user_edit_face_color(self, event):
        """User selected a face color.
        
        Change the face color of selected points.

        Note:
            - Using hex #RRGGBBAA
            - QColor takes #AARRGGBB, see _data_model.data (QtCore.Qt.ForegroundRole)
        """
        layer = self._viewer.layers.selection.active  # can be None
        try:
            print('        layer selected_data:', layer.selected_data)
            print('        self.selected_data:', self._selected_data)
            if not setsAreEqual(layer.selected_data, self._selected_data):
                logger.warning('ignoring event: selected_data do not match')
                return
        except (AttributeError) as e:
            logger.warning(e)
            return
            
        if self._selected_data:
                       
            current_face_color = self._layer.current_face_color  # hex

            logger.info(f'current_face_color:{current_face_color}')

            dfProperties = self.getDataFrame()

            index = list(self._selected_data)
            dfProperties.loc[index, 'Face Color'] = current_face_color
            
            #for oneRowIndex in index:
            #    properties.loc[oneRowIndex, 'Face Color'] = current_face_color

            # copy selected data, not sure this is needed, updates _layerSelectionCopy
            self._copy_data()

            print('  -->> emit "change"')
            print('        self._selected_data:', self._selected_data)
            print('        dfProperties:')
            pprint(dfProperties)
                
            #pprint(vars(event))
            #print('\n\n')
            _selected_data_set = set(self._selected_data)
            self.signalDataChanged.emit('change',
                            _selected_data_set,
                            # self._selected_data,
                            self._layerSelectionCopy,
                            dfProperties)

    def slot_user_edit_name(self, event):
        print('slot_user_edit_name()')
        #newName = self._layer.name
        newName = event.source.name
        self.signalLayerNameChange.emit(newName)

    def slot_user_edit_properties(self, event):
        logger.info('')

    def slot_user_edit_features(self, event):
        logger.info('')

    def slot_select_layer(self, event):
        """Respond to layer selection in viewer.
        
        Args:
            event (Event): event.type == 'changed'
        """
        #logger.info(f'event.type: {event.type}')

        if self._onlyOneLayer:
            return

        # BUG: does not give the correct layer
        # Need to query global viewer. Is selected layer in event???
        #layer = event.source
        layer = self._viewer.layers.selection.active
        
        #if layer is not None:
        #    if layer != self._layer:
        #        self.connectLayer(layer)
        if layer != self._layer:
            self._connectLayer(layer)

    def slot_insert_layer(self, event):
        """Respond to new layer in viewer.
        """
        
        if self._onlyOneLayer:
            return
                
        if event.type == 'inserting':
            pass
        elif event.type == 'inserted':
            logger.info(f'New layer "{event.value}" was inserted at index {event.index}')
            
            layer = event.value
            self._connectLayer(layer)

    def slot_remove_layer(self, event):
        """Respond to layer delete in viewer.
        """

        if self._onlyOneLayer:
            return

        if event.type == 'removing':
            pass
        elif event.type == 'removed':
            logger.info(f'Removed layer "{event.value}"')
            
            # table data is empty
            #self.refreshTableData([])

            # TODO: does not work, newSelectedLayer is always None
            # we are not receiving new layer selection
            # do it manually from current state of the viewer
            newSelectedLayer = self._viewer.layers.selection.active
            self._connectLayer(newSelectedLayer)

    def printEvent(self, event):
        """Print all info on an event.
        
        TODO (cudmore) Not used.
        """
        print(f'    _printEvent() type:{type(event)}')
        print(f'    event.type: {event.type}')
        print(f'    event.source: {event.source} {type(event.source)}')
        print(f'    event.source.name: "{event.source.name}"')        
        print(f'    event.source.mode: {event.source.mode}')        
        print(f'    event.source.selected_data: {event.source.selected_data}')

        # data is either a list or an ndarray
        print(f'    type(event.source.data): {type(event.source.data)}')
        print(f'    len(event.source.data): {len(event.source.data)}')

        print(f'    event.source.data: {event.source.data}')
        
        #try:
        #    print(f'    event.added: {event.added}')
        #except (AttributeError) as e:
        #    print(f'    event.added: ERROR')

class pointsLayer(mmLayer):
    def __init__(self, viewer, layer, *args, **kwargs):

        super().__init__(viewer, layer, *args, **kwargs)

        logger.info('Creating pointsLayer')

        # features this layer will calculate
        # updated in _updateFeatures
        # stored in layer features and displayed as columns in table
        self.addFeature('x')
        self.addFeature('y')
        if self._layer.ndim >= 3:
            self.addFeature('z')
    
        self._updateFeatures()

        # todo (cudmore) for now, experiment with this in the mmPoints layer
        #self._undo = mmUndo(self)  # undo connect to self.signalDataChanged

    def _connectLayer(self, layer=None):
        """Connect underlying layer signals to slots.
        """
        super()._connectLayer()

        # this triggers but only for points layer
        # was this
        self._layer._face.events.current_color.connect(self.slot_user_edit_face_color)
        # this this
        #self._layer.events.face_color.connect(self.slot_user_edit_face_color)
        #self._layer.events.current_face_color.connect(self.slot_user_edit_face_color)

        self._layer.events.symbol.connect(self.slot_user_edit_symbol)  # points layer
        self._layer.events.size.connect(self.slot_user_edit_size)  # points layer

    def _updateFeatures(self, selectedDataSet=None):
        """Update layer features based on selection.
        
        Used for (i) creation and (ii) on data move.

        Args:
            selectedDataSet (set) selected data, Pass None to update all.
        """
        if selectedDataSet is None:
            selectedDataSet = set(range(self.numItems()))
        
        
        selectedList = list(selectedDataSet)

        # logger.info(f'check x/y/z order')
        # print(self._layer.data)
        
        #TODO: (cudmore) what if points layer has dim > 3 ???
        if self._layer.ndim == 3:
            self._layer.features.loc[selectedList, 'z'] = \
                            self._layer.data[selectedList,0]
            self._layer.features.loc[selectedList, 'x'] = \
                                self._layer.data[selectedList,2]
            self._layer.features.loc[selectedList, 'y'] = \
                                self._layer.data[selectedList,1]
        elif self._layer.ndim == 2:
            self._layer.features.loc[selectedList, 'x'] = \
                                self._layer.data[selectedList,1]
            self._layer.features.loc[selectedList, 'y'] = \
                                self._layer.data[selectedList,0]

    def _copy_data(self):
        """Copy selected points to clipboard.
        
        Taken from napari.layers.points.points.py
        
        This is used to capture 'state' so we can undo with _paste_data
        
        problems with `pip install napari`
        e.g. 'text': layer.text._copy(index)
        gives error: AttributeError: 'TextManager' object has no attribute '_copy'

        TODO (cudmore) this is changing with different version of napari.
        """
        if len(self.selected_data) > 0:
            layer = self._layer  # abb
            index = list(self.selected_data)
            self._layerSelectionCopy = {
                'data': deepcopy(layer.data[index]),
                'edge_color': deepcopy(layer.edge_color[index]),
                'face_color': deepcopy(layer.face_color[index]),
                'shown': deepcopy(layer.shown[index]),
                'size': deepcopy(layer.size[index]),
                'edge_width': deepcopy(layer.edge_width[index]),
                'features': deepcopy(layer.features.iloc[index]),
                'indices': layer._slice_indices,
                #'text': layer.text._copy(index),
            }
            # TODO (Cudmore) layer.text.values is usually a <class 'numpy.ndarray'>
            # is this always true?
            # secondly, what is layer.text.value anyway? and what is dtype <U1
            # print(f'  === layer.text.values: "{layer.text.values}" {type(layer.text.values)}')
            # print('    ', layer.text.values.shape, layer.text.values.dtype)
            #if len(layer.text.values.shape) == 0:
            if layer.text.values.size == 0:
                    self._layerSelectionCopy['text'] = np.empty(0)
            else:
                try:
                    self._layerSelectionCopy['text'] = deepcopy(layer.text.values[index])
                except (IndexError) as e:
                    logger.error(f'I DO NOT UNDERSTAND HOW TO FIX THIS! {e}')
                    self._layerSelectionCopy['text'] = np.empty(0)

        else:
            self._layerSelectionCopy = {}

    def _paste_data(self, layerSelectionCopy=None):
        """Paste any point from clipboard and select them.
        
        Used by undo to 'paste/add' after delete.
        
        Copy of code in napari.layers.points.points.py
        
        We need to swap self ... for `layer = self._layer``

        Notes:
            This is very complicated, will break on napari updates.
            Hard to unit test.
        """
        layer = self._layer
        if layerSelectionCopy is None:
            _clipboard = self._layerSelectionCopy
        else:
            _clipboard = layerSelectionCopy

        npoints = len(layer._view_data)
        totpoints = len(layer.data)
        
        #if len(layer._clipboard.keys()) > 0:
        if len(_clipboard.keys()) > 0:
            not_disp = layer._dims_not_displayed
            data = deepcopy(_clipboard['data'])
            offset = [
                layer._slice_indices[i] - _clipboard['indices'][i]
                for i in not_disp
            ]
            data[:, not_disp] = data[:, not_disp] + np.array(offset)
            layer._data = np.append(layer.data, data, axis=0)
            layer._shown = np.append(
                layer.shown, deepcopy(_clipboard['shown']), axis=0
            )
            layer._size = np.append(
                layer.size, deepcopy(_clipboard['size']), axis=0
            )

            #layer._feature_table.append(_clipboard['features'])

            #layer.text._paste(**_clipboard['text'])

            layer._edge_width = np.append(
                layer.edge_width,
                deepcopy(_clipboard['edge_width']),
                axis=0,
            )
            layer._edge._paste(
                colors=_clipboard['edge_color'],
                properties=_features_to_properties(
                    _clipboard['features']
                ),
            )
            layer._face._paste(
                colors=_clipboard['face_color'],
                properties=_features_to_properties(
                    _clipboard['features']
                ),
            )

            # new in `pip install napari`
            layer._feature_table.append(_clipboard['features'])

            layer._selected_view = list(
                range(npoints, npoints + len(_clipboard['data']))
            )
            layer._selected_data = set(
                range(totpoints, totpoints + len(_clipboard['data']))
            )

            if len(_clipboard['text']) > 0:
                layer.text.values = np.concatenate(
                    (layer.text.values, _clipboard['text']), axis=0
                )

            layer.refresh()

    def getDataFrame(self, getFull=False) -> pd.DataFrame:
        # getDataFrame
        # TODO (cudmore) add symbol encoding

        df = super().getDataFrame(getFull=getFull)

        if getFull:
            selectedList = list(range(len(self._layer.data)))
        else:
            selectedList = list(self._selected_data)

        # logger.warning(f'selectedList:{selectedList}')

        # now handled by _updateFeatures (only update when needed)
        '''
        # prepend (z,y,x)) columns
        df.insert(0, 'x', self._layer.data[selectedList,2])
        df.insert(0, 'y', self._layer.data[selectedList,1])
        if self._layer.ndim == 3:
            df.insert(0, 'z', self._layer.data[selectedList,0])
        '''

        # abb 202402 we are receiving a list of symbols
        # prepend symbol column
        symbol = self._layer.symbol  # str
        # logger.warning(f'getFull:{getFull} received symbol:{symbol} {type(symbol)}')
        # symbol = str(symbol)  # abb 20240206
        symbol = [SYMBOL_ALIAS[str(_symbol)] for _symbol in symbol]  # abb 202402

        # abb remove 202402
        # try:
        #     symbol = SYMBOL_ALIAS[symbol]
        # except (KeyError) as e:
        #     logger.warning(f'did not find symbol in SYMBOL_ALIAS named "{symbol}"')
        #     symbol = 'X'
        # # this is needed to keep number of rows correct
        # symbolList = [symbol] * len(selectedList)  # data.shape[0]  # make symbols for each point

        # abb 202402 cludge
        #symbolList = [symbol[0]] * len(selectedList)  # data.shape[0]  # make symbols for each point

        symbolList = [symbol[i] for i in selectedList]

        df.insert(loc=0, column='Symbol', value=symbolList)  # insert as first column
        # df.insert(loc=0, column='Symbol', value=symbol)  # insert as first column

        return df

    def addAnnotation(self, coords, event=None, features:dict = None):
        """Add a single annotation to a layer.
        
        Define when deriving. For points layer use 'self._layer.add(cords)'

        Notes:
            Does not seem to be a simple way to add points to existing layer.
            This does not set properties/features correctly
        """
        
        '''
        if event is not None:
            print('calling _points_mouse_bindings()')
            _points_mouse_bindings.add(self._layer, event)
        else:
            self._layer.add(coords)
        '''
        
        #
        # IMPORTANT !!!!
        #
        # do the add (napari), this TRIGGERS
        # add events before it returns
        self._layer.add(coords)  # napari function call

        # point was added and all callbacks responded

        # assign features
        logger.info('assigning features from external return dict')
        addedIdx = self._numItems  # after added
        addedIdx -= 1
        for featureColumn in self._layer.features.columns:
            if featureColumn in features.keys():
                addedFeatureValue = features[featureColumn]
                print(f'      addedIdx:{addedIdx} featureColumn:{featureColumn} addedFeatureValue:{addedFeatureValue}')
                self._layer.features.loc[addedIdx, featureColumn] = addedFeatureValue
            else:
                # _layer has a feature we did not set???
                print(f'  did not find featureColumn:{featureColumn} in added features')
                pass

    def _flashItem(self, selectedRow : int):
        """Flash size/color if selected item to make it visible to user.

        Notes:
            layer.refresh() did not do update, instead we are
            tapping into and refreshing Qt in the event loop with 
                get_app().processEvents()
        """

        # parameter
        # _numFlash = 3
        # _sleep1 = 0.07
        # _sleep2 = 0.04

        # logger.info(f'_numFlash:{_numFlash} _sleep1:{_sleep1} _sleep2:{_sleep2}')

        _origColor = self._layer.face_color[selectedRow].copy()
        _origSize = self._layer.size[selectedRow].copy()
        # _flashColor = [1., 1., 0., 1.]
        # _flashSize = _origSize / 2
        
        # we really need to create a timer object because
        # multiple calls will collide when they overwrite self._flashTimerIteration
        if self._flashTimer is not None and self._flashTimer.isActive():
            logger.warning(f'flash timer was still running')
            return
        
        self._flashTimerInterval = 30  # ms
        self._flashTimerIterations = 6  # must be even
        self._flashTimerIteration = 0

        logger.info(f'{self._flashTimerIterations} iterations at interval {self._flashTimerInterval} ms')

        self._flashTimer = QtCore.QTimer(self)
        self._flashTimer.setInterval(30)  # ms

        _origColor = self._layer.face_color[selectedRow].copy()
        _origSize = self._layer.size[selectedRow].copy()

        _callback = lambda selectedRow=selectedRow, _origColor=_origColor, _origSize=_origSize \
            : self._on_flash_timer(selectedRow, _origColor, _origSize)
        self._flashTimer.timeout.connect(_callback)
        self._flashTimer.start()

    def _on_flash_timer(self, selectedRow, _origColor, _origSize):
        """Called when self.xxx QTimer times out
        """
        doFlash = self._flashTimerIteration % 2 == 0
        
        # logger.info(f'    _flashTimerIteration:{self._flashTimerIteration} doFlash:{doFlash}')

        _flashColor = [1., 1., 0., 1.]
        #_flashSize = _origSize / 2
        _flashSize = _origSize * 3

        # do flash
        if doFlash:
            self._layer.face_color[selectedRow] = _flashColor
            self._layer.size[selectedRow] = _flashSize
            self._layer.refresh()
            get_app().processEvents()
            #time.sleep(_sleep1)
        else:
            self._layer.face_color[selectedRow] = _origColor
            self._layer.size[selectedRow] = _origSize
            self._layer.refresh()
            get_app().processEvents()
            #time.sleep(_sleep2)

        # increment
        self._flashTimerIteration += 1
        if self._flashTimerIteration >= self._flashTimerIterations:
            self._flashTimer.stop()

    def snapToItem(self, selectedRow : int, isAlt : bool =False):
        """Snap viewer to z-Plane of selected row and optionally to (y,x)
        
        Only snap when one row is selected, not multiple.

        Args:
            selectedRow (int): The row to snap to.
            isAlt (bool): If True then center point on (y,x)

        TODO:
            "Setting the camera center also resets the zoom"
            see: https://github.com/napari/napari/issues/3723
            on 20220322, was closed and should be fixed with next version of vispy
            see: https://github.com/vispy/vispy/pull/2312
        """
        isThreeD = self._layer.data.shape[1] == 3
        
        if isThreeD:
            zSlice = self._layer.data[selectedRow][0]  # assuming (z,y,x)
            yPnt = self._layer.data[selectedRow][1]  # assuming (z,y,x)
            xPnt = self._layer.data[selectedRow][2]  # assuming (z,y,x)
            logger.info(f'selectedRow:{selectedRow} zSlice:{zSlice} y:{yPnt} x:{xPnt}')

            # z-Plane
            axis = 0 # assuming (z,y,x)
            self._viewer.dims.set_point(axis, zSlice)

            # (y,x)
            if isAlt:
                self._viewer.camera.center = (zSlice, yPnt, xPnt)
        
        else:
            yPnt = self._layer.data[selectedRow][0]  # assuming (z,y,x)
            xPnt = self._layer.data[selectedRow][1]  # assuming (z,y,x)
            logger.info(f'y:{yPnt} x:{xPnt}')
            if isAlt:
                self._viewer.camera.center = (yPnt, xPnt)

        # flash selection to make it visible to user
        self._flashItem(selectedRow)

    def slot_user_edit_symbol(self, event):
        """Respond to user selecting a new symbol.
        
        Special case, all points in layer have same symbol, 
        need to refresh entire table.
        """

        # TODO (cudmore) add mmLayer.emitChangeAll()
         
        all_selected_data = set(range(self.numItems()))
        
        logger.info(f'-->> emit change with all_selected_data:{all_selected_data}')

        #selected_data2 = self._layer.data
        dfFeatures = self.getDataFrame(getFull=True)

        # TODO (cudmore) we do not want changeSymbol to be part of undo
        self.signalDataChanged.emit('change', all_selected_data,
                            #self._layerSelectionCopy,
                            dict(),
                            dfFeatures)

    def slot_user_edit_size(self, event):
        logger.info('  -->> NOT IMPLEMENTED')

class shapesLayer(mmLayer):
    """
    event.source.mode in:
        'direct': allows for shapes to be selected and their individual vertices to be moved.
        'select': allows for entire shapes to be selected, moved and resized.
        'VERTEX_INSERT': 
        'VERTEX_REMOVE':
    
    shape_type in:
        'path': A list (array) of points making a path
    """
    def __init__(self, viewer, layer, *args, **kwargs):
        super().__init__(viewer, layer, *args, **kwargs)

        self.addFeature('x')
        self.addFeature('y')
        self.addFeature('z')
    
        self._updateFeatures()

    def getDataFrame(self, getFull=False) -> pd.DataFrame:
        # TODO (cudmore) make sure it works for 2d/3d (what about N-Dim ???)

        df = super().getDataFrame(getFull=getFull)

        if getFull:
            selectedList = list(range(len(self._layer.data)))
        else:
            selectedList = list(self._selected_data)
        
        # now handled in _updateFeatures
        # iterate through each shape and calculate (z,y,x)      
        '''
        yMean = [np.mean(self._layer.data[idx][:,1]) for idx in selectedList]
        xMean = [np.mean(self._layer.data[idx][:,2]) for idx in selectedList]
        
        df.insert(0, 'x', xMean)
        df.insert(0, 'y', yMean)
        if self._layer.ndim == 3:
            zMean = [np.mean(self._layer.data[idx][:,0]) for idx in selectedList]
            df.insert(0, 'z', zMean)
        '''

        shape_type = [self._layer.shape_type[idx] for idx in selectedList]        
        df.insert(0, 'Shape Type', shape_type)

        return df

    def _updateFeatures(self, selectedDataSet=None):
        """Update underlying layer features based on selection.
        
        Used in creation and on data move.

        Args:
            selectedDataSet (set) selected data, Pass None to update all.
        """
        if selectedDataSet is None:
            selectedDataSet = set(range(self.numItems()))
        
        selectedList = list(selectedDataSet)

        logger.info(f'{self._derivedClassName()} selectedList:{selectedList}')
        logger.info(f'self._layer.data is:')
        print(self._layer.data)

        if self._layer.ndim == 2:
            yMean = [np.mean(self._layer.data[idx][:,0]) for idx in selectedList]
            xMean = [np.mean(self._layer.data[idx][:,1]) for idx in selectedList]
        
            self._layer.features.loc[selectedList, 'x'] = xMean
            self._layer.features.loc[selectedList, 'y'] = yMean
        
        elif self._layer.ndim >= 3:
            yMean = [np.mean(self._layer.data[idx][:,1]) for idx in selectedList]
            xMean = [np.mean(self._layer.data[idx][:,2]) for idx in selectedList]
        
            self._layer.features.loc[selectedList, 'x'] = xMean
            self._layer.features.loc[selectedList, 'y'] = yMean

            zMean = [np.mean(self._layer.data[idx][:,0]) for idx in selectedList]
            self._layer.features.loc[selectedList, 'z'] = zMean

        else:
            logger.warning(f'Did not update with self._layer.ndim:{self._layer.ndim}')

        print('   now self._layer.features:')
        pprint(self._layer.features)

    def _copy_data(self):
        """Copy selected shapes to clipboard.
        
        Taken from napari.layers.shapes.shapes.py

        This is buggy, depends on napari version !!!
        """
        if len(self.selected_data) > 0:
            layer = self._layer
            index = list(self.selected_data)
            self._layerSelectionCopy = {
                'data': [
                    deepcopy(layer._data_view.shapes[i])
                    for i in layer._selected_data
                ],
                'edge_color': deepcopy(layer._data_view._edge_color[index]),
                'face_color': deepcopy(layer._data_view._face_color[index]),
                'features': deepcopy(layer.features.iloc[index]),
                'indices': layer._slice_indices,
                'text': layer.text._copy(index),  # abb 202402 un-commented
            }
            
            # abb remove 202402
            # if len(layer.text.values) == 0:
            #     self._layerSelectionCopy['text'] = np.empty(0)
            # else:
            #     try:
            #         self._layerSelectionCopy['text'] = deepcopy(layer.text.values[index])
            #     except (IndexError) as e:
            #         logger.error(f'I DO NOT UNDERSTAND HOW TO FIX THIS! {e}')
            #         self._layerSelectionCopy['text'] = np.empty(0)
        else:
            self._layerSelectionCopy = {}

    def _paste_data(self, layerSelectionCopy=None):
        """Paste any shapes from clipboard and then selects them.
        
        Copy of code in napari.layers.shapes.shapes.py
        
        We need to swap self ... for `layer = self._layer``

        Notes:
            This is very complicated, will break on napari updates.
            Hard to unit test.
        """
        layer = self._layer  # replaces self.
        if layerSelectionCopy is None:
            _clipboard = self._layerSelectionCopy
        else:
            _clipboard = layerSelectionCopy

        cur_shapes = layer.nshapes
        if len(_clipboard.keys()) > 0:
            # Calculate offset based on dimension shifts
            offset = [
                layer._slice_indices[i] - _clipboard['indices'][i]
                for i in layer._dims_not_displayed
            ]

            layer._feature_table.append(_clipboard['features'])

            # Add new shape data
            for i, s in enumerate(_clipboard['data']):
                shape = deepcopy(s)
                data = copy(shape.data)
                data[:, layer._dims_not_displayed] = data[
                    :, layer._dims_not_displayed
                ] + np.array(offset)
                shape.data = data
                face_color = _clipboard['face_color'][i]
                edge_color = _clipboard['edge_color'][i]
                layer._data_view.add(
                    shape, face_color=face_color, edge_color=edge_color
                )

            if len(_clipboard['text']) > 0:
                layer.text.values = np.concatenate(
                    (layer.text.values, _clipboard['text']), axis=0
                )

            layer.selected_data = set(
                range(cur_shapes, cur_shapes + len(_clipboard['data']))
            )

            layer.move_to_front()

    def slot_user_edit_data(self, event):        
        super().slot_user_edit_data(event)
        #logger.info('shapesLayer')
        #self._printEventState(event)

    def _printEventState(self, event):
        print('    === _printEventState()')
        print('      event.source.mode:', event.source.mode)
        print('      event.source.selected_data:', event.source.selected_data)
        print('      len(event.source.data):', len(event.source.data))
        print('      self.numItems():', self.numItems())
        print('      self._selected_data:', self._selected_data)
        #print('      self._selected_data2:', self._selected_data2)

    def addShapes(self, data, shape_type):
        #if not isinstance(shape_type, list):
        #    shape_type = [shape_type]
        
        #print('shapeLayer.addShapes()')
        #print('  data:', type(data))
        #print('  shape_type:', shape_type)
        if shape_type == 'polygon':
            self._layer.add_polygons(data)
        elif shape_type == 'path':
            self._layer.add_paths(data)

class shapesPathLayer(shapesLayer):
    def __init__(self, viewer, layer):
        super().__init__(viewer, layer)

    def addPath(self, data):
        shape_type = 'path'
        self.addShapes(data, shape_type)

    def addAnnotation(self, coords, event = None):
        if event is not None:
            print('calling _shapes_mouse_bindings()')
            
            # oct 17, was this
            # _shapes_mouse_bindings.vertex_insert(self._layer, event)

# AttributeError: 'Labels' object has no attribute 'selected_data'
#class labelLayer(mmLayer):
# label layer (napari) is derived from self._layer.events
class labelLayer(QtCore.QObject):

    # Note: these have to be kept in sync with mmLayer signals
    signalDataChanged = QtCore.Signal(object, object, object, pd.DataFrame)
    # action'
    # selected set
    # selected data : not used
    # selected df
    
    signalLayerNameChange = QtCore.Signal(str)

    def __init__(self, viewer, layer,
                        onAddCallback=None,
                        onDeleteCallback=None,):
        """
        Args:
            onAddCallback: not implemented
            onDeleteCallback: not implemented
        """
        #super().__init__(viewer, layer)
        super().__init__()

        self._viewer = viewer
        self._layer = layer

        # for label layer, this is an integer (not a set)
        self._selected_label = self._layer.selected_label

        # just show one selected label (hide all others)
        #self._layer.show_selected_label = True
        
        self._connectLayer()

    def bringToFront(self):
        if self._viewer.layers.selection.active != self._layer:
            self._viewer.layers.selection.active = self._layer

    def getName(self):
        return self._layer.name

    def _copy_data(self):
        logger.info('labelLayer NOT IMPLEMENTED')

    def slot_selected_label(self, event):
        """Respond to user setting label in viewer.
        """
        logger.info('labelLayer')
        selected_label = self._layer.selected_label # int
        
        if selected_label == self._selected_label:
            print('  no new label selection')
            return

        self._selected_label = selected_label
        print('  _selected_label:', self._selected_label)
        
        #properties = self.getDataFrame()

        #print('  properties:')
        #pprint(properties)

        '''
        print('  event.source', event.source)  # same as self._layer
        print('  event.type', event.type)
        print('  selected_label:', self._layer.selected_label)
        print('  event.source.selected_label:', event.source.selected_label)
        '''

        self._selected_label = event.source._selected_label  # int

        properties = self.getDataFrame()
        print('  -->> emit "select"')
        # in label layer we will only every select one label
        # signal/slot expects a list
        selectedLabelList = [self._selected_label]
        emptyDict = dict()
        self.signalDataChanged.emit('select', selectedLabelList, emptyDict, properties)

        #_vars = vars(event)
        #pprint(_vars)

    def getDataFrame_all(self) -> pd.DataFrame:
        # TODO (cudmore) this does not work !!!
        logger.info('label layer')
        return self.getDataFrame(getFull=True)

    def getDataFrame(self, getFull=False) -> pd.DataFrame:
        # self._layer.features gives us a (features, properties) pandas dataframe !!!
        
        logger.info(f'label layer getFull:{getFull}')

        dfFeatures = self._layer.features  # all features

        if getFull:
            #selectedList = range(len(self._layer.data))
            # TODO (cudmore) consider keeeping track of this as a member _numLabels
            selectedList = np.unique(self._layer.data).tolist()  # list
        else:
            selectedList = [self._selected_label]  # int

        # label index is 1 based, add one to list
        # TODO (cudmore) our data model does not work with row labels 1,2,3,...
        #  it s expecting row index 0 to be preesent
        #  need to switch over all .iLoc[] to .loc[] or similar
        '''
        if selectedList:
            selectedList = selectedList[0:-1]
            selectedList = [index+1 for index in selectedList]
        '''
        # drop 0 from list
        zeroIndex = selectedList.index(0)
        if zeroIndex is not None:
            logger.info('removing 0 from list, label layer starts at 1')
            del selectedList[zeroIndex]

        #print('  selectedList:', selectedList)
        #print('  dfFeatures:')
        #pprint(dfFeatures)

        if len(dfFeatures) == 0:
            dfFeatures = pd.DataFrame(index=selectedList)
        
        # reduce by selection
        df = dfFeatures.loc[selectedList]

        df.loc[selectedList, "label"] = selectedList

        # TODO (cudmore) add z/y/x as mean of pixels in label
        
        # TODO (cudmore add color with layer get_color(idx) as 'Face Color'
        colorList_rgba = [self._layer.get_color(index)
                        for index in selectedList]
        
        if selectedList:
            colorList_rgba[0] = (1., 1., 1., 1.)  # index 0 is not actually a label (it selects all)
        # use str(rgb_to_hex(oneColor)[0])
        colorList_hex = [str(rgb_to_hex(oneColor)[0])
                        for oneColor in colorList_rgba]

        #print('  colorList_hex:', colorList_hex)
        df.loc[selectedList, "Face Color"] = colorList_hex

        # abb cudmore baltimore, adding region props to table
        # Note: region props does not return row 0
        _properties = ['label', 'centroid', 'area']  # 'solidity' gives convex-hull error
        props_dict = regionprops_table(self._layer.data, properties=_properties)
        dfProps = pd.DataFrame(props_dict)
        # rename some columns
        dfProps = dfProps.rename(columns={'centroid-0': 'z', 'centroid-1': 'y', 'centroid-2': 'z'})

        #print('df:')
        #pprint(df)

        return df

    def slot_user_edit_name(self, event):
        logger.info('')
        #newName = self._layer.name
        newName = event.source.name
        self.signalLayerNameChange.emit(newName)

    def _connectLayer(self, layer=None):
        self._layer.events.name.connect(self.slot_user_edit_name)
        self._layer.events.selected_label.connect(self.slot_selected_label)


    def selectItems(self, selectedRowSet : set):
        """Set the selected items in layer.
        
        Called from _my_widget on user selectnig row(s) in table
        """
        #self._layer.selected_data = selectedRowSet
        selectedRowList = list(selectedRowSet)
        if selectedRowList:
            selectedRow = selectedRowList[0]
            logger.info(f'labelLayer selectedRow: {selectedRow}')
            self._layer.selected_label = selectedRow

    def snapToItem(self, selectedRow : int, isAlt : bool =False):
        pass

    def doUndo(self):
        #self._undo.doUndo()
        pass