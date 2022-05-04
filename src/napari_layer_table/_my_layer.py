"""
"""

from pprint import pprint
#from tkinter.messagebox import showinfo

import numpy as np
import pandas as pd

from qtpy import QtCore

import napari

#from napari.layers.points import _points_mouse_bindings  # import add, highlight, select
from napari.layers.shapes import _shapes_mouse_bindings  #vertex_insert

from napari_layer_table._my_logger import logger

# TODO (cudmore) put this in a _tils.py file (used by miltiple files)
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

        #self._blockOnAdd = False

        self._selected_data = layer.selected_data
        if list(self._selected_data):
            self._selected_data2 = layer.data[self._selected_data]
        else:
            self._selected_data2 = None
        
        self._numItems = len(layer.data)

        self._connectLayer()

    def snapToItem(self, selectedRow : int, isAlt : bool =False):
        pass

    def bringToFront(self):
        if self._viewer.layers.selection.active != self._layer:
            self._viewer.layers.selection.active = self._layer

    def numItems(self):
        return self._numItems
        
    def getLayer(self):
        return self._layer

    def getSelection(self):
        return self._selected_data

    def numItems(self):
        #return len(self._layer.data)
        return self._numItems

    def removeSelected(self):
        """Remove/delete selected items from layer.
        """
        self._layer.remove_selected()

    def selectItems(self, selectedRowSet : set):
        self._layer.selected_data = selectedRowSet

    def _connectLayer(self, layer=None):
        
        self._layer.events.name.connect(self.slot_user_edit_name)
        self._layer.events.highlight.connect(self.slot_user_edit_highlight)
        self._layer.events.data.connect(self.slot_user_edit_data)

        self._layer.events.features.connect(self.slot_user_edit_features)

        # this does not trigger? Is not included in label layer
        self._layer.events.face_color.connect(self.slot_user_edit_face_color)
        
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
    
    def addAnnotation(self, coords, event = None):
        """Add an annotation to a layer.
        
        Define when deriving. For points layer use 'self._layer.add(cords)'
       
        Args:
            coords:
            event: napari mouse down event
        """
        pass

    def slot_select_layer(self, event):
        """Respond to change in layer selection in viewer.
        
        Args:
            event (Event): event.type == 'changed'
        """
        print(f'slot_select_layer() event.type: {event.type}')


    def getLayerDataFrame(self) -> pd.DataFrame:
        #logger.info('')
        return self._getSelectedProperties(getFull=True)

    def _getSelectedProperties(self, getFull=False) -> pd.DataFrame:
        # self._layer.features gives us a (features, properties) pandas dataframe !!!
        
        dfFeatures = self._layer.features  # all features

        if getFull:
            selectedList = range(len(self._layer.data))
        else:
            selectedList = self._selected_data

        # reduce by selection
        df = dfFeatures.iloc[list(selectedList)]

        return df

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

        #if 'Shift' in event.modifiers:
        #    print('slot_user_edit_highlight() return on shift')
        #    return

        action = None
        
        #logger.info('')
        #print('  len(event.source.data):', len(event.source.data))
        #print('  self.numItems():', self.numItems())

        if len(event.source.data) > self.numItems():
            # add an object/annotation for points layer is point, for shapes layer is shape
            # event.source.selected_data gives us the added points
            # crap (cudmore) on add in shape layer selected_data is not valid !!!!!!!!!!
            action = 'add'
            #print(f'  add event.source.selected_data: {event.source.selected_data}')
            #print(f'    layer name: "{event.source.name}"')
        elif len(event.source.data) < self.numItems():
            # event.source.selected_data tells us the rows
            # THEY NO LONGER EXIST
            # our current/previous self._selected_data tells us the rows
            action = 'delete'
            #_deleted_selected_data = self._selected_data
            _deleted_selected_data = event.source.selected_data.copy()
            #print(f'  delete self._selected_data:', self._selected_data)
            #print(f'    {event.source.name}')
            #print('*** on delete event.source.selected_data is :', event.source.selected_data)
        else:
            # both (update selection, move)
            if np.array_equal(self._selected_data, event.source.selected_data):
                # data may have changed
                selected_data_list = list(event.source.selected_data)
                # see 'error' above
                if isinstance(event.source.data, list):
                    tmp0 = np.array(event.source.data, dtype=object)
                else:
                    tmp0 = event.source.data
                tmp = np.take(tmp0, selected_data_list, axis=0)
                if not np.array_equal(self._selected_data2, tmp):
                    action = 'change'
                    #print(f'!!! data changed for object index: {event.source.selected_data}')
                    #print('  ', tmp)
            else:
                action = 'select'
            
            '''
            else:
                # new selection
                # if we have a current selection, check our _selected_data2 matches the layer data
                # this will take into account creating (polygon, path)
                # when user terminates with esc, we loose last point
                
                action = 'select'
                #print(f'  select event.source.selected_data:', event.source.selected_data)
                #print(f'    {event.source.name}')

                # transform 'select' into 'change'
                # ... SUPER COMPLICATED !!!
                selected_data_list = list(event.source.selected_data)
                # see 'error' above
                if isinstance(event.source.data, list):
                    tmp0 = np.array(event.source.data, dtype=object)
                else:
                    tmp0 = event.source.data
                tmp = np.take(tmp0, selected_data_list, axis=0)
                if not np.array_equal(self._selected_data2, tmp):
                    action = 'change'
                    print('TRANSFORMING "select" to "change"')
                    # event.source.selected_data is empty
                    print('  event.source.selected_data:', event.source.selected_data)  # EMPTY
                    print(f'  _selected_data: {self._selected_data}')
                    # _selected_data2 is out of date (one too many points)
                    print(f'  _selected_data2: {self._selected_data2}')
                    print('SELECTED DATA IS OUT OF SYNC ... one to many points ... should be')
                    #print(tmp0)
                    tmpSelectedDataList = list(self._selected_data)
                    tmp999 = np.take(tmp0, tmpSelectedDataList, axis=0)
                    print('tmp999')
                    print(tmp999)
                    self._selected_data2 = tmp999
            '''

        # on 'delete', selected_data is no longer valid, was deleted
        if action == 'delete':
            self._selected_data = set()
        else:
            self._selected_data = event.source.selected_data.copy()
        
        # see 'error' above
        #selected_data_list = list(event.source.selected_data)
        selected_data_list = list(self._selected_data)
        #print('*** selected_data_list is now:', selected_data_list)
        if isinstance(event.source.data, list):
            tmp0 = np.array(event.source.data, dtype=object)
        else:
            tmp0 = event.source.data
        self._selected_data2 = np.take(tmp0, selected_data_list, axis=0)

        # here data is not changing, only selection
        #self._data = event.source.data.copy()
        self._numItems = len(event.source.data)

        # signal what changed, try not to signal during dynamic user interaction ???
        if action == 'add':
            # added data indices are self._selected_data
            # added data is self._selected_data2
            #self._blockOnAdd = True
            print('         !!!!!!!!!!emit add', self._selected_data)
            print('         event.source.selected_data:', event.source.selected_data)

            properties = self._getSelectedProperties()
            self.signalDataChanged.emit('add', self._selected_data, self._selected_data2, properties)
            #self._blockOnAdd = False

        elif action == 'delete':
            # deleted data indices were _deleted_selected_data
            self.signalDataChanged.emit('delete', _deleted_selected_data, None, pd.DataFrame())
        elif action == 'change':
            # changed indices are self._selected_data
            # changed data is self._selected_data2
            # handled by slot_user_edit_data
            pass
            # self.signalDataChanged.emit('change', self._selected_data, self._selected_data2)
        elif action == 'select':
            properties = self._getSelectedProperties()
            print('    emit "select"')
            print('      self._selected_data:', self._selected_data)
            self.signalDataChanged.emit('select', self._selected_data, self._selected_data2, properties)
        #self.printEvent(event)

    def slot_user_edit_data(self, event):
        """User edited a point in the current layer.
        
        move:
                
        Notes:
            On key-press (like delete), we need to ignore event.source.mode
        """
        
        # this is actually useful to signal the end of a click+drag (rather than continuous updates)
        
        '''
        print('\n=== slot_user_edit_data()')
        print('event.source.selected_data:', event.source.selected_data)
        pprint(event.source.data)
        print('')
        '''
        
        #if self._blockOnAdd:
        #    return
        
        action = 'none'
        if len(event.source.data) > self.numItems():
            action = 'add'
        elif len(event.source.data) < self.numItems():
            action = 'delete'
            _deleted_selected_data = event.source.selected_data.copy()

        logger.info('')
        print('    local action:', action)

        #properties = event.source.properties
        properties = self._getSelectedProperties()
        print('  emit "change" with')
        print('    self._selected_data:', self._selected_data)
        print('    self._selected_data2:', self._selected_data2)
        print('    properties:', properties)

        self.signalDataChanged.emit('change', self._selected_data, self._selected_data2, properties)

    def slot_user_edit_face_color(self, event):
        print('slot_user_edit_face_color()')

    def slot_user_edit_name(self, event):
        print('slot_user_edit_name()')
        #newName = self._layer.name
        newName = event.source.name
        self.signalLayerNameChange.emit(newName)

    def slot_user_edit_properties(self, event):
        logger.info('')

    def slot_user_edit_features(self, event):
        logger.info('')

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
        
        self._layer.events.symbol.connect(self.slot_user_edit_symbol)  # points layer
        self._layer.events.size.connect(self.slot_user_edit_size)  # points layer

    def _getSelectedProperties(self, getFull=False) -> pd.DataFrame:
        df = super()._getSelectedProperties(getFull=getFull)

        if getFull:
            selectedList = range(len(self._layer.data))
        else:
            selectedList = list(self._selected_data)

        # prepend point layer columns
        df.insert(0, 'x', self._layer.data[selectedList,2])
        df.insert(0, 'y', self._layer.data[selectedList,1])
        df.insert(0, 'z', self._layer.data[selectedList,0])

        # TODO: add symbol encoding
              
        logger.info('NEED TO USE iLoc[] ???')
        '''
        pprint(df)
        print('tmp:', self._layer.face_color[selectedList,:])

        tmpColor = [oneColor.tolist() for oneColor in self._layer.face_color[selectedList]]		
        df['face_color'] = tmpColor
        '''

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
        print('slot_user_edit_symbol()')

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

    def _getSelectedProperties(self, getFull=False) -> pd.DataFrame:
        df = super()._getSelectedProperties(getFull=getFull)

        if getFull:
            selectedList = range(len(self._layer.data))
        else:
            selectedList = list(self._selected_data)

        logger.info('shapesLayer')
        
        shape_type = [self._layer.shape_type[idx] for idx in selectedList]        
        df.loc[selectedList, 'Shape Type'] = shape_type

        # TODO (cudmore) iterate through each shape and (depending on shape_tye) calculate (z,y,x)
        # for most shapes these are the mean across each dimension
        
        # TODO (cudmore) make sure it works for 2d/3d (what about N-Dim ???)

        '''
        print('selectedList:', selectedList)
        print(self._layer.data)
        if len(self._layer.data) > 0:
            print(self._layer.data[0].shape)
            print(type(self._layer.data[0]))
            print(self._layer.data[0])
            print(self._layer.data[0][:,0])
        '''
        zMean = [np.mean(self._layer.data[idx][:,0]) for idx in selectedList]
        yMean = [np.mean(self._layer.data[idx][:,1]) for idx in selectedList]
        xMean = [np.mean(self._layer.data[idx][:,2]) for idx in selectedList]
        
        print('zMean:', zMean)
        df.loc[selectedList, 'z'] = zMean
        df.loc[selectedList, 'y'] = yMean
        df.loc[selectedList, 'x'] = xMean

        # TODO (cudmore) I do not understand how to do this !!!
        '''
        tmpColor = [oneColor for oneColor in self._layer.face_color[selectedList]]		
        print('selectedList:', selectedList)
        print('tmpColor:')
        print(tmpColor)
        df.loc[selectedList, 'face_color'] = tmpColor
        '''
        for oneIdx in selectedList:
            print('oneIdx:', oneIdx)
            oneColor = self._layer.face_color[oneIdx]
            oneColor = oneColor.tolist()
            print(oneIdx, oneColor)
            df.at[oneIdx, 'face_color'] = oneColor

        return df

    def slot_user_edit_highlight(self, event):
        """
        1) This is triggered when user selects 'mode'
        """
        
        #logger.info('shapesLayer')
        #self._printEventState(event)

        newSelection = not setsAreEqual(event.source.selected_data, self._selected_data)

        action = 'none'
        if len(event.source.data) > self.numItems():
            if newSelection:
                action = 'add'
        elif len(event.source.data) < self.numItems():
            action = 'delete'
        elif newSelection:
            action = 'select'
 
        if action=='add':
            print('      -->> ADD NEW ITEM')
            self._selected_data = event.source.selected_data
            self._numItems = len(event.source.data)

            selected_data_list = list(self._selected_data)
            if isinstance(event.source.data, list):
                tmp0 = np.array(event.source.data, dtype=object)
            else:
                tmp0 = event.source.data
            self._selected_data2 = np.take(tmp0, selected_data_list, axis=0)

            properties = self._getSelectedProperties()
            
            print('        -->> emit "add" with:')
            print('        self._selected_data:', self._selected_data)
            print('        self._selected_data2:', self._selected_data2)
            print('        properties:', properties)
            self.signalDataChanged.emit('add', self._selected_data, self._selected_data2, properties)
        
        elif action == 'delete':
            print('      -->> emit "delete" with')
            print('        self._selected_data:', self._selected_data)
            #self.signalDataChanged.emit('delete', _deleted_selected_data, None, pd.DataFrame())
            delete_selected_data = self._selected_data.copy()
            self._selected_data = set()
            self._selected_data2 = None
            self.signalDataChanged.emit('delete', delete_selected_data, None, pd.DataFrame())

        elif action == 'select':
            self._selected_data = event.source.selected_data
            self._selected_data2 = self._getSelectedData2(event)
            properties = self._getSelectedProperties()
 
            print('      -->> emit "select" with')
            print('        self._selected_data:', self._selected_data)
            print('        self._selected_data2:', self._selected_data2)
            print('        properties:', properties)
            self.signalDataChanged.emit('select', self._selected_data, self._selected_data2, properties)

    def slot_user_edit_data(self, event):        
        super().slot_user_edit_data(event)
        #logger.info('shapesLayer')
        #self._printEventState(event)

    def _getSelectedData2(self, event):
        """Get the data from our current selection.
        """
        selected_data_list = list(self._selected_data)
        if isinstance(event.source.data, list):
            tmp0 = np.array(event.source.data, dtype=object)
        else:
            tmp0 = event.source.data
        _selected_data2 = np.take(tmp0, selected_data_list, axis=0)
        return _selected_data2

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
        layer = self.getLayer()
        if shape_type == 'polygon':
            layer.add_polygons(data)
        elif shape_type == 'path':
            layer.add_paths(data)

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
    signalLayerNameChange = QtCore.Signal(str)

    def __init__(self, viewer, layer):
        #super().__init__(viewer, layer)
        super().__init__()

        self._viewer = viewer
        self._layer = layer

        self._selected_label = self._layer.selected_label

        # just show one selected label (hide all others)
        #self._layer.show_selected_label = True
        
        self._connectLayer()

    def slot_selected_label(self, event):
        logger.info('')
        selected_label = self._layer.selected_label
        #if selected_label != self._selected_label:
        #   print('  new label selection')
        self._selected_label = selected_label
        print('  _selected_label:', self._selected_label)
        
        properties = self._getSelectedProperties()

        print('  properties:')
        pprint(properties)

        '''
        print('  event.source', event.source)  # same as self._layer
        print('  event.type', event.type)
        print('  selected_label:', self._layer.selected_label)
        print('  event.source.selected_label:', event.source.selected_label)
        '''

        #_vars = vars(event)
        #pprint(_vars)

    def getLayerDataFrame(self) -> pd.DataFrame:
        logger.info('label layer')
        return self._getSelectedProperties(getFull=True)

    def _getSelectedProperties(self, getFull=False) -> pd.DataFrame:
        # self._layer.features gives us a (features, properties) pandas dataframe !!!

        logger.info('label layer')

        dfFeatures = self._layer.features  # all features

        if getFull:
            #selectedList = range(len(self._layer.data))
            # TODO (cudmore) consider keeeping track of this as a member _numLabels
            selectedList = np.unique(self._layer.data)
        else:
            selectedList = self._selected_data

        print('  selectedList:', selectedList)
        print('  dfFeatures:')
        pprint(dfFeatures)

        # reduce by selection
        df = dfFeatures
        #df = dfFeatures.iloc[list(selectedList)]

        return df

    def slot_user_edit_name(self, event):
        logger.info('')
        #newName = self._layer.name
        newName = event.source.name
        self.signalLayerNameChange.emit(newName)

    def _connectLayer(self, layer=None):
        self._layer.events.name.connect(self.slot_user_edit_name)
        self._layer.events.selected_label.connect(self.slot_selected_label)

