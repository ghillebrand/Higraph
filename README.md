# Higraph
Higraph is a pure Python and PySide6 GUI to edit node-and-edge graphs, including hypergraphs and David Harel's extensions of nodes to sets, which he called "[Higraphs](https://dl.acm.org/doi/10.1145/42411.42414)".
It maintains a structured dictionary of the elements of the graph, and their relationships, whilst allowing the graphical editing and layout of the graph and the elements.
<p align="center">  
<img width="800" height="578" alt="image" src="https://github.com/user-attachments/assets/9fa0df31-608b-4ebf-b0fc-503e4f632364" />
</p>
Figure 7 from Harel's paper, drawn in the tool. The item dictionary is on the left, and the visually editable model on the right.


There is an accessible underlying graph model which can be interactively accessed via a Python shell. 
All items have Python dictionaries for metadata, allowing flexibility of application.

**Hyperedges** are supported as n-ary directed or undirected edges. **Blobs** are nodes extended to sets, and are aware of their parent and child relationships. 
Multiple parents are supported.

Data is stored in XML files, loosely based on `graphml` files.

## Usage
The tool _aims_ to be easy to use for non-mathematicians and non-programmers! 
- **Nodes** are added by clicking on the <img width="37" height="30" alt="image" src="https://github.com/user-attachments/assets/85153350-8f5f-4751-ae6a-845a47916300" /> icon, or tapping the `N` key and click where you want the node.
- **Blobs** are created from the <img width="44" height="31" alt="image" src="https://github.com/user-attachments/assets/ab666cbd-522f-4155-a88d-69d3b53299c7" /> icon, or tapping the `B` key, and dragging out the shape of the blob, as required.
- **Edges** are created from the <img width="36" height="32" alt="image" src="https://github.com/user-attachments/assets/16f6232d-de2f-41f7-9fec-6a6ac579f383" /> icon, or tapping `E`. Note that all edges are implicitly hyperedges, and so node-edge and edge-node connections can also be made.
  - Edges are Hermite Splines. Select an edge, and a set of editing handles appear, allowing the shape to be adjusted.
  - Right-clicking allows additional control points to be added or removed.
<p align="center">  
  <img width="252" height="142" alt="image" src="https://github.com/user-attachments/assets/74d7ab04-429b-44b8-ab64-14e175b32e04" />  when selected: <img width="244" height="137" alt="image" src="https://github.com/user-attachments/assets/f3a03f67-5217-481d-b1f2-1fc6cf30f1b7" />
</p>
Double-clicking on any item in the dictionary or on the image allows its various properties to be edited. For edges, this includes directedness, and whether to draw them a straight lines or Hermite splines. Additional metadata can be added here too.

<p align="center">  
<img width="400" height="342" alt="image" src="https://github.com/user-attachments/assets/9a8c3988-6279-484a-afeb-7a261489208e" />
</p>

- Copy and paste are supported:
  - internally (and between copies of the program)
  - as text, although the current format needs some work to be easily used
  - as a bitmap
- Graphs can be printed, and exported to `svg`
- Undo/ redo is partially implemented.
- Preferences: edge type, etc can be set.
- A rudimentary Python shell is currently available. Upgrading this to [pyQtConsole](https://github.com/pyqtconsole/pyqtconsole) is on the roadmap!

<p align="center">  
<img width="800" height="436" alt="image" src="https://github.com/user-attachments/assets/5362545d-810b-480a-bc51-7b825ff3c49b" />
</p>
    

# Getting started
For Windows, there is a binary release [here](https://github.com/ghillebrand/Higraph/releases)

For other platforms:
- create a folder, 
- ideally, create a virtual enviroment  `python -m venv C:\path\to\new\virtual\environment` (and make it active with `scripts\activate`)
- install PySide with `pip install PySide6`
- copy all the code from here (`git clone https://github.com/ghillebrand/Higraph.git`) or download the zip from the [Releases](https://github.com/ghillebrand/Higraph/releases) page.
- Run `python mainwindow.py`



