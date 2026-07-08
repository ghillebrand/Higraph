""" Test program for Hermite Spline Class"""

from PySide6.QtWidgets import QMainWindow, QGraphicsScene, QGraphicsView, QApplication, QGraphicsTextItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import  QPen, QPainter, QInputEvent

import sys

from PolyLineItem import StraightLineItem, HermiteSplineItem, HandleItem

class grScene(QGraphicsScene):
    """ Simple scene to handle some basic clicks for testing"""
    def __init__(self):
        super().__init__()
    
    def mousePressEvent(self, mouseEvent):
        mPos = mouseEvent.scenePos()
        if (mouseEvent.button() == Qt.MouseButton.RightButton):
            # Nothing selected, print all the coordinates 
            if len(self.selectedItems()) == 0:
                self.printAll()

            #right click on a selected item to add
            elif len(self.selectedItems()) == 1 and not( mouseEvent.modifiers() & Qt.ShiftModifier) :
                #Note: Should the check if we are still within hit-distance of the selection
                # be here, or in .addPoint()?
                #Add a new point into the spline at mPos
                if self.selectedItems()[0].contains(mPos):
                    self.selectedItems()[0].addPoint(mPos)
                return
            #<shift> rightclick to delete
            elif len(self.selectedItems()) == 1 and ( mouseEvent.modifiers() & Qt.ShiftModifier) :
                #delete the control point at mPos
                self.selectedItems()[0].deletePoint(mPos)
                return
        
        #pass on
        super().mousePressEvent(mouseEvent)

    def printAll(self):
        print("\nScene items")
        for i,item in enumerate(self.items()):
            print(i,item)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scene = grScene()
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        #Test with same start and end point
        p = QPointF(33,33)
        t = [(0,QPointF(50, -50)),  (QPointF(50, -50),0)]
        HSp0 = HermiteSplineItem(([p,p]),t)
        #Polyline
        SL1 = StraightLineItem([QPointF(333,300), QPointF(444, 450)])
        print(SL1)
        self.scene.addItem(SL1)
        
        self.scene.printAll()

        L2 = StraightLineItem([QPointF(500,500), QPointF(600, 200),QPointF(700,500)])
        self.scene.addItem(L2)
        self.scene.printAll()

        #Don't confuse the tangents with vectors! The tangents point in the direction of `t`
        #2 point
        spline2 = HermiteSplineItem( [QPointF(150, 400), QPointF(250, 400)],        #points
                                     [(0,QPointF(50, -50)),  (QPointF(50, -50),0)]   #tangents (0's for outer, undefined tangents)
        )
        self.scene.addItem(spline2)
        self.scene.printAll()

        #2pt, no tangents given
         
        spline2nt = HermiteSplineItem( [QPointF(150, 450), QPointF(250, 500)])

        self.scene.addItem(spline2nt)
        self.scene.printAll()

        #4 point
        spline4 = HermiteSplineItem([   QPointF(100, 200),   #points
                                        QPointF(150,150), 
                                        QPointF(210,290), 
                                        QPointF(300, 200)
                                     ], 
                                    [   (0,QPointF(20, -40)),  #tangents
                                        (QPointF(10,10), QPointF(10,10)), 
                                        (QPointF(20,20), QPointF(20,20)), 
                                        (QPointF(50, 50),0)
                                    ] 
        )
        self.scene.addItem(spline4)
        spline4.pen = QPen(Qt.red, 1)
        self.scene.printAll()

        #3 point, no tangents
        spline5 = HermiteSplineItem([QPointF(300, 100),QPointF(350,50), QPointF(400,100)])
        self.scene.addItem(spline5)
        spline5.pen = QPen(Qt.darkGreen, 1)
        self.scene.printAll()

        instructions = QGraphicsTextItem("Click a curve to edit it. Select and right-click to add a point."\
                                        " <shift>right click to delete a point on a selected line.\n" \
                                        "Right click on empty space to print all the spline coordinates")
        instructions.setPos(0,0)
        self.scene.addItem(instructions)
        self.scene.printAll()

        self.scene.setSceneRect(QRectF(0, 0, 800, 600))
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        self.setWindowTitle("Hermite Spline Editor")
        self.resize(900, 700)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())