from pprint import pprint
from typing import Set, List
import numpy as np
import pandas as pd

from qtpy import QtCore, QtGui, QtWidgets
from napari_layer_table._data_model import pandasModel
from napari_layer_table._my_logger import logger

class myTableView(QtWidgets.QTableView):
    """Table view to display list of points in a point layer.
    """

    signalSelectionChanged = QtCore.Signal(object, object)
    """Emit when user changes row selection."""

    mtv_signalEditingRows = QtCore.Signal(object, object)
    """Emit when user edits a row,
        e.g. on pressing keyboard 'a' to toggle 'accept' column.
    
    Args:
        rows (List[int])
        df (pd.DataFrame) modified dataframe
    """
    def __init__(self, parent=None):
        super().__init__(parent)

        self.myModel = None
        
        self.blockUpdate = False
        
        self.hiddenColumnSet = set()
        self.hiddenColumnSet.add('Face Color')

        self._toggleColOnAccept = 'accept'
        # Column to toggle on keyboard 'a'

        self.setSizePolicy(QtWidgets.QSizePolicy.Expanding,
                            QtWidgets.QSizePolicy.Expanding)

        self.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers
                            | QtWidgets.QAbstractItemView.DoubleClicked)

        self.setTabKeyNavigation(False)  # 112022

        # by default focusPolicy() is strong focus QtCore.Qt.StrongFocus

        self.setSelectionBehavior(QtWidgets.QTableView.SelectRows)

        # allow discontinuous selections (with command key)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)

        self.setSortingEnabled(True)

        # to allow click on already selected row
        self.clicked.connect(self.old_on_user_click_row)

    def keyPressEvent(self, event : QtGui.QKeyEvent):
        """
        Parameters
        ----------
        event : PyQt5.QtGui.QKeyEvent
        """
        logger.info(f'user pressed key text:{event.text()}')

        _handled = False
        if event.key() == QtCore.Qt.Key_A:
            if self._toggleColOnAccept is not None:
                _handled = True
                
                # toggle selected row(s) 'accept' column
                rowList = self._getRowSelection()
                if len(rowList)>0:
                    self._toggleColumn(rowList, self._toggleColOnAccept)
                
        if not _handled:
            # if not handled, call inherited to continue propogation
            super().keyPressEvent(event)

    def _toggleColumn(self, rowList : List[int], col : str):
        """Toggle a column to True/False.
        
        e.g. on pressing keyboard 'a' to toggle 'accept' column.

        If col item is '' then it is False

        Parameters
        ----------
        rowList : list of int
        col : str
            Column name to toggle
        """
        
        logger.info(f'rowList:{rowList} col:{col}')

        # set the rows at col to True/False
        _df = self.myModel.myGetData()

        if not col in _df.columns:
            logger.warning(f'Did not find column "{col}" in model dataframe')
            return
        
        df = _df.loc[rowList].copy()
        colVals = df[col].tolist()
        for idx, colVal in enumerate(colVals):
            logger.info(f'  {idx} colVal:"{colVal}" {type(colVal)}')
            if colVal=='':
                # newColVal = True
                newColVal = 'Yes'
            else:
                newColVal = ''  # False
            colVals[idx] = newColVal
        # logger.info(f'        setting df col:{col} to {colVals}')
        df[col] = colVals

        # do not do this directly, wait until slot_editedRows(rows, df)
        # self.myModel.mySetRow(rowList, df)
        
        logger.info(f'  -->> emit mtv_signalEditingRows (rowList, df))')
        logger.info(f'    rowList:{rowList}')
        logger.info(f'    df is: {df}')

        self.myModel.mySetRow(rowList, df)

        #self.mtv_signalEditingRows.emit(rowList, df)

        #self.slot_editedRows(rowList, df)

        # 20230322, I can't get the interface to refresh after changing the model
        # logger.info('interface does not refresh after changing the model with setData')
        # self.xxx

    def setFontSize(self, fontSize : int = 11):
        """Set the table font size.
        
        This does not set the font size of cells, that is done in model data().
        """
        aFont = QtGui.QFont('Arial', fontSize)
        self.setFont(aFont)  # set the font of the cells
        self.horizontalHeader().setFont(aFont)
        self.verticalHeader().setFont(aFont)

        self.verticalHeader().setDefaultSectionSize(fontSize)  # rows
        self.verticalHeader().setMaximumSectionSize(fontSize)
        #self.horizontalHeader().setDefaultSectionSize(_fontSize)  # rows
        #self.horizontalHeader().setMaximumSectionSize(_fontSize)
        self.resizeRowsToContents()

    def slot_editedRows(self, rowList : List[int], df : pd.DataFrame):
        logger.info('received rowList and df as follows')
        print('  rowList:', rowList)
        print('  df:')
        print(df)

        print('  after user change calling myModel.mySetRoww')
        
        self.myModel.mySetRow(rowList, df)

    def _getRowSelection(self) -> List[int]:
        """Get the current row(s) selection.
        """
        selectedIndexes = [self.proxy.mapToSource(modelIndex).row()
                            for modelIndex in self.selectedIndexes()]
        
        # reduce to list of unique values
        selectedIndexes = list(set(selectedIndexes))  # to get unique values

        return selectedIndexes

    def getNumRows(self):
        """Get number of rows from the model.
        """
        return self.myModel.rowCount()
    
    def getColumns(self):
        """Get columns from model.
        """
        return self.myModel.myGetData().columns

    def clearSelection(self):
        """Over-ride inherited.
        
        Just so we can see this in our editor.
        """
        super().clearSelection()
    
    def selectRow(self, rowIdx : int):
        """Select one row.
        
        Args:
            rowIdx (int): The row index into the model.
                it is not the visual row index if table is sorted
        """
        modelIndex = self.myModel.index(rowIdx, 0)  # rowIdx is in 'model' coordinates
        visualRow = self.proxy.mapFromSource(modelIndex).row()
        logger.info(f'model rowIdx:{rowIdx} corresponds to visual row:{visualRow}')
        super().selectRow(visualRow)

    def mySelectRows(self, rows : Set[int]):
        """Make a new row selection from viewer.
        """
                        
        if self.blockUpdate:
            return
        
        # to stop event recursion
        self.blockUpdate = True
        
        selectionModel = self.selectionModel()
        if selectionModel:
            selectionModel.clear()
        
            if rows:
                indexes = [self.myModel.index(r, 0) for r in rows]  # [QModelIndex]
                visualRows = [self.proxy.mapFromSource(modelIndex) for modelIndex in indexes]

                mode = QtCore.QItemSelectionModel.Select | QtCore.QItemSelectionModel.Rows
                [self.selectionModel().select(i, mode) for i in visualRows]

                logger.warning(f'20221101 FIX SNAP TO SELECTED ROW')
                column = 0
                # error row is a QtCore.QModelIndex ???
                row = visualRows[0]
                # abb mar 22
                row = row.row()
                index = self.model().index(row, column)
                self.scrollTo(index, QtWidgets.QAbstractItemView.PositionAtTop)  # EnsureVisible

            else:
                #print('  CLEARING SELECTION')
                self.clearSelection()
        
        #
        self.blockUpdate = False

    def mySetModel_from_df(self, df : pd.DataFrame):
        myModel = pandasModel(df)
        self.mySetModel(myModel)

    def mySetModel(self, model : pandasModel):
        """ Set the model. Needed so we can show/hide columns

        Args:
            model (pd.DataFrame): DataFrame to set model to.
        """
        logger.info('')
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
        """Set a column hidden or visible.
        
        Parameters
        ----------
        colStr : str
            Column to hid or show
        hidden : bool
            If True then visible, otherwise hidden
        """
        _columns = self.myModel.myGetData().columns
        if not colStr in _columns:
            logger.error(f'did not find {colStr} in model columns')
            logger.error(f'  available columns are: {_columns}')
            return
            
        if hidden:
            self.hiddenColumnSet.add(colStr)  # will not add twice
        else:
            if colStr in self.hiddenColumnSet:
                self.hiddenColumnSet.remove(colStr)
        
        logger.info(f'self.hiddenColumnSet: {self.hiddenColumnSet}')

        self._refreshHiddenColumns()
        #colIdx = self.myModel._data.columns.get_loc(colStr)
        #self.setColumnHidden(colIdx, hidden)

    def _refreshHiddenColumns(self):
        columns = self.myModel.myGetData().columns
        for column in columns:
            colIdx = columns.get_loc(column)
            self.setColumnHidden(colIdx, column in self.hiddenColumnSet)

    def old_on_user_click_row(self, item):
        """User clicked a row.
        
        Only respond if alt+click. Used to zoom into point

        Args:
            item (QModelIndex): Model index of one row user selection.
        
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
                selected (QItemSelection):
                deselected (QItemSelection):

            Notes:
                - We are not using (selected, deselected) parameters,
                    instead are using self.selectedIndexes()
                - Connected to: self.selectionModel().selectionChanged
        """

        if self.blockUpdate:
            #self.blockUpdate = False
            return
            
        # pure PyQt
        modifiers = QtWidgets.QApplication.keyboardModifiers()
        isShift = modifiers == QtCore.Qt.ShiftModifier
        isAlt = modifiers == QtCore.Qt.AltModifier
        
        # BINGO, don't use params, use self.selectedIndexes()
        selectedIndexes = [self.proxy.mapToSource(modelIndex).row()
                            for modelIndex in self.selectedIndexes()]
        
        # reduce to list of unique values
        selectedIndexes = list(set(selectedIndexes))  # to get unique values
        
        logger.info(f'  -->> emit signalSelectionChanged selectedIndexes:{selectedIndexes} isAlt:{isAlt}')
        
        self.blockUpdate = True  # nov 3, 2022
        self.signalSelectionChanged.emit(selectedIndexes, isAlt)
        self.blockUpdate = False  # nov 3, 2022

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

