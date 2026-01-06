""" Various constants """

#TODO: Put these in a config file at some point
NODESIZE = 15
#Selection tolerance
HITSIZE = 5
#Offset to use when pasting nodes
PASTE_OFFSET = 20

DISPLAY_NAME_BY_DEFAULT = True

#Constants for edge type
STRAIGHT = 0
SPLINE = 1
DEFAULT_EDGE = SPLINE #SPLINE #STRAIGHT 

#Model level default for edges
ISDIGRAPH = True

APP_NAME = "qtPyGraphEdit V02.0"

# Indices for Qt Item metadata tags 
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QListWidgetItem

#index data: item Num from Graph
KEY_INDEX = Qt.UserRole + 1
#type date: item type 
KEY_ROLE = Qt.UserRole + 2

# To let Qt know what are nodes and what are edges
#TODO: Can ListWidgets take any type for roles? (Items can)
ROLE_NODE = QListWidgetItem.ItemType.UserType + 1
ROLE_EDGE = QListWidgetItem.ItemType.UserType + 2
ROLE_HYPEREDGE = QListWidgetItem.ItemType.UserType + 6

#Handles for connecting/ moving
ROLE_HANDLE = QListWidgetItem.ItemType.UserType + 3
ROLE_POLYLINE = QListWidgetItem.ItemType.UserType + 4
ROLE_DUMMYNODE = QListWidgetItem.ItemType.UserType + 5