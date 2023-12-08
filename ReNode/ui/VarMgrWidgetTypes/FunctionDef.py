from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from Qt import QtCore
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from NodeGraphQt.custom_widgets.properties_bin.prop_widgets_base import *
from ReNode.ui.SearchMenuWidget import SearchComboButton,addTreeContent,createTreeDataContent,addTreeContentItem
from ReNode.app.utils import updateIconColor, mergePixmaps, generateIconParts

class DataTypeSelectorGroup(QWidget):
    def __init__(self,srcLayout=None,ofsX=0,ofsY=0):
        super(DataTypeSelectorGroup,self).__init__()
        from ReNode.ui.VariableManager import VariableManager
        lay = srcLayout or QGridLayout()

        contents = VariableManager.refObject.getAllTypesTreeContent()
        comboButton = SearchComboButton()
        comboButton.loadContents(contents)

        lay.addWidget(QLabel("Тип параметра:"),ofsX+0,ofsY+0)
        lay.addWidget(comboButton,ofsX+0,ofsY+1)
        self.widParamType = comboButton

        self.widDataType = QComboBox()
        for vobj in VariableManager.refObject.variableDataType:
            icn = None
            if isinstance(vobj.icon,list):
                for pat in vobj.icon:
                    icntemp = QPixmap(pat)
                    if icn:
                        icntemp = mergePixmaps(icn,icntemp)
                    icn = icntemp
                icn = QIcon(icn)
            else:
                icn = QIcon(vobj.icon)
            self.widDataType.addItem(icn,vobj.text)
            self.widDataType.setItemData(self.widDataType.count()-1,vobj.dataType,Qt.UserRole)
        self.widDataType.currentIndexChanged.connect(lambda: self.onDataTypeChanged(self.widDataType.currentIndex()))
        lay.addWidget(QLabel("Тип данных:"),ofsX+1,ofsY+0)
        lay.addWidget(self.widDataType,ofsX+1,ofsY+1)

        self.ofsX = ofsX
        self.ofsY = ofsY
        self.optText = None
        self.optData = None

        optText = QLabel("Тип значений:")
        lay.addWidget(optText,ofsX+2,ofsY+0)
        optData = SearchComboButton()
        optData.loadContents(contents)
        lay.addWidget(optData,ofsX+2,ofsY+1)
        
        self.optData = optData
        self.optText = optText

        if not srcLayout:
            self.setLayout(lay)
            self.srcLayout = lay
        else:
            self.srcLayout = srcLayout
        
        self.onDataTypeChanged(0)

    def updateVisual(self,tobj):
        hasVisible = tobj.dataType == "dict"
        self.optData.setVisible(hasVisible)
        self.optText.setVisible(hasVisible)


    def onDataTypeChanged(self,newIndexDatatype):
        from ReNode.ui.VariableManager import VariableTypedef,VariableDataType,VariableManager
        #newIndexDatatype = args[0]
        tobj : VariableDataType = VariableManager.refObject.variableDataType[newIndexDatatype]
        self.updateVisual(tobj)

class FunctionDefWidget(QWidget):

    value_changed = QtCore.Signal(object)

    def __init__(self):
        super(FunctionDefWidget,self).__init__()        
        self.initUI()

    def initUI(self):
        #параметры функции
        self.layout = QVBoxLayout()

        # Создайте кнопку для добавления нового элемента
        self.addButton = QPushButton("Добавить параметр")
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
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        #self.scrollAreaLayout.addStretch(1)
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)
        self.scrollArea.setMinimumHeight(400)

        self.layout.addWidget(self.scrollArea)
        self.setLayout(self.layout)

        self.updateCountText()

    def updateCountText(self):
        if len(self.arrayElements):
            self.countInfo.setText(f"Параметров: {len(self.arrayElements)}")
        else:
            self.countInfo.setText(f"Без параметров")

        for i, elay in enumerate(self.arrayElements):
            elay.itemAt(0).widget().setText(f'{i+1}: ')

        self.getParamInfo()

    def get_value(self):
        return None
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

    class InternalGrid(QGridLayout):
        def __init__(self):
            super().__init__()
            self.paramName = None
            self.paramDesc = None
            self.paramType = None
            self.paramDataType = None
            self.paramValueTypes = None #for dict

    def getParamInfo(self):
        """Получает массив метаданных для создания функции
        
            {
                "name": paramName,
                "desc": paramDesc,
                "dataType": paramDataType,
                "type": paramType,
                "optValType": optValType
            }
        
        """
        
        paramData = []
        for itm in self.arrayElements:
            grid : FunctionDefWidget.InternalGrid = itm.itemAt(1).widget().layout()
            paramName = grid.paramName.text().rstrip(' ').lstrip(' ')
            paramDesc = grid.paramDesc.text().rstrip(' ').lstrip(' ')
            paramDataType = grid.paramDataType.currentData() #value,dict,array,etc...
            paramType = grid.paramType.get_value()
            optValType = grid.paramValueTypes.get_value() #for dict (value type)

            print(f"{paramDataType}[{paramType},{optValType}] {paramName} - {paramDesc}")
            paramData.append({
                "name": paramName,
                "desc": paramDesc,
                "dataType": paramDataType,
                "type": paramType,
                "optValType": optValType
            })

        return paramData


    def addArrayElement(self,val=None):
        from ReNode.ui.VariableManager import VariableManager

        if len(self.arrayElements) >= 15:
            VariableManager.refObject.nodeGraphComponent.mainWindow.logger.error("Слишком много параметров. Используйте объекты или контейнеры для передачи.")
            return

        # Создайте горизонтальный контейнер для нового элемента
        elementLayout = QHBoxLayout()

        elementLayout.addWidget(QLabel('')) #индексатор

        # Создайте виджет для значения элемента (может быть QLineEdit, QSpinBox или другой)
        elementValueWidget = None

        grid = FunctionDefWidget.InternalGrid()
        mainGroup = QWidget()
        mainGroup.setLayout(grid)
        elementLayout.addWidget(mainGroup)
        #elementLayout.addLayout(grid)

        paramName = QLineEdit()
        optWid = paramName.fontMetrics().width("Имя параметра")
        paramName.setMaximumWidth(optWid + 10)
        paramName.setPlaceholderText("Имя параметра")
        paramDesc = QLineEdit()
        paramDesc.setPlaceholderText("Описание параметра (опционально)")
        grid.addWidget(paramName,0,0)
        grid.addWidget(paramDesc,0,1)
        
        groupType = DataTypeSelectorGroup(srcLayout=grid,ofsX=2,ofsY=0)
        
        #init references
        grid.paramName = paramName
        grid.paramDesc = paramDesc
        grid.paramType = groupType.widParamType
        grid.paramDataType = groupType.widDataType
        grid.paramValueTypes = groupType.optData

        #grid.addWidget(groupType,1,0)

        # paramTypeDesc = QLabel('Тип параметра:')
        # paramTypeDesc.setToolTip("Тип данных параметра")
        # contents = VariableManager.refObject.getAllTypesTreeContent()
        # comboButton = SearchComboButton()
        # comboButton.loadContents(contents)
        # grid.addWidget(paramTypeDesc,1,0,alignment=Qt.AlignmentFlag.AlignLeft)
        # grid.addWidget(comboButton,1,1)

        # paramDataTypeDesc = QLabel("Тип данных:")
        # paramDataTypeDesc.setToolTip("Тип данных параметра")
        # grid.addWidget(paramDataTypeDesc,2,0,alignment=Qt.AlignmentFlag.AlignLeft)
        # paramDataType = QComboBox()
        # grid.addWidget(paramDataType,2,1)
        # paramDataTypeSelect = SearchComboButton()
        # paramDataTypeSelect.loadContents(contents)
        # grid.addWidget(paramDataTypeSelect,2,2)
        

        #elementLayout.addWidget(elementValueWidget)

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
                itm = elementLayout.itemAt(i)
                if isinstance(itm, QLayout):
                    #delete all items inside layout
                    for j in reversed(range(itm.count())):
                        itm.itemAt(j).widget().deleteLater()
                    itm.deleteLater()
                widget = itm.widget()
                if widget:
                    widget.deleteLater()
            elementLayout.deleteLater()
        self.updateCountText()
                
        self.callChangeValEvent()