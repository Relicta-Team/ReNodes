from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ReNode.app.Logger import RegisterLogger

class WidgetListElements(QWidget):
    def __init__(self):
        super().__init__()
        self.vlayout = QVBoxLayout()

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scrollAreaLayout.addStretch(1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.vlayout.addWidget(self.scrollArea)
        self.setLayout(self.vlayout)

class Inspector(QDockWidget):
    refObject = None
    def __init__(self,graphRef):
        Inspector.refObject = self
        super().__init__("Инспектор")
        self.nodeGraphComponent = graphRef
        self.logger = RegisterLogger("Inspector")
        self.propertyList = [] 
        
        self.propertyListWidget = QWidget()
        self.vlayout = QVBoxLayout() #main vertical layout
        self.propertyListWidget.setLayout(self.vlayout)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scrollAreaLayout.addStretch(1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        
        self.vlayout.addWidget(QLabel("Список свойств:"))
        self.vlayout.addWidget(self.scrollArea)
        #self.vlayout.addWidget(QLabel("Test footer"))
        #self.mainWidget = WidgetListElements()
        self.setWidget(self.propertyListWidget)
        

        for i in range(1,100):
            self.addProperty(f"inspector prop {i}",QLabel("TEST VALUE" + " e" * 100))

    def addProperty(self,propName,propObject):
        hlayout = QHBoxLayout()
        hlayout.setSpacing(20)
        name = QLabel(propName)
        name.setTextInteractionFlags(name.textInteractionFlags() | Qt.TextSelectableByMouse)
        hlayout.addWidget(name)
        hlayout.addWidget(propObject)
        self.scrollAreaLayout.addLayout(hlayout)

    def updateProps(self):
        for item in self.propertyList:
            item.deleteLater()
        self.propertyList.clear()

        pass