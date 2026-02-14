"""HG version has hacks for higraph  """

import math
from typing import List

from PySide6.QtCore import QRectF, QPointF, Qt, QLineF
from PySide6.QtGui import QPen, QBrush, QPainter, QPainterPath, QPainterPathStroker
from PySide6.QtWidgets import QGraphicsObject, QGraphicsItem, QGraphicsRectItem

#HITSIZE = 5
from  HGConstants import *
from GraphicsSupport import *

def closestPointOnLine(p1:QPointF, p2:QPointF, point: QPointF):
    """ Finds the closesest point between p1&p2 to point. Returns closest_point, distance
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


class StraightLineItem(QGraphicsItem):

    def __init__(self, p: List[QPointF], parent=None):
        """Create a polyline with a list of points (QPointFs)."""
        super().__init__(parent)
        self.suppressItemChange = True
        self._p = p
        self.pen = QPen(Qt.darkBlue, 1)
        self._boundingRect = QRectF()
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self._path = self._createPolyPath()
        self._pHandles = []
        self.suppressItemChange = False

    def __repr__(self):
        #tuple formatted, can't be fed into constructor, since it's a string :(
        return str(f"({self._p})")

    def boundingRect(self):
        if not self._p:
            return QRectF()
        minx = min(pt.x() for pt in self._p)
        miny = min(pt.y() for pt in self._p)
        maxx = max(pt.x() for pt in self._p)
        maxy = max(pt.y() for pt in self._p)
        return QRectF(minx, miny, maxx - minx, maxy - miny).adjusted(-HITSIZE, -HITSIZE, HITSIZE, HITSIZE)

    def shape(self):
        outlinePath = QPainterPathStroker()
        outlinePath.setWidth(HITSIZE*2)
        return outlinePath.createStroke(self._path)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemSelectedHasChanged:
            # value is a bool indicating new selected state
            #isSelected = bool(value)
            isSelected = self.parentItem() and self.parentItem().isSelected()
            if isSelected:
                self._createHandles()
            else:
                self._deleteHandles()
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        #print(f"SL Paint {self._p }")
        painter.save()
        #TODO: This code doesn't work with TestPolyLine, and it should (when there are no parents in place)
        isSel:bool = self.isSelected()
        if self.parentItem():
            isSel = isSel or self.parentItem().isSelected()

        if isSel:  #self.isSelected():
        #if self.isSelected():
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine))
        else:
            painter.setPen(QPen(Qt.black))  #self.pen)

        painter.drawPath(self._path)
        painter.restore()

    def textPos(self, t:float = 0.5)->QPointF:
        """ returns the QPointF coord of t in [0,1] along the line 
                (t in the sense of parametric curves """
        return self._path.pointAtPercent(t)

    def isSelected(self)->bool:
        """ show self as selected if the parent is selected"""
        return self.parentItem() and self.parentItem().isSelected()
    
    """def setSelected(self,state:bool):
        # set as selected if parent is selected
        #print(f"SL setSelected {state=}")
        #TODO: Check how this messes with built-in selection handling.
        isSelected = self.parentItem() and self.parentItem().isSelected()
        #print(f"HS setSelected {isSelected =}, and {self.parentItem().isOnlySelected=}")
        #if isSelected:
        #if self.parentItem().isOnlySelected:
        if isSelected and self.parentItem().isOnlySelected:
            self._createHandles()
        else:
            #print("calling _deleteHandles")
            self._deleteHandles()
        #super().setSelected(isSelected)"""

    def endAngle(self):
        """ Use the path details to work out the end angle. """
        dx = self._p[-1].x() - self._p[-2].x()
        dy = self._p[-1].y() - self._p[-2].y()

        angleDeg = math.degrees(math.atan2(dy, dx))
        return angleDeg        

    def addPoint(self, point: QPointF):
        """ Add a point to the line, if close enough"""
        #TODO: This is disabled to allow self-edges. is this a problem?
        #Close enough?
        #if not self.contains(point): 
        #    return

        #Put point in at the right place
        minD = math.inf
        for i in range(self._path.elementCount()-1):
            #xo, yo = self._path.elementAt(i).x, self._path.elementAt(i).y
            newP,newD = closestPointOnLine(QPointF(self._path.elementAt(i)),
                                            QPointF(self._path.elementAt(i+1)),point)
            if newD < minD:
                closestP,minD,idx = newP,newD,i

        self._deleteHandles()
        self._p.insert(idx+1,point)
        self.prepareGeometryChange()
        self._createHandles()
        self.updatePath()

    def deletePoint(self, point: QPointF):
        # Remove nearest point within HITSIZE
        min_dist = math.inf
        min_idx = -1
        for i, pt in enumerate(self._p):
            dist = math.hypot(point.x() - pt.x(), point.y() - pt.y())
            if dist < min_dist:
                min_dist = dist
                min_idx = i
        if min_dist <= HITSIZE and len(self._p) > 2:
            self._deleteHandles()
            self._p.pop(min_idx)

            self.prepareGeometryChange()
            self._createHandles()
            self._updateFromHandles(point)
            self.update()

    def setP(self,n:int, p:QPointF):
        """sets the nth point to the value p. n is a list index """
        self._p[n] = p

    def updatePath(self):
        self._path = self._createPolyPath()
        self._boundingRect = self._path.boundingRect().adjusted(-HITSIZE, -HITSIZE, HITSIZE, HITSIZE)
        self.update()

    def moveMidPoints(self,delta):
        """Feels like a hack, but move the mid points when BOTH ends are moved (eg in a multiselect) """
        #if self.suppressItemChange == True:
        #    return

        self.prepareGeometryChange()
        #End points are moved with the nodes - just deal with middle
        for i in range(1,len(self._p)-1):
            self._p[i] += delta

    def _createHandles(self):
        """ show control handles. Used on selection and add/ delete """
        #clear existing handles
        #for h in self._pHandles:
        #    self.scene().removeItem(h)
        self._pHandles.clear()
        self.parentItem().setZValue(3000)
        # Add new handles
        #TODO: is idx used?

        for idx, pt in enumerate(self._p):
            handle = HandleItem(pt, color=Qt.green,parent=self)
            handle.setMoveCallback(self._updateFromHandles)
            self._pHandles.append(handle)

    def _deleteHandles(self):
        """ Delete handles when deselected"""
        self.suppressItemChange = True
        # Remove existing handles
        for h in self._pHandles:
            self.scene().removeItem(h)
            del h
        self._pHandles.clear()
        self.parentItem().setZValue(0)
        self.suppressItemChange = False

    def _updateFromHandles(self, moved):
        """ if a handle moves, update the coords, and recompute the spline curve """
        #to deal with deletion time inconsistencies: 
        if self.suppressItemChange == True:
            return

        self.prepareGeometryChange()
        for i in range(len(self._p)):
            self._p[i] = self._pHandles[i].pos()
        self.updatePath()
        if self.parentItem:
            self.parentItem().updateLine()

    def _createPolyPath(self):
        """ build the poly-line """
        path = QPainterPath(self._p[0])
        for i in range(1,len(self._p)):
            path.lineTo(self._p[i])
        return path
 
class HermiteSplineItem(QGraphicsItem):

    def __init__(self, p:List, t:List=[], parent=None):
        """ create a hermite (cubic) spline with a list of points (QPointFs) and an optional, matching list of 2-tuples of tangents (QPointFs). 
            Tangent coordinates are relative to their parent point. 
            First tangent tuple is (0,QPointF), and last is (QPointF,0)
        """
        super().__init__(parent)
        self.suppressItemChange = True
        self._p = p
        
        #How many lines per segment
        #TODO: Put this in HGConstants
        self.linesPerSegment = 40

        #Tangents
        self.scaleFactor = 40 #20 #how long the default tangents are
        #Are tangents given:
        if len(t) == len(p):
            self._t = t
        elif len(t) == 0:
            #Compute default tangents for each point.
            self._t = [0 for _ in range(len(self._p))]
            
            #Start [0] (and end): Just aim for the next point (also deals with 2 pt case)
            hyp = math.sqrt((self._p[0].x() - self._p[1].x())**2 +(self._p[0].y() - self._p[1].y())**2 )
            dx = (self._p[1].x() - self._p[0].x())/hyp * self.scaleFactor
            dy = (self._p[1].y() - self._p[0].y())/hyp * self.scaleFactor
            self._t[0] = (QPointF(0,0),QPointF(dx,dy))

            #End [-1]
            hyp = math.sqrt((self._p[-1].x() - self._p[-2].x())**2 +(self._p[-1].y() - self._p[-2].y())**2 )
            dx = (self._p[-1].x() -self._p[-2].x())/hyp * self.scaleFactor
            dy = (self._p[-1].y() -self._p[-2].y())/hyp * self.scaleFactor
            self._t[-1] = (QPointF(dx,dy),QPointF(0,0))

            #MultiPoint
            for i in range(1,len(self._p)-1):
                hyp = math.sqrt((self._p[i-1].x() - self._p[i+1].x())**2 +(self._p[i-1].y() - self._p[i+1].y())**2 )
                dx = (self._p[i+1].x() - self._p[i-1].x())/hyp * self.scaleFactor
                dy = (self._p[i+1].y() - self._p[i-1].y())/hyp * self.scaleFactor
                self._t[i] = (QPointF(dx,dy),QPointF(dx,dy))                

        else:
            print(f"Must have tangents set!!!\n{p=}\n{t=}")
            pass

        #To keep selection code sane, have empty lists
        self._pHandles = []
        self._tHandles = []

        self.pen = QPen(Qt.black, 1)# QPen(Qt.darkBlue, 1) 
        self._boundingRect = QRectF()
        #self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        #For graph drawing, splines will only ever move via nodes moving, so this is not needed
        #In the general case of free-standing splines, this would need more careful handling.
        #self.setFlag(QGraphicsItem.ItemIsMovable, True)

        #Tell parent that things have changed, to update arrows??
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges,True)
        self.setFlag(self.GraphicsItemFlag.ItemSendsScenePositionChanges,True)

        #draw, since itemChange is not called without handles
        self._path = self._createHermitePath()
        self._boundingRect = self._path.boundingRect().adjusted(-20, -20, 20, 20)
        self.update()

        self.suppressItemChange = False

    def __repr__(self):
        #tuple formatted, can be fed into constructor
        return str(f"({self._p},\n{self._t})")
        #return str(f"(p_ids:{[hex(id(pp)) for pp in self._p]},\n{self._t})")
        #return super().__repr__()

    def boundingRect(self) -> QRectF:
        adjust = 2
        return self._boundingRect.united (self.childrenBoundingRect().adjusted(-adjust, -adjust, adjust, adjust))

    def shape(self):
        outlinePath = QPainterPathStroker()
        outlinePath.setWidth(HITSIZE*2)
        return outlinePath.createStroke(self._path)
    
    def itemChange(self, change, value):
        #print(f"HS itemChanged {change=} {value=}")
        #JH Hopefully this is never suddenly called (it would be unexpected)
        if change == QGraphicsItem.ItemSelectedHasChanged:
            # value is a bool indicating new selected state
            #isSelected = bool(value)
            isSelected = self.parentItem() and self.parentItem().isSelected()
            #print(f"HS itemC {isSelected =}")
            if isSelected:
                self._createHandles()
            else:
                self._deleteHandles()
                
        return super().itemChange(change, value)

    def paint(self, painter: QPainter, option, widget=None):
        #print(f"HS Paint {self._p }")

        isSel:bool = self.isSelected()
        if self.parentItem():
            isSel = isSel or self.parentItem().isSelected()

        if isSel: #self.isSelected():
            painter.setPen(QPen(Qt.blue,1,Qt.DashLine))

            # Draw tangents, if this is the ONLY selected edge
            if self.parentItem().isOnlySelected:
                painter.setPen(QPen(Qt.blue,1,Qt.DashLine))
                painter.drawLine(self._p[0], self._p[0] + self._t[0][1])
                for i in range(1,len(self._p)-1):
                    painter.drawLine(self._p[i], self._p[i] - self._t[i][0])      #left
                    painter.drawLine(self._p[i], self._p[i] + self._t[i][1])      #right
                painter.drawLine(self._p[-1], self._p[-1] - self._t[-1][0]) 
        else:
            painter.setPen(self.pen)
            #painter.setPen(QPen(Qt.black,1))

        painter.drawPath(self._path)

    def textPos(self,t:float = 0.5)->QPointF:
        """ returns the QPointF coord of t in [0,1] along the line 
                (t in the sense of parametric curves """
        return self._path.pointAtPercent(t)

    def isSelected(self)->bool:
        """ show self as selected if the parent is selected"""
        return self.parentItem() and self.parentItem().isSelected()
    
    """def setSelected(self,state:bool):
        # set as selected if parent is selected
        #print(f"HS setSelected {state=}")
        #TODO: Check how this messes with built-in selection handling.
        isSelected = self.parentItem() and self.parentItem().isSelected()
        #print(f"HS setSelected {isSelected =}, and {self.parentItem().isOnlySelected=}")
        #if isSelected:
        #if self.parentItem().isOnlySelected:
        if isSelected and self.parentItem().isOnlySelected:
            self._createHandles()
        else:
            #print("calling _deleteHandles")
            self._deleteHandles()
        #super().setSelected(isSelected)"""

    def endAngle(self):
        """ Use the path details to work out the end angle. For HS, use the tangent """

        dx = self._t[-1][0].x()
        dy = self._t[-1][0].y()

        angleDeg = math.degrees(math.atan2(dy, dx))
        return angleDeg

    def addPoint(self,newP:QPointF):
        """ Add a control point into the spline at newP"""
        
        #Find which points it's between. 
        # Just uses the start point of each element, since they're short
        minD = math.inf 
        ic, xc, yc = 0,0,0
        for i in range(self._path.elementCount()):
            xo, yo = self._path.elementAt(i).x, self._path.elementAt(i).y
            newD = math.sqrt((newP.x() - xo)**2+ (newP.y() - yo)**2)
            if newD < minD:
                ic, xc, yc = i,xo,yo
                minD = newD
        #Is the click close enough to allow creating a point?
        if minD > HITSIZE:
            return

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
        self._deleteHandles()
        self._createHandles()
        self.update()

    def deletePoint(self,delP:QPointF):
        """Delete the control point nearest delP"""
        if len(self._p)>2:  # can't delete start or end points
            minD = math.inf
            ic, xc, yc = 0,0,0  #c for closest
            for i in range(len(self._p)):
                xo, yo = self._p[i].x(), self._p[i].y()
                newD = math.sqrt((delP.x() - xo)**2+ (delP.y() - yo)**2)
                if newD < minD:
                    ic, xc, yc = i,xo,yo
                    minD = newD

            self.suppressItemChange = True
        #TODO: CHeck for <hitsize?
            if minD <= HITSIZE and ic !=0 and ic!=len(self._p)-1:
                self._deleteHandles()
                #remove tangents
                self._t.pop(ic)
                #remove point
                self._p.pop(ic)
                self.suppressItemChange = False
                self._createHandles()
                self.update()
            """if minD <= HITSIZE and len(self._p) > 2:
                #remove handles 
                #Not first point
                if ic != 0:
                    self.scene().removeItem(self._tHandles[ic][1])
                #Not last point
                if ic != len(self._p):
                    self.scene().removeItem(self._tHandles[ic][0])
                #TODO: What if ic _is_ 0 or last? Will this not corrupt things?
                self._tHandles.pop(ic)

                

                #remove point
                #self._pHandles[ic].suppressItemChange = True
                self.scene().removeItem(self._pHandles[ic])
                self._pHandles.pop(ic)
                self._p.pop(ic)"""

                
            #redraw
            #self._updateFromHandles(delP)
        else:
            return
                

    def setP(self, n:int, p:QPointF):
        """sets the nth point to the value p. n is a list index """
        self._p[n] = p
        #print(f"setP {self._p[n]} {hex(id(self._p[n]))} set to {p}, {hex(id(p))} ")

    def updatePath(self):
        """ Allow the calling of the recalculation independently of handle updates"""
        self._path = self._createHermitePath()
        self._boundingRect = self._path.boundingRect().adjusted(-20, -20, 20, 20)
        self.update()    

    def moveMidPoints(self,delta):
        """Feels like a hack, but move the mid points when BOTH ends are moved (eg in a multiselect) """
        self.prepareGeometryChange()
        #End points are moved with the nodes - just deal with middle
        for i in range(1,len(self._p)-1):
            self._p[i] += delta

    def _createHandles(self):
        """create handles on single selection, in called from itemChange()"""

        #Start and end points always present p0, pn (or p-1)
        #have a list of point and tgnt handles
        # print("createHandles")
        self.parentItem().setZValue(3000)
        self._pHandles = []
        for pi in self._p: 
            self._pHandles.append(HandleItem(pi,color=Qt.green,parent=self))

        #Tangent handles
        self._tHandles = []
        #start
        # no left tgt, use 0
        self._tHandles.append((QPointF(0,0),
                                HandleItem(self._t[0][1],color=Qt.blue,parent=self._pHandles[0]))) 
        #Middle
        for i in range(1,len(self._t) -1): #End points have 1 tgt, mid pts 2
            self._tHandles.append((HandleItem(-self._t[i][0],color=Qt.blue,parent=self._pHandles[i]), #left
                                   HandleItem(self._t[i][1],color=Qt.blue,parent=self._pHandles[i]))) #right
        #End
        #no right tangent, use 0, must be a QPointF
        self._tHandles.append((HandleItem(-self._t[-1][0],color=Qt.blue,parent=self._pHandles[-1]),
                                QPointF(0,0))) 

        for ph in self._pHandles:
            ph.setMoveCallback(self._updateFromHandles)

        self._tHandles[0][1].setMoveCallback(self._updateFromHandles) #note Start has no left tangent
        for i in range(1,len(self._tHandles)-1):
            self._tHandles[i][0].setMoveCallback(self._updateFromHandles)
            self._tHandles[i][1].setMoveCallback(self._updateFromHandles)
        self._tHandles[-1][0].setMoveCallback(self._updateFromHandles) #note End has no right tangent

    def _deleteHandles(self):
        """ Delete handles when deselected"""
        #mouse event processing manipulates the selection a lot - this needs to be robust.
        #This assume splines only ever have handles as children.
        #TODO: Check that childItems are isInstance(HandleItem)
        if len(self._pHandles) == 0 and len(self.childItems()) == 0:
            #print("call to delete handles WHEN NONE ")
            return
        #print("Deleting handles")

        self.suppressItemChange = True

        for handle in self._tHandles:
            del handle
        self._tHandles.clear()

        #del self._pHandles
        for handle in self._pHandles:  
            self.scene().removeItem(handle)
            del handle
        #for i in range(len(self._pHandles)):
        #    self.scene().removeItem(self._pHandles[i])
        self._pHandles.clear()
        self.parentItem().setZValue(0)
        
        self.suppressItemChange = False
        
    def _updateFromHandles(self, moved=0):
        """ if a handle moves, update the coords, and recompute the spline curve """
        #TODO: Remove `moved` as param - not used
        #to deal with deletion time inconsistencies: 
        if self.suppressItemChange == True:
            return

        self.prepareGeometryChange()
        for i in range(len(self._p)):
            self._p[i] = self._pHandles[i].pos()

        #Subtract the parent point pos()
        if HandleItem.lastChanged == self._tHandles[0][1]:
            pt = self._pHandles[0].pos()
            self._tHandles[0][1].suppressItemChange = True
            self._tHandles[0][1].setPos(self._tHandles[0][1].pos() - pt)
            self._tHandles[0][1].suppressItemChange = False
            self._t[0] = (QPointF(0,0),self._tHandles[0][1].pos())

        for i in range(1,len(self._t)-1):
            # maintain C2 symmetry. class variable in HandleItem tracks the last updated item
            # The tuple structure allows for asymmetrical tangents - not currently implemented.
            if HandleItem.lastChanged == self._tHandles[i][0]:
                #_t are parented to _p, so adjust coords by - _p
                pt = self._pHandles[i].pos()
                self._tHandles[i][0].suppressItemChange = True
                self._tHandles[i][0].setPos(self._tHandles[i][0].pos() - pt)
                self._tHandles[i][0].suppressItemChange = False

                self._tHandles[i][1].suppressItemChange = True
                #Since this is derived from the opposite point, dont adjust twice?
                self._tHandles[i][1].setPos(-self._tHandles[i][0].pos()) #reflect
                self._tHandles[i][1].suppressItemChange = False

            elif HandleItem.lastChanged == self._tHandles[i][1]:
                pt = self._pHandles[i].pos()
                self._tHandles[i][1].suppressItemChange = True
                self._tHandles[i][1].setPos(self._tHandles[i][1].pos() - pt)
                self._tHandles[i][1].suppressItemChange = False

                self._tHandles[i][0].suppressItemChange = True
                self._tHandles[i][0].setPos(-self._tHandles[i][1].pos()) #reflect
                self._tHandles[i][0].suppressItemChange = False

            self._t[i] = (-self._tHandles[i][0].pos(), self._tHandles[i][1].pos())
        if HandleItem.lastChanged == self._tHandles[-1][0]:
            pt = self._pHandles[-1].pos()
            self._tHandles[-1][0].suppressItemChange = True
            self._tHandles[-1][0].setPos(self._tHandles[-1][0].pos() - pt)
            self._tHandles[-1][0].suppressItemChange = False
            self._t[-1] = (-self._tHandles[-1][0].pos(),QPointF(0,0)) #left facing tgnt is -ve
        
        #Create the path
        self.updatePath()
        if self.parentItem:
            self.parentItem().updateLine()

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
            
            t0 = self._t[seg][1]    #right facing tangent
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

