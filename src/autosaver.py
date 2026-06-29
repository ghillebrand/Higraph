"""
Manage autosaving
"""

import os
import datetime as dt
from pathlib import Path
from PySide6.QtCore import QStandardPaths, QCoreApplication, QTimer, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton

from HGConstants import *


class RestoreFileDialog(QDialog):
    """ Gemini dialog to pick a file from the list
        Displays a modal dialog allowing users to pick a file to restore.
        Returns the selected filename string, "Cancel", or "DeleteAll".
    """

    def __init__(self, file_names: list[str], parent=None)->str:
        super().__init__(parent)
        self.setWindowTitle("Restore Autosave File")
        self.resize(450, 300)
        
        # Default value if the user closes the window using the X button
        self.result_value = "Cancel"

        # Main Layout
        layout = QVBoxLayout(self)

        # 1. File Selection List
        self.list_widget = QListWidget()
        self.list_widget.addItems(file_names)
        # Pre-select the first item so OK works immediately without requiring an explicit click
        if file_names:
            self.list_widget.setCurrentRow(0)
        layout.addWidget(self.list_widget)

        # 2. Setup Buttons Layout
        button_layout = QHBoxLayout()
        
        btn_ok = QPushButton("OK")
        btn_delete_all = QPushButton("Delete All")
        btn_cancel = QPushButton("Cancel")
        
        # Standardize button sizing
        btn_ok.setDefault(True)  # Pressing Enter triggers OK
        
        button_layout.addWidget(btn_ok)
        button_layout.addWidget(btn_delete_all)
        button_layout.addStretch()  # Pushes cancel button to the far right
        button_layout.addWidget(btn_cancel)
        layout.addLayout(button_layout)

        # 3. Component Event Signals
        btn_ok.clicked.connect(self._handle_ok)
        btn_delete_all.clicked.connect(self._handle_delete_all)
        btn_cancel.clicked.connect(self._handle_cancel)
        
        # UX polish: Double-clicking an item in the list behaves like clicking OK
        self.list_widget.itemDoubleClicked.connect(self._handle_ok)

    def _handle_ok(self):
        selected_items = self.list_widget.selectedItems()
        if selected_items:
            self.result_value = selected_items[0].text()
            self.accept()

    def _handle_delete_all(self):
        self.result_value = "DeleteAll"
        self.accept()

    def _handle_cancel(self):
        self.result_value = "Cancel"
        self.reject()


def fileToRestore(fileNames: list[str]) -> str:
    """
    Displays a modal dialog allowing users to pick a file to restore.
    Returns the selected filename string, "Cancel", or "DeleteAll".
    """
    # Guard clause if no files exist to display
    if not fileNames:
        return "Cancel"
        
    dialog = RestoreFileDialog(fileNames)
    dialog.exec()  # Blocks application flow until dialog is dismissed
    
    return dialog.result_value


class autoSaver():
    """ manage all the bits & bobs for autosaving"""
    #Slot for interval update
    updateInterval = Signal()

    def __init__(self, saveFn:callable , openFn:callable , interval:int=1, cycleSize:int = 10, statusBar = None):
        """ setup the autosave process, 
            Calls `saveFn` every `interval` minutes. 
            Calls `openFn` on start if needed for a restore
            Use `cycleCount` files - delete old files out of the cycle count
        """
        baseDir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        self.autosaveDir = os.path.join(baseDir, "autosaves")
        #Make the dir if needed
        os.makedirs(self.autosaveDir, exist_ok=True)
        self.setFileName("untitled")

        self.interval:int = interval
        #don't make infinite saves!
        self.cycleSize:int = cycleSize
        self.cycleCount = 0

        self.saveFunc:callable = saveFn
        self.openFunc:callable = openFn  #for restoring
        self.statusBar = statusBar

        #Check for any orphans, and optionally restore
        self.checkForAutoSaves()
        
        #Set the timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.autoSave)
        if self.interval != 0:
            self.timer.start(self.interval * 1000 * 10)   #* 60 * 1000) #10 sec "minutes" for testing!
        else:
            self.timer.stop()


    def setFileName(self,fileName:str):
        """ set the base fileName to use for saving. Should (must?) include full path
            updated on fileSaveAs
        """
        self.baseFileName:str = fileName

    def setCycleSize(self,CycleSize:int):
        """ Set how many cycles to keep
        """
        self.cycleSize:int = CycleSize

    def setInterval(self,newInterval:int):
        """ update the interval (from preference edit)"""
        self.interval = newInterval
        if self.interval != 0:
            self.timer.start(self.interval * 1000 * 10)   #* 60 * 1000) #10 sec "minutes" for testing!
        else:
            self.timer.stop()

    def autoSave(self):
        """ Autosave periodically """
        #Remove the file(s) from the previous cycle
        for f in Path(self.autosaveDir).glob(f"*{self.cycleCount}.higraphml"):
            Path.unlink(f)

        timeStamp:str = dt.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        saveFile:str = os.path.join(self.autosaveDir,self.baseFileName + "_autosave_" + timeStamp + "_" + str(self.cycleCount)+".higraphml")
        if self.statusBar:
            self.statusBar().showMessage(f"Autosaving to {saveFile}",1000)
        self.saveFunc(autoSaveName=saveFile)
        self.cycleCount = (self.cycleCount + 1) % self.cycleSize

    def checkForAutoSaves(self):
        """ check if there is an autosave file left over after a crash"""
        fileNames = []
        for f in Path(self.autosaveDir).glob(f"*_autosave_*.higraphml"):
            fileNames.append(str(f))
        #print(f"Autosave found file {fileNames}")
        if fileNames:
            #Get the file to restore, or other command
            dialog = RestoreFileDialog(fileNames)
            dialog.exec()  # Blocks application flow until dialog is dismissed
            result = dialog.result_value
            if "higraphml" in result:
                self.openFunc(inFile=result)
                for f in Path(self.autosaveDir).glob(f"*.higraphml"):
                    Path.unlink(f)            

            if result == "DeleteAll":
                    for f in Path(self.autosaveDir).glob(f"*.higraphml"):
                        Path.unlink(f)         
            #Note: "Cancel" will just let the old files be overwritten in time
  


    def clearAutoSaves(self):
        """ Remove any autosaves on clean closeEvent"""
        for f in Path(self.autosaveDir).glob(f"*.higraphml"):
            Path.unlink(f)