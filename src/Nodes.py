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
            QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem, QAbstractGraphicsShapeItem,
            QLineEdit, QInputDialog, QMenu, QFileDialog, QStyleOptionGraphicsItem, QGraphicsObject,
            QSlider, QLabel, QStatusBar,
            QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton)

from PySide6 import (QtCore, QtWidgets, QtGui )
from PySide6.QtGui import (QStandardItemModel, QStandardItem, QPolygonF,QPainter,
            QTransform, QFont, QFontMetrics, QAction, QCursor, QPen,QBrush,
            QPainterPath, QPainterPathStroker, QCursor,QColor,
            QGuiApplication, QImage, QPixmap)
from PySide6.QtCore import (QLineF, QPointF,QPoint, QRect, QRectF, 
            QSize, QSizeF, Qt, Signal, Slot, QTimer, QObject,
            QMimeData, QBuffer, QByteArray, QIODevice)


#A helper blob drawing class
# Gemini code.
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem
from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QPainterPath, QPainterPathStroker, QPen, QBrush, QColor

class QRoundedRectItem(QGraphicsObject):
    # Custom signal emitted when the border is clicked
    clicked = Signal()

    def __init__(self, rect: QRectF, xRadius: float=0, yRadius: float=0, mode=Qt.AbsoluteSize,parent=None):
        super().__init__(parent)
        self._rect = rect
        self._xRadius = xRadius
        self._yRadius = yRadius
        self._mode = mode
        
        # Style configuration
        self._penWidth = 1.0
        self._baseColor = QColor("black")
        self._hoverColor = QColor("red")
        self._pen = QPen(Qt.NoPen)  #QPen(self._baseColor, self._penWidth)
        
        # Interaction settings
        self.setAcceptHoverEvents(True)
        #self.setFlags(QGraphicsObject.ItemIsSelectable | QGraphicsObject.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        #Let the parent handle the buttons
        self.setAcceptedMouseButtons(Qt.NoButton)
        
        self._isHovered = False

    def boundingRect(self) -> QRectF:
        # Increase the bounding box slightly to account for the pen width
        margin = self._pen.widthF() / 2

        return self._rect.adjusted(-margin, -margin, margin, margin)

    def shape(self) -> QPainterPath:
        # Returns only the hollow border path
        basePath = QPainterPath()
        basePath.addRoundedRect(self._rect, self._xRadius, self._yRadius, self._mode)
        stroker = QPainterPathStroker()
        stroker.setWidth(HITSIZE) # Hit-area thickness
        return stroker.createStroke(basePath)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        #painter.setRenderHint(QPainter.Antialiasing)
        
        # Determine styling by looking at the PARENT'S state
        parent = self.parentItem()
        if parent and parent.isSelected():
            painter.setPen(QPen(Qt.blue, 1.5, Qt.DashLine))
        elif parent and getattr(parent, '_isHovered', False):
            painter.setPen(QPen(QColor("red"), 1.5))
        else:
            painter.setPen(QPen(Qt.black, 1.0))
            
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self._rect, self._xRadius, self._yRadius, self._mode)

    def setPen(self,pen):
        self._pen = pen

    def hoverEnterEvent(self, event):
        self._isHovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._isHovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        # Only emits if the user clicks the actual 'shape' (the outline)
        #print(f"RR mouse pressed {event=}")
        #self.clicked.emit()
        super().mousePressEvent(event)



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
        self.setFlag(self.GraphicsItemFlag.ItemSendsScenePositionChanges)

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

class VisBlobItem(VisNodeItem):
    """Generalise point-like nodes to sets. Blame Harel for the name"""

    def __init__(self,posn, model,listWidget, parent=None, nameP ="", id=None,
                    metadata={}, metadataAttributes={},
                    height=NODESIZE, width=NODESIZE,xRadius=0, yRadius=0, radMode = Qt.AbsoluteSize, parents=[],children=[]):
        """  posn is the topleft, size is width and height, Radii are corner curves
           NB: `parent` is the (visual) Qt parent, `parents` is the (abstract) core Graph blob parent """
        
        super().__init__(posn, model,listWidget, parent=parent, nameP ="", id=None,
                    metadata={}, metadataAttributes={})

        self.suppressItemChange = True

        #Fix Blob-Node differences
        #add to the text list
        lWitem = self.listWidget.findItemByIdx(self.nodeNum)
        #This is not setting the role - it is still 1001 - NODE
        #TODO: Revisit the value the model adds
        self.node.setData(KEY_ROLE,ROLE_BLOB)
        lWitem.setData(KEY_ROLE,ROLE_BLOB)

        self.setData(KEY_ROLE, ROLE_BLOB)
        #self.scene().removeItem(self.nodeShape)

        self.parents = parents
        self.children = children

        #Node constructor doesn't take parents & children, so add now

        # make the rect
        #self.nodeShape = QGraphicsEllipseItem(-NODESIZE/2,-NODESIZE/2,NODESIZE,NODESIZE,self)

        #    def __init__(self, rect: QRectF, xRadius: float=0, yRadius: float=0, mode=Qt.AbsoluteSize,parent=None):

        self._rect = QRectF(0,0,width,height)
        self._width = width
        self._height = height
        self._xRadius = xRadius
        self._yRadius = yRadius
        self._radMode = radMode
        self.nodeShape = QRoundedRectItem(self._rect,parent=self,
                                xRadius = self._xRadius, yRadius = self._yRadius, mode = self._radMode)
        self.nodeShape.my_parent_item = self #coPilot's suggestion to stop GC issues. Force a strong reference
        self.nodeShape.setPen(QPen(Qt.NoPen))
        self.nodeShape.setFlag(QGraphicsItem.ItemIsSelectable, False)

        #Use the edge `isOnlySelected` logic as far as possible for handle creation
        self.isOnlySelected = False

        self.suppressItemChange = False

    def __repr__(self):
        r = f"\noo VisBLOBItem\nIndex:{self.data(KEY_INDEX) }  Role:{self.data(KEY_ROLE) =} @ {self.pos() =}\n"+\
                f"{self.startsEdges = },\n{self.endsEdges = }\n00" #\n {self.nodeShape =})"
        r += f"\n{self.parents=}\n{self.children}"
        return r
    __str__ = __repr__

    def boundingRect(self):
        #TODO: Add in the displayed text
        # Must cover both the rectangle and the text area
        return self._rect.adjusted(-5, -20, 5, 5)
    
    def shape(self):
        # Combined shape: Hollow Border + Solid Text Area
        #path = self.nodeShape.shape() 
        path = self.mapFromItem(self.nodeShape, self.nodeShape.shape())
        if self.metadataAttributes.get('name', {}).get('display', True):
            #TODO: When text is rich text, this will need updating
            tFont = QFont()
            fm = QFontMetrics(tFont)
            # Use same rect/logic as paint() for text hit-area
            textRect = fm.boundingRect(self._rect.toRect(), Qt.AlignCenter, self.dispText)
            path.addRect(QRectF(textRect))
            
        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        if self.isSelected():
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine))
        else:
            painter.setPen(Qt.black)

        #self.nodeShape is painted by Qt

        #Draw the text if set to display
        if self.metadataAttributes['name']['display']:
            # Pos on top (this can be generalised to left, bottom, right, etc)
            #r = QRectF(0,-NODESIZE,0,0) 
            #update height & width
            #r = painter.drawText(r,Qt.AlignCenter,self.dispText)
            #painter.drawText(r, Qt.AlignCenter, self.dispText)
            painter.drawText(self._rect, Qt.AlignLeft | Qt.AlignTop, self.dispText)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedChange:
            if self.isOnlySelected:
                self._createHandles()
        
        # Detect when the selection state changes
        if change == QGraphicsItem.ItemSelectedChange:
            # value is the new selection state (True/False)
            # Force the child border to repaint so it picks up the new state
            if hasattr(self, 'nodeShape'):
                self.nodeShape.update()
        return super().itemChange(change, value)

    def _createHandles(self):
        """ Handles for resizing"""

        TLx = self.pos().x()
        TLy = self.pos().y()
        BRx = self._width
        BRy = self._height
        
        #A list of handles, clockwise, 0 = TL, 1 = TR, 2 = BR, 3 = BL
        self._Handles = []
        self._Handles.append(HandleItem(QPointF(TLx,TLy),color=Qt.green,parent=self))
        self._Handles.append(HandleItem(QPointF(BRx,TLy),color=Qt.green,parent=self))
        self._Handles.append(HandleItem(QPointF(BRx,BRy),color=Qt.green,parent=self))
        self._Handles.append(HandleItem(QPointF(TLx,BRy),color=Qt.green,parent=self))
        
        for h in self._Handles:
            h.setMoveCallback(self._updateFromHandles)

    def _deleteHandles(self):
        """ Delete handles when deselected"""
        self.suppressItemChange = True
        # Remove existing handles
        for h in self._Handles:
            self.scene().removeItem(h)
        self._Handles.clear()
        self.suppressItemChange = False

    def _updateFromHandles(self,pos):
        if self.suppressItemChange == True:
            return
        





    def mousePressEvent(self, event):
        #Call VisNode's mouse handler
        super().mousePressEvent(event)