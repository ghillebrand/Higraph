""" Edges code """
#For debugging: (stack traces)
import traceback
import gc

#Global constants. 
from  HGConstants import *

# core Graph class:
from coreGraph import Graph

#Helper & housekeeping functions
#Draw nice edges
from PolyLineItemHG import StraightLineItem, HermiteSplineItem, HandleItem
from GraphicsSupport import *
from Nodes import  * #Needed for type checking

#For file handling and clipboard
import xml.etree.ElementTree as ET
from xml.dom import minidom

from PySide6.QtWidgets import ( QApplication, QWidget, QMainWindow, QDialog,
            QGraphicsScene, QGraphicsView, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
            QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
            QLineEdit, QInputDialog, QMenu, QFileDialog, QStyleOptionGraphicsItem, QGraphicsObject,
            QSlider, QLabel, QStatusBar,
            QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton)

from PySide6 import (QtCore, QtWidgets, QtGui )
from PySide6.QtGui import (QStandardItemModel, QStandardItem, QPolygonF,QPainter,
            QTransform, QFont, QFontMetrics, QAction, QCursor, QPen,QBrush,
            QPainterPath, QPainterPathStroker, QCursor, QColor, 
            QGuiApplication, QImage, QPixmap)
from PySide6.QtCore import (QLineF, QPointF,QPoint, QRect, QRectF, 
            QSize, QSizeF, Qt, Signal, Slot, QTimer, QObject,
            QMimeData, QBuffer, QByteArray, QIODevice)



class VisEdgeItem(QGraphicsObject): #QGraphicsItem,QObject):
    """ Create a new edge - both Graph Model and Visual ("graphics")
      This connects visual edges to model and list 
    """
    #Create the signal for editing
    requestEdit = Signal(object)  

    def __init__(self,model,treeWidget, sItem, eItem, directed='', parent=None, nameP="", id=None,
                    polyLineType = DEFAULT_EDGE, points=[],tangents=[],metadata={}, metadataAttributes={}):
        """ Create a visual edge, using the pos of the st and end, which are tuples of (Node,Port)
        points must be QPointFs and tangents must be tuples of QPointFs, relative to the points
        """
        super().__init__(parent)
        self.suppressItemChange = True  # suppress itemChange until all attribs set.

        self.model = model
        #self.listWidget = listWidget
        self.treeWidget = treeWidget
        #Note: Unlike a node which is a 1-click create,
        #   an edge can only be created once the start and end nodes are known. 
        #   Thus drawing must precede the creation of the abstract edge.
        #   This drawing has to be handled by the Scene mouse events, prior to construction.

        #SO code: track the VisNodes
        #TODO: update to startItem for hypergraphs
        #Set up basics here, call setStart & setEnd after the geom is in place, for updates.
        #startNode must be a tuple (node,port). convert if not
        #TODO: Was this only needed during construction - all `sItems` seem to be tuples now.
        if not type(sItem) is tuple: 
            #print(f"{sItem._Ports =}")
            if len(sItem._Ports) == 0: #No ports, create one
                spID = sItem.createPort(self.startNode.pos())
            sItem = (sItem,sItem._Ports[spID])
        self.startNode = sItem
        #print(f"port {sItem=}")
        
        #Add ports to endNode
        if not type(eItem) is tuple: 
            #print(f"{eItem._Ports =}")
            if len(eItem._Ports) == 0: #No ports, create one
                epID = eItem.createPort(self.endNode.pos())
            eItem = (eItem,eItem._Ports[epID])
        self.endNode = eItem

        #Create an abstract edge, and keep the index as well
        sName =self.model.Gr.nodeD[sItem[0].nodeNum].metadata['name'] 
        eName =self.model.Gr.nodeD[eItem[0].nodeNum].metadata['name'] 

        #if not nameP:
        #TODO: Refactor edgeNum & nodeNum to itemNum for hyperedges
        #TODO: Make nameP more configureable
        #defName = f"{sName}->{eName}"
        defName = "" #just the ID
        self.edge,self.edgeNum = self.model.addGMEdge(sItem[0],eItem[0],nameP = defName,id=id)
        #update the name with the edge ID, to help tracking
        # self.metadata is just a more elegant wrapper
        self.metadata = self.model.Gr.edgeD[self.edgeNum].metadata
        #"deep copy" the dict
        for k,v in metadata.items():
            self.metadata[k] = v
        #initialise metadataAttributes if not passed in:
        if len(metadataAttributes) > 0:
            self.metadataAttributes = metadataAttributes
        else:
            self.metadataAttributes = {'name':{'display':DISPLAY_NAME_BY_DEFAULT}}

        #TODO: This overwrites in metadata['name'] value, but it should be the same?
        #self.model.Gr.edgeD[self.edgeNum].metadata.update({'name':f"{self.edgeNum} {self.model.Gr.edgeD[self.edgeNum].metadata['name']}"})
        self.metadata['name'] = f"{self.edgeNum} {self.metadata['name']}"
        if nameP:
            #self.edge,self.edgeNum = self.model.addGMEdge(sItem,eItem,nameP=nameP)
            self.metadata['name'] = nameP
                
        #add to the text list
        #TODO: Should this not be driven from the model?
        #lWitem = QListWidgetItem(self.metadata['name'])
        #lWitem.setData(KEY_INDEX,self.edgeNum)
        #lWitem.setData(KEY_ROLE,ROLE_EDGE)
        #self.listWidget.addItem(lWitem)
        #add to tree
        tWitem = QTreeWidgetItem([self.model.Gr.edgeD[self.edgeNum].metadata['name'],str(self.edgeNum), "edge"])
        tWitem.setData(0, KEY_INDEX,self.edgeNum)
        tWitem.setData(0, KEY_ROLE,ROLE_EDGE)
        self.treeWidget.addTopLevelItem(tWitem)

        # Create a text item to hold & show the ID number
        #self.textItem = QGraphicsTextItem(f"{self.edgeNum}", self)
        #textRect = self.textItem.boundingRect()
        #self.textItem.setPos(-textRect.width()/2, -textRect.height()/2)
        
        #Non-display data, for referencing to model and listView
        noPen = QPen(Qt.NoPen)
        self.setData(KEY_INDEX, self.edgeNum)
        self.setData(KEY_ROLE, ROLE_EDGE)

        #Draw name in the middle
        #self.textItem = QGraphicsTextItem(self.model.Gr.edgeD[self.edgeNum].metadata['name'], parent=self)
        # chatGPT's suggestion to avoid shape() not selecting it - TransparentTextItem
        self.textItem = TransparentTextItem(self.metadata['name'], parent=self) 
        #Stop Python GC from mangling things on delete. This ref is critical?? - Python crashes on delete without it.?
        self.textItem.my_parent_item = self

        self.textItem.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.textItem.setFlag(QGraphicsItem.ItemIsFocusable, False)

        #a place to display metadata
        self.metaDisplay = TransparentTextItem("", parent=self)
        self.metaDisplay.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.metaDisplay.setFlag(QGraphicsItem.ItemIsFocusable, False)
        #populate it
        self.setMetadataDisplay()

        #Create the graphical line
        #PointList to pass to polyLine
        if len(points) > 0:
            ptList = [self.startNode[1].scenePos()] + points + [self.endNode[1].scenePos()]
        else: #just start with a 2-pt line
            ptList = [self.startNode[1].scenePos(),self.endNode[1].scenePos()]
        #Track what sort of edge this one is
        self._polyEdge = polyLineType
        if self._polyEdge == STRAIGHT:
            self.edgeLine = StraightLineItem(ptList,parent=self)
        else: #Assume spline! Error checking later!
            #If no tangents given, and start/end are on a blob, make tangent at right angles to blob
            if len(tangents) == 0:
                #Orthogonal to `nodeshape` at `point`
                startSlope = self.startNode[1].orthogonalSlope()
                endSlope =  self.endNode[1].orthogonalSlope()
                tgtScaleFactor = 30 #TODO: Make this a global constant (also used in PolyLineItem)
                tangents = [(QPointF(0,0),  
                             QPointF(startSlope[0] * tgtScaleFactor, startSlope[1] * tgtScaleFactor))]

                tangents.append((QPointF(-endSlope[0] * tgtScaleFactor,-endSlope[1] * tgtScaleFactor), 
                                QPointF(0,0)))

            self.edgeLine = HermiteSplineItem(p=ptList,t=tangents,parent=self)

        #Stop Python GC from mangling things on delete (It seems this ref is not critical)
        self.edgeLine.setData(KEY_ROLE,ROLE_POLYLINE)
        self.edgeLine.my_parent_item = self

        #self.edgeLine.setPen(noPen)
        self.edgeLine.setFlag(QGraphicsItem.ItemIsSelectable, False)
        
        #Add in the arrowhead for digraph
        #TODO: Should this not only be in paint(), to update dynamically? updateLine() might be the place?
        if directed == '':
            self.isDirected = self.model.isDigraph
        else:
            #self.isDirected = directed == 'true'  JH
            self.isDirected=directed

        if self.isDirected:
            self.endShape = ArrowHeadItem(size=NODESIZE/2, parent=self)
        else:
            self.endShape = None

        self.bRect =self.edgeLine.boundingRect()

        #Link up the topology for the visual graph.
        sItem[0].startsEdges.append(self)
        sItem[1].startsEdgeLines.append(self)  #JH duplicate this for now
        self.setStart(sItem)
        eItem[0].endsEdges.append(self)
        eItem[1].endsEdgeLines.append(self)    #JH duplicate this for now
        self.setEnd(eItem)

        #Selection and editing vars:
        #edit Handles
        self.stH = None
        self.endH = None
        self.setFlags(self.GraphicsItemFlag.ItemSendsScenePositionChanges)
        #V00: Set edges to only move via nodes.
        #Needs to be selectable to edit name/ show in list.
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, False) #Moving done via enditems/ handles
        self.setZValue(0)
        self.setAcceptHoverEvents(True)
        self.isHovered=False
        #self._hoverColor = QColor("red")
        self._baseColor = DRAWING_COLOUR
        self._hoverColor = HOVER_COLOUR
        self._selectColor = SELECT_COLOUR
        #Checking if this was why there were ghosts
        #self.setCacheMode(QGraphicsItem.NoCache)
        
        #is this the only edge selected (used for rerouting)
        self.isOnlySelected = False
        #disable the guard
        self.suppressItemChange = False  # enable itemChange normally

    def __repr__(self):
        return f"\n>> VisEdgeItem {super().__repr__()}\n {self.textItem.toPlainText() =}\n edgeLines {[(eL.lineNum,hex(id(eL))) for eL in self.edgeLines] }\n" + \
                        f"ID: {self.edgeNum} text:{self.textItem.toPlainText()} s:({[(sN[0].data(KEY_INDEX),sN[1].index) for sN in self.startNodes]})" + \
                        f" e:({[(sN[0].data(KEY_INDEX),sN[1].index) for sN in self.endNodes]}))\n<<"

    def toXML(self,Xparent):
        """ add an Element Tree node to the XML parent node with the Edge Data 
            This uses the yEd names for line types for compatibility
        """
        xmlEdge = ET.Element(
            "edge",
            id=str(self.edgeNum),
            source=str(self.startNode[0].nodeNum),
            target=str(self.endNode[0].nodeNum),
            sourceport=str(self.startNode[1].index),
            targetport=str(self.endNode[1].index)
        )
        if self.isDirected: 
            xmlEdge.set("directed", "true")     
        else:
            xmlEdge.set("directed", "false") 

        data = ET.SubElement(xmlEdge, "data", key="data_edge")
        if self._polyEdge == STRAIGHT:
            pl = ET.SubElement(data, "y:PolyLineEdge")
        else:
            pl = ET.SubElement(data, "y:QuadCurveEdge")

        if self.isDirected: 
            ET.SubElement(pl, "y:Arrows", {'source':"none", 'target':"standard"})  

        #Add in the points   
        points = self.edgeLine._p
        if len(points) > 0:
            path = ET.SubElement(pl,"y:Path ") #No ports yet
            pathElts = []
            for p in points[1:-1]:
                pathElts.append(ET.SubElement(path, "y:Point", {"x":str(p.x()),"y":str(p.y())}))
            #Tangents 
            if self._polyEdge == SPLINE:
                tangents = self.edgeLine._t

                if len(tangents) > 0:
                    ET.SubElement(path,"h:StartTangent", {"x":str(tangents[0][1].x()),
                                                          "y":str(tangents[0][1].y())})
                    for i,pElt in enumerate(pathElts):
                        ET.SubElement(pElt,"h:Tangent",
                                            {"leftx":str(tangents[i+1][0].x()), "lefty":str(tangents[i+1][0].y()), 
                                             "rightx":str(tangents[i+1][1].x()),"righty":str(tangents[i+1][1].y())})

                    ET.SubElement(path,"h:EndTangent", {"x":str(tangents[-1][0].x()),"y":str(tangents[-1][0].y())})


        #TODO: Refactor edge save/ load code to not use edgeLabel as `name` - do it all in metadata
        label = ET.SubElement(pl, "y:EdgeLabel")
        label.text = self.metadata['name']
        for atK,atV in self.metadataAttributes['name'].items():
            metaAtt = ET.SubElement(label, "h:metadataAttribute", {"key":atK,"value":str(atV)})

        #add metadata other than name
        if len(self.metadata) >= 2:
            for k, v in self.metadata.items():
                if k != "name":
                    metaEl  = ET.SubElement(xmlEdge, "h:metadata", {"key":k,"value":str(v)})
                    for atK,atV in self.metadataAttributes[k].items():
                        metaAtt = ET.SubElement(metaEl, "h:metadataAttribute", {"key":atK,"value":str(atV)})


        return xmlEdge
        
    def setMetadataDisplay(self):
        metaStr = ''
        for k,v in self.metadata.items():
            if k != 'name':
                if self.metadataAttributes[k]['display']:
                    metaStr += "\n"+k +":"+v
        self.metaDisplay.setPlainText(metaStr)

    def boundingRect(self):
        """ edges boundingRect """
        adjust = 2 # self.pen.width() / 2
        return self.childrenBoundingRect().adjusted(-adjust, -adjust, adjust, adjust)

    def paint(self, painter, option, widget=None):
        #print(f" Paint {self.edgeNum =}")
        #painter.setPen(Qt.red)
        #painter.drawRect(self.bRect)
        #use the textBRect to adjust exact display position on the line (can be a [0,1] multiplier)
        textBRect = self.textItem.boundingRect()
        midPt = self.edgeLine.textPos(0.5)
        #painter.drawEllipse(midPt,2,2)
        self.textItem.setPos(midPt.x() - textBRect.width()/2  + NODESIZE/2, \
                             midPt.y() - textBRect.height()/2 + NODESIZE/2)
        self.metaDisplay.setPos(self.textItem.pos()+QPointF(0,0))
        #painter.drawRect(self.textItem.boundingRect())
       
        if self.isSelected():
            painter.setPen(QPen(self._selectColor,1,Qt.DashLine))
            self.textItem.setDefaultTextColor(self._selectColor)   
            self.metaDisplay.setDefaultTextColor(self._selectColor)
        elif self.isHovered:
            painter.setPen(QPen(self._hoverColor))
            self.textItem.setDefaultTextColor(self._hoverColor)   
            self.metaDisplay.setDefaultTextColor(self._hoverColor)
        else:
            painter.setPen(self._baseColor)
            self.textItem.setDefaultTextColor(self._baseColor)
            self.metaDisplay.setDefaultTextColor(self._baseColor)

        #TODO: Move this to itemChanged?
        self.textItem.setVisible(self.metadataAttributes['name']['display'])

        #self.edgeLine.paint(painter,option,widget)

        #painter.drawText(QPoint(0,0),self.textItem.toPlainText())
        #painter.drawText(tPos,self.dispText) #textItem.toPlainText())

        #Debug - draw the shape path
        #painter.drawPath(self.shape())

    def shape(self):
        """ Set a tight selection shape """
        path = self.edgeLine.shape()

        #Text
        path.addRect(self.textItem.boundingRect().translated(self.textItem.pos()))

        outlinePath = QPainterPathStroker()
        outlinePath.setWidth(HITSIZE*2)
        return outlinePath.createStroke(path)

    """def mousePressEvent(self, mouseEvent):
        if (mouseEvent.button() == Qt.MouseButton.LeftButton):

            modifiers = mouseEvent.modifiers()
            #TODO: Handle shift & ctrl click properly. 
            #TODO: Should this be here, or in Scene.mousePress???
            #if not (modifiers & Qt.ShiftModifier or modifiers & Qt.ControlModifier) and \
            #    not self.isSelected():
            if not self.isSelected():
                self.scene().clearEdgeOnly(self)
                self.scene().clearSelection()
                
            self.setSelected(True)
            #Highlight the list item as well
            #print(f"\nSelected elt: {self.data(KEY_INDEX)}\n")
            lWItem = self.listWidget.findItemByIdx(self.data(KEY_INDEX))
            self.listWidget.setCurrentItem(lWItem)"""

    def mouseDoubleClickEvent(self, mouseEvent):
        self.requestEdit.emit(self)
        mouseEvent.accept()

    def hoverEnterEvent(self, event):
        self.isHovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.isHovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        #print(f"edge item change {change},{value}")
        #guard clause to trap calls from __init__
        if not self.suppressItemChange:
            #if change == QGraphicsItem.ItemSelectedHasChanged:
            if change in [QGraphicsItem.ItemSelectedHasChanged, QGraphicsItem.ItemScenePositionHasChanged]:
                #print(f"Selected Edge {self.dispText} ")
                #Select the children
                for child in self.childItems():
                    child.setSelected(value)

            # Change the display text - what would the <change> be? Using ToolTip as the closest
            #TODO: Fix the `change` value to something more meanigful
            if change == QGraphicsItem.GraphicsItemChange.ItemToolTipChange:
                self.textItem.setPlainText(self.model.Gr.edgeD[self.edgeNum].metadata['name'] )
        
        return super().itemChange(change, value)

    def setPolylineType(self, lineType:int):
        """set and change _polyEdge """

        if self._polyEdge != lineType:
            self._polyEdge = lineType
            ptList = self.edgeLine._p
            self.edgeLine._deleteHandles() 
            self.scene().removeItem(self.edgeLine) 
            del self.edgeLine 
            #self.edgeLine.my_parent_item = None
            #if self.isOnlySelected:
            #    self.scene().clea#rEdgeOnly(self)
            if self._polyEdge == STRAIGHT:
                self.edgeLine = StraightLineItem(ptList,parent=self) 
            elif self._polyEdge == SPLINE:
                self.edgeLine = HermiteSplineItem(ptList,parent=self)

            self.edgeLine.setData(KEY_ROLE,ROLE_POLYLINE)
            self.edgeLine.my_parent_item = self
            self.edgeLine.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.setSelected(False)
            self.scene().thisHandleObjectSelected=None
            self.updateLine()

    def setDirected(self, isDirected:bool):
        """ set is driected, add/ remove arrow"""
    
        if self.isDirected != isDirected:
            self.isDirected = isDirected
            if isDirected:  #restore the arrow
                self.endShape = ArrowHeadItem(size=NODESIZE/2, parent=self)
            else:
                #Note, previous endShape dereference should delete it
                self.scene().removeItem(self.endShape)
                self.endShape = None
            self.updateLine()
                

    #From musicamente's SO post   
    # These are to setup the initial edge, which will always start out as a 2 pt edge. 
    #TODO: Polylines will allow creation of multi-point lines up front - change rubberline to use a polyline

    def setStart(self, start):
        """ Set the startItem to start, a (Node,Port) tuple. Also update model, for edits"""
        self.startNode = start
        #Set the port startsLines
        #self.edgeLine.setP(0,start.scenePos())
        self.updateLine(start)

    def setEnd(self, end):
        #TODO: Add updateEdge() to Graph class, then include here??
        self.endNode = end
        #self.edgeLine.setP(-1,end.scenePos())
        self.updateLine(end)

    def updateLine(self, source=None):
        """ Tell Qt the ends have moved. source:tuple(Node,port) = None allows an arrow recalc without point change"""
        self.prepareGeometryChange()
        #TODO: For hypergraphs, start/ end may be a point on a PolyLine
        #When called from VisNodeItem.itemChange, source is pure VisNode, not a tuple

        #print(f"updateLine called with {type(source)=}")
        #print(traceback.print_stack())
        #source may be a `Handle`, which a not a tuple, or just a Node: Normalise to tuple
        if not type(source) is tuple: 
            if type(source) is VisNodeItem or type(source) is VisBlobItem:
                # Search for the correct port
                if source == self.startNode[0]: #Start
                    for p in source._Ports:
                        if p == self.startNode[1]:
                            source = (source,p)
                else: #end
                    for p in source._Ports:
                        if p == self.endNode[1]:
                            source = (source,p)

            if  type(source) is HandleItem:
                #print(f"Making Handle into a tuple")
                source = (0,source)
        
        if source == self.startNode:
            #Set the 0th edgeLine point to where the `source` object port (now) is. 
            #print(f"setting start from {source[0].nodeNum}, {source[1].index}")
            #print("updateLine start withOUT t")
            self.edgeLine.setP(0,source[1].scenePos())

        elif source == self.endNode: #endNode
            #print(f"setting end from {source[0].nodeNum}, {source[1].index}")
            #print("updateLine end withOUT t")
            self.edgeLine.setP(-1,source[1].scenePos())

        #Draw the arrow/ end shape
        if self.endShape:
            self.endShape.prepareGeometryChange()
            # Compute rotation angle
            angle_deg = self.edgeLine.endAngle()
            self.endShape.setRotation(angle_deg)
            self.endShape.setPos(self.edgeLine._p[-1])
        #If needed move all the polyline points - updatePath handles this.
        self.edgeLine.updatePath()

###################################################################################################################

class VisHyperEdgeItem(QGraphicsObject): 
    """ Create a new Hyperedge - both Graph Model and Visual ("graphics")
      This connects visual edges to model and list
      This DOES NOT inherit from VisEdgeItem - there are too many deep changes.
    """
    #Create the signal for editing
    requestEdit = Signal(object)  

    def __init__(self,model, Scene, treeWidget,sItem, eItem, directed='', parent=None, nameP="", id=None,
                    polyLineType = DEFAULT_EDGE, points=[],tangents=[],metadata={}, metadataAttributes={},
                    dummyNodes=None,edgeLines=None, hyperEdgeGraph=None):

        """ Create a visual edge, using the pos of the st and end items, which are tuples of (Node,Port)
            points must be QPointFs and tangents must be tuples of QPointFs, relative to the points
            When created from XML, points will be empty (should?), dummyNodes & edgeLines pre-populated for linking up.
            The hyperEdgeGraph is only used to reconstruct at load, and not stored.
        """
        #TODO: Check - points may be redundant with hyperEdges
        super().__init__(parent)
        self.suppressItemChange = True  # suppress itemChange until all attribs set.

        self.Scene = Scene
        self.model = model
        self.treeWidget = treeWidget

        #A hyperedge may have _many_ start and end nodes, or just 1 of each - normalise to lists here.
        #Hyper Step 1: just make this work with 1 elt lists of start/ end
        if type(sItem) is list:
            self.startNodes = sItem
        else:
            self.startNodes = [sItem]

        if type(eItem) is list:
            self.endNodes = eItem
        else:
            self.endNodes = [eItem]

        #Store the edgeLines aka segments (>1 for hyperEdges) 
        #NOTE! parameter edgeLine (and dummyNode) is mutable, and will store previous call values
        self.edgeLines = [] if edgeLines is None else edgeLines
        
        #List of the intermediate, dummy nodes needed to graphical contruct the hyper edge 
        self.dummyNodes = [] if dummyNodes is None else dummyNodes

        #option to set a default name. 
        defName = "" #just the ID

        #Create an abstract edge, and keep the index as well
        #Simple edge
        
        #these should have two indices one for list one for tuple  JH (maybe procedure sorts it out?). ok
        #but for now it is not a list, so it's ok
        #THere is always a simple edge to start
        self.edge,self.edgeNum = self.model.addGMEdge(self.startNodes[0][0],
                                                    self.endNodes[0][0],nameP = defName,id=id)
        if len(self.startNodes) > 1 or len(self.endNodes) > 1:
            #deal with creation of hyperedge from passed in lists.

            #add each additional start
            for s in self.startNodes[1:]:
                self.model.Gr.addEdge(s[0].data(KEY_INDEX), self.edge.data(KEY_INDEX))
            #add each additional end
            for e in self.endNodes[1:]:
                self.model.Gr.addEdge(self.edge.data(KEY_INDEX),e[0].data(KEY_INDEX))

        
        # self.metadata is just a more elegant wrapper
        self.metadata = self.model.Gr.edgeD[self.edgeNum].metadata
        #"deep copy" the dict
        for k,v in metadata.items():
            self.metadata[k] = v
        #initialise metadataAttributes if not passed in:
        if len(metadataAttributes) > 0:
            self.metadataAttributes = metadataAttributes
        else:
            self.metadataAttributes = {'name':{'display':DISPLAY_NAME_BY_DEFAULT}}

        #TODO: This overwrites in metadata['name'] value, but it should be the same?
        #self.model.Gr.edgeD[self.edgeNum].metadata.update({'name':f"{self.edgeNum} {self.model.Gr.edgeD[self.edgeNum].metadata['name']}"})
        self.metadata['name'] = f"{self.edgeNum} {self.metadata['name']}"
        if nameP:
            #self.edge,self.edgeNum = self.model.addGMEdge(sItem,eItem,nameP=nameP)
            self.metadata['name'] = nameP
                
        #add to the text list
        #TODO: Should this not be driven from the model?
        tWitem = QTreeWidgetItem([self.model.Gr.edgeD[self.edgeNum].metadata['name'],str(self.edgeNum)])
        tWitem.setIcon(2, Scene.mainwindow.EDGE_ICON)
        tWitem.setData(0, KEY_INDEX,self.edgeNum)
        tWitem.setData(0, KEY_ROLE,ROLE_EDGE)
        self.treeWidget.addTopLevelItem(tWitem)

        #Used to switch off built in drawing
        noPen = QPen(Qt.NoPen)

        #Non-display data, for referencing to model and listView
        self.setData(KEY_INDEX, self.edgeNum)
        #TODO: leaving as ROLE_EDGE in initial development, but update to ROLE_HYPEREDGE???
        self.setData(KEY_ROLE, ROLE_EDGE) 

        #Draw name in the middle
        #self.textItem = QGraphicsTextItem(self.model.Gr.edgeD[self.edgeNum].metadata['name'], parent=self)
        # chatGPT's suggestion to avoid shape() not selecting it - TransparentTextItem
        self.textItem = TransparentTextItem(self.metadata['name'], parent=self) 

        self.textItem.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.textItem.setFlag(QGraphicsItem.ItemIsFocusable, False)

        #a place to display metadata
        self.metaDisplay = TransparentTextItem("", parent=self)
        self.metaDisplay.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.metaDisplay.setFlag(QGraphicsItem.ItemIsFocusable, False)
        #populate it
        self.setMetadataDisplay()

        #Create the graphical lines

        #directed edge?
        if directed == '':
            self.isDirected = self.model.isDigraph
        else:
            self.isDirected=directed
        
        #this will create the necessary arrows - needed before `setStart` is called
        #Add in the arrowhead for digraph
        self.endShape = []
        if self.isDirected:
            #Every endNode end will need an arrowhead
            for e in self.endNodes:
                #print(f"he add arrow {e[0].nodeNum}=")
                #pos & details are set in `updateLine`. Additional endShapes created in addSegment
                self.endShape.append(ArrowHeadItem(size=NODESIZE/2, parent=self))


        #Track what sort of edge this one is
        self._polyEdge = polyLineType   
        self.tgtScaleFactor = TANGENT_SCALE_FACTOR 
     
        #Simple edge, created interactively (no hyperEdgeGraph, which is _only_ created in `fromXML`)
        if len(self.startNodes) == 1 and len(self.endNodes) == 1 and hyperEdgeGraph is None:
            #print(f"he: simple creation {len(dummyNodes)=}")
            stN = self.startNodes[0]
            endN = self.endNodes[0]
            if len(points) == 0: #just start with a 2-pt line from the port coords
                ptList = [stN[1].scenePos(),endN[1].scenePos()]
            else: #Wrap the intermediate points with the start & end port position
                ptList = [stN[1].scenePos()] + points + [endN[1].scenePos()]

            if self._polyEdge == STRAIGHT:
                self.edgeLines.append(StraightLineItem(ptList,parent=self))
            else: #Assume spline! Error checking later!
                #If no tangents given, and start/end are on a blob, make tangent at right angles to blob
                #The spline constructor default doesn't (can't) do the orthogonal tangents. Do them here.
                if len(tangents) == 0:
                    #Orthogonal to `nodeshape` at `point`
                    startSlope = self.startNodes[0][1].orthogonalSlope()
                    endSlope =  self.endNodes[0][1].orthogonalSlope()
                    tangents = [(QPointF(0,0),  
                                QPointF(startSlope[0] * self.tgtScaleFactor, startSlope[1] * self.tgtScaleFactor))]

                    tangents.append((QPointF(-endSlope[0] * self.tgtScaleFactor,-endSlope[1] * self.tgtScaleFactor), 
                                    QPointF(0,0)))

                self.edgeLines.append(HermiteSplineItem(p=ptList,t=tangents,parent=self))
            
            #Link up the topology for the visual graph - tell the start & end nodes about the edge
            #Initially, there will only be one edgeLine ([0]) per edge. Others added one by one.
            for stN in self.startNodes: #Loops are redundant - handled in hyperedge else:
                stN[0].startsEdges.append(self) #NODE
                #Tell the Port too.
                stN[1].startsEdgeLines.append(self.edgeLines[0]) 
                self.setStart(stN, self.edgeLines[0])
            for endN in self.endNodes:
                endN[0].endsEdges.append(self) #NODE
                #Port
                endN[1].endsEdgeLines.append(self.edgeLines[0]) 
                self.setEnd(endN, self.edgeLines[0])
            
        else: #Created from XML
            #If we are _creating_ an n-ary edge, it must be from a file/ clipboard, 
            # so `points`, `tangents` & dummyNodes will be populated, 
            # and instantiated in edgeLines, with hyperEdgeGraph holding the structure.
            
            #print(f"HE init: sItem {[d[0].nodeNum for d in sItem]}") 
            #print(f"HE init: eItem {[d[0].nodeNum for d in eItem]}") 
            #print(f"HE init: dummyNodes { [(d[0].nodeNum, [el.lineNum for el in d[0].startsEdgeLines], [el.lineNum for el in d[0].endsEdgeLines]) for d in dummyNodes]}") 
            #print(f"HE init: edgelines: {[e.lineNum for e in edgeLines]}")
            #print(f"HE init: hyperEdgeGraph {hyperEdgeGraph}")
            #For each edgeLine, tell the start and end nodes. NOTE: dummyNodes are connected already in fromXML()

            for eL,eLNodes in hyperEdgeGraph.items():
                #print(f"heGr  eL {eL.lineNum}, ({eLNodes[0][0].nodeNum}, {eLNodes[0][1].nodeNum}),({eLNodes[1][0].nodeNum}, {eLNodes[1][1].nodeNum}) ")
                if eLNodes[0][0].data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                    #print(f"    sItem {eL.lineNum}, ({eLNodes[0][0].nodeNum}, {eLNodes[0][1].index})")
                    stN = eLNodes[0] #tuple of (node,port)
                    stN[0].startsEdges.append(self)
                    stN[1].startsEdgeLines.append(eL)
                    #Why does this not crash, since end is not yet set???
                    self.setStart(stN, eL)
                if eLNodes[1][0].data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                    #print(f"    eItem {eL.lineNum}, ({eLNodes[1][0].nodeNum}, {eLNodes[1][1].index})")
                    endN = eLNodes[1] #tuple of (node,port)
                    endN[0].endsEdges.append(self)
                    endN[1].endsEdgeLines.append(eL)
                    self.setEnd(endN, eL)   
            #Now set the parenting
            for d in self.dummyNodes:
                d[0].setParentItem(self)
            for e in self.edgeLines:
                e.setParentItem(self)
        """
        print(f"he init checking port endlines")
        for d in self.endNodes:
            print(f" endNode  {d[0].nodeNum} port {d[1].index}")
            for e in d[0].startsEdges:
                print(f"   starts Edge {e.edgeNum}")
            for e in d[0].endsEdges:
                print(f"   ends Edge {e.edgeNum}")            
            #print(f"  endNode  {d[0].nodeNum} port {d[1].index}")
            for e in d[1].startsEdgeLines:
                print(f"   starts eLine {e.lineNum}")
            for e in d[1].endsEdgeLines:
                print(f"   ends eLine {e.lineNum}")
        """
        #Bounding rectangle
        self.bRect = QRectF(0,0,0,0) #initial bounding rectangle
        for edgeLine in self.edgeLines:
            edgeLine.setData(KEY_ROLE,ROLE_POLYLINE)
            edgeLine.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.bRect = self.bRect.united(edgeLine.boundingRect())

        #Selection and editing vars:
        #TODO: will need a list of st & end handles
        #edit Handles
        self.stH = None
        self.endH = None

        self.setFlags(self.GraphicsItemFlag.ItemSendsScenePositionChanges)
        #Needs to be selectable to edit name/ show in list.
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, False) #Moving done via enditems/ handles
        self.setZValue(0)
        self.setAcceptHoverEvents(True)
        self.isHovered=False
        self._baseColor = DRAWING_COLOUR
        self._hoverColor = HOVER_COLOUR
        self._selectColor = SELECT_COLOUR
        
        #is this the only edge selected (used for rerouting)
        self.isOnlySelected = False
        #disable the guard
        self.suppressItemChange = False  # enable itemChange normally

    def __repr__(self):
        #TODO: fix for hyperedges
        #return f"\n>> VisHyperEdgeItem {hex(id(self))} {super().__repr__()}\nID: {self.edgeNum} text:{self.textItem.toPlainText()} edgelines = {[e.lineNum for e in self.edgeLines]}\ns:({self.startNodes[0][0].data(KEY_INDEX)}, {self.startNodes[0][1].index})" + \
        #        f" e:({self.endNodes[0][0].data(KEY_INDEX)}, {self.endNodes[0][1].index})\ndummyNodes = {[d.nodeNum for d in self.dummyNodes[0]]}\n <<"
        dummyNodeEdgeLines = []
        for dN in self.dummyNodes:
            dummyNodeEdgeLines.append([dN[0].nodeNum, "S: "])
            for e in dN[0].startsEdgeLines:
                dummyNodeEdgeLines.append(e.lineNum)
            dummyNodeEdgeLines.append("  E:")
            for e in dN[0].endsEdgeLines:
                dummyNodeEdgeLines.append(e.lineNum)

        return f"\n>> VisHyperEdgeItem {hex(id(self))} {super().__repr__()}\n {self.textItem.toPlainText() =}\n edgeLines {[eL.lineNum for eL in self.edgeLines] }\n" + \
                        f"ID: {self.edgeNum} text:{self.textItem.toPlainText()} startNodes (node,port):({[(sN[0].nodeNum,sN[1].nodeNum) for sN in self.startNodes]})\n endNodes (node,port):({[(N[0].nodeNum,N[1].nodeNum) for N in self.endNodes]}))\ndummyNodes {[d[0].nodeNum for d in self.dummyNodes]} {dummyNodeEdgeLines=}\n<<"
                #hyperEdgeGraph: {[(h[0][0].nodeNum,h[1][0].nodeNum) for h in self.hyperEdgeGraph]
    
    def toXML(self,Xparent):
        """ add an Element Tree node to the XML parent node with the Edge Data
        """
        xmlEdge = ET.Element(
            "hyperedge",
            id=str(self.edgeNum)   )
        
        if self.isDirected: 
            xmlEdge.set("directed", "true")     
        else:
            xmlEdge.set("directed", "false") 
        if self.isDirected: #subelement or just a property? 
            ET.SubElement(xmlEdge, "y:Arrows", {'source':"none", 'target':"standard"})  

        if self._polyEdge == STRAIGHT:
            xmlEdge.set("lineType", "Straight")
        else:
            xmlEdge.set("lineType", "Spline")

        #Build  edgeLine:start and edgeEdline:end dictionaries for saving edge start/ ends
        hStarts = {} # dict 
        hEnds = {} # dict
        nL = ET.SubElement(xmlEdge,"h:nodeList")
        for n in self.startNodes:
            ET.SubElement(nL,"start" , 
                 source= str(n[0].nodeNum),
                 sourceport=str(n[1].index)  )
            #store the start (node,port) for the edgeLine (end is not yet defined)
            hStarts.update({n[1].startsEdgeLines[0].lineNum : (n[0].nodeNum, n[1].index)})

        for n in self.endNodes:
            ET.SubElement(nL,"end",
                 target = str(n[0].nodeNum),
                 targetport=str(n[1].index) )
            #Update the 'end' tuple
            #print(f"he toX endNode {n[0].nodeNum} port {n[1].index} {len(n[1].endsEdgeLines)=}")
            hEnds.update({n[1].endsEdgeLines[0].lineNum : (n[0].nodeNum, n[1].index)})
        
        dL = ET.SubElement(xmlEdge,"h:dummyNodeList")
        for n in self.dummyNodes:
            #Currently (Apr 2026) dummyNodes don't have ports dN[0] = dN[1]
            dNElt = ET.SubElement(dL,"dummyNode", id=str(n[0].nodeNum), x=str(n[0].pos().x()),y=str(n[0].pos().y()) )
            for eL in n[0].startsEdgeLines:
                ET.SubElement(dNElt, "startsEdgeLine", eL=str(eL.lineNum))
                hStarts.update({eL.lineNum : (n[0].nodeNum, n[1].nodeNum)})
            for eL in n[0].endsEdgeLines:
                ET.SubElement(dNElt, "endsEdgeLine", eL=str(eL.lineNum))
                hEnds.update({eL.lineNum  : (n[0].nodeNum, n[1].nodeNum)})
        
        #the hyperEdge graph - a comment, to aid debugging. Data needed is in the edgeLine element
        #print(f"hyperEdge {self.edgeNum} {hStarts.items()} , {hEnds.items()}")
        hEdgeGraph = dict()
        for k,v in hStarts.items():
            hEdgeGraph.update({k:(v,hEnds[k])})
        #print(f"hyperEdge {hEdgeGraph}")
        comment = ET.Comment(f"hyperEdge {hEdgeGraph}")

        #Add the edgelines
        eLL = ET.SubElement(xmlEdge,"h:edgeLineList")
        eLL.append(comment)

        for eL in self.edgeLines:
            #edgeLine id=<eLineID> source=<nID> sourceport=<portID> target=<nID> targetport=<portID>
            eLelt =  ET.SubElement(eLL,"edgeLine", id=str(eL.lineNum), 
                                source=str(hStarts[eL.lineNum][0]), sourceport=str(hStarts[eL.lineNum][1]), 
                                target=str(hEnds[eL.lineNum][0]), targetport=str(hEnds[eL.lineNum][1])  )
            #Add in the points   
            points = eL._p
            if len(points) > 0:
                path = ET.SubElement(eLelt,"y:Path ") #No ports yet
                pathElts = []
                for p in points[1:-1]:
                    pathElts.append(ET.SubElement(path, "y:Point", {"x":str(p.x()),"y":str(p.y())}))
                #Tangents 
                if self._polyEdge == SPLINE:
                    tangents = eL._t

                    if len(tangents) > 0:
                        ET.SubElement(path,"h:StartTangent", {"x":str(tangents[0][1].x()),
                                                            "y":str(tangents[0][1].y())})
                        for i,pElt in enumerate(pathElts):
                            ET.SubElement(pElt,"h:Tangent",
                                                {"leftx":str(tangents[i+1][0].x()), "lefty":str(tangents[i+1][0].y()), 
                                                "rightx":str(tangents[i+1][1].x()),"righty":str(tangents[i+1][1].y())})

                        ET.SubElement(path,"h:EndTangent", {"x":str(tangents[-1][0].x()),"y":str(tangents[-1][0].y())})


        #TODO: Refactor edge save/ load code to not use edgeLabel as `name` - do it all in metadata
        #label = ET.SubElement(pl, "y:EdgeLabel")
        #label.text = self.metadata['name']
        #for atK,atV in self.metadataAttributes['name'].items():
        #    metaAtt = ET.SubElement(label, "h:metadataAttribute", {"key":atK,"value":str(atV)})

        #add metadata (including than name)
        if len(self.metadata) >= 1:
            for k, v in self.metadata.items():
                metaEl  = ET.SubElement(xmlEdge, "h:metadata", {"key":k,"value":str(v)})
                for atK,atV in self.metadataAttributes[k].items():
                    metaAtt = ET.SubElement(metaEl, "h:metadataAttribute", {"key":atK,"value":str(atV)})

        return xmlEdge
        
    def setMetadataDisplay(self):
        metaStr = ''
        for k,v in self.metadata.items():
            if k != 'name':
                if self.metadataAttributes[k]['display']:
                    metaStr += "\n"+k +":"+v
        self.metaDisplay.setPlainText(metaStr)

    def boundingRect(self):
        """ edges boundingRect """
        adjust = 2 # self.pen.width() / 2
        return self.childrenBoundingRect().adjusted(-adjust, -adjust, adjust, adjust)

    def paint(self, painter, option, widget=None):
        #print(f" Paint {self.edgeNum =}")
        #painter.setPen(Qt.red)
        #painter.drawRect(self.bRect)
        #use the textBRect to adjust exact display position on the line (can be a [0,1] multiplier)
        textBRect = self.textItem.boundingRect()
        #HACK: Putting the text at the middle of the first segment. Where should it go?
        #  This code should be in itemChanged, not paint
        midPt = self.edgeLines[0].textPos(0.5)
        #painter.drawEllipse(midPt,2,2)
        self.textItem.setPos(midPt.x() - textBRect.width()/2  + NODESIZE/2, \
                             midPt.y() - textBRect.height()/2 + NODESIZE/2)
        self.metaDisplay.setPos(self.textItem.pos()+QPointF(0,0))
        #painter.drawRect(self.textItem.boundingRect())
       
        if self.isSelected():
            painter.setPen(QPen(self._selectColor,1,Qt.DashLine))
            self.textItem.setDefaultTextColor(self._selectColor)   
            self.metaDisplay.setDefaultTextColor(self._selectColor)
        elif self.isHovered:
            painter.setPen(QPen(self._hoverColor))
            self.textItem.setDefaultTextColor(self._hoverColor)   
            self.metaDisplay.setDefaultTextColor(self._hoverColor)
        else:
            painter.setPen(self._baseColor)
            self.textItem.setDefaultTextColor(self._baseColor)
            self.metaDisplay.setDefaultTextColor(self._baseColor)

        #TODO: Move this to itemChanged?
        self.textItem.setVisible(self.metadataAttributes['name']['display'])

        #self.edgeLine.paint(painter,option,widget)

        #painter.drawText(QPoint(0,0),self.textItem.toPlainText())
        #painter.drawText(tPos,self.dispText) #textItem.toPlainText())

        #Debug - draw the shape path
        #painter.drawPath(self.shape())

    def shape(self):
        """ Set a tight selection shape """
        path = QPainterPath()
        for eL in self.edgeLines:
            path.addPath(eL.shape())

        #Text
        path.addRect(self.textItem.boundingRect().translated(self.textItem.pos()))

        outlinePath = QPainterPathStroker()
        outlinePath.setWidth(HITSIZE*2)
        return outlinePath.createStroke(path)
    
    def _createHandles(self):
        for line in self.edgeLines:
            line._createHandles()
        return

    def _deleteHandles(self):
        for line in self.edgeLines:
            line._deleteHandles()
        return
    
    """def mousePressEvent(self, mouseEvent):
        if (mouseEvent.button() == Qt.MouseButton.LeftButton):

            modifiers = mouseEvent.modifiers()
            #TODO: Handle shift & ctrl click properly. 
            #TODO: Should this be here, or in Scene.mousePress???
            #if not (modifiers & Qt.ShiftModifier or modifiers & Qt.ControlModifier) and \
            #    not self.isSelected():
            if not self.isSelected():
                self.scene().clearEdgeOnly(self)
                self.scene().clearSelection()
                
            self.setSelected(True)
            #Highlight the list item as well
            #print(f"\nSelected elt: {self.data(KEY_INDEX)}\n")
            lWItem = self.listWidget.findItemByIdx(self.data(KEY_INDEX))
            self.listWidget.setCurrentItem(lWItem)"""

    def mouseDoubleClickEvent(self, mouseEvent):
        self.requestEdit.emit(self)
        mouseEvent.accept()

    def hoverEnterEvent(self, event):
        self.isHovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self.isHovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        #print(f"edge item change {change},{value}")
        #guard clause to trap calls from __init__
        if not self.suppressItemChange:
            if change == QGraphicsItem.ItemSelectedHasChanged:
            #if change in [QGraphicsItem.ItemSelectedHasChanged, QGraphicsItem.ItemScenePositionHasChanged]:
                #print(f"Selected Edge {self.dispText} ")
                #Select the children
                for child in self.childItems():
                    child.setSelected(value)

            # Change the display text - what would the <change> be? Using ToolTip as the closest
            #TODO: Fix the `change` value to something more meanigful
            if change == QGraphicsItem.GraphicsItemChange.ItemToolTipChange:
                self.textItem.setPlainText(self.model.Gr.edgeD[self.edgeNum].metadata['name'] )
        
        return super().itemChange(change, value)

    def setPolylineType(self, lineType:int):
        """ set and change _polyEdge to `lineType`
            deletes lines of old type (SPLINE / STRAIGHT), and replaces them with the new type
        """

        if self._polyEdge != lineType:
            self._polyEdge = lineType
            #grab the points from each edgeLine
            eLinePoints = []
            for e in self.edgeLines:
                eLinePoints.append(e._p)
                #self.edgeLine._deleteHandles() 
                e._deleteHandles() 
                #self.scene().removeItem(self.edgeLine) 
                e.setParentItem(None)
                self.scene().removeItem(e)
            #del self.edgeLine 
            #Don't delete them yet - we need their connections (heg to the rescue?)
            self.edgeLines.clear()

            #self.edgeLine.my_parent_item = None
            #if self.isOnlySelected:
            #    self.scene().clea#rEdgeOnly(self)
            #Rebuild as the new line type
            #What about dummyNodes, ports.startsLines, etc
            for ptList in eLinePoints:
                if self._polyEdge == STRAIGHT:
                    #self.edgeLine = StraightLineItem(ptList,parent=self) 
                    eL = StraightLineItem(ptList,parent=self) 
                elif self._polyEdge == SPLINE:
                    #self.edgeLine = HermiteSplineItem(ptList,parent=self)
                    eL = HermiteSplineItem(ptList,parent=self)

                #self.edgeLine.setData(KEY_ROLE,ROLE_POLYLINE)
                eL.setData(KEY_ROLE,ROLE_POLYLINE)
                #self.edgeLine.my_parent_item = self #TODO: Needed???
                #self.edgeLine.setFlag(QGraphicsItem.ItemIsSelectable, False)
                eL.setFlag(QGraphicsItem.ItemIsSelectable, False)
                self.edgeLines.append(e)

            self.setSelected(False)
            self.scene().thisHandleObjectSelected=None
            self.updateLine()

    def setDirected(self, isDirected:bool):
        """ set isDirected, add/ remove arrows """
    
        if self.isDirected != isDirected:
            self.isDirected = isDirected
            if isDirected:  #restore the arrow
                for e in self.endNodes:
                    if e[0].data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]: #Not on dummyNodes
                        self.endShape.append(ArrowHeadItem(size=NODESIZE/2, parent=self))
            else:
                #Note, previous endShape dereference should delete it
                for i in range(len(self.endShape)):
                    self.scene().removeItem(self.endShape[i])
                self.endShape.clear()
            self.updateLine()
                

    #From musicamente's SO post   
    # These are to setup the initial edge, which will always start out as a 2 pt edge. 
    #TODO: Polylines will allow creation of multi-point lines up front - change rubberline to use a polyline

    def setStart(self, start, edgeLine = None):
        """ Set the startItem to start, a (Node,Port) tuple. Also update model, for edits"""

        if not edgeLine:
            print("setStart: Setting edgeLine to [0]")
            traceback.print_stack(limit=3)
            edgeLine = self.edgeLines[0]

        #Hyperedge - add to the list of starts, if not already present. 
        if not start in self.startNodes:
            self.startNodes.append(start)
        #Set the port startsLines
        #self.edgeLine.setP(0,start.scenePos())
        self.updateLine(start,edgeLine)

    def setEnd(self, end, edgeLine = None):
        """ Set the end of self to end, a (Node,Port) tuple. Also update model, for edits""" 
         
         # call from old code, not a handle
        if not edgeLine and end[0].data(ROLE_KEY) not in [ROLE_NODE,ROLE_BLOB, ROLE_HANDLE]: #HACK: end[0] != end[1]:  
            print("setEnd: Setting edgeLine to [0]")
            traceback.print_stack(limit=3)
            edgeLine = self.edgeLines[0]

        #TODO: Add updateEdge() to Graph class, then include here?? (No, missing scene context?
        #node may not end the same edge twice
        if not end in self.endNodes:
            self.endNodes.append(end)
        #self.edgeLine.setP(-1,end.scenePos())
        self.updateLine(end, edgeLine)

    def updateLine(self, source=None, edgeLine = None):
        """ Tell Qt the ends have moved. 
            source is the (node,port) tuple which triggered the udpate. Only 1 node at a time will call.
            source = None allows an arrow recalc without point change
            Hyperedges can have >1 lines. Pass in the polyLine (edgeline) to update.
            This will link the line and the port
        """
        # late bound params `=>` not in p3.13 :(  
        #This is for backwards compatibility with simple edges - check later
        if not edgeLine:
            #print("**********updateLine - setting edgeLine to [0]")
            #traceback.print_stack(limit=3)
            edgeLine = self.edgeLines[0]
        #print(f" updateLine: {edgeLine.lineNum=}")

        self.prepareGeometryChange()
        #TODO: For hypergraphs, segment start/ end may be a dummyNode
        #For hyperedges, there are possibly multiple edgeLines

        #When called from VisNodeItem.itemChange, source is pure VisNode, not a tuple
        
        #print(f"updateLine called with {type(source)=}")
        #print(traceback.print_stack())
        #source may be a `Handle`, which a not a tuple, or just a Node: Normalise to tuple
        if not type(source) is tuple: 
            if type(source) is VisNodeItem or type(source) is VisBlobItem:
                # Search for the correct port
                if source == self.startNode[0]: #Start
                    for p in source._Ports:
                        if p == self.startNode[1]:
                            source = (source,p)
                            #print(f"setting start to {p.index=}")
                else: #end
                    for p in source._Ports:
                        if p == self.endNode[1]:
                            source = (source,p)
                            #print(f"setting end to {p.index=}")

            if  type(source) is HandleItem:
                #print(f"Making Handle into a tuple")
                #source = (source,source) #>> Don't do this - endNodes end up being set in odd places.
                source = (0,source)
        #print(f"{source=}  == {self.startNode=}")

        #############
        """if source and type(source[0] )== VisBlobItem and source[0]==self.startNode[0]\
                and source[1].t==self.startNode[1].t:
            self.edgeLine.setP(0,source[1].scenePos())
        elif source and type(source[0] )== VisBlobItem and source[0]==self.endNode[0]\
                and source[1].t==self.endNode[1].t:
            self.edgeLine.setP(-1,source[1].scenePos())
        elif source == self.startNode:
            #Set the 0th edgeLine point to where the `source` object port (now) is. 
            #print(f"setting start from {source[0].nodeNum}, {source[1].index}")
            self.edgeLine.setP(0,source[1].scenePos())

        elif source == self.endNode: #endNode
            #print(f"setting end from {source[0].nodeNum}, {source[1].index}")
            self.edgeLine.setP(-1,source[1].scenePos())"""

        ###########

        if source in self.startNodes:
            edgeLine.setP(0,source[1].scenePos())
        elif source in self.endNodes: #endNode
            #print(f"updateLine: setting end from node {source[0].nodeNum}, port {source[1].nodeNum} with endLines {[eL.lineNum for eL in source[1].endsEdgeLines]}")
            edgeLine.setP(-1,source[1].scenePos())

        #DummyNodes are handled in the callback, I _think_    
        elif type(source) == dummyNodeItem:
            print("Dummynode")

        #Draw the arrow/ end shape
        #Currently, endshapes have no managed relationship to the end nodes - they are just allocated out
        if len(self.endShape) > 0:
            arrowCount = 0
            for eN in self.endNodes:
                if eN[0].data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                    #During init, endsEdgeLines may not yet be populated.
                    if len(eN[1].endsEdgeLines) > 0 and arrowCount < len(self.endShape): 
                        eS = self.endShape[arrowCount]
                        eS.prepareGeometryChange()
                        # Compute rotation angle
                        #port is eN[1]
                        # there is only ever 1 line per port.
                        angleDeg = eN[1].endsEdgeLines[0].endAngle()
                        eS.setRotation(angleDeg)
                        eS.setPos(eN[1].endsEdgeLines[0]._p[-1])
                        arrowCount += 1

        #If needed move all the polyline points - updatePath handles this.
        edgeLine.updatePath()

    def addSegment(self, edgeLine, newNode, start, nodePt, splitPoint:QPointF ):
        """ Adds another segment to a hyperedge, between `newNode` and the segment `edgeLine`, 
            with `start` being the "Node" or the "Edge"
            `nodePt` is where to put the port on `newNode`
            Splits the `edgeLine`, adding a dummyNode at that splitPoint
            Adds a new Polyline in the correct direction
            updates self.edgeLines[], self.dummyNodes[], >> removed >> self.hyperEdgeGraph[]
            >>updates the node reverse pointers via updateLine()
            Returns False if guard clauses not met, else false.
        """
        #store the start & end nodes (or dummyNodes) before any changes
        #Note: The guard clause included in this loop should be applied in the scene
        #TODO: Move the guard clause from here once everything is stable    
        stN = None
        for sN in self.startNodes:
            if newNode == sN[0]:
                #TODO" THis should be a popup, with names, as well as numbers
                print(f"Error - node {newNode.nodeNum} already starts edge {self.edgeNum}")
                return False
            if edgeLine in sN[1].startsEdgeLines:
                stN = sN
        if stN == None: # check for dummyNode
            for dN in self.dummyNodes:
                if edgeLine in dN[1].startsEdgeLines:
                    stN = dN
        endN = None       
        for eN in self.endNodes:
            if newNode == eN[0]:
                #TODO" THis should be a popup, with names, as well as numbers
                print(f"Error - node {newNode.nodeNum} already ends edge {self.edgeNum}")
                return False         
            if edgeLine in eN[1].endsEdgeLines:
                endN = eN
        #if endN: 
        if endN == None: # check for dummyNode
            for dN in self.dummyNodes:
                if edgeLine in dN[1].endsEdgeLines:
                    endN = dN
        #print(f"addSeg segment Start node = {stN[0].nodeNum}, seg end node = {endN[0].nodeNum}")

        #Add a dummyNode at splitPoint, also its own "port", to make it shape consistent with stored nodes
        dN = dummyNodeItem(splitPoint, parent=self) #parent = self  makes updates a bit easier
        #print(f" addSeg after create {dN.pos()=}")
        # dN is it's own node and port, used for handles too.
        dN = (dN,dN)  
        self.dummyNodes.append(dN)

        splitLine = edgeLine.split(dN[0].pos() ) #scenePos()) #self now ends just before splitPoint
        splitLine.setData(KEY_ROLE,ROLE_POLYLINE)
        splitLine.my_parent_item = self #TODO: Needed???
        splitLine.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.bRect = self.bRect.united(splitLine.boundingRect())

        self.edgeLines.append(splitLine)
        #Fix the end nodes
        #Disconnect the original edgeLine
        endN[1].endsEdgeLines.remove(edgeLine)
        #Connect it to the dN port
        dN[1].endsEdgeLines.append(edgeLine)
        
        #Fix the start nodes
        dN[1].startsEdgeLines.append(splitLine)
        endN[1].endsEdgeLines.append(splitLine)

        #print(f"addSeg split: {self.endNodes.index(endN)=} {[e[0].nodeNum for e in self.endNodes]}")
        #Tell the splitLine end point about its new value, if it is a real node, not a dummy node
        if endN[0].data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]: 
            self.setEnd(endN,splitLine)

        #Now create the new, third edge. from `Node` to the dummyNode
        if start == "Node":  #node --> edge
            #newNode needs another port
            nPort = newNode.createPort(nodePt)    
            #give the edgeLine the new endpoint 
            pts = [nPort.pos(),dN[0].pos()]
            #Make pretty tangents
            tgts = []        
            newSlope = nPort.orthogonalSlope()
            tgts = [(QPointF(0,0),  
                             QPointF(newSlope[0] * self.tgtScaleFactor, 
                                     newSlope[1] * self.tgtScaleFactor))]
            # directed parallel to existing t's at end - steal from edgeLine
            tgts.append( edgeLine._t[-1] )
            newEdge = HermiteSplineItem(p=pts, t=tgts, parent=self)
            newEdge.setData(KEY_ROLE,ROLE_POLYLINE)

            #Add this to startNodes
            newNP = (newNode,nPort)
            newNP[0].startsEdges.append(self)
            newNP[1].startsEdgeLines.append(newEdge)

            self.edgeLines.append(newEdge)
            self.startNodes.append(newNP)
            self.setStart(newNP,newEdge) 

            #Update the dummyNode as end
            dN[0].endsEdgeLines.append(newEdge)

        else: #edge -> node
            #print("addSegment : edge->Node")
            #newNode needs another port
            nPort = newNode.createPort(nodePt)    
            #give the edgeLine the new endpoint 
            pts = [dN[1].pos(), nPort.pos()]
            #Make pretty tangents
            #Use the start tangent of the split line
            tgts = [splitLine._t[0] ]
            newSlope = nPort.orthogonalSlope()
            tgts.append( (QPointF(newSlope[0] * -self.tgtScaleFactor, newSlope[1] * -self.tgtScaleFactor),QPointF(0,0))  )

            newEdge = HermiteSplineItem(p=pts, t=tgts, parent=self)
            newEdge.setData(KEY_ROLE,ROLE_POLYLINE)

            newNP = (newNode,nPort)
            #Tell the node & port it has an extra edge ending at it.
            newNP[0].endsEdges.append(self)
            newNP[1].endsEdgeLines.append(newEdge)
            
            #Add this to endNodes
            self.edgeLines.append(newEdge)
            self.endNodes.append(newNP)
            self.setEnd(newNP,newEdge) 

            #Update the dummyNode as start
            dN[0].startsEdgeLines.append(newEdge)
        
        #Tidy up all the end arrows by toggling isDirected (remove and then add back)
        self.setDirected(not self.isDirected)
        self.setDirected(not self.isDirected)
        
        #Edge added succesfully
        return True

    def hyperEdgeGraph(self)->dict:
        """ Runs through the nodes, dummyNodes and edgeLines, 
            and returns dictionary of INDICES {edge: ((startNode,startPort),(endNode,endPort))}
            Based on a segment of `toXML()` 
            heg[idx][0] is the start (node,port) tuple.
            heg[idx][1] is the end (node,port) tuple
        """

        hStarts = {} # dict 
        hEnds = {} # dict
        for n in self.startNodes:
            hStarts.update({n[1].startsEdgeLines[0].lineNum : (n[0].nodeNum, n[1].index)})

        for n in self.endNodes:
            #print(f"he toX endNode {n[0].nodeNum} port {n[1].index} {len(n[1].endsEdgeLines)=}")
            hEnds.update({n[1].endsEdgeLines[0].lineNum : (n[0].nodeNum, n[1].index)})
        
        for n in self.dummyNodes:
            #Currently (Apr 2026) dummyNodes don't have ports dN[0] = dN[1]
            for eL in n[0].startsEdgeLines:
                hStarts.update({eL.lineNum : (n[0].nodeNum, n[1].nodeNum)})
            for eL in n[0].endsEdgeLines:
                hEnds.update({eL.lineNum  : (n[0].nodeNum, n[1].nodeNum)})
        
        #the hyperEdge graph - a comment, to aid debugging. Data needed is in the edgeLine element
        #print(f"hyperEdge {self.edgeNum} {hStarts.items()} , {hEnds.items()}")
        hEdgeGraph = dict()
        for k,v in hStarts.items():
            hEdgeGraph.update({k:(v,hEnds[k])})

        #print(f"hyperEdge {hEdgeGraph}")
        return hEdgeGraph

    def delSegment(self, delEdgeLine):
        """ Deletes the edgeLine, if it won't destroy the whole edge """

        def delEdgeLineFromStartNode(sNItem,eLIdx):
            """ Delete the reference to eLine `eLIdx` in startNode `sNItem`"""

            print(f"deledgeline {sNItem.nodeNum=}")
            if  sNItem.data(KEY_ROLE) == ROLE_DUMMYNODE:
                sNItem.startsEdgeLines.remove([eL for eL in self.edgeLines if eL.lineNum == eLIdx][0])
            else: #real Node
                #print(f"delSeg: delELSN: real node")
                #1st clear the s/eNodes tuple, to avoid referencing issues
                for n in self.startNodes:
                    if n[0] == sNItem: # an edge can only start once from a node
                        self.startNodes.remove(n)
                        break
                #Find the port. heg uses `index`, not nodeNum
                #print(f"delSeg {[p.index for p in sNItem._Ports if p.index == heg[eLIdx][0][1]]}")
                #Find the port
                p = [p for p in sNItem._Ports if p.index == heg[eLIdx ][0][1]][0]
                sNItem.deletePort(p) #Which deals with startsEdgeLines
                #Remove the node ptr to this whole edge
                sNItem.startsEdges.remove(self)
                

        def delEdgeLineFromEndNode(eNItem, eLIdx):
            """ Delete the reference to eLine `eLIdx` in endNode `eNItem`"""
            if  eNItem.data(KEY_ROLE) == ROLE_DUMMYNODE:
                eNItem.endsEdgeLines.remove([eL for eL in self.edgeLines if eL.lineNum == eLIdx][0])
            else: #real Node

                #Find the port. heg uses `index`, not nodeNum, so search ...
                p = [p for p in eNItem._Ports if p.index == heg[eLIdx][1][1]][0]
                #1st clear the s/eNodes tuple, to avoid referencing issues
                for n in self.endNodes:
                    if n[0] == eNItem: # an edge can only start once from a node
                        self.endNodes.remove(n)
                        break
                eNItem.deletePort(p)
                #Remove the node ptr to this whole edge
                eNItem.endsEdges.remove(self)


        #TODO: look at failure modes (and return values)
        dEIdx = delEdgeLine.lineNum

        #get the hyperEdgeGraph for navigation/ checking
        heg = self.hyperEdgeGraph()
        print(f"delSeg {dEIdx=} {heg=}")

        #Check for dN - dN segment (can't delete)
        sN = heg[dEIdx][0][0]
        sNItem = self.Scene.findItemByIdx(sN)
        eN = heg[dEIdx][1][0]
        eNItem = self.Scene.findItemByIdx(eN)
        #print(f"delseg {sN=}, {eN=}")
        canDelete:bool = sNItem.data(KEY_ROLE) != ROLE_DUMMYNODE or \
                          eNItem.data(KEY_ROLE) != ROLE_DUMMYNODE

        #Check if the sN/ eN node is the *only* start/ end node 
        #NOTE: This is only really true for directed edges. (But then 2 s/eNs would have to be split apart). User must delete the whole edge for this.
        if sNItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
            canDelete = canDelete and len(self.startNodes) > 1 
        if eNItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
            canDelete = canDelete and len(self.endNodes) > 1

        if not canDelete:
            #TODO: Make this a `QtWidgets.QMessageBox`
            print(f"Error - Deleting this segment will destroy the edge")
            return

        self.suppressItemChange = True

        #Node side pointers
        #only "proper" edges have distinct ports
        if sNItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:  
            #Remove from the self.model.Gr
            self.model.Gr.delNodeFromEdge(sNItem.nodeNum, self.edgeNum)
            delEdgeLineFromStartNode(sNItem, dEIdx)

        if eNItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
            #Remove from the self.model.Gr
            self.model.Gr.delNodeFromEdge(eNItem.nodeNum, self.edgeNum)
            delEdgeLineFromEndNode(eNItem, dEIdx)

        #Check how many edgeLines at the dummyNode
        if sNItem.data(KEY_ROLE) == ROLE_DUMMYNODE:
            dNItem = sNItem
        elif eNItem.data(KEY_ROLE) == ROLE_DUMMYNODE:
            dNItem = eNItem
        dNEdgeLinesCount = len(dNItem.startsEdgeLines) + len(dNItem.endsEdgeLines)

        #Keep the coords 
        dNpos = dNItem.pos()
        #print(f"delseg deleting {dNItem.nodeNum=}")

        #if == 3, consolidate the 2 edgelines into 1
        if dNEdgeLinesCount == 3:
            #Get the 2 edgeLines that the dN joins. Note: the edge order is correct by construction
            #  ends = incoming, starts = outgoing
            eLold = dNItem.endsEdgeLines + dNItem.startsEdgeLines

            #Remove the common line, leaving newStart -> newEnd, where newEdge must be linked
            eLold.remove(delEdgeLine)
            newStart = heg[eLold[0].lineNum][0][0] # [0][0] is node
            newStartItem = self.Scene.findItemByIdx(newStart)

            #print(f"delseg {newStart=}  {newStartItem=}")
            newEnd = heg[eLold[1].lineNum][1][0]
            newEndItem = self.Scene.findItemByIdx(newEnd)

            #print(f"delseg - consol {newEnd=} {newEndItem=}")
            #Unlink the edgeLines to be replaced
            delEdgeLineFromStartNode(newStartItem, eLold[0].lineNum)
            delEdgeLineFromEndNode(newEndItem, eLold[1].lineNum)

            #Reattach to start/end/dummyNodes

            #start at (newStartItem,NEWport) or (dN,dN)
            #This could go after the edgeLine is recreated - newPoints doesn't need it?
            #print(f"delseg {newStartItem.nodeNum=}")
            if newStartItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
                #1st edgeLine's 1st point:
                newSPort = newStartItem.createPort(eLold[0]._p[0])
            elif newStartItem.data(KEY_ROLE) in [ROLE_DUMMYNODE]: #dummyNode
                newSPort = newStartItem
            else:
                print(f"ERROR deleting segment in edge {self.edgeNum} - start mangled")
            #print(f"delseg {newEndItem.nodeNum=}")
            if newEndItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
                #last edgeLine's lastst point:
                newEPort = newEndItem.createPort(eLold[1]._p[-1])
            elif newEndItem.data(KEY_ROLE) in [ROLE_DUMMYNODE]: #dummyNode
                newEPort = newEndItem
            else:
                 print(f"ERROR deleting segment in edge {self.edgeNum} - end mangled")

            #get the rest of the points and tangents.
            newPoints = []

            #incoming points
            newPoints += eLold[0]._p[:-1]
            if self._polyEdge == SPLINE:
                newTangents = eLold[0]._t[:-1]

            # Treat the dN as a point, use left tangents as default (this is a bit arbitrary)
            newPoints += [dNItem.pos()]
            if self._polyEdge == SPLINE:
                if dNItem == sNItem: #start has Right tangents (1st tuple item) 
                    #_t is a list of tuples
                    newTangents += [(delEdgeLine._t[0][1],delEdgeLine._t[0][1])]
                else: #left tangent 
                    newTangents += [(delEdgeLine._t[1][0],delEdgeLine._t[1][0])]
            
            #End
            newPoints += eLold[1]._p[1:]
            if self._polyEdge == SPLINE:
                newTangents += eLold[1]._t[1:]

            #Build a new edgeLine
            if self._polyEdge == SPLINE:
                eLNew = HermiteSplineItem(p=newPoints,t=newTangents,parent=self)
            else:
                eLNew = StraightLineItem(newPoints,parent=self)
            eLNew.setFlag(QGraphicsItem.ItemIsSelectable, False)
            #TODO: Should bRect not be totally recreated, since we are subtracting?
            self.bRect = self.bRect.united(eLNew.boundingRect())
            eLNew.setData(KEY_ROLE,ROLE_POLYLINE)
            self.edgeLines.append(eLNew)

            #Add eLNew to startNodes and the port
            newSNP = (newStartItem,newSPort)
            #print(f"del seg {newSNP[0].nodeNum=} {newSNP[1].nodeNum=}")
            if newStartItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
                newSNP[0].startsEdges.append(self)
                self.setStart(newSNP,eLNew)
            newSNP[1].startsEdgeLines.append(eLNew)

            #and end
            newENP = (newEndItem,newEPort)
            #print(f"del seg {newENP[0].nodeNum=} {newENP[1].nodeNum=}")
            if newEndItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
                newENP[0].endsEdges.append(self)
                self.setEnd(newENP,eLNew)
            newENP[1].endsEdgeLines.append(eLNew)

            #remove the 2 old eLs
            #TODO: This shouldn't be in a for loop, but I can't remember what it should be!
            for e in eLold:
                ##??? Somehow a pointer is being missed in this loop, causing the second-delete error
                # and also that the item isn't bein removed from the scene/ edge
                #Remove the pointers from start/endNode to the OLD edgeLines
                #print(f"delSeg ==3 removing {e.lineNum=}")
                e.setParentItem(None)
                self.edgeLines.remove(e)
                self.Scene.removeItem(e)
                #del(e)

            #Remove dummyNode (which is stored as a tuple
            self.dummyNodes.remove((dNItem,dNItem))
            dNItem.setParentItem(None)
            self.Scene.removeItem(dNItem)


        #remove item from edgeLines & scene
        print(f"delSeg end edgeLines: {[e.lineNum for e in self.edgeLines]}")
        print(f"delSeg {delEdgeLine.lineNum=}")
        delEdgeLine.setParentItem(None)
        self.edgeLines.remove(delEdgeLine)
        self.Scene.removeItem(delEdgeLine)
        del delEdgeLine

        #print(f"delseg eLs after del {[e.lineNum for e in self.edgeLines]}")
        #Force a cleanup???
        gc.collect()
        print(f"delseg heg2: {self.hyperEdgeGraph()}")

        self.suppressItemChange = False
        #Tidy up the arrows
        self.setDirected(not self.isDirected)
        self.setDirected(not self.isDirected)
        self.update()

    def edgeLineAt(self, pos):
        """ Takes a position, and returns the edgeLine closest to that point
            Part of the migration from single edgeLines to multiple edgeLines
        """
        for eL in self.edgeLines:
            if eL.contains(pos):
                return eL
        
        return None  #Not found. Just making the default explicit.

            
        

