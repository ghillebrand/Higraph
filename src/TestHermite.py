""" Test program for Hermite Spline Class"""


from PySide6.QtWidgets import QMainWindow, QGraphicsScene, QGraphicsView, QApplication, QGraphicsTextItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import  QPen, QPainter, QInputEvent

import sys

from  HermiteSpline import HermiteSplineItem, HandleItem

class grScene(QGraphicsScene):
    """ Simple scene to handle some basic clicks for testing"""

    def __init__(self):
        super().__init__()
    
    def mousePressEvent(self, mouseEvent):
        mPos = mouseEvent.scenePos()
        if (mouseEvent.button() == Qt.MouseButton.RightButton):
            # Nothing selected, print all the coordinates 
            if len(self.selectedItems()) == 0:
                print("Scene Items:")
                for item in self.items():
                    print(item)
            #right click on a selected item to add
            elif len(self.selectedItems()) == 1 and not( mouseEvent.modifiers() & Qt.ShiftModifier) :
                #Add a new point into the spline at mPos
                self.selectedItems()[0].addPoint(mPos)
            #<shift> rightclick to delete
            elif len(self.selectedItems()) == 1 and ( mouseEvent.modifiers() & Qt.ShiftModifier) :
                #delete the control point at mPos
                self.selectedItems()[0].deletePoint(mPos)
        
        #pass on
        super().mousePressEvent(mouseEvent)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scene = grScene()
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)

        #Don't confuse the tangents with vectors! The tangents point in the direction of `t`
        #2 point
        spline2 = HermiteSplineItem( [QPointF(150, 400), QPointF(250, 400)],        #points
                                    [(0,QPointF(50, -50)),  (QPointF(50, -50),0)]   #tangents (0's for outer, undefined tangents)
        )
        self.scene.addItem(spline2)

        #2pt, no tangents given
        spline2nt = HermiteSplineItem( [QPointF(450, 100), QPointF(550, 150)])
        self.scene.addItem(spline2nt)

        #3 point
        spline3 = HermiteSplineItem( [QPointF(250, 300),     QPointF(400,330),                  QPointF(550, 300)], #points
                                    [(0,QPointF(50, -50)), (QPointF(10,10),QPointF(10,10)), (QPointF(50, -50),0)] #tangents
        )
        self.scene.addItem(spline3)
        spline3.pen = QPen(Qt.blue, 1)

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

        #3 point, no tangents
        spline5 = HermiteSplineItem([QPointF(500, 100),QPointF(550,50), QPointF(600,100)])
        self.scene.addItem(spline5)
        spline5.pen = QPen(Qt.darkGreen, 1)

        #5 point, no tangents
        spline5 = HermiteSplineItem([QPointF(500, 400),QPointF(550,550), QPointF(600,450), QPointF(650,550),QPointF(700,400)])
        self.scene.addItem(spline5)

        #3 point, 'backwards'
        splineb3 = HermiteSplineItem([QPointF(400,550), QPointF(350,600), QPointF(200,550)])
        self.scene.addItem(splineb3)

        instructions = QGraphicsTextItem("Click a curve to edit it. Select and right-click to add a point.\n" \
                                        "Right click on empty space to print all the spline coordinates")
        instructions.setPos(0,0)
        self.scene.addItem(instructions)

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