""" Test program for Hermite Spline Class"""


from PySide6.QtWidgets import QMainWindow, QGraphicsScene, QGraphicsView, QApplication, QGraphicsTextItem
from PySide6.QtCore import QRectF, QPointF, Qt
from PySide6.QtGui import  QPen, QPainter

import sys

from  HermiteSpline import HermiteSplineItem, HandleItem

class grScene(QGraphicsScene):
    """ Simple scene to handle some basic clicks for testing"""

    def __init__(self):
        super().__init__()
    
    def mousePressEvent(self, mouseEvent):
        mPos = mouseEvent.scenePos()
        if (mouseEvent.button() == Qt.MouseButton.RightButton):
            if len(self.selectedItems()) == 0:
                # Nothing selected, print all the coordinates 
                print("Scene Items:")
                for item in self.items():
                    print(f"{item},")
            elif len(self.selectedItems()) == 1:
                #Add a new point into the spline at mPos
                self.selectedItems()[0].addPoint(mPos)

        #pass on
        super().mousePressEvent(mouseEvent)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scene = grScene()
        self.view = QGraphicsView(self.scene)
        self.setCentralWidget(self.view)
	
        Hermite = [
                ([QPointF(253.000000, 196.000000), QPointF(329.224281, 178.603375), QPointF(267.000000, 199.000000)],
                [(0, QPointF(33.000000, -22.000000)), (QPointF(7.698649, 18.458895), QPointF(7.698649, 18.458895)), (QPointF(-17.000000, -9.000000), 0)]),
                ([QPointF(440.000000, 179.000000), QPointF(479.688092, 154.238046), QPointF(440.000000, 190.000000)],
                [(0, QPointF(2.888544, -16.055728)), (QPointF(19.765034, -3.056703), QPointF(19.765034, -3.056703)), (QPointF(-57.111456, 5.944272), 0)]),
                ([QPointF(192.000000, 211.000000), QPointF(171.000000, 243.000000), QPointF(203.000000, 280.000000)],
                [(0, QPointF(-19.000000, -37.000000)), (QPointF(12.000000, 35.000000), QPointF(12.000000, 35.000000)), (QPointF(16.000000, -21.000000), 0)]),
                ([QPointF(251.000000, 398.000000), QPointF(370.000000, 390.000000), QPointF(422.000000, 385.000000), QPointF(496.000000, 388.000000)],
                [(0, QPointF(56.000000, -13.000000)), (QPointF(13.000000, 15.000000), QPointF(13.000000, 15.000000)), (QPointF(12.000000, -13.000000), QPointF(12.000000, -13.000000)), (QPointF(45.000000, 9.000000), 0)]),
                ([QPointF(121.000000, 10.000000), QPointF(480.375674, -69.014486), QPointF(525.000000, 147.000000), QPointF(516.233420, 313.385420), QPointF(494.100954, 426.429797), QPointF(400.513545, 479.730057), QPointF(302.000000, 459.000000)],
                [(0, QPointF(44.142136, -145.142136)), (QPointF(36.462751, 52.356841), QPointF(36.462751, 52.356841)), (QPointF(7.000000, 35.000000), QPointF(7.000000, 35.000000)), (QPointF(-0.008696, 19.999998), QPointF(-0.008696, 19.999998)), (QPointF(-25.251409, 14.172903), QPointF(-25.251409, 14.172903)), (QPointF(-33.121361, 3.862898), QPointF(-33.121361, 3.862898)), (QPointF(-45.857864, 1.142136), 0)]),
                ([QPointF(233.000000, 150.000000), QPointF(353.000000, 163.000000), QPointF(365.000000, 289.000000), QPointF(369.122645, 328.061740), QPointF(413.000000, 325.000000), QPointF(406.609339, 283.036817), QPointF(399.148121, 153.834996), QPointF(509.000000, 142.000000)],
                [(0, QPointF(85.324555, -25.026334)), (QPointF(7.888544, 14.944272), QPointF(7.888544, 14.944272)), (QPointF(-10.000000, 24.000000), QPointF(-10.000000, 24.000000)), (QPointF(11.994385, -4.526100), QPointF(11.994385, -4.526100)), (QPointF(17.888544, -8.944272), QPointF(17.888544, -8.944272)), (QPointF(-2.505728, -19.842412), QPointF(-2.505728, -19.842412)), (QPointF(7.452899, -14.051009), QPointF(7.452899, -14.051009)), (QPointF(14.324555, 28.026334), 0)]),
                ([QPointF(495.000000, 392.000000), QPointF(397.000000, 421.000000), QPointF(261.000000, 408.000000)],
                [(0, QPointF(-47.142136, -4.857864)), (QPointF(-83.000000, 9.000000), QPointF(-83.000000, 9.000000)), (QPointF(-29.973666, 17.675445), 0)]),
        ]
        
        splines = []
        for s in Hermite:
            splines.append(HermiteSplineItem(s[0],s[1]))
            self.scene.addItem(splines[-1])

        instructions = QGraphicsTextItem("Click a curve to edit it. Select and right-click to add a point.\n" \
                                        "Right click on empty space to print all the spline coordinates")
        instructions.setPos(0,0)
        self.scene.addItem(instructions)

        #self.scene.setSceneRect(QRectF(0, 0, 800, 600))
        self.view.setRenderHint(QPainter.Antialiasing)
        self.view.setDragMode(QGraphicsView.RubberBandDrag)
        #self.resize(900, 700)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())