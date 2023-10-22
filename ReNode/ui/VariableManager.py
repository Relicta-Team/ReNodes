from PyQt5 import QtGui
from PyQt5.QtWidgets import QMainWindow,QMessageBox,QCompleter,QListView,QLabel, QDockWidget, QWidget, QVBoxLayout, QComboBox, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem
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

class VariableCategory:
    def __init__(self,varcat='',varcatText = '',varcatTextTree=''):
        self.category = varcat
        self.categoryTextName = varcatText
        self.categoryTreeTextName = varcatTextTree

class ExtendedComboBox(QComboBox):
    def __init__(self, parent=None):
        super(ExtendedComboBox, self).__init__(parent)

        self.setFocusPolicy(Qt.StrongFocus)
        self.setEditable(True)

        # add a filter model to filter matching items
        self.pFilterModel = QSortFilterProxyModel(self)
        self.pFilterModel.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.pFilterModel.setSourceModel(self.model())

        # add a completer, which uses the filter model
        self.completer = QCompleter(self.pFilterModel, self)
        # always show all (filtered) completions
        self.completer.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.setCompleter(self.completer)

        # connect signals
        self.lineEdit().textEdited.connect(self.pFilterModel.setFilterFixedString)
        self.completer.activated.connect(self.on_completer_activated)
        self.currentIndexChanged.connect(self._onCurIndChanged)

        self.lastIndex = -1

    def _onCurIndChanged(self,*args,**kwargs):
        self.lastIndex = args[0]

    def focusInEvent(self, e) -> None:
        self.lastIndex = self.currentIndex()
        return super().focusInEvent(e)

    def focusOutEvent(self, e) -> None:
        idx = self.findText(self.lineEdit().text())
        if idx >= 0:
            self.setCurrentIndex(idx)
        else:
            self.setCurrentIndex(self.lastIndex)
        return super().focusOutEvent(e)

    # on selection of an item from the completer, select the corresponding item from combobox 
    def on_completer_activated(self, text):
        if text:
            index = self.findText(text)
            self.setCurrentIndex(index)
            self.activated[str].emit(self.itemText(index))


    # on model change, update the models of the filter and completer as well 
    def setModel(self, model):
        super(ExtendedComboBox, self).setModel(model)
        self.pFilterModel.setSourceModel(model)
        self.completer.setModel(self.pFilterModel)


    # on model column change, update the model column of the filter and completer as well
    def setModelColumn(self, column):
        self.completer.setCompletionColumn(column)
        self.pFilterModel.setFilterKeyColumn(column)
        super(ExtendedComboBox, self).setModelColumn(column)   

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

        self.variableCategoryList = [
            VariableCategory('localvariable',"Локальная переменная","Локальные переменные"),
            VariableCategory('classvariable','Переменная графа',"Переменные графа")
            #TODO constants
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

        layout.addWidget(QLabel("Категория переменной:"))
        self.widCat = QComboBox()
        for vcat in self.variableCategoryList:
            self.widCat.addItem(vcat.categoryTextName)
        self.widCat.currentIndexChanged.connect(self._onVariableCategoryChanged)
        layout.addWidget(self.widCat)
        # self.widCat.setEditable(True)
        # self.widCat.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        # # change completion mode of the default completer from InlineCompletion to PopupCompletion
        # self.widCat.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)

        layout.addWidget(QLabel("Тип данных:"))
        self.widVarType = ExtendedComboBox()
        for vobj in self.variableTempateData:
            self.widVarType.addItem(vobj.variableTextName,vobj)
        self.widVarType.currentIndexChanged.connect(self._onVariableTypeChanged)
        layout.addWidget(self.widVarType)

        layout.addWidget(QLabel("Имя:"))
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
        self.widVarTree.setHeaderLabels(["Имя", "Тип", "Значение"])
        self.widVarTree.setColumnWidth(0,self.widVarTree.columnWidth(0)*2)
        layout.addWidget(self.widVarTree)

        central_widget.setLayout(layout)
    
    def _onVariableTypeChanged(self, *args, **kwargs):
        newIndex = args[0]
        varobj = self.variableTempateData[newIndex]
        print(f"New variable type is {varobj}")
        pass

    def _onVariableCategoryChanged(self, *args, **kwargs):
        newIndex = args[0]
        pass

    def variableExists(self, category, name):
        # Проверка наличия переменной с заданным именем в выбранной категории
        category_item = self.widVarTree.findItems(category, Qt.MatchExactly)
        if category_item:
            category_item = category_item[0]
            for row in range(category_item.childCount()):
                item = category_item.child(row)
                if item.text(0) == name:
                    return True
        return False

    def showErrorMessageBox(self, message):
        # Отобразите сообщение об ошибке в диалоговом окне
        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Critical)
        msg_box.setText(message)
        msg_box.setWindowTitle("Ошибка")
        msg_box.exec_()

    def createVariable(self):
        # Получите значения типа переменной, имени и дефолтного значения
        variable_type = self.widVarType.currentText()
        variable_name = self.widVarName.text()
        default_value = self.widInitVal.text()
        current_category = self.widCat.currentText() # Определите, к какой категории переменных относится новая переменная (локальная или классовая)

        category_tree_name = next((obj.categoryTreeTextName for obj in self.variableCategoryList if obj.categoryTextName == current_category),None)
        if not category_tree_name:
            raise Exception("Неизвестная категория для создания переменной")
        

        variable_exists = self.variableExists(category_tree_name, variable_name)
        
        if variable_exists:
            # Выведите сообщение об ошибке
            self.showErrorMessageBox(f"Переменная с именем '{variable_name}' уже существует в категории '{category_tree_name}'!")
            return

        # Создайте новый элемент дерева для переменной и добавьте его в дерево
        item = QTreeWidgetItem([variable_name, variable_type, default_value])

        itmsTree = self.widVarTree.findItems(category_tree_name,Qt.MatchExactly)
        if itmsTree:
            itmsTree[0].addChild(item)
        else:
            itmsTree = QTreeWidgetItem([category_tree_name])
            self.widVarTree.addTopLevelItem(itmsTree)
            itmsTree.addChild(item)

        # Очистите поля ввода
        self.widVarName.clear()
        self.widInitVal.clear()
