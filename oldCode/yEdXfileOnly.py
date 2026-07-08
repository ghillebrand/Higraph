from __future__ import annotations
"""
Modified from https://github.com/cole-st-john/yEdExtended 

Python library extending yEd functionality through programmatic interface to graphs.
This module only contains the yEd graph creation, read and write code.

"""

"""
BSD 3-Clause License
Copyright (c) 2024, Cole St John
Copyright (c) 2020, James Scott-Brown & The Pyyed Contributors
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.

2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

3. Neither the name of the copyright holder nor the names of its
   contributors may be used to endorse or promote products derived from
   this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""

# import asyncio
import io
import os
import platform
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from random import randint
from shutil import which
from time import sleep
from tkinter import messagebox as msg
from typing import Any, Dict, List, Optional, Union
from warnings import warn
from xml.dom import minidom

#import openpyxl as pyxl
#import pandas as pd
#import psutil

# Enumerated parameters / Constants
app_platform = platform.platform().split("-")[0]
PROGRAM_NAME = "yEd"

# Testing related triggers
testing = False
local_testing = None
show_guis = True

LINE_TYPES = [
    "line",
    "dashed",
    "dotted",
    "dashed_dotted",
]

FONT_STYLES = [
    "plain",
    "bold",
    "italic",
    "bolditalic",
]

HORIZONTAL_ALIGNMENTS = [
    "left",
    "center",
    "right",
]

VERTICAL_ALIGNMENTS = [
    "top",
    "center",
    "bottom",
]

CUSTOM_PROPERTY_SCOPES = [
    "node",
    "edge",
]  # TODO: DOES THIS NEED GROUP?

CUSTOM_PROPERTY_TYPES = [
    "string",
    "int",
    "double",
    "boolean",
]

#GH: Added this to avoid
#self.list_of_labels.append(EdgeLabel(label_text, **kwargs))
#TypeError: EdgeLabel.__init__() got an unexpected keyword argument 'distance'

EDGE_LABEL_PARAMS = [
            "text",
            "height",
            "width",
            "alignment",
            "fontFamily",
            "fontSize",
            "fontStyle",
            "horizontalTextPosition",
            "verticalTextPosition",
            "underlinedText",
            "textColor",
            "iconTextGap",
            "visible",
            "borderColor",
            "backgroundColor",
            "hasBackgroundColor",
            "label_text"
    ]

def checkValue(
    parameter_name: str,
    value: Any,
    validValues: Optional[List[str]] = None,
) -> None:
    """Check whether given inputs
    (e.g. Shape, Arrow type, Line type, etc.)
    are valid (within existing enumerated options).
    If not valid - returns error message for input."""

    if validValues:
        if value not in validValues:
            raise ValueError(f"{parameter_name} '{value}' is not supported. Use: '{', '.join(validValues)}'")


class File:
    """Object to check and act on (primarily yEd) files / filepaths."""

    def __init__(self, file_name_or_path=None, extension=""):
        self.DEFAULT_FILE_NAME = "temp"
        self.EXTENSION: str
        self.dir = self.path_validate(file_name_or_path)
        self.basename = self.base_name_validate(file_name_or_path, extension)
        self.fullpath = os.path.join(self.dir, self.basename)
        self.window_search_name = self.basename + " - yEd"
        self.file_exists = os.path.isfile(self.fullpath)

    def full_path_validate(self):
        self.file_exists = os.path.isfile(self.fullpath)

    def path_validate(self, temp_name_or_path=None):
        """Validate if the file was initialized with valid path - returning the same path - if not valid, return working directory as default path."""
        path = os.getcwd()
        if temp_name_or_path:
            path = os.path.dirname(temp_name_or_path)
            if not os.path.exists(path):
                path = os.getcwd()
        return os.path.realpath(path)

    def base_name_validate(self, temp_name_or_path, extension):
        """Validate / Build valid file name with extension"""
        temp_name = ""
        if temp_name_or_path:
            temp_name = os.path.basename(temp_name_or_path)

        # if no file name - give file name
        temp_name = temp_name or f"{self.DEFAULT_FILE_NAME}"

        # check for extension
        name, extension_from_name = os.path.splitext(temp_name)  # break up name into name + ext
        has_extension_assigned = any(extension_from_name)
        extension_received_from_function = any(extension)

        # if extension - update file object with Extension
        if has_extension_assigned:
            self.EXTENSION = extension_from_name

        # if no extension - assign extension from function and update file object
        elif not has_extension_assigned and extension_received_from_function:
            self.EXTENSION = extension
            temp_name += self.EXTENSION

        # if no extensions in name or from function - assign default file extension and update file object
        elif not has_extension_assigned and not extension_received_from_function:
            self.EXTENSION = ".graphml"  # default file extension
            temp_name += self.EXTENSION

        return temp_name  # give back name+ext combo
    
    #TODO: Move to another file
    def open_with_yed(self, force=False, wait=False):
        """Method to open GraphML file directly with yEd application (must be installed and on path)."""

        # Ensure a valid yed extension file
        if self.EXTENSION != ".graphml":
            raise RuntimeWarning("Trying to open non-graphml file with yEd.")

        print("opening file with yed...")

        open_yed_file(self, force, wait)

        return get_yed_pid()


class Label:
    """Generic Label Class for nodes / edges in yEd"""

    graphML_tagName = None

    def __init__(
        self,
        text="",
        height="18.1328125",
        width=None,
        alignment="center",
        fontFamily="Dialog",
        fontSize="12",
        fontStyle="plain",
        horizontalTextPosition="center",
        verticalTextPosition="center",
        underlinedText="false",
        textColor="#000000",
        iconTextGap="4",
        visible="true",
        borderColor=None,
        backgroundColor=None,
        hasBackgroundColor="false",
    ):
        # make class abstract
        if type(self) is Label:
            raise Exception("Label is an abstract class and cannot be instantiated directly")

        self._text = text

        # Initialize dictionary for parameters
        self._params = {}
        self.updateParam("horizontalTextPosition", horizontalTextPosition, HORIZONTAL_ALIGNMENTS)
        self.updateParam("verticalTextPosition", verticalTextPosition, VERTICAL_ALIGNMENTS)
        self.updateParam("alignment", alignment, HORIZONTAL_ALIGNMENTS)
        self.updateParam("fontStyle", fontStyle, FONT_STYLES)

        # TODO: Implement range checks
        self.updateParam("fontFamily", fontFamily)
        self.updateParam("iconTextGap", iconTextGap)
        self.updateParam("fontSize", fontSize)
        self.updateParam("textColor", textColor)
        self.updateParam("visible", visible.lower(), ["true", "false"])
        self.updateParam("underlinedText", underlinedText.lower(), ["true", "false"])
        if backgroundColor:
            hasBackgroundColor = "true"
        self.updateParam("hasBackgroundColor", hasBackgroundColor.lower(), ["true", "false"])
        self.updateParam("width", width)
        self.updateParam("height", height)
        self.updateParam("borderColor", borderColor)
        self.updateParam("backgroundColor", backgroundColor)

    def updateParam(
        self,
        parameter_name,
        value,
        validValues=None,
    ):
        if value is None:
            return False
        checkValue(parameter_name, value, validValues)

        self._params[parameter_name] = value
        return True

    def addSubElement(self, shape):
        label = ET.SubElement(shape, self.graphML_tagName, **self._params)
        label.text = self._text


class NodeLabel(Label):
    """Node specific label"""

    VALIDMODELPARAMS = {
        "internal": ["t", "b", "c", "l", "r", "tl", "tr", "bl", "br"],
        "corners": ["nw", "ne", "sw", "se"],
        "sandwich": ["n", "s"],
        "sides": ["n", "e", "s", "w"],
        "eight_pos": ["n", "e", "s", "w", "nw", "ne", "sw", "se"],
    }

    graphML_tagName = "y:NodeLabel"

    def __init__(
        self,
        text,
        alignment="center",
        fontFamily="Dialog",
        fontSize="12",
        fontStyle="plain",
        height="18.1328125",
        horizontalTextPosition="center",
        verticalTextPosition="center",
        underlinedText="false",
        iconTextGap="4",
        textColor="#000000",
        visible="true",
        hasBackgroundColor="false",
        width="55.708984375",
        modelName="internal",
        borderColor=None,
        backgroundColor=None,
        modelPosition="c",
    ):
        super().__init__(
            text,
            height,
            width,
            alignment,
            fontFamily,
            fontSize,
            fontStyle,
            horizontalTextPosition,
            verticalTextPosition,
            underlinedText,
            textColor,
            iconTextGap,
            visible,
            borderColor,
            backgroundColor,
            hasBackgroundColor,
        )

        self.updateParam("modelName", modelName, NodeLabel.VALIDMODELPARAMS.keys())
        self.updateParam("modelPosition", modelPosition, NodeLabel.VALIDMODELPARAMS[modelName])


class EdgeLabel(Label):
    """Edge specific label"""

    VALIDMODELPARAMS = {
        "two_pos": ["head", "tail"],
        "centered": ["center"],
        "six_pos": ["shead", "thead", "head", "stail", "ttail", "tail"],
        "three_center": ["center", "scentr", "tcentr"],
        "center_slider": None,
        "side_slider": None,
    }

    graphML_tagName = "y:EdgeLabel"

    def __init__(
        self,
        text,
        alignment="center",
        fontFamily="Dialog",
        fontSize="12",
        fontStyle="plain",
        height="18.1328125",
        horizontalTextPosition="center",
        verticalTextPosition="center",
        underlinedText="false",
        iconTextGap="4",
        textColor="#000000",
        # horizontal_text_position="center",
        # vertical_text_position="center",
        visible="true",
        hasBackgroundColor="false",
        width="55.708984375",
        modelName="centered",
        modelPosition="center",
        borderColor=None,
        backgroundColor=None,
        preferredPlacement=None,
    ):
        super().__init__(
            text,
            height,
            width,
            alignment,
            fontFamily,
            fontSize,
            fontStyle,
            horizontalTextPosition,
            verticalTextPosition,
            underlinedText,
            textColor,
            iconTextGap,
            # horizontal_text_position,
            # vertical_text_position,
            visible,
            borderColor,
            backgroundColor,
            hasBackgroundColor,
        )

        self.updateParam("modelName", modelName, EdgeLabel.VALIDMODELPARAMS.keys())
        self.updateParam("modelPosition", modelPosition, EdgeLabel.VALIDMODELPARAMS[modelName])
        self.updateParam("preferredPlacement", preferredPlacement)


class CustomPropertyDefinition:
    """Custom properties which can be added to yEd objects / graph as a whole"""

    def __init__(
        self,
        scope,
        name,
        property_type,
        default_value,
    ):
        """
        scope: [node|edge]
        name: name of the custom property
        property_type: [string|boolean|int|double]
                        boolean: Java keywords [true|false]
        default_value: any above datatype represented as a string
        """
        self.scope = scope
        self.name = name
        self.property_type = property_type
        self.default_value = default_value
        self.id = "%s_%s" % (self.scope, self.name)

    def convert_to_xml(self) -> ET.Element:
        custom_prop_key = ET.Element("key", id=self.id)
        custom_prop_key.set("for", self.scope)
        custom_prop_key.set("attr.name", self.name)
        custom_prop_key.set("attr.type", self.property_type)

        return custom_prop_key


class Node:
    """yEd Node object - representing a single node in the graph"""

    custom_properties_defs = {}

    VALID_NODE_SHAPES = [
        "rectangle",
        "rectangle3d",
        "roundrectangle",
        "diamond",
        "ellipse",
        "fatarrow",
        "fatarrow2",
        "hexagon",
        "octagon",
        "parallelogram",
        "parallelogram2",
        "star5",
        "star6",
        "star6",
        "star8",
        "trapezoid",
        "trapezoid2",
        "triangle",
        "trapezoid2",
        "triangle",
    ]

    def __init__(
        self,
        name: str = "",  # non-unique node name
        labelAlignment="center",
        shape="rectangle",
        fontFamily="Dialog",
        underlinedText="false",
        fontStyle="plain",
        fontSize="12",
        shapeFill="#FFCC00",
        transparent="false",
        borderColor="#000000",
        borderType="line",
        borderWidth="1.0",
        height=False,
        width=False,
        x=False,
        y=False,
        node_type="ShapeNode",
        UML: Union[bool, dict] = False,
        custom_properties=None,
        description="",
        url="",
    ):
        self.name: str = name
        self.id: str = generate_temp_uuid()  # temporary unique
        self.parent: Union[(Group, Graph, None)] = None

        self.list_of_labels: list[NodeLabel] = []  # initialize list of labels

        if name:
            self.add_label(
                label_text=name,
                alignment=labelAlignment,
                fontFamily=fontFamily,
                underlinedText=underlinedText,
                fontStyle=fontStyle,
                fontSize=fontSize,
            )

        self.node_type = node_type
        self.UML = UML

        # node shape
        checkValue("shape", shape, Node.VALID_NODE_SHAPES)
        self.shape = shape

        # shape fill
        self.shapeFill = shapeFill
        self.transparent = transparent

        # border options
        self.borderColor = borderColor
        self.borderWidth = borderWidth

        checkValue("borderType", borderType, LINE_TYPES)
        self.borderType = borderType

        # geometry
        self.geom = {}
        if height:
            self.geom["height"] = height
        if width:
            self.geom["width"] = width
        if x:
            self.geom["x"] = x
        if y:
            self.geom["y"] = y

        self.description = description
        self.url = url

        # Handle Node Custom Properties
        for name, definition in Node.custom_properties_defs.items():
            if custom_properties:
                for k, v in custom_properties.items():
                    if k not in Node.custom_properties_defs:
                        raise RuntimeWarning("key %s not recognised" % k)
                    if name == k:
                        setattr(self, name, custom_properties[k])
                        break
                else:
                    setattr(self, name, definition.default_value)
            else:
                setattr(self, name, definition.default_value)

    def add_label(self, label_text, **kwargs) -> Node:
        """Adds node label - > returns node for continued node operations"""
        self.list_of_labels.append(NodeLabel(label_text, **kwargs))
        return self

    def convert_to_xml(self) -> ET.Element:
        """Converting node object to xml object"""

        xml_node = ET.Element("node", id=str(self.id))
        data = ET.SubElement(xml_node, "data", key="data_node")
        shape = ET.SubElement(data, "y:" + self.node_type)

        if self.geom:
            ET.SubElement(shape, "y:Geometry", **self.geom)
        # <y:Geometry height="30.0" width="30.0" x="475.0" y="727.0"/>

        ET.SubElement(shape, "y:Fill", color=self.shapeFill, transparent=self.transparent)

        ET.SubElement(
            shape,
            "y:BorderStyle",
            color=self.borderColor,
            type=self.borderType,
            width=self.borderWidth,
        )

        for label in self.list_of_labels:
            label.addSubElement(shape)

        ET.SubElement(shape, "y:Shape", type=self.shape)

        # UML specific
        if self.UML:
            UML = ET.SubElement(shape, "y:UML")

            attributes = ET.SubElement(UML, "y:AttributeLabel", type=self.shape)
            attributes.text = self.UML["attributes"]

            methods = ET.SubElement(UML, "y:MethodLabel", type=self.shape)
            methods.text = self.UML["methods"]

            stereotype = self.UML["stereotype"] if "stereotype" in self.UML else ""
            UML.set("stereotype", stereotype)

        # Special items
        if self.url:
            url_node = ET.SubElement(xml_node, "data", key="url_node")
            url_node.text = self.url

        if self.description:
            description_node = ET.SubElement(xml_node, "data", key="description_node")
            description_node.text = self.description

        # Node Custom Properties
        for name, definition in Node.custom_properties_defs.items():
            node_custom_prop = ET.SubElement(xml_node, "data", key=definition.id)
            node_custom_prop.text = getattr(self, name)

        return xml_node

    @classmethod
    def set_custom_properties_defs(cls, custom_property) -> None:
        cls.custom_properties_defs[custom_property.name] = custom_property


class Edge:
    """yEd Edge - connecting Nodes or Groups"""

    custom_properties_defs = {}

    ARROW_TYPES = [
        "none",
        "standard",
        "white_delta",
        "diamond",
        "white_diamond",
        "short",
        "plain",
        "concave",
        "convex",
        "circle",
        "transparent_circle",
        "dash",
        "skewed_dash",
        "t_shape",
        "crows_foot_one_mandatory",
        "crows_foot_many_mandatory",
        "crows_foot_many_optional",
        "crows_foot_one",
        "crows_foot_many",
        "crows_foot_optional",
    ]

    def __init__(
        self,
        node1: Node,
        node2: Node,
        name: str = "",
        arrowhead="standard",
        arrowfoot="none",
        color="#000000",
        lineType="line",
        width="1.0",
        label_background_color="",
        label_borderColor="",
        source_label=None,
        target_label=None,
        custom_properties=None,
        description="",
        url="",
        list_of_labels=[],
    ):
        # Primary operations
        self.node1: Node = node1
        self.node2: Node = node2
        self.name: str = name
        self.list_of_labels: list[EdgeLabel] = []  # initialize list of labels
        self.id: str = generate_temp_uuid()  # give temp id
        self.parent: Union[(Group, Graph, None)] = None

        if name:
            self.add_label(
                name,
                borderColor=label_borderColor,
                backgroundColor=label_background_color,
            )

        # if not node1 or not node2:
        #     id = "%s_%s" % (node1, node2)

        if source_label is not None:
            self.add_label(
                source_label,
                modelName="six_pos",
                modelPosition="shead",
                preferredPlacement="source_on_edge",
                borderColor=label_borderColor,
                backgroundColor=label_background_color,
            )

        if target_label is not None:
            self.add_label(
                target_label,
                modelName="six_pos",
                modelPosition="thead",
                preferredPlacement="source_on_edge",
                borderColor=label_borderColor,
                backgroundColor=label_background_color,
            )

        if list_of_labels:
            for label_info_dict in list_of_labels:
                #GH Edge name is "label_text" in yEd
                if 'label_text' in label_info_dict.keys() :
                    self.name = label_info_dict['label_text']
                    
                self.add_label(**label_info_dict)

        checkValue("arrowhead", arrowhead, Edge.ARROW_TYPES)
        self.arrowhead = arrowhead

        checkValue("arrowfoot", arrowfoot, Edge.ARROW_TYPES)
        self.arrowfoot = arrowfoot

        checkValue("lineType", lineType, LINE_TYPES)
        self.lineType = lineType

        self.color = color
        self.width = width

        self.description = description
        self.url = url

        # Handle Edge Custom Properties
        for name, definition in Edge.custom_properties_defs.items():
            if custom_properties:
                for k, v in custom_properties.items():
                    if k not in Edge.custom_properties_defs:
                        raise RuntimeWarning("key %s not recognised" % k)
                    if name == k:
                        setattr(self, name, custom_properties[k])
                        break
                else:
                    setattr(self, name, definition.default_value)
            else:
                setattr(self, name, definition.default_value)

    #GH Made label_text a named param to fit with the list_of_labels structure
    def add_label(self, label_text="X", **kwargs):
        """Adding edge label"""
        self.list_of_labels.append(EdgeLabel(label_text, **kwargs))
        # Enable method chaining
        return self

    def convert_to_xml(self) -> ET.Element:
        """Converting edge object to xml object"""

        edge = ET.Element(
            "edge",
            id=str(self.id),
            source=str(self.node1.id),
            target=str(self.node2.id),
        )

        data = ET.SubElement(edge, "data", key="data_edge")
        pl = ET.SubElement(data, "y:PolyLineEdge")

        ET.SubElement(pl, "y:Arrows", source=self.arrowfoot, target=self.arrowhead)
        ET.SubElement(pl, "y:LineStyle", color=self.color, type=self.lineType, width=self.width)

        for label in self.list_of_labels:
            label.addSubElement(pl)

        if self.url:
            url_edge = ET.SubElement(edge, "data", key="url_edge")
            url_edge.text = self.url

        if self.description:
            description_edge = ET.SubElement(edge, "data", key="description_edge")
            description_edge.text = self.description

        # Edge Custom Properties
        for name, definition in Edge.custom_properties_defs.items():
            edge_custom_prop = ET.SubElement(edge, "data", key=definition.id)
            edge_custom_prop.text = getattr(self, name)

        return edge

    @classmethod
    def set_custom_properties_defs(cls, custom_property) -> None:
        cls.custom_properties_defs[custom_property.name] = custom_property


class Group:
    """yEd Group Object (Visual Container of Nodes / Edges / also can recursively act as Node)"""

    VALID_SHAPES = [
        "rectangle",
        "rectangle3d",
        "roundrectangle",
        "diamond",
        "ellipse",
        "fatarrow",
        "fatarrow2",
        "hexagon",
        "octagon",
        "parallelogram",
        "parallelogram2",
        "star5",
        "star6",
        "star6",
        "star8",
        "trapezoid",
        "trapezoid2",
        "triangle",
        "trapezoid2",
        "triangle",
    ]

    def __init__(
        self,
        name: str = "",
        top_level_graph=None,
        labelAlignment="center",
        shape="rectangle",
        closed="false",
        fontFamily="Dialog",
        underlinedText="false",
        fontStyle="plain",
        fontSize="12",
        fill="#FFCC00",
        transparent="false",
        borderColor="#000000",
        borderType="line",
        borderWidth="1.0",
        height=False,
        width=False,
        x=False,
        y=False,
        custom_properties=None,
        description="",
        url="",
    ):
        self.name = name
        self.parent: Union[(Group, Graph, None)] = None  # set during add_group
        self.id = generate_temp_uuid()

        self.nodes: dict[str, Node] = {}
        self.groups: dict[str, Group] = {}
        self.edges: dict[str, Edge] = {}
        self.combined_objects = {}

        self.top_level_graph = top_level_graph

        # node shape
        checkValue("shape", shape, Group.VALID_SHAPES)
        self.shape = shape

        self.closed = closed

        # label formatting options
        self.fontFamily = fontFamily
        self.underlinedText = underlinedText

        checkValue("fontStyle", fontStyle, FONT_STYLES)
        self.fontStyle = fontStyle
        self.fontSize = fontSize

        checkValue("labelAlignment", labelAlignment, HORIZONTAL_ALIGNMENTS)
        self.labelAlignment = labelAlignment

        self.fill = fill
        self.transparent = transparent

        self.geom = {}
        if height:
            self.geom["height"] = height
        if width:
            self.geom["width"] = width
        if x:
            self.geom["x"] = x
        if y:
            self.geom["y"] = y

        self.borderColor = borderColor
        self.borderWidth = borderWidth

        checkValue("borderType", borderType, LINE_TYPES)
        self.borderType = borderType

        self.description = description
        self.url = url

        # Handle Node Custom Properties
        for name, definition in Node.custom_properties_defs.items():
            if custom_properties:
                for k, v in custom_properties.items():
                    if k not in Node.custom_properties_defs:
                        raise RuntimeWarning("key %s not recognised" % k)
                    if name == k:
                        setattr(self, name, custom_properties[k])
                        break
                else:
                    setattr(self, name, definition.default_value)
            else:
                setattr(self, name, definition.default_value)

    def add_node(self, node: Union[Node, str, None] = None, **kwargs) -> Node:
        """Adding node within Group - accepts node object (simply assigns), or node name or none (to create new node without name)."""
        return add_node(self, node, **kwargs)

    def add_group(self, group: Union[Group, str, None] = None, **kwargs) -> Group:
        """Adding group to Group - accepts group object (simply assigns), or group name or none (to create new group without name)"""
        return add_group(self, group, **kwargs)

    def add_edge(
        self,  # owner
        node1: Optional[Union[(Node, Group, str)]] = None,
        node2: Optional[Union[(Node, Group, str)]] = None,
        **kwargs,
    ) -> Edge:
        """Adding edge to Group - for node1/node2 uses node / group objects or accepts names (creating new nodes under self) - or function can alternatively accept an instantiated Edge object."""

        # map args into kwargs in case of spreadsheet data management ops
        if node1:
            kwargs["node1"] = node1
        if node2:
            kwargs["node2"] = node2

        return add_edge(self, **kwargs)

    # Removal of items ==============================
    def remove_node(self, node: Union[Node, str]) -> None:
        """Remove/Delete a node from group - by object or id."""
        remove_node(self, node)

    def remove_group(self, group: Union[Group, str], **kwargs) -> None:
        """Removes a group from within current group object (and same parent graph) - by object or id."""
        remove_group(self, group, **kwargs)

    def remove_edge(self, edge: Union[Edge, str]) -> None:
        """Removing edge from group - by object or id."""
        remove_edge(self, edge)

    def is_ancestor(self, node) -> bool:
        """Check for possible nesting conflict of this id usage"""
        return node.parent is not None and (node.parent is self or self.is_ancestor(node.parent))

    def convert_to_xml(self) -> ET.Element:
        """Converting graph object to graphml xml object"""

        node = ET.Element("node", id=self.id)
        node.set("yfiles.foldertype", "group")
        data = ET.SubElement(node, "data", key="data_node")

        # node for group
        pabn = ET.SubElement(data, "y:ProxyAutoBoundsNode")
        r = ET.SubElement(pabn, "y:Realizers", active="0")
        group_node = ET.SubElement(r, "y:GroupNode")

        if self.geom:
            ET.SubElement(group_node, "y:Geometry", **self.geom)

        ET.SubElement(group_node, "y:Fill", color=self.fill, transparent=self.transparent)

        ET.SubElement(
            group_node,
            "y:BorderStyle",
            color=self.borderColor,
            type=self.borderType,
            width=self.borderWidth,
        )

        label = ET.SubElement(
            group_node,
            "y:NodeLabel",
            modelName="internal",
            modelPosition="t",
            fontFamily=self.fontFamily,
            fontSize=self.fontSize,
            underlinedText=self.underlinedText,
            fontStyle=self.fontStyle,
            alignment=self.labelAlignment,
        )
        label.text = self.name

        ET.SubElement(group_node, "y:Shape", type=self.shape)

        ET.SubElement(group_node, "y:State", closed=self.closed)

        graph = ET.SubElement(node, "graph", edgedefault="directed", id=self.id)

        if self.url:
            url_node = ET.SubElement(node, "data", key="url_node")
            url_node.text = self.url

        if self.description:
            description_node = ET.SubElement(node, "data", key="description_node")
            description_node.text = self.description

        # Add group contained items (recursive)
        for id in self.nodes:
            n = self.nodes[id].convert_to_xml()
            graph.append(n)

        for id in self.groups:
            n = self.groups[id].convert_to_xml()
            graph.append(n)

        for id in self.edges:
            e = self.edges[id].convert_to_xml()
            graph.append(e)

        # Node Custom Properties
        for name, definition in Node.custom_properties_defs.items():
            node_custom_prop = ET.SubElement(node, "data", key=definition.id)
            node_custom_prop.text = getattr(self, name)

        return node
        # ProxyAutoBoundsNode crap just draws bar at top of group


class GraphStats:
    """Object to query and carry complete structure of current (recursive) graph objects and relationships."""

    def __init__(self, graph: Graph):
        self.graph = graph
        self.gather_metadata()  # initial extraction

    def recursive_id_extract(self, graph_or_input_node) -> None:
        """Gather complete structure of current (recursive) graph objects and relationships."""
        sub_nodes = graph_or_input_node.nodes.values()
        sub_groups = graph_or_input_node.groups.values()
        sub_edges = graph_or_input_node.edges.values()

        for node in sub_nodes:
            self.all_nodes[node.id] = node

        for edge in sub_edges:
            self.all_edges[edge.id] = edge

        for group in sub_groups:
            self.all_groups[group.id] = group
            self.recursive_id_extract(group)

    def gather_metadata(self):
        """Gather metadata for all objects in the graph."""

        # Establish / clear data structures
        self.all_nodes: dict[str, Node] = {}
        self.all_groups: dict[str, Group] = {}
        self.all_objects: dict[str, Union[Node, Group]] = {}
        self.all_edges: dict[str, Edge] = {}
        self.all_graph_items: dict[str, Union[Node, Group, Edge]] = {}
        self.id_to_name: dict[str, str] = {}
        self.name_to_ids: dict[str, list[str]] = {}
        self.duplicate_names: set[str] = set()

        # (re)extract core graph data
        self.recursive_id_extract(self.graph)

        # Combine remaining data ========================
        self.all_objects = {**self.all_nodes, **self.all_groups}
        self.all_graph_items = {**self.all_objects, **self.all_edges}
        for obj in self.all_graph_items.values():
            self.id_to_name[obj.id] = obj.name
            current_ids = self.name_to_ids.get(obj.name, [])
            if current_ids:
                self.duplicate_names.add(obj.name)
            current_ids.append(obj.id)
            self.name_to_ids[obj.name] = current_ids

    def find_by_id(self, id) -> Union[Node, Group, Edge, None]:
        """Find object by unique yEd id."""
        return self.all_graph_items.get(id, None)

    def find_by_name(self, name) -> List[Union[Node, Group, Edge]]:
        """Find object by user assigned name - needs to provide for multiple (needs deduplication)."""
        return [self.all_graph_items[id] for id in self.name_to_ids.get(name, [])]

    def name_reused(self, name: str) -> bool:
        """Find object by user assigned name - needs to provide for multiple (needs deduplication)."""
        return name in self.duplicate_names

    def print_stats(self):
        print(f"Graph Stats of {self.graph.id}")
        for k, v in vars(self).items():
            if isinstance(v, Graph):
                continue
            else:
                print(f"\tStat: {k} : {len(v)}")



class Graph:
    """Graph structure - carries yEd graph information"""

    def __init__(self, directed="directed", id="G"):
        self.directed = directed
        self.id = id

        self.nodes: dict[str, Node] = {}
        self.groups: dict[str, Group] = {}
        self.edges: dict[str, Edge] = {}
        self.combined_objects: dict[str, Union[(Node, Group)]] = {}

        self.custom_properties = []

        self.graphml: ET.Element

    # Addition of items ============================
    def add_node(self, node: Union[Node, str, None] = None, **kwargs) -> Node:
        """Adding node within Graph - accepts node object (simply assigns), or node name or none (to create new node)."""
        return add_node(self, node, **kwargs)

    def add_group(self, group: Union[Group, str, None] = None, **kwargs) -> Group:
        """Adding group to Graph"""
        return add_group(self, group, **kwargs)

    def add_edge(
        self,  # owner
        node1: Optional[Union[(Node, Group, str)]] = None,
        node2: Optional[Union[(Node, Group, str)]] = None,
        **kwargs,
    ) -> Edge:
        """Adding edge to Graph - for node1/node2 uses node / group objects or accepts names (creating new nodes under self) - or function can alternatively accept an instantiated Edge object."""

        # map args into kwargs in case of spreadsheet data management ops
        if node1:
            kwargs["node1"] = node1
        if node2:
            kwargs["node2"] = node2

        return add_edge(self, **kwargs)

    def define_custom_property(self, scope, name, property_type, default_value):
        """Adding custom properties to graph (which makes them available on the contained objects in yEd)"""
        if scope not in CUSTOM_PROPERTY_SCOPES:
            raise RuntimeWarning("Scope %s not recognised" % scope)
        if property_type not in CUSTOM_PROPERTY_TYPES:
            raise RuntimeWarning("Property Type %s not recognised" % property_type)
        if not isinstance(default_value, str):
            raise RuntimeWarning("default_value %s needs to be a string" % default_value)
        custom_property = CustomPropertyDefinition(scope, name, property_type, default_value)
        self.custom_properties.append(custom_property)
        if scope == "node":
            Node.set_custom_properties_defs(custom_property)
        elif scope == "edge":
            Edge.set_custom_properties_defs(custom_property)

    # Removal of items ==============================
    def remove_node(self, node: Union[Node, str]) -> None:
        """Remove/Delete a node from graph"""
        remove_node(self, node)

    def remove_group(self, group: Union[Group, str], **kwargs) -> None:
        """Removes a group from within current graph object (and same parent graph)."""
        remove_group(self, group, **kwargs)

    def remove_edge(self, edge: Union[Edge, str]) -> None:
        """Removing edge from graph - uses id."""
        remove_edge(self, edge)

    # TODO: ADD FUNCTIONALITY TO REMOVE / MODIFY CUSTOM PROPERTIES

    # Graph functionalities ===========================
    def construct_graphml(self) -> None:
        """Creating template graphml xml structure and then placing all graph items into it."""

        # Creating XML structure in Graphml format
        # xml = ET.Element("?xml", version="1.0", encoding="UTF-8", standalone="no")

        graphml = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
        graphml.set("xmlns:java", "http://www.yworks.com/xml/yfiles-common/1.0/java")
        graphml.set("xmlns:sys", "http://www.yworks.com/xml/yfiles-common/markup/primitives/2.0")
        graphml.set("xmlns:x", "http://www.yworks.com/xml/yfiles-common/markup/2.0")
        graphml.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        graphml.set("xmlns:y", "http://www.yworks.com/xml/graphml")
        graphml.set("xmlns:yed", "http://www.yworks.com/xml/yed/3")
        graphml.set(
            "xsi:schemaLocation",
            "http://graphml.graphdrawing.org/xmlns http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd",
        )

        # Adding some implementation specific keys for identifying urls, descriptions
        node_key = ET.SubElement(graphml, "key", id="data_node")
        node_key.set("for", "node")
        node_key.set("yfiles.type", "nodegraphics")

        # Definition: url for Node
        node_key = ET.SubElement(graphml, "key", id="url_node")
        node_key.set("for", "node")
        node_key.set("attr.name", "url")
        node_key.set("attr.type", "string")

        # Definition: description for Node
        node_key = ET.SubElement(graphml, "key", id="description_node")
        node_key.set("for", "node")
        node_key.set("attr.name", "description")
        node_key.set("attr.type", "string")

        # Definition: url for Edge
        node_key = ET.SubElement(graphml, "key", id="url_edge")
        node_key.set("for", "edge")
        node_key.set("attr.name", "url")
        node_key.set("attr.type", "string")

        # Definition: description for Edge
        node_key = ET.SubElement(graphml, "key", id="description_edge")
        node_key.set("for", "edge")
        node_key.set("attr.name", "description")
        node_key.set("attr.type", "string")

        # Definition: Custom Properties for Nodes and Edges
        for prop in self.custom_properties:
            graphml.append(prop.convert_to_xml())

        edge_key = ET.SubElement(graphml, "key", id="data_edge")
        edge_key.set("for", "edge")
        edge_key.set("yfiles.type", "edgegraphics")

        # Graph node containing actual objects
        graph = ET.SubElement(graphml, "graph", edgedefault=self.directed, id=self.id)

        # Convert python graph objects into xml structure
        for node in self.nodes.values():
            graph.append(node.convert_to_xml())

        for group in self.groups.values():
            graph.append(group.convert_to_xml())

        for edge in self.edges.values():
            graph.append(edge.convert_to_xml())

        self.graphml = graphml

    def persist_graph(self, file=None, pretty_print=False, overwrite=False, vcs_version=False) -> File:
        """Convert graphml object->xml tree->graphml file.
        Temporary naming used if not given.
        """

        graph_file = File(file, extension=".graphml")

        if graph_file.file_exists and not overwrite:
            raise FileExistsError(f"File already exists: {graph_file.fullpath}")

        self.construct_graphml()

        if pretty_print:
            raw_str = ET.tostring(self.graphml)
            pretty_str = minidom.parseString(raw_str).toprettyxml()
            with open(graph_file.fullpath, "w") as f:
                f.write(pretty_str)
        else:
            tree = ET.ElementTree(self.graphml)
            tree.write(graph_file.fullpath)  # Uses internal method to XML Etree

        # Save simplified version for ease of vcs reviewability
        if vcs_version:
            print("VCS Removed (GH)")
            pass

        # Update the file as existing or not
        graph_file.full_path_validate()

        #print("persisting graph to file:", graph_file.fullpath)
        return graph_file

    def stringify_graph(self) -> str:
        """Returns Stringified version of graph in graphml format"""
        self.construct_graphml()
        # Py2/3 sigh.
        if sys.version_info.major < 3:
            return ET.tostring(self.graphml, encoding="UTF-8")
        else:
            return ET.tostring(self.graphml, encoding="UTF-8").decode()

    def from_XML_string(self, graph_str:str):
        
        # Taken from xml_to_simple_string
        # Preprocessing of file for ease of parsing
        graph_str = graph_str.replace("\n", " ")  # line returns
        graph_str = graph_str.replace("\r", " ")  # line returns
        graph_str = graph_str.replace("\t", " ")  # tabs
        graph_str = re.sub("<graphml .*?>", "<graphml>", graph_str)  # unneeded schema
        graph_str = graph_str.replace("> <", "><")  # empty text
        graph_str = graph_str.replace("y:", "")  # unneeded namespace prefix
        graph_str = graph_str.replace("xml:", "")  # unneeded namespace prefix
        graph_str = graph_str.replace("yfiles.", "")  # unneeded namespace prefix
        graph_str = re.sub(" {1,}", " ", graph_str)  # reducing redundant spaces

        # Begin XML parsing

        id_existing_to_graph_obj = dict()

        #root = ET.fromstring(graph_str)
        root = ET.fromstring(graph_str)

        # Extract off key information==============================
        all_keys = root.findall("key")
        key_dict = dict()
        for a_key in all_keys:
            sub_key_dict = dict()

            key_id = a_key.attrib.get("id")
            # sub_key_dict["label"] = a_key.attrib.get("for")
            sub_key_dict["attr"] = a_key.attrib.get("attr.name", None)
            # sub_key_dict["label"] = a_key.attrib.get("type")
            key_dict[key_id] = sub_key_dict

        # Get major graph node
        graph_root = root.find("graph")
        if graph_root:
            # get major graph info
            graph_dir = graph_root.get("edgedefault")
            graph_id = graph_root.get("id")
        else: #in stringified versions, this may be missing. Use yEd defaults
            graph_dir = "directed"
            graph_id = "G"

        # instantiate graph object
        new_graph = Graph(directed=graph_dir, id=graph_id)

        # Parse graph

        def is_group_node(node):
            return "foldertype" in node.attrib

        def process_node(parent, input_node):
            # Get sub nodes of this node (group or graph)
            current_level_nodes = input_node.findall("node")
            current_level_edges = input_node.findall("edge")

            for node in current_level_nodes:
                # normal nodes
                if not is_group_node(node):
                    node_init_dict = dict()

                    # <node id="n1">
                    existing_node_id = node.attrib.get("id", None)  # FIXME:

                    data_nodes = node.findall("data")
                    info_node = None
                    for data_node in data_nodes:
                        info_node = data_node.find("GenericNode") or data_node.find("ShapeNode")
                        if info_node is not None:
                            node_init_dict["node_type"] = info_node.tag

                            # Geometry information
                            node_geom = info_node.find("Geometry")
                            if node_geom is not None:
                                # print(f"{node_geom.tag = }, {node_geom.get("x") =} {node_geom.get("y") =} ")
                                geometry_vars = ["height", "width", "x", "y"]
                                for var in geometry_vars:
                                    val = node_geom.get(var)
                                    if val is not None:
                                        node_init_dict[var] = val

                            node_label = info_node.find("NodeLabel")
                            if node_label is not None:
                                node_init_dict["name"] = node_label.text

                                # TODO: PORT REST OF NODELABEL

                            # <Fill color="#FFCC00" transparent="false" />
                            fill = info_node.find("Fill")
                            if fill is not None:
                                node_init_dict["shapeFill"] = fill.get("color")
                                node_init_dict["transparent"] = fill.get("transparent")

                            # <BorderStyle color="#000000" type="line" width="1.0" />
                            border_style = info_node.find("BorderStyle")
                            if border_style is not None:
                                node_init_dict["borderColor"] = border_style.get("color")
                                node_init_dict["borderType"] = border_style.get("type")
                                node_init_dict["borderWidth"] = border_style.get("width")

                            # <Shape type="rectangle" />
                            shape_sub = info_node.find("Shape")
                            if shape_sub is not None:
                                node_init_dict["shape"] = shape_sub.get("type")

                            uml = info_node.find("UML")
                            if uml is not None:
                                node_init_dict["shape"] = uml.get("AttributeLabel")
                            # TODO: THERE IS FURTHER DETAIL TO PARSE HERE under uml
                        else:
                            info = data_node.text
                            if info is not None:
                                info = re.sub(r"<!\[CDATA\[", "", info)  # unneeded schema
                                info = re.sub(r"\]\]>", "", info)  # unneeded schema

                                the_key = data_node.attrib.get("key")

                                info_type = key_dict[the_key]["attr"]
                                if info_type in ["url", "description"]:
                                    node_init_dict[info_type] = info
                    # Removing empty items
                    node_init_dict = {key: value for (key, value) in node_init_dict.items() if value is not None}
                    # create node
                    new_node = parent.add_node(**node_init_dict)
                    id_existing_to_graph_obj[existing_node_id] = new_node

                # group nodes
                # <node id="n2" yfiles.foldertype="group">
                elif is_group_node(node):
                    group_init_dict = dict()

                    # <node id="n1">
                    existing_group_id = node.attrib.get("id", None)

                    # Actual Group Data ===================================
                    data_nodes = node.findall("data")
                    for data_node in data_nodes:
                        proxy = data_node.find("ProxyAutoBoundsNode")
                        if proxy is not None:
                            realizer = proxy.find("Realizers")

                            group_nodes = realizer.findall("GroupNode")

                            for group_node in group_nodes:
                                geom_node = group_node.find("Geometry")
                                if geom_node is not None:
                                    group_init_dict["height"] = geom_node.attrib.get("height", None)
                                    group_init_dict["width"] = geom_node.attrib.get("width", None)
                                    group_init_dict["x"] = geom_node.attrib.get("x", None)
                                    group_init_dict["y"] = geom_node.attrib.get("y", None)

                                fill_node = group_node.find("Fill")
                                if fill_node is not None:
                                    group_init_dict["fill"] = fill_node.attrib.get("color", None)
                                    group_init_dict["transparent"] = fill_node.attrib.get("transparent", None)

                                borderstyle_node = group_node.find("BorderStyle")
                                if borderstyle_node is not None:
                                    group_init_dict["borderColor"] = borderstyle_node.attrib.get("color", None)
                                    group_init_dict["borderType"] = borderstyle_node.attrib.get("type", None)
                                    group_init_dict["borderWidth"] = borderstyle_node.attrib.get("width", None)

                                nodelabel_node = group_node.find("NodeLabel")
                                if nodelabel_node is not None:
                                    group_init_dict["name"] = (
                                        nodelabel_node.text
                                    )  # TODO: SHOULD THIS JUST BE THE FIRST ONE?  IN OTHER WORDS - IS THERE MULTIPLE THINGS TO BE CAUGHT HERE?
                                    group_init_dict["fontFamily"] = nodelabel_node.attrib.get("fontFamily", None)
                                    group_init_dict["fontSize"] = nodelabel_node.attrib.get("fontSize", None)
                                    group_init_dict["underlinedText"] = nodelabel_node.attrib.get("underlinedText", None)
                                    group_init_dict["fontStyle"] = nodelabel_node.attrib.get("fontStyle", None)
                                    group_init_dict["labelAlignment"] = nodelabel_node.attrib.get("alignment", None)

                                group_shape_node = group_node.find("Shape")
                                if group_shape_node is not None:
                                    group_init_dict["shape"] = group_shape_node.attrib.get("type", None)

                                group_state_node = group_node.find("State")
                                if group_state_node is not None:
                                    group_init_dict["closed"] = group_state_node.attrib.get("closed", None)
                                    # group_init_dict["aaa"] = group_state_node.attrib.get("closedHeight",None)
                                    # group_init_dict["aaaa"] = group_state_node.attrib.get("closedWidth",None)
                                    # group_init_dict["aaaa"] = group_state_node.attrib.get("innerGraphDisplayEnabled",None)

                                break

                        else:
                            info = data_node.text
                            if info is not None:
                                info = re.sub(r"<!\[CDATA\[", "", info)  # unneeded schema
                                info = re.sub(r"\]\]>", "", info)  # unneeded schema

                                the_key = data_node.attrib.get("key")

                                info_type = key_dict[the_key]["attr"]
                                if info_type in ["url", "description"]:
                                    group_init_dict[info_type] = info

                    # Group - Graph node
                    sub_graph_node = node.find("graph")

                    # Removing empty items
                    group_init_dict = {key: value for (key, value) in group_init_dict.items() if value is not None}

                    # Creating new group
                    new_group = parent.add_group(**group_init_dict)
                    id_existing_to_graph_obj[existing_group_id] = new_group

                    # Recursive processing
                    if sub_graph_node is not None:
                        process_node(parent=new_group, input_node=sub_graph_node)

                # unknown node type
                else:
                    raise NotImplementedError

            # edges then establish connections
            for edge_node in current_level_edges:
                edge_init_dict = dict()

                # <node id="n1">
                edge_id = edge_node.attrib.get("id", None)
                node1_id = edge_node.attrib.get("source", None)
                node2_id = edge_node.attrib.get("target", None)

                try:
                    edge_init_dict["node1"] = id_existing_to_graph_obj.get(node1_id)
                    edge_init_dict["node2"] = id_existing_to_graph_obj.get(node2_id)
                except Exception:  # TODO: MAKE MORE SPECIFIC
                    print(f"One of nodes of existing edge {edge_id} not found: {node1_id}, {node2_id} ")

                # FIXME: HOW TO MOVE FROM NODE IDS TO NODE OBJECTS - MOVE THROUGH GRAPHML FOR THE TEXT OF THAT OBJECT? - OR USE A DICTIONARY

                # <data key="d5">
                data_nodes = edge_node.findall("data")
                for data_node in data_nodes:
                    #GH TODO: Add Bezier edge
                    polylineedge = data_node.find("PolyLineEdge")            

                    if polylineedge is not None:
                        # TODO: ADD POSITION MANAGEMENT
                        # path_node = polylineedge.find("Path")
                        # if path_node:
                        #   edge_init_dict["label"] = path_node.attrib.get("sx")
                        #   edge_init_dict["label"] = path_node.attrib.get("sy")
                        #   edge_init_dict["label"] = path_node.attrib.get("tx")
                        #   edge_init_dict["label"] = path_node.attrib.get("ty")

                        linestyle_node = polylineedge.find("LineStyle")
                        if linestyle_node is not None:
                            edge_init_dict["color"] = linestyle_node.attrib.get("color", None)
                            edge_init_dict["lineType"] = linestyle_node.attrib.get("type", None)
                            edge_init_dict["width"] = linestyle_node.attrib.get("width", None)

                        arrows_node = polylineedge.find("Arrows")
                        if arrows_node is not None:
                            edge_init_dict["arrowfoot"] = arrows_node.attrib.get("source", None)
                            edge_init_dict["arrowhead"] = arrows_node.attrib.get("target", None)

                        # edgelabel_node = polylineedge.find("EdgeLabel")
                        edgelabel_nodes = polylineedge.findall("EdgeLabel")
                        if edgelabel_nodes is not None:
                            edge_init_dict["list_of_labels"] = list()
                            for edgelabel_node in edgelabel_nodes:
                                label_dict = dict()

                                {
                                    label_dict.update({key: edgelabel_node.attrib[key]})
                                    for key in edgelabel_node.attrib
                                    if key not in ["text", "source", "target"]
                                }

                                label_dict["label_text"] = edgelabel_node.text or ""
                                # edge_init_dict["arrowfoot"] = edgelabel_node.attrib.get("source", None)
                                # edge_init_dict["arrowhead"] = edgelabel_node.attrib.get("target", None)

                                edge_init_dict["list_of_labels"].append(label_dict)

                    else:
                        info = data_node.text
                        if info is not None:
                            info = re.sub(r"<!\[CDATA\[", "", info)  # unneeded schema
                            info = re.sub(r"\]\]>", "", info)  # unneeded schema

                            the_key = data_node.attrib.get("key")

                            info_type = key_dict[the_key]["attr"]
                            if info_type in ["url", "description"]:
                                edge_init_dict[info_type] = info

                # bendstyle_node = polylineedge.find("BendStyle")
                # edge_init_dict["smoothed"] = linestyle_node.attrib.get("smoothed") # TODO: ADD THIS

                # TODO:
                #   CUSTOM PROPERTIES

                # Removing empty items
                #print(f"{edge_init_dict["node1"].id =} \nEdge Dict BEFORE STRIP\n{edge_init_dict = }")
                edge_init_dict = {key: value for (key, value) in edge_init_dict.items() if value is not None}
                
                #GH: Remove unhandled EDGE_LABEL_ITEMS
                if 'list_of_labels' in edge_init_dict.keys():
                    temp_list_of_labels = edge_init_dict['list_of_labels'][0]
                    #print(f"{temp_list_of_labels = }")
                    temp_list_of_labels = {key: value for (key, value) in temp_list_of_labels.items() if key in EDGE_LABEL_PARAMS}
                    #print(f"\n after strip {temp_list_of_labels = }")
                    #'label_text' must be the first item in the list
                    label = temp_list_of_labels.pop('label_text')
                    labTextDict = {'label_text': label}
                    edge_init_dict['list_of_labels'] = [labTextDict, temp_list_of_labels]
                
                #print(f"Edge Dict AFTER STRIP\n{edge_init_dict = }")
                parent.add_edge(**edge_init_dict)

        process_node(parent=new_graph, input_node=graph_root)

        return new_graph


    def from_existing_graph(self, file: str | File):
        """Parse GraphML xml of existing/stored graph file into python Graph structure."""



        # Manage file input ==============================
        if isinstance(file, File):
            graph_file = file
        else:
            graph_file = File(file, extension=".graphml")
        if not graph_file.file_exists:
            raise FileNotFoundError

        # Simplify input into string ==============================
        graph_str = xml_to_simple_string(graph_file.fullpath)

        #GH call the string to graph code
        new_graph = self.from_XML_string(graph_str)

        return new_graph

    def manage_graph_data_in_spreadsheet(self, type: Optional[str] = None):
        """Port graph data into spreadsheet in several formats for easy and bulk creation and management.  Then ports back into python graph structure. Types: "obj_and_hierarchy", "object_data", "relations" """
        return SpreadsheetManager().bulk_data_management(graph=self, type=type)

    def gather_graph_stats(self) -> GraphStats:
        """Creating current Graph Stats for the current graph"""
        return GraphStats(graph=self)

    def run_graph_rules(self, correct: Optional[str] = None) -> None:
        """Check a few graph items that are most likely to fail following manual data management.  Correct them automatically or manually."""
        if correct is None:  #  ("auto", "manual")
            correct = "auto"

        stats = self.gather_graph_stats()

        def stranded_edges_check(self, graph_stats: GraphStats, correct: str) -> set[Edge]:
            """Check for edges with no longer valid nodes (these will prevent yEd from opening the file).  Correct them automatically or manually."""
            stranded_edges = set()
            for edge_id, edge in graph_stats.all_edges.items():
                node1_exist = edge.node1 in graph_stats.all_objects.values()
                node2_exist = edge.node2 in graph_stats.all_objects.values()
                at_least_one_edge = any([node1_exist, node2_exist])
                stranded_edge = not all([node1_exist, node2_exist])
                if stranded_edge:
                    stranded_edges.add(edge)

            if correct == "auto":
                for edge in stranded_edges:
                    edge.parent.remove_edge(edge)  # Any further postprocessing needed?

            elif correct == "manual":
                # spreadsheet - run relations and highlight edges with issues?
                raise NotImplementedError("Manual correction of stranded edges is not yet implemented.")

            # offer review or update edges
            return stranded_edges

        stranded_edges = stranded_edges_check(self, stats, correct)


# Utilities =======================================
def xml_to_simple_string(file_path) -> str:
    """Takes GraphML xml in string format and reduces complexity of the string for simpler parsing (without loss of any significant information).  Returns simplified string."""
    graph_str = ""
    try:
        with open(file_path, "r") as graph_file:
            graph_str = graph_file.read()

    except FileNotFoundError:
        print(f"Error, file not found: {file_path}")
        raise FileNotFoundError(f"Error, file not found: {file_path}")
    else:
        # Preprocessing of file for ease of parsing
        graph_str = graph_str.replace("\n", " ")  # line returns
        graph_str = graph_str.replace("\r", " ")  # line returns
        graph_str = graph_str.replace("\t", " ")  # tabs
        graph_str = re.sub("<graphml .*?>", "<graphml>", graph_str)  # unneeded schema
        graph_str = graph_str.replace("> <", "><")  # empty text
        graph_str = graph_str.replace("y:", "")  # unneeded namespace prefix
        graph_str = graph_str.replace("xml:", "")  # unneeded namespace prefix
        graph_str = graph_str.replace("yfiles.", "")  # unneeded namespace prefix
        graph_str = re.sub(" {1,}", " ", graph_str)  # reducing redundant spaces

    return graph_str


def generate_temp_uuid() -> str:
    """Temporary unique id for objects."""
    return str(randint(1, 1000000))


def assign_traceable_id(obj) -> None:
    """Creating unique traceable id for graph objects in similar format to yEd:
    n0, n1, ... for nodes and groups at a level
    e0, e1, ... for edges at a level
    n2::n2::n0 for nodes and groups at following level - full tracability
    n2::e0 for edges at following level - full tracability (lowest level ownership where linked)
    """
    parent_id_prefix = ""
    if isinstance(obj.parent, Group):
        parent_id_prefix = obj.parent.id + "::"

    if isinstance(obj, Node) or isinstance(obj, Group):
        # This object already logged under this owner - rename to order in list
        if obj in list(obj.parent.combined_objects.values()):
            obj_parent_index = list(obj.parent.combined_objects.values()).index(obj)
            obj.id = parent_id_prefix + "n" + str(obj_parent_index)  # FIXME: HAS TO BE THE INDEX OF THIS ITEM IN THE LIST
        # this item is new - appending to end of current dict - give new number for that level
        else:
            obj.id = parent_id_prefix + "n" + str(len(obj.parent.combined_objects))
    elif isinstance(obj, Edge):
        if obj in list(obj.parent.edges.values()):
            obj_parent_index = list(obj.parent.edges.values()).index(obj)
            obj.id = parent_id_prefix + "e" + str(obj_parent_index)
        else:
            obj.id = parent_id_prefix + "e" + str(len(obj.parent.edges))  # FIXME: HAS TO BE THE INDEX OF THIS ITEM IN THE LIST

    # print(obj.id)


def update_traceability(obj, owner, operation, heal=True) -> None:
    """Updating ownership of object based on parent."""

    if operation == "add":
        # Setting parent
        obj.parent = owner
        if isinstance(obj.parent, Group):
            obj.top_level_graph = obj.parent.top_level_graph
        else:
            obj.top_level_graph = obj.parent

        assign_traceable_id(obj)

        if isinstance(obj, Node):
            obj.parent.nodes[obj.id] = obj
            obj.parent.combined_objects[obj.id] = obj
        elif isinstance(obj, Group):
            obj.parent.groups[obj.id] = obj
            obj.parent.combined_objects[obj.id] = obj
        elif isinstance(obj, Edge):
            obj.parent.edges[obj.id] = obj

    if operation == "remove":
        if isinstance(obj, Node):
            del obj.parent.nodes[obj.id]
            del obj.parent.combined_objects[obj.id]

        elif isinstance(obj, Group):
            # reroute dependents ===================
            if heal:
                for node in obj.nodes.values():
                    node.parent = obj.parent  # reassign parent: node side
                    obj.parent.nodes[node.id] = node  # reassign parent: group side

                for edge in obj.edges.values():
                    edge.parent = obj.parent  # reassign parent: edge side
                    obj.parent.edges[edge.id] = edge  # reassign parent: group/graph side

                for group in obj.groups.values():
                    group.parent = obj.parent
                    obj.parent.groups[group.id] = group  # reassign parent: group side

            del obj.parent.groups[obj.id]
            del obj.parent.combined_objects[obj.id]

        elif isinstance(obj, Edge):
            del obj.parent.edges[obj.id]


# Reused graph functionality ============================
def add_node(owner, node, **kwargs) -> Node:
    """Adding node within Graph - accepts node object (simply assigns), or node name or none (to create new node)."""
    if isinstance(node, Node):
        # just update traceability - ownership
        pass
    if isinstance(node, str) or node is None:
        if node:
            kwargs["name"] = node
        node = Node(**kwargs)
    update_traceability(obj=node, owner=owner, operation="add")
    return node


def add_edge(owner: Union[(Graph, Group)], **kwargs) -> Edge:
    """Adding edge to graph -
    if node1/node2 names provided - creates nodes under the owner,
    otherwise, expects node / group objects at or under this owner level.
    Alternatively, can pass in an instantiated Edge object for ownership update."""

    edge = kwargs.get("edge", None)

    # If an edge is not passed in, create one
    if not edge:
        node1 = kwargs.get("node1", None)
        node2 = kwargs.get("node2", None)

        # Creating nodes if necessary from names - under owner
        if isinstance(node1, str):
            node1 = owner.add_node(node1)
            kwargs["node1"] = node1

        if isinstance(node2, str):
            node2 = owner.add_node(node2)
            kwargs["node2"] = node2

        # If not valid object, like None, should error out
        if not isinstance(node1, (Node, Group)):
            raise RuntimeWarning(f"Object {node1} doesn't exist")

        if not isinstance(node2, (Node, Group)):
            raise RuntimeWarning(f"Object {node2} doesn't exist")

        # http://graphml.graphdrawing.org/primer/graphml-primer.html#Nested
        # The edges between two nodes in a nested graph have to be declared in a graph,
        # which is an ancestor of both nodes in the hierarchy.

        if isinstance(owner, Group):
            if not (owner.is_ancestor(node1) and owner.is_ancestor(node2)):
                raise RuntimeWarning("Group %s is not ancestor of both %s and %s" % (owner.id, node1.id, node2.id))

        edge = Edge(**kwargs)

    # If an edge is passed in, continue on to traceability update
    else:
        pass

    update_traceability(obj=edge, owner=owner, operation="add")

    return edge


def add_group(owner, group, **kwargs) -> Group:
    """Adding group to graph"""
    if isinstance(group, Group):
        # just needs update to traceability - ownership
        pass
    if isinstance(group, str) or group is None:
        # if isinstance(owner, Group):
        #     top_level_graph = owner.top_level_graph
        # else:
        #     top_level_graph = owner
        if group:
            kwargs["name"] = group
        group = Group(**kwargs)
    heal: bool = kwargs.get("heal", True)
    update_traceability(obj=group, owner=owner, operation="add", heal=heal)
    return group


def remove_node(owner, node, **kwargs) -> None:
    """Remove/Delete a node - accepts node or node id"""
    if isinstance(node, Node):
        if node not in owner.nodes.values():
            raise RuntimeWarning(f"Node {node.id} doesn't exist")
    if isinstance(node, str):
        if node not in owner.nodes:
            raise RuntimeWarning(f"Node {node} doesn't exist")
        node = owner.nodes[node]
    update_traceability(obj=node, owner=owner, operation="remove")


def remove_group(owner, group, **kwargs) -> None:
    """Removes a group from within current object."""
    if isinstance(group, Group):
        if group not in owner.groups.values():
            raise RuntimeWarning(f"Group {group.id} doesn't exist")
    if isinstance(group, str):
        if group not in owner.groups:
            raise RuntimeWarning(f"Group {group} doesn't exist")
        group = owner.groups[group]

    update_traceability(obj=group, owner=owner, operation="remove")


def remove_edge(owner, edge, **kwargs) -> None:
    """Removing edge - uses id."""
    if isinstance(edge, Edge):
        if edge not in owner.edges.values():
            raise RuntimeWarning(f"Edge {edge.id} doesn't exist")
    if isinstance(edge, str):
        if edge not in owner.edges:
            raise RuntimeWarning(f"Edge {edge} doesn't exist")
        edge = owner.edges[edge]
    update_traceability(obj=edge, owner=owner, operation="remove")
