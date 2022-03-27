import logging
import pytest

import napari_layer_table

tests = [
    ('debug', logging.DEBUG, False),
    ('info', logging.INFO, True),
    ('warn', logging.WARNING, True),
    ('error', logging.ERROR, True),
    ('critical', logging.CRITICAL, True)
]

@pytest.mark.parametrize('levelStr, level, expected', tests)
def test_logging(levelStr, level, expected, caplog):
    # Arrange
    caplog.set_level(logging.INFO)
    message = f'testing {levelStr} logging'

    # Act
    napari_layer_table.logger.log(level=level, msg=message)

    # Assert
    # my_logger logs only at INFO level and above
    assert (message in caplog.text) == expected
