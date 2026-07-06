from PySide6.QtWidgets import (
    QMessageBox
)
from PySide6.QtCore import Qt
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
    
    msgBox = QMessageBox()
    msgBox.setWindowTitle("Higraph - Error")
    msgBox.setIcon(QMessageBox.Icon.Critical)
    msgBox.setText(msg)
    if infoText: msgBox.setInformativeText(infoText)
    detailTrailer = "\nemail details to higraph@isijingi.co.za"
    #TODO: Add this once the repo is public
    #  or log an issue on github https://github.com/ghillebrand/Higraph/issues"
    msgBox.setDetailedText(detailText+detailTrailer)
    #The user must do the emailing
    msgBox.setStandardButtons(QMessageBox.StandardButton.Ok)
    msgBox.setDefaultButton(QMessageBox.StandardButton.Ok)
    ret = msgBox.exec()