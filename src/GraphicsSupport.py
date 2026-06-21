
#Global constants. 
from  HGConstants import *
from coreGraph import getGUID

import math

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

#Various support functions & classes.

def p1TopLeftp2(p1:QPointF, p2:QPointF)->bool:
    """ is p1 'left' and 'above' p2 - used to not create 'inverted' rectangles """
    return p1.x() < p2.x() and p1.y() < p2.y()

def closestPointOnLine(p1:QPointF, p2:QPointF, point: QPointF):
    """ Finds the closesest point between p1&p2 to point. Returns tuple (closest_point, distance)
        Helper function for StraightLineItem.addPoint() on straight lines with long segments
    """

    # Vector line
    line_dx = p2.x() - p1.x()
    line_dy = p2.y() - p1.y()

    # Vector from p1 to point
    pt_dx = point.x() - p1.x()
    pt_dy = point.y() - p1.y()

    # Project point onto line, normalized by line length squared
    line_len_sq = line_dx * line_dx + line_dy * line_dy
    if line_len_sq == 0:  # Degenerate line (length = 0)
        return p1, math.hypot(pt_dx, pt_dy)

    t = (pt_dx * line_dx + pt_dy * line_dy) / line_len_sq

    # Clamp t to [0, 1] if you want closest point *on the segment*
    # Remove clamp if infinite line is desired
    t = max(0, min(1, t))

    # Closest point
    closest_x = p1.x() + t * line_dx
    closest_y = p1.y() + t * line_dy
    closest_point = QPointF(closest_x, closest_y)

    # Distance
    dx = point.x() - closest_x
    dy = point.y() - closest_y
    distance = math.hypot(dx, dy)

    return closest_point, distance

class TransparentTextItem(QGraphicsTextItem):
    """ allows parent.shape() to select the text, rather than the textItem always grabbing the event  """
    def __init__(self, text:str, parent=None):
        if not parent:
            print(f"Error creating TransparentTextItem - no parent set")
        super().__init__(text,parent)

    def paint(self, painter, option, widget=None):
        super().paint(painter,option,widget)

    def mousePressEvent(self, event):
        # Forward to parent
        if self.parentItem():
            self.parentItem().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        if self.parentItem():
            self.parentItem().mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if self.parentItem():
            self.parentItem().mouseDoubleClickEvent(event)
        else:
            super().mouseDoubleClickEvent(event)

class ArrowHeadItem(QGraphicsItem):
    """An arrowhead. 
        position updates are driven from the parent item
       chatGPT based code """

    def __init__(self, size=NODESIZE, parent=None):
        super().__init__(parent)
        self.size = size
        # Define arrowhead polygon pointing right (+X)
        self.polygon = QPolygonF([
            QPointF(0, 0),
            QPointF(-size, size / 2),
            QPointF(-size, -size / 2)
        ])
        #Transform by -NODESIZE/2 to not disappear under the node
        #self.polygon.translate(QPointF(-NODESIZE/2,0))
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setZValue(0)

    def boundingRect(self):
        # Rectangle covering the polygon
        return QRectF(-self.size, -self.size/2, self.size, self.size)

    def paint(self, painter, option, widget):
        #print("Arrow Paint")

        #WHy is this needed? parent sel should propagate?
        #This code runs, but has no effect? What is overriding it?
        painter.save()
        if self.parentItem():
            if self.parentItem().isSelected():
                self.setSelected(True)
                #print("Setting arrow as selected")
                painter.setBrush(QBrush(Qt.blue))
                painter.setPen(QPen(Qt.blue,1,Qt.DashLine)) 
            else:
                painter.setBrush(QBrush(Qt.black))
                painter.setPen(QPen(Qt.black))

        painter.drawPolygon(self.polygon)
        painter.restore()

class HandleItem(QGraphicsRectItem):
    """ a generic graphics handle to facilitate moving points during editing"""
    lastChanged = None  #Track the handle which was last changed
    lastChangedbyCentre = QPointF(0,0)  # JH add for debugging

    def __init__(self, center: QPointF, hSize=HITSIZE, color=Qt.red, handleShape="rectangle", parent=None):

        super().__init__(-hSize, -hSize, 2 * hSize, 2 * hSize, parent)

        #stop constructor changes messing with .itemChange()
        self.suppressItemChange = True 

        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.NoPen))
        self.handleShape = handleShape  #circle or rectangle
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        #NOT selectable, otherwise default click handling gets in the way
        self.setFlag(QGraphicsItem.ItemIsSelectable, False)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsScenePositionChanges,True)
        self.setData(KEY_ROLE, ROLE_HANDLE)
        #Guarantee its at the front
        self.setZValue(3000)
        self.setPos(center)
        self._onMoveCallback = None
        
        self.suppressItemChange = False
        self.centre=center #JH added for debugging

    def setMoveCallback(self, callback):
        self._onMoveCallback = callback

    def clearMoveCallback(self):
        self._onMoveCallback = None

    def itemChange(self, change, value):
        #print(f"Handle change {change=} {value=}")
        if ( change == QGraphicsItem.ItemPositionHasChanged
            and not self.suppressItemChange 
            and self._onMoveCallback
        ):
            #Track which was the last handle touched
            HandleItem.lastChanged = self   
            HandleItem.lastChangedbyCentre = self.centre  #JH added for debugging
            #self._onMoveCallback(self.scenePos())
            self._onMoveCallback(value)  #new absolute? position of handle JH
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):

        painter.save()
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        if self.handleShape == "circle":
            painter.drawEllipse(self.rect())
        else:
            painter.drawRect(self.rect())
        painter.restore()
        
class dummyNodeRoot(QGraphicsItem):
    """ an almost-abstract graphics-only node-like object to manage joins for hyperedges, ports for nodes """
    nextID = 1000
    IDsUsed = set()

    def __init__(self,center: QPointF,  parent=None, id=None):
        super().__init__(parent=parent)
        self.suppressItemChange = True
        #This might be resolved by the starts end finishEdges code 
        self.setPos(center)
        #self.setFlag(QGraphicsItem.ItemIsMovable, True)
 
        #Note - since this is a purely geometric construct, these are called `EdgeLines``, not `Edges`
        self.startsEdgeLines = []
        self.endsEdgeLines = []

        #ID for saving, and debugging 
        #Check for unique ID
        if id !=None:
            self.nodeNum=id
        else:
            self.nodeNum = getGUID(id)
        """
        if id and not id in dummyNodeRoot.IDsUsed:
                self.nodeNum = id
                dummyNodeRoot.IDsUsed.add(id)
        else:
            while dummyNodeRoot.nextID in dummyNodeRoot.IDsUsed:
                dummyNodeRoot.nextID += 1
            self.nodeNum = dummyNodeRoot.nextID
            dummyNodeRoot.IDsUsed.add(self.nodeNum)
            dummyNodeRoot.nextID += 1   
        """

        self.suppressItemChange = False

    def boundingRect(self):
        bRect = QRect(self.x(), self.y(), self.x()+1, self.y()+1)
        return bRect
    
    def paint(self, painter: QPainter, option, widget=None):
        """ This object is only visible via a handle, but paint is required by Qt """
        #Debugging
        #painter.drawRect(QRectF(-5,-5,10,10))
        pass

class dummyNodeItem(dummyNodeRoot):
    """ true dummyNodes need an `itemchange()` method, which breaks `port`s"""
    def __init__(self,center: QPointF,  parent=None, id=None):
        super().__init__(center, parent=parent, id=id)

        self.setData(KEY_ROLE, ROLE_DUMMYNODE)
        self.setData(KEY_INDEX, self.nodeNum)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,True)
        self.setFlag(QGraphicsItem.ItemIsSelectable,False)

    def itemChange(self, change, value):
        if self.suppressItemChange:
            return super().itemChange(change, value)
        
        if change in [QGraphicsItem.ItemPositionHasChanged, QGraphicsItem.ItemScenePositionHasChanged]:
            #print(f"itm change dN {self.nodeNum} ", end = ",  ")
            #print(f".", end = "",flush=True)
            #update attached points
            for eL in self.startsEdgeLines:
                #print(f"start {eL.lineNum=} ", end = ",  ", flush=True)
                #eL._p[0] = self.pos()
                eL.setP(0, self.scenePos(), "DummyNode")
                eL.updatePath()
            
            for eL in self.endsEdgeLines:
                #print(f"end {eL.lineNum=} ",end = ",  ", flush=True)
                #eL._p[-1] = self.pos()
                eL.setP(-1, self.scenePos(), "DummyNode")
                eL.updatePath()

        return super().itemChange(change, value)

    def _updateFromHandles(self,pos):
        
        #if self.suppressItemChange == True:
        #    return
        self.suppressItemChange = True

        self.prepareGeometryChange()
        #print(">", end = "", flush=True)
        self.setPos(pos)
        for eL in self.startsEdgeLines:
            #eL._p[0] = self.pos()
            eL.setP(0,self.pos(),"DummyNode")
            eL.updatePath()
        for eL in self.endsEdgeLines:
            #eL._p[-1] = self.pos()
            eL.setP(-1,self.pos(),"DummyNode")
            eL.updatePath()
        #Tell the edge to update
        #edge = self.startsEdgeLines[0].parentItem()
        #edge.updateLine()
        self.suppressItemChange = False

class port(dummyNodeRoot):
    """ a port for nodes to give edges a spot to connect. `t` is where on the perimeter the point is"""
    def __init__(self,center: QPointF, t:float = 0, index:int = -1, parent=None):
        super().__init__(center, parent=parent)
        self.t = t  
        self.index = index #Index must only be used for XML. (and undo?)

    def orthogonalSlope(self)->tuple:
        """ Return (dx,dy) at right angles to the `nodeshape` at `t` """
        #Check that parent has a path
        #print(f"{self.parentItem().parentItem().nodeNum=}", end = "")
        if self.parentItem().parentItem().data(KEY_ROLE) == ROLE_NODE: #Node
            dy = math.sin(2*math.pi * self.t)
            dx = math.cos(2*math.pi * self.t)
        elif self.parentItem().parentItem().data(KEY_ROLE) == ROLE_BLOB:  #Blob
            
            # getting angle from elements - Qt `angleAtPercent` is wonky at best
            polygon = self.parentItem()._basePath.toFillPolygon()
            pos = self.parentItem().parentItem().parameterToPosition(self.t)

            pCount = self.parentItem().parentItem()._polygon.count()
            #odd errors mean some t's return pos not in the segment bounding rect, so search for _closest_
            minD = math.inf
            for i in range( pCount - 1):
                p1 = polygon[i]
                p2 = polygon[i + 1]
                #print(f"seg {i} is {p1} to {p2}")
                newP,newD = closestPointOnLine(p1,p2,pos)
                if newD < minD:
                    closestP,minD,idx = newP,newD,i      

            p1 = p1 = polygon[idx]
            p2 = polygon[idx + 1]
            dx = p2.x()-p1.x()
            dy = p2.y()-p1.y()
            # normalise
            hyp = (dx**2 + dy**2)**0.5
            dx /= hyp
            dy /= hyp
            #print(f"recalc angle at t={self.t:1.5f} seg {idx}/{pCount} {dy:1.5f}/{dx:1.5f}, {math.atan2(dy,dx)*180/math.pi % 360}  ")
            #Rotate back by 90 deg
            dx, dy = dy, -dx

        return (dx,dy)
    
    #Used for debugging
    def XXitemChange(self, change, value):
        if self.suppressItemChange:
            return super().itemChange(change, value)
        
        if change in [QGraphicsItem.ItemPositionHasChanged]:
            #print(f"itm change dN {self.nodeNum} ", end = ",  ")
            print(f"*", end = "",flush=True)