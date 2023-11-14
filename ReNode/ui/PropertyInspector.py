from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ReNode.app.Logger import RegisterLogger

class Inspector(QDockWidget):
    refObject = None
    def __init__(self,graphRef):
        Inspector.refObject = self
        super().__init__("Инспектор")
        self.nodeGraphComponent = graphRef
        self.logger = RegisterLogger("Inspector")
    

    def updateProps(self):
        pass