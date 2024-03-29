## Development workflow

Before pushing either a branch or main to github, you need to check some things locally or else the push will fail.

On github, we are running some workflows defined in [.github/workflows](.github/workflows).

1) Run all tests with `pytest`. The `--maxfail=2` will stop testing after just 2 errors and is sometmies easier to debug.

    ```
    pytest --maxfail=2
    ```

2) We are using flake8 for code linting. We only check for a few error (E9, F63, etc). See [flake documentation](https://flake8.pycqa.org/en/latest/user/error-codes.html) for more info.

    ```
    flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
    ```

    If this **passes**, you will just see a '0'. If this **fails** you might see something like this:

    ```
    src/napari_layer_table/debugInterface.py:77:10: F821 undefined name 'shapesLayer'
    sl = shapesLayer(viewer, shapes_layer)
         ^
    1     F821 undefined name 'shapesLayer'
    ```

3) Pushing a new version

    If you are ready to push a new version to **main**, you need to update the version in [setup.cfg](setup.cfg). Otherwise, pushing the code to PyPi (for pip install) will fail.

    ```
    [metadata]
    name = napari-layer-table
    version = 0.0.9
    ```

4) If you made changes to the mkdocs documentation, you need to check that too.

    The mkdocs files are in [mkdocs.yml](mkdocs.yml) file and in the [docs/](docs/) folder.

    ```
    mkdocs build
    ```

    You can always run the documentation in a local browser using

    ```
    mkdocs serve
    ```

## Known bugs

 - Designed for 3D points, will generally work with 2d. Need to add a unit test to test 2d mode.
 
 - On user delete layer (with napari gui trash can icon), although another layer is selected (in napari viewer), we do not receive the event and our table remains on the previous (now deleted) layer. Table is updated correctly once user clicks in the image part of the viewer.

 - [fixed] if rows are selected and user sorts on column, selection is not updated

 - [fixed] If user sorts by column and then (adds, deletes) a point, on refresh our table is no longer in sort order.
  - [fixed] Keep track of sort order (column name, ascending/decending).
   - On add/delete point, if we have a sort 'column' then resort with proper ascending/desending.
   - [fixed] Make sure the selection is correct

## Start using pyenv again

`pyenv` allows multiple version of Python to be installed and to easily switch between them. This might help to locally test diferent Python versions for build errors which will show up when we push to GitHub.

```
# install pyenv
git clone https://github.com/pyenv/pyenv ~/.pyenv

# setup pyenv (you should also put these three lines in .bashrc or similar)
export PATH="${HOME}/.pyenv/bin:${PATH}"
export PYENV_ROOT="${HOME}/.pyenv"
eval "$(pyenv init -)"

# install Python 3.7
pyenv install 3.7.12

# make it available globally
pyenv global system 3.7.12
```

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

# Debug branch 'cudmore-labels-oct-30' with Whistler data

### New Features:

- We now flash the point that was selected so user can see it better
- added myTableView setFontSize()
- mostly fixed keystroke problems (needed more 'block' in slots)
- implemented key 'a' to toggle a column True/False, see _xxx

### Bugs

- Up/down arrows do not work
- When making table from labeled, grab color of layer label and show in table
- [fixed] When table is sorted by column and user clicks a row (point layer), the correct point is selected but the table sort order is lost (very confusing)
- [fixed] when table rows are sorted by a column, we were painting the background row with idx (not wanted), insead we need to use the row index (Real row) that is displayed.