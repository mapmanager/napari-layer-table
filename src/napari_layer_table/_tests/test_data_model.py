from napari_layer_table import pandasModel
import numpy as np
import pandas as pd
import pytest
from qtpy import QtCore

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
    (np.array([[50, 55], [60, 65], [70, 75]]), 3),
    (np.array([[50, 55, 66], [50, 60, 65]]), 2),
    (np.array([[]]), 1), # (0, 0) -> 2D array: 1 row, 0 columns
    (np.array([]), 0), # (0,) -> 1D array: 0 rows, no columns
]

col_count_test_cases = [
    (np.array([[50, 55], [60, 65], [70, 75]]), 2),
    (np.array([[50, 55, 66], [50, 60, 65]]), 3),
    (np.array([[]]), 0),
]

data_test_cases = [
    (np.array([[50.5, 60.6], [70.7, 80.8]]), MockIndex(0,0), QtCore.Qt.DisplayRole, 50.5),
    (np.array([[50, 55], [60, 65], [70, 75]]), MockIndex(1,1), QtCore.Qt.DisplayRole, 65),
    (np.array([[np.bool_(True)], [np.bool_(False)], [np.bool_(False)]]), MockIndex(2,0), QtCore.Qt.DisplayRole, 'False'),
    (np.array([['nan'], ['12.5'], ['10.0']]), MockIndex(0,0), QtCore.Qt.DisplayRole, ''),
]

@pytest.mark.parametrize('points, expected', init_test_cases)
def test_init(points, expected):
    # Arrange
    data = pd.DataFrame(points)

    # Act
    data_model = pandasModel(data)

    # Assert
    assert (data_model is not None) == expected

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

@pytest.mark.parametrize('points, index, role, expected', data_test_cases)
def test_data_with_role(points, index, role, expected):
    # Arrange
    data_model = pandasModel(pd.DataFrame(points))

    # Act
    actual_data = data_model.data(index, role)

    # Assert
    assert actual_data == expected
