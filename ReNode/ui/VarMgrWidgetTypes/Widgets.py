from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from ReNode.ui.SearchMenuWidget import SearchComboButton,addTreeContent,createTreeDataContent,addTreeContentItem,createTreeContentItem
from ReNode.app.utils import updateIconColor, mergePixmaps, generateIconParts
import datetime

class VarMgrBaseWidgetType:
    """
        Базовый тип переменной. В унаследованных членах должны быть реализованы:
        - createWidgets
        - статический метод getVariableMakerVisualInfo
        - статчиеский метод onItemCreated
    """
    def __init__(self):
        from ReNode.ui.VariableManager import VariableManager,VariableCategory
        self.layout :QVBoxLayout = None
        self.variableManagerRef :VariableManager = None
        self.categoryObject :VariableCategory = None

    @staticmethod
    def getVarMgr():
        from ReNode.ui.VariableManager import VariableManager
        return VariableManager.refObject

    def getMainLayout(self) -> QVBoxLayout:
        return self.layout

    def initObject(self):
        self.variableTempateData = self.variableManagerRef.variableTempateData
        self.variableDataType = self.variableManagerRef.variableDataType
        self.nodeGraphComponent = self.variableManagerRef.nodeGraphComponent

        self.variableManagerRef._curCategory = self
        self.createWidgets()

    def createWidgets(self):
        layout = self.layout

    def deleteWidgets(self):
        layout = self.layout
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.deleteLayoutWidgets(item.layout())


    def deleteLayoutWidgets(self, layout):
        while layout.count() > 0:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                self.deleteLayoutWidgets(item.layout())

    def createVariable(self,varname,vargroup):
        self.variableManagerRef.showErrorMessageBox(f"Создание для \'{self.categoryObject.categoryTextName}\' не реализовано в текущей версии редактора")
        return 404

    def registerVariable(self,vardict):
        from NodeGraphQt.base.commands import VariableCreatedCommand
        cat_sys_name = self.categoryObject.category
        varmgr = self.variableManagerRef

        if not varmgr.variables.get(cat_sys_name):
            varmgr.variables[cat_sys_name] = {}
        
        variableSystemName = vardict.get('systemname')
        if not variableSystemName:
            raise Exception(f"Не указано системное имя идентификатора! {vardict}")
        
        if variableSystemName in varmgr.variables[cat_sys_name]:
            varmgr.showErrorMessageBox(f"Коллизия системных имен идентификаторов. Айди '{variableSystemName}' уже существует!")
            return
        
        for cat,stor in varmgr.variables.items():
            if variableSystemName in stor:
                varmgr.showErrorMessageBox(f"Коллизия системных имен идентификаторов. Айди '{variableSystemName}' уже существует в другой категории - {cat}")
                return

        varmgr.getUndoStack().push(VariableCreatedCommand(varmgr,cat_sys_name,vardict))

    @staticmethod
    def getVariableMakerVisualInfo(variable_id,variable_data):
        """Возвращает названия колонок для визуального отображения в дереве"""
        return None
    @staticmethod
    def onItemCreated(item:QTreeWidgetItem,variable_id,variable_data):
        """Пост-обработчик создания элемента в дереве. Например, можно установить описание или иконку"""
        return None

class VarMgrVariableWidget(VarMgrBaseWidgetType):
    def createWidgets(self):
        layout : QVBoxLayout = self.layout

        layout.addWidget(QLabel("Тип данных:"))

        type_layout = QHBoxLayout()
        layout.addLayout(type_layout)

        self.widVarType = SearchComboButton()
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
        objTree = fact.getClassAllChildsTree("GameObject")
        addTreeContentItem(objectTree,objTree)

        addTreeContentItem(objectTree,fact.getClassAllChildsTree("ServerClient"))

        self.widVarType.loadContents(treeContent)
        self.widVarType.changed_event.connect(self._onVariableTypeChanged)
        type_layout.addWidget(self.widVarType)

        self.widDataType = QComboBox()
        for vobj in self.variableDataType:
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
        self.widDataType.currentIndexChanged.connect(self._onDataTypeChanged)
        type_layout.addWidget(self.widDataType)

        __lbl = QLabel("Начальное значение:")
        __lbl.setToolTip("Значение, которое будет присвоено переменной при создании")
        layout.addWidget(__lbl)
        self.widInitVal = QLineEdit()
        layout.addWidget(self.widInitVal)
        self._initialValue = None

        self._updateVariableValueVisual(self.variableTempateData[0],self.variableDataType[0])
    
    def _onVariableTypeChanged(self, data,text,icon):
        from ReNode.ui.VariableManager import VariableTypedef,VariableDataType
        vart: VariableTypedef = self.variableManagerRef.getVariableTypedefByType(data)
        tobj : VariableDataType = self.variableDataType[self.widDataType.currentIndex()]

        self._updateVariableValueVisual(vart,tobj)
        pass

    def _onDataTypeChanged(self,*args,**kwargs):
        from ReNode.ui.VariableManager import VariableTypedef,VariableDataType
        newIndexDatatype = args[0]

        curdata = self.widVarType.get_value()
        vart = self.variableManagerRef.getVariableTypedefByType(curdata)
        tobj : VariableDataType = self.variableDataType[newIndexDatatype]
        self._updateVariableValueVisual(vart,tobj)

    def _updateVariableValueVisual(self,tp,dt):
        from ReNode.ui.VariableManager import VariableTypedef,VariableDataType
        tp: VariableTypedef
        dt: VariableDataType

        isValue = dt.dataType == 'value' or not dt.instance
        #delete prev
        idx = self.layout.indexOf(self.widInitVal)
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
        self.layout.insertWidget(idx,self.widInitVal)

        self._initialValue = self.widInitVal.get_value()
        pass

    def createVariable(self,varname,vargroup):
        from ReNode.ui.VariableManager import VariableTypedef,VariableDataType
        from ReNode.ui.ArrayWidget import DictWidget,ArrayWidget

        categoryObj = self.categoryObject
        variable_name = varname
        variable_group = vargroup
        variable_type = self.widVarType.get_value()
        default_value = self.widInitVal.get_value()
        varMgr = self.variableManagerRef

        varInfo = varMgr.getVariableTypedefByType(variable_type)

        if not varInfo:
            raise Exception(f"Неизвестный тип переменной: {variable_type}")

        isObject = varMgr.isObjectType(variable_type)

        var_typename = varInfo.variableType
        if isObject: #обновляем тип если это подтип объекта
            var_typename = variable_type + "^" #добавляем символ наследования

        cat_sys_name = categoryObj.category
        dt : VariableDataType = varMgr.variableDataType[self.widDataType.currentIndex()]

        reprType = str(varInfo)

        #update 
        if isinstance(self.widInitVal,DictWidget) and dt.dataType == "dict":

            if variable_type != "string":
                varMgr.showErrorMessageBox(f"В текущей версии ключи словарей могут быть только строками")
                return

            countItems = self.widInitVal.get_values_count()
            curLenItems = len(default_value)
            if countItems != curLenItems:
                self.variableManagerRef.showErrorMessageBox(f"Ключи словаря должны принимать разные значения;\nУникальных элементов: {curLenItems}, установлено {countItems}")
                return

            kv_valtypeTextname = self.widInitVal.selectType.get_value()
            kv_itemInfo = varMgr.getVariableTypedefByType(kv_valtypeTextname)
            if not kv_itemInfo:
                raise Exception(f"Неизвестный тип переменной: {kv_valtypeTextname}")
            vtypename = kv_itemInfo.variableType
            if varMgr.isObjectType(kv_valtypeTextname):
                #add postfix with real type
                vtypename = kv_valtypeTextname + "^"
                #vtypename += "^" 
            var_typename += "," + vtypename
            reprType += "|" + str(kv_itemInfo)
            pass

        if dt.dataType != "value":
            var_typename = f"{dt.dataType}[{var_typename}]"
            variable_type = dt.text
        
        itm = datetime.datetime.now()
        #variableSystemName = hex(id(itm))
        variableSystemName = f'{hex(id(itm))}_{itm.year}{itm.month}{itm.day}{itm.hour}{itm.minute}{itm.second}{itm.microsecond}'

        vardict = {
            "name": variable_name,
            "type": var_typename,
            "datatype": dt.dataType,
            "typename": variable_type,
            "value": default_value,
            "category": cat_sys_name,
            "group": variable_group,
            #TODO сделать чтобы системные имена генерировались от обычных
            "systemname": variableSystemName, # никогда не должно изменяться и всегда эквивалентно ключу в категории

            "reprType": reprType,
            "reprDataType": str(dt),
        }

        self.registerVariable(vardict)
        # reset value to default
        self.widInitVal.set_value(self._initialValue)

    @staticmethod
    def getVariableMakerVisualInfo(variable_id,variable_data):
        varmgr = VarMgrBaseWidgetType.getVarMgr()
        name = variable_data['name']
        variable_type = variable_data['typename']
        fulltype = variable_data['type']
        value = variable_data['value']
        defvalstr = str(value) if not isinstance(value, str) else value

        #varInfo, dt = self._getVarDataByRepr(variable_data['reprType'],variable_data['reprDataType'])
        varInfo, dt = varmgr.getVarDataByType(fulltype,True)
        if not varInfo or not dt:
            raise Exception(f"Невозможно загрузить переменную {variable_id}; Информация и данные о типе: {varInfo}; {dt}")

        if dt.dataType != "value":
            if isinstance(varInfo,list):
                variable_type = f'{variable_type} ({", ".join([o__.variableTextName for o__ in varInfo])})'
            else:
                variable_type = f'{variable_type} ({varInfo.variableTextName})'
        else:
            variable_type = varInfo.variableTextName

        return [name,variable_type,defvalstr]
    
    @staticmethod
    def onItemCreated(item:QTreeWidgetItem,variable_id,variable_data):
        varmgr = VarMgrBaseWidgetType.getVarMgr()
        fulltype = variable_data['type']
        
        #set description to column 1
        item.setToolTip(1,fulltype)
        
        varInfo, dt = varmgr.getVarDataByType(fulltype,False)

        if isinstance(varInfo,list):
            pathes = dt.icon
            colors = [o__.color for o__ in varInfo]
            item.setIcon(1,QIcon(generateIconParts(pathes,colors)))
        else:
            icn = QIcon(dt.icon)
            icn = updateIconColor(icn,varInfo.color)
            item.setIcon(1, icn)
    
class VarMgrFunctionWidget(VarMgrBaseWidgetType):
    
    def createWidgets(self):
        layout = self.getMainLayout()
        from ReNode.ui.VarMgrWidgetTypes.FunctionDef import FunctionDefWidget


        # Возаращаемое значение
        layRet = QHBoxLayout()
        layout.addLayout(layRet)
        retvalText__ = QLabel("Возвращаемое значение:")
        retvalText__.setToolTip("Возвращаемое значение - это то, что будет возвращать функция после своего выполнения")
        layRet.addWidget(retvalText__,alignment=Qt.AlignLeft)
        self.comboButton = SearchComboButton()
        cont = self.getVarMgr().getAllTypesTreeContent()
        if cont:
            newitem = createTreeContentItem("null","Не возвращает значения",QIcon())
            newitem['desc'] = "Функция не будет возвращать никакого значения"
            cont['childs'].insert(0,newitem)
        self.comboButton.loadContents(cont)
        layRet.addWidget(self.comboButton)
        
        #todo datatype (value, list etc)

        self.retDesc = QLineEdit()
        self.retDesc.setPlaceholderText("Описание...")
        self.retDesc.setToolTip("Описание возвращаемого значения (опционально)")
        layout.addWidget(self.retDesc)

        layout.addWidget(FunctionDefWidget())
    
    def getVariableMakerVisualInfo(variable_id,variable_data):
        return

    @staticmethod
    def onItemCreated(item:QTreeWidgetItem,variable_id,variable_data):
        pass