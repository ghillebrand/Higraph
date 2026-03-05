from __future__ import annotations

"""
V02 of a Python Graph Editing Tool. 
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
#import gc
import weakref

from typing import List, Dict

from PySide6.QtWidgets import ( QAbstractItemView, QApplication, QWidget, QMainWindow, QDialog,
            QGraphicsScene, QGraphicsView, QListWidget, QListWidgetItem,
            QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem, QGraphicsTextItem, QGraphicsLineItem,
            QLineEdit, QInputDialog, QMenu, QFileDialog, QStyleOptionGraphicsItem, QGraphicsObject,
            QSlider, QLabel, QStatusBar, QColorDialog, 
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

from ui_form import Ui_MainWindow
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
from EditVisItemDialog import EditVisEdgeItemDialog, EditVisNodeItemDialog



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
        n = self.Gr.addNode(id=id)
        #Default name is node number
        if not nameP:
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
        Graph.nextID = 0
        Graph.IDsUsed = set()
        super().clear()


class grScene(QGraphicsScene):
    """ holds and extends all the drawing, connects to model using VisNodeItem and VisEdgeItem"""
    # See Hg QT6.gaphor `GrScene INSERT states` for analysis of states (StateMachine)

    #Mouse state enum
    # INSERTEDGE2CLICK for handling choice of item in ambiguous cases, which requires a click to choose, 
    # and thus the end is selected on a Press, not a release.
    INSERTNODE, INSERTBLOB, INSERTEDGE, POINTER, INSERTEDGE2CLICK, MOVEEDGEEND, MOVEHANDLE, DOUBLECLICK, DRAGGING = range(9)
    mouseModeDic={INSERTNODE:"INSERTNODE", INSERTBLOB:"INSERTBLOB", INSERTEDGE:"INSERTEDGE", POINTER:"POINTER", INSERTEDGE2CLICK:"INSERTEDGE2CLICK",\
                   MOVEEDGEEND:"MOVEEDGEEND", MOVEHANDLE:"MOVEHANDLE", DOUBLECLICK:"DOUBLECLICK", DRAGGING:"DRAGGING"}
    #TO pass edit requests to mainwindow. Signal must be class, not instance variables.
    edgeEditRequested = Signal(object)
    nodeEditRequested = Signal(object)

    def __init__(self, model,listWidget,undoStack, mainwindow):
        super().__init__()
        self.model = model
        self.listWidget = listWidget
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

        # For ListWidget
        self.changedByCode=False

        #Handle hovering
        self.lastHovered = None #QGraphicsItem

        #Track single item selection (for edges)
        self.onlySelected = None
        self.thisHandleObjectSelected = None

        #For dragging
        self._lastMousePos = QPointF(0,0)

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
        ###polyline
        #self.rubberLine = StraightLineItem([self.startPoint, self.endPoint])
        self.rubberLine = QLineF(self.startPoint, self.endPoint)

        #self.GrRubberLine = self.addItem(self.rubberLine)
        self.GrRubberLine = self.addLine(self.rubberLine)
        
    def stretchRubberLine(self,mPos):
        """ called from INSERTEDGE: mouseMove """
        self.endPoint = mPos # mouseEvent.scenePos()
        ###
        self.rubberLine.setP2(self.endPoint)
        #self.rubberLine.setP(-1,self.endPoint)
        #self.rubberLine.updatePath()
        self.GrRubberLine.setLine(self.rubberLine)

    def endRubberLine(self):
        """called on successful end item found for edge:
         from INSERTEDGE mouseRelease or INSERTEDGE2CLICK mousePress """
        #TODO: How does this relate to finishMovingEdgeEnd?

        #TODO: Create the ports on the nodes
        #Start port
        #TODO: Sharing ports makes moving complex. The need for shared ports points to using hyperedges rather
        #startPort = self.tmpEdgeSt.findPort(self.startPoint)
        #if startPort != None:
        startPort = self.tmpEdgeSt.createPort(self.startPoint)
        #print(f"{startPort=}")

        #endPort = self.tmpEdgeEnd.findPort(self.endPoint)
        #if endPort !- None:
        endPort = self.tmpEdgeEnd.createPort(self.endPoint)

        #Create the actual edge
        newAction=createEdgeCommand(None, self, self.model,self.listWidget, (self.tmpEdgeSt,startPort), (self.tmpEdgeEnd,endPort), parent=None)
        self.undoStack.push(newAction)
        #edgeItem = VisEdgeItem(self.model,self.listWidget, (self.tmpEdgeSt,startPort), (self.tmpEdgeEnd,endPort), parent=None)

        #Add to *Scene*
        #self.addItem(edgeItem)
        #edgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True) #can't select a node to move it due to drawing order
        #edgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)

    def resetRubberLine(self):
        """ Called whether or not an edge is created """
        if self.tmpEdgeSt:
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
        #print(f"StartMovingEdge {edge.metadata['name']}")
        self.handle = handle #Store the box for the Move/ Finish functions
        #is handle at start or end?
        if self.handle.pos() == edge.startNode[1].scenePos():
            # NOTE: Node relinking is only done on successful finish, so track the old Terminator item
            self.EdgeEnd = "start"
            self.oldTermItem = edge.startNode
            #print(f"start move {self.oldTermItem}\n{self.oldTermItem[1].index}")

            #link edge to handle to move
            edge.setStart((handle,handle)) #Handles are dummy nodes _and_ ports
        else:
            self.EdgeEnd = "end"
            # NOTE: Node relinking is only done on successful finish
            self.oldTermItem = edge.endNode
            edge.setEnd((handle,handle))

        handle.setFlag(QGraphicsItem.ItemIsMovable, True)

    def MoveEdgeEnd(self,edge,mPos):
        """edge is a VisEdgeItem, that has been set up for moving (cBs in place) """
        self.handle.setPos(mPos) 
        edge.updateLine(self.handle)
        
    def finishMovingEdgeEnd(self,edge,mPos,mouseEvent):
        """ note pickItemAt needs the full mouseEvent (screenPos) """
        #Check that this is on a valid node/ Termination pt
        newTermItem = self.pickItemAt(mouseEvent, QSize(HITSIZE,HITSIZE),[ROLE_NODE, ROLE_BLOB])

        if newTermItem != None:
            #print(f"finMovEdge {newTermItem.metadata['name']} {mPos=}")
            if newTermItem == self.oldTermItem[0]: #Just reposition the port
                #print(f"finMove - updating port {self.oldTermItem[1].index} ")
                self.oldTermItem[0].updatePort(self.oldTermItem[1],mPos)
                #TODO: Check this for flow with rest of func!
                if self.EdgeEnd == "start":
                    edge.setStart(self.oldTermItem)
                else:  #end
                    edge.setEnd(self.oldTermItem)
                #return
            #Check for a self-edge: newTerm == startE and we were moving `end` or the other end is now looped back
            #  if so, make sure there is a mid point in the  polyline line
            elif (newTermItem == edge.startNode[0] and self.EdgeEnd == "end") or \
                newTermItem == edge.endNode[0] and self.EdgeEnd == "start":
                print(f"Self edge {self.EdgeEnd}")
                if len(edge.edgeLine._p) < 3:
                    #add in a point on the middle for now. (only works for straight, splines are OK)
                    #TODO: Refine!!!
                    edge.edgeLine.addPoint(newTermItem.pos()+QPointF(HITSIZE*4,HITSIZE*4))

            #Unlink Edge from handle, link to newItem, (if we have really moved:)
            #TODO **Crashes on "move back" - port counting mangled**
            if self.EdgeEnd == "start":
                # Delete the old port
                oldP = self.oldTermItem[1]  #.index
                #print(oldP)
                self.oldTermItem[0].deletePort(oldP)
                #Unlink from the old node
                self.oldTermItem[0].startsEdges.remove(edge)
                self.oldTermItem[1].startsEdgeLines.remove(edge)

                # Add a port at mPos
                p = newTermItem.createPort(mPos)
                newTermItem = (newTermItem, p)
                edge.setStart(newTermItem)
                #relink self.oldTermItem in Graph
                # While clunky, these params will work with any item type
                self.model.Gr.updateEdge(edge.data(KEY_INDEX) ,self.oldTermItem[0].data(KEY_INDEX), "start", newTermItem[0].data(KEY_INDEX))
                #Relink to new node
                newTermItem[0].startsEdges.append(edge)
                newTermItem[1].startsEdgeLines.append(edge)
            
            if self.EdgeEnd == "end":
                #TODO: The port code is true for either end - review flow of function and tidy up
                # Delete the old port
                oldP = self.oldTermItem[1]   #.index
                #print(oldP)
                self.oldTermItem[0].deletePort(oldP)
                #Move the reverse pointer from the oldTermItem to the new:
                self.oldTermItem[0].endsEdges.remove(edge)
                self.oldTermItem[1].endsEdgeLines.remove(edge)
                # Add a port at mPos
                p = newTermItem.createPort(mPos)
                newTermItem = (newTermItem, p)
                edge.setEnd(newTermItem)
                self.model.Gr.updateEdge(edge.data(KEY_INDEX) ,self.oldTermItem[0].data(KEY_INDEX), "end", newTermItem[0].data(KEY_INDEX))
                
                newTermItem[0].endsEdges.append(edge)
                newTermItem[1].endsEdgeLines.append(edge)
        
        else: # link back to old
            #print("Missed (nothing found) on relink")
            self.handle.setPos(self.oldTermItem[1].pos())
            #TODO: Check all the linkages ()
            if self.EdgeEnd == "start":
                edge.setStart(self.oldTermItem)
            else:  #end
                edge.setEnd(self.oldTermItem)

        self.handle = None

    def clearEdgeOnly(self, edge):
        """ Remove the controlboxes from an edge and deselect."""
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

    def clearSelection(self):
        for item in self.selectedItems():
            item.isOnlySelected=False
        return super().clearSelection()
        
    def mousePressEvent(self, mouseEvent):
        
        mPos = mouseEvent.scenePos()
        #Track the last mouse position for Pointer moves
        self._lastMousePos = mPos

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
            if mouseEvent.modifiers() and Qt.ControlModifier and \
                    self.mouseMode==self.POINTER and len(self.selectedItems())>0:
                selItem = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_EDGE,ROLE_NODE,ROLE_BLOB])
                if selItem:
                    selItem = selItem[0]
                    if self.thisHandleObjectSelected:
                        self.thisHandleObjectSelected._deleteHandles()
                        self.thisHandleObjectSelected=None
                    lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))
                    self.changedByCode=True
                    self.listWidget.setCurrentItem(lWItem, QItemSelectionModel.SelectionFlag.Toggle)
                    self.changedByCode=False
                    super().mousePressEvent(mouseEvent)
                    return
     
            if self.mouseMode==self.POINTER:
                selItems = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_HANDLE])
                if len(selItems) > 0:
                    selItem=selItems[0]
                    #it's a handle, process
                    #selItem.setSelected(True)   JH Handles aren't selectable
                    p = selItem.parentItem()
                    #p.setSelected(True)  JH should already be selected
                    #p._createHandles()   #JH to figure out blobs testing
                    # p.parentItem.setSelected(True)
                    if p.data(KEY_ROLE) == ROLE_POLYLINE and (selItem == p._pHandles[0] or selItem == p._pHandles[-1]):
                        self.mouseMode = self.MOVEEDGEEND
                        #Start move
                        #selHandles  _Must_ be a handle, and parent must be a visEdge - deal with the polyline inbetween
                        self.startMovingEdgeEnd(selItem.parentItem().parentItem(), selItem)
                    else: #tangent or Mid point, or Blob corner to move
                        self.handle = selItem
                        self.mouseMode = self.MOVEHANDLE
                        if p.data(KEY_ROLE) == ROLE_BLOB:
                            selItem.setMoveCallback(p._updateFromHandles)  #JH
                        #BUG - DRagging - this stops dragging from an edge, but not having it breaks tangent update values
                        #mouseEvent.accept()
                        #return
                    mouseEvent.accept()
                    return
      
            if len(self.selectedItems())>1:
                self.mouseMode=self.DRAGGING #or in the middle of a modifier selection
                # hand over to QT? or exit?
                super().mousePressEvent(mouseEvent)
                return
            # in all other cases clear selection
            self.clearSelection()
            self.listWidget.clearSelection()
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
                newAction=createNodeCommand(mPos, self, self.model, self.listWidget)
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
                itm = self.pickItemAt(mouseEvent,QSizeF(10,10),[ROLE_NODE, ROLE_BLOB]) #,ROLE_EDGE
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
                itm = self.pickItemAt(mouseEvent,QSizeF(10,10),[ROLE_NODE, ROLE_BLOB]) #,ROLE_EDGE
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
                selItem = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_EDGE,ROLE_HANDLE,ROLE_NODE,ROLE_BLOB, ROLE_POLYLINE])
                if selItem:
                    selItem = selItem[0]
                #else:
                #    selItem = None
                    if selItem.isHovered:   #This stops it selecting just out of reach of the border line
                        if selItem.data(KEY_ROLE) == ROLE_NODE:
                            self.changedByCode=True
                            lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))
                            self.listWidget.setCurrentItem(lWItem)
                            self.changedByCode=False
                            selItem.isOnlySelected = True
                            selItem.setSelected(True)
                            super().mousePressEvent(mouseEvent)
                            return
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
                            lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))
                            self.listWidget.setCurrentItem(lWItem)
                            self.changedByCode=False
                            # accept? return?

                        if selItem.data(KEY_ROLE) == ROLE_POLYLINE :
                            # save handleobject and create handles
                            self.thisHandleObjectSelected=selItem
                            self.onlySelected=selItem
                            selItem.setSelected(True)
                            parent = selItem.parentItem()
                            parent.setSelected(True)
                            parent.isOnlySelected = True
                            selItem._createHandles()

                            #selItem.setSelected(False)
                            #selItem = parent
                            #selItem.setSelected(True) # check this
                        # super().mousePressEvent(mouseEvent)
                        # return
                        
                        if selItem.data(KEY_ROLE) == ROLE_EDGE:
                            if not selItem.stH:
                                selItem.setZValue(2000) #move the edge above nodes
                            # item.stHandle must be the 1st point handle: item.edgeLine._pHandles[0]
                            #print("Setting stH", end="")
                                if len(selItem.edgeLine._pHandles)>0:
                                    selItem.stH = selItem.edgeLine._pHandles[0]
                                    selItem.endH = selItem.edgeLine._pHandles[-1]
                                else:
                                    print("No handles yet")
                            self.changedByCode=True
                            lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))
                            self.listWidget.setCurrentItem(lWItem)
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
                                ("add Point","addPt" ),
                                ("del Point","delPt" ),
                                ("Edit Details", lambda: self.mainwindow.showEditEdgeDialog(item))
                            ]
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
                    item.edgeLine._deleteHandles()
                    item.edgeLine.addPoint(mPos)
                    item.edgeLine.setSelected(True)

                elif cxChoice == "delPt":
                    item.edgeLine.deletePoint(mPos)

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
        items=self.itemsHere(mPos, QSize(HITSIZE,HITSIZE), [ROLE_NODE, ROLE_BLOB])
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
                        item.edgeLine.moveMidPoints(delta)
                        #print("e" , end ="")
            
        elif self.mouseMode == self.MOVEEDGEEND:
            self.MoveEdgeEnd(self.onlySelected.parentItem(),mPos)
            mouseEvent.accept()
            
        elif self.mouseMode == self.MOVEHANDLE:
            #print("Move Handle")
            #Same code as moveEdgeEnd
            self.handle.setPos(mPos) 
              
        super().mouseMoveEvent(mouseEvent)

    def mouseReleaseEvent(self, mouseEvent):
        mPos = mouseEvent.scenePos()
        #print(f"release {self.mouseMode =}")
        if (mouseEvent.button() == Qt.MouseButton.RightButton) and\
                mouseEvent.modifiers() and Qt.ControlModifier: 
            screamText=self.addText("Screams")
            screamText.deleteLater
            #self.posnLabel.deleteLater
            #self.update()
        if self.mouseMode == self.INSERTNODE:
            #print("Node release at :",mouseEvent.scenePos())
            #print("up node")
            #TODO: Clear selection after adding a node (or before?)
            self.clearSelection()
            self.updateBlobParenting()
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
            blob = VisBlobItem(QPointF(TLx,TLy),self.model, self.listWidget, 
                            height = height, width = width,
                            xRadius = BLOB_CORNER_RADIUS, yRadius = BLOB_CORNER_RADIUS)
            self.addItem(blob)
            self.updateBlobParenting()
            self.mouseMode = self.POINTER
            mouseEvent.accept()
            return
        elif self.mouseMode == self.INSERTEDGE:
            #print("up edge")
            #CreateEdge code 
            #TODO: Put this in its own function
            if self.tmpEdgeSt:
                itm = self.pickItemAt(mouseEvent,QSizeF(10,10),[ROLE_NODE,ROLE_BLOB]) # add ,ROLE_EDGE to the list for multigraphs
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
                if not(mouseEvent.modifiers() and Qt.ControlModifier):
                    self.listWidget.clearSelection()
                    self.changedByCode=True
                    for selItem in self.selectedItems():
                        lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))  
                        self.listWidget.setCurrentItem(lWItem, QItemSelectionModel.SelectionFlag.Select)
                    self.changedByCode=False
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
            self.finishMovingEdgeEnd(self.onlySelected.parentItem(), mPos,mouseEvent)
            self.mouseMode = self.POINTER
            self.views()[0].setCursor(Qt.ArrowCursor)
            mouseEvent.accept()
            #return
        elif self.mouseMode == self.MOVEHANDLE:
            #SHOULD all be handled by Qt? or callback?
            #print("End move handle")
            self.mouseMode = self.POINTER
        elif self.mouseMode == self.DRAGGING:
            if self.qtListToListOfIdxs(self.selectedItems()) != self.qtListToListOfIdxs(self.listWidget.selectedItems()):
                #update listview
                self.listWidget.clearSelection()
                self.changedByCode=True
                for selItem in self.selectedItems():
                    lWItem = self.listWidget.findItemByIdx(selItem.data(KEY_INDEX))  
                    self.listWidget.setCurrentItem(lWItem, QItemSelectionModel.SelectionFlag.Select)
                self.changedByCode=False
            #print(f"up: DRAGGING --> POINTER")
            self.mouseMode = self.POINTER
        
        #Only do this on release, for performance reasons.
        self.updateBlobParenting()

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

    def updateBlobParenting(self):
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
                sItem.parents = []
                sItem.children = []
                self.model.Gr.nodeD[sItem.nodeNum].resetParents([])
                self.model.Gr.nodeD[sItem.nodeNum].resetChildren([])
        
        #Recreate lists
        for parent, children in sorted(directChildList.items()):
            pItem = self.findItemByIdx(parent)
            self.model.Gr.nodeD[parent].resetChildren(children)

            for c in children:
                cItem = self.findItemByIdx(c)
                pItem.children.append(cItem)
                self.model.Gr.nodeD[c].addParent(parent)
                cItem.parents.append(pItem)


    def signalTest(self):
        print("signal sent to scene successfully")

    def findItemByIdx(self,idx):
        """takes a ROLE_INDEX value, and return the item out, or none """
        for item in self.items():
            if item.data(KEY_INDEX) == idx:
                return item
        return None

    def deleteItemAndChildren(self,item):
        #print(f" start dIC for {item}")
        #BUG:DeleteEdge This leaves a the line/ polyline 'in the scene' (but not in scene.getItems()!)
        #Trying https://pypi.org/project/referrers/ to look for links
        #1st try overflows the line allocation in VSCodium
        #import referrers
        #print(referrers.get_referrer_graph(item))

        #TODO: Make this recursive, deleting leaves first (Python/ C++ memory handling issue - see old code in V00)
        # Recursively remove and delete children. Action is post-recursion to delete from the bottom up
        #TODO - why does doing this cause index errors (use b2.grml, multiple select, as test)
        #for child in item.childItems():
        cList = item.childItems()
        for child in cList:
            #print(f"dIC {child}")
            self.deleteItemAndChildren( child)
        
        #print(f"   now processing dIC for {item}")
        item.suppressItemChange = True
        #unparent
        #item.setParentItem(None)
        # Remove from scene
        #if its an edge, tell the nodes ends that the edge is gone
        if item.data(KEY_ROLE) == ROLE_EDGE:
            item.startNode[0].startsEdges.remove(item)
            #print(f"{item.endNode = }") #eItem
            item.endNode[0].endsEdges.remove(item)
            item.startNode[1].startsEdgeLines.remove(item)
            item.endNode[1].endsEdgeLines.remove(item)
            #print(f"{item.endNode.endsEdges =}")
        #print(f"{item =}")  
        #logging.debug("delItem&chld scene items, BEFORE remove")
        #for i in self.items():
        #    logging.debug(f"{i =}")        
        
        # Register a finalize callback to confirm deletion
        #weakref.finalize(item, self._on_finalize, repr(item))

        item.suppressItemChange = False  
        self.removeItem(item)
        #import referrers
        #print(referrers.get_referrer_graph(item, max_depth=3))
        
        #logging.debug("delItem&chld scene items, AFTER remove")
        #for i in self.items():
        #    logging.debug(f"{i =}")
        #Item now belongs to Scene, del from memory
        #forcing the del will crash sooner. Otherwise, crashes on GC?
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
    def __init__(self, posn, scene, model, listWidget):
        super().__init__()
        self.node = None  
        self.posn = posn
        self.scene = scene
        self.model = model
        self.listWidget=listWidget
        self.nodeNum = 0 #placeholder

    def undo(self):
        #delIdx = self.node.data(KEY_INDEX)
        delIdx = self.nodeNum
        self.scene.mainwindow.delNode(delIdx)

    def redo(self):
        #VisNodeItem adds to the model and the  list
        if self.node==None:   # this is the first actual create of the node
            newNode =  VisNodeItem(self.posn,self.model,self.listWidget)
            # save the node index for recreating identically
            self.nodeNum = newNode.nodeNum
            #update port  PARENTS (maybe recompute position?)
            #for p in newNode._Ports:
            #    p.setParentItem(newNode.nodeShape)
        else:   # this is creation after deleting
            #newNode =  VisNodeItem(self.posn,self.node.model,self.node.listWidget ,nameP=self.node.metadata['name'], \
            #                   id = self.node.nodeNum, metadata=self.node.metadata, \
            #                    metadataAttributes=self.node.metadataAttributes, ports=self.node._Ports)
            newNode =  VisNodeItem(self.posn,self.model,self.listWidget, id=self.nodeNum)
            
        #update port  PARENTS (maybe recompute position?)
        #for p in newNode._Ports:
        #    p.setParentItem(newNode)
        newNode.setPos(self.posn)
        #Add to *Scene*
        self.scene.addItem(newNode)

        newNode.setFlag(QGraphicsItem.ItemIsSelectable, True)
        newNode.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.node=newNode   

class deleteNodeCommand(QUndoCommand):
    def __init__(self, node, posn, scene, model, listWidget):
        super().__init__()
        self.node = node
        self.nodeNum = self.node.nodeNum
        self.posn = posn
        self.scene = scene
        self.model = model
        self.listWidget=listWidget
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

    def undo(self):
        #VisNodeItem adds to the model and the  list
        #newNode =  VisNodeItem(self.posn,self.node.model,self.node.listWidget ,nameP=self.node.metadata['name'], \
        #                    id = self.node.nodeNum, metadata=self.node.metadata, \
        #                    metadataAttributes=self.node.metadataAttributes, ports=self.ports)
        newNode =  VisNodeItem(self.posn,self.model,self.listWidget ,nameP=self.metadata['name'], \
                            id = self.nodeNum, metadata=self.metadata, \
                            metadataAttributes=self.metadataAttributes, ports=self.ports)
        #update port  PARENTS (maybe recompute position?)
        #for p in newNode._Ports:
        #    p.setParentItem(newNode)
        newNode.setPos(self.posn)
        #Add to *Scene*
        self.scene.addItem(newNode)   
        newNode.setFlag(QGraphicsItem.ItemIsSelectable, True)
        newNode.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.node=newNode
        #now read any edges that were deleted with the node
        #(I really don't know how it re-adds the ports so easily)
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
            newEdge = VisEdgeItem(self.model,self.listWidget,edgeItem[0].startNode, edgeItem[0].endNode, 
                                directed=edgeItem[0].isDirected,  nameP=edgeItem[0].metadata['name'], id = edgeItem[0].edgeNum,
                                polyLineType = edgeItem[0]._polyEdge, points=edgeItem[1][1:-1], #exclude edgepoints
                                tangents=edgeItem[2], metadata=edgeItem[0].metadata, metadataAttributes=edgeItem[0].metadataAttributes)
            
            self.scene.addItem(newEdge)

    def redo(self):
        delIdx = self.node.data(KEY_INDEX)   #should use self.nodeNum
        self.scene.mainwindow.delNode(delIdx)
        
class createEdgeCommand(QUndoCommand):
    def __init__(self, edge, scene, model, listWidget, startNode, endNode, parent=None):
        super().__init__()
        self.edge = edge
        self.edgeNum=0 #placeholder
        self.scene = scene
        self.model = model
        self.listWidget=listWidget
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
            newEdge = VisEdgeItem(self.model,self.listWidget,self.startNode, self.endNode)                              
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
            newEdge = VisEdgeItem(self.model,self.listWidget,self.startNode, self.endNode, 
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
    def __init__(self, edge, scene, model, listWidget, startNode, endNode, parent=None):
        super().__init__()
        self.edge = edge
        self.edgeNum=edge.edgeNum
        self.scene = scene
        self.model = model
        self.listWidget=listWidget
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
        if self.edge != None and self.edge.edgeLine._t:
            self.tangentPoints=self.edge.edgeLine._t
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
        newEdge = VisEdgeItem(self.model,self.listWidget,self.startNode, self.endNode, 
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

def XXfindItemByIdx(self,idx):
    """another patch to LWid
      feed in a ROLE_INDEX value, and get the ITEM out, or none """
    for row in range(self.count()):
        item = self.item(row)
        if item.data(KEY_INDEX) == idx:
            return item
    return None
QListWidget.findItemByIdx = findItemByIdx

def findItemRowByIdx(self,idx):
    """another patch to LWid
      feed in a ROLE_INDEX value, and get the item ROW of the item out, or none """
    for row in range(self.count()):
        item = self.item(row)
        if item.data(KEY_INDEX) == idx:
            return row
    return None
QListWidget.findItemRowByIdx = findItemRowByIdx

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
        self.ui.listWidget.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
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
        self.ui.listWidget.setSortRoles( (KEY_ROLE,KEY_INDEX) )
        self.ui.listWidget.itemChanged.connect(self.updateSceneText)
        #self.ui.listWidget.itemClicked.connect(self.listClick) # this is now called by itemSelectionChanged
        self.ui.listWidget.itemDoubleClicked.connect(self.listDblClicked)
        
        self.undoStack=QUndoStack()

        #Setup the graphicsView, linking model,scene and list. Scene needs to know the mainwindow to call dialogs, etc
        self.Scene = grScene(self.model,self.ui.listWidget, self.undoStack, self)
        #self.Scene.selectionChanged.connect(self.actionSceneSelectChange)
        self.ui.listWidget.itemSelectionChanged.connect(self.actionListSelectChange)

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
        self.Scene.mouseMode = grScene.INSERTBLOB
        #self.actionPointer.setChecked(False)
        self.statusBar().showMessage("Insert Blob",3000)

    def actionNewEdge(self):
        self.statusBar().showMessage("Insert Edge",3000)
        #print("Add an edge")
        self.Scene.mouseMode = grScene.INSERTEDGE

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
        idx = item.data(KEY_INDEX)
        for sItem in self.Scene.items():
            if sItem.data(KEY_ROLE) in [ROLE_NODE, ROLE_EDGE,ROLE_BLOB]:
                if sItem.data(KEY_INDEX) == idx: # iNum:
                    sItem.setSelected(True)
                    if sItem.data(KEY_ROLE) in [ROLE_EDGE]:
                        self.Scene.thisHandleObjectSelected=sItem.edgeLine
                        self.Scene.onlySelected=sItem.edgeLine
                        sItem.edgeLine.setSelected(True)
                        sItem.isOnlySelected=True
                        sItem.edgeLine._createHandles()
                        if not sItem.stH:
                            sItem.setZValue(2000) #move the edge above nodes
                            if len(sItem.edgeLine._pHandles)>0:
                                sItem.stH = sItem.edgeLine._pHandles[0]
                                sItem.endH = sItem.edgeLine._pHandles[-1]
                            else:
                                print("No handles yet")
                    elif sItem.data(KEY_ROLE) in [ROLE_BLOB]:
                        self.Scene.thisHandleObjectSelected=sItem
                        self.Scene.onlySelected=sItem
                        sItem.setSelected(True)
                        sItem.isOnlySelected=True
                        sItem._createHandles() #JH
                    # sItem.edgeLine._createHandles()

                    #print(idx)
                    #break

    def listDblClicked(self,item):
        #print("listDblClicked", item.text(), item.index())
        #item.setFlags(item.flags() | Qt.ItemIsEditable)
        #self.ui.listWidget.editItem(item)
        #print(f"Editing {item.text() =}, id = {item.data(KEY_INDEX)}")

        #copilot Integration: If the double-clicked item is an edge, open the edit dialog
        if item.data(KEY_ROLE) == ROLE_EDGE:
            # Find the corresponding VisEdgeItem in the scene
            edgeItem = self.Scene.findItemByIdx(item.data(KEY_INDEX))
            if edgeItem:
                #TODO: This should be a signal? (but I can't make them work)
                self.showEditEdgeDialog(edgeItem)
        elif item.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
            nodeItem = self.Scene.findItemByIdx(item.data(KEY_INDEX))
            if nodeItem:
                self.showEditNodeDialog(nodeItem)
        else: #Not called anymore?
            item.setFlags(item.flags() | Qt.ItemIsEditable)
            self.ui.listWidget.editItem(item)

        self.updateSceneText(item)

    def updateSceneText(self,item):
        """ Code for the listWidget to tell the scene that something has changed (name)"""
        #Maybe should be updateMODELText - scene updates via the model?

        #print("Upddata_blobate scene text")
        #print(f"updateSceneText id = {item.data(KEY_INDEX)} {item.text()}::{item.data(KEY_ROLE)}")

        iNum = item.data(KEY_INDEX)
        #print(f"{item.text()}::{item.data(KEY_INDEX)}>{item.data(KEY_ROLE)} {iNum =}")
        new_text = item.text()
        itemModelRow=self.model.findRowByIdx(iNum)
        self.model.item(itemModelRow).setText(new_text)
        #TODO: The list update should trigger some change flag/ be embedded 
        if item.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
            self.model.Gr.nodeD[iNum].metadata.update({'name':new_text})
        elif item.data(KEY_ROLE) == ROLE_EDGE:
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
        self.ui.listWidget.repaint()

    def actionListSelectChange(self):
        if not self.Scene.changedByCode:
            selected_items = self.ui.listWidget.selectedItems()
            if len(selected_items)>1:
                if self.Scene.thisHandleObjectSelected:
                    self.Scene.thisHandleObjectSelected._deleteHandles()
                    self.Scene.thisHandleObjectSelected=None
                    self.Scene.onlySelected=None
                self.Scene.clearSelection()
                for item in selected_items:
                    idx = item.data(KEY_INDEX)
                    for sItem in self.Scene.items():
                        if sItem.data(KEY_ROLE) in [ROLE_NODE, ROLE_EDGE,ROLE_BLOB]:
                            if sItem.data(KEY_INDEX) == idx: # iNum:
                                sItem.setSelected(True)
            else:
                if len(selected_items)!=0:
                    self.listClick(selected_items[0])

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



    #Menu-like Actions
    def action_FileNew(self):
        #print("FileNew")
        #Tidy up where we are
        """self.Scene.clearSelection()
        if self.Scene.onlySelected:
            self.Scene.onlySelected.isOnlySelected =False
        self.Scene.onlySelected = None
        self.Scene.thisHandleObjectSelected = None"""
        self.action_EditSelectNone()
        
        #clear window vars
        self.setWindowTitle(APP_NAME +"[*]")
        self.fileName = ""

        #clear model
        self.model.clear()
        #clear ListW
        self.ui.listWidget.clear()
        #Clear Scene
        #TODO: Reset the temp vars for odd reloads
        # eg self.onlySelected
        #suppress itemChanged processing (will put the flag on _everything_, which is ugly, but easy.)
        for i in self.Scene.items():
            i.suppressItemChange = True
        self.Scene.clear()

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

        newNode =  VisNodeItem(QPointF(nodeX,nodeY),self.model,self.ui.listWidget ,nameP=nodeName, id = id,
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

        newBlob =  VisBlobItem(QPointF(blobX,blobY),self.model,self.ui.listWidget, width=blobWidth,\
                               height=blobHeight, xRadius=blobXRadius, yRadius=blobYRadius,\
                                nameP=blobName, id = id, \
                                metadata=blobMetadata, metadataAttributes=blobMetadataAttributes,ports=nodePorts)
        
        newBlob.suppressItemChange = True

        #update port  PARENTS 
        for p in newBlob._Ports:
            p.setParentItem(newBlob)  #JH should be shape?

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
        if eItem == None:
            print(f"WARNING! - End Item ID {eItemID} not found ")
        
        #Add the port
        sItem = (sItem, sItem.portFromIndex(srcPort))
        eItem = (eItem, eItem.portFromIndex(tgtPort))
        #

        directed = xEdge.attrib.get("directed", '')
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
        newEdge = VisEdgeItem(self.model,self.ui.listWidget,sItem, eItem, 
                                directed=directed,  nameP=edgeName, id = id,
                                polyLineType = polyLineType, points=points,tangents=tangents,
                                metadata=edgeMetadata, metadataAttributes=edgeMetadataAttributes   )

        return newEdge

    def action_FileOpen(self):
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
        oldToNewID = {}

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
            oldToNewID[fileID] = GItem.nodeNum
            #TODO: Do something meaningful with mismatches
            #if fileID != GItem.nodeNum:
            #    print(f"WARNING: node id {fileID=} changed on load")
            
            self.Scene.addItem(GItem)
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
            oldToNewID[fileID] = GItem.nodeNum
            #TODO: Do something meaningful with mismatches
            #if fileID != GItem.nodeNum:
            #    print(f"WARNING: node id {fileID=} changed on load")
            
            self.Scene.addItem(GItem)
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
                                            newStartID=oldToNewID[sItemID],
                                            newEndID = oldToNewID[eItemID])

            #Add to Scene
            self.Scene.addItem(edgeItem)
            edgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            edgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)
        
        self.Scene.update()

        self.setWindowTitle(str(os.path.basename(self.fileName)) + " " + APP_NAME + "[*]")

        self.setZoom(100)
        zoomToFitWithMargin(self.ui.graphicsView, margin=0.2)

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
            print("\nListView items:\n",
               "\n".join([self.ui.listWidget.item(x).text()+ \
                " ID:"+str(self.ui.listWidget.item(x).data(KEY_INDEX))+ \
                " type:"+str(self.ui.listWidget.item(x).data(KEY_ROLE)) \
                    for x in range(self.ui.listWidget.count())]))
            #graphics View ~= scene
            print("\nui.graphicsView items:\n","\n   ".join([str(itm) \
                for itm in self.ui.graphicsView.items()]))
            
            lstr = "core Graph Model\n"+ str(self.model.Gr)
            lstr += f"model items {self.model.getModelItems()} \n"
            lstr += "\nListView items:\n"
            lstr += "\n".join([self.ui.listWidget.item(x).text()+ " ID:"+str(self.ui.listWidget.item(x).data(KEY_INDEX))+ \
                " type:"+str(self.ui.listWidget.item(x).data(KEY_ROLE)) for x in range(self.ui.listWidget.count())])
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
                if sItem.startNode[0] in selectedItems and sItem.endNode[0] in selectedItems:
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
        oldToNewID = {}
        for xNode in graphStr.iter("node"):
            #print(f"FileOpen - nodes: {ET.tostring(xNode)=}")
            GItem = self.nodeFromXML(xNode, newID=True)
            oldToNewID[int(xNode.attrib.get("id"))] = GItem.nodeNum

            #Bump the pasted items over by PASTE_OFFSET
            GItem.moveBy(PASTE_OFFSET,PASTE_OFFSET)
            
            self.Scene.addItem(GItem)
            GItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            GItem.setFlag(QGraphicsItem.ItemIsMovable, True) 
            GItem.setSelected(True)   

        #blobs
        for xBlob in graphStr.iter("blob"):
            #print(f"FileOpen - nodes: {ET.tostring(xNode)=}")
            GItem = self.blobFromXML(xBlob, newID=True)
            oldToNewID[int(xBlob.attrib.get("id"))] = GItem.nodeNum

            #Bump the pasted items over by PASTE_OFFSET
            GItem.suppressItemChange = True
            GItem.moveBy(PASTE_OFFSET,PASTE_OFFSET)
            GItem.suppressItemChange = False

            self.Scene.addItem(GItem)
            GItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            GItem.setFlag(QGraphicsItem.ItemIsMovable, True) 
            GItem.setSelected(True)   
        #Edges
        for xEdge in graphStr.iter("edge"):
            sItemID = int(xEdge.attrib.get("source", None))
            eItemID = int(xEdge.attrib.get("target", None))

            #BUG - edges don't work on paste - ID's have changed!

            edgeItem = self.edgeFromXML(xEdge, newID=True, 
                                            newStartID=oldToNewID[sItemID],
                                            newEndID = oldToNewID[eItemID])
            #Bump any polyline points over
            for pt in edgeItem.edgeLine._p:
                pt += QPointF(PASTE_OFFSET,PASTE_OFFSET)

            #Add to Scene
            self.Scene.addItem(edgeItem)
            edgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True)
            edgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)
            edgeItem.setSelected(True)
        
        self.Scene.update()

    #Some helper functions for deletion

    def delEdge(self, delIdx):
        """ all the calls to delete an edge"""
        #delete from model
        self.model.delEdge(delIdx)
        #Delete from LWscene updat
        delRow = self.ui.listWidget.findItemRowByIdx(delIdx)
        delItem = self.ui.listWidget.takeItem(delRow)
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

    def delNode(self, delIdx):
        """ all the calls to delete an node"""
        #TODO: Pop a warning dialog when deleting the edges

        #Check for any edges attached and delete
        eList = self.model.edgesAtNode(self.Scene.findItemByIdx(delIdx))
        if eList:
            for e in eList:
                self.delEdge(e)
        if self.Scene.thisHandleObjectSelected==self.Scene.findItemByIdx(delIdx):
            self.Scene.thisHandleObjectSelected = None

        #Delete from Scene first, since there are complex deps to other parts which get in a knot
        self.Scene.deleteItemAndChildren(self.Scene.findItemByIdx(delIdx))

        #delete from model
        self.model.delNode(delIdx)

        #Delete from LW
        delRow = self.ui.listWidget.findItemRowByIdx(delIdx)
        delItem = self.ui.listWidget.takeItem(delRow)
        del delItem


    def action_EditDelete(self):
        #print("Edit>Delete")
        #Edge Delete (must delete edges 1st)
        selected_items = self.Scene.selectedItems()
        self.Scene.clearSelection()
        if selected_items:
            for item in selected_items:
                #print(self.model.itemName(item))
                if item.data(KEY_ROLE) == ROLE_EDGE:
                    delIdx = item.data(KEY_INDEX)
                    #self.delEdge(delIdx)
                    newAction=deleteEdgeCommand(item, self.Scene, self.model, self.ui.listWidget, item.startNode, item.endNode, parent=None)
                    self.undoStack.push(newAction)
            #Node delete - 1st del any connected edges - handled by GrScene
            for item in selected_items:
                if item.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
                    delIdx = item.data(KEY_INDEX)
                    #self.delNode(delIdx)
                    newAction=deleteNodeCommand(item, item.scenePos(), self.Scene, self.model, self.ui.listWidget)
                    self.undoStack.push(newAction)

        #logging.debug("about to update from action_EditDelete",stack_info=True  )
        #gc.collect() #This will crash the whole thing, with no traces
        #debug_qgraphicsitem_refs()  #More coPilot code ...

        #self.Scene.update()
        #Trying to get rid of the orphan lines - which go when the view changes so that scrollbars are added.
        self.Scene.invalidate(self.Scene.sceneRect(), QGraphicsScene.AllLayers)
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
                lWItem = self.Scene.listWidget.findItemByIdx(item.data(KEY_INDEX))
                self.Scene.listWidget.setCurrentItem(lWItem, QItemSelectionModel.SelectionFlag.Select)                    
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
        self.Scene.listWidget.clearSelection()

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
        dlg = EditVisEdgeItemDialog(visEdgeItem, parent=self)
        if dlg.exec() == dlg.accepted:
            # Attributes are already updated by the dialog's accept method
            self.Scene.update()
            self.ui.listWidget.repaint()

    def showEditNodeDialog(self, visNodeItem):
        dlg = EditVisNodeItemDialog(visNodeItem, parent=self)
        if dlg.exec() == dlg.accepted:
            # Attributes are already updated by the dialog's accept method
            self.Scene.update()
            self.ui.listWidget.repaint()


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