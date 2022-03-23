"""
Widget to display points layer as a table.

See my post here:
	https://github.com/napari/napari/issues/720
"""

from pprint import pprint
import sys
import logging
from functools import partial  # for checkbox callbacks

import numpy as np
import pandas as pd

import napari

from PyQt5 import QtWidgets, QtCore, QtGui

# set up logging
logger = logging.getLogger()
logger.setLevel(level=logging.DEBUG)
streamHandler = logging.StreamHandler(sys.stdout)
consoleFormat = '%(levelname)5s %(name)8s  %(filename)s %(funcName)s() line:%(lineno)d -- %(message)s'
c_format = logging.Formatter(consoleFormat)
streamHandler.setFormatter(c_format)
logger.addHandler(streamHandler)

from napari_layer_table._table_widget import myTableView
from napari_layer_table._table_widget import pandasModel

#
# see here for searching unicode symbols
# # https://unicode-search.net/unicode-namesearch.pl
# here, we map napari shape names to unicode characters we can print
SYMBOL_ALIAS = {
	'arrow': '\u02C3',
	'clobber': '\u2663',
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
		
		self._layer = None
		self._selectedData = None

		self._showProperties = True
		"""Toggle point properties"""
		
		self._showCoordinates = True
		"""Toggle point coordinates"""

		self._out_of_slice_display = True
		# see: out_of_slice_display in
		# https://napari.org/docs/dev/api/napari.layers.Points.html

		self._shift_click_for_new = True
		"""Allow new points on shift+click. Do not need to set mode to 'add'
		"""
		
		#self.myTable = None
		self.InitGui()  # order matters, connectLayer() is accessing table
						# but table has to first be created

		self.onlyOneLayer = None
		"""If true, will not switch to different layer, requires oneLayer parameter"""

		if oneLayer is None:
			self.onlyOneLayer = False
			oneLayer = self._findActiveLayers()
			if oneLayer is not None:
				self.connectLayer(oneLayer)
		else:
			self.onlyOneLayer = True
			self.connectLayer(oneLayer)

		# this does not seem to have events
		#self._viewer.layers.selection.active
		
		# see docstring for eventedlist
		# https://github.com/napari/napari/blob/1d784cf8373495d9591594b6dd6ac479d5566ed1/napari/utils/events/containers/_evented_list.py#L34
		
		# was this
		# this receives all user interaction with all layers
		self._viewer.layers.events.connect(self.slot_user_modified_layer)
		
		self._viewer.layers.events.inserting.connect(self.slot_insert_layer)
		self._viewer.layers.events.inserted.connect(self.slot_insert_layer)
		self._viewer.layers.events.removed.connect(self.slot_remove_layer)
		self._viewer.layers.events.removing.connect(self.slot_remove_layer)

		# does nothing
		# self._viewer.layers.events.changed.connect(self.slot_changed_layer)

		# open self as a dock widget inside napari window
		self.area = 'right'
		self._dockWidget = self._viewer.window.add_dock_widget(self, area=self.area, name='Layer Table Plugin')

		# self._dockWidget is type napari._qt.widgets.qt_viewer_dock_widget.QtViewerDockWidget
		# some sort of wrapped QDockWidget
		# but ... this does not work
		# self._dockWidget.setWindowTitle('xxx yyy')
	
	def on_refresh_button(self):
		logger.info('')
		self.refresh()

	def on_mouse_drag(self, layer, event):
		"""
		Handle user mouse-clicks

		TODO:
			- Add this as an option (activate vie right-click menu)
			- OR Move this out of plugin and put in main mapmanager
		"""
		# pure PyQt
		#modifiers = QtWidgets.QApplication.keyboardModifiers()
		#isShift = modifiers == QtCore.Qt.ShiftModifier
		#logger.info(f'isShift:{isShift}')

		if 'Shift' in event.modifiers:
			# make a new point at cursor position
			data_coordinates = self._layer.world_to_data(event.position)
			# always add as integer pixels (not fractional/float pixels)
			cords = np.round(data_coordinates).astype(int)
			
			#print(f'  data_coordinates:', data_coordinates)
			#print(f'  cords:', cords)
			
			self._layer.add(cords)

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
			#self._layer.events.properties.disconnect(self.slot_user_modified_properties)
		self._layer = layer
		
		# display the name of the layer in our widget
		self.layerNameLabel.setText(self._layer.name)

		# not sure
		#self._data = layer.data
		
		self._layer.events.data.connect(self.slot_user_edit_data)
		self._layer.events.name.connect(self.slot_user_edit_name)
		
		# these don't work
		#self._layer.events.properties.connect(self.slot_user_modified_face_color)
		#self._layer.events.face_color.connect(self.slot_user_modified_face_color)
		
		# connecting twice
		# does not work, faceColorEdit is color picker interface
		# AttributeError: 'Points' object has no attribute 'faceColorEdit'
		# self._layer.faceColorEdit.color_changed.connect(self.changeFaceColor)
		
		# this does not call our callback ... bug in napari???
		self._layer.events.face_color.connect(self.slot_user_modified_face_color)
		# this works but layer is not updated yet
		self._layer._face.events.current_color.connect(self.slot_user_modified_face_color)
		
		# we are not setting face color in the plugin
		#self._layer._edge.events.current_color.connect(self.slot_user_modified_edge_color)


		# when user switches layers, napari does not visually switch selections?
		# but the layer does remember it. Set it to empty set()
		# otherwise our interface would re-select the previous selection
		self._layer.selected_data = set()
		self._selectedData = None
		
		# tweek UI the way cudmore likes it !!!
		if self._shift_click_for_new:
			self._layer.mouse_drag_callbacks.append(self.on_mouse_drag)
		
		# TODO: remove this, should by part of map manager
		# leaving it here as proof-of-concept
		self._layer.mouse_wheel_callbacks.append(self.on_mouse_wheel)

		# Will increase/decrease point size as we move above/up and below/down (z) of point
		self._layer.out_of_slice_display = self._out_of_slice_display

		# full refresh of table
		self.refresh()

	#@Slot(np.ndarray)
	def changeFaceColor(self, color: np.ndarray):
		"""Update face color of layer model from color picker user input."""
		#with self.layer.events.current_face_color.blocker():
		#    self.layer.current_face_color = color
		logger.info('')

	def slot_user_modified_face_color(self):
		"""Respond to user selecting face color with color picker.

			Notes:
				- Unlike other event callbacks, this has no parameters.
				
		"""
		logger.info('')
		
		# features is same as properties
		#features = self._layer.features
		#print('  features is:')		
		#print(features)

		# user point selection
		selected_data = self._layer.selected_data
		if not selected_data:
			return
		
		# face color set/selected in face color color picker

		# this is the rgba of the selected point
		rgbaOfSelection = self._layer._face.current_color
		current_face_color = self._layer.current_face_color  # hex
		print(f'  TODO: set point {selected_data} in table to symbol color {rgbaOfSelection} {current_face_color}')


		#print('  self._layer.face_color is an nparray of rgba colors')
		#print(self._layer.face_color)

		# we need new function just to set the color of symbol in table
		# using current_face_color
		# Following does not work
		'''
		selectedDataList = list(selected_data)
		theLayer = self._viewer.layers.selection.active
		myTableData = self.getLayerData(rowList=selectedDataList, fromLayer=theLayer)
		self.myTable2.myModel.mySetRow(selectedDataList, myTableData)
		'''

	# we are not showing edge color in plugin
	'''
	def slot_user_modified_edge_color(self):
		"""Respond to user selecting edge color with color picker.

			Out table does not show edhe color, do nothing.

			Notes:
				- Unlike other event callbacks, this has no parameters.
		"""
		# our table does not show edge color, do nothing
		return
		logger.info('')
		# user point selection
		selected_data = self._layer.selected_data
		if not selected_data:
			return
		# edge color set/selected in face color color picker
		current_edge_color = self._layer.current_edge_color

		print(f'  TODO: set point {selected_data} in table to edge color {current_edge_color}')
	'''

	def keyPressEvent(self, event):
		"""
		"""
		logger.info(f'key press is: {event.text()}')
		delete_keylist = [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]
		# if event.key() == QtCore.Qt.Key_Delete:
		if event.key() in delete_keylist:
			self._layer.remove_selected()
		else:
			print('  did not understand key')

	def _findActiveLayers(self):
		"""
		Find pre-existing selected layer and connect to it.
		"""
		for layer in self._viewer.layers:
			if isinstance(layer, self.acceptedLayers):
				if layer == self._viewer.layers.selection.active:
					# connect to existing active layer
					return layer
		return None

	def InitGui(self):


		# main vertical layout
		vbox_layout = QtWidgets.QVBoxLayout()

		# one row of controls
		controls_hbox_layout = QtWidgets.QHBoxLayout()

		# full refresh of table
		refreshButton = QtWidgets.QPushButton('Refresh')
		refreshButton.clicked.connect(self.on_refresh_button)
		controls_hbox_layout.addWidget(refreshButton)

		# the current layer name
		self.layerNameLabel = QtWidgets.QLabel('')
		controls_hbox_layout.addWidget(self.layerNameLabel)

		vbox_layout.addLayout(controls_hbox_layout)

		self.myTable2 = myTableView()
		# to pass selections in table back to the viewer
		self.myTable2.signalSelectionChanged.connect(self.slot_selectionChanged)
		vbox_layout.addWidget(self.myTable2)

		# finalize
		self.setLayout(vbox_layout)

	# not used
	'''
	def setRow(self, rowSet : set, pntList : list):
		"""
		Set table row to new values.

		Usually responding to a user dragging a point.

		Args:
			rowSet (set of row indices)
			pntList (list of np.ndarray)
		"""
		logger.info(f'rowSet:{rowSet}')
		print(f'  NEED TO IMPLEMENT SET ROW !!!')

		for row in rowSet:
			row = int(row)
			newRow = pntList[row]  # the z/y/x coordinates

			newRowList = newRow.tolist()
			
			print(f'  setting values of row: {newRowList}')
			
			#  data is a DataView object
			#self.myTable2.data[row] = newRowList

			rowDict = {
				'symbol': 'xxx',
				'z': newRowList[0],
				'x': newRowList[1],
				'y': newRowList[2],
				'Prop 1': 'd',
				'Is Good': False
			}

			# this does not work, our model is no longer our pandasmodel !!!
			self.myTable2.myModel.mySetRow(row, rowDict)
			
			# on changing, don't auto sort
			# need to keep track of column user sorted on and sort on that
			#self.myTable2.proxy.sort(row)
	'''

	def old_setRow(self, rowSet : set, pntList : list):
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

	def refresh(self, data = None):
		"""Refresh table with new layer data
		
		This refreshes entire table (slow).
		We need to add rowIdx param and just refresh one row.
		One row refresh occurs on (add, delete, move)
		One row refresh also should depend on state change of layer like 'marker' or 'face_color'
		"""
		
		layerDataFrame = self.getLayerData(data)
		self._refreshTableData(layerDataFrame)

	def getLayerData(self, data: np.ndarray = None, rowList: list = None, fromLayer = None) -> pd.DataFrame:
		"""
		Get our customized layer data to display in a table.
		
		This includes (symbol, coordinates, properties)

		Args:
			data (np.ndarray)
			rowList (list)
			fromLayer (layer) not used, leave this in case we receive
				a callback but self._layer is not updated yet
		"""
		
		if fromLayer is None:
			fromLayer = self._layer
		
		if data is None:
			data = fromLayer.data

		if data is None:
			logger.warning(f'layer "{self._layer}"" did not have any data')
			return None

		if rowList is None:
			rowList = range(data.shape[0])

		logger.info('')
		print('  rowList:', type(rowList), rowList)

		df = pd.DataFrame()
		
		if self._showCoordinates:
			if data.shape[1] == 3:
				df['z'] = data[rowList,0]
				df['x'] = data[rowList,2]  # swapped
				df['y'] = data[rowList,1]
			elif data.shape[1] == 2:
				df['x'] = data[rowList,0]
				df['y'] = data[rowList,1]
			
			else:
				logger.error(f'got bad data shape {data.shape}')
		
		if self._showProperties:
			for k,v in self._layer.properties.items():
				df[k] = v[rowList]

		# TODO: put this first but be sure to get number of points in layer
		
		#
		# face color
		symbol = self._layer.symbol  # str
		try:
			symbol = SYMBOL_ALIAS[symbol]
		except (KeyError) as e:
			logger.warning(f'did not find symbol in SYMBOL_ALIAS named "{symbol}"')
			symbol = 'X'
		# this is needed to keep number of rows correct
		symbolList = [symbol] * len(rowList)  # data.shape[0]  # make symbols for each point
		df.insert(loc=0, column='symbol', value=symbolList)  # insert as first column
		
		tmpColor = [row for row in self._layer.face_color[rowList]]
		df['face_color'] = tmpColor

		return df

	def _refreshTableData(self, data):
		"""Refresh all data in table.

		Args:
			data (pd.DataFrame)
		"""
		
		if data is None:
			return
		
		if self.myTable2 is None:
			return

		logger.info(f'')
		print('  shape:', data.shape)
		print('  columns:', data.columns)

		myModel = pandasModel(data)
		self.myTable2.mySetModel(myModel)

		# always hide face_color column
		try:
			colIdx = data.columns.get_loc('face_color')
			if colIdx != -1:
				print(f'  !!! hiding face_color column {colIdx}')
				self.myTable2.setColumnHidden(colIdx, True)
		except (KeyError) as e:
			logger.warning('did not find face_color column, symbol colors will not work')

	def on_delete_key(self):
		"""
		User pressed deleted key.
		
		Delete the selected point/shape
		"""
		logger.info('TODO: delete selected point from current layer')
	
	def snapToImagePlane(self, zPlane):
		"""Snap the viewer to an image plane.
		
		Assuming first dimension is image planes.
		"""
		axis = 0 # assuming (z,y,x)
		self._viewer.dims.set_point(axis, zPlane)

	def snapToPoint(self, selectedRow):
		"""Snap viewer to a selected row.
		"""
		pass

	def contextMenuEvent(self, event):
		"""
		Show a context menu on mouse right-click.

		This is an inherited function of QWidget.
		"""

		# create the menu
		contextMenu = QtWidgets.QMenu(self)
		
		# add menu item actions
		showCoordinates = contextMenu.addAction("Show Coordinates")
		showCoordinates.setCheckable(True)
		showCoordinates.setChecked(self._showCoordinates)
		
		showProperties = contextMenu.addAction("Show Properties")
		showProperties.setCheckable(True)
		showProperties.setChecked(self._showProperties)

		contextMenu.addSeparator()
		shiftClickForNew = contextMenu.addAction("Shift+Click for new")
		shiftClickForNew.setCheckable(True)
		shiftClickForNew.setChecked(self._shift_click_for_new)

		out_of_slice_display = contextMenu.addAction("Out Of Slice Display")
		out_of_slice_display.setCheckable(True)
		out_of_slice_display.setChecked(self._out_of_slice_display)


		contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table To Clipboard")

		# show the menu
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))
		
		# take action
		if action == showCoordinates:
			self._showCoordinates = not self._showCoordinates
			self.refresh()
		elif action == showProperties:
			self._showProperties = not self._showProperties
			self.refresh()
		elif action == shiftClickForNew:
			self._shift_click_for_new = not self._shift_click_for_new
			# TODO: add/remove event
		elif action == out_of_slice_display:
			self._out_of_slice_display = not self._out_of_slice_display
			#self.refresh()
			if self._layer is not None:
				self._layer.out_of_slice_display = self._out_of_slice_display
		elif action == copyTable:
			# TODO: Add a copyTable() function to myTable2 (so we don't hve to explicity refer to the model)
			self.myTable2.myModel.myCopyTable()
		elif action is not None:
			logger.warning(f'action not taken "{action.text()}"')

	def slot_selectionChanged(self, selectedRowList):
		"""Respond to user selecting a table row.
		"""
		logger.info(f'selectedRowList: {selectedRowList}')
		
		selectedRowSet = set(selectedRowList)

		# emit back to viewer
		self._layer.selected_data = selectedRowSet

		# if only one row selected then snap z of the image layer
		if len(selectedRowList) == 1:
			selectedRow = selectedRowList[0]  # the first row selection
			zSlice = self._layer.data[selectedRow][0]  # assuming (z,y,x)
			self.snapToImagePlane(zSlice)

			# move viewer so selected point is in view
			self.snapToPoint(selectedRow)

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
		self.layerNameLabel.setText(event.source.name)

	#def slot_changed_layer(self, event):
	#	logger.info('')

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

		myEventType = None
		#if event.source.mode == 'add':
		#	myEventType = 'add'
		currentNumRows = self.myTable2.getNumRows()
		if currentNumRows < len(event.source.data):
			myEventType = 'add'
		elif currentNumRows > len(event.source.data):
			myEventType = 'delete'
		else:
			myEventType = 'move'

		print('  myEventType:', myEventType)
		
		if myEventType == 'add':
			theLayer = event.source  # has the new point
			addedRowList = list(event.source.selected_data)
			print(f'  addedRowList:', addedRowList)
			#myTableData = self.getLayerData(rowList=addedRowList, fromLayer=theLayer)
			# assuming self._layer is already updated
			myTableData = self.getLayerData(rowList=addedRowList)
			self.myTable2.myModel.myAppendRow(myTableData)
			self.selectInTable(event.source.selected_data)

		elif myEventType == 'delete':
			deleteRowList = list(event.source.selected_data)
			print(f'  deleteRowList: {deleteRowList}')

			for deleteRow in deleteRowList:
				self.myTable2.myModel.myDeleteRow(deleteRow)

		elif myEventType == 'move':
			#for point in event.source.selected_data:
			#	movedData = event.source.data[point]
			#	print(f'  moved point index {point} is now at: {movedData}')
			# update table
			#self.setRow(event.source.selected_data, event.source.data)

			theLayer = event.source  # has the changed points
			moveRowList = list(event.source.selected_data)
			print(f'  moveRowList:', moveRowList)
			#myTableData = self.getLayerData(rowList=moveRowList, fromLayer=theLayer)
			# assuming self._layer is already updated
			myTableData = self.getLayerData(rowList=moveRowList)
			self.myTable2.myModel.mySetRow(moveRowList, myTableData)

		#self._printEvent(event)

	def selectInTable(self, selected_data):
		logger.info(f'selected_data: {selected_data}')

		# select via underlying qtableview
		if selected_data:
			for oneRow in selected_data:
				#self.myTable.native.selectRow(oneRow)
				self.myTable2.selectRow(oneRow)
				#break
		else:
			print('  xxx TODO: cancel selection if empty !!!')
			self.myTable2.clearSelection()

	def slot_user_modified_properties(self, event):
		logger.info(event.type)
	
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

		elif event.type == 'set_data':
			print('  event.type:', event.type, ' --> doing nothing ...')
			#layer = self._viewer.layers.selection.active
			#logger.info(f'{event.type} layer.selected_data: {layer.selected_data}')
		elif event.type == 'highlight':
			#pprint(vars(event))
			# TODO: This is bad, grabbing from global
			layer = self._viewer.layers.selection.active
			#print('face_color:', layer.face_color)
			if isinstance(layer, self.acceptedLayers):
				if layer != self._layer:
					self.connectLayer(layer)

				'''
				for oneRow in layer.selected_data:
					logger.info(f'Selecting table row {oneRow} for layer "{layer}"')
					print(f'  selected data is: {layer.selected_data}')
					self.myTable.native.selectRow(oneRow)
				'''

				if layer.selected_data != self._selectedData:
					logger.info(f'assigning self._selectedData = {layer.selected_data}')
					self._selectedData = layer.selected_data
					
					# get properties of selected data
					pntList = list(self._selectedData)
					for k,v in layer.properties.items():
						print(f'  properties at pnt {self._selectedData} {k} {v[pntList]}')

					# select via underlying qtableview
					self.selectInTable(self._selectedData)

		#elif event.type == 'inserting':
		#	logger.info(f'Inserting new layer "{layer}"')

		#elif event.type == 'set_data':
		#	# may be usefull
		#	pass

		#elif event.type == 'thumbnail':
		#	# may be usefull
		#	pass
		
		elif event.type == 'current_edge_color':
			pass
			#logger.info(f'current_edge_color: {event}')
		
		elif event.type == 'current_face_color':
			print('  event.type:', event.type, ' --> doing nothing ...')
			# this is not triggered on color change
			# logger.info(f'current_face_color: type(event):{type(event)}')
			# print('xxx event is:')
			# pprint(event)

		elif event.type == 'current_properties':
			print('  event.type:', event.type, ' --> doing nothing ...')
			#logger.info(f'current_properties: {event}')
		
		#elif event.type == 'data':
		#	# may be usefull
		#	pass
		
		elif event.type == 'symbol':
			logger.info('symbol')
			self.refresh()

		else:
			print('  did not understand event.type:', event.type, ' --> doing nothing ...')
			#logger.warning(f'Did not understand event.type: {event.type}')

	def _printEvent(self, event):
		"""
		Print info for napari event received in general slot_
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
	def _loadLine(path):
		skiprows = 7  # todo: read this from header comment
		df = pd.read_csv(path, skiprows=skiprows)
		print(df.head())

	linePath = '/home/cudmore/Downloads/bil/d9/01/line/rr30a_s0_l.txt'
	#_loadLine(linePath)
	'''

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
	# test 2d points
	points2d = np.array([[500, 550], [600, 650], [700, 750]])
	pointsLayer2d = viewer.add_points(points2d,
							size=20, face_color='yellow', name='yellow carrots')
	pointsLayer2d.mode = 'select'
	pointsLayer2d.symbol = '^'

	points1 = np.array([[zSlice, 100, 100], [zSlice, 200, 200], [zSlice, 300, 300], [zSlice, 400, 400]])
	pointsLayer = viewer.add_points(points1,
							size=30, face_color='green', name='green circles')
	pointsLayer.mode = 'select'

	points2 = np.array([[zSlice, 550, 500], [zSlice, 650, 600], [zSlice, 750, 700]])
	pointsLayer2 = viewer.add_points(points2,
							size=30, face_color='magenta', 
							#edge_color='magenta',
							#edge_width_is_relative=False,
							#edge_width=10,
							name='magenta crosses')
	pointsLayer2.mode = 'select'
	#pointsLayer2.symbols = ['+'] * points2.shape[0]
	pointsLayer2.symbol = '+'
	
	# add some properties
	pointsLayer2.properties = {
		'Prop 1': ['a', 'b', 'c'],
		'Is Good': [True, False, True],
	}

	# run the plugin
	#aMyInterface = LayerTablePlugin(viewer, oneLayer=pointsLayer2)
	aMyInterface = LayerTablePlugin(viewer, oneLayer=None)

	napari.run()

if __name__ == '__main__':
	run()