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
from ReNode.ui.SearchMenuWidget import SearchComboButton,addTreeContent,createTreeDataContent,addTreeContentItem
from ReNode.ui.VarMgrWidgetTypes.Widgets import *
import datetime
from ReNode.app.Logger import RegisterLogger
import re
import enum

class MemberType(enum.Enum):
    """Тип члена отражает какие данные можно вводить в менеджере переменных"""
    Unknown = -1
    """Неизвестный тип члена"""
    Variable = 0,
    """Переменная хранится в классе, имеет тип данных и значение"""
    Function = 1
    """Функция хранится в классе, имеет параметры и возвращаемое значение"""

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

    def copy(self,newtype=''):
        vtype = newtype or self.variableType
        vtextname = self.variableTextName
        vMgr = VariableManager.refObject
        if vMgr.isObjectType(vtype):
            vtextname = vMgr.getObjectTypeName(vtype)
        return VariableTypedef_Copy(vtype,vtextname,self.classInstance,self.dictProp,self.color)

class VariableTypedef_Copy(VariableTypedef):
    def __init__(self,vart="",vartText="",classMaker=None,dictProp={},color=None):
        super().__init__(vart,vartText,classMaker,dictProp,color)

    #def __del__(self):
    #    print(f'!!!!!!!!!!!! temp variable deleted: {self}')

class VariableCategory:
    def __init__(self,memtype:MemberType,varcat='',varcatText = '',varcatTextTree='',vardesc=''):
        self.category = varcat
        self.categoryTextName = varcatText
        self.categoryTreeTextName = varcatTextTree
        self.categoryDescription = vardesc
        self.memtype = memtype
        
        inst = None
        if self.memtype == MemberType.Unknown:
            inst = VarMgrBaseWidgetType
        elif self.memtype == MemberType.Variable:
            inst = VarMgrVariableWidget
        elif self.memtype == MemberType.Function:
            inst = VarMgrFunctionWidget
        else:
            raise Exception(f"Unknown member type: {self.memtype.name}")
        
        self.instancer = inst

class VariableDataType:
    def __init__(self,vartext='',vartype='',varicon='',instancer=None):
        self.text = vartext
        self.dataType = vartype
        self.icon = varicon #string or list of string
        self.instance = instancer
    
    def __repr__(self):
        return f"{self.dataType} ({self.text})"

class VariableLibrary:
    def __init__(self):
        self.typeList = [
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
            # VariableTypedef("string","Строка",PropLineEdit,{"input": {
            #     "text": "Текст"
            # }},color=QtGui.QColor("Magenta")),
            VariableTypedef("string","Строка",PropTextEdit,{"edit": {
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
            VariableTypedef("object","Объект",PropObject
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

        self.valueTypeList = [
            VariableDataType("Значение","value","data\\icons\\pill_16x.png",None),
            VariableDataType("Массив","array","data\\icons\\ArrayPin.png",ArrayWidget),
            VariableDataType("Словарь","dict",["data\\icons\\pillmapkey_16x.png","data\\icons\\pillmapvalue_16x.png"],DictWidget),
            VariableDataType("Сет","set","data\\icons\\pillset_40x.png",ArrayWidget),
        ]

    def getTypeIcon(self,typ:str,colorize=False):
        valueType = "value"
        compareType = typ
        if typ.startswith("array") or typ.startswith("set") or typ.startswith("dict"):
            vdat = re.findall('\w+\^?',compareType)
            valueType = vdat[0]
            compareType = [vdat[1],vdat[2]]
        
        icon = None
        for vdt in self.valueTypeList:
            if vdt.dataType == valueType:
                icon = vdt.icon
                break
        if not icon: return None

        if not colorize: return icon

        if not isinstance(icon,list): icon = [icon]
        if not isinstance(compareType,list): compareType = [compareType]
        colorList = []

        for comptype in compareType:
            for t in self.typeList:
                if t.variableType == comptype:
                    colorList.append(t.color.name())

        return [icon,colorList]

class VariableManager(QDockWidget):
    refObject = None
    def __init__(self,actionVarViewer = None,nodeSystem=None):
        VariableManager.refObject = self
        super().__init__("Менеджер пользовательских свойств")
        
        self.logger = RegisterLogger("VariableManager")
        self.nodeGraphComponent = nodeSystem
        
        self.actionVarViewer = actionVarViewer
        
        #varmap: class, local
        self.variables = {}
        self._typeData = VariableLibrary()

        self.variableTempateData = self._typeData.typeList

        self.variableCategoryList = [
            #class specific vars
            VariableCategory(MemberType.Variable,'localvar',"Локальная переменная","Локальные переменные","Локальная переменная - это переменная, создаваемая и существующая в пределах одного события или функции. Используются для записи и хранения временных данных."),
            VariableCategory(MemberType.Variable,'classvar','Переменная класса',"Переменные класса","Переменная класса - это переменная, принадлежащая созданному объекту. (прим. Человек имеет переменную 'Имя', 'Возраст')"),
            VariableCategory(MemberType.Function,'classfunc',"Функция класса","Функции класса","Функции класса - это функция, принадлежащая созданному объекту. (прим. Человек имеет функцию класса 'Проснуться', 'Поднять бровь')"),

            #constant
            VariableCategory(MemberType.Unknown,"const","Константа","Константы","Константа - это переменная, которая не может быть изменена. (прим. 'Дней в неделе')"),
            VariableCategory(MemberType.Unknown,'enum',"Перечисление","Перечисления","Перечисление это идентификаторов, каждому из которых присвоено значение (прим. Перечисление 'Цвет' имеет идентификаторы 'Красный','Желтый','Зелёный')"),
            VariableCategory(MemberType.Unknown,"struct","Структура","Структуры","Набор данных, связанных определённым образом. (прим. Структура 'Координаты' имеет поля 'Широта','Долгота')"),
        ]

        self.variableDataType = self._typeData.valueTypeList

        self.initUI()
        self.setupContextMenu()

    def initUI(self):
        # Создайте центральный виджет для док-зоны
        central_widget = QWidget()
        # Создайте вертикальный макет для центрального виджета
        layout = QVBoxLayout()
        layout.setContentsMargins(2, 2, 2, 0)
        central_widget.setLayout(layout)
        self.mainLayout = layout
        #self.widLayout = layout #TODO fixme

        #делаем скролл зону
        self.scrollArea = QScrollArea()
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scrollArea.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        self.scrollAreaWidgetContents = QWidget()
        self.scrollAreaLayout = QVBoxLayout(self.scrollAreaWidgetContents)
        self.scrollAreaLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        #self.scrollAreaLayout.addStretch(1) #факапит отображение
        self.scrollArea.setWidget(self.scrollAreaWidgetContents)

        layout.addWidget(self.scrollArea)
        self.setWidget(central_widget)
        layout = self.scrollAreaLayout

        __lbl = QLabel("Категория:")
        __ttpCat = "Категории:"
        layout.addWidget(__lbl)

        self.widCat = QComboBox()
        for __i, vcat in enumerate(self.variableCategoryList):
            self.widCat.addItem(vcat.categoryTextName)
            self.widCat.setItemData(__i, vcat.categoryDescription,Qt.ToolTipRole)
            self.widCat.setItemData(__i,vcat.category,Qt.UserRole)
            __ttpCat += "\n" + vcat.categoryDescription
        self.widCat.currentIndexChanged.connect(self._onVariableCategoryChanged)
        layout.addWidget(self.widCat)
        __lbl.setToolTip(__ttpCat)

        __lbl = QLabel("Имя:")
        __lbl.setToolTip("Уникальный идентификатор члена")
        layout.addWidget(__lbl)
        self.widVarName = QLineEdit()
        self.widVarName.setMaxLength(128)
        layout.addWidget(self.widVarName)

        __lbl = QLabel("Группа:")
        __lbl.setToolTip("Имя группы для члена (опционально)")
        layout.addWidget(__lbl)
        self.widVarGroup = QLineEdit()
        self.widVarGroup.setMaxLength(128)
        layout.addWidget(self.widVarGroup)

        # ---------------------- custom loader vartype -----------------------
        self.layoutCatWidgets = QVBoxLayout()
        layout.addLayout(self.layoutCatWidgets)

        self._curCategory : VarMgrBaseWidgetType = None #string name
        self._updateCategory(self.variableCategoryList[2].category)

        # Кнопка создания переменной
        self.widCreateVar = QPushButton("Создать")
        self.widCreateVar.setMinimumWidth(200)
        self.widCreateVar.setMinimumHeight(40)
        self.widCreateVar.clicked.connect(self.createVariable)
        layout.addWidget(self.widCreateVar,alignment=Qt.AlignmentFlag.AlignCenter)

        # Дерево для отображения списка переменных
        self.widVarTree = QTreeWidget()
        self.widVarTree.setMinimumHeight(200)
        self.widVarTree.setHeaderLabels(["Имя", "Тип", "Значение"])
        self.widVarTree.setColumnWidth(0,self.widVarTree.columnWidth(0)*2)
        layout.addWidget(self.widVarTree)
        self.widVarTree.setDragEnabled(True)
        self.widVarTree.setDragDropMode(QtWidgets.QAbstractItemView.DragDropMode.DragOnly)
        self.widVarTree.setObjectName("VariableManager.tree")
        self.widVarTree.setSortingEnabled(True)  # Включите сортировку
        self.widVarTree.sortItems(0, Qt.AscendingOrder)  # Сортировка по первому столбцу (индекс 0) в порядке возрастания

    def _updateCategory(self,catName):
        oldCat = self._curCategory
        if oldCat:
            oldCat.deleteWidgets()
            del oldCat
        newcat = self.getVariableCategoryByType(catName)
        if newcat:
            obj = newcat.instancer()
            obj.categoryObject = newcat
            obj.variableManagerRef = self
            obj.layout = self.layoutCatWidgets
            obj.initObject()

    def _onVariableCategoryChanged(self, *args, **kwargs):
        newIndex = args[0]
        self._updateCategory(self.variableCategoryList[newIndex].category)
        pass

    def getAllTypesTreeContent(self):
        treeContent = createTreeDataContent()

        objectTree = treeContent
        for vobj in self.variableTempateData:
            icon = QIcon("data\\icons\\pill_16x.png")
            colored_icon = updateIconColor(icon, vobj.color)
            _tempTree = addTreeContent(treeContent,vobj.variableType,vobj.variableTextName,colored_icon)
            if vobj.variableType == "object":
                objectTree = _tempTree
        #gobj add
        fact = self.nodeGraphComponent.getFactory()
        for objTree in fact.getClassAllChildsTree("object")['childs']:
            addTreeContentItem(objectTree,objTree)
        return treeContent

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

        if not self.nodeGraphComponent.sessionManager.getActiveTabData():
            self.nodeGraphComponent.sessionManager.logger.warning("Нет активной вкладки для создания переменной")
            return

        # Получите значения типа переменной, имени и дефолтного значения
        variable_name = self.widVarName.text().rstrip(' ').lstrip(' ')
        variable_group = self.widVarGroup.text().rstrip(' ').lstrip(' ')

        current_category = self.widCat.currentText() # Определите, к какой категории переменных относится новая переменная (локальная или классовая)
        if not current_category:
            self.showErrorMessageBox(f"Неизвестная категория")
            return
        
        curCat:VarMgrBaseWidgetType = self._curCategory
        curCatObj = curCat.categoryObject

        if not curCatObj:
            self.showErrorMessageBox(f"Категория не определена")
            return
        if not curCat:
            self.showErrorMessageBox(f"Виджет категории не определен")
            return
        if not variable_name:
            self.showErrorMessageBox(f"Укажите имя идентификатора")
            return        
        if self.variableExists(curCatObj.category, variable_name):
            # Выведите сообщение об ошибке
            self.showErrorMessageBox(f"Идентификатор '{variable_name}' уже существует в категории '{curCatObj.categoryTreeTextName}'!")
            return
        
        res = curCat.createVariable(variable_name, variable_group)
        if res == True:
            self.widVarName.clear()
            self.widVarGroup.clear()

    def getUndoStack(self) -> QUndoStack:
        return self.nodeGraphComponent.graph._undo_stack

    def setupContextMenu(self):
        # Создайте контекстное меню
        self.context_menu = QMenu(self)
        #TODO change variable action (вводит все пользовательские данные по формам и кнопка создать заменяется на изменить)
        
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

    def _updateNodeSync(self,nodeObj:RuntimeNode,id,nodeClassname):
        from ReNode.app.NodeFactory import NodeFactory
        lvdata = self.getVariableDataById(id)
        if not lvdata:
            raise Exception("Unknown variable id "+id)
        fact : NodeFactory = self.nodeGraphComponent.getFactory()
        catObj = self.getVariableCategoryById(id,retObject=True)
        if catObj:
            catObjInstancer:VarMgrBaseWidgetType = catObj.instancer
            instancerType = None
            for k,v in catObjInstancer.instancerKind.items():
                if nodeClassname == v:
                    instancerType = k
                    break
            if instancerType:
                catObjInstancer.onCreateVarFromTree(fact,lvdata,nodeObj,instancerType)
        

    def _updateNode(self,nodeObj:RuntimeNode,id,instancerType,catObjInstancer):
        from ReNode.app.NodeFactory import NodeFactory
        lvdata = self.getVariableDataById(id)
        if not lvdata:
            raise Exception("Unknown variable id "+id)
                
        _class = nodeObj.nodeClass
        fact : NodeFactory = self.nodeGraphComponent.getFactory()
        cfg = fact.getNodeLibData(_class)
        nodeObj.set_property('name',cfg["name"].format(
            catObjInstancer.resolveCreatedNodeName(lvdata["name"])
        ),False,doNotRename=True)
        nodeObj.set_property('nameid',id,False)

        nodeObj.set_port_deletion_allowed(True)

        catObjInstancer.onCreateVarFromTree(fact,lvdata,nodeObj,instancerType)

        nodeObj.update()
        pass

    def getVariableDataById(self,id) -> None | dict:
        for cat in self.variables.values():
            for k,v in cat.items():
                if k == id: return v
        return None
    
    def isObjectType(self,type):
        """
            Проверяет является ли тип типом объекта (унаследованного от object)

            Допускается использование типов с постфиксом наследования (^)
        """
        if type.endswith("^"): #remove postfix
            type = type[:-1]
        
        if self.nodeGraphComponent.getFactory().isTypeOf(type,"object"):
            return True
        return False

    def getObjectTypeName(self,type):
        if type.endswith("^"): #remove postfix
            type = type[:-1]
        cType = self.nodeGraphComponent.getFactory().getClassData(type)
        if not cType: return None
        return cType.get("name",type)

    def getVariableTypedefByType(self,type,useTextTypename=False) -> None | VariableTypedef:
        if self.isObjectType(type):
            type = "object"
        
        for vobj in self.variableTempateData:
           if useTextTypename and vobj.variableTextName == type: return vobj
           if vobj.variableType == type: return vobj 
        return None
    
    def getVariableCategoryByType(self,type):
        for vobj in self.variableCategoryList:
            if vobj.category == type: return vobj
        return None

    def getVariableDataTypeByType(self,type):
        """
            Возвращает тип данных (значение, массив и т.д.)
        """
        for vobj in self.variableDataType:
            if vobj.dataType == type: return vobj
        return None

    def _getVarDataByRepr(self,vartRepr,vardtRepr):
        """
            !УСТАРЕВШИЙ МЕТОД, КОТОРЫЙ НЕ ДОЛЖЕН БЫТЬ ИСПОЛЬЗОВАН!\n
            Используйте getVarDataByType
        """
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

    def getVarDataByType(self,fullTypename,canCreateCopy=False) -> tuple[VariableTypedef | list[VariableTypedef] | None,VariableDataType|None]:
        """
            Возвращает tuple (VariableTypedef | list[VariableTypedef],VariableDataType) по полному имени типа
        """
        datatype = "value"
        values = [fullTypename]
        if re.findall('[\[\]\,]',fullTypename):
            typeinfo = re.findall('\w+\^?',fullTypename)
            datatype = typeinfo[0]
            values = typeinfo[1:]
        
        #fullType
        dtObj = self.getVariableDataTypeByType(datatype)
        valList = []
        for val in values:
            valObj = self.getVariableTypedefByType(val)
            if not valObj:
                raise Exception(f"Variable type not found: {val}; Fulltypename: {fullTypename}")
            
            if canCreateCopy:
                vCopy = valObj.copy(val)
                valList.append(vCopy)
            else:
                valList.append(valObj)
            
        vRet = valList if len(valList) > 1 else valList[0]
        return vRet,dtObj

    def getTextTypename(self,fulltypename):
        """Возвращает репрезентацию типа в русском названии"""
        if fulltypename == "Exec": return "Выполнение"
        if fulltypename == "null": return "Ничего"
        
        vRet,dtObj = self.getVarDataByType(fulltypename,canCreateCopy=True)
        if dtObj.dataType == 'value':
            return vRet.variableTextName
        else:
            dtName = dtObj.text
            listVals = []
            if isinstance(vRet,list):
                checkedList = vRet
            else:
                checkedList = [vRet]
            
            listVals = []
            for obj in checkedList:
                listVals.append(obj.variableTextName)
                del obj
        
            return f"{dtName}({', '.join(listVals)})"

    def getIconFromTypename(self,fulltypename):
        if fulltypename == "Exec": return QIcon()
        if fulltypename == "null": return QIcon()

        """Возвращает инстанс иконки для типа с нужными цветами"""
        varInfo, dt = self.getVarDataByType(fulltypename,False)

        if isinstance(varInfo,list):
            pathes = dt.icon
            colors = [o__.color for o__ in varInfo]
            return QIcon(generateIconParts(pathes,colors))
        else:
            icn = QIcon(dt.icon)
            icn = updateIconColor(icn,varInfo.color)
            return icn

    def getColorByType(self,fulltypename):
        if fulltypename == "null": return [255,255,255,255]
        if fulltypename == "Exec": return [255,255,255,255]
        varInfo, dt = self.getVarDataByType(fulltypename,False)
        color = None
        if isinstance(varInfo,list):
            color = varInfo[0].color
        else:
            color = varInfo.color
        return [*color.getRgb()]
    
    def getCustomPropsByType(self,fulltypename):
        """Получает пользовательское свойство по типу (для инпут портов)"""
        if fulltypename == "null": return {}
        if fulltypename == "Exec": return {}
        varInfo, dt = self.getVarDataByType(fulltypename,False)
        prtInfo = None
        if isinstance(varInfo,list):
            prtInfo = varInfo[0].dictProp
        else:
            prtInfo = varInfo.dictProp

        return prtInfo

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
            catObj = self.getVariableCategoryByType(category)
            if not catObj:
                raise Exception(f"Неизвестная категория для создания переменной: {category}")
            category_item = QTreeWidgetItem([catObj.categoryTreeTextName])
            category_item.setFlags(category_item.flags() & ~QtCore.Qt.ItemFlag.ItemIsDragEnabled)
            self.widVarTree.addTopLevelItem(category_item)

           

            for variable_id, variable_data in variables.items():
                treeItemListTexts = catObj.instancer.getVariableMakerVisualInfo(variable_id,variable_data)
                if not treeItemListTexts:
                    self.logger.error(f"Неовзможно загрузить переменную {variable_id}")
                    continue
                
                group = variable_data.get('group',"")

                item = QTreeWidgetItem(treeItemListTexts)
                item.setFlags(item.flags() | QtCore.Qt.ItemFlag.ItemIsDragEnabled)
                item.setData(0, QtCore.Qt.UserRole, variable_id)
                
                catObj.instancer.onItemCreated(item,variable_id,variable_data)

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

    def getVariableCategoryById(self,idvar,retObject=False):
        """Получает категорию переменной по айди"""
        for cat,items in self.variables.items():
            if idvar in items:
                if retObject:
                    return self.getVariableCategoryByType(cat)
                else:
                    return cat
        return None