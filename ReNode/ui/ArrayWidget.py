from PyQt5 import QtGui
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

class ArrayWidget(QWidget):
    def __init__(self, instancer=None):
        super(ArrayWidget,self).__init__()
        self.instancer = instancer
        self.initUI()

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

    def get_value(self):
        return [element.itemAt(0).widget().get_value() for element in self.arrayElements]

    def set_value(self, values):
        for elementLayout in self.arrayElements.copy():
            self.removeArrayElement(elementLayout)
        
        self.arrayElements.clear()
        
        for v in values:
            self.addArrayElement(val=v)

        self.updateCountText()
        return

    def addArrayElement(self,val=None):
        # Создайте горизонтальный контейнер для нового элемента
        elementLayout = QHBoxLayout()

        # Создайте виджет для значения элемента (может быть QLineEdit, QSpinBox или другой)
        elementValueWidget = None
        if self.instancer:
            elementValueWidget = self.instancer()
            if val:
                elementValueWidget.set_value(val)
        else:
            elementValueWidget = QLineEdit()
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

        def moveDown():
            index = self.arrayElements.index(elementLayout)
            if index < len(self.arrayElements) - 1:
                element = self.arrayElements.pop(index)
                self.arrayElements.insert(index + 1, element)
                self.scrollAreaLayout.takeAt(index)
                self.scrollAreaLayout.insertLayout(index + 1, elementLayout)

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

    def removeArrayElement(self, elementLayout):
        if elementLayout in self.arrayElements:
            self.arrayElements.remove(elementLayout)
            for i in reversed(range(elementLayout.count())):
                widget = elementLayout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            elementLayout.deleteLater()
        self.updateCountText()


class DictWidget(QWidget):
    def __init__(self, instancer,widVarType):
        super(DictWidget, self).__init__()
        self.instancer = instancer
        self.widVarTypeRef :QComboBox = widVarType
        self.initUI()

    def initUI(self):
        self.layout = QVBoxLayout()
        
        laydat = QHBoxLayout()
       
        self.layout.addLayout(laydat)
        laydat.addWidget(QLabel("Тип значений:"))

        self.selectType = self.widVarTypeRef.__class__()
        laydat.addWidget(self.selectType)
        for idx in range(0,self.widVarTypeRef.count()-1):
            txt = self.widVarTypeRef.itemText(idx)
            icn = self.widVarTypeRef.itemIcon(idx)
            self.selectType.addItem(icn,txt)

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

    def get_value(self):
        return [element.itemAt(0).widget().get_value() for element in self.arrayElements]

    def set_value(self, values):
        for elementLayout in self.arrayElements.copy():
            self.removeArrayElement(elementLayout)
        
        self.arrayElements.clear()
        
        for v in values:
            self.addArrayElement(val=v)

        self.updateCountText()
        return

    def addArrayElement(self,val=None):
        # Создайте горизонтальный контейнер для нового элемента
        elementLayout = QHBoxLayout()

        # Создайте виджет для значения элемента (может быть QLineEdit, QSpinBox или другой)
        elementValueWidget = None
        if self.instancer:
            elementValueWidget = self.instancer()
            if val:
                elementValueWidget.set_value(val)
        else:
            elementValueWidget = QLineEdit()
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

        def moveDown():
            index = self.arrayElements.index(elementLayout)
            if index < len(self.arrayElements) - 1:
                element = self.arrayElements.pop(index)
                self.arrayElements.insert(index + 1, element)
                self.scrollAreaLayout.takeAt(index)
                self.scrollAreaLayout.insertLayout(index + 1, elementLayout)

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

    def removeArrayElement(self, elementLayout):
        if elementLayout in self.arrayElements:
            self.arrayElements.remove(elementLayout)
            for i in reversed(range(elementLayout.count())):
                widget = elementLayout.itemAt(i).widget()
                if widget:
                    widget.deleteLater()
            elementLayout.deleteLater()
        self.updateCountText()