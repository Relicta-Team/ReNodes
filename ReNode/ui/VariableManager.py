from PyQt5 import QtGui
from PyQt5.QtWidgets import QMainWindow,QMessageBox,QAction,QCompleter,QListView,QMenu,QLabel, QDockWidget, QWidget, QHBoxLayout,QVBoxLayout, QComboBox, QLineEdit, QPushButton, QTreeWidget, QTreeWidgetItem
from PyQt5.QtCore import *
from PyQt5.QtGui import QIcon, QPixmap,QColor, QPainter

from NodeGraphQt.custom_widgets.properties_bin.custom_widget_slider import *
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_value_edit import *
from NodeGraphQt.custom_widgets.properties_bin.prop_widgets_base import *
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_color_picker import *
from NodeGraphQt.custom_widgets.properties_bin.custom_widget_vectors import *
from NodeGraphQt.base.commands import *
from ReNode.app.utils import updateIconColor, mergePixmaps, generateIconParts
from ReNode.ui.Nodes import RuntimeNode
from ReNode.ui.ArrayWidget import *
import datetime
from ReNode.app.Logger import RegisterLogger

class VariableInfo:
    def __init__(self):
        pass

class VariableTypedef:
    def __init__(self,vart="",vartText="",classMaker=None,dictProp={},color=None):
        self.variableType = vart #typename
        self.variableTextName = vartText #representation in utf-8
        self.classInstance = classMaker
        self.dictProp = dictProp
        self.color : QColor = color

        if "|" in self.variableType:
            raise Exception(f"{self.variableType} is not a valid typename; Token \"|\" is not allowed in typename")
        if "|" in self.variableTextName:
            raise Exception(f"{self.variableTextName} is not a valid textname; Token \"|\" is not allowed in textname")
    
    def __repr__(self):
        return f"{self.variableType} ({self.variableTextName})"

class VariableCategory:
    def __init__(self,varcat='',varcatText = '',varcatTextTree=''):
        self.category = varcat
        self.categoryTextName = varcatText
        self.categoryTreeTextName = varcatTextTree

class VariableDataType:
    def __init__(self,vartext='',vartype='',varicon='',instancer=None):
        self.text = vartext
        self.dataType = vartype
        self.icon = varicon #string or list of string
        self.instance = instancer
    
    def __repr__(self):
        return f"{self.dataType} ({self.text})"

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
    refObject = None
    def __init__(self,actionVarViewer = None,nodeSystem=None):
        VariableManager.refObject = self
        super().__init__("Переменные")
        self.logger = RegisterLogger("VariableManager")
        self.nodeGraphComponent = nodeSystem
        
        self.actionVarViewer = actionVarViewer
        
        #varmap: class, local
        self.variables = {}

        self.variableTempateData = [
            #base types
            VariableTypedef("int","Целое число",IntValueEdit,{"spin": {
                "text": "Число",
				"range": {"min":-999999,"max":999999}
            }},color=QtGui.QColor("Sea green")),
            VariableTypedef("float","Дробное число",FloatValueEdit,{"fspin": {
                "text": "Число",
                "range": {"min":-999999,"max":999999},
                "floatspindata": {
                    "step": 0.5,
                    "decimals": 5
                }
            }},color=QtGui.QColor("Yellow green")),
            VariableTypedef("string","Строка",PropLineEdit,{"input": {
                "text": "Текст"
            }},color=QtGui.QColor("Magenta")),
            VariableTypedef("string","Длинная строка",PropTextEdit,{"edit": {
                "text": "Текст"
            }},color=QtGui.QColor("Magenta")),
            VariableTypedef("bool","Булево",PropCheckBox,{"bool":{
                "text": "Булево"
            }},color=QtGui.QColor("Maroon")),

            #colors
            VariableTypedef("color","Цвет",PropColorPickerRGB,{"color": {
                "text": "Цвет"
            }},color=QtGui.QColor("#00C7B3")),
            VariableTypedef("color","Цвет с альфа-каналом",PropColorPickerRGBA,{"color": {
                "text": "Цвет"
            }},color=QtGui.QColor("#048C7F")),

            #vectors
            VariableTypedef("vector2","2D Вектор",PropVector2,{"vec2": {
                "text": "Вектор"
            }},color=QtGui.QColor("#D4A004")),
            VariableTypedef("vector3","3D Вектор",PropVector3,{"vec3": {
                "text": "Вектор"
            }},color=QtGui.QColor("#D48104")),
            #TODO need specwidget for use this
            # VariableTypedef("vector4","4D Вектор",PropVector4,{"vector": {
            #     "text": "Вектор"
            # }},color=QtGui.QColor("#D45B04")),

            #platform specific objects
            VariableTypedef("object","Объект",PropLineEdit
                # ,{"input": {
                #     "text": "Объект"
                #     }
                # }
            ,color=QtGui.QColor("#1087C7")),
            VariableTypedef("model","Модель",PropLineEdit
                # ,{"input": {
                # "text": "Модель"
                # }}
            ,color=QtGui.QColor("#4C4CA8")),
            VariableTypedef("handle","Дескриптор события",IntValueEdit
                # ,{"spin": {
                # "text": "Число",
				# "range": {"min":0,"max":999999}
                # }}
            ,color=QtGui.QColor("Sea green").lighter(50)),

        ]

        self.variableCategoryList = [
            VariableCategory('local',"Локальная переменная","Локальные переменные"),
            VariableCategory('class','Переменная графа',"Переменные графа")
            #TODO constants
        ]

        self.variableDataType = [
            VariableDataType("Значение","value","data\\icons\\pill_16x.png",None),
            VariableDataType("Массив","array","data\\icons\\ArrayPin.png",ArrayWidget),
            VariableDataType("Словарь","dict",["data\\icons\\pillmapkey_16x.png","data\\icons\\pillmapvalue_16x.png"],DictWidget),
            VariableDataType("Сет","set","data\\icons\\pillset_40x.png",ArrayWidget),
        ]

        self.initUI()
        self.setupContextMenu()

    def initUI(self):
        # Создайте центральный виджет для док-зоны
        central_widget = QWidget(self)
        self.setWidget(central_widget)

        # Создайте вертикальный макет для центрального виджета
        layout = QVBoxLayout()
        self.widLayout = layout

        __lbl = QLabel("Категория переменной:")
        __lbl.setToolTip("Категория переменной:\nЛокальная переменная - это переменная, создаваемая и существующая в пределах одного события\nПеременная графа - это переменная, существующая и доступная внутри этого графа")
        layout.addWidget(__lbl)
        self.widCat = QComboBox()
        for vcat in self.variableCategoryList:
            self.widCat.addItem(vcat.categoryTextName)
        self.widCat.currentIndexChanged.connect(self._onVariableCategoryChanged)
        layout.addWidget(self.widCat)


        layout.addWidget(QLabel("Тип данных:"))

        type_layout = QHBoxLayout()
        layout.addLayout(type_layout)

        self.widVarType = ExtendedComboBox()
        for vobj in self.variableTempateData:
            icon = QtGui.QIcon("data\\icons\\pill_16x.png")
            colored_icon = updateIconColor(icon, vobj.color)
            
            self.widVarType.addItem(colored_icon,vobj.variableTextName,vobj)
        self.widVarType.currentIndexChanged.connect(self._onVariableTypeChanged)
        type_layout.addWidget(self.widVarType)

        self.widDataType = QComboBox()
        for vobj in self.variableDataType:
            icn = None
            if isinstance(vobj.icon,list):
                for pat in vobj.icon:
                    icntemp = QtGui.QPixmap(pat)
                    if icn:
                        icntemp = mergePixmaps(icn,icntemp)
                    icn = icntemp
                icn = QtGui.QIcon(icn)
            else:
                icn = QtGui.QIcon(vobj.icon)
            self.widDataType.addItem(icn,vobj.text)
        self.widDataType.currentIndexChanged.connect(self._onDataTypeChanged)
        type_layout.addWidget(self.widDataType)

        __lbl = QLabel("Имя:")
        __lbl.setToolTip("Имя переменной")
        layout.addWidget(__lbl)
        self.widVarName = QLineEdit()
        self.widVarName.setMaxLength(128)
        layout.addWidget(self.widVarName)

        __lbl = QLabel("Группа:")
        __lbl.setToolTip("Имя группы для переменной (опционально)")
        layout.addWidget(__lbl)
        self.widVarGroup = QLineEdit()
        self.widVarGroup.setMaxLength(128)
        layout.addWidget(self.widVarGroup)

        __lbl = QLabel("Начальное значение:")
        __lbl.setToolTip("Значение, которое будет присвоено переменной при создании")
        layout.addWidget(__lbl)
        self.widInitVal = QLineEdit()
        layout.addWidget(self.widInitVal)
        self._initialValue = None
        self._updateVariableValueVisual(self.variableTempateData[0],self.variableDataType[0])

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
        vart : VariableTypedef = self.variableTempateData[newIndex]
        tobj : VariableDataType = self.variableDataType[self.widDataType.currentIndex()]
        self._updateVariableValueVisual(vart,tobj)
        pass

    def _onDataTypeChanged(self,*args,**kwargs):
        newIndex = args[0]
        vart = self.variableTempateData[self.widVarType.currentIndex()]
        tobj : VariableDataType = self.variableDataType[newIndex]
        self._updateVariableValueVisual(vart,tobj)

    def _updateVariableValueVisual(self,tp : VariableTypedef,dt : VariableDataType):
        isValue = dt.dataType == 'value' or not dt.instance
        #delete prev
        idx = self.widLayout.indexOf(self.widInitVal)
        self.widInitVal.deleteLater()

        objInstance = None
        if isValue:
            objInstance = tp.classInstance()
        else:
            if dt.dataType == 'dict':
                objInstance = dt.instance(tp.classInstance,self.widVarType)
            else:
                objInstance = dt.instance(tp.classInstance)
        
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
        variable_group = self.widVarGroup.text().rstrip(' ').lstrip(' ')
        
        current_category = self.widCat.currentText() # Определите, к какой категории переменных относится новая переменная (локальная или классовая)

        category_tree_name = next((obj.categoryTreeTextName for obj in self.variableCategoryList if obj.categoryTextName == current_category),None)
        if not category_tree_name:
            raise Exception("Неизвестная категория для создания переменной")
        
        cat_sys_name = next((obj.category for obj in self.variableCategoryList if obj.categoryTextName == current_category),None)
        varInfo = next((obj for obj in self.variableTempateData if obj.variableTextName == variable_type),None)

        var_typename = varInfo.variableType

        if not variable_name:
            self.showErrorMessageBox(f"Укажите имя переменной")
            return

        variable_exists = self.variableExists(cat_sys_name, variable_name)
        
        if variable_exists:
            # Выведите сообщение об ошибке
            self.showErrorMessageBox(f"Переменная с именем '{variable_name}' уже существует в категории '{category_tree_name}'!")
            return

        dt : VariableDataType = self.variableDataType[self.widDataType.currentIndex()]

        reprType = str(varInfo)

        #update 
        if isinstance(self.widInitVal,DictWidget) and dt.dataType == "dict":
            kv_valtypeTextname = self.widInitVal.selectType.currentText()
            kv_itemInfo = next((obj for obj in self.variableTempateData if obj.variableTextName == kv_valtypeTextname),None)
            var_typename += "," + kv_itemInfo.variableType
            reprType += "|" + str(kv_itemInfo)
            pass

        if dt.dataType != "value":
            var_typename = f"{dt.dataType}[{var_typename}]"
            variable_type = dt.text
        
        itm = datetime.datetime.now()
        #variableSystemName = hex(id(itm))
        variableSystemName = f'{hex(id(itm))}_{itm.year}{itm.month}{itm.day}{itm.hour}{itm.minute}{itm.second}{itm.microsecond}'


        if not self.variables.get(cat_sys_name):
            self.variables[cat_sys_name] = {}
        
        if variableSystemName in self.variables[cat_sys_name]:
            self.showErrorMessageBox(f"Коллизия системных имен переменных. Айди '{variableSystemName}' уже существует!")
            return
        
        for cat,stor in self.variables.items():
            if variableSystemName in stor:
                self.showErrorMessageBox(f"Коллизия системных имен переменных. Айди '{variableSystemName}' уже существует в другой категории - {cat}")
                return

        vardict = {
            "name": variable_name,
            "type": var_typename,
            "datatype": dt.dataType,
            "typename": variable_type,
            "value": default_value,
            "category": cat_sys_name,
            "group": variable_group,
            "systemname": variableSystemName, # никогда не должно изменяться и всегда эквивалентно ключу в категории

            "reprType": reprType,
            "reprDataType": str(dt),
        }
        self.getUndoStack().push(VariableCreatedCommand(self,cat_sys_name,vardict))


        # Очистите поля ввода
        self.widVarName.clear()
        self.widInitVal.set_value(self._initialValue)

    def getUndoStack(self) -> QUndoStack:
        return self.nodeGraphComponent.graph._undo_stack

    def setupContextMenu(self):
        # Создайте контекстное меню
        self.context_menu = QMenu(self)
        #TODO rename action, duplicate
        #self.rename_action = self.context_menu.addAction("Переименовать")
        
        self.change_group_action = self.context_menu.addAction("Изменить группу")
        self.delete_action = self.context_menu.addAction("Удалить переменную")
        self.delete_action.triggered.connect(self.deleteSelectedVariable)
        self.change_group_action.triggered.connect(self.changeSelectedVariableGroup)
        #self.rename_action.triggered.connect(self.renameSelectedVariable)
        self.variableContextActions = [
            self.change_group_action,
            self.delete_action
        ]

        self.rename_group_action = self.context_menu.addAction("Переименовать группу")
        self.rename_group_action.triggered.connect(self.renameSelectedGroup)
        self.delete_group_action = self.context_menu.addAction("Удалить группу")
        self.delete_group_action.triggered.connect(self.deleteSelectedGroup)

        self.groupContextActions = [
            self.rename_group_action,
            self.delete_group_action
        ]

        self.cancel = self.context_menu.addAction("Отмена")

        # Подключите событие customContextMenuRequested для показа контекстного меню
        self.widVarTree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.widVarTree.customContextMenuRequested.connect(self.showContextMenu)

    const_groupDataToken = "@group"

    def showContextMenu(self, pos):
        item = self.widVarTree.itemAt(pos)
        # Отображайте контекстное меню только если курсор мыши находится над элементом
        if item:
            isVariable = item.flags() & QtCore.Qt.ItemFlag.ItemIsDragEnabled
            isGroup = item.data(0,QtCore.Qt.UserRole)
            self.current_variable_item = item
            if isVariable:
                [act.setVisible(True) for act in self.variableContextActions]
                [act.setVisible(False) for act in self.groupContextActions]
                self.context_menu.exec_(QtGui.QCursor.pos())
                return
            if isGroup:
                [act.setVisible(False) for act in self.variableContextActions]
                [act.setVisible(True) for act in self.groupContextActions]
                self.context_menu.exec_(QtGui.QCursor.pos())
                return
            self.current_variable_item = None
    def deleteSelectedVariable(self):
        if hasattr(self, "current_variable_item"):
            self.deleteVariable(self.current_variable_item)
    
    def changeSelectedVariableGroup(self):
        if hasattr(self, "current_variable_item"):
            self.changeVariableGroup(self.current_variable_item)

    def renameSelectedGroup(self):
        if hasattr(self, "current_variable_item"):
            item = self.current_variable_item
            if item:
                oldName = item.text(0)
                newname,result = self.nodeGraphComponent.graph.input_dialog("Введите новое имя группы. Удалите текст для того, чтобы разгрупировать переменную",
                title="Изменение группы переменных", deftext=oldName)
                if not result: return
                newname = newname.rstrip(' ').lstrip(' ')
                if oldName == newname: return
                hstack = self.getUndoStack()
                if item.childCount()==0:
                    self.showErrorMessageBox("Невозможно изменить название группы '{}' - список элементов пуст".format(oldName))
                    return
                variable_system_name = item.child(0).data(0,QtCore.Qt.UserRole)
                vardata = self.getVariableDataById(variable_system_name)
                if not vardata: raise Exception(f"Cant find variable by system name for rename group: {variable_system_name}")
                cat = vardata['category']
                hstack.push(ChangeGroupNameForVariables(self,cat,oldName,newname))

    def deleteSelectedGroup(self):
        if hasattr(self,"current_variable_item"):
            item = self.current_variable_item
            if item:
                groupname = item.text(0)
                result = self.nodeGraphComponent.graph.question_dialog(
                    f"Вы уверены, что хотите удалить группу '{groupname}'?\nВсе переменные из этой группы будут удалены.",
                    "Удаление группы")
                if result:
                    hstack = self.getUndoStack()

                    if item.childCount()==0:
                        self.showErrorMessageBox("Невозможно удалить группу '{}' - список элементов пуст".format(groupname))
                        return
                    variable_system_name = item.child(0).data(0,QtCore.Qt.UserRole)
                    vardata = self.getVariableDataById(variable_system_name)
                    if not vardata: raise Exception(f"Cant find variable by system name for delete group: {variable_system_name}")
                    cat = vardata['category']

                    hstack.beginMacro(f"Удаление группы '{groupname}'")

                    cmd = DeleteGroupForVariables(self,cat,groupname)
                    cmd.deleteVariableInGraph()
                    hstack.push(cmd)

                    hstack.endMacro()


    def renameSelectedVariable(self):
        if hasattr(self, "current_variable_item"):
            #self.widVarTree.editItem(self.current_variable_item,0)
            from PyQt5.QtWidgets import QInputDialog
            text, ok = QInputDialog.getText(self.widVarTree, 'Ввод текста', 'Введите что-нибудь:',
                flags=QtCore.Qt.WindowType.FramelessWindowHint | QtCore.Qt.WindowType.Popup)
            if ok:
                # Выводим введенный текст
                print('Вы ввели:', text)

    def changeVariableGroup(self, item):
        if item:
            variable_system_name = item.data(0, Qt.UserRole)
            
            # Получите категорию переменной из имени элемента
            vardata = self.getVariableDataById(variable_system_name)
            if not vardata: raise Exception(f"Cant find variable by system name: {variable_system_name}")

            oldname = vardata.get('group',"")            
            newname,result = self.nodeGraphComponent.graph.input_dialog("Введите новое имя группы. Удалите текст для того, чтобы разгрупировать переменную",
                title="Изменение группы переменной", deftext=oldname)

            if not result: return
            newname = newname.rstrip(' ').lstrip(' ')
            if oldname == newname: return

            hstack = self.getUndoStack()
            hstack.push(VariableChangePropertyCommand(self,vardata['category'],variable_system_name,'group',newname,""))

    def deleteVariable(self, item):
        if item:
            # Получите системное имя переменной, хранящееся в данных элемента
            variable_system_name = item.data(0, Qt.UserRole)
            
            # Получите категорию переменной из имени элемента
            vardata = self.getVariableDataById(variable_system_name)
            if not vardata: raise Exception(f"Cant find variable by system name: {variable_system_name}")
            category = vardata['category']
            hstack = self.getUndoStack()

            canDeleteVariable =  category in self.variables and variable_system_name in self.variables[category]
            if not canDeleteVariable:
                self.showErrorMessageBox(f"Невозможно удалить несуществующую переменную {vardata['name']} из категории {category}")
                return

            hstack.beginMacro(f"Удаление переменной {vardata['name']}")
            # Удаляем переменную из графа
            graph = self.nodeGraphComponent.graph
            allnodes = graph.get_nodes_by_class(None)
            for node in allnodes:
                if node.has_property('nameid'):
                    if node.get_property('nameid') == variable_system_name:
                        graph.delete_node(node,True) #push undo for history

            hstack.push(VariableDeletedCommand(self,category,self.variables[category][variable_system_name]))

            hstack.endMacro()

    def _updateNode(self,nodeObj:RuntimeNode,id,getorset):
        from ReNode.app.NodeFactory import NodeFactory
        lvdata = self.getVariableDataById(id)
        if not lvdata:
            raise Exception("Unknown variable id "+id)
        #varInfo = self.getVariableTypedefByType(lvdata['typename'],True)
        varInfo,varDt = self._getVarDataByRepr(lvdata['reprType'],lvdata['reprDataType'])
        
        _class = nodeObj.nodeClass
        fact : NodeFactory = self.nodeGraphComponent.getFactory()
        cfg = fact.getNodeLibData(_class)
        nodeObj.set_property('name',f'{cfg["name"].format("<b>"+lvdata["name"]+"</b>")}',False,
            doNotRename=True)
        nodeObj.set_property('nameid',id,False)

        portColor = None

        #setup partial icon with color support
        kvdat = []
        if isinstance(varInfo,list):
            for i,varInfoElement in enumerate(varInfo):
                if i==0:
                    portColor = [*varInfoElement.color.getRgb()]
                kvdat.append(varDt.icon[i])
                kvdat.append(varInfoElement.color)
        else:
            kvdat = [varDt.icon,varInfo.color]
            portColor = [*varInfo.color.getRgb()]
        nodeObj.update_icon_parts(kvdat,False)

        code = ""
        inval = "@in.2"
        
        self.logger.warning("TODO: remove obsolete option 'code' from variable accessors")
        if lvdata['category']=='local':
            code = f"{lvdata['systemname']}" if getorset == "get" else f"{lvdata['systemname']} = {inval}; @out.1"
        elif lvdata['category']=='class':
            code = f"this getVariable \"{lvdata['systemname']}\"" if getorset == "get" else f"this setVariable [\"{lvdata['systemname']}\",{inval}]; @out.1"
        else:
            raise Exception(f"Unknown category {lvdata['category']}")
        
        nodeObj.set_property('code',code,False)

        if "set" == getorset and varDt.dataType == 'value':
            props = varInfo.dictProp
            for k,v in props.items():
                fact.addProperty(nodeObj,k,lvdata['name'],v)

        vardict = None
        realType = lvdata['type']
        if "set" == getorset:
            vardict = {
                "type":realType, #varInfo.variableType
                "allowtypes":[realType],
                #"color":[255,0,0,255],
                "color": portColor,
                "display_name":True,
                "mutliconnect":False,
                "style":None,
            }
            fact.addInput(nodeObj,lvdata['name'],vardict)

            #Adding output with multiconnect
            vardict = vardict.copy()
            vardict["mutliconnect"] = True
            fact.addOutput(nodeObj,lvdata['name'],vardict)
        else:
            vardict = {
                "type":realType,
                "allowtypes":[realType],
                #"color":[255,0,0,255],
                "color": portColor,
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
    
    def _getVarDataByRepr(self,vartRepr,vardtRepr):
        reprVar = None
        if "|" in vartRepr:
            searcher = vartRepr.split("|")
            listRet = []
            for search_pattern in searcher:
                listRet.append(next((obj for obj in self.variableTempateData if str(obj) == search_pattern),None))
            reprVar = listRet
        else:
            reprVar = next((obj for obj in self.variableTempateData if str(obj) == vartRepr),None)
        reprDt = next((obj for obj in self.variableDataType if str(obj) == vardtRepr),None)

        return reprVar,reprDt

    def syncVariableManagerWidget(self):
        self.loadVariables(self.variables,False)

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

        dictGroup = {} # key: group name, value: groupwidget

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
                group = variable_data.get('group',"")
                defvalstr = str(value) if not isinstance(value, str) else value

                varInfo, dt = self._getVarDataByRepr(variable_data['reprType'],variable_data['reprDataType'])
                if not varInfo or not dt:
                    raise Exception(f"Невозможно загрузить переменную {variable_id}; Информация и данные о типе: {varInfo}; {dt}")

                if dt.dataType != "value":
                    if isinstance(varInfo,list):
                        variable_type = f'{variable_type} ({", ".join([o__.variableTextName for o__ in varInfo])})'
                    else:
                        variable_type = f'{variable_type} ({varInfo.variableTextName})'

                item = QTreeWidgetItem([name, variable_type, defvalstr])
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
                item.setData(0, QtCore.Qt.UserRole, variable_id)

                if isinstance(varInfo,list):
                    pathes = dt.icon
                    colors = [o__.color for o__ in varInfo]
                    item.setIcon(1,QtGui.QIcon(generateIconParts(pathes,colors)))
                else:
                    icn = QtGui.QIcon(dt.icon)
                    icn = updateIconColor(icn,varInfo.color)
                    item.setIcon(1, icn)

                if group == "":
                    category_item.addChild(item)
                else:
                    if group not in dictGroup:
                        group_item = QTreeWidgetItem([group])
                        group_item.setFlags(group_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsDragEnabled)
                        group_item.setData(0, QtCore.Qt.UserRole, VariableManager.const_groupDataToken)
                        category_item.addChild(group_item)
                        dictGroup[group] = group_item
                    dictGroup[group].addChild(item)
                    
        
        del dictGroup
        self.widVarTree.expandAll()