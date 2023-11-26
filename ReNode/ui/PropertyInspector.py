from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ReNode.app.Logger import RegisterLogger
from ReNode.app.NodeFactory import NodeFactory
from ReNode.ui.VariableManager import VariableManager, VariableTypedef

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

        # информация свойств (тип графа, имена классов и тд)
        self.infoData = {}

        self.propertyList = [] 
        
        self.propertyListWidget = QWidget()
        self.vlayout = QVBoxLayout() #main vertical layout
        self.vlayout.setContentsMargins(2,2,2,0)
        self.propertyListWidget.setLayout(self.vlayout)

        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        #self.scrollAreaLayout.addStretch(1) #факапит отображение
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        
        self.vlayout.addWidget(QLabel("Список свойств:"))
        self.vlayout.addWidget(self.scrollArea)
        #self.vlayout.addWidget(QLabel("Test footer"))
        #self.mainWidget = WidgetListElements()
        self.setWidget(self.propertyListWidget)
        

        #for i in range(1,4):
        #    self.addProperty(f"inspector prop {i}",QLabel("TEST VALUE" + " e" * 100))

    def addProperty(self,propName,propObject=None):
        hlayout = QGridLayout()
        hlayout.setSpacing(2)
        name = QLabel(propName)
        name.setTextInteractionFlags(name.textInteractionFlags() | Qt.TextSelectableByMouse)
        hlayout.addWidget(name,0,0)
        if propObject:
            if isinstance(propObject,QCheckBox):
                layProp = (0,1)
                layReset = (0,2)
            else:
                layProp = (1,0)
                layReset = (1,1)
            hlayout.addWidget(propObject,*layProp)

            removeButton = QPushButton("")
            icn = QtGui.QIcon("data\\icons\\resetToDefault_32x.png")
            #removeButton.setMaximumWidth(32)
            removeButton.setFixedWidth(32)
            removeButton.setIcon(icn)
            removeButton.setToolTip("Сбросить значение")
            hlayout.addWidget(removeButton,*layReset)

        self.scrollAreaLayout.addLayout(hlayout)

        self.propertyList.append(hlayout)
        return name
        

    def cleanupPropsVisual(self):
        for item in self.propertyList.copy():
            self.scrollAreaLayout.removeItem(item)
            for i in range(item.count()):
                item.itemAt(i).widget().deleteLater()
            item.deleteLater()
        self.propertyList.clear()

    def updateProps(self):
        self.cleanupPropsVisual()
        
        #collect fields
        fact : NodeFactory = self.nodeGraphComponent.getFactory()
        vmgr : VariableManager = self.nodeGraphComponent.variable_manager
        classname = self.infoData.get('parent','object')
        cd = fact.getClassData(classname)
        if not cd:
            self.logger.error("Cannot load class data for {}".format(classname))
            return

        nodeCats = cd.get('inspectorProps',{})
        
        for cat,nodes in nodeCats.items():
            #if cat != "fields": continue

            for propName,propContents in nodes.items():
                #if propName != "name": continue

                nodeName = propContents.get('node',propName)
                nodeData = fact.getNodeLibData(cat + "." + nodeName)
                fName = nodeData['name']
                fDesc = nodeData.get('desc',"")
                fRet = nodeData['returnType']

                vObj = vmgr.getVariableTypedefByType(fRet)
                propObj = None
                if vObj:
                    propObj = vObj.classInstance()
                
                nameObj = self.addProperty(fName,propObj)
                nameObj.setToolTip(fDesc)
            

            