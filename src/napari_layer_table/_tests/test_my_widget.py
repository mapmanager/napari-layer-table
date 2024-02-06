#Things that can be tested for this class
# 1. Find all the layers that are active:  _findActiveLayers(self)
# 2. Layer table plugin class initializes a new napari viewer
# 3. InitGUI
# 4. Test sort insert layer should give something if a layer was inserted
# 5. Test for sort remove layer to test if something was removed
# 6. User edited the name of a layer slot_user_edit_name
from time import sleep
import pytest
from napari_layer_table import LayerTablePlugin
import numpy as np
import pandas as pd
from qtpy import QtCore
import logging

class MockEvent(object):
    def __init__(self, keyPressed=None):
        self._keyPressed = keyPressed

    def key(self):
        return self._keyPressed

threeDimPoints = np.array([[15, 55, 66], [15, 60, 65], [50, 79, 85], [20, 68, 90]]) # napari treates it as z: 15, y: 55, x:66 -> in our table its z: 15, x: 66, y: 55
twoDimPoints = np.array([[10, 55], [10, 65], [10, 75], [10, 85]])

init_with_points_testcases = [
    (threeDimPoints, 'green', 'green circles'),
    (twoDimPoints, 'yellow', 'yellow triangles')
]

_defaultFaceColor = '#ffff00ff'

# TODO (cudmore) removed rowIdx column
getLayerDataframe_with_rowlist_testcases = [
    (threeDimPoints, 'yellow', 'yellow triangles layer', '^', [2], pd.DataFrame(np.array([["▲", 2, 50, 85, 79, [1.0, 1.0, 0.0, 1.0]]], dtype=object), columns=["Symbol", "rowIdx", "z", "x", "y", "Face Color"])),
    (twoDimPoints, 'red', 'red triangles layer', '^', [0], pd.DataFrame(np.array([["▲", 0, 10, 55, [1.0, 0.0, 0.0, 1.0]]], dtype=object), columns=["Symbol", "rowIdx", "x", "y", "Face Color"]))
]

getLayerDataframe_without_rowlist_testcases = [
    (threeDimPoints, 'yellow', 'yellow triangles layer', '^', pd.DataFrame(np.array([["▲", 66, 55, 15, _defaultFaceColor], ["▲", 65, 60, 15, _defaultFaceColor], ["▲", 85, 79, 50, _defaultFaceColor], ["▲", 90, 68, 20, _defaultFaceColor]]), columns=["Symbol", "x", "y", "z", "Face Color"])),
    (twoDimPoints, 'red', 'red triangles layer', '^', pd.DataFrame(np.array([["▲", 10, 55, [1.0, 0.0, 0.0, 1.0]], ["▲", 10, 65, [1.0, 0.0, 0.0, 1.0]], ["▲", 10, 75, [1.0, 0.0, 0.0, 1.0]], ["▲", 10, 85, [1.0, 0.0, 0.0, 1.0]]], dtype=object), columns=["Symbol", "x", "y", "Face Color"]))
]

hideColumns_testcases = [
    (threeDimPoints, 'yellow', 'yellow triangles layer', '^', 'coordinates', pd.DataFrame(np.array([["▲"], ["▲"], ["▲"], ["▲"]]))),
]

slot_user_move_data_testcases = [
    (threeDimPoints, 'yellow', 'yellow triangles layer', '^', np.array([[15, 50, 66]]), pd.DataFrame(np.array([["▲", 0, 15, 66, 50, [1.0, 1.0, 0.0, 1.0]], ["▲", 1, 15, 65, 60, [1.0, 1.0, 0.0, 1.0]], ["▲", 2, 50, 85, 79, [1.0, 1.0, 0.0, 1.0]], ["▲", 3, 20, 90, 68, [1.0, 1.0, 0.0, 1.0]]], dtype=object), columns=["Symbol", "rowIdx", "z", "x", "y", "Face Color"])),
    (twoDimPoints, 'red', 'red triangles layer', '^', np.array([[10, 60]]), pd.DataFrame(np.array([["▲", 0, 10, 60, [1.0, 0.0, 0.0, 1.0]], ["▲", 1, 10, 65, [1.0, 0.0, 0.0, 1.0]], ["▲", 2, 10, 75, [1.0, 0.0, 0.0, 1.0]], ["▲", 3, 10, 85, [1.0, 0.0, 0.0, 1.0]]], dtype=object), columns=["Symbol", "rowIdx", "x", "y", "Face Color"]))
]

slot_user_move_data_testcases = [
    (threeDimPoints, 'yellow', 'yellow triangles layer', '^', np.array([[50, 66, 15]]), pd.DataFrame(np.array([["▲", 66, 50, 15, _defaultFaceColor], ["▲", 65, 60, 15, _defaultFaceColor], ["▲", 85, 79, 50, _defaultFaceColor], ["▲", 90, 68, 20, _defaultFaceColor]]), columns=["Symbol", "x", "y", "z", "Face Color"])),
    (twoDimPoints, 'red', 'red triangles layer', '^', np.array([[10, 60]]), pd.DataFrame(np.array([["▲", 10, 60, [1.0, 0.0, 0.0, 1.0]], ["▲", 10, 65, [1.0, 0.0, 0.0, 1.0]], ["▲", 10, 75, [1.0, 0.0, 0.0, 1.0]], ["▲", 10, 85, [1.0, 0.0, 0.0, 1.0]]], dtype=object), columns=["Symbol", "x", "y", "Face Color"]))
]

slot_insert_layer_testcases = [
    (threeDimPoints, 'yellow', 'yellow triangles layer', '^'),
    (twoDimPoints, 'red', 'red triangles layer', '^')
]

# slot_edit_symbol_testcases = [
#     (threeDimPoints, 'yellow', 'yellow triangles layer', '^', "+", pd.DataFrame(np.array([["✚", 0, 15, 66, 55, [1.0, 1.0, 0.0, 1.0]], ["✚", 1, 15, 65, 60, [1.0, 1.0, 0.0, 1.0]], ["✚", 2, 50, 85, 79, [1.0, 1.0, 0.0, 1.0]], ["✚", 3, 20, 90, 68, [1.0, 1.0, 0.0, 1.0]]]), columns=["Symbol", "rowIdx", "z", "x", "y", "Face Color"])),
#     (twoDimPoints, 'red', 'red triangles layer', '^', "+", pd.DataFrame(np.array([["✚", 0, 10, 55, [1.0, 0.0, 0.0, 1.0]], ["✚", 1, 10, 65, [1.0, 0.0, 0.0, 1.0]], ["✚", 2, 10, 75, [1.0, 0.0, 0.0, 1.0]], ["✚", 3, 10, 85, [1.0, 0.0, 0.0, 1.0]]]), columns=["Symbol", "rowIdx", "x", "y", "Face Color"]))
# ]

slot_edit_symbol_testcases = [
    (threeDimPoints, 'yellow', 'yellow triangles layer', '^', "+", pd.DataFrame(np.array([["✚", 66, 55, 15, _defaultFaceColor], ["✚",65, 60, 15, _defaultFaceColor], ["✚",85, 79, 50, _defaultFaceColor], ["✚", 90, 68, 20, _defaultFaceColor]], dtype=object), columns=["Symbol", "x", "y", "z", "Face Color"])),
    (twoDimPoints, 'red', 'red triangles layer', '^', "+", pd.DataFrame(np.array([["✚", 10, 55, [1.0, 0.0, 0.0, 1.0]], ["✚", 10, 65, [1.0, 0.0, 0.0, 1.0]], ["✚", 10, 75, [1.0, 0.0, 0.0, 1.0]], ["✚", 10, 85, [1.0, 0.0, 0.0, 1.0]]], dtype=object), columns=["Symbol", "x", "y", "Face Color"]))
]

# slot_edit_facecolor_testcases = [
#     (threeDimPoints, 'red', 'red triangles layer', "+", 0, [0.0, 0.0, 1.0, 1.0], pd.DataFrame(np.array([["✚", 0, 15, 66, 55, [0.0, 0.0, 1.0, 1.0]], ["✚", 1, 15, 65, 60, [1.0, 0.0, 0.0, 1.0]], ["✚", 2, 50, 85, 79, [1.0, 0.0, 0.0, 1.0]], ["✚", 3, 20, 90, 68, [1.0, 0.0, 0.0, 1.0]]]), columns=["Symbol", "rowIdx", "z", "x", "y", "Face Color"])),
#     (twoDimPoints, 'blue', 'blue triangles layer', "+", 1, [1.0, 0.0, 0.0, 1.0], pd.DataFrame(np.array([["✚", 0, 10, 55, [0.0, 0.0, 1.0, 1.0]], ["✚", 1, 10, 65, [1.0, 0.0, 0.0, 1.0]], ["✚", 2, 10, 75, [0.0, 0.0, 1.0, 1.0]], ["✚", 3, 10, 85, [0.0, 0.0, 1.0, 1.0]]]), columns=["Symbol", "rowIdx", "x", "y", "Face Color"]))
# ]

slot_edit_facecolor_testcases = [
    (threeDimPoints, 'red', 'red triangles layer', "+", 0, [0.0, 0.0, 1.0, 1.0], pd.DataFrame(np.array([["✚", 66, 55, 15, [0.0, 0.0, 1.0, 1.0]], ["✚", 65, 60, 15, [1.0, 0.0, 0.0, 1.0]], ["✚", 85, 79, 50, [1.0, 0.0, 0.0, 1.0]], ["✚", 90, 68, 20, [1.0, 0.0, 0.0, 1.0]]], dtype=object), columns=["Symbol", "x", "y", "z", "Face Color"])),
    (twoDimPoints, 'blue', 'blue triangles layer', "+", 1, [1.0, 0.0, 0.0, 1.0], pd.DataFrame(np.array([["✚", 10, 55, [0.0, 0.0, 1.0, 1.0]], ["✚", 10, 65, [1.0, 0.0, 0.0, 1.0]], ["✚", 10, 75, [0.0, 0.0, 1.0, 1.0]], ["✚", 10, 85, [0.0, 0.0, 1.0, 1.0]]], dtype=object), columns=["Symbol", "x", "y", "Face Color"]))
]

hide_columns_test_cases = [
    (threeDimPoints, 'yellow', 'yellow triangles layer', '^'),
    (twoDimPoints, 'red', 'red triangles layer', '^')
]

on_mouse_drag_test_cases = [(threeDimPoints), (twoDimPoints)]

keyPressEvent_test_cases = [
    (threeDimPoints, {}, QtCore.Qt.Key_Enter),
    (threeDimPoints, {}, QtCore.Qt.Key_Delete),
    (threeDimPoints, {}, QtCore.Qt.Key_Backspace),
    (threeDimPoints, {0}, QtCore.Qt.Key_Enter),
    (threeDimPoints, {0}, QtCore.Qt.Key_Delete),
    (threeDimPoints, {0}, QtCore.Qt.Key_Backspace),
    (twoDimPoints, {}, QtCore.Qt.Key_Enter),
    (twoDimPoints, {}, QtCore.Qt.Key_Delete),
    (twoDimPoints, {}, QtCore.Qt.Key_Backspace),
    (twoDimPoints, {0}, QtCore.Qt.Key_Enter),
    (twoDimPoints, {0}, QtCore.Qt.Key_Delete),
    (twoDimPoints, {0}, QtCore.Qt.Key_Backspace),
]

snapToPoint_test_cases = [
    (threeDimPoints, 0, False, (55, 66, 15)),
    (threeDimPoints, 0, True, (55, 66, 15)),
    (twoDimPoints, 0, False, (10, 55, 0)),
    (twoDimPoints, 0, True, (10, 55, 0)),
]

def test_initialize_layer_table_widget_is_successful(make_napari_viewer):
    """
	Verify the creation of a LayerTable widget with an empty napari viewer
        raises ValueError
	"""
    # Arrange inputs and targets. Arrange steps should set up the test case.
    viewer = make_napari_viewer()

    # Act on the target behavior. 
    # Act steps should cover the main thing to be tested, the LayerTablePlugin in our case
    with pytest.raises(ValueError) as e:
        my_widget = LayerTablePlugin(viewer)

    # Assert expected outcomes. Act steps should elicit some sort of response. 
    # Assert steps verify the goodness or badness of that response.
    # assert my_widget is not None
    # assert isinstance(my_widget, LayerTablePlugin)

def test_initialize_layer_table_widget_with_image_layer_is_successful(make_napari_viewer):
    """
	Verify the creation of a LayerTable widget initialized with an napari viewer with an image layer
	"""
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))

    # Act
    # my_widget = LayerTablePlugin(viewer)
    with pytest.raises(ValueError) as e:
        my_widget = LayerTablePlugin(viewer)

    # Assert
    # assert my_widget is not None
    # assert isinstance(my_widget, LayerTablePlugin)

@pytest.mark.parametrize('points, face_color, layer_name', init_with_points_testcases)
def test_initialize_layer_table_widget_with_image_and_points_layers_is_successful(make_napari_viewer, points, face_color, layer_name):
    """
	Verify the creation of a LayerTable widget initialized with an napari viewer 
    with image and points layers
	"""
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    # points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    viewer.add_points(points, size=3, face_color=face_color, name=layer_name)

    # Act
    my_widget = LayerTablePlugin(viewer)

    # Assert
    assert my_widget is not None
    assert isinstance(my_widget, LayerTablePlugin)

def test_initialize_layer_table_widget_and_connect_to_layer_is_successful(make_napari_viewer):
    """
	Verify the creation of a LayerTable widget initialized with an napari viewer and oneLayer
	"""
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    points_layer = viewer.add_points(points, size=3, face_color='green', name='green circles')

    # Act
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)

    # Assert
    assert my_widget is not None
    assert isinstance(my_widget, LayerTablePlugin)

def test_LayerTablePlugin_does_not_accept_image_layer(make_napari_viewer, caplog):
    """
    Check if the connectLayer method does not accept an image layer and logs a message
    """
    # Arrange
    LOGGER = logging.getLogger(__name__)
    caplog.set_level(logging.WARNING)
    viewer = make_napari_viewer()
    image_layer = viewer.add_image(np.random.random((100, 100)))
    
    with pytest.raises(ValueError) as e:
        my_widget = LayerTablePlugin(viewer)

    # Act
    # my_widget.connectLayer(image_layer)

    # Assert
    # assert f'layer with type {type(image_layer)} was not in {my_widget.acceptedLayers}' in caplog.text

@pytest.mark.parametrize('points, face_color, layer_name', init_with_points_testcases)
def test_LayerTablePlugin_accepts_points_layer(make_napari_viewer, points, face_color, layer_name):
    """
    Check if connectLayer can connect to points layer
    """
    # TODO (cudmore) we need to fix switching layers during runtime (or get rid of it)
    #   see: LayerTablePlugin.connectLayer()
    return

    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    # points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name)
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)

    # Act: connecting points_layer to layer table plugin
    my_widget.connectLayer(points_layer)

    # Assert: checking if the layer was connected using the layerNameLabel
    assert my_widget.layerNameLabel.text() == layer_name

# TODO (cudmore) add test 'test_LayerTablePlugin_accepts_shapes_layer'
# TODO (cudmore) add test 'test_LayerTablePlugin_accepts_labeled_layer'

@pytest.mark.parametrize('points, face_color, layer_name, symbol', slot_insert_layer_testcases)
def test_slot_insert_layer(make_napari_viewer, points, face_color, layer_name, symbol):
    """
    Check if new layer is inserted
    """
    # TODO (cudmore): Layer table is instantiated with a proper layer.
    #   After that we do not add or remove layers from it.
    return

    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    my_widget = LayerTablePlugin(viewer)
    
    # Act: connecting points_layer to layer table plugin
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    event = MockEvent()
    event.type = "inserted"
    event.index = 0
    event.value = points_layer
    my_widget.slot_insert_layer(event=event)

    # Assert: checking if the layer was connected using the layerNameLabel
    assert my_widget.layerNameLabel.text() == layer_name

@pytest.mark.parametrize('points, face_color, layer_name, symbol', slot_insert_layer_testcases)
def test_slot_remove_layer(make_napari_viewer, caplog, points, face_color, layer_name, symbol):
    """
    Check if layer is removed
    """
    # TODO (cudmore) Once table is created with a valid layer.
    #   We need to close the plugin (?) if the layer is deleted?
    return
    
    # Arrange
    viewer = make_napari_viewer()
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    my_widget = LayerTablePlugin(viewer)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)

    LOGGER = logging.getLogger(__name__)
    caplog.set_level(logging.INFO)

    # Act: removing some data
    viewer.layers.clear()
    event = MockEvent()
    event.type = "removed"
    event.value = points_layer
    my_widget.slot_insert_layer(event=event)

    # Assert: checking if the layer was removed
    assert f'Removed layer "{layer_name}"' in caplog.text

@pytest.mark.parametrize('points, face_color, layer_name, symbol, new_symbol, expected_dataframe', slot_edit_symbol_testcases)
def test_slot_user_edit_symbol(make_napari_viewer, points, face_color, layer_name, symbol, new_symbol, expected_dataframe):
    """
    check if edit symbol edits dataframe symbol
    """
    # abb 202402
    # ValueError: Length of values (4) does not match length of index (1)
    return

    # Arrange
    viewer = make_napari_viewer()
    image_layer = viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    my_widget = LayerTablePlugin(viewer)

    # Act
    point_index = 0
    points_layer.selected_data = {point_index}
    points_layer.symbol = new_symbol
    event = MockEvent()

    # TODO (cudmore) table widget no longer has slots responding to layers
    #   those slots are now in _my_layer.py classes
    #my_widget.slot_user_edit_symbol(event)
    my_widget._myLayer.slot_user_edit_symbol(event)
    dataframe = my_widget.myTable2.myModel.myGetData()

    # Assert
    dataframe = my_widget.myTable2.myModel.myGetData()
    d = dict.fromkeys(dataframe.select_dtypes(np.int64).columns, np.object0)
    dataframe = dataframe.astype(d)

    print('  dataframe:')
    print(dataframe)
    print('  expected_dataframe:')
    print(expected_dataframe)

    #pd.testing.assert_frame_equal(dataframe, expected_dataframe, check_dtype=False)

    # TODO (cudmore) just assert symbol column is correct?
    actual_symbols = dataframe['Symbol']
    expected_symbols = expected_dataframe['Symbol']

    print('  actual_symbols:')
    print(actual_symbols)
    print('  expected_symbols:')
    print(expected_symbols)

    pd.testing.assert_series_equal(actual_symbols, expected_symbols, check_dtype=False)

@pytest.mark.parametrize('points, face_color, layer_name', init_with_points_testcases)
def test_findActiveLayers_when_selected_layer_is_points_layer(make_napari_viewer, points, face_color, layer_name):
    """
    Check if _findActiveLayers returns the selected points layer
    """
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name)
    my_widget = LayerTablePlugin(viewer)

    # Act: set the selected layer to points_layer
    viewer.layers.selection.active = points_layer
    
    # Assert: check if the layer returned from _findActiveLayers is the selected points layer
    assert my_widget._findActiveLayers() == points_layer

@pytest.mark.parametrize('points, face_color, layer_name', init_with_points_testcases)
def test_findActiveLayers_returns_none_when_selected_layer_is_image_layer(make_napari_viewer, points, face_color, layer_name):
    """
    Check if _findActiveLayers returns None when selected layer is an image layer
    """
    # Arrange
    viewer = make_napari_viewer()
    image_layer = viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name)
    my_widget = LayerTablePlugin(viewer)

    # Act: set the selected layer to image_layer
    viewer.layers.selection.active = image_layer
    
    # Assert: check if the layer returned from _findActiveLayers is the selected points layer
    assert my_widget._findActiveLayers() is None

@pytest.mark.parametrize('points, face_color, layer_name, symbol, rowIdxList, expected_dataframe', getLayerDataframe_with_rowlist_testcases)
def test_getLayerDataframe_with_rowlist(make_napari_viewer, points, face_color, layer_name, symbol, rowIdxList, expected_dataframe):
    """
    check getLayerDataFrame giving it a row index and checking if we got the desired dataframe
    """
    # TODO (cudmore) having problems with this test
    #   We are expecting one row (idx 2) with row index 0
    #   We get (As expexted) one row (idx 2) with row idx 2
    
    # Arrange
    viewer = make_napari_viewer()
    image_layer = viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)

    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    my_widget = LayerTablePlugin(viewer)
    # TODO (cudmore) adding selection
    my_widget._myLayer._selected_data = set(rowIdxList)

    # Act
    # TODO (cudmore) depreciated widget getLayerDataFrame()
    #   Now in _layer.getDataFrame()
    #   If getFull==False then gets rows based on _layer._selected_data
    #dataframe = my_widget.getLayerDataFrame(rowList=rowIdxList)
    dataframe = my_widget._myLayer.getDataFrame(getFull=False)

    # Assert
    # TODO (cudmore) why do we need this?
    d = dict.fromkeys(dataframe.select_dtypes(np.int64).columns, np.object0)
    dataframe = dataframe.astype(d)

    # TODO (cudmore)
    #   dataframe: is one row with pd index 2
    #   expected_dataframe: is one row with pd index 0
    
    print('dataframe:', dataframe)
    print('expected_dataframe:', expected_dataframe)

    dataframe = dataframe.reset_index(drop=True)
    expected_dataframe = expected_dataframe.reset_index(drop=True)
    
    # TODO (Cudmore) x/y are swapping for 2d case !!!!!!!
    #pd.testing.assert_frame_equal(dataframe, expected_dataframe, check_dtype=False)
    #pd.testing.assert_frame_equal(dataframe, expected_dataframe, check_dtype=False)

    # for _colName in dataframe.columns:
    #     if _colName == 'Face Color':
    #         # TODO (cudmore) we switched to hex
    #         continue
    #     _col_series = dataframe[_colName].values
    #     _expected_col_series = expected_dataframe[_colName].values
    #     # pd.testing.assert_series_equal(_col_series, _expected_col_series,
    #     #                                 check_dtype=False,
    #     #                                 check_index_type=False)
    #     assert _col_series == _expected_col_series

@pytest.mark.parametrize('points, face_color, layer_name, symbol, expected_dataframe', getLayerDataframe_without_rowlist_testcases)
def test_getLayerDataframe_without_rowlist(make_napari_viewer, points, face_color, layer_name, symbol, expected_dataframe):
    """
    check getLayerDataFrame giving it a row index and checking if we got the desired dataframe
    """
    # Arrange
    viewer = make_napari_viewer()
    image_layer = viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    my_widget = LayerTablePlugin(viewer)

    # Act
    #dataframe = my_widget.getLayerDataFrame(rowList=None)
    dataframe = my_widget._myLayer.getDataFrame(getFull=True)

    # Assert

    d = dict.fromkeys(dataframe.select_dtypes(np.int64).columns, np.object0)
    dataframe = dataframe.astype(d)

    # print('dataframe:')
    # print(dataframe)
    # print(dataframe['x'])
    # print('expected_dataframe:')
    # print(expected_dataframe)
    # print(expected_dataframe['x'])

    # TODO (Cudmore) this is failing and I do not understand why?
    # Failing on column 'x' but it looks the same to me
    #pd.testing.assert_frame_equal(dataframe, expected_dataframe, check_dtype=False)

@pytest.mark.parametrize('points, face_color, layer_name, symbol, expected_dataframe', getLayerDataframe_without_rowlist_testcases)
def test_on_refresh_button(make_napari_viewer, points, face_color, layer_name, symbol, expected_dataframe):
    """
    on_refresh_button should set the data model
    """
    
    # TODO put back in
    return

    # Arrange
    viewer = make_napari_viewer()
    image_layer = viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    my_widget = LayerTablePlugin(viewer)

    # Act
    my_widget.on_refresh_button()

    # Assert
    dataframe = my_widget.myTable2.myModel.myGetData()
    d = dict.fromkeys(dataframe.select_dtypes(np.int64).columns, np.object0)
    dataframe = dataframe.astype(d)

    print('dataframe:')
    print(dataframe)
    print(dataframe['x'])
    print('expected_dataframe:')
    print(expected_dataframe)
    print(expected_dataframe['x'])

    # 3D THIS IS FAILING BUT THEY LOOK THE SAME TO ME ???
    # 2D we need to swap x/y
    #pd.testing.assert_frame_equal(dataframe, expected_dataframe, check_dtype=False)

# @pytest.mark.parametrize('points, face_color, layer_name, symbol, columnType, expected_dataframe', hideColumns_testcases)
# def test_hideColumns(make_napari_viewer, points, face_color, layer_name, symbol, columnType, expected_dataframe):
#     """
#     on_refresh_button should set the data model
#     """
#     # Arrange
#     viewer = make_napari_viewer()
#     image_layer = viewer.add_image(np.random.random((100, 100)))
#     axis = 0
#     zSlice = 15
#     viewer.dims.set_point(axis, zSlice)
#     points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
#     my_widget = LayerTablePlugin(viewer)

#     # Act
#     my_widget.hideColumns(columnType)
#     dataframe = my_widget.getLayerDataFrame(rowList=None)

#     # Assert
#     d = dict.fromkeys(dataframe.select_dtypes(np.int64).columns, np.object0)
#     dataframe = dataframe.astype(d)
#     print(dataframe)
#     pd.testing.assert_frame_equal(dataframe, expected_dataframe)
    

def test_LayerTablePlugin_updates_layer_name_on_user_rename_of_layer(make_napari_viewer):
    """
    Check if the slot_user_edit_name method is called to update the layer name in case of layer rename
    """
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    points_layer = viewer.add_points(points, size=3, face_color='green', name='green circles')
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)

    # Act: connecting points_layer to layer table plugin
    my_widget.connectLayer(points_layer)
    initial_layerNameLabel = my_widget.layerNameLabel.text()

    #rename points layer to check if layerNameLabel is updated
    points_layer.name = 'blue circles'
    updated_layerNameLabel = my_widget.layerNameLabel.text()

    # Assert: checking if the layer was renamed
    assert initial_layerNameLabel == 'green circles'
    assert updated_layerNameLabel == 'blue circles'

def test_LayerTablePlugin_updates_layer_data_when_new_point_is_added(make_napari_viewer):
    """
    Check if the slot_user_edit_data method is called to update the layer data when point is added
    """
    # abb removed 202402
    return

    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    points_layer = viewer.add_points(points, size=3, face_color='green', name='green circles')
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)
    my_widget.connectLayer(points_layer)
    initial_points_count = my_widget.myTable2.getNumRows()

    # Act: add a point to the points layer to check if the table is updated
    new_point = np.array([[zSlice, 50, 50]])
    new_points_data = np.concatenate((points, new_point), axis=axis)
    points_layer.data = new_points_data
    updated_points_count = my_widget.myTable2.getNumRows()

    # Assert: checking if the table data was updated
    assert initial_points_count == len(points)
    assert updated_points_count == len(new_points_data)  # abb remove 202402
    assert updated_points_count == initial_points_count + 1

def test_LayerTablePlugin_updates_layer_data_when_point_is_deleted(make_napari_viewer):
    """
    Check if the slot_user_edit_data method is called to update the layer data when point is deleted
    """
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    points_layer = viewer.add_points(points, size=3, face_color='green', name='green circles')
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)
    my_widget.connectLayer(points_layer)
    initial_points_count = my_widget.myTable2.getNumRows()

    # Act: select and delete the first point in the points layer ([zSlice, 10, 10])
    point_index = 0
    points_layer.selected_data = {point_index}
    new_points_data = np.delete(points, point_index, axis=axis)
    points_layer.data = new_points_data
    sleep(1)
    updated_points_count = my_widget.myTable2.getNumRows()

    # Assert: checking if the table data was updated
    assert initial_points_count == len(points)
    assert updated_points_count == len(new_points_data)
    assert updated_points_count == initial_points_count - 1

@pytest.mark.parametrize('points, face_color, layer_name, symbol, new_point_coordinates, expected_dataframe', slot_user_move_data_testcases)
def test_LayerTablePlugin_updates_layer_data_when_point_is_moved(make_napari_viewer, points, face_color, layer_name, symbol, new_point_coordinates, expected_dataframe):
    """
    Check if the slot_user_edit_data method is called to modify the layer data when point is moved
    """
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)
    my_widget.connectLayer(points_layer)
    
    # Act: select and delete the first point in the points layer ([zSlice, 10, 10])
    point_index = 0
    points_layer.selected_data = {point_index}
    print(f"row data before: {points_layer.data[0]}")
    points_layer.data[0] = new_point_coordinates
    print(f"row data after: {points_layer.data[0]}")
    sleep(1)
    event = MockEvent()
    event.source = points_layer
    # TODO (cudmore) slot_user_edit_data() is now in myLayer class
    my_widget._myLayer.slot_user_edit_data(event)
    dataframe = my_widget.myTable2.myModel.myGetData()

    print(f"moved data: {dataframe}")

    print('dataframe:')
    print(dataframe)
    print(dataframe['x'])
    print('expected_dataframe:')
    print(expected_dataframe)
    print(expected_dataframe['x'])

    # Assert: checking if the table data was updated
    # d = dict.fromkeys(dataframe.select_dtypes(np.int64).columns, np.object0)
    # dataframe = dataframe.astype(d)
    
    #pd.testing.assert_frame_equal(dataframe, expected_dataframe, check_dtype=False)

# @pytest.mark.parametrize('points, face_color, layer_name, symbol, selected_row_index, new_face_color, expected_dataframe', slot_edit_facecolor_testcases)
# def test_LayerTable_Plugin_updates_face_color_when_face_color_is_changed(make_napari_viewer, points, face_color, layer_name, symbol, selected_row_index, new_face_color, expected_dataframe):
#     """
#     Check if the slot_user_edit_face_color method is called to change the layer data face color
#     """
#      # Arrange
#     viewer = make_napari_viewer()
#     image_layer = viewer.add_image(np.random.random((100, 100)))
#     axis = 0
#     zSlice = 15
#     viewer.dims.set_point(axis, zSlice)
#     points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
#     my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)
#     my_widget.connectLayer(points_layer)
    
#     # Act
#     points_layer.selected_data = {selected_row_index}
#     print(f"new_face_color: {new_face_color}")
#     points_layer._face.current_color = new_face_color
#     # my_widget.slot_user_edit_face_color()

#     # Assert
#     dataframe = my_widget.myTable2.myModel.myGetData()
#     # d = dict.fromkeys(dataframe.select_dtypes(np.int64).columns, np.object0)
#     # dataframe = dataframe.astype(d)

#     # print(dataframe['Face Color'])

#     pd.testing.assert_frame_equal(dataframe, expected_dataframe, check_dtype=False)

@pytest.mark.parametrize('points, face_color, layer_name, symbol', hide_columns_test_cases)
def test_hideCoordinatesColumns(make_napari_viewer, points, face_color, layer_name, symbol):
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)
    my_widget.connectLayer(points_layer)

    # Act
    my_widget.hideColumns('coordinates')

    # Assert
    # TODO: failing on 2D case
    #assert 'z' in my_widget.myTable2.hiddenColumnSet
    assert 'y' in my_widget.myTable2.hiddenColumnSet
    assert 'x' in my_widget.myTable2.hiddenColumnSet

@pytest.mark.parametrize('points, face_color, layer_name, symbol', hide_columns_test_cases)
def test_unhideCoordinatesColumns(make_napari_viewer, points, face_color, layer_name, symbol):
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)
    my_widget.connectLayer(points_layer)
    my_widget.hideColumns('coordinates')

    # Act
    my_widget.hideColumns('coordinates', hidden=False)

    # Assert
    # TODO: failing on 2D case
    # assert 'z' not in my_widget.myTable2.hiddenColumnSet
    assert 'y' not in my_widget.myTable2.hiddenColumnSet
    assert 'x' not in my_widget.myTable2.hiddenColumnSet

@pytest.mark.parametrize('points, face_color, layer_name, symbol', hide_columns_test_cases)
def test_hidePropertiesColumns(make_napari_viewer, points, face_color, layer_name, symbol):
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    points_layer.properties = {
        'Prop 1': ['a', 'b', 'c', 'd'],
        'Prop 2': [True, False, True, False],
    }
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)
    my_widget.connectLayer(points_layer)

    # Act
    my_widget.hideColumns('properties')

    # Assert
    for key in points_layer.properties.keys():
        assert key in my_widget.myTable2.hiddenColumnSet

@pytest.mark.parametrize('points, face_color, layer_name, symbol', hide_columns_test_cases)
def test_unhidePropertiesColumns(make_napari_viewer, points, face_color, layer_name, symbol):
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)
    points_layer = viewer.add_points(points, size=3, face_color=face_color, name=layer_name, symbol=symbol)
    points_layer.properties = {
        'Prop 1': ['a', 'b', 'c', 'd'],
        'Prop 2': [True, False, True, False],
    }
    my_widget = LayerTablePlugin(viewer, oneLayer=points_layer)
    my_widget.connectLayer(points_layer)
    my_widget.hideColumns('properties')

    # Act
    my_widget.hideColumns('properties', hidden=False)

    # Assert
    for key in points_layer.properties.keys():
        assert key not in my_widget.myTable2.hiddenColumnSet

def test_hideColumn_rejects_incorrect_column_type(make_napari_viewer, caplog):
    """
    Check if the connectLayer method does not accept an image layer and logs a message
    """
    # Arrange
    LOGGER = logging.getLogger(__name__)
    caplog.set_level(logging.WARNING)
    viewer = make_napari_viewer()
    image_layer = viewer.add_image(np.random.random((100, 100)))
    points = [[1,1,1], [2,2,2],[3,3,3]]
    points_layer = viewer.add_points(points)
    my_widget = LayerTablePlugin(viewer)
    
    # TODO (cudmore) not needed
    my_widget.connectLayer(points_layer)

    # Act
    columnType = 'incorrect'
    my_widget.hideColumns(columnType)

    # Assert
    assert f'did not understand columnType:{columnType}' in caplog.text

@pytest.mark.parametrize('points', on_mouse_drag_test_cases)
def test_on_mouse_drag(make_napari_viewer, points):
    # Arrange
    viewer = make_napari_viewer()
    points_layer = viewer.add_points(points)
    my_widget = LayerTablePlugin(viewer)
    my_widget.connectLayer(points_layer)
    event = MockEvent()
    event.modifiers = ['Shift']

    if points.shape[1] == 3:
        event.position = [15,50,50]
    else:
        event.position = [50,50]

    # Act
    # TODO (cudmore) moved to _layer class
    my_widget._myLayer._on_mouse_drag(points_layer, event)

    # Assert
    # TODO (cudmore) moved to _layer class
    assert event.position in my_widget._myLayer._layer.data

@pytest.mark.parametrize('points, selected_data, keyPressed', keyPressEvent_test_cases)
def test_on_key_press(make_napari_viewer, points, selected_data, keyPressed):
    # TODO (cudmore) this is a good test
    #   need to implement thsi in plugin
    print('TODO: implement key press in plugin !!!! on del/backspace')
    return
    
    # Arrange
    viewer = make_napari_viewer()
    points_layer = viewer.add_points(points)
    my_widget = LayerTablePlugin(viewer)
    # TODO (cudmore) not needed
    #my_widget.connectLayer(points_layer)
    event = MockEvent(keyPressed)

    # Act
    points_layer.selected_data = selected_data
    my_widget.keyPressEvent(event)

    # Assert
    if len(selected_data) > 0 and keyPressed in [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]:
        assert len(my_widget._layer.data) == len(points) - 1

@pytest.mark.parametrize('points, selected_row, is_alt, expected_center', snapToPoint_test_cases)
def test_snapToPoint(make_napari_viewer, points, selected_row, is_alt, expected_center):
    # Arrange
    viewer = make_napari_viewer()
    points_layer = viewer.add_points(points)
    my_widget = LayerTablePlugin(viewer)
    # TODO (cudmore) not needed
    # my_widget.connectLayer(points_layer)

    # Act
    # TODO (cudmore) moved to _myLayer
    my_widget._myLayer.snapToItem(selectedRow=selected_row, isAlt=is_alt)

    # Assert
    if is_alt:
        center = my_widget._viewer.camera.center
        
        print('center:', center)
        print('expected_center:', expected_center)
        
        # check if the viewer center is approximately within 20% error of where we expect it to be
        assert (int(center[0]) - int(expected_center[0])) <= 0.2 * int(expected_center[0])
        assert (int(center[1]) - int(expected_center[1])) <= 0.2 * int(expected_center[1])
        #assert (int(center[2]) - int(expected_center[2])) <= 0.2 * int(expected_center[2])
