from pprint import pprint
import math
import numpy as np
import pandas as pd
from qtpy import QtCore, QtGui, QtWidgets
from napari_layer_table._my_logger import logger
from typing import List
import time

class pandasModel(QtCore.QAbstractTableModel):

    #signalMyDataChanged = QtCore.pyqtSignal(object, object, object)
    signalMyDataChanged = QtCore.Signal(object, object, object)
    """Emit on user editing a cell."""

    def __init__(self, data : pd.DataFrame):
        """Data model for a pandas dataframe.

        Args:
            data (pd.dataframe): pandas dataframe
        """
        QtCore.QAbstractTableModel.__init__(self)
        
        self._data = data

    def rowCount(self, parent=None):
        return self._data.shape[0]

    def columnCount(self, parnet=None):
        return self._data.shape[1]

    def data(self, index, role=QtCore.Qt.DisplayRole):
        """
        QtDocs: "Returns the data stored under the given role for the item referred to by the index."
        
        Parameters
        ----------
        index : PyQt5.QtCore.QModelIndex
        role : 
        """
        #logger.info(f'index:{index.row()} {index.column()} {index}')
        if index.isValid():
            if role == QtCore.Qt.ToolTipRole:
                # no tooltips here
                pass
            #elif role in [QtCore.Qt.DisplayRole, QtCore.Qt.EditRole]:
            elif role in [QtCore.Qt.DisplayRole]:
                columnName = self._data.columns[index.column()]

                realRow = index.row()
                retVal = self._data.loc[realRow, columnName]
            
                #time.sleep(0.1)

                if columnName == 'accept' and realRow==1:
                    # logger.info(' ======================================= accept column')
                    # print('  index.row():', index.row())
                    # print('  index.column():', index.column())
                    # print('  realRow:', realRow)
                    # print('  columnName:', columnName)
                    # print(f'  self._data.loc[realRow] is:')
                    
                    print(f'  (0) retVal is: "{retVal}"')

                    # comment this and toggle with 'a' does not work
                    print(self._data.loc[realRow])
                    
                    print(f'  (1) retVal is: "{retVal}"')

                    # print(f'  self._data.loc[realRow, columnName] is "{self._data.loc[realRow, columnName]}"')
                    # print('  self._data["accept"]: is')
                    # print(self._data["accept"])
                    # print('  self._data["x"]: is')
                    # print(self._data["x"])
                    # logger.info('  ========================================self._data is:')
                    # print(self._data)
                    # print('')

                    pass

                return str(retVal)
                #return str(retVal)
                #return QtCore.QVariant(retVal)

                # if columnName == 'accept':
                #     logger.info(f'orig retVal: "{retVal}" {type(retVal)}')
                #     print('  self._data:')
                #     print(self._data)

                if isinstance(retVal, np.float64):
                    retVal = float(retVal)
                elif isinstance(retVal, np.int64):
                    retVal = int(retVal)
                elif isinstance(retVal, np.bool_):
                    retVal = str(retVal)
                elif isinstance(retVal, list):
                    retVal = str(retVal)
                elif isinstance(retVal, str) and retVal == 'nan':
                    # logger.info('nan error 1')
                    retVal = ''

                elif isinstance(retVal, float) and math.isnan(retVal):
                    # don't show 'nan' in table
                    logger.info('nan error 2')
                    retVal = ''
                # added march 22
                elif isinstance(retVal, str):
                    logger.info(f'new mar 22 returning {retVal} {type(retVal)}')
                    #retVal = retVal

                if columnName == 'accept':
                    logger.info(f'  returning realRow:{realRow} columnName:{columnName} retVal: "{retVal}"')
                
                return retVal

            elif role == QtCore.Qt.FontRole:
                #realRow = self._data.index[index.row()]
                realRow = index.row()
                columnName = self._data.columns[index.column()]
                if columnName == 'Symbol':
                    # make symbols larger
                    return QtCore.QVariant(QtGui.QFont('Arial', pointSize=14))
                return QtCore.QVariant()

            elif role == QtCore.Qt.ForegroundRole:
                columnName = self._data.columns[index.column()]
                colorColumns = ['Symbol', 'Shape Type']
                #if columnName == 'Symbol':
                if columnName in colorColumns:
                    # don't get col from index, get from name
                    realRow = self._data.index[index.row()]
                    face_color = self._data.loc[realRow, 'Face Color'] # rgba
                    # TODO: face_color is sometimes a scalar
                    # try:
                    #  _color = (np.array(color.getRgb()) / 255).astype(np.float32)
                    try:
                        #r = int(face_color[0] * 255)
                        #g = int(face_color[1] * 255)
                        #b = int(face_color[2] * 255)
                        #alpha = int(face_color[3] * 255)
                        #theColor = QtCore.QVariant(QtGui.QColor(r, g, b, alpha))
                        # swap AA
                        # napari uses proper order #RRGGBBAA
                        # pyqt uses stange order #AARRGGBB
                        face_color = face_color[0] + face_color[7:9] + face_color[1:7]
                        theColor = QtCore.QVariant(QtGui.QColor(face_color))
                        return theColor
                    except (IndexError) as e:
                        logger.error(f'expecting "Face Color"" as list of rgba, got scalar of {face_color}')
                        return QtCore.QVariant()
                return QtCore.QVariant()

            elif role == QtCore.Qt.BackgroundRole:
                realRow = self._data.index[index.row()]
                
                columnName = self._data.columns[index.column()]
                if columnName == 'Face Color':
                    realRow = self._data.index[index.row()]
                    face_color = self._data.loc[realRow, 'Face Color'] # rgba
                    face_color = face_color[0] + face_color[7:9] + face_color[1:7]
                    theColor = QtCore.QVariant(QtGui.QColor(face_color))
                    return theColor         
                #elif index.row() % 2 == 0:
                elif realRow % 2 == 0:
                    return QtCore.QVariant(QtGui.QColor('#444444'))
                else:
                    return QtCore.QVariant(QtGui.QColor('#666666'))
        #
        return QtCore.QVariant()

    def setData(self, index, value, role=QtCore.Qt.EditRole):
        """Respond to user/keyboard edits.

            Qt docs: "Sets the role data for the item at index to value."

            True if value is changed. Calls layoutChanged after update.
        
        Returns:
            (bool): False if value is not different from original value.
        """
        logger.info('THIS DOES NOT GET CAALLED    !!!!!!!!!!!!!')
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
            print('  self._data.columns:', self._data.columns)
            raise

        theRet = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable

        # isEditable = True
        # isCheckbox = False
        # if isEditable:
        #     theRet |= QtCore.Qt.ItemIsEditable
        # if isCheckbox:
        #     #logger.info(f'isCheckbox {columnIdx}')
        #     theRet |= QtCore.Qt.ItemIsUserCheckable

        # flags |= QtCore.Qt.ItemIsEditable | QtCore.Qt.ItemIsUserCheckable | Qt.ItemIsEnabled

        return theRet

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
        logger.info(f'Copied table to clipboard with shape: {dfCopy.shape}')
        pprint(dfCopy)

    def myAppendRow(self, dfRow : pd.DataFrame = None):
        """Append one row to internal DataFrame.
        
        Args:
            dfRow (pd.DataFrame): One row DataFrame to append.
        """
        if dfRow.empty:
            return

        logger.info('')
        # append one empty row
        newRowIdx = len(self._data)
        self.beginInsertRows(QtCore.QModelIndex(), newRowIdx, newRowIdx)

        self._data = pd.concat([self._data, dfRow], ignore_index=True)

        self.endInsertRows()

    def myDeleteRows(self, rows: list):
        """Delete a list of rows from model.

        Args:
            rows (list of int): row indices to delete
        
        TODO: get update of rows to work
        """
        logger.info('qqqqqqq  wwwwwww')
        # minRow = min(rows)
        # maxRow = max(rows)
        # want this
        # self.beginRemoveRows(QtCore.QModelIndex(), minRow, maxRow)
        self.beginResetModel()

        self._data = self._data.drop(rows)
        self._data = self._data.reset_index(drop=True)
    
        # want this
        # self.endRemoveRows()
        self.endResetModel()

    def mySetRow(self, rowList: List[int], df: pd.DataFrame, ignoreAccept : bool = False):
        """Set a number of rows from a pandas dataframe.
        
        Args:
            rowList (list of int): row indices to change
            df (pd.Dataframe): DataFrame with new values for each row in rowList.
                Rows of dataframe correspond to enumeration of rowList list
            ignoreAccept (bool): If True then do not assign 'accept' column
                This is used when user moves a point
                Napari layer does not know about accept
        """

        # logger.info(f'  === (0) received rowList and df, df type is {type(df)}')
        # logger.info(f'                       rowList:{rowList}')
        # logger.info('  df')
        # print(df)

        # print('   before we do anything, self._data is:')
        # print(self._data)

        # print('          Mar 22, HERE IS WERE WE SET DATA AND IT DOES NOT GET UPDATED XXXXXXXXXXXXXX')

        for dfIdx, rowIdx in enumerate(rowList):
            # on switching to v2, was giving error
            # our df has row indices matching the changed rows (same as rowList)
            
            # ARRRGGGGG, 20230323, without copy this does not work !!!!!
            #oneRow = df.loc[rowIdx].copy()
            oneRow = df.loc[rowIdx]
            
            # print('(0.0) oneRow is type', type(oneRow), 'and had values of:')
            # print(oneRow)

            #IndexError: iloc cannot enlarge its target object
            try:
                # logger.info(f'  setting rowIdx:{rowIdx} to oneRow from df')
                # print(f'      setting one row to new values oneRow is:')
                # print(oneRow)
                # print(f'=== (1) row {rowIdx} before set is:')
                # print(self._data.loc[rowIdx])

                #
                # set
                #
                #oneRow['accept'] = 999
                #self._data.loc[rowIdx] = oneRow

                # accept column is owned by layer table and is not in lanapri layer

                # oneRow is a pandas.core.series.Series
                if ignoreAccept:
                    _oneRowDict = oneRow.to_dict()
                    for k,v in _oneRowDict.items():
                        if k == 'accept':
                            continue
                        self._data.loc[rowIdx, k] = v
                else:
                    self._data.loc[rowIdx] = oneRow
                
                # print('  === (2) row after set is:')
                # print(self._data.loc[rowIdx])

                # print('  === (2.5) "accept" col after set self._data["accept"] is')
                # print(self._data['accept'])
                # print(self._data['x'])

                # print('   self._data.columns is:')
                # print(self._data.columns)

                # print('  === (2) self._data after set is:')
                # print(self._data)

            except (ValueError) as e:
                logger.error(e)
                logger.error(f'rowIdx: {rowIdx}')
                logger.error(f'oneRow: {oneRow}')

            startIdx = self.index(rowIdx, 0)  # QModelIndex
            stopIdx = self.index(rowIdx, self._data.shape[1]-1)  # QModelIndex
            
            #stopIdx = self.index(rowIdx+1, self._data.shape[1]-1)  # QModelIndex

            #print('  startIdx:', startIdx.row(), startIdx.column())
            #print('  stopIdx:', stopIdx.row(), stopIdx.column())
            
            # logger.info(f'  XXXXXXXX startIdx:{startIdx.row()} {startIdx.column()}')
            # logger.info(f'  XXXXXXXX stopIdx:{stopIdx.row()} {stopIdx.column()}')

            # does nothing
            #self.dataChanged.emit(startIdx, stopIdx)
            
            # print('           -->> self.dataChanged.emit with:')
            # print('            startIdx:', startIdx.row(), startIdx.column())
            # print('            stopIdx:', stopIdx.row(), stopIdx.column())
            #self.dataChanged.emit(startIdx, stopIdx, [QtCore.Qt.DisplayRole])
            self.dataChanged.emit(startIdx, stopIdx)

            # logger.info('(4) at end')
            # print(self._data)
            # print(self._data['accept'])

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

    def myGetData(self):
        return self._data