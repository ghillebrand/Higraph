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
            QPainterPath, QPainterPathStroker, QCursor,
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
        if not type(sItem) is tuple: 
            print(f"{sItem._Ports =}")
            if len(sItem._Ports) == 0: #No ports, create one
                spID = sItem.createPort(self.startNode.pos())
            sItem = (sItem,sItem._Ports[spID])
        self.startNode = sItem
        #print(f"port {sItem=}")
        
        #TODO: Add ports to endNode
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
            #ptList = [self.startNode[1].pos()] + points + [self.endNode[1].pos()]
            ptList = [self.startNode[1].scenePos()] + points + [self.endNode[1].scenePos()]
        else: #just start with a 2-pt line
            #ptList = [self.startNode[1].pos(),self.endNode[1].pos()]
            ptList = [self.startNode[1].scenePos(),self.endNode[1].scenePos()]
        #Track what sort of edge this one is
        self._polyEdge = polyLineType
        
        if self._polyEdge == STRAIGHT:
            self.edgeLine = StraightLineItem(ptList,parent=self)
        else: #Assume spline! Error checking later!
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
            self.isDirected = directed == 'true'

        if self.isDirected:
            self.endShape = ArrowHeadItem(size=NODESIZE/2, parent=self)
        else:
            self.endShape = None

        self.bRect =self.edgeLine.boundingRect()

        #Link up the topology for the visual graph.
        #TODO: hypergraph - lines  can start xor end on an edge - 
        sItem[0].startsEdges.append(self)
        self.setStart(sItem)
        eItem[0].endsEdges.append(self)
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
            target=str(self.endNode.nodeNum)
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
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine))
            self.textItem.setDefaultTextColor(Qt.blue)   
            self.metaDisplay.setDefaultTextColor(Qt.blue)
        else:
            painter.setPen(Qt.black)
            self.textItem.setDefaultTextColor(Qt.black)
            self.metaDisplay.setDefaultTextColor(Qt.black)

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

    def itemChange(self, change, value):
        #print(f"edge item change {change},{value}")
        #guard clause to trap calls from __init__
        if not self.suppressItemChange:
            if change == QGraphicsItem.ItemSelectedHasChanged:
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
                # Search for the correct port!
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

        if source == self.startNode: 
            #Set the 0th edgeLine point to where the `source` object port (now) is. 
            #print(f"setting start from {source[0].nodeNum}, {source[1].index}")
            self.edgeLine.setP(0,source[1].scenePos())

        if source == self.endNode: #endNode
            #print(f"setting end from {source[0].nodeNum}, {source[1].index}")
            self.edgeLine.setP(-1,source[1].scenePos())

        #Draw the arrow/ end shape
        if self.endShape:
            self.endShape.prepareGeometryChange()
            # Compute rotation angle
            #TODO: This version the visible "end" is HITSIZE pixels away from the node centre 
            angle_deg = self.edgeLine.endAngle()
            self.endShape.setRotation(angle_deg)
            self.endShape.setPos(self.edgeLine._p[-1])
        #If needed move all the polyline points - updatePath handles this.
        self.edgeLine.updatePath()
