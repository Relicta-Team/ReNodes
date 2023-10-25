from PyQt5 import QtGui
from PyQt5.QtWidgets import QMainWindow,QMessageBox,QAction,QCompleter,QListView,QMenu,QLabel, QDockWidget, QWidget, QVBoxLayout, QComboBox, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import *

from NodeGraphQt.custom_widgets.properties_bin.custom_widget_slider import *
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_value_edit import *
from NodeGraphQt.custom_widgets.properties_bin.prop_widgets_base import *
from ReNode.ui.Nodes import RuntimeNode
from ReNode.ui.ArrayWidget import ArrayWidget

class VariableInfo:
    def __init__(self):
        pass

class VariableTypedef:
    def __init__(self,vart="",vartText="",classMaker=None,dictProp={},widParam=None):
        self.variableType = vart #typename
        self.variableTextName = vartText #representation in utf-8
        self.classInstance = classMaker
        self.dictProp = dictProp
        self.classInstanceParam = widParam
    
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
    def __init__(self,actionVarViewer = None,nodeSystem=None):
        
        super().__init__("Переменные")
        self.nodeGraphComponent = nodeSystem
        
        self.actionVarViewer = actionVarViewer
        
        #varmap: class, local
        self.variables = {}

        self.variableTempateData = [
            VariableTypedef("int","Целое число",IntValueEdit,{"spin": {
                "text": "Число",
				"range": {"min":-999999,"max":99999}
            }}),
            VariableTypedef("float","Дробное число",FloatValueEdit,{"fspin": {
                "text": "Число",
                "range": {"min":-999999,"max":999999},
                "floatspindata": {
                    "step": 0.5,
                    "decimals": 5
                }
            }}),
            VariableTypedef("string","Строка",PropLineEdit,{"input": {
                "text": "Текст"
            }}),
            VariableTypedef("string","Длинная строка",PropTextEdit,{"edit": {
                "text": "Текст"
            }}),
            VariableTypedef("bool","Булево",PropCheckBox,{"bool":{
                "text": "Булево"
            }})
        ]

        for vobj in self.variableTempateData.copy():
            self.variableTempateData.append(VariableTypedef(
                f"array[{vobj.variableType}]",
                f"Массив {vobj.variableTextName}"
                ,ArrayWidget,vobj.dictProp,
                widParam=vobj.classInstance)
            )

        self.variableCategoryList = [
            VariableCategory('local',"Локальная переменная","Локальные переменные"),
            VariableCategory('class','Переменная графа',"Переменные графа")
            #TODO constants
        ]

        self.initUI()
        self.setupContextMenu()
        
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

        layout.addWidget(QLabel("Тип данных:"))
        self.widVarType = ExtendedComboBox()
        for vobj in self.variableTempateData:
            self.widVarType.addItem(vobj.variableTextName,vobj)
        self.widVarType.currentIndexChanged.connect(self._onVariableTypeChanged)
        layout.addWidget(self.widVarType)

        layout.addWidget(QLabel("Имя:"))
        self.widVarName = QLineEdit()
        self.widVarName.setMaxLength(128)
        layout.addWidget(self.widVarName)

        layout.addWidget(QLabel("Начальное значение:"))
        self.widInitVal = QLineEdit()
        layout.addWidget(self.widInitVal)
        self._initialValue = None
        self._onVariableTypeChanged((0))

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
        self.widVarTree.setDragEnabled(True)
        self.widVarTree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.widVarTree.setObjectName("VariableManager.tree")
        self.widVarTree.setSortingEnabled(True)  # Включите сортировку
        self.widVarTree.sortItems(0, Qt.AscendingOrder)  # Сортировка по первому столбцу (индекс 0) в порядке возрастания
        

        central_widget.setLayout(layout)
    
    def _onVariableTypeChanged(self, *args, **kwargs):
        newIndex = args[0]
        varobj : VariableTypedef = self.variableTempateData[newIndex]
        typeInstance = varobj.classInstance
        #print(f"New variable type is {varobj}")
        idx = self.widLayout.indexOf(self.widInitVal)
        self.widInitVal.deleteLater()
        objInstance = None
        if varobj.classInstanceParam:
            objInstance = typeInstance(varobj.classInstanceParam)
        else:
            objInstance = typeInstance()
        self.widInitVal = objInstance
        self.widLayout.insertWidget(idx,self.widInitVal)
        self._initialValue = self.widInitVal.get_value()
        pass

    def _onVariableCategoryChanged(self, *args, **kwargs):
        newIndex = args[0]
        pass

    def variableExists(self, category, name):
        # Проверка наличия переменной с заданным именем в выбранной категории
        for varInfo in self.variables.get(category,{}).values():
            if varInfo['name'] == name: return True
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
        variable_name = self.widVarName.text().rstrip(' ').lstrip(' ')
        default_value = self.widInitVal.get_value()
        
        current_category = self.widCat.currentText() # Определите, к какой категории переменных относится новая переменная (локальная или классовая)

        category_tree_name = next((obj.categoryTreeTextName for obj in self.variableCategoryList if obj.categoryTextName == current_category),None)
        if not category_tree_name:
            raise Exception("Неизвестная категория для создания переменной")
        
        cat_sys_name = next((obj.category for obj in self.variableCategoryList if obj.categoryTextName == current_category),None)
        var_typename = next((obj.variableType for obj in self.variableTempateData if obj.variableTextName == variable_type),None)

        if not variable_name:
            self.showErrorMessageBox(f"Укажите имя переменной")
            return

        variable_exists = self.variableExists(cat_sys_name, variable_name)
        
        if variable_exists:
            # Выведите сообщение об ошибке
            self.showErrorMessageBox(f"Переменная с именем '{variable_name}' уже существует в категории '{category_tree_name}'!")
            return

        # Создайте новый элемент дерева для переменной и добавьте его в дерево
        defvalstr = str(default_value) if not isinstance(default_value,str) else default_value
        item = QTreeWidgetItem([variable_name, variable_type, defvalstr])
        item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
        variableSystemName = hex(id(item))
        item.setData(0, QtCore.Qt.UserRole, variableSystemName)

        itmsTree = self.widVarTree.findItems(category_tree_name,Qt.MatchExactly)
        if itmsTree:
            itmsTree[0].addChild(item)
        else:
            itmsTree = QTreeWidgetItem([category_tree_name])
            itmsTree.setFlags(itmsTree.flags() & ~QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.widVarTree.addTopLevelItem(itmsTree)
            itmsTree.addChild(item)

        if not self.variables.get(cat_sys_name):
            self.variables[cat_sys_name] = {}
        self.variables[cat_sys_name][variableSystemName] = {
            "name": variable_name,
            "type": var_typename,
            "typename": variable_type,
            "value": default_value,
            "category": cat_sys_name,
            "systemname": variableSystemName
        }

        # Очистите поля ввода
        self.widVarName.clear()
        self.widInitVal.set_value(self._initialValue)

    def setupContextMenu(self):
        # Создайте контекстное меню
        self.context_menu = QMenu(self)
        #TODO rename action
        #self.rename_action = self.context_menu.addAction("Переименовать")
        self.delete_action = self.context_menu.addAction("Удалить переменную")
        self.cancel = self.context_menu.addAction("Отмена")
        self.delete_action.triggered.connect(self.deleteSelectedVariable)
        #self.rename_action.triggered.connect(self.renameSelectedVariable)

        # Подключите событие customContextMenuRequested для показа контекстного меню
        self.widVarTree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.widVarTree.customContextMenuRequested.connect(self.showContextMenu)

    def showContextMenu(self, pos):
        item = self.widVarTree.itemAt(pos)
        # Отображайте контекстное меню только если курсор мыши находится над элементом
        if item:
            if item.childCount() > 0:
                # Это категория (ветка), не отображаем контекстное меню
                return
            self.current_variable_item = item
            self.context_menu.exec_(QtGui.QCursor.pos())

    def deleteSelectedVariable(self):
        if hasattr(self, "current_variable_item"):
            self.deleteVariable(self.current_variable_item)
            self.syncActionText()
    
    def renameSelectedVariable(self):
        if hasattr(self, "current_variable_item"):
            #self.widVarTree.editItem(self.current_variable_item,0)
            from PyQt5.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self.widVarTree, 'Ввод текста', 'Введите что-нибудь:',
                flags=QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Popup)
            if ok:
                # Выводим введенный текст
                print('Вы ввели:', text)

    def deleteVariable(self, item):
        if item:
            # Получите системное имя переменной, хранящееся в данных элемента
            variable_system_name = item.data(0, Qt.UserRole)
            
            # Получите категорию переменной из имени элемента
            vardata = self.getVariableDataById(variable_system_name)
            if not vardata: raise Exception(f"Cant find variable by system name: {variable_system_name}")
            category = vardata['category']
            
            # Удаляем переменную из графа
            graph = self.nodeGraphComponent.graph
            allnodes = graph.get_nodes_by_class(None)
            for node in allnodes:
                if node.has_property('nameid'):
                    if node.get_property('nameid') == variable_system_name:
                        graph.delete_node(node,False)

            # Удалите переменную из дерева
            parent = item.parent() if item.parent() else self.widVarTree
            parent.removeChild(item)

            # Удалите переменную из словаря переменных
            if category in self.variables and variable_system_name in self.variables[category]:
                del self.variables[category][variable_system_name]

            if parent.childCount() == 0:
                # Если у родительского элемента больше нет детей, удаляем его
                parent_index = self.widVarTree.indexOfTopLevelItem(parent)
                if parent_index >= 0:
                    self.widVarTree.takeTopLevelItem(parent_index)
                    # Удалите категорию из словаря переменных, если она пуста
                    if category in self.variables:
                        del self.variables[category]

    def _updateNode(self,nodeObj:RuntimeNode,id,getorset):
        from ReNode.app.NodeFactory import NodeFactory
        lvdata = self.getVariableDataById(id)
        if not lvdata:
            raise Exception("Unknown variable id "+id)
        vartypedata = self.getVariableTypedefByType(lvdata['typename'],True)

        _class = nodeObj.nodeClass
        fact : NodeFactory = self.nodeGraphComponent.getFactory()
        cfg = fact.getNodeLibData(_class)
        nodeObj.set_property('name',f'<span style=\'font-family: Arial; font-size: 11pt;\'><b>{cfg["name"].format(lvdata["name"])}</b></span>',False,
            doNotRename=True)
        nodeObj.set_property('nameid',id)

        code = ""
        inval = "@in.2"
        
        if lvdata['category']=='local':
            code = f"{lvdata['systemname']}" if getorset == "get" else f"{lvdata['systemname']} = {inval}; @out.1"
        elif lvdata['category']=='class':
            code = f"this getVariable \"{lvdata['systemname']}\"" if getorset == "get" else f"this setVariable [\"{lvdata['systemname']}\",{inval}]; @out.1"
        else:
            raise Exception(f"Unknown category {lvdata['category']}")
        
        nodeObj.set_property('code',code)

        if "set" == getorset:
            props = vartypedata.dictProp
            for k,v in props.items():
                fact.addProperty(nodeObj,k,lvdata['name'],v)

        vardict = None
        if "set" == getorset:
            vardict = {
                "type":vartypedata.variableType,
                "allowtypes":[vartypedata.variableType],
                "color":[
                    255,
                    255,
                    255,
                    255
                ],
                "display_name":True,
                "mutliconnect":False,
                "style":None,
            }
            fact.addInput(nodeObj,lvdata['name'],vardict)
        else:
            vardict = {
                "type":vartypedata.variableType,
                "allowtypes":[vartypedata.variableType],
                "color":[
                    255,
                    255,
                    255,
                    255
                ],
                "display_name":True,
                "mutliconnect":False,
                "style":None,
            }
            fact.addOutput(nodeObj,"Значение",vardict)

        nodeObj.update()
        pass

    def getVariableDataById(self,id) -> None | dict:
        for cat in self.variables.values():
            for k,v in cat.items():
                if k == id: return v
        return None
    
    def getVariableTypedefByType(self,type,useTextTypename=False) -> None | VariableTypedef:
        for vobj in self.variableTempateData:
           if useTextTypename and vobj.variableTextName == type: return vobj
           if vobj.variableType == type: return vobj 
        return None
    
    def loadVariables(self, dictData,clearPrevDict = False):
        # Очистите существующие переменные из self.variables и дерева
        self.clearVariables(doCleanupVars = clearPrevDict)

        # Обновите self.variables с данными из dictData
        def deep_update(d, u):
            for k, v in u.items():
                if isinstance(v, dict):
                    d[k] = deep_update(d.get(k, {}), v)
                else:
                    d[k] = v
            return d
        deep_update(self.variables, dictData)
        #self.variables.update(dictData)

        # Пересоздайте переменные в дереве
        self.populateVariableTree()

    def clearVariables(self,doCleanupVars=False):
        # Очистите все переменные из self.variables
        if doCleanupVars:
            self.variables.clear()

        # Очистите все элементы дерева
        self.widVarTree.clear()

    def populateVariableTree(self):
        # Пересоздайте переменные в дереве на основе данных в self.variables
        for category, variables in self.variables.items():
            category_tree_name = next((obj.categoryTreeTextName for obj in self.variableCategoryList if obj.category == category),None)
            if not category_tree_name:
                raise Exception("Неизвестная категория для создания переменной")
            category_item = QTreeWidgetItem([category_tree_name])
            category_item.setFlags(category_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.widVarTree.addTopLevelItem(category_item)

           

            for variable_id, variable_data in variables.items():
                name = variable_data['name']
                variable_type = variable_data['typename']
                value = variable_data['value']
                defvalstr = str(value) if not isinstance(value, str) else value

                item = QTreeWidgetItem([name, variable_type, defvalstr])
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
                item.setData(0, QtCore.Qt.UserRole, variable_id)
                category_item.addChild(item)