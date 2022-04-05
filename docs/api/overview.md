The napari-layer-table plugin is made of a number of files including:

 - [_my_widget.py](_my_widget.md) is the main entry point and all you really need to use the plugin.
 - [_table_widget.py](_table_widget.md) is derived from QTableView and customizes the display of the data.
 - [_date_model.py](_date_model.md) is derived from QAbstractTableModel and provides the _table_widget with a data model.

 TODO: How do we link to the actual file in the repo ?

 See the [examples/](../../examples/) folder for how to embed the plugin into your own code.

