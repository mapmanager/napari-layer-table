"""
Widget to display points layer as a table.

See my post here:
	https://github.com/napari/napari/issues/720
"""

from pprint import pprint
import sys
import time
import warnings
import logging
import tifffile
import numpy as np
import pandas as pd

import napari
#from napari_tools_menu import register_dock_widget
#from napari.qt import thread_worker
from PyQt5 import QtWidgets
#from PyQt5 import QtCore

#from magicgui import magicgui
from magicgui.widgets import Table

# set up logging
logger = logging.getLogger()
logger.setLevel(level=logging.DEBUG)
streamHandler = logging.StreamHandler(sys.stdout)
consoleFormat = '%(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s'
c_format = logging.Formatter(consoleFormat)
streamHandler.setFormatter(c_format)
logger.addHandler(streamHandler)

'''
def _loadLine(path):
	skiprows = 7  # todo: read this from header comment
	df = pd.read_csv(path, skiprows=skiprows)
	print(df.head())

linePath = '/home/cudmore/Downloads/bil/d9/01/line/rr30a_s0_l.txt'
#_loadLine(linePath)
'''

#@register_dock_widget(menu="Measurement > Layer Table")
class LayerTablePlugin(QtWidgets.QWidget):
	# TODO: extend this to shape layers
	#acceptedLayers = (napari.layers.Points, napari.layers.Shapes)
	acceptedLayers = (napari.layers.Points)

	def __init__(self, napari_viewer, oneLayer=None):
		"""
		Args:
			viewer (napari viewer)
			oneLayer (layer) If given then connect to this one layer,
							otherwise, connect to all existing layers.
		"""
		super().__init__()

		self._viewer = napari_viewer
		
		#self._viewer.bind_key('d', self.userPressedKey)

		self._layer = None
		self._data = None  # list of list of points
		self._selectedData = None

		self.InitGui()  # order matters, connectLayer() is accessing table
						# but table has to first be created

		self.onlyOneLayer = True

		if oneLayer is None:
			self.onlyOneLayer = False
			oneLayer = self._findActiveLayers()
		if oneLayer is not None:
			self.connectLayer(oneLayer)

		# this does not seem to have events
		#self._viewer.layers.selection.active
		
		# see docstring for eventedlist
		# https://github.com/napari/napari/blob/1d784cf8373495d9591594b6dd6ac479d5566ed1/napari/utils/events/containers/_evented_list.py#L34
		
		# this receives all user interaction with all layers
		self._viewer.layers.events.connect(self.slot_user_modified_layer)
		
		self._viewer.layers.events.inserting.connect(self.slot_insert_layer)
		self._viewer.layers.events.inserted.connect(self.slot_insert_layer)
		self._viewer.layers.events.removed.connect(self.slot_remove_layer)
		self._viewer.layers.events.removing.connect(self.slot_remove_layer)

	def userPressedKey(self, event):
		"""
		TODO: delete selected point from layer and plugin!
		"""
		print('xxx:', event, type(event))
	
	def keyPressEvent(self, event):
		print('this never happens')

	'''
	@viewer.bind_key('d')
	def myDeleteKey(self):
		print('xxx')
	'''

	def connectLayer(self, layer):
		"""Connect to one layer.
		
			Args:
				layer (layer) Layer to connect to.
		"""
		logger.info(f'Connecting to layer "{layer}"')
		if not isinstance(layer, self.acceptedLayers):
			logger.warning(f'layer with type {type(layer)} was not in {self.acceptedLayers}')
			return

		if self._layer is not None:
			self._layer.events.data.disconnect(self.slot_user_edit_data)
			self._layer.events.name.disconnect(self.slot_user_edit_name)
		self._layer = layer
		#self._data = layer.data
		self._layer.events.data.connect(self.slot_user_edit_data)
		self._layer.events.name.connect(self.slot_user_edit_name)

		# when user switches layers, napari does not visually switch selections?
		# but the layer does remember it. Set it to empty set()
		# otherwise our interface would re-select the previous selection
		self._layer.selected_data = set()

		self._selectedData = None
		
		self.refreshTableData(layer.data)  # assigns self._data

		#self.myTable.native.selectRow(None)

	def _findActiveLayers(self):
		"""
		Find a pre-existing layer and connect to it.
		"""
		for layer in self._viewer.layers:
			if isinstance(layer, self.acceptedLayers):
				if layer == self._viewer.layers.selection.active:
					# connect to existing active layer
					#self.connectLayer(layer)
					return layer
		return None

	def InitGui(self):
		columnHeaders = ('z', 'x', 'y')
		self.myTable = Table(columns=columnHeaders, value=self._data)

		# does not work
		# self.myTable.changed.connect(self.tableChanged)

		# select one and only one row (not cells and not multiple rows)
		self.myTable.native.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
		#self.myTable.native.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
		#self.myTable.native.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
		self.myTable.native.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

		# this would allow user edits in table
		#myTable.native.itemChanged.connect(onItemChanged)

		# depreciated, see on_selectionChanged
		# user select row -->> select in viewer layer
		#self.myTable.native.itemClicked.connect(self.on_table_rowClicked)

		# respond to changes in table selection
		selection_model = self.myTable.native.selectionModel()
		selection_model.selectionChanged.connect(self.on_selectionChanged)

		# want to have 'delete' key NOT delete entries in row of table
		# this captures all delete key events and we can no longer delete
		# a point even when focus is on the viewer (not the table)
		#QtWidgets.QShortcut(QtCore.Qt.Key_Delete, self.myTable.native, activated=self.on_delete_key)

		
		#
		# make layout 
		#self.vbox_layout = QtWidgets.QVBoxLayout()
		#self.vbox_layout.addWidget(self.layer_combo_box)
		#self.vbox_layout.addWidget(self.myTable)

		#self.setLayout(self.vbox_layout)

		#self.myTable.show(run=True)

		self._viewer.window.add_dock_widget(self.myTable)

	'''
	def tableChanged(self):
		logger.info('')
	'''

	def setRow(self, rowSet : set, pntList : list):
		"""
		Set table row to new values.

		Usually responding to a user dragging a point.

		Args:
			rowSet (set of row indices)
			pntList (list of np.ndarray)
		"""
		logger.info(f'rowSet:{rowSet}, pntList:{pntList}')

		for idx, row in enumerate(rowSet):
			row = int(row)
			newRow = pntList[row]

			newRowList = newRow.tolist()
			if len(newRowList) == 2:
				index = 0
				value = 0
				newRowList.insert(index, value)

			print(f'  inserting newRowList: {newRowList}')
			#  data is a DataView object
			self.myTable.data[row] = newRowList

	def refreshTableData(self, data):
		"""
		Completely refresh table data with a new set of points.
		"""

		'''
		# currentDict is like
		{
			'data': [[29, 550, 500], [29, 650, 600], [29, 750, 700]],
			'index': (0, 1, 2),
			'columns': ('z', 'x', 'y')
		}
		'''

		if data is None:
			return
			
		data = np.round(data, 2)
		
		self._data = data

		currentDict = self.myTable.value  # get table as dict
		currentDict['data'] = data
		currentDict['index'] = {i for i in range(len(data))}  # enum comprehension
		#currentDict['columns'] = xxx

		self.myTable.value = currentDict

	'''
	def on_table_rowClicked(self, item):
		"""
		User clicked on table row ... select in viewer

		Params:
			item (QTableWidgetItem): The item clicked
		"""
		logger.info(f'item: {item}')

		selectionModel = self.myTable.native.selectionModel()
		selectedRows = selectionModel.selectedRows()  # should only be one row

		print(f'  selectedRows: {type(selectedRows)} {selectedRows}')
		
		#selectedRowList = []
		#for selectedRow in selectedRows:
		#	print('  selectedRow:', selectedRow.row())
		#	selectedRowList.append(selectedRow.row())
		#selectedRowSet = set(selectedRowList)
		selectedRowList = [selectedRow.row() for selectedRow in selectedRows]
		selectedRowSet = set(selectedRowList)

		#
		# emit back to viewer
		# select point set
		self._layer.selected_data = selectedRowSet

		# if only one selected then snap z of the image layer
		if len(selectedRowList) == 1:
			selectedRow = selectedRowList[0]  # the first row selection
			zSlice = self._data[selectedRow][0]  # assuming (z,y,x)
			self.snapToImagePlane(zSlice)
	'''

	def on_delete_key(self):
		"""
		User pressed deleted key.
		
		Delete the selected point/shape
		"""
		logger.info('TODO: delete selected point from current layer')
	
	def on_selectionChanged(self, selected, deselected):
		"""
		User clicked or used keyboard to select a table row.

		Args:
			selected (QItemSelection)
		
		Notes:
			We are not using parameters, we are looking at current selection in table.
			This assumes that when this slot is triggered, it has already been set.
		"""
		logger.info('')
		modelIndexList = self.myTable.native.selectionModel().selectedRows()
		selectedRowList = [modelIndex.row() for modelIndex in modelIndexList]
		selectedRowSet = set(selectedRowList)

		#
		# emit back to viewer
		self._layer.selected_data = selectedRowSet

		# if only one selected then snap z of the image layer
		if len(selectedRowList) == 1:
			selectedRow = selectedRowList[0]  # the first row selection
			zSlice = self._data[selectedRow][0]  # assuming (z,y,x)
			self.snapToImagePlane(zSlice)

	def snapToImagePlane(self, zPlane):
		"""Snap the viewer to an image plane.
		
		Assuming first dimension is image planes.
		"""
		axis = 0 # assuming (z,y,x)
		self._viewer.dims.set_point(axis, zPlane)

	def slot_insert_layer(self, event):
		"""
		User inserted a new layer.
		"""
		
		if self.onlyOneLayer:
			return
		
		logger.info(f'event.type: {event.type}')
		
		eventType = event.type
		if eventType == 'inserting':
			pass
		elif eventType == 'inserted':
			logger.info(f'New layer "{event.value}" was inserted at index {event.index}')
			
			layer = event.value
			self.connectLayer(layer)
			
			# table data is empty
			#self.refreshTableData([])

	def slot_remove_layer(self, event):
		"""
		User deleted a layer
		"""

		if self.onlyOneLayer:
			return

		eventType = event.type
		if eventType == 'removing':
			pass
		elif eventType == 'removed':
			logger.info('')
			print(f'  Removed layer "{event.value}"')
			
			# table data is empty
			#self.refreshTableData([])

			# TODO: does not work, newSelectedLayer is always None
			# we are not receiving new layer selection
			# do it manually from current state of the viewer
			#newSelectedLayer = self._viewer.layers.selection.active
			#self.connectLayer(newSelectedLayer)

	def slot_user_edit_name(self, event):
		"""User edited the name of a layer
		"""
		logger.info(f'name is now: {event.source.name}')
	
	def slot_user_edit_data(self, event):
		"""
		User edited a point in the current layer.
		
		This including: (add, delete, move). Also inclludes key press (confusing)

		Args:
			event (???)

		Notes:
			On key-press (like delete), we need to ignore event.source.mode
		"""
		logger.info('')

		# event.type == 'data'  # maybe useful ???
		
		# this is HUGE
		# pprint(vars(event.source))

		myEventType = None
		if event.source.mode == 'add':
			myEventType = 'add'
		elif len(self._data) != len(event.source.data):
			myEventType = 'delete'
		else:
			myEventType = 'move'

		# catch user key-stroke 'delete'
		if myEventType == 'add' and (len(event.source.data) < len(self._data)):
			myEventType = 'delete'

		print('  myEventType:', myEventType)
		
		if myEventType == 'add':
			print(f'  add will always append to end')
			for point in event.source.selected_data:
				try:
					addedData = event.source.data[point]
				except (IndexError) as e:
					logger.error(e)
				else:
					print(f'  added point index {point} is now: {addedData}')
			# add to table
			self.refreshTableData(event.source.data)
			self.selectInTable(event.source.selected_data)

		elif myEventType == 'delete':
			print(f'  deleted points set {event.source.selected_data}')
			# already deleted from data
			# delete from table
			self.refreshTableData(event.source.data)
		elif myEventType == 'move':
			for point in event.source.selected_data:
				movedData = event.source.data[point]
				print(f'  moved point index {point} is now at: {movedData}')
			# update table
			self.setRow(event.source.selected_data, event.source.data)

		#self._printEvent(event)

	def selectInTable(self, selected_data):
		# select via underlying qtableview
		for oneRow in selected_data:
			self.myTable.native.selectRow(oneRow)
			#break

	def slot_user_modified_layer(self, event):
		"""User selected a new layer.
		
			Args:
				event (LayerList)

			Notes:
				This function is called repeatedly as user
				moves mouse over layers and points

				This is called when user changes ANY property of the layer
		"""
		
		# as it is, this function gets called a lot !!!
		# logger.info(f'event type {type(event)}')
		# print(f'  event.type: {event.type}')

		layer = None
		if event.type == 'inserted':
			pass
			#layer = event.value

		elif event.type == 'removed':
			pass
			#layer = event.value
			#newSelectedLayer = self._viewer.layers.selection.active
			#self.connectLayer(newSelectedLayer)

		elif event.type == 'highlight':
			#pprint(vars(event))
			# TODO: This is bad, grabbing from global
			layer = self._viewer.layers.selection.active
			if isinstance(layer, self.acceptedLayers):
				if layer != self._layer:
					self.connectLayer(layer)
					#self._selectedData = None
					# refresh table
					#self.refreshTableData(layer.data)

				'''
				for oneRow in layer.selected_data:
					logger.info(f'Selecting table row {oneRow} for layer "{layer}"')
					print(f'  selected data is: {layer.selected_data}')
					self.myTable.native.selectRow(oneRow)
				'''

				if layer.selected_data != self._selectedData:
					logger.info(f'assigning self._selectedData = {layer.selected_data}')
					self._selectedData = layer.selected_data
					# select via underlying qtableview
					self.selectInTable(self._selectedData)

		#elif event.type == 'inserting':
		#	logger.info(f'Inserting new layer "{layer}"')

		elif event.type == 'set_data':
			# may be usefull
			pass

		elif event.type == 'thumbnail':
			# may be usefull
			pass
		
		elif event.type == 'current_edge_color':
			# may be usefull
			pass
		
		elif event.type == 'current_face_color':
			# may be usefull
			pass
		
		elif event.type == 'current_properties':
			# may be usefull
			pass
		
		elif event.type == 'data':
			# may be usefull
			pass
		
		else:
			logger.warning(f'Did not understand event.type: {event.type}')

	def _printEvent(self, event):
		"""
		Print info for event received in general slot_
		"""
		#logger.info(f'Event type: {type(event)}')
		print(f'  == _printEvent() type:{type(event)}')
		print(f'    event.type: {event.type}')
		#print(f'    event.mode: {event.mode}')
		print(f'    event.source: {event.source} {type(event.source)}')
		print(f'    event.source.mode: {event.source.mode}')
		print(f'    event.source.selected_data: {event.source.selected_data}')
		print(f'    event.source.data: {event.source.data}')
		try:
			print(f"    event.added: {event.added}")
		except (AttributeError) as e:
			pass
		
		activeLayer = self._viewer.layers.selection.active
		print(f'    viewer.layers.selection.active: {type(activeLayer)} {activeLayer}')

def run():
	
	'''
	#path = '/home/cudmore/Downloads/bil/d9/01/rr30a_s1_ch2.tif'
	path = '/media/cudmore/data/richard/rr30a/raw/rr30a_s0_ch2.tif'
	image = tifffile.imread(path)
	print('  image is', image.shape, image.dtype)
	'''

	numSlices = 20
	minInt = 0
	maxInt = 100
	image = np.random.randint(minInt, maxInt, (numSlices,1024,1024))

	viewer = napari.Viewer()

	#print(viewer.dims.indices)
	print('  viewer.dims.point:', viewer.dims.point)
	print('  viewer.dims.order:', viewer.dims.order)

	imageLayer = viewer.add_image(image, colormap='green', blending='additive')

	# set viewer to slice zSLice
	axis = 0
	zSlice = 15
	viewer.dims.set_point(axis, zSlice)

	# synthetic points
	# if one point has a float, magicgui table makes ALL float
	points1 = np.array([[zSlice, 100, 100], [zSlice, 200, 200], [zSlice, 300, 300], [zSlice, 400, 400]])
	pointsLayer = viewer.add_points(points1,
							size=30, face_color='green', name='green circles')
	pointsLayer.mode = 'select'

	points2 = np.array([[zSlice, 550, 500], [zSlice, 650, 600], [zSlice, 750, 700]])
	pointsLayer2 = viewer.add_points(points2,
							size=30, face_color='magenta', name='magenta crosses')
	pointsLayer2.mode = 'select'
	pointsLayer2.symbol = '+'

	# run the plugin
	aMyInterface = LayerTablePlugin(viewer, oneLayer=pointsLayer2)

	napari.run()

if __name__ == '__main__':
	run()