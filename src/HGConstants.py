""" Various constants and preferences"""

#Absolute System Constants
#-------------------------

#Constants for edge type
STRAIGHT = 0
SPLINE = 1

APP_NAME = "Higraph"
# Attempt to follow semantic versioning https://semver.org/spec/v2.0.0.html
APP_VERSION = "0.3.1"

# Indices for Qt Item metadata tags 
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QTreeWidgetItem

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

#Helpful for debugging
roleDic={ROLE_NODE: "ROLE_NODE",
        ROLE_EDGE:"ROLE_EDGE", 
        ROLE_HYPEREDGE :"ROLE_HYPEREDGE",
        ROLE_BLOB:"ROLE_BLOB",
        ROLE_HANDLE:"ROLE_HANDLE",
        ROLE_POLYLINE:"ROLE_POLYLINE",
        ROLE_DUMMYNODE:"ROLE_DUMMYNODE"}


#Being replaced by prefs dataclass

#User Preferences
#----------------
#TODO: Reverse the prefs version
NODESIZE = 15
#Selection tolerance
HITSIZE = 5
#Offset to use when pasting nodes
PASTE_OFFSET = 100

BLOB_CORNER_RADIUS = 10
TANGENT_SCALE_FACTOR = 20

#options and defaults
from PySide6.QtGui import QColor

HOVER_COLOUR=QColor("blue")
SELECT_COLOUR=QColor("blue")
DRAWING_COLOUR=QColor("black")
BLOB_HANDLE_COLOUR=QColor("green")
EDGE_HANDLE_COLOUR=QColor("green")
POINT_COLOUR=QColor("purple")

# End of user prefs (to be deleted")
from PySide6.QtCore import QSettings
from PySide6.QtGui import QColor
from dataclasses import dataclass, fields,  field

@dataclass
class UserPreferences:
    """ 
        Modifiable list of constants that the user can update.
        Managed via QSettings
    """

    DISPLAY_NAME_BY_DEFAULT:bool = True
    DISPLAY_BLOB_DESCRIPTION_BY_DEFAULT:bool = False
    BLOB_FONT_SIZE :int = 9
    BLOB_FONT_IS_RESIZABLE:bool = True
    BLOB_NAME_ON_TOP:bool = False

    #Model level, and default for new edges 
    ISDIGRAPH :bool = True
    DEFAULT_EDGE :int = SPLINE

    #options and defaults
    AutoSaveMins:int = 1
    AutoSaveCycleSize:int = 10

    #How to indicate copied names, to avoid confusion
    copySuffix = "+"

    def _get_settings_handle(self) -> QSettings:
        """Returns the OS-specific settings handle."""
        return QSettings("isijingi", APP_NAME)

    def __repr__(self):
        """Inspects all attributes dynamically and converts them to a long string """
        settings = self._get_settings_handle()
        
        r = ""
        for f in fields(self):
            # Convert field names like 'ui_theme' to Qt group paths like 'ui/theme'
            #qt_key = f.name.replace("_", "/", 1)
            qt_key = f.name
            current_value = getattr(self, f.name)
            
            r += f"({qt_key} : {current_value})\t"
        return r
    __str__ = __repr__

    def save(self):
        """Inspects all attributes dynamically and saves them to the OS."""
        settings = self._get_settings_handle()
        
        for f in fields(self):
            # Convert field names like 'ui_theme' to Qt group paths like 'ui/theme'
            #qt_key = f.name.replace("_", "/", 1)
            qt_key = f.name
            current_value = getattr(self, f.name)
            
            settings.setValue(qt_key, current_value)

    def load(self):
        """Inspects all fields, reads from OS, and forces strict type-casting."""
        settings = self._get_settings_handle()
        
        for f in fields(self):
            #qt_key = f.name.replace("_", "/", 1)
            qt_key = f.name
            
            # Fetch from QSettings, fallback to the dataclass's default value if missing
            # If a field uses a default_factory (like a list), we evaluate it
            default_value = f.default if f.default_factory == field().default_factory else f.default_factory()
            raw_value = settings.value(qt_key, default_value)
            
            # --- CRITICAL: Reflection Type-Casting ---
            # QSettings can return data as strings or loose types depending on the platform.
            # We look at the dataclass type-hints to force the correct type back.
            try:
                if f.type is bool:
                    if isinstance(raw_value, str):
                        typed_value = raw_value.lower() in ("true", "1", "yes")
                    else:
                        typed_value = bool(int(raw_value))
                elif f.type is list or (hasattr(f.type, '__origin__') and f.type.__origin__ is list):
                    # Handle lists safely (QSettings returns them natively or as string lists)
                    typed_value = list(raw_value) if raw_value is not None else default_value
                else:
                    # Dynamically invoke the type constructor (e.g., int("15") -> 15)
                    typed_value = f.type(raw_value)
            except (ValueError, TypeError):
                # Fallback safeguard if data on disk is corrupted/un-parsable
                typed_value = default_value

            # Update the class instance attribute dynamically
            setattr(self, f.name, typed_value)

    
#Define this for access by all other modules
prefs = UserPreferences()