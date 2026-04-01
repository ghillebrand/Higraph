""" Edges code """
#For debugging: (stack traces)
import traceback

#Global constants. 
from  HGConstants import *

from  GraphicsSupport import *

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
            QGraphicsScene, QGraphicsView, QListWidget, QListWidgetItem,
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

    def __init__(self,model,listWidget,sItem, eItem, directed='', parent=None, nameP="", id=None,
                    polyLineType = DEFAULT_EDGE, points=[],tangents=[],metadata={}, metadataAttributes={}):
        """ Create a visual edge, using the pos of the st and end, which are tuples of (Node,Port)
        points must be QPointFs and tangents must be tuples of QPointFs, relative to the points
        """
        super().__init__(parent)
        self.suppressItemChange = True  # suppress itemChange until all attribs set.

        self.model = model
        self.listWidget = listWidget
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
            print(f"{sItem._Ports =}")
            if len(sItem._Ports) == 0: #No ports, create one
                spID = sItem.createPort(self.startNode.pos())
            sItem = (sItem,sItem._Ports[spID])
        self.startNode = sItem
        #print(f"port {sItem=}")
        
        #Add ports to endNode
        if not type(eItem) is tuple: 
            print(f"{eItem._Ports =}")
            if len(eItem._Ports) == 0: #No ports, create one
                spID = eItem.createPort(self.endNode.pos())
            eItem = (eItem,eItem._Ports[spID])
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
        lWitem = QListWidgetItem(self.metadata['name'])
        lWitem.setData(KEY_INDEX,self.edgeNum)
        lWitem.setData(KEY_ROLE,ROLE_EDGE)
        self.listWidget.addItem(lWitem)

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
                #print(f"{startSlope=}, {endSlope=}")
                tgtScaleFactor = 30 #TODO: Make this a global constant (also used in PolyLineItem)
                tangents = [(QPointF(0,0),  
                             QPointF(startSlope[0] * tgtScaleFactor, startSlope[1] * tgtScaleFactor))]

                tangents.append((QPointF(-endSlope[0] * tgtScaleFactor,-endSlope[1] * tgtScaleFactor), 
                                QPointF(0,0)))
                #print(f"{tangents=}")

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
        #TODO: hypergraph - lines  can start xor end on an edge - 
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
        return f"\n>> VisEdgeItem {super().__repr__()}\n {self.textItem.toPlainText() =}\n{self.edgeLine =}\n" + \
                        f"ID: {self.edgeNum} text:{self.textItem.toPlainText()} s:({self.startNode[0].data(KEY_INDEX)}, {self.startNode[1].index})" + \
                        f" e:({self.endNode[0].data(KEY_INDEX)}, {self.endNode[1].index})) <<"

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
        """ Tell Qt the ends have moved. source = None allows an arrow recalc without point change"""
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
                            #print(f"setting start to {p.index=}")
                else: #end
                    for p in source._Ports:
                        if p == self.endNode[1]:
                            source = (source,p)
                            #print(f"setting end to {p.index=}")

            if  type(source) is HandleItem:
                #print(f"Making Handle into a tuple")
                source = (0,source)
        #print(f"{source=}  == {self.startNode=}")
        #Checking the .t value is not needed now that there is only 1 edge per port.
        
        ### Is this even needed???!!! I don't think so
        #if source and type(source[0] )== VisBlobItem and source[0]==self.startNode[0] and source[1].t==self.startNode[1].t:
        #    self.edgeLine.setP(0,source[1].scenePos())
        #    print("updateLine start with t")
        #elif source and type(source[0] )== VisBlobItem and source[0]==self.endNode[0] and source[1].t==self.endNode[1].t:
        #    self.edgeLine.setP(-1,source[1].scenePos())
        #    print("updateLine end with t")
        #el
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


class VisHyperEdgeItem(QGraphicsObject): 
    """ Create a new Hyperedge - both Graph Model and Visual ("graphics")
      This connects visual edges to model and list
      This DOES NOT inherit from VisEdgeItem - there are too many deep changes.
    """
    #Create the signal for editing
    requestEdit = Signal(object)  

    def __init__(self,model,listWidget,sItem, eItem, directed='', parent=None, nameP="", id=None,
                    polyLineType = DEFAULT_EDGE, points=[],tangents=[],metadata={}, metadataAttributes={}):

        """ Create a visual edge, using the pos of the st and end, which are tuples of (Node,Port)
        points must be QPointFs and tangents must be tuples of QPointFs, relative to the points
        """
        super().__init__(parent)
        self.suppressItemChange = True  # suppress itemChange until all attribs set.

        self.model = model
        self.listWidget = listWidget

        #startNode must be a tuple (node,port). convert if not

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
        
        #Store the edgeLines (>1 for hyperEdges)
        self.edgeLines = [] 
        #List of the dummy nodes needed to graphical contruct the hyper edge
        dummyNodes = []
        #the structure of the binary(?) graph mapping out the hyperedge. 
        #  This will be tuples of `VisNodeItems` and `dummyNodeItems`
        #  len == 0 implies simple edge, >0 hyperedge
        hyperEdgeGraph = []

        #option to set a default name. 
        defName = "" #just the ID

        #Create an abstract edge, and keep the index as well
        #Simple edge
        if len(self.startNodes) == 1 and len(self.endNodes) == 1:
            self.edge,self.edgeNum = self.model.addGMEdge(sItem[0],eItem[0],nameP = defName,id=id)
        else:
            #handle creation of hyperedge from passed in lists.
            pass
        
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
        lWitem = QListWidgetItem(self.metadata['name'])
        lWitem.setData(KEY_INDEX,self.edgeNum)
        lWitem.setData(KEY_ROLE,ROLE_EDGE)
        self.listWidget.addItem(lWitem)

        # Create a text item to hold & show the ID number
        #self.textItem = QGraphicsTextItem(f"{self.edgeNum}", self)
        #textRect = self.textItem.boundingRect()
        #self.textItem.setPos(-textRect.width()/2, -textRect.height()/2)

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
        
        #Simple edge
        if len(self.startNodes) == 1 and len(self.endNodes) == 1:
            stN = self.startNodes[0]
            endN = self.endNodes[0]
            if len(points) > 0: 
                ptList = [stN[1].scenePos()] + points + [endN[1].scenePos()]
            else: #just start with a 2-pt line
                ptList = [stN[1].scenePos(),endN[1].scenePos()]
            #if len(points) > 0: 
            #    ptList = [self.startNode[1].scenePos()] + points + [self.endNode[1].scenePos()]
            #else: #just start with a 2-pt line
            #    ptList = [self.startNode[1].scenePos(),self.endNode[1].scenePos()]
        else: #Hyperedge
            #If we are _creating_ an n-ary edge, it must be from a file, so `points` and `tangents` will be populated
            
            pass

        #Track what sort of edge this one is
        self._polyEdge = polyLineType
        if self._polyEdge == STRAIGHT:
            self.edgeLines.append(StraightLineItem(ptList,parent=self))
        else: #Assume spline! Error checking later!
            #If no tangents given, and start/end are on a blob, make tangent at right angles to blob
            if len(tangents) == 0:
                #Orthogonal to `nodeshape` at `point`
                startSlope = self.startNodes[0][1].orthogonalSlope()
                endSlope =  self.endNodes[0][1].orthogonalSlope()
                #print(f"{startSlope=}, {endSlope=}")
                tgtScaleFactor = 30 #TODO: Make this a global constant (also used in PolyLineItem)
                tangents = [(QPointF(0,0),  
                             QPointF(startSlope[0] * tgtScaleFactor, startSlope[1] * tgtScaleFactor))]

                tangents.append((QPointF(-endSlope[0] * tgtScaleFactor,-endSlope[1] * tgtScaleFactor), 
                                QPointF(0,0)))
                #print(f"{tangents=}")

            self.edgeLines.append(HermiteSplineItem(p=ptList,t=tangents,parent=self))
        
        self.bRect = QRectF(0,0,0,0)
        for edgeLine in self.edgeLines:
            edgeLine.setData(KEY_ROLE,ROLE_POLYLINE)
            #Stop Python GC from mangling things on delete (It seems this ref is not critical)
            #self.edgeLine.my_parent_item = self

            #self.edgeLine.setPen(noPen)
            edgeLine.setFlag(QGraphicsItem.ItemIsSelectable, False)
            self.bRect = self.bRect.united(edgeLine.boundingRect())

        #Add in the arrowhead for digraph
        if directed == '':
            self.isDirected = self.model.isDigraph
        else:
            #self.isDirected = directed == 'true'  JH
            self.isDirected=directed

        if self.isDirected:
            self.endShape = ArrowHeadItem(size=NODESIZE/2, parent=self)
        else:
            self.endShape = None

        

        #Link up the topology for the visual graph.
        #TODO: hypergraph - multiple starts 
        #Node
        for stI in self.startNodes:
            stI[0].startsEdges.append(self)
            #Port
            stI[1].startsEdgeLines.append(self)  #JH duplicate this for now
            self.setStart(stI)

        #end Nodes
        for endI in self.endNodes:
            endI[0].endsEdges.append(self)
            #Port
            endI[1].endsEdgeLines.append(self)    #JH duplicate this for now
            self.setEnd(endI)

        #Selection and editing vars:
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
        return f"\n>> VisHyperEdgeItem {super().__repr__()}\n {self.textItem.toPlainText() =}\n{self.edgeLines =}\n" + \
                        f"ID: {self.edgeNum} text:{self.textItem.toPlainText()} s:({self.startNode[0].data(KEY_INDEX)}, {self.startNode[1].index})" + \
                        f" e:({self.endNode[0].data(KEY_INDEX)}, {self.endNode[1].index})) <<"

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
        #HACK: Putting the text at the middle of the first segment. Where should it go?
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
        #Hyperedge - add to the list of starts, if not already present. 
        if not start in self.startNodes:
            self.startNodes.append(start)
        #Set the port startsLines
        #self.edgeLine.setP(0,start.scenePos())
        self.updateLine(start)

    def setEnd(self, end):
        #TODO: Add updateEdge() to Graph class, then include here??
        #node may not end twice
        if not end in self.endNodes:
            self.endNodes.append(end)
        #self.edgeLine.setP(-1,end.scenePos())
        self.updateLine(end)

    def updateLine(self, source=None):
        """ Tell Qt the ends have moved. 
            source is the node which triggered the udpate. Only 1 node at a time will call.
            source = None allows an arrow recalc without point change
            Hyperedges can have >1 lines. Update all of them? Only the one changed/ passed in?
        """
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
                source = (0,source)
        #print(f"{source=}  == {self.startNode=}")
        #work out which end (node!) to update

        if source in self.startNodes:
            #stN = self.startNodes.index(source)
            #How do we know which edgeline? Does source.startsEdges know? Or need the subgraph of the hyperedge?
            #HACK:  for one segment
            #set the start to the scenePos of the port (tuple is (node,port))
            self.edgeLines[0].setP(0,source[1].scenePos())
        elif source in self.endNodes: #endNode
            #print(f"setting end from {source[0].nodeNum}, {source[1].index}")
            self.edgeLines[0].setP(-1,source[1].scenePos())

        #Draw the arrow/ end shape
        #TODO: Draw the arrow at all the endNodes. Each ending of the edge will need its own endShape
        if self.endShape:
            self.endShape.prepareGeometryChange()
            # Compute rotation angle
            #HACK: This works for single segments only
            angleDeg = self.edgeLines[0].endAngle()
            self.endShape.setRotation(angleDeg)
            self.endShape.setPos(self.edgeLines[0]._p[-1])
        #If needed move all the polyline points - updatePath handles this.
        #HACK: single segment
        self.edgeLines[0].updatePath()
