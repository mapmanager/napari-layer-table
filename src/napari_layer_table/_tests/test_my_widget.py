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
import sys
import logging

def test_initialize_layer_table_widget_is_successful(make_napari_viewer):
    """
	Verify the creation of a LayerTable widget initialized with an napari viewer with no layers
	"""
    # Arrange inputs and targets. Arrange steps should set up the test case.
    viewer = make_napari_viewer()

    # Act on the target behavior. 
    # Act steps should cover the main thing to be tested, the LayerTablePlugin in our case
    my_widget = LayerTablePlugin(viewer)

    # Assert expected outcomes. Act steps should elicit some sort of response. 
    # Assert steps verify the goodness or badness of that response.
    assert my_widget is not None
    assert isinstance(my_widget, LayerTablePlugin)

def test_initialize_layer_table_widget_with_image_layer_is_successful(make_napari_viewer):
    """
	Verify the creation of a LayerTable widget initialized with an napari viewer with an image layer
	"""
    # Arrange
    viewer = make_napari_viewer()
    viewer.add_image(np.random.random((100, 100)))

    # Act
    my_widget = LayerTablePlugin(viewer)

    # Assert
    assert my_widget is not None
    assert isinstance(my_widget, LayerTablePlugin)

def test_initialize_layer_table_widget_with_image_and_points_layers_is_successful(make_napari_viewer):
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
    points1 = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    viewer.add_points(points1, size=3, face_color='green', name='green circles')

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

def test_LayerTablePlugin_does_not_connect_image_layer(make_napari_viewer, caplog):
    """
    Check if the connectLayer method does not accept an image layer and logs a message
    """
    # Arrange
    LOGGER = logging.getLogger(__name__)
    caplog.set_level(logging.WARNING)
    viewer = make_napari_viewer()
    image_layer = viewer.add_image(np.random.random((100, 100)))
    my_widget = LayerTablePlugin(viewer)

    # Act
    my_widget.connectLayer(image_layer)

    # Assert
    assert f'layer with type {type(image_layer)} was not in {my_widget.acceptedLayers}' in caplog.text

def test_LayerTablePlugin_connects_points_layer(make_napari_viewer):
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

    # Assert: checking if the layer was connected using the layerNameLabel
    assert my_widget.layerNameLabel.text() == 'green circles'

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
    my_widget.connectLayer(points_layer)
    initial_points_count = my_widget.myTable2.getNumRows()

    # Act: add a point to the points layer to check if the table is updated
    new_point = np.array([[zSlice, 50, 50]])
    new_points_data = np.concatenate((points, new_point), axis=axis)
    points_layer.data = new_points_data
    updated_points_count = my_widget.myTable2.getNumRows()

    # Assert: checking if the table data was updated
    assert initial_points_count == len(points)
    assert updated_points_count == len(new_points_data)
    assert updated_points_count == initial_points_count + 1

def test_LayerTablePlugin_updates_layer_data_when_point_is_deleted(make_napari_viewer):
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
