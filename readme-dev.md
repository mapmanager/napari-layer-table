## Known bugs

 - Designed for 3D points, will generally work with 2d but will get runtime errors.
 
 - On user delete layer (with trash can icon), although another layer is selected (in napari viewer), we do not receive the event and our table remains empty. Table is updated correctly once user clicks in the image part of the viewer.

 - When user hits 'delete' key to delete a point, we also delete the selected row in our table. This does not produce a bug but is visually annoying. User keystroke with 'delete' is usefull for deleting layer points (we need to maintain this).

## TODO

 - add boolean property to turn off layer switching. We will use this from inside mapmanager to have it just listen to a single point layer that we create with code.
 
 - Figure out how to manager key press events in magicgui table. If we can't do it then use a derived QTableView with a proper data model.

 - Get it to work with 3d points


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

