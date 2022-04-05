"""
	This script will do the following:
	 - Create a viewer
	 - Add sample image data as an image layer
	 - Create two point layers
	 - Run the LayerTablePlugin
	 - Have fun !!!
"""

import numpy as np
from skimage import data

import napari
from napari_layer_table import LayerTablePlugin

# make a viewer
viewer = napari.Viewer()

# create 3D sample image data
image = data.binary_blobs(length=128, volume_fraction=0.1, n_dim=3)

# add an image layer with sample image data
imageLayer = viewer.add_image(image, colormap='green', blending='additive')

# all of our points will be in slice 'zSlice'
zSlice = 15

# set viewer to slice zSLice
axis = 0
viewer.dims.set_point(axis, zSlice)

# create 3D points
points = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])

# create a points layer from our points
pointsLayer = viewer.add_points(points,
						size=30, face_color='magenta', name='magenta circles')
print(type(pointsLayer))

# add some properties to the points layer (will be displayed in the table)
pointsLayer.properties = {
	'Prop 1': ['a', 'b', 'c', 'd'],
	'Prop 2': [True, False, True, False],
}

# set the layer to 'select' mode (not needed)
pointsLayer.mode = 'select'

# make a second points layer
points2 = np.array([[zSlice, 75, 55], [zSlice, 85, 65], [zSlice, 95, 75]])
pointsLayer2 = viewer.add_points(points2,
						size=30, face_color='blue', 
						#edge_color='magenta',
						#edge_width_is_relative=False,
						#edge_width=10,
						name='blue crosses')
pointsLayer2.mode = 'select'
pointsLayer2.symbol = '+'

# create the plugin.
#ltp = LayerTablePlugin(viewer, oneLayer=pointsLayer)
ltp = LayerTablePlugin(viewer, oneLayer=None)

# add the plugin to the viewer
area = 'right'
name = 'Layer Table Plugin'
dockWidget = viewer.window.add_dock_widget(ltp, area=area, name=name)

# run the napari event loop
napari.run()
