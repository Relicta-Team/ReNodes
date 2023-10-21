from PyQt5.QtWidgets import QMainWindow,QLabel, QDockWidget, QWidget, QVBoxLayout, QComboBox, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import *

from NodeGraphQt.custom_widgets.properties_bin.custom_widget_slider import *
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_value_edit import *
from NodeGraphQt.custom_widgets.properties_bin.prop_widgets_base import *


class VariableInfo:
    def __init__(self):
        pass

class VariableTypedef:
    def __init__(self,vart="",vartText="",classMaker=None):
        self.variableType = vart #typename
        self.variableTextName = vartText #representation in utf-8
        self.classInstance = classMaker
    
    def __repr__(self):
        return f"{self.variableType} ({self.variableTextName})"

class VariableManager(QDockWidget):
    def __init__(self,actionVarViewer = None):
        
        super().__init__("Variables")

        self.actionVarViewer = actionVarViewer
        
        self.localVariables = {}
        self.classVariables = {}
        
        self.variableTempateData = [
            VariableTypedef("int","Целое число",IntValueEdit),
            VariableTypedef("float","Дробное число",FloatValueEdit),
            VariableTypedef("string","Строка",PropTextEdit)
        ]

        self.initUI()
        
    def syncActionText(self,initState=None):
        condition = self.isVisible()
        if initState:
            condition = initState
        newtext = "&Скрыть окно переменных" if condition else "&Показать окно переменных"
        self.actionVarViewer.setText(newtext)

    def initUI(self):
        # Создайте центральный виджет для док-зоны
        central_widget = QWidget(self)
        self.setWidget(central_widget)

        # Создайте вертикальный макет для центрального виджета
        layout = QVBoxLayout()
        self.widLayout = layout

        layout.addWidget(QLabel("Тип переменной:"))
        self.widVarType = QComboBox()
        for vobj in self.variableTempateData:
            self.widVarType.addItem(vobj.variableTextName,vobj)
        self.widVarType.currentIndexChanged.connect(self._onVariableTypeChanged)
        
        layout.addWidget(self.widVarType)

        layout.addWidget(QLabel("Имя переменной:"))
        self.widVarName = QLineEdit()
        layout.addWidget(self.widVarName)

        layout.addWidget(QLabel("Начальное значение:"))
        self.widInitVal = QLineEdit()
        layout.addWidget(self.widInitVal)

        # Кнопка создания переменной
        self.widCreateVar = QPushButton("Создать")
        self.widCreateVar.setMinimumWidth(200)
        self.widCreateVar.setMinimumHeight(40)
        self.widCreateVar.clicked.connect(self.createVariable)
        layout.addWidget(self.widCreateVar,alignment=Qt.AlignmentFlag.AlignCenter)

        # Дерево для отображения списка переменных
        self.widVarTree = QTreeWidget()
        self.widVarTree.setHeaderLabels(["Name", "Type", "Default Value"])
        layout.addWidget(self.widVarTree)

        central_widget.setLayout(layout)

    def _onVariableTypeChanged(self, *args, **kwargs):
        newIndex = args[0]
        varobj = self.variableTempateData[newIndex]
        print(f"New variable type is {varobj}")
        pass

    def createVariable(self):
        # Получите значения типа переменной, имени и дефолтного значения
        variable_type = self.widVarType.currentText()
        variable_name = self.widVarName.text()
        default_value = self.widInitVal.text()

        # Создайте новый элемент дерева для переменной и добавьте его в дерево
        item = QTreeWidgetItem([variable_name, variable_type, default_value])
        self.widVarTree.addTopLevelItem(item)


