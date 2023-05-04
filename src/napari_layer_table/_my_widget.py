"""
Widget to display points layer as a table.

 - The selected layer is displayed in the table.
 - The table has columns for:

     - Point symbol with face color
     - Point coordinates (x,y,z)
     - If the layer has properties, these are also columns

 - Bi-directional selection between layer and table.
 - Bi-directional delete between layer and table.
 - Points added to the layer are added to the table.
 - Points moved in the layer are updated in the table.
 - Changes to face color and symbol in the layer are updated in the table.

 Right-click for context menu to:

 - Toggle table columns on/off.
 - Toggle shift+click to add a point to the layer (no need to switch viewer mode)
 - Copy table to clipboard
"""

from pprint import pprint

import numpy as np
import pandas as pd

import napari

# to convert [r,g,b,a] to hex
# from napari.utils.colormaps.standardize_color import rgb_to_hex

from qtpy import QtWidgets, QtCore, QtGui

from napari_layer_table._my_logger import logger
from napari_layer_table._table_widget import myTableView
from napari_layer_table._data_model import pandasModel
from typing import List, Set
import warnings

from napari_layer_table import _my_layer

class LayerTablePlugin(QtWidgets.QWidget):
    acceptedLayers = (napari.layers.Points,
                        napari.layers.Shapes,
                        napari.layers.Labels)

    # TODO (cudmore) add this back in when we allow user edit of cell(s)
    ltp_signalDataChanged = QtCore.Signal(str, set, pd.DataFrame)
    """Emit signal to the external code when user adds and deletes items.
       Emits:
           (str) event type which can be "add", "move" or "delete" 
            (pd.DataFrame) for the edited row
    """

    ltp_signalEditedRows = QtCore.Signal(object, object)
    """Signal emited after user edited table data and we accepted it.
    
    Args:
        rows (List[int])
        df (df.DataFrame)
    """

    def __init__(self, napari_viewer : napari.Viewer,
                    oneLayer=None,
                    onAddCallback=None):
        """A widget to display a layer as a table.
        
        Allows bi-directional selection and editing.

        Args:
            viewer (napari.Viewer): Existing napari viewer.
            oneLayer (layer): If given then connect to this one layer,
                            otherwise, connect to all existing layers.
            onAddCallback (func) function is called on shift+click
                params(set, pd.DataFrame)
                return Union[None, dict]

        Raises:
            ValueError: If napari_viewer does not have a valid selected layer.
                Designed to work with (points, shapes, labels) layers.
                and to work with one Napari layer.

        TODO (cudmore) check params and return of onAddCallback
            takes a string and returns ???

        TODO (cudmore) once we are created with an accpeted layer.
            Need to close the plugin (?) if user deletes the layer?
        """
        super().__init__()

        warnings.filterwarnings(
            action='ignore',
            category=FutureWarning
        )

        self._viewer = napari_viewer
        
        if oneLayer is None:
            oneLayer = self._findActiveLayers()
        
        # if oneLayer is None:
        #     logger.error(f'did not find a layer ???')

        # _myLayer is from our class hierarchy to fix interface problems
        #   with variable layers in napari
        
        if isinstance(oneLayer, napari.layers.points.points.Points):
            self._myLayer = _my_layer.pointsLayer(self._viewer, oneLayer, onAddCallback=onAddCallback)
        elif isinstance(oneLayer, napari.layers.shapes.shapes.Shapes):
            self._myLayer = _my_layer.shapesLayer(self._viewer, oneLayer, onAddCallback=onAddCallback)
        elif isinstance(oneLayer, napari.layers.labels.labels.Labels):
            self._myLayer = _my_layer.labelLayer(self._viewer, oneLayer, onAddCallback=onAddCallback)
        else:
            self._myLayer = None  # ERROR
            logger.error(f'Did not understand layer of type: {type(oneLayer)}')
            logger.error(f'Expecting a viewer with an active layer in {self.acceptedLayers}')
            raise ValueError

        #self._layer = oneLayer
        # actual napari layer

        # we have layer in our list of 'acceptedLayers'
        self._myLayer.signalDataChanged.connect(self.slot2_layer_data_change)
        self._myLayer.signalLayerNameChange.connect(self.slot2_layer_name_change)

        # used to halt callbacks to prevent signal/slot recursion
        self._blockUserTableSelection = False
        self._blockDeleteFromTable = False

        self._showProperties = True  # Toggle point properties columns
        self._showCoordinates = True  # Toggle point coordinates columns (z,y,x)
        self._shift_click_for_new = False  # Toggle new points on shift+click
        #self._showFaceColor = True
        
        # If True, will not switch to different layer
        #self._onlyOneLayer = oneLayer is not None

        #self.myTable = None
        self._initGui()  # order matters, connectLayer() is accessing table
                        # but table has to first be created

        self.slot2_layer_name_change(self._myLayer.getName())

        # key binding are confusing
        # i want keyboard 'a' to toggle selected row, 'accept' column
        #self.setFocusPolicy(QtCore.Qt.StrongFocus)
        #self._viewer.bind_key('i', self._key_i_pressed)

        self.refresh()  # refresh entire table

    # no work
    # def keyPressEvent(self, event):
    #     logger.info('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    #@self.viewer.bind_key('i')
    # def _key_i_pressed(self, viewer):
    #     logger.info('!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!')

    def getTableView(self):
        """Get underlying QTableView.
        """
        return self.myTable2

    def newOnShiftClick(self, on : bool):
        """Toggle shift+click for new.
        """
        self._myLayer.newOnShiftClick(on)

    def slot2_layer_data_change(self, action :str,
                        selection : set,
                        layerSelectionCopy : dict,
                        df : pd.DataFrame):
        """Respond to user interface change through liazon myLayer.
        
            TODO (cudmore) data is not used???
        """
        '''
        logger.info('')
        print('    action:', action)
        print('    selection:', selection)
        print('    data:', data)
        print('    df:')
        pprint(df)
        '''

        if action == 'select':
            # TODO (cudmore) if Layer is labaeled then selection is a list
            if isinstance(selection, list):
                selection = set(selection)
            self.selectInTable(selection)
            self.ltp_signalDataChanged.emit(action, selection, df)

        elif action == 'add':
            #addedRowList = selection
            #myTableData = self.getLayerDataFrame(rowList=addedRowList)
            myTableData = df
            self.myTable2.myModel.myAppendRow(myTableData)
            self.selectInTable(selection)
            self.ltp_signalDataChanged.emit(action, selection, df)

        elif action == 'delete':
            # was this
            deleteRowSet = selection
            #logger.info(f'myEventType:{myEventType} deleteRowSet:{deleteRowSet}')
            #deletedDataFrame = self.myTable2.myModel.myGetData().iloc[list(deleteRowSet)]
            
            self._deleteRows(deleteRowSet)
            
            #self._blockDeleteFromTable = True
            #self.myTable2.myModel.myDeleteRows(deleteRowList)
            #self._blockDeleteFromTable = False

            self.ltp_signalDataChanged.emit(action, selection, df)

        elif action == 'change':
            moveRowList = list(selection) #rowList is actually indexes
            myTableData = df
            #myTableData = self.getLayerDataFrame(rowList=moveRowList)
            
            # this is what I call on a keystroke like 'a' for accept but interface is not updated???
            self.myTable2.myModel.mySetRow(moveRowList, myTableData, ignoreAccept=True)
            
            logger.warning('!!! we emit ltp_signalDataChanged but it is not connected to anybody')
            self.ltp_signalDataChanged.emit(action, selection, df)
        else:
            logger.info(f'did not understand action: "{action}"')

    def slot2_layer_name_change(self, name :str):
        #logger.info(f'name is now: {name}')
        self.layerNameLabel.setText(name)

    def _initGui(self):

        # main vertical layout
        vbox_layout = QtWidgets.QVBoxLayout()

        # one row of controls
        controls_hbox_layout = QtWidgets.QHBoxLayout()

        # full refresh of table
        # refreshButton = QtWidgets.QPushButton('Refresh')
        # refreshButton.setToolTip('Refresh the entire table')
        # refreshButton.clicked.connect(self.on_refresh_button)
        # controls_hbox_layout.addWidget(refreshButton)

        # bring layer to front in napari viewer
        #if self._onlyOneLayer:
        bringToFrontButton = QtWidgets.QPushButton('')
        bringToFrontButton.setToolTip('Bring layer to front')
        # want to set an icon, temporary use built in is SP_TitleBarNormalButton
        #TODO (cudmore) install our own .svg icons, need to use .qss file
        style = self.style()
        bringToFrontButton.setIcon(
                    style.standardIcon(QtWidgets.QStyle.SP_FileIcon))

        bringToFrontButton.clicked.connect(self.on_bring_to_front_button)
        controls_hbox_layout.addWidget(bringToFrontButton, alignment=QtCore.Qt.AlignLeft)

        # TODO: not implemented
        # undoButton = QtWidgets.QPushButton('Undo')
        # undoButton.setToolTip('Undo')
        # # want to set an icon, temporary use built in is SP_TitleBarNormalButton
        # #TODO (cudmore) install our own .svg icons, need to use .qss file
        # style = self.style()
        # #undoButton.setIcon(
        # #            style.standardIcon(QtWidgets.QStyle.SP_BrowserReload))

        # undoButton.clicked.connect(self.on_undo_button)
        # controls_hbox_layout.addWidget(undoButton)

        # the current layer name
        self.layerNameLabel = QtWidgets.QLabel('')
        controls_hbox_layout.addWidget(self.layerNameLabel, alignment=QtCore.Qt.AlignLeft)

        controls_hbox_layout.addStretch()

        vbox_layout.addLayout(controls_hbox_layout)

        self.myTable2 = myTableView()
        #self.myTable2.setFontSize(11)
        # to pass selections in table back to the viewer
        self.myTable2.signalSelectionChanged.connect(self.slot_selection_changed)
        self.myTable2.mtv_signalEditingRows.connect(self.slot_editingRows)
        # Important: we need to disconnect this signal if we have
        # a dedicated backend with data and table is a copy
        self.ltp_signalEditedRows.connect(self.myTable2.slot_editedRows)

        vbox_layout.addWidget(self.myTable2)

        # finalize
        self.setLayout(vbox_layout)

    def _findActiveLayers(self):
        """Find pre-existing selected layer.
        """
        for layer in self._viewer.layers:
            if isinstance(layer, self.acceptedLayers):
                if layer == self._viewer.layers.selection.active:
                    # connect to existing active layer
                    return layer
        return None

    def old_on_refresh_button(self):
        """TODO: need to preserve 'accept' column.
        """
        logger.info('')
        self.refresh()

    def on_bring_to_front_button(self):
        """Bring the layer to the front in napari viewer.
        
        TODO (cudmore): update to _my_layer
        """
        logger.info('')
        self._myLayer.bringToFront()
        #if self._viewer.layers.selection.active != self._myLayer:
        #    #print('  seting layer in viewer')
        #    self._viewer.layers.selection.active = self._myLayer

    def old_on_undo_button(self):
        self._myLayer.doUndo()

    def connectLayer(self, layer):
        """Connect to one layer.
        
        Args:
            layer (layer): Layer to connect to.

        TODO:
            Need to handle layer=None and just empty the interface
        """
        logger.error('TODO (cudmore) need to refactor this !!!')
        logger.error('  basically all calls to connect have to go through our layer heirarchy in _my_layer ...')
        return
        
        #if layer is None:
        #    return
        
        if layer is not None and not isinstance(layer, self.acceptedLayers):
            logger.warning(f'layer with type {type(layer)} was not in {self.acceptedLayers}')
            return

        logger.info(f'Connecting to layer "{layer}"')

        # disconnect from existing (previous) layer
        if self._layer is not None:
            self._layer.events.data.disconnect(self.slot_user_edit_data)
            self._layer.events.name.disconnect(self.slot_user_edit_name)
            self._layer.events.symbol.disconnect(self.slot_user_edit_symbol)
            self._layer.events.size.disconnect(self.slot_user_edit_size)
            self._layer.events.highlight.disconnect(self.slot_user_edit_highlight)
            
            # special case
            self._layer.events.face_color.disconnect(self.slot_user_edit_face_color)
            self._layer._face.events.current_color.disconnect(self.slot_user_edit_face_color)
        
        self._layer = layer
        
        # if layer is None, hide interface
        if self._layer is None:
            logger.info('no layer selection ,hiding interface')
            # TODO (cudmore) the following is not needed, just hide the widget
            #emptyDataFrame = pd.DataFrame()
            # set name to ''
            #self.layerNameLabel.setText('')
            # set table to empty
            #self._refreshTableData(emptyDataFrame)
            self.hide()
            return
        else:
            self.show()

        # display the name of the layer
        self.layerNameLabel.setText(self._layer.name)

        # AttributeError: 'pointsLayer' object has no attribute 'events'
        self._layer.events.data.connect(self.slot_user_edit_data)
        self._layer.events.name.connect(self.slot_user_edit_name)
        self._layer.events.symbol.connect(self.slot_user_edit_symbol)
        self._layer.events.size.connect(self.slot_user_edit_size)
        self._layer.events.highlight.connect(self.slot_user_edit_highlight)

        # this does not call our callback ... bug in napari???
        self._layer.events.face_color.connect(self.slot_user_edit_face_color)
        # this works but layer is not updated yet
        try:
            self._layer._face.events.current_color.connect(self.slot_user_edit_face_color)
        except (AttributeError) as e:
            logger.warning(e)

        # important: when user switches layers, napari does not visually switch selections?
        # but the layer does remember it. Set it to empty set()
        # otherwise our interface would re-select the previous selection
        self._layer.selected_data = set()
        self._selectedData = None
        
        self._updateMouseCallbacks()

        # TODO: remove this, should by part of map manager
        # leaving it here as proof-of-concept
        #self._myLayer.mouse_wheel_callbacks.append(self.on_mouse_wheel)

        # full refresh of table
        self.refresh()
  
    def refresh(self):
        """Refresh entire table with current layer.
        
        Note:
            This refreshes entire table (slow).
            Should only be used on table creation and layer switching.
            Do not use for edits like add, delete, change/move.
        """
        #layerDataFrame = self.getLayerDataFrame()
        layerDataFrame = self._myLayer.getDataFrame(getFull=True)
        self._refreshTableData(layerDataFrame)

    def _refreshTableData(self, df : pd.DataFrame):
        """Refresh all data in table by setting its data model from provided dataframe.

        Args:
            df (pd.DataFrame): Pandas dataframe to refresh with.
        """
        
        if self.myTable2 is None:
            # interface has not been initialized
            return

        if df is None:
            return
        
        logger.info(f'Full refresh ... limit use of this')
        logger.info(f'refreshing from df:')
        print(df)

        myModel = pandasModel(df)
        self.myTable2.mySetModel(myModel)

    def contextMenuEvent(self, event):
        """Show a context menu on mouse right-click.

        This is an inherited function of QWidget.
        """

        # create the menu
        contextMenu = QtWidgets.QMenu(self)
        
        # add menu item actions
        showCoordinates = contextMenu.addAction("Coordinates")
        showCoordinates.setCheckable(True)
        showCoordinates.setChecked(self._showCoordinates)
        
        showProperties = contextMenu.addAction("Properties")
        showProperties.setCheckable(True)
        showProperties.setChecked(self._showProperties)

        #showFaceColor = contextMenu.addAction("Face Color")
        #showFaceColor.setCheckable(True)
        #showFaceColor.setChecked(self._showFaceColor)

        contextMenu.addSeparator()
        shiftClickForNew = contextMenu.addAction("Shift+Click for new")
        shiftClickForNew.setCheckable(True)
        shiftClickForNew.setChecked(self._shift_click_for_new)

        #contextMenu.addSeparator()
        copyTable = contextMenu.addAction("Copy Table To Clipboard")

        contextMenu.addSeparator()

        # all columns in pandas data model
        columns = self.myTable2.getColumns()
        for column in columns:
            isHidden = column in self.myTable2.hiddenColumnSet
            columnAction = contextMenu.addAction(column)
            columnAction.setCheckable(True)
            columnAction.setChecked(not isHidden)

        # all properties in pandas data
        # these are part of columns

        # show the popup menu
        action = contextMenu.exec_(self.mapToGlobal(event.pos()))
        
        # take action
        if action == showCoordinates:
            self._showCoordinates = action.isChecked()
            self.hideColumns('coordinates', not action.isChecked())
        elif action == showProperties:
            self._showProperties = action.isChecked()
            self.hideColumns('properties', not action.isChecked())
        
        elif action == shiftClickForNew:
            self._shift_click_for_new = not self._shift_click_for_new    
            #self._updateMouseCallbacks()
            self._myLayer._updateMouseCallbacks(self._shift_click_for_new)

        elif action == copyTable:
            self.myTable2.myModel.myCopyTable()
        
        elif action is not None:
            # show/hide individual comuns
            column = action.text()
            hidden = column in self.myTable2.hiddenColumnSet
            self.myTable2.mySetColumnHidden(column, not hidden)  # toggle hidden

        #elif action is not None:
        #    logger.warning(f'action not taken "{action.text()}"')

    def hideColumns(self, columnType : str, hidden : bool = True):
        """Hide different sets of columns.

        Args:
            columnType (str): from
                - 'coordinates': Show or hide (z, y, x) columns.
                - 'properties': Show or hide all layer property key columns.
            hidden (bool): If true then column will be hidden, otherwise show.
        """
        logger.info(f'columnType:{columnType} hidden:{hidden}')
        if columnType == 'coordinates':
            self.myTable2.mySetColumnHidden('z', hidden)
            self.myTable2.mySetColumnHidden('y', hidden)
            self.myTable2.mySetColumnHidden('x', hidden)
        elif columnType == 'properties':
            for property in self._myLayer.properties.keys():
                self.myTable2.mySetColumnHidden(property, hidden)
        else:
            logger.warning(f'did not understand columnType:{columnType}')

    def selectInTable(self, selected_data : Set[int]):
        """Select in table in response to viewer (add, highlight).
        
        Args:
            selected_data (set[int]): Set of selected rows to select
        """
        if self._blockDeleteFromTable:
            #self._blockDeleteFromTable = False
            return
        
        logger.info(f'selected_data: {selected_data}')

        self.myTable2.mySelectRows(selected_data)

    def slot_selection_changed(self, selectedRowList : List[int], isAlt : bool):
        """Respond to user selecting a table row.

        Note:
            - This is coming from user selection in table,
                we do not want to propogate
        """
        if self._blockDeleteFromTable:
            #self._blockDeleteFromTable = False
            return

        logger.info(f'selectedRowList: {selectedRowList} isAlt:{isAlt}')
        
        selectedRowSet = set(selectedRowList)

        self._blockUserTableSelection = True
        self._myLayer.selectItems(selectedRowSet)
        self._blockUserTableSelection = False

        # if only one row selected then snap z of the image layer
        if len(selectedRowList) == 1:
            selectedRow = selectedRowList[0]  # the first row selection
            self._myLayer.snapToItem(selectedRow, isAlt)

        # TODO (cudmore) getDataFrame is getting from self._myLayer.selected_Data
        # is this always the same as selectedRowSet?
        df = self._myLayer.getDataFrame()
        self.ltp_signalDataChanged.emit('select', selectedRowSet, df)

    def slot_editingRows(self, rowList : List[int], df : pd.DataFrame):
        """Respond to user editing table rows.
        """
        logger.info('  CONNECTED TO self.myTable2.mtv_signalEditingRows')
        logger.info('  received rowList and df as follows')
        print('  rowList:', rowList)
        print('  df:')
        print(df)
        
        logger.info(f'  -->> NOW emit ltp_signalEditedRows')
        
        self.ltp_signalEditedRows.emit(rowList, df)
        
    def _deleteRows(self, rows : Set[int]):
        self._blockDeleteFromTable = True
        self.myTable2.myModel.myDeleteRows(rows)
        self._blockDeleteFromTable = False
            
def run():
    #numSlices = 20
    minInt = 0
    maxInt = 100
    xySize = 128
    #image = np.random.randint(minInt, maxInt, (xySize,xySize,xySize))

    from skimage import data
    image = data.binary_blobs(length=128, volume_fraction=0.1, n_dim=3)
    image = image.astype(float)
    logger.info(f'image: {image.shape} {image.dtype}')
    viewer = napari.Viewer()

    #print('  viewer.dims.point:', viewer.dims.point)
    #print('  viewer.dims.order:', viewer.dims.order)

    imageLayer = viewer.add_image(image, colormap='green', blending='additive')

    # set viewer to slice zSLice
    axis = 0
    zSlice = 15
    viewer.dims.set_point(axis, zSlice)

    # test 2d points
    points2d = np.array([[50, 55], [60, 65], [70, 75]])
    pointsLayer2d = viewer.add_points(points2d,
                            size=20, face_color='yellow', name='yellow carrots')
    pointsLayer2d.mode = 'select'
    pointsLayer2d.symbol = '^'

    # test 3D points
    points1 = np.array([[zSlice, 10, 10], [zSlice, 20, 20], [zSlice, 30, 30], [zSlice, 40, 40]])
    pointsLayer = viewer.add_points(points1,
                            size=30, face_color='green', name='green circles')
    pointsLayer.mode = 'select'

    points2 = np.array([[zSlice, 75, 55], [zSlice, 85, 65], [zSlice, 95, 75]])
    pointsLayer2 = viewer.add_points(points2,
                            size=30, face_color='magenta', 
                            #edge_color='magenta',
                            #edge_width_is_relative=False,
                            #edge_width=10,
                            name='magenta crosses')
    pointsLayer2.mode = 'select'
    #pointsLayer2.symbols = ['+'] * points2.shape[0]
    pointsLayer2.symbol = '+'
    
    # add some properties
    pointsLayer2.properties = {
        'Prop 1': ['a', 'b', 'c'],
        'Is Good': [True, False, True],
    }

    # run the plugin
    ltp = LayerTablePlugin(viewer, oneLayer=None)

    area = 'right'
    name = 'Layer Table Plugin'
    dockWidget = viewer.window.add_dock_widget(ltp, area=area, name=name)

    napari.run()

# if __name__ == '__main__':
#     run()