from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from ReNode.ui.SearchMenuWidget import SearchComboButton,addTreeContent,createTreeDataContent,addTreeContentItem,createTreeContentItem
from ReNode.app.utils import updateIconColor, mergePixmaps, generateIconParts, transliterate
import datetime

def prepEscape(data):
    return data.replace(':',"\:").replace('\"',"\\\"")

def prepVariableName(origName):
    return transliterate(origName,replaceSpaceToUnderline=True)

class VarMgrBaseWidgetType:
    """
        Базовый тип переменной. В унаследованных членах должны быть реализованы:
        - createWidgets
        - статический метод getVariableMakerVisualInfo
        - статчиеский метод onItemCreated

        - статическое поле instancerKind для отношения типа действия к классу переменной (getvar->variable.get)
        - классовый метод onCreateVarFromTree - вызывается при создании переменной в графе

        - статическое поле kindTypes - список типов (classfunc,classvar)
        - статический метод onCreateVLibData для создания узлов в библиотеке из пользовательских данных
    """
    def __init__(self):
        from ReNode.ui.VariableManager import VariableManager,VariableCategory
        self.layout :QVBoxLayout = None
        self.variableManagerRef :VariableManager = None
        self.categoryObject :VariableCategory = None

    kindTypes = []

    canUpdateNode = False
    """Флаг обновления узла при создании переменной. Сейчас включен только для локальных переменных"""

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

    def createVariable(self,varname,vargroup) -> None|bool:
        """Если эта функция возврщает True то создание переменной было успешно"""
        self.variableManagerRef.showErrorMessageBox(f"Создание для \'{self.categoryObject.categoryTextName}\' не реализовано в текущей версии редактора")

    def registerVariable(self,vardict):
        from NodeGraphQt.base.commands import VariableCreatedCommand
        cat_sys_name = self.categoryObject.category
        varmgr = self.variableManagerRef

        if not varmgr.variables.get(cat_sys_name):
            varmgr.variables[cat_sys_name] = {}
        
        varId = self.generateVariableId()
        
        if varId in varmgr.variables[cat_sys_name]:
            varmgr.showErrorMessageBox(f"Коллизия системных имен идентификаторов. Айди '{varId}' уже существует! Повторите попытку создания.")
            return
        
        for cat,stor in varmgr.variables.items():
            if varId in stor:
                varmgr.showErrorMessageBox(f"Коллизия системных имен идентификаторов. Айди '{varId}' уже существует в другой категории - {cat}. Повторите попытку создания.")
                return

        varmgr.getUndoStack().push(VariableCreatedCommand(varmgr,cat_sys_name,vardict,varId))

    @staticmethod
    def getVariableMakerVisualInfo(variable_id,variable_data):
        """Возвращает названия колонок для визуального отображения в дереве"""
        return None
    @staticmethod
    def onItemCreated(item:QTreeWidgetItem,variable_id,variable_data):
        """Пост-обработчик создания элемента в дереве. Например, можно установить описание или иконку"""
        return None

    def generateVariableId(self):
        itm = datetime.datetime.now()
        return f'{hex(id(itm))}_{itm.year}{itm.month}{itm.day}{itm.hour}{itm.minute}{itm.second}{itm.microsecond}'


    instancerKind = {
        "unknown":"noclass"
    }
    """Переопределяемый тип отношения типа действия к создаваемому классу переменной"""

    @classmethod
    def getVariableInstancerClassName(cls,instancerType,infoData,varData):
        """Возвращает имя инстансера для переменной (не переопределяемый)"""
        return cls.instancerKind.get(instancerType)

    @classmethod
    def onCreateVarFromTree(cls,fact,lvdata,nodeObj,instancerType):
        """Обработчик созданной переменной в графе:
            - fact - ссылка на факторию переменных
            - lvdata - словарь переменной. Содержит все данные, необходимые для создания
            - nodeObj - созданной узел
            - instancerType - тип инстансера (getvar,callfunc, etc...)
        """
        raise NotImplementedError()
    
    @classmethod
    def resolveCreatedNodeName(cls,oldName):
        return "<b>"+oldName+"</b>"
    
    @staticmethod
    def getInstanceByType(type):
        for class_ in VarMgrBaseWidgetType.__subclasses__():
            if type in class_.kindTypes:
                return class_
        return None

    @staticmethod
    def onCreateVLibData(factory,varDict,classDict):
        """Событие создания ноды в библиотеке. Преобразует пользовательский словарь в словарь библиотеки"""
        raise NotImplementedError("Require onCreateVLibData(factory,varDict) method")

class VarMgrVariableWidget(VarMgrBaseWidgetType):
    kindTypes = ['classvar']

    canUpdateNode = True

    @staticmethod
    def onCreateVLibData(factory,varDict,classDict):
        sysName = varDict['systemname']

        classDict['classObject']['fields']['defined'][sysName] = {
            "return": varDict["type"]
        }

        memberData = [f"def:f:{classDict['className']}.{sysName}_0"]
        memberData.append(f'name:{prepEscape(varDict["name"])}')

        #todo desc
        #memberData.append(f'desc:{prepEscape(varDict["desc"])}')
        memberData.append('prop:all')
        memberData.append('classprop:1')
        memberData.append(f'return:{varDict["type"]}') #todo desc for return type
        value = varDict['value']
        strValue = f'{value}'
        memberData.append(f'defval:{prepEscape(strValue)}')

        return '\n'.join(memberData)

    instancerKind = {
        "getvar": "variable.get",
        "setvar": "variable.set",
    }

    @classmethod
    def onCreateVarFromTree(cls, fact,lvdata, nodeObj, instancerType):

        varInfo,varDt = cls.getVarMgr().getVarDataByType(lvdata['type'])
        portColor = None

        #setup partial icon with color support
        kvdat = []
        if isinstance(varInfo,list):
            for i,varInfoElement in enumerate(varInfo):
                if i==0:
                    portColor = [*varInfoElement.color.getRgb()]
                kvdat.append(varDt.icon[i])
                kvdat.append(varInfoElement.color.darker(65))
        else:
            kvdat = [varDt.icon,varInfo.color.darker(65)]
            portColor = [*varInfo.color.getRgb()]
        nodeObj.update_icon_parts(kvdat,True)

        nodeObj.set_color(*portColor)

        if "setvar" == instancerType and varDt.dataType == 'value':
            props = varInfo.dictProp
            for k,v in props.items():
                fact.addProperty(nodeObj,k,lvdata['name'],v)

        vardict = None
        realType = lvdata['type']
        if "setvar" == instancerType:
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
            fact.addOutput(nodeObj,"Значение",vardict)
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

    def createWidgets(self):
        layout : QVBoxLayout = self.layout

        layout.addWidget(QLabel("Тип данных:"))

        type_layout = QHBoxLayout()
        layout.addLayout(type_layout)

        self.widVarType = SearchComboButton()
        # treeContent = createTreeDataContent()

        # objectTree = treeContent
        # for vobj in self.variableTempateData:
        #     icon = QIcon("data\\icons\\pill_16x.png")
        #     colored_icon = updateIconColor(icon, vobj.color)
        #     _tempTree = addTreeContent(treeContent,vobj.variableType,vobj.variableTextName,colored_icon)
        #     if vobj.variableType == "object":
        #         objectTree = _tempTree
        # #gobj add
        # fact = self.nodeGraphComponent.getFactory()
        # objTree = fact.getClassAllChildsTree("GameObject")
        # addTreeContentItem(objectTree,objTree)

        # addTreeContentItem(objectTree,fact.getClassAllChildsTree("ServerClient"))
        # доступны все типы
        treeContent = self.getVarMgr().getAllTypesTreeContent()

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
        variable_type = self.widVarType.get_value() #имя типа (string,int,object...)
        default_value = self.widInitVal.get_value()
        varMgr = self.variableManagerRef
        
        realName = prepVariableName(variable_name)

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

            if var_typename != "string":
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

        vardict = {
            "name": variable_name,
            "type": var_typename,
            "value": default_value,
            "category": cat_sys_name,
            "group": variable_group,
            "systemname": realName, # никогда не должно изменяться и всегда эквивалентно ключу в категории
            
            "reprType": reprType,#todo remove
            "reprDataType": str(dt),#todo remove
        }

        self.registerVariable(vardict)
        # reset value to default
        self.widInitVal.set_value(self._initialValue)

        return True

    @staticmethod
    def getVariableMakerVisualInfo(variable_id,variable_data):
        varmgr = VarMgrBaseWidgetType.getVarMgr()
        name = variable_data['name']
        fulltype = variable_data['type']
        variable_type = fulltype #имя типа utf-8
        value = variable_data['value']
        defvalstr = str(value) if not isinstance(value, str) else value

        #varInfo, dt = self._getVarDataByRepr(variable_data['reprType'],variable_data['reprDataType'])
        varInfo, dt = varmgr.getVarDataByType(fulltype,True)
        if not varInfo or not dt:
            raise Exception(f"Невозможно загрузить переменную {variable_id}; Информация и данные о типе: {varInfo}; {dt}")

        if dt.dataType != "value":
            if isinstance(varInfo,list):
                variable_type = f'{dt.text} ({", ".join([o__.variableTextName for o__ in varInfo])})'
            else:
                variable_type = f'{dt.text} ({varInfo.variableTextName})'
        else:
            variable_type = varInfo.variableTextName

        return [name,variable_type,defvalstr]
    
    @staticmethod
    def onItemCreated(item:QTreeWidgetItem,variable_id,variable_data):
        varmgr = VarMgrBaseWidgetType.getVarMgr()
        fulltype = variable_data['type']
        
        #set description to column 1
        item.setToolTip(1,fulltype)
        
        item.setIcon(1,varmgr.getIconFromTypename(fulltype))

class VarMgrClassVariableWidget(VarMgrVariableWidget):
    canUpdateNode = False
    @classmethod
    def getVariableInstancerClassName(cls,instancerType,infoData,varData):
        className = infoData['classname']
        mem = f"fields.{className}.{(varData['systemname'])}_0"
        if instancerType == "setvar":
            return mem + ".set"
        elif instancerType == "getvar":
            return mem + ".get"
        else:
            return None
        
    def createVariable(self, varname, vargroup):
        
        realName = prepVariableName(varname)
        className = self.nodeGraphComponent.inspector.infoData.get('classname')
        if className:
            members = self.nodeGraphComponent.getFactory().getClassAllFields(className)
            members = [m.lower() for m in members]
            if realName.lower() in members:
                self.getVarMgr().showErrorMessageBox(f"Переменная с именем \"{varname}\" ({realName}) уже существует в классе \"{className}\".")
                return False
        
        return super().createVariable(varname, vargroup)

class VarMgrFunctionWidget(VarMgrBaseWidgetType):
    
    @classmethod
    def getVariableInstancerClassName(cls,instancerType,infoData,varData):
        className = infoData['classname']
        mem = f"methods.{className}.{(varData['systemname'])}_0"
        if instancerType == "deffunc":
            return mem + ".def"
        elif instancerType == "callfunc":
            return mem
        else:
            return None

    @staticmethod
    def onCreateVLibData(factory,varDict,classDict):
        
        #callfunc dict
        sysName = varDict['systemname']

        classDict['classObject']['methods']['defined'][sysName] = {
            "return": "<undefined>"
        }

        memberData = [f"def:m:{classDict['className']}.{sysName}_0"]
        memberData.append(f'name:{prepEscape(varDict["name"])}')
        if varDict.get("desc"):
            memberData.append(f'desc:{prepEscape(varDict["desc"])}')
        memberData.append("type:method")

        if varDict.get('returnType','null') != 'null':
            memberData.append(f'return:{prepEscape(varDict["returnType"])}:{prepEscape(varDict["returnDesc"])}')
        else:
            memberData.append(f'return:{prepEscape(varDict.get("returnType","null"))}')

        execType = "all"
        if varDict.get('isPure'): execType = "pure"

        memberData.append(f'exec:{execType}')

        #add ports
        for p in varDict['params']:
            memberData.append(f'in:{p["type"]}:{prepEscape(p["name"])}:{prepEscape(p["desc"])}')
            optionParams = []
            if p.get("opt",False): #check require connection
                optionParams.append("require=0")
                #так как параметр опциональный то подклчение не требуется
            
            serVal = prepEscape(str(p['value'])) #serialized value
            optionParams.append('def={}'.format(serVal))
            if optionParams:
                memberData.append(f'opt:{":".join(optionParams)}')

        return "\n".join(memberData)

    kindTypes = ['classfunc']

    instancerKind = {
        "deffunc": "function.def",
        "callfunc": "function.call",
    }

    @classmethod
    def onCreateVarFromTree(cls, fact,lvdata, nodeObj, instancerType):
        isDefineFunc = instancerType == "deffunc"
        
        icn = None
        if instancerType == "deffunc":
            icn = "data\\icons\\icon_Blueprint_OverrideFunction_16x"
        else:
            icn = "data\\icons\\icon_BluePrintEditor_Function_16px"

        nodeObj.set_icon(icn,True)
        nodeColor = None

        nodeColor = [
            149,
            94,
            0,
            255
            ] if isDefineFunc else [
                0,
                69,
                104,
                255
            ]

        if nodeColor: nodeObj.set_color(*nodeColor)

        varMgr = cls.getVarMgr()
        isPureFunc = lvdata.get("isPure")
        canMulCon = True if isDefineFunc else False
        for paramDict in lvdata['params']:
            portClr = varMgr.getColorByType(paramDict['type'])
            portParams = {
                "mutliconnect":canMulCon,
                "display_name":True,
                "color":portClr,
                "type":paramDict['type'],
                "allowtypes":[paramDict['type']],
                "style":None,
            }
            if isDefineFunc:
                fact.addOutput(nodeObj,paramDict['name'],portParams)
            else:
                fact.addInput(nodeObj,paramDict['name'],portParams)

                props = varMgr.getCustomPropsByType(paramDict['type'])
                for k,v in props.items():
                    fact.addProperty(nodeObj,k,paramDict['name'],v)
        
        if not isDefineFunc and lvdata['returnType'] != "null":
            
            #add return value
            portClr = varMgr.getColorByType(lvdata['returnType'])
            portParams = {
                "mutliconnect":False,
                "display_name":True,
                "color":portClr,
                "type":lvdata['returnType'],
                "allowtypes":[lvdata['returnType']],
                "style":None,
            }
            fact.addOutput(nodeObj,"Результат",portParams)

        if isPureFunc and not isDefineFunc:
            fInp = nodeObj.get_input(0)
            if fInp and fInp.view.port_typeName == "Exec":
                nodeObj.delete_input(fInp)
            fOut = nodeObj.get_output(0)
            if fOut and fOut.view.port_typeName == "Exec":
                nodeObj.delete_output(fOut)
            pass

        return True

    @classmethod
    def resolveCreatedNodeName(cls,oldName):
        return oldName

    def createWidgets(self):
        layout = self.getMainLayout()
        from ReNode.ui.VarMgrWidgetTypes.FunctionDef import FunctionDefWidget

        #Описание функции
        layRet = QHBoxLayout()
        layout.addLayout(layRet)
        descTextInfo = QLabel("Описание функции:")
        descTextInfo.setToolTip("Выводимое описание функции (опционально)")
        layRet.addWidget(descTextInfo,alignment=Qt.AlignLeft)
        self.funcitonDescText = QTextEdit()
        self.funcitonDescText.setPlaceholderText("Описание...")
        layRet.addWidget(self.funcitonDescText)

        #pure function flag
        layRet = QHBoxLayout()
        layout.addLayout(layRet)
        pureFuncText__ = QLabel("Чистая функция:")
        pureFuncText__.setToolTip("Флаг, показывающий, что функция чистая.\nЧистые функции не изменяют целевой объект и вызываются для каждого подключенного узла.")
        layRet.addWidget(pureFuncText__,alignment=Qt.AlignLeft)
        self.pureFuncFlag = QCheckBox()
        layRet.addWidget(self.pureFuncFlag)

        # Возаращаемое значение
        layRet = QHBoxLayout()
        layout.addLayout(layRet)
        retvalText__ = QLabel("Возвращаемое значение:")
        retvalText__.setToolTip("Возвращаемое значение - это то, что будет возвращать функция после своего выполнения")
        layRet.addWidget(retvalText__,alignment=Qt.AlignLeft)
        self.returnType = SearchComboButton()
        cont = self.getVarMgr().getAllTypesTreeContent()
        if cont:
            newitem = createTreeContentItem("null","Не возвращает значения",QIcon())
            newitem['desc'] = "Функция не будет возвращать никакого значения"
            cont['childs'].insert(0,newitem)
        self.returnType.loadContents(cont)
        __retTypeZone = QWidget()
        __retTypeLayout = QGridLayout()
        __retTypeZone.setLayout(__retTypeLayout)
        layRet.addWidget(__retTypeZone,10)
        __retTypeLayout.addWidget(self.returnType,0,0)

        #datatype return
        self.widReturnDataType = QComboBox()
        for vobj in self.variableManagerRef.variableDataType:
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
            self.widReturnDataType.addItem(icn,vobj.text)
            self.widReturnDataType.setItemData(self.widReturnDataType.count()-1,vobj.dataType,Qt.UserRole)
        
        __retTypeLayout.addWidget(self.widReturnDataType,0,1)

        self.widValTypes = SearchComboButton()
        cont = self.getVarMgr().getAllTypesTreeContent()
        #load content for valuetypes (dict values)
        if cont:
            self.widValTypes.loadContents(cont)
        self.widValTypesLabel = QLabel("Тип значений:")
        __retTypeLayout.addWidget(self.widValTypesLabel,1,0)
        __retTypeLayout.addWidget(self.widValTypes,1,1)
        def onDataTypeChanged():
            valType = self.returnType.get_value()
            dataType = self.widReturnDataType.currentData()
            
            self.widReturnDataType.setVisible(valType != "null")

            canShowLine2 = dataType == "dict" and valType != "null"
            self.widValTypes.setVisible(canShowLine2)
            self.widValTypesLabel.setVisible(canShowLine2)
        self.widReturnDataType.currentIndexChanged.connect(lambda: onDataTypeChanged())
        self.returnType.changed_event.connect(lambda: onDataTypeChanged())
        onDataTypeChanged()

        self.retDesc = QLineEdit()
        self.retDesc.setPlaceholderText("Описание...")
        self.retDesc.setToolTip("Описание возвращаемого значения (опционально)")
        layout.addWidget(self.retDesc)

        self.widFunctionParams = FunctionDefWidget()
        layout.addWidget(self.widFunctionParams)
    
    def getReturnTypeInfo(self):
        """Возвращает tuple с полным типом возвращаемого значения и описанием (если указано)"""
        retType = self.returnType.get_value()
        retDesc = self.retDesc.text()
        #no return
        if retType == "null":
            return retType,retDesc
        
        datatype = self.widReturnDataType.currentData()
        if datatype != "value":
            containerType = retType
            if datatype=='dict':
                containerType += f",{self.widValTypes.get_value()}"
            retType = f'{datatype}[{containerType}]'

        return retType,retDesc

    def createVariable(self,varname,vargroup):
        varMgr = self.getVarMgr()
        funcName = varname
        funcGrp = vargroup
        funcDesc = self.funcitonDescText.toPlainText()
        retTypename, retDesc = self.getReturnTypeInfo()
        funcParamsDict = self.widFunctionParams.getParamInfo()
        isPureFunc = self.pureFuncFlag.isChecked()
        #retType = self.comboButton.get_value()

        retTypename = varMgr.prepareTypeForCreate(retTypename)

        if retTypename == 'null' and isPureFunc:
            self.getVarMgr().showErrorMessageBox("Нельзя создать чистую функцию, которая не возвращает значение.")
            return False

        realName = prepVariableName(funcName)
        className = self.nodeGraphComponent.inspector.infoData.get('classname')
        if className:
            members = self.nodeGraphComponent.getFactory().getClassAllMethods(className)
            members = [m.lower() for m in members]
            if realName.lower() in members:
                self.getVarMgr().showErrorMessageBox(f"Функция с именем \"{funcName}\" ({realName}) уже существует в классе \"{className}\".")
                return False

        #check params
        uniParams = []
        for i, param in enumerate(funcParamsDict):
            if param['name'] == '':
                self.getVarMgr().showErrorMessageBox(f"Параметр {i+1} должен иметь имя. Укажите его.")
                return
            if param['name'] in ["nameid","Вход","Выход"]:
                self.getVarMgr().showErrorMessageBox(f"Параметр {i+1} не может иметь зарезервированное имя \"{param['name']}\". Укажите другое имя.")
                return
            if param['name'] in uniParams:
                self.getVarMgr().showErrorMessageBox(f"Имя параметра \"{param['name']}\" уже использовано в параметре {uniParams.index(param['name'])+1}. Укажите другое имя.")
                return
            uniParams.append(param['name'])

        funcInfo = {
            "name":funcName,
            "group":funcGrp,
            "desc":funcDesc,
            "params":funcParamsDict,
            'isPure': isPureFunc,
            "returnType":retTypename,
            "returnDesc":retDesc,

            "systemname": realName
        }

        self.registerVariable(funcInfo)
        return True

    @staticmethod
    def getVariableMakerVisualInfo(variable_id,variable_data):
        vmgr = VarMgrBaseWidgetType.getVarMgr()
        typeNameText = vmgr.getTextTypename(variable_data["returnType"])
        retT = f'Возвращает: {typeNameText}'
        paramList = ', '.join([vmgr.getTextTypename(dictInfo['type']) for dictInfo in variable_data["params"]])
        return [variable_data['name'],retT,"Параметры: " + paramList]

    @staticmethod
    def onItemCreated(item:QTreeWidgetItem,variable_id,variable_data):
        vmgr = VarMgrBaseWidgetType.getVarMgr()
        item.setIcon(0,QIcon("data\\icons\\icon_BluePrintEditor_Function_16px"))

        item.setIcon(1,vmgr.getIconFromTypename(variable_data["returnType"]))
        pass