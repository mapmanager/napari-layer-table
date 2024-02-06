from napari_layer_table import pandasModel, myTableView
import numpy as np
import pandas as pd
import pytest
import logging

from qtpy import QtCore, QtGui, QtWidgets

threeDimPoints = np.array([[50, 55, 66], [50, 60, 65], [50, 79, 85], [50, 68, 90]])
twoDimPoints = np.array([[50, 55], [60, 65], [70, 75], [80, 85]])
pointWithoutCoordinates = np.array([[]])
noPoints = np.array([])

get_num_rows_test_cases = [
    (twoDimPoints, 4), # 2D array
    (threeDimPoints, 4), # 3D array
    (pointWithoutCoordinates, 1), # (0, 0) -> 2D array: 1 row, 0 columns
    (noPoints, 0), # (0,) -> 1D array: 0 rows, no columns
]

get_num_columns_test_cases = [
    (twoDimPoints, pd.DataFrame(twoDimPoints).columns), # 2D array
    (threeDimPoints, pd.DataFrame(threeDimPoints).columns), # 3D array
    (pointWithoutCoordinates, pd.DataFrame(pointWithoutCoordinates).columns), # (0, 0) -> 2D array: 1 row, 0 columns
    (noPoints, pd.DataFrame(noPoints).columns), # (0,) -> 1D array: 0 rows, no columns
]

select_row_test_cases = [
    (twoDimPoints, 1, 1), # 2D array
    (threeDimPoints, 0, 0), # 3D array
]

select_rows_test_cases = [
    (twoDimPoints, {2}, {2}), # 1 row selected
    (twoDimPoints, {0, 2}, {0, 2}), # non-continuous selection
    (threeDimPoints, {0, 1, 2}, {0, 1, 2}), # continuous selection
    (threeDimPoints, {0, 1, 2, 3}, {0, 1, 2, 3}), # all rows selected
    (twoDimPoints, {}, {})
]

my_set_model_test_cases = [
    (twoDimPoints, pd.DataFrame(twoDimPoints)), # 2D array
    (threeDimPoints, pd.DataFrame(threeDimPoints)), # 3D array
    (pointWithoutCoordinates, pd.DataFrame(pointWithoutCoordinates)), # (0, 0) -> 2D array: 1 row, 0 columns
    (noPoints, pd.DataFrame(noPoints)), # (0,) -> 1D array: 0 rows, no columns
]

# dataframe, colStr, hidden
my_set_column_hidden_test_cases = [
    (pd.DataFrame([
          [1, 9, 2],
          [1, 0, -1],
        ], columns = ['x', 'y', 'z']), 'x', True),
    (pd.DataFrame([
          [1, 2],
          [1, -1],
        ], columns = ['x', 'y']), 'y', False),
    # (pd.DataFrame([
    #       [1, 2],
    #       [1, -1],
    #     ], columns = ['x', 'y']), 'Symbol', True)  # TODO: Symbol was 'w'?
]

my_set_column_hidden_for_unhiding_hidden_columns_test_cases = [
    (pd.DataFrame([
          [1, 9, 2],
          [1, 0, -1],
        ], columns = ['x', 'y', 'z']), 'x'),
    (pd.DataFrame([
          [1, 2],
          [1, -1],
        ], columns = ['x', 'y']), 'y'),
]


@pytest.fixture
def table(qtbot):
    """
    just by putting `qtbot` in the list of arguments
    pytest-qt will start up an event loop for you

    A word about Pytest fixtures:
    pytest fixtures are functions attached to the tests which run 
    before the test function is executed. 

    pytest fixture function is automatically called by the pytest framework 
    when the name of the argument and the fixture is the same.
    """
    tableView = myTableView()

    # qtbot provides a convenient addWidget method that will ensure 
    # that the widget gets closed at the end of the test.
    qtbot.addWidget(tableView)
    return tableView


def test_init(table):
    assert table is not None
    assert 'Face Color' in table.hiddenColumnSet
    assert table.myModel is None
    assert table.blockUpdate == False

@pytest.mark.parametrize('points, expected_row_count', get_num_rows_test_cases)
def test_get_num_rows(table, points, expected_row_count):
    # Arrange
    data = pd.DataFrame(points)
    data_model = pandasModel(data)
    table.mySetModel(data_model)

    # Act
    numOfRows = table.getNumRows()

    # Assert
    assert numOfRows == expected_row_count

@pytest.mark.parametrize('points, expected_columns', get_num_columns_test_cases)
def test_get_columns(table, points, expected_columns):
    # Arrange
    data = pd.DataFrame(points)
    data_model = pandasModel(data)
    table.mySetModel(data_model)

    # Act
    columns = table.getColumns()

    # Assert
    assert columns.equals(expected_columns)

def test_clear_selection(table):
    # Act
    table.clearSelection()

    # Assert
    assert table.selectionModel() is None

@pytest.mark.parametrize('points, rowIdx, expected_rowIdx', select_row_test_cases)
def test_select_row(table, points, rowIdx, expected_rowIdx):
    # Arrange
    data = pd.DataFrame(points)
    data_model = pandasModel(data)
    table.mySetModel(data_model)

    # Act
    table.selectRow(rowIdx)

    # Assert
    indexes = table.selectionModel().selectedRows()
    assert indexes[0].row() == expected_rowIdx

@pytest.mark.parametrize('points, rows, expected_rows', select_rows_test_cases)
def test_select_rows(table, points, rows, expected_rows):
    # Arrange
    data = pd.DataFrame(points)
    data_model = pandasModel(data)
    table.mySetModel(data_model)

    # Act
    table.mySelectRows(rows)

    # Assert
    indexes = table.selectionModel().selectedRows()
    assert len(indexes) == len(expected_rows)
    for index in sorted(indexes):
        assert index.row() in expected_rows

@pytest.mark.parametrize('points, expected_model_data', my_set_model_test_cases)
def test_my_set_model(table, points, expected_model_data):
    # Arrange
    data = pd.DataFrame(points)
    data_model = pandasModel(data)

    # Act
    table.mySetModel(data_model)

    # Assert
    pd.testing.assert_frame_equal(table.myModel.myGetData(), expected_model_data)
    # The following doesn't work on Windows, probably due to a pandas bug with .equals()
    # assert table.myModel.myGetData().equals(expected_model_data)

@pytest.mark.parametrize('dataframe, colStr, hidden', my_set_column_hidden_test_cases)
def test_my_Set_Column_Hidden(table, dataframe, colStr, hidden):
    # Arrange
    data_model = pandasModel(dataframe)
    table.mySetModel(data_model)

    # Act
    table.mySetColumnHidden(colStr, hidden)

    # Assert
    assert (colStr in table.hiddenColumnSet) == hidden 

@pytest.mark.parametrize('dataframe, colStr', my_set_column_hidden_for_unhiding_hidden_columns_test_cases)
def test_my_set_column_hidden_for_unhiding_hidden_columns(table, dataframe, colStr):
    # Arrange
    data_model = pandasModel(dataframe)
    table.mySetModel(data_model)
    table.mySetColumnHidden(colStr, True)

    # Act
    table.mySetColumnHidden(colStr, False)

    #print('table.hiddenColumnSet:', table.hiddenColumnSet)

    # Assert
    assert colStr not in table.hiddenColumnSet

def test_on_selection_changed_when_block_update_is_true(table):
    """
    TODO (cudmore): This is testing user selecting item in list.
    The function xxx() checks if blockUpdate is True and returns.
    It does not modify block update?
    """
    return
    
    # Arrange
    dataframe = pd.DataFrame([
          [1, 9, 2],
          [1, 0, -1],
        ], columns = ['x', 'y', 'z'])
    data_model = pandasModel(dataframe)
    table.mySetModel(data_model)
    table.blockUpdate = True

    # Act
    table.on_selectionChanged(None, None)

    # Assert
    assert table.blockUpdate == False

on_selection_changed_test_cases = [
    (twoDimPoints, {2}, [2]), # 1 row selected
    (twoDimPoints, {0, 2}, [0, 2]), # non-continuous selection
    (threeDimPoints, {0, 1, 2}, [0, 1, 2]), # continuous selection
    (threeDimPoints, {0, 1, 2, 3}, [0, 1, 2, 3]), # all rows selected
]

@pytest.mark.parametrize('points, selectRowIdxs, expectedLogIdxs', on_selection_changed_test_cases)
def test_on_selection_changed(table, caplog, points, selectRowIdxs, expectedLogIdxs):
    # Arrange
    caplog.set_level(logging.INFO)

    dataframe = pd.DataFrame(points)
    data_model = pandasModel(dataframe)
    table.mySetModel(data_model)
    table.blockUpdate = False

    # Act
    table.mySelectRows(selectRowIdxs)
    table.on_selectionChanged(None, None)

    # Assert
    assert f"selectedIndexes:{expectedLogIdxs}" in caplog.text
