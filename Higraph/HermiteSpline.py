"""
Seeded from chatGPT (4o) Hermite spline code, 
extended to handle relative tangents, selecting, mulitple points, with dynamic handle creation

"""
from typing import List, Dict

from PySide6.QtWidgets import (QMainWindow, QGraphicsScene, QGraphicsView, QApplication, 
                               QGraphicsObject, QGraphicsEllipseItem, QGraphicsItem, QGraphicsTextItem )
from PySide6.QtGui import QPainter, QPainterPath, QPen, QBrush, QColor, QPainterPathStroker
from PySide6.QtCore import QRectF, QPointF, Qt

import sys
import math

#selection accuracy - how close to get a hit?
HITSIZE = 5

class HandleItem(QGraphicsEllipseItem):
    """ a generic graphics handle to facilitate moving points during editing"""
    lastChanged = None  #Track the handle which was last changed

    def __init__(self, center: QPointF, radius=5, color=Qt.red, parent=None):
        super().__init__(-radius, -radius, 2 * radius, 2 * radius, parent)

        #stop constructor changes messing with .itemChange()
        self.suppressItemChange = True 

        self.setBrush(QBrush(color))
        self.setPen(QPen(Qt.black))
        self.setFlag(QGraphicsEllipseItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,True)
        self.setZValue(10)
        self.setPos(center)
        self._onMoveCallback = None
        
        self.suppressItemChange = False

    def setMoveCallback(self, callback):
        self._onMoveCallback = callback

    def clearMoveCallback(self):
        self._onMoveCallback = None

    def itemChange(self, change, value):
        #TODO: Include if change == QGraphicsItem.ItemPositionChange.

        if not self.suppressItemChange and self._onMoveCallback:
            HandleItem.lastChanged = self   #Track which was the last handle touched
            self._onMoveCallback(self.scenePos())

        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):

        painter.save()
        painter.setBrush(self.brush())
        painter.setPen(self.pen())
        painter.drawEllipse(self.rect())
        painter.restore()
        

class HermiteSplineItem(QGraphicsObject):

    def __init__(self, p:List, t:List=[], parent=None):
        """ create a hermite (cubic) spline with a list of points (QPointFs) and an optional, matching list of 2-tuples of tangents (QPointFs). 
            Tangent coordinates are relative to their parent point. 
            First tangent tuple is (0,QPointF), and last is (QPointF,0)
        """
        super().__init__(parent)
        self.suppressItemChange = True
        self._p = p
        
        #How many lines per segment
        self.linesPerSegment = 40

        #Tangents
        self.scaleFactor = 20 #how long the default tangents are
        #Are tangents given:
        if len(t) == len(p):
            self._t = t
        elif len(t) == 0:
            #Compute default tangents for each point.
            self._t = [0 for _ in range(len(self._p))]
            

            #Start and end: Just aim for the next point (also deals with 2 pt case)
            hyp = math.sqrt((self._p[0].x() - self._p[1].x())**2 +(self._p[0].y() - self._p[1].y())**2 )
            dx = (self._p[1].x() - self._p[0].x())/hyp * self.scaleFactor
            dy = (self._p[1].y() - self._p[0].y())/hyp * self.scaleFactor
            self._t[0] = (0,QPointF(dx,dy))

            #End
            hyp = math.sqrt((self._p[-1].x() - self._p[-2].x())**2 +(self._p[-1].y() - self._p[-2].y())**2 )
            dx = (self._p[-1].x() -self._p[-2].x())/hyp * self.scaleFactor
            dy = (self._p[-1].y() -self._p[-2].y())/hyp * self.scaleFactor
            self._t[-1] = (QPointF(dx,dy),0)

            #MultiPoint
            for i in range(1,len(self._p)-1):
                hyp = math.sqrt((self._p[i-1].x() - self._p[i+1].x())**2 +(self._p[i-1].y() - self._p[i+1].y())**2 )
                dx = (self._p[i+1].x() - self._p[i-1].x())/hyp * self.scaleFactor
                dy = (self._p[i+1].y() - self._p[i-1].y())/hyp * self.scaleFactor
                self._t[i] = (QPointF(dx,dy),QPointF(dx,dy))                

        else:
            print("Must have tangents set!!!")
            pass

        self.pen = QPen(Qt.darkBlue, 1) 
        self._boundingRect = QRectF()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        #For graph drawing, splines will only ever move via nodes moving, so this is not needed
        #In the general case of free-standing splines, this would need more careful handling.
        #self.setFlag(QGraphicsItem.ItemIsMovable, True)

        #draw, since itemChange is not called without handles
        self._path = self._createHermitePath()
        self._boundingRect = self._path.boundingRect().adjusted(-20, -20, 20, 20)
        self.update()

        self.suppressItemChange = False

        #Create the editing handles
        #self._createHandles()
        #self._deleteHandles()

    def __repr__(self):
        #tuple formatted, can be fed into constructor
        return str(f"({self._p},\n{self._t})")

    def addPoint(self,newP:QPointF):
        """ Add a control point into the spline at newP"""
        #Find which points it's between
        
        minD = math.inf #infinite distance
        ic, xc, yc = 0,0,0
        for i in range(self._path.elementCount()):
            xo, yo = self._path.elementAt(i).x, self._path.elementAt(i).y
            newD = math.sqrt((newP.x() - xo)**2+ (newP.y() - yo)**2)
            if newD < minD:
                ic, xc, yc = i,xo,yo
                minD = newD
        #TODO: This requires a fixed num of lines/ segment - make it a constant
        i = ic // self.linesPerSegment

        #Calc the tangents using the previous and next segment points (not spline knots)
        xl = self._path.elementAt(ic-1).x
        yl = self._path.elementAt(ic-1).y
        xr = self._path.elementAt(ic+1).x
        yr = self._path.elementAt(ic+1).y
        hyp = math.sqrt((xr-xl)**2 + (yr-yl)**2 )
        dx = (xr-xl)/hyp * self.scaleFactor
        dy = (yr-yl)/hyp * self.scaleFactor
        #Add to the lists
        self._p.insert(i+1,QPointF(xc,yc))
        self._t.insert(i+1,(QPointF(dx,dy), QPointF(dx,dy)))
        self.update()

    def deletePoint(self,delP:QPointF):
        """Delete the control point nearest delP"""
        minD = math.inf
        ic, xc, yc = 0,0,0
        for i in range(len(self._p)):
            xo, yo = self._p[i].x(), self._p[i].y()
            newD = math.sqrt((delP.x() - xo)**2+ (delP.y() - yo)**2)
            if newD < minD:
                ic, xc, yc = i,xo,yo
                minD = newD

        self.suppressItemChange = True
        #remove handles 
        #Not first point
        if ic != 0:
            self.scene().removeItem(self._tHandles[ic][1])
        #Not last point
        if ic != len(self._p):
            self.scene().removeItem(self._tHandles[ic][0])
        self._tHandles.pop(ic)

        #remove tangents
        self._t.pop(ic)

        #remove point
        #self._pHandles[ic].suppressItemChange = True
        self.scene().removeItem(self._pHandles[ic])
        self._pHandles.pop(ic)
        self._p.pop(ic)

        self.suppressItemChange = False
        #redraw
        self._updateFromHandles(delP)
        self.update()

    def _createHandles(self):
        """create handles on single selection, in called from itemChange()"""

        #Start and end points always present p0, pn (or p-1)
        #have a list of point and tgnt handles
        self._pHandles = []
        for pi in self._p:
            self._pHandles.append(HandleItem(pi,color=Qt.green,parent=self))

        self._tHandles = []
        #start
        self._tHandles.append((0,HandleItem(self._t[0][1],color=Qt.blue,parent=self._pHandles[0]))) # no left tgt, use 0
        #Middle
        for i in range(1,len(self._t) -1): #End points have 1 tgt, mid pts 2
            self._tHandles.append((HandleItem(-self._t[i][0],color=Qt.blue,parent=self._pHandles[i]), #left
                                   HandleItem(self._t[i][1],color=Qt.blue,parent=self._pHandles[i]))) #right
        #End
        self._tHandles.append((HandleItem(-self._t[-1][0],color=Qt.blue,parent=self._pHandles[-1]),0))  #no right tangent, use 0

        for ph in self._pHandles:
            ph.setMoveCallback(self._updateFromHandles)

        self._tHandles[0][1].setMoveCallback(self._updateFromHandles) #note Start has no left tangent
        for i in range(1,len(self._tHandles)-1):
            self._tHandles[i][0].setMoveCallback(self._updateFromHandles)
            self._tHandles[i][1].setMoveCallback(self._updateFromHandles)
        self._tHandles[-1][0].setMoveCallback(self._updateFromHandles) #note End has no right tangent

    def _deleteHandles(self):
        """ Delete handles when deselected"""

        self.suppressItemChange = True

        #del self._tHandles first, since they are parented to pointHandles
        self.scene().removeItem(self._tHandles[0][1])
        for i in range(1,len(self._tHandles)-1):
            self.scene().removeItem(self._tHandles[i][0])
            self.scene().removeItem(self._tHandles[i][1])
        self.scene().removeItem(self._tHandles[-1][0])
        self._tHandles.clear()

        #del self._pHandles
        for i in range(len(self._pHandles)):
            self._pHandles[i].suppressItemChange = True 
            self.scene().removeItem(self._pHandles[i])
        self._pHandles.clear()

        self.suppressItemChange = False
        
    def _updateFromHandles(self, moved):
        """ if a handle moves, update the coords, and recompute the spline curve """
        #to deal with deletion time inconsistencies: 
        if self.suppressItemChange == True:
            return

        self.prepareGeometryChange()
        for i in range(len(self._p)):
            self._p[i] = self._pHandles[i].pos()

        self._t[0] = (0,self._tHandles[0][1].pos())
        for i in range(1,len(self._t)-1):
            # maintain C2 symmetry. class variable in HandleItem tracks the last updated item
            # The tuple structure allows for asymmetrical tangents - not currently implemented.
            if HandleItem.lastChanged == self._tHandles[i][0]:
                #Changing the symmetric handle causes an itemChange call loop - block that. 
                # Geometry calculation is not impacted
                self._tHandles[i][1].suppressItemChange = True
                self._tHandles[i][1].setPos(-self._tHandles[i][0].pos()) #reflect
                self._tHandles[i][1].suppressItemChange = False
            elif HandleItem.lastChanged == self._tHandles[i][1]:
                self._tHandles[i][0].suppressItemChange = True
                self._tHandles[i][0].setPos(-self._tHandles[i][1].pos()) #reflect
                self._tHandles[i][0].suppressItemChange = False

            self._t[i] = (-self._tHandles[i][0].pos(), self._tHandles[i][1].pos())
        self._t[-1] = (-self._tHandles[-1][0].pos(),0) #left facing tgnt is -ve
        
        #Create the path
        self._path = self._createHermitePath()
        self._boundingRect = self._path.boundingRect().adjusted(-20, -20, 20, 20)
        self.update()

    def boundingRect(self) -> QRectF:
        adjust = 2
        return self._boundingRect.united (self.childrenBoundingRect().adjusted(-adjust, -adjust, adjust, adjust))

    def shape(self):
        outlinePath = QPainterPathStroker()
        outlinePath.setWidth(HITSIZE*2)
        return outlinePath.createStroke(self._path)
    
    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            # value is a bool indicating new selected state
            isSelected = bool(value)
            if isSelected:
                self._createHandles()
            else:
                self._deleteHandles()
                
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        if self.isSelected():
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine))

            # Draw tangents
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine))
            painter.drawLine(self._p[0], self._p[0] + self._t[0][1])
            for i in range(1,len(self._p)-1):
                painter.drawLine(self._p[i], self._p[i] - self._t[i][0])      #left
                painter.drawLine(self._p[i], self._p[i] + self._t[i][1])      #right
            painter.drawLine(self._p[-1], self._p[-1] - self._t[-1][0]) 
        else:
            painter.setPen(self.pen)

        painter.drawPath(self._path)

    def _createHermitePath(self) -> QPainterPath:
        """ compute the new curve """

        #First iteration of dynamic steps calculation.
        #p0p1:float = math.sqrt((self._p[0].x() - self._p[-1].x())**2 +(self._p[0].y() - self._p[-1].y())**2 )
        #steps = int(p0p1/10) #This doesn't deal with big tangents. Needs some more maths!

        path = QPainterPath(self._p[0])
        #Loop over each segment
        for seg in range(len(self._p)-1):
            p0 = self._p[seg]
            p1 = self._p[seg+1]
            
            t0 = self._t[seg][1]    #right tangent
            t1 = self._t[seg+1][0]  #left
            
            for i in range(1, self.linesPerSegment + 1):
                t = i / self.linesPerSegment
                pt = self._hermiteInterp(p0,t0,p1,t1,t)
                path.lineTo(pt)

        return path

    def _hermiteInterp(self, p0,t0,p1,t1, t: float) -> QPointF:
        """ perform the t^th step of the Hermite interpolation between p0 and p1, with tangents t0 and t1"""
        h00 = 2 * t**3 - 3 * t**2 + 1
        h10 = t**3 - 2 * t**2 + t
        h01 = -2 * t**3 + 3 * t**2
        h11 = t**3 - t**2
        
        #accentuate the magnitude of the tangent
        tension = 4 

        x = ( h00 * p0.x() + h10 * t0.x() * tension
            + h01 * p1.x() + h11 * t1.x() * tension  )
        y = ( h00 * p0.y() + h10 * t0.y() * tension
            + h01 * p1.y() + h11 * t1.y() * tension  )
            
        return QPointF(x, y)

