""" copilot/ chatGPT code to edit an edge """

from PySide6.QtWidgets import (
    QWidget, QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QPushButton, QDialogButtonBox, QFormLayout, QComboBox,
    QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import Qt
from  HGConstants import *

class EditVisNodeItemDialog(QDialog):
    """
    Dialog to edit all attributes of a VisEdgeItem.
    Pass an instance of VisEdgeItem to the constructor.
    When accepted, updates the attributes of the original object.
    """

    def __init__(self, visNodeItem, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit node {visNodeItem.metadata['name']} ")
        self.visNodeItem = visNodeItem

        # --- Dialog Layout ---
        layout = QVBoxLayout(self)

        form = QFormLayout()
        # node Number (read-only)
        self.nodeNumLabel = QLabel(str(visNodeItem.nodeNum))
        form.addRow("node ID", self.nodeNumLabel)

        #Display parents and children
        parents=",".join([str(p) for p in visNodeItem.model.Gr.nodeD[visNodeItem.nodeNum].parents])
        #parents = ",".join([str(p.nodeNum) for p in visNodeItem.parents]) JH
        children=",".join([str(c) for c in visNodeItem.model.Gr.nodeD[visNodeItem.nodeNum].children])
        #children = ",".join([str(c.nodeNum) for c in visNodeItem.children]) JH
        self.parentsLabel = QLabel(parents)
        self.childrenLabel = QLabel(children)
        form.addRow("Parents:", self.parentsLabel)
        form.addRow("Children:", self.childrenLabel)

        # Start Edges Index (read-only)
        startsEdgestr = ",".join([str(ed.edgeNum) for ed in visNodeItem.startsEdges])
        endsEdgestr = ",".join([str(ed.edgeNum) for ed in visNodeItem.endsEdges])

        self.startsEdgesLabel = QLabel(startsEdgestr)
        self.endsEdgesLabel = QLabel(endsEdgestr)
        form.addRow("Starts Edges:", self.startsEdgesLabel)
        form.addRow("Ends Edges:", self.endsEdgesLabel)

        #Add in the metadata
        #update metadata for description from textbox
        if 'description' in self.visNodeItem.metadata \
                and self.visNodeItem.metadata['description']!=self.visNodeItem.blobDescription.toPlainText():
            self.visNodeItem.metadata['description']=self.visNodeItem.blobDescription.toPlainText()

        self.nodeMetadata = self.visNodeItem.metadata
        self.nodeMetadataAttributes = self.visNodeItem.metadataAttributes
        self.metadataWidget = MetadataEditorWidget(self.visNodeItem.metadata,
                                                    self.visNodeItem.metadataAttributes, self)
        form.addRow("Metadata:", self.metadataWidget)

        layout.addLayout(form)
        #Make it wider
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        # Dialog buttons
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)


    def accept(self):
        #Grab the metadata changes to reflect elsewhere
        self.metadataWidget.setMetadataAndAttributes(self.visNodeItem)

        newName = self.nodeMetadata["name"]
        if hasattr(self.visNodeItem, "dispText"):
            self.visNodeItem.dispText = newName

        graphModel = getattr(self.visNodeItem, "model", None)
        nodeNum = self.visNodeItem.nodeNum

        # Update abstract graph metadata and model
        if graphModel:
            graphModel.Gr.nodeD[nodeNum].metadata['name'] = newName

            # Also update model item text if available
            modelItem = graphModel.findItemByIdx(nodeNum)
            if modelItem:
                modelItem.setText(newName)

            # Update the corresponding list widget item if necessary
            listWidget = getattr(self.visNodeItem, "listWidget", None)
            if listWidget:
                lwItem = listWidget.findItemByIdx(nodeNum)
                if lwItem:
                    lwItem.setText(newName)
            # Update treeWidget
            treeWidget = getattr(self.visNodeItem, "treeWidget", None)
            twItems=treeWidget.findItems(str(nodeNum), Qt.MatchRecursive, 1)
            for twItem in twItems:
                twItem.setText(0,newName)


        self.visNodeItem.update()

        # update the scene and list widget visually
        parentWin = self.parent()
        parentWin.Scene.update()
        parentWin.ui.listWidget.repaint()
        self.visNodeItem.setMetadataDisplay()
        super().accept()

class EditVisEdgeItemDialog(QDialog):
    """
    Dialog to edit all attributes of a VisEdgeItem.
    Pass an instance of VisEdgeItem to the constructor.
    When accepted, updates the attributes of the original object.
    original code from chatGPT, modified
    """

    def __init__(self, visEdgeItem, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit edge {visEdgeItem.metadata['name']} ")
        self.visEdgeItem = visEdgeItem

        # --- Gather initial values ---
        edgeNum = getattr(visEdgeItem, "edgeNum", "")
        #dispText = getattr(visEdgeItem, "dispText", "")
        startNodeIdx = getattr(visEdgeItem.startNode[0], "nodeNum", "")
        endNodeIdx = getattr(visEdgeItem.endNode[0], "nodeNum", "")
        polyEdge = visEdgeItem._polyEdge
        isDirected = getattr(visEdgeItem, "isDirected", None)

        # Attributes from the model (if present)
        graphModel = getattr(visEdgeItem, "model", None)
        #self.edgeMetadata = graphModel.Gr.edgeD[edgeNum].metadata if graphModel else {}
        self.edgeMetadata = self.visEdgeItem.metadata
        self.edgeMetadataAttributes = self.visEdgeItem.metadataAttributes

        startNodeName = graphModel.Gr.nodeD[startNodeIdx].metadata["name"]
        endNodeName = graphModel.Gr.nodeD[endNodeIdx].metadata["name"]

        edgeName = self.visEdgeItem.metadata.get("name", self.visEdgeItem.textItem.toPlainText())

        # --- Dialog Layout ---
        layout = QVBoxLayout(self)

        form = QFormLayout()
        # Edge Number (read-only)
        self.edgeNumLabel = QLabel(str(edgeNum))
        form.addRow("Edge ID", self.edgeNumLabel)

        # Start Node Index (read-only)
        self.startNodeLabel = QLabel(str(startNodeIdx) +": "+ startNodeName)

        form.addRow("Start Node", self.startNodeLabel)

        # End Node Index (read-only)
        self.endNodeLabel = QLabel(str(endNodeIdx)+": "+ endNodeName)
        form.addRow("End Node", self.endNodeLabel)

        # Directed?
        self.directedCheckbox = QCheckBox("Directed")
        if isDirected is not None:
            self.directedCheckbox.setChecked(isDirected)
        form.addRow("Is Directed", self.directedCheckbox)

        #Edge type        
        self.edgeTypeCombo = QComboBox()
        self.edgeTypeCombo.addItems(['Straight', 'Spline'])
        #choose the right type (Straight = default)
        if polyEdge == SPLINE:
            self.edgeTypeCombo.setCurrentIndex(1)     
        form.addRow("Edge drawing type",self.edgeTypeCombo)

        #Metadata edit

        self.metadataWidget = MetadataEditorWidget(self.visEdgeItem.metadata,
                                                    self.visEdgeItem.metadataAttributes, self)
        form.addRow("Metadata:", self.metadataWidget)

        layout.addLayout(form)
        #Make it wider
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)

        # Dialog buttons
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def accept(self):
        #print("Edit VisEdge Accept")
        # Update metadata (which includes name)
        #update metadata
        #self.edgeMetadata.clear()
        #self.edgeMetadata.update(self.metadataWidget.setMetadataAndAttributes())
        self.metadataWidget.setMetadataAndAttributes(self.visEdgeItem)

        # --- Update VisEdgeItem attributes ---
        #newName = self.nameEdit.text()
        newName = self.edgeMetadata["name"]
        if hasattr(self.visEdgeItem, "textItem"):
            self.visEdgeItem.textItem.setPlainText(newName)

        graphModel = getattr(self.visEdgeItem, "model", None)
        edgeNum = self.visEdgeItem.edgeNum

        # Update abstract graph metadata and model
        if graphModel:
            graphModel.Gr.edgeD[edgeNum].metadata['name'] = newName

            # Also update model item text if available
            modelItem = graphModel.findItemByIdx(edgeNum)
            if modelItem:
                modelItem.setText(newName)

            # Update the corresponding list widget item if necessary
            listWidget = getattr(self.visEdgeItem, "listWidget", None)
            if listWidget:
                lwItem = listWidget.findItemByIdx(edgeNum)
                if lwItem:
                    lwItem.setText(newName)
                        # Update treeWidget
            treeWidget = getattr(self.visEdgeItem, "treeWidget", None)
            twItem=treeWidget.findItemByIdx(edgeNum)
            twItem.setText(1,newName)

        # Directed
        isDirected = self.directedCheckbox.isChecked()
        self.visEdgeItem.setDirected(isDirected)

        #Linetype - index matches STRAIGHT==0 and SPLINE==1
        lineType = self.edgeTypeCombo.currentIndex()
        self.visEdgeItem.setPolylineType(lineType)

        self.visEdgeItem.update()

        # update the scene and list widget visually
        parentWin = self.parent()
        if parentWin and hasattr(parentWin, "Scene"):
            parentWin.Scene.update()
        if parentWin and hasattr(parentWin.ui, "listWidget"):
            parentWin.ui.listWidget.repaint()
            parentWin.ui.treeWidget.repaint()
        
        self.visEdgeItem.setMetadataDisplay()
        super().accept()


class MetadataEditorWidget(QWidget):
    def __init__(self, metadata: dict, metadataAttributes:dict, parent=None):
        super().__init__(parent)

        self._metadata = metadata

        self.table = QTableWidget(0, 3, self)
        self.table.setHorizontalHeaderLabels(["Key", "Value", "Display"])

        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.setEditTriggers(
            QTableWidget.DoubleClicked |
            QTableWidget.EditKeyPressed |
            QTableWidget.AnyKeyPressed
        )

        # --- automatic resizing ---
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)

        self.table.verticalHeader().setVisible(False)
        self.table.setSizeAdjustPolicy(
            QTableWidget.AdjustToContents
        )

        self._populateTable(metadata,metadataAttributes )

        # --- buttons ---
        addButton = QPushButton("Add")
        removeButton = QPushButton("Remove")

        addButton.clicked.connect(self.addRow)
        removeButton.clicked.connect(self.removeSelectedRow)

        buttonRow = QHBoxLayout()
        buttonRow.addWidget(addButton)
        buttonRow.addWidget(removeButton)
        buttonRow.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.table)
        layout.addLayout(buttonRow)

    # ----------------------------------------------------
    # Population
    # ----------------------------------------------------

    def _populateTable(self, metadata: dict, metadataAttributes:dict):
        """
        Expected metadata format:
         2 dicts:
            metadata = {'key':'value'}
            metadataAttributes = {'key', {'display': True | False, 'posx' = x, 'posy' = y} }
        """
        #print(f"{metadata=}\n{metadataAttributes}")
        for key, entry in metadata.items():
            value = ""
            display = True

            value = str(entry)
            if key in metadataAttributes:
                display = metadataAttributes[key].get("display", True)
                
            self._addRow(key, value, display)

    def _addRow(self, key="", value="", display=True):
        row = self.table.rowCount()
        self.table.insertRow(row)

        keyItem = QTableWidgetItem(str(key))
        #Don't allow the editing of the key "name"
        if key == "name":
            keyItem.setFlags( Qt.ItemIsEnabled )  # Qt.ItemIsSelectable |  NOT editable

        self.table.setItem(row, 0, keyItem)
        self.table.setItem(row, 1, QTableWidgetItem(str(value)))

        displayItem = QTableWidgetItem()
        displayItem.setFlags(
            Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable
        )
        displayItem.setCheckState(Qt.Checked if display else Qt.Unchecked)

        self.table.setItem(row, 2, displayItem)
        self.table.setCurrentCell(row, 1 if key == "name" else 0)

    def _isProtectedRow(self, row: int) -> bool:
        item = self.table.item(row, 0)
        return item and item.text() == "name"

    # ----------------------------------------------------
    # Slots
    # ----------------------------------------------------

    def addRow(self):
        self._addRow()

    def removeSelectedRow(self):
        row = self.table.currentRow()
        if self._isProtectedRow(row):
            return  # silently ignore (or show a warning)
        if row >= 0:
            self.table.removeRow(row)

        self.table.removeRow(row)
    # ----------------------------------------------------
    # Keyboard handling
    # ----------------------------------------------------

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Insert:
            self.addRow()
            event.accept()
            return

        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            if row >= 0 and not self._isProtectedRow(row):
                self.removeSelectedRow()
            event.accept()
            return

        super().keyPressEvent(event)

    # ----------------------------------------------------
    # Result extraction
    # ----------------------------------------------------

    def setMetadataAndAttributes(self,visItem):
        """ updates itemMetadata and itemMetadataAttributes
            (Must work for nodes and edges)
        """
        visItem.metadata.clear()
        visItem.metadataAttributes.clear()

        for row in range(self.table.rowCount()):
            keyItem = self.table.item(row, 0)
            valItem = self.table.item(row, 1)
            dispItem = self.table.item(row, 2)

            if not keyItem:
                continue

            key = keyItem.text().strip()
            if not key:
                continue

            value = valItem.text() if valItem else ""
            display = dispItem.checkState() == Qt.Checked if dispItem else True
            visItem.metadata[key] = value
            visItem.metadataAttributes[key] = {'display':display}
        if 'description' in visItem.metadata and visItem.metadata['description'] != visItem.blobDescription.toPlainText():
            visItem.blobDescription.setPlainText(visItem.metadata['description'])
            
