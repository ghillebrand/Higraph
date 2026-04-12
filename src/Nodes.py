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
            QGraphicsScene, QGraphicsView, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
            QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem, QAbstractGraphicsShapeItem,
            QLineEdit, QInputDialog, QMenu, QFileDialog, QStyleOptionGraphicsItem, QGraphicsObject,
            QSlider, QLabel, QStatusBar, QColorDialog, QFontDialog,
            QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton)

from PySide6 import (QtCore, QtWidgets, QtGui )
from PySide6.QtGui import (QStandardItemModel, QStandardItem, QPolygonF,QPainter,
            QTransform, QFont, QFontMetrics, QAction, QCursor, QPen,QBrush,
            QPainterPath, QPainterPathStroker, QCursor,QColor, QUndoStack, QUndoCommand,
            QGuiApplication, QImage, QPixmap, QTextCharFormat)
from PySide6.QtCore import (QLineF, QPointF,QPoint, QRect, QRectF, 
            QSize, QSizeF, Qt, Signal, Slot, QTimer, QObject,
            QMimeData, QBuffer, QByteArray, QIODevice)


#A helper blob drawing class
# Gemini code.
from PySide6.QtWidgets import QGraphicsObject, QStyleOptionGraphicsItem, QGraphicsItemGroup
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
        self._baseColor = DRAWING_COLOUR
        self._hoverColor = HOVER_COLOUR
        self._selectColor = SELECT_COLOUR
        self._pen = QPen(Qt.NoPen)  #QPen(self._baseColor, self._penWidth)

        self._basePath = QPainterPath()
        self._basePath.addRoundedRect(self._rect, self._xRadius, self._yRadius, self._mode)
        
        # Interaction settings
        self.setAcceptHoverEvents(True)
        #self.setFlags(QGraphicsObject.ItemIsSelectable | QGraphicsObject.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        #Let the parent handle the buttons
        self.setAcceptedMouseButtons(Qt.NoButton)
        self.setCacheMode(QGraphicsItem.CacheMode.NoCache)
        #self.setVisible(False) #JH needed if local paint is removed
        self.isHovered = False

    def boundingRect(self) -> QRectF:
        # Increase the bounding box slightly to account for the pen width
        margin = self._pen.widthF() / 2

        return self._rect.adjusted(-margin, -margin, margin, margin)

    def shape(self) -> QPainterPath:
        # Returns only the hollow border path
        self._basePath = QPainterPath()
        self._basePath.addRoundedRect(self._rect, self._xRadius, self._yRadius, self._mode)
        stroker = QPainterPathStroker()
        stroker.setWidth(HITSIZE) # Hit-area thickness
        return stroker.createStroke(self._basePath)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
    #jh commented out entire function to romove local paint   
        # Determine styling by looking at the PARENT'S state
        parent = self.parentItem()
        if parent and parent.isSelected():
            painter.setPen(QPen(self._selectColor, 1.0, Qt.DashLine))
        elif self.isHovered:
            painter.setPen(self._hoverColor)
        else:
            painter.setPen(QPen(self._baseColor, 1.0))
            
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(self._rect, self._xRadius, self._yRadius, self._mode)

    def setPen(self,pen):
        self._pen = pen

    def setRoundedRect(self, rect: QRectF):
        """ Allows the changing of Rounded Rect params in a Qt-like way"""
        #TODO: Extend to **kwargs processing to allow changing of all params
        self._rect = rect

    def hoverEnterEvent(self, event):
        self.isHovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.isHovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        # Only emits if the user clicks the actual 'shape' (the outline)
        #print(f"RR mouse pressed {event=}")
        #self.clicked.emit()
        super().mousePressEvent(event)

class BlobTextItem(QGraphicsTextItem):
    def __init__(self, text, width, parent):
        super().__init__(text, parent)
        if not BLOB_NAME_ON_TOP:
            self.yOffset=10
        else:
            self.yOffset=0
        self.setPos(0, self.yOffset)
        #self.setPos(x, y)

        # 1. Enable editing and selection
        self.setTextInteractionFlags(Qt.TextEditorInteraction|Qt.LinksAccessibleByMouse)
        self.document().contentsChanged.connect(self.textChanged)
        #self.setOpenExternalLinks(True)

        # 2. Appearance tweaks
        self.setDefaultTextColor(QColor("#2c3e50"))
        self.setFont(QFont("Arial", BLOB_FONT_SIZE))
        #self.setTextWidth(width)
        self.setTextSize(parent)
        # 3. Make the item movable within the scene
        self.setFlag(QGraphicsTextItem.ItemIsMovable)
        #self.setFlag(QGraphicsTextItem.ItemIsSelectable)
    
    def boundingRect(self):
        # Get the original rect to keep the calculated width
        rect = super().boundingRect()
        # Force the height to our custom value
        return QRectF(rect.x(), rect.y(), rect.width(), min(self.parentItem()._height-self.yOffset, rect.height()))

    def paint(self, painter, option, widget):
        # Optional: Draw a subtle background behind the text
        if self.parentItem().metadataAttributes['description']['display']:
            painter.setClipRect(self.boundingRect())
            painter.setBrush(QColor(240, 240, 240, 100))
            painter.setPen(Qt.NoPen)
            painter.drawRect(self.boundingRect())
            
            # Call the original paint method to draw the text itself
            super().paint(painter, option, widget)

    def setTextSize(self, parent):
        if parent.metadataAttributes['description']['display']== False:
        #if self.parentItem().Scene.optionBlobDesc == False:
            super().setTextWidth(1)
        else:
            super().setTextWidth(parent._width)
            if BLOB_FONT_IS_RESIZABLE == True:
                currentHeight=super().boundingRect().height()
                currentFontSize=self.font().pointSize()
                if currentHeight > parent._height and currentFontSize>6:
                    while currentHeight > parent._height and currentFontSize>6:
                        currentFontSize-=1
                        self.setFont(QFont("Arial",currentFontSize))
                        currentHeight=super().boundingRect().height()
                elif currentHeight+5 < parent._height and currentFontSize<BLOB_FONT_SIZE:
                    while currentHeight+5 < parent._height and currentFontSize<BLOB_FONT_SIZE:
                        currentFontSize+=1
                        self.setFont(QFont("Arial",currentFontSize))
                        currentHeight=super().boundingRect().height()
    
    def textChanged(self):
        self.setTextSize(self.parentItem())
        return
    
        
    def mousePressEvent(self, event):
        # Forward to parent
        if self.parentItem() and self.parentItem().metadataAttributes['description']['display']==False:
            event.ignore()
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parentItem() and self.parentItem().metadataAttributes['description']['display']==False:
            event.ignore()
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.parentItem() and self.parentItem().metadataAttributes['description']['display']==False:
            event.ignore()
        else:
            super().mouseDoubleClickEvent(event)


    #def mousePressEvent(self, mouseEvent):
    #    if (mouseEvent.button() == Qt.MouseButton.RightButton):
    """cursor = self.textCursor()
            if cursor.hasSelection():
                font=QFontDialog.getFont()
                if font.isValid():
                    fmt= QTextCharFormat()
                    fmt.setFont(font)
                    cursor.mergeCharFormat(fmt)
                    self.setTextCursor(cursor)
                colour=QColorDialog.getColor()
                if colour.isValid():
                    fmt = QTextCharFormat()
                    fmt.setForeground(colour)
                    cursor.mergeCharFormat(fmt)
                    self.setTextCursor(cursor)"""
     #       return super().mousePressEvent(mouseEvent)


class VisNodeItem(QGraphicsObject):
    """ Create a new node - both Graph Model and Visual ("graphics") 
    This connects visual Rect to model and list 
    
    """
    #Create the signal for editing
    requestEdit = Signal(object)  

    def __init__(self,posn,model, treeWidget, parent=None, nameP ="", id=None,
                    metadata={}, metadataAttributes={},ports = [], parents=[]):
        #print(f"In VisNodeItem {posn =}")
        super().__init__(parent)
        self.suppressItemChange = True  # suppress itemChange (was protected, but scene needs to set it)
        
        self.model = model
        #self.listWidget = listWidget
        self.treeWidget = treeWidget
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
        self.blobDescription=""   #needed for blobs
        #Update positions
        #add to the text list
        #lWitem = QListWidgetItem(self.model.Gr.nodeD[self.nodeNum].metadata['name'])
        #lWitem.setData(KEY_INDEX,self.nodeNum)
        #lWitem.setData(KEY_ROLE,ROLE_NODE)
        #self.listWidget.addItem(lWitem)

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
        
        self.parents = parents
        #This will always be empty, but it makes the code more general
        self.children = [] 
        self.childGroup=None  #safest to initialise this upfront


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
        self._nextPort = -1 #Counter for port index, -1 mean none
        self._Ports = []
        #save any ports passed in
        # copy to _Ports
        for p in ports:
            if p.index > self._nextPort: self._nextPort = p.index
            self._Ports.append(p)
            p.setParentItem(self.nodeShape)


        #Make nodes appear in front of edges for painting & selection
        self.setZValue(1000)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsScenePositionChanges)
        
        #TODO: hoverEvents are not sent when there is an explicit mouseEVent handler. Handle in scene and delete here
        self.setAcceptHoverEvents(True)
        self.isHovered = False
        #self._hoverColor = QColor("red")
        self._baseColor = DRAWING_COLOUR
        self._hoverColor = HOVER_COLOUR
        self._selectColor = SELECT_COLOUR
        self.suppressItemChange = False  # enable itemChange normally

    def __repr__(self):
        return f"\n*>* VisNodeItem {super().__repr__()}\nIndex:{self.data(KEY_INDEX) }  Role:{self.data(KEY_ROLE) =} @ {self.pos() =} Ports:{self._Ports=}\n\
                {self.startsEdges = },\n{self.endsEdges = }\n*<*" #\n {self.nodeShape =})"
    __str__ = __repr__

    def toXML(self,Xparent):
        """ add an Element Tree node to the XML parent node with the Edge Data """
        xmlNode = ET.Element("node", id=str(self.nodeNum))

        data = ET.SubElement(xmlNode, "data", key="data_node")
        shape = ET.SubElement(data, "y:" + "ShapeNode")
        ET.SubElement(shape, "y:Geometry", {'x':str(self.pos().x()), 'y':str(self.pos().y())})
        for p in self._Ports:    
            ET.SubElement(shape,"port",name=str(p.index), t=str(p.t), x=str(p.pos().x()), y=str(p.pos().y()) )

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

        #Add parents
        if len(self.parents) > 0:
            comment = ET.Comment("Parent nodes/ blobs included for reference. Recalculated from geometry on load")
            xmlNode.append(comment)
            parents = ET.SubElement(xmlNode,"h:parents")
            parents.text = " ".join([str(p.nodeNum) for p in self.parents])

        return xmlNode

    def setMetadataDisplay(self):
        """setup metadata to display
            This should be the same code as in VisEdgeItem
        """
        #TODO: This needs to be called by itemChange somehow.
        metaStr = ''
        for k,v in self.metadata.items():
            if k != 'name' and k != 'description':
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
            painter.setPen(QPen(self._selectColor,1,Qt.DashLine))
            self.nodeShape.setPen(QPen(self._selectColor,1,Qt.DashLine))
        elif self.isHovered:
            painter.setPen(self._hoverColor)
            self.nodeShape.setPen(self._hoverColor)
        else:
            painter.setPen(self._baseColor)
            self.nodeShape.setPen(self._baseColor)


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
            if change in [QGraphicsItem.ItemPositionHasChanged, QGraphicsItem.ItemChildAddedChange,QGraphicsItem.ItemScenePositionHasChanged]:
                for port in self._Ports:
                    for sEdge in port.startsEdgeLines:
                #for sEdge in self.startsEdges:
                        sEdge.updateLine((self,port))
                #for eEdge in self.endsEdges:
                    for eEdge in port.endsEdgeLines:
                        eEdge.updateLine((self, port))

        #note the **return**
        return super().itemChange(change,value)
    
    def hoverEnterEvent(self, event):
        self.isHovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.isHovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def positionToParameter(self, screenPos:QPointF)->float:
            """ Takes a pos, and returns a value giving the position of the pos on the nodeshape's edge """
            #gemini code

            #Find the parametric position of the point on the nodeshape
            #Calculates the clockwise 'distance' around the perimeter.
            # 0.0 = Right, 0.25 = bottom, 0.5 = left, 0.75 = top.

            center = self.pos()
            #Calculate delta from center
            dy = screenPos.y() - center.y()
            dx = screenPos.x() - center.x()
            angle = math.atan2(dy, dx)

            #Normalize to [0, 1) range  (Python % 1 is very clever with signs & floats!!)
            t = (angle/(2*math.pi)) % 1
            return t

    def parameterToPosition(self, t:float)->QPointF:
        """ Takes a parameter, and uses nodeshape geometry to work out a pos on the nodeshape"""
        #NODESIZE/2 is harcoded here
        angle = t*math.pi*2
        pos = QPointF(NODESIZE/2 * math.cos(angle),NODESIZE/2 * math.sin(angle)   )
        return pos

    def createPort(self,screenPos)->int:
        """ Create a port at `pos` for an edge to connect on, return the int index for reference"""
        #TODO: Return a tuple (index, object) ??

        #cycle the point through the param calc 1. to get the para for future use, 2. to get the exact shape fit for 'close' clicks
        #find the param position
        t = self.positionToParameter(screenPos)

        #Create the port, add to the node's list
        #This snaps the port to exactly on the shape (pos may be slightly off)
        portPos = self.parameterToPosition(t)

        #print(f"{t=},{portPos=}")
        #Parent to nodeShape for better geom flexibility
        self._nextPort += 1 
        p = port(portPos, t=t, index =self._nextPort,  parent=self.nodeShape)
        #print(f"Port created on node{self.nodeNum}: as port{p.index} at {p.t} {len(self._Ports)=}")
        self._Ports.append(p) 

        #TODO: Should this not rather return `p`?
        return p

    def findPort(self,screenPos)->int:
        """ checks for a port at screenPos using HITSIZE, returns index if found, -1 if not"""
        found = None
        minD = math.inf
        for existingPort in self._Ports:
            d = QLineF(existingPort.scenePos(), screenPos).length()
            #print(f"{self.nodeNum}:{existingPort.index=} findPort: {d}")
            if d <= HITSIZE:
                if d < minD:
                    #found = existingPort.index
                    found = existingPort
                    minD = d
        return found

    def updatePort(self, p:port, pos:QPointF):
        """ update pos of port p in the nodes list of ports """

        p.t = self.positionToParameter(pos)
        p.setPos(self.parameterToPosition(p.t))
        #print(f"New pos = {p.pos()}")

    def updatePorts(self):
        """After any geom change, recalculate each port's pos from t """
        
        for p in self._Ports:
            p.setPos(self.parameterToPosition(p.t))

    def updatePortEdges(self):
        """ Update the edges attached to each port """
        for port in self._Ports:
            for sEdge in port.startsEdgeLines:
                sEdge.updateLine((self,port))
            for eEdge in port.endsEdgeLines:
                eEdge.updateLine((self, port)) 

    def deletePort(self, delPort:port): # delIndex:int):
        """Remove a port """
        #TODO: How to check there are no references to _Ports[i]
        #TODO: index is not used - delete based on ID 
        #Currently (02a) only one edge per port

        self._Ports.remove(delPort)
        delPort.setParentItem(None)
        del delPort

    def portFromIndex(self, Xindex)->port:
        """ Returns the port object corresponding to the index """
        for p in self._Ports:
            if p.index == Xindex:
                return p
        print(f"WARNING: port {Xindex} not found on node {self.nodeNum}")

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

        super().mousePressEvent(mouseEvent)
        """

class VisBlobItem(VisNodeItem):
    """Generalise point-like nodes to sets. Blame Harel for the name"""
    #Constants for the corners of a (rectangular) blob
    TL = 0
    TR = 1
    BR = 2
    BL = 3

    def __init__(self,posn, model, treeWidget, parent=None, nameP ="", id=None,
                    metadata={}, metadataAttributes={}, ports = [],
                    height=NODESIZE, width=NODESIZE,xRadius=0, yRadius=0, radMode = Qt.AbsoluteSize, parents=[],children=[]): 
        """  posn is the topleft, size is width and height, Radii are corner curves
           NB: `parent` is the (visual) Qt parent, `parents` is the (abstract) core Graph blob parent """
        super().__init__(posn, model, treeWidget, parent=parent, nameP =nameP, id=id,
                    metadata=metadata, metadataAttributes=metadataAttributes,ports=ports)

        self.suppressItemChange = True

        #Fix Blob-Node differences
        #TODO: Make blob names default to bnn

        #add to the text list
        #lWitem = self.listWidget.findItemByIdx(self.nodeNum)
        #TODO: Revisit the value the model adds
        self.node.setData(KEY_ROLE,ROLE_BLOB)
        #lWitem.setData(KEY_ROLE,ROLE_BLOB)


        self.setData(KEY_ROLE, ROLE_BLOB)

        self.setAcceptHoverEvents(True)
        self.isHovered=False
        #self._hoverColor=QColor("cyan")
        self._baseColor = DRAWING_COLOUR
        self._hoverColor = HOVER_COLOUR
        self._selectColor = SELECT_COLOUR
        self.parents = parents
        self.children = children

        #Node constructor doesn't take parents & children, so add now

        #Remove the nodeShape set in the parent - first reparent ports
        for port in self._Ports:
            port.setParentItem(self)
        self.nodeShape.setParentItem(None)
        del self.nodeShape
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
        # give ports back to the nodeshape
        for port in self._Ports:
            port.setParentItem(self.nodeShape)
        #blob text JH
        if 'description' not in self.metadataAttributes:
            self.metadataAttributes['description']={'display':DISPLAY_BLOB_DESCRIPTION_BY_DEFAULT}
            self.metadata['description']='*'
       # if DISPLAY_BLOB_DESCRIPTION_BY_DEFAULT:
        if 'description' in self.metadata:
            blobText=self.metadata['description']
        else:
            blobText="*"
        container = BlobTextItem(blobText, width, self)
        self.blobDescription=container
        #else:
        #    container = BlobTextItem("", width, self)
        #    self.text=container
        #    self.text.setFlag(QGraphicsItem.ItemIsVisible, False)
        #    self.text.setFlag(QGraphicsItem.ItemIsSelectable, False)

        #Metadata disply position
        self.metaDisplay.setPos(QPointF(NODESIZE/4, -NODESIZE/4))  

        #Placeholder for drag handles
        self._Handles = []


        #Create a polygon version for `parameterFromPos` - also in `updateFromHandles`
        self._basePath = QPainterPath()
        self._basePath.addRoundedRect(self._rect, self._xRadius, self._yRadius)
        #totalLength = self._basePath.length()
        self._polygon = self._basePath.toFillPolygon()


        #Use the edge `isOnlySelected` logic as far as possible for handle creation
        self.isOnlySelected = False

        self.suppressItemChange = False

    def __repr__(self):
        r = f"\noo VisBLOBItem\nIndex:{self.data(KEY_INDEX) }  Role:{self.data(KEY_ROLE) =} @ {self.pos() =} Ports:{self._Ports =}\n"+\
                f"{self.startsEdges = },\n{self.endsEdges = }\n00" #\n {self.nodeShape =})"
        return r
    __str__ = __repr__

    def toXML(self, Xparent):
        
        xmlBlob = ET.Element("h:blob", id=str(self.nodeNum))

        data = ET.SubElement(xmlBlob, "data", key="data_blob")
        shape = ET.SubElement(data, "h:" + "ShapeBlob")
        ET.SubElement(shape, "h:Geometry", {'x':str(self.pos().x()),\
             'y':str(self.pos().y()), 'width':str(self._width), 'height':str(self._height), \
                'xRadius':str(self._xRadius),'yRadius':str(self._yRadius), \
                'radMode':str(self._radMode)})
        for p in self._Ports:    
            ET.SubElement(shape,"port",name=str(p.index), t=str(p.t), x=str(p.pos().x()), y=str(p.pos().y()) )

        blobLabel = ET.SubElement(shape, "h:BlobLabel")
        blobLabel.text = self.metadata['name']
        for atK,atV in self.metadataAttributes['name'].items():
            metaAtt = ET.SubElement(blobLabel, "h:metadataAttribute", {"key":atK,"value":str(atV)})
        #update metadata from blobDescription
        if 'description' in self.metadata \
                and self.metadata['description']!=self.blobDescription.toPlainText():
            self.metadata['description']=self.blobDescription.toPlainText()
        #add metadata other than name
        if len(self.metadata) >= 2:
            for k, v in self.metadata.items():
                if k != "name":
                    metaEl  = ET.SubElement(xmlBlob, "h:metadata", {"key":k,"value":str(v)})
                    for atK,atV in self.metadataAttributes[k].items():
                        metaAtt = ET.SubElement(metaEl, "h:metadataAttribute", {"key":atK,"value":str(atV)})

        if len(self.parents) > 0:
            comment = ET.Comment("Parent nodes/ blobs included for reference. Recalculated from geometry on load")
            xmlBlob.append(comment)
            parents = ET.SubElement(xmlBlob,"h:parents")
            parents.text = " ".join([str(p.nodeNum) for p in self.parents])
        if len(self.children) > 0:
            comment = ET.Comment("Child nodes/ blobs included for reference. Recalculated from geometry on load")
            xmlBlob.append(comment)
            children = ET.SubElement(xmlBlob,"h:children")
            children.text = " ".join([str(c.nodeNum) for c in self.children])  

        return xmlBlob

    def boundingRect(self):
        #TODO: Add in the displayed text
        return self.nodeShape._rect.adjusted(-5, -5, 5, 5)
    
    def shape(self):
        # Combined shape: Hollow Border + Solid Text Area
        #print("Blob shape udpate")
        #path = self.nodeShape.shape() 
        path = self.mapFromItem(self.nodeShape, self.nodeShape.shape())

        #TODO: This does not put the textRect where paint does (FontMetrics boundrect does not see the Qt.Align flags)
        #if self.metadataAttributes.get('name', {}).get('display', True):
        #    #TODO: When text is rich text, this will need updating
        #    tFont = QFont()
        #    fm = QFontMetrics(tFont)
        #    # Use same rect/logic as paint() for text hit-area
        #    textRect = fm.boundingRect(self._rect.toRect(), Qt.AlignLeft | Qt.AlignCenter, self.dispText)
        #    path.addRect(QRectF(textRect))

        #outlinePath = QPainterPathStroker()
        #outlinePath.setWidth(HITSIZE*2)
        #return outlinePath.createStroke(path)            
        return path
     
    def hoverEnterEvent(self, event):
        self.isHovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.isHovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def paint(self, painter: QPainter, option: QStyleOptionGraphicsItem, widget=None):
        if self.isSelected():
            painter.setPen(QPen(self._selectColor,1,Qt.DashLine))
        elif self.isHovered:
            painter.setPen(self._hoverColor)
        else:
            painter.setPen(self._baseColor)

        #self.nodeShape is painted by Qt, using parent's pen???

        #JH put this (below) in if rectangle paint is removed
        #painter.drawRoundedRect(self.nodeShape._rect, self.nodeShape._xRadius, self.nodeShape._yRadius, self.nodeShape._mode)

        #Draw the text if set to display
        if self.metadataAttributes['name']['display']:
            # Pos on top (this can be generalised to left, bottom, right, etc)
            if BLOB_NAME_ON_TOP:
                r = QRectF(0,-NODESIZE,0,0) 
                r = painter.drawText(r,Qt.AlignCenter,self.dispText)
                painter.drawText(r, Qt.AlignCenter, self.dispText)
            else:
            #painter.drawText(self._rect, Qt.AlignCenter | Qt.AlignTop, self.dispText)
            #TODO: This must become a transparentTextItem, to be selectable, and to put the bounding rect in the right place
                painter.drawText(self._rect, Qt.AlignLeft | Qt.AlignTop, self.dispText)
        #Debug - draw the shape path

        #painter.setPen(QPen(Qt.green,1))
        #painter.drawPath(self._basePath)
        #painter.drawPath(self.shape())
        #painter.drawRect(self.boundingRect())

    def getChildList(self, blob)->list:
        """ Return a list of all children and childrens children etc """
        descendants = []
        for c in blob.children:
            descendants.append(c)
            descendants.extend(self.getChildList(c))
        
        return descendants
    
    def removeGroup(self, groupName):
        try:    #if the group has been deleted it might have left a wraith
            kidsToGo=self.childGroup.childItems()
            #print(f"deleting blob group for {self.nodeNum}, with kids {[(k.nodeNum,hex(id(k))) for k in kids]}")
            #JH for item in kids: #self.children:
            for item in kidsToGo:
                  #removeFromGroup seems to bug out occasionally :/
                self.childGroup.removeFromGroup(item)
                
                #This seems more reliable.
                newScenePos = item.mapToScene(0, 0)
                item.setParentItem(None)
                item.scene().update()
                item.setPos(newScenePos)
            self.scene().destroyItemGroup(self.childGroup)
            self.childGroup=None
        except:
            pass
        return()


    def itemChange(self, change, value):
        if self.suppressItemChange:
            return super().itemChange(change, value)
        #print(f"Blob {self.nodeNum}, {change=} {value=} ")

        #On ItemSelectedHasChanged, create a temp group of contained BLOBS and NODES. Delete on deselect
        if change == QGraphicsItem.ItemSelectedHasChanged :
            #kids = self.getChildList(self)
            kidsIdx=self.scene().getDirectContainmentGraph(self.scene().getContainmentMap(self))[self.data(KEY_INDEX)]
            kids=[]
            for k in kidsIdx:
                kids.append(self.scene().findItemByIdx(k))
            #print("checking kids", kidsIdx)
            #print("and this is kids", kids)
            #if value == 1 and len(self.children) > 0 and self.isOnlySelected: #when selected
            if value == 1 and self.isOnlySelected: #when selected
            #if value == 1 and len(self.scene().selectedItems())==1: #this is better, but stops select all working
                #Make group
                self.childGroup = QGraphicsItemGroup(self)
                for item in kids:
                    self.childGroup.addToGroup(item)
            #else: #unselected or no children
            elif value == 0: #when deselected
                #delete group
                #print(f"delete group for {self.nodeNum} - childGroup: {getattr(self, "childGroup" , "No childGroup")} ")
                #if getattr(self, "childGroup" , False):
                self.removeGroup(self.childGroup)
                    #JH kids = self.getChildList(self)

                """kidsToGo=self.childGroup.childItems()
                    #print(f"deleting blob group for {self.nodeNum}, with kids {[(k.nodeNum,hex(id(k))) for k in kids]}")
                    #JH for item in kids: #self.children:
                    for item in kidsToGo:
                        #removeFromGroup seems to bug out occasionally :/
                        #self.childGroup.removeFromGroup(item)
                        
                        #This seems more reliable.
                        newScenePos = item.mapToScene(0, 0)
                        item.setParentItem(self)
                        item.setPos(newScenePos)
                    self.scene().destroyItemGroup(self.childGroup)"""
                    #JH rescue any children that were excluded by a resize
                    #if getattr(self, "childGroup" , False):
                    #    if type(self.childGroup) == "QGraphicsItemGroup":
                    #        self.scene().destroyItemGroup(self.childGroup)
                    #print(f"AFTER deleting blob group for {self.nodeNum}, with kids {[(k.nodeNum,hex(id(k))) for k in kids]}")

            #Call the edge update
            for k in kids:
                k.updatePortEdges() 

        #Moved
        if change in [QGraphicsItem.ItemPositionHasChanged, QGraphicsItem.ItemChildAddedChange]:
            #print("blob pos change")
            pass

        return super().itemChange(change, value)
    
    def XXpositionToParameter(self, mousePos:QPointF)->float:
        #Both of these seem to work. Not sure why I wrote 2!
        # the path may not always be reactangular, so keep options opem
        self._basePath = QPainterPath()
        self._basePath.addRoundedRect(self._rect, self._xRadius, self._yRadius)
        totalLength = self._basePath.length()

        #turn shape to polygon by letting curves be multiple short edges
        self._polygon = self._basePath.toFillPolygon()
        relativeMousePos = self.mapFromScene(mousePos)

        #step through the line segments accumulating the distance before the mouse is found
        accumulatedLength=0
        pCount = self._polygon.count()
        #print(f"{pCount=}")
        for i in range(self._polygon.count() - 1):
            p1 = self._polygon[i]
            p2 = self._polygon[i + 1]
            line = QLineF(p1, p2)
            #print(f"seg {i} is {p1} to {p2}")
            """
            #pointLine=QLineF(relativeMousePos,relativeMousePos)
            if p1TopLeftp2(p1,p2):
                pRect = QRectF(p1,p2) 
            else:
                pRect = QRectF(p2,p1)
            pRect = pRect.adjusted(-HITSIZE/2,-HITSIZE/2, HITSIZE/2,HITSIZE/2)
            if pRect.contains(relativeMousePos):
                print(f"\n{relativeMousePos} in {pRect} seg {i}/{pCount}")
                shortLine=QLineF(p1, relativeMousePos)
                accumulatedLength+=shortLine.length()
                break
            else:
                print(f"x{i}", end =" ")
                accumulatedLength+=line.length()
            """
            betweenx=False
            betweeny=False
            if (p1.x()<=relativeMousePos.x()+HITSIZE and relativeMousePos.x()-HITSIZE<=p2.x()) or\
               (p1.x()>=relativeMousePos.x()-HITSIZE and relativeMousePos.x()+HITSIZE>=p2.x()):
                betweenx=True
            if (p1.y()<=relativeMousePos.y()+HITSIZE and relativeMousePos.y()-HITSIZE<=p2.y()) or\
               (p1.y()>=relativeMousePos.y()-HITSIZE and relativeMousePos.y()+HITSIZE>=p2.y()):
                betweeny=True
            if betweenx and betweeny:
                shortLine=QLineF(p1, relativeMousePos)
                accumulatedLength+=shortLine.length()
                break
            else:          
                accumulatedLength+=line.length()
            
        t=accumulatedLength/totalLength
        return(t)    

    def _closestTOnSegment(self, a: QPointF, b: QPointF, p: QPointF) -> float:
        """ Calculates the local projection parameter t for point p on segment ab """
        #gemini
        line = QLineF(a, b)
        if line.length() == 0: 
            return 0.0
        
        dx = b.x() - a.x()
        dy = b.y() - a.y()
        
        # Dot product projection formula: 
        # t = [(p-a) · (b-a)] / |b-a|^2
        t = ((p.x() - a.x()) * dx + (p.y() - a.y()) * dy) / (dx**2 + dy**2)
        return max(0.0, min(t, 1.0))

    def positionToParameter(self, scenePos:QPointF)->float:
        """ Takes a pos, and returns a value giving the position of the pos on the blobs's edge 
            Uses _polygon set in `updateFromHandles`
        """
        #gemini code
        #TODO: This should be in updateFromHandles
        self._basePath = QPainterPath()
        self._basePath.addRoundedRect(self._rect, self._xRadius, self._yRadius)
        totalLength = self._basePath.length()

        if totalLength == 0:
            return 0.0
        #Find the parametric position of the point on the nodeshape
        #Path to polygon segements
        self._polygon = self._basePath.toFillPolygon()

        localPos = self.mapFromScene(scenePos)

        bestT = 0.0
        minDist = math.inf
        accumulatedLength = 0.0

        # 3. Iterate through segments to find the closest projection
        for i in range(self._polygon.count() - 1):
            p1 = self._polygon[i]
            p2 = self._polygon[i + 1]
            line = QLineF(p1, p2)
            segmentLen = line.length()

            # Find the 0.0-1.0 parameter on this specific segment
            tSeg = self._closestTOnSegment(p1, p2, localPos)
            
            pointOnSeg = line.pointAt(tSeg)
            #print(f"{pointOnSeg =}")
            dist = QLineF(localPos, pointOnSeg).length()

            # 4. Update the global bestT if this segment is closer
            if dist < minDist:
                minDist = dist
                # Calculate global t: (LengthSoFar + ProgressInSegment) / totalLength
                bestT = (accumulatedLength + (tSeg * segmentLen)) / totalLength
            
            accumulatedLength += segmentLen

        t = max(0.0, min(bestT, 1.0))
        return t

    def parameterToPosition(self, t:float)->QPointF:
        """ Takes a parameter, and uses nodeshape geometry to work out a pos on the nodeshape"""

        pos = self._basePath.pointAtPercent(t)
        return pos

    """
    def setSelected(self,state:bool):
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
        super().setSelected(state)
        """

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
        self._Handles.append(HandleItem(QPointF(0,0),color=BLOB_HANDLE_COLOUR,parent=self))
        self._Handles.append(HandleItem(QPointF(BRx,0),color=BLOB_HANDLE_COLOUR,parent=self))
        self._Handles.append(HandleItem(QPointF(BRx,BRy),color=BLOB_HANDLE_COLOUR,parent=self))
        self._Handles.append(HandleItem(QPointF(0,BRy),color=BLOB_HANDLE_COLOUR,parent=self))
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

        #resize text when blob resizes
        self.blobDescription.setTextSize(self)

        #Figure out the geometry for these lines
        self.setPos(TLx,TLy)
        self._rect=QRectF(0,0,self._width,self._height)  #JH I hope this is right
        self.nodeShape.setRoundedRect(QRectF(0,0,self._width,self._height))

        #Create a polygon version for `parameterFromPos`
        self.updatePorts()

        self.suppressItemChange = False
        
        #this SHOULD be propagated via itemChange(), but that only happens at start, not end of handle move use itemChanged() (past-tense)?
        self.updatePortEdges()

    def updatePorts(self):
        """After any geom change, recalculate each port's pos from t """

        #Create a polygon version for `parameterFromPos`
        self._basePath = QPainterPath()
        self._basePath.addRoundedRect(self._rect, self._xRadius, self._yRadius)
        totalLength = self._basePath.length()
        self._polygon = self._basePath.toFillPolygon()
        #Update all `port` positions - this almost/ sometimes works
        for p in self._Ports:
            p.setPos(self.parameterToPosition(p.t))


    def mousePressEvent(self, event):
        #Call VisNode's mouse handler
        super().mousePressEvent(event)