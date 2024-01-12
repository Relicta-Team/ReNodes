import typing
from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from ReNode.app.Logger import RegisterLogger
from ReNode.app.NodeFactory import NodeFactory
from ReNode.ui.VariableManager import VariableManager, VariableTypedef
from ReNode.app.utils import generateIconParts
from NodeGraphQt.base.commands import ChangeInspectorPropertyCommand,ResetToDefaultInspectorPropertyCommand

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

class QLabelWithIcon(QWidget):
    def __init__(self,_text=None):
        super().__init__()

        layout = QHBoxLayout()
        layout.setContentsMargins(2, 0, 0, 0)
        self.setLayout(layout)

        self.textWid = QLabel(text=_text)
        self.icon = QLabel()
        #self.icon.setFixedWidth(16)
        layout.addWidget(self.icon)
        layout.addSpacing(-4)
        layout.addWidget(self.textWid)

        layout.addStretch()
    
    def setPixmap(self,pixmap):                         self.icon.setPixmap(pixmap)
    def pixmap(self):                                   return self.icon.pixmap()
    def setProperty(self, name: str, value) -> bool:    return self.textWid.setProperty(name, value)
    def property(self, name: str):                      return self.textWid.property(name)
    
    def setText(self,text):                             self.textWid.setText(text)
    def text(self):                                     return self.textWid.text()

    def setTextInteractionFlags(self,flags):            self.textWid.setTextInteractionFlags(flags)
    def textInteractionFlags(self):                     return self.textWid.textInteractionFlags()

    def setToolTip(self,tip):                           self.textWid.setToolTip(tip)
    def toolTip(self):                                  return self.textWid.toolTip()

    

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

    def getUndoStack(self) -> QUndoStack:
        return self.nodeGraphComponent.graph._undo_stack

    def getPropNameView(self,cat,sysname) -> QLabelWithIcon | QLabel: return self.propWidgetRefs[cat + "." + sysname][0]
    def getPropView(self,cat,sysname): return self.propWidgetRefs[cat + "." + sysname][1]

    def setPropValue(self,cat,sysname,val,toDefault=False):
        obj = self.getPropView(cat,sysname)
        if obj:
            props = self.infoData['props']
            if cat not in props: props[cat] = {}
            if toDefault:
                self.getUndoStack().push(ResetToDefaultInspectorPropertyCommand(self,props,cat,sysname))
            else:
                self.getUndoStack().push(ChangeInspectorPropertyCommand(self,props,cat,sysname,val))
            #replaced in command
            #self.syncPropValue(cat,sysname,False) #sync visual

            
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
                objText.setText(objText.property("defaultName"))
                if setProp:
                    obj.blockSignals(True)
                    obj.set_value(props[cat][sysname])
                    obj.blockSignals(False)
            else:
                objText.setText(f"{objText.property('defaultName')} (знач. от {par})")
                if setProp:
                    obj.blockSignals(True)
                    obj.set_value(obj.property("defaultValue"))
                    obj.blockSignals(False)
            pass

    def resetPropToDefault(self,cat,sysname):
        props = self.infoData.get('props')
        if props and cat in props and sysname in props[cat]:
            #del props[cat][sysname]
            #self.syncPropValue(cat,sysname,True)
            self.setPropValue(cat,sysname,None,True)
        pass

    def addProperty(self,definedFromClass,category,propSysName,propName,propObject=None,defaultValue=None):
        hlayout = QGridLayout()
        hlayout.setSpacing(2)
        name = QLabelWithIcon(propName)
        name.setProperty("defaultName",propName)
        name.setProperty("defClass",definedFromClass)
        name.setTextInteractionFlags(name.textInteractionFlags() | Qt.TextSelectableByMouse)

        hlayout.addWidget(name,0,0)
       
        if propObject:
            #validate values
            if not hasattr(propObject,"set_value"):
                raise Exception(f"Property {propName} has no set_value method")
            if not hasattr(propObject,"get_value"):
                raise Exception(f"Property {propName} has no get_value method")

            #register reference to property view
            self.propWidgetRefs[category + "." + propSysName] = (name,propObject)
            if defaultValue == None or defaultValue == "$NULL$":
                defaultValue = propObject.get_value()
            propObject.setProperty("defaultValue",defaultValue)
            
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

        # подключаем сигнал изменения значения только после первой синхронизации
        def onChangeValue(newval):
            _val = propObject.get_value()
            self.setPropValue(category,propSysName,_val)

        #check if propObject has value_changed field
        if hasattr(propObject,"value_changed"):
            propObject.value_changed.connect(onChangeValue)
            pass
        elif hasattr(propObject,"valueChanged"):
            propObject.valueChanged.connect(onChangeValue)
            pass
        else:
            raise Exception(f"Property {propName} has no change value signal")

        return name
        

    def cleanupPropsVisual(self):
        for item in self.propertyList.copy():
            self.scrollAreaLayout.removeItem(item)
            for i in range(item.count()):
                intItm = item.itemAt(i)
                intItm.widget().deleteLater()
            item.deleteLater()
        self.propertyList.clear()
        self.propWidgetRefs.clear()

    def updateProps(self):
        self.cleanupPropsVisual()
        
        # !!! ------- TEST FILE SYSTEM TREE ----------
        # dir = "."
        # self.model = QFileSystemModel()
        
        # self.model.setRootPath(dir)
        # self.model.setNameFilters(["*.png","*.graph","*.txt"])
        # self.model.setNameFilterDisables(True)
        # self.model.setFilter(QDir.Dirs | QDir.Filter.Files)
        
        # self.tree =  QTreeView()
        
        # self.tree.setModel(self.model)
        # self.tree.setRootIndex(self.model.index(dir))
        # self.tree.setColumnWidth(0, 250)
        # self.tree.setAlternatingRowColors(True)
        # self.tree.setDragEnabled(True)
        # self.tree.setDragDropMode(QAbstractItemView.DragDrop)
        # self.tree.setDefaultDropAction(Qt.MoveAction)
        # self.scrollAreaLayout.addWidget(self.tree)


        #collect fields
        fact : NodeFactory = self.nodeGraphComponent.getFactory()
        vmgr : VariableManager = self.nodeGraphComponent.variable_manager
        classname = self.infoData.get('classname','object')
        cd = fact.getClassData(classname)
        if not cd:
            self.logger.error("Cannot load class data for {}".format(classname))
            return
        baseList = cd.get('baseList',[])
        # all members check
        existsOptions = {
            "fields": {}, "methods": {}
        }
        optionTextNames = {"fields":"Поле","methods":"Константный метод"}

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
                    fRet = propContents['return'] #для отладки типов можно брать из инспектора
                    fDefault = propContents.get('defval',"$NULL$")
                    # отладочная проверка
                    if nodeData['returnType'] != propContents['return']:
                        from ReNode.app.application import Application
                        if not Application.isDebugMode():
                            raise Exception(f"return type mismatch: {nodeData['returnType']} != {propContents['return']}")

                    vObj,vType = vmgr.getVarDataByType(fRet)
                    propObj = None
                    if vObj:
                        if vType.instance: #not value
                            if vType.dataType == "dict":
                                propObj = vType.instance(vObj[0].classInstance,vObj[1].classInstance)
                                #propObj = vType.instance(*[itm.classInstance for itm in vObj])
                            else:
                                propObj = vType.instance(vObj.classInstance)
                        else:
                            propObj = vObj.classInstance()
                    
                    nameObj = self.addProperty(baseName,cat,propName,fName,propObj,fDefault)
                    if vType:
                        icns = vType.icon
                        clrs = vObj
                        if not isinstance(icns,list):
                            icns = [icns]
                        if not isinstance(clrs,list):
                            clrs = [clrs.color]
                        else:
                            clrs = [itm.color for itm in clrs]
                        #icons to pixmap list
                        pixlist = [QPixmap(icn) for icn in icns]
                        newIcon = generateIconParts(pixlist,clrs)
                        pixW = 16
                        pixH = 16
                        nameObj.setPixmap(newIcon.scaled(pixW,pixH,Qt.KeepAspectRatio))
                    
                    dataTypeText = vmgr.getTextTypename(fRet)
                    nameObj.setToolTip(f"{fDesc}\n\nУнаследовано от {baseName}\nСистемное имя: {propName}\nТип данных: {dataTypeText} ({fRet})\nТип члена: {optionTextNames[cat]}")


                    # line = QFrame()
                    # #line.setGeometry(QRect(320, 150, 118, 3))
                    # line.setFrameShape(QFrame.HLine)
                    # line.setFrameShadow(QFrame.Sunken)
                    # self.scrollAreaLayout.addWidget(line)
                    # self.propertyList.append(line)
                        

            