"""
Widget to display points layer as a table.

 - The selected layer is displayed in the table.
 - The table has columns for:

     - Point symbol with face color
	 - Point coordinates (x,y,z)
	 - If the layer has properties, these are also columns

 - Bi-directional selection between layer and table.
 - Bi-directional delete between layer and table.
 - Points added to the layer are added to the table.
 - Points moved in the layer are updated in the table.
 - Changes to face color and symbol in the layer are updated in the table.

 Right-click for context menu to:

 - Toggle table columns on/off.
 - Toggle shift+click to add a point to the layer (no need to switch viewer mode)
 - Copy table to clipboard
"""

from pprint import pprint
import sys
import logging

import numpy as np
import pandas as pd

import napari

# to convert [r,g,b,a] to hex
# from napari.utils.colormaps.standardize_color import rgb_to_hex

from qtpy import QtWidgets, QtCore, QtGui

from napari_layer_table._my_logger import logger
from napari_layer_table._table_widget import myTableView
from napari_layer_table._data_model import pandasModel
from typing import List, Set
import warnings

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

def setsAreEqual(a, b):
	"""Convenience function. Return true if sets (a, b) are equal.
	"""
	if len(a) != len(b):
		return False
	for x in a:
		if x not in b:
			return False
	return True

class LayerTablePlugin(QtWidgets.QWidget):
	# TODO: extend this to shape layers
	#acceptedLayers = (napari.layers.Points, napari.layers.Shapes)
	acceptedLayers = (napari.layers.Points)

	signalDataChanged = QtCore.Signal(object, object)
	"""Emit signal to the external applictaion using this plugin when user adds/deletes/moves points.
	   Emits:
	   	1. event type which can be "add", "move" or "delete" 
		2. pandas dataframe for the edited row
	"""

	def __init__(self, napari_viewer : napari.Viewer,
					oneLayer=None,
					onAddCallback=None):
		"""A widget to display a point layer as a table.

		Args:
			viewer (napari.Viewer): Existing napari viewer.
			oneLayer (layer): If given then connect to this one layer,
							otherwise, connect to all existing layers.
			onAddCallback (def) function callback on adding points

		TODO (cudmore) check params and return of onAddCallback
			takes a string and returns ???
		"""
		super().__init__()

		warnings.filterwarnings(
			action='ignore',
			category=FutureWarning
		)
		self._viewer = napari_viewer
		
		self._layer = None  # current selected layer
		self._selectedData = None  # current selected data in selected layer

		# used to halt callbacks to prevent signal/slot recursion
		self._blockUserTableSelection = False
		self._blockDeleteFromTable = False

		self._showProperties = True  # Toggle point properties columns
		self._showCoordinates = True  # Toggle point coordinates columns (z,y,x)
		self._shift_click_for_new = False  # Toggle new points on shift+click
		#self._showFaceColor = True
		
		#self.myTable = None
		self.InitGui()  # order matters, connectLayer() is accessing table
						# but table has to first be created

		# If True, will not switch to different layer
		self._onlyOneLayer = oneLayer is not None

		if oneLayer is not None:
			self.connectLayer(oneLayer)
		else:
			oneLayer = self._findActiveLayers()
			#if oneLayer is not None:
			#	self.connectLayer(oneLayer)
			self.connectLayer(oneLayer)

		self._onAddCallback = onAddCallback
		
		# slots to detect a change in layer selection
		self._viewer.layers.events.inserting.connect(self.slot_insert_layer)
		self._viewer.layers.events.inserted.connect(self.slot_insert_layer)
		self._viewer.layers.events.removed.connect(self.slot_remove_layer)
		self._viewer.layers.events.removing.connect(self.slot_remove_layer)

		self._viewer.layers.selection.events.changed.connect(self.slot_select_layer)

	def InitGui(self):

		# main vertical layout
		vbox_layout = QtWidgets.QVBoxLayout()

		# one row of controls
		controls_hbox_layout = QtWidgets.QHBoxLayout()

		# full refresh of table
		refreshButton = QtWidgets.QPushButton('Refresh')
		refreshButton.setToolTip('Refresh the entire table')
		refreshButton.clicked.connect(self.on_refresh_button)
		controls_hbox_layout.addWidget(refreshButton)

		# bring layer to front in napari viewer
		bringToFrontButton = QtWidgets.QPushButton('btf')
		bringToFrontButton.setToolTip('Bring layer to front')
		# want to set an icon, temporary use built in is SP_TitleBarNormalButton
		#TODO (cudmore) install our own .svg icons, need to use .qss file
		style = self.style()
		bringToFrontButton.setIcon(
						style.standardIcon(QtWidgets.QStyle.SP_FileIcon))

		bringToFrontButton.clicked.connect(self.on_bring_to_front_button)
		controls_hbox_layout.addWidget(bringToFrontButton)

		# the current layer name
		self.layerNameLabel = QtWidgets.QLabel('')
		controls_hbox_layout.addWidget(self.layerNameLabel)

		vbox_layout.addLayout(controls_hbox_layout)

		self.myTable2 = myTableView()
		# to pass selections in table back to the viewer
		self.myTable2.signalSelectionChanged.connect(self.slot_selection_changed)
		vbox_layout.addWidget(self.myTable2)

		# finalize
		self.setLayout(vbox_layout)

	def _findActiveLayers(self):
		"""Find pre-existing selected layer.
		"""
		for layer in self._viewer.layers:
			if isinstance(layer, self.acceptedLayers):
				if layer == self._viewer.layers.selection.active:
					# connect to existing active layer
					return layer
		return None

	def on_refresh_button(self):
		logger.info('')
		self.refresh()

	def on_bring_to_front_button(self):
		"""Bring the layer to the front in napari viewer.
		"""
		logger.info('')
		if self._viewer.layers.selection.active != self._layer:
			#print('  seting layer in viewer')
			self._viewer.layers.selection.active = self._layer

	def on_mouse_drag(self, layer, event):
		"""Handle user mouse-clicks. Intercept shift+click to make a new point.

		Will only be called when install in _updateMouseCallbacks().
		"""
		if 'Shift' in event.modifiers:
			# make a new point at cursor position
			data_coordinates = self._layer.world_to_data(event.position)
			# always add as integer pixels (not fractional/float pixels)
			cords = np.round(data_coordinates).astype(int)
			
			# add to layer
			self._layer.add(cords)

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

	def keyPressEvent(self, event):
		"""Handle key press in table.

		Remove/Delete selected points on (Delete, Backspace).

		TODO: Move to tableview ?
		"""
		#logger.info(f'key press is: {event.text()}')
		delete_keylist = [QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace]
		if event.key() in delete_keylist:
			selectedData = self._layer.selected_data
			if not selectedData:
				logger.warning(f'Nothing to delete, selectedData:{selectedData}')
			else:
				logger.info(f'Delete points from layer: {selectedData}')
				self._blockDeleteFromTable = True
				self._layer.remove_selected()
				#self._deleteRows(selectedData)
				self._blockDeleteFromTable = False
		else:
			pass
			#print(f'  did not understand key {event.text()}')

	def connectLayer(self, layer):
		"""Connect to one layer.
		
		Args:
			layer (layer): Layer to connect to.

		TODO:
			Need to handle layer=None and just empty the interface
		"""
		#if layer is None:
		#	return
		
		if layer is not None and not isinstance(layer, self.acceptedLayers):
			logger.warning(f'layer with type {type(layer)} was not in {self.acceptedLayers}')
			return

		logger.info(f'Connecting to layer "{layer}"')

		# disconnect from existing (previous) layer
		if self._layer is not None:
			self._layer.events.data.disconnect(self.slot_user_edit_data)
			self._layer.events.name.disconnect(self.slot_user_edit_name)
			self._layer.events.symbol.disconnect(self.slot_user_edit_symbol)
			self._layer.events.size.disconnect(self.slot_user_edit_size)
			self._layer.events.highlight.disconnect(self.slot_user_edit_highlight)
			
			# special case
			self._layer.events.face_color.disconnect(self.slot_user_edit_face_color)
			self._layer._face.events.current_color.disconnect(self.slot_user_edit_face_color)
		
		self._layer = layer
		
		# if layer is None, hide interface
		if self._layer is None:
			logger.info('no layer selection ,hiding interface')
			# TODO (cudmore) the following is not needed, just hide the widget
			#emptyDataFrame = pd.DataFrame()
			# set name to ''
			#self.layerNameLabel.setText('')
			# set table to empty
			#self._refreshTableData(emptyDataFrame)
			self.hide()
			return
		else:
			self.show()

		# display the name of the layer
		self.layerNameLabel.setText(self._layer.name)

		self._layer.events.data.connect(self.slot_user_edit_data)
		self._layer.events.name.connect(self.slot_user_edit_name)
		self._layer.events.symbol.connect(self.slot_user_edit_symbol)
		self._layer.events.size.connect(self.slot_user_edit_size)
		self._layer.events.highlight.connect(self.slot_user_edit_highlight)

		# this does not call our callback ... bug in napari???
		self._layer.events.face_color.connect(self.slot_user_edit_face_color)
		# this works but layer is not updated yet
		try:
			self._layer._face.events.current_color.connect(self.slot_user_edit_face_color)
		except (AttributeError) as e:
			logger.warning(e)

		# important: when user switches layers, napari does not visually switch selections?
		# but the layer does remember it. Set it to empty set()
		# otherwise our interface would re-select the previous selection
		self._layer.selected_data = set()
		self._selectedData = None
		
		self._updateMouseCallbacks()

		# TODO: remove this, should by part of map manager
		# leaving it here as proof-of-concept
		#self._layer.mouse_wheel_callbacks.append(self.on_mouse_wheel)

		# full refresh of table
		self.refresh()

	def _updateMouseCallbacks(self):
		"""Enable/disable shift+click for new points.
		"""
		if self._shift_click_for_new:
			self._layer.mouse_drag_callbacks.append(self.on_mouse_drag)
		else:
			try:
				self._layer.mouse_drag_callbacks.remove(self.on_mouse_drag)
			except (ValueError) as e:
				# not in list
				pass
			
	def getLayerDataFrame(self, rowList: List[int] = None) -> pd.DataFrame:
		"""Get current layer as a DataFrame.
		
		This includes (symbol, coordinates, properties, face color)

		Args:
			rowList (list[int]): Specify a list of rows to just fetch those rows,
				used to change symbol, color, and on move
		"""
		
		if self._layer is None:
			return None

		data = self._layer.data

		if data is None:
			logger.warning(f'layer "{self._layer}" did not have any data')
			return None

		# if not specified, get a range of all rows
		if rowList is None:
			rowList = range(data.shape[0])

		df = pd.DataFrame()
		
		df['rowIdx'] = rowList

		# coordinates
		if data.shape[1] == 3:
			df['z'] = data[rowList,0]
			df['x'] = data[rowList,2]  # swapped
			df['y'] = data[rowList,1]
		elif data.shape[1] == 2:
			df['x'] = data[rowList,0]
			df['y'] = data[rowList,1]		
		else:
			logger.error(f'got bad data shape {data.shape}')
		
		# properties
		#logger.info(f'getting properties rowList:{rowList}')
		for k,v in self._layer.properties.items():
			#print(f'{k}:{v[rowList]}')
			df[k] = v[rowList]

		# symbol
		symbol = self._layer.symbol  # str
		try:
			symbol = SYMBOL_ALIAS[symbol]
		except (KeyError) as e:
			logger.warning(f'did not find symbol in SYMBOL_ALIAS named "{symbol}"')
			symbol = 'X'
		# this is needed to keep number of rows correct
		symbolList = [symbol] * len(rowList)  # data.shape[0]  # make symbols for each point
		df.insert(loc=0, column='Symbol', value=symbolList)  # insert as first column
		
		# face color
		# we need to use rgba, can not use hex as it does not map correctly
		# with selected color LUT (viridis is default?)
		tmpColor = [oneColor.tolist() for oneColor in self._layer.face_color[rowList]]		
		df['Face Color'] = tmpColor

		# print results
		#logger.info(f'  rowList:{rowList}, df is shape {df.shape}')
		#pprint(df, indent=4)

		return df

	def refresh(self):
		"""Refresh entire table with current layer.
		
		Note:
			This refreshes entire table (slow).
			Should only be used on table creation and layer switching.
			Do not use for edits like add, delete, change/move.
		"""
		layerDataFrame = self.getLayerDataFrame()
		self._refreshTableData(layerDataFrame)

	def _refreshTableData(self, df : pd.DataFrame):
		"""Refresh all data in table by setting its data model from provided dataframe.

		Args:
			df (pd.DataFrame): Pandas dataframe to refresh with.
		"""
		
		if self.myTable2 is None:
			# interface has not been initialized
			return

		if df is None:
			return
		
		logger.info(f'Full refresh ... limit use of this')

		myModel = pandasModel(df)
		self.myTable2.mySetModel(myModel)

	def snapToPoint(self, selectedRow : int, isAlt : bool =False):
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

	def contextMenuEvent(self, event):
		"""Show a context menu on mouse right-click.

		This is an inherited function of QWidget.
		"""

		# create the menu
		contextMenu = QtWidgets.QMenu(self)
		
		# add menu item actions
		showCoordinates = contextMenu.addAction("Coordinates")
		showCoordinates.setCheckable(True)
		showCoordinates.setChecked(self._showCoordinates)
		
		showProperties = contextMenu.addAction("Properties")
		showProperties.setCheckable(True)
		showProperties.setChecked(self._showProperties)

		#showFaceColor = contextMenu.addAction("Face Color")
		#showFaceColor.setCheckable(True)
		#showFaceColor.setChecked(self._showFaceColor)

		contextMenu.addSeparator()
		shiftClickForNew = contextMenu.addAction("Shift+Click for new")
		shiftClickForNew.setCheckable(True)
		shiftClickForNew.setChecked(self._shift_click_for_new)

		#contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table To Clipboard")

		contextMenu.addSeparator()

		# all columns in pandas data model
		columns = self.myTable2.getColumns()
		for column in columns:
			isHidden = column in self.myTable2.hiddenColumnSet
			columnAction = contextMenu.addAction(column)
			columnAction.setCheckable(True)
			columnAction.setChecked(not isHidden)

		# all properties in pandas data
		# these are part of columns

		# show the popup menu
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))
		
		# take action
		if action == showCoordinates:
			self._showCoordinates = action.isChecked()
			self.hideColumns('coordinates', not action.isChecked())
		elif action == showProperties:
			self._showProperties = action.isChecked()
			self.hideColumns('properties', not action.isChecked())
		
		elif action == shiftClickForNew:
			self._shift_click_for_new = not self._shift_click_for_new	
			self._updateMouseCallbacks()

		elif action == copyTable:
			self.myTable2.myModel.myCopyTable()
		
		elif action is not None:
			# show/hide individual comuns
			column = action.text()
			hidden = column in self.myTable2.hiddenColumnSet
			self.myTable2.mySetColumnHidden(column, not hidden)  # toggle hidden

		#elif action is not None:
		#	logger.warning(f'action not taken "{action.text()}"')

	def hideColumns(self, columnType : str, hidden : bool = True):
		"""Hide different sets of columns.

		Args:
			columnType (str): from
				- 'coordinates': Show or hide (z, y, x) columns.
				- 'properties': Show or hide all layer property key columns.
			hidden (bool): If true then column will be hidden, otherwise show.
		"""
		logger.info(f'columnType:{columnType} hidden:{hidden}')
		if columnType == 'coordinates':
			self.myTable2.mySetColumnHidden('z', hidden)
			self.myTable2.mySetColumnHidden('y', hidden)
			self.myTable2.mySetColumnHidden('x', hidden)
		elif columnType == 'properties':
			for property in self._layer.properties.keys():
				self.myTable2.mySetColumnHidden(property, hidden)
		else:
			logger.warning(f'did not understand columnType:{columnType}')

	def selectInTable(self, selected_data : Set[int]):
		"""Select in table in response to viewer (add, highlight).
		
		Args:
			selected_data (set[int]): Set of selected rows to select
		"""
		if self._blockDeleteFromTable:
			#self._blockDeleteFromTable = False
			return
		
		logger.info(f'selected_data: {selected_data}')

		self.myTable2.mySelectRows(selected_data)

	def slot_selection_changed(self, selectedRowList : List[int], isAlt : bool):
		"""Respond to user selecting a table row.

		Note:
			- This is coming from user selection in table,
				we do not want to propogate
		"""
		if self._blockDeleteFromTable:
			#self._blockDeleteFromTable = False
			return

		logger.info(f'selectedRowList: {selectedRowList} isAlt:{isAlt}')
		
		selectedRowSet = set(selectedRowList)

		self._blockUserTableSelection = True
		self._layer.selected_data = selectedRowSet  # emit back to viewer
		self._blockUserTableSelection = False

		# if only one row selected then snap z of the image layer
		if len(selectedRowList) == 1:
			selectedRow = selectedRowList[0]  # the first row selection
			self.snapToPoint(selectedRow, isAlt)

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
		# #layer = event.source
		layer = self._viewer.layers.selection.active
		
		#if layer is not None:
		#	if layer != self._layer:
		#		self.connectLayer(layer)
		if layer != self._layer:
			self.connectLayer(layer)

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
			self.connectLayer(layer)

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
			self.connectLayer(newSelectedLayer)

	def slot_user_edit_name(self, event):
		"""User edited the name of a layer.
		"""
		# if self._onlyOneLayer:
		# 	return
		logger.info(f'name is now: {event.source.name}')
		self.layerNameLabel.setText(event.source.name)

	def slot_user_edit_data(self, event):
		"""User edited a point in the current layer.
		
		This including: (add, delete, move). Also inclludes key press (confusing)

		Notes:
			On key-press (like delete), we need to ignore event.source.mode
		"""
		myEventType = None
		currentNumRows = self.myTable2.getNumRows()
		if currentNumRows < len(event.source.data):
			myEventType = 'add'
		elif currentNumRows > len(event.source.data):
			myEventType = 'delete'
		else:
			myEventType = 'move'
		
		#logger.info('')
		#print('  currentNumRows:', currentNumRows)
		#print('  len(event.source.data):', len(event.source.data))

		if myEventType == 'add':
			theLayer = event.source  # has the new point
			addedRowList = list(event.source.selected_data)
			logger.info(f'myEventType:{myEventType} addedRowList:{addedRowList}')

			if self._onAddCallback is not None:
				# TODO (cudmore) this also needs to update (face_color, symbol)
				returnDict = self._onAddCallback(addedRowList, event.source.properties)
				if returnDict is not None:
					print(f'{self._onAddCallback} returnDict:')
					for k,v in returnDict.items():
						print(f'  {k}: {v}')
					
					# modify napari layer properties
					#updateLayer = event.source  # does not update
					updateLayer = self._layer  # does update
					updateLayer.properties['roiType'][addedRowList] = returnDict['roiType']
					updateLayer.face_color[addedRowList] = returnDict['face_color']
					updateLayer.size[addedRowList] = returnDict['size']

					# above is working but we need to trigger an update in viewer?
					# this interferes with event chain --> causes errors
					# updateLayer.events.face_color()
				
			myTableData = self.getLayerDataFrame(rowList=addedRowList)
			self.myTable2.myModel.myAppendRow(myTableData)
			self.selectInTable(event.source.selected_data)
			self.signalDataChanged.emit(myEventType, myTableData)

		elif myEventType == 'delete':
			deleteRowSet = event.source.selected_data
			logger.info(f'myEventType:{myEventType} deleteRowSet:{deleteRowSet}')
			#index = list(deleteRowSet)[0]
			deletedDataFrame = self.myTable2.myModel.myGetData().iloc[list(deleteRowSet)]
			self._deleteRows(deleteRowSet)
			#self._blockDeleteFromTable = True
			#self.myTable2.myModel.myDeleteRows(deleteRowList)
			#self._blockDeleteFromTable = False
			self.signalDataChanged.emit(myEventType, deletedDataFrame)

		elif myEventType == 'move':
			theLayer = event.source  # has the changed points
			moveRowList = list(event.source.selected_data) #rowList is actually indexes
			# assuming self._layer is already updated
			logger.info(f'myEventType:{myEventType} moveRowList:{moveRowList}')
			myTableData = self.getLayerDataFrame(rowList=moveRowList)
			self.myTable2.myModel.mySetRow(moveRowList, myTableData)
			self.signalDataChanged.emit(myEventType, myTableData)

	def _deleteRows(self, rows : Set[int]):
		self._blockDeleteFromTable = True
		self.myTable2.myModel.myDeleteRows(rows)
		self._blockDeleteFromTable = False
		
	def slot_user_edit_symbol(self, event):
		"""Respond to user editing point symbol.
		
		For now, update the entire table. Not sure if napari allows symbols for individual points.
		"""
		myTableData = self.getLayerDataFrame()
		rowCount = self.myTable2.myModel.rowCount()
		self.myTable2.myModel.mySetRow(list(range(rowCount)), myTableData)

	def slot_user_edit_size(self, event):
		"""Respond to user settting size.

		TODO:
			- Not implemented
			- Add 'Size' as a column in getLayerDataFrame()
		"""		
		logger.info(f'{event.type}')
		
		#
		#layer = self._viewer.layers.selection.active
		layer = event.source

		# list of [nxm] sizes with n points and m dimensions for each size
		sizes = layer.size
		selected_data = layer.selected_data
		
		#print('  selected_data:', selected_data)
		#print('  sizes:', sizes)

	def slot_user_edit_highlight(self, event):
		"""Respond to user selection of point(s)
		
		We receive this on hover. Only react if selected_data has changed.
		"""
		if self._blockUserTableSelection:
			#self._blockUserTableSelection = False
			return

		# TODO: find signal that is explicit for 'switch layer'
		#layer = self._viewer.layers.selection.active
		layer = event.source
		if isinstance(layer, self.acceptedLayers):
			# new selection if layer selection is not same as our selection
			newSelection = self._selectedData is None or \
							not setsAreEqual(layer.selected_data, self._selectedData)
			if newSelection:
				self._selectedData = set(layer.selected_data)  # shallow copy
				self.selectInTable(self._selectedData)
	
	def slot_user_edit_face_color(self):
		"""Respond to user selecting face color with color picker.
			Notes:
				- Unlike other event callbacks, this has no parameters.
				- Unlike others, self._layer is not updated
				- We are grabbing the new selected color and
					setting selectedDataList to that color
				- bad choice but all I could find is:
					self._layer._face.current_color
		"""
		logger.info('')
		
		# user point selection
		selected_data = self._layer.selected_data
		selectedDataList = list(selected_data)
		if not selected_data:
			return
		
		rgbaOfSelection = self._layer._face.current_color  # rgba
		#hexColorOfSelection = self._layer.current_face_color  # hex

		# TODO: we need new function just to set the color of symbol in table		

		# grab the entire table (slow)
		myTableData = self.getLayerDataFrame(rowList=selectedDataList)
		
		# set color of selectedDataList rows
		for idx, selectedData in enumerate(selectedDataList):
			myTableData.at[idx, 'Face Color'] = rgbaOfSelection
		
		self.myTable2.myModel.mySetRow(selectedDataList, myTableData)

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
	#numSlices = 20
	minInt = 0
	maxInt = 100
	xySize = 128
	#image = np.random.randint(minInt, maxInt, (xySize,xySize,xySize))

	from skimage import data
	image = data.binary_blobs(length=128, volume_fraction=0.1, n_dim=3)
	image = image.astype(float)
	logger.info(f'image: {image.shape} {image.dtype}')
	viewer = napari.Viewer()

	#print('  viewer.dims.point:', viewer.dims.point)
	#print('  viewer.dims.order:', viewer.dims.order)

	imageLayer = viewer.add_image(image, colormap='green', blending='additive')

	# set viewer to slice zSLice
	axis = 0
	zSlice = 15
	viewer.dims.set_point(axis, zSlice)

	# test 2d points
	points2d = np.array([[50, 55], [60, 65], [70, 75]])
	pointsLayer2d = viewer.add_points(points2d,
							size=20, face_color='yellow', name='yellow carrots')
	pointsLayer2d.mode = 'select'
	pointsLayer2d.symbol = '^'

	# test 3D points
	points1 = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
	pointsLayer = viewer.add_points(points1,
							size=30, face_color='green', name='green circles')
	pointsLayer.mode = 'select'

	points2 = np.array([[zSlice, 75, 55], [zSlice, 85, 65], [zSlice, 95, 75]])
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
	ltp = LayerTablePlugin(viewer, oneLayer=None)

	area = 'right'
	name = 'Layer Table Plugin'
	dockWidget = viewer.window.add_dock_widget(ltp, area=area, name=name)

	napari.run()

# if __name__ == '__main__':
# 	run()