from pprint import pprint
import math
import numpy as np
import pandas as pd

from qtpy import QtCore, QtGui, QtWidgets

from napari_layer_table._my_logger import logger

class myTableView(QtWidgets.QTableView):
	"""Table view to display list of points in a point layer.
	"""

	signalSelectionChanged = QtCore.Signal(object, object)
	"""Emit when user changes row selection."""

	def __init__(self, parent=None):
		super(myTableView, self).__init__(parent)

		self.myModel = None
		
		self.blockUpdate = False
		
		self.hiddenColumnSet = set()
		self.hiddenColumnSet.add('Face Color')

		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
							QtWidgets.QSizePolicy.Expanding)
		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers
							| QtWidgets.QAbstractItemView.DoubleClicked)

		self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

		# allow discontinuous selections (with command key)
		self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

		self.setSortingEnabled(True)

		# to allow click on already selected row
		self.clicked.connect(self.old_on_user_click_row)

	def getNumRows(self):
		"""Get number of rows from the model.
		"""
		return self.myModel.rowCount()
	
	def getColumns(self):
		"""Get columns from model.
		"""
		return self.myModel._data.columns

	def clearSelection(self):
		"""Over-ride inherited.
		
		Just so we can see this in our editor.
		"""
		super().clearSelection()
	
	def selectRow(self, rowIdx : int):
		"""Select one row.
		
		Args:
			rowIdx (int) The row index into the model.
				it is not the visual row index if table is sorted
		"""
		modelIndex = self.myModel.index(rowIdx, 0)  # rowIdx is in 'model' coordinates
		visualRow = self.proxy.mapFromSource(modelIndex).row()
		logger.info(f'model rowIdx:{rowIdx} corresponds to visual row:{visualRow}')
		super().selectRow(visualRow)

	def mySelectRows(self, rows : set):
		"""Make a new row selection from viewer.
		"""
				
		# to stop event recursion
		self.blockUpdate = True
		
		self.selectionModel().clear()
		
		if rows:
			indexes = [self.myModel.index(r, 0) for r in rows]  # [QModelIndex]
			visualRows = [self.proxy.mapFromSource(modelIndex) for modelIndex in indexes]

			mode = QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
			[self.selectionModel().select(i, mode) for i in visualRows]

		else:
			#print('  CLEARING SELECTION')
			self.clearSelection()

	def mySetModel(self, model):
		""" Set the model. Needed so we can show/hide columns

		Args:
			model (pandasModel)
		"""
		self.myModel = model
		
		selectionModel = self.selectionModel()
		if selectionModel is not None:
			selectionModel.selectionChanged.disconnect(self.on_selectionChanged)

		self.proxy = QtCore.QSortFilterProxyModel()
		self.proxy.setSourceModel(model)

		self.myModel.beginResetModel()
		self.setModel(self.proxy)
		self.myModel.endResetModel()
		
		self.selectionModel().selectionChanged.connect(self.on_selectionChanged)
		#self.selectionModel().currentChanged.connect(self.old_on_currentChanged)

		# refresh hidden columns, only usefull when we first build interface
		self._refreshHiddenColumns()

	def mySetColumnHidden(self, colStr : str, hidden : bool):
		if hidden:
			self.hiddenColumnSet.add(colStr)  # will not add twice
		else:
			if colStr in self.hiddenColumnSet:
				self.hiddenColumnSet.remove(colStr)
		self._refreshHiddenColumns()
		#colIdx = self.myModel._data.columns.get_loc(colStr)
		#self.setColumnHidden(colIdx, hidden)

	def _refreshHiddenColumns(self):
		for column in self.myModel._data.columns:
			colIdx = self.myModel._data.columns.get_loc(column)
			self.setColumnHidden(colIdx, column in self.hiddenColumnSet)

	def old_on_user_click_row(self, item):
		"""User clicked a row.
		
		Only respond if alt+click. Used to zoom into point

		Args:
			item (QModelIndex)
		
		TODO:
			This is used so alt+click (option on macos) will work
				even in row is already selected. This is causing 'double'
				selection callbacks with on_selectionChanged()
		"""				
		# pure PyQt
		modifiers = QtWidgets.QApplication.keyboardModifiers()
		#isShift = modifiers == QtCore.Qt.ShiftModifier
		isAlt = modifiers == QtCore.Qt.AltModifier
		
		if not isAlt:
			return
		
		row = self.proxy.mapToSource(item).row()
		logger.info(f'row:{row}')

		selectedRowList = [row]
		self.signalSelectionChanged.emit(selectedRowList, isAlt)

	def on_selectionChanged(self, selected, deselected):
		"""Respond to change in selection.

			Args:
				selected, deselected (QItemSelection)

			Notes:
				connected to:
				self.selectionModel().selectionChanged
		"""

		if self.blockUpdate:
			self.blockUpdate = False
			return
			
		# pure PyQt
		modifiers = QtWidgets.QApplication.keyboardModifiers()
		isShift = modifiers == QtCore.Qt.ShiftModifier
		isAlt = modifiers == QtCore.Qt.AltModifier
		
		# BINGO, don't use params, use self.selectedIndexes()
		selectedIndexes = [self.proxy.mapToSource(modelIndex).row() for modelIndex in self.selectedIndexes()]
		
		# reduce to list of unique values
		selectedIndexes = set(selectedIndexes)  # to get unique values
		selectedIndexes = list(selectedIndexes)

		logger.info(f'selectedIndexes:{selectedIndexes}')
		
		
		self.signalSelectionChanged.emit(selectedIndexes, isAlt)

	'''
	def old_on_currentChanged(self, current, previous):
		"""
		
		Args:
			current (QtCore.QModelIndex)
		"""
		modifiers = QtWidgets.QApplication.keyboardModifiers()
		isShift = modifiers == QtCore.Qt.ShiftModifier

		logger.info('')
		print(f'  current:{current.row()}')
		print(f'  previous:{previous.row()}')

		selectedRows = self.selectionModel().selectedRows()
		print(f'  selectedRows:{selectedRows}')

		#self.signalSelectionChanged.emit(selectedRowList, isShift)
	'''

class pandasModel(QtCore.QAbstractTableModel):

	#signalMyDataChanged = QtCore.pyqtSignal(object, object, object)
	signalMyDataChanged = QtCore.Signal(object, object, object)
	"""Emit on user editing a cell."""

	def __init__(self, data):
		"""Data model for a pandas dataframe.

		Args:
			data (dataframe): pandas dataframe
		"""
		QtCore.QAbstractTableModel.__init__(self)
		
		self._data = data

	def rowCount(self, parent=None):
		return self._data.shape[0]

	def columnCount(self, parnet=None):
		return self._data.shape[1]

	def data(self, index, role=QtCore.Qt.DisplayRole):
		if index.isValid():
			if role == QtCore.Qt.ToolTipRole:
				# no tooltips here
				pass
			elif role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
				columnName = self._data.columns[index.column()]

				realRow = index.row()
				retVal = self._data.loc[realRow, columnName]
				if isinstance(retVal, np.float64):
					retVal = float(retVal)
				elif isinstance(retVal, np.int64):
					retVal = int(retVal)
				elif isinstance(retVal, np.bool_):
					retVal = str(retVal)
				elif isinstance(retVal, list):
					retVal = str(retVal)
				elif isinstance(retVal, str) and retVal == 'nan':
					retVal = ''

				if isinstance(retVal, float) and math.isnan(retVal):
					# don't show 'nan' in table
					retVal = ''
				return retVal

			elif role == QtCore.Qt.FontRole:
				#realRow = self._data.index[index.row()]
				realRow = index.row()
				columnName = self._data.columns[index.column()]
				if columnName == 'Symbol':
					# make symbols larger
					return QtCore.QVariant(QtGui.QFont('Arial', pointSize=16))
				return QtCore.QVariant()

			elif role == QtCore.Qt.ForegroundRole:
				columnName = self._data.columns[index.column()]
				if columnName == 'Symbol':
					# don't get col from index, get from name
					realRow = self._data.index[index.row()]
					face_color = self._data.loc[realRow, 'Face Color'] # rgba
					# TODO: face_color is sometimes a scalar
					# try:
					#  _color = (np.array(color.getRgb()) / 255).astype(np.float32)
					try:
						r = face_color[0] * 255
						g = face_color[1] * 255
						b = face_color[2] * 255
						alpha = face_color[3] * 255
						theColor = QtCore.QVariant(QtGui.QColor(r, g, b, alpha))
						return theColor
					except (IndexError) as e:
						logger.error(f'expecting "Face Color"" as list of rgba, got scalar of {face_color}')
						return QtCore.QVariant()
				return QtCore.QVariant()

			elif role == QtCore.Qt.BackgroundRole:
				if index.row() % 2 == 0:
					return QtCore.QVariant(QtGui.QColor('#444444'))
				else:
					return QtCore.QVariant(QtGui.QColor('#666666'))
		#
		return QtCore.QVariant()

	def old_setData(self, index, value, role=QtCore.Qt.EditRole):
		"""Respond to user/keyboard edits.

			True if value is changed. Calls layoutChanged after update.
		
		Returns:
			False if value is not different from original value.
		"""
		if index.isValid():
			if role == QtCore.Qt.EditRole:
				rowIdx = index.row()
				columnIdx = index.column()

				# in general, DO NOT USE iloc, use loc as it is absolute (i,j)
				columnName = self._data.columns[index.column()]
				realRow = index.row()
				v = self._data.loc[realRow, columnName]
				if isinstance(v, np.float64):
					try:
						if value == '':
							value = np.nan
						else:
							value = float(value)
					except (ValueError) as e:
						logger.info('  No action -->> please enter a number')
						#self.signalUpdateStatus.emit('Please enter a number')
						return False

				# set
				self._data.loc[realRow, columnName] = value
				#self._data.iloc[rowIdx, columnIdx] = value

				# emit change
				emitRowDict = self.myGetRowDict(realRow)
				self.signalMyDataChanged.emit(columnName, value, emitRowDict)

				return True

		#
		return QtCore.QVariant()

	def flags(self, index):
		if not index.isValid():
			logger.warning(f'index is not valid: {index}')

		rowIdx = index.row()
		columnIdx = index.column()

		# use to check isEditable
		try:
			columnName = self._data.columns[columnIdx]
		except(IndexError) as e:
			logger.warning(f'IndexError for columnIdx:{columnIdx} len:{len(self._data.columns)}')
			print('self._data.columns:', self._data.columns)
			raise

		theRet = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
		isEditable = False
		isCheckbox = False
		if isEditable:
			theRet |= QtCore.Qt.ItemIsEditable
		if isCheckbox:
			#logger.info(f'isCheckbox {columnIdx}')
			theRet |= QtCore.Qt.ItemIsUserCheckable
		#
		return theRet

		# flags |= QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable | Qt.ItemIsEnabled

	def headerData(self, col, orientation, role):
		if role == QtCore.Qt.DisplayRole:
			if orientation == QtCore.Qt.Horizontal:
				try:
					return self._data.columns[col]
				except(IndexError) as e:
					logger.warning(f'IndexError for col:{col} len:{len(self._data.columns)}, shape:{self._data.shape}')
					#raise
			elif orientation == QtCore.Qt.Vertical:
				# this is to show pandas 'index' column
				return col

		return QtCore.QVariant()

	def old_sort(self, Ncol, order):
		"""Not used when we have a sort model proxy.
		"""
		logger.info(f'Ncol:{Ncol} order:{order}')
		self.layoutAboutToBeChanged.emit()
		self._data = self._data.sort_values(self._data.columns[Ncol], ascending=not order)
		self.layoutChanged.emit()

	def myCopyTable(self):
		"""Copy model data to clipboard.
		"""
		dfCopy = self._data.copy()
		dfCopy.to_clipboard(sep='\t', index=False)
		logger.info(f'Copied table to clipboard with num rows: {dfCopy.shape}')
		print('  TODO: make sure table is not garbled. In particular list items and columns with spaces')
		
	def myAppendRow(self, dfRow=None):
		"""Append one row to internal DataFrame.
		
		Args:
			dfRow (pd.DataFrame)
		"""
		# append one empty row
		newRowIdx = len(self._data)
		self.beginInsertRows(QtCore.QModelIndex(), newRowIdx, newRowIdx)

		self._data = pd.concat([self._data, dfRow], ignore_index=True)

		self.endInsertRows()

	def myDeleteRows(self, rows :list):
		"""Delete a list of rows from model.
		
		TODO: get update of rows to work
		"""
		minRow = min(rows)
		maxRow = max(rows)

		# want this
		# self.beginRemoveRows(QtCore.QModelIndex(), minRow, maxRow)
		self.beginResetModel()

		self._data = self._data.drop(rows)
		self._data = self._data.reset_index(drop=True)
	
		# want this
		# self.endRemoveRows()
		self.endResetModel()

	def mySetRow(self, rowList : list, df: pd.DataFrame):
		"""Set a number of rows from a pandas dataframe.
		
		Args:
			rowList (list of int): row indices to change
			df (pd.Dataframe) new values, EXPLAIN THIS
				rows of dataframe correspond to enumeration of rowList list
		"""
	
		#logger.info(f'rowList:{rowList}')
		#print('  from df:')
		#pprint(df)

		logger.info(f'rowList:{rowList}')
		
		for dfIdx, rowIdx in enumerate(rowList):
			oneRow = df.loc[dfIdx]
			self._data.iloc[rowIdx] = oneRow  # needed because we are passed small df that changed

			startIdx = self.index(rowIdx, 0)  # QModelIndex
			stopIdx = self.index(rowIdx, self._data.shape[1]-1)  # QModelIndex
			
			self.dataChanged.emit(startIdx, stopIdx)

		return True

	def old_myGetValue(self, rowIdx, colStr):
		val = None
		if colStr not in self._data.columns:  #  columns is a list
			logger.error(f'Got bad column name: "{colStr}"')
		elif len(self._data)-1 < rowIdx:
			logger.error(f'Got bad row:{rowIdx} from possible {len(self._data)}')
		else:
			val = self._data.loc[rowIdx, colStr]
		return val
