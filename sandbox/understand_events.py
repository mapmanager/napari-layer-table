"""
Trying to understand napari events.

In particular, when items are modified in a givan layer.

For example, in a point layer, when points are (added, deleted, modified).

Also applies to other layers including (points, shapes, labeled)

To modify clipping of 3d shapes

See:
    napari/layers/shapes/_shape_list.py
    ShapeList._update_displayed

    and github post

"""

import numpy as np
from skimage import data

import napari

my_selected_set = set()

def run():
    # make a viewer
    viewer = napari.Viewer()

    # create 3D sample image data
    image = data.binary_blobs(length=128, volume_fraction=0.1, n_dim=3)

    # add an image layer with sample image data
    imageLayer = viewer.add_image(image, colormap='green', blending='additive')

    # all of our points will be in slice 'zSlice'
    #zSlice = 15
    zSlice = 0

    # set viewer to slice zSLice
    axis = 0
    viewer.dims.set_point(axis, zSlice)

    # create 3D points
    points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])

    # create a points layer from our points
    pointsLayer = viewer.add_points(points,
                            size=30, 
                            face_color='magenta', 
                            name='magenta circles')

    # add some properties to the points layer (will be displayed in the table)
    pointsLayer.properties = {
        'Prop 1': ['a', 'b', 'c', 'd'],
        'Prop 2': [True, False, True, False],
    }

    #
    # connect to test what we get
    
    # these are layer events
    # this is what we want for points in a point layer
    # shapes in a shape layer
    # labels in a labeled layer ...
    '''
    viewer.layers.events.inserting.connect
    viewer.layers.events.inserted.connect
    viewer.layers.events.removing.connect
    viewer.layers.events.removed.connect
    '''

    # respond to change in layer
    viewer.layers.selection.events.changed.connect(slot_select_layer)

    layer = pointsLayer
    layer.events.data.connect(slot_user_edit_data)
    layer.events.name.connect(slot_user_edit_name)
    layer.events.symbol.connect(slot_user_edit_symbol)
    layer.events.size.connect(slot_user_edit_size)
    layer.events.highlight.connect(slot_user_edit_highlight)

    layer.events.properties.connect(slot_user_edit_properties)

    # run the napari event loop
    napari.run()

def slot_select_layer(event):
    """Respond to change in layer selection in viewer.
    
    Args:
        event (Event): event.type == 'changed'
    """
    print(f'slot_select_layer() event.type: {event.type}')

def slot_user_edit_data(event):
    """User edited a point in the current layer.
    
    This including: (add, delete, move). Also inclludes key press (confusing)

    Notes:
        On key-press (like delete), we need to ignore event.source.mode
    """
    print('slot_user_edit_data()')

def slot_user_edit_name(event):
    print('slot_user_edit_name()')

def slot_user_edit_symbol(event):
    print('slot_user_edit_symbol()')

def slot_user_edit_size(event):
    print('slot_user_edit_size()')

def slot_user_edit_highlight(event):
    """Called repeatedly on mouse hover.
    """
    global my_selected_set
    if event.source.selected_data == my_selected_set:
        return
    my_selected_set = event.source.selected_data
    print(f'slot_user_edit_highlight() my_selected_set:{my_selected_set}')

    if event.source.mode == 'add':
        # point(s) added, selected set tells us the point(s)
        # point is already in a layer
        # we would like to not allow add in some cases
        print(f'  added point {my_selected_set} see updated data ...')
        
    printEvent(event)

def slot_user_edit_properties(event):
    print('slot_user_edit_properties()')

def printEvent(event):
    print(f'  == _printEvent() type:{type(event)}')
    print(f'    event.type: {event.type}')
    #print(f'    event.mode: {event.mode}')
    print(f'    event.source: {event.source} {type(event.source)}')
    print(f'    event.source.mode: {event.source.mode}')
    print(f'    event.source.selected_data: {event.source.selected_data}')
    print(f'    event.source.data: {event.source.data}')
    try:
        print(f'    event.added: {event.added}')
    except (AttributeError) as e:
        print(f'    event.added: ERROR')

if __name__ == '__main__':
    run()