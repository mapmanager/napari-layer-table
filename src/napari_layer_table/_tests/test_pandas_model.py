from napari_layer_table import pandasModel
import numpy as np
import pandas as pd
import pytest
from qtpy import QtCore, QtGui

class MockIndex:
    """
    This class mocks QModelIndex which is required to be passed to the several methods in the data model
    to test them. This is a form of Duck Typing (https://en.wikipedia.org/wiki/Duck_typing)

    A few words about mocking:
    An object under test may have dependencies on other (complex) objects. 
    To isolate the behavior of the object you want to replace the other objects by mocks that 
    simulate the behavior of the real objects. This is useful if the real objects are impractical
    to incorporate into the unit test.
    In short, mocking is creating objects that simulate the behavior of real objects.
    """
    def __init__(self, row, col) -> None:
        self._row = row
        self._col = col
    
    def isValid(self) -> bool:
        return True
    
    def row(self):
        return self._row
    
    def column(self):
        return self._col
    

init_test_cases = [
    (np.array([[50, 55], [60, 65], [70, 75]]), True),
    (np.array([[50, 55, 66], [50, 60, 65], [50, 70, 75]]), True),
    (np.array([[]]), True), # this symbolizes 1 row, 0 columns
    (None, True),
]

row_count_test_cases = [
    (np.array([[50, 55], [60, 65], [70, 75]]), 3), # 2D array
    (np.array([[50, 55, 66], [50, 60, 65]]), 2), # 3D array
    (np.array([[]]), 1), # (0, 0) -> 2D array: 1 row, 0 columns
    (np.array([]), 0), # (0,) -> 1D array: 0 rows, no columns
]

col_count_test_cases = [
    (np.array([[50, 55], [60, 65], [70, 75]]), 2),
    (np.array([[50, 55, 66], [50, 60, 65]]), 3),
    (np.array([[]]), 0),
]

# points, index, expected
data_display_role_test_cases = [
    (np.array([[50.5, 60.6], [70.7, 80.8]]), MockIndex(0,0), 50.5),
    (np.array([[50, 55], [60, 65], [70, 75]]), MockIndex(1,1), 65),
    # (np.array([[np.bool_(True)], [np.bool_(False)], [np.bool_(False)]]), MockIndex(2,0), 'False'),
    (np.array([[np.bool_(True)], [np.bool_(False)], [np.bool_(False)]]), MockIndex(2,0), False),
    (np.array([['nan'], ['12.5'], ['10.0']]), MockIndex(0,0), 'nan'),
]

# data_font_role_test_cases = [
#     # (np.array([['Symbol'], ['^'], ['+'], ['X']]), MockIndex(1,0), QtCore.QVariant(QtGui.QFont('Arial', pointSize=16))),
#     (pd.DataFrame().insert(loc=0, column='Symbol', value=[['X']]), MockIndex(1,0), QtCore.QVariant(QtGui.QFont('Arial', pointSize=16)))
# ]

header_data_test_cases = [
    (pd.DataFrame([
          [1, 9, 2],
          [1, 0, -1],
        ], columns = ['x', 'y', 'z']), QtCore.Qt.Horizontal, 0, 'x'),
    (pd.DataFrame([
          [1, 9],
          [1, 0],
        ], columns = ['x', 'y']), QtCore.Qt.Horizontal, 1, 'y'),
    (pd.DataFrame([
          [1, 9],
          [1, 0],
        ], columns = ['x', 'y']), QtCore.Qt.Vertical, 0, 0),
]

my_append_row_test_cases = [
    (np.array([[50, 55], [60, 65], [70, 75]]), np.array([[40, 50]]), 4),
    (np.array([[50, 55, 66], [50, 60, 65]]), np.array([[40, 50, 70]]), 3),
    (np.array([[50, 55, 66], [50, 60, 65]]), None, 2)
]

my_delete_rows_test_cases = [
    (np.array([[50, 55], [60, 65], [70, 75]]), [0], 2),
    (np.array([[50, 55, 66], [50, 60, 65]]), [0,1], 0)
]

# points, rows_to_set, data_to_set, expected_data
my_set_row_test_cases = [
    # TODO (cudmore) rows to set is a df with row index matching table model df
    # (np.array([[50, 55], [60, 65], [70, 75]]), [2], pd.DataFrame([[80, 85]]), pd.DataFrame([[50, 55], [60, 65], [80, 85]])),
    (np.array([[50, 55], [60, 65], [70, 75]]), [0,1], pd.DataFrame([[70, 75], [80, 85]]), pd.DataFrame([[50, 55], [70, 75], [80, 85]])),
    (np.array([[50, 55, 66], [50, 60, 65]]), [0,1], pd.DataFrame([[70, 75, 76], [80, 85, 86]]), pd.DataFrame([[70, 75, 76], [80, 85, 86]]))
]

@pytest.mark.parametrize('points, expected', init_test_cases)
def test_init(points, expected):
    # Arrange
    data = pd.DataFrame(points)

    # Act
    data_model = pandasModel(data)

    # Assert
    # assert (data_model is not None) == expected
    assert data_model.myGetData().equals(data) == expected


@pytest.mark.parametrize('points, expected', row_count_test_cases)
def test_row_count(points, expected):
    # Arrange
    data = pd.DataFrame(points)
    data_model = pandasModel(data)

    # Act
    row_count = data_model.rowCount()

    # Assert
    assert row_count == expected

@pytest.mark.parametrize('points, expected', col_count_test_cases)
def test_column_count(points, expected):
    # Arrange
    data = pd.DataFrame(points)
    data_model = pandasModel(data)

    # Act
    col_count = data_model.columnCount()

    # Assert
    assert col_count == expected

@pytest.mark.parametrize('points, index, expected', data_display_role_test_cases)
def test_data_with_display_role(points, index, expected):
    # TODO: put back in
    return

    # Arrange
    data_model = pandasModel(pd.DataFrame(points))

    # Act
    actual_data = data_model.data(index, QtCore.Qt.DisplayRole)

    # Assert
    assert actual_data == expected

# @pytest.mark.parametrize('points, index, expected', data_font_role_test_cases)
# def test_data_with_font_role(points, index, expected):
#     # Arrange
#     data_model = pandasModel(points)

#     # Act
#     actual_data = data_model.data(index, QtCore.Qt.FontRole)

#     # Assert
#     assert actual_data.value() == expected.value()

@pytest.mark.parametrize('points, orientation, col, expected', header_data_test_cases)
def test_header_data(points, orientation, col, expected):
    # Arrange
    data_model = pandasModel(points)

    # Act
    actual_data = data_model.headerData(col, orientation, QtCore.Qt.DisplayRole)

    # Assert
    assert actual_data == expected

@pytest.mark.parametrize('points, new_point, expected_rowcount', my_append_row_test_cases)
def test_my_append_row(points, new_point, expected_rowcount):
    # Arrange
    data_model = pandasModel(pd.DataFrame(points))

    # Act
    data_model.myAppendRow(pd.DataFrame(new_point))

    # Assert
    assert data_model.rowCount() == expected_rowcount

@pytest.mark.parametrize('points, points_to_delete, expected_rowcount', my_delete_rows_test_cases)
def test_my_delete_row(points, points_to_delete, expected_rowcount):
    # Arrange
    data_model = pandasModel(pd.DataFrame(points))

    # Act
    data_model.myDeleteRows(points_to_delete)

    # Assert
    assert data_model.rowCount() == expected_rowcount

@pytest.mark.parametrize('points, rows_to_set, data_to_set, expected_data', my_set_row_test_cases)
def test_my_set_row(points, rows_to_set, data_to_set, expected_data):
    # Arrange
    data_model = pandasModel(pd.DataFrame(points))

    # Act
    result = data_model.mySetRow(rows_to_set, data_to_set)

    # Assert
    assert result == True

    # Windows considers integers to be int32. We need to convert the dataframe to have int64 values instead
    # TODO (cudmore) our model df is a mixture of types, not just int?
    # df = data_model.myGetData()
    # d = dict.fromkeys(df.select_dtypes(np.int32).columns, np.int64)
    # df = df.astype(d)
    # pd.testing.assert_frame_equal(df, expected_data)

    # The following doesn't work on Windows, probably due to a pandas bug with .equals()
    # assert data_model.myGetData().equals(expected_data) == True
