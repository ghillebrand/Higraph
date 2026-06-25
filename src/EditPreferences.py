#import sys
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                                 QWidget, QFormLayout, QSpinBox, QCheckBox,
                                 QComboBox, QPushButton, QColorDialog, QDialogButtonBox)
from PySide6.QtGui import QColor

from  HGConstants import *

class EditPreferences(QDialog):
    """
        Edit the preferences
        Gemini June 2026
    """
    def __init__(self, prefs, parent=None):
        super().__init__(parent)
        self.prefs = prefs
        self.setWindowTitle("Preferences")
        self.resize(450, 500)
        
        # Temporary storage for colors so variations are only committed if 'OK' is clicked
        self.loaded_colors = {}

        # Main Layout
        main_layout = QVBoxLayout(self)
        
        # Tab Container
        self.tabs = QTabWidget()
        self.tabs.addTab(self._create_sizing_tab(), "Graph Preferences")
        self.tabs.addTab(self._create_display_tab(), "Display")
        #self.tabs.addTab(self._create_color_tab(), "Canvas Colors")
        main_layout.addWidget(self.tabs)
        
        # Dialog Action Buttons (OK / Cancel)
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

    def _create_sizing_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)

        
        # Routing Engine Preferences
        self.cb_is_digraph = QCheckBox(checked=self.prefs.ISDIGRAPH)
        
        self.combo_edge_type = QComboBox()
        self.combo_edge_type.addItem("Straight Line", STRAIGHT)
        self.combo_edge_type.addItem("Spline Curve", SPLINE)

        # Set current index based on loaded constant
        initial_idx = 1 if self.prefs.DEFAULT_EDGE == SPLINE else 0
        self.combo_edge_type.setCurrentIndex(initial_idx)
        self.sbAutoSaveTime = QSpinBox(minimum=0, maximum=30, value=self.prefs.AutoSaveMins)

        layout.addRow("Default Edge Type:", self.combo_edge_type)
        layout.addRow("Directed Edges (Digraph):", self.cb_is_digraph)
        layout.addRow("Autosave time (Mins, 0= off):", self.sbAutoSaveTime)

        return widget

    def _create_display_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # Boolean Checkboxes
        self.cb_display_name = QCheckBox("Show item names automatically", checked=self.prefs.DISPLAY_NAME_BY_DEFAULT)
        self.cb_display_desc = QCheckBox("Show blob descriptions automatically", checked=self.prefs.DISPLAY_BLOB_DESCRIPTION_BY_DEFAULT)
        self.cb_font_resizable = QCheckBox("Allow text scaling on resize", checked=self.prefs.BLOB_FONT_IS_RESIZABLE)
        self.cb_name_on_top = QCheckBox("Blob name on top (or inside)", checked=self.prefs.BLOB_NAME_ON_TOP)
        
        # Typography Size
        self.sb_font_size = QSpinBox(minimum=4, maximum=144, value=self.prefs.BLOB_FONT_SIZE)

        layout.addRow("Item Names Displayed:", self.cb_display_name)
        layout.addRow("Item Description Layout:", self.cb_display_desc)
        layout.addRow("Base Blob Text Font Size:", self.sb_font_size)
        layout.addRow("Blob Text Resizing:", self.cb_font_resizable)
        layout.addRow("Blob Name Position:", self.cb_name_on_top)
        
        return widget

    #This is cool code, and may be useful later.
    #Not currently used
    def _create_color_tab(self) -> QWidget:
        widget = QWidget()
        layout = QFormLayout(widget)
        
        # List mapping the target Preference variable name to a User-Friendly Label
        color_fields = [
            ("HOVER_COLOUR", "Element Hover State:"),
            ("SELECT_COLOUR", "Active Selection Frame:"),
            ("DRAWING_COLOUR", "Vector Line/Edge Base:"),
            ("BLOB_HANDLE_COLOUR", "Blob Control Handles:"),
            ("EDGE_HANDLE_COLOUR", "Edge Control Handles:"),
            ("POINT_COLOUR", "Vertex Anchor Points:")
        ]

        for attr_name, label_text in color_fields:
            # Extract current QColor instance
            current_color = getattr(self.prefs, attr_name)
            self.loaded_colors[attr_name] = current_color
            
            # Construct color button preview
            btn = QPushButton()
            self._update_button_swatch(btn, current_color)
            
            # Connect runtime click action
            btn.clicked.connect(self._make_color_picker_slot(attr_name, btn))
            layout.addRow(label_text, btn)
            
        return widget

    def _update_button_swatch(self, button: QPushButton, color: QColor):
        """Forces the button to act as a physical color sample swatch."""
        # Convert light colors to contrast safely against text if text is needed
        hex_color = color.name()
        button.setStyleSheet(f"""
            QPushButton {{
                background-color: {hex_color};
                border: 2px solid #555555;
                border-radius: 4px;
                min-height: 28px;
            }}
            QPushButton:hover {{
                border: 2px solid #ffffff;
            }}
        """)

    def _make_color_picker_slot(self, attr_name: str, button: QPushButton):
        """Factory pattern to tie target attributes cleanly to their picking triggers."""
        def open_picker():
            initial_color = self.loaded_colors[attr_name]
            selected_color = QColorDialog.getColor(initial_color, self, f"Select Theme Color")
            
            if selected_color.isValid():
                self.loaded_colors[attr_name] = selected_color
                self._update_button_swatch(button, selected_color)
        return open_picker

    def accept(self):
        """Converts UI states back to the target Dataclass properties upon saving."""
        # 1. Update Sizing Fields
        #self.NODESIZE = self.sb_node_size.value()
        #self.prefs.HITSIZE = self.sb_hit_size.value()
        #self.prefs.PASTE_OFFSET = self.sb_paste_offset.value()
        #self.BLOB_CORNER_RADIUS = self.sb_corner_radius.value()
        #self.prefs.TANGENT_SCALE_FACTOR = self.sb_tangent_scale.value()
        
        # 2. Update Configuration Dropdowns/Booleans
        self.prefs.ISDIGRAPH = self.cb_is_digraph.isChecked()
        self.prefs.DEFAULT_EDGE = self.combo_edge_type.currentData()
        self.prefs.AutoSaveMins= self.sbAutoSaveTime.value()
        #TODO: call mainwindow.autoSave.setInterval(...) as Signal?

        # 3. Update Display Options
        self.prefs.DISPLAY_NAME_BY_DEFAULT = self.cb_display_name.isChecked()
        self.prefs.DISPLAY_BLOB_DESCRIPTION_BY_DEFAULT = self.cb_display_desc.isChecked()
        self.prefs.BLOB_FONT_SIZE = self.sb_font_size.value()
        self.prefs.BLOB_FONT_IS_RESIZABLE = self.cb_font_resizable.isChecked()
        self.prefs.BLOB_NAME_ON_TOP = self.cb_name_on_top.isChecked()

        # 4. Extract Staged Color Items
        for attr_name, color_obj in self.loaded_colors.items():
            setattr(self.prefs, attr_name, color_obj)

        # 5. Commit directly to disk 
        if hasattr(self.prefs, 'save'):
            self.prefs.save()

        super().accept()