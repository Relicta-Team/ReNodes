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
from ReNode.ui.SearchMenuWidget import SearchComboButton,SearchComboButtonAutoload,addTreeContent,createTreeDataContent,addTreeContentItem
from ReNode.ui.VarMgrWidgetTypes.Widgets import *
import datetime
from ReNode.app.Logger import RegisterLogger
import re
import enum
import ast

class MemberType(enum.Enum):
    """Тип члена отражает какие данные можно вводить в менеджере переменных"""
    Unknown = -1
    """Неизвестный тип члена"""
    Variable = 0
    """Переменная хранится в классе, имеет тип данных и значение"""
    Function = 1
    """Функция хранится в классе, имеет параметры и возвращаемое значение"""
    LocalVariable = 2
    """Локальная переменная"""

class VariableInfo:
    def __init__(self):
        pass

class VariableTypedef:
    def __init__(self,vart="",vartText="",classMaker=None,dictProp={},color=None,defaultValue=None,parseFunction=None):
        self.variableType = vart #typename
        self.variableTextName = vartText #representation in utf-8
        self.classInstance = classMaker
        self.dictProp = dictProp
        self.color : QColor = color

        self.defaultValue = defaultValue
        self.parseFunction = parseFunction

        if self.defaultValue is None or not self.parseFunction:
            raise Exception("Both default value and parse function must be set for type " + vart)

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
        return VariableTypedef_Copy(vtype,vtextname,self.classInstance,self.dictProp,self.color,self.defaultValue,self.parseFunction)

class VariableTypedef_Copy(VariableTypedef):
    def __init__(self,vart="",vartText="",classMaker=None,dictProp={},color=None,dval=None,pfunc=None):
        super().__init__(vart,vartText,classMaker,dictProp,color,dval,pfunc)

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
            inst = VarMgrClassVariableWidget
        elif self.memtype == MemberType.LocalVariable:
            inst = VarMgrVariableWidget
        elif self.memtype == MemberType.Function:
            inst = VarMgrFunctionWidget
        else:
            raise Exception(f"Unknown member type: {self.memtype.name}")
        
        self.instancer = inst

class VariableDataType:
    def __init__(self,vartext='',vartype='',varicon='',instancer=None,defaultValue=None,parseFunction=None):
        self.text = vartext
        self.dataType = vartype
        self.icon = varicon #string or list of string
        self.instance = instancer
        
        self.defaultValue = defaultValue
        self.parseFunction = parseFunction
        if defaultValue is None:
            raise Exception("Default value must be set for datatype " + vartype)
        if parseFunction is None:
            raise Exception("Parse function must be set for datatype " + vartype)
    
    def __repr__(self):
        return f"{self.dataType} ({self.text})"

class VariableLibrary:
    def __init__(self):
        self.typeList = [
            #base types
            VariableTypedef("int","Целое число",IntValueEdit,{"spin": {
                "text": "Число",
                "range": {"min":-999999,"max":999999}
            }},color=QtGui.QColor("Sea green"),
            defaultValue=0,parseFunction=int),
            VariableTypedef("float","Дробное число",FloatValueEdit,{"fspin": {
                "text": "Число",
                "range": {"min":-999999,"max":999999},
                "floatspindata": {
                    "step": 0.5,
                    "decimals": 5
                }
            }},color=QtGui.QColor("Yellow green"),
            defaultValue=0.0,parseFunction=float),
            # VariableTypedef("string","Строка",PropLineEdit,{"input": {
            #     "text": "Текст"
            # }},color=QtGui.QColor("Magenta")),
            VariableTypedef("string","Строка",PropTextEdit,{"edit": {
                "text": "Текст"
            }},color=QtGui.QColor("Magenta"),
            defaultValue="",parseFunction=lambda x: x),
            VariableTypedef("bool","Булево",PropCheckBox,{"bool":{
                "text": "Булево"
            }},color=QtGui.QColor("Maroon"),
            defaultValue=False,parseFunction=lambda x: x.lower() == "true"),

            #colors
            VariableTypedef("color","Цвет",PropColorPickerRGB,{"color": {
                "text": "Цвет"
            }},color=QtGui.QColor("#00C7B3"),
            defaultValue=[0,0,0,0],parseFunction=lambda x: [float(t) for t in x.strip('[]').split(',')[:4]]),
            VariableTypedef("color","Цвет с альфа-каналом",PropColorPickerRGBA,{"color": {
                "text": "Цвет"
            }},color=QtGui.QColor("#048C7F"),
            defaultValue=[0,0,0,0],parseFunction=lambda x: [float(t) for t in x.strip('[]').split(',')[:4]]),

            #vectors
            VariableTypedef("vector2","2D Вектор",PropVector2,{"vec2": {
                "text": "Вектор"
            }},color=QtGui.QColor("#D4A004"),
            defaultValue=[0,0],parseFunction=lambda x: [float(t) for t in x.strip('[]').split(',')[:2]]),
            VariableTypedef("vector3","3D Вектор",PropVector3,{"vec3": {
                "text": "Вектор"
            }},color=QtGui.QColor("#D48104"),
            defaultValue=[0,0,0],parseFunction=lambda x: [float(t) for t in x.strip('[]').split(',')[:3]]),
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
            ,color=QtGui.QColor("#1087C7"),
            defaultValue='nullPtr',parseFunction=lambda x: x),
            
            VariableTypedef('class',"Класс",SearchComboButtonAutoload,{"typeselect": {
                "text": "Тип"
            }
            },color=QtGui.QColor("#1044C7"),
            defaultValue='object',parseFunction=lambda x: x),
            VariableTypedef("classname","Имя класса",SearchComboButtonAutoload,{"typeselect": {
                "text": "Имя класса"
            }},color=QtGui.QColor("#5C10C7"),
            defaultValue='object',parseFunction=lambda x: x),

            #enum special category
            VariableTypedef("enum","Перечисление",PropComboBox,
                color=QtGui.QColor("#2D543E"),
            defaultValue='-1',parseFunction=int),

            VariableTypedef("model","Модель",PropLineEdit
                # ,{"input": {
                # "text": "Модель"
                # }}
            ,color=QtGui.QColor("#4C4CA8"),
            defaultValue='objNull',parseFunction=lambda x: x),
            VariableTypedef("handle","Дескриптор события",IntValueEdit
                # ,{"spin": {
                # "text": "Число",
                # "range": {"min":0,"max":999999}
                # }}
            ,color=QtGui.QColor("Sea green").lighter(50),
            defaultValue=-1,parseFunction=int),
            VariableTypedef("list","Абстрактный массив",PropAbstract
                ,color=QtGui.QColor("#EBE01E"),
                defaultValue='[]',parseFunction=lambda x: x,
            ),
            VariableTypedef("void","Абстрактное значение",PropAbstract
                ,color=QtGui.QColor("#02D109"),
                defaultValue='NIL',parseFunction=lambda x: x
            )
        ]
        
        #parseFunction(str,tuple[str]) -> parseFunction("[1,2,3]",["int"])
        def _parseDataVal(val,types,refClassDict):
            parsed = ast.literal_eval(val)
            
            if parsed:
                if isinstance(parsed,dict):
                    fitem = list(parsed.items())[0]
                else:
                    fitem = [parsed[0]]
                
                if len(types) != len(fitem):
                    raise ValueError(f"Types count {len(types)} != {len(fitem)} on parse data value {val} as {types}")

                for i in range(len(types)):
                    kit = fitem[i]
                    tit = types[i]
                    parsvt = self.parseGameValue(str(kit),tit,refClassDict)
                    if parsvt != kit:
                        raise Exception(f'Error on parse value')
                return parsed
            else:
                return parsed

        self.valueTypeList = [
            VariableDataType("Значение","value","data\\icons\\pill_16x.png",None,
                defaultValue=object(),
                parseFunction=lambda val,types,rd:val),
            VariableDataType("Массив","array","data\\icons\\ArrayPin.png",ArrayWidget,
                defaultValue=[],
                parseFunction=_parseDataVal),
            VariableDataType("Словарь","dict",["data\\icons\\pillmapkey_16x.png","data\\icons\\pillmapvalue_16x.png"],DictWidget,
                defaultValue={},
                parseFunction=_parseDataVal),
            VariableDataType("Сет","set","data\\icons\\pillset_40x.png",ArrayWidget,
                defaultValue=[],
                parseFunction=_parseDataVal),
        ]

    def parseGameValue(self,strval:str,returnType:str,refClassDict:dict):
        """Парсит строчное игровое значение в значение для работы редактора (любой python тип)"""
        #parse object type
        if self.isObjectType(returnType,refClassDict):
            returnType = "object"
        
        tObj,dtObj = self.getVarDataByType(returnType,False)

        isValueType = dtObj.dataType == 'value'
            
        if strval == "$NULL$":
            return tObj.defaultValue if isValueType else dtObj.defaultValue
        else:
            if isValueType:
                return tObj.parseFunction(strval)
            else:
                if isinstance(tObj,list):
                    valist = tuple(t.variableType for t in tObj)
                else:
                    valist = tuple([tObj.variableType])
                return dtObj.parseFunction(strval,valist,refClassDict)

    def getTypeIcon(self,typ:str,colorize=False):
        valueType = "value"
        compareType = typ
        if typ.startswith("array") or typ.startswith("set") or typ.startswith("dict"):
            vdat = re.findall('[\w\.]+\^?',compareType)
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
    
    def prepPortColors(self,val:dict):
        from ReNode.app.NodeFactory import NodeFactory
        typecolor = {}
        for objInfo in self.typeList:
            typecolor[objInfo.variableType] = [*objInfo.color.getRgb()]

        isDefaultColor = None
        portType = None

        if val['inputs']:
            for v in val['inputs'].values():
                portType = v['type']

                if re.findall('[\[\]\,]',portType):
                    #portType = f'array[{portType}]'
                    typeinfo = re.findall('[\w\.]+\^?',portType)
                    portType = typeinfo[1]

                if portType.endswith("^"): portType = "object" #temp fix object colors
                if portType.startswith('enum.'): portType = 'enum'

                isDefaultColor = not v.get('color') or v['color']== list(NodeFactory.defaultColor) or v['color'] == [255,255,255,255]
                if portType in typecolor and isDefaultColor:
                    v['color'] = typecolor[portType]
                    v['border_color'] = None
        
        if val['outputs']:
            for v in val['outputs'].values():
                portType = v['type']

                if re.findall('[\[\]\,]',portType):
                    typeinfo = re.findall('[\w\.]+\^?',portType)
                    portType = typeinfo[1]

                if portType.endswith("^"): portType = "object" #temp fix object colors
                if portType.startswith('enum.'): portType = 'enum'

                isDefaultColor = not v.get('color') or v['color']== list(NodeFactory.defaultColor) or v['color'] == [255,255,255,255]
                if portType in typecolor and isDefaultColor:
                    v['color'] = typecolor[portType]
                    v['border_color'] = None

    def getVarDatatypeByType(self,type)->VariableDataType|None:
        for t in self.valueTypeList:
            if t.dataType == type:
                return t
        return None

    def getVarTypedefByType(self,type)->VariableTypedef|None:
        if type.endswith("^"): 
            type = "object"
        
        for t in self.typeList:
            if t.variableType == type:
                return t
        return None

    def isObjectType(self,type,refClassDict)->bool:
        if type.endswith("^"): type = type[:-1]

        classData = refClassDict.get(type)
        if not classData: return False
        return "object" in classData.get('baseList',[])
    
    def getVarDataByType(self,fullTypename,canCreateCopy=False) -> tuple[VariableTypedef | list[VariableTypedef] | None,VariableDataType|None]:
        """
            Возвращает tuple (VariableTypedef | list[VariableTypedef],VariableDataType) по полному имени типа
        """
        datatype = "value"
        values = [fullTypename]
        if re.findall('[\[\]\,]',fullTypename):
            typeinfo = re.findall('[\w\.]+\^?',fullTypename)
            datatype = typeinfo[0]
            values = typeinfo[1:]
        
        #fullType
        dtObj = self.getVarDatatypeByType(datatype)
        valList = []
        for val in values:
            valObj = self.getVarTypedefByType(val)
            if not valObj:
                raise Exception(f"Variable type not found: {val}; Fulltypename: {fullTypename}")
            
            if canCreateCopy:
                vCopy = valObj.copy(val)
                valList.append(vCopy)
            else:
                valList.append(valObj)
            
        vRet = valList if len(valList) > 1 else valList[0]
        return vRet,dtObj
    
    def getIconFromTypename(self,fulltypename,retSerializable = False):
        """Получает готовую иконку по полному имени типа"""
        
        if fulltypename == "Exec": return "" if retSerializable else QIcon()
        if fulltypename == "null": return "" if retSerializable else QIcon()

        """Возвращает инстанс иконки для типа с нужными цветами"""
        varInfo, dt = self.getVarDataByType(fulltypename,False)

        if isinstance(varInfo,list):
            pathes = dt.icon
            if retSerializable:
                if not isinstance(pathes,list):
                    pathes = [pathes]
                colorList = [cl.color.name()for cl in varInfo]
                retVal = []
                for i,pt_ in enumerate(pathes):
                    retVal.append(pt_)
                    retVal.append(colorList[i])
                return retVal

            
            colors = [o__.color for o__ in varInfo]
            return QIcon(generateIconParts(pathes,colors))
        else:
            if retSerializable: return [dt.icon,varInfo.color.name()]

            icn = QIcon(dt.icon)
            icn = updateIconColor(icn,varInfo.color)
            return icn

    def getColorByType(self,fulltypename):
        """Получает цвет по полному имени типа"""
        if fulltypename == "null": return [255,255,255,255]
        if fulltypename == "Exec": return [255,255,255,255]
        varInfo, dt = self.getVarDataByType(fulltypename,False)
        color = None
        if isinstance(varInfo,list):
            color = varInfo[0].color
        else:
            color = varInfo.color
        return [*color.getRgb()]

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
            VariableCategory(MemberType.LocalVariable,'localvar',"Локальная переменная","Локальные переменные","Локальная переменная - это переменная, создаваемая и существующая в пределах одного события или функции. Используются для записи и хранения временных данных."),
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
        self._updateCategory(self.variableCategoryList[0].category)

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
        """Получает полную библиотеку типов в виде дерева для создания через SearchComboButton"""
        treeContent = createTreeDataContent()

        objectTree = treeContent
        enumTree = treeContent
        enumIconCommon = QIcon("data\\icons\\Enum")
        enumItemIcon = None
        for vobj in self.variableTempateData:
            icon = QIcon("data\\icons\\pill_16x.png")
            colored_icon = updateIconColor(icon, vobj.color)
            dataName = vobj.variableType
            typeName = vobj.variableTextName
            if dataName == "enum":
                dataName = ""
                typeName = "Перечисления"
                enumItemIcon = colored_icon
                colored_icon = enumIconCommon
                
            _tempTree = addTreeContent(treeContent,dataName,typeName,colored_icon)
            if vobj.variableType == "object":
                objectTree = _tempTree
            if vobj.variableType == "enum":
                _tempTree['desc'] = 'Список всех перечислений, определенных в сборке.'
                enumTree = _tempTree
        #gobj add
        fact = self.nodeGraphComponent.getFactory()
        for objTree in fact.getClassAllChildsTree("object")['childs']:
            addTreeContentItem(objectTree,objTree)
        #enum add
        ens = fact.getClassData("ReNode_AbstractEnum")['allEnums']
        for enType,enDict in ens.items():
            addTreeContentItem(enumTree,createTreeContentItem(enType,enDict['name'],enumItemIcon))

        
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

    def getVirtualLib(self):
        return self.nodeGraphComponent.getFactory().vlib

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
        # reserved check
        if variable_name == "nameid":
            self.showErrorMessageBox(f"Идентификатор не может быть '{variable_name}'")
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
            varId = item.data(0, Qt.UserRole)
            
            # Получите категорию переменной из имени элемента
            vardata = self.getVariableDataById(varId)
            if not vardata: raise Exception(f"Cant find variable by system name: {varId}")

            oldname = vardata.get('group',"")            
            newname,result = self.nodeGraphComponent.graph.input_dialog("Введите новое имя группы. Удалите текст для того, чтобы разгрупировать переменную",
                title="Изменение группы переменной", deftext=oldname)

            if not result: return
            newname = newname.rstrip(' ').lstrip(' ')
            if oldname == newname: return

            hstack = self.getUndoStack()
            hstack.push(VariableChangePropertyCommand(self,vardata['category'],varId,'group',newname,""))

    def deleteVariable(self, item):
        if item:
            # Получите системное имя переменной, хранящееся в данных элемента
            varId = item.data(0, Qt.UserRole)
            
            # Получите категорию переменной из имени элемента
            vardata = self.getVariableDataById(varId)
            if not vardata: raise Exception(f"Cant find variable by system name: {varId}")
            category = self.getVariableCategoryById(varId,retObject=False)
            hstack = self.getUndoStack()

            canDeleteVariable =  category in self.variables and varId in self.variables[category]
            if not canDeleteVariable:
                self.showErrorMessageBox(f"Невозможно удалить несуществующую переменную {vardata['name']} из категории {category}")
                return

            hstack.beginMacro(f"Удаление переменной {vardata['name']}")
            # Удаляем переменную из графа
            graph = self.nodeGraphComponent.graph
            allnodes = graph.get_nodes_by_class(None)
            for node in allnodes:
                if node.has_property('nameid'):
                    if node.get_property('nameid') == varId:
                        graph.delete_node(node,True) #push undo for history
            
            catObj = self.getVariableCategoryById(varId,retObject=True)
            if catObj:
                varData = self.getVariableDataById(varId)
                if varData:
                    catObjInstancer = catObj.instancer
                    infoData = self.nodeGraphComponent.inspector.infoData
                    for instancerType in catObjInstancer.instancerKind.keys():
                        typename = catObjInstancer.getVariableInstancerClassName(instancerType,infoData,varData)
                        allNodes = graph.get_nodes_by_class(typename)
                        if typename and len(allNodes) > 0:
                            for node in allNodes:
                                graph.delete_node(node,True)


            hstack.push(VariableDeletedCommand(self,category,varId))

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
        ),True,doNotRename=True)
        nodeObj.set_property('nameid',id,True)

        nodeObj.set_port_deletion_allowed(True)

        catObjInstancer.onCreateVarFromTree(fact,lvdata,nodeObj,instancerType)

        nodeObj.update()
        pass

    def getVariableDataById(self,id,refVarDict=None) -> None | dict:
        varDict = refVarDict or self.variables
        for cat in varDict.values():
            for k,v in cat.items():
                if k == id: return v
        return None
    
    def isObjectType(self,type):
        """
            Проверяет является ли тип типом объекта (унаследованного от object)

            Допускается использование типов с постфиксом наследования (^)
        """        
        return self.nodeGraphComponent.getFactory().isObjectType(type)

    def isEnumType(self,type):
        """
            Проверяет является ли тип типом перечисления (унаследованного от enum)
        """
        return self.nodeGraphComponent.getFactory().isEnumType(type)
    
    def getFactory(self):
        return self.nodeGraphComponent.getFactory()

    def getObjectTypeName(self,type):
        if type.endswith("^"): #remove postfix
            type = type[:-1]
        cType = self.nodeGraphComponent.getFactory().getClassData(type)
        if not cType: return None
        return cType.get("name",type)

    def prepareTypeForCreate(self,fulltypename):
        """Подготовка типа для использования. Добавляет постфиксы ^ к именам объектов"""
        if fulltypename == 'null': return fulltypename
        vobj,dtobj = self.getVarDataByType(fulltypename)
        if dtobj.dataType == 'value':
            if self.isObjectType(fulltypename) and not fulltypename.endswith("^"): fulltypename += '^'
            return fulltypename
        else:
            typeinfo = re.findall('[\w\.]+\^?',fulltypename)
            rval = typeinfo[0]+"["
            for i in range(1,len(typeinfo)):
                tdat = typeinfo[i]
                if self.isObjectType(tdat) and not tdat.endswith("^"): tdat += '^'
                if i > 1: rval += ","
                rval += tdat
            rval += ']'
            return rval

    def getVariableTypedefByType(self,type,canCreateCopy=False) -> None | VariableTypedef:
        sourceType = type
        if self.isObjectType(type):
            type = "object"
        if self.isEnumType(type):
            type = "enum"
        
        for vobj in self.variableTempateData:
            if vobj.variableType == type: 
                if canCreateCopy:
                    return vobj.copy(sourceType)
                return vobj
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

    def getVarDataByType(self,fullTypename,canCreateCopy=False) -> tuple[VariableTypedef | list[VariableTypedef] | None,VariableDataType|None]:
        """
            Возвращает tuple (VariableTypedef | list[VariableTypedef],VariableDataType) по полному имени типа
        """
        datatype = "value"
        values = [fullTypename]
        if re.findall('[\[\]\,]',fullTypename):
            typeinfo = re.findall('[\w\.]+\^?',fullTypename)
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
        if not vRet or not dtObj: return "Неизвестно"

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
    
    def getCustomPropsByType(self,fulltypename,propname = None):
        """Получает пользовательское свойство по типу (для инпут портов)"""
        if fulltypename == "null": return {}
        if fulltypename == "Exec": return {}
        varInfo, dt = self.getVarDataByType(fulltypename,False)
        prtInfo = None
        if isinstance(varInfo,list):
            prtInfo = varInfo[0].dictProp
        else:
            prtInfo = varInfo.dictProp
        if propname:
            for prpName,prpDat in prtInfo.items():
                prpDat = prpDat.copy()
                prpDat['text'] = propname
                prtInfo[prpName] = prpDat
        return prtInfo

    def syncVariableManagerWidget(self):
        self.loadVariables(self.variables,False)
        self.syncNodesVirtualLib()

    def syncNodesVirtualLib(self):
        vlib = self.getVirtualLib()
        infoData = self.nodeGraphComponent.graph.infoData
        vars = self.variables
        vlib.onUpdateUserVariables(infoData,vars)
        pass

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
            
            if not variables: continue #переменных в категории нет

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

    def getVariableCategoryById(self,idvar,retObject=False,refVarDict=None):
        """Получает категорию переменной по айди"""
        varDict = refVarDict or self.variables
        for cat,items in varDict.items():
            if idvar in items:
                if retObject:
                    return self.getVariableCategoryByType(cat)
                else:
                    return cat
        return None
    
    def getVariableNodeNameById(self,idvar,instancerKindType=None,refVarDict=None,refInfoData=None):
        catObj = self.getVariableCategoryById(idvar,retObject=True,refVarDict=refVarDict)
        if not catObj: return None
        vdata = self.getVariableDataById(idvar,refVarDict=refVarDict)
        if not vdata: return None
        catObjInstancer = catObj.instancer
        infoData = refInfoData or self.nodeGraphComponent.inspector.infoData
        if instancerKindType:
            return catObjInstancer.getVariableInstancerClassName(instancerKindType,infoData,vdata)
        else:
            retList = []
            for instT in catObjInstancer.instancerKind.keys():
                typename = catObjInstancer.getVariableInstancerClassName(instT,infoData,vdata)
                if typename:
                    retList.append(typename)
            return retList
        
