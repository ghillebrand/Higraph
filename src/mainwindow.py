from __future__ import annotations

"""
V03 of a Python Graph Editing Tool. 
Grant Hillebrand 

See https://isijingi.co.za/wp/category/higraph/ for related posts.

"""
#TODO: Tidy these up to from <lib> import <used>
import sys
import os
import copy
import math
import re
import traceback 

#For file handling and clipboard
import xml.etree.ElementTree as ET
from xml.dom import minidom

#Debugging stuff

#import logging
import gc
import weakref

from typing import List, Dict

from PySide6.QtWidgets import ( QAbstractItemView, QApplication, QWidget, QMainWindow, QDialog,
            QGraphicsScene, QGraphicsView, QListWidget, QListWidgetItem, QTreeWidget, 
            QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
            QLineEdit, QInputDialog, QMenu, QFileDialog, QStyleOptionGraphicsItem, QGraphicsObject,
            QSlider, QLabel, QStatusBar, QColorDialog, QMessageBox,
            QGraphicsSceneMouseEvent,
            QVBoxLayout, QHBoxLayout, QTextEdit, QPushButton)

from PySide6 import (QtCore, QtWidgets, QtGui )
from PySide6.QtGui import (QStandardItemModel, QStandardItem, QPolygonF,QPainter,
            QTransform, QFont, QFontMetrics, QAction, QCursor, QPen,QBrush,
            QPainterPath, QPainterPathStroker, QCursor, QUndoStack, QUndoCommand,
            QGuiApplication, QImage, QPixmap)
from PySide6.QtCore import (QCoreApplication, QLineF, QPointF,QPoint, QRect, QRectF, 
            QSize, QSizeF, Qt, Signal, Slot, QTimer, QObject, QEvent, 
            QMimeData, QBuffer, QByteArray, QIODevice, QItemSelectionModel)
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtPrintSupport import QPrinter, QPrintDialog
#from PySide6.Qtcore import QItemSelectionModel

from ui_formTree import Ui_MainWindow
from ui_Credits import Ui_dlgCredits
from Ui_HelpAbout import Ui_dlgAbout

#Global constants. 
from  HGConstants import *

# core Graph class:
from coreGraph import Graph

#Helper & housekeeping functions
#Draw nice edges
from PolyLineItemHG import StraightLineItem, HermiteSplineItem, HandleItem
from GraphicsSupport import *

#Node code
from Nodes import *
from Edges import *

#cGPT edit code
from EditVisItemDialog import *  #EditVisEdgeItemDialog, EditVisNodeItemDialog

class graphModel(QStandardItemModel):
    """ Hold the visual details for the nodes and edges of the graph (x,y, size)
        V0: Nodes: nodeID FK from Graph, x,y
            Edges: edgeID FK from Graph, sx, sy, ex, ey.
        V01: Edges as splines

        Will/ must! stay in sync with Graph, which will handle topology.
    """

    def __init__(self):
        super().__init__()
        #Setup the abstract graph
        self.Gr = Graph()
        #TODO: Read this from config/ on file load
        self.isDigraph = ISDIGRAPH  

    def __repr__(self):
        rStr =""
        for row in range(self.rowCount()):
            #TODO: Columns not used here
            for col in range(self.columnCount()):
                item = self.item(row, col)
                rStr += f"({row}, {col}): idx ={item.data(KEY_INDEX)},{item.data(KEY_ROLE)} \n {item}\n\n"
        return rStr

    __str__ = __repr__


    def getModelItems(self):
        return [f"{self.item(i).text()}::{self.item(i).data(KEY_INDEX)} ({self.item(i).data(KEY_ROLE)})" \
            for i in range(self.rowCount())]

    def addGMNode(self,posn,nameP="",id=None):
        """Make a Graph Model NODE item, return the item and the index number (item,n) """
        #NB: The order in the lists (Gr, listView and model MUST BE MAINTAINED.

        # Make the coreGraph02 node
        n = self.Gr.addNode(name=nameP, id=id)
        #self.Gr.nodeD[n].metadata.update({'name':nameP })
        #Default name is node number
        if nameP=="":
            self.Gr.nodeD[n].metadata.update({'name': f"n{n}"})
        else:
            self.Gr.nodeD[n].metadata.update({'name': nameP})

        #Make the Qt Item with text n
        item = QStandardItem(str(n))
        item.setData(n,KEY_INDEX)
        item.setData(ROLE_NODE,KEY_ROLE)

        self.appendRow(item)
        return item,n

    def getGMNodes(self):
        """ Returns all the Graph Model Nodes"""
        return [self.item(i).data(self.ROLE_NODE) or self.item(i).data(self.ROLE_BLOB)  for i in range(self.rowCount())]

    def addGMEdge(self,sItem, eItem, nameP=None, id=None):
        """Make a Graph Model EDGE item, return the item and the index number (item,n) 
           Note that either (but not both) of s & e may also be an edge (hypergraph)
        """
        start = sItem.nodeNum
        end = eItem.nodeNum
        e = self.Gr.addEdge(start,end,id=id)
        self.Gr.edgeD[e].metadata.update({'name':nameP })
        #Make the Qt Item with text e
        item = QStandardItem(str(e))
        item.setData(e,KEY_INDEX)
        item.setData(ROLE_EDGE,KEY_ROLE)
        #Add to the model
        self.appendRow(item)
        return item,e

    def findItemByIdx(self,idx):
        """takes a ROLE_INDEX value, and get the item out, or none """
        for row in range(self.rowCount()):
            item = self.item(row)
            if item.data(KEY_INDEX) == idx:
                return item
        return None

    def findRowByIdx(self,idx):
        """takes a ROLE_INDEX value, and returns the model row out, or none """
        for row in range(self.rowCount()):
            item = self.item(row)
            if item.data(KEY_INDEX) == idx:
                return row
        return None

    def itemName(self,itm)->str:
        """ Take a KEY_INDEX, returns the name from the graph"""
        iName = ""
        if itm.data(KEY_ROLE) in [ ROLE_NODE, ROLE_BLOB]:
            iName = self.Gr.nodeD[int(itm.nodeNum)].metadata['name']
        elif itm.data(KEY_ROLE) == ROLE_EDGE:
            iName = self.Gr.edgeD[int(itm.edgeNum)].metadata['name']
        return(iName)

    def edgesAtNode(self,itm):
        """ Take a node's KEY_INDEX, returns a list of  attached graph edges (both ends), or None"""
        eList = []
        if itm.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
            eList = copy.deepcopy(self.Gr.nodeD[int(itm.nodeNum)].startsEdges)
            eList += copy.deepcopy(self.Gr.nodeD[int(itm.nodeNum)].endsEdges)
        return(eList)

    def delEdge(self, delIdx):
        """ Takes an internal index value,
         and deletes the edge from the abstract graph and the model.
         May evolve to manage all the deletions here, rather than scene
        """
        #Delete from Gr
        #print(f"Scene del Edge About to delete {delIdx =} from {self.Gr =}")
        self.Gr.delEdge(delIdx)
        # Models work by rows, not items
        self.removeRow(self.findRowByIdx(delIdx))

    def delNode(self, delIdx):
        """ Takes an internal index value,
         and deletes the node from the abstract graph and the model.
         May evolve to manage all the deletions here, rather than scene
        """
        #Delete from Gr
        #print(f"model delNode {delIdx =}")
        #print(f"{self.Gr =}")
        self.Gr.delNode(delIdx)
        # Models work by rows, not items
        self.removeRow(self.findRowByIdx(delIdx))

    def clear(self):
        """ Extend the base clear method to clear the abstract Graph too"""
        del self.Gr
        self.Gr = Graph()
        #Reset the global Gr id counter too
        Graph.nextID = 1
        Graph.IDsUsed = set()
        super().clear()


class grScene(QGraphicsScene):
    """ holds and extends all the drawing, connects to model using VisNodeItem and VisEdgeItem"""
    # See Hg QT6.gaphor `GrScene INSERT states` for analysis of states (StateMachine)

    #Mouse state enum
    # INSERTEDGE2CLICK for handling choice of item in ambiguous cases, which requires a click to choose, 
    # and thus the end is selected on a Press, not a release.
    INSERTNODE, INSERTBLOB, INSERTEDGE, POINTER, INSERTEDGE2CLICK, MOVEEDGEEND, MOVEHANDLE, DOUBLECLICK, DRAGGING, INSERTHYPEREDGE = range(10)
    mouseModeDic={INSERTNODE:"INSERTNODE", INSERTBLOB:"INSERTBLOB", INSERTEDGE:"INSERTEDGE", POINTER:"POINTER", INSERTEDGE2CLICK:"INSERTEDGE2CLICK",\
                   MOVEEDGEEND:"MOVEEDGEEND", MOVEHANDLE:"MOVEHANDLE", DOUBLECLICK:"DOUBLECLICK", DRAGGING:"DRAGGING"}
    #TO pass edit requests to mainwindow. Signal must be class, not instance variables.
    edgeEditRequested = Signal(object)
    nodeEditRequested = Signal(object)

    def __init__(self, model,treeWidget, undoStack, mainwindow):
        super().__init__()
        self.model = model
        #self.listWidget = listWidget
        self.treeWidget = treeWidget
        self.undoStack = undoStack
        self.mainwindow = mainwindow
        self.mouseMode = self.POINTER

        # Placeholders for nodes & edges between mouse states when creating an edge
        self.tmpEdgeSt = None #QGraphicsItem - temp start
        self.tmpEdgeEnd = None
        self.startPoint = None #QPoints, to draw the edge's line/ Blob rectangle
        self.endPoint = None
        self.rubberLine = None
        self.GrRubberLine =None

        # For TreeWidget
        self.changedByCode=False

        #Handle hovering
        self.lastHovered = None #QGraphicsItem

        #Track single item selection (for edges)
        self.onlySelected = None
        self.thisHandleObjectSelected = None
        self.groupedItems = []  #when grouped items aren't selected

        #For dragging
        self._lastMousePos = QPointF(0,0)
        self.dragEdge=None

        #For avoiding click on same spot undoing bulk select
        self._lastMouseClickPos = QPointF(0,0)

        #Add axes to help see how things move & debug graphical issues.
            #TODO: THere must be a better solution!
        #WHite to provide a auto-zoom anchor
        #"""
        VLine = QGraphicsLineItem(0,100,0,-100)
        self.addItem(VLine)
        VLine.setPen(QPen(Qt.black))
        HLine = QGraphicsLineItem(100,0,-100,0)
        HLine.setPen(QPen(Qt.black))
        self.addItem(HLine) 
        #"""



    def itemsHere(self, pos: QPointF, size: QSizeF, itemRoles: List[int], hitRect=None):
        """Return a list of the items who's roles match `itemRoles`, within `size` of `pos` """
        if hitRect==None:
            half_w = size.width() / 2
            half_h = size.height() / 2
            rect = QRectF(pos.x() - half_w, pos.y() - half_h, size.width(), size.height())
        else:
            rect=hitRect
        raw = self.items(rect, Qt.IntersectsItemShape, Qt.DescendingOrder)
        filtered = []
        for itm in raw:
            #print(itm)
            if itm.data(KEY_ROLE) in itemRoles:
                filtered.append(itm)
                    #break
        #print(filtered)
        return filtered

    def pickItemAt(self, mouseEvent, size: QSizeF, itemRoles: List[int]):
        """ Return the user's choice of item at mouseEvent.scenePos() +- size, of type itemRoles, or None 
            TODO: This can be extended to return the <point> on the item, to allow for multiedges and blob 'control points'
        """
        #TODO: Change the param to pos, to make it more useful
        #or use .mapToGlobal(pos)) instead of passing in the whole event?
        mPos = mouseEvent.scenePos()
        items = self.itemsHere(mPos, size, itemRoles)
        #print(f"{items =}")
        pickedItem = None
        if len(items) == 1:
            pickedItem = items[0]
        elif len(items) > 1:
            #Since this will add a click, we go to a 2 click insert for edges
            if self.mouseMode == self.INSERTEDGE:
                self.mouseMode = self.INSERTEDGE2CLICK
            # standalone popup context menu
            menu = QMenu()
            actions = [] #menuActions equate to selectable items.
            act = QAction("Pick an item:", menu)
            menu.addAction(act)
            actions.append((act, None))
            for itm in items:
                if itm.data(KEY_ROLE) == ROLE_EDGE:
                    iType = "Edge"
                    label = f"{iType}:{itm.data(KEY_INDEX)}>{itm.textItem.toPlainText()}" 
                elif itm.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                    iType = "Node"
                    label = f"{iType}:{itm.data(KEY_INDEX)}>{itm.dispText}" 
                elif itm.data(KEY_ROLE) == ROLE_HANDLE:
                    iType = "Handle"
                    label = f"{iType}" 
                else:
                    iType = ""
                    label = f"{iType}:Unkown thing clicked" 
                act = QAction(label, menu)
                menu.addAction(act)
                actions.append((act, itm))
            #Add None to the end of the list
            act = QAction("None", menu)
            menu.addAction(act)
            actions.append((act, None))

            # exec() returns the QAction that was triggered (or None) 
            chosen_action = menu.exec(mouseEvent.screenPos()) 
            if chosen_action:
                # find which item corresponds to that action
                for act, itm in actions:
                    if act is chosen_action:
                        pickedItem = itm

        return pickedItem

    def contextMenu(self, mouseEvent, menuElts: List[tuple]):
        """ Takes a list of description:action tuples, and returns the chosen one, or None
        """
        # standalone popup context menu
        menu = QMenu()
        #Keep a list (dict?) of actions, to act on
        actions = []
        
        for (label,action) in menuElts:
            act = QAction(label, menu)
            menu.addAction(act)
            actions.append((act, action))
        #Add None to the end of the list
        act = QAction("None", menu)
        menu.addAction(act)
        actions.append((act, None))

        # exec() returns the QAction that was triggered (or None) 
        chosen_action = menu.exec(mouseEvent.screenPos()) 
        pickedItem = None
        if chosen_action:
            # find which act corresponds to that action
            for act, itm in actions:
                if act is chosen_action:
                        pickedItem = itm

        return pickedItem

    def getSceneMousePos(self):
        """ return the current scene mouse position using *global* pos. Needed for multi-click inserts. Assumes only 1 view"""
        global_pos = QCursor.pos()
        #Assume only 1 view for now
        view = self.views()[0]
        view_pos = view.mapFromGlobal(global_pos)
        scene_pos = view.mapToScene(view_pos)
        return scene_pos
        
    # JH this doesn't work and was left in accidentally, but maybe there is a purpose in it
    def snapToShape(self, mouseEvent, selItem, pos: QPointF, size: QSizeF, hitRect=None):
        if hitRect==None:
            half_w = size.width() / 2
            half_h = size.height() / 2
            rect = QRectF(pos.x() - half_w, pos.y() - half_h, size.width(), size.height())
            self.addRect(rect)
        else:
            rect=hitRect
        for i in range(int(pos.x()-half_w)-1, int(pos.x() + half_w)+1):
            for j in range(int(pos.y()-half_h)-1, int(pos.y() + half_h)+1):
                if selItem in self.itemsHere(QPoint(i,j),QSize(1,1),[ROLE_BLOB, ROLE_EDGE, ROLE_NODE, ROLE_POLYLINE]):
                    mouseOffset=(pos.x()-i, pos.y()-j)
                    mouseEvent.setPos(QPoint(mouseEvent.pos().x()-mouseOffset[0],(mouseEvent.pos().y()-mouseOffset[1] )))
                    mouseEvent.setScenePos(QPoint(mouseEvent.scenePos().x()-mouseOffset[0],(mouseEvent.scenePos().y()-mouseOffset[1] )))
                    mouseEvent.setScreenPos(QPoint(mouseEvent.screenPos().x()-mouseOffset[0],(mouseEvent.screenPos().y()-mouseOffset[1] )))
                    rect=QRectF(mouseEvent.scenePos().x(), mouseEvent.scenePos().y(), HITSIZE, HITSIZE)
                    self.addRect(rect)
                    return(mouseEvent)

    #Code to handle the edge rubber banding during creation (QT handles edit changes)

    def startRubberLine(self, mPos):
        """ called from INSERTEDGE: mousePress. All vars are class global """
        #lock the start item in place so that it doesn't drag
        self.tmpEdgeSt.setFlag(self.tmpEdgeSt.GraphicsItemFlag.ItemIsMovable, False)
        
        #This will change when the whole boundary/ edge can be a connection point
        #self.startPoint = self.tmpEdgeSt.pos()
        self.startPoint = mPos  #self.tmpEdgeSt.pos()
        self.endPoint = self.getSceneMousePos()

        #Create the rubberBand line (actual edge is created on mouseRelease)
        #polyline
        #self.rubberLine = StraightLineItem([self.startPoint, self.endPoint])
        self.rubberLine = QLineF(self.startPoint, self.endPoint)
        self.GrRubberLine = self.addLine(self.rubberLine)
        
    def stretchRubberLine(self,mPos):
        """ called from INSERTEDGE: mouseMove """
        self.endPoint = mPos # mouseEvent.scenePos()
        #
        self.rubberLine.setP2(self.endPoint)
        #self.rubberLine.setP(-1,self.endPoint)
        #self.rubberLine.updatePath()
        self.GrRubberLine.setLine(self.rubberLine)

    def endRubberLine(self):
        """called on successful end item found for edge:
         from INSERTEDGE mouseRelease or INSERTEDGE2CLICK mousePress """
        #TODO: How does this relate to finishMovingEdgeEnd?

        #If both ends are node-like, then this is a new edge.
        if self.tmpEdgeSt.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB] and self.tmpEdgeEnd.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
            #Each edge gets it's own port:Start port
            startPort = self.tmpEdgeSt.createPort(self.startPoint)
            endPort = self.tmpEdgeEnd.createPort(self.endPoint)

            #Create the actual edge
            #newAction=createEdgeCommand(None, self, self.model,self.listWidget, (self.tmpEdgeSt,startPort), (self.tmpEdgeEnd,endPort), parent=None)
            #self.undoStack.push(newAction)
            #edgeItem = VisEdgeItem(self.model,self.listWidget, (self.tmpEdgeSt,startPort), (self.tmpEdgeEnd,endPort), parent=None)
            edgeItem = VisHyperEdgeItem(self.model, self, self.treeWidget, (self.tmpEdgeSt,startPort), (self.tmpEdgeEnd,endPort), parent=None)

            #Commented out because now done in createEdgeCommand
            #Add to *Scene*
            #TODO: fix this for UNDO (sort out createEdgeCommand, add an addEdgeSegmentCommand)
            self.addItem(edgeItem)
            edgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            #can't select a node to move it due to drawing order
            edgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)
        # Otherwise, add a segment to the edge, forming a hyperedge
        elif self.tmpEdgeSt.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB] and self.tmpEdgeEnd.data(KEY_ROLE) in [ROLE_EDGE]:
            #"Node -> edge"
            #Find the segment
            itms = self.itemsHere( self.endPoint, QSize(1,1), [ROLE_POLYLINE])
            if len(itms) == 1 and itms[0].data(KEY_ROLE) == ROLE_POLYLINE:
                edgeLine = itms[0]
            else:
                print("Node-> error finding edgeLine in {itms}")
                return
            #Guard clause: nodes may only start/ end the same edge once.
            #Is there a guard condition for edges?
            #TODO: Move the guard clause here from `addSegment`

            #split it at the given point, update hyperedge geometry
            if self.tmpEdgeEnd.addSegment(edgeLine, self.tmpEdgeSt, start="Node", nodePt = self.startPoint, splitPoint=self.endPoint ):
                # On success, update the model
                #Best way to find the edge? Using edgeLine.parentItem
                self.model.Gr.addEdge( self.tmpEdgeSt.data(KEY_INDEX), edgeLine.parentItem().data(KEY_INDEX) )

        elif self.tmpEdgeSt.data(KEY_ROLE) in [ROLE_EDGE] and self.tmpEdgeEnd.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
            #edge->node
            #Find the segment
            itms = self.itemsHere( self.startPoint, QSize(1,1), [ROLE_POLYLINE])
            if len(itms) == 1 and itms[0].data(KEY_ROLE) == ROLE_POLYLINE:
                edgeLine = itms[0]
            else:
                print("Node-> error finding edgeLine in {itms}")
                return      
            #split it at the given point, update hyperedge geometry
            if self.tmpEdgeSt.addSegment(edgeLine, self.tmpEdgeEnd, start="Edge", nodePt = self.endPoint, splitPoint=self.startPoint ):
                #update the model.
                #Best way to find the edge? Using edgeLine.parentItem
                self.model.Gr.addEdge( edgeLine.parentItem().data(KEY_INDEX), self.tmpEdgeEnd.data(KEY_INDEX) )


    def resetRubberLine(self):
        """ Called whether or not an edge is created """
        if self.tmpEdgeSt and self.tmpEdgeSt.data(KEY_ROLE) != ROLE_EDGE:
            self.tmpEdgeSt.setFlag(self.tmpEdgeSt.GraphicsItemFlag.ItemIsMovable, True)
        if self.GrRubberLine:
            self.removeItem(self.GrRubberLine)
        self.tmpEdgeSt = None 
        self.tmpEdgeEnd = None
        self.startPoint = None 
        self.endPoint = None
        self.rubberLine = None
        self.GrRubberLine =None

    #Code to handle end terminator moving
    def startMovingEdgeEnd(self,edge, handle):
        """ relink edge, using handle as the floating end point
        similar to rubberLine, but we now have a line to work with"""


        #Hyperedges have a number of possible starts
        """
        #Only invoke `MovingEdgeEnd` if this is an edge-node cxn, not a edge-dummyNode
        #Which point the handles comes from
        # handle.parentItem is polyLine, which has a list of points, _p. _p[0] is start, _p[-1] end.
        edgeLine = handle.parentItem() 
        startPt = edgeLine._pHandles.index(handle)
        #if the "port" is a dummyNode, don't treat as an edgeEnd move
        print(f" {edgeLine._p[startPt]=}")
        for d in edge.dummyNodes:
            if d[0].pos() == edgeLine._p[startPt]:
                print("dummyStart")
                return
        """

        #print(f"StartMovingEdge {edge.metadata['name']}")
        self.handle = handle #Store the box for the Move/ Finish functions
        #is handle at start or end?
        #if self.handle.pos() == edge.startNode[1].scenePos():
        #Which point the handles comes from
        # handle.parentItem is polyLine, which has a list of points, _p. _p[0] is start, _p[-1] end.
        edgeLine = handle.parentItem() 
        startPt = edgeLine._pHandles.index(handle)
        #print(f"SMEE {type(startPt)} value {startPt=}")
        #print(f"StMME edgeLine = {edgeLine.lineNum}")    
        if startPt == 0: 
            # NOTE: Node relinking is only done on successful finish, so track the old Terminator item
            self.EdgeEnd = "start"
            #Work out which startNode
            #Step through the (node,port)s until we match the polyLine
            
            for NP in edge.startNodes:
                if edgeLine in NP[1].startsEdgeLines:
                    self.oldTermItem = NP
                    #print(f"SMEE start oldTermItem = {NP[0].nodeNum}")
                    break
            #self.oldTermItem = edge.startNode
            #print(f"start move {self.oldTermItem}\n{self.oldTermItem[1].index}")

            #link edge to handle to move
            edge.setStart((handle,handle),edgeLine) #Handles are dummy nodes _and_ ports
        else:
            self.EdgeEnd = "end"
            # NOTE: Node relinking is only done on successful finish
            #self.oldTermItem = edge.endNode
            #Work out which startNode
            #Step through the (node,port)s until we match the polyLine
            
            for NP in edge.endNodes:
                if edgeLine in NP[1].endsEdgeLines:
                    self.oldTermItem = NP
                    #print(f"SMEE end oldTermItem = {NP[0].nodeNum}")
                    break
            edge.setEnd((handle,handle),edgeLine)

        handle.setFlag(QGraphicsItem.ItemIsMovable, True)

    def MoveEdgeEnd(self,edge,mPos):
        """edge is a VisEdgeItem, that has been set up for moving (handles in place) """
        self.handle.setPos(mPos) 
        edge.updateLine(self.handle)
        
    def finishMovingEdgeEnd(self,edge,mPos,mouseEvent):
        """ note pickItemAt needs the full mouseEvent (screenPos) """
        #Check that this is on a valid node/ Termination pt
        newTermItem = self.pickItemAt(mouseEvent, QSize(HITSIZE,HITSIZE),[ROLE_NODE, ROLE_BLOB])
        if newTermItem != None:
            #print(f"finMovEdge {newTermItem.metadata['name']} {mPos=}")
            #Node the same, only move the port
            if newTermItem == self.oldTermItem[0]: #Just reposition the port
                #print(f"finMove - updating port {self.oldTermItem[1].index} ")
                self.oldTermItem[0].updatePort(self.oldTermItem[1],mPos)
                #TODO: Check this for flow with rest of func!
                if self.EdgeEnd == "start":
                    edgeLine = self.oldTermItem[1].startsEdgeLines[0]
                    edge.setStart(self.oldTermItem,edgeLine)
                else:  #end
                    edgeLine = self.oldTermItem[1].endsEdgeLines[0]
                    edge.setEnd(self.oldTermItem,edgeLine)
                #return

            #Check for a self-edge: newTerm == startE and we were moving `end` or the other end is now looped back
            #  if so, make sure there is a mid point in the  polyline line
            #TODO: Generalise from ...Node[0]
            #HACK: Just disabled self-edges totally during build of hyperedges
            elif False: ###*****###(newTermItem == edge.startNode[0] and self.EdgeEnd == "end") or \
                #newTermItem == edge.endNode[0] and self.EdgeEnd == "start":
                print(f"Self edge {self.EdgeEnd}")
                if len(edge.edgeLine._p) < 3 and edge._polyEdge==STRAIGHT:
                    #add in a point on the middle for now. (only works for straight, splines are OK)
                    #TODO: Refine!!!
                    edge.edgeLine.addPoint(newTermItem.pos()+QPointF(HITSIZE*4,HITSIZE*4))

            #Find the edgeLine involved. 
            #TODO: Check what happens if you try to drag a `dummyNode` handle onto a real node!
            #Unlink Edge from handle, link to newItem, (if we have really moved:)
            if self.EdgeEnd == "start":
                #Grab the line from the old Port's list of edgeLines:
                edgeLine = self.oldTermItem[1].startsEdgeLines[0]


                #Unlink from the old node
                self.oldTermItem[0].startsEdges.remove(edge)
                self.oldTermItem[1].startsEdgeLines.remove(edgeLine)
                # Delete the old port
                oldP = self.oldTermItem[1]  #.index
                self.oldTermItem[0].deletePort(oldP)
                
                # Add a port at mPos
                p = newTermItem.createPort(mPos)
                newTermItem = (newTermItem, p)
                edge.startNodes.remove(self.oldTermItem)
                #clear the old handle ending
                edge.startNodes.remove((self.handle,self.handle))
                edge.setStart(newTermItem,edgeLine)
                #relink self.oldTermItem in Graph
                # While clunky, these params will work with any item type
                self.model.Gr.updateEdge(edge.data(KEY_INDEX) ,self.oldTermItem[0].data(KEY_INDEX), "start", newTermItem[0].data(KEY_INDEX))

                #TODO: change the edge.hyperEdgeGraph  (is it ever used? - No - commented out)
                #Relink to new node
                newTermItem[0].startsEdges.append(edge)
                newTermItem[1].startsEdgeLines.append(edgeLine)
            
            if self.EdgeEnd == "end":                
                edgeLine = self.oldTermItem[1].endsEdgeLines[0]
                #TODO: The port code is true for either end - review flow of function and tidy up
                
                #Move the reverse pointer from the oldTermItem to the new:
                self.oldTermItem[0].endsEdges.remove(edge)
                self.oldTermItem[1].endsEdgeLines.remove(edgeLine)
                # Delete the old port
                oldP = self.oldTermItem[1] 
                self.oldTermItem[0].deletePort(oldP)

                # Add a port at mPos
                p = newTermItem.createPort(mPos)
                newTermItem = (newTermItem, p)
                # Where is edge.endNodes updated??? (old (node,port) removed, new added <<<<
                edge.endNodes.remove(self.oldTermItem)
                #clear the old handle ending
                edge.endNodes.remove((self.handle,self.handle))
                #set the new one
                edge.setEnd(newTermItem,edgeLine)
                #print(f"fmme after setEnd edge endNodes are {[type(n[0]) for n in edge.endNodes]}")
                self.model.Gr.updateEdge(edge.data(KEY_INDEX) ,self.oldTermItem[0].data(KEY_INDEX), "end", newTermItem[0].data(KEY_INDEX))
                
                newTermItem[0].endsEdges.append(edge)
                newTermItem[1].endsEdgeLines.append(edgeLine)        
        else: # link back to old
            #print("Missed (nothing found) on relink")
            self.handle.setPos(self.oldTermItem[1].scenePos())
            
            #TODO: Check all the linkages ()
            if self.EdgeEnd == "start":
                edgeLine = self.oldTermItem[1].startsEdgeLines[0]
                edge.setStart(self.oldTermItem,edgeLine)
            else:  #end
                edgeLine = self.oldTermItem[1].endsEdgeLines[0]
                edge.setEnd(self.oldTermItem,edgeLine)

        self.handle = None

    def clearEdgeOnly(self, edge):
        """ No longer used
            Remove the controlboxes from an edge and deselect."""
        #TODO: Generalise to items, for blob handles

        #For edges, was there only one selected? Clear.
        edge.isOnlySelected = None

        #Clear the scene selection too
        self.onlySelected = None

        #clear any pointers to handles
        #HACK: func needs to be generalised to blobs. use getAttribute() for blobs for now
        #if edge.stH:
        if getattr(edge,'stH',None):
            edge.setZValue(0) #below nodes
            edge.stH = None
        #if edge.endH:
        if getattr(edge,'endH',None):
            edge.endH = None
        #HACK: deal with blobs better
        if getattr(edge,'edgeLine',None):
            edge.edgeLine.setSelected(False)
        edge.setSelected(False)

    def qtListToListOfIdxs(self, qtList):
        #qtlist is any list of item objects (that have data(KEY_INDEX))
        outlist=[]
        for t in qtList:
            try:
                outlist.append(t.data(KEY_INDEX))
            except:
                pass
        outlist.sort()
        return(outlist)
    
    def qtTreeToListOfIdxs(self, qtList):
        #qttreelist is any list of item objects (that have data(0,KEY_INDEX))
        outlist=[]
        for t in qtList:
            try:
                outlist.append(t.data(0,KEY_INDEX))
            except:
                pass
        outlist.sort()
        return(outlist)
    
    def savePosition(self, selection):
        infoList=[]
        for item in selection:
            if item.data(KEY_ROLE)==ROLE_NODE:
                saveItem=[item.data(KEY_INDEX), item.data(KEY_ROLE), item.scenePos()]
                infoList.append(saveItem)
            elif item.data(KEY_ROLE)==ROLE_BLOB:
                saveItem=[item.data(KEY_INDEX), item.data(KEY_ROLE), item.scenePos(), (item._width, item._height)]
                infoList.append(saveItem)
        return(infoList)
    
    def rePosition(self, infoList):
        #NB the port update code comes from node itemchange
        item=self.findItemByIdx(infoList[0][0])
        if item.scenePos()!=infoList[0][2] or (item.data(KEY_ROLE)==ROLE_BLOB and infoList[0][3]!=(item._width, item._height)): 
        #unless this is a redo, the move/resize has already happened   
        #update position
            for itemInfo in infoList:
                item=self.findItemByIdx(itemInfo[0])
                item.setPos(itemInfo[2])
                if item.data(KEY_ROLE)==ROLE_BLOB and itemInfo[3]!=(item._width, item._height):
                    if len(item._Handles)==0:
                        item._createHandles() 
                        handlesMade=True
                    else:
                        handlesMade=False                       
                    #NB this code comes from _updatefromhandles (modified)
                    item.suppressItemChange = True
                    item.prepareGeometryChange()
                    item._width=itemInfo[3][0]
                    item._height=itemInfo[3][1]
                    item._Handles[VisBlobItem.TL].setPos(0,0)
                    item._Handles[VisBlobItem.TR].setPos(item._width, 0)
                    item._Handles[VisBlobItem.BR].setPos(item._width, item._height)
                    item._Handles[VisBlobItem.BL].setPos(0, item._height)
                    #resize text when blob resizes
                    item.blobDescription.setTextSize(item)
                    #Figure out the geometry for these lines
                    item._rect=QRectF(0,0,item._width,item._height)
                    item.nodeShape.setRoundedRect(QRectF(0,0,item._width,item._height))
                    #Create a polygon version for `parameterFromPos`
                    item.updatePorts()
                    item.suppressItemChange = False
                    if handlesMade:
                        item._deleteHandles()
                for port in item._Ports:
                    for sEdgeLine in port.startsEdgeLines:
                        sEdgeLine.parentItem().updateLine((self,port),sEdgeLine)
                    for eEdgeLine in port.endsEdgeLines:
                        #eEdge.updateLine((self, port),eEdgeLine)
                        eEdgeLine.parentItem().updateLine((self, port),eEdgeLine)
        #update treewidget
        directParentDic=self.getDirectParentDic()   
        for itemInfo in infoList:
            item=self.findItemByIdx(itemInfo[0])
            oldParents=set(self.model.Gr.nodeD[itemInfo[0]].parents)
            if itemInfo[0] in directParentDic:
                newParents=set(directParentDic[itemInfo[0]])
            else:
                newParents=set([])
            if oldParents != newParents:
                itemsInTree=self.treeWidget.findItems(str(itemInfo[0]), Qt.MatchRecursive, 1)
                itemInTree=itemsInTree[0]       
                if newParents==set([]):
                    self.model.Gr.nodeD[itemInfo[0]].resetParents([])
                    self.treeWidget.addTopLevelItem(QTreeWidgetItem.clone(itemsInTree[0]))
                else:
                    self.model.Gr.nodeD[itemInfo[0]].resetParents(directParentDic[itemInfo[0]])
                    parentsToAdd=list(newParents-oldParents)
                    for p in parentsToAdd:
                        #find parent in tree
                        parentsInTree=self.treeWidget.findItems(str(p), Qt.MatchRecursive, 1)
                        for parentInTree in parentsInTree:
                            newChildClone=QTreeWidgetItem.clone(itemInTree)
                            parentInTree.addChild(newChildClone)
                        self.model.Gr.nodeD[p].addChild((itemInfo[0]))
                if oldParents==set([]):
                    itemExact=self.treeWidget.findItems(str(itemInfo[0]), Qt.MatchExactly, 1)
                    itemIdx=self.treeWidget.indexOfTopLevelItem(itemExact[0])
                    itemTaken=self.treeWidget.takeTopLevelItem(itemIdx)
                else:
                    parentsToRemove=list(oldParents-newParents)
                    for p in parentsToRemove:
                        #find parent in tree
                        parentsInTree=self.treeWidget.findItems(str(p), Qt.MatchRecursive, 1)
                        for parentInTree in parentsInTree:
                            removedChildren=parentInTree.takeChildren()
                            for i in itemsInTree:
                                if i in removedChildren:
                                    removedChildren.remove(i)
                            parentInTree.addChildren(removedChildren)
                            #parentInTree.takeChild(parentInTree.indexOfChild(itemsInTree[0]))  #check that this removes correctly
                        self.model.Gr.nodeD[p].delChild(itemInfo[0])
            #check for any children that have not been picked up already
            newKidsIdx=set(self.getDirectContainmentGraph(self.getContainmentMap(item))[itemInfo[0]])
            oldKidsIdx=set(self.model.Gr.getDescendents(itemInfo[0]))
            #if newKidsIdx==set([]) and oldKidsIdx==set([]):
               # kidsToDo=[]
           # else:
            kidsToDo=list(newKidsIdx|oldKidsIdx)
            for kid in kidsToDo:
                if kid not in directParentDic:
                    directParentDic[kid]=[]
                if directParentDic[kid]!= self.model.Gr.nodeD[kid].parents:
                    oldParents=set(self.model.Gr.nodeD[kid].parents)
                    if kid in directParentDic:
                        newParents=set(directParentDic[kid])
                    else:
                        newParents=set([])
                    if oldParents != newParents:
                        itemsInTree=self.treeWidget.findItems(str(kid), Qt.MatchRecursive, 1)
                        itemInTree=itemsInTree[0]       
                        if newParents==set([]):
                            self.model.Gr.nodeD[kid].resetParents([])
                            self.treeWidget.addTopLevelItem(QTreeWidgetItem.clone(itemsInTree[0]))
                        else:
                            self.model.Gr.nodeD[kid].resetParents(directParentDic[kid])
                            parentsToAdd=list(newParents-oldParents)
                            for p in parentsToAdd:
                                #find parent in tree
                                parentsInTree=self.treeWidget.findItems(str(p), Qt.MatchRecursive, 1)
                                for parentInTree in parentsInTree:
                                    newChildClone=QTreeWidgetItem.clone(itemInTree)
                                    parentInTree.addChild(newChildClone)
                                self.model.Gr.nodeD[p].addChild(kid)
                        if oldParents==set([]):
                            itemExact=self.treeWidget.findItems(str(kid), Qt.MatchExactly, 1)
                            itemIdx=self.treeWidget.indexOfTopLevelItem(itemExact[0])
                            itemTaken=self.treeWidget.takeTopLevelItem(itemIdx)
                        else:
                            parentsToRemove=list(oldParents-newParents)
                            for p in parentsToRemove:
                                #find parent in tree
                                parentsInTree=self.treeWidget.findItems(str(p), Qt.MatchRecursive, 1)
                                for parentInTree in parentsInTree:
                                    removedChildren=parentInTree.takeChildren()
                                    for i in itemsInTree:
                                        if i in removedChildren:
                                            removedChildren.remove(i)
                                    parentInTree.addChildren(removedChildren)
                                    #parentInTree.takeChild(parentInTree.indexOfChild(itemsInTree[0]))  #check that this removes correctly
                                self.model.Gr.nodeD[p].delChild(kid)

            #kids=[]
            #for k in kidsIdx:
            #    kids.append(self.findItemByIdx(k))
            
            
                
        return
    
    def clearSelection(self):
        for item in self.selectedItems():
            item.isOnlySelected=False
        return super().clearSelection()
        
    def mousePressEvent(self, mouseEvent):
        if mouseEvent.scenePos() == self._lastMouseClickPos:
            mouseEvent.accept()
            return
        self.savedPositionList=[]
        mPos = mouseEvent.scenePos()
        #Track the last mouse position for Pointer moves
        self._lastMousePos = mPos
        #save the last click position
        self._lastMouseClickPos = mPos

        #print(f"Press {self.mouseMode =}")
        #print(f"\nStart mousePress {len(self.selectedItems())=}",end = ' ')
        #for s in self.selectedItems():
        #    print(type(s),end = ",")
        #print()

        #Throw away the second single click from a double click.
        if self.mouseMode == self.DOUBLECLICK:
            self.mouseMode = self.POINTER
            mouseEvent.accept()
            return
        if (mouseEvent.button() == Qt.MouseButton.LeftButton):
            if mouseEvent.modifiers() == Qt.KeyboardModifier.ControlModifier and \
                    self.mouseMode==self.POINTER and len(self.selectedItems())>0:
                selItem = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_EDGE,ROLE_NODE,ROLE_BLOB])
                #print(f"scene MPE first if {selItem}")
                if selItem:
                    selItem = selItem[0]
                    selItem.setSelected(True)
                    if self.thisHandleObjectSelected:
                        self.thisHandleObjectSelected.isOnlySelected=False
                        if self.thisHandleObjectSelected.data(KEY_ROLE)==ROLE_POLYLINE:
                            self.thisHandleObjectSelected.parentItem().isOnlySelected=False  #to squash tangent lines
                        self.thisHandleObjectSelected._deleteHandles()
                        self.thisHandleObjectSelected=None
                    #tWItem = self.treeWidget.findItemByIdx(selItem.data(KEY_INDEX))
                    self.changedByCode=True
                    self.mainwindow.setCurrentTreeItems(selItem.data(KEY_INDEX),QItemSelectionModel.SelectionFlag.Toggle)
                    self.changedByCode=False
                    super().mousePressEvent(mouseEvent)
                    return
                
            if mouseEvent.modifiers() == Qt.KeyboardModifier.AltModifier and\
                    self.mouseMode==self.POINTER:  #select blob and children
                selItem = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_BLOB])
                #print(f"scene MPE first if {selItem}")
                if selItem:
                    selItem = selItem[0]
                    self.clearSelection()
                    self.treeWidget.clearSelection()
                    if self.thisHandleObjectSelected:
                        self.thisHandleObjectSelected.isOnlySelected=False
                        self.thisHandleObjectSelected._deleteHandles()
                        self.thisHandleObjectSelected=None  
                    selItem.setSelected(True)              
                    #tWItem = self.treeWidget.findItemByIdx(selItem.data(KEY_INDEX))
                    self.changedByCode=True
                    self.mainwindow.setCurrentTreeItems(selItem.data(KEY_INDEX),QItemSelectionModel.SelectionFlag.Toggle)
                    self.changedByCode=False
                    kidsIdx=(self.getContainmentMap(selItem))[selItem.data(KEY_INDEX)]
                    insideItems=[]
                    for k in kidsIdx:
                        insideItems.append(self.findItemByIdx(k))
                    #insideItems=self.itemsHere(mPos,QSize(selItem._width, selItem._height),[ROLE_BLOB, ROLE_NODE])
                    self.changedByCode=True
                    for insideItem in insideItems:
                        if insideItem != selItem:
                            insideItem.setSelected(True)
                            #tWItem = self.treeWidget.findItemByIdx(insideItem.data(KEY_INDEX))
                            self.mainwindow.setCurrentTreeItems(insideItem.data(KEY_INDEX),QItemSelectionModel.SelectionFlag.Toggle)
                    self.changedByCode=False
                    super().mousePressEvent(mouseEvent)
                    return
     
            if self.mouseMode==self.POINTER:
                selItems = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_HANDLE])
                if len(selItems) > 0:
                    selItem=selItems[0]
                    p = selItem.parentItem()
                    #it's a handle, process

                    #selItem.setSelected(True)   JH Handles aren't selectable
                    # p = selItem.parentItem() #GH - moved to top
                    #p.setSelected(True)  JH should already be selected
                    #p._createHandles()   #JH to figure out blobs testing
                    # p.parentItem.setSelected(True)
                    if p.data(KEY_ROLE) == ROLE_POLYLINE and (selItem == p._pHandles[0] or selItem == p._pHandles[-1]):
                        
                        #Is it a dummyNode?
                        #Only invoke `MovingEdgeEnd` if this is an edge-node cxn, not a edge-dummyNode
                        #Which point the handles comes from
                        # handle.parentItem is polyLine, which has a list of points, _p. _p[0] is start, _p[-1] end.
                        handle = selItem  #local
                        edge = selItem.parentItem().parentItem()#p has to be an edge at this point
                        edgeLine = selItem.parentItem() 
                        startPt = edgeLine._pHandles.index(selItem) #handle)
                        isDummyNode = False
                        for d in edge.dummyNodes: 
                            if d[0].pos() == edgeLine._p[startPt]: #Note: dummyNodes will start AND end
                                dummyNode = d[0]
                                isDummyNode = True
                                break
                        if isDummyNode:
                            self.handle = handle
                            self.mouseMode = self.MOVEHANDLE
                            handle.setMoveCallback(dummyNode._updateFromHandles)
                            
                        else: #We have a normal handle to process
                            self.mouseMode = self.MOVEEDGEEND
                            #Start move
                            #selHandles  _Must_ be a handle, and parent must be a visEdge - deal with the polyline inbetween
                            self.startMovingEdgeEnd(selItem.parentItem().parentItem(), selItem)
                    else: #tangent or Mid point, or Blob corner to move
                        self.handle = selItem
                        self.mouseMode = self.MOVEHANDLE
                        if p.data(KEY_ROLE) == ROLE_BLOB:
                            self.savedPositionList=self.savePosition([p])
                            selItem.setMoveCallback(p._updateFromHandles)  
                            selItem.parentItem().removeGroup("group")
                        #BUG - DRagging - this stops dragging from an edge, but not having it breaks tangent update values
                        #mouseEvent.accept()
                        #return
                    mouseEvent.accept()
                    return
            itemsClicked=self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_BLOB, ROLE_NODE, ROLE_EDGE])
            if len(self.selectedItems())>1 and len(itemsClicked) != 0 and itemsClicked[0] in self.selectedItems():
                self.mouseMode=self.DRAGGING #or in the middle of a modifier selection
                self.dragEdge=None
                if len(self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_BLOB, ROLE_NODE]))==0:
                    edgeItems = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_EDGE])  #find out if a line is being dragged
                    if len(edgeItems)>0 and edgeItems[0] in self.selectedItems():
                        self.dragEdge=edgeItems[0]
                    else:
                        self.mouseMode=self.POINTER    #the mouse is no longer over the selected items
                # hand over to QT? or exit?
                #save current position for undo
                self.savedPositionList=self.savePosition(self.selectedItems())
                super().mousePressEvent(mouseEvent)
                return
            # in all other cases clear selection
            self.clearSelection()
            #self.listWidget.clearSelection()
            self.treeWidget.clearSelection()
            if self.thisHandleObjectSelected:
                self.thisHandleObjectSelected._deleteHandles()
                self.thisHandleObjectSelected=None               

            # process menu insert objects
            if self.mouseMode == self.INSERTNODE:
                #TODO: For blobs, this will have to move to mouseRelease, to allow rectangle drag
                #Items sizes should be relative to (0,0)
                mPos = mouseEvent.scenePos()
                #VisNodeItem adds to the model and the  list
                ###item = VisNodeItem(mPos, self.model,self.listWidget)
                ###item.setPos(mPos)
                #Add to *Scene*
                ###self.addItem(item)

                ###item.setFlag(QGraphicsItem.ItemIsSelectable, True)
                ###item.setFlag(QGraphicsItem.ItemIsMovable, True)

                #put create node on undo stack
                newAction=createNodeCommand(mPos, self, self.model, self.treeWidget, type=ROLE_NODE)
                self.undoStack.push(newAction)

                #TODO: Should this be actionPointer, to update the toolbar, etc
                self.mouseMode = self.POINTER
                mouseEvent.accept()
                return
            #
            if self.mouseMode == self.INSERTBLOB:
                self.startPoint = mouseEvent.scenePos()
                #TODO: Create the blob here, and draw a proper blob for creation, not a rect
                
            #
            if self.mouseMode == self.INSERTEDGE:
                itm = self.pickItemAt(mouseEvent,QSizeF(10,10),[ROLE_NODE, ROLE_BLOB, ROLE_EDGE]) #
                if itm:
                    self.tmpEdgeSt = itm
                    self.startRubberLine(mPos)
                else: #Miss
                    self.tmpEdgeSt = None
                mouseEvent.accept()
                return
            #
            #This is the end of a 2-click-insert (via pickItem) -  means END the rubberBanding, create the edge 
            if self.mouseMode == self.INSERTEDGE2CLICK: 
                itm = self.pickItemAt(mouseEvent,QSizeF(10,10),[ROLE_NODE, ROLE_BLOB, ROLE_EDGE]) #
                if itm:
                    self.tmpEdgeEnd = itm 
                    self.endPoint = mPos
                    self.endRubberLine()
                self.resetRubberLine()
                self.mouseMode = self.POINTER
                mouseEvent.accept()
                return
            #
            # Now process item selection
            if self.mouseMode == self.POINTER:
                selItem = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_EDGE,ROLE_HANDLE,ROLE_NODE,ROLE_BLOB])
                if selItem:
                    selItem = selItem[0]
                #else:
                    #selItem = None
                    if selItem.isHovered:   #This stops it selecting just out of reach of the border line
                        if selItem.data(KEY_ROLE) == ROLE_NODE:
                            self.changedByCode=True
                            #lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))
                            #self.listWidget.setCurrentItem(lWItem)
                            self.mainwindow.setCurrentTreeItems(selItem.data(KEY_INDEX),QItemSelectionModel.SelectionFlag.Select)
                            self.changedByCode=False
                            selItem.isOnlySelected = True
                            selItem.setSelected(True)
                            self.savedPositionList=self.savePosition([selItem])
                            #super().mousePressEvent(mouseEvent) JH commented out
                            #return JH commented out APril 11 2026
                        #immediately hand off for Qt to move
                        #BUG:Dragging With these on, DRAGGING doesn't happen, off, a single node select doesn't clear selection
                        #Solution: Move `isSelected` to mouseRelease, to allow for movement
                        #TODO: DRAGGING
                        #super().mousePressEvent(mouseEvent)
                        #return

                        if selItem.data(KEY_ROLE) == ROLE_BLOB:
                            #print(f"Sel Blob {selItem.metadata['name']}")
                            self.onlySelected = selItem
                            self.thisHandleObjectSelected=selItem
                            selItem.isOnlySelected = True
                            selItem.setSelected(True)
                            selItem._createHandles() #JH
                            self.changedByCode=True
                            #lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))
                            #self.listWidget.setCurrentItem(lWItem)
                            self.mainwindow.setCurrentTreeItems(selItem.data(KEY_INDEX),QItemSelectionModel.SelectionFlag.Select)
                            self.changedByCode=False
                            self.savedPositionList=self.savePosition([selItem])
                            # accept? return?

                        if selItem.data(KEY_ROLE) == ROLE_POLYLINE :
                            print(f"scene mousePress Polyline {selItem.lineNum}")
                            # save handleobject and create handles
                            self.thisHandleObjectSelected=selItem
                            self.onlySelected=selItem
                            selItem.setSelected(True)
                            parent = selItem.parentItem() 
                            parent.setSelected(True) #Select the Edge
                            parent.isOnlySelected = True
                            #TODO: Hyperedge - create handles on all the edgeLines
                            selItem._createHandles()
                            #This code leaves a lot of orphans, but is the ultimate goal
                            #Temp fix for hyperedges
                            #for eL in parent.edgeLines:
                            #    eL._createHandles()

                            #selItem.setSelected(False)
                            #selItem = parent
                            #selItem.setSelected(True) # check this
                        # super().mousePressEvent(mouseEvent)
                        # return
                        if selItem.data(KEY_ROLE) == ROLE_EDGE:
                            self.thisHandleObjectSelected=selItem
                            self.onlySelected=selItem
                            selItem.setSelected(True)
                            selItem.isOnlySelected=True
                            #parent = selItem.parentItem() 
                            #parent.setSelected(True) #Select the Edge
                            #parent.isOnlySelected = True
                            #TODO: Hyperedge - create handles on all the edgeLines
                            #print("running create")
                            selItem._createHandles()
                            if not selItem.stH:
                                selItem.setZValue(2000) #move the edge above nodes
                                # item.stHandle must be the 1st point handle: item.edgeLine._pHandles[0]
                                #print(" Setting stH", end="")
                                #print(f" clicked on {selItem.edgeLineAt(mPos)._pHandles}")
                                #Which edgeLine?
                                #if len(selItem.edgeLine._pHandles)>0:
                                if getattr(selItem.edgeLineAt(mPos),'_pHandles',False):
                                    if len(selItem.edgeLineAt(mPos)._pHandles)>0:
                                        selItem.stH = selItem.edgeLineAt(mPos)._pHandles[0]
                                        selItem.endH = selItem.edgeLineAt(mPos)._pHandles[-1]
                                    else:
                                        print("No handles yet")
                                else:
                                        print("No handles yet - _pHandle not defined")
                            self.changedByCode=True
                            #lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))
                            #self.listWidget.setCurrentItem(lWItem)
                            tWItem = self.treeWidget.findItemByIdx(selItem.data(KEY_INDEX))
                            self.treeWidget.setCurrentItem(tWItem)
                            self.changedByCode=False
                            # if not selItem.endH:
                            #print(", endH")
                            #     selItem.endH = selItem.edgeLine._pHandles[-1]
                            # will this ever be needed?
                            #selItem.setSelected(True) 
                            #selItem.isOnlySelected = True
                        #Let the scene remember, for unsetting
                            #self.onlySelected = selItem
                            mouseEvent.accept()
                            return

        if (mouseEvent.button() == Qt.MouseButton.RightButton):
            mPos = mouseEvent.scenePos()
            posText="Co ords ("+str(int(mPos.x()))+","+str(int(mPos.y()))+")"
            #selItem = self.itemAt(mPos,self.views()[0].transform())
            selItem = self.selectedItems()
            #TODO if selItem == None: selItem = itemAt
            # createContextMenu(mouseEvent, listOfTuples option:action)->action??
            cxMenu = None
            if len(selItem) == 1:
                item = selItem[0]
                
                if item.data(KEY_ROLE) == ROLE_EDGE:
                    #Where to do the handles update for these?
                    cxMenu = [  (posText, None),
                                ("Add Point","addPt" ),
                                ("Delete Point","delPt" )]
                    if len(item.edgeLines) > 1 :  #Only offer delete if meaningful
                        cxMenu.append(("Delete Segment","delSegment"))
                    cxMenu.append( ("Edit Details", lambda: self.mainwindow.showEditEdgeDialog(item)) )
                    cxMenu.append( ("Print HyperEdge structure", lambda: print(f"{item.edgeNum=} {item.hyperEdgeGraph()}")) )
                            
                if item.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                    cxMenu = [  (posText, None),
                              (("Edit Details", 
                                lambda: self.mainwindow.showEditNodeDialog(item)))
                            ]
            else: #no or >1 selected.
                cxMenu =[(posText, None),
                         ("print",lambda: MainWindow.action_DebugPrint(MainWin))]

            if cxMenu:
                cxChoice = self.contextMenu(mouseEvent, cxMenu)

                #Adding & deleting points impacts selection, so deal with carefully
                if cxChoice == "addPt":
                    edgeLine = item.edgeLineAt(mPos)
                    edgeLine._deleteHandles()
                    edgeLine.addPoint(mPos)
                    edgeLine.setSelected(True)

                elif cxChoice == "delPt":
                    edgeLine = item.edgeLineAt(mPos)
                    edgeLine.deletePoint(mPos)
                    item.setSelected(True)
                    item.update()

                elif cxChoice == "delSegment":
                    edgeLine = item.edgeLineAt(mPos)
                    edgeLine._deleteHandles()                    
                    item.delSegment(edgeLine)
                    #TODO: Sort out handle selection
                    item.setSelected(True)
                    item.update()

                #if a lambda, run it
                if callable(cxChoice):
                    cxChoice()

        #pass on

        super().mousePressEvent(mouseEvent)

    def mouseMoveEvent(self, mouseEvent):
        mPos = mouseEvent.scenePos()
        #print(f"M: {self.mouseMode} ",end="",flush=True)
        delta = mPos - self._lastMousePos
        self._lastMousePos = mPos 

        #Hovering would be nice, but this gets the job done.
        #Just filter for valid items:
        items=self.itemsHere(mPos, QSize(HITSIZE,HITSIZE), [ROLE_NODE, ROLE_BLOB, ROLE_EDGE])
        #if len(items)>=1: print(f"{[type(_) for _ in items]=}")
        if items != [] and (self.mouseMode in (self.INSERTEDGE, self.INSERTEDGE2CLICK, self.MOVEEDGEEND)):
            self.views()[0].setCursor(Qt.CrossCursor)
        else:
            self.views()[0].setCursor(Qt.ArrowCursor)

        if self.mouseMode == self.INSERTNODE:
            #print("moving at :",mouseEvent.scenePos())
            #print("n" , end ="")
            pass
        elif self.mouseMode == self.INSERTEDGE or self.mouseMode == self.INSERTEDGE2CLICK:
            #print("Ins edge move")
            #Rubber band the edge
            #print(f">",end="")
            if self.tmpEdgeSt:
                self.stretchRubberLine(mPos)
                mouseEvent.accept()
            
        elif self.mouseMode == self.POINTER:
            #Mostly handled by Qt
            pass
        
        #manually handle click drag (This _could_ be another state, but only used here)
        #elif self.mouseMode == self.DRAGGING: # and mouseEvent.buttons() & Qt.LeftButton:
        if self.mouseMode == self.DRAGGING:# and (mouseEvent.buttons() & Qt.LeftButton):
            #Handle edges with multiple points - update the points
            sIlist = self.selectedItems()
            #print(f"->{len(sIlist)}",end="")
            if len(sIlist) > 2: #high probability of an edge in the mix
                for item in sIlist:
                    if item.data(KEY_ROLE) == ROLE_EDGE:
                        #move hyperEdge dummyNodes if they exist, before the `updatePath()`
                        for dN in item.dummyNodes:
                            #print(f"dN {dN[0].nodeNum} sPos{dN[0].pos()} + d {delta} = {dN[0].pos() + delta} move)")
                            dN[0].setPos(dN[0].pos() + delta)
                            #print(f" {item.edgeLines[0]._p[-1]=} "
                            pass
                        
                        for eL in item.edgeLines:
                            eL.moveMidPoints(delta)
                            eL.updatePath()
                            pass
                        if item==self.dragEdge:
                            for node in sIlist:
                                if node.data(KEY_ROLE) in [ROLE_BLOB, ROLE_NODE]:
                                    node.setPos(node.scenePos()+delta)

            
        elif self.mouseMode == self.MOVEEDGEEND:
            #self.MoveEdgeEnd(self.onlySelected.parentItem(),mPos)
            self.MoveEdgeEnd(self.thisHandleObjectSelected,mPos)
            mouseEvent.accept()
            
        elif self.mouseMode == self.MOVEHANDLE:
            #print("Move Handle")
            #Same code as moveEdgeEnd
            self.handle.setPos(mPos) 
              
        super().mouseMoveEvent(mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        mPos = mouseEvent.scenePos()
        #print(f"release {self.mouseMode =}")

        if self.mouseMode == self.INSERTNODE:
            #print("Node release at :",mouseEvent.scenePos())
            #print("up node")
            #TODO: Clear selection after adding a node (or before?)
            self.clearSelection()
            #self.updateBlobParenting()
            self.mouseMode = self.POINTER
            return # Or use the eventHandled method?
        elif self.mouseMode == self.INSERTBLOB:
            #add the  Blob
            #TODO: Check for parents/ children - here, or itemChanged?
            # Drawing from BR to TL makes ellipse
            #Ensure startPoint is TL, mPos is BR
            TLx = self.startPoint.x()
            TLy = self.startPoint.y()
            BRx = mPos.x()
            BRy = mPos.y()
            if TLx < BRx:
                TLx,BRx = BRx, TLx
            if TLy < BRy:
                TLy, BRy = BRy, TLy
            height = TLy - BRy
            width = TLx - BRx
            TLx -= width
            TLy -= height
            newAction=createNodeCommand(QPointF(TLx,TLy), self, self.model, self.treeWidget, 
                                        height = height, width = width, xRadius = BLOB_CORNER_RADIUS, 
                                        yRadius = BLOB_CORNER_RADIUS, type=ROLE_BLOB)
            self.undoStack.push(newAction)
            #blob = VisBlobItem(QPointF(TLx,TLy),self.model, self.listWidget, 
            #                height = height, width = width,
            #                xRadius = BLOB_CORNER_RADIUS, yRadius = BLOB_CORNER_RADIUS)
            #self.addItem(blob)
            #self.updateBlobParenting()
            self.mouseMode = self.POINTER
            #creating a blob accidentally does a rubber band selection, so clear that
            self.clearSelection()
            mouseEvent.accept()
            return
        elif self.mouseMode == self.INSERTEDGE:
            #print("up edge")
            #CreateEdge code 
            #TODO: Put this in its own function
            if self.tmpEdgeSt:
                itm = self.pickItemAt(mouseEvent,QSizeF(10,10),[ROLE_NODE,ROLE_BLOB, ROLE_EDGE])
                if itm:
                    #For now, disallow self edges/ loops
                    #TODO: When they are allowed, note that tangent calc breaks.
                    if self.tmpEdgeSt != itm:
                        self.tmpEdgeEnd = itm 
                        self.endPoint = mPos
                        self.endRubberLine()

                #Clean up
                self.resetRubberLine()
                #Force a redraw
                self.update()
            self.mouseMode = self.POINTER
            #Reset the cursor
            self.views()[0].setCursor(Qt.ArrowCursor)
            self.clearSelection()
            #done processing - bail
            return

        elif self.mouseMode == self.POINTER:
            if len(self.selectedItems()) > 0:
                if mouseEvent.modifiers():
                    return
                self.treeWidget.clearSelection()
                self.changedByCode=True
                for selItem in self.selectedItems():
                    self.mainwindow.setCurrentTreeItems(selItem.data(KEY_INDEX),QItemSelectionModel.SelectionFlag.Select)                          
                self.changedByCode=False
                if self.savedPositionList != []:
                    newAction=moveNodeCommand(self.savedPositionList, self.savePosition(self.selectedItems()), self, self.model, self.treeWidget)
                    self.undoStack.push(newAction)

                    #self.rePosition(self.savedPositionList)
                # print("up select at", mouseEvent.scenePos())
                #if len(self.selectedItems()) == 2:
                #    for s in self.selectedItems():
                #        print(s)
                #else:
                #    print(f"{len(self.selectedItems())} items selected")
                #print(f"{len(self.selectedItems())=}",end = ' ')
                #for s in self.selectedItems():
                #    print(type(s),end = ",")
                #print()
                #pass
            #MainWindow.actionSceneSelectChange(MainWindow.Scene)
        elif self.mouseMode == self.MOVEEDGEEND:
            #print("Finish moveEdgeEnd")
            #self.finishMovingEdgeEnd(self.onlySelected.parentItem(), mPos,mouseEvent)
            self.finishMovingEdgeEnd(self.thisHandleObjectSelected, mPos,mouseEvent)
            self.mouseMode = self.POINTER
            self.views()[0].setCursor(Qt.ArrowCursor)
            mouseEvent.accept()
            #return
        elif self.mouseMode == self.MOVEHANDLE:
            #SHOULD all be handled by Qt? or callback?
            #print("End move handle")
            if self.savedPositionList != []:
                newAction=moveNodeCommand(self.savedPositionList, self.savePosition(self.selectedItems()), self, self.model, self.treeWidget)
                self.undoStack.push(newAction)
            self.mouseMode = self.POINTER
        elif self.mouseMode == self.DRAGGING:
            if self.qtListToListOfIdxs(self.selectedItems()) != self.qtTreeToListOfIdxs(self.treeWidget.selectedItems()):
                #update treeview
                self.treeWidget.clearSelection()
                self.changedByCode=True
                for selItem in self.selectedItems():
                    tWItem = self.treeWidget.findItemByIdx(selItem.data(KEY_INDEX))  
                    self.treeWidget.setCurrentItem(tWItem, 0, QItemSelectionModel.SelectionFlag.Select)
                self.changedByCode=False
            #print(f"up: DRAGGING --> POINTER")
            self.mouseMode = self.POINTER
            if self.savedPositionList != []:
                newAction=moveNodeCommand(self.savedPositionList, self.savePosition(self.selectedItems()), self, self.model, self.treeWidget)
                self.undoStack.push(newAction)
            #self.rePosition(self.savedPositionList)
        #Only do this on release, for performance reasons.
        #self.updateBlobParenting()

        super().mouseReleaseEvent(mouseEvent)  

    def mouseDoubleClickEvent(self, mouseEvent: QGraphicsSceneMouseEvent) -> None:
        if mouseEvent.button() == Qt.LeftButton:
            pos: QPointF = mouseEvent.scenePos()
            self.mouseMode = self.DOUBLECLICK
            #print(f"Double-click at {pos}")
            item = self.pickItemAt(mouseEvent,QSize(HITSIZE,HITSIZE),[ROLE_EDGE,ROLE_NODE,ROLE_BLOB])
            if item and item.data(KEY_ROLE) == ROLE_EDGE:
                #self.clearEdgeOnly(item)
                #Pass the edit signal to Mainwindow.
                #print(f"{item.requestEdit.connect=}, {self.mainwindow.showEditEdgeDialog=}")
                #item.requestEdit.connect(self.mainwindow.showEditEdgeDialog)   #edgeEditRequested.emit)
                #item.requestEdit.connect(self.edgeEditRequested.emit)
                #Even this simple test doesn't work
                #item.requestEdit.connect(self.signalTest)
                #HACK: Call the dialog directly. Signals would be better
                self.mainwindow.showEditEdgeDialog(item)

            #print(f"{item=}")
            if item and item.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                self.mainwindow.showEditNodeDialog(item)
            
            self.mouseMode = self.POINTER

            mouseEvent.accept()
            #super().mouseDoubleClickEvent(mouseEvent)

    def getDirectContainmentGraph(self, containmentMap):
        """
        Reduces a total containment map (dictionary of lists) to a direct parent-child adjacency list.
        Input: {0: [1, 2], 1: [2], 2: []}
        Output: {0: [1], 1: [2], 2: []}
        Helper for `updateBlobParenting`
        """
        #Gemini
        
        directChildList = {}

        for parent, descendants in containmentMap.items():
            # Start by assuming all descendants are potential direct children
            #TODO: Does this need to use `item` handles rather than indexes. Both work. INdexes are more human readable, `items` will avoid a lookup later
            directChildren = set(descendants)
            
            # For every descendant 'a', check if it is contained by any OTHER descendant 'b'
            for a in descendants:
                for b in descendants:
                    if a == b:
                        continue
                    
                    # If b contains a, then a is a grandchild of 'parent', not a direct child
                    # We check the original containmentMap to see b's full list of descendants
                    if a in containmentMap.get(b, []):
                        directChildren.discard(a)
                        break 
            
            directChildList[parent] = list(directChildren)
            
        return directChildList
    
    def getDirectParentDic(self):
        #Get all the blobs, to search inside of:
        blobList = []
        for sItem in self.items():
            if sItem.data(KEY_ROLE) in [ROLE_BLOB]:
                blobList.append(sItem)              
        #Gemini structure
        containmentMap = {}
        for b in blobList:
            searchArea = b.sceneBoundingRect()
            itemsInside = self.items(searchArea, mode=Qt.ItemSelectionMode.ContainsItemShape )
            childBlobs = []
            for item in itemsInside:
                if item != b and item.data(KEY_ROLE) in [ROLE_BLOB,ROLE_NODE]:
                    childBlobs.append(item.nodeNum)
            containmentMap[b.nodeNum] = childBlobs
        """
        Reduces a total containment map (dictionary of lists) to a direct child:[parent] dictionary.
        Input: {0: [1, 2], 1: [2], 2: []}
        Output: {1:[0], 2: [1]}
    
  
        """
  
        
        directParentDic = {}

        for ancestor, descendants in containmentMap.items():  
            # Start by assuming all descendants are potential direct children
            #TODO: Does this need to use `item` handles rather than indexes. Both work. INdexes are more human readable, `items` will avoid a lookup later
            directChildren = set(descendants)
            
            # For every descendant 'a', check if it is contained by any OTHER descendant 'b'
            for a in descendants:
                for b in descendants:
                    if a == b:
                        continue
                    
                    # If b contains a, then a is a grandchild of 'parent', not a direct child
                    # We check the original containmentMap to see b's full list of descendants
                    if a in containmentMap.get(b, []):
                        directChildren.discard(a)
                        break 
            
            for a in list(directChildren):
                if a in directParentDic:
                    directParentDic[a].append(ancestor)
                else:
                    directParentDic[a]=[ancestor]
            
        return directParentDic

    def getContainmentMap(self, blob):
        containmentMap = {}
        searchArea = blob.sceneBoundingRect()
        itemsInside = self.items(searchArea, mode=Qt.ItemSelectionMode.ContainsItemShape )
        childBlobs = []
        for item in itemsInside:
            if item != blob and item.data(KEY_ROLE) in [ROLE_BLOB,ROLE_NODE]:
                childBlobs.append(item.nodeNum)
        containmentMap[blob.nodeNum] = childBlobs
        return(containmentMap)
    
    def getDirectChildDic(self):
        """Recalculate the parents & children of the blobs and nodes in the scene"""
        #Get all the blobs, to search inside of:
        blobList = []
        for sItem in self.items():
            if sItem.data(KEY_ROLE) in [ROLE_BLOB]:
                blobList.append(sItem)
                
        #Gemini structure
        containmentMap = {}
        for b in blobList:
            searchArea = b.sceneBoundingRect()
            itemsInside = self.items(searchArea, mode=Qt.ItemSelectionMode.ContainsItemShape )
            childBlobs = []
            for item in itemsInside:
                if item != b and item.data(KEY_ROLE) in [ROLE_BLOB,ROLE_NODE]:
                    childBlobs.append(item.nodeNum)
            containmentMap[b.nodeNum] = childBlobs
        #Find the immediate parents.
        directChildDic = self.getDirectContainmentGraph(containmentMap)
        return(directChildDic)



    def updateBlobParenting(self):
        print("running blob paretning")
        """Recalculate the parents & children of the blobs and nodes in the scene"""
        #Get all the blobs, to search inside of:
        blobList = []
        for sItem in self.items():
            if sItem.data(KEY_ROLE) in [ROLE_BLOB]:
                blobList.append(sItem)
                
        #Gemini structure
        containmentMap = {}
        for b in blobList:
            searchArea = b.sceneBoundingRect()
            itemsInside = self.items(searchArea, mode=Qt.ItemSelectionMode.ContainsItemShape )
            childBlobs = []
            for item in itemsInside:
                if item != b and item.data(KEY_ROLE) in [ROLE_BLOB,ROLE_NODE]:
                    childBlobs.append(item.nodeNum)
            containmentMap[b.nodeNum] = childBlobs
        #Find the immediate parents.
        directChildList = self.getDirectContainmentGraph(containmentMap)

        #Reset parents & children 
        for sItem in self.items():
            if sItem.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                #print(f"reseting {sItem.nodeNum}")
                ##sItem.parents = [] JH
                ##sItem.children = [] JH
                self.model.Gr.nodeD[sItem.nodeNum].resetParents([])
                self.model.Gr.nodeD[sItem.nodeNum].resetChildren([])
        
        #Recreate lists 
       
        for parent, children in sorted(directChildList.items()):
            ##pItem = self.findItemByIdx(parent) JH
            self.model.Gr.nodeD[parent].resetChildren(children)

            #print(f"-------------{parent=} {type(pItem)}")
            for c in children:
                ##cItem = self.findItemByIdx(c) JH
                #print(f"adding child {c=}, {type(cItem)}")

                ##if not cItem is None: JH
                    ## pItem.children.append(cItem) JH
                self.model.Gr.nodeD[c].addParent(parent)
                    ##cItem.parents.append(pItem) JH
                ##else:  JH
                    ## print(f"Warning - node {c} seems to have disappeared!") JH

        # update Tree widget
        # parent items (top level)
        topLevelItems=[]
        for top in range(self.treeWidget.topLevelItemCount()):
            item=self.treeWidget.topLevelItem(top)
            topLevelItems.append(int(item.text(0)))
        topLevelSet=set(topLevelItems)
        parentSet=set(directChildList.keys())
        if topLevelSet != parentSet:
            #add any missing top level items
            for z in parentSet-topLevelSet:
                tWitem = QTreeWidgetItem([self.model.Gr.nodeD[z].metadata['name'],str(z), ROLE_NODE])
                tWitem.setIcon(2,self.Scene.mainwindow.NODE_ICON)
                tWitem.setData(0, KEY_INDEX,z)
                tWitem.setData(0, KEY_ROLE,ROLE_NODE)
                self.treeWidget.addTopLevelItem(tWitem)
            #remove any extra top level items                
            for z in topLevelSet-parentSet:
                tWitem=self.treeWidget.findItemByIdx(z)
                self.treeWidget.takeTopLevelItem(self.treeWidget.indexOfTopLevelItem(tWitem))
        # child items for each top level (parent)
        for top in range(self.treeWidget.topLevelItemCount()):
            item=self.treeWidget.topLevelItem(top)
            childLevelItems=[]
            for ch in range(item.childCount()):
                childItem=item.child(ch)
                childLevelItems.append(int(childItem.text(0)))
            childLevelSet=set(childLevelItems)
            if int(item.text(0)) in directChildList.keys():
                childSet=set(directChildList[int(item.text(0))])
            else:
                childSet=set([])
            if childLevelSet!=childSet:
                 #add any missing child level items
                for z in childSet-childLevelSet:
                    tWitem = QTreeWidgetItem([str(z), self.model.Gr.nodeD[z].metadata['name']])
                    tWitem.setData(0, KEY_INDEX,z)
                    tWitem.setData(0, KEY_ROLE,ROLE_NODE)
                    item.addChild(tWitem)  #figure out if this will allow adding twice
            #remove any extra top level items                
            for z in childLevelSet-childSet:
                tWitem=self.treeWidget.findItemByIdx(z)
                print("this is twitem", tWitem)
                item.takeChild(item.indexOfChild(tWitem))

    def signalTest(self):
        print("signal sent to scene successfully")

    def findItemByIdx(self,idx):
        """takes a ROLE_INDEX value, and return the item out, or none """
        for item in self.items():
            if item.data(KEY_INDEX) == idx:
                return item
        return None

    def deleteItemAndChildren(self,item):
        """ REmove the items from the scene
            assumes that the rest of the model links are dealt with
        """
        
        #print(f"   now processing dIC for {item}")
        item.suppressItemChange = True
        #unparent
        #item.setParentItem(None)
        # Remove from scene
        #if its an edge, tell the nodes ends that the edge is gone
        if item.data(KEY_ROLE) == ROLE_EDGE:
            for i in item.startNodes:
                i[0].startsEdges.remove(item)
                #EdgeLine references are removed by removing the port from the node
                #i[1].startsEdgeLines.remove(item)
            for i in item.endNodes:
                i[0].endsEdges.remove(item)
                #i[1].startsEdgeLines.remove(item)

        #unparent
        item.setParentItem(None)

        item.suppressItemChange = False  
        self.removeItem(item)
        del item

    def update(self):
        #print("scene updating")
        #logging.debug("Scene updating")
        super().update()

    #Part of tracking down the ghost lines - gc takes a while. forced gc crashes the whole thing.
    # Living with the ghost lines for now :/
    @staticmethod
    def _on_finalize(item_repr):
        print(f"[Finalize] {item_repr} has been garbage collected.")

# classes for working with undo and redo (QUndoStack)
class createNodeCommand(QUndoCommand):
    def __init__(self, posn, scene, model, treeWidget, width=10, height=10, xRadius=10, yRadius=10,type=ROLE_NODE):
        super().__init__()
        self.node = None  
        self.posn = posn
        self.scene = scene
        self.model = model
        #self.listWidget=listWidget
        self.treeWidget=treeWidget
        self.nodeNum = 0 #placeholder
        self.type=type
        if type==ROLE_BLOB:
            self.width=width
            self.height=height
            self.xRadius=xRadius
            self.yRadius=yRadius

    def undo(self):
        #delIdx = self.node.data(KEY_INDEX)
        #NB delNode deletes from treewidget
        delIdx = self.nodeNum
        self.scene.mainwindow.delNode(delIdx)

    def redo(self):
        #VisNodeItem/ VisBlobItem adds to the model and the  list
        if self.node==None:   # this is the first actual create of the node
            if self.type == ROLE_NODE:
                newNode =  VisNodeItem(self.posn,self.model, self.treeWidget)
                # save the node index for recreating identically
            else:
                newNode =  VisBlobItem(self.posn,self.model, self.treeWidget, height=self.height, width=self.width, 
                                       xRadius=self.xRadius, yRadius=self.yRadius)
            self.nodeNum = newNode.nodeNum
            #update port  PARENTS (maybe recompute position?)
            #for p in newNode._Ports:
            #    p.setParentItem(newNode.nodeShape)
        else:   # this is creation after deleting
            #newNode =  VisNodeItem(self.posn,self.node.model,self.node.listWidget ,nameP=self.node.metadata['name'], \
            #                   id = self.node.nodeNum, metadata=self.node.metadata, \
            #                    metadataAttributes=self.node.metadataAttributes, ports=self.node._Ports)
            if self.type == ROLE_NODE:
                newNode =  VisNodeItem(self.posn,self.model, self.treeWidget, id=self.nodeNum)
            else:
                newNode =  VisBlobItem(self.posn,self.model, self.treeWidget, id=self.nodeNum, \
                                       height=self.height, width=self.width, xRadius=self.xRadius,\
                                        yRadius=self.yRadius)
            
        #update port  PARENTS (maybe recompute position?)
        #for p in newNode._Ports:
        #    p.setParentItem(newNode)
        newNode.setPos(self.posn)
        #Add to *Scene*
        self.scene.addItem(newNode)

        # Now that it is added to scene parents can be found and treewidget updated
        self.scene.mainwindow.addTreeNode(newNode, self.type)
        
        newNode.setFlag(QGraphicsItem.ItemIsSelectable, True)
        newNode.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.node=newNode   

class deleteNodeCommand(QUndoCommand):
    def __init__(self, node, posn, scene, model, treeWidget, type=ROLE_NODE, parent=None):
        super().__init__(parent=parent)
        self.node = node
        self.nodeNum = self.node.nodeNum
        self.posn = posn
        self.scene = scene
        self.model = model
        #self.listWidget=listWidget
        self.treeWidget=treeWidget
        self.eList=[]
        for edge in self.model.edgesAtNode(self.node):
            self.eList.append(edge)
        #self.eList = self.model.edgesAtNode(self.node)
        self.edges=[]
        self.ports=[]
        for port in self.node._Ports:
            self.ports.append(port)

        for e in self.eList:
            self.points=[]
            self.tangentPoints=[]
            edgeItem = self.scene.findItemByIdx(e)
            if edgeItem.edgeLine._t:
                self.tangentPoints=edgeItem.edgeLine._t
            else:
                self.tangentPoints=[]
            if edgeItem.edgeLine._p:
                for p in edgeItem.edgeLine._p:
                    self.points.append(p)
            else:
                self.points=[]
            self.edges.append((edgeItem, self.points, self.tangentPoints))
        self.metadata={}
        for k,v in node.metadata.items():
            self.metadata[k] = v
        self.metadataAttributes={}
        for k,v in node.metadataAttributes.items():
            self.metadataAttributes[k] = v
        self.type=type
        self.parents=[]
        for parent in self.node.parents:
            self.parents.append(parent)
        if type==ROLE_BLOB:
            self.width=self.node._width
            self.height=self.node._height
            self.xRadius=self.node._xRadius
            self.yRadius=self.node._yRadius
            self.children=[]
            for child in self.node.children:
                self.children.append(child)

    def undo(self):
        #VisNodeItem adds to the model and the  list
        #newNode =  VisNodeItem(self.posn,self.node.model,self.node.listWidget ,nameP=self.node.metadata['name'], \
        #                    id = self.node.nodeNum, metadata=self.node.metadata, \
        #                    metadataAttributes=self.node.metadataAttributes, ports=self.ports)
        if self.type == ROLE_NODE:
            newNode =  VisNodeItem(self.posn,self.model,self.treeWidget, nameP=self.metadata['name'], \
                                id = self.nodeNum, metadata=self.metadata, \
                                metadataAttributes=self.metadataAttributes, ports=self.ports, parents=self.parents)
        else:
            newNode = VisBlobItem(self.posn,self.model, self.treeWidget, nameP=self.metadata['name'], \
                                id = self.nodeNum, metadata=self.metadata, metadataAttributes=self.metadataAttributes,\
                                      ports=self.ports, height=self.height, width=self.width, xRadius=self.xRadius,\
                                        yRadius=self.yRadius, parents=self.parents, children=self.children)

        newNode.setPos(self.posn)
        #Add to *Scene*
        self.scene.addItem(newNode)   
        newNode.setFlag(QGraphicsItem.ItemIsSelectable, True)
        newNode.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.node=newNode

        # Now that it is added to scene parents can be found and treewidget updated
        self.scene.mainwindow.addTreeNode(newNode, self.type)
        
        #now read any edges that were deleted with the node
        #(I really don't know how it re-adds the ports so easily)
        #JH the above stopped working and this code should now be redundant (edges deleted before enetering delNode)
        for edgeItem in self.edges:
            if edgeItem[0].startNode[0].nodeNum==newNode.nodeNum:
                edgeItem[0].startNode=(newNode, edgeItem[0].startNode[1])
            else:
                edgeItem[0].startNode=(self.scene.findItemByIdx(edgeItem[0].startNode[0].nodeNum),edgeItem[0].startNode[1])
                edgeItem[0].startNode[0]._Ports.append(edgeItem[0].startNode[1])
            if edgeItem[0].endNode[0].nodeNum==newNode.nodeNum:
                edgeItem[0].endNode=(newNode, edgeItem[0].endNode[1])
            else:
                edgeItem[0].endNode=(self.scene.findItemByIdx(edgeItem[0].endNode[0].nodeNum),edgeItem[0].endNode[1])
                edgeItem[0].endNode[0]._Ports.append(edgeItem[0].endNode[1])
            newEdge = VisEdgeItem(self.model,self.treeWidget, edgeItem[0].startNode, edgeItem[0].endNode, 
                                directed=edgeItem[0].isDirected,  nameP=edgeItem[0].metadata['name'], id = edgeItem[0].edgeNum,
                                polyLineType = edgeItem[0]._polyEdge, points=edgeItem[1][1:-1], #exclude edgepoints
                                tangents=edgeItem[2], metadata=edgeItem[0].metadata, metadataAttributes=edgeItem[0].metadataAttributes)
            
            self.scene.addItem(newEdge)

    def redo(self):
        delIdx = self.node.data(KEY_INDEX)   
        #print("checkng -arents", self.scene.model.Gr.nodeD[self.scene.model.Gr.nodeD[delIdx].children[0]].parents)
        self.scene.mainwindow.delNode(delIdx)
        
class createEdgeCommand(QUndoCommand):
    def __init__(self, edge, scene, model, treeWidget, startNode, endNode, parent=None):
        super().__init__()
        self.edge = edge
        self.edgeNum=0 #placeholder
        self.scene = scene
        self.model = model
        #self.listWidget=listWidget
        self.treeWidget=treeWidget
        # save node and port data
        self.startNode=startNode
        self.startNodeNum=startNode[0].nodeNum
        self.endNode=endNode
        self.endNodeNum=endNode[0].nodeNum
        self.startPortPos=startNode[1].scenePos()
        self.startPortT=self.startNode[1].t
        self.startPortIndex=self.startNode[1].index
        #self.startPortParent=self.startNode[1].parentItem()
        self.endPortPos=endNode[1].scenePos()
        self.endPortT=self.endNode[1].t
        self.endPortIndex=self.endNode[1].index
        """#self.endPortParent=self.endNode[1].parentItem()
        # save edgepoints and tangents
        self.points=[]
        self.tangentPoints=[]
        if self.edge != None and self.edge.edgeLine._t:
            self.tangentPoints=self.edge.edgeLine._t
        else:
            self.tangentPoints=[]
        if self.edge != None and self.edge.edgeLine._p:
            for p in self.edge.edgeLine._p:
                self.points.append(p)
        else:
            self.points=[]"""

    def undo(self):
        #delIdx = self.edge.data(KEY_INDEX) 
        delIdx = self.edgeNum  
        self.scene.mainwindow.delEdge(delIdx)

    def redo(self):
        #VisEdgeItem adds to the model and the  list
        if self.edge==None:
            newEdge = VisEdgeItem(self.model,self.treeWidget, self.startNode, self.endNode)                              
        else:
            # if any of the nodes have been deleted and recreated they need to be found by reference
            startNodeZero=self.scene.findItemByIdx(self.startNodeNum)
            endNodeZero=self.scene.findItemByIdx(self.endNodeNum)
            # ports WILL have been deleted, so recreate and add to node 
            portPos = startNodeZero.parameterToPosition(self.startPortT)
            startNodeOne=port(portPos, t=self.startPortT, index =self.startPortIndex, parent=startNodeZero.nodeShape)
            portPos = endNodeZero.parameterToPosition(self.endPortT)
            endNodeOne=port(portPos, t=self.endPortT, index =self.endPortIndex, parent=endNodeZero.nodeShape)
            startNodeZero._Ports.append(startNodeOne)
            endNodeZero._Ports.append(endNodeOne)
            self.startNode=(startNodeZero, startNodeOne)
            self.endNode=(endNodeZero, endNodeOne)
            newEdge = VisEdgeItem(self.model,self.treeWidget, self.startNode, self.endNode, 
                                id = self.edgeNum)
        self.edgeNum=newEdge.edgeNum  

            #newEdge = VisEdgeItem(self.model,self.listWidget,self.edge.startNode, self.edge.endNode, 
            #                    directed=self.edge.isDirected,  nameP=self.edge.metadata['name'], id = self.edge.edgeNum,
            #                    polyLineType = self.edge._polyEdge, points=self.points[1:-1], #exclude edgepoints
            #                    tangents=self.tangentPoints, metadata=self.edge.metadata, metadataAttributes=self.edge.metadataAttributes)
               

        #Add to *Scene*
        self.scene.addItem(newEdge)
        newEdge.setFlag(QGraphicsItem.ItemIsSelectable, True) #can't select a node to move it due to drawing order
        newEdge.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.edge=newEdge

class deleteEdgeCommand(QUndoCommand):
    def __init__(self, edge, scene, model, treeWidget, startNodes, endNodes, parent=None):
        super().__init__(parent=parent)
        self.edge = edge
        self.edgeNum=edge.edgeNum
        self.scene = scene
        self.model = model
        #self.listWidget=listWidget
        self.treeWidget=treeWidget
        self.isDirected=edge.isDirected
        self._polyEdge=edge._polyEdge
        self.startNode=startNode
        self.startNodeNum=startNode[0].nodeNum
        self.endNode=endNode
        self.endNodeNum=endNode[0].nodeNum
        #save port elements to recreate
        self.startPortPos=self.startNode[1].scenePos()
        self.startPortT=self.startNode[1].t
        self.startPortIndex=self.startNode[1].index
        #self.startPortParent=self.startNode[1].parentItem()
        self.endPortPos=self.endNode[1].scenePos()
        self.endPortT=self.endNode[1].t
        self.endPortIndex=self.endNode[1].index
        #self.endPortParent=self.endNode[1].parentItem()
        self.points=[]
        self.tangentPoints=[]
        #if self.edge != None and hasattr("self.edge.edgeLine","_t"):
        if self._polyEdge == SPLINE:
            for t in self.edge.edgeLine._t:
                self.tangentPoints.append(t)
            #self.tangentPoints=self.edge.edgeLine._t
        else:
            self.tangentPoints=[]
        if self.edge != None and self.edge.edgeLine._p:
            for p in self.edge.edgeLine._p:
                self.points.append(p)
        else:
            self.points=[]
        self.metadata={}
        for k,v in edge.metadata.items():
            self.metadata[k] = v
        self.metadataAttributes={}
        for k,v in edge.metadataAttributes.items():
            self.metadataAttributes[k] = v

    def undo(self):
        #if the connecting nodes have been deleted and recreated their referencing is suspect
        startNodeZero=self.scene.findItemByIdx(self.startNodeNum)
        endNodeZero=self.scene.findItemByIdx(self.endNodeNum)
        #self.edge.startNode=(self.scene.findItemByIdx(self.edge.startNode[0].nodeNum),self.edge.startNode[1])
        #self.edge.endNode=(self.scene.findItemByIdx(self.edge.endNode[0].nodeNum),self.edge.endNode[1])
        # ports WILL have been deleted, so recreate and add to node 
        portPos = startNodeZero.parameterToPosition(self.startPortT)
        startNodeOne=port(portPos, t=self.startPortT, index =self.startPortIndex, parent=startNodeZero.nodeShape)
        portPos = endNodeZero.parameterToPosition(self.endPortT)
        endNodeOne=port(portPos, t=self.endPortT, index =self.endPortIndex, parent=endNodeZero.nodeShape)
        startNodeZero._Ports.append(startNodeOne)
        endNodeZero._Ports.append(endNodeOne)
        self.startNode=(startNodeZero, startNodeOne)
        self.endNode=(endNodeZero, endNodeOne)
        """#recreate ports if necessary
        if not self.edge.startNode[1] or not self.edge.startNode[1].parentItem():#instead of being deleted QT removes the parent. Weird but
            pStart= port(self.startPortPos, t=self.startPortT, index =self.startPortIndex, parent=self.startNode[0].nodeShape)
            self.edge.startNode[0]._Ports.append(pStart)
            self.edge.startNode=(self.edge.startNode[0],pStart)
        else:
            self.edge.startNode[0]._Ports.append(self.edge.startNode[1])
        if not self.edge.endNode[1] or not self.edge.endNode[1].parentItem():
            pEnd= port(self.endPortPos, t=self.endPortT, index =self.endPortIndex, parent=self.endNode[0].nodeShape)
            self.edge.endNode[0]._Ports.append(pEnd)
            self.edge.endNode=(self.edge.endNode[0],pEnd)
        else:
            self.edge.endNode[0]._Ports.append(self.edge.endNode[1])  """
        #VisEdgeItem adds to the model and the  list      
        newEdge = VisEdgeItem(self.model,self.treeWidget, self.startNode, self.endNode, 
                            directed=self.isDirected,  nameP=self.metadata['name'], id = self.edgeNum,
                            polyLineType = self._polyEdge, points=self.points[1:-1], #exclude edgepoints
                            tangents=self.tangentPoints, metadata=self.metadata, metadataAttributes=self.metadataAttributes)
               
        #Add to *Scene*
        self.scene.addItem(newEdge)
        newEdge.setFlag(QGraphicsItem.ItemIsSelectable, True) #can't select a node to move it due to drawing order
        newEdge.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.edge=newEdge

    def redo(self):
        delIdx = self.edge.data(KEY_INDEX)
        self.scene.mainwindow.delEdge(delIdx)

class moveNodeCommand(QUndoCommand):
    def __init__(self, lastPosition, currentPosition, scene, model, treeWidget):
        super().__init__()
        self.currentPosition=copy.deepcopy(currentPosition) 
        self.lastPosition=copy.deepcopy(lastPosition)
        self.scene = scene
        self.model = model
        self.treeWidget=treeWidget

    def undo(self):
        self.scene.rePosition(self.lastPosition)

    def redo(self):
        #reposition to current position
        self.scene.rePosition(self.currentPosition)
        
        

def debug_qgraphicsitem_refs():
    """ coPilot code to track gc issues. """
    #import gc
    print("debug_qgraphicsitem_refs()")
    gc.collect()
    print(f"gc stats {gc.get_stats()}")
    for obj in gc.get_objects():
        if isinstance(obj, QGraphicsItem):
            print("Alive QGraphicsItem:", obj)
            refs = gc.get_referrers(obj)
            print(f"There are {refs =} referrers")
            #print("  Referrers:")
            #for ref in refs:
            #    print("   ", ref)

#=======
# "monkey patch" QListWidget to create data() sorted lists
# can't properly extend QListWidget 'cos it's setup in the .ui file
# Courtesy of chatGPT

# Store original addItem method
_original_addItem = QListWidget.addItem

# Add sort_roles attribute to QListWidget instances
def _addItem_with_sort(self, item):
    _original_addItem(self, item)
    roles = getattr(self, "_sort_roles", None)
    if roles:
        _resort_items(self, roles)

def _resort_items(widget, roles):
    items = []
    while widget.count():
        items.append(widget.takeItem(0))
    #TODO: Make sort by name an option
    items.sort(key=lambda item: tuple(item.data(role) for role in roles))
    for item in items:
        _original_addItem(widget, item)

def set_sort_roles(self, roles):
    self._sort_roles = roles
    _resort_items(self, roles)
# Patch methods into QListWidget
QListWidget.addItem = _addItem_with_sort
QListWidget.setSortRoles = set_sort_roles

def findItemByIdx(self,idx):
    """another patch to LWid
      feed in a ROLE_INDEX value, and get the item out, or none """
    for row in range(self.count()):
        item = self.item(row)
        if item.data(KEY_INDEX) == idx:
            return item
    return None
QListWidget.findItemByIdx = findItemByIdx

def findTreeItemByIdx(self,idx):
    """another patch to TWid
      feed in a ROLE_INDEX value, and get the item out, or none """
    for a in range(self.topLevelItemCount()):
        item = self.topLevelItem(a)
        if item.data(0,KEY_INDEX) == idx:
            return item
        for b in range(self.topLevelItem(a).childCount()):
            bitem = item.child(b)
            if bitem.data(0,KEY_INDEX) == idx:
                return bitem
    return None
QTreeWidget.findItemByIdx = findTreeItemByIdx

def XXfindItemByIdx(self,idx):
    """another patch to LWid
      feed in a ROLE_INDEX value, and get the ITEM out, or none """
    for row in range(self.count()):
        item = self.item(row)
        if item.data(KEY_INDEX) == idx:
            return item
    return None
QListWidget.findItemByIdx = findItemByIdx

def findItemRowByIdx(self,idx): #NOTUSED
    """another patch to LWid
      feed in a ROLE_INDEX value, and get the item ROW of the item out, or none """
    for row in range(self.count()):
        item = self.item(row)
        if item.data(KEY_INDEX) == idx:
            return row
    return None
QListWidget.findItemRowByIdx = findItemRowByIdx

def findTreeItemRowByIdx(self,idx):
    """another patch to tWid
      feed in a ROLE_INDEX value, and get the item ROW of the item out, or none """
    for row in range(self.topLevelItemCount()):
        item = self.item(row)
        if item.data(KEY_INDEX) == idx:
            return row
    return None
QTreeWidget.findItemRowByIdx = findTreeItemRowByIdx

_original_wheelEvent = QGraphicsView.wheelEvent
def WheelEvent(self, event):
    if event.modifiers() and Qt.ControlModifier:
        currentZoom=self.transform().m11()
        zoomInFactor = 1.25 * currentZoom * 100
        zoomOutFactor=(1/1.25) * currentZoom * 100
        if event.angleDelta().y() > 0:
            #self.scale(zoomInFactor, zoomInFactor)
            self.window().zoom_slider.setValue(zoomInFactor)
        else:
            #self.scale(zoomOutFactor, zoomOutFactor)
            self.window().zoom_slider.setValue(zoomOutFactor)
    _original_wheelEvent(self,event)
QGraphicsView.wheelEvent=WheelEvent

#end monkeypatch    
#=======


#Some global helper functions
class CodeExecDialog(QDialog):
    """Let the user run arbitrary Python code against the model """
    def __init__(self, parent=None, scene=None):
        super().__init__(parent)
        self.setWindowTitle("Python Code Executor - Experimental - does not save!")
        self.resize(600, 400)
        self.setModal(False) 

        self.scene = scene  # Reference to the MainWindow's scene

        # Layouts
        mainLayout = QVBoxLayout()
        inputLabel = QLabel("Python Code ('S' is scene, 'M' is model, 'G' is Graph):")
        self.codeEdit = QTextEdit()
        self.codeEdit.setText("#Examples - No. of Scene items: \nresult = str(len(S.items()))\n" +
                                "nC = len(G.nodeD)\neC = len(G.edgeD)\n" +
                                "result += f'\\n Node Count: {nC}, Edge Count {eC}'\n" +
                                "#Directed or not:\nresult += f'\\n{M.isDigraph == False =}\\n' \n" +
                                "#Graph Model contents:\nresult += f'{M.getModelItems() =}\\n' \n"+
                                "#Abstract Graph G:\nresult += f'{G =}'")

        outputLabel = QLabel("Output:")
        self.outputEdit = QTextEdit()
        self.outputEdit.setReadOnly(True)

        buttonLayout = QHBoxLayout()
        runButton = QPushButton("Run")
        closeButton = QPushButton("Close")
        buttonLayout.addWidget(runButton)
        buttonLayout.addWidget(closeButton)

        mainLayout.addWidget(inputLabel)
        mainLayout.addWidget(self.codeEdit)
        mainLayout.addWidget(outputLabel)
        mainLayout.addWidget(self.outputEdit)
        mainLayout.addLayout(buttonLayout)
        self.setLayout(mainLayout)

        # Connections
        runButton.clicked.connect(self.runCode)
        closeButton.clicked.connect(self.close)

    def runCode(self):
        """
        Execute the code entered in the text box.
        """
        code = self.codeEdit.toPlainText()
        output = ""

        # Prepare the local context
        localContext = {"S": self.scene, "G":self.scene.model.Gr, "M":self.scene.model}

        try:
            # Execute code
            exec(code, {}, localContext)

            # If they defined 'result', show it
            if "result" in localContext:
                output = str(localContext["result"])
            else:
                output = "Code executed successfully. (No 'result' defined.)"
        except Exception:
            output = "Exception:\n" + traceback.format_exc()

        self.outputEdit.setPlainText(output)


def zoomToFitWithMargin(view, margin=0.25):
    """ chatGpt. Pass in a QGraphicsView and a margin multiplier  """
    # Get bounding rect of all items
    sceneRect = view.scene().itemsBoundingRect()

    if sceneRect.isNull():
        # Nothing to fit
        return

    # Inflate by 25% on each side
    marginX = sceneRect.width() * margin
    marginY = sceneRect.height() * margin
    sceneRect.adjust(-marginX, -marginY, marginX, marginY)

    # Compute the transform to fit the rect
    viewportRect = view.viewport().rect()
    if viewportRect.isEmpty():
        return

    # Calculate scale factors
    xScale = viewportRect.width() / sceneRect.width()
    yScale = viewportRect.height() / sceneRect.height()
    scale = min(xScale, yScale)

    # Limit scaling to 100% max
    scale = min(scale, 1.0)

    # Build the target transform manually
    transform = QTransform()
    transform.translate(view.viewport().width() / 2, view.viewport().height() / 2)
    transform.scale(scale, scale)
    transform.translate(-sceneRect.center().x(), -sceneRect.center().y())

    view.setTransform(transform)


def paintItemAndChildren(item, painter):
    """
    chatGPT: Paint the item and all its children recursively.
    """
    # Default style option
    option = QStyleOptionGraphicsItem()

    # Save painter state
    painter.save()

    # Apply the item's transform
    painter.setTransform(item.sceneTransform(), combine=False)

    # Paint the item itself
    item.paint(painter, option, widget=None)

    # Paint the children
    for child in item.childItems():
        #print(child)
        paintItemAndChildren(child, painter)

    painter.restore()


basedir = os.path.dirname(__file__)

try:
    from ctypes import windll  # Only exists on Windows.
    myappid = "za.co.isijingi.qtpyGraphEdit.v00"
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except ImportError:
    pass

class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.treeWidget.setColumnCount(3)
        self.ui.treeWidget.setIndentation(15)
        self.ui.treeWidget.setColumnHidden(1,True)
        self.ui.treeWidget.setHeaderLabels(["Name", "Index", "Type"])
        self.ui.treeWidget.setSortingEnabled(True)
        #self.ui.listWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.treeWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.ui.actionZoomIn.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl++", None))
        self.ui.actionZoomOut.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+-", None))
        #TODO: Put in the `isWindowModified()` code
        self.setWindowTitle(APP_NAME +"[*]")
        self.fileName = ""

        #Where the data lives
        self.model = graphModel()

        #Display List
        #self.ui.listWidget.setModel(self.model)
        #setup the list to sort by TYPE then ID (using patched function above)
        #self.ui.listWidget.setSortRoles( (KEY_ROLE,KEY_INDEX) )
        #self.ui.listWidget.itemChanged.connect(self.updateSceneText)
        self.ui.treeWidget.itemChanged.connect(self.updateSceneText)
        #self.ui.listWidget.itemClicked.connect(self.listClick) # this is now called by itemSelectionChanged
        #self.ui.listWidget.itemDoubleClicked.connect(self.listDblClicked)
        self.ui.treeWidget.itemDoubleClicked.connect(self.listDblClicked)
        
        self.undoStack=QUndoStack()

        #Setup the graphicsView, linking model,scene and list. Scene needs to know the mainwindow to call dialogs, etc
        self.Scene = grScene(self.model, self.ui.treeWidget, self.undoStack, self)
        #self.Scene.selectionChanged.connect(self.actionSceneSelectChange)
        #self.ui.listWidget.itemSelectionChanged.connect(self.actionListSelectChange)
        self.ui.treeWidget.itemSelectionChanged.connect(self.actionListSelectChange)

        self.Scene.edgeEditRequested.connect(self.showEditEdgeDialog)
        self.Scene.nodeEditRequested.connect(self.showEditNodeDialog)

        self.ui.graphicsView.setScene(self.Scene)
        self.ui.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.ui.graphicsView.setDragMode(QGraphicsView.RubberBandDrag)
        #JH try self.ui.graphicsView.setMouseTracking(True)
        self.ui.graphicsView.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
       # JH self.ui.graphicsView.setTransformationAnchor(self.ui.graphicsView.ViewportAnchor.AnchorUnderMouse)
        #TODO: Make this image centre until scrollwheel zooming is fixed
        self.ui.graphicsView.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        # JH self.ui.graphicsView.setResizeAnchor(self.ui.graphicsView.ViewportAnchor.AnchorUnderMouse)

        # Create a status bar
        status_bar = QStatusBar()
        self.setStatusBar(status_bar)
     
        # Create search bar
        self.searchbar = QLineEdit(placeholderText="Search ...")
        self.searchbar.textChanged.connect(self.search)
        status_bar.addPermanentWidget(self.searchbar)

        # Create a slider
        self.zoom_slider = QSlider(Qt.Horizontal)
        self.zoom_slider.setMinimum(10)     # 10%
        self.zoom_slider.setMaximum(400)    # 400%
        self.zoom_slider.setValue(100)      # Start at 100%
        self.zoom_slider.setTickInterval(10)
        self.zoom_slider.setTickPosition(QSlider.TicksBelow)

        # Label to show current zoom
        self.zoom_label = QLabel("Zoom: 100%")

        # Add slider and label to the status bar
        status_bar.addPermanentWidget(self.zoom_label)
        status_bar.addPermanentWidget(self.zoom_slider)

        # Connect the slider to the zoom handler
        self.zoom_slider.valueChanged.connect(self.setZoom)


        #deal with deletions not updating - doesn't help - issue is with object persistence
        #self.ui.graphicsView.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)

        #link UI to local code
        #Graph Tool bar tools
        self.ui.actionNewNode.triggered.connect(self.actionNewNode)
        self.ui.actionNewEdge.triggered.connect(self.actionNewEdge)
        self.ui.actionNewBlob.triggered.connect(self.actionNewBlob)
        self.ui.actionPointer.triggered.connect(self.actionPointer)

        #File
        self.ui.action_New.triggered.connect(self.action_FileNew)
        self.ui.action_Open.triggered.connect(self.action_FileOpen)
        self.ui.actionSave.triggered.connect(self.action_FileSave)
        self.ui.actionSave_As.triggered.connect(self.action_FileSaveAs)
        self.ui.actionClose.triggered.connect(self.action_FileClose)
        self.ui.actionExport.triggered.connect(self.action_FileExport)

        self.ui.actionPrint.triggered.connect(self.action_Print)
        #Edit
        self.ui.actionCopy.triggered.connect(self.action_EditCopy)
        self.ui.actionCut.triggered.connect(self.action_EditCut)
        self.ui.actionPaste.triggered.connect(self.action_EditPaste)
        self.ui.action_Delete.triggered.connect(self.action_EditDelete)
        self.ui.actionSelect_All.triggered.connect(self.action_EditSelectAll)
        self.ui.actionSelect_None.triggered.connect(self.action_EditSelectNone)
        self.ui.actionZoomIn.triggered.connect(self.action_EditZoomIn)
        self.ui.actionZoomOut.triggered.connect(self.action_EditZoomOut)

        self.actionEditUndo = QAction("Undo", self)
        self.ui.menuEdit.addAction(self.actionEditUndo)
        self.actionEditRedo = QAction("Redo", self)
        self.ui.menuEdit.addAction(self.actionEditRedo)
        self.actionEditUndo.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+z", None))
        self.actionEditRedo.setShortcut(QCoreApplication.translate("MainWindow", u"Ctrl+y", None))
        self.actionEditUndo.triggered.connect(self.undoStack.undo)
        self.actionEditRedo.triggered.connect(self.undoStack.redo)

        #Tools & other 
        self.execCodeAction = QAction("Run Python Code", self)
        self.execCodeAction.triggered.connect(self.showCodeDialog)
        self.ui.menuTools.addAction(self.execCodeAction)

        """
        self.selectColourDefaultsAction = QAction("Select Colours", self)
        self.selectColourDefaultsAction.triggered.connect(self.selectColours)
        self.ui.menuTools.addAction(self.selectColourDefaultsAction)
        """

        #Help
        self.ui.action_About.triggered.connect(self.action_HelpAbout)
        self.ui.action_Credits.triggered.connect(self.action_HelpCredits)
        self.NODE_ICON=self.ui.icon8
        self.BLOB_ICON=self.ui.icon11
        self.EDGE_ICON=self.ui.icon9

    #GraphicsView/ scene handling
    def setZoom(self, value):
        """
        chatGPT
        Slot to set the zoom level of the QGraphicsView.
        """
        scale = value / 100.0  # Convert to 0.1 - 4.0
        self.ui.graphicsView.resetTransform()          # Reset any existing zoom
        self.ui.graphicsView.scale(scale, scale)       # Apply new zoom
        self.zoom_label.setText(f"Zoom: {value}%")

    def search(self, text):
        searchText = text.strip().casefold()
        items=self.ui.treeWidget.findItems(searchText, Qt.MatchRecursive)
        if len(items) !=0:
            self.ui.treeWidget.clearSelection()
            items[0].setSelected(True)
        else:
            items=self.ui.treeWidget.findItems(searchText, Qt.MatchStartsWith|Qt.MatchRecursive)
            if len(items) !=0:
                self.ui.treeWidget.clearSelection()
                items[0].setSelected(True)
                #self.setCurrentTreeItems(items[0].data(0,KEY_INDEX), QItemSelectionModel.SelectionFlag.Select)
                #self.listClick(items[0])


    #Action Code

    def showCodeDialog(self):
        self.codeDialog  = CodeExecDialog(self, scene=self.Scene)
        self.codeDialog.show()

    """
    def selectColours(self):
        #store self.codeDialog as an attribute to prevent it from being garbage-collected 
        colour=QColorDialog.getColor()
        if colour.isValid():
            DRAWING_COLOUR=colour
    """

    #Graph actions from the toolbar

    def actionNewNode(self):
        #Set the mouseMode to node
        if self.Scene.thisHandleObjectSelected:
            self.Scene.thisHandleObjectSelected._deleteHandles()
            self.Scene.thisHandleObjectSelected=None
            self.Scene.onlySelected=None
        self.Scene.clearSelection()
        #self.ui.listWidget.clearSelection()
        self.ui.treeWidget.clearSelection()
        self.Scene.mouseMode = grScene.INSERTNODE
        #self.actionPointer.setChecked(False)
        self.statusBar().showMessage("Insert Node",3000)

        """
        #TODO: Use this to properly set/ unset the toolbar buttons
        from DiagramScene:
        @Slot(QGraphicsPolygonItem)
        def item_inserted(self, item):
            print(f"Item inserted {item}")
            self._pointer_type_group.button(DiagramScene.MoveItem).setChecked(True)
            self.scene.set_mode(self._pointer_type_group.checkedId())
            self._button_group.button(item.diagram_type).setChecked(False)
        """

    def actionNewBlob(self):
        if self.Scene.thisHandleObjectSelected:
            self.Scene.thisHandleObjectSelected._deleteHandles()
            self.Scene.thisHandleObjectSelected=None
            self.Scene.onlySelected=None
        self.Scene.clearSelection()
        self.ui.treeWidget.clearSelection()
        self.Scene.mouseMode = grScene.INSERTBLOB
        #self.actionPointer.setChecked(False)
        self.statusBar().showMessage("Insert Blob",3000)

    def actionNewEdge(self):
        if self.Scene.thisHandleObjectSelected:
            self.Scene.thisHandleObjectSelected._deleteHandles()
            self.Scene.thisHandleObjectSelected=None
            self.Scene.onlySelected=None
        self.Scene.clearSelection()
        self.ui.treeWidget.clearSelection()
        self.statusBar().showMessage("Insert Edge",3000)
        #print("Add an edge")
        self.Scene.mouseMode = grScene.INSERTEDGE

    def actionNewHyperEdge(self):
        self.statusBar().showMessage("Insert Hyperedge",3000)
        #print("Add an edge")
        self.Scene.mouseMode = grScene.INSERTHYPEREDGE

    def actionPointer(self):
        self.statusBar().showMessage("Select Mode",3000)
        self.Scene.mouseMode = grScene.POINTER

    def listClick(self,item):

        #if not self.multipleListSelectionFlag:
            #print(f"listClick {item} , {item.text()}")
            #clear the selection
        if self.Scene.thisHandleObjectSelected:
            self.Scene.thisHandleObjectSelected._deleteHandles()
            self.Scene.thisHandleObjectSelected=None
            self.Scene.onlySelected=None
        self.Scene.clearSelection()

        #select the *graphics* view of the clicked item as well
        idx = item.data(0,KEY_INDEX)
        sItem=self.Scene.findItemByIdx(idx)
        #for sItem in self.Scene.items():  #this should probably be using finditembyidx JH
        if sItem.data(KEY_ROLE) in [ROLE_NODE, ROLE_EDGE,ROLE_BLOB]:
            #if sItem.data(KEY_INDEX) == idx: # iNum:
            sItem.setSelected(True)
            if sItem.data(KEY_ROLE) in [ROLE_EDGE, ROLE_BLOB]:
                self.Scene.thisHandleObjectSelected=sItem
                self.Scene.onlySelected=sItem
                sItem.setSelected(True)
                sItem.isOnlySelected=True
                #Hyperedge - create handles on all the edgeLines
                sItem._createHandles()
            if sItem.data(KEY_ROLE) in [ROLE_EDGE]:
                if not sItem.stH:  #copied from mousepressevent
                    sItem.setZValue(2000) #move the edge above nodes
                    if getattr(sItem.edgeLines[0],'_pHandles',False):
                        if len(sItem.edgeLines[0]._pHandles)>0:
                            sItem.stH = sItem.edgeLines[0]._pHandles[0]
                            sItem.endH = sItem.edgeLines[0]._pHandles[-1]
                        else:
                            print("No handles yet")
                    else:
                            print("No handles yet - _pHandle not defined")
                    """if len(sItem._pHandles)>0:
                        sItem.stH = sItem._pHandles[0]
                        sItem.endH = sItem._pHandles[-1]
                    else:
                        print("No handles yet")"""

        # check for additional entry in treewidget
        twItems=self.ui.treeWidget.findItems(str(idx), Qt.MatchRecursive, 1)
        if len(twItems)>1:
            self.Scene.changedByCode=True
            for twItem in twItems:
                self.ui.treeWidget.setCurrentItem(twItem,0,QItemSelectionModel.SelectionFlag.Select)
            self.Scene.changedByCode=False

    def listDblClicked(self,item):
        #print("listDblClicked", item.text(), item.index())
        #item.setFlags(item.flags() | Qt.ItemIsEditable)
        #self.ui.listWidget.editItem(item)
        #print(f"Editing {item.text() =}, id = {item.data(KEY_INDEX)}")

        #copilot Integration: If the double-clicked item is an edge, open the edit dialog
        if item.data(0,KEY_ROLE) == ROLE_EDGE:
            # Find the corresponding VisEdgeItem in the scene
            edgeItem = self.Scene.findItemByIdx(item.data(0,KEY_INDEX))
            if edgeItem:
                #TODO: This should be a signal? (but I can't make them work)
                self.showEditEdgeDialog(edgeItem)
        elif item.data(0,KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
            nodeItem = self.Scene.findItemByIdx(item.data(0,KEY_INDEX))
            if nodeItem:
                self.showEditNodeDialog(nodeItem)
        else: #Not called anymore?
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            #self.ui.listWidget.editItem(item)

        self.updateSceneText(item)

    def updateSceneText(self,item):
        """ Code for the list/Tree Widget to tell the scene that something has changed (name)"""
        #Maybe should be updateMODELText - scene updates via the model?

        #print("Upddata_blobate scene text")
        #print(f"updateSceneText id = {item.data(KEY_INDEX)} {item.text()}::{item.data(KEY_ROLE)}")

        iNum = item.data(0,KEY_INDEX)
        #print(f"{item.text()}::{item.data(KEY_INDEX)}>{item.data(KEY_ROLE)} {iNum =}")
        new_text = item.text(0)
        itemModelRow=self.model.findRowByIdx(iNum)
        self.model.item(itemModelRow).setText(new_text)
        #TODO: The list update should trigger some change flag/ be embedded 
        if item.data(0,KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
            self.model.Gr.nodeD[iNum].metadata.update({'name':new_text})
        elif item.data(0,KEY_ROLE) == ROLE_EDGE:
            self.model.Gr.edgeD[iNum].metadata.update({'name':new_text})
        #Update of added attrib in the scene
        #TODO: Make this dataChanged.emit() work 
        #Find the index of the visEdge
        for sItem in self.Scene.items():
            if sItem.data(KEY_INDEX) == iNum:
                #TODO: How to get an index to pass?
                #sIDX = sItem.index()
                #Just call it directly, with a dummy change item
                sItem.itemChange(QGraphicsItem.GraphicsItemChange.ItemToolTipChange,0)
            #self.model.dataChanged.emit(sIDX, sIDX)

        self.Scene.update()
        #self.ui.listWidget.repaint()
        self.ui.treeWidget.repaint()

    def actionListSelectChange(self):
        if not self.Scene.changedByCode:
            selected_items = self.ui.treeWidget.selectedItems()
            if len(selected_items)>1:
                if self.Scene.thisHandleObjectSelected:
                    self.Scene.thisHandleObjectSelected._deleteHandles()
                    self.Scene.thisHandleObjectSelected=None
                    self.Scene.onlySelected=None
                self.Scene.clearSelection()
                for item in selected_items:
                    idx = item.data(0,KEY_INDEX)
                    for sItem in self.Scene.items():
                        if sItem.data(KEY_ROLE) in [ROLE_NODE, ROLE_EDGE,ROLE_BLOB]:
                            if sItem.data(KEY_INDEX) == idx: # iNum:
                                sItem.setSelected(True)
                    # check for additional entry in treewidget
                    self.Scene.changedByCode=True
                    self.setCurrentTreeItems(idx, QItemSelectionModel.SelectionFlag.Select)
                    self.Scene.changedByCode=False
                    """twItems=self.ui.treeWidget.findItems(str(idx), Qt.MatchRecursive, 1)
                    if len(twItems)>1:
                        self.Scene.changedByCode=True
                        for twItem in twItems:
                            self.ui.treeWidget.setCurrentItem(twItem,0,QItemSelectionModel.SelectionFlag.Select)
                        self.Scene.changedByCode=False"""
            else:
                if len(selected_items)!=0:
                    self.listClick(selected_items[0])

    def setCurrentTreeItems(self, idx, flag):
        twItems=self.ui.treeWidget.findItems(str(idx), Qt.MatchRecursive, 1)
        if len(twItems)>0:
            #self.Scene.changedByCode=True
            for twItem in twItems:
                self.ui.treeWidget.setCurrentItem(twItem,0,flag)
                #self.ui.treeWidget.twItem.setSelected(True)
           # self.Scene.changedByCode=False


    """def actionSceneSelectChange(self):  Endless loop with listchange!
        selected_items = self.Scene.selectedItems()
        if len(selected_items)>1:
            self.Scene.listWidget.clearSelection()
            for item in selected_items:
                idx = item.data(KEY_INDEX)
                sItem=self.Scene.listWidget.findItemByIdx(idx)
                if sItem.data(KEY_ROLE) in [ROLE_NODE, ROLE_EDGE,ROLE_BLOB]:
                    #if sItem.data(KEY_INDEX) == idx: # iNum:
                    self.Scene.listWidget.setCurrentItem(sItem)"""

    def addTreeNode(self, newNode, nodeType):
        #this code still has bugs on very complex blob nesting structures
        directChildDic=self.Scene.getDirectChildDic()   #this is basically the updateblobparenting code
        c=[]    #children
        p=[]    #parents
        for k,v in directChildDic.items():
            if newNode.nodeNum in v:
                p.append(k)
            elif k==newNode.nodeNum:
                for eachV in v:
                    c.append(eachV)
        if p==[]:  #toplevel item
            tWitem = QTreeWidgetItem([self.model.Gr.nodeD[newNode.nodeNum].metadata['name'],str(newNode.nodeNum)])
            if nodeType==ROLE_NODE:
                tWitem.setIcon(2,self.Scene.mainwindow.NODE_ICON)
            else:
                tWitem.setIcon(2,self.Scene.mainwindow.BLOB_ICON)
            tWitem.setData(0, KEY_INDEX,newNode.nodeNum)
            tWitem.setData(0, KEY_ROLE, nodeType)
            self.ui.treeWidget.addTopLevelItem(tWitem)
        else:
            for eachP in p:
                #eachPItem=self.ui.treeWidget.findItemByIdx(eachP)  # this is defective JH
                eachPItemList=self.ui.treeWidget.findItems(str(eachP), Qt.MatchRecursive, 1)
                for eachPItem in eachPItemList:
                    tWitem = QTreeWidgetItem([self.model.Gr.nodeD[newNode.nodeNum].metadata['name'],str(newNode.nodeNum)])
                    if nodeType==ROLE_NODE:
                        tWitem.setIcon(2,self.Scene.mainwindow.NODE_ICON)
                    else:
                        tWitem.setIcon(2,self.Scene.mainwindow.BLOB_ICON)
                    tWitem.setData(0, KEY_INDEX,newNode.nodeNum)
                    tWitem.setData(0, KEY_ROLE,nodeType)
                    eachPItem.addChild(tWitem) 
                self.model.Gr.nodeD[eachP].addChild(newNode.nodeNum)
            self.model.Gr.nodeD[newNode.nodeNum].resetParents(p)
        if c!=[]:  #only a blob can have children, these may need to be reparented
            for eachC in c:
                cParents=copy.deepcopy(self.model.Gr.nodeD[eachC].parents) #deepcopy no longer needed JH
                eachCItemList=self.ui.treeWidget.findItems(str(eachC), Qt.MatchRecursive, 1)
                eachCItem=eachCItemList[0]  #will use the parent list to iterate, not the the item list
                #for eachCItem in eachCItemList:
                if cParents != []:
                    for eachCParent in cParents:
                        if eachCParent in p: #this child's parent is the blob's parent
                            #eachCParentItem=self.ui.treeWidget.findItemByIdx(eachCParent) #this is suspect JH
                            eachCParentItems=self.ui.treeWidget.findItems(str(eachCParent), Qt.MatchRecursive, 1)
                            for eachCParentItem in eachCParentItems:
                                tWitem.addChild(eachCParentItem.takeChild(eachCParentItem.indexOfChild(eachCItem)))
                            self.model.Gr.nodeD[eachC].delParent(eachCParent)
                            self.model.Gr.nodeD[eachC].addParent(newNode.nodeNum)
                            self.model.Gr.nodeD[eachCParent].delChild(eachC)
                            self.model.Gr.nodeD[newNode.nodeNum].addChild(eachC)
                        else:   # this is adding the child to an additional parent 
                            if eachC not in self.model.Gr.nodeD[newNode.nodeNum].children: #check not already added         
                                newChildClone=QTreeWidgetItem.clone(eachCItem)
                                tWitem.addChild(newChildClone)   
                                self.model.Gr.nodeD[newNode.nodeNum].addChild(eachC)
                            self.model.Gr.nodeD[eachC].addParent(newNode.nodeNum)
                else: #unparented
                    itemIdx=self.ui.treeWidget.indexOfTopLevelItem(eachCItem)
                    removedItem=self.ui.treeWidget.takeTopLevelItem(itemIdx)
                    tWitem.addChild(removedItem)
                    self.model.Gr.nodeD[eachC].addParent(newNode.nodeNum)
                    self.model.Gr.nodeD[newNode.nodeNum].addChild(eachC)


    #Menu-like Actions
    def action_FileNew(self):
        #print("FileNew")
        #Tidy up where we are
        """self.Scene.clearSelection()
        if self.Scene.onlySelected:
            self.Scene.onlySelected.isOnlySelected =False
        self.Scene.onlySelected = None
        self.Scene.thisHandleObjectSelected = None"""

        #check for unsaved changes
        if not self.Scene.undoStack.isClean():
            if self.askForFileSave()=="Cancel":
                return
            

        self.action_EditSelectNone()
        
        #clear window vars
        self.setWindowTitle(APP_NAME +"[*]")
        self.fileName = ""

        #clear model
        self.model.clear()
        #clear ListW
        #self.ui.listWidget.clear()
        self.ui.treeWidget.clear()
        #Clear Scene
        #TODO: Reset the temp vars for odd reloads
        # eg self.onlySelected
        #suppress itemChanged processing (will put the flag on _everything_, which is ugly, but easy.)
        for i in self.Scene.items():
            i.suppressItemChange = True
        self.Scene.clear()
        #clear stack
        self.Scene.undoStack.clear()
        # Reset any existing zoom
        self.ui.graphicsView.resetTransform()     

    def askForFileSave(self):
        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "The document has been modified.\nDo you want to save your changes?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel,
            QMessageBox.Save  # Default button
            )

        if reply == QMessageBox.Save:
            self.action_FileSaveAs()
            return("Saved")
        elif reply == QMessageBox.Cancel:
            return("Cancel")
        else:
            return("Continue")

    def nodeFromXML(self,xNode,newID=False)->VisNodeItem:
        """ Create a new node from an XML string
            if newID is True, the item is created with a newID,otherwise, the read value.
            This is the difference between file load (new items) and edit paste (structure)
            Returns VisNodeItem
        """
        #Use old yEd + load code
        nodeMetadata = {}
        nodeMetadataAttributes = {}
        nodePorts = []

        #TODO: type check id
        if not newID:
            id = int(xNode.attrib.get("id"))
            #JH temp override for n0
            if id==0:
                id=1000
        else:
            id = ''
        for dataNode in xNode.iter("data"):
            shapeNode = dataNode.find("ShapeNode")
            if shapeNode != None:
                # Geometry information
                geom = shapeNode.find("Geometry")
                if geom is not None:
                    nodeX = float(geom.get("x"))
                    nodeY = float(geom.get("y"))
                
                #Get ports
                for nextP, p in enumerate(shapeNode.iter("port")):
                    #print(p.attrib)
                    tmpP = port(QPointF(float(p.get("x")),float(p.get("y"))), t=float(p.get("t")), index = int(p.get("name"))  ) 
                    nodePorts.append(tmpP)
                #print(f"{id=},{nextP=}")

                nodeLable = shapeNode.find("NodeLabel")
                if nodeLable is not None:
                    nodeName = nodeLable.text.strip()
                    if newID:
                        nodeName="*"+nodeName
                    for nodeNameAttribs in nodeLable.iter("metadataAttribute"):
                        #nodeMetadataAttributes['name'] = {nodeNameAttribs.attrib.get("key"): nodeNameAttribs.attrib.get("value")}
                        #Deal with Boolean for display (This is why you should use the proper key types!)
                        if nodeNameAttribs.attrib.get("key") == 'display':
                            nodeMetadataAttributes['name'] = {'display':nodeNameAttribs.attrib.get("value") == "True"}
                        else:
                            nodeMetadataAttributes['name'] = {nodeNameAttribs.attrib.get("key"): nodeNameAttribs.attrib.get("value")}

            #TODO: Add in error processing for corrupt/ odd files
        # Look for a metadata node
        for metaEl in xNode.iter("metadata"):
            metaKey = metaEl.attrib.get("key")
            nodeMetadata[metaKey] = metaEl.attrib.get("value").strip()
            for nodeNameAttribs in metaEl.iter("metadataAttribute"):
                #Deal with Boolean for display (This is why you should use the proper key types!)
                #TODO: Get the boolean value into the XML
                if nodeNameAttribs.attrib.get("key") == 'display':
                    nodeMetadataAttributes[metaKey] = {'display':nodeNameAttribs.attrib.get("value") == "True"}
                else:
                    nodeMetadataAttributes[metaKey] = {nodeNameAttribs.attrib.get("key"): nodeNameAttribs.attrib.get("value")}

        newNode =  VisNodeItem(QPointF(nodeX,nodeY),self.model,self.ui.treeWidget, nameP=nodeName, id = id,
                                metadata=nodeMetadata, metadataAttributes=nodeMetadataAttributes, ports=nodePorts)
        
        #update port  PARENTS (maybe recompute position?)

        for p in newNode._Ports:
            p.setParentItem(newNode.nodeShape)
            #print(f"{newNode.nodeNum=},{p.index=}")
        newNode.updatePorts()

        return newNode

    def blobFromXML(self,xBlob,newID=False)->VisBlobItem:
        """ Create a new node from an XML string
            if newID is True, the item is created with a newID,otherwise, the read value.
            This is the difference between file load (new items) and edit paste (structure)
            Returns VisBlobItem
        """
        #Use old yEd + load code
        blobMetadata = {}
        blobMetadataAttributes = {}
        nodePorts = []

        #TODO: type check id
        if not newID:
            id = int(xBlob.attrib.get("id"))
            #JH temp override for n0
            if id==0:
                id=1000
        else:
            id = ''
        for dataBlob in xBlob.iter("data"):
            shapeBlob = dataBlob.find("ShapeBlob")
            if shapeBlob != None:
                # Geometry information
                geom = shapeBlob.find("Geometry")
                if geom is not None:
                    blobX = float(geom.get("x"))
                    blobY = float(geom.get("y"))
                    blobWidth = float(geom.get("width"))
                    blobHeight = float(geom.get("height"))
                    blobXRadius=float(geom.get("xRadius"))
                    blobYRadius=float(geom.get("yRadius"))

                #Get ports
                for nextP, p in enumerate(shapeBlob.iter("port")):
                    tmpP = port(QPointF(float(p.get("x")),float(p.get("y"))), t=float(p.get("t")), index = int(p.get("name"))  ) 
                    nodePorts.append(tmpP)
                #print(f"{id=},{nextP=}")

                blobLabel = shapeBlob.find("BlobLabel")
                if blobLabel is not None:
                    blobName = blobLabel.text.strip()
                    if newID:
                        blobName="*"+blobName
                    for blobNameAttribs in blobLabel.iter("metadataAttribute"):
                        #nodeMetadataAttributes['name'] = {nodeNameAttribs.attrib.get("key"): nodeNameAttribs.attrib.get("value")}
                        #Deal with Boolean for display (This is why you should use the proper key types!)
                        if blobNameAttribs.attrib.get("key") == 'display':
                            blobMetadataAttributes['name'] = {'display':blobNameAttribs.attrib.get("value") == "True"}
                        else:
                            blobMetadataAttributes['name'] = {blobNameAttribs.attrib.get("key"): blobNameAttribs.attrib.get("value")}

            #TODO: Add in error processing for corrupt/ odd files
        # Look for a metadata node
        for metaEl in xBlob.iter("metadata"):
            metaKey = metaEl.attrib.get("key")
            blobMetadata[metaKey] = metaEl.attrib.get("value").strip()
            for blobNameAttribs in metaEl.iter("metadataAttribute"):
                #Deal with Boolean for display (This is why you should use the proper key types!)
                #TODO: Get the boolean value into the XML
                if blobNameAttribs.attrib.get("key") == 'display':
                    blobMetadataAttributes[metaKey] = {'display':blobNameAttribs.attrib.get("value") == "True"}
                else:
                    blobMetadataAttributes[metaKey] = {blobNameAttribs.attrib.get("key"): blobNameAttribs.attrib.get("value")}

        newBlob =  VisBlobItem(QPointF(blobX,blobY),self.model, self.ui.treeWidget, width=blobWidth,\
                               height=blobHeight, xRadius=blobXRadius, yRadius=blobYRadius,\
                                nameP=blobName, id = id, \
                                metadata=blobMetadata, metadataAttributes=blobMetadataAttributes,ports=nodePorts)
        
        newBlob.suppressItemChange = True

        #update port  PARENTS 
        for p in newBlob._Ports:
            p.setParentItem(newBlob.nodeShape) 

        # (maybe recompute position?)
        newBlob.updatePorts()
 
        newBlob.suppressItemChange = False
        return newBlob
    
    def edgeFromXML(self,xEdge,newID=False,newStartID=None, newEndID=None)->VisEdgeItem:
        """ Create a new edge from an XML string
            if newID is True, the item is created with a newID,otherwise, the read value.
            This is the difference between file load (new items) and edit paste (structure)
            newStartID & newEndID also must be overwritten on paste/ structure copy
            Returns VisEdgeItem
        """

        if not newID:
            #TODO: type check id/ process string IDs
            id = int(xEdge.attrib.get("id"))
        else:
            id = ''
        
        #yEd uses string IDs, not ints :/
        if newStartID is not None: #Note: Can't use "truthy" here since 0 is a valid option!
            sItemID = newStartID
        else:
            sItemID = int(xEdge.attrib.get("source", None))

        if newEndID is not None:
            eItemID = newEndID
        else:
            eItemID = int(xEdge.attrib.get("target", None))

        #Ports
        srcPort = int(xEdge.attrib.get("sourceport"))
        tgtPort = int(xEdge.attrib.get("targetport"))

        sItem = self.Scene.findItemByIdx(sItemID)
        eItem = self.Scene.findItemByIdx(eItemID)
        if sItem == None:
            #TODO - this should be in a try-except, since this means the file is corrupt
            print(f"WARNING! - Start Item ID {sItemID} not found ")
            #return None
        if eItem == None:
            print(f"WARNING! - End Item ID {eItemID} not found ")
            #return None
        
        #Add the port
        sItem = (sItem, sItem.portFromIndex(srcPort))
        eItem = (eItem, eItem.portFromIndex(tgtPort))
        #

        #directed = xEdge.attrib.get("directed", '')
        if xEdge.attrib.get("directed", '') == "true":  #xml needs string not bool
            directed=True
        else:
            directed=False
        edgeMetadata = {}
        edgeMetadataAttributes = {}

        for dataEdge in xEdge.iter("data"):
            points=[]
            tangents = []
            polylineedge = dataEdge.find("PolyLineEdge")
            polyLineType = STRAIGHT
            if polylineedge is None:
                polylineedge = dataEdge.find("QuadCurveEdge")
                polyLineType = SPLINE 
            if polylineedge is not None:
                path = polylineedge.find("Path")
                if path is not None:
                    if polyLineType == SPLINE:
                        #get tangents
                        startT = path.find("StartTangent")
                        if startT is not None: 
                            #Each list entry is a tuple of tuples!
                            tangents.append( ( QPointF(0,0),
                                               QPointF(float(startT.attrib.get("x")),
                                                   float(startT.attrib.get("y")) )
                                            ) )
                        
                    pathPoints = path.findall("Point")
                    if pathPoints is not None:
                        points = []
                        for pt in pathPoints:
                            #TODO: Not only pastes might generate `newID`s. Needs a better method.
                            if newID:  #if this is a paste, offset any points
                                points.append( QPointF(float(pt.attrib.get("x"))+PASTE_OFFSET,
                                            float(pt.attrib.get("y"))+PASTE_OFFSET) )  
                            else: 
                                points.append( QPointF(float(pt.attrib.get("x")),
                                            float(pt.attrib.get("y"))) )
                            #if QuadCurve, #get tangents
                            if polyLineType == SPLINE:
                                T = pt.find("Tangent")
                                if T is not None:
                                    tangents.append( ( QPointF(float(T.attrib.get("leftx")),
                                                                float(T.attrib.get("lefty")) ),
                                                        QPointF(float(T.attrib.get("rightx")),
                                                                float(T.attrib.get("righty")) )
                                            ) )

                    if polyLineType == SPLINE:
                        #get End tangents
                        endT = path.find("EndTangent")
                        if endT is not None:
                            tangents.append( (  QPointF(float(endT.attrib.get("x")),
                                                float(endT.attrib.get("y")) ),
                                                QPointF(0,0)
                                            ) )

                edgeLable = polylineedge.find("EdgeLabel")
                if edgeLable is not None:
                    edgeName = edgeLable.text #TODO: This gets a prepended space. Check
                    for edgeNameAttribs in edgeLable.iter("metadataAttribute"):
                        #Deal with Boolean for display (This is why you should use the proper key types!)
                        if edgeNameAttribs.attrib.get("key") == 'display':
                            edgeMetadataAttributes['name'] = {'display':edgeNameAttribs.attrib.get("value") == "True"}
                        else:
                            edgeMetadataAttributes['name'] = {edgeNameAttribs.attrib.get("key"): edgeNameAttribs.attrib.get("value")}                        

        #Read any additional metadata
        for metaEl in xEdge.iter("metadata"):
            metaKey = metaEl.attrib.get("key")
            edgeMetadata[metaKey] = metaEl.attrib.get("value")
            for edgeNameAttribs in metaEl.iter("metadataAttribute"):
                #Deal with Boolean for display (This is why you should use the proper key types!)
                if edgeNameAttribs.attrib.get("key") == 'display':
                    edgeMetadataAttributes[metaKey] = {'display':edgeNameAttribs.attrib.get("value") == "True"}
                else:
                    edgeMetadataAttributes[metaKey] = {edgeNameAttribs.attrib.get("key"): edgeNameAttribs.attrib.get("value")}

        #All the data read, create the edge
        newEdge = VisEdgeItem(self.model,self.ui.treeWidget, sItem, eItem, 
                                directed=directed,  nameP=edgeName, id = id,
                                polyLineType = polyLineType, points=points,tangents=tangents,
                                metadata=edgeMetadata, metadataAttributes=edgeMetadataAttributes   )

        return newEdge

    
    def hyperEdgeFromXML(self,xEdge,newID=False)->VisHyperEdgeItem:
        """ Create a new hyperEdge from an XML string `xEdge`
            if newID is True, the item is created with a newID,otherwise, the read value.
            This is the difference between file load (new items) and edit paste (structure)
            newStartID & newEndID also must be overwritten on paste/ structure copy
            For hyperedges, this will create the `edgeLine` here, and pass it in to the hyperEdge constructor.
            Returns VisHyperEdgeItem
        """

        if not newID:
            #TODO: type check id/ process string IDs
            id = int(xEdge.attrib.get("id"))
            #print(f"HyperEdge {id} being read")
        else: 
            id = '' #let the model assign an ID

        #directed
        if xEdge.attrib.get("directed", '') == "true":  #xml needs string not bool
            directed=True
        else:
            directed=False

        #lineType (STRAIGHT | SPLINE)
        lineType = xEdge.attrib.get("lineType", "")
        if lineType == "Straight":  
            polyLineType = STRAIGHT
        elif lineType == "Spline":  
            polyLineType = SPLINE
        else:
            polyLineType = DEFAULT_EDGE

        #Arrowheads
        #Currently just using the defaults
        #TODO: Read in the type of terminator symbols (well - write alt terminator symbol code!)

        #Extact start (`sItem`) & end ((eItem`) ID's 
        #newID implies we need newStartID used to be None? Use newID.
        sItem = []
        sNodes = []
        eItem = []
        eNodes = []
        
        #print(f"old to NewIDs {[(k,v) for k,v in self.oldToNewID.items()]}")

        for aNode in xEdge.find("nodeList"): 
            #Starts
            if aNode.tag == "start":
                s = int(aNode.attrib.get("source", 0))
                if not s:
                    print(f"ERROR: can't find source in {aNode}")
                    return None
                #TODO: refactor `oldToNewID` to work purely on int's!
                #print(f"Start node {s} --> {self.oldToNewID[str(s)]}")
                #s = self.oldToNewID[str(s)] 
                s = self.oldToNewID[s] 
                sItm = self.Scene.findItemByIdx(s)
                #Track real nodes to differentiate from dummys later
                sNodes.append(s)
                p = int(aNode.attrib.get("sourceport", 0))
                pItm = sItm.portFromIndex(p)
                #This assumes portIDs don't/ won't change - should be OK - local to nodes
                sItem.append( (sItm,pItm) )

            if aNode.tag == "end":
                e = int(aNode.attrib.get("target", 0))
                if not e:
                    print(f"ERROR: can't find target in {aNode}")
                    return None
                #print(f"end node {e} --> {self.oldToNewID[str(e)]}")
                e = self.oldToNewID[e]
                eItm = self.Scene.findItemByIdx(e)
                #Track real nodes
                eNodes.append(e)
                p = int(aNode.attrib.get("targetport", 0))
                pItm = eItm.portFromIndex(p)
                #This assumes portIDs don't/ won't change
                eItem.append( (eItm,pItm) )

        #dummyNodes - read, and instantiate
        dNList = []
        eLstarts = {} #Dictionary of  {eL.lineNum: dN} for start of lines
        eLends = {}   #For ends of lines. Note these contain whole dN objects, not nodeNums
        oldToNewdN = {}  #Track any dummyNodeID changes
        for dNode in xEdge.find("dummyNodeList"):
            dNID = int(dNode.attrib.get("id",0))
            dNx = float(dNode.attrib.get("x"))
            dNy = float(dNode.attrib.get("y"))
            if newID : #create a newID
                iD = 0
                offset=PASTE_OFFSET
            else:
                iD=dNID
                offset=0
            #Note: `parent` will have to be updated once the edge is created.
            dN = dummyNodeItem(QPointF(dNx+offset,dNy+offset),id=iD)
            #Note: EdgeLines don't yet exist - this will need to be udpated once they do.
            #Get the edges that start/ end here
            for sE in dNode.findall("startsEdgeLine"):
                eLstarts[int(sE.attrib.get("eL"))] = dN
            for eE in dNode.findall("endsEdgeLine"):
                eLends[int(eE.attrib.get("eL"))] = dN
            #Track the dNID in case it was changed on create
            #print(f"{dNID=} --> {dN.nodeNum}")
            oldToNewdN[dNID] = dN.nodeNum
            dNList.append( (dN,dN) )  #dummyNode are their own ports
            #Which edges this starts
            
        #edgeLines - read and instantiate

        #Note that if edgeLine ID's change, nodes will auto-update them during creation. I think.
        edgeLineList = []
        hyperEdgeGraph = dict() #An ordinary digraph of the hyperedge
        
        oldToNewEL = {}  #Track any edgeLineID changes
        for eL in xEdge.find("edgeLineList"):
            #print(f"edgeLine: {eL.attrib}")
            points=[]
            tangents = []
            #Note: dN edgeID need to become global (Real nodes could go beyond 1000 ...)
            #If not in sItem or eItem, then a dummy node
            eLID = int(eL.attrib.get("id",0))
            if newID : #create a newID by calling with 0
                iD = False #0
            else:
                iD = eLID

            #Get elStart, then check if it's a node or a dummyNode (and for end)
            sItm,pItm = None,None
            eLStart = int(eL.attrib.get("source", 0))
            if eLStart in self.oldToNewID:
                eLStart = self.oldToNewID[eLStart]  #JH
            if eLStart in sNodes: #real, not dummy
                sItm = self.Scene.findItemByIdx(eLStart)
                eLStartPort = int(eL.attrib.get("sourceport", 0))
                spItm = sItm.portFromIndex(eLStartPort)
                
            else: #dummy Node
                #find the dummy node
                stDN = oldToNewdN[eLStart]
                sItm = [d[0] for d in dNList if d[0].nodeNum == stDN][0]  #rtn DNitem, not a list
                spItm = sItm#[1] #dummyNodes are their own ports,

            eItm, pItm = None,None
            eLEnd = int(eL.attrib.get("target"))
            if eLEnd in self.oldToNewID:
                eLEnd = self.oldToNewID[eLEnd]  #JH
            if eLEnd in eNodes: #real, not dummy
                eItm = self.Scene.findItemByIdx(eLEnd)
                eLEndPort = int(eL.attrib.get("targetport", 0))
                epItm = eItm.portFromIndex(eLEndPort)
            else: #dummy Node
                #find the dummy node
                endDN = oldToNewdN[eLEnd]
                eItm = [d[0] for d in dNList if d[0].nodeNum == endDN][0]  #rtn DNitem, not a list
                epItm = eItm #[1]

            path = eL.find("Path")
            points = []
            #Start point
            points.append(spItm.pos())
            #Tangents and middle points
            if path is not None:
                if polyLineType == SPLINE:
                    #get tangents
                    startT = path.find("StartTangent")
                    if startT is not None: 
                        #Each list entry is a tuple of tuples!
                        tangents.append( ( QPointF(0,0),
                                            QPointF(float(startT.attrib.get("x")),
                                                float(startT.attrib.get("y")) )
                                        ) )
                    
                pathPoints = path.findall("Point")
                if pathPoints is not None:
                    for pt in pathPoints:
                        #TODO: Not only pastes might generate `newID`s. Needs a better method.
                        if newID:  #if this is a paste, offset any points
                            points.append( QPointF(float(pt.attrib.get("x"))+PASTE_OFFSET,
                                        float(pt.attrib.get("y"))+PASTE_OFFSET) )  
                        else: 
                            points.append( QPointF(float(pt.attrib.get("x")),
                                        float(pt.attrib.get("y"))) )
                        #if QuadCurve, #get tangents
                        if polyLineType == SPLINE:
                            T = pt.find("Tangent")
                            if T is not None:
                                tangents.append( ( QPointF(float(T.attrib.get("leftx")),
                                                            float(T.attrib.get("lefty")) ),
                                                    QPointF(float(T.attrib.get("rightx")),
                                                            float(T.attrib.get("righty")) )
                                        ) )

                if polyLineType == SPLINE:
                    #get End tangents
                    endT = path.find("EndTangent")
                    if endT is not None:
                            tangents.append( (  QPointF(float(endT.attrib.get("x")),
                                                float(endT.attrib.get("y")) ),
                                                QPointF(0,0)
                                            ) )
            #End point
            points.append(epItm.pos())
            #Now create the edgeLine, and store it
            if polyLineType == SPLINE:
                #Created with no parent, since edge does not yet exist. Link at the end
                newEdgeLine = HermiteSplineItem(p=points, t=tangents, id=iD)
            elif polyLineType == STRAIGHT:
                newEdgeLine = StraightLineItem(p=points,  id=iD)
            oldToNewEL[eLID] = newEdgeLine.lineNum
            #print(f"heX {eLID=} -> {oldToNewEL[eLID]}")
            #TODO: What has to be updated if eLID changes!?@?

            #Put this into the hyperEdgeGraph for this edge
            #print(f"   heFX edge {id} edgeLine {eLID=}  ({sItm.nodeNum}, {spItm.nodeNum}) : ({eItm.nodeNum},{epItm.nodeNum})")
            hyperEdgeGraph.update({newEdgeLine:((sItm,spItm),(eItm,epItm))})
            #print(f"heg: {[(k.lineNum,v[0][0].nodeNum,v[1][0].nodeNum) for k,v in hyperEdgeGraph.items()]}\neLStarts: {[(k,v.nodeNum) for k,v in eLstarts.items()]}\neLends: {[(k,v.nodeNum) for k,v in eLends.items()]}")
            edgeLineList.append(newEdgeLine)
            #Tell the dummyNodes 
            #if newEdgeLine.lineNum in eLstarts.keys():
            if eLID in eLstarts.keys():
                #print(f" adding eL {newEdgeLine.lineNum} to start at  {eLstarts[newEdgeLine.lineNum].nodeNum}")
                #eLstarts[newEdgeLine.lineNum].startsEdgeLines.append(newEdgeLine)
                eLstarts[eLID].startsEdgeLines.append(newEdgeLine)
            #if newEdgeLine.lineNum in eLends.keys():
            if eLID in eLends.keys():
                #print(f" adding eL {newEdgeLine.lineNum} to end at {eLends[newEdgeLine.lineNum].nodeNum}")
                #eLends[newEdgeLine.lineNum].endsEdgeLines.append(newEdgeLine)
                eLends[eLID].endsEdgeLines.append(newEdgeLine)
                
        #print(f"edgelines: {[e.lineNum for e in edgeLineList]}")

        #Read metadata, including `name`
        edgeMetadata = {}
        edgeMetadataAttributes = {}        
        for metaEl in xEdge.iter("metadata"):
            metaKey = metaEl.attrib.get("key")
            edgeMetadata[metaKey] = metaEl.attrib.get("value")
            for edgeNameAttribs in metaEl.iter("metadataAttribute"):
                #Deal with Boolean for display (This is why you should use the proper key types!)
                if edgeNameAttribs.attrib.get("key") == 'display':
                    edgeMetadataAttributes[metaKey] = {'display':edgeNameAttribs.attrib.get("value") == "True"}
                else:
                    edgeMetadataAttributes[metaKey] = {edgeNameAttribs.attrib.get("key"): edgeNameAttribs.attrib.get("value")}
        
        edgeName = edgeMetadata['name']
        #TODO: This is for copies - needs a better check for file read ID changes
        if newID:
            edgeName="*"+edgeName
        #All the data read, create the edge
        newEdge = VisHyperEdgeItem(self.model, self.Scene, self.ui.treeWidget, sItem, eItem, 
                                directed=directed,  nameP=edgeName, id = id,
                                polyLineType = polyLineType, points=points,tangents=tangents,
                                metadata=edgeMetadata, metadataAttributes=edgeMetadataAttributes,
                                dummyNodes=dNList  , edgeLines=edgeLineList,
                                hyperEdgeGraph=hyperEdgeGraph   )

        #TODO: Update parenting of dummyNodes & edgeLines
        for dN in dNList:
            dN[0].setParentItem(newEdge)
        for eL in edgeLineList:
            eL.setParentItem(newEdge)

        return newEdge


    def action_FileOpen(self):
        #check for unsaved changes
        if not self.Scene.undoStack.isClean():
            if self.askForFileSave()=="Cancel":
                return
            self.undoStack.setClean()   #so that this isn't called again when the environment is cleared
        """ Read a graphml file in, create all the elements """
        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getOpenFileName(self, 
            "Load File", dir="", filter ="graphml files(*.graphml);;All Files(*)", options = options)
        if fileName == '':  #dialog returns '' on <esc>        
            return
        #Clear the current graph
        self.action_FileNew()

        self.fileName = fileName

        #Load the .graphml file as a string
        #Key elements from 
        #fileReading: yEd xml_to_simple_string()
        graphStr = ""
        try:
            with open(fileName, "r") as graphFile:
                graphStr = graphFile.read()

        except FileNotFoundError:
            print(f"Error, file not found: {graphFile}")
            raise FileNotFoundError(f"Error, file not found: {graphFile}")


        # Preprocessing of file for ease of parsing
        #TODO: Check how this will mess with multiline metadata
        graphStr = graphStr.replace("\n", " ")  # line returns
        graphStr = graphStr.replace("\r", " ")  # line returns
        graphStr = graphStr.replace("\t", " ")  # tabs
        graphStr = re.sub("<graphml .*?>", "<graphml>", graphStr)  # unneeded schema
        graphStr = graphStr.replace("> <", "><")  # empty text
        graphStr = graphStr.replace("y:", "")  # unneeded namespace prefix
        graphStr = graphStr.replace("xml:", "")  # unneeded namespace prefix
        graphStr = graphStr.replace("h:", "")  # unneeded namespace prefix

        graphStr = graphStr.replace("yfiles.", "")  # unneeded namespace prefix
        graphStr = re.sub(" {1,}", " ", graphStr)  # reducing redundant spaces

        # Get major graph node
        root = ET.fromstring(graphStr)

        graphStr = root.find("graph")
        if graphStr is not None:
            # get major graph info
            graphDir = graphStr.get("edgedefault")
            self.model.isDirected = graphDir == "directed"
        else: 
            self.model.isDirected = ISDIGRAPH 

        #Track the old -> new IDs to deal with string IDs, and hook up edges
        #Hyperedges are complex, so make it accessible to hyperEdgeFromXML
        self.oldToNewID = {}

        #Nodes
        for xNode in graphStr.iter("node"):
            #print(f"FileOpen - nodes: {ET.tostring(xNode)=}")
            #Handle yEd-style string IDs
            fileID = xNode.attrib.get("id")
            try: #is the read ID a valid int- use it
                id = int(fileID)
                newID = False
            except ValueError: #No - generate a new one.
                newID = True

            GItem = self.nodeFromXML(xNode, newID=newID)
            #Track it, even if it doesn't change - simplifies the edge code
            self.oldToNewID[int(fileID)] = GItem.nodeNum
            #TODO: Do something meaningful with mismatches
            #if fileID != GItem.nodeNum:
            #    print(f"WARNING: node id {fileID=} changed on load")
            
            self.Scene.addItem(GItem)
            self.addTreeNode(GItem, ROLE_NODE)
            GItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            GItem.setFlag(QGraphicsItem.ItemIsMovable, True)    

        #Blobs
        for xBlob in graphStr.iter("blob"):
            #print(f"FileOpen - nodes: {ET.tostring(xNode)=}")
            #Handle yEd-style string IDs
            fileID = xBlob.attrib.get("id")
            try: #is the read ID a valid int- use it
                id = int(fileID)
                newID = False
            except ValueError: #No - generate a new one.
                newID = True

            GItem = self.blobFromXML(xBlob, newID=newID)
            #Track it, even if it doesn't change - simplifies the edge code
            self.oldToNewID[int(fileID)] = GItem.nodeNum
            #TODO: Do something meaningful with mismatches
            #if fileID != GItem.nodeNum:
            #    print(f"WARNING: node id {fileID=} changed on load")
            
            self.Scene.addItem(GItem)
            self.addTreeNode(GItem, ROLE_BLOB)
            GItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            GItem.setFlag(QGraphicsItem.ItemIsMovable, True)    

        #Edges
        for xEdge in graphStr.iter("edge"):
            #Handle yEd-style string IDs
            fileID = xEdge.attrib.get("id")
            try: #is the read ID a valid int- use it
                id = int(fileID)
                newID = False
            except ValueError: #No - generate a new one.
                newID = True
            
            sItemID = xEdge.attrib.get("source", None)
            eItemID = xEdge.attrib.get("target", None)
            edgeItem = self.edgeFromXML(xEdge, newID=newID, 
                                            newStartID=self.oldToNewID[sItemID],
                                            newEndID = self.oldToNewID[eItemID])

            #Add to Scene
            self.Scene.addItem(edgeItem)
            edgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            edgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)
        
        #HyperEdges
        for xEdge in graphStr.iter("hyperedge"):
            hEdgeItem = self.hyperEdgeFromXML(xEdge)
            #Add to Scene
            self.Scene.addItem(hEdgeItem)
            hEdgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            hEdgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)

        self.Scene.update()

        self.setWindowTitle(str(os.path.basename(self.fileName)) + " " + APP_NAME + "[*]")
        self.oldToNewID.clear()

        #self.setZoom(100)
        #zoomToFitWithMargin(self.ui.graphicsView, margin=0.2)

    def action_FileSave(self):
        """ 
            Write the graph to a yEd-style graphml file.
            Heavily based on yEdx code
        """
        if self.fileName:

            #Generate the graph header info
            # Creating XML structure in Graphml format
            # Reference: yEdxFileOnly: construct_graphml
            # xml = ET.Element("?xml", version="1.0", encoding="UTF-8", standalone="no")

            graphml = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
            graphml.set("xmlns:java", "http://www.yworks.com/xml/yfiles-common/1.0/java")
            graphml.set("xmlns:sys", "http://www.yworks.com/xml/yfiles-common/markup/primitives/2.0")
            graphml.set("xmlns:x", "http://www.yworks.com/xml/yfiles-common/markup/2.0")
            graphml.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
            graphml.set("xmlns:y", "http://www.yworks.com/xml/graphml")
            graphml.set("xmlns:yed", "http://www.yworks.com/xml/yed/3")
            graphml.set("xmlns:h", "http://www.isijingi.co.za/higraph")
            graphml.set(
                "xsi:schemaLocation",
                "http://graphml.graphdrawing.org/xmlns http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd",
            )

            # Adding some implementation specific keys for identifying urls, descriptions
            nodeKey = ET.SubElement(graphml, "key", id="data_node")
            nodeKey.set("for", "node")
            nodeKey.set("yfiles.type", "nodegraphics")

            blobKey = ET.SubElement(graphml, "key", id="data_blob")
            blobKey.set("for", "blob")
            blobKey.set("higraph.type", "blobgraphics")

            edgeKey = ET.SubElement(graphml, "key", id="data_edge")
            edgeKey.set("for", "edge")
            edgeKey.set("yfiles.type", "edgegraphics")


            # Graph node containing actual objects
            if self.model.isDigraph:
                directed = 'directed'
            else:
                directed = 'undirected'

            graph = ET.SubElement(graphml, "graph", edgedefault=directed, id="G")

            #Add the nodes & edges
            for sItem in self.Scene.items():
                #if sItem.data(KEY_ROLE) == ROLE_NODE or sItem.data(KEY_ROLE) == ROLE_EDGE :
                if sItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_EDGE,ROLE_BLOB]:
                    graph.append(sItem.toXML(graph))

            #Add the keys for the metadata at graph level

            #Write to file
            raw_str = ET.tostring(graphml)
            pretty_str = minidom.parseString(raw_str).toprettyxml()
            #TODO: Check pathing!
            with open(self.fileName, "w") as f:
                f.write(pretty_str)

            # Mark current state as saved
            self.Scene.undoStack.setClean() 

        else:
            self.action_FileSaveAs()

    def action_FileSaveAs(self):
        #print("File SaveAs")  
        #TODO: Implement isWindowModified()
        #if not self.isWindowModified():
        #    return

        options = QtWidgets.QFileDialog.Options()
        options |= QtWidgets.QFileDialog.DontUseNativeDialog
        fileName, _ = QtWidgets.QFileDialog.getSaveFileName(self, 
            "Save File", dir=self.fileName, filter ="graphml files(*.graphml);;All Files(*)", options = options)
        
        #Note: Qt checks for overwrites, etc
        if fileName:  #dialog returns '' on <esc>
            if fileName[-8:] == ".graphml":
                self.fileName = fileName
            else:
                self.fileName = fileName+".graphml"
            self.setWindowTitle(str(os.path.basename(self.fileName)) + " " + APP_NAME + "[*]")
            self.action_FileSave()
                 
    def action_FileClose(self):
        print("File Close")  

    def action_Print(self):
        """
        chatGPT. Slot to print the entire QGraphicsScene.
        """
        printer = QPrinter(QPrinter.ScreenResolution)# HighResolution) 

        # Show print dialog
        printDialog = QPrintDialog(printer, self)
        if printDialog.exec() == QPrintDialog.Accepted:
            painter = QPainter(printer)
            
            # Get the full scene rectangle
            #sceneRect = self.Scene.sceneRect()
            sceneRect = self.Scene.itemsBoundingRect() 
            #print(f"{sceneRect =}")

            # Compute scale to fit scene onto the page
            #TODO: Apply a human brain to this scaling - this gives weird results.
            pageRect = printer.pageRect(QPrinter.DevicePixel).toRect()
            #print(f"{pageRect =}")
            xScale = pageRect.width() / sceneRect.width()
            yScale = pageRect.height() / sceneRect.height()
            scale = min(xScale, yScale)
            #print(f"{scale =}")
            scale = scale/5 #needs tweaking

            # Center the scene on the page
            #xOffset = (pageRect.width() - sceneRect.width() * scale) / 2
            #yOffset = (pageRect.height() - sceneRect.height() * scale) / 2

            #painter.translate(xOffset, yOffset)
            #painter.scale(scale, scale)
        
            # Render the scene
            self.Scene.render(painter)

            painter.end()

    def action_DebugPrint(self):
            print("core Graph Model\n",self.model.Gr)
            print("model items \n",self.model.getModelItems())
            #print(f"{self.model =}")
            """print("\nListView items:\n",
               "\n".join([self.ui.listWidget.item(x).text()+ \
                " ID:"+str(self.ui.listWidget.item(x).data(KEY_INDEX))+ \
                " type:"+str(self.ui.listWidget.item(x).data(KEY_ROLE)) \
                    for x in range(self.ui.listWidget.count())]))"""
            #graphics View ~= scene
            print("\nui.graphicsView items:\n","\n   ".join([str(itm) \
                for itm in self.ui.graphicsView.items()]))
            
            lstr = "core Graph Model\n"+ str(self.model.Gr)
            lstr += f"model items {self.model.getModelItems()} \n"
            """lstr += "\nListView items:\n"
            lstr += "\n".join([self.ui.listWidget.item(x).text()+ " ID:"+str(self.ui.listWidget.item(x).data(KEY_INDEX))+ \
                " type:"+str(self.ui.listWidget.item(x).data(KEY_ROLE)) for x in range(self.ui.listWidget.count())])"""
            lstr += "\nui.graphicsView items:\n"
            lstr += "\n   ".join([str(itm) for itm in self.ui.graphicsView.items()])
            #logging.debug(lstr)

    def action_FileExport(self):
        # Fold this into FileSaveAs??
        #chatGPT code
        #print("File Export") 
        filePath, _ = QFileDialog.getSaveFileName(
            self,
            "Save SVG File",
            "",
            "Scalable Vector Graphics (*.svg)"
        )

        if not filePath:
            return  # User cancelled

        # Create SVG generator
        generator = QSvgGenerator()
        generator.setFileName(filePath)
        #TODO: bounding box still not snug, but workable.
        generator.setSize(self.Scene.sceneRect().size().toSize())  #itemsBoundingRect().size().toSize())

        #TODO: Why is there a lot of white space at the top left?
        generator.setTitle(f"{APP_NAME} Export")

        # Paint the scene into the generator
        #TODO: Deselect before painting, then reselect (copy from copy bitmap code)
        painter = QPainter(generator)
        self.Scene.render(painter)
        painter.end()

    def action_EditCopy(self):
        """ chatGPT"""
        #print("Edit>Copy")
        selectedItems = self.Scene.selectedItems()
        if not selectedItems:
            return

        mimeData = QMimeData()

        #Simple Model Text
        #=================

        plainText = ""
        for sItem in selectedItems:
            if sItem.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                plainText += str(self.model.Gr.nodeD[sItem.data(KEY_INDEX)])
            if sItem.data(KEY_ROLE) == ROLE_EDGE:
                plainText += str(self.model.Gr.edgeD[sItem.data(KEY_INDEX)])
        mimeData.setText(plainText)

        #graphml - pastable format
        #=========================

        # Code similar to action_FileOpen. Use that as the "master" copy.
        #Positions only updated on PASTE
        #TODO: Create a function `initialiseGraphml` with all this boilerplate

        graphml = ET.Element("graphml", xmlns="http://graphml.graphdrawing.org/xmlns")
        graphml.set("xmlns:java", "http://www.yworks.com/xml/yfiles-common/1.0/java")
        graphml.set("xmlns:sys", "http://www.yworks.com/xml/yfiles-common/markup/primitives/2.0")
        graphml.set("xmlns:x", "http://www.yworks.com/xml/yfiles-common/markup/2.0")
        graphml.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        graphml.set("xmlns:y", "http://www.yworks.com/xml/graphml")
        graphml.set("xmlns:yed", "http://www.yworks.com/xml/yed/3")
        graphml.set("xmlns:h", "http://www.isijingi.co.za/higraph")
        graphml.set(
            "xsi:schemaLocation",
            "http://graphml.graphdrawing.org/xmlns http://www.yworks.com/xml/schema/graphml/1.1/ygraphml.xsd",
        )

        # Adding some implementation specific keys for identifying urls, descriptions
        nodeKey = ET.SubElement(graphml, "key", id="data_node")
        nodeKey.set("for", "node")
        nodeKey.set("yfiles.type", "nodegraphics")

        blobKey = ET.SubElement(graphml, "key", id="data_blob")
        blobKey.set("for", "blob")
        blobKey.set("higraph.type", "blobgraphics")
        
        edgeKey = ET.SubElement(graphml, "key", id="data_edge")
        edgeKey.set("for", "edge")
        edgeKey.set("yfiles.type", "edgegraphics")
        graph = ET.SubElement(graphml, "graph", id="clipboard")

        #Add the nodes & edges
        for sItem in selectedItems:
            if sItem.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB] :
                graph.append(sItem.toXML(graph))
            if sItem.data(KEY_ROLE) == ROLE_EDGE:
                #TODO: Check the semantics here - does this make sense
                #only copy edges if all ends are in the selection
                includeEdge=True
                for startN in sItem.startNodes:
                    if startN[0] not in selectedItems:
                        includeEdge=False
                        break
                if includeEdge==True:
                    for endN in sItem.endNodes:
                        if endN[0] not in selectedItems:
                            includeEdge=False
                            break
                if includeEdge==True:
                #if sItem.startNode[0] in selectedItems and sItem.endNode[0] in selectedItems:
                    graph.append(sItem.toXML(graph))

        #graphmlData = yGr.stringify_graph()
        rawStr = ET.tostring(graphml)
        #This parse step is not critical, but it does ensure that the XML is correct
        prettyStr = minidom.parseString(rawStr).toprettyxml()

        mimeData.setData("application/xml", prettyStr.encode("utf-8"))

        #Bitmap
        #======

        # Compute the bounding rect of all selected items
        boundingRect = selectedItems[0].sceneBoundingRect()
        for item in selectedItems[1:]:
            boundingRect = boundingRect.united(item.sceneBoundingRect())

        # Align to integers
        boundingRect = boundingRect.toAlignedRect()

        # Create the image
        image = QImage(boundingRect.size(), QImage.Format.Format_RGB16)
        image.fill(Qt.white)

        #Deselect to show in black, not blue!
        #if len(selectedItems) == 1 and selectedItems[0].data(KEY_ROLE) == ROLE_EDGE:
        #    self.Scene.clearEdgeOnly(selectedItems[0])

        if self.Scene.thisHandleObjectSelected != None and \
                (self.Scene.thisHandleObjectSelected in selectedItems or \
                self.Scene.thisHandleObjectSelected.parentItem() in selectedItems):
            self.Scene.thisHandleObjectSelected._deleteHandles()

        self.Scene.clearSelection()
        self.ui.treeWidget.clearSelection()

        # Render the selected items
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)

        # Translate so that boundingRect.topLeft() is (0,0)
        #Only use this when calling item.paint(), not with Scene.render()
        #painter.translate(-boundingRect.topLeft())

        # Draw only selected items
        #"""
        itemsInRect = self.Scene.itemsHere((0,0),0,[ROLE_EDGE,ROLE_NODE,ROLE_BLOB],boundingRect)
        visibleItems=[]
        for it in itemsInRect:
            if it not in selectedItems:
                visibleItems.append(it)
                it.setVisible(False)

        # Temp - chop off at bounding rect
        self.Scene.render(painter, target=QRectF(), source=boundingRect) # item.sceneBoundingRect())
        #"""

        # Paint only the selected items (and the children of compound items)
        """
        painter.setPen(Qt.black)
        option = QStyleOptionGraphicsItem()
        #TODO: Get children items of NDOES to properly translate. 
        # This may be a deeper issue with structure of the objects
        painter.translate(-boundingRect.topLeft())
        for item in selectedItems:
            print(f"{item.data(KEY_INDEX) =} {item.pos() =}")
            #paintItemAndChildren(item,painter)
            item.paint(painter, option)
            
            for child in item.childItems():
                print(f"{child =}")
                painter.save()
                #Works for edges, not nodes:
                painter.translate(item.scenePos())
                painter.setTransform(child.sceneTransform(), True)
                
                child.paint(painter,option,widget=None)
                painter.restore()
        """
        painter.end()
        for it in visibleItems:
            it.setVisible(True)
        #Reselect
        for item in selectedItems:
            item.setSelected(True)

        if self.Scene.thisHandleObjectSelected != None and \
                (self.Scene.thisHandleObjectSelected in selectedItems or \
                self.Scene.thisHandleObjectSelected.parentItem() in selectedItems):
            self.Scene.thisHandleObjectSelected._createHandles()

        mimeData.setImageData(image)
        QGuiApplication.clipboard().setMimeData(mimeData)

        # Copy image to clipboard for MSFT :/ This gets hacky  (win32 calls)
        #TODO: figure out how to handle MSFT DIBs (Edit>CopyImage)
        #pixmap = QPixmap.fromImage(image)
        #QGuiApplication.clipboard().setPixmap(pixmap)

    def action_EditCut(self):
        print("Edit>Cut")

        #Edite->Copy
        #Delete selected?

    def action_EditPaste(self):
        #print("Edit>Paste")
        # Extract the graphML->Graph code, and put in Edit>Paste(needing mods for new nodes)
        # The newly pasted items will be selected, to make them easy to move

        self.action_EditSelectNone()

        clipboard = QGuiApplication.clipboard()
        mimeData = clipboard.mimeData()

        # Check and extract XML if available
        if mimeData.hasFormat("application/xml"):
            xmlBytes = mimeData.data("application/xml")  # returns QByteArray
            graphStr = bytes(xmlBytes).decode("utf-8")
        else:
            return #Nothing readable on the clipboard

        # Preprocessing of string for ease of parsing
        #TODO: Check how this will mess with multiline metadata
        graphStr = graphStr.replace("\n", " ")  # line returns
        graphStr = graphStr.replace("\r", " ")  # line returns
        graphStr = graphStr.replace("\t", " ")  # tabs
        graphStr = re.sub("<graphml .*?>", "<graphml>", graphStr)  # unneeded schema
        graphStr = graphStr.replace("> <", "><")  # empty text
        graphStr = graphStr.replace("y:", "")  # unneeded namespace prefix
        graphStr = graphStr.replace("xml:", "")  # unneeded namespace prefix
        graphStr = graphStr.replace("h:", "")  # unneeded namespace prefix

        graphStr = graphStr.replace("yfiles.", "")  # unneeded namespace prefix
        graphStr = re.sub(" {1,}", " ", graphStr)  # reducing redundant spaces

        # Get major graph node
        root = ET.fromstring(graphStr)

        graphStr = root.find("graph")

        #Track the old -> new IDs to hook up edges
        self.oldToNewID = {}
        for xNode in graphStr.iter("node"):
            #print(f"FileOpen - nodes: {ET.tostring(xNode)=}")
            GItem = self.nodeFromXML(xNode, newID=True)
            self.oldToNewID[int(xNode.attrib.get("id"))] = GItem.nodeNum

            #Bump the pasted items over by PASTE_OFFSET
            GItem.moveBy(PASTE_OFFSET,PASTE_OFFSET)
            
            self.Scene.addItem(GItem)
            self.addTreeNode(GItem, ROLE_NODE)
            GItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            GItem.setFlag(QGraphicsItem.ItemIsMovable, True) 
            GItem.setSelected(True)   

        #blobs
        for xBlob in graphStr.iter("blob"):
            #print(f"FileOpen - nodes: {ET.tostring(xNode)=}")
            GItem = self.blobFromXML(xBlob, newID=True)
            self.oldToNewID[int(xBlob.attrib.get("id"))] = GItem.nodeNum

            #Bump the pasted items over by PASTE_OFFSET
            GItem.suppressItemChange = True
            GItem.moveBy(PASTE_OFFSET,PASTE_OFFSET)
            GItem.suppressItemChange = False

            self.Scene.addItem(GItem)
            self.addTreeNode(GItem, ROLE_BLOB)
            GItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            GItem.setFlag(QGraphicsItem.ItemIsMovable, True) 
            GItem.setSelected(True)   
        #Edges
        for xEdge in graphStr.iter("edge"):
            sItemID = int(xEdge.attrib.get("source", None))
            eItemID = int(xEdge.attrib.get("target", None))

            #BUG - edges don't work on paste - ID's have changed!

            edgeItem = self.edgeFromXML(xEdge, newID=True, 
                                            newStartID=self.oldToNewID[sItemID],
                                            newEndID = self.oldToNewID[eItemID])
            #Bump any polyline points over -  now done in edgefromXML
            #for pt in edgeItem.edgeLine._p:
            #    pt += QPointF(PASTE_OFFSET,PASTE_OFFSET)

            #Add to Scene
            self.Scene.addItem(edgeItem)
            edgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            edgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)
            edgeItem.setSelected(True)

        #HyperEdges
        for xEdge in graphStr.iter("hyperedge"):
            hEdgeItem = self.hyperEdgeFromXML(xEdge, newID=True)
            #Add to Scene
            self.Scene.addItem(hEdgeItem)
            hEdgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            hEdgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)
            hEdgeItem.setSelected(True)
        
        self.Scene.update()
        self.oldToNewID.clear()

    #Some helper functions for deletion

    def delEdge(self, delIdx):
        """ all the calls to delete an edge"""
        #delete from model
        self.model.delEdge(delIdx)
        #Delete from LWscene updat
        #delRow = self.ui.listWidget.findItemRowByIdx(delIdx)
        #delItem = self.ui.listWidget.takeItem(delRow)
        itemsToBeDeleted = self.ui.treeWidget.findItems(str(delIdx), Qt.MatchRecursive, 1)
        for item in itemsToBeDeleted:
            self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))
        #del delItem
        #Delete from Scene
        delItem = self.Scene.findItemByIdx(delIdx)
        #remove CBs
        #self.Scene.clearEdgeOnly(delItem)
        delItem.edgeLine._deleteHandles()
        if self.Scene.thisHandleObjectSelected==delItem.edgeLine:
            self.Scene.thisHandleObjectSelected = None
        
        #Del the port on the nodes
        delItem.startNode[0].deletePort(delItem.startNode[1])
        delItem.endNode[0].deletePort(delItem.endNode[1])

        self.Scene.deleteItemAndChildren(delItem)

        del delItem 

    def delHyperEdge(self, delIdx):
        """ all the calls to delete a Hyperedge"""

        #delete from model
        self.model.delEdge(delIdx)

        #Delete from LWscene updat
        #delRow = self.ui.listWidget.findItemRowByIdx(delIdx)
        #delItem = self.ui.listWidget.takeItem(delRow)
        itemsToBeDeleted = self.ui.treeWidget.findItems(str(delIdx), Qt.MatchRecursive, 1)
        for item in itemsToBeDeleted:
            self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))
        #del delItem
        #Delete from Scene
        delItem = self.Scene.findItemByIdx(delIdx)

        for eL in delItem.edgeLines:
            eL._deleteHandles()

        if self.Scene.thisHandleObjectSelected in delItem.edgeLines:
            self.Scene.thisHandleObjectSelected = None
        
        #Del the port on the nodes 
        for n in delItem.startNodes:
            p = n[1]
            n = (n[0],0) #unhook the port from the immutable tuple
            n[0].deletePort(p)
        for n in delItem.endNodes:
            p = n[1]
            n = (n[0],0) #unhook the port from the immutable tuple
            n[0].deletePort(p)
        

        #debug_qgraphicsitem_refs()

        self.Scene.deleteItemAndChildren(delItem)
        
        del delItem 

    def delNode(self, delIdx):
        """ all the calls to delete an node"""
        #TODO: Pop a warning dialog when deleting the edges

        #Check for any edges attached and delete
        #TODO: If the edge is a hyperedge, only delete the attached segment, 
        # not the whole edge
        #JH this should now be redundant-edges deleted beforehand
        eList = self.model.edgesAtNode(self.Scene.findItemByIdx(delIdx))
        if eList:
            for e in eList:
                self.delEdge(e)
        #JH to here        
        if self.Scene.thisHandleObjectSelected==self.Scene.findItemByIdx(delIdx):
            self.Scene.thisHandleObjectSelected = None
        #Delete from Scene first, since there are complex deps to other parts which get in a knot
        self.Scene.deleteItemAndChildren(self.Scene.findItemByIdx(delIdx))
        #delete from model
        nodeParents=copy.deepcopy(self.model.Gr.nodeD[delIdx].parents)
        self.model.delNode(delIdx)
        #Delete from LW
        #delRow = self.ui.listWidget.findItemRowByIdx(delIdx)
        #delItem = self.ui.listWidget.takeItem(delRow)
        #del delItem
        #Delete from Treewidget and reparent any children
        itemsToBeDeleted=self.ui.treeWidget.findItems(str(delIdx), Qt.MatchRecursive, 1)
        for item in itemsToBeDeleted:
            itemParent=item.parent()
            if item.childCount()!=0:
                for c in range(item.childCount()):
                    itemChild=item.child(c)                
                    if itemParent==None:
                        if len(self.model.Gr.nodeD[itemChild.data(0,KEY_INDEX)].parents)==0: #if item isn't parented elsewhere
                            self.ui.treeWidget.addTopLevelItem(QTreeWidgetItem.clone(itemChild))
                    else:
                        itemParent.addChild(QTreeWidgetItem.clone(itemChild))
            if itemParent==None:
                self.ui.treeWidget.takeTopLevelItem(self.ui.treeWidget.indexOfTopLevelItem(item))
            else:
                itemParent.takeChild(itemParent.indexOfChild(item))

        #del delItem  #is this necessary? JH


    def action_EditDelete(self):
        #print("Edit>Delete")
        #Edge Delete (must delete edges 1st)
        selected_items = self.Scene.selectedItems()
        if len(self.Scene.selectedItems())==1 and self.Scene.thisHandleObjectSelected:
            self.Scene.thisHandleObjectSelected._deleteHandles()
            self.Scene.thisHandleObjectSelected=None
        self.Scene.clearSelection()
        self.ui.treeWidget.clearSelection()
 
        if selected_items:
            self.undoStack.beginMacro("Delete/Undelete")
            for item in selected_items:
                if item.data(KEY_ROLE) == ROLE_EDGE:
                    delIdx = item.data(KEY_INDEX)
                    #self.delEdge(delIdx)
                    self.delHyperEdge(delIdx)
                    #newAction=deleteEdgeCommand(item, self.Scene, self.model, self.ui.treeWidget, item.startNodes, item.endNodes, parent=None)
                    #self.undoStack.push(newAction)
            #Node delete - 1st del any connected edges - handled by GrScene
            for item in selected_items:
                if item.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
                    delIdx = item.data(KEY_INDEX)
                    #check for any unselected edges attached to node and delete
                    eList = self.model.edgesAtNode(self.Scene.findItemByIdx(delIdx))
                    if eList:
                        for e in eList:
                            edgeItem = self.Scene.findItemByIdx(e)
                            #self.delEdge(e)
                            if edgeItem not in selected_items:
                                #TODO: re-implement UNDO!
                                self.delHyperEdge(e)
                                # newAction=deleteEdgeCommand(edgeItem, self.Scene, self.model, self.ui.treeWidget, edgeItem.startNode, edgeItem.endNode, parent=None)
                                #self.undoStack.push(newAction)
                    newAction=deleteNodeCommand(item, item.scenePos(), self.Scene, self.model, self.ui.treeWidget, type=item.data(KEY_ROLE), parent=None)
                    self.undoStack.push(newAction)
            self.undoStack.endMacro()
            #self.Scene.updateBlobParenting()        #JH there must be a better way to do this
        #logging.debug("about to update from action_EditDelete",stack_info=True  )
        #gc.collect() #This will crash the whole thing, with no traces
        #debug_qgraphicsitem_refs()  #More coPilot code ...

        #self.Scene.update()
        #Trying to get rid of the orphan lines - which go when the view changes so that scrollbars are added.
        #JHself.Scene.invalidate(self.Scene.sceneRect(), QGraphicsScene.AllLayers)
        #GC takes some time (~100ms?) to finalise, so delay the repaint
     #JH   QTimer.singleShot(500, lambda: self.ui.graphicsView.viewport().repaint())
        #self.Scene.invalidate(self.Scene.sceneRect(), QGraphicsScene.AllLayers)
      #JH  self.ui.graphicsView.viewport().repaint()  #update()
        #self.Scene.invalidate()

    def action_EditSelectAll(self):
        #print("Edit>SelectAll")
        #TODO: For multiple scenes from 1 model, what to do? (select model, or scene?)
        #  Maybe select all needs to be context sensitive - scene, or list =model
        self.Scene.changedByCode=True
        for item in self.Scene.items():
            if item.GraphicsItemFlag.ItemIsSelectable:
                item.isOnlySelected=False  
                item.setSelected(True)
                #lWItem = self.Scene.listWidget.findItemByIdx(item.data(KEY_INDEX))
                #self.Scene.listWidget.setCurrentItem(lWItem, QItemSelectionModel.SelectionFlag.Select)   
                self.setCurrentTreeItems(item.data(KEY_INDEX), QItemSelectionModel.SelectionFlag.Select)                
            if self.Scene.thisHandleObjectSelected:  
                self.Scene.thisHandleObjectSelected._deleteHandles()
                self.Scene.thisHandleObjectSelected=None
        self.Scene.changedByCode=False

    def action_EditSelectNone(self):
        #print("Edit>SelectNone")
        if len(self.Scene.selectedItems())==1 and self.Scene.thisHandleObjectSelected:
            self.Scene.thisHandleObjectSelected._deleteHandles()
            self.Scene.thisHandleObjectSelected=None
        #if self.Scene.onlySelected: 
        #    self.Scene.clearEdgeOnly(self.Scene.onlySelected)
        self.Scene.clearSelection()
        #self.Scene.listWidget.clearSelection()
        self.Scene.treeWidget.clearSelection()

    def action_EditZoomIn(self):
        #print("Edit>ZoomIn")
        currentZoom=self.ui.graphicsView.transform().m11() #horizontal value JH
        #currentZoomy=self.self.ui.graphicsView.transform().m22() #vertical scale
        zoomInFactor=1.25 * currentZoom * 100
        self.zoom_slider.setValue(zoomInFactor)

    def action_EditZoomOut(self):
        #print("Edit>ZoomOut")
        currentZoom=self.ui.graphicsView.transform().m11()
        zoomOutFactor=(1/1.25) * currentZoom * 100
        self.zoom_slider.setValue(zoomOutFactor)

    def action_HelpAbout(self):
        dlg = action_Aboutdlg(self)
        dlg.exec()

    def action_HelpCredits(self):
        dlg = action_CreditsDlg(self)
        dlg.exec()

    def showEditEdgeDialog(self, visEdgeItem):
        """
        copilot Show the EditVisEdgeItemDialog for the given VisEdgeItem and apply changes.
        """
        #dlg = EditVisEdgeItemDialog(visEdgeItem, parent=self)
        dlg = EditVisHyperEdgeItemDialog(visEdgeItem, parent=self)
        if dlg.exec() == dlg.accepted:
            # Attributes are already updated by the dialog's accept method
            self.Scene.update()
            #self.ui.listWidget.repaint()
            self.ui.treeWidget.repaint()

    def showEditNodeDialog(self, visNodeItem):
        dlg = EditVisNodeItemDialog(visNodeItem, parent=self)
        if dlg.exec() == dlg.accepted:
            # Attributes are already updated by the dialog's accept method
            self.Scene.update()
            #self.ui.listWidget.repaint()
            self.ui.treeWidget.repaint()


#Dialogs called by mainwindow
class action_Aboutdlg(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.dlg = Ui_dlgAbout()
        self.dlg.setupUi(self)

class action_CreditsDlg(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.uidlgCred = Ui_dlgCredits()
        self.uidlgCred.setupUi(self)


#--------------------------------------------
#import cProfile

if __name__ == "__main__":
    print("="*100)
    #print(f"Garbage collection is {gc.isenabled()}")
    #logger = logging.getLogger(__name__)
    #logging.basicConfig(filename='higraphDebug.log', 
    #                    encoding='utf-8', 
    #                    level=logging.DEBUG,
    #                    format='%(asctime)s %(message)s\nStk>%(stack_info)s')
    #logging.debug("\n\nStarting\n********\n")
    app = QApplication(sys.argv)
    #NOTE: also put `os.path.join(basedir,` into ui_form.py after generation
    app.setWindowIcon(QtGui.QIcon(os.path.join(basedir,'qtpyGraphEdit.ico')))
    MainWin = MainWindow()
    MainWin.resize(800, 600)
    MainWin.show()
    #cProfile.run('sys.exit(app.exec())')
    sys.exit(app.exec())