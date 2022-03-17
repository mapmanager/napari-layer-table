from pprint import pprint
import math
import numpy as np
import pandas as pd
from PyQt5 import QtCore, QtGui, QtWidgets

import logging
logger = logging.getLogger()

class myTableView(QtWidgets.QTableView):
	"""Table view to display list of files.

	TODO: Try and implement the first column (filename) as a frozen column.

	See: https://doc.qt.io/qt-5/qtwidgets-itemviews-frozencolumn-example.html
	"""

	signalSelectionChanged = QtCore.pyqtSignal(object)
	
	'''
	signalDuplicateRow = QtCore.pyqtSignal(object) # row index
	signalDeleteRow = QtCore.pyqtSignal(object) # row index
	#signalRefreshTabe = QtCore.pyqtSignal(object) # row index
	signalCopyTable = QtCore.pyqtSignal()
	signalFindNewFiles = QtCore.pyqtSignal()
	signalSaveFileTable = QtCore.pyqtSignal()
	'''

	def __init__(self, parent=None):
		"""
		"""
		super(myTableView, self).__init__(parent)

		self.myModel = None
		
		#self.doIncludeCheckbox = False  # todo: turn this on
		# need a local reference to delegate else 'segmentation fault'
		#self.keepCheckBoxDelegate = myCheckBoxDelegate(None)

		#self.setFont(QtGui.QFont('Arial', 10))
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
							QtWidgets.QSizePolicy.Expanding)
		self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

		self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers
							| QtWidgets.QAbstractItemView.DoubleClicked)

		# does not do anything
		#self.resizeColumnsToContents()

		self.setSortingEnabled(True)

		# allow discontinuous selections (with command key)
		self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

	def getNumRows(self):
		"""Get number of rows from the model.
		"""
		return self.myModel.rowCount()
	
	def clearSelection(self):
		"""Over-ride inherited.
		
		Just so we can see this in our editor.
		"""
		super().clearSelection()
	
	def selectRow(self, rowIdx):
		"""
		over-ride to get sort order right
		
		rowIdx is index into model
		it is not the visual row index if table is sorted
		we need to find the actual table row with data index {rowIdx}
		"""

		modelIndex = self.myModel.index(rowIdx, 0)  # rowIdx is in 'model' coordinates
		visualRow = self.proxy.mapFromSource(modelIndex).row()

		logger.info(f'model rowIdx:{rowIdx} corresponds to visual row:{visualRow}')

		# might work, need to also have de-select (somewhere else???)
		# mode = QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
		#self.selectionModel().select(modelIndex, mode)

		super().selectRow(visualRow)

	def mySetModel(self, model):
		"""
		Set the model. Needed so we can show/hide columns
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
		
		# self.myModel.layoutChanged.emit()
		# self.myModel.modelReset.emit()

		# was this
		# self.setModel(model)

		#self.selectionModel().selectionChanged.disconnect(self.on_selectionChanged)
		'''
		try:
			selectionModel = self.selectionModel()
			if selectionModel is not None:
				selectionModel.selectionChanged.disconnect(self.on_selectionChanged)
		except(TypeError) as e:
			logger.error(e)

		'''
		self.selectionModel().selectionChanged.connect(self.on_selectionChanged)

	'''
	# trying to use this to remove tooltip when it comes up as empty ''
	def viewportEvent(self, event):
		logger.info('')
		return True
	'''

	def on_selectionChanged(self, selected, deselected):
		"""
			Args:
				selected, deselected (QItemSelection)

			TODO: This is always called twice ???
		"""
		
		modelIndexList = selected.indexes()
		
		#QItemSelectionModel
		#modelIndexList = self.selectionModel().selectedRows()
		# was this
		#modelIndexList = self.selectionModel().selectedIndexes()
		
		#for modelIndex in modelIndexList:
		#	print('  modelIndex:', modelIndex, type(modelIndex))  # QModelIndex
		
		# use self.proxy.mapToSource to map from sort to 'real' order
		selectedRowList = [self.proxy.mapToSource(modelIndex).row()
							for modelIndex in modelIndexList]
				
		# convert to sort order
		#selectedRowList = [
		#	self.model()._data.index[rowIdx]
		#	for rowIdx in selectedRowList0]

		if len(selectedRowList) > 0:
			selectedRowList = [selectedRowList[0]]
		
		logger.info('')
		print('  selectedRowList:', selectedRowList)

		self.signalSelectionChanged.emit(selectedRowList)
	
	def old_contextMenuEvent(self, event):
		"""
		Show a context menu on mouse right-click
		"""

		contextMenu = QtWidgets.QMenu(self)
		
		# add menu item actions
		showCoordinates = contextMenu.addAction("Show Coordinates")
		showProperties = contextMenu.addAction("Show Properties")
		contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table")

		# show the
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))
		#logger.info(f'  action:{action}')
		if action == showCoordinates:
			pass
			#self.signalDuplicateRow.emit(selectedRow)
		elif action is not None:
			logger.warning(f'action not taken "{action}"')

		'''
		contextMenu = QtWidgets.QMenu(self)
		duplicateRow = contextMenu.addAction("Duplicate Row")
		contextMenu.addSeparator()
		deleteRow = contextMenu.addAction("Delete Row")
		contextMenu.addSeparator()
		copyTable = contextMenu.addAction("Copy Table")
		contextMenu.addSeparator()
		findNewFiles = contextMenu.addAction("Sync With Folder")
		contextMenu.addSeparator()
		saveTable = contextMenu.addAction("Save Table")
		#
		action = contextMenu.exec_(self.mapToGlobal(event.pos()))
		#logger.info(f'  action:{action}')
		if action == duplicateRow:
			#print('  todo: duplicateRow')
			tmp = self.selectedIndexes()
			if len(tmp)>0:
				selectedRow = tmp[0].row()
				self.signalDuplicateRow.emit(selectedRow)
		elif action == deleteRow:
			#print('  todo: deleteRow')
			tmp = self.selectedIndexes()
			if len(tmp)>0:
				selectedRow = tmp[0].row()
				self.signalDeleteRow.emit(selectedRow)
			else:
				logger.warning('no selection?')
		elif action == copyTable:
			#print('  todo: copyTable')
			self.signalCopyTable.emit()
		elif action == findNewFiles:
			#print('  todo: findNewFiles')
			self.signalFindNewFiles.emit()
		elif action == saveTable:
			#print('  todo: saveTable')
			self.signalSaveFileTable.emit()
		else:
			logger.warning(f'action not taken "{action}"')
		'''

class pandasModel(QtCore.QAbstractTableModel):

	signalMyDataChanged = QtCore.pyqtSignal(object, object, object)
	"""Emit on user editing a cell."""

	def __init__(self, data):
		"""
		Data model for a pandas dataframe

		Args:
			data (dataframe): pandas dataframe
		"""
		QtCore.QAbstractTableModel.__init__(self)

		self.isDirty = False

		self._data = data

		#self.setSortingEnabled(True)

	'''
	def modelReset(self):
		print('modelReset()')
	'''

	def rowCount(self, parent=None):
		return self._data.shape[0]

	def columnCount(self, parnet=None):
		return self._data.shape[1]

	def data(self, index, role=QtCore.Qt.DisplayRole):
		if index.isValid():
			if role == QtCore.Qt.ToolTipRole:
				# removed
				# swapped sanpy.bDetection.defaultDetection to a class
				# do not want to instantiate every time
				'''
				# get default value from bAnalysis
				defaultDetection = sanpy.bDetection.defaultDetection
				columnName = self._data.columns[index.column()]
				toolTip = QtCore.QVariant()  # empty tooltip
				try:
					toolTip = str(defaultDetection[columnName]['defaultValue'])
					toolTip += ': ' + defaultDetection[columnName]['description']
				except (KeyError):
					pass
				return toolTip
				'''
			elif role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
				columnName = self._data.columns[index.column()]

				# don't get col from index, get from name
				#realRow = self._data.index[index.row()]
				realRow = index.row()
				retVal = self._data.loc[realRow, columnName]
				if isinstance(retVal, np.float64):
					retVal = float(retVal)
				elif isinstance(retVal, np.int64):
					retVal = int(retVal)
				elif isinstance(retVal, np.bool_):
					retVal = str(retVal)
				elif isinstance(retVal, str) and retVal == 'nan':
					retVal = ''

				if isinstance(retVal, float) and math.isnan(retVal):
					# don't show 'nan' in table
					retVal = ''
				return retVal

			elif role == QtCore.Qt.CheckStateRole:
				columnName = self._data.columns[index.column()]
				#realRow = self._data.index[index.row()]
				realRow = index.row()
				retVal = self._data.loc[realRow, columnName]
				if columnName == 'I':
					if retVal:
						return QtCore.Qt.Checked
					else:
						return QtCore.Qt.Unchecked
				return QtCore.QVariant()

			elif role == QtCore.Qt.FontRole:
				#realRow = self._data.index[index.row()]
				realRow = index.row()
				columnName = self._data.columns[index.column()]
				if columnName == 'L':
					if self._data.isLoaded(realRow):  # or self._data.isSaved(realRow):
						return QtCore.QVariant(QtGui.QFont('Arial', pointSize=32))
				elif columnName == 'A':
					if self._data.isAnalyzed(realRow):  # or self._data.isSaved(realRow):
						return QtCore.QVariant(QtGui.QFont('Arial', pointSize=32))
				elif columnName == 'S':
					if self._data.isSaved(realRow):
						return QtCore.QVariant(QtGui.QFont('Arial', pointSize=32))
				return QtCore.QVariant()
			elif role == QtCore.Qt.ForegroundRole:
				columnName = self._data.columns[index.column()]
				if columnName == 'symbol':
					# don't get col from index, get from name
					realRow = self._data.index[index.row()]
					face_color = self._data.loc[realRow, 'face_color']
					#retVal = self._data.loc[realRow, columnName]
					#print('xxx retVal:', retVal)
					r = face_color[0] * 255
					g = face_color[1] * 255
					b = face_color[2] * 255
					alpha = face_color[3] * 255
					return QtCore.QVariant(QtGui.QColor(r, g, b, alpha))
					#return QtCore.QVariant(QtGui.QColor(255, retVal[1], retVal[2]))
				return QtCore.QVariant()
			elif role == QtCore.Qt.BackgroundRole:
				if index.row() % 2 == 0:
					return QtCore.QVariant(QtGui.QColor('#444444'))
				else:
					return QtCore.QVariant(QtGui.QColor('#666666'))

		#
		return QtCore.QVariant()

	# def update(self, dataIn):
	# 	print('  pandasModel.update() dataIn:', dataIn)

	def setData(self, index, value, role=QtCore.Qt.EditRole):
		"""
		Respond to user/keyboard edits.

		True if value is changed. Calls layoutChanged after update.
		Returns:
			False if value is not different from original value.
		"""
		if index.isValid():
			if role == QtCore.Qt.EditRole:
				rowIdx = index.row()
				columnIdx = index.column()

				# use to check isEditable
				'''
				columnName = self._data.columns[columnIdx]
				if self.isAnalysisDir:
					isEditable = self._data.columnIsEditable(columnName)
					if not isEditable:
						return False
				'''

				# in general, DO NOT USE iLoc, use loc as it is absolute (i,j)
				columnName = self._data.columns[index.column()]
				#realRow = self._data.index[index.row()]
				realRow = index.row()
				v = self._data.loc[realRow, columnName]
				#logger.info(f'Existing value for column "{columnName}" is v: "{v}" {type(v)}')
				#logger.info(f'  proposed value:"{value}" {type(value)}')
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
				#logger.info(f'  New value for column "{columnName}" is "{value}" {type(value)}')
				self._data.loc[realRow, columnName] = value
				#self._data.iloc[rowIdx, columnIdx] = value

				# emit change
				emitRowDict = self.myGetRowDict(realRow)
				self.signalMyDataChanged.emit(columnName, value, emitRowDict)

				self.isDirty = True
				return True
			elif role == QtCore.Qt.CheckStateRole:
				rowIdx = index.row()
				columnIdx = index.column()
				columnName = self._data.columns[index.column()]
				#realRow = self._data.index[index.row()]
				realRow = index.row()
				logger.info(f'CheckStateRole column:{columnName} value:{value}')
				if columnName == 'I':
					self._data.loc[realRow, columnName] = value == 2
					self.dataChanged.emit(index, index)
					return QtCore.Qt.Checked

		#
		return QtCore.QVariant()

	def flags(self, index):
		if not index.isValid():
			logger.info('not valid')

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
		'''
		if self.isAnalysisDir:
			# columnsDict is a big dict, one key for each column, in analysisDir.sanpyColumns
			isEditable = self._data.columnIsEditable(columnName)
			isCheckbox = self._data.columnIsCheckBox(columnName)
		'''
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

	def sort(self, Ncol, order):
		logger.info(f'Ncol:{Ncol} order:{order}')
		self.layoutAboutToBeChanged.emit()
		self._data = self._data.sort_values(self._data.columns[Ncol], ascending=not order)
		self.layoutChanged.emit()

	def myCopyTable(self):
		"""
		Copy model data to clipboard.
		"""
		dfCopy = self._data.copy()
		dfCopy.to_clipboard(sep='\t', index=False)
		logger.info(f'Copied table to clipboard with num rows: {dfCopy.shape}')
		print('  TODO: make sure table is not garbled. In particular list items and columns with spaces')
		
	def myAppendRow(self, dfRow=None):
		"""
		Append one row to internal DataFrame
		
		Args:
			dfRow (pd.DataFrame)
		"""
		# append one empty row
		newRowIdx = len(self._data)
		self.beginInsertRows(QtCore.QModelIndex(), newRowIdx, newRowIdx)

		#df = self._data
		#df = df.append(pd.Series(), ignore_index=True)
		#df = df.reset_index(drop=True)
		#self._data = df

		#self._data.append(dfRow, ignore_index=True)

		self._data = pd.concat([self._data, dfRow], ignore_index=True)

		self.endInsertRows()

	def myDeleteRow(self, rowIdx):
		'''
		# prompt the user for (ok, cancel)
		msg = QtWidgets.QMessageBox()
		msg.setStandardButtons(QtWidgets.QMessageBox.Ok | QtWidgets.QMessageBox.Cancel)
		msg.setDefaultButton(QtWidgets.QMessageBox.Ok)
		msg.setIcon(QtWidgets.QMessageBox.Warning)
		msg.setText(f'Are you sure you want to delete row {rowIdx}?')
		msg.setWindowTitle("Delete Row")
		returnValue = msg.exec_()
		if returnValue == QtWidgets.QMessageBox.Ok:
		'''
		if True:
			
			#logger.info(f'rowIdx:{rowIdx} {type(rowIdx)}')
			
			self.beginRemoveRows(QtCore.QModelIndex(), rowIdx, rowIdx)
						
			#print('  before delete:')
			#pprint(self._data)
			
			# TODO: not sure if we should do assignment (like here) or in place ???
			self._data = self._data.drop([rowIdx])
			self._data = self._data.reset_index(drop=True)
			
			#print('  after delete:')
			#pprint(self._data)

			#
			self.endRemoveRows()

	def mySetRow(self, rowList, df):
		"""Set a number of rows from a pandas dataframe
		
		Args:
			rowList (list of int): row indices to change
			df (pd.Dataframe) new values, EXPLAIN THIS
		"""
	
		logger.info(f'rowList:{rowList}')
		print('  from df:')
		pprint(df)

		for dfIdx, rowIdx in enumerate(rowList):
			oneRow = df.loc[dfIdx]
			self._data.iloc[rowIdx] = oneRow  # needed because we are passed small df that changed

			# TODO: Is there a more simple way?			
			# TODO: I do not understand how to signal a data change in one entire row ???

			startIdx = self.index(rowIdx, 0)  # QModelIndex
			stopIdx = self.index(rowIdx, self._data.shape[1]-1)  # QModelIndex
			
			self.dataChanged.emit(startIdx, stopIdx)

			# this is not working
			#self.dataChanged.emit(startIdx, startIdx, [QtCore.Qt.EditRole,])
			
			# try to refresh eveything (does not work)
			# self.dataChanged.emit(QtCore.QModelIndex, QtCore.QModelIndex, [])

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

	def old_myGetRowDict(self, rowIdx):
		"""
		return a dict with selected row as dict (includes detection parameters)
		"""
		theRet = {}
		for column in self._data.columns:
			theRet[column] = self.old_myGetValue(rowIdx, column)
		return theRet

	def old_myGetColumnList(self, col):
		# return all values in column as a list
		colList = self._data[col].tolist()
		return colList

	def old_mySaveDb(self, path):
		#print('pandasModel.mySaveDb() path:', path)
		#logger.info(f'Saving csv {path}')
		self._data.to_csv(path, index=False)
		self.isDirty = False
