""" 
    Node code - simple nodes and blob (set) nodes
"""

from  HGConstants import *
from GraphicsSupport import *

#For file handling and clipboard
import xml.etree.ElementTree as ET
from xml.dom import minidom

from PySide6.QtWidgets import ( QApplication, QWidget, QMainWindow, QDialog,
            QGraphicsScene, QGraphicsView, QListWidget, QListWidgetItem,
            QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
            QLineEdit, QInputDialog, QMenu, QFileDialog, QStyleOptionGraphicsItem, QGraphicsObject,
            QSlider, QLabel, QStatusBar,
            QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton)

from PySide6 import (QtCore, QtWidgets, QtGui )
from PySide6.QtGui import (QStandardItemModel, QStandardItem, QPolygonF,QPainter,
            QTransform, QFont, QFontMetrics, QAction, QCursor, QPen,QBrush,
            QPainterPath, QPainterPathStroker, QCursor,
            QGuiApplication, QImage, QPixmap)
from PySide6.QtCore import (QLineF, QPointF,QPoint, QRect, QRectF, 
            QSize, QSizeF, Qt, Signal, Slot, QTimer, QObject,
            QMimeData, QBuffer, QByteArray, QIODevice)



class VisNodeItem(QGraphicsObject):
    """ Create a new node - both Graph Model and Visual ("graphics") 
    This connects visual Rect to model and list 
    
    """
    #Create the signal for editing
    requestEdit = Signal(object)  

    def __init__(self,posn,model,listWidget, parent=None, nameP ="", id=None,
                    metadata={}, metadataAttributes={}):
        #print(f"In VisNodeItem {posn =}")
        super().__init__(parent)
        self.suppressItemChange = True  # suppress itemChange (was protected, but scene needs to set it)
        
        self.model = model
        self.listWidget = listWidget
        #Store the edges that start/ end at this node
        self.startsEdges = []  
        self.endsEdges = []  

        #WHERE it must appear
        self.setPos(posn)
        
        #Create an abstract node, and keep the index as well
        self.node,self.nodeNum = self.model.addGMNode(posn,nameP=nameP,id=id)

        #Additional graph-relevant node data
        self.metadata = self.model.Gr.nodeD[self.nodeNum].metadata
        #How to display each metadata item
        #"deep copy" the dict
        for k,v in metadata.items():
            self.metadata[k] = v
        #initialise metadataAttributes if not passed in:
        if len(metadataAttributes) > 0:
            self.metadataAttributes = metadataAttributes
        else:
            self.metadataAttributes = {'name':{'display':DISPLAY_NAME_BY_DEFAULT}}

        #add to the text list
        lWitem = QListWidgetItem(self.model.Gr.nodeD[self.nodeNum].metadata['name'])
        lWitem.setData(KEY_INDEX,self.nodeNum)
        lWitem.setData(KEY_ROLE,ROLE_NODE)
        self.listWidget.addItem(lWitem)

        # Create a text item to hold & show the ID number
        # Not needed with KEY_INDEX role
        #self.textItem = QGraphicsTextItem(f"{self.nodeNum}", self)
        #textRect = self.textItem.boundingRect()
        #self.textItem.setPos(-textRect.width()/2, -textRect.height()/2)
        #self.textItem.setFlag(QGraphicsItem.ItemIsSelectable, False)
        #self.textItem.setFlag(QGraphicsItem.ItemIsFocusable, False)

        self.dispText = self.model.Gr.nodeD[int(self.nodeNum)].metadata['name']

        #a place to display metadata
        self.metaDisplay = TransparentTextItem("xx", parent=self)
        self.metaDisplay.setPos(QPointF(NODESIZE/2,-NODESIZE*2))  #NODESIZE/2,0))
        self.metaDisplay.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.metaDisplay.setFlag(QGraphicsItem.ItemIsFocusable, False)
        #populate it
        self.setMetadataDisplay()

        #Non-display version, for referencing to model and listView
        self.setData(KEY_INDEX, self.nodeNum)
        self.setData(KEY_ROLE, ROLE_NODE)
        
        #The shape of the node- rectangle
        #1st 2 parms are origin, 2nd 2 are width & height
        #Rect shape
        #self.nodeShape = QGraphicsRectItem(-NODESIZE/2,-NODESIZE/2,NODESIZE,NODESIZE,self)
        #Circle Shape
        self.nodeShape = QGraphicsEllipseItem(-NODESIZE/2,-NODESIZE/2,NODESIZE,NODESIZE,self)
        self.nodeShape.my_parent_item = self #coPilot's suggestion to stop GC issues. Force a strong reference
        self.nodeShape.setPen(QPen(Qt.NoPen))
        #TODO: Set selectable False - see if that processes clicks better?
        self.nodeShape.setFlag(QGraphicsItem.ItemIsSelectable, False)

        #Make nodes appear in front of edges for painting & selection
        self.setZValue(1000)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlags(self.GraphicsItemFlag.ItemSendsScenePositionChanges)

        #self.setAcceptHoverEvents(True)
        self.hovered = False

        self.suppressItemChange = False  # enable itemChange normally

    def __repr__(self):
        return f"\n** VisNodeItem {super().__repr__()}\nIndex:{self.data(KEY_INDEX) }  Role:{self.data(KEY_ROLE) =} @ {self.pos() =}\n\
                {self.startsEdges = },\n{self.endsEdges = }\n**" #\n {self.nodeShape =})"
    __str__ = __repr__

    def toXML(self,Xparent):
        """ add an Element Tree node to the XML parent node with the Edge Data """
        xmlNode = ET.Element("node", id=str(self.nodeNum))

        data = ET.SubElement(xmlNode, "data", key="data_node")
        shape = ET.SubElement(data, "y:" + "ShapeNode")
        ET.SubElement(shape, "y:Geometry", {'x':str(self.pos().x()), 'y':str(self.pos().y())})
        nodeLabel = ET.SubElement(shape, "y:NodeLabel")
        nodeLabel.text = self.metadata['name']
        for atK,atV in self.metadataAttributes['name'].items():
            metaAtt = ET.SubElement(nodeLabel, "h:metadataAttribute", {"key":atK,"value":str(atV)})
        
        #add metadata other than name
        if len(self.metadata) >= 2:
            for k, v in self.metadata.items():
                if k != "name":
                    metaEl  = ET.SubElement(xmlNode, "h:metadata", {"key":k,"value":str(v)})
                    for atK,atV in self.metadataAttributes[k].items():
                        metaAtt = ET.SubElement(metaEl, "h:metadataAttribute", {"key":atK,"value":str(atV)})

        return xmlNode

    def setMetadataDisplay(self):
        """setup metadata to display
            This should be the same code as in VisEdgeItem
        """
        #TODO: This needs to be called by itemChange somehow.
        metaStr = ''
        for k,v in self.metadata.items():
            if k != 'name':
                if self.metadataAttributes[k]['display']:
                    metaStr += "\n"+k +":"+v
        self.metaDisplay.setPlainText(metaStr)

    def boundingRect(self):

        #Calc text box. 
        #Hardcoding on top for now
        #self.dispText = self.model.Gr.nodeD[int(self.nodeNum)].metadata['name']
        #self.dispText += f"\n{int(self.pos().x())},{int(self.pos().y())}"
        tFont = QFont()
        metrics = QFontMetrics(tFont)
        textRect = metrics.boundingRect(self.dispText)
        #centre it
        textRect.adjust(-textRect.width()/2,-textRect.height()/2,-textRect.width()/2,-textRect.height()/2)

        nodeRect = QRectF(-NODESIZE/2,-NODESIZE/2,NODESIZE,NODESIZE)

        penWidth = 2
        bRect = nodeRect.united(textRect).adjusted(-penWidth,-penWidth,penWidth,penWidth)
        return bRect

        #TODO: This allows the attribs to be selected, but makes for an overly big bounding rect. 
        # shape() might be a better solution.
        #adjust = 2 # self.pen.width() / 2
        #return self.childrenBoundingRect().adjusted(-adjust, -adjust, adjust, adjust)



    def paint(self, painter, option, widget=None):
        """ Draw a VisNode item"""
        #Debug: Show the centre of the node
        #painter.drawLine(-10,-10,10,10)
        #painter.drawLine(-10,10,10,-10)
        #painter.drawRect(self.boundingRect())
        
        painter.setClipping(True)

        if self.isSelected():
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine))
        else:
            painter.setPen(Qt.black)

        if self.hovered:
            brush = QBrush(Qt.lightGray)  # Light gray fill
        else:
            brush = QBrush(Qt.white)      # Normal fill
        #brush = QBrush(Qt.NoBrush) #white)
        painter.setBrush(brush)

        #TODO: Use the shape used in the constructor - will need a flag
        #painter.drawRect(self.nodeShape.rect())
        painter.drawEllipse(self.nodeShape.rect())

        #Draw the text if set to display
        if self.metadataAttributes['name']['display']:
            # Pos on top (this can be generalised to left, bottom, right, etc)
            r = QRectF(0,-NODESIZE,0,0) 
            #update height & width
            r = painter.drawText(r,Qt.AlignCenter,self.dispText)
            painter.drawText(r, Qt.AlignCenter, self.dispText)

        #Draw displayed metadata - automagic?

    def mouseDoubleClickEvent(self, mouseEvent):
        self.requestEdit.emit(self)
        mouseEvent.accept()

    def itemChange(self,change,value):
        """ in particular, deal with VisNode moving --> update VisEdges"""
        if not self.suppressItemChange:
            #TODO: figure out the differen `change` options
            #Name change
            self.dispText = self.model.Gr.nodeD[int(self.nodeNum)].metadata['name']
            
            #Position change
            if change == QGraphicsItem.ItemPositionHasChanged:
                for sEdge in self.startsEdges:
                    sEdge.updateLine(self)
                for eEdge in self.endsEdges:
                    eEdge.updateLine(self)

        #note the **return**
        return super().itemChange(change,value)

    #TODO: hoverEvents are not sent when there is an explicit mouseEVent handler. Handle in scene and delete here
    def xxhoverEnterEvent(self, event=None):
        self.hovered = True
        self.update()  # trigger repaint
        super().hoverEnterEvent(event)

    def xxhoverLeaveEvent(self, event):
        self.hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, mouseEvent):
        if (mouseEvent.button() == Qt.MouseButton.LeftButton):
            #TODO: check for <shift> & <ctrl> click to add, otherwise clear.
            #NOTE: Qt clears the selection elsewhere on mouseRelease 
            modifiers = mouseEvent.modifiers()
            if not (modifiers & Qt.ShiftModifier or modifiers & Qt.ControlModifier) \
                and not self.isSelected():
                self.scene().clearSelection()
            self.setSelected(True)
            #Highlight the list item as well
            lWItem = self.listWidget.findItemByIdx(self.data(KEY_INDEX))
            self.listWidget.setCurrentItem(lWItem)

        super().mousePressEvent(mouseEvent)
