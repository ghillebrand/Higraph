import sys
from PySide6.QtWidgets import (
    QMessageBox
)
from PySide6.QtCore import Qt, QStandardPaths
from  HGConstants import *

def WarningMessage(msg:str, infoText = "", detailText = ""):
    """ Standard Warning Message """

    msgBox = QMessageBox()
    msgBox.setWindowTitle("Higraph - Warning")
    msgBox.setIcon(QMessageBox.Icon.Warning)
    msgBox.setText(msg)
    if infoText: msgBox.setInformativeText(infoText)
    if detailText: msgBox.setDetailedText(detailText)
    msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
    msgBox.setDefaultButton(QMessageBox.StandardButton.Ok)
    ret = msgBox.exec()


def ErrorMessage(msg:str, infoText = "", detailText = ""):
    """ Standard error message """

    #Since this asks the user to email the error file, make sure the data is written
    sys.stdout.flush()
    sys.stderr.flush()

    msgBox = QMessageBox()
    msgBox.setWindowTitle("Higraph - Error")
    msgBox.setIcon(QMessageBox.Icon.Critical)
    msgBox.setText(msg)
    if infoText: msgBox.setInformativeText(infoText)
    detailTrailer = f"\nPlease copy this text and email it,\nand the error file in {QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)}\nalong with any useful details to\nhigraph@isijingi.co.za\nor log an issue on github \nhttps://github.com/ghillebrand/Higraph/issues"
    # The info text is not copyable, so include it again with the details
    msgBox.setDetailedText(msg +"\n"+infoText+"\n"+detailText+detailTrailer)
    #The user must do the emailing
    msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
    msgBox.setDefaultButton(QMessageBox.StandardButton.Ok)
    ret = msgBox.exec()