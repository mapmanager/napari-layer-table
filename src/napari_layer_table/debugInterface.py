import time
from pprint import pprint

import pandas as pd
import numpy as np

#from qtpy import QtCore

import napari

from napari_layer_table import LayerTablePlugin
from napari_layer_table import shapesLayer
from napari_layer_table import pointsLayer
from napari_layer_table import labelLayer
from napari_layer_table import shapesPathLayer
from napari_layer_table._my_logger import logger

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
        'accept': '',
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
    edge_width = 2
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
    edge_width = 2
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
    """Signal emitted from plugin on user (selection, edit, delete)
    """
    print('== on_user_edit_points2()')
    print('  action:', action)
    print('  df:')
    pprint(df)

def _makePointsLayer(viewer):
    #
    # user always required to make their own layer
    zSlice = 0
    data = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    
    # to debug running plugin with empty layer
    # if we run plugin with empy points layer, x y columns are not added
    # workaround is to run plugin with at least one point
    #data = []
    
    ndim = 3
    name = 'my points layer'
    size = 30
    face_color = 'magenta'

    properties = {
        'accept': '',
        'prop1': 'a',
        'prop2': 2,
    }

    points_layer = viewer.add_points(data,
                        ndim=ndim,
                        name = name,
                        size=size, 
                        face_color=face_color, 
                        shown = True,
                        properties=properties)

    return points_layer

def _makePointsLayer_2d(viewer):
    #
    # user always required to make their own layer
    data = np.array([[5, 8], [10, 11], [15, 14], [20, 17]])
    ndim =2
    name = 'my points layer 2d'
    size = 20
    face_color = 'blue'

    properties = {
        'prop1': 'a',
        'prop2': 2,
    }

    points_layer = viewer.add_points(data,
                        ndim=ndim,
                        name = name,
                        size=size, 
                        face_color=face_color, 
                        shown = True,
                        properties=properties)

    return points_layer

def _makeShapesLayer(viewer):
    # user always required to make their own layer
    data = None
    ndim = 3
    name = 'my shapes layer'
    edge_width = 2
    edge_color = 'coral'
    face_color = 'royalblue'
    shapes_layer = viewer.add_shapes(data,
                        ndim=ndim,
                        name=name,
                        edge_width=edge_width,
                        edge_color=edge_color,
                        face_color=face_color)

    return shapes_layer

def _makeLabelLayer(viewer):
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
    from skimage.measure import regionprops, regionprops_table
    #props = regionprops(label_image, coins)
    _propsDict = regionprops_table(label_image, properties=['label', 'centroid', 'area'])
    _dfProps = pd.DataFrame(_propsDict)

    #print('props:')
    #pprint(regionProps)
    #for idx, prop in enumerate(props):
    #    #print(f"num_pixels: {prop['num_pixels']}")
    #    print(f"{idx} centroid: {prop['centroid']}")

    # viewer = napari.view_image(coins, name='coins')

    # TODO: get this features=props working
    # label_layer = viewer.add_labels(label_image, features=props, name='coins label')
    label_layer = viewer.add_labels(label_image, name='coins label')

    '''
    print('label_layer:')
    print('  selected_label:', label_layer.selected_label)
    print('  len labels data:', len(label_layer.data))
    print('  num_colors:', label_layer.num_colors)
    print('  np.unique:', np.unique(label_layer.data))
    '''

    return label_layer

def runPlugin(viewer, layer, onAddCallback=None):

    # create the plugin
    ltp = LayerTablePlugin(viewer, oneLayer=layer, onAddCallback=onAddCallback)
    #ltp.signalDataChanged.connect(on_user_edit_points2)

    # show
    area = 'right'
    name = layer.name
    _dockWidget = viewer.window.add_dock_widget(ltp, 
                        area=area, name=name)

    return ltp

def addPointCallback(selectedData : set, df : pd.DataFrame) -> dict:
    logger.info('BINGO')
    return {}

def flashItem(_layer, selectedRow):
    # flash size/color to make it visible
    class _selfClass:
        def __init__(self, _layer):
            self._layer = _layer
    self = _selfClass(_layer)

    _origColor = self._layer.face_color[selectedRow].copy()
    _origSize = self._layer.size[selectedRow].copy()
    _flashColor = [1., 1., 0., 1.]
    _flashSize = _origSize * 5

    print('_origColor:', _origColor)
    print('_origSize:', _origSize)
    print('_flashColor:', _flashColor)
    print('_flashSize:', _flashSize)

    _numFlash = 2
    for _flash in range(_numFlash):
        print('  _flash:', _flash)
        self._layer.face_color[selectedRow] = _flashColor
        self._layer.size[selectedRow] = _flashSize
        self._layer.refresh()
        # self._layer.events.size()
        # self._layer.events.face_color()
        # self._layer.events.refresh()
        #no work self._layer.update()
        time.sleep(0.1)
        # 2
        self._layer.face_color[selectedRow] = _origColor
        self._layer.size[selectedRow] = _origSize
        self._layer.refresh()
        # self._layer.events.size()
        # self._layer.events.face_color()
        # self._layer.events.refresh()
        #no work self._layer.update()
        time.sleep(0.1) 

    _finalColor = self._layer.face_color[selectedRow]
    _finalSize = self._layer.size[selectedRow]
    print('_finalColor:', _finalColor)
    print('_finalSize:', _finalSize)

def run():

    _app = napari.qt.get_app()  # PyQt5.QtWidgets.QApplication
    _app.processEvents()
    print('_app:', type(_app))

    viewer = napari.Viewer()

    # points
    if 1:
        #points_layer = _makePointsLayer_2d(viewer)
        points_layer = _makePointsLayer(viewer)  # 3d
        
        points_ltp = runPlugin(viewer, points_layer, onAddCallback=addPointCallback)
        points_ltp._myLayer.newOnShiftClick(True)  # turn on shift+click to add

    #flashItem(points_layer, 2)

    # shapes
    if 0:
        shapes_layer = _makeShapesLayer(viewer)
        runPlugin(viewer, shapes_layer)

    # label layer
    if 0:
        label_layer = _makeLabelLayer(viewer)
        runPlugin(viewer, label_layer)

    # label layer has get_Color[idx)
    # print('face_color:', points_layer.get_color) # [[r, g, b, a]]

    napari.run()


if __name__ == '__main__':
    run()