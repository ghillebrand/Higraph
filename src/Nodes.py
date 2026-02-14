""" 
    Node code - simple nodes and blob (set) nodes
"""

from  HGConstants import *
from GraphicsSupport import *

#For file handling and clipboard
import xml.etree.ElementTree as ET
from xml.dom import minidom
import math

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
 #JH   clicked = Signal()

    def __init__(self, rect: QRectF, xRadius: float=BLOB_CORNER_RADIUS, yRadius: float=BLOB_CORNER_RADIUS, 
                    mode=Qt.AbsoluteSize,parent=None):
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
        #self.setAcceptHoverEvents(True)
        #self.setFlags(QGraphicsObject.ItemIsSelectable | QGraphicsObject.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        #Let the parent handle the buttons
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)
        #self.setVisible(False) #JH needed if local paint is removed
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
    #jh commented out entire function to romove local paint   
        # Determine styling by looking at the PARENT'S state
        parent = self.parentItem()
        if parent and parent.isSelected():
            painter.setPen(QPen(Qt.blue, 1.0, Qt.DashLine))
        else:
            painter.setPen(QPen(Qt.black, 1.0))
            
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self._rect, self._xRadius, self._yRadius, self._mode)

    def setPen(self,pen):
        self._pen = pen

    def setRoundedRect(self, rect: QRectF):
        """ Allows the changing of Rounded Rect params in a Qt-like way"""
        #TODO: Extend to **kwargs processing to allow changing of all params
        self._rect = rect

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

        #TODO: Change this to TransparentTextItem
        self.dispText = self.model.Gr.nodeD[int(self.nodeNum)].metadata['name']

        #a place to display metadata
        self.metaDisplay = TransparentTextItem("", parent=self)
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
        #JH remove self.nodeShape.my_parent_item = self #coPilot's suggestion to stop GC issues. Force a strong reference
        #self.nodeShape.setPen(QPen(Qt.NoPen))
        #Filled or clear - used for debugging
        brush = QBrush(Qt.white)      # Normal fill
        #brush = QBrush(Qt.NoBrush)   # clear)
        self.nodeShape.setBrush(brush)

        #TODO: Set selectable False - see if that processes clicks better?
        self.nodeShape.setFlag(QGraphicsItem.ItemIsSelectable, False)

        #Ports where edges will connect
        self._nextPort = 0 #Counter for port index
        self._Ports = []

        #Make nodes appear in front of edges for painting & selection
        self.setZValue(1000)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsScenePositionChanges)
        
        #TODO: hoverEvents are not sent when there is an explicit mouseEVent handler. Handle in scene and delete here
        #self.setAcceptHoverEvents(True)
        #self.hovered = False

        self.suppressItemChange = False  # enable itemChange normally

    def __repr__(self):
        return f"\n*>* VisNodeItem {super().__repr__()}\nIndex:{self.data(KEY_INDEX) }  Role:{self.data(KEY_ROLE) =} @ {self.pos() =}, {self._Ports=}\n\
                {self.startsEdges = },\n{self.endsEdges = }\n*<*" #\n {self.nodeShape =})"
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
            self.nodeShape.setPen(QPen(Qt.blue,1,Qt.DashLine))
        else:
            painter.setPen(Qt.black)
            self.nodeShape.setPen(QPen(Qt.black))


        brush = QBrush(Qt.white)      # Normal fill
        #brush = QBrush(Qt.NoBrush) #white)
        painter.setBrush(brush)

        #TODO: Use the shape used in the constructor - will need a flag
        #painter.drawRect(self.nodeShape.rect())
        #painter.drawEllipse(self.nodeShape.rect())

        #Draw the text if set to display
        if self.metadataAttributes['name']['display']:
            # Pos on top (this can be generalised to left, bottom, right, etc)
            r = QRectF(0,-NODESIZE,0,0) 
            #update height & width
            r = painter.drawText(r,Qt.AlignCenter,self.dispText)
            painter.drawText(r, Qt.AlignCenter, self.dispText)

        #Draw displayed metadata - automagically from the TransparentTextItem painter

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
            if change in [QGraphicsItem.ItemPositionHasChanged, QGraphicsItem.ItemChildAddedChange]:
                for sEdge in self.startsEdges:
                    sEdge.updateLine(self)
                for eEdge in self.endsEdges:
                    eEdge.updateLine(self)

        #note the **return**
        return super().itemChange(change,value)

    def createPort(self,screenPos)->int:
        """ Create a port at `pos` for an edge to connect on, return the int index for reference"""
        #gemini code
        #This is harcoded to a circle of radius NODESIZE/2  Other shapes/ options later
        #Find the parametric position of the point on the nodeshape
        #Calculates the clockwise 'distance' around the perimeter.
        # 0.0 = Top, 0.25 = Right, 0.5 = Bottom, 0.75 = Left.

        center = self.pos()

        #Calculate delta from center
        dy = screenPos.y() - center.y()
        dx = screenPos.x() - center.x()
        angle = math.atan2(dy, dx)
        #Shift angle so that -PI/2 (Top) becomes 0, normalize to a 0.0 -> 1.0 range
        fraction = (angle + math.pi / 2) / (2 * math.pi)
        #Normalize to [0, 1) range to handle negative results from the shift (Python % 1 is magic!)
        t =  fraction % 1.0

        #Create the port, add to the node's list
        # Calculate the exact coords from the angle ("snap")
        portPos = QPointF(NODESIZE/2 *math.cos(angle),NODESIZE/2 *math.sin(angle)   )
        #print(f"{t=},{portPos=}")
        #Parent to nodeShape for better geom flexibility
        #TODO: Does dummyNode need to be a QGraphicsItem? can it not just be a QPointF????
        p = dummyNodeItem(portPos, parent=self.nodeShape)
        #Store the position and index as the ID of the port
        p.t = t 
        p.index = self._nextPort
        print(f"Port created N={self.nodeNum}: P={p.index} at {p.t}")
        self._Ports.append(p)
        print(f"{self._Ports=}")
  
        self._nextPort += 1

        return p.index

    def findPort(self,screenPos)->int:
        """ checks for a port at screenPos using HITSIZE, returns index if found, -1 if not"""
        found = -1
        minD = math.inf
        for existingPort in self._Ports:
            d = QLineF(existingPort.scenePos(), screenPos).length()
            print(f"{self.nodeNum}:{existingPort.index=} findPort: {d}")
            if d <= HITSIZE:
                if d < minD:
                    found = existingPort.index
                    minD = d
        print(f"{found=}")
        return found

    """def mousePressEvent(self, mouseEvent):
        if (mouseEvent.button() == Qt.MouseButton.LeftButton):
            #TODO: check for <shift> & <ctrl> click to add, otherwise clear.
            #NOTE: Qt clears the selection elsewhere on mouseRelease 
            modifiers = mouseEvent.modifiers()
            if not (modifiers & Qt.ShiftModifier or modifiers & Qt.ControlModifier)\
                    and self.scene().mouseMode!=self.scene().DRAGGING:
          #      and not self.isSelected():
                self.scene().clearSelection()
            self.setSelected(True)
            #Highlight the list item as well
            print("JH node mousepress",len(self.scene().selectedItems()), self.scene().mouseMode)
            if len(self.scene().selectedItems())==0:
                lWItem = self.listWidget.findItemByIdx(self.data(KEY_INDEX))
                self.listWidget.setCurrentItem(lWItem)

        super().mousePressEvent(mouseEvent)"""

class VisBlobItem(VisNodeItem):
    """Generalise point-like nodes to sets. Blame Harel for the name"""
    #Constants for the corners of a (rectangular) blob
    TL = 0
    TR = 1
    BR = 2
    BL = 3

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
        #Remove the nodeShape set in the parent
        self.nodeShape.setParentItem(None)
        del self.nodeShape

        self.parents = parents
        self.children = children

        #Node constructor doesn't take parents & children, so add now

        # make the rect
        self._rect = QRectF(0,0,width,height)
        self._width = width
        self._height = height
        self._xRadius = xRadius
        self._yRadius = yRadius
        self._radMode = radMode
        self.nodeShape = QRoundedRectItem(self._rect,parent=self,
                                xRadius = self._xRadius, yRadius = self._yRadius, mode = self._radMode)
        # JH remove self.nodeShape.my_parent_item = self #coPilot's suggestion to stop GC issues. Force a strong reference
        self.nodeShape.setPen(QPen(Qt.NoPen))
        self.nodeShape.setFlag(QGraphicsItem.ItemIsSelectable, False)

        #Placeholder for drag handles
        self._Handles = []



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
        return self.nodeShape._rect.adjusted(-5, -20, 5, 5)
    
    def shape(self):
        # Combined shape: Hollow Border + Solid Text Area
        #print("Blob shape udpate")
        #path = self.nodeShape.shape() 
        path = self.mapFromItem(self.nodeShape, self.nodeShape.shape())
        if self.metadataAttributes.get('name', {}).get('display', True):
            #TODO: When text is rich text, this will need updating
            tFont = QFont()
            fm = QFontMetrics(tFont)
            # Use same rect/logic as paint() for text hit-area
            textRect = fm.boundingRect(self._rect.toRect(), Qt.AlignCenter, self.dispText)
            path.addRect(QRectF(textRect))

        #outlinePath = QPainterPathStroker()
        #outlinePath.setWidth(HITSIZE*2)
        #return outlinePath.createStroke(path)            
        return path

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        if self.isSelected():
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine))
        else:
            painter.setPen(Qt.black)

        #self.nodeShape is painted by Qt, using parent's pen???

        #JH put this (below) in if rectangle paint is removed
        #painter.drawRoundedRect(self.nodeShape._rect, self.nodeShape._xRadius, self.nodeShape._yRadius, self.nodeShape._mode)

        #Draw the text if set to display
        if self.metadataAttributes['name']['display']:
            # Pos on top (this can be generalised to left, bottom, right, etc)
            #r = QRectF(0,-NODESIZE,0,0) 
            #update height & width
            #r = painter.drawText(r,Qt.AlignCenter,self.dispText)
            #painter.drawText(r, Qt.AlignCenter, self.dispText)
            #TODO: This must become a transparentTextItem, to be selectable, and to put the bounding rect in the right place
            painter.drawText(self._rect, Qt.AlignLeft | Qt.AlignTop, self.dispText)

    def itemChange(self, change, value):
        if self.suppressItemChange:
            return super().itemChange(change, value)
        #print(f"{change=} {value=}")
        #Moved
        if change in [QGraphicsItem.ItemPositionHasChanged, QGraphicsItem.ItemChildAddedChange]:
            #print("blob move")
            pass

        return super().itemChange(change, value)

    """def setSelected(self,state:bool):
        if len(self.scene().selectedItems())<=1:
            if state:
                #print(f"Blob setSel createH")
                self._createHandles()
                self.scene().thisHandleObjectSelected=self
            else:
                #print("blob setSel calling _deleteHandles")
                self.scene().onlySelected = None
                self.scene().thisHandleObjectSelected = None
                self.isOnlySelected = False
                self._deleteHandles()
        super().setSelected(state)"""

    def _createHandles(self):
        """ Handles for resizing"""
        self.suppressItemChange = True
        #Clear existing handles
        for h in self._Handles:
            self.scene().removeItem(h)
            del h
        self._Handles.clear()

        TLx = self.pos().x()
        TLy = self.pos().y()
        BRx = self._width
        BRy = self._height
        
        #A list of handles, clockwise, 0 = TL, 1 = TR, 2 = BR, 3 = BL
        self._Handles = []
        self._Handles.append(HandleItem(QPointF(0,0),color=Qt.green,parent=self))
        self._Handles.append(HandleItem(QPointF(BRx,0),color=Qt.red,parent=self))
        self._Handles.append(HandleItem(QPointF(BRx,BRy),color=Qt.blue,parent=self))
        self._Handles.append(HandleItem(QPointF(0,BRy),color=Qt.cyan,parent=self))
        #for h in self._Handles: JH
        #    h.setMoveCallback(self._updateFromHandles)
        self.suppressItemChange = False

    def _deleteHandles(self):
        """ Delete handles when deselected"""
        self.suppressItemChange = True
        # Remove existing handles
        for h in self._Handles:
            h.setParentItem(None)
            self.scene().removeItem(h)
            del h
        self._Handles.clear()
        self.suppressItemChange = False

    def _updateFromHandles(self,pos):
        
        if self.suppressItemChange == True:
            return

        self.suppressItemChange = True

        self.prepareGeometryChange()

        BlobPos = self.pos()
        TLx = self.pos().x()
        TLy = self.pos().y()
        BRx = self._width
        BRy = self._height

        #print(f"start update {TLx},{TLy},{BRx},{BRy}")
        rTLx,rTLy,rBRx,rBRy = 0,0,BRx,BRy

        #Translate to Blob coords
        #TODO: use proper Qt translate?
        relPos = pos - BlobPos

        lastHandle = -1
        dist = HITSIZE * 10 #Effectively, infinity!
        for i,h in enumerate(self._Handles):
           # hDist = math.hypot(h.pos().x() - relPos.x(), h.pos().y() - relPos.y()) JH
            hDist = math.hypot(h.pos().x() - pos.x(), h.pos().y() - pos.y())
            if hDist < dist:
                dist = hDist
                lastHandle = i

        #Note - all these positions are RELATIVE to pos()
        match lastHandle:
            case 0: #TL
                if BRx - relPos.x() >= HITSIZE*2: 
                    rTLx = relPos.x()
                    TLx += rTLx
                    BRx -= rTLx                   
                if BRy - relPos.y() >= HITSIZE*2:
                    rTLy = relPos.y()
                    TLy += rTLy
                    BRy -= rTLy
            case 1: #TR BRx is width
                if relPos.x() >= HITSIZE*2:
                    rBRx = relPos.x()
                    BRx = rBRx
                if BRy - relPos.y() >= HITSIZE*2:
                    rTLy = relPos.y()               
                    TLy += rTLy
                    BRy -= rTLy
            case 2: #BR
                if relPos.x() >= HITSIZE*2:
                    rBRx = relPos.x() 
                    BRx = rBRx
                if relPos.y() >= HITSIZE*2:
                    rBRy = relPos.y()                
                    BRy = rBRy
            case 3: #BL
                if BRx - relPos.x() >= HITSIZE*2:
                    rTLx = relPos.x() 
                    TLx += rTLx
                    BRx -= rTLx
                if relPos.y() >= HITSIZE*2:
                    rBRy = relPos.y()               
                    BRy = rBRy
                

        """#Check for "too thin" before updating, using HITSIZE as measure
        if BRx < HITSIZE*2:
            self.suppressItemChange = False
            return
        if BRy < HITSIZE*2:
            self.suppressItemChange = False
            return"""
        self._Handles[VisBlobItem.TL].setPos(QPointF(rTLx,rTLy))
        self._Handles[VisBlobItem.TR].setPos(QPointF(rBRx,rTLy))
        self._Handles[VisBlobItem.BR].setPos(rBRx,rBRy)
        self._Handles[VisBlobItem.BL].setPos(rTLx,rBRy)

        #Now set the blob pos & w/h from the blobs

        #orders are right, transform back blob coords
        self._height = BRy
        self._width = BRx 

        #Figure out the geometry for these lines
        self.setPos(TLx,TLy)
        self.nodeShape.setRoundedRect(QRectF(0,0,self._width,self._height))

        self.suppressItemChange = False
        
        #TODO this SHOULD be propagated via itemChange(), but that only happens at start, not end of handle move use itemChanged() (past-tense)?
        for sEdge in self.startsEdges:
            sEdge.updateLine(self)
        for eEdge in self.endsEdges:
            eEdge.updateLine(self)


    def mousePressEvent(self, event):
        #Call VisNode's mouse handler
        super().mousePressEvent(event)