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
import traceback  #for the Python window

#For file handling and clipboard
import xml.etree.ElementTree as ET
from xml.dom import minidom

#Debugging stuff

#import logging
#import gc
import weakref

from typing import List, Dict

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
from PySide6.QtSvg import QSvgGenerator
from PySide6.QtPrintSupport import QPrinter, QPrintDialog

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

    def __init__(self, model,listWidget,mainwindow):
        super().__init__()
        self.model = model
        self.listWidget = listWidget
        self.mainwindow = mainwindow
        self.mouseMode = self.POINTER

        # Placeholders for nodes & edges between mouse states when creating an edge
        self.tmpEdgeSt = None #QGraphicsItem - temp start
        self.tmpEdgeEnd = None
        self.startPoint = None #QPoints, to draw the edge's line/ Blob rectangle
        self.endPoint = None
        self.rubberLine = None
        self.GrRubberLine =None

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



    def itemsHere(self, pos: QPointF, size: QSizeF, itemRoles: List[int]):
        """Return a list of the items who's roles match `itemRoles`, within `size` of `pos` """
        half_w = size.width() / 2
        half_h = size.height() / 2
        rect = QRectF(pos.x() - half_w, pos.y() - half_h, size.width(), size.height())
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
        
    #Code to handle the edge rubber banding during creation (QT handles edit changes)

    def startRubberLine(self, mPos):
        """ called from INSERTEDGE: mousePress. All vars are class global """
        #lock the start item in place so that it doesn't drag
        self.tmpEdgeSt.setFlag(self.tmpEdgeSt.GraphicsItemFlag.ItemIsMovable, False)
        
        #This will change when the whole boundary/ edge can be a connection point
        self.startPoint = self.tmpEdgeSt.pos()
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

        #Create the actual edge
        edgeItem = VisEdgeItem(self.model,self.listWidget,self.tmpEdgeSt, self.tmpEdgeEnd, parent=None)
        #Add to *Scene*
        self.addItem(edgeItem)
        edgeItem.setFlag(QGraphicsItem.ItemIsSelectable, True) #can't select a node to move it due to drawing order
        edgeItem.setFlag(QGraphicsItem.ItemIsMovable, False)

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
        if self.handle.pos() == edge.startNode.pos():
            # NOTE: Node relinking is only done on successful finish, so track the old Terminator item
            self.EdgeEnd = "start"
            self.oldTermItem = edge.startNode
            #link edge to handle to move
            edge.setStart(handle)
        else:
            self.EdgeEnd = "end"
            # NOTE: Node relinking is only done on successful finish
            self.oldTermItem = edge.endNode
            edge.setEnd(handle)

        handle.setFlag(QGraphicsItem.ItemIsMovable, True)

    def MoveEdgeEnd(self,edge,mPos):
        """edge is a VisEdgeItem, that has been set up for moving (cBs in place) """
        self.handle.setPos(mPos) 
        edge.updateLine(self.handle)
        
    def finishMovingEdgeEnd(self,edge,mPos,mouseEvent):
        """ note pickItemAt needs the full mouseEvent (screenPos) """

        #Check that this is on a valid node/ Termination pt
        newTermItem = self.pickItemAt(mouseEvent, QSize(HITSIZE,HITSIZE),[ROLE_NODE, ROLE_BLOB])
        #print(f"finMovEdge {newTermItem.metadata['name']=} {mPos=}")
        if newTermItem:
            #Check for a self-edge: newTerm == startE or  endE
            #  if so, make sure there is a mid point in the  polyline line
            if newTermItem == edge.startNode or newTermItem == edge.endNode:
                if len(edge.edgeLine._p) < 3:
                    #add in a point on the middle for now. (only works for straight, splines are OK)
                    #TODO: Refine!!!
                    edge.edgeLine.addPoint(newTermItem.pos()+QPointF(HITSIZE*4,HITSIZE*4))

            #Unlink Edge from handle, link to newItem, (if we have really moved:)
            if self.EdgeEnd == "start":# and newTermItem != self.oldTermItem:
                edge.setStart(newTermItem)
                #relink self.oldTermItem in Graph
                # While clunky, these params will work with any item type
                self.model.Gr.updateEdge(edge.data(KEY_INDEX) ,self.oldTermItem.data(KEY_INDEX), "start", newTermItem.data(KEY_INDEX))
                #Move the reverse pointer from the oldTermItem to the new:
                self.oldTermItem.startsEdges.remove(edge)
                newTermItem.startsEdges.append(edge)
            
            elif self.EdgeEnd == "end":# and newTermItem != self.oldTermItem:  #end
                edge.setEnd(newTermItem)
                self.model.Gr.updateEdge(edge.data(KEY_INDEX) ,self.oldTermItem.data(KEY_INDEX), "end", newTermItem.data(KEY_INDEX))
                #Move the reverse pointer from the oldTermItem to the new:
                self.oldTermItem.endsEdges.remove(edge)
                newTermItem.endsEdges.append(edge)
        
        else: # link back to old
            #print("Missed (nothing found) on relink")
            self.handle.setPos(self.oldTermItem.pos())
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
            if self.mouseMode==self.POINTER:
                selItems = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_HANDLE])
                if len(selItems) > 0:
                    selItem=selItems[0]
                    #it's a handle, process
                    selItem.setSelected(True)
                    p = selItem.parentItem()
                    p.setSelected(True)
                    # p.parentItem.setSelected(True)
                    if p.data(KEY_ROLE) == ROLE_POLYLINE and (selItem == p._pHandles[0] or selItem == p._pHandles[-1]):
                        self.mouseMode = self.MOVEEDGEEND
                        #Start move
                        #selHandles  _Must_ be a handle, and parent must be a visEdge - deal with the polyline inbetween
                        self.startMovingEdgeEnd(selItem.parentItem().parentItem(), selItem)
                    else: #tangent or Mid point, or Blob corner to move
                        self.handle = selItem
                        self.mouseMode = self.MOVEHANDLE
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
            if self.thisHandleObjectSelected:
                self.thisHandleObjectSelected._deleteHandles()
                self.thisHandleObjectSelected=None

            # process menu insert objects
            if self.mouseMode == self.INSERTNODE:
                #TODO: For blobs, this will have to move to mouseRelease, to allow rectangle drag
                #Items sizes should be relative to (0,0)
                mPos = mouseEvent.scenePos()
                #VisNodeItem adds to the model and the  list
                item = VisNodeItem(mPos, self.model,self.listWidget)
                item.setPos(mPos)
                #Add to *Scene*
                self.addItem(item)

                item.setFlag(QGraphicsItem.ItemIsSelectable, True)
                item.setFlag(QGraphicsItem.ItemIsMovable, True)

                #TODO: Should this be actionPointer, to update the toolbar, etc
                self.mouseMode = self.POINTER
                mouseEvent.accept()
                return
            #
            if self.mouseMode == self.INSERTBLOB:
                self.startPoint = mouseEvent.scenePos()
                #TODO: Create the blob here, and draw a proper blob for creation, not a rect
                # JH check what needs to be set and where this goes (accept and return?)
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
#                else:
#                    selItem = None

                    if selItem.data(KEY_ROLE) == ROLE_NODE:
                        super().mousePressEvent(mouseEvent)
                        return
                    #immediately hand off for Qt to move
                    #BUG:Dragging With these on, DRAGGING doesn't happen, off, a single node select doesn't clear selection
                    #Solution: Move `isSelected` to mouseRelease, to allow for movement
                    #TODO: DRAGGING
                    #super().mousePressEvent(mouseEvent)
                    #return

                    if selItem.data(KEY_ROLE) == ROLE_BLOB:
                        print(f"Sel Blob {selItem.metadata['name']}")
                        self.onlySelected = selItem
                        self.thisHandleObjectSelected=selItem
                        selItem.isOnlySelected = True
                        selItem.setSelected(True)
                        # accept? return?

                    #If selecting a POLYLINE, bump select to parent - JH why?
                    if selItem.data(KEY_ROLE) == ROLE_POLYLINE :
                        # save handleobject and create handles
                        self.thisHandleObjectSelected=selItem
                        self.onlySelected=selItem
                        selItem.setSelected(True)
                        parent = selItem.parentItem()
                        parent.setSelected(True)
                        parent.isOnlySelected = True
                        selItem._createHandles()

                        #selItem.setSelected(False) # JH does this remove from QT selection also? Wait, this is Gcode
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
                            else:
                                print("No handles yet")
                        if not selItem.endH:
                        #print(", endH")
                             selItem.endH = selItem.edgeLine._pHandles[-1]
                        # will this ever be needed?
                        #selItem.setSelected(True) #JH do we need this?
                        #selItem.isOnlySelected = True
                    #Let the scene remember, for unsetting
                        #self.onlySelected = selItem
                        mouseEvent.accept()
                        return

            """if self.mouseMode == self.INSERTNODE:
                self.clearSelection()
                #For edges, was there only one selected? Clear.
                if self.onlySelected:
                    self.clearEdgeOnly(self.onlySelected)

                #TODO: For blobs, this will have to move to mouseRelease, to allow rectangle drag
                #Items sizes should be relative to (0,0)
                mPos = mouseEvent.scenePos()
                #print(f"Insert node: {mPos =}, \n{mouseEvent =}")
                #VisNodeItem adds to the model and the  list
                item = VisNodeItem(mPos, self.model,self.listWidget)
                item.setPos(mPos)
                #Add to *Scene*
                self.addItem(item)

                item.setFlag(QGraphicsItem.ItemIsSelectable, True)
                item.setFlag(QGraphicsItem.ItemIsMovable, True)

                #TODO: Should this be actionPointer, to update the toolbar, etc
                self.mouseMode = self.POINTER
                mouseEvent.accept()
                return
            elif self.mouseMode == self.INSERTBLOB:
                self.clearSelection()
                #For edges, was there only one selected? Clear.
                if self.onlySelected:
                    self.clearEdgeOnly(self.onlySelected)
                self.startPoint = mouseEvent.scenePos()
                #TODO: Create the blob here, and draw a proper blob for creation, not a rect

            elif self.mouseMode == self.INSERTEDGE:
                #print("Ins edge")
                self.clearSelection()
                #For edges, was there only one selected? Clear.
                if self.onlySelected:
                    self.clearEdgeOnly(self.onlySelected)

                itm = self.pickItemAt(mouseEvent,QSizeF(10,10),[ROLE_NODE, ROLE_BLOB]) #,ROLE_EDGE
                #print(f"{self.mouseMode =}")
                if itm:
                    self.tmpEdgeSt = itm
                    self.startRubberLine(mPos)
                else: #Miss
                    self.tmpEdgeSt = None

            #This is the end of a 2-click-insert (via pickItem) -  means END the rubberBanding, create the edge 
            elif self.mouseMode == self.INSERTEDGE2CLICK: 
                itm = self.pickItemAt(mouseEvent,QSizeF(10,10),[ROLE_NODE, ROLE_BLOB]) #,ROLE_EDGE
                if itm:
                    self.tmpEdgeEnd = itm 
                    self.endPoint = mPos
                    self.endRubberLine()
                self.resetRubberLine()
                self.mouseMode = self.POINTER
                return
    
            elif self.mouseMode == self.POINTER:
                # SCENE based selection - as much as possible is handled at the Qt Item level
                
                #Note: this design requires selecting, then moving on the next click

                #A click on a HANDLE or NODE means select and possibly move. 
                # On an EDGE means select

                #TODO: Make pickItemAt work properly here, and use the filter to contextualise selection (node, edge, handle), must also handle the addition of a click into the stream

                #HACK: Currently this returns the TOP item.  - see TODO above
                #ArrowHeads should _not_ be selectable/ movable, but they are breaking moves...
                selItem = self.itemsHere(mPos,QSize(HITSIZE,HITSIZE),[ROLE_EDGE,ROLE_HANDLE,ROLE_NODE,ROLE_BLOB, ROLE_POLYLINE])
                if selItem:
                    selItem = selItem[0]
                else:
                    selItem = None

                #selItem = self.itemAt(mPos,self.views()[0].transform())
                #if selItem:
                #    print(f"{type(selItem)=} , {selItem.data(KEY_ROLE)=} , {type(self.onlySelected)=}")
                #else:
                #    print("select empty")

                #If a click on a new item, clear old selection, set as this
                ## THis breaks clicking a handle whilst a edge is selected :/
                #if len(self.selectedItems()) == 1:
                #    if self.selectedItems()[0] != selItem:
                #        self.clearSelection()
                #        #Don't add anything here - that depends on the rest of the context

                if not selItem: #Nothing selected, clear
                    self.clearSelection()
                    #For edges, was there only one selected? Clear.
                    if self.onlySelected:
                        self.clearEdgeOnly(self.onlySelected)
                        #self.onlySelected = None               

                #Minor hack - leaves handles until end of drag
                if selItem and selItem.data(KEY_ROLE) == ROLE_NODE:
                    if self.onlySelected: #Clear handles
                        self.clearEdgeOnly(self.onlySelected)
                    #immediately hand off for Qt to move
                    #BUG:Dragging With these on, DRAGGING doesn't happen, off, a single node select doesn't clear selection
                    #Solution: Move `isSelected` to mouseRelease, to allow for movement
                    #TODO: DRAGGING
                    #super().mousePressEvent(mouseEvent)
                    #return

                if selItem and selItem.data(KEY_ROLE) == ROLE_BLOB:
                    print(f"Sel Blob {selItem.metadata['name']}")
                    if self.onlySelected: #Clear handles
                        self.clearEdgeOnly(self.onlySelected)
                    self.onlySelected = selItem
                    selItem.isOnlySelected = True
                    selItem.setSelected(True)


                #deal with selecting end-point handles  (leave ordinary handles & tangents to Qt?)
                #Move end point handles
                clickedHandle:bool = selItem and selItem.data(KEY_ROLE) == ROLE_HANDLE 

                #If selecting a POLYLINE, bump select to parent
                if selItem and selItem.data(KEY_ROLE) == ROLE_POLYLINE :
                    #print("stepping up from HS to visEdge")
                    parent = selItem.parentItem()
                    selItem.setSelected(False)
                    selItem = parent
                    selItem.setSelected(True)
                    
                #clear handle unless edge or handle, which we deal with here 
                #different edge selected
                clickedDifferentEdge:bool = selItem and selItem.data(KEY_ROLE) == ROLE_EDGE  and \
                        (self.onlySelected and selItem != self.onlySelected ) #empty start
                #if not clickedHandle and clickedDifferentEdge:
                if clickedDifferentEdge:
                    self.clearSelection()
                    #print("different edge")
                    #For edges, was there only one selected? Clear, and point to new selection
                    #TODO: This feels like it duplicates the next section, but ...
                    if self.onlySelected:
                        self.clearEdgeOnly(self.onlySelected)
                        self.onlySelected = selItem
                        selItem.edgeLine.setSelected(True)

                #Why set this to selected? Rather handle in NODE and EDGE if's?
                if selItem is not None:
                    selItem.setSelected(True)

                selected_items = self.selectedItems()
                #len is 0 or 1
                #exactly 1 edge selected
                #print(f"{len(selected_items)=}")
                #Add the handles
                #Remember that VisEdge has it's own mouse handler for listWidget - check overlap/ ...
                if len(selected_items) == 1 and (selItem.data(KEY_ROLE) == ROLE_EDGE ):
                    #Clear whatever was previously selected
                    self.clearSelection()
                    self.clearEdgeOnly(selItem)
                    #HACK: - this switch from selItem to item is not consistent.
                    selItem.setSelected(True)
                    item = selected_items[0]
                    item.isOnlySelected = True
                    #Let the scene remember, for unsetting
                    self.onlySelected = item

                    #HACK: force selection to create handles (selection order processing is mangled)
                    item.edgeLine.setSelected(True)

                    if not item.stH:
                        item.setZValue(2000) #move the edge above nodes
                        # item.stHandle must be the 1st point handle: item.edgeLine._pHandles[0]
                        #print("Setting stH", end="")
                        if len(item.edgeLine._pHandles)>0:
                            item.stH = item.edgeLine._pHandles[0]
                        else:
                            print("No handles yet")
                    if not item.endH:
                        #print(", endH")
                        item.endH = item.edgeLine._pHandles[-1]

                if selItem and selItem.data(KEY_ROLE) == ROLE_HANDLE:
                    #print(f"Handle: {type(selItem)=}")
                    #if the parent is HS and selItem = _pH[0] or -1, then start moving end of edge
                    p = selItem.parentItem()
                    if p.data(KEY_ROLE) == ROLE_POLYLINE and (selItem == p._pHandles[0] or selItem == p._pHandles[-1]):
                        #mouseEvent.accept()
                        self.mouseMode = self.MOVEEDGEEND
                        #print(f"start MOVEEDGEEND{self.mouseMode=} {selItem.parentItem()=}")
                        #Start move
                        #selItem  _Must_ be a handle, and parent must be a visEdge - deal with the polyline inbetween
                        self.startMovingEdgeEnd(selItem.parentItem().parentItem(), selItem)
                    else: #tangent or Mid point, or Blob corner to move
                        self.handle = selItem
                        #self.handle.setBrush(QBrush(Qt.black))
                        self.mouseMode = self.MOVEHANDLE
                        #BUG - DRagging - this stops dragging from an edge, but not having it breaks tangent update values
                        mouseEvent.accept()
                        return

                #if we get here, and selected_items >2, we're about to drag
                if len(selected_items) > 2:
                    #print("setting mode to DRAGGING")
                    self.mouseMode = self.DRAGGING"""

        if (mouseEvent.button() == Qt.MouseButton.RightButton):
            mPos = mouseEvent.scenePos()
            #selItem = self.itemAt(mPos,self.views()[0].transform())
            selItem = self.selectedItems()
            #TODO if selItem == None: selItem = itemAt
            # createContextMenu(mouseEvent, listOfTuples option:action)->action??
            cxMenu = None
            if len(selItem) == 1:
                item = selItem[0]
                
                if item.data(KEY_ROLE) == ROLE_EDGE:
                    #Where to do the handles update for these?
                    cxMenu = [  ("add Point","addPt" ),
                                ("del Point","delPt" ),
                                ("Edit Details", lambda: self.mainwindow.showEditEdgeDialog(item))
                            ]
                if item.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                    cxMenu = [  (("Edit Details", 
                                lambda: self.mainwindow.showEditNodeDialog(item)))
                            ]
            else: #no or >1 selected.
                cxMenu =[("print",lambda: MainWindow.action_DebugPrint(MainWin))]

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
        if self.mouseMode == self.INSERTNODE:
            #print("Node release at :",mouseEvent.scenePos())
            #print("up node")
            #TODO: Clear selection after adding a node (or before?)
            self.clearSelection()
            self.mouseMode = self.POINTER
            return # Or use the eventHandled method?
        elif self.mouseMode == self.INSERTBLOB:
            #add the  Blob
            #TODO: Check for parents/ children - here, or itemChanged?
            blob = VisBlobItem(self.startPoint,self.model, self.listWidget, 
                            height = mPos.y()-self.startPoint.y(), width = mPos.x()-self.startPoint.x(),
                            xRadius=10,yRadius=10)
            self.addItem(blob)
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
                pass
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
            #print(f"up: DRAGGING --> POINTER")
            self.mouseMode = self.POINTER

        super().mouseReleaseEvent(mouseEvent)  

    def mouseDoubleClickEvent(self, mouseEvent: QGraphicsSceneMouseEvent) -> None:
        if mouseEvent.button() == Qt.LeftButton:
            pos: QPointF = mouseEvent.scenePos()
            self.mouseMode = self.DOUBLECLICK
            #print(f"Double-click at {pos}")
            item = self.pickItemAt(mouseEvent,QSize(HITSIZE,HITSIZE),[ROLE_EDGE,ROLE_NODE,ROLE_BLOB])
            if item and item.data(KEY_ROLE) == ROLE_EDGE:
                self.clearEdgeOnly(item)
                #Pass the edit signal to Mainwindow.
                #print(f"{item.requestEdit.connect=}, {self.mainwindow.showEditEdgeDialog=}")
                #item.requestEdit.connect(self.mainwindow.showEditEdgeDialog)   #edgeEditRequested.emit)
                #item.requestEdit.connect(self.edgeEditRequested.emit)
                #Even this simple test doesn't work
                #item.requestEdit.connect(self.signalTest)
                #HACK: Call the dialog directly. Signals would be better
                self.mainwindow.showEditEdgeDialog(item)

            print(f"{item=}")
            if item and item.data(KEY_ROLE) in [ROLE_NODE, ROLE_BLOB]:
                self.mainwindow.showEditNodeDialog(item)
            
            self.mouseMode = self.POINTER

            mouseEvent.accept()
            #super().mouseDoubleClickEvent(mouseEvent)

    def signalTest(self):
        print("signal sent to scene successfully")

    def WheelEvent(self, event):
        #print("wheelevent")
        zoomInFactor = 1.25
        zoomOutFactor = 1 / zoomInFactor
        if event.delta().y() > 0:
            self.scale(zoomInFactor, zoomInFactor)
        else:
            self.scale(zoomOutFactor, zoomOutFactor)

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
            item.startNode.startsEdges.remove(item)
            #print(f"{item.endNode = }") #eItem
            item.endNode.endsEdges.remove(item)
            #print(f"{item.endNode.endsEdges =}")
        #print(f"{item =}")  
        #logging.debug("delItem&chld scene items, BEFORE remove")
        #for i in self.items():
        #    logging.debug(f"{i =}")        
        
        # Register a finalize callback to confirm deletion
        #weakref.finalize(item, self._on_finalize, repr(item))

        item.suppressItemChange = True
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

def findItemByIdx(self,idx):
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
        self.ui.listWidget.itemClicked.connect(self.listClick)
        self.ui.listWidget.itemDoubleClicked.connect(self.listDblClicked)

        #Setup the graphicsView, linking model,scene and list. Scene needs to know the mainwindow to call dialogs, etc
        self.Scene = grScene(self.model,self.ui.listWidget,self)
        #self.Scene.selectionChanged.connect(self.actionSceneSelectChange(self.Scene)) JH Commented out
    
        self.Scene.edgeEditRequested.connect(self.showEditEdgeDialog)
        self.Scene.nodeEditRequested.connect(self.showEditNodeDialog)

        self.ui.graphicsView.setScene(self.Scene)
        self.ui.graphicsView.setRenderHint(QPainter.Antialiasing)
        self.ui.graphicsView.setDragMode(QGraphicsView.RubberBandDrag)
        self.ui.graphicsView.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        #TODO: Make this image centre until scrollwheel zooming is fixed
        self.ui.graphicsView.setResizeAnchor(QGraphicsView.AnchorUnderMouse)

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

        #Tools & other 
        self.execCodeAction = QAction("Run Python Code", self)
        self.execCodeAction.triggered.connect(self.showCodeDialog)
        self.ui.menuTools.addAction(self.execCodeAction)

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
        #store self.codeDialog as an attribute to prevent it from being garbage-collected 
        self.codeDialog  = CodeExecDialog(self, scene=self.Scene)
        self.codeDialog.show()

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
        #print(f"listClick {item} , {item.text()}")
        #clear the selection
        self.Scene.clearSelection()
        #select the *graphics* view of the clicked item as well
        idx = item.data(KEY_INDEX)
        for sItem in self.Scene.items():
            if sItem.data(KEY_ROLE) in [ROLE_NODE, ROLE_EDGE,ROLE_BLOB]:
                if sItem.data(KEY_INDEX) == idx: # iNum:
                    sItem.setSelected(True)
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

        #print("Update scene text")
        #print(f"updateSceneText id = {item.data(KEY_INDEX)} {item.text()}::{item.data(KEY_ROLE)}")

        iNum = item.data(KEY_INDEX)
        #print(f"{item.text()}::{item.data(KEY_INDEX)}>{item.data(KEY_ROLE)} {iNum =}")
        new_text = item.text()
        self.model.item(iNum).setText(new_text)
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

    def actionSceneSelectChange(self, scene):

        selected_items = scene.selectedItems()
        if selected_items:
            print("Selected items:")
            for item in selected_items:
                print("  ", item)
        #else:
        #    print("No items selected.")

    #Menu-like Actions
    def action_FileNew(self):
        #print("FileNew")
        #Tidy up where we are
        self.Scene.clearSelection()
        if self.Scene.onlySelected:
            self.Scene.onlySelected.isOnlySelected =False
        self.Scene.onlySelected = None
        self.Scene.thisHandleObjectSelected = None
        
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
                    #geometry_vars = ["height", "width", "x", "y"]

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
                                metadata=nodeMetadata, metadataAttributes=nodeMetadataAttributes)
        return newNode

    def edgeFromXML(self,xEdge,newID=False,newStartID=None, newEndID=None)->VisEdgeItem:
        """ Create a new edge from an XML string
            if newID is True, the item is created with a newID,otherwise, the read value.
            This is the difference between file load (new items) and edit paste (structure)
            newStartID & newEndID also must be overwritten on paste/ structure copy
            Returns VisEdgeItem
        """
        #Use old yEd + load code
        #print(ET.tostring(xEdge))
        

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

        sItem = self.Scene.findItemByIdx(sItemID)
        eItem = self.Scene.findItemByIdx(eItemID)
        if sItem == None:
            print(f"WARNING! - Start Item ID {sItemID} not found ")
        if eItem == None:
            print(f"WARNING! - End Item ID {eItemID} not found ")
        #Find the items

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
            sceneRect = self.Scene.sceneRect()
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
            xOffset = (pageRect.width() - sceneRect.width() * scale) / 2
            yOffset = (pageRect.height() - sceneRect.height() * scale) / 2

            painter.translate(xOffset, yOffset)
            painter.scale(scale, scale)
        
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
                if sItem.startNode in selectedItems and sItem.endNode in selectedItems:
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
        if len(selectedItems) == 1 and selectedItems[0].data(KEY_ROLE) == ROLE_EDGE:
            self.Scene.clearEdgeOnly(selectedItems[0])
        self.Scene.clearSelection()

        # Render the selected items
        painter = QPainter(image)
        painter.setRenderHint(QPainter.Antialiasing)

        # Translate so that boundingRect.topLeft() is (0,0)
        #Only use this when calling item.paint(), not with Scene.render()
        #painter.translate(-boundingRect.topLeft())

        # Draw only selected items
        #"""
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

        #Reselect
        for item in selectedItems:
            item.setSelected(True)

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

        self.Scene.clearSelection()
        if self.Scene.onlySelected:
            self.Scene.clearEdgeOnly()

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

        #Edges
        for xEdge in graphStr.iter("edge"):
            sItemID = int(xEdge.attrib.get("source", None))
            eItemID = int(xEdge.attrib.get("target", None))

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
        self.Scene.clearEdgeOnly(delItem)
        self.Scene.deleteItemAndChildren(delItem)

    def delNode(self, delIdx):
        """ all the calls to delete an node"""
        #Check for any edges attached
        #TODO: Pop a warning dialog when deleting the edges
        eList = self.model.edgesAtNode(self.Scene.findItemByIdx(delIdx))
        if eList:
            for e in eList:
                self.delEdge(e)

        #Delete from Scene first, since there are complex deps to other parts which get in a knot
        self.Scene.deleteItemAndChildren(self.Scene.findItemByIdx(delIdx))
        #delete from model
        self.model.delNode(delIdx)
        #Delete from LW
        delRow = self.ui.listWidget.findItemRowByIdx(delIdx)
        delItem = self.ui.listWidget.takeItem(delRow)
        del delItem
        #Delete from Scene
        #self.Scene.deleteItemAndChildren(self.Scene.findItemByIdx(delIdx))

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
                    self.delEdge(delIdx)
            #Node delete - 1st del any connected edges - handled by GrScene
            for item in selected_items:
                if item.data(KEY_ROLE) in [ROLE_NODE,ROLE_BLOB]:
                    delIdx = item.data(KEY_INDEX)
                    self.delNode(delIdx)

        #logging.debug("about to update from action_EditDelete",stack_info=True  )
        #gc.collect() #This will crash the whole thing, with no traces
        #debug_qgraphicsitem_refs()  #More coPilot code ...

        #self.Scene.update()
        #Trying to get rid of the orphan lines - which go when the view changes so that scrollbars are added.
        self.Scene.invalidate(self.Scene.sceneRect(), QGraphicsScene.AllLayers)
        #GC takes some time (~100ms?) to finalise, so delay the repaint
        QTimer.singleShot(500, lambda: self.ui.graphicsView.viewport().repaint())
        #self.Scene.invalidate(self.Scene.sceneRect(), QGraphicsScene.AllLayers)
        self.ui.graphicsView.viewport().repaint()  #update()
        #self.Scene.invalidate()

    def action_EditSelectAll(self):
        #print("Edit>SelectAll")
        #TODO: For multiple scenes from 1 model, what to do? (select model, or scene?)
        #  Maybe select all needs to be context sensitive - scene, or list =model
        for item in self.Scene.items():
            if item.GraphicsItemFlag.ItemIsSelectable:
                item.setSelected(True)

    def action_EditSelectNone(self):
        #print("Edit>SelectNone")
        if self.Scene.onlySelected: 
            self.Scene.clearEdgeOnly(self.Scene.onlySelected)
        self.Scene.clearSelection()

    def action_EditZoomIn(self):
        #print("Edit>ZoomIn")
        pass

    def action_EditZoomOut(self):
        #print("Edit>ZoomOut")
        pass

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
    MainWin.resize(600, 400)
    MainWin.show()
    #cProfile.run('sys.exit(app.exec())')
    sys.exit(app.exec())