
Still working on the layer-table-plugin to handle layers (points, shapes, labels).

As you pointed out, as data-structures the (points, shapes, labels) layer have minor differences. Should be easy.

Yet, it is a complete mess becuase of differences in their run-time signals. The logic to determine user interface changes from napari is super complex.

Lets say within the (points, shapes) layer that each 'item' is an object:
    points layer : 'items' are points
    shape layer : 'items' are shapes
    
We want 'events' for a (points, shapes) layer like:
    create
    update
    delete

The best I can do is monitor events in (highlight, data) but the logic is super complex and completely different between just the (points, shapes) layers.

We need to make a simple example of this complexity and post it to the napari github.

In the plugin grant proposal, I would like to propose we modify napari to give us the signals. Then our plugin code (and all others) would be super easy to implement.
