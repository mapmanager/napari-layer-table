The napari-layer-table plugin is made of a number of files including:

 - [_my_widget.py](_my_widget.md) is the main entry point and all you really need to use the plugin.
 - [_my_layer.py](_my_layer.md) a class heirarchy to parallel Napari layers. This serves as a liason between the user interacting with the GUI and the backend..
 - [_table_widget.py](_table_widget.md) is derived from QTableView and customizes the display of the data.
 - [_data_model.py](_data_model.md) is derived from QAbstractTableModel and provides the _table_widget with a data model.

 See the [examples/](../../examples/) folder for how to embed the plugin into your own code.

