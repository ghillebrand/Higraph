""" Various constants """

#TODO: Put these in a config file at some point
NODESIZE = 15
#Selection tolerance
HITSIZE = 5
#Offset to use when pasting nodes
PASTE_OFFSET = 20

BLOB_CORNER_RADIUS = 10
TANGENT_SCALE_FACTOR = 20

DISPLAY_NAME_BY_DEFAULT = True
DISPLAY_BLOB_DESCRIPTION_BY_DEFAULT = False
BLOB_FONT_SIZE = 12
BLOB_FONT_IS_RESIZABLE = True
BLOB_NAME_ON_TOP = False

#Constants for edge type
STRAIGHT = 0
SPLINE = 1
DEFAULT_EDGE = SPLINE #SPLINE #STRAIGHT 

#Model level default for edges
ISDIGRAPH = True

APP_NAME = "qtPyGraphEdit V03.0"
# Attempt to follow semantic versioning https://semver.org/spec/v2.0.0.html
APP_VERSION = "0.3.0"

# Indices for Qt Item metadata tags 
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem, QTreeWidgetItem
from PySide6.QtGui import QColor

#index data: item Num from Graph
KEY_INDEX = Qt.UserRole + 1
#type date: item type 
KEY_ROLE = Qt.UserRole + 2

# To let Qt know what are nodes and what are edges
#TODO: Can ListWidgets take any type for roles? (Items can)
# The order here is used for the sort in the listWidget
ROLE_NODE = QTreeWidgetItem.ItemType.UserType + 1
ROLE_BLOB = QTreeWidgetItem.ItemType.UserType + 2
ROLE_EDGE = QTreeWidgetItem.ItemType.UserType + 3
ROLE_HYPEREDGE = QTreeWidgetItem.ItemType.UserType + 4

#Handles for connecting/ moving - don't appear in the model dict
ROLE_HANDLE = QTreeWidgetItem.ItemType.UserType + 10
ROLE_POLYLINE = QTreeWidgetItem.ItemType.UserType + 11
ROLE_DUMMYNODE = QTreeWidgetItem.ItemType.UserType + 12

roleDic={ROLE_NODE: "ROLE_NODE",
        ROLE_EDGE:"ROLE_EDGE", 
        ROLE_HYPEREDGE :"ROLE_HYPEREDGE",
        ROLE_BLOB:"ROLE_BLOB",
        ROLE_HANDLE:"ROLE_HANDLE",
        ROLE_POLYLINE:"ROLE_POLYLINE",
        ROLE_DUMMYNODE:"ROLE_DUMMYNODE"}

#options and defaults

HOVER_COLOUR=QColor("blue")
SELECT_COLOUR=QColor("blue")
DRAWING_COLOUR=QColor("black")
BLOB_HANDLE_COLOUR=QColor("green")
EDGE_HANDLE_COLOUR=QColor("green")
POINT_COLOUR=QColor("purple")