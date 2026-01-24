# qtPyGraphEdit
A graphical node-edge graph editor, in Python and Qt (PySide6). Currently very much in development, in a pre-alpha state.
<p align="centre">
<img width="205" height="153" alt="image" src="https://github.com/user-attachments/assets/3003b49e-4625-4cc3-91b0-0da034a61bbc" />  V0.0.0
            <br>
<img width="500" height="380" alt="image" src="https://github.com/user-attachments/assets/7067d275-d660-45f1-a077-92cf5cff30dd" /> V0.1.0

</p>
<p align="centre">
            

The interface - an (editable) object list on the left, and the editable graph on the right. Tools on the top. 
            
The black circle adds **Nodes (shortcut - "N"),** the tracks add **Edges ("E")** The pointer goes into select mode. Double click the text in the list to edit names. Selection in one window shows in the other. I _think_ the menu options are self explanatory?
</p>

This is a prototype and learning project. My primary goal is to learn Qt/ Pyside, and to figure out the patterns needed to support model (repository) -based, multi-graphical view higraphs. I have some blog posts about the project [here](https://isijingi.co.za/wp/category/higraph/)

Given that there seem to be very few (no?) _graphical_ graph editors in Python, it is possible that someone may see the utility in taking this rolling chassis, and turning it into a graphical front-end for something like `networkx`. Since this has a (rudimentary) live Python scripting window, it can be extended to support command line and GUI interactions.

## V0 is a simple node-edge graph editor

Goal: Build a basic PySide6 framework for a model-viewController, with a truly independent Graph model
This is currently based on a simple [custom Graph library](https://github.com/ghillebrand/qtPyGraphEdit/blob/main/src/coreGraph.py), which will be extended to higraphs in V1. One could use `networkx` or an equivalent at this point, but it doesn't support higraphs, so the work will have to be done sooner or later.

### V0.0
- Dictionary of nodes and edges with meta data. 
- Displayed in a text list and graphically
- Edit the graph - add, delete, edit text for nodes & edges, move nodes, reroute edges. 
- Save and load (Graphml with yED extensions). This uses code from [yEdExtended](https://github.com/cole-st-john/yEdExtended)
- Copy/ Paste as text, graphics and internally to duplicate items.
- A rudimentary Python shell that runs with (write!) access to the Graph, Scene and Model data.
- NOTE: This version uses the qtcreator `.ui` files, which places some constraints on what one can do. There are some workarounds to this in the code. As I understand Qt better, hopefully there will be fewer of these!

_Currently, V00 has a bug on deleting an edge, such that quite often, but not always, the edge is removed from the data structures, but the Qt Scene still draws it._

### V0.1
There has been quite a lot of refactoring of the code. the `yEd` library, which was an invaluable stepping stone for persistence in V00 has been replaced with internal XML read/ write code. As I begin to understand Qt better, I fix things. There are still ~70 `TODO`s, but a number have been dealt with, and many are reminders for future versions.

- Hermite splines for edges - based around [this code](https://github.com/vedantyadu/Hermite-cubic-spline). I _really_ think Bezier splines are an ugly way to edit curves. 
- Multipoint edges - all edges can have multiple bend points.
- Edges are editable, and can be directed or undirected, and rectilinear or spline. Only one sort of arrow-head at this point!
- Text display and edit for extended metadata (was in V0.3, but got moved here)
- Models still round-trip to yEd, but metadata currently does not pull through, and the Hermite spline points become Bezier control points, so the curves look different. 
  
<img width="790" height="288" alt="image" src="https://github.com/user-attachments/assets/f4eed419-bfc9-46fb-839a-f9479e16bd38" />

The editing dialog. It is simple and functional - I'm still working out how to use Qt!

## TODO:

### V0.2
- Hyperedges - n-ended edges. 
            
### V0.3
- Multiple tabs - editable views of different subsets of the master Graph model 

### V0.4
- Higraphs - nodes become sets. This will likely be strictly heirarchical sets (ie no set intersections/ overlaps)

### V0.5
- Overlapping sets.

# Getting Started with editing the code
If you are totally new to Qt (or PySide, the Python version used here), this is a [good tutorial](www.pythonguis.com/tutorials/pyside6-qgraphics-vector-graphics/)

Otherwise, 
- create a folder, 
- create a virtual enviroment  `python -m venv C:\path\to\new\virtual\environment` (and make it active with `scripts\activate`)
- install PySide with `pip install PySide6`
- copy all the code from here (git clone https://github.com/ghillebrand/qtPyGraphEdit.git) or download the zip from the green `Code` button above.
- Run `python mainwindow.py`, or open `mainwindow.py` with you favourite editor. I use VSCodium: VSCode without the telemetry back to Microsoft.
- If you want to edit the dialogs, then you need the Qt designer `qtcreator` and to compile the `.ui` files to `.py`. The command is `pyside6-uic <file>.ui -o <file>.py`

The code comes with no guarantees at this point - not even that it will run! It certainly has rough edges and bugs. I do try to check that what's here runs, but this is still very much the beginning of a much longer journey.
