from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from Qt import QtCore

from ReNode.ui.SearchMenuWidget import SearchComboButton,addTreeContent,createTreeDataContent,addTreeContentItem

class ArrayWidget(QWidget):

    value_changed = QtCore.Signal(object)

    def __init__(self, instancer=None):
        super(ArrayWidget,self).__init__()
        self.instancer = instancer
        self.valuetype = '' # это просто строчная репрезентация типа
        self.isEnum = False
        self.initUI()

    def init_enum_values(self,valuetypes):
        self.valuetype = valuetypes
        self.isEnum = self.getFactory().isEnumType(valuetypes)

    def getNodeGraphComponent(self):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        return NodeGraphComponent.refObject
    def getFactory(self):
        return self.getNodeGraphComponent().getFactory()

    def initUI(self):
        self.layout = QVBoxLayout()

        # Создайте кнопку для добавления нового элемента
        self.addButton = QPushButton("Добавить элемент")
        self.addButton.clicked.connect(self.addArrayElement)
        self.layout.addWidget(self.addButton)

        self.countInfo = QLabel("")
        self.layout.addWidget(self.countInfo)

        # Создайте список для хранения элементов массива
        self.arrayElements = []

        # Создайте область прокрутки для элементов
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scrollAreaLayout.addStretch(1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.layout.addWidget(self.scrollArea)
        self.setLayout(self.layout)

        self.updateCountText()

    def updateCountText(self):
        self.countInfo.setText(f"Количество элементов: {len(self.arrayElements)}")

        for i, elay in enumerate(self.arrayElements):
            elay.itemAt(0).widget().setText(f'{i}: ')

    def get_value(self):
        return [element.itemAt(1).widget().get_value() for element in self.arrayElements]

    def set_value(self, values):
        for elementLayout in self.arrayElements.copy():
            self.removeArrayElement(elementLayout)
        
        self.arrayElements.clear()
        
        for v in values:
            self.addArrayElement(val=v)

        self.updateCountText()

        self.callChangeValEvent()
        return

    def callChangeValEvent(self):
        self.value_changed.emit(self.get_value())

    def addArrayElement(self,val=None):
        # Создайте горизонтальный контейнер для нового элемента
        elementLayout = QHBoxLayout()

        elementLayout.addWidget(QLabel(''))

        # Создайте виджет для значения элемента (может быть QLineEdit, QSpinBox или другой)
        elementValueWidget = None
        if self.instancer:
            elementValueWidget = self.instancer()
            if self.isEnum:
                elementValueWidget.init_enum_values(self.valuetype)
            if val:
                elementValueWidget.set_value(val)

            elementValueWidget.value_changed.connect(lambda: self.callChangeValEvent())
        else:
            elementValueWidget = QLabel("ERROR INSTANCE NOT SET")
        elementLayout.addWidget(elementValueWidget)

        # Создайте кнопки для перемещения элемента вверх и вниз
        moveUpButton = QPushButton("")
        moveUpButton.setIcon(QtGui.QIcon("data\\icons\\ArrowUp_12x.png"))
        moveUpButton.setToolTip("Поднять выше")
        moveDownButton = QPushButton("")
        moveDownButton.setIcon(QtGui.QIcon("data\\icons\\ArrowDown_12x.png"))
        moveDownButton.setToolTip("Опустить ниже")

        def moveUp():
            index = self.arrayElements.index(elementLayout)
            if index > 0:
                element = self.arrayElements.pop(index)
                self.arrayElements.insert(index - 1, element)
                self.scrollAreaLayout.takeAt(index)
                self.scrollAreaLayout.insertLayout(index - 1, elementLayout)
                self.updateCountText()
                self.callChangeValEvent()

        def moveDown():
            index = self.arrayElements.index(elementLayout)
            if index < len(self.arrayElements) - 1:
                element = self.arrayElements.pop(index)
                self.arrayElements.insert(index + 1, element)
                self.scrollAreaLayout.takeAt(index)
                self.scrollAreaLayout.insertLayout(index + 1, elementLayout)
                self.updateCountText()
                self.callChangeValEvent()

        moveUpButton.clicked.connect(moveUp)
        moveDownButton.clicked.connect(moveDown)

        elementLayout.addWidget(moveUpButton)
        elementLayout.addWidget(moveDownButton)

        # Создайте кнопку для удаления элемента
        removeButton = QPushButton("")
        removeButton.setIcon(QtGui.QIcon("data\\icons\\Cross_12x.png"))
        removeButton.setToolTip("Удалить")
        removeButton.clicked.connect(lambda: self.removeArrayElement(elementLayout))
        elementLayout.addWidget(removeButton)

        self.arrayElements.append(elementLayout)
        self.scrollAreaLayout.insertLayout(len(self.arrayElements) - 1, elementLayout)

        self.updateCountText()
                
        self.callChangeValEvent()

    def removeArrayElement(self, elementLayout):
        if elementLayout in self.arrayElements:
            self.arrayElements.remove(elementLayout)
            for i in reversed(range(elementLayout.count())):
                widget = elementLayout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            elementLayout.deleteLater()
        self.updateCountText()
                
        self.callChangeValEvent()


class DictWidget(QWidget):

    value_changed = QtCore.Signal(object)

    def __init__(self, instancer,widVarType):
        super(DictWidget, self).__init__()
        from ReNode.ui.VariableManager import VariableManager
        self.varmgr = VariableManager.refObject
        self.instancer = instancer

        self.keytype = '' #not used now
        self.valuetype = ''
        self.isEnum = False # for valuetype

        if not widVarType: #autodef
            raise Exception("TODO FIX dict widget")
            widVarType = self.varmgr.widVarType
        self.activeSeachBox = isinstance(widVarType,SearchComboButton)
        if self.activeSeachBox:
            self.widVarTypeRef :SearchComboButton = widVarType
            self.valWidgetInstancer = None
        else:
            self.valWidgetInstancer = widVarType
            self.widVarTypeRef = None
        self.initUI()

    def isConstDictValue(self): return not self.activeSeachBox

    def init_enum_values(self,keytype):
        self.keytype = keytype
    def on_update_value_type(self,data):
        self.valuetype = data
        self.isEnum = self.getFactory().isEnumType(data)
    #region Internal helpers
    def getNodeGraphComponent(self):
        from ReNode.ui.NodeGraphComponent import NodeGraphComponent
        return NodeGraphComponent.refObject
    def getFactory(self):
        return self.getNodeGraphComponent().getFactory()
    #endregion

    def initUI(self):
        self.layout = QVBoxLayout()
        
        if not self.isConstDictValue():
            laydat = QHBoxLayout()
        
            self.layout.addLayout(laydat)
            laydat.addWidget(QLabel("Тип значений:"))

        
            self.selectType = self.widVarTypeRef.__class__()
            laydat.addWidget(self.selectType)
            self.selectType.loadContents(self.widVarTypeRef.dictTree)
            # for idx in range(0,self.widVarTypeRef.count()):
            #     txt = self.widVarTypeRef.itemText(idx)
            #     icn = self.widVarTypeRef.itemIcon(idx)
            #     self.selectType.addItem(icn,txt)

            def __curIdxChanged(data,text,icon):
                if len(self.arrayElements) > 0:
                    for item in self.arrayElements.copy():
                        self.removeArrayElement(item)
                    return
                #data is real data
                self.on_update_value_type(data)
            self.selectType.changed_event.connect(__curIdxChanged)

        # Создайте кнопку для добавления нового элемента
        self.addButton = QPushButton("Добавить элемент")
        self.addButton.clicked.connect(self.addArrayElement)
        self.layout.addWidget(self.addButton)

        self.countInfo = QLabel("")
        self.layout.addWidget(self.countInfo)

        # Создайте список для хранения элементов массива
        self.arrayElements = []

        # Создайте область прокрутки для элементов
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.scrollAreaLayout.addStretch(1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        self.layout.addWidget(self.scrollArea)
        self.setLayout(self.layout)

        self.updateCountText()

    def updateCountText(self):
        self.countInfo.setText(f"Количество элементов: {len(self.arrayElements)}\nКлюч : значение")

    def get_value(self):
        # print(f'len items: {len(self.arrayElements)}')
        # for i, element in enumerate(self.arrayElements):
        #     print(f"key {i}: {element.itemAt(0).widget().get_value()}")
        #     print(f"val {i}: {element.itemAt(1).widget().get_value()}")
        
        return {
            element.itemAt(0).widget().get_value() : element.itemAt(1).widget().get_value() for element in self.arrayElements
        }
    
    def get_values_count(self):
        return len(self.arrayElements)

    def set_value(self, values):
        for elementLayout in self.arrayElements.copy():
            self.removeArrayElement(elementLayout)
        
        self.arrayElements.clear()
        
        for v,ve in values.items():
            self.addArrayElement(keyVal=v,valItem=ve)

        self.updateCountText()

        self.callChangeValEvent()
        return

    def callChangeValEvent(self):
        self.value_changed.emit(self.get_value())

    def addArrayElement(self,keyVal=None,valItem=None):
        from ReNode.ui.VariableManager import VariableManager

        if self.widVarTypeRef and self.widVarTypeRef.get_value() != "string":
            from ReNode.app.application import Application
            #! потому что например для ключей типа vec3 выпадет исключение при формировании словаря
            Application.refObject.logger.error(f"В текущей версии программы ключами словаря могут быть только строки - \"{self.widVarTypeRef.get_text()}\" не допускается")
            return

        # Создайте горизонтальный контейнер для нового элемента
        elementLayout = QHBoxLayout()

        # Создайте виджет для значения элемента (может быть QLineEdit, QSpinBox или другой)
        elementValueWidget = None
        if self.instancer:
            elementValueWidget = self.instancer()
            if keyVal:
                elementValueWidget.set_value(keyVal)
            
            elementValueWidget.value_changed.connect(lambda: self.callChangeValEvent())
        else:
            elementValueWidget = QLineEdit()
        elementLayout.addWidget(elementValueWidget)

        if self.isConstDictValue():
            instancerValue = self.valWidgetInstancer()
        else:
            type = self.selectType.get_value()
            typeObj = VariableManager.refObject.getVariableTypedefByType(type)
            instancerValue = typeObj.classInstance()
        if self.isEnum:
            instancerValue.init_enum_values(self.valuetype)
        if valItem:
            instancerValue.set_value(valItem)
        
        instancerValue.value_changed.connect(lambda: self.callChangeValEvent())

        elementLayout.addWidget(instancerValue)


        # Создайте кнопки для перемещения элемента вверх и вниз
        moveUpButton = QPushButton("")
        moveUpButton.setIcon(QtGui.QIcon("data\\icons\\ArrowUp_12x.png"))
        moveUpButton.setToolTip("Поднять выше")
        moveDownButton = QPushButton("")
        moveDownButton.setIcon(QtGui.QIcon("data\\icons\\ArrowDown_12x.png"))
        moveDownButton.setToolTip("Опустить ниже")

        def moveUp():
            index = self.arrayElements.index(elementLayout)
            if index > 0:
                element = self.arrayElements.pop(index)
                self.arrayElements.insert(index - 1, element)
                self.scrollAreaLayout.takeAt(index)
                self.scrollAreaLayout.insertLayout(index - 1, elementLayout)
                self.callChangeValEvent()

        def moveDown():
            index = self.arrayElements.index(elementLayout)
            if index < len(self.arrayElements) - 1:
                element = self.arrayElements.pop(index)
                self.arrayElements.insert(index + 1, element)
                self.scrollAreaLayout.takeAt(index)
                self.scrollAreaLayout.insertLayout(index + 1, elementLayout)
                self.callChangeValEvent()

        moveUpButton.clicked.connect(moveUp)
        moveDownButton.clicked.connect(moveDown)

        elementLayout.addWidget(moveUpButton)
        elementLayout.addWidget(moveDownButton)

        # Создайте кнопку для удаления элемента
        removeButton = QPushButton("")
        removeButton.setIcon(QtGui.QIcon("data\\icons\\Cross_12x.png"))
        removeButton.setToolTip("Удалить")
        removeButton.clicked.connect(lambda: self.removeArrayElement(elementLayout))
        elementLayout.addWidget(removeButton)

        self.arrayElements.append(elementLayout)
        self.scrollAreaLayout.insertLayout(len(self.arrayElements) - 1, elementLayout)

        self.updateCountText()
                
        self.callChangeValEvent()

    def removeArrayElement(self, elementLayout):
        if elementLayout in self.arrayElements:
            self.arrayElements.remove(elementLayout)
            for i in reversed(range(elementLayout.count())):
                widget = elementLayout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            elementLayout.deleteLater()
        self.updateCountText()
                
        self.callChangeValEvent()