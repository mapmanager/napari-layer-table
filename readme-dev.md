## Known bugs

 - Designed for 3D points, will generally work with 2d. Need to add a unit test to test 2d mode.
 
 - On user delete layer (with napari gui trash can icon), although another layer is selected (in napari viewer), we do not receive the event and our table remains on the previous (now deleted) layer. Table is updated correctly once user clicks in the image part of the viewer.

 - [fixed] if rows are selected and user sorts on column, selection is not updated

 - [fixed] If user sorts by column and then (adds, deletes) a point, on refresh our table is no longer in sort order.
  - Keep track of sort order (column name, ascending/decending).
   - On add/delete point, if we have a sort 'column' then resort with proper ascending/desending.
   - Make sure the selection is correct


## TODO

 - my logger defined in _my_widget.py is double printing all logger lines (in console). I guess this is because logger is initialized each time .py file is  included? Fix by putting creation of logger into a function?

 - [done] see `onlyOneLayer`. Add boolean property to turn off layer switching. We will use this from inside mapmanager to have it just listen to a single point layer that we create with code.
 
 - Allow multiple point selection in table. Get multiple disjoint selections working in the table. On selecting in table, select all in viewer and vica-versa. Will have to decide how we 'snap' to point (z) and (x,y) when multiple are selected
   - When user click+drag in viewer then select multiple points in table
   - When user shift+click or command+click in the table then select multiple points in the viewer

 - add shift+click to table row. On shift+click in table, snap image viewer to point (z,y,x) and zoom to a default amount. Add property to control the amount of zoom. If user is already zoomed into the image then keep that zoom.
 
## Keep track of a layer

- Select Layer
- Move Point
- Add Point
- Delete Point

## Turned off warnings during mouse drag

In file

```
mm_env/lib/python3.8/site-packages/vispy/app/backends/_qt.py
```

```
# abb
with warnings.catch_warnings():
	warnings.simplefilter('ignore')
	if q & qtmod:
		mod += (v,)
```

## Fresh dev install

```
python -m mm_env
source mm_env/bin/activate
pip install --upgrade pip

pip install pyqt5
pip install napari
pip install -e .
```

## SWC file format

From: http://www.neuromorpho.org/myfaq.jsp

The three dimensional structure of a neuron can be represented in a SWC format (Cannon et al., 1998). SWC is a simple Standardized format. Each line has 7 fields encoding data for a single neuronal compartment:
an integer number as compartment identifier
type of neuronal compartment
   0 - undefined
   1 - soma
   2 - axon
   3 - basal dendrite
   4 - apical dendrite
   5 - custom (user-defined preferences)
   6 - unspecified neurites
   7 - glia processes

x coordinate of the compartment
y coordinate of the compartment
z coordinate of the compartment
radius of the compartment
parent compartment
Every compartment has only one parent and the parent compartment for the first point in each file is always -1 (if the file does not include the soma information then the originating point of the tree will be connected to a parent of -1). The index for parent compartments are always less than child compartments. Loops and unconnected branches are excluded. All trees should originate from the soma and have parent type 1 if the file includes soma information. Soma can be a single point or more than one point. When the soma is encoded as one line in the SWC, it is interpreted as a "sphere". When it is encoded by more than 1 line, it could be a set of tapering cylinders (as in some pyramidal cells) or even a 2D projected contour ("circumference").

