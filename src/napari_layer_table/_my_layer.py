"""
"""
from pprint import pprint

import numpy as np
import pandas as pd

# turn off pandas warning
# no longer needed, in general all pandas 'cells' have to be scalar
# this was needed when we were assigning a list for (r,g,b,a), now using #RRGGBBAA
# see: https://stackoverflow.com/questions/20625582/how-to-deal-with-settingwithcopywarning-in-pandas
# for a way to temporarily turn it off using 'with'
# pd.options.mode.chained_assignment = None

from qtpy import QtCore

#from napari.layers.points import _points_mouse_bindings  # import add, highlight, select
from napari.layers.shapes import _shapes_mouse_bindings  #vertex_insert
from napari.layers.utils.layer_utils import features_to_pandas_dataframe

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
    'cross': '\u271A',
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
    signalDataChanged = QtCore.Signal(object, object, object, pd.DataFrame)
    signalLayerNameChange = QtCore.Signal(str)

    def __init__(self, viewer, layer):
        super().__init__()
        
        self._viewer = viewer
        self._layer = layer
        
        self._shift_click_for_new = False

        self._onlyOneLayer = True

        #self._blockOnAdd = False

        self._selected_data = layer.selected_data
        if list(self._selected_data):
            self._selected_data2 = layer.data[self._selected_data]
        else:
            # TODO (cudmore) can we initialize with None ???
            self._selected_data2 = np.ndarray([])
        
        self._numItems = len(layer.data)

        self._connectLayer()

        # slots to detect a change in layer selection
        self._viewer.layers.events.inserting.connect(self.slot_insert_layer)
        self._viewer.layers.events.inserted.connect(self.slot_insert_layer)
        self._viewer.layers.events.removed.connect(self.slot_remove_layer)
        self._viewer.layers.events.removing.connect(self.slot_remove_layer)

        self._viewer.layers.selection.events.changed.connect(self.slot_select_layer)

        # todo (cudmore)
        #self._undo = mmUndo(self)
        #self.signalDataChanged.connect(self._undo.slot_change)

    def doUndo(self):
        self._undo.doUndo()

    def snapToItem(self, selectedRow : int, isAlt : bool =False):
        pass

    def bringToFront(self):
        if self._viewer.layers.selection.active != self._layer:
            self._viewer.layers.selection.active = self._layer

    def getName(self):
        return self._layer.name
    
    def numItems(self):
        return self._numItems
        
    def selectItems(self, selectedRowSet : set):
        """Set the selected items in layer.
        
        Called from _my_widget on user selectnig row(s) in table
        """
        self._layer.selected_data = selectedRowSet

    def _connectLayer(self, layer=None):
        
        self._layer.events.name.connect(self.slot_user_edit_name)
        self._layer.events.highlight.connect(self.slot_user_edit_highlight)
        self._layer.events.data.connect(self.slot_user_edit_data)

        self._layer.events.features.connect(self.slot_user_edit_features)

        # we want to receive an event when user sets the face color of (points, shapes)
        # this does not trigger?
        self._layer.events.face_color.connect(self.slot_user_edit_face_color)
        # this triggers but only for points layer
        #self._layer._face.events.current_color.connect(self.slot_user_edit_face_color)
        
        # want to use this, only triggers for shapes layer
        #self._layer.events.current_face_color.connect(self.slot_user_edit_face_color)

        # this is never called, not sure if it even triggers
        self._layer.events.properties.connect(self.slot_user_edit_properties)

    def _updateMouseCallbacks(self, on = None):
        """Enable/disable shift+click for new points.
        """
        if on is not None:
            self._shift_click_for_new = on
        
        if self._shift_click_for_new:
            self._layer.mouse_drag_callbacks.append(self._on_mouse_drag)
        else:
            try:
                self._layer.mouse_drag_callbacks.remove(self._on_mouse_drag)
            except (ValueError) as e:
                # not in list
                pass
            
    def _on_mouse_drag(self, layer, event):
        """Handle user mouse-clicks. Intercept shift+click to make a new point.

        Will only be called when install in _updateMouseCallbacks().
        """
        if 'Shift' in event.modifiers:
            # make a new point at cursor position
            data_coordinates = self._layer.world_to_data(event.position)
            # always add as integer pixels (not fractional/float pixels)
            cords = np.round(data_coordinates).astype(int)
            
            # add to layer, only for points layer?
            # for shape layer type 'path', use add_paths()
            # self._layer.add(cords)
            self.addAnnotation(cords, event)

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

    def addAnnotation(self, coords, event = None):
        """Add an annotation to a layer.
        
        Define when deriving. For points layer use 'self._layer.add(cords)'
       
        Args:
            coords:
            event: napari mouse down event
        """
        pass

    def old_slot_select_layer(self, event):
        """Respond to change in layer selection in viewer.
        
        Args:
            event (Event): event.type == 'changed'
        """
        print(f'slot_select_layer() event.type: {event.type}')


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

        #print('\n\n')
        #logger.info(self._derivedClassName())
        #print('  event.source.selected_data:', event.source.selected_data)
        #print('  self._selected_data:', self._selected_data)

        newSelection = not setsAreEqual(event.source.selected_data, self._selected_data)

        action = 'none'
        if len(event.source.data) > self.numItems():
            # add an item: for points layer is point, for shapes layer is shape
            # event.source.selected_data gives us the added points
            # for shape layer, *this is called multiple tmes without the added items selected
            if newSelection:
                action = 'add'
        elif len(event.source.data) < self.numItems():
            # event.source.selected_data tells us the rows
            # THEY NO LONGER EXIST
            # our current/previous self._selected_data tells us the rows
            action = 'delete'
            #_deleted_selected_data = event.source.selected_data.copy()
        elif newSelection:
            action = 'select'
            
        # signal what changed
        if action == 'add':
            self._selected_data = event.source.selected_data
            self._numItems = len(event.source.data)

            # TODO (cudmore) event.source.data is sometimes a list?
            # Rely on np.ndarray cast from list
            selected_data_list = list(self._selected_data)

            self._selected_data2 = np.take(event.source.data, selected_data_list, axis=0)

            properties = self.getDataFrame()
            print('  -->> emit "select"')
            self.signalDataChanged.emit('add', self._selected_data, self._selected_data2, properties)

        elif action == 'delete':
            # deleted data indices were _deleted_selected_data
            delete_selected_data = self._selected_data.copy()
            delete_selected_data2 = self._selected_data2.copy()
            self._selected_data = set()
            self._selected_data2 = np.ndarray([])
            self._numItems = len(event.source.data)
            print('  -->> emit "delete"')
            self.signalDataChanged.emit('delete', delete_selected_data, delete_selected_data2, pd.DataFrame())
        
        elif action == 'select':
            self._selected_data = event.source.selected_data
            selectedDataList = list(self._selected_data)
            self._selected_data2 = np.take(event.source.data, selectedDataList, axis=0)
            properties = self.getDataFrame()
            print('  -->> emit "select"')
            self.signalDataChanged.emit('select', self._selected_data, self._selected_data2, properties)

    def slot_user_edit_data(self, event):
        """User edited a point in the current layer.
        
        This is generated when user finishes a click+drag.
                
        Notes:
            On key-press (like delete), we need to ignore event.source.mode
        """

        '''
        action = 'none'
        if len(event.source.data) > self.numItems():
            action = 'add'
        elif len(event.source.data) < self.numItems():
            action = 'delete'
            #_deleted_selected_data = event.source.selected_data.deepcopy()

        logger.info('')
        print('    not respondng to action:', action)
        '''

        properties = self.getDataFrame()
        print('  -->> emit signalDataChanged "change" with')
        print('    self._selected_data:', self._selected_data)
        print('    self._selected_data2:', self._selected_data2)
        #print('    properties:', properties)

        self.signalDataChanged.emit('change', self._selected_data, self._selected_data2, properties)

    def slot_user_edit_face_color(self, event):
        """User selected a face color.
        
        Change the face color of selected points.

        Note:
            - Using hex #RRGGBBAA
            - QColor takes #AARRGGBB, see _data_model.data (QtCore.Qt.ForegroundRole)
        """
        if self._selected_data:
                       
            current_face_color = self._layer.current_face_color  # hex

            logger.info(f'current_face_color:{current_face_color}')

            properties = self.getDataFrame()

            index = list(self._selected_data)
            properties.loc[index, 'Face Color'] = current_face_color
            
            #for oneRowIndex in index:
            #    properties.loc[oneRowIndex, 'Face Color'] = current_face_color

            self.signalDataChanged.emit('change', self._selected_data, self._selected_data2, properties)

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
    def __init__(self, viewer, layer):

        super().__init__(viewer, layer)

    def _connectLayer(self, layer=None):
        
        super()._connectLayer()

        # this triggers but only for points layer
        self._layer._face.events.current_color.connect(self.slot_user_edit_face_color)

        self._layer.events.symbol.connect(self.slot_user_edit_symbol)  # points layer
        self._layer.events.size.connect(self.slot_user_edit_size)  # points layer

    def getDataFrame(self, getFull=False) -> pd.DataFrame:
        # getDataFrame
        # TODO (cudmore) add symbol encoding

        df = super().getDataFrame(getFull=getFull)

        if getFull:
            selectedList = list(range(len(self._layer.data)))
        else:
            selectedList = list(self._selected_data)

        # prepend (z,y,x)) columns
        df.insert(0, 'x', self._layer.data[selectedList,2])
        df.insert(0, 'y', self._layer.data[selectedList,1])
        if self._layer.ndim == 3:
            df.insert(0, 'z', self._layer.data[selectedList,0])

        # prepend symbol column
        symbol = self._layer.symbol  # str
        try:
            symbol = SYMBOL_ALIAS[symbol]
        except (KeyError) as e:
            logger.warning(f'did not find symbol in SYMBOL_ALIAS named "{symbol}"')
            symbol = 'X'
        # this is needed to keep number of rows correct
        symbolList = [symbol] * len(selectedList)  # data.shape[0]  # make symbols for each point
        df.insert(loc=0, column='Symbol', value=symbolList)  # insert as first column

        return df

    def addAnnotation(self, coords, event=None):
        """Add an annotation to a layer.
        
        Define when deriving. For points layer use 'self._layer.add(cords)'
        """
        
        '''
        if event is not None:
            print('calling _points_mouse_bindings()')
            _points_mouse_bindings.add(self._layer, event)
        else:
            self._layer.add(coords)
        '''
        self._layer.add(coords)

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
            logger.info(f'zSlice:{zSlice} y:{yPnt} x:{xPnt}')

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

    def slot_user_edit_symbol(self, event):
        """Respond to user selecting a new symbol.
        
        All points in layer have same symbol, need to refresh entire table.
        """
        logger.info('slot_user_edit_symbol() -->> emit')

        # TODO (cudmore) add mmLayer.emitChangeAll()
         
        selected_data = list(range(self.numItems()))
        selected_data2 = self._layer.data
        df = self.getDataFrame_all()
        
        print('  selected_data:', selected_data)
        print('  selected_data2:', selected_data2)
        print('  df:')
        pprint(df)

        self.signalDataChanged.emit('change', selected_data, selected_data2, df)

    def slot_user_edit_size(self, event):
        print('slot_user_edit_size()')

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
    def __init__(self, viewer, layer):
        super().__init__(viewer, layer)

        #self._undo = mmUndo(self)

    def getDataFrame(self, getFull=False) -> pd.DataFrame:
        # TODO (cudmore) make sure it works for 2d/3d (what about N-Dim ???)

        df = super().getDataFrame(getFull=getFull)

        if getFull:
            selectedList = list(range(len(self._layer.data)))
        else:
            selectedList = list(self._selected_data)
        
        # iterate through each shape and calculate (z,y,x)      
        yMean = [np.mean(self._layer.data[idx][:,1]) for idx in selectedList]
        xMean = [np.mean(self._layer.data[idx][:,2]) for idx in selectedList]
        
        df.insert(0, 'x', xMean)
        df.insert(0, 'y', yMean)
        if self._layer.ndim == 3:
            zMean = [np.mean(self._layer.data[idx][:,0]) for idx in selectedList]
            df.insert(0, 'z', zMean)

        shape_type = [self._layer.shape_type[idx] for idx in selectedList]        
        df.insert(0, 'Shape Type', shape_type)

        return df

    def slot_user_edit_highlight(self, event):
        """
        1) This is triggered when user selects 'mode'
        """
        
        super().slot_user_edit_highlight(event)
        return

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
        print('      self._selected_data2:', self._selected_data2)

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
            _shapes_mouse_bindings.vertex_insert(self._layer, event)

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

    def __init__(self, viewer, layer):
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
        self.signalDataChanged.emit('select', selectedLabelList, None, properties)

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

        print('  selectedList:', selectedList)
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

        print('  colorList_hex:', colorList_hex)
        df.loc[selectedList, "Face Color"] = colorList_hex

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