
#Global constants. 
from  HGConstants import *

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

#Various support classes.

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
        self.polygon.translate(QPointF(-NODESIZE/2,0))
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

        """if self.isSelected():
            #TODO: Arrow is never selected!
            #print("Arrow Paint SELECTED")
            painter.setBrush(QBrush(Qt.blue))
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine)) 
        else:
            painter.setBrush(QBrush(Qt.black))
            painter.setPen(QPen(Qt.black))"""
        painter.drawPolygon(self.polygon)
        painter.restore()

class HandleItem(QGraphicsRectItem):
    """ a generic graphics handle to facilitate moving points during editing"""
    lastChanged = None  #Track the handle which was last changed
    lastChangedbyCentre = QPointF(0,0)  # JH add for debugging

    def __init__(self, center: QPointF, hSize=HITSIZE, color=Qt.red, parent=None):

        super().__init__(-hSize, -hSize, 2 * hSize, 2 * hSize, parent)

        #stop constructor changes messing with .itemChange()
        self.suppressItemChange = True 

        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.NoPen))
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
        #painter.drawEllipse(self.rect())
        painter.drawRect(self.rect())
        painter.restore()
        


class dummyNodeItem(QGraphicsItem):
    """ a graphics-only node-like object to manage joins for hyperedges, ports for nodes """
    def __init__(self,center: QPointF,  parent=None):
        super().__init__(parent=parent)
        #This might be resolved by the starts end finishEdges code 
        #self.setData(KEY_ROLE, ROLE_DUMMYNODE)
        self.setPos(center)
        #Note - since this is a purely geometric construct, these are called `EdgeLines``, not `Edges`
        #Not used for ports
        self.startsEdgeLines = []
        self.endsEdgeLines = []

    def boundingRect(self):
        return QRect(self.x(), self.y(), self.x()+1, self.y()+1)
    
    def paint(self, painter: QPainter, option, widget=None):
        """ This object is only visable via a handle, but paint is required by Qt """
        pass