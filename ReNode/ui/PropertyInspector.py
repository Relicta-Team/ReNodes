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
        self.propWidgetRefs = {}
        
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
        #    self.addProperty("syscat","propsysname",f"inspector prop {i}",QLabel("TEST VALUE" + " e" * 100))

    def getPropNameView(self,cat,sysname): return self.propWidgetRefs[cat + "." + sysname][0]
    def getPropView(self,cat,sysname): return self.propWidgetRefs[cat + "." + sysname][1]

    def setPropValue(self,cat,sysname,val):
        obj = self.getPropView(cat,sysname)
        if obj:
            props = self.infoData['props']
            if cat not in props: props[cat] = {}
            props[cat][sysname] = val
            
            self.syncPropValue(cat,sysname,False) #sync visual
        pass

    def syncPropValue(self,cat,sysname,setProp=False):
        obj = self.getPropView(cat,sysname)
        props = self.infoData
        props = self.infoData.get('props')
        
        #first init props
        if not props:
            self.infoData['props'] = {}
            props = self.infoData['props']
        if obj:
            hasValue = cat in props and sysname in props[cat]
            objText = self.getPropNameView(cat,sysname)
            par = objText.property("defClass")
            if hasValue:
                objText.setText(objText.property("default"))
                if setProp:
                    obj.set_value(props[cat][sysname])
            else:
                objText.setText(f"{objText.property('default')} (от {par})")
                if setProp:
                    obj.blockSignals(True)
                    obj.set_value(obj.property("default"))
                    obj.blockSignals(False)
            pass

    def resetPropToDefault(self,cat,sysname):
        props = self.infoData.get('props')
        if props and cat in props and sysname in props[cat]:
            del props[cat][sysname]
            self.syncPropValue(cat,sysname,True)
        pass

    def addProperty(self,definedFromClass,category,propSysName,propName,propObject=None):
        hlayout = QGridLayout()
        hlayout.setSpacing(2)
        name = QLabel(propName)
        name.setProperty("default",propName)
        name.setProperty("defClass",definedFromClass)
        name.setTextInteractionFlags(name.textInteractionFlags() | Qt.TextSelectableByMouse)
        hlayout.addWidget(name,0,0)
        if propObject:
            #validate values
            if not hasattr(propObject,"set_value"):
                raise Exception(f"Property {propName} has no set_value method")
            if not hasattr(propObject,"get_value"):
                raise Exception(f"Property {propName} has no get_value method")

            def onChangeValue(newval):
                _val = propObject.get_value()
                self.setPropValue(category,propSysName,_val)

            #register reference to property view
            self.propWidgetRefs[category + "." + propSysName] = (name,propObject)
            propObject.setProperty("default",propObject.get_value())

            #check if propObject has value_changed field
            if hasattr(propObject,"value_changed"):
                propObject.value_changed.connect(onChangeValue)
                pass
            elif hasattr(propObject,"valueChanged"):
                propObject.valueChanged.connect(onChangeValue)
                pass
            else:
                raise Exception(f"Property {propName} has no change value signal")
            
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

            removeButton.clicked.connect(lambda: self.resetPropToDefault(category,propSysName))

        self.scrollAreaLayout.addLayout(hlayout)

        self.propertyList.append(hlayout)

        self.syncPropValue(category,propSysName,True)

        return name
        

    def cleanupPropsVisual(self):
        for item in self.propertyList.copy():
            self.scrollAreaLayout.removeItem(item)
            for i in range(item.count()):
                item.itemAt(i).widget().deleteLater()
            item.deleteLater()
        self.propertyList.clear()
        self.propWidgetRefs.clear()

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
        baseList = cd.get('baseList',[])
        # all members check
        existsOptions = {
            "fields": {}, "methods": {}
        }

        for baseName in baseList:
            objData = fact.getClassData(baseName)
            if not objData: raise Exception(f"Cannot load class data for {baseName} -> {classname}: {baseList}")
            
            nodeCats = objData.get('inspectorProps',{})
            
            for cat,nodes in nodeCats.items():
                #if cat != "fields": continue

                for propName,propContents in nodes.items():
                    #if propName != "name": continue

                    if propName in existsOptions[cat]: continue
                    existsOptions[cat][propName] = True

                    nodeName = propContents.get('node',propName)
                    nodeData = fact.getNodeLibData(cat + "." + nodeName)
                    fName = nodeData['name']
                    fDesc = nodeData.get('desc',"")
                    fRet = nodeData['returnType']

                    vObj = vmgr.getVariableTypedefByType(fRet)
                    propObj = None
                    if vObj:
                        propObj = vObj.classInstance()
                    
                    nameObj = self.addProperty(baseName,cat,propName,fName,propObj)
                    nameObj.setToolTip(fDesc)
            

            