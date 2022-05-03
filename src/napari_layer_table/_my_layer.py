"""
"""

from pprint import pprint
from tkinter.messagebox import showinfo

import numpy as np
import pandas as pd

from qtpy import QtCore

import napari

from napari.layers.points import _points_mouse_bindings  # import add, highlight, select
from napari.layers.shapes import _shapes_mouse_bindings  #vertex_insert

#from pymapmanager._logger import logger
from napari_layer_table._my_logger import logger

class mmLayer(QtCore.QObject):
    signalDataChanged = QtCore.Signal(object, object, object, pd.DataFrame)

    def __init__(self, viewer, layer):
        super().__init__()
        
        self._viewer = viewer
        self._layer = layer

        self._shift_click_for_new = False

        self._selected_data = layer.selected_data
        if list(self._selected_data):
            self._selected_data2 = layer.data[self._selected_data]
        else:
            self._selected_data2 = None
        
        self._numItems = len(layer.data)

        self._connectLayer()

    def numItems(self):
        return self._numItems
        
    def getLayer(self):
        return self._layer

    def getSelection(self):
        return self._selected_data

    def numItems(self):
        return len(self._layer.data)

    def _connectLayer(self, layer=None):
        
        self._layer.events.name.connect(self.slot_user_edit_name)
        self._layer.events.highlight.connect(self.slot_user_edit_highlight)
        self._layer.events.data.connect(self.slot_user_edit_data)
        
        # this does not trigger? Is not included in label layer
        self._layer.events.face_color.connect(self.slot_user_edit_face_color)
        
        # points layer
        #self._layer.events.symbol.connect(self.slot_user_edit_symbol)  # points layer
        #self._layer.events.size.connect(self.slot_user_edit_size)  # points layer

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
        
        if len(event.source.data) > self.numItems():
            # add an object/annotation for points layer is point, for shapes layer is shape
            # event.source.selected_data gives us the added points
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

        properties = self._getSelectedProperties()

        # signal what changed, try not to signal during dynamic user interaction ???
        if action == 'add':
            # added data indices are self._selected_data
            # added data is self._selected_data2
            self.signalDataChanged.emit('add', self._selected_data, self._selected_data2, properties)

        elif action == 'delete':
            # deleted data indices were _deleted_selected_data
            self.signalDataChanged.emit('delete', _deleted_selected_data, None, None)
        elif action == 'change':
            # changed indices are self._selected_data
            # changed data is self._selected_data2
            # handled by slot_user_edit_data
            pass
            # self.signalDataChanged.emit('change', self._selected_data, self._selected_data2)
        elif action == 'select':
            self.signalDataChanged.emit('select', self._selected_data, self._selected_data2, properties)
        #self.printEvent(event)

    def _getSelectedProperties(self) ->pd.DataFrame:
        # self._layer.features gives us a (features, properties) pandas dataframe !!!
        
        #print('features;')
        #pprint(self._layer.features)
        
        '''
        selected_data_list = list(self._selected_data)
        properties = {}
        for k,v in self._layer.properties.items():
            properties[k] = v[selected_data_list]
        return properties
        '''

        dfFeatures = self._layer.features  # all features

        # reduce by selection
        df = dfFeatures.iloc[list(self._selected_data)]

        return df

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
        #properties = event.source.properties
        properties = self._getSelectedProperties()
        self.signalDataChanged.emit('change', self._selected_data, self._selected_data2, properties)

    def slot_user_edit_face_color(self, event):
        print('slot_user_edit_face_color()')

    def slot_user_edit_name(self, event):
        print('slot_user_edit_name()')

    def slot_user_edit_symbol(self, event):
        print('slot_user_edit_symbol()')

    def slot_user_edit_size(self, event):
        print('slot_user_edit_size()')

    def slot_user_edit_properties(self, event):
        print('slot_user_edit_properties()')

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

    def _getSelectedProperties(self) -> pd.DataFrame:
        df = super()._getSelectedProperties()

        selectedList = list(self._selected_data)

        # prepend point layer columns
        df.insert(0, 'x', self._layer.data[selectedList,2])
        df.insert(0, 'y', self._layer.data[selectedList,1])
        df.insert(0, 'z', self._layer.data[selectedList,0])

        # TODO: add symbol encoding
        
        #pprint(df)
        #print('tmp:', self._layer.face_color[selectedList,:])
        
        tmpColor = [oneColor.tolist() for oneColor in self._layer.face_color[selectedList]]		
        df['face_color'] = tmpColor

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
    def __init__(self, viewer, layer):
        #super().__init__(viewer, layer)
        super().__init__()

        self._viewer = viewer
        self._layer = layer

        self._selected_label = self._layer.selected_label

        # just show one selected label (hide all others)
        #self._layer.show_selected_label = True
        
        self._layer.events.selected_label.connect(self.slot_selected_label)
    
    def slot_selected_label(self, event):
        print('slot_selected_label()')
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

    def _getSelectedProperties(self) -> pd.DataFrame:
        # self._layer.features gives us a (features, properties) pandas dataframe !!!
        
        #print('features;')
        #pprint(self._layer.features)
        
        '''
        selected_data_list = list(self._selected_data)
        properties = {}
        for k,v in self._layer.properties.items():
            properties[k] = v[selected_data_list]
        return properties
        '''

        dfFeatures = self._layer.features  # all features

        print('dfFeatures:')
        pprint(dfFeatures)
        
        # reduce by selection
        #df = dfFeatures.iloc[[self._selected_label]]

        return dfFeatures

def slot_external_data_changed(action, rows, data, properties):
    print('=== slot_external_data_changed()')
    print('  action:', action)
    print('  rows:', rows)
    print('  data:')
    pprint(data)
    print('  properties:')
    pprint(properties)

def myMakePointsLayer(viewer):

    # user always required to make their own layer
    data = None
    ndim = 3
    name = 'my points layer'
    size = 30
    face_color = 'magenta'

    properties = {
        'prop1': 'a',
        'prop2': 2,
    }
    properties = None

    points_layer = viewer.add_points(data,
                        ndim=ndim,
                        name = name,
                        size=size, 
                        face_color=face_color, 
                        shown = True,
                        properties=properties)

    # make our points layer
    pl = pointsLayer(viewer, points_layer)
    pl._updateMouseCallbacks(True)

    zSlice = 0
    points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    pl.addAnnotation(points)

    pl.signalDataChanged.connect(slot_external_data_changed)

    return pl

def myMakeShapesLayer(viewer):

    # user always required to make their own layer
    data = None
    ndim = 3
    name = 'my shapes layer'
    edge_width = 5
    edge_color = 'coral'
    face_color = 'royalblue'
    shapes_layer = viewer.add_shapes(data,
                        ndim=ndim,
                        name=name,
                        edge_width=edge_width,
                        edge_color=edge_color,
                        face_color=face_color)

    sl = shapesLayer(viewer, shapes_layer)
    
    polygonData = np.array([[0, 11, 13], [0, 21, 23], [0, 31, 43]])
    shape_type = 'polygon'
    sl.addShapes(polygonData, shape_type=shape_type)

    sl.signalDataChanged.connect(slot_external_data_changed)

    return sl

def myMakeShapesPathsLayer(viewer):

    # user always required to make their own layer
    data = None
    ndim = 3
    name = 'my shapes path layer'
    edge_width = 5
    edge_color = 'coral'
    face_color = 'royalblue'
    shapes_layer = viewer.add_shapes(data,
                        ndim=ndim,
                        name=name,
                        edge_width=edge_width,
                        edge_color=edge_color,
                        face_color=face_color)   

    spl = shapesPathLayer(viewer, shapes_layer)

    pathData = np.array(
        [[256.        , 160.06901423,  42.33424721],
        [256.        ,  62.80985887, 138.86213073],
        [256.        , 150.56248024, 312.90482979],
        [256.        , 261.71580066, 300.47320843]]
    )

    spl.addPath(pathData)
    spl._updateMouseCallbacks(True)
    spl.signalDataChanged.connect(slot_external_data_changed)

    return spl

def myMakeLabelLayer(viewer):
    from skimage import data
    from skimage.filters import threshold_otsu
    from skimage.segmentation import clear_border
    from skimage.measure import label
    from skimage.morphology import closing, square, remove_small_objects

    coins = data.coins()[50:-50, 50:-50]
    # apply threshold
    thresh = threshold_otsu(coins)
    bw = closing(coins > thresh, square(4))
    # remove artifacts connected to image border
    cleared = remove_small_objects(clear_border(bw), 20)
    # label image regions
    label_image = label(cleared)

    # get region properties
    # see: https://scikit-image.org/docs/dev/api/skimage.measure.html#skimage.measure.regionprops
    from skimage.measure import regionprops
    props = regionprops(label_image, coins)
    #print('props:')
    #pprint(regionProps)
    #for idx, prop in enumerate(props):
    #    #print(f"num_pixels: {prop['num_pixels']}")
    #    print(f"{idx} centroid: {prop['centroid']}")

    # viewer = napari.view_image(coins, name='coins')

    # TODO: get this features=props working
    # label_layer = viewer.add_labels(label_image, features=props, name='coins label')
    label_layer = viewer.add_labels(label_image, name='coins label')

    ll = labelLayer(viewer, label_layer)

    print('label_layer:')
    print('  selected_label:', label_layer.selected_label)
    print('  len labels data:', len(label_layer.data))
    print('  num_colors:', label_layer.num_colors)
    print('  np.unique:', np.unique(label_layer.data))

    return ll

def on_user_edit_points2(action : str, df : pd.DataFrame):
    print('== on_user_edit_points2()')

if __name__ == '__main__':
    from napari_layer_table import LayerTablePlugin
    
    viewer = napari.Viewer()
    
    pl = myMakePointsLayer(viewer)
    sl = myMakeShapesLayer(viewer)
    spl =  myMakeShapesPathsLayer(viewer)
    ll = myMakeLabelLayer(viewer)

    # show a pl as a layer-table-plugin
    on_add_point_callback = None
    pointsTable = LayerTablePlugin(viewer,
                            oneLayer=pl.getLayer(),
                            onAddCallback=on_add_point_callback)

    # receive (add, delete, move)
    pointsTable.signalDataChanged.connect(on_user_edit_points2)

    # only allow new points with shift-click when a pointType is selected
    # see: self.on_roitype_popup() where we turn this off when 'All' is selected
    #self.pointsTable._shift_click_for_new = False
    #self.pointsTable._updateMouseCallbacks()

    napari.run()
